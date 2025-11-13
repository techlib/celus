import csv
from datetime import datetime
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
from logs.logic.reporting.slicer import FlexibleDataSlicer, SlicerConfigError, SlicerConfigErrorCode
from logs.models import DimensionText
from organizations.fake_data import OrganizationFactory
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
    slicer = FlexibleDataSlicer(["platform"], include_row_totals=True)
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
    slicer = FlexibleDataSlicer(["metric"])
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
        slicer = FlexibleDataSlicer(["target"])
        report_type = flexible_slicer_test_data["report_types"][0]
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", report_type))
        slicer.tag_roll_up = True
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
        slicer = FlexibleDataSlicer(["target"])
        report_type = flexible_slicer_test_data["report_types"][0]
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", report_type))
        slicer.tag_roll_up = True
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
        slicer = FlexibleDataSlicer(["target"])
        report_type = flexible_slicer_test_data["report_types"][0]
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", report_type))
        slicer.add_filter(TagDimensionFilter("target", tag1))
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
        slicer = FlexibleDataSlicer(["target"], include_all_zero_rows=True)
        report_type = flexible_slicer_test_data["report_types"][0]
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", report_type))
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
        slicer = FlexibleDataSlicer(["target"])
        slicer.add_group_by("metric")
        export = FlexibleDataExport.create_from_slicer(slicer, admin_user)
        data = export_output(export)
        assert data.splitlines()[0].startswith("Title/Database,ISSN,EISSN,ISBN,")

    def test_create_output_file_with_item(
        self, flexible_slicer_test_data_with_items, admin_user, export_output
    ):
        """
        Tests that using item as primary dimension also adds DOI and other extra columns.
        Also test that publication date is formatted correctly.
        """
        slicer = FlexibleDataSlicer(["item"])
        slicer.order_by = ["item__name"]
        slicer.add_group_by("metric")
        slicer.order_by = ["item__name"]
        export = FlexibleDataExport.create_from_slicer(slicer, admin_user)
        data = export_output(export)
        assert data.splitlines()[0].startswith("Item,DOI,ISSN,EISSN,ISBN,Publication date,")
        assert data.splitlines()[1].startswith("Item 1,10.1234/567890,,,,2020-01-01,")

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
        slicer = FlexibleDataSlicer(["target"])
        if split:
            slicer.add_split_by(split_by)
        slicer.add_group_by("metric")
        export = FlexibleDataExport.create_from_slicer(slicer, admin_user, fmt=fmt)
        export.create_output_file(raise_exception=True)
        assert export.output_file.name.endswith(".zip" if fmt == FileFormat.ZIP_CSV else ".xlsx")
        # both .zip and .xlsx are zip files
        with ZipFile(export.output_file.file.name, "r") as zipfile:
            if fmt == FileFormat.ZIP_CSV:
                for archname in zipfile.namelist():
                    assert archname.endswith(".csv")
                assert "_metadata.csv" in zipfile.namelist()
            else:
                assert "[Content_Types].xml" in zipfile.namelist(), (
                    "XLSX should contain [Content_Types].xml"
                )
                workbook = openpyxl.load_workbook(export.output_file.file.name)
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
        slicer = FlexibleDataSlicer(["organization"])
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
            ["platform"],
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
class TestFlexibleDataExportMultiindex:
    def test_basic_multiindex_csv(self, flexible_slicer_test_data, admin_user, export_output):
        """
        Test basic multiindex export with 2 primary dimensions (organization, platform)
        """
        slicer = FlexibleDataSlicer(["organization", "platform"])
        slicer.add_group_by("metric")
        slicer.order_by = ["organization", "platform"]
        export = FlexibleDataExport.create_from_slicer(slicer, admin_user)
        data = export_output(export)
        lines = data.splitlines()
        # Check header (Tags columns are included after each taggable dimension)
        assert lines[0].startswith(
            "Organization,Organization Tags,Platform,Platform Tags,Metric 1,Metric 2,Metric 3"
        )
        # Check that we have 9 data rows (3 orgs x 3 platforms)
        assert len(lines) == 10  # 1 header + 9 data rows
        # Check first data row (now with empty tags columns)
        assert lines[1].startswith("Organization 1,,Platform 1,,")

    def test_multiindex_with_title(self, flexible_slicer_test_data, admin_user, export_output):
        """
        Test multiindex with a dimension that has extra columns (title with ISSN, etc.)
        """
        slicer = FlexibleDataSlicer(["platform", "target"])
        slicer.add_group_by("metric")
        slicer.order_by = ["platform", "target"]
        export = FlexibleDataExport.create_from_slicer(slicer, admin_user)
        data = export_output(export)
        lines = data.splitlines()
        # Check header includes extra columns for title (ISSN, EISSN, ISBN)
        header = lines[0]
        assert "Platform" in header
        assert "Title/Database" in header
        assert "ISSN" in header
        assert "EISSN" in header
        assert "ISBN" in header
        # Check that we have 9 data rows (3 platforms x 3 titles)
        assert len(lines) == 10  # 1 header + 9 data rows

        # Verify actual ISSN, EISSN, ISBN values are exported in data rows
        titles = flexible_slicer_test_data["targets"]
        # Find header column positions
        cols = header.split(",")
        issn_idx = cols.index("ISSN")
        eissn_idx = cols.index("EISSN")
        isbn_idx = cols.index("ISBN")

        # Check at least one row has actual identifier values
        found_values = {"issn": [], "eissn": [], "isbn": []}

        for line in lines[1:]:  # Skip header
            parts = line.split(",")
            if len(parts) > max(issn_idx, eissn_idx, isbn_idx):
                # Collect non-empty values
                if parts[issn_idx].strip():
                    found_values["issn"].append(parts[issn_idx])
                if parts[eissn_idx].strip():
                    found_values["eissn"].append(parts[eissn_idx])
                if parts[isbn_idx].strip():
                    found_values["isbn"].append(parts[isbn_idx])

        # At least one of the identifiers should be present
        assert found_values["issn"] or found_values["eissn"] or found_values["isbn"], (
            f"No ISSN, EISSN, or ISBN values found in export. "
            f"Sample row: {lines[1] if len(lines) > 1 else 'N/A'}"
        )

        # Verify that the exported identifiers match actual title data
        exported_issns = set(found_values["issn"])
        exported_eissns = set(found_values["eissn"])
        exported_isbns = set(found_values["isbn"])
        actual_issns = {t.issn for t in titles if t.issn}
        actual_eissns = {t.eissn for t in titles if t.eissn}
        actual_isbns = {t.isbn for t in titles if t.isbn}

        # Check that exported values are a subset of actual values (or equal)
        assert exported_issns.issubset(actual_issns) or not exported_issns, (
            f"Exported ISSNs {exported_issns} don't match actual {actual_issns}"
        )
        assert exported_eissns.issubset(actual_eissns) or not exported_eissns, (
            f"Exported EISSNs {exported_eissns} don't match actual {actual_eissns}"
        )
        assert exported_isbns.issubset(actual_isbns) or not exported_isbns, (
            f"Exported ISBNs {exported_isbns} don't match actual {actual_isbns}"
        )

    def test_triple_index(self, flexible_slicer_test_data, admin_user, export_output):
        """
        Test with 3 primary dimensions - including verification of title identifiers
        """
        slicer = FlexibleDataSlicer(["organization", "platform", "target"])
        slicer.add_group_by("metric")
        slicer.order_by = ["organization", "platform", "target"]
        export = FlexibleDataExport.create_from_slicer(slicer, admin_user)
        data = export_output(export)
        lines = data.splitlines()
        header = lines[0]
        # Check header has all 3 dimensions (plus Tags, ISSN, EISSN, ISBN for title)
        assert "Organization" in header
        assert "Platform" in header
        assert "Title/Database" in header
        assert "ISSN" in header
        assert "EISSN" in header
        assert "ISBN" in header
        # Check that we have 27 data rows (3 orgs x 3 platforms x 3 titles)
        assert len(lines) == 28  # 1 header + 27 data rows

        # Verify title identifiers are exported (not just empty columns)
        cols = header.split(",")
        issn_idx = cols.index("ISSN")
        isbn_idx = cols.index("ISBN")

        # Check that at least some rows have identifier values
        identifiers_found = False
        for line in lines[1:]:
            parts = line.split(",")
            if len(parts) > max(issn_idx, isbn_idx):
                if parts[issn_idx].strip() or parts[isbn_idx].strip():
                    identifiers_found = True
                    break

        assert identifiers_found, (
            f"No ISSN or ISBN values found in triple index export. "
            f"Sample row: {lines[1] if len(lines) > 1 else 'N/A'}"
        )

    def test_multiindex_with_tags(
        self, flexible_slicer_test_data, admin_user, export_output, tagged_titles
    ):
        """
        Test that tags appear right after their dimension columns in multiindex
        """
        # Tag some platforms too
        from publications.models import Platform
        from tags.fake_data import TagFactory

        platforms = Platform.objects.all()
        tc = TagClassFactory.create(name="Platform TC", scope=TagScope.PLATFORM)
        platform_tag = TagFactory(tag_class=tc, name="Platform Tag 1")
        platform_tag.tag(platforms[0], admin_user)

        slicer = FlexibleDataSlicer(["platform", "target"])
        slicer.add_group_by("metric")
        slicer.order_by = ["platform", "target"]
        export = FlexibleDataExport.create_from_slicer(slicer, admin_user)
        data = export_output(export)
        lines = data.splitlines()
        header = lines[0]
        # Check that tags appear right after their dimension columns with dimension name prefix:
        # Platform, Platform Tags, Title/Database, ISSN, EISSN, ISBN, Title/Database Tags, ...
        cols = header.split(",")
        platform_idx = cols.index("Platform")
        # Tags column should come right after Platform and include dimension name
        assert cols[platform_idx + 1] == "Platform Tags"

        # Find Title/Database index
        title_idx = cols.index("Title/Database")
        # ISBN comes after ISSN, EISSN, ISBN for title
        issn_idx = cols.index("ISSN")
        eissn_idx = cols.index("EISSN")
        isbn_idx = cols.index("ISBN")
        # Tags should come after ISBN
        assert issn_idx == title_idx + 1
        assert eissn_idx == title_idx + 2
        assert isbn_idx == title_idx + 3
        # Find tags column after title attributes - should include dimension name
        tags_after_title = isbn_idx + 1
        assert cols[tags_after_title] == "Title/Database Tags"

    def test_multiindex_with_tags_single_dimension_compatibility(
        self, flexible_slicer_test_data, admin_user, export_output, tagged_titles
    ):
        """
        Test that single dimension reports still use "tags" column name (not pk_tags)
        """
        slicer = FlexibleDataSlicer(["target"])
        slicer.add_group_by("metric")
        export = FlexibleDataExport.create_from_slicer(slicer, admin_user)
        data = export_output(export)
        lines = data.splitlines()
        header = lines[0]
        # For single dimension, should use "Tags" not "pk_tags"
        assert "Title/Database,ISSN,EISSN,ISBN,Tags," in header
        # Verify that pk_tags is NOT in the header (backward compatibility)
        assert "pk_tags" not in header.lower()

    def test_multiindex_with_totals_csv(self, flexible_slicer_test_data):
        """
        Test multiindex with row and column totals in CSV
        """
        import csv
        from io import StringIO

        slicer = FlexibleDataSlicer(["organization", "platform"])
        slicer.add_group_by("metric")
        slicer.order_by = ["organization", "platform"]
        exporter = FlexibleDataSimpleCSVExporter(
            slicer, include_row_totals=True, include_col_totals=True
        )
        out = StringIO()
        exporter.stream_data_to_sink(out)
        out.seek(0)
        rows = list(csv.reader(out))
        # Check header has row total column
        assert "Row total" in rows[0]
        # Check last row is totals
        assert rows[-1][0] == "Total"
        # Verify structure: Organization, Platform, Row total, Metric1, Metric2, Metric3
        assert len(rows[0]) == 6  # 2 primary dims + row total + 3 metrics

    def test_multiindex_excel(self, flexible_slicer_test_data):
        """
        Test multiindex with Excel export
        """
        from io import BytesIO

        import openpyxl

        slicer = FlexibleDataSlicer(["organization", "platform"])
        slicer.add_group_by("metric")
        slicer.order_by = ["organization", "platform"]
        exporter = FlexibleDataExcelExporter(slicer, include_charts=False, include_col_totals=True)
        out = BytesIO()
        exporter.stream_data_to_sink(out)
        out.seek(0)
        workbook = openpyxl.load_workbook(out)
        assert "report" in workbook.sheetnames
        sheet = workbook["report"]
        # Check header
        header = [cell.value for cell in list(sheet.rows)[0]]
        assert header[0] == "Organization"
        assert header[1] == "Platform"
        # Check we have data rows
        assert len(list(sheet.rows)) > 1

    def test_multiindex_with_split_by(self, flexible_slicer_test_data, admin_user, inmemory_media):
        """
        Test multiindex with split_by creating multiple sheets
        """
        slicer = FlexibleDataSlicer(["organization", "platform"])
        slicer.add_group_by("metric")
        slicer.add_split_by("target")
        slicer.order_by = ["organization", "platform"]
        export = FlexibleDataExport.create_from_slicer(slicer, admin_user, fmt=FileFormat.ZIP_CSV)
        export.create_output_file(raise_exception=True)
        # Verify the file was created and has multiple CSV files
        with ZipFile(export.output_file.file.name, "r") as zipfile:
            csv_files = [name for name in zipfile.namelist() if name.endswith(".csv")]
            # Should have metadata + one file per title (3 titles)
            assert len(csv_files) >= 3

    def test_multiindex_trend_mode_csv(self, flexible_slicer_test_data, admin_user, export_output):
        """
        Test CSV export with multiindex + trend mode
        """
        slicer = FlexibleDataSlicer(
            ["platform", "organization"],
            trend_mode=True,
            base_subset_filters=[DateDimensionFilter("date", "2019-12-01", "2019-12-31")],
            compared_subset_filters=[DateDimensionFilter("date", "2020-01-01", "2020-03-31")],
        )
        slicer.add_filter(
            ForeignKeyDimensionFilter("report_type", flexible_slicer_test_data["report_types"][0])
        )
        slicer.order_by = ["platform", "organization"]
        export = FlexibleDataExport.create_from_slicer(slicer, admin_user)
        data = export_output(export)
        lines = data.splitlines()

        # Check header - includes tag columns for multiindex
        header = lines[0]
        expected_headers = [
            "Platform",
            "Platform Tags",
            "Organization",
            "Organization Tags",
            "2019-12",
            "2020-01 - 2020-03",
            "Change",
            "Change %",
        ]
        assert header == ",".join(expected_headers)

        # Check that we have data rows
        assert len(lines) > 1  # At least header + data rows

        # Check first data row has numeric values for trend columns
        if len(lines) > 1:
            first_data_row = lines[1].split(",")
            assert len(first_data_row) == 8  # 4 dimension columns + 4 trend columns
            # Check that trend columns are numeric (not empty)
            assert first_data_row[4] == "378"  # base
            assert first_data_row[5] == "5508"  # compared
            assert first_data_row[6] == "5130"  # diff
            assert first_data_row[7] != ""  # reldiff

    def test_multiindex_trend_mode_excel(self, flexible_slicer_test_data, admin_user):
        """
        Test Excel export with multiindex + trend mode including formulas
        """
        slicer = FlexibleDataSlicer(
            ["platform", "organization"],
            trend_mode=True,
            base_subset_filters=[DateDimensionFilter("date", "2019-12-01", "2019-12-31")],
            compared_subset_filters=[DateDimensionFilter("date", "2020-01-01", "2020-03-31")],
        )
        slicer.add_filter(
            ForeignKeyDimensionFilter("report_type", flexible_slicer_test_data["report_types"][0])
        )
        exporter = FlexibleDataExcelExporter(slicer, include_tags=False, include_charts=False)
        out = BytesIO()
        exporter.stream_data_to_sink(out)
        out.seek(0)
        workbook = openpyxl.load_workbook(out)
        sheet = workbook["report"]

        # Check headers - no tag columns when include_tags=False
        headers = [cell.value for cell in sheet[1]]
        expected_headers = [
            "Platform",
            "Organization",
            "2019-12",
            "2020-01 - 2020-03",
            "Change",
            "Change %",
        ]
        assert headers == expected_headers

        # Check that we have data rows
        assert sheet.max_row > 1

        # Check that formulas are present in trend columns
        if sheet.max_row > 1:
            # Check that Change column has formulas (column 5 = E)
            change_cell = sheet.cell(row=2, column=5)  # Change column
            assert change_cell.value is not None
            if isinstance(change_cell.value, str) and change_cell.value.startswith("="):
                # It's a formula - should be D2-C2 (compared - base)
                assert "D2-C2" in change_cell.value or "D3-C3" in change_cell.value

            # Check that Change % column has formulas (column 6 = F)
            change_pct_cell = sheet.cell(row=2, column=6)  # Change % column
            assert change_pct_cell.value is not None
            if isinstance(change_pct_cell.value, str) and change_pct_cell.value.startswith("="):
                # It's a formula
                assert "(" in change_pct_cell.value and ")" in change_pct_cell.value

    def test_multiindex_trend_mode_with_totals(
        self, flexible_slicer_test_data, admin_user, export_output
    ):
        """
        Test multiindex + trend mode with column totals
        """
        slicer = FlexibleDataSlicer(
            ["platform", "organization"],
            trend_mode=True,
            base_subset_filters=[DateDimensionFilter("date", "2019-12-01", "2019-12-31")],
            compared_subset_filters=[DateDimensionFilter("date", "2020-01-01", "2020-03-31")],
        )
        slicer.add_filter(
            ForeignKeyDimensionFilter("report_type", flexible_slicer_test_data["report_types"][0])
        )
        slicer.order_by = ["organization", "platform"]
        export = FlexibleDataExport.create_from_slicer(slicer, admin_user)
        export.include_col_totals = True
        data = export_output(export)
        lines = data.splitlines()

        # Check that we have data rows
        assert len(lines) > 1

        expected_values = [
            [378, 5508, 5130],
            [3294, 14256, 10962],
            [6210, 23004, 16794],
            [9126, 31752, 22626],
            [12042, 40500, 28458],
            [14958, 49248, 34290],
            [17874, 57996, 40122],
            [20790, 66744, 45954],
            [23706, 75492, 51786],
        ]

        for i, line in enumerate(lines[1:]):  # Skip header
            values = line.split(",")
            assert len(values) == 8  # 4 dimension columns + 4 trend columns
            # Check that trend columns have numeric values
            assert values[4] == str(expected_values[i][0])  # base
            assert values[5] == str(expected_values[i][1])  # compared
            assert values[6] == str(expected_values[i][2])  # diff
            assert values[7] != ""  # hard to check, just check that it is not empty


@pytest.mark.django_db
class TestFlexibleDataExportExcel:
    def test_totals_as_formulas(self, flexible_slicer_test_data):
        """
        Primary dimension: organization
        Group by: platform
        DimensionFilter:
        """
        slicer = FlexibleDataSlicer(["organization"])
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

    @pytest.mark.parametrize("multiindex", [True, False])
    def test_dates_have_correct_format(self, flexible_slicer_test_data, multiindex):
        """
        Tests that dates have correct format
        """
        slicer = FlexibleDataSlicer(["organization", "date"] if multiindex else ["date"])
        slicer.add_group_by("platform")
        slicer.order_by = ["date"]
        exporter = FlexibleDataExcelExporter(slicer, include_charts=False, include_col_totals=True)
        out = BytesIO()
        exporter.stream_data_to_sink(out)
        out.seek(0)
        workbook = openpyxl.load_workbook(out)
        sheet = workbook["report"]
        # we need to check that the dates are correctly formatted
        # (they are numbers with the date format, which openpyxl converts to datetime)
        date_col = 1 if multiindex else 0
        org_multiplier = 3 if multiindex else 1
        for row in sheet.iter_rows(min_row=2, max_row=1 + org_multiplier * 4):  # 4 months
            cell = row[date_col]
            assert isinstance(cell.value, datetime)
            assert cell.number_format == "yyyy-mm"

    def test_create_output_file_with_item(
        self, flexible_slicer_test_data_with_items, admin_user, export_output
    ):
        """
        Tests that using item as primary dimension also adds DOI and other extra columns
        """
        slicer = FlexibleDataSlicer(["item"])
        slicer.add_group_by("metric")
        slicer.order_by = ["item__name"]
        exporter = FlexibleDataExcelExporter(slicer, include_charts=False, include_col_totals=True)
        out = BytesIO()
        exporter.stream_data_to_sink(out)
        out.seek(0)
        workbook = openpyxl.load_workbook(out)
        sheet = workbook["report"]

        assert [[cell.value for cell in row] for row in sheet.rows] == [
            ["Item", "DOI", "ISSN", "EISSN", "ISBN", "Publication date", "Metric 1", "Metric 2"],
            [
                "Item 1",
                "10.1234/567890",
                None,
                None,
                None,
                datetime(2020, 1, 1, 0, 0),
                26688,
                28128,
            ],
            ["Item 2", "10.1234/567891", "3574-4169", None, None, None, 26784, 28224],
            ["Item 3", "10.1234/567892", None, None, "978-3-16-148410-0", None, 27456, 28896],
            ["Total", None, None, None, None, None, "=SUM(G2:G4)", "=SUM(H2:H4)"],
        ]

    @pytest.mark.parametrize("include_tags", [True, False])
    @pytest.mark.parametrize("row_totals", [True, False])
    def test_trend_mode(self, flexible_slicer_test_data, include_tags, row_totals, admin_user):
        slicer = FlexibleDataSlicer(
            ["platform"],
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
        slicer = FlexibleDataSlicer(["organization"])
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

    @pytest.mark.parametrize(["max_parts", "error"], [(2, True), (3, False)])
    def test_maximum_part_number_excel(self, flexible_slicer_test_data, max_parts, error):
        slicer = FlexibleDataSlicer(["platform"])
        slicer.MAXIMUM_POSSIBLE_PARTS = max_parts
        slicer.add_group_by("metric")
        slicer.add_split_by("target")
        exporter = FlexibleDataExcelExporter(slicer, include_tags=False, include_charts=False)
        out = BytesIO()
        if error:
            with pytest.raises(SlicerConfigError) as exc:
                exporter.stream_data_to_sink(out)
            assert exc.value.code == SlicerConfigErrorCode.E112.value
        else:
            # should not raise an exception
            exporter.stream_data_to_sink(out)

    @pytest.mark.parametrize(["max_cols", "error"], [(2, True), (3, False)])
    def test_maximum_column_number(self, flexible_slicer_test_data, max_cols, error):
        slicer = FlexibleDataSlicer(["platform"])
        slicer.MAXIMUM_POSSIBLE_GROUPS = max_cols
        slicer.add_group_by("metric")
        exporter = FlexibleDataExcelExporter(slicer, include_tags=False, include_charts=False)
        out = BytesIO()
        if error:
            with pytest.raises(SlicerConfigError) as exc:
                exporter.stream_data_to_sink(out)
            assert exc.value.code == SlicerConfigErrorCode.E101.value
        else:
            # should not raise an exception
            exporter.stream_data_to_sink(out)

    @pytest.mark.parametrize(["max_parts", "error"], [(2, True), (3, False)])
    def test_maximum_part_number_csv(self, flexible_slicer_test_data, max_parts, error):
        slicer = FlexibleDataSlicer(["platform"])
        slicer.MAXIMUM_POSSIBLE_PARTS = max_parts
        slicer.add_group_by("metric")
        slicer.add_split_by("target")
        exporter = FlexibleDataZipCSVExporter(slicer, include_tags=False)
        out = BytesIO()
        if error:
            with pytest.raises(SlicerConfigError) as exc:
                exporter.stream_data_to_sink(out)
            assert exc.value.code == SlicerConfigErrorCode.E112.value
        else:
            # should not raise an exception
            exporter.stream_data_to_sink(out)

    def test_empty_export(self, flexible_slicer_test_data):
        slicer = FlexibleDataSlicer(["organization"])
        slicer.add_group_by("platform")
        m = MetricFactory(name="Empty metric")
        slicer.add_filter(ForeignKeyDimensionFilter("metric", [m]))
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
        assert [[cell.value for cell in row] for row in sheet.rows] == []

    def test_empty_export_with_empty_coverage(self, flexible_slicer_test_data):
        """
        Check that there is no error when exporting data with empty coverage.
        """
        slicer = FlexibleDataSlicer(["organization"])
        slicer.add_group_by("platform")
        # when using new organization, the coverage is empty
        org = OrganizationFactory()
        slicer.add_filter(ForeignKeyDimensionFilter("organization", [org]))
        exporter = FlexibleDataExcelExporter(
            slicer, include_tags=False, include_charts=False, include_col_totals=True
        )
        out = BytesIO()
        exporter.stream_data_to_sink(out)
        out.seek(0)
        workbook = openpyxl.load_workbook(out)
        assert workbook.sheetnames == ["metadata", "report"]
        sheet = workbook["report"]
        assert [[cell.value for cell in row] for row in sheet.rows] == []
        for row in workbook["metadata"].iter_rows():
            if row[0].value == "Coverage":
                assert row[1].value == "-"

    # --- Multiindex incompatible options (export-level) ---

    def test_multiindex_tag_roll_up_incompatible_export(self, flexible_slicer_test_data):
        slicer = FlexibleDataSlicer(["platform", "organization"], tag_roll_up=True)
        slicer.add_group_by("metric")
        exporter = FlexibleDataExcelExporter(slicer, include_tags=False, include_charts=False)
        out = BytesIO()
        with pytest.raises(SlicerConfigError) as exc:
            exporter.stream_data_to_sink(out)
        assert exc.value.code == SlicerConfigErrorCode.E114.value

    def test_multiindex_include_all_zero_rows_incompatible_export(self, flexible_slicer_test_data):
        slicer = FlexibleDataSlicer(["platform", "organization"], include_all_zero_rows=True)
        slicer.add_group_by("metric")
        exporter = FlexibleDataExcelExporter(slicer, include_tags=False, include_charts=False)
        out = BytesIO()
        with pytest.raises(SlicerConfigError) as exc:
            exporter.stream_data_to_sink(out)
        assert exc.value.code == SlicerConfigErrorCode.E115.value

    def test_multiindex_trend_mode_export(self, flexible_slicer_test_data, admin_user):
        slicer = FlexibleDataSlicer(
            ["platform", "organization"],
            trend_mode=True,
            base_subset_filters=[DateDimensionFilter("date", "2019-12-01", "2019-12-31")],
            compared_subset_filters=[DateDimensionFilter("date", "2020-01-01", "2020-03-31")],
        )
        slicer.add_filter(
            ForeignKeyDimensionFilter("report_type", flexible_slicer_test_data["report_types"][0])
        )
        exporter = FlexibleDataExcelExporter(
            slicer, include_tags=True, include_charts=False, report_owner=admin_user
        )
        out = BytesIO()
        exporter.stream_data_to_sink(out)
        out.seek(0)
        workbook = openpyxl.load_workbook(out)
        sheet = workbook["report"]

        # Check that we have the expected columns - includes tag columns for multiindex
        headers = [cell.value for cell in sheet[1]]
        expected_headers = [
            "Platform",
            "Platform Tags",
            "Organization",
            "Organization Tags",
            "2019-12",
            "2020-01 - 2020-03",
            "Change",
            "Change %",
        ]
        assert headers == expected_headers

        # Check that we have data rows
        assert sheet.max_row > 1  # At least header + data rows

    def test_multiindex_explicit_dimension_excel(self, flexible_slicer_test_data, admin_user):
        """
        Test Excel export with multiindex using explicit remapped dimensions (dim1, dim2)
        """
        slicer = FlexibleDataSlicer(["dim1", "platform"])
        slicer.add_group_by("metric")
        slicer.add_filter(
            ForeignKeyDimensionFilter("report_type", flexible_slicer_test_data["report_types"][0])
        )
        slicer.order_by = ["dim1", "platform"]
        exporter = FlexibleDataExcelExporter(slicer, include_tags=False, include_charts=False)
        out = BytesIO()
        exporter.stream_data_to_sink(out)
        out.seek(0)
        workbook = openpyxl.load_workbook(out)
        sheet = workbook["report"]

        # Check headers
        headers = [cell.value for cell in sheet[1]]
        expected_headers = ["dimension-0", "Platform", "Metric 1", "Metric 2", "Metric 3"]
        assert headers == expected_headers

        # Check that we have data rows
        assert sheet.max_row > 1

        # Check first data row has actual values (not empty)
        first_data_row = [cell.value for cell in sheet[2]]  # Row 2 (after header)
        assert len(first_data_row) == 5
        # Check that dim1 column has actual text values (not empty)
        assert first_data_row[0] is not None
        assert first_data_row[0] != ""
        assert isinstance(first_data_row[0], str)
        # Check that platform column has actual text values
        assert first_data_row[1] is not None
        assert first_data_row[1] != ""
        assert isinstance(first_data_row[1], str)
        # Check that metric columns have numeric values
        assert first_data_row[2] is not None
        assert first_data_row[3] is not None
        assert first_data_row[4] is not None

    def test_multiindex_explicit_dimension_csv(
        self, flexible_slicer_test_data, admin_user, export_output
    ):
        """
        Test CSV export with multiindex using explicit remapped dimensions (dim1, dim2)
        """
        slicer = FlexibleDataSlicer(["dim1", "platform"])
        slicer.add_group_by("metric")
        slicer.add_filter(
            ForeignKeyDimensionFilter("report_type", flexible_slicer_test_data["report_types"][0])
        )
        slicer.order_by = ["dim1", "platform"]
        # Use the exporter directly to control include_tags
        exporter = FlexibleDataSimpleCSVExporter(slicer, include_tags=False)
        out = StringIO()
        exporter.stream_data_to_sink(out)
        data = out.getvalue()
        lines = data.splitlines()

        # Check header
        header = lines[0]
        expected_headers = ["dimension-0", "Platform", "Metric 1", "Metric 2", "Metric 3"]
        assert header == ",".join(expected_headers)

        # Check that we have data rows
        assert len(lines) > 1

        # Check first data row has actual values (not empty)
        first_data_row = lines[1].split(",")
        assert len(first_data_row) == 5
        # Check that dim1 column has actual text values (not empty)
        assert first_data_row[0] != ""
        assert first_data_row[0] in ["A", "B", "C"]  # Expected dim1 values
        # Check that platform column has actual text values
        assert first_data_row[1] != ""
        assert first_data_row[1] in ["Platform 1", "Platform 2", "Platform 3"]
        # Check that metric columns have numeric values
        assert first_data_row[2] != ""
        assert first_data_row[3] != ""
        assert first_data_row[4] != ""


@pytest.mark.django_db
class TestFlexibleDataExportMergeReportTypes:
    def test_cover_sheet_metadata_shows_merged_report_types(
        self, flexible_slicer_test_data, admin_user
    ):
        """
        Test that cover sheet metadata shows merged report types when merge_report_types is True
        """
        slicer = FlexibleDataSlicer(["platform"], merge_report_types=True)
        report_types = flexible_slicer_test_data["report_types"]
        # Need exactly 2 report types for merge_report_types
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", report_types[:2]))
        slicer.add_group_by("metric")

        export = FlexibleDataExport.create_from_slicer(slicer, admin_user)
        export.file_format = FileFormat.ZIP_CSV
        out = BytesIO()
        export.write_data(out)
        out.seek(0)

        with ZipFile(out, "r") as zipfile:
            with zipfile.open("_metadata.csv", "r") as infile:
                metadata_content = infile.read().decode("utf-8")
                lines = metadata_content.splitlines()

        # Check that "Merged report types" appears in metadata
        merged_rt_line_idx = 0
        for idx, line in enumerate(lines):
            if "Merged report types" in line or "merged report types" in line.lower():
                merged_rt_line_idx = idx
                break
        else:
            assert False, "Merged report types line not found in metadata"

        # Check that both report type names are present
        assert report_types[0].name in lines[merged_rt_line_idx]
        assert report_types[1].name in lines[merged_rt_line_idx + 1]

    @pytest.mark.parametrize("include_row_totals", [True, False])
    @pytest.mark.parametrize("include_col_totals", [True, False])
    def test_export_contains_report_types_column(
        self,
        flexible_slicer_test_data,
        admin_user,
        export_output,
        include_row_totals,
        include_col_totals,
    ):
        """
        Test that exported data contains Used reports column when merge_report_types is True
        """
        slicer = FlexibleDataSlicer(
            ["platform"],
            merge_report_types=True,
            include_row_totals=include_row_totals,
            include_col_totals=include_col_totals,
        )
        report_types = flexible_slicer_test_data["report_types"]
        # Need exactly 2 report types for merge_report_types
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", report_types[:2]))
        slicer.add_group_by("metric")

        export = FlexibleDataExport.create_from_slicer(slicer, admin_user)
        data = export_output(export)
        lines = data.splitlines()

        # Check header contains Used reports column
        header = lines[0]
        assert "Used reports" in header

        # Check that data rows have Used reports column with values
        # The column should be the last column in the output
        header_parts = header.split(",")
        rt_col_index = header_parts.index("Used reports")

        # Verify it's the last column
        assert rt_col_index == len(header_parts) - 1, "Used reports should be the last column"

        assert len(lines) > 1, "No data rows found in exported data"
        # Check at least one data row has report type names
        found_rt_values = False
        for line in lines[1:]:
            parts = line.split(",")
            if len(parts) > rt_col_index:
                rt_value = parts[rt_col_index]
                # Should contain at least one report type name
                if rt_value and rt_value != "-":
                    assert report_types[0].name in rt_value or report_types[1].name in rt_value
                    found_rt_values = True

        assert found_rt_values, "No report type values found in exported data"

    def test_export_without_merge_report_types_no_column(
        self, flexible_slicer_test_data, admin_user, export_output
    ):
        """
        Test that Used reports column is NOT present when merge_report_types is False
        """
        slicer = FlexibleDataSlicer(["platform"], merge_report_types=False)
        report_type = flexible_slicer_test_data["report_types"][0]
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", report_type))
        slicer.add_group_by("metric")

        export = FlexibleDataExport.create_from_slicer(slicer, admin_user)
        data = export_output(export)
        lines = data.splitlines()

        # Check header does NOT contain Used reports column
        header = lines[0]
        assert "Used reports" not in header

        # Also check metadata doesn't contain merged report types info
        export.file_format = FileFormat.ZIP_CSV
        out = BytesIO()
        export.write_data(out)
        out.seek(0)
        with ZipFile(out, "r") as zipfile:
            with zipfile.open("_metadata.csv", "r") as infile:
                metadata_content = infile.read().decode("utf-8")
                assert "merged report types" not in metadata_content.lower()

    @pytest.mark.parametrize(
        "exporter_cls", [FlexibleDataSimpleCSVExporter, FlexibleDataZipCSVExporter]
    )
    def test_report_types_column_in_all_formats(self, flexible_slicer_test_data, exporter_cls):
        """
        Test that Used reports column works in both CSV and ZIP CSV formats
        """
        slicer = FlexibleDataSlicer(["platform"], merge_report_types=True)
        report_types = flexible_slicer_test_data["report_types"]
        slicer.add_filter(ForeignKeyDimensionFilter("report_type", report_types[:2]))
        slicer.add_group_by("metric")

        exporter = exporter_cls(slicer)
        out = StringIO() if exporter_cls == FlexibleDataSimpleCSVExporter else BytesIO()
        exporter.stream_data_to_sink(out)
        out.seek(0)

        if exporter_cls == FlexibleDataZipCSVExporter:
            with ZipFile(out, "r") as zipfile:
                names = [name for name in zipfile.namelist() if name != "_metadata.csv"]
                with zipfile.open(names[0], "r") as csvfile:
                    content = csvfile.read().decode("utf-8")
        else:
            content = out.read()

        lines = content.splitlines()
        header = lines[0]
        assert "Used reports" in header
