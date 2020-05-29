import pytest

from core.models import DataSource
from erms.sync import ERMSObjectSyncer
from publications.logic.sync import PlatformSyncer
from publications.models import Platform


@pytest.mark.django_db
class TestERMSSynchronization(object):

    def test_dict_syncer(self):
        data = [{'id': 2265,
                 'class': 'Platform',
                 'vals': {'url': ['https://foo.bar.baz/'],
                          'name@en': ['NAME-EN'],
                          'name@cs': ['NAME-CS'],
                          'provider@en': ['Provider EN'],
                          'provider@cs': ['Provider CS'],
                          'short name@en': ['SHORT_NAME']},
                 'refs': {}}]
        data_source, _created = DataSource.objects.get_or_create(short_name='ERMS',
                                                                 type=DataSource.TYPE_API)
        syncer = PlatformSyncer(data_source)
        stats = syncer.sync_data(data)
        assert stats[ERMSObjectSyncer.Status.NEW] == 1
        assert Platform.objects.count() == 1
        platform = Platform.objects.get()
        assert platform.name == 'NAME-EN'
        assert platform.name_en == 'NAME-EN'
        assert platform.name_cs == 'NAME-CS'
        assert platform.provider == 'Provider EN'
        assert platform.provider_cs == 'Provider CS'
        assert platform.short_name == 'SHORT_NAME'
        assert platform.url == 'https://foo.bar.baz/'

