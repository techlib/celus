import copy
import typing
from pathlib import Path
from unittest.mock import patch

import pytest
from celus_nigiri import CounterRecord
from celus_nigiri.counter4 import Counter4BR2Report
from celus_nigiri.counter5 import Counter5TRReport
from django.core.management import call_command
from django.db.models import Count, Sum
from django.urls import reverse
from hcube.api.models.aggregation import Sum as HSum
from nibbler.logic.processing import counter_format_poops, get_records_from_nibbler_output
from organizations.tests.conftest import organization_random, organizations  # noqa - fixture
from publications.fake_data import PlatformFactory
from publications.logic.title_management import find_mergeable_titles, merge_titles
from publications.models import Item, PlatformInterestReport, PlatformTitle, Title
from publications.tests.conftest import interest_rt  # noqa - fixture

from logs.fake_data import ManualDataUploadFullFactory, MetricFactory, ReportTypeFactory
from logs.models import (
    AccessLog,
    DimensionText,
    ImportBatch,
    InterestGroup,
    ReportInterestMetric,
    ReportMaterializationSpec,
    ReportType,
)

from ..cubes import AccessLogCube, ch_backend
from ..exceptions import DataAlreadyPresent
from ..logic.data_import import import_counter_records


def get_records(path: Path, platform: str) -> typing.Generator[CounterRecord, None, None]:
    return list(get_records_from_nibbler_output(counter_format_poops(path, platform)))


@pytest.mark.django_db
class TestDataImport:
    """
    Tests functionality of the logic.data_import module
    """

    def test_import_counter_records_simple_data_0d(
        self, counter_records_0d, organizations, report_type_nd, platform
    ):
        assert AccessLog.objects.count() == 0
        assert Title.objects.count() == 0
        report_type = report_type_nd(0)
        import_counter_records(report_type, organizations[0], platform, counter_records_0d)
        assert AccessLog.objects.count() == 1
        assert ImportBatch.objects.count() == 1
        assert Title.objects.count() == 1
        al = AccessLog.objects.get()
        assert al.value == 50
        assert al.dim1 is None
        assert PlatformTitle.objects.count() == 1

    def test_temporary_item_title_conversion(self, organizations, report_type_nd, platform):
        assert AccessLog.objects.count() == 0
        assert Title.objects.count() == 0
        rt_ir_m1 = report_type_nd(0, short_name="IR_M1")
        rt_ir = report_type_nd(0, short_name="IR")
        cr1 = CounterRecord(
            start="2020-01-01",
            end="2020-01-31",
            metric="Total_Item_Requests",
            value=1,
            item="ItemX",
            item_ids={"Print_ISSN": "00010001"},
            title="TitleX",
            title_ids={"Print_ISSN": "00010000"},
        )
        cr2 = copy.deepcopy(cr1)  # CounterRecords are altered during processing
        import_counter_records(rt_ir_m1, organizations[0], platform, [cr1])
        assert AccessLog.objects.count() == 1
        assert ImportBatch.objects.count() == 1
        assert Title.objects.count() == 1
        assert Title.objects.first().name == "ItemX"
        assert Title.objects.first().issn == "0001-0001"
        assert Item.objects.count() == 0, "No item is created for IR_M1"
        al = AccessLog.objects.get()
        assert al.value == 1
        assert al.dim1 is None
        assert PlatformTitle.objects.count() == 1

        import_counter_records(rt_ir, organizations[0], platform, [cr2])
        assert AccessLog.objects.count() == 2
        assert ImportBatch.objects.count() == 2
        assert Title.objects.count() == 2
        assert Title.objects.order_by("pk")[1].name == "TitleX"
        assert Title.objects.order_by("pk")[1].issn == "0001-0000"
        assert Item.objects.count() == 1, "Item is created for IR"
        assert Item.objects.first().name == "ItemX"
        assert Item.objects.first().issn == "0001-0001"
        al = AccessLog.objects.order_by("pk").last()
        assert al.value == 1
        assert al.dim1 is None
        assert PlatformTitle.objects.count() == 2

    def test_import_counter_records_simple_data_0d_more_passes(
        self, counter_records_nd, organizations, report_type_nd, platform
    ):
        """
        Tests that when the import has to go over the imported data in several passes
        (batches, not import batches), it still functions properly
        """
        assert AccessLog.objects.count() == 0
        record_number = 10
        crs = counter_records_nd(1, record_number=record_number)
        report_type = report_type_nd(1)
        import_counter_records(report_type, organizations[0], platform, crs, buffer_size=1)
        assert AccessLog.objects.count() == record_number

    def test_simple_data_import_1d(
        self, counter_records_nd, organizations, report_type_nd, platform
    ):
        assert AccessLog.objects.count() == 0
        assert Title.objects.count() == 0
        crs = list(counter_records_nd(1))
        report_type = report_type_nd(1)
        import_counter_records(report_type, organizations[0], platform, crs)
        assert AccessLog.objects.count() == 1
        assert Title.objects.count() == 1
        al = AccessLog.objects.get()
        assert al.value == crs[0].value
        # check that the remap of the value is the same as the original text value
        assert DimensionText.objects.get(pk=al.dim1).text == crs[0].dimension_data["dim0"]
        assert al.dim2 is None

    def test_data_import_mutli_3d(
        self, counter_records_nd, organizations, report_type_nd, platform
    ):
        assert AccessLog.objects.count() == 0
        assert Title.objects.count() == 0
        crs = list(counter_records_nd(3, record_number=10))
        report_type = report_type_nd(3)
        _ibs, stats = import_counter_records(report_type, organizations[0], platform, crs)
        assert stats["skipped logs"] == 0
        assert stats["new logs"] == 10
        assert AccessLog.objects.count() == 10
        assert Title.objects.count() > 0
        al = AccessLog.objects.order_by("pk")[0]
        assert al.value == crs[0].value
        # check that the remap of the value is the same as the original text value
        assert DimensionText.objects.get(pk=al.dim1).text == crs[0].dimension_data["dim0"]
        assert DimensionText.objects.get(pk=al.dim2).text == crs[0].dimension_data["dim1"]
        assert DimensionText.objects.get(pk=al.dim3).text == crs[0].dimension_data["dim2"]
        assert al.dim4 is None

    @pytest.mark.parametrize(
        ["months", "log_count", "log_sum"],
        [
            (None, 6, 63),
            (["2018-01-01"], 3, 7),
            (["2018-01-01", "2018-03-01"], 4, 39),
            (["2018-01-01", "2018-02-01"], 5, 31),
            (["2018-01-01", "2018-02-01", "2018-03-01"], 6, 63),
            (["2018-02-01", "2018-03-01"], 3, 56),
            (["2018-02-01"], 2, 24),
        ],
    )
    def test_data_import_month_skipping(
        self, counter_records, organizations, report_type_nd, platform, months, log_count, log_sum
    ):
        assert AccessLog.objects.count() == 0
        assert Title.objects.count() == 0
        data = [
            [None, "2018-01-01", "1v1", "2v1", "3v1", 1],
            [None, "2018-01-01", "1v2", "2v1", "3v1", 2],
            [None, "2018-01-01", "1v2", "2v2", "3v1", 4],
            [None, "2018-02-01", "1v1", "2v1", "3v1", 8],
            [None, "2018-02-01", "1v1", "2v2", "3v2", 16],
            [None, "2018-03-01", "1v1", "2v3", "3v2", 32],
        ]
        crs = counter_records(data, metric="Hits", platform=platform.name)
        organization = organizations[0]
        report_type = report_type_nd(3)
        import_counter_records(report_type, organization, platform, crs, months=months)
        assert AccessLog.objects.count() == log_count
        assert AccessLog.objects.aggregate(sum=Sum("value"))["sum"] == log_sum

    def test_data_import_mutli_3d_repeating_data(
        self, counter_records_nd, organizations, report_type_nd, platform
    ):
        """
        Tests that when the same values occur in the import data, they are remapped correctly to
        the save database value.
        """
        assert AccessLog.objects.count() == 0
        assert Title.objects.count() == 0
        crs = list(
            counter_records_nd(3, record_number=10, title="Title ABC", dim_value="one value")
        )
        rt: ReportType = report_type_nd(3)
        import_counter_records(rt, organizations[0], platform, crs)
        assert AccessLog.objects.count() == 10
        assert Title.objects.count() > 0
        al1, al2 = AccessLog.objects.order_by("pk")[:2]
        assert al1.value == crs[0].value
        # check that only one remap is created for each dimension
        assert DimensionText.objects.filter(text="one value").count() == 3
        dt1 = DimensionText.objects.get(text="one value", dimension=rt.dimensions_sorted[0])
        # check that values with the same dimension use the same remap
        assert al1.dim1 == dt1.pk
        assert al2.dim1 == dt1.pk
        dt2 = DimensionText.objects.get(text="one value", dimension=rt.dimensions_sorted[1])
        assert al1.dim2 == dt2.pk
        assert al2.dim2 == dt2.pk
        assert al1.dim3 is not None
        assert al1.dim4 is None

    def test_reimport(self, counter_records_nd, organizations, report_type_nd, platform):
        """
        Test that reimporting the same data will lead to an exception
        """
        crs = list(counter_records_nd(3, record_number=1, title="Title ABC", dim_value="one value"))
        rt: ReportType = report_type_nd(3)
        _ibs, stats = import_counter_records(rt, organizations[0], platform, crs)
        assert AccessLog.objects.count() == 1
        assert Title.objects.count() == 1
        assert stats["new logs"] == 1
        assert stats["new platformtitles"] == 1
        with pytest.raises(DataAlreadyPresent):
            import_counter_records(rt, organizations[0], platform, crs)

    @pytest.mark.parametrize(["buffer_size"], [(10,), (3,), (2,), (1,)])
    def test_duplicated_data_in_one_import(
        self, counter_records_nd, organizations, report_type_nd, platform, buffer_size
    ):
        """
        Test that when there are several records with the same dimensions in the records,
        they are properly merged together.
        It should work regardless of buffer_size - which means even if the clashing records
        are in different batches
        """
        cr = list(counter_records_nd(3, record_number=1, title="Title ABC", dim_value="one"))[0]
        crs = [cr, cr, cr]
        rt: ReportType = report_type_nd(3)
        _ibs, stats = import_counter_records(
            rt, organizations[0], platform, crs, buffer_size=buffer_size
        )
        assert AccessLog.objects.count() == 1
        assert AccessLog.objects.get().value == 3 * cr.value
        assert Title.objects.count() == 1
        assert stats["new logs"] == 1
        assert stats["new platformtitles"] == 1

    @pytest.mark.clickhouse
    @pytest.mark.django_db(transaction=True)
    def test_interest_and_materialization_are_done_during_import(
        self, counter_records, organizations, report_type_nd, clickhouse_on_off, interest_rt
    ):
        """
        Test that when records are imported, interest and materialization are done
        directly with the import
        """
        platform = PlatformFactory.create()
        report_type = report_type_nd(1)
        organization = organizations[0]
        # now define the interest
        PlatformInterestReport.objects.create(platform=platform, report_type=report_type)
        ReportInterestMetric.objects.create(
            report_type=report_type,
            metric=MetricFactory.create(short_name="Hits"),
            interest_group=InterestGroup.objects.create(short_name="ig1", position=1),
        )
        # and materialized view
        rt_no_title_spec = ReportMaterializationSpec.objects.create(
            base_report_type=report_type, keep_target=False
        )
        rt_no_title = ReportType.objects.create(
            materialization_spec=rt_no_title_spec, short_name="no_title", name="no_title"
        )
        # and materialized interest to cover all possible cases
        int_no_title_spec = ReportMaterializationSpec.objects.create(
            base_report_type=interest_rt, keep_target=False
        )
        int_no_title = ReportType.objects.create(
            materialization_spec=int_no_title_spec, short_name="int_no_title", name="int_no_title"
        )
        assert rt_no_title.approx_record_count == 0
        # import the data
        data1 = [
            ["Title1", "2018-01-01", "1v1", 1],
            ["Title2", "2018-01-01", "1v2", 2],
            ["Title3", "2018-01-01", "1v2", 4],
        ]
        crs1 = counter_records(data1, metric="Hits", platform="Platform1")
        ibs, _stats = import_counter_records(report_type, organization, platform, crs1)
        assert len(ibs) == 1, "only one import batch created"
        assert (
            AccessLog.objects.count() == 3 + 3 + 2 + 1
        ), "3 normal, 3 interest, 2 materialized, 1 materialized interest"
        assert report_type.accesslog_set.aggregate(sum=Sum("value"))["sum"] == 7
        assert interest_rt.accesslog_set.count() == 3, "3 interest logs created"
        assert interest_rt.accesslog_set.aggregate(sum=Sum("value"))["sum"] == 7
        assert rt_no_title.accesslog_set.count() == 2, "2 materialized logs created (1 per dim1)"
        assert rt_no_title.accesslog_set.aggregate(sum=Sum("value"))["sum"] == 7
        assert int_no_title.accesslog_set.count() == 1, "1 materialized interest log created"
        assert int_no_title.accesslog_set.aggregate(sum=Sum("value"))["sum"] == 7
        rt_no_title.refresh_from_db()
        assert rt_no_title.approx_record_count == 2, "approx count was updated"
        if clickhouse_on_off:
            # clickhouse it turned on, so we should have the same results in clickhouse
            for i, rt in enumerate([report_type, interest_rt]):
                assert (
                    ch_backend.get_one_record(
                        AccessLogCube.query().filter(report_type_id=rt.pk).aggregate(HSum("value"))
                    ).sum
                    == 7
                ), f"rt {i} should have sum of hits == 7"
            for i, rt in enumerate([rt_no_title, int_no_title]):
                assert (
                    ch_backend.get_one_record(
                        AccessLogCube.query().filter(report_type_id=rt.pk).aggregate(HSum("value"))
                    ).sum
                    == 0
                ), f"mrt {i} should have sum of hits == 0 as it is materialized"


@pytest.mark.django_db
class TestCounter4Import:
    def test_import_br2_tsv(self, organizations, report_type_nd, platform):
        rt = report_type_nd(1, dimension_names=["Publisher"])

        path = Path(__file__).parent / "data/counter4/counter4_br2.tsv"
        records = get_records(path, platform)

        assert len(records) == 60  # 12 months, 5 titles
        organization = organizations[0]
        assert AccessLog.objects.count() == 0
        _ibs, stats = import_counter_records(rt, organization, platform, (e for e in records))
        assert AccessLog.objects.count() == 60
        assert stats["new logs"] == 60
        values = [
            al["value"]
            for al in AccessLog.objects.filter(
                target__name="Columbia Electronic Encyclopedia, 6th Edition"
            )
            .order_by("date")
            .values()
        ]
        assert len(values) == 12
        assert values == [1, 10, 2, 3, 5, 0, 0, 0, 0, 0, 0, 0]

    def test_c4_import_title_types_ids_and_platform(self, organizations, report_type_nd, platform):
        expected = [
            (
                "Auditing Your Human Resources Department: A Step-by-Step Guide to Assessing the "
                "Key Areas of Your Program",
                ["453619"],
                "9780814416617",
            ),
            ("Columbia Electronic Encyclopedia, 6th Edition", ["576175"], "9780787650155"),
            ("International Business Times", [], ""),
            ("World Congress on Engineering 2007 (Volume 1)", ["422959"], "9789889867157"),
            ("World Congress on Engineering 2009 (Volume 1)", ["657512"], "9789881701251"),
        ]

        rt = report_type_nd(
            len(Counter4BR2Report.dimensions), dimension_names=Counter4BR2Report.dimensions
        )
        path = Path(__file__).parent / "data/counter4/counter4_br2.tsv"
        records = get_records(path, platform)

        assert len(records) == 60  # 12 months, 5 titles
        organization = organizations[0]
        assert Title.objects.count() == 0
        import_counter_records(rt, organization, platform, (e for e in records))
        assert Title.objects.count() == 5
        # test title publication type
        assert list(
            Title.objects.order_by("pub_type").values("pub_type").annotate(count=Count("id"))
        ) == [
            {"pub_type": Title.PUB_TYPE_BOOK, "count": 4},
            {"pub_type": Title.PUB_TYPE_UNKNOWN, "count": 1},
        ]
        # test other title properties
        for title in Title.objects.all():
            for exp_title, exp_ids, exp_isbn in expected:
                if exp_title == title.name:
                    assert title.proprietary_ids == exp_ids
                    assert title.isbn == exp_isbn
                    break
            else:
                assert False, "expected title was not found"
        # test that the Platform dimension was properly handled
        pl_attr = rt.dim_name_to_dim_attr("Platform")
        pl_dim = rt.dimension_by_attr_name(pl_attr)
        ebsco_text = DimensionText.objects.filter(dimension=pl_dim, text="EBSCOhost")
        assert ebsco_text.exists(), "corresponding DimensionText should have been created"
        ebsco_text = ebsco_text.get()
        for al in AccessLog.objects.all():
            assert getattr(al, pl_attr) == ebsco_text.pk


@pytest.mark.django_db
class TestCounter5Import:
    @pytest.mark.parametrize(
        ["filename", "expected_titles", "expected_items"],
        [
            (
                "counter5_table_dr.csv",
                [
                    (
                        "ARTICLES",
                        {
                            "proprietary_ids": ["Test123"],
                            "uris": [],
                            "isbn": "",
                            "issn": "",
                            "eissn": "",
                            "doi": "",
                        },
                    ),
                    (
                        "BOOKS",
                        {
                            "proprietary_ids": ["Test456"],
                            "uris": [],
                            "isbn": "",
                            "issn": "",
                            "eissn": "",
                            "doi": "",
                        },
                    ),
                ],
                [],
            ),
            (
                "COUNTER_R5_Report_Examples_TR.csv",
                [
                    (
                        "Journal Six",
                        {
                            "proprietary_ids": ["xyz123"],
                            "uris": ["https://foo.bar.baz/"],
                            "isbn": "",
                            "issn": "",
                            "eissn": "9876-5432",
                            "doi": "10.1000/ xyz123",
                        },
                    )
                ],
                [],
            ),
            (
                "counter5_ir_sample.tsv",
                [
                    (
                        "Journal 45",
                        {
                            "proprietary_ids": ["SampleIR:45"],
                            "uris": [],
                            "isbn": "",
                            "issn": "2859-4118",
                            "eissn": "2859-4231",
                            "doi": "10.1729/jhik",
                        },
                    ),
                    (
                        "Book 1092",
                        {
                            "proprietary_ids": ["SampleIR:b1092"],
                            "uris": [],
                            "isbn": "9783164584012",
                            "issn": "",
                            "eissn": "",
                            "doi": "10.1729/zbcd.1243",
                        },
                    ),
                ],
                [
                    (
                        "Item 100026",
                        {
                            "proprietary_ids": ["SampleIR:100026"],
                            "uris": [],
                            "isbn": "",
                            "issn": "",
                            "eissn": "",
                            "doi": "10.1729/jhik.345",
                        },
                    ),
                    (
                        "Item 100027",
                        {
                            "proprietary_ids": ["SampleIR:100027"],
                            "uris": [],
                            "isbn": "9783164484107",
                            "issn": "",
                            "eissn": "",
                            "doi": "10.1729/zbcd.457",
                        },
                    ),
                    (
                        "Item 100029",
                        {
                            "proprietary_ids": ["SampleIR:100029"],
                            "uris": [],
                            "isbn": "",
                            "issn": "",
                            "eissn": "",
                            "doi": "",
                        },
                    ),
                    (
                        "Item 100030",
                        {
                            "proprietary_ids": ["SampleIR:100030"],
                            "uris": [],
                            "isbn": "",
                            "issn": "",
                            "eissn": "",
                            "doi": "10.1729/abcd.434",
                        },
                    ),
                ],
            ),
        ],
    )
    def test_c5_import_title_types_and_ids(
        self,
        organization_random,
        report_type_nd,
        platform,
        filename,
        expected_titles,
        expected_items,
    ):
        # we do not care much about the dimensions - just about titles
        rt = report_type_nd(0)

        path = Path(__file__).parent / "data/counter5" / filename
        records = get_records(path, platform)
        assert Title.objects.count() == 0
        import_counter_records(rt, organization_random, platform, records)
        assert Title.objects.count() == len(expected_titles)
        assert Item.objects.count() == len(expected_items)
        for title in Title.objects.all():
            for exp_title, ids in expected_titles:
                if exp_title == title.name:
                    for id in ["proprietary_ids", "uris", "isbn", "issn", "eissn", "doi"]:
                        assert getattr(title, id) == ids[id], f"title {id} mismatch"
                    break
            else:
                assert False, "expected title was not found"

        for item in Item.objects.all():
            for exp_title, ids in expected_items:
                if exp_title == item.name:
                    for id in ["proprietary_ids", "uris", "isbn", "issn", "eissn", "doi"]:
                        assert getattr(item, id) == ids[id], f"item {id} mismatch"
                    break
            else:
                assert False, "expected item was not found"

    @pytest.mark.parametrize(
        ["filename", "count"],
        [
            ("counter5_table_dr.csv", 121),
            ("counter5_table_dr.tsv", 121),
            ("counter5_table_ir_m1.csv", 22788),
            ("counter5_table_pr.csv", 252),
            ("counter5_ir_sample.tsv", 48),
        ],
    )
    def test_c5_table_record_count(self, filename, count, platform):
        path = Path(__file__).parent / "data/counter5" / filename
        records = get_records(path, platform)
        assert count == len(records)

    def test_c5_tr_nature_merging(self, organization_random, platform):
        rt = ReportTypeFactory(
            name="Counter 5 - Title report",
            short_name="TR",
            default_platform_interest=True,
            dimensions=Counter5TRReport.dimensions,
        )

        path = Path(__file__).parent / "data/counter5/counter5_tr_nature.json"
        records = get_records(path, platform)
        import_counter_records(rt, organization_random, platform, records)
        assert Title.objects.filter(name="Nature").count() == 1, "only one Nature"
        assert (
            AccessLog.objects.count()
            == AccessLog.objects.values(
                "organization_id",
                "platform_id",
                "report_type_id",
                "metric_id",
                "target_id",
                "date",
                "dim1",
                "dim2",
                "dim3",
                "dim4",
                "dim5",
                "dim6",
                "dim7",
                "dim8",
            )
            .distinct()
            .count()
        ), "no duplicates"

    @pytest.mark.clickhouse
    @pytest.mark.django_db(transaction=True)
    def test_c5_tr_merging_duplicates(self, organization_random, platform, clickhouse_db):
        """
        This tests a real-life example of a report where the same title is reported with different
        proprietary ids. Once it had and ISSN, once it did not.
        Thus, it was taken as two different titles. But then another record came, where the ISSN
        was reported for the title that did not have it before. This should trigger a merge.
        And this then results in the same import batch containing duplicated records for the same
        title and other dimensions.
        """
        rt = ReportTypeFactory(
            name="Counter 5 - Title report",
            short_name="TR",
            default_platform_interest=True,
            dimensions=Counter5TRReport.dimensions,
        )

        path = Path(__file__).parent / "data/counter5/TR-one-title-more-ids.json"
        records = get_records(path, platform)
        import_counter_records(rt, organization_random, platform, records)
        assert Title.objects.filter(name="GQ Gentlemens Quarterly").count() == 2
        t1, t2 = Title.objects.filter(name="GQ Gentlemens Quarterly")
        t_no_issn = t2 if t1.issn else t1
        t_with_issn = t1 if t2 is t_no_issn else t2
        # update t_no_issn with the issn from t_with_issn
        t_no_issn.issn = t_with_issn.issn
        t_no_issn.save()
        for titles in find_mergeable_titles():
            merge_titles(titles)
        assert Title.objects.filter(name="GQ Gentlemens Quarterly").count() == 1
        key_attrs = (
            "organization_id",
            "platform_id",
            "report_type_id",
            "metric_id",
            "target_id",
            "date",
            "dim1",
            "dim2",
            "dim3",
            "dim4",
            "dim5",
            "dim6",
            "dim7",
            "dim8",
        )
        assert (
            AccessLog.objects.count() > AccessLog.objects.values(*key_attrs).distinct().count()
        ), "there are duplicates"
        assert ch_backend.get_count(AccessLogCube.query()) > ch_backend.get_count(
            AccessLogCube.query().group_by(*key_attrs)
        )
        old_sum = AccessLog.objects.aggregate(sum=Sum("value"))["sum"]
        # now we want to fix them
        call_command("find_split_records", "--fix-it")
        assert (
            AccessLog.objects.count() == AccessLog.objects.values(*key_attrs).distinct().count()
        ), "there are no duplicates"
        assert AccessLog.objects.aggregate(sum=Sum("value"))["sum"] == old_sum
        assert (
            ch_backend.get_one_record(AccessLogCube.query().aggregate(HSum("value"))).sum == old_sum
        )


@pytest.mark.django_db
class TestReprocessMDU:
    def test_reimport_admin_action(self, admin_client):
        mdu = ManualDataUploadFullFactory.create()
        # reprocess and check
        with patch("logs.admin.import_manual_upload_data") as task_patch:
            admin_client.post(
                reverse("admin:logs_manualdataupload_changelist"),
                {"action": "reimport", "_selected_action": [str(mdu.pk)]},
            )
            task_patch.apply_async.assert_called_once()
