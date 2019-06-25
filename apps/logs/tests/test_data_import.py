import pytest

from logs.models import ReportType, Dimension, ReportTypeToDimension, OrganizationPlatform
from publications.models import Platform
from sushi.counter5 import CounterRecord

from ..logic.data_import import import_counter_records
from organizations.tests.fixtures import organizations


@pytest.fixture
def counter_records():
    rec1 = CounterRecord(platform='Platform1', start='2019-01-01', end='2019-01-31', title='Title X',
                         title_ids={'issn': '1234-5678'})
    rec1.metric = 'Metric 1'
    rec1.value = 50
    return [rec1]


@pytest.mark.django_db
class TestDataImport(object):

    """
    Tests functionality of the logic.data_import module
    """

    def test_simple_data_import(self, counter_records, organizations):
        platform = Platform.objects.create(ext_id='pl1', short_name='Platform1', name='Platform 1',
                                           provider='Provider 1')
        op = OrganizationPlatform(organization=organizations[0], platform=platform)
        import_counter_records()


