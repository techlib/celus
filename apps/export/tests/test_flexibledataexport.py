import pytest

from export.models import FlexibleDataExport
from logs.logic.queries import (
    FlexibleDataSlicer,
    ForeignKeyDimensionFilter,
    ExplicitDimensionFilter,
)
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


@pytest.mark.django_db
class TestFlexibleDataExport:
    def test_simple(self, slicer, admin_user):
        export = FlexibleDataExport.create_from_slicer(slicer, admin_user)
        assert export.export_params == slicer.config()

    def test_file_output(self, slicer, admin_user, settings):
        settings.DEFAULT_FILE_STORAGE = 'inmemorystorage.InMemoryStorage'
        export = FlexibleDataExport.create_from_slicer(slicer, admin_user)
        export.output_file.name = 'test.csv'
        with export.output_file.open('w') as outfile:
            export.write_data(outfile)
        assert export.output_file.size > 0
        data = export.output_file.open('r').read()
        assert data.splitlines() == [
            'platform,A / Metric 1,A / Metric 2,A / Metric 3,B / Metric 1,B / Metric 2,B / Metric 3',
            'Platform 1,12294,13590,14886,12330,13626,14922',
            'Platform 2,16182,17478,18774,16218,17514,18810',
            'Platform 3,20070,21366,22662,20106,21402,22698',
        ]

    def test_create_output_file(self, slicer, admin_user, settings):
        settings.DEFAULT_FILE_STORAGE = 'inmemorystorage.InMemoryStorage'
        export = FlexibleDataExport.create_from_slicer(slicer, admin_user)
        export.create_output_file()
        assert export.output_file.size > 0
        data = export.output_file.open('r').read()
        assert data.splitlines() == [
            'platform,A / Metric 1,A / Metric 2,A / Metric 3,B / Metric 1,B / Metric 2,B / Metric 3',
            'Platform 1,12294,13590,14886,12330,13626,14922',
            'Platform 2,16182,17478,18774,16218,17514,18810',
            'Platform 3,20070,21366,22662,20106,21402,22698',
        ]

    def test_create_output_file_with_title(self, flexible_slicer_test_data, admin_user, settings):
        """
        Tests that using title as primary dimension also adds ISBN and other extra columns
        """
        slicer = FlexibleDataSlicer(primary_dimension='target')
        slicer.add_group_by('metric')
        settings.DEFAULT_FILE_STORAGE = 'inmemorystorage.InMemoryStorage'
        export = FlexibleDataExport.create_from_slicer(slicer, admin_user)
        export.create_output_file()
        assert export.output_file.size > 0
        data = export.output_file.open('r').read()
        assert data.splitlines()[0].startswith('target,ISSN,EISSN,ISBN,')
