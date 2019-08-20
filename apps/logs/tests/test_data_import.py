import pytest

from logs.models import ReportType, AccessLog, DimensionText, ImportBatch
from publications.models import Platform, Title

from ..logic.data_import import import_counter_records
from organizations.tests.conftest import organizations


@pytest.mark.django_db
class TestDataImport(object):

    """
    Tests functionality of the logic.data_import module
    """

    def test_api_simple_data_0d(self, counter_records_0d, organizations, report_type_nd):
        platform = Platform.objects.create(ext_id=1234, short_name='Platform1', name='Platform 1',
                                           provider='Provider 1')
        assert AccessLog.objects.count() == 0
        assert Title.objects.count() == 0
        report_type = report_type_nd(0)
        import_counter_records(report_type, organizations[0], platform, counter_records_0d,
                               ImportBatch.objects.create(organization=organizations[0],
                                                          platform=platform,
                                                          report_type=report_type))
        assert AccessLog.objects.count() == 1
        assert Title.objects.count() == 1
        al = AccessLog.objects.get()
        assert al.value == 50
        assert al.dim1 is None

    def test_simple_data_import_1d(self, counter_records_nd, organizations, report_type_nd):
        platform = Platform.objects.create(ext_id=1234, short_name='Platform1', name='Platform 1',
                                           provider='Provider 1')
        assert AccessLog.objects.count() == 0
        assert Title.objects.count() == 0
        crs = list(counter_records_nd(1))
        report_type = report_type_nd(1)
        import_counter_records(report_type, organizations[0], platform, crs,
                               ImportBatch.objects.create(organization=organizations[0],
                                                          platform=platform,
                                                          report_type=report_type))
        assert AccessLog.objects.count() == 1
        assert Title.objects.count() == 1
        al = AccessLog.objects.get()
        assert al.value == crs[0].value
        # check that the remap of the value is the same as the original text value
        assert DimensionText.objects.get(pk=al.dim1).text == crs[0].dimension_data['dim0']
        assert al.dim2 is None

    def test_data_import_mutli_3d(self, counter_records_nd, organizations, report_type_nd):
        platform = Platform.objects.create(ext_id=1234, short_name='Platform1', name='Platform 1',
                                           provider='Provider 1')
        assert AccessLog.objects.count() == 0
        assert Title.objects.count() == 0
        crs = list(counter_records_nd(3, record_number=10))
        report_type = report_type_nd(3)
        stats = import_counter_records(report_type, organizations[0], platform, crs,
                                       ImportBatch.objects.create(organization=organizations[0],
                                                                  platform=platform,
                                                                  report_type=report_type))
        assert stats['skipped logs'] == 0
        assert stats['new logs'] == 10
        assert AccessLog.objects.count() == 10
        assert Title.objects.count() > 0
        al = AccessLog.objects.order_by('pk')[0]
        assert al.value == crs[0].value
        # check that the remap of the value is the same as the original text value
        assert DimensionText.objects.get(pk=al.dim1).text == crs[0].dimension_data['dim0']
        assert DimensionText.objects.get(pk=al.dim2).text == crs[0].dimension_data['dim1']
        assert DimensionText.objects.get(pk=al.dim3).text == crs[0].dimension_data['dim2']
        assert al.dim4 is None

    def test_data_import_mutli_3d_repeating_data(self, counter_records_nd, organizations,
                                                 report_type_nd):
        platform = Platform.objects.create(ext_id=1234, short_name='Platform1', name='Platform 1',
                                           provider='Provider 1')
        assert AccessLog.objects.count() == 0
        assert Title.objects.count() == 0
        crs = list(counter_records_nd(3, record_number=10, title='Title ABC',
                                      dim_value='one value'))
        rt = report_type_nd(3)  # type: ReportType
        import_counter_records(rt, organizations[0], platform, crs,
                               ImportBatch.objects.create(organization=organizations[0],
                                                          platform=platform,
                                                          report_type=rt))
        assert AccessLog.objects.count() == 10
        assert Title.objects.count() > 0
        al1, al2 = AccessLog.objects.order_by('pk')[:2]
        assert al1.value == crs[0].value
        # check that only one remap is created for each dimension
        assert DimensionText.objects.filter(text='one value').count() == 3
        dt1 = DimensionText.objects.get(text='one value', dimension=rt.dimensions_sorted[0])
        # check that values with the same dimension use the same remap
        assert al1.dim1 == dt1.pk
        assert al2.dim1 == dt1.pk
        dt2 = DimensionText.objects.get(text='one value', dimension=rt.dimensions_sorted[1])
        assert al1.dim2 == dt2.pk
        assert al2.dim2 == dt2.pk
        assert al1.dim3 is not None
        assert al1.dim4 is None

    def test_reimport(self, counter_records_nd, organizations, report_type_nd):
        platform = Platform.objects.create(ext_id=1234, short_name='Platform1', name='Platform 1',
                                           provider='Provider 1')
        crs = list(counter_records_nd(3, record_number=1, title='Title ABC',
                                      dim_value='one value'))
        rt = report_type_nd(3)  # type: ReportType
        stats = import_counter_records(rt, organizations[0], platform, crs,
                                       ImportBatch.objects.create(organization=organizations[0],
                                                                  platform=platform,
                                                                  report_type=rt))
        assert AccessLog.objects.count() == 1
        assert Title.objects.count() == 1
        assert stats['new logs'] == 1
        stats = import_counter_records(rt, organizations[0], platform, crs,
                                       ImportBatch.objects.create(organization=organizations[0],
                                                                  platform=platform,
                                                                  report_type=rt))
        assert stats['new logs'] == 0
        assert stats['skipped logs'] == 1
