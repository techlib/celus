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
    def fn(dim_number, record_number=1):
        fake = faker.Faker()
        for i in range(record_number):
            dim_data = {f'dim{i}': fake.word() for i in range(dim_number)}
            rec = CounterRecord(platform=f'Platform{fake.pyint()}',
                                start='2019-01-01',
                                end='2019-01-31',
                                metric=f'Metric {fake.pyint()}',
                                value=fake.pyint(),
                                dimension_data=dim_data,
                                title=f'title {fake.pyint()}',
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
        import_counter_records(report_type_nd(3), op, crs)
        assert AccessLog.objects.count() == 10
        assert Title.objects.count() > 0
        al = AccessLog.objects.order_by('pk')[0]
        assert al.value == crs[0].value
        # check that the remap of the value is the same as the original text value
        assert DimensionText.objects.get(pk=al.dim1).text == crs[0].dimension_data['dim0']
        assert DimensionText.objects.get(pk=al.dim2).text == crs[0].dimension_data['dim1']
        assert DimensionText.objects.get(pk=al.dim3).text == crs[0].dimension_data['dim2']
        assert al.dim4 is None

