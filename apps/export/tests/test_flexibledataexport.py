from io import BytesIO
from zipfile import ZipFile

import pytest
from export.enums import FileFormat
from export.models import FlexibleDataExport
from logs.logic.reporting.filters import (
    ExplicitDimensionFilter,
    ForeignKeyDimensionFilter,
    TagDimensionFilter,
)
from logs.logic.reporting.slicer import FlexibleDataSlicer
from logs.models import DimensionText
from publications.logic.fake_data import TitleFactory
from tags.logic.fake_data import TagClassFactory, TagForTitleFactory
from tags.models import TagScope

from test_fixtures.entities.logs import MetricFactory


@pytest.fixture
def slicer(flexible_slicer_test_data):
    """
    creates moderately complex `FlexibleDataSlicer` instance
    """
    slicer = FlexibleDataSlicer(primary_dimension='platform')
    texts = flexible_slicer_test_data['dimension_values'][0][:2]
    report_type = flexible_slicer_test_data['report_types'][0]
    dim1_ids = DimensionText.objects.filter(text__in=texts).values_list('pk', flat=True)
    slicer.add_filter(ExplicitDimensionFilter('dim1', dim1_ids), add_group=True)
    slicer.add_filter(ForeignKeyDimensionFilter('report_type', report_type))
    slicer.add_group_by('metric')
    return slicer


@pytest.fixture
def slicer2(flexible_slicer_test_data):
    MetricFactory(name="", short_name="MS")  # metric with short_name only
    slicer = FlexibleDataSlicer(primary_dimension='metric')
    slicer.include_all_zero_rows = True
    texts = flexible_slicer_test_data['dimension_values'][0][:2]
    report_type = flexible_slicer_test_data['report_types'][0]
    dim1_ids = DimensionText.objects.filter(text__in=texts).values_list('pk', flat=True)
    slicer.add_filter(ExplicitDimensionFilter('dim1', dim1_ids), add_group=True)
    slicer.add_filter(ForeignKeyDimensionFilter('report_type', report_type))
    slicer.add_group_by('platform')
    return slicer


@pytest.fixture
def tagged_titles(flexible_slicer_test_data, admin_user):
    titles = flexible_slicer_test_data['targets']
    tc = TagClassFactory.create(name='TC', scope=TagScope.TITLE)
    tag1 = TagForTitleFactory(tag_class=tc, name='Tag 1')
    tag1.tag(titles[0], admin_user)
    tag1.tag(titles[1], admin_user)
    tag2 = TagForTitleFactory(tag_class=tc, name='Tag 2')
    tag2.tag(titles[2], admin_user)
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
        with ZipFile(out, 'r') as zipfile:
            names = [name for name in zipfile.namelist() if name != '_metadata.csv']
            with zipfile.open(names[0], 'r') as infile:
                return infile.read().decode('utf-8')

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
            'Platform,Tags,A / Metric 1,A / Metric 2,A / Metric 3,B / Metric 1,B / Metric 2,B / Metric 3',
            'Platform 1,,12294,13590,14886,12330,13626,14922',
            'Platform 2,,16182,17478,18774,16218,17514,18810',
            'Platform 3,,20070,21366,22662,20106,21402,22698',
        ]

    def test_create_output_file_for_slicer2(self, slicer2, admin_user, export_output):
        export = FlexibleDataExport.create_from_slicer(slicer2, admin_user)
        data = export_output(export)
        assert data.splitlines() == [
            'Metric,A / Platform 1,A / Platform 2,A / Platform 3,B / Platform 1,B / Platform 2,B / Platform 3',
            'Metric 1,12294,16182,20070,12330,16218,20106',
            'Metric 2,13590,17478,21366,13626,17514,21402',
            'Metric 3,14886,18774,22662,14922,18810,22698',
            'MS,0,0,0,0,0,0',
        ]

    @pytest.mark.parametrize('show_remainder', [True, False])
    def test_create_output_file_with_tag_rollup(
        self, tagged_titles, flexible_slicer_test_data, admin_user, export_output, show_remainder
    ):
        slicer = FlexibleDataSlicer(primary_dimension='platform')
        report_type = flexible_slicer_test_data['report_types'][0]
        slicer.add_filter(ForeignKeyDimensionFilter('report_type', report_type))
        slicer.tag_roll_up = True
        slicer.primary_dimension = 'target'
        slicer.show_untagged_remainder = show_remainder
        slicer.add_group_by('metric')

        export = FlexibleDataExport.create_from_slicer(slicer, admin_user)
        data = export_output(export)
        expected = [
            'Tag,Metric 1,Metric 2,Metric 3',
            'Tag 1,96012,103788,111564',
            'Tag 2,49950,53838,57726',
        ]
        if show_remainder:
            expected += ['-- untagged remainder --,0,0,0']
        assert data.splitlines() == expected
        if show_remainder:
            # try untagging and recomputing
            tagged_titles['tag2'].delete()
            export = FlexibleDataExport.create_from_slicer(slicer, admin_user)
            data = export_output(export)
            assert data.splitlines() == [
                'Tag,Metric 1,Metric 2,Metric 3',
                'Tag 1,96012,103788,111564',
                '-- untagged remainder --,49950,53838,57726',
            ]

    def test_create_output_file_with_tag_filter(
        self, tagged_titles, flexible_slicer_test_data, admin_user, export_output
    ):
        tag1 = tagged_titles['tag1']
        slicer = FlexibleDataSlicer(primary_dimension='platform')
        report_type = flexible_slicer_test_data['report_types'][0]
        slicer.add_filter(ForeignKeyDimensionFilter('report_type', report_type))
        slicer.add_filter(TagDimensionFilter('target', tag1))
        slicer.primary_dimension = 'target'
        slicer.add_group_by('metric')
        t1, t2, _ = tagged_titles['titles']

        export = FlexibleDataExport.create_from_slicer(slicer, admin_user)
        data = export_output(export)
        assert data.splitlines() == [
            'Title/Database,ISSN,EISSN,ISBN,Tags,Metric 1,Metric 2,Metric 3',
            f'Title 1,{t1.issn},{t1.eissn},{t1.isbn},{tag1.full_name},47358,51246,55134',
            f'Title 2,{t2.issn},{t2.eissn},{t2.isbn},{tag1.full_name},48654,52542,56430',
        ]

    def test_tagged_output_query_count(
        self,
        tagged_titles,
        flexible_slicer_test_data,
        admin_user,
        export_output,
        django_assert_max_num_queries,
    ):
        tag1 = tagged_titles['tag1']
        # create 100 tagged titles
        title100 = TitleFactory.create_batch(100)
        for title in title100:
            tag1.tag(title, admin_user)
        slicer = FlexibleDataSlicer(primary_dimension='platform', include_all_zero_rows=True)
        report_type = flexible_slicer_test_data['report_types'][0]
        slicer.add_filter(ForeignKeyDimensionFilter('report_type', report_type))
        slicer.primary_dimension = 'target'
        slicer.add_group_by('metric')

        export = FlexibleDataExport.create_from_slicer(slicer, admin_user)
        with django_assert_max_num_queries(20):
            # we want to avoid the n+1 query problem, so the number of queries should
            # be much lower than the number of titles
            data = export_output(export)
        assert len(data.splitlines()) == 104, 'should have 103 titles plus header'

    def test_create_output_file_with_title(
        self, flexible_slicer_test_data, admin_user, export_output
    ):
        """
        Tests that using title as primary dimension also adds ISBN and other extra columns
        """
        slicer = FlexibleDataSlicer(primary_dimension='target')
        slicer.add_group_by('metric')
        export = FlexibleDataExport.create_from_slicer(slicer, admin_user)
        data = export_output(export)
        assert data.splitlines()[0].startswith('Title/Database,ISSN,EISSN,ISBN,')

    @pytest.mark.parametrize(['split_by'], [('platform',), ('date__year',), ('date',)])
    @pytest.mark.parametrize(
        ['fmt', 'split'],
        [
            (FileFormat.ZIP_CSV, True),
            (FileFormat.ZIP_CSV, False),
            (FileFormat.XLSX, True),
            (FileFormat.XLSX, False),
        ],
    )
    def test_create_output_file_format(
        self, flexible_slicer_test_data, admin_user, fmt, split, split_by, inmemory_media
    ):
        """
        Tests that using title as primary dimension also adds ISBN and other extra columns
        """
        slicer = FlexibleDataSlicer(primary_dimension='target')
        if split:
            slicer.add_split_by(split_by)
        slicer.add_group_by('metric')
        export = FlexibleDataExport.create_from_slicer(slicer, admin_user, fmt=fmt)
        export.create_output_file(raise_exception=True)
        assert export.output_file.name.endswith('.zip' if fmt == FileFormat.ZIP_CSV else '.xlsx')
        # both .zip and .xlsx are zip files
        with ZipFile(export.output_file.file, 'r') as zipfile:
            if fmt == FileFormat.ZIP_CSV:
                for archname in zipfile.namelist():
                    assert archname.endswith('.csv')
            else:
                assert (
                    '[Content_Types].xml' in zipfile.namelist()
                ), 'XLSX should contain [Content_Types].xml'
