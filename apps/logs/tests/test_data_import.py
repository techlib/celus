import pytest

from logs.models import ReportType, Dimension, ReportTypeToDimension, OrganizationPlatform, \
    AccessLog
from publications.models import Platform
from sushi.counter5 import CounterRecord

from ..logic.data_import import import_counter_records
from organizations.tests.fixtures import organizations


@pytest.fixture
def counter_records():
    rec1 = CounterRecord(platform='Platform1', start='2019-01-01', end='2019-01-31',
                         title='Title X', title_ids={'Print_ISSN': '1234-5678'})
    rec1.metric = 'Metric 1'
    rec1.value = 50
    return [rec1]


@pytest.fixture
def report_types():
    rt1 = ReportType.objects.create(short_name='0d', name='0 dimensional report')
    return [rt1]


@pytest.mark.django_db
class TestDataImport(object):

    """
    Tests functionality of the logic.data_import module
    """

    def test_simple_data_import(self, counter_records, organizations, report_types):
        platform = Platform.objects.create(ext_id=1234, short_name='Platform1', name='Platform 1',
                                           provider='Provider 1')
        op = OrganizationPlatform.objects.create(organization=organizations[0], platform=platform)
        assert AccessLog.objects.count() == 0
        import_counter_records(report_types[0], op, counter_records)
        assert AccessLog.objects.count() == 1
        al = AccessLog.objects.get()
        assert al.value == 50
        assert al.dim1 is None


