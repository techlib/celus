import pytest

from logs.models import ReportType, Dimension, ReportTypeToDimension, OrganizationPlatform, \
    AccessLog, DimensionText
from publications.models import Platform, Title
from sushi.counter5 import CounterRecord
import faker

from ..logic.data_import import import_counter_records
from organizations.tests.fixtures import organizations


@pytest.fixture
def counter_records_0d():
    rec1 = CounterRecord(platform='Platform1', start='2019-01-01', end='2019-01-31',
                         metric='Metric 1', value=50, dimension_data={},
                         title='Title X', title_ids={'Print_ISSN': '1234-5678'})
    return [rec1]


@pytest.fixture
def counter_records_nd():
    def fn(dim_number, record_number=1, title=None, dim_value=None):
        """
        :param dim_number: number of dimensions
        :param record_number: number of records
        :param title: if given, used for all titles, otherwise random value will be created
        :param dim_value: use this for all dimensions values, if None, a random word will be used
        :return:
        """
        fake = faker.Faker()
        for i in range(record_number):
            dim_data = {f'dim{i}': fake.word() if dim_value is None else dim_value
                        for i in range(dim_number)}
            if title is None:
                title = f'title {fake.pyint()}'
            rec = CounterRecord(platform=f'Platform{fake.pyint()}',
                                start='2019-01-01',
                                end='2019-01-31',
                                metric=f'Metric {fake.pyint()}',
                                value=fake.pyint(),
                                dimension_data=dim_data,
                                title=title,
                                title_ids={'ISBN': fake.isbn13()})
            yield rec
    return fn


@pytest.fixture
def report_type_nd():
    def fn(dim_number):
        rt = ReportType.objects.create(short_name=f'{dim_number}d',
                                       name=f'{dim_number} dimensional report')
        for i in range(dim_number):
            dim = Dimension.objects.create(short_name=f'dim{i}', name=f'dimension-{i}',
                                           type=Dimension.TYPE_TEXT)
            ReportTypeToDimension.objects.create(report_type=rt, dimension=dim, position=i)
        return rt
    return fn


@pytest.mark.django_db
class TestDataImport(object):

    """
    Tests functionality of the logic.data_import module
    """

    def test_simple_data_import_0d(self, counter_records_0d, organizations, report_type_nd):
        platform = Platform.objects.create(ext_id=1234, short_name='Platform1', name='Platform 1',
                                           provider='Provider 1')
        op = OrganizationPlatform.objects.create(organization=organizations[0], platform=platform)
        assert AccessLog.objects.count() == 0
        assert Title.objects.count() == 0
        import_counter_records(report_type_nd(0), op, counter_records_0d)
        assert AccessLog.objects.count() == 1
        assert Title.objects.count() == 1
        al = AccessLog.objects.get()
        assert al.value == 50
        assert al.dim1 is None

    def test_simple_data_import_1d(self, counter_records_nd, organizations, report_type_nd):
        platform = Platform.objects.create(ext_id=1234, short_name='Platform1', name='Platform 1',
                                           provider='Provider 1')
        op = OrganizationPlatform.objects.create(organization=organizations[0], platform=platform)
        assert AccessLog.objects.count() == 0
        assert Title.objects.count() == 0
        crs = list(counter_records_nd(1))
        import_counter_records(report_type_nd(1), op, crs)
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
        op = OrganizationPlatform.objects.create(organization=organizations[0], platform=platform)
        assert AccessLog.objects.count() == 0
        assert Title.objects.count() == 0
        crs = list(counter_records_nd(3, record_number=10))
        stats = import_counter_records(report_type_nd(3), op, crs)
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
        op = OrganizationPlatform.objects.create(organization=organizations[0], platform=platform)
        assert AccessLog.objects.count() == 0
        assert Title.objects.count() == 0
        crs = list(counter_records_nd(3, record_number=10, title='Title ABC',
                                      dim_value='one value'))
        rt = report_type_nd(3)  # type: ReportType
        import_counter_records(rt, op, crs)
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
        op = OrganizationPlatform.objects.create(organization=organizations[0], platform=platform)
        crs = list(counter_records_nd(3, record_number=1, title='Title ABC',
                                      dim_value='one value'))
        rt = report_type_nd(3)  # type: ReportType
        stats = import_counter_records(rt, op, crs)
        assert AccessLog.objects.count() == 1
        assert Title.objects.count() == 1
        assert stats['new logs'] == 1
        stats = import_counter_records(rt, op, crs)
        assert stats['new logs'] == 0
        assert stats['skipped logs'] == 1
