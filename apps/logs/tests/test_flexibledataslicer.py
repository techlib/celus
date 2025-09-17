import codecs
import csv
from io import BytesIO, StringIO
from unittest.mock import MagicMock
from zipfile import ZipFile

import openpyxl
import pytest
from django.db.models import Q
from organizations.models import Organization
from publications.models import Item, Platform, Title
from tags.fake_data import TagClassFactory, TagFactory, TagForTitleFactory
from tags.models import AccessibleBy, Tag, TagScope

from logs.cubes import AccessLogCube, ch_backend
from logs.fake_data import MetricFactory
from logs.logic.materialized_reports import recompute_materialized_reports
from logs.logic.reporting.export import (
    FlexibleDataExcelExporter,
    FlexibleDataSimpleCSVExporter,
    FlexibleDataZipCSVExporter,
)
from logs.logic.reporting.filters import (
    DateDimensionFilter,
    ExplicitDimensionFilter,
    ForeignKeyDimensionFilter,
    TagClassDimensionFilter,
    TagDimensionFilter,
)
from logs.logic.reporting.slicer import FlexibleDataSlicer, SlicerConfigError, SlicerConfigErrorCode
from logs.models import (
    AccessLog,
    DimensionText,
    ImportBatch,
    Metric,
    ReportMaterializationSpec,
    ReportType,
)


def remap_row_keys_to_short_names(row: dict, primary_dimension, dimensions: list) -> dict:
    result = {}
    for key, value in row.items():
        if key.startswith("grp-"):
            parts = key[4:].split(",")
            new_key_parts = []
            for part, dimension in zip(parts, dimensions):
                obj = dimension.objects.get(pk=int(part))
                if hasattr(obj, "short_name"):
                    new_key_parts.append(obj.short_name)
                else:
                    new_key_parts.append(str(obj))
            new_key = "-".join(new_key_parts)
            result[new_key] = value
        elif key == "pk":
            obj = primary_dimension.objects.get(pk=value)
            result[key] = getattr(obj, "short_name", str(obj))
    return result


@pytest.mark.django_db
class TestFlexibleDataSlicerComputations:
    @pytest.fixture(params=[True, False])
    def show_zero(self, request):
        return request.param

    def test_data_generator(self, flexible_slicer_test_data):
        # the 1 + 3 bellow is 1 for report type with 1 dimension and 3 for report type with
        # 2 dimensions which contributes 4* the number of records
        assert AccessLog.objects.count() == 3 * 3 * 3 * 3 * 4 * 3 * (1 + 4)

        # # uncomment the following to get the test data in a CSV file
        # # it is useful when you want to use pivot table in a spreadsheet to check the calculations
        # # it will produce a table with primary keys for all dimensions
        # cursor = connection.cursor()
        #
        # with open('/tmp/TestFlexibleDataSlicer.csv', 'w') as out:
        #     cursor.copy_expert(
        #         "COPY (SELECT report_type_id, organization_id, platform_id, metric_id, target_id,"
        #         " date, dim1, dim2, value FROM logs_accesslog) TO stdout WITH CSV HEADER",
        #         out,
        #     )

    def test_org_sum_all(self, flexible_slicer_test_data):
        """
        Primary dimension: organization
        Group by:
        DimensionFilter:
        """
        slicer = FlexibleDataSlicer(primary_dimension="organization")
        # without any groups/columns, the result would not make much sense
        with pytest.raises(SlicerConfigError):
            slicer.get_data()

    def test_org_sum_by_platform(self, flexible_slicer_test_data, show_zero):
        """
        Primary dimension: organization
        Group by: platform
        DimensionFilter:
        """
        slicer = FlexibleDataSlicer(primary_dimension="organization")
        slicer.add_group_by("platform")
        slicer.include_all_zero_rows = show_zero
        data = list(slicer.get_data())
        assert len(data) == Organization.objects.count()
        data = [remap_row_keys_to_short_names(row, Organization, [Platform]) for row in data]
        data.sort(key=lambda rec: rec["pk"])
        # the following numbers were obtained by a separate calculation in a spreadsheet pivot table
        assert data == [
            {"pk": "org1", "pl1": 519318, "pl2": 717606, "pl3": 915894},
            {"pk": "org2", "pl1": 1114182, "pl2": 1312470, "pl3": 1510758},
            {"pk": "org3", "pl1": 1709046, "pl2": 1907334, "pl3": 2105622},
        ]

    def test_org_sum_by_platform_filter_metric(self, flexible_slicer_test_data, show_zero):
        """
        Primary dimension: organization
        Group by: platform
        DimensionFilter: metric
        """
        slicer = FlexibleDataSlicer(primary_dimension="organization")
        slicer.add_group_by("platform")
        slicer.include_all_zero_rows = show_zero
        metric = flexible_slicer_test_data["metrics"][0]
        slicer.add_filter(ForeignKeyDimensionFilter("metric", [metric.pk]))
        data = list(slicer.get_data())
        assert len(data) == Organization.objects.count()
        data = [remap_row_keys_to_short_names(row, Organization, [Platform]) for row in data]
        data.sort(key=lambda rec: rec["pk"])
        # the following numbers were obtained by a separate calculation in a spreadsheet pivot table
        assert data == [
            {"pk": "org1", "pl1": 167598, "pl2": 233694, "pl3": 299790},
            {"pk": "org2", "pl1": 365886, "pl2": 431982, "pl3": 498078},
            {"pk": "org3", "pl1": 564174, "pl2": 630270, "pl3": 696366},
        ]

    def test_org_sum_by_platform_filter_platform(self, flexible_slicer_test_data, show_zero):
        """
        Primary dimension: organization
        Group by: platform
        DimensionFilter: platform
        """
        slicer = FlexibleDataSlicer(primary_dimension="organization")
        platforms = flexible_slicer_test_data["platforms"][1:]
        slicer.add_filter(ForeignKeyDimensionFilter("platform", platforms), add_group=True)
        slicer.include_all_zero_rows = show_zero
        data = list(slicer.get_data())
        assert len(data) == Organization.objects.count()
        data = [remap_row_keys_to_short_names(row, Organization, [Platform]) for row in data]
        data.sort(key=lambda rec: rec["pk"])
        # the following numbers were obtained by a separate calculation in a spreadsheet pivot table
        assert data == [
            {"pk": "org1", "pl2": 717606, "pl3": 915894},
            {"pk": "org2", "pl2": 1312470, "pl3": 1510758},
            {"pk": "org3", "pl2": 1907334, "pl3": 2105622},
        ]

    def test_org_sum_by_platform_filter_platform_metric(self, flexible_slicer_test_data, show_zero):
        """
        Primary dimension: organization
        Group by: platform
        DimensionFilter: platform, metric
        """
        slicer = FlexibleDataSlicer(primary_dimension="organization")
        platforms = flexible_slicer_test_data["platforms"][1:]
        metrics = flexible_slicer_test_data["metrics"][1:]
        slicer.add_filter(ForeignKeyDimensionFilter("platform", platforms), add_group=True)
        slicer.add_filter(ForeignKeyDimensionFilter("metric", metrics), add_group=False)
        slicer.include_all_zero_rows = show_zero
        data = list(slicer.get_data())
        assert len(data) == Organization.objects.count()
        data = [remap_row_keys_to_short_names(row, Organization, [Platform]) for row in data]
        data.sort(key=lambda rec: rec["pk"])
        # the following numbers were obtained by a separate calculation in a spreadsheet pivot table
        assert data == [
            {"pk": "org1", "pl2": 483912, "pl3": 616104},
            {"pk": "org2", "pl2": 880488, "pl3": 1012680},
            {"pk": "org3", "pl2": 1277064, "pl3": 1409256},
        ]

    def test_org_sum_by_platform_filter_organization(self, flexible_slicer_test_data, show_zero):
        """
        Primary dimension: organization
        Group by: platform
        DimensionFilter: organization
        """
        slicer = FlexibleDataSlicer(primary_dimension="organization")
        organizations = flexible_slicer_test_data["organizations"][1:]
        slicer.add_filter(
            ForeignKeyDimensionFilter("organization", [org.pk for org in organizations]),
            add_group=False,
        )
        slicer.add_group_by("platform")
        slicer.include_all_zero_rows = show_zero
        data = list(slicer.get_data())
        assert len(data) == len(organizations)
        data = [remap_row_keys_to_short_names(row, Organization, [Platform]) for row in data]
        data.sort(key=lambda rec: rec["pk"])
        # the following numbers were obtained by a separate calculation in a spreadsheet pivot table
        assert data == [
            {"pk": "org2", "pl1": 1114182, "pl2": 1312470, "pl3": 1510758},
            {"pk": "org3", "pl1": 1709046, "pl2": 1907334, "pl3": 2105622},
        ]

    def test_org_sum_by_platform_filter_platform_organization(
        self, flexible_slicer_test_data, show_zero
    ):
        """
        Primary dimension: organization
        Group by: platform
        DimensionFilter: organization, platform
        """
        slicer = FlexibleDataSlicer(primary_dimension="organization")
        platforms = flexible_slicer_test_data["platforms"][1:]
        organizations = flexible_slicer_test_data["organizations"][1:]
        slicer.add_filter(
            ForeignKeyDimensionFilter("platform", [pl.pk for pl in platforms]), add_group=True
        )
        slicer.add_filter(
            ForeignKeyDimensionFilter("organization", [org.pk for org in organizations]),
            add_group=False,
        )
        slicer.include_all_zero_rows = show_zero
        data = list(slicer.get_data())
        assert len(data) == len(organizations)
        data = [remap_row_keys_to_short_names(row, Organization, [Platform]) for row in data]
        data.sort(key=lambda rec: rec["pk"])
        # the following numbers were obtained by a separate calculation in a spreadsheet pivot table
        assert data == [
            {"pk": "org2", "pl2": 1312470, "pl3": 1510758},
            {"pk": "org3", "pl2": 1907334, "pl3": 2105622},
        ]

    def test_org_sum_by_platform_metric_filter_platform_metric(
        self, flexible_slicer_test_data, show_zero
    ):
        """
        Primary dimension: organization
        Group by: platform, metric
        DimensionFilter: platform, metric
        """
        slicer = FlexibleDataSlicer(primary_dimension="organization")
        platforms = flexible_slicer_test_data["platforms"][1:]
        metrics = flexible_slicer_test_data["metrics"][1:]
        slicer.add_filter(
            ForeignKeyDimensionFilter("platform", [pl.pk for pl in platforms]), add_group=True
        )
        slicer.add_filter(
            ForeignKeyDimensionFilter("metric", [met.pk for met in metrics]), add_group=True
        )
        slicer.include_all_zero_rows = show_zero
        data = list(slicer.get_data())
        assert len(data) == Organization.objects.count()
        data = [
            remap_row_keys_to_short_names(row, Organization, [Platform, Metric]) for row in data
        ]
        data.sort(key=lambda rec: rec["pk"])
        # the following numbers were obtained by a separate calculation in a spreadsheet pivot table
        assert data == [
            {"pk": "org1", "pl2-m2": 239202, "pl3-m2": 305298, "pl2-m3": 244710, "pl3-m3": 310806},
            {"pk": "org2", "pl2-m2": 437490, "pl3-m2": 503586, "pl2-m3": 442998, "pl3-m3": 509094},
            {"pk": "org3", "pl2-m2": 635778, "pl3-m2": 701874, "pl2-m3": 641286, "pl3-m3": 707382},
        ]

    def test_platform_sum_by_metric_filter_dim1(self, flexible_slicer_test_data, show_zero):
        """
        Primary dimension: platform
        Group by: metric
        DimensionFilter: dim1
        """
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        texts = flexible_slicer_test_data["dimension_values"][0][:2]
        dim1_ids = DimensionText.objects.filter(text__in=texts).values_list("pk", flat=True)
        slicer.add_filter(ExplicitDimensionFilter("dim1", dim1_ids), add_group=False)
        slicer.add_group_by("metric")
        slicer.include_all_zero_rows = show_zero
        data = list(slicer.get_data())
        assert len(data) == Platform.objects.count()
        data = [remap_row_keys_to_short_names(row, Platform, [Metric]) for row in data]
        data.sort(key=lambda rec: rec["pk"])
        # the following numbers were obtained by a separate calculation in a spreadsheet pivot table
        assert data == [
            {"pk": "pl1", "m1": 731160, "m2": 742176, "m3": 753192},
            {"pk": "pl2", "m1": 863352, "m2": 874368, "m3": 885384},
            {"pk": "pl3", "m1": 995544, "m2": 1006560, "m3": 1017576},
        ]

    def test_platform_sum_by_rt_filter_metric(self, flexible_slicer_test_data, show_zero):
        """
        Primary dimension: platform
        Group by: report type
        DimensionFilter: metric
        """
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        slicer.add_filter(
            ForeignKeyDimensionFilter("metric", flexible_slicer_test_data["metrics"][:2]),
            add_group=False,
        )
        slicer.add_group_by("report_type")
        slicer.include_all_zero_rows = show_zero
        data = list(slicer.get_data())
        assert len(data) == Platform.objects.count()
        data = [remap_row_keys_to_short_names(row, Platform, [ReportType]) for row in data]
        data.sort(key=lambda rec: rec["pk"])
        # the following numbers were obtained by a separate calculation in a spreadsheet pivot table
        assert data == [
            {"pk": "pl1", "rt1": 80784, "rt2": 2131056},
            {"pk": "pl2", "rt1": 104112, "rt2": 2504304},
            {"pk": "pl3", "rt1": 127440, "rt2": 2877552},
        ]

    def test_metric_sum_by_rt_filter_platform(self, flexible_slicer_test_data, show_zero):
        """
        Primary dimension: metric
        Group by: report type
        DimensionFilter: platform
        """
        slicer = FlexibleDataSlicer(primary_dimension="metric")
        slicer.add_filter(
            ForeignKeyDimensionFilter("platform", [flexible_slicer_test_data["platforms"][0]]),
            add_group=False,
        )
        slicer.add_group_by("report_type")
        slicer.include_all_zero_rows = show_zero
        data = list(slicer.get_data())
        assert len(data) == Platform.objects.count()
        data = [remap_row_keys_to_short_names(row, Metric, [ReportType]) for row in data]
        data.sort(key=lambda rec: rec["pk"])
        # the following numbers were obtained by a separate calculation in a spreadsheet pivot table
        assert data == [
            {"pk": "m1", "rt1": 39906, "rt2": 1057752},
            {"pk": "m2", "rt1": 40878, "rt2": 1073304},
            {"pk": "m3", "rt1": 41850, "rt2": 1088856},
        ]

    @pytest.mark.parametrize(["order_by"], (("platform",), ("-platform",)))
    def test_platform_order_by_platform(self, flexible_slicer_test_data, order_by, show_zero):
        """
        Primary dimension: platform
        Group by: metric
        DimensionFilter: None
        Order by: platform (primary dimension)
        """
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        slicer.add_group_by("metric")
        slicer.order_by = [order_by]
        slicer.include_all_zero_rows = show_zero
        data = list(slicer.get_data())
        assert len(data) == Platform.objects.count()
        remapped = [remap_row_keys_to_short_names(row, Platform, [Metric]) for row in data]
        if order_by.startswith("-"):
            assert remapped[0]["pk"] == "pl3"
        else:
            assert remapped[0]["pk"] == "pl1"

    @pytest.fixture(params=["-", ""])
    def order_by_sign(self, request):
        return request.param

    @pytest.mark.parametrize(
        ["primary_dim"],
        [
            ("platform",),
            ("metric",),
            ("target",),
            ("organization",),
            ("report_type",),
            ("dim1",),
            ("dim2",),
            ("date",),
            ("date__year",),
        ],
    )
    def test_order_by_primary_dim(
        self, flexible_slicer_test_data, primary_dim, order_by_sign, show_zero
    ):
        """
        Test that ordering by primary dimension works for any primary dimension - the purpose
        of the test is to make sure it does not crash
        """
        slicer = FlexibleDataSlicer(primary_dimension=primary_dim)
        report_type = flexible_slicer_test_data["report_types"][1]
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", report_type))
        slicer.add_group_by("metric")
        slicer.include_all_zero_rows = show_zero
        slicer.order_by = [order_by_sign + primary_dim]
        data = list(slicer.get_data())
        assert len(data) > 0

    def test_report_type_pk_mapping_with_materialized_reports(self, flexible_slicer_test_data):
        """Test that pk mapping works correctly when report_type is primary dimension
        with materialized reports."""
        base_rt = flexible_slicer_test_data["report_types"][0]

        mat_spec = ReportMaterializationSpec.objects.create(
            base_report_type=base_rt, name="Test Mat", keep_target=False
        )
        mat_rt = ReportType.objects.create(
            short_name="MAT_TEST", materialization_spec=mat_spec, approx_record_count=100
        )

        slicer = FlexibleDataSlicer(primary_dimension="report_type", include_all_zero_rows=True)
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", [base_rt.pk]))
        slicer.add_group_by("metric")
        slicer._replace_report_type_with_materialized()

        if slicer._mat_reports_map:
            assert mat_rt.pk in slicer._mat_reports_map
            assert slicer._mat_reports_map[mat_rt.pk] == base_rt.pk

            data = list(slicer.get_data())
            for row in data:
                assert row["pk"] == base_rt.pk
                assert row["pk"] != mat_rt.pk

    @pytest.mark.parametrize(
        ["primary_dim", "order_by", "record_count"],
        [("target", "target__issn", 3), ("target", "target__isbn", 3)],
    )
    def test_order_by_related_field(
        self,
        flexible_slicer_test_data,
        primary_dim,
        order_by,
        record_count,
        order_by_sign,
        show_zero,
    ):
        """
        Test ordering by fields related to the primary dimension.
        We just want to test that it does not crash and returns the correct number of records
        """
        slicer = FlexibleDataSlicer(primary_dimension=primary_dim)
        report_type = flexible_slicer_test_data["report_types"][1]
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", report_type))
        slicer.add_group_by("metric")
        slicer.include_all_zero_rows = show_zero
        slicer.order_by = [order_by_sign + order_by]
        data = list(slicer.get_data())
        assert len(data) == record_count

    @pytest.mark.parametrize(["dim", "error"], [("dim1", False), ("dim2", True)])
    def test_group_by_explicit_dim_with_two_rts(self, flexible_slicer_test_data, dim, error):
        """
        Primary dimension: platform
        Group by: metric, dim
        DimensionFilter: None

        When more than one report type is used, grouping by explicit dimension is only possible
        if the dimension is the same for all report types and is stored in the same field.
        """
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        slicer.add_group_by(dim)

        if error:
            with pytest.raises(SlicerConfigError):
                slicer.get_data()
        else:
            slicer.get_data()

    @pytest.mark.parametrize(["dim", "error"], [("dim1", False), ("dim2", True)])
    def test_filter_by_explicit_dim_with_two_rts(self, flexible_slicer_test_data, dim, error):
        """
        Primary dimension: platform
        Group by: metric, dim
        DimensionFilter: dim1

        When more than one report type is used, filtering by explicit dimension is only possible
        if the dimension is the same for all report types and is stored in the same field.
        """
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        dim_idx = ["dim1", "dim2"].index(dim)
        texts = flexible_slicer_test_data["dimension_values"][dim_idx][:2]
        dim_ids = DimensionText.objects.filter(text__in=texts).values_list("pk", flat=True)
        slicer.add_filter(ExplicitDimensionFilter(dim, dim_ids))
        slicer.add_group_by("metric")

        if error:
            with pytest.raises(SlicerConfigError):
                slicer.get_data()
        else:
            slicer.get_data()

    def test_platform_sum_by_metric_filter_dim1_rt(self, flexible_slicer_test_data, show_zero):
        """
        Primary dimension: platform
        Group by: metric
        DimensionFilter: dim1, report_type
        """
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        texts = flexible_slicer_test_data["dimension_values"][0][:2]
        report_type = flexible_slicer_test_data["report_types"][0]
        dim1_ids = DimensionText.objects.filter(text__in=texts).values_list("pk", flat=True)
        slicer.add_filter(ExplicitDimensionFilter("dim1", dim1_ids), add_group=False)
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", report_type))
        slicer.add_group_by("metric")
        slicer.include_all_zero_rows = show_zero
        data = list(slicer.get_data())
        assert len(data) == Platform.objects.count()
        data = [remap_row_keys_to_short_names(row, Platform, [Metric]) for row in data]
        data.sort(key=lambda rec: rec["pk"])
        # the following numbers were obtained by a separate calculation in a spreadsheet pivot table
        assert data == [
            {"pk": "pl1", "m1": 26568, "m2": 27216, "m3": 27864},
            {"pk": "pl2", "m1": 34344, "m2": 34992, "m3": 35640},
            {"pk": "pl3", "m1": 42120, "m2": 42768, "m3": 43416},
        ]

    def test_platform_sum_by_metric_dim1_filter_dim1_rt(self, flexible_slicer_test_data, show_zero):
        """
        Primary dimension: platform
        Group by: metric, dim1
        DimensionFilter: dim1, report_type
        """
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        texts = flexible_slicer_test_data["dimension_values"][0][:2]
        report_type = flexible_slicer_test_data["report_types"][0]
        dim1_ids = DimensionText.objects.filter(text__in=texts).values_list("pk", flat=True)
        slicer.add_filter(ExplicitDimensionFilter("dim1", dim1_ids), add_group=True)
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", report_type))
        slicer.add_group_by("metric")
        slicer.include_all_zero_rows = show_zero
        data = list(slicer.get_data())
        assert len(data) == Platform.objects.count()
        data = [
            remap_row_keys_to_short_names(row, Platform, [DimensionText, Metric]) for row in data
        ]
        data.sort(key=lambda rec: rec["pk"])
        # the following numbers were obtained by a separate calculation in a spreadsheet pivot table
        assert data == [
            {
                "pk": "pl1",
                "A-m1": 13266,
                "A-m2": 13590,
                "A-m3": 13914,
                "B-m1": 13302,
                "B-m2": 13626,
                "B-m3": 13950,
            },
            {
                "pk": "pl2",
                "A-m1": 17154,
                "A-m2": 17478,
                "A-m3": 17802,
                "B-m1": 17190,
                "B-m2": 17514,
                "B-m3": 17838,
            },
            {
                "pk": "pl3",
                "A-m1": 21042,
                "A-m2": 21366,
                "A-m3": 21690,
                "B-m1": 21078,
                "B-m2": 21402,
                "B-m3": 21726,
            },
        ]

    def test_org_sum_by_platform_filter_platform_by_tag(
        self, flexible_slicer_test_data, show_zero, admin_user
    ):
        """
        Primary dimension: organization
        Group by: platform
        DimensionFilter: tag on platform
        """
        slicer = FlexibleDataSlicer(primary_dimension="organization")
        platforms = flexible_slicer_test_data["platforms"][1:]
        tag = TagFactory.create(name="my_platforms", tag_class__scope=TagScope.PLATFORM)
        for platform in platforms:
            tag.tag(platform, admin_user)
        slicer.add_filter(TagDimensionFilter("platform", tag), add_group=True)
        slicer.include_all_zero_rows = show_zero
        data = list(slicer.get_data())
        assert len(data) == Organization.objects.count()
        data = [remap_row_keys_to_short_names(row, Organization, [Platform]) for row in data]
        data.sort(key=lambda rec: rec["pk"])
        # the following numbers were obtained by a separate calculation in a spreadsheet pivot table
        assert data == [
            {"pk": "org1", "pl2": 717606, "pl3": 915894},
            {"pk": "org2", "pl2": 1312470, "pl3": 1510758},
            {"pk": "org3", "pl2": 1907334, "pl3": 2105622},
        ]

    def test_org_sum_by_platform_filter_platform_by_tag_class(
        self, flexible_slicer_test_data, show_zero, admin_user
    ):
        """
        Primary dimension: organization
        Group by: platform
        DimensionFilter: tag on platform
        """
        slicer = FlexibleDataSlicer(primary_dimension="organization")
        platforms = flexible_slicer_test_data["platforms"][1:]
        tc = TagClassFactory(scope=TagScope.PLATFORM)
        tags = TagFactory.create_batch(3, name="my_platforms", tag_class=tc)
        for tag, platform in zip(tags, platforms):
            tag.tag(platform, admin_user)
        slicer.add_filter(TagClassDimensionFilter("platform", tc), add_group=True)
        slicer.include_all_zero_rows = show_zero
        data = list(slicer.get_data())
        assert len(data) == Organization.objects.count()
        data = [remap_row_keys_to_short_names(row, Organization, [Platform]) for row in data]
        data.sort(key=lambda rec: rec["pk"])
        # the following numbers were obtained by a separate calculation in a spreadsheet pivot table
        assert data == [
            {"pk": "org1", "pl2": 717606, "pl3": 915894},
            {"pk": "org2", "pl2": 1312470, "pl3": 1510758},
            {"pk": "org3", "pl2": 1907334, "pl3": 2105622},
        ]

    def test_title_sum_by_platform_filter_metric_platform_title_by_tag(
        self, flexible_slicer_test_data, show_zero, admin_user
    ):
        """
        Primary dimension: title/target
        Group by: platform
        DimensionFilter: tag on title, platform, metric
        """
        slicer = FlexibleDataSlicer(primary_dimension="target")
        platforms = flexible_slicer_test_data["platforms"][:2]
        metric = flexible_slicer_test_data["metrics"][0]
        titles = [flexible_slicer_test_data["targets"][0], flexible_slicer_test_data["targets"][2]]
        tag = TagForTitleFactory.create(name="my_titles")
        for title in titles:
            tag.tag(title, admin_user)

        slicer.add_filter(ForeignKeyDimensionFilter("platform", platforms), add_group=True)
        slicer.add_filter(TagDimensionFilter("target", tag), add_group=False)
        slicer.add_filter(ForeignKeyDimensionFilter("metric", metric), add_group=False)
        slicer.include_all_zero_rows = show_zero
        data = list(slicer.get_data())
        assert len(data) == len(titles)
        data = [remap_row_keys_to_short_names(row, Title, [Platform]) for row in data]
        data.sort(key=lambda rec: rec["pk"])
        # the following numbers were obtained by a separate calculation in a spreadsheet pivot table
        assert data == [
            {"pk": "Title 1", "pl1": 364050, "pl2": 430146},
            {"pk": "Title 3", "pl1": 367722, "pl2": 433818},
        ]

    def test_title_sum_by_platform_filter_metric_platform_by_tag_title_by_tag(
        self, flexible_slicer_test_data, show_zero, admin_user
    ):
        """
        Primary dimension: title/target
        Group by: platform
        DimensionFilter: tag on title, tag on platform, metric
        """
        slicer = FlexibleDataSlicer(primary_dimension="target")
        metric = flexible_slicer_test_data["metrics"][0]
        platforms = flexible_slicer_test_data["platforms"][:2]
        pl_tag = TagFactory.create(name="my_platforms", tag_class__scope=TagScope.PLATFORM)
        for platform in platforms:
            pl_tag.tag(platform, admin_user)
        titles = [flexible_slicer_test_data["targets"][0], flexible_slicer_test_data["targets"][2]]
        title_tag = TagForTitleFactory.create(name="my_titles")
        for title in titles:
            title_tag.tag(title, admin_user)

        slicer.add_filter(TagDimensionFilter("platform", pl_tag), add_group=True)
        slicer.add_filter(TagDimensionFilter("target", title_tag), add_group=False)
        slicer.add_filter(ForeignKeyDimensionFilter("metric", metric), add_group=False)
        slicer.include_all_zero_rows = show_zero
        data = list(slicer.get_data())
        assert len(data) == len(titles)
        data = [remap_row_keys_to_short_names(row, Title, [Platform]) for row in data]
        data.sort(key=lambda rec: rec["pk"])
        # the following numbers were obtained by a separate calculation in a spreadsheet pivot table
        assert data == [
            {"pk": "Title 1", "pl1": 364050, "pl2": 430146},
            {"pk": "Title 3", "pl1": 367722, "pl2": 433818},
        ]

    def test_org_sum_by_metric_with_target_ordering(self, flexible_slicer_test_data):
        """
        Primary dimension: organization
        Group by: metric
        Sort by: target

        Note: sorting by target is invalid in this context, we are testing mitigation of the error
        """
        slicer = FlexibleDataSlicer(primary_dimension="organization")
        slicer.add_group_by("metric")
        slicer.include_all_zero_rows = False
        slicer.order_by = ["target"]
        data = list(slicer.get_data())
        assert len(data) == len(flexible_slicer_test_data["organizations"])

    @pytest.mark.parametrize("show_zero", [True, False])
    def test_group_by_title_tag(self, flexible_slicer_test_data_with_tags, show_zero):
        """
        Primary dimension: title/target
        Group by: metric
        Tag roll-up: True
        """
        slicer = FlexibleDataSlicer(
            primary_dimension="target", tag_roll_up=True, include_all_zero_rows=show_zero
        )
        slicer.add_filter(
            ForeignKeyDimensionFilter("metric", flexible_slicer_test_data_with_tags["metrics"][0]),
            add_group=True,
        )
        data = list(slicer.get_data())
        assert len(data) == (3 if show_zero else 2)
        data.sort(key=lambda rec: rec["pk"])
        exp_data = [
            {"pk": "tag1", "m1": 2586384},
            {"pk": "tag2", "m1": 1301454},
            {"pk": "tag3", "m1": 0},
        ]
        assert [remap_row_keys_to_short_names(row, Tag, [Metric]) for row in data] == (
            exp_data if show_zero else exp_data[:-1]
        )

    @pytest.mark.parametrize("show_zero", [True, False])
    def test_group_by_title_tag_with_tag_filter(
        self, flexible_slicer_test_data_with_tags, show_zero
    ):
        """
        Primary dimension: title/target
        Group by: metric
        Tag roll-up: True
        Tag filter: tag1, tag3
        """
        slicer = FlexibleDataSlicer(
            primary_dimension="target", tag_roll_up=True, include_all_zero_rows=show_zero
        )
        slicer.add_filter(
            ForeignKeyDimensionFilter("metric", flexible_slicer_test_data_with_tags["metrics"][0]),
            add_group=True,
        )
        slicer.tag_filter = Q(name__in=["tag1", "tag3"])
        data = list(slicer.get_data())
        assert len(data) == (2 if show_zero else 1)
        data.sort(key=lambda rec: rec["pk"])
        exp_data = [{"pk": "tag1", "m1": 2586384}, {"pk": "tag3", "m1": 0}]
        assert [remap_row_keys_to_short_names(row, Tag, [Metric]) for row in data] == (
            exp_data if show_zero else exp_data[:-1]
        )

    @pytest.mark.parametrize(
        ["included_tags", "expected"],
        [
            ([], 3887838),
            (["tag1"], 1301454),
            (["tag2"], 2586384),
            (["tag3"], 3887838),
            (["tag1", "tag2"], 0),
            (["tag1", "tag3"], 1301454),
            (["tag2", "tag3"], 2586384),
            (["tag1", "tag2", "tag3"], 0),
        ],
    )
    def test_tag_remainder(self, flexible_slicer_test_data_with_tags, included_tags, expected):
        """
        Tests the computation of the remaining usage for stuff without any tag

        Primary dimension: title/target
        Group by: metric
        Tag roll-up: True
        """
        slicer = FlexibleDataSlicer(
            primary_dimension="target", tag_roll_up=True, include_all_zero_rows=False
        )
        slicer.add_filter(
            ForeignKeyDimensionFilter("metric", flexible_slicer_test_data_with_tags["metrics"][0]),
            add_group=True,
        )
        slicer.tag_filter = Q(name__in=included_tags)
        remainder = slicer.get_remainder()
        data = remap_row_keys_to_short_names(remainder, Tag, [Metric])
        assert data == {"m1": expected}

    @pytest.mark.parametrize(
        ["included_tags", "expected"],
        [
            ([], 701082),
            (["tag1"], 235530),
            (["tag2"], 465552),
            (["tag3"], 701082),
            (["tag1", "tag2"], 0),
        ],
    )
    def test_tag_remainder_with_parts(
        self, flexible_slicer_test_data_with_tags, included_tags, expected
    ):
        """
        Tests the computation of the remaining usage for stuff without any tag

        Primary dimension: title/target
        Group by: metric
        Split by: organization
        Tag roll-up: True
        """
        slicer = FlexibleDataSlicer(
            primary_dimension="target", tag_roll_up=True, include_all_zero_rows=False
        )
        slicer.add_filter(
            ForeignKeyDimensionFilter("metric", flexible_slicer_test_data_with_tags["metrics"][0]),
            add_group=True,
        )
        slicer.tag_filter = Q(name__in=included_tags)
        slicer.add_split_by("organization")
        remainder = slicer.get_remainder(
            part=[flexible_slicer_test_data_with_tags["organizations"][0]]
        )
        data = remap_row_keys_to_short_names(remainder, Tag, [Metric])
        assert data == {"m1": expected}

    def test_trend_mode_month_over_month(self, flexible_slicer_test_data, show_zero):
        """
        Tests that the year-over-year calculation works correctly

        Primary dimension: platform
        DimensionFilter: metric, report_type
        """
        slicer = FlexibleDataSlicer(
            primary_dimension="platform",
            trend_mode=True,
            base_subset_filters=[DateDimensionFilter("date", "2019-12-01", "2019-12-31")],
            compared_subset_filters=[DateDimensionFilter("date", "2020-01-01", "2020-03-31")],
            include_all_zero_rows=show_zero,
        )
        slicer.add_filter(
            ForeignKeyDimensionFilter("metric", flexible_slicer_test_data["metrics"][0])
        )
        slicer.add_filter(
            ForeignKeyDimensionFilter("report_type", flexible_slicer_test_data["report_types"][0])
        )
        slicer.order_by = ["platform__pk"]
        data = list(slicer.get_data())

        assert [
            {"base": 8883, "compared": 31023, "diff": 22140, "reldiff": 22140 / 8883},
            {"base": 11799, "compared": 39771, "diff": 27972, "reldiff": 27972 / 11799},
            {"base": 14715, "compared": 48519, "diff": 33804, "reldiff": 33804 / 14715},
        ] == [
            {
                "base": rec["base"],
                "compared": rec["compared"],
                "diff": rec["diff"],
                "reldiff": rec["reldiff"],
            }
            for rec in data
        ]

    @pytest.mark.parametrize("order_by", ("diff", "reldiff", "base", "compared"))
    @pytest.mark.parametrize("desc", (True, False), ids=("desc", "asc"))
    def test_trend_mode_order_by(self, flexible_slicer_test_data, order_by, desc):
        slicer = FlexibleDataSlicer(
            primary_dimension="platform",
            trend_mode=True,
            base_subset_filters=[DateDimensionFilter("date", "2019-12-01", "2019-12-31")],
            compared_subset_filters=[DateDimensionFilter("date", "2020-01-01", "2020-03-31")],
        )
        slicer.add_filter(
            ForeignKeyDimensionFilter("metric", flexible_slicer_test_data["metrics"][0])
        )
        slicer.add_filter(
            ForeignKeyDimensionFilter("report_type", flexible_slicer_test_data["report_types"][0])
        )
        slicer.order_by = [("-" if desc else "") + order_by]
        data = list(slicer.get_data())
        assert len(data) == 3
        if desc:
            assert data[0][order_by] > data[1][order_by] > data[2][order_by]
        else:
            assert data[0][order_by] < data[1][order_by] < data[2][order_by]

    def test_group_by_item(self, flexible_slicer_test_data_with_items):
        """
        Primary dimension: item
        Group by: metric
        """
        slicer = FlexibleDataSlicer(primary_dimension="item")
        slicer.add_filter(
            ForeignKeyDimensionFilter("metric", flexible_slicer_test_data_with_items["metrics"][0]),
            add_group=True,
        )
        slicer.order_by = ["item__pk"]
        data = list(slicer.get_data())
        assert len(data) == 3
        items = flexible_slicer_test_data_with_items["items"]
        # the data was obtained using libreoffice calc on the test data
        exp_data = [
            {"pk": items[0].name, "m1": 26688},
            {"pk": items[1].name, "m1": 26784},
            {"pk": items[2].name, "m1": 27456},
        ]
        assert [remap_row_keys_to_short_names(rec, Item, [Metric]) for rec in data] == exp_data

    def test_group_by_item_with_title_filter(self, flexible_slicer_test_data_with_items):
        """
        Primary dimension: item
        Group by: metric
        Filter: title
        """
        slicer = FlexibleDataSlicer(primary_dimension="item")
        slicer.add_filter(
            ForeignKeyDimensionFilter("target", flexible_slicer_test_data_with_items["targets"][0])
        )
        slicer.add_group_by("metric")
        slicer.order_by = ["item__pk"]
        data = list(slicer.get_data())
        assert len(data) == 2
        exp_data = [
            {"pk": flexible_slicer_test_data_with_items["items"][0].name, "m1": 26688, "m2": 28128},
            {"pk": flexible_slicer_test_data_with_items["items"][1].name, "m1": 26784, "m2": 28224},
        ]
        assert [remap_row_keys_to_short_names(rec, Item, [Metric]) for rec in data] == exp_data

    def test_group_by_item_with_title_filter_by_tag(
        self, flexible_slicer_test_data_with_items, admin_user
    ):
        """
        Primary dimension: item
        Group by: metric
        Filter: title
        """
        tag = TagFactory.create(name="my_tag", tag_class__scope=TagScope.TITLE)
        title = flexible_slicer_test_data_with_items["targets"][0]
        tag.tag(title, admin_user)
        slicer = FlexibleDataSlicer(primary_dimension="item")
        slicer.add_filter(TagDimensionFilter("target", [tag.pk]))
        slicer.add_group_by("metric")
        slicer.order_by = ["item__pk"]
        data = list(slicer.get_data())
        assert len(data) == 2
        exp_data = [
            {"pk": flexible_slicer_test_data_with_items["items"][0].name, "m1": 26688, "m2": 28128},
            {"pk": flexible_slicer_test_data_with_items["items"][1].name, "m1": 26784, "m2": 28224},
        ]
        assert [remap_row_keys_to_short_names(rec, Item, [Metric]) for rec in data] == exp_data


@pytest.mark.clickhouse
@pytest.mark.usefixtures("clickhouse_on_off")
@pytest.mark.django_db(transaction=True)
class TestFlexibleDataSlicerPossibleDimensionValues:
    def test_get_possible_dimension_values_unfiltered(self, flexible_slicer_test_data):
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        metric_data = slicer.get_possible_dimension_values("metric")
        assert metric_data["count"] == Metric.objects.count()

    def test_get_possible_dimension_values_with_direct_filter(self, flexible_slicer_test_data):
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        metrics = flexible_slicer_test_data["metrics"][1:]
        slicer.add_filter(ForeignKeyDimensionFilter("metric", metrics))
        metric_data = slicer.get_possible_dimension_values("metric")
        assert metric_data["count"] == len(metrics)

    @pytest.mark.parametrize(["dim", "count"], [("dim1", 3), ("dim2", 1)])
    def test_get_possible_dimension_values_with_materialized_report(
        self, flexible_slicer_test_data, dim, count
    ):
        """
        Test that materialized report type which does not keep the dimension for which we want
        to get possible values is not used in the computation of possible values.
        """
        rt = flexible_slicer_test_data["report_types"][0]
        ReportType.objects.create(
            short_name="materialized",
            materialization_spec=ReportMaterializationSpec.objects.create(
                base_report_type=rt, keep_dim1=False, keep_dim2=False
            ),
        )
        recompute_materialized_reports()
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        metrics = flexible_slicer_test_data["metrics"][1:]
        slicer.add_filter(ForeignKeyDimensionFilter("metric", metrics))
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", rt))
        metric_data = slicer.get_possible_dimension_values(dim)
        assert slicer._mat_reports_map == {}, "no materialized report should be used"
        assert metric_data["count"] == count

    @pytest.mark.parametrize("ignore_self", [True, False])
    @pytest.mark.parametrize("primary_dimension", ["platform", "target", "organization"])
    def test_get_possible_dimension_values_with_direct_tag_filter(
        self, flexible_slicer_test_data, admin_user, ignore_self, primary_dimension
    ):
        """
        When filtering by tag, we also want to filter the tagged dimension itself,
        even if `ignore_self` is given.
        It must also work the same regardless of the primary dimension.
        """
        tag = TagFactory.create(name="my_tag", tag_class__scope=TagScope.PLATFORM)
        for pl in flexible_slicer_test_data["platforms"][:2]:
            tag.tag(pl, admin_user)
        slicer = FlexibleDataSlicer(primary_dimension=primary_dimension)
        slicer.add_filter(TagDimensionFilter("platform", [tag.pk]))
        platform_data = slicer.get_possible_dimension_values("platform", ignore_self=ignore_self)
        assert platform_data["count"] == 2

    @pytest.mark.parametrize("tagged_count", [0, 2])
    @pytest.mark.parametrize("primary_dimension", ["platform", "target", "organization"])
    @pytest.mark.parametrize("tagged_dimension", ["platform", "target", "organization"])
    def test_get_possible_dimension_values_with_direct_empty_tag_filter(
        self,
        flexible_slicer_test_data,
        admin_user,
        tagged_count,
        primary_dimension,
        tagged_dimension,
    ):
        """
        Check that when filtering by tag and the tag has nothing associated with it,
        the result is empty. Check that extra organization filter does not affect the result.
        """
        tag = TagFactory.create(
            name="my_tag",
            tag_class__scope={
                "platform": TagScope.PLATFORM,
                "target": TagScope.TITLE,
                "organization": TagScope.ORGANIZATION,
            }[tagged_dimension],
        )
        for pl in flexible_slicer_test_data[f"{tagged_dimension}s"][:tagged_count]:
            tag.tag(pl, admin_user)
        slicer = FlexibleDataSlicer(primary_dimension=primary_dimension)
        slicer.add_filter(TagDimensionFilter(tagged_dimension, [tag.pk]))
        slicer.organization_filter = Organization.objects.all()
        platform_data = slicer.get_possible_dimension_values(tagged_dimension, ignore_self=True)
        assert platform_data["count"] == tagged_count

    def test_get_possible_dimension_values_with_indirect_filter(
        self, flexible_slicer_test_data, clickhouse_on_off
    ):
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        metrics = flexible_slicer_test_data["metrics"][1:]
        organization = flexible_slicer_test_data["organizations"][0]
        slicer.add_filter(ForeignKeyDimensionFilter("metric", metrics))
        # let's try for the complete data
        organization_data = slicer.get_possible_dimension_values("organization")
        assert organization_data["count"] == Organization.objects.count(), (
            "the data is complete so all organizations should be present"
        )
        # let's delete all records related to one organization and the filtered metrics
        AccessLog.objects.filter(metric__in=metrics, organization=organization).delete(
            i_know_what_i_am_doing=True
        )
        if clickhouse_on_off:
            # we need to sync clickhouse because we did not use the standard way of deleting data
            ch_backend.delete_records(AccessLogCube.query().filter(organization_id=organization.pk))
        organization_data = slicer.get_possible_dimension_values("organization")
        assert organization_data["count"] == Organization.objects.count() - 1, (
            "one organization should not be present in the data anymore"
        )

    def test_get_possible_dimension_values_with_text_filter_implicit_dim(
        self, flexible_slicer_test_data
    ):
        """
        Tests that substring filtering works for `FlexibleDataSlicer.get_possible_dimension_values`
        for implicit dimensions
        """
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        metric_data = slicer.get_possible_dimension_values("metric", text_filter="2")
        assert metric_data["count"] == 1
        assert metric_data["values"][0]["metric"] == Metric.objects.get(name__icontains="2").pk

    def test_get_possible_dimension_values_with_text_filter_explicit_dim(
        self, flexible_slicer_test_data
    ):
        """
        Tests that substring filtering works for `FlexibleDataSlicer.get_possible_dimension_values`
        for explicit dimensions
        """
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        report_type = flexible_slicer_test_data["report_types"][1]
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", report_type.pk))
        metric_data = slicer.get_possible_dimension_values("dim1", text_filter="C")
        assert metric_data["count"] == 1
        assert metric_data["values"][0]["dim1"] == DimensionText.objects.get(text="C").pk

    def test_get_possible_dimension_values_with_list_of_pks(self, flexible_slicer_test_data):
        """
        Tests that a list of pk's for the queried dimension may be used by the slicer to limit
        output of `get_possible_dimension_values`
        """
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        metrics = flexible_slicer_test_data["metrics"][1:]
        metric_data = slicer.get_possible_dimension_values("metric", pks=[m.pk for m in metrics])
        assert metric_data["count"] == 2
        assert {rec["metric"] for rec in metric_data["values"]} == {m.pk for m in metrics}

    def test_get_possible_dimension_values_with_list_of_pks_explicit_dim(
        self, flexible_slicer_test_data
    ):
        """
        Tests that a list of pk's for the queried dimension may be used by the slicer to limit
        output of `get_possible_dimension_values`
        """
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        report_type = flexible_slicer_test_data["report_types"][1]
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", report_type.pk))
        dts = DimensionText.objects.filter(text__in=["A", "B"], dimension__short_name="dim1name")
        metric_data = slicer.get_possible_dimension_values("dim1", pks=[dt.pk for dt in dts])
        assert metric_data["count"] == 2
        assert {rec["dim1"] for rec in metric_data["values"]} == {dt.pk for dt in dts}

    @pytest.mark.parametrize(
        ["search_text", "result_count"], [("2000", 1), ("200", 5), ("19", 1), ("18", 0)]
    )
    def test_get_possible_dimension_values_query_with_list_of_explicit_dim_int_values(
        self, flexible_slicer_test_data2, search_text, result_count
    ):
        """
        Tests that a list of integer values the queried dimension may be used by the slicer to limit
        output of `get_possible_dimension_values`
        """
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        report_type = flexible_slicer_test_data2["report_types"][1]
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", report_type.pk))
        metric_data = slicer.get_possible_dimension_values("dim2", text_filter=search_text)
        assert metric_data["count"] == result_count


@pytest.mark.django_db
class TestFlexibleDataSlicerOther:
    def test_create_from_config(self):
        """
        Test that slicer created from config has the same params as the original slicer
        :return:
        """
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        slicer.add_filter(ForeignKeyDimensionFilter("metric", [1, 2, 3]))
        slicer.add_filter(DateDimensionFilter("date", "2020-01-01", "2020-03-31"))
        slicer.add_filter(ExplicitDimensionFilter("dim1", [10, 11]))
        slicer.add_group_by("organization")
        config = slicer.config()
        new_slicer = FlexibleDataSlicer.create_from_config(config)
        assert new_slicer.primary_dimension == slicer.primary_dimension
        assert new_slicer.group_by == slicer.group_by
        assert new_slicer.order_by == slicer.order_by
        assert len(new_slicer.dimension_filters) == len(slicer.dimension_filters)
        for new_fltr, old_fltr in zip(new_slicer.dimension_filters, slicer.dimension_filters):
            assert new_fltr.config() == old_fltr.config()

    def test_computation_from_config(self, flexible_slicer_test_data):
        """
        Test that slicer created from config gives the same result as the original slicer
        :return:
        """
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        texts = flexible_slicer_test_data["dimension_values"][0][:2]
        report_type = flexible_slicer_test_data["report_types"][0]
        dim1_ids = DimensionText.objects.filter(text__in=texts).values_list("pk", flat=True)
        slicer.add_filter(ExplicitDimensionFilter("dim1", dim1_ids), add_group=True)
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", report_type))
        slicer.add_group_by("metric")
        data = list(slicer.get_data())
        new_slicer = FlexibleDataSlicer.create_from_config(slicer.config())
        assert data == list(new_slicer.get_data())

    @pytest.mark.parametrize(["show_zero", "row_count"], [(True, 4), (False, 3)])
    def test_include_zero_usage(self, flexible_slicer_test_data, show_zero, row_count):
        """
        Test that slicer correctly reacts to `include_all_zero_rows`
        :return:
        """
        Title.objects.create(name="Zero usage")  # add one unused title
        assert Title.objects.count() == 4
        slicer = FlexibleDataSlicer(primary_dimension="target")
        slicer.add_group_by("metric")
        slicer.include_all_zero_rows = show_zero
        data = list(slicer.get_data())
        assert len(data) == row_count

    @pytest.mark.parametrize(
        [
            "organization_idx",
            "platform_idx",
            "report_type_idx",
            "start_month",
            "end_month",
            "exp_ib_count",
            "exp_ib_max",
        ],
        [
            (None, None, 0, "2019-12-01", "2020-03-31", 35, 36),
            (None, None, 1, "2019-12-01", "2020-03-31", 36, 36),
            (0, 0, 0, "2019-12-01", "2020-03-31", 3, 4),
            (0, 0, 0, "2019-12-01", "2020-01-31", 1, 2),
            (0, 0, 1, "2019-12-01", "2020-03-31", 4, 4),
            (0, 0, 0, None, None, 3, 4),
            (None, None, 0, None, None, 35, 36),
            (None, None, 1, None, None, 36, 36),
            (0, 1, 0, "2019-12-01", "2020-03-31", 4, 4),
        ],
    )
    def test_report_coverage(
        self,
        flexible_slicer_test_data,
        organization_idx,
        platform_idx,
        report_type_idx,
        start_month,
        end_month,
        exp_ib_count,
        exp_ib_max,
    ):
        """
        Test the `get_coverage` method of the slicer in different scenarios.
        """
        # we need to remove some data to create some holes
        assert ImportBatch.objects.count() == 72
        orgs = flexible_slicer_test_data["organizations"]
        platforms = flexible_slicer_test_data["platforms"]
        rts = flexible_slicer_test_data["report_types"]
        ImportBatch.objects.filter(
            organization=orgs[0], platform=platforms[0], report_type=rts[0], date="2020-01-01"
        ).delete()
        # create the slicer
        rt = rts[report_type_idx]
        pl = platforms[platform_idx] if platform_idx is not None else None
        org = orgs[organization_idx] if organization_idx is not None else None
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        slicer.add_group_by("metric")
        slicer.add_filter(DateDimensionFilter("date", start_month, end_month))
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", rt))
        if pl:
            slicer.add_filter(ForeignKeyDimensionFilter("platform", pl))
        if org:
            slicer.add_filter(ForeignKeyDimensionFilter("organization", org))
        coverage = slicer.get_coverage()["overall"]
        assert coverage["ib_count"] == exp_ib_count
        assert coverage["ib_max"] == exp_ib_max

    def test_report_coverage_with_multiple_report_types(self, flexible_slicer_test_data):
        # delete 3 import batches
        ImportBatch.objects.filter(
            organization=flexible_slicer_test_data["organizations"][0],
            report_type=flexible_slicer_test_data["report_types"][0],
            date="2020-01-01",
        ).delete()
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        slicer.add_group_by("metric")
        slicer.add_filter(
            ForeignKeyDimensionFilter("report_type", flexible_slicer_test_data["report_types"])
        )
        coverage = slicer.get_coverage()["overall"]
        assert coverage["ib_count"] == 69
        assert coverage["ib_max"] == 72

    @pytest.mark.parametrize(
        ("org_idx", "exp_ib_count", "exp_ib_max"),
        [(None, 14, 16), (0, 14, 16), (1, 14, 16), (2, 22, 24)],
    )
    def test_report_coverage_with_tag_based_filter(
        self, flexible_slicer_test_data, admin_user, org_idx, exp_ib_count, exp_ib_max
    ):
        """
        Test that the coverage computation can deal with tag-based filters instead of FK-based
        filters. And also that it works together with FK-based filters.

        The filters should be "ored" together.
        """
        # delete 3 import batches
        ImportBatch.objects.filter(
            organization=flexible_slicer_test_data["organizations"][0],
            report_type=flexible_slicer_test_data["report_types"][0],
            date="2020-01-01",
        ).delete()
        # add tags to platforms and organizations
        platforms = flexible_slicer_test_data["platforms"]
        tag1 = TagFactory(tag_class__scope=TagScope.PLATFORM, tag_class__name="cls1", name="tag1")
        tag1.tag(platforms[0], admin_user)
        tag1.tag(platforms[1], admin_user)
        orgs = flexible_slicer_test_data["organizations"]
        tag2 = TagFactory(
            tag_class__scope=TagScope.ORGANIZATION, tag_class__name="cls2", name="tag2"
        )
        tag3 = TagFactory(
            tag_class__scope=TagScope.ORGANIZATION, tag_class__name="cls2", name="tag3"
        )
        tag2.tag(orgs[0], admin_user)
        tag2.tag(orgs[1], admin_user)
        tag3.tag(orgs[1], admin_user)  # double tag org[1] to make sure it does not mess things up
        # create the slicer
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        slicer.add_group_by("metric")
        slicer.add_filter(
            ForeignKeyDimensionFilter("report_type", flexible_slicer_test_data["report_types"][0])
        )
        slicer.add_filter(TagDimensionFilter("platform", tag1))
        slicer.add_filter(TagDimensionFilter("organization", [tag2, tag3]))
        if org_idx:
            slicer.add_filter(ForeignKeyDimensionFilter("organization", orgs[org_idx].pk))
        coverage = slicer.get_coverage()["overall"]
        assert coverage["ib_count"] == exp_ib_count
        assert coverage["ib_max"] == exp_ib_max

    def test_report_coverage_in_trend_mode(self, flexible_slicer_test_data):
        # delete 3 import batches
        rt1 = flexible_slicer_test_data["report_types"][0]
        ImportBatch.objects.filter(
            organization=flexible_slicer_test_data["organizations"][0],
            report_type=rt1,
            date="2020-01-01",
        ).delete()
        slicer = FlexibleDataSlicer(
            primary_dimension="platform",
            trend_mode=True,
            base_subset_filters=[DateDimensionFilter("date", "2020-01", "2020-01")],
            compared_subset_filters=[DateDimensionFilter("date", "2020-02", "2020-02")],
        )
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", rt1))
        coverage = slicer.get_coverage()
        assert "base" in coverage
        assert "compared" in coverage
        assert coverage["base"]["ib_count"] == 6
        assert coverage["base"]["ib_max"] == 9
        assert coverage["compared"]["ib_count"] == 9
        assert coverage["compared"]["ib_max"] == 9

    def test_report_coverage_in_trend_mode_with_global_date_filter(self, flexible_slicer_test_data):
        """
        Test that when date filter is applied globally, it is ignored in the trend mode
        and does not cause an error
        """
        rt1 = flexible_slicer_test_data["report_types"][0]
        slicer = FlexibleDataSlicer(
            primary_dimension="platform",
            trend_mode=True,
            base_subset_filters=[DateDimensionFilter("date", "2020-01", "2020-01")],
            compared_subset_filters=[DateDimensionFilter("date", "2020-02", "2020-02")],
        )
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", rt1))
        slicer.add_filter(DateDimensionFilter("date", "2018-01", "2018-02"))
        coverage = slicer.get_coverage()
        # test that there is complete coverage, if global date filter was not ignored
        # the coverage data would be just zeros
        assert coverage["base"]["ib_count"] == 9
        assert coverage["base"]["ib_max"] == 9
        assert coverage["compared"]["ib_count"] == 9
        assert coverage["compared"]["ib_max"] == 9

    def test_report_coverage_with_empty_involved_report_types(self, flexible_slicer_test_data):
        """
        Test that get_coverage handles the case when involved_report_types returns an empty list
        without raising KeyError or ZeroDivisionError
        """
        # Create a slicer
        slicer = FlexibleDataSlicer(primary_dimension="platform")

        # Mock the involved_report_types method to return an empty list
        from unittest.mock import patch

        with patch.object(slicer, "involved_report_types", return_value=[]):
            # This should not raise any exceptions (KeyError or ZeroDivisionError)
            coverage = slicer.get_coverage()

            # Verify the structure is correct
            assert "overall" in coverage
            assert coverage["overall"].get("ib_count") is None
            assert coverage["overall"].get("ib_max") is None
            assert coverage["overall"]["ratio"] is None

    def test_resolve_explicit_dimension_with_multiple_report_types(self, flexible_slicer_test_data):
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        slicer.add_filter(
            ForeignKeyDimensionFilter("report_type", flexible_slicer_test_data["report_types"])
        )
        assert slicer.resolve_explicit_dimension("dim1").short_name == "dim1name"
        with pytest.raises(SlicerConfigError) as exc_info:
            # this should raise an error because "dim2" is not present in both report types
            slicer.resolve_explicit_dimension("dim2")
            assert exc_info.value.code == SlicerConfigErrorCode.E113


@pytest.mark.django_db
class TestFlexibleDataSimpleCSVExporter:
    @pytest.mark.parametrize("include_row_totals", [True, False])
    def test_export_empty_data(self, flexible_slicer_test_data, include_row_totals):
        """
        Primary dimension: organization
        Group by: platform
        DimensionFilter:
        """
        slicer = FlexibleDataSlicer(primary_dimension="organization")
        slicer.add_group_by("platform")
        # filter by new unused metric
        m = MetricFactory()
        slicer.add_filter(ForeignKeyDimensionFilter("metric", [m]))
        exporter = FlexibleDataSimpleCSVExporter(
            slicer, include_tags=False, include_row_totals=include_row_totals
        )
        out = StringIO()
        exporter.stream_data_to_sink(out)
        assert out.getvalue() == ""

    @pytest.mark.parametrize("include_row_totals", [True, False])
    def test_org_sum_by_platform(self, flexible_slicer_test_data, include_row_totals):
        """
        Primary dimension: organization
        Group by: platform
        DimensionFilter:
        """
        slicer = FlexibleDataSlicer(primary_dimension="organization")
        slicer.add_group_by("platform")
        exporter = FlexibleDataSimpleCSVExporter(
            slicer, include_tags=False, include_row_totals=include_row_totals
        )
        out = StringIO()
        exporter.stream_data_to_sink(out)
        output = out.getvalue()
        assert len(output.splitlines()) == Organization.objects.count() + 1
        if include_row_totals:
            assert output.splitlines() == [
                "Organization,Row total,Platform 1,Platform 2,Platform 3",
                "Organization 1,2152818,519318,717606,915894",
                "Organization 2,3937410,1114182,1312470,1510758",
                "Organization 3,5722002,1709046,1907334,2105622",
            ]
        else:
            assert output.splitlines() == [
                "Organization,Platform 1,Platform 2,Platform 3",
                "Organization 1,519318,717606,915894",
                "Organization 2,1114182,1312470,1510758",
                "Organization 3,1709046,1907334,2105622",
            ]

    @pytest.mark.parametrize("include_tags", [True, False])
    def test_org_sum_by_platform_with_tags(self, flexible_slicer_test_data, include_tags, users):
        """
        Primary dimension: organization
        Group by: platform
        DimensionFilter:
        """
        admin_user = users["admin1"]
        tc = TagClassFactory(scope=TagScope.ORGANIZATION, name="foo")
        tag1 = TagFactory(tag_class=tc, name="bar")
        tag2 = TagFactory(tag_class=tc, name="baz")
        tag3 = TagFactory(
            tag_class=tc, name="invisible", owner=users["admin2"], can_see=AccessibleBy.OWNER
        )  # invisible to admin_user
        tag1.tag(flexible_slicer_test_data["organizations"][0], admin_user)
        tag2.tag(flexible_slicer_test_data["organizations"][0], admin_user)
        tag2.tag(flexible_slicer_test_data["organizations"][1], admin_user)
        tag3.tag(flexible_slicer_test_data["organizations"][1], admin_user)

        slicer = FlexibleDataSlicer(primary_dimension="organization")
        slicer.add_group_by("platform")
        slicer.order_by = ["organization"]
        exporter = FlexibleDataSimpleCSVExporter(
            slicer, include_tags=include_tags, report_owner=admin_user
        )
        out = StringIO()
        exporter.stream_data_to_sink(out)
        output = out.getvalue()
        assert len(output.splitlines()) == Organization.objects.count() + 1
        if include_tags:
            assert output.splitlines() == [
                "Organization,Tags,Platform 1,Platform 2,Platform 3",
                "Organization 1,foo / bar | foo / baz,519318,717606,915894",
                "Organization 2,foo / baz,1114182,1312470,1510758",
                "Organization 3,,1709046,1907334,2105622",
            ]
        else:
            assert output.splitlines() == [
                "Organization,Platform 1,Platform 2,Platform 3",
                "Organization 1,519318,717606,915894",
                "Organization 2,1114182,1312470,1510758",
                "Organization 3,1709046,1907334,2105622",
            ]

    def test_platform_sum_by_metric_dim1_filter_dim1_rt(self, flexible_slicer_test_data):
        """
        Primary dimension: platform
        Group by: metric, dim1
        DimensionFilter: dim1, report_type
        """
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        texts = flexible_slicer_test_data["dimension_values"][0][:2]
        report_type = flexible_slicer_test_data["report_types"][0]
        dim1_ids = DimensionText.objects.filter(text__in=texts).values_list("pk", flat=True)
        slicer.add_filter(ExplicitDimensionFilter("dim1", dim1_ids), add_group=True)
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", report_type))
        slicer.add_group_by("metric")
        slicer.order_by = ["platform"]
        exporter = FlexibleDataSimpleCSVExporter(slicer)
        out = StringIO()
        exporter.stream_data_to_sink(out)
        output = out.getvalue()
        assert output.splitlines() == [
            "Platform,A / Metric 1,A / Metric 2,A / Metric 3,B / Metric 1,B / Metric 2,B / "
            "Metric 3",
            "Platform 1,13266,13590,13914,13302,13626,13950",
            "Platform 2,17154,17478,17802,17190,17514,17838",
            "Platform 3,21042,21366,21690,21078,21402,21726",
        ]

    def test_platform_sum_by_date_filter_rt(self, flexible_slicer_test_data):
        """
        Primary dimension: platform
        Group by: date
        DimensionFilter: report_type
        """
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        report_type = flexible_slicer_test_data["report_types"][0]
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", report_type))
        slicer.add_group_by("date")
        slicer.order_by = ["platform"]
        exporter = FlexibleDataSimpleCSVExporter(slicer)
        out = StringIO()
        exporter.stream_data_to_sink(out)
        output = out.getvalue()
        assert output.splitlines() == [
            "Platform,2019-12-01,2020-01-01,2020-02-01,2020-03-01",
            "Platform 1,27378,29565,31752,33939",
            "Platform 2,36126,38313,40500,42687",
            "Platform 3,44874,47061,49248,51435",
        ]

    @pytest.mark.parametrize("include_tags", [True, False])
    def test_platform_sum_by_date_filter_rt_with_tags(
        self, flexible_slicer_test_data, include_tags, admin_user
    ):
        """
        Primary dimension: platform
        Group by: date
        DimensionFilter: report_type
        """
        tc = TagClassFactory(scope=TagScope.PLATFORM, name="foo")
        tag1 = TagFactory(tag_class=tc, name="bar")
        tag2 = TagFactory(tag_class=tc, name="baz")
        tag1.tag(flexible_slicer_test_data["platforms"][0], admin_user)
        tag2.tag(flexible_slicer_test_data["platforms"][0], admin_user)
        tag2.tag(flexible_slicer_test_data["platforms"][1], admin_user)

        slicer = FlexibleDataSlicer(primary_dimension="platform")
        report_type = flexible_slicer_test_data["report_types"][0]
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", report_type))
        slicer.add_group_by("date")
        exporter = FlexibleDataSimpleCSVExporter(
            slicer, include_tags=include_tags, report_owner=admin_user
        )
        out = StringIO()
        exporter.stream_data_to_sink(out)
        output = out.getvalue()
        if include_tags:
            assert sorted(output.splitlines()) == sorted(
                [
                    "Platform,Tags,2019-12-01,2020-01-01,2020-02-01,2020-03-01",
                    "Platform 1,foo / bar | foo / baz,27378,29565,31752,33939",
                    "Platform 2,foo / baz,36126,38313,40500,42687",
                    "Platform 3,,44874,47061,49248,51435",
                ]
            )
        else:
            assert sorted(output.splitlines()) == sorted(
                [
                    "Platform,2019-12-01,2020-01-01,2020-02-01,2020-03-01",
                    "Platform 1,27378,29565,31752,33939",
                    "Platform 2,36126,38313,40500,42687",
                    "Platform 3,44874,47061,49248,51435",
                ]
            )

    def test_platform_sum_by_date__year_filter_rt(self, flexible_slicer_test_data):
        """
        Primary dimension: platform
        Group by: date__year
        DimensionFilter: report_type
        """
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        report_type = flexible_slicer_test_data["report_types"][0]
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", report_type))
        slicer.add_group_by("date__year")
        exporter = FlexibleDataSimpleCSVExporter(slicer)
        out = StringIO()
        exporter.stream_data_to_sink(out)
        output = out.getvalue()
        assert output.splitlines() == [
            "Platform,2019,2020",
            "Platform 1,27378,95256",
            "Platform 2,36126,121500",
            "Platform 3,44874,147744",
        ]

    def test_platform_sum_by_date__year_filter_rt_with_monitor(self, flexible_slicer_test_data):
        """
        Primary dimension: platform
        Group by: date__year
        DimensionFilter: report_type

        uses monitor function
        """
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        report_type = flexible_slicer_test_data["report_types"][0]
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", report_type))
        slicer.add_group_by("date__year")
        exporter = FlexibleDataSimpleCSVExporter(slicer)
        out = StringIO()
        monitor = MagicMock()
        exporter.stream_data_to_sink(out, progress_monitor=monitor)
        assert monitor.call_count == 2  # once at start, once at the end
        monitor.assert_called_with(3, 3)

    def test_platform_sum_by_date__year_filter_date(self, flexible_slicer_test_data):
        """
        Primary dimension: platform
        Group by: date__year
        DimensionFilter: date
        """
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        report_type = flexible_slicer_test_data["report_types"][0]
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", report_type))
        slicer.add_filter(DateDimensionFilter("date", "2020-01-01", "2020-03-31"))
        slicer.add_group_by("date__year")
        exporter = FlexibleDataSimpleCSVExporter(slicer)
        out = StringIO()
        exporter.stream_data_to_sink(out)
        output = out.getvalue()
        assert len(output.splitlines()) == 4
        assert len(output.splitlines()[0].split(",")) == 2, "only two columns"
        assert output.splitlines()[0].split(",")[1] == "2020", 'second column is "2020"'

    def test_year_by_metric(self, flexible_slicer_test_data):
        """
        Primary dimension: date__year
        Group by: metric
        DimensionFilter: report_type
        """
        slicer = FlexibleDataSlicer(primary_dimension="date__year")
        report_type = flexible_slicer_test_data["report_types"][0]
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", report_type))
        slicer.add_group_by("metric")
        slicer.order_by = ["date__year"]
        exporter = FlexibleDataSimpleCSVExporter(slicer)
        out = StringIO()
        exporter.stream_data_to_sink(out)
        output = out.getvalue()
        assert len(output.splitlines()) == 3
        assert len(output.splitlines()[0].split(",")) == 4, "three metrics and primary dim"
        assert output.splitlines()[1].split(",")[0] == "2019", "first row starts with year 2019"

    def test_explicit_dim_by_metric(self, flexible_slicer_test_data):
        """
        Primary dimension: dim1
        Group by: metric
        DimensionFilter: report_type
        """
        slicer = FlexibleDataSlicer(primary_dimension="dim1")
        report_type = flexible_slicer_test_data["report_types"][0]
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", report_type))
        slicer.add_group_by("metric")
        slicer.order_by = ["dim1"]
        exporter = FlexibleDataSimpleCSVExporter(slicer)
        out = StringIO()
        exporter.stream_data_to_sink(out)
        output = out.getvalue()
        assert len(output.splitlines()) == 4, "3 dim values + header"
        assert len(output.splitlines()[0].split(",")) == 4, "three metrics and primary dim"
        assert output.splitlines()[1].split(",")[0] == "A", 'first row starts with "A"'

    def test_org_sum_by_platform_with_org_extra_filter(self, flexible_slicer_test_data):
        """
        Primary dimension: organization
        Group by: platform
        DimensionFilter:
        Extra filter: organization (simulates user with limited org access)
        """
        slicer = FlexibleDataSlicer(primary_dimension="organization")
        slicer.add_group_by("platform")
        slicer.add_extra_organization_filter([flexible_slicer_test_data["organizations"][1].pk])
        exporter = FlexibleDataSimpleCSVExporter(slicer)
        out = StringIO()
        exporter.stream_data_to_sink(out)
        output = out.getvalue()
        assert output.splitlines() == [
            "Organization,Platform 1,Platform 2,Platform 3",
            "Organization 2,1114182,1312470,1510758",
        ]

    def test_split_by_org_get_parts(self, flexible_slicer_test_data):
        """
        Split dimension: organization
        Primary dimension: platform
        Group by: metric
        DimensionFilter:
        """
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        slicer.add_split_by("organization")
        slicer.add_group_by("metric")
        parts = slicer.get_parts_queryset()
        assert {p["organization"] for p in parts} == {
            org.pk for org in flexible_slicer_test_data["organizations"]
        }

    def test_split_by_org_get_parts_with_split_filter(self, flexible_slicer_test_data):
        """
        Split dimension: organization
        Primary dimension: platform
        Group by: metric
        DimensionFilter: organization (thus limiting the number of parts after split)
        """
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        slicer.add_split_by("organization")
        slicer.add_group_by("metric")
        organizations = flexible_slicer_test_data["organizations"][:2]
        slicer.add_filter(ForeignKeyDimensionFilter("organization", organizations))
        parts = slicer.get_parts_queryset()
        assert {p["organization"] for p in parts} == {org.pk for org in organizations}

    def test_split_by_org_get_data_missing_part_arg(self, flexible_slicer_test_data):
        """
        Split dimension: organization
        Primary dimension: platform
        Group by: metric
        DimensionFilter:
        """
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        slicer.add_split_by("organization")
        slicer.add_group_by("metric")
        with pytest.raises(SlicerConfigError):
            slicer.get_data()

    def test_split_by_org_get_data(self, flexible_slicer_test_data):
        """
        Split dimension: organization
        Primary dimension: platform
        Group by: metric
        DimensionFilter:
        """
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        slicer.add_split_by("organization")
        slicer.add_group_by("metric")
        org = flexible_slicer_test_data["organizations"][0]
        data = slicer.get_data(part=[org.pk])
        expected = {"Platform 1": 519318, "Platform 2": 717606, "Platform 3": 915894}
        found = {Platform.objects.get(pk=rec["pk"]).name: rec["_total"] for rec in data}
        assert found == expected

    def test_split_by_date_get_data(self, flexible_slicer_test_data):
        """
        Split dimension: date
        Primary dimension: platform
        Group by: metric
        DimensionFilter:
        """
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        slicer.add_split_by("date")
        slicer.add_group_by("metric")
        data = slicer.get_data(part=["2020-01"])
        expected = {"Platform 1": 817047, "Platform 2": 965763, "Platform 3": 1114479}
        found = {Platform.objects.get(pk=rec["pk"]).name: rec["_total"] for rec in data}
        assert found == expected

    def test_streaming_of_multipart_data(self, flexible_slicer_test_data):
        """
        Split dimension: organization
        Primary dimension: platform
        Group by: metric
        DimensionFilter:
        """
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        slicer.add_split_by("organization")
        slicer.add_group_by("metric")
        exporter = FlexibleDataZipCSVExporter(slicer)
        out = BytesIO()
        exporter.stream_data_to_sink(out)
        out.seek(0)
        with ZipFile(out, "r") as zipfile:
            assert len(zipfile.namelist()) == len(flexible_slicer_test_data["organizations"]) + 1
            assert set(zipfile.namelist()) == {
                "_metadata.csv",
                "organization-1.csv",
                "organization-2.csv",
                "organization-3.csv",
            }

    def test_metadata_multipart(self, flexible_slicer_test_data):
        """
        Split dimension: organization
        Primary dimension: platform
        Group by: metric
        DimensionFilter:
        """
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        report_type = flexible_slicer_test_data["report_types"][0]
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", report_type))
        slicer.add_split_by("organization")
        slicer.add_group_by("metric")

        exporter = FlexibleDataZipCSVExporter(slicer)
        out = BytesIO()
        exporter.stream_data_to_sink(out)
        out.seek(0)
        with ZipFile(out, "r") as zipfile:
            with zipfile.open("_metadata.csv", "r") as metafile:
                decoder = codecs.getreader("utf-8")(metafile)
                reader = csv.reader(decoder)
                data = list(reader)
                assert data[5] == ["Data coverage", "100.0%"]
                assert data[6] == ["Split by", "Organization"]
                assert data[7] == ["Rows", "Platform"]
                assert data[8] == ["Columns", "Metric"]
                assert data[9] == ["Applied filters", f"Report type: {report_type.name}"]

    def test_metadata_unfiltered_orgs(self, flexible_slicer_test_data):
        """
        Test that when organization is not part of split_by, group_by or a filter, that a list
        of organizations will be added to the metadata to make it obvious to the user what
        he got.
        Split dimension: organization
        Primary dimension: platform
        Group by: metric
        DimensionFilter:
        """
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        report_type = flexible_slicer_test_data["report_types"][0]
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", report_type))
        slicer.add_group_by("metric")

        exporter = FlexibleDataZipCSVExporter(slicer)
        out = BytesIO()
        exporter.stream_data_to_sink(out)
        out.seek(0)
        with ZipFile(out, "r") as zipfile:
            with zipfile.open("_metadata.csv", "r") as metafile:
                decoder = codecs.getreader("utf-8")(metafile)
                reader = csv.reader(decoder)
                data = list(reader)
                assert data[5] == ["Data coverage", "100.0%"]
                assert data[6] == ["Split by", "-"]
                assert data[7] == ["Rows", "Platform"]
                assert data[8] == ["Columns", "Metric"]
                assert data[9] == ["Applied filters", f"Report type: {report_type.name}"]
                assert data[11] == [
                    "Included organizations",
                    "(No organization filter was applied, the data represent the following "
                    "organizations)",
                ]
                org_names = {row[1] for row in data[12 : len(data)]}  # noqa: E203
                assert org_names == {org.name for org in Organization.objects.all()}

    def test_metadata_trend_mode(self, flexible_slicer_test_data):
        """
        Primary dimension: platform
        Group by: trend-mode
        """
        slicer = FlexibleDataSlicer(
            primary_dimension="platform",
            trend_mode=True,
            base_subset_filters=[DateDimensionFilter("date", start="2020-01-01", end="2020-01-31")],
            compared_subset_filters=[
                DateDimensionFilter("date", start="2020-02-01", end="2020-02-29")
            ],
        )
        report_type = flexible_slicer_test_data["report_types"][0]
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", report_type))

        exporter = FlexibleDataZipCSVExporter(slicer)
        out = BytesIO()
        exporter.stream_data_to_sink(out)
        out.seek(0)
        with ZipFile(out, "r") as zipfile:
            with zipfile.open("_metadata.csv", "r") as metafile:
                decoder = codecs.getreader("utf-8")(metafile)
                reader = csv.reader(decoder)
                data = list(reader)
                assert data[5] == [
                    "Data coverage",
                    "Base period: 100.0%",
                    "Compared period: 100.0%",
                ]
                assert data[6] == ["Split by", "-"]
                assert data[7] == ["Rows", "Platform"]
                assert data[8] == ["Columns", "Trend analysis: 2020-01 vs 2020-02"]
                assert data[9] == ["Applied filters", f"Report type: {report_type.name}"]


@pytest.mark.django_db
class TestFilters:
    def test_foreign_key_filter(self, flexible_slicer_test_data):
        report_type = flexible_slicer_test_data["report_types"][0]
        fltr = ForeignKeyDimensionFilter("report_type", report_type)
        assert str(fltr) == f"report_type: {report_type.name}"

    @pytest.mark.parametrize(
        ["start", "end", "expected"],
        [
            ("2020-10-01", "2021-03", "2020-10-01 - 2021-03-31"),
            ("2020-10-01", "2020-10-01", "2020-10-01 - 2020-10-01"),
            ("2020-10", "2020-10", "2020-10-01 - 2020-10-31"),
            ("2020-01-01", "2020-01-01", "2020-01-01 - 2020-01-01"),
            ("2020-01-01", "2020-12-31", "2020-01-01 - 2020-12-31"),
            ("2020-01", "2020-12", "2020-01-01 - 2020-12-31"),
            ("2020-01-01", "2020-12-01", "2020-01-01 - 2020-12-01"),
            ("2020-01-01", "2021-12-31", "2020-01-01 - 2021-12-31"),
        ],
    )
    def test_date_filter(self, start, end, expected):
        fltr = DateDimensionFilter("date", start, end)
        assert str(fltr) == f"date: {expected}"

    @pytest.mark.parametrize(
        ["start", "end", "expected"],
        [
            ("2020-10-01", "2021-03", "2020-10 - 2021-03"),
            ("2020-10-01", "2020-10-01", "2020-10"),
            ("2020-10", "2020-10", "2020-10"),
            ("2020-01-01", "2020-01-01", "2020-01"),
            ("2020-01-01", "2020-12-31", "2020"),
            ("2020-01", "2020-12", "2020"),
            ("2020-01-01", "2020-12-01", "2020-01 - 2020-12"),
            ("2020-01-01", "2021-12-31", "2020 - 2021"),
            ("2020-01", "2021-12", "2020 - 2021"),
        ],
    )
    def test_date_filter_smart_str(self, start, end, expected):
        fltr = DateDimensionFilter("date", start, end)
        assert fltr.smart_str() == expected

    def test_explicit_dim_filter(self, flexible_slicer_test_data):
        texts = flexible_slicer_test_data["dimension_values"][0][1:]
        dim1_ids = DimensionText.objects.filter(text__in=texts).values_list("pk", flat=True)
        fltr = ExplicitDimensionFilter("dim1", dim1_ids)
        value = "; ".join(texts)
        assert str(fltr) == f"dim1: {value}"


@pytest.mark.django_db
class TestFiltersInSlicerContext:
    """
    Explicit dim filter can be properly resolved only in the context of a slicer, so we add the
    same tests as in `TestFilters` here with a slicer at hand.

    Slicer also decodes the name of the dimension to `verbose_name`
    """

    def _slicer_filter_to_str(self, fltr) -> str:
        slicer = FlexibleDataSlicer(primary_dimension="metric")
        slicer.add_filter(fltr)
        return slicer.filter_to_str(fltr)

    def test_foreign_key_filter(self, flexible_slicer_test_data):
        report_type = flexible_slicer_test_data["report_types"][0]
        fltr = ForeignKeyDimensionFilter("report_type", report_type)
        assert self._slicer_filter_to_str(fltr) == f"Report type: {report_type.name}"

    def test_date_filter(self):
        fltr = DateDimensionFilter("date", "2020-10-01", "2021-03")
        assert self._slicer_filter_to_str(fltr) == "Date: 2020-10-01 - 2021-03-31"

    def test_explicit_dim_filter(self, flexible_slicer_test_data):
        texts = flexible_slicer_test_data["dimension_values"][0][1:]
        dim1_ids = DimensionText.objects.filter(text__in=texts).values_list("pk", flat=True)
        # for explicit dimension resolution, we need to have a report type specified
        report_type = flexible_slicer_test_data["report_types"][0]
        slicer = FlexibleDataSlicer(primary_dimension="metric")
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", report_type))
        fltr = ExplicitDimensionFilter("dim1", dim1_ids)
        value = "; ".join(texts)
        assert slicer.filter_to_str(fltr) == f"dim1name: {value}"


@pytest.mark.django_db
class TestFlexibleDataExcelExporter:
    """
    Tests for exporting data to excel format
    """

    @pytest.mark.parametrize(
        ["name_in", "name_out"],
        [
            ("Sheet", "Sheet"),
            (
                "Very long name of the sheet that does not fit into 32",
                "Very long name of the sheet th…",
            ),
            ("Forbidden & ?: characters \\/ etc.", "Forbidden & characters etc."),
            ("More forbidden'", "More forbidden"),
            ("History", "History_"),
            ("history'", "history_"),
            ("'", "Sheet"),
            ("Long that fits after []??? removal", "Long that fits after removal"),
            ("Long that does not fit after []??? removal", "Long that does not fit after r…"),
        ],
    )
    def test_xslx_cleanup_sheetname(self, name_in, name_out):
        assert FlexibleDataExcelExporter.cleanup_sheetname(name_in) == name_out

    @pytest.mark.parametrize("include_charts", [True, False])
    def test_include_charts(self, flexible_slicer_test_data, include_charts):
        """
        Test that the `include_charts` parameter works as expected
        """
        slicer = FlexibleDataSlicer(primary_dimension="organization")
        slicer.add_group_by("platform")
        exporter = FlexibleDataExcelExporter(
            slicer, include_tags=False, include_charts=include_charts
        )
        out = BytesIO()
        exporter.stream_data_to_sink(out)
        out.seek(0)
        workbook = openpyxl.load_workbook(out)
        if include_charts:
            assert workbook.sheetnames == ["metadata", "report", "Chart - report"]
        else:
            assert workbook.sheetnames == ["metadata", "report"]
