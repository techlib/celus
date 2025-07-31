import logging
from datetime import date
from unittest import mock

import pytest
from celus_nigiri import CounterRecord
from django.core.management import call_command
from django.db.models import Sum
from django.utils.timezone import now
from organizations.fake_data import OrganizationFactory
from organizations.tests.conftest import organizations  # noqa - fixture
from publications.fake_data import PlatformFactory, TitleFactory
from publications.models import Platform
from publications.tests.conftest import interest_groups, interest_rt  # noqa - fixture

from logs.cubes import AccessLogCube, create_ch_backend
from logs.fake_data import (
    ImportBatchFactory,
    ImportBatchFullFactory,
    InterestGroupFactory,
    MetricFactory,
    ReportTypeFactory,
)
from logs.logic.data_import import import_counter_records
from logs.logic.interest.computation import (
    InterestComputer,
    _find_metric_interest_changes,
    _find_report_type_metric_disconnect,
    _find_unprocessed_batches,
    fast_compare_existing_and_new_records,
    find_superseded_import_batches,
    find_superseding_import_batches,
    get_report_type_superseding_report_types,
    get_report_types_superseded_by_report_type,
    sync_interest_for_import_batch,
)
from logs.logic.materialized_reports import (
    create_materialized_accesslogs,
    sync_materialized_reports_for_import_batch,
)
from logs.models import (
    AccessLog,
    Dimension,
    DimensionText,
    InterestConfig,
    InterestDimensionValueMapping,
    InterestProfile,
    Metric,
    ReportInterestMetric,
    ReportMaterializationSpec,
    ReportType,
)
from logs.tasks import sync_interest_for_superseded_import_batches_task


@pytest.mark.clickhouse
@pytest.mark.usefixtures("clickhouse_db")
@pytest.mark.django_db()
class TestInterestCalculation:
    @classmethod
    def get_dim_text_id(cls, dim_name, text):
        return DimensionText.objects.get(
            dimension=Dimension.objects.get(short_name=dim_name), text=text
        ).pk

    def test_interest_rt_structure(self, interest_rt):
        assert interest_rt.dimensions_sorted[0].short_name == "Original_Report_Type"
        assert interest_rt.dimensions_sorted[1].short_name == "Original_Metric"
        assert interest_rt.dimensions_sorted[2].short_name == "Access_Type"
        assert interest_rt.dimensions_sorted[3].short_name == "Access_Method"

    def test_extract_interest_from_import_batch(
        self, report_type_nd, interest_rt, django_assert_max_num_queries
    ):
        uir = MetricFactory.create(short_name="Unique_Item_Requests")
        rt = report_type_nd(1)
        ig = InterestGroupFactory(short_name="ig1", position=1)
        ReportInterestMetric.objects.create(report_type=rt, metric=uir, interest_group=ig)
        titles = TitleFactory.create_batch(5)
        ib = ImportBatchFullFactory.create(
            report_type=rt, create_accesslogs__metrics=[uir], create_accesslogs__titles=titles
        )
        with django_assert_max_num_queries(10):  # TODO: lower this number later
            interest_computer = InterestComputer(interest_rt)
        with django_assert_max_num_queries(35):  # TODO: lower this number later
            interest_data = interest_computer.extract_interest_from_import_batch(ib)

        assert len(interest_data) == 5

        for rec in interest_data:
            orig_rt_dim_text_id = self.get_dim_text_id("Original_Report_Type", rt.short_name)
            assert rec["dim1"] == orig_rt_dim_text_id
            assert DimensionText.objects.get(pk=orig_rt_dim_text_id).text_local_en == rt.name_en, (
                "whole name is preserved"
            )
            orig_metric_dim_text_id = self.get_dim_text_id("Original_Metric", uir.short_name)
            assert rec["dim2"] == orig_metric_dim_text_id
            assert (
                DimensionText.objects.get(pk=orig_metric_dim_text_id).text_local_en == uir.name_en
            ), "whole name is preserved"
            assert rec["dim3"] == self.get_dim_text_id("Access_Type", "Controlled")
            assert rec["dim4"] == self.get_dim_text_id("Access_Method", "Normal")
            assert rec["metric_id"] != uir.pk
            assert Metric.objects.get(pk=rec["metric_id"]).short_name == "ig1"
            assert rec["value"] != 0

    def test_simple(
        self, counter_records, organizations, report_type_nd, interest_rt, interest_groups
    ):
        platform = Platform.objects.create(
            short_name="Platform1", name="Platform 1", provider="Provider 1"
        )
        report_type = report_type_nd(1)
        organization = organizations[0]
        orig_metric = MetricFactory.create(short_name="Hits")
        # define the interest
        ReportInterestMetric.objects.create(
            report_type=report_type, metric=orig_metric, interest_group=interest_groups["full_text"]
        )
        # import data
        data1 = [
            ["Title1", "2018-01-01", "1v1", 1],
            ["Title2", "2018-01-01", "1v2", 2],
            ["Title3", "2018-01-01", "1v2", 4],
        ]
        crs1 = counter_records(data1, metric="Hits", platform="Platform1")
        ibs, _stats = import_counter_records(report_type, organization, platform, crs1)
        # check
        assert len(ibs) == 1, "only one import batch created"
        assert AccessLog.objects.count() == 6, "3 normal + 3 interest"
        assert report_type.accesslog_set.count() == 3, "3 normal logs"
        assert report_type.accesslog_set.aggregate(sum=Sum("value"))["sum"] == 7
        assert interest_rt.accesslog_set.count() == 3, "3 interest logs"
        assert interest_rt.accesslog_set.aggregate(sum=Sum("value"))["sum"] == 7
        for al in interest_rt.accesslog_set.all():
            assert al.dim1 == self.get_dim_text_id("Original_Report_Type", report_type.short_name)
            assert al.dim2 == self.get_dim_text_id("Original_Metric", orig_metric.short_name)
            assert al.dim3 == self.get_dim_text_id("Access_Type", "Controlled")
            assert al.dim4 == self.get_dim_text_id("Access_Method", "Normal")
            assert al.metric_id != orig_metric.pk
            assert Metric.objects.get(pk=al.metric_id).short_name == "full_text"

    @pytest.mark.parametrize(["new_before_old"], [[True], [False]])
    @pytest.mark.django_db(transaction=True)
    def test_superseded_report_types(
        self,
        counter_records,
        organizations,
        report_type_nd,
        new_before_old,
        interest_rt,
        interest_groups,
    ):
        """
        Test that when there are data for two report types from which one obsoletes the other,
        the newer data get precedence in interest values. On the other hand, if there are only
        data for that date in the old batch, take the data from there.

        The `new_before_old` parameter controls for which RT the data are loaded first.
        If old is loaded later, it will simply not create the extra interest logs. If new is
        loaded later, it will also need to remove the corresponding interest logs from old.
        This way we test both scenarios in one test. Both should end up with the same result.
        """
        organization = organizations[0]
        platform = Platform.objects.create(
            short_name="Platform1", name="Platform 1", provider="Provider 1"
        )
        report_type_old: ReportType = report_type_nd(1, short_name="old")
        report_type_new: ReportType = report_type_nd(1, short_name="new")
        report_type_old.superseded_by = report_type_new
        report_type_old.save()
        # now define the interest
        hit_metric = MetricFactory.create(short_name="Hits")
        ReportInterestMetric.objects.create(
            report_type=report_type_old,
            metric=hit_metric,
            interest_group=interest_groups["full_text"],
        )
        ReportInterestMetric.objects.create(
            report_type=report_type_new,
            metric=hit_metric,
            interest_group=interest_groups["full_text"],
        )
        # prepare data
        data_old = [
            ["Title1", "2018-01-01", "1v1", 1],
            ["Title2", "2018-01-01", "1v2", 2],
            ["Title3", "2018-02-01", "1v2", 4],  # this is extra - has different date
        ]
        crs_old = counter_records(data_old, metric="Hits", platform="Platform1")
        data_new = [
            ["Title1", "2018-01-01", "1v1", 8],
            ["Title2", "2018-01-01", "1v2", 16],
            ["Title3", "2018-01-01", "1v2", 32],  # date differs
        ]
        crs_new = counter_records(data_new, metric="Hits", platform="Platform1")
        # import and check
        if new_before_old:
            ibs_new, _stats = import_counter_records(
                report_type_new, organization, platform, crs_new
            )
        ibs_old, _stats = import_counter_records(report_type_old, organization, platform, crs_old)
        if not new_before_old:
            ibs_new, _stats = import_counter_records(
                report_type_new, organization, platform, crs_new
            )
        assert len(ibs_old) == 2, "one import batch per month"
        old_ib1, old_ib2 = sorted(ibs_old, key=lambda x: x.date)
        old_ib1.refresh_from_db()
        old_ib2.refresh_from_db()
        assert old_ib1.date == date(2018, 1, 1)
        assert old_ib2.date == date(2018, 2, 1)
        assert old_ib1.interest_ib == ibs_new[0], "interest is superseded by new"
        assert old_ib1.interest_timestamp is not None, "interest timestamp is set"
        assert old_ib2.interest_ib == old_ib2, "contains its own interest"
        assert old_ib1.accesslog_set.count() == 2, "2 normal + no interest logs in first batch"
        assert old_ib2.accesslog_set.count() == 2, "1 normal + 1 interest logs in second batch"

        assert len(ibs_new) == 1, "only one import batch created for one month"
        new_ib = ibs_new[0]
        assert new_ib.accesslog_set.count() == 6, "3 normal logs + 3 interest logs"
        assert interest_rt.accesslog_set.count() == 4, "3 new interest logs + 1 remaining old"

    def test_two_report_types_with_the_same_metric(
        self, counter_records, organizations, report_type_nd, interest_rt
    ):
        """
        Test that when two report types use the same metric for interest calculation,
        the interest is calculated correctly.
        """
        organization = organizations[0]
        platform = Platform.objects.create(
            short_name="Platform1", name="Platform 1", provider="Provider 1"
        )
        report_type_1: ReportType = report_type_nd(1, short_name="old")
        report_type_2: ReportType = report_type_nd(1, short_name="new")
        # now define the interest
        hit_metric = MetricFactory.create(short_name="Hits")
        ig1 = InterestGroupFactory(short_name="ig1", position=1)
        ig2 = InterestGroupFactory(short_name="ig2", position=2)
        ReportInterestMetric.objects.create(
            report_type=report_type_1, metric=hit_metric, interest_group=ig1
        )
        ReportInterestMetric.objects.create(
            report_type=report_type_2, metric=hit_metric, interest_group=ig2
        )
        # prepare data
        data_1 = [
            ["Title1", "2018-01-01", "1v1", 1],
            ["Title2", "2018-01-01", "1v2", 2],
            ["Title3", "2018-02-01", "1v2", 4],  # this is extra - has different date
        ]
        data_2 = [
            ["Title1", "2018-01-01", "1v1", 8],
            ["Title2", "2018-01-01", "1v2", 16],
            ["Title3", "2018-01-01", "1v2", 32],  # date differs
        ]
        crs_1 = counter_records(data_1, metric="Hits", platform="Platform1")
        crs_2 = counter_records(data_2, metric="Hits", platform="Platform1")
        # import and check
        import_counter_records(report_type_1, organization, platform, crs_1)
        import_counter_records(report_type_2, organization, platform, crs_2)
        assert report_type_1.accesslog_set.count() == 3
        assert report_type_2.accesslog_set.count() == 3
        assert interest_rt.accesslog_set.count() == 6
        # check that the interest values are correct
        dim1 = interest_rt.dimensions_sorted[0]
        dim1_values = {
            rec["text"]: rec["pk"]
            for rec in DimensionText.objects.filter(dimension=dim1).values("pk", "text")
        }
        assert interest_rt.accesslog_set.filter(dim1=dim1_values["old"]).aggregate(
            sum=Sum("value")
        ) == {"sum": 7}
        assert interest_rt.accesslog_set.filter(dim1=dim1_values["new"]).aggregate(
            sum=Sum("value")
        ) == {"sum": 56}

    def test_with_materialized_reports(
        self, counter_records, organizations, report_type_nd, interest_rt
    ):
        """
        Test that when there are materialized report data present in import batch that they
        are not counted into interest.
        """
        platform = Platform.objects.create(
            short_name="Platform1", name="Platform 1", provider="Provider 1"
        )
        report_type = report_type_nd(1)
        organization = organizations[0]
        # define interest
        data1 = [
            ["Title1", "2018-01-01", "1v1", 1],
            ["Title2", "2018-01-01", "1v2", 2],
            ["Title3", "2018-01-01", "1v2", 4],
        ]
        crs1 = counter_records(data1, metric="Hits", platform="Platform1")

        ibs, _stats = import_counter_records(report_type, organization, platform, crs1)
        assert AccessLog.objects.count() == 3
        assert len(ibs) == 1, "only one import batch"
        # create materialized report
        mat_def = ReportMaterializationSpec.objects.create(
            base_report_type=report_type, keep_dim1=False
        )
        mat_rt = ReportType.objects.create(short_name="materialized", materialization_spec=mat_def)
        mat_rec_count = create_materialized_accesslogs(mat_rt)
        assert mat_rec_count == 3
        ib = ibs[0]
        assert ib.accesslog_set.count() == 6
        # connect the interest with report type and platform
        ReportInterestMetric.objects.create(
            report_type=report_type,
            metric=Metric.objects.get(short_name="Hits"),
            interest_group=InterestGroupFactory(short_name="ig1", position=1),
        )
        sync_interest_for_import_batch(ib, interest_rt)
        assert interest_rt.accesslog_set.count() == 3, "3 interest logs"
        assert interest_rt.accesslog_set.aggregate(sum=Sum("value"))["sum"] == 7

    @pytest.mark.django_db(transaction=True)
    def test_sync_interest_for_import_batch_with_interest_materialized_views(
        self, counter_records, organizations, interest_rt, report_type_nd, settings
    ):
        """
        Test that when there are materialized views for interest, when interest is recalculated,
        the materialized views are recalculated as well.

        The recomputation is done in a transaction, so we need to use transaction=True in the
        decorator.
        """
        settings.CLICKHOUSE_SYNC_ACTIVE = False
        platform = Platform.objects.create(
            short_name="Platform1", name="Platform 1", provider="Provider 1"
        )
        rt = report_type_nd(1)
        organization = organizations[0]
        interest_sub_rt = report_type_nd(1, short_name="interest_sub")
        interest_sub_rt.materialization_spec = ReportMaterializationSpec.objects.create(
            name="X", base_report_type=interest_rt
        )
        interest_sub_rt.save()
        # define interest
        data1 = [
            ["Title1", "2018-01-01", "1v1", 1],
            ["Title2", "2018-01-01", "1v2", 2],
            ["Title3", "2018-01-01", "1v2", 4],
        ]
        crs1 = counter_records(data1, metric="Hits", platform="Platform1")

        ibs, _stats = import_counter_records(rt, organization, platform, crs1)
        assert AccessLog.objects.count() == 3
        assert len(ibs) == 1, "only one import batch"
        assert interest_rt.accesslog_set.count() == 0, "no interest logs yet"
        assert interest_sub_rt.accesslog_set.count() == 0, "no interest logs yet"
        # connect the interest with report type and platform
        ig = InterestGroupFactory(short_name="ig1", position=1)
        ReportInterestMetric.objects.create(
            report_type=rt, metric=Metric.objects.get(short_name="Hits"), interest_group=ig
        )
        for ib in ibs:
            sync_interest_for_import_batch(ib, interest_rt)
            sync_materialized_reports_for_import_batch(ib)
        assert interest_rt.accesslog_set.count() == 3, "3 interest logs"
        assert interest_rt.accesslog_set.aggregate(sum=Sum("value"))["sum"] == 7
        assert interest_sub_rt.accesslog_set.count() == 3, "3 interest logs"
        assert interest_sub_rt.accesslog_set.aggregate(sum=Sum("value"))["sum"] == 7
        assert (
            AccessLog.objects.filter(report_type=interest_rt, import_batch_id__in=ibs).count() > 0
        ), "interest logs are in the import batches"
        assert (
            AccessLog.objects.filter(report_type=interest_sub_rt, import_batch_id__in=ibs).count()
            > 0
        ), "materialized interest logs are in the import batches"
        # now let's update the interest definition
        # create a report type that supersedes the old one and thus should replace the
        # existing interest logs with the new ones
        rt2 = report_type_nd(1, short_name="new")
        rt.superseded_by = rt2
        rt.save()
        ReportInterestMetric.objects.create(
            report_type=rt2, metric=Metric.objects.get(short_name="Hits"), interest_group=ig
        )
        crs2 = counter_records(
            [["Title1", "2018-01-01", "1v1", 5], ["Title2", "2018-01-01", "1v2", 7]],
            metric="Hits",
            platform="Platform1",
        )
        ibs2, _stats = import_counter_records(rt2, organization, platform, crs2)
        # check that the interest logs are updated
        assert (
            AccessLog.objects.filter(report_type=interest_rt, import_batch_id__in=ibs).count() == 0
        ), "interest logs from the original import batches are removed"
        assert (
            AccessLog.objects.filter(report_type=interest_sub_rt, import_batch_id__in=ibs).count()
            == 0
        ), "materialized interest logs from the original import batches are removed"
        assert (
            AccessLog.objects.filter(report_type=interest_rt, import_batch_id__in=ibs2).count() > 0
        ), "interest logs are in the new import batches"
        assert (
            AccessLog.objects.filter(report_type=interest_sub_rt, import_batch_id__in=ibs2).count()
            > 0
        ), "materialized interest logs are in the new import batches"


@pytest.mark.clickhouse
@pytest.mark.usefixtures("clickhouse_db")
@pytest.mark.django_db()
class TestRealWorldInterestCalculation:
    def test_create_interest_definitions(self, interest_groups, interest_rt):
        call_command("check_report_type_dimensions", "--fix-it")
        assert ReportType.objects.count() > 0
        assert ReportInterestMetric.objects.count() == 0
        call_command("check_interest_definitions", "--fix-it")
        assert ReportInterestMetric.objects.count() > 0
        assert InterestProfile.objects.count() > 0

    @pytest.mark.parametrize("interest_profile", [None, "total", "unique"])
    def test_computation_with_profiles(self, interest_groups, interest_rt, interest_profile):
        call_command("check_report_type_dimensions", "--fix-it")
        call_command("check_interest_definitions", "--fix-it")
        # now compute interest
        organization = OrganizationFactory()
        if interest_profile:
            InterestConfig.objects.create(
                organization=organization,
                interest_profile=InterestProfile.objects.get(short_name=interest_profile),
            )
        platform = PlatformFactory()
        report_type = ReportType.objects.get(short_name="TR51")
        dates = {"start": "2024-01-01", "end": "2024-01-31"}
        dimension_data = {
            "Data_Type": "Book",
            "Access_Type": "Free_To_Read",
            "Access_Method": "Normal",
        }
        crs = [
            CounterRecord(
                value=2,
                title="Title1",
                metric="Total_Item_Requests",
                dimension_data=dimension_data,
                **dates,
            ),
            CounterRecord(
                value=1,
                title="Title1",
                metric="Unique_Item_Requests",
                dimension_data=dimension_data,
                **dates,
            ),
        ]
        import_counter_records(report_type, organization, platform, crs)
        assert AccessLog.objects.count() == 3, "two normal, one interest"
        assert AccessLog.objects.filter(report_type=interest_rt).count() == 1, "one interest log"
        al = AccessLog.objects.filter(report_type=interest_rt).first()
        assert al.value == 1 if interest_profile == "unique" else 2
        assert al.organization == organization
        assert al.platform == platform

        assert DimensionText.objects.get(id=al.dim1).text == "TR51"
        assert (
            DimensionText.objects.get(id=al.dim2).text == "Unique_Item_Requests"
            if interest_profile == "unique"
            else "Total_Item_Requests"
        )
        assert DimensionText.objects.get(id=al.dim3).text == "Free"
        assert DimensionText.objects.get(id=al.dim4).text == "Normal"

    def test_access_type_and_method(self, interest_groups, interest_rt):
        """
        Test that values of access type and method are correctly mapped to interest dimensions
        """
        call_command("check_report_type_dimensions", "--fix-it")
        call_command("check_interest_definitions", "--fix-it")
        organization = OrganizationFactory()
        platform = PlatformFactory()
        report_type = ReportType.objects.get(short_name="TR51")
        basics = {
            "start": "2024-01-01",
            "end": "2024-01-31",
            "title": "Title 1",
            "metric": "Total_Item_Requests",
        }
        crs = [
            CounterRecord(
                value=1,
                dimension_data={
                    "Data_Type": "Book",
                    "Access_Type": "Free_To_Read",
                    "Access_Method": "Normal",
                },
                **basics,
            ),
            CounterRecord(
                value=2,
                dimension_data={
                    "Data_Type": "Book",
                    "Access_Type": "Free_To_Read",
                    "Access_Method": "TDM",
                },
                **basics,
            ),
            CounterRecord(
                value=4,
                dimension_data={
                    "Data_Type": "Book",
                    "Access_Type": "Open",
                    "Access_Method": "Normal",
                },
                **basics,
            ),
            CounterRecord(
                value=8,
                dimension_data={"Data_Type": "Book", "Access_Type": "Open", "Access_Method": "TDM"},
                **basics,
            ),
            CounterRecord(
                value=16,
                dimension_data={
                    "Data_Type": "Book",
                    "Access_Type": "Controlled",
                    "Access_Method": "Normal",
                },
                **basics,
            ),
            CounterRecord(
                value=32,
                dimension_data={
                    "Data_Type": "Book",
                    "Access_Type": "Controlled",
                    "Access_Method": "TDM",
                },
                **basics,
            ),
            CounterRecord(
                value=64,
                dimension_data={
                    "Data_Type": "Book",
                    "Access_Type": "Controlled",
                    "Access_Method": "XXX",
                },
                **basics,
            ),
        ]

        import_counter_records(report_type, organization, platform, crs)
        # the interest should be:
        # - Free, Normal: 1 + 4 = 5
        # - Free, TDM: 2 + 8 = 10
        # - Controlled, Normal: 16 + 64 = 80
        # - Controlled, TDM: 32

        assert AccessLog.objects.count() == 7 + 4, "11 access logs"
        assert AccessLog.objects.filter(report_type=interest_rt).count() == 4, "4 interest logs"
        assert set(
            (
                DimensionText.objects.get(id=al.dim3).text,
                DimensionText.objects.get(id=al.dim4).text,
                al.value,
            )
            for al in AccessLog.objects.filter(report_type=interest_rt)
        ) == {
            ("Free", "Normal", 5),
            ("Free", "TDM", 10),
            ("Controlled", "Normal", 80),
            ("Controlled", "TDM", 32),
        }

    def test_data_type_filtering_in_ir(self, interest_groups, interest_rt):
        """
        Test that data type filtering in interest report type works
        """
        call_command("check_report_type_dimensions", "--fix-it")
        call_command("check_interest_definitions", "--fix-it")
        organization = OrganizationFactory()
        platform = PlatformFactory()
        report_type = ReportType.objects.get(short_name="IR51")
        basics = {
            "start": "2024-01-01",
            "end": "2024-01-31",
            "title": "Title 1",
            "metric": "Total_Item_Requests",
            "item": "Item 1",
        }
        crs = [
            CounterRecord(
                value=1,
                dimension_data={
                    "Data_Type": "Book",
                    "Access_Type": "Free_To_Read",
                    "Access_Method": "Normal",
                },
                **basics,
            ),
            CounterRecord(
                value=2,
                dimension_data={
                    "Data_Type": "Journal",
                    "Access_Type": "Free_To_Read",
                    "Access_Method": "TDM",
                },
                **basics,
            ),
            CounterRecord(
                value=4,
                dimension_data={
                    "Data_Type": "FooBar",
                    "Access_Type": "Open",
                    "Access_Method": "Normal",
                },
                **basics,
            ),
            CounterRecord(
                value=8,
                dimension_data={
                    "Data_Type": "Multimedia",
                    "Access_Type": "Open",
                    "Access_Method": "TDM",
                },
                **basics,
            ),
            CounterRecord(
                value=16,
                dimension_data={
                    "Data_Type": "Audiovisual",
                    "Access_Type": "Controlled",
                    "Access_Method": "Normal",
                },
                **basics,
            ),
            CounterRecord(
                value=32,
                dimension_data={
                    "Data_Type": "Image",
                    "Access_Type": "Controlled",
                    "Access_Method": "TDM",
                },
                **basics,
            ),
            CounterRecord(
                value=64,
                dimension_data={
                    "Data_Type": "Interactive_Resource",
                    "Access_Type": "Controlled",
                    "Access_Method": "XXX",
                },
                **basics,
            ),
        ]
        import_counter_records(report_type, organization, platform, crs)
        # the interest should be:
        # - Full_Text, Free, Normal: 1 + 4 = 5
        # - Full_Text, Free, TDM: 2 = 2
        # - Multimedia, Free, TDM: 8 = 8
        # - Multimedia, Controlled, Normal: 16+64 = 80
        # - Multimedia, Controlled, TDM: 32 = 32

        logger = logging.getLogger(__name__)
        logger.info(
            "Metric values %s",
            interest_rt.accesslog_set.all().values("metric__short_name").annotate(Sum("value")),
        )
        logger.info(
            "AccessLog values %s", interest_rt.accesslog_set.all().values_list("value", flat=True)
        )
        assert AccessLog.objects.count() == 7 + 5, "12 access logs"
        assert AccessLog.objects.filter(report_type=interest_rt).count() == 5, "5 interest logs"
        assert set(
            (
                al.metric.short_name,
                DimensionText.objects.get(id=al.dim3).text,
                DimensionText.objects.get(id=al.dim4).text,
                al.value,
            )
            for al in AccessLog.objects.filter(report_type=interest_rt)
        ) == {
            ("full_text", "Free", "Normal", 5),
            ("full_text", "Free", "TDM", 2),
            ("multimedia", "Free", "TDM", 8),
            ("multimedia", "Controlled", "Normal", 80),
            ("multimedia", "Controlled", "TDM", 32),
        }

    @pytest.mark.parametrize(
        ["rt", "expected"],
        [
            ("TR51", ["IR51"]),
            ("IR51", []),
            ("TR", ["IR51", "TR51"]),
            ("JR1", ["IR51", "TR51", "TR"]),
            ("BR2", ["IR51", "TR51", "TR"]),
            ("DB1", ["DR51", "DR"]),
            ("DR51", []),
            ("DR", ["DR51"]),
            ("IR_M1", ["IR51"]),
        ],
    )
    def test_get_report_type_superseding_report_types(
        self, interest_rt, interest_groups, rt, expected
    ):
        """
        Test that get_report_type_superseding_report_types returns the correct list of report types
        """
        call_command("check_report_type_dimensions", "--fix-it")
        call_command("check_interest_definitions", "--fix-it")
        rt = ReportType.objects.get(short_name=rt)
        assert [t.short_name for t in get_report_type_superseding_report_types(rt)] == expected

    @pytest.mark.parametrize(
        ["rt", "expected"],
        [
            ("TR", ["JR1", "BR2"]),
            ("TR51", ["TR", "JR1", "BR2"]),
            ("IR51", ["TR51", "TR", "JR1", "BR2", "IR_M1"]),
            ("DR51", ["DR", "DB1"]),
            ("DR", ["DB1"]),
            ("JR1", []),
            ("BR2", []),
            ("IR_M1", []),
        ],
    )
    def test_get_report_types_superseded_by_report_type(
        self, interest_rt, interest_groups, rt, expected
    ):
        """
        Test that get_report_types_superseded_by_report_type returns the correct list of
        report types
        """
        call_command("check_report_type_dimensions", "--fix-it")
        call_command("check_interest_definitions", "--fix-it")
        rt = ReportType.objects.get(short_name=rt)
        assert {t.short_name for t in get_report_types_superseded_by_report_type(rt)} == set(
            expected
        )

    @pytest.mark.parametrize(
        ["ref_rt", "expected"],
        [
            ("TR", []),  # the lowest in the hierarchy - no superseding
            ("TR51", ["TR"]),  # direct superseding
            ("IR51", ["TR51", "TR"]),  # indirect superseding
        ],
    )
    def test_find_superseded_import_batches(self, organizations, ref_rt, expected):
        """
        Test that find_superseded_import_batches returns the correct list of import batches.
        Tests both direct and indirect (over multiple report types) superseding.
        """
        organization = organizations[0]
        platform = PlatformFactory()
        call_command("check_report_type_dimensions", "--fix-it")
        call_command("check_interest_definitions", "--fix-it")
        tr = ReportType.objects.get(short_name="TR")
        tr_51 = ReportType.objects.get(short_name="TR51")
        ir_51 = ReportType.objects.get(short_name="IR51")
        br1 = ReportType.objects.get(short_name="BR1")
        # create import batches for all report types
        tr_to_ib = {
            rt.short_name: ImportBatchFactory(
                organization=organization, platform=platform, report_type=rt, date="2024-01-01"
            )
            for rt in [tr, tr_51, ir_51]
        }
        # extra import batch for BR1 - it is for a different month, so it should not be found
        # in any of the results
        ImportBatchFactory(
            organization=organization, platform=platform, report_type=br1, date="2024-02-01"
        )
        # now test the function
        ref_ib = tr_to_ib[ref_rt]
        assert set(find_superseded_import_batches(ref_ib)) == set(tr_to_ib[rt] for rt in expected)

    @pytest.mark.parametrize(
        ["existing_tr", "clashes"], [[None, False], ["IR51", True], ["TR51", True]]
    )
    def test_report_type_hierarchy_during_import(
        self, interest_rt, interest_groups, existing_tr, clashes
    ):
        """
        Test that interest from IR51 will prevent computation of interest from TR
        """
        call_command("check_report_type_dimensions", "--fix-it")
        call_command("check_interest_definitions", "--fix-it")
        organization = OrganizationFactory()
        platform = PlatformFactory()
        tr = ReportType.objects.get(short_name="TR")
        if existing_tr:
            ImportBatchFactory(
                organization=organization,
                platform=platform,
                report_type=ReportType.objects.get(short_name=existing_tr),
                date="2024-01-01",
            )
        crs = [
            CounterRecord(
                value=1,
                metric="Total_Item_Requests",
                start="2024-01-01",
                end="2024-01-31",
                title="Title 1",
                dimension_data={
                    "Data_Type": "Book",
                    "Access_Type": "Free_To_Read",
                    "Access_Method": "Normal",
                },
            )
        ]
        import_counter_records(tr, organization, platform, crs)
        if clashes:
            assert AccessLog.objects.count() == 1, "1 access log"
            assert AccessLog.objects.filter(report_type=interest_rt).count() == 0, "no interest log"
        else:
            assert AccessLog.objects.count() == 2, "2 access logs"
            assert AccessLog.objects.filter(report_type=interest_rt).count() == 1, "1 interest log"

    @pytest.mark.parametrize(
        ["tested_rt", "expected"],
        [
            ("TR51", "IR51"),
            ("IR51", None),
            ("TR", "IR51"),
            ("JR1", "IR51"),
            ("BR2", "IR51"),
            ("DB1", "DR51"),
            ("DR51", None),
            ("DR", "DR51"),
            ("IR_M1", "IR51"),
        ],
    )
    def test_find_superseding_import_batches(
        self, interest_rt, interest_groups, tested_rt, expected
    ):
        """
        Test that find_superseding_import_batches returns the correct list of import batches
        - even if there are multiple import batches for the same date - the one with the highest
        positioned report type should be returned
        """
        call_command("check_report_type_dimensions", "--fix-it")
        call_command("check_interest_definitions", "--fix-it")
        organization = OrganizationFactory()
        platform = PlatformFactory()
        # create import batches for the same date and for all report types
        for rt in ReportType.objects.all().exclude(short_name="interest"):
            ImportBatchFactory(
                organization=organization, platform=platform, report_type=rt, date="2024-01-01"
            )
        # get the tested report type
        rt = ReportType.objects.get(short_name=tested_rt)
        ibs = find_superseding_import_batches(rt, organization, platform)
        if expected:
            assert ibs[date(2024, 1, 1)].report_type.short_name == expected
        else:
            assert len(ibs) == 0

    @pytest.mark.parametrize("pr_version", ["PR", "PR51"])
    def test_report_interest_metric_for_pr_is_deleted(
        self, interest_rt, interest_groups, pr_version
    ):
        """
        Test that the report interest metric for PR is deleted as it is obsolete in new interest
        system
        """
        pr = ReportTypeFactory(short_name=pr_version)
        ReportInterestMetric.objects.create(
            report_type=pr,
            metric=MetricFactory(short_name="Unique_Item_Requests"),
            interest_group=interest_groups["full_text"],
        )
        assert ReportInterestMetric.objects.count() == 1
        call_command("check_interest_definitions", "--fix-it")
        assert ReportInterestMetric.objects.count() == 0


@pytest.mark.django_db()
class TestInterestRecomputationDetection:
    """
    Tests that code to detect ImportBatches that need to have their interest recomputed
    works properly
    """

    def test_find_unprocessed_batches(self, organizations, report_type_nd):
        organization = organizations[0]
        platform = Platform.objects.create(
            short_name="Platform1", name="Platform 1", provider="Provider 1"
        )
        report_type: ReportType = report_type_nd(1)
        ib1 = ImportBatchFactory(
            organization=organization, platform=platform, report_type=report_type
        )
        ImportBatchFactory(
            organization=organization,
            platform=platform,
            report_type=report_type,
            interest_timestamp=now(),
        )
        # now define the interest
        hit_metric = MetricFactory.create(short_name="Hits")
        ig = InterestGroupFactory(short_name="ig1", position=1)
        ReportInterestMetric.objects.create(
            report_type=report_type, metric=hit_metric, interest_group=ig
        )
        # let's test the function
        qs = _find_unprocessed_batches()
        assert {obj.pk for obj in qs} == {ib1.pk}

    def test_find_metric_interest_changes(self, organizations, report_type_nd):
        organization = organizations[0]
        platform = Platform.objects.create(
            short_name="Platform1", name="Platform 1", provider="Provider 1"
        )
        report_type: ReportType = report_type_nd(1, short_name="rt1")
        report_type2: ReportType = report_type_nd(1, short_name="rt2")
        assert report_type.pk != report_type2.pk
        # now define the interest
        ib1 = ImportBatchFactory(
            organization=organization,
            platform=platform,
            report_type=report_type,
            interest_timestamp=now(),
        )
        hit_metric = Metric.objects.create(short_name="Hits")
        ig = InterestGroupFactory(short_name="ig1", position=1)
        ReportInterestMetric.objects.create(
            report_type=report_type, metric=hit_metric, interest_group=ig
        )
        ImportBatchFactory(
            organization=organization,
            platform=platform,
            report_type=report_type,
            interest_timestamp=now(),
        )
        # let's test the function
        qs = _find_metric_interest_changes()
        assert {obj.pk for obj in qs} == {ib1.pk}

    def test_find_report_type_metric_disconnect(self, organizations, report_type_nd, interest_rt):
        organization = organizations[0]
        platform = Platform.objects.create(
            short_name="Platform1", name="Platform 1", provider="Provider 1"
        )
        report_type: ReportType = report_type_nd(1)
        # now define the interest
        ib1 = ImportBatchFactory(
            organization=organization,
            platform=platform,
            report_type=report_type,
            interest_timestamp=now(),
        )
        hit_metric = MetricFactory.create(short_name="Hits")
        ig = InterestGroupFactory(short_name="ig1", position=1)
        rim = ReportInterestMetric.objects.create(
            report_type=report_type, metric=hit_metric, interest_group=ig
        )
        AccessLog.objects.create(
            report_type=report_type,
            platform=platform,
            import_batch=ib1,
            organization=organization,
            value=10,
            date="2019-01-01",
            metric=hit_metric,
        )
        stats = sync_interest_for_import_batch(ib1, interest_rt)
        assert stats["new_logs"] == 1
        # let's test the function - this time it is generator as there are more queries returned
        qs = next(_find_report_type_metric_disconnect())
        assert {obj.pk for obj in qs} == set()
        # let's do the disconnect and retry
        rim.delete()
        qs = next(_find_report_type_metric_disconnect())
        assert {obj.pk for obj in qs} == {ib1.pk}

    @pytest.mark.django_db(transaction=True)
    def test_superseded_interest_deleted_with_different_titles(
        self, counter_records, organizations, report_type_nd, interest_rt
    ):
        """
        Test that there are old data for obsolete interest and I import new ones for the
        obsoleting RT, the old interest data will be removed even if the titles are different.
        """
        organization = organizations[0]
        platform = Platform.objects.create(
            short_name="Platform1", name="Platform 1", provider="Provider 1"
        )
        report_type_old: ReportType = report_type_nd(1, short_name="old")
        report_type_new: ReportType = report_type_nd(1, short_name="new")
        report_type_old.superseded_by = report_type_new
        report_type_old.save()
        # define interest
        hit_metric = MetricFactory(short_name="Hits")
        ig = InterestGroupFactory(short_name="ig1", position=1)
        ReportInterestMetric.objects.create(
            report_type=report_type_old, metric=hit_metric, interest_group=ig
        )
        ReportInterestMetric.objects.create(
            report_type=report_type_new, metric=hit_metric, interest_group=ig
        )
        # prepare data
        data_old = [
            ["Title1", "2018-01-01", "1v1", 1],
            ["Title2", "2018-01-01", "1v2", 2],
            ["Title3", "2018-01-01", "1v2", 4],
        ]
        data_new = [
            ["Title1", "2018-01-01", "1v1", 8],
            ["Title4", "2018-01-01", "1v2", 16],  # new title
            ["Title5", "2018-01-01", "1v2", 32],  # new title
        ]
        crs_old = counter_records(data_old, metric="Hits", platform="Platform1")
        crs_new = counter_records(data_new, metric="Hits", platform="Platform1")

        ibs_old, _stats = import_counter_records(report_type_old, organization, platform, crs_old)
        assert AccessLog.objects.count() == 6, "3 normal + 3 interest"
        assert len(ibs_old) == 1
        ib_old = ibs_old[0]
        assert interest_rt.accesslog_set.count() == 3, "3 of 3 should make it to interest"
        assert ib_old.accesslog_set.filter(report_type=interest_rt).count() == 3, (
            "3 interest records"
        )
        # import new data
        ibs_new, _stats = import_counter_records(report_type_new, organization, platform, crs_new)
        assert len(ibs_new) == 1
        ib_new = ibs_new[0]
        assert interest_rt.accesslog_set.count() == 3, "still 3 interest records, but new ones"
        assert ib_new.accesslog_set.filter(report_type=interest_rt).count() == 3, (
            "# new interest records from new data"
        )
        assert ib_old.accesslog_set.filter(report_type=interest_rt).count() == 0, (
            "old interest should be removed"
        )

    def test_interest_superseding_ib_is_deleted(self, organizations, report_type_nd, interest_rt):
        """
        Test that if IB1 is superseded by IB2, and IB2 is deleted, IB1 will have its interest
        recomputed
        """

        call_command("check_report_type_dimensions", "--fix-it")
        call_command("check_interest_definitions", "--fix-it")
        # now compute interest
        organization = OrganizationFactory()
        platform = PlatformFactory()
        tr_51 = ReportType.objects.get(short_name="TR51")
        tr_50 = ReportType.objects.get(short_name="TR")
        dates = {"start": "2024-01-01", "end": "2024-01-31"}
        dimension_data = {
            "Data_Type": "Book",
            "Access_Type": "Free_To_Read",
            "Access_Method": "Normal",
        }
        crs = [
            CounterRecord(
                value=2,
                title="Title1",
                metric="Total_Item_Requests",
                dimension_data=dimension_data,
                **dates,
            ),
            CounterRecord(
                value=1,
                title="Title1",
                metric="Unique_Item_Requests",
                dimension_data=dimension_data,
                **dates,
            ),
        ]
        tr51_ibs, _stats = import_counter_records(tr_51, organization, platform, crs)
        # import the same data for TR50
        tr50_ibs, _stats = import_counter_records(tr_50, organization, platform, crs)
        assert len(tr51_ibs) == 1
        assert len(tr50_ibs) == 1
        tr51_ib = tr51_ibs[0]
        tr50_ib = tr50_ibs[0]
        assert tr51_ib.interest_ib == tr51_ib
        assert tr51_ib.accesslog_set.filter(report_type=interest_rt).count() == 1
        assert tr50_ib.interest_ib == tr51_ib
        assert tr50_ib.accesslog_set.filter(report_type=interest_rt).count() == 0, "no interest"
        # delete the superseded IB
        with mock.patch(
            "logs.signals.sync_interest_for_superseded_import_batches_task.delay"
        ) as mock_task:
            tr51_ib.delete()
            assert mock_task.call_count == 1
        # now run the task manually
        sync_interest_for_superseded_import_batches_task()
        tr50_ib.refresh_from_db()
        # check that the interest is recomputed
        assert tr50_ib.interest_ib == tr50_ib
        assert tr50_ib.accesslog_set.filter(report_type=interest_rt).count() == 1, "interest"


class TestSupportCode:
    def test_fast_compare_existing_and_new_records(self):
        old_records = [
            {"a": 10, "b": 20, "pk": 1},
            {"a": 20, "b": 30, "pk": 2},
            {"a": 40, "b": 60, "pk": 3},
        ]
        new_records = [
            {"a": 10, "b": 20},
            {"a": 20, "b": 30},
            {"a": 50, "b": 60},
            {"a": 40, "b": 70},
        ]
        add, remove, same = fast_compare_existing_and_new_records(old_records, new_records, "ab")
        assert same == 2
        assert add == [{"a": 50, "b": 60}, {"a": 40, "b": 70}]
        assert remove == {3}


@pytest.mark.clickhouse
@pytest.mark.django_db(transaction=True)
class TestRecomputeInterestCLI:
    @pytest.mark.parametrize("interest_profile", [None, "total", "unique"])
    def test_recompute_force_interest_with_profiles(
        self, interest_groups, interest_rt, interest_profile, clickhouse_on_off
    ):
        call_command("check_report_type_dimensions", "--fix-it")
        call_command("check_interest_definitions", "--fix-it")
        # now compute interest
        organization = OrganizationFactory()
        if interest_profile:
            InterestConfig.objects.create(
                organization=organization,
                interest_profile=InterestProfile.objects.get(short_name=interest_profile),
            )
        platform = PlatformFactory()
        report_type = ReportType.objects.get(short_name="TR51")
        dates = {"start": "2024-01-01", "end": "2024-01-31"}
        dimension_data = {
            "Data_Type": "Book",
            "Access_Type": "Free_To_Read",
            "Access_Method": "Normal",
        }
        crs = [
            CounterRecord(
                value=2,
                title="Title1",
                metric="Total_Item_Requests",
                dimension_data=dimension_data,
                **dates,
            ),
            CounterRecord(
                value=1,
                title="Title1",
                metric="Unique_Item_Requests",
                dimension_data=dimension_data,
                **dates,
            ),
        ]
        import_counter_records(report_type, organization, platform, crs)

        # delete the interest data from accesslog
        AccessLog.objects.filter(report_type=interest_rt).delete(i_know_what_i_am_doing=True)
        assert AccessLog.objects.filter(report_type=interest_rt).count() == 0
        if clickhouse_on_off:
            ch_backend = create_ch_backend()
            ch_backend.delete_records(AccessLogCube.query().filter(report_type_id=interest_rt.pk))
            assert (
                ch_backend.get_count(AccessLogCube.query().filter(report_type_id=interest_rt.pk))
                == 0
            )

        call_command("recompute_interest", "-f")

        assert AccessLog.objects.count() == 3, "two normal, one interest"
        assert AccessLog.objects.filter(report_type=interest_rt).count() == 1, "one interest log"
        al = AccessLog.objects.filter(report_type=interest_rt).first()
        assert al.value == 1 if interest_profile == "unique" else 2
        assert al.organization == organization
        assert al.platform == platform

        assert DimensionText.objects.get(id=al.dim1).text == "TR51"
        assert (
            DimensionText.objects.get(id=al.dim2).text == "Unique_Item_Requests"
            if interest_profile == "unique"
            else "Total_Item_Requests"
        )
        assert DimensionText.objects.get(id=al.dim3).text == "Free"
        assert DimensionText.objects.get(id=al.dim4).text == "Normal"

        # check clickhouse was synced
        if clickhouse_on_off:
            ch_backend = create_ch_backend()
            assert (
                ch_backend.get_count(AccessLogCube.query().filter(report_type_id=interest_rt.pk))
                == 1
            )
            rec = ch_backend.get_one_record(
                AccessLogCube.query().filter(report_type_id=interest_rt.pk)
            )
            assert DimensionText.objects.get(id=rec.dim1).text == "TR51"
            assert DimensionText.objects.get(id=rec.dim2).text == (
                "Unique_Item_Requests" if interest_profile == "unique" else "Total_Item_Requests"
            )
            assert DimensionText.objects.get(id=rec.dim3).text == "Free"
            assert DimensionText.objects.get(id=rec.dim4).text == "Normal"

    @pytest.mark.parametrize("interest_profile", [None, "total", "unique"])
    def test_recompute_force_interest_with_profiles_and_no_mappings(
        self, interest_groups, interest_rt, interest_profile, clickhouse_on_off
    ):
        """
        Tests the recompute_interest cli command, but simulates situation where there are no
        mappings for Access_Type and Access_Method stored with the report types and default
        values are used.

        This test is here to guard against regression where the interest computation would
        compute null values for Access_Type and Access_Method instead of using the default values.
        """
        call_command("check_report_type_dimensions", "--fix-it")
        call_command("check_interest_definitions", "--fix-it")
        # delete the mappings - only the non-default ones
        InterestDimensionValueMapping.objects.exclude(source_rtdim__isnull=True).delete()
        # now compute interest
        organization = OrganizationFactory()
        if interest_profile:
            InterestConfig.objects.create(
                organization=organization,
                interest_profile=InterestProfile.objects.get(short_name=interest_profile),
            )
        platform = PlatformFactory()
        report_type = ReportType.objects.get(short_name="TR51")
        dates = {"start": "2024-01-01", "end": "2024-01-31"}
        dimension_data = {
            "Data_Type": "Book",
            "Access_Type": "Free_To_Read",
            "Access_Method": "Normal",
        }
        crs = [
            CounterRecord(
                value=2,
                title="Title1",
                metric="Total_Item_Requests",
                dimension_data=dimension_data,
                **dates,
            ),
            CounterRecord(
                value=1,
                title="Title1",
                metric="Unique_Item_Requests",
                dimension_data=dimension_data,
                **dates,
            ),
        ]
        import_counter_records(report_type, organization, platform, crs)

        # delete the interest data from accesslog
        AccessLog.objects.filter(report_type=interest_rt).delete(i_know_what_i_am_doing=True)
        assert AccessLog.objects.filter(report_type=interest_rt).count() == 0
        if clickhouse_on_off:
            ch_backend = create_ch_backend()
            ch_backend.delete_records(AccessLogCube.query().filter(report_type_id=interest_rt.pk))
            assert (
                ch_backend.get_count(AccessLogCube.query().filter(report_type_id=interest_rt.pk))
                == 0
            )

        call_command("recompute_interest", "-f")

        assert AccessLog.objects.count() == 3, "two normal, one interest"
        assert AccessLog.objects.filter(report_type=interest_rt).count() == 1, "one interest log"
        al = AccessLog.objects.filter(report_type=interest_rt).first()
        assert al.value == 1 if interest_profile == "unique" else 2
        assert al.organization == organization
        assert al.platform == platform

        assert DimensionText.objects.get(id=al.dim1).text == "TR51"
        assert (
            DimensionText.objects.get(id=al.dim2).text == "Unique_Item_Requests"
            if interest_profile == "unique"
            else "Total_Item_Requests"
        )
        assert DimensionText.objects.get(id=al.dim3).text == "Controlled", "default value"
        assert DimensionText.objects.get(id=al.dim4).text == "Normal", "default value"

        # check clickhouse was synced
        if clickhouse_on_off:
            ch_backend = create_ch_backend()
            assert (
                ch_backend.get_count(AccessLogCube.query().filter(report_type_id=interest_rt.pk))
                == 1
            )
            rec = ch_backend.get_one_record(
                AccessLogCube.query().filter(report_type_id=interest_rt.pk)
            )
            assert DimensionText.objects.get(id=rec.dim1).text == "TR51"
            assert DimensionText.objects.get(id=rec.dim2).text == (
                "Unique_Item_Requests" if interest_profile == "unique" else "Total_Item_Requests"
            )
            assert DimensionText.objects.get(id=rec.dim3).text == "Controlled", "default value"
            assert DimensionText.objects.get(id=rec.dim4).text == "Normal", "default value"
