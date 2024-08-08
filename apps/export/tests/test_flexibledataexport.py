import csv
from io import BytesIO, StringIO, TextIOWrapper
from zipfile import ZipFile

import openpyxl
import pytest
from logs.fake_data import MetricFactory
from logs.logic.reporting.export import (
    FlexibleDataExcelExporter,
    FlexibleDataSimpleCSVExporter,
    FlexibleDataZipCSVExporter,
)
from logs.logic.reporting.filters import (
    DateDimensionFilter,
    ExplicitDimensionFilter,
    ForeignKeyDimensionFilter,
    TagDimensionFilter,
)
from logs.logic.reporting.slicer import FlexibleDataSlicer
from logs.models import DimensionText
from publications.fake_data import TitleFactory
from tags.fake_data import TagClassFactory, TagForTitleFactory
from tags.models import AccessibleBy, TagScope

from export.enums import FileFormat
from export.models import FlexibleDataExport


@pytest.fixture
def slicer(flexible_slicer_test_data):
    """
    creates moderately complex `FlexibleDataSlicer` instance
    """
    slicer = FlexibleDataSlicer(primary_dimension="platform", include_row_totals=True)
    texts = flexible_slicer_test_data["dimension_values"][0][:2]
    report_type = flexible_slicer_test_data["report_types"][0]
    dim1_ids = DimensionText.objects.filter(text__in=texts).values_list("pk", flat=True)
    slicer.add_filter(ExplicitDimensionFilter("dim1", dim1_ids), add_group=True)
    slicer.add_filter(ForeignKeyDimensionFilter("report_type", report_type))
    slicer.add_group_by("metric")
    return slicer


@pytest.fixture
def slicer2(flexible_slicer_test_data):
    MetricFactory(name="", short_name="MS")  # metric with short_name only
    slicer = FlexibleDataSlicer(primary_dimension="metric")
    slicer.include_all_zero_rows = True
    texts = flexible_slicer_test_data["dimension_values"][0][:2]
    report_type = flexible_slicer_test_data["report_types"][0]
    dim1_ids = DimensionText.objects.filter(text__in=texts).values_list("pk", flat=True)
    slicer.add_filter(ExplicitDimensionFilter("dim1", dim1_ids), add_group=True)
    slicer.add_filter(ForeignKeyDimensionFilter("report_type", report_type))
    slicer.add_group_by("platform")
    return slicer


@pytest.fixture
def tagged_titles(flexible_slicer_test_data, admin_user, users):
    titles = flexible_slicer_test_data["targets"]
    tc = TagClassFactory.create(name="TC", scope=TagScope.TITLE)
    tag1 = TagForTitleFactory(tag_class=tc, name="Tag 1")
    tag1.tag(titles[0], admin_user)
    tag1.tag(titles[1], admin_user)
    tag2 = TagForTitleFactory(tag_class=tc, name="Tag 2")
    tag2.tag(titles[2], admin_user)
    # this is a tag which should not be visible to admin_user and thus not appear in any export
    private_tag = TagForTitleFactory(
        name="Private Tag",
        owner=users["user1"],
        can_assign=AccessibleBy.OWNER,
        can_see=AccessibleBy.OWNER,
    )
    private_tag.tag(titles[0], users["user1"])
    return locals()


@pytest.fixture
def export_output():
    """
    Returns a function that will return the contents of the first file in a zip file which is
    not named '_metadata.csv'
    """

    def fn(export: FlexibleDataExport):
        out = BytesIO()
        export.file_format = FileFormat.ZIP_CSV
        export.write_data(out)
        with ZipFile(out, "r") as zipfile:
            names = [name for name in zipfile.namelist() if name != "_metadata.csv"]
            with zipfile.open(names[0], "r") as infile:
                return infile.read().decode("utf-8")

    yield fn


@pytest.mark.django_db
class TestFlexibleDataExport:
    def test_simple(self, slicer, admin_user):
        export = FlexibleDataExport.create_from_slicer(slicer, admin_user)
        assert export.export_params == slicer.config()

    def test_create_output_file_for_slicer(self, slicer, admin_user, export_output):
        export = FlexibleDataExport.create_from_slicer(slicer, admin_user)
        data = export_output(export)
        assert data.splitlines() == [
            "Platform,Tags,Row total,A / Metric 1,A / Metric 2,A / Metric 3,B / Metric 1,"
            "B / Metric 2,B / Metric 3",
            "Platform 1,,81648,13266,13590,13914,13302,13626,13950",
            "Platform 2,,104976,17154,17478,17802,17190,17514,17838",
            "Platform 3,,128304,21042,21366,21690,21078,21402,21726",
        ]

    def test_create_output_file_for_slicer2(self, slicer2, admin_user, export_output):
        export = FlexibleDataExport.create_from_slicer(slicer2, admin_user)
        data = export_output(export)
        assert data.splitlines() == [
            "Metric,A / Platform 1,A / Platform 2,A / Platform 3,B / Platform 1,"
            "B / Platform 2,B / Platform 3",
            "Metric 1,13266,17154,21042,13302,17190,21078",
            "Metric 2,13590,17478,21366,13626,17514,21402",
            "Metric 3,13914,17802,21690,13950,17838,21726",
            "MS,0,0,0,0,0,0",
        ]

    @pytest.mark.parametrize("show_remainder", [True, False])
    def test_create_output_file_with_tag_rollup(
        self, tagged_titles, flexible_slicer_test_data, admin_user, export_output, show_remainder
    ):
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        report_type = flexible_slicer_test_data["report_types"][0]
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", report_type))
        slicer.tag_roll_up = True
        slicer.primary_dimension = "target"
        slicer.show_untagged_remainder = show_remainder
        slicer.add_group_by("metric")

        export = FlexibleDataExport.create_from_slicer(slicer, admin_user)
        data = export_output(export)
        expected = [
            "Tag,Metric 1,Metric 2,Metric 3",
            "Tag 1,102816,104760,106704",
            "Tag 2,51894,52866,53838",
        ]
        if show_remainder:
            expected += ["-- untagged remainder --,0,0,0"]
        assert data.splitlines() == expected
        if show_remainder:
            # try untagging and recomputing
            tagged_titles["tag2"].delete()
            export = FlexibleDataExport.create_from_slicer(slicer, admin_user)
            data = export_output(export)
            assert data.splitlines() == [
                "Tag,Metric 1,Metric 2,Metric 3",
                "Tag 1,102816,104760,106704",
                "-- untagged remainder --,51894,52866,53838",
            ]

    def test_create_output_file_with_tag_rollup_and_hidden_tag_class(
        self, tagged_titles, flexible_slicer_test_data, admin_user, export_output
    ):
        """
        Tags from hidden tag class should not be visible in the output
        """
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        report_type = flexible_slicer_test_data["report_types"][0]
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", report_type))
        slicer.tag_roll_up = True
        slicer.primary_dimension = "target"
        slicer.show_untagged_remainder = False
        slicer.add_group_by("metric")

        # mark class for tag1 as hidden (it is shared by tag1 and tag2, so both should be hidden)
        tag1 = tagged_titles["tag1"]
        tag1.tag_class.change_hidden_for_user(admin_user, True)

        export = FlexibleDataExport.create_from_slicer(slicer, admin_user)
        data = export_output(export)
        assert data.splitlines() == [], "no tags should be visible"

        # add new tag with a new class - it should be visible
        new_tag = TagForTitleFactory(name="New Tag")
        new_tag.tag(flexible_slicer_test_data["targets"][2], admin_user)

        export = FlexibleDataExport.create_from_slicer(slicer, admin_user)
        data = export_output(export)
        assert data.splitlines() == ["Tag,Metric 1,Metric 2,Metric 3", "New Tag,51894,52866,53838"]

    @pytest.mark.parametrize("hide_tag_class", [True, False])
    def test_create_output_file_with_tag_filter(
        self, tagged_titles, flexible_slicer_test_data, admin_user, export_output, hide_tag_class
    ):
        tag1 = tagged_titles["tag1"]
        slicer = FlexibleDataSlicer(primary_dimension="platform")
        report_type = flexible_slicer_test_data["report_types"][0]
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", report_type))
        slicer.add_filter(TagDimensionFilter("target", tag1))
        slicer.primary_dimension = "target"
        slicer.add_group_by("metric")
        t1, t2, _ = tagged_titles["titles"]
        if hide_tag_class:
            # if we hide the tag class, the filtering by tag should still work
            # but the output should not include the tag name
            tag1.tag_class.change_hidden_for_user(admin_user, True)

        export = FlexibleDataExport.create_from_slicer(slicer, admin_user)
        data = export_output(export)
        tag_value = "" if hide_tag_class else tag1.full_name
        # make sure the order is deterministic because there is no ordering in the query
        exp = data.splitlines()
        exp = [exp[0]] + list(sorted(exp[1:]))
        assert exp == [
            "Title/Database,ISSN,EISSN,ISBN,Tags,Metric 1,Metric 2,Metric 3",
            f"Title 1,{t1.issn},{t1.eissn},{t1.isbn},{tag_value},51246,52218,53190",
            f"Title 2,{t2.issn},{t2.eissn},{t2.isbn},{tag_value},51570,52542,53514",
        ]

    def test_tagged_output_query_count(
        self,
        tagged_titles,
        flexible_slicer_test_data,
        admin_user,
        export_output,
        django_assert_max_num_queries,
    ):
        tag1 = tagged_titles["tag1"]
        # create 100 tagged titles
        title100 = TitleFactory.create_batch(100)
        for title in title100:
            tag1.tag(title, admin_user)
        slicer = FlexibleDataSlicer(primary_dimension="platform", include_all_zero_rows=True)
        report_type = flexible_slicer_test_data["report_types"][0]
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", report_type))
        slicer.primary_dimension = "target"
        slicer.add_group_by("metric")

        export = FlexibleDataExport.create_from_slicer(slicer, admin_user)
        with django_assert_max_num_queries(26):
            # we want to avoid the n+1 query problem, so the number of queries should
            # be much lower than the number of titles
            data = export_output(export)
        assert len(data.splitlines()) == 104, "should have 103 titles plus header"

    def test_create_output_file_with_title(
        self, flexible_slicer_test_data, admin_user, export_output
    ):
        """
        Tests that using title as primary dimension also adds ISBN and other extra columns
        """
        slicer = FlexibleDataSlicer(primary_dimension="target")
        slicer.add_group_by("metric")
        export = FlexibleDataExport.create_from_slicer(slicer, admin_user)
        data = export_output(export)
        assert data.splitlines()[0].startswith("Title/Database,ISSN,EISSN,ISBN,")

    @pytest.mark.parametrize(["split_by"], [("platform",), ("date__year",), ("date",)])
    @pytest.mark.parametrize(
        ["fmt", "split"],
        [
            (FileFormat.ZIP_CSV, True),
            (FileFormat.ZIP_CSV, False),
            (FileFormat.XLSX, True),
            (FileFormat.XLSX, False),
            (FileFormat.XLSX_NO_CHARTS, True),
            (FileFormat.XLSX_NO_CHARTS, False),
        ],
    )
    def test_create_output_file_format(
        self, flexible_slicer_test_data, admin_user, fmt, split, split_by, inmemory_media
    ):
        """
        Tests that using title as primary dimension also adds ISBN and other extra columns
        """
        slicer = FlexibleDataSlicer(primary_dimension="target")
        if split:
            slicer.add_split_by(split_by)
        slicer.add_group_by("metric")
        export = FlexibleDataExport.create_from_slicer(slicer, admin_user, fmt=fmt)
        export.create_output_file(raise_exception=True)
        assert export.output_file.name.endswith(".zip" if fmt == FileFormat.ZIP_CSV else ".xlsx")
        # both .zip and .xlsx are zip files
        with ZipFile(export.output_file.file, "r") as zipfile:
            if fmt == FileFormat.ZIP_CSV:
                for archname in zipfile.namelist():
                    assert archname.endswith(".csv")
                assert "_metadata.csv" in zipfile.namelist()
            else:
                assert (
                    "[Content_Types].xml" in zipfile.namelist()
                ), "XLSX should contain [Content_Types].xml"
                workbook = openpyxl.load_workbook(export.output_file.file)
                assert "metadata" in workbook.sheetnames


@pytest.mark.django_db
class TestFlexibleDataExportCSV:
    @pytest.mark.parametrize("zip_csv", [True, False])
    @pytest.mark.parametrize("row_totals", [True, False])
    @pytest.mark.parametrize("col_totals", [True, False])
    def test_totals(self, flexible_slicer_test_data, row_totals, col_totals, zip_csv):
        """
        Tests that totals are calculated correctly
        """
        slicer = FlexibleDataSlicer(primary_dimension="organization")
        slicer.add_group_by("platform")
        slicer.order_by = ["organization__name"]
        exporter_cls = FlexibleDataZipCSVExporter if zip_csv else FlexibleDataSimpleCSVExporter
        exporter = exporter_cls(
            slicer, include_tags=False, include_row_totals=row_totals, include_col_totals=col_totals
        )
        out = BytesIO() if zip_csv else StringIO()
        exporter.stream_data_to_sink(out)
        out.seek(0)
        if zip_csv:
            with ZipFile(out, "r") as zipfile:
                with zipfile.open("report.csv", "r") as csvfile:
                    rows = list(csv.reader(TextIOWrapper(csvfile)))
        else:
            rows = list(csv.reader(out))
        exp = [
            ["Organization", "Platform 1", "Platform 2", "Platform 3"],
            ["Organization 1", "519318", "717606", "915894"],
            ["Organization 2", "1114182", "1312470", "1510758"],
            ["Organization 3", "1709046", "1907334", "2105622"],
        ]
        if col_totals:
            exp.append(["Total", "3342546", "3937410", "4532274"])
        if row_totals:
            exp[0].insert(1, "Row total")
            for i, row in enumerate(exp[1:]):
                exp[i + 1].insert(1, str(sum(int(x) for x in row[1:])))
        assert rows == exp

    @pytest.mark.parametrize("zip_csv", [True, False])
    @pytest.mark.parametrize("row_totals", [True, False])
    @pytest.mark.parametrize("col_totals", [True, False])
    def test_trend_mode(self, flexible_slicer_test_data, row_totals, col_totals, zip_csv):
        slicer = FlexibleDataSlicer(
            primary_dimension="platform",
            trend_mode=True,
            base_subset_filters=[DateDimensionFilter("date", "2019-12-01", "2019-12-31")],
            compared_subset_filters=[DateDimensionFilter("date", "2020-01-01", "2020-03-31")],
        )
        slicer.order_by = ["platform__name"]
        # include_row_totals is ignored in trend mode, but we add it to test to really check
        # that it is ignored
        exporter_cls = FlexibleDataZipCSVExporter if zip_csv else FlexibleDataSimpleCSVExporter
        exporter = exporter_cls(
            slicer, include_tags=False, include_row_totals=row_totals, include_col_totals=col_totals
        )
        out = BytesIO() if zip_csv else StringIO()
        exporter.stream_data_to_sink(out)
        out.seek(0)
        if zip_csv:
            with ZipFile(out, "r") as zipfile:
                with zipfile.open("report.csv", "r") as csvfile:
                    rows = list(csv.reader(TextIOWrapper(csvfile)))
        else:
            rows = list(csv.reader(out))
        p1_base, p1_compared = 779868, 2562678
        p2_base, p2_compared = 928584, 3008826
        p3_base, p3_compared = 1077300, 3454974
        exp = [
            ["Platform", "2019-12", "2020-01 - 2020-03", "Change", "Change %"],
            [
                "Platform 1",
                str(p1_base),
                str(p1_compared),
                str(p1_compared - p1_base),
                str((p1_compared - p1_base) / p1_base),
            ],
            [
                "Platform 2",
                str(p2_base),
                str(p2_compared),
                str(p2_compared - p2_base),
                str((p2_compared - p2_base) / p2_base),
            ],
            [
                "Platform 3",
                str(p3_base),
                str(p3_compared),
                str(p3_compared - p3_base),
                str((p3_compared - p3_base) / p3_base),
            ],
        ]
        if col_totals:
            base = p1_base + p2_base + p3_base
            compared = p1_compared + p2_compared + p3_compared
            exp.append(
                [
                    "Total",
                    str(base),
                    str(compared),
                    str(compared - base),
                    str((compared - base) / base),
                ]
            )
        assert rows == exp


@pytest.mark.django_db
class TestFlexibleDataExportExcel:
    def test_totals_as_formulas(self, flexible_slicer_test_data):
        """
        Primary dimension: organization
        Group by: platform
        DimensionFilter:
        """
        slicer = FlexibleDataSlicer(primary_dimension="organization")
        slicer.add_group_by("platform")
        slicer.order_by = ["organization__name"]
        exporter = FlexibleDataExcelExporter(
            slicer, include_tags=False, include_charts=False, include_col_totals=True
        )
        out = BytesIO()
        exporter.stream_data_to_sink(out)
        out.seek(0)
        workbook = openpyxl.load_workbook(out)
        assert workbook.sheetnames == ["metadata", "report"]
        sheet = workbook["report"]
        assert [[cell.value for cell in row] for row in sheet.rows] == [
            ["Organization", "Platform 1", "Platform 2", "Platform 3"],
            ["Organization 1", 519318, 717606, 915894],
            ["Organization 2", 1114182, 1312470, 1510758],
            ["Organization 3", 1709046, 1907334, 2105622],
            ["Total", "=SUM(B2:B4)", "=SUM(C2:C4)", "=SUM(D2:D4)"],
        ]

    @pytest.mark.parametrize("include_tags", [True, False])
    @pytest.mark.parametrize("row_totals", [True, False])
    def test_trend_mode(self, flexible_slicer_test_data, include_tags, row_totals, admin_user):
        slicer = FlexibleDataSlicer(
            primary_dimension="platform",
            trend_mode=True,
            base_subset_filters=[DateDimensionFilter("date", "2019-12-01", "2019-12-31")],
            compared_subset_filters=[DateDimensionFilter("date", "2020-01-01", "2020-03-31")],
        )
        slicer.order_by = ["platform__name"]
        # include_row_totals is ignored when trend_mode is True, but we want to check it anyway
        exporter = FlexibleDataExcelExporter(
            slicer,
            report_owner=admin_user,
            include_tags=include_tags,
            include_charts=False,
            include_row_totals=row_totals,
            include_col_totals=True,
        )
        out = BytesIO()
        exporter.stream_data_to_sink(out)
        out.seek(0)
        workbook = openpyxl.load_workbook(out)
        sheet = workbook["report"]
        exp_data = [
            ["Platform", "2019-12", "2020-01 - 2020-03", "Change", "Change %"],
            ["Platform 1", 779868, 2562678, "=C2-B2", "=(C2-B2)/B2"],
            ["Platform 2", 928584, 3008826, "=C3-B3", "=(C3-B3)/B3"],
            ["Platform 3", 1077300, 3454974, "=C4-B4", "=(C4-B4)/B4"],
            ["Total", "=SUM(B2:B4)", "=SUM(C2:C4)", "=C5-B5", "=(C5-B5)/B5"],
        ]
        if include_tags:

            def shift(text):
                """Shifts the letters in the formula by one to the right."""
                for letter in "EDCBA":
                    text = text.replace(letter, chr(ord(letter) + 1))
                return text

            exp_data[0].insert(1, "Tags")
            for i in range(1, 5):
                # add None for tags
                exp_data[i].insert(1, None)
                # shift the rest of the columns to the right
                exp_data[i][4] = shift(exp_data[i][4])
                exp_data[i][5] = shift(exp_data[i][5])
                if i == 4:
                    exp_data[i][2] = shift(exp_data[i][2])
                    exp_data[i][3] = shift(exp_data[i][3])

        assert [[cell.value for cell in row] for row in sheet.rows] == exp_data

    @pytest.mark.parametrize("include_row_totals", [True, False])
    @pytest.mark.parametrize("include_col_totals", [True, False])
    def test_show_totals(self, flexible_slicer_test_data, include_row_totals, include_col_totals):
        slicer = FlexibleDataSlicer(primary_dimension="organization")
        slicer.add_group_by("platform")
        slicer.order_by = ["organization__name"]
        exporter = FlexibleDataExcelExporter(
            slicer,
            include_charts=False,
            include_row_totals=include_row_totals,
            include_col_totals=include_col_totals,
        )
        out = BytesIO()
        exporter.stream_data_to_sink(out)
        out.seek(0)
        workbook = openpyxl.load_workbook(out)
        ws = workbook["report"]
        if include_row_totals:
            expected_output = [
                ["Organization", "Row total", "Platform 1", "Platform 2", "Platform 3"],
                ["Organization 1", "=SUM(C2,D2,E2)", 519318, 717606, 915894],
                ["Organization 2", "=SUM(C3,D3,E3)", 1114182, 1312470, 1510758],
                ["Organization 3", "=SUM(C4,D4,E4)", 1709046, 1907334, 2105622],
            ]
            if include_col_totals:
                expected_output.append(
                    ["Total", "=SUM(C5,D5,E5)", "=SUM(C2:C4)", "=SUM(D2:D4)", "=SUM(E2:E4)"]
                )
        else:
            expected_output = [
                ["Organization", "Platform 1", "Platform 2", "Platform 3"],
                ["Organization 1", 519318, 717606, 915894],
                ["Organization 2", 1114182, 1312470, 1510758],
                ["Organization 3", 1709046, 1907334, 2105622],
            ]
            if include_col_totals:
                expected_output.append(["Total", "=SUM(B2:B4)", "=SUM(C2:C4)", "=SUM(D2:D4)"])
        assert [[cell.value for cell in row] for row in ws.rows] == expected_output
