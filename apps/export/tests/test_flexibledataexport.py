from io import BytesIO
from zipfile import ZipFile

import pytest

from export.enums import FileFormat
from export.models import FlexibleDataExport
from logs.logic.reporting.filters import ForeignKeyDimensionFilter, ExplicitDimensionFilter
from logs.logic.reporting.slicer import FlexibleDataSlicer
from logs.models import DimensionText


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

    def test_create_output_file(self, slicer, admin_user, export_output):
        export = FlexibleDataExport.create_from_slicer(slicer, admin_user)
        data = export_output(export)
        assert data.splitlines() == [
            'Platform,A / Metric 1,A / Metric 2,A / Metric 3,B / Metric 1,B / Metric 2,B / Metric 3',
            'Platform 1,12294,13590,14886,12330,13626,14922',
            'Platform 2,16182,17478,18774,16218,17514,18810',
            'Platform 3,20070,21366,22662,20106,21402,22698',
        ]

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
        self, flexible_slicer_test_data, admin_user, settings, fmt, split, split_by
    ):
        """
        Tests that using title as primary dimension also adds ISBN and other extra columns
        """
        settings.DEFAULT_FILE_STORAGE = 'inmemorystorage.InMemoryStorage'
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
