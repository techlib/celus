import pytest

from organizations.logic.data_import import import_sushi_credentials
from organizations.logic.sync import OrganizationSyncer
from organizations.models import Organization, SushiCredentials
from publications.models import Platform


@pytest.mark.django_db
class TestLogicDataImport(object):

    def test_sushi_import(self, organizations):
        assert SushiCredentials.objects.count() == 0
        data = [
            {
                'platform': 'XXX',
                'organization': organizations[0].internal_id,
                'client_id': 'AAA',
                'requestor_id': 'RRR',
                'URL': 'http://this.is/test/',
                'version': 4,
             }
        ]
        Platform.objects.create(short_name='XXX', name='XXXX', ext_id=10)
        stats = import_sushi_credentials(data)
        assert SushiCredentials.objects.count() == 1
        credentials = SushiCredentials.objects.get()
        assert credentials.version == data[0]['version']
        assert credentials.url == data[0]['URL']
        assert credentials.organization == organizations[0]
        assert stats['added'] == 1

