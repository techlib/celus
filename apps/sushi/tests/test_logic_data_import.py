import pytest
from core.models import DataSource
from organizations.tests.conftest import organizations  # noqa - fixture
from publications.models import Platform
from sushi.logic.data_import import import_sushi_credentials

from test_fixtures.entities.platforms import PlatformFactory

from ..models import SushiCredentials


@pytest.mark.django_db
class TestLogicDataImport:
    def test_sushi_import(self, organizations):
        assert SushiCredentials.objects.count() == 0
        data = [
            {
                'platform': 'XXX',
                'organization': organizations[0].internal_id,
                'customer_id': 'AAA',
                'requestor_id': 'RRR',
                'URL': 'http://this.is/test/',
                'version': 4,
            },
            {
                'platform': 'XXX',
                'organization': organizations[1].internal_id,
                'customer_id': 'BBB',
                'requestor_id': 'RRRX',
                'URL': 'http://this.is/test/2',
                'version': 5,
                'extra_attrs': f'auth=un,pass;api_key={"key" * 100};foo=bar',
            },
        ]
        Platform.objects.create(short_name='XXX', name='XXXX', ext_id=10)
        stats = import_sushi_credentials(data)
        assert stats['added'] == 2
        assert SushiCredentials.objects.count() == 2
        credentials = SushiCredentials.objects.all().order_by('pk')
        # check individual objects
        cr1 = credentials[0]
        assert cr1.counter_version == data[0]['version']
        assert cr1.url == data[0]['URL']
        assert cr1.organization == organizations[0]
        cr2 = credentials[1]
        assert cr2.counter_version == data[1]['version']
        assert cr2.url == data[1]['URL']
        assert cr2.organization == organizations[1]
        assert cr2.http_username == 'un'
        assert cr2.http_password == 'pass'
        assert cr2.api_key == 'key' * 100
        assert cr2.extra_params == {'foo': 'bar'}
        # retry
        stats = import_sushi_credentials(data)
        assert stats['skipped'] == 2
        assert SushiCredentials.objects.count() == 2

    def test_sushi_reimport(self, organizations):
        assert SushiCredentials.objects.count() == 0
        data = [
            {
                'platform': 'XXX',
                'organization': organizations[0].internal_id,
                'customer_id': 'AAA',
                'requestor_id': 'RRR',
                'URL': 'http://this.is/test/',
                'version': 4,
            },
            {
                'platform': 'XXX',
                'organization': organizations[1].internal_id,
                'customer_id': 'BBB',
                'requestor_id': 'RRRX',
                'URL': 'http://this.is/test/2',
                'version': 5,
                'extra_attrs': 'auth=un,pass;api_key=kekekeyyy;foo=bar',
            },
        ]
        Platform.objects.create(short_name='XXX', name='XXXX', ext_id=10)
        stats = import_sushi_credentials(data)
        assert stats['added'] == 2
        assert SushiCredentials.objects.count() == 2
        # retry
        data[1]['URL'] = 'http://new.url/'
        data[1]['extra_attrs'] = 'api_key=kekekeyyy;foo=bar'
        stats = import_sushi_credentials(data)
        assert stats['skipped'] == 1
        assert stats['synced'] == 1
        assert SushiCredentials.objects.count() == 2
        credentials = SushiCredentials.objects.get(url='http://new.url/')
        assert credentials.http_password == ''
        assert credentials.http_username == ''

    @pytest.mark.parametrize('organization_idx', [0, 1])
    def test_sushi_import_with_custom_platforms(self, organizations, organization_idx):
        assert SushiCredentials.objects.count() == 0
        pl_global = PlatformFactory.create(short_name='pl-global', ext_id=10)
        s1, _ = DataSource.objects.get_or_create(
            short_name='s1', organization=organizations[0], type=DataSource.TYPE_ORGANIZATION
        )
        s2, _ = DataSource.objects.get_or_create(
            short_name='s2', organization=organizations[1], type=DataSource.TYPE_ORGANIZATION
        )
        pl_org1 = PlatformFactory.create(short_name='pl-org1', source=s1, ext_id=11)
        pl_org2 = PlatformFactory.create(short_name='pl-org2', source=s2, ext_id=12)
        data = [
            {
                'platform': pl_global.short_name,
                'organization': organizations[organization_idx].internal_id,
                'customer_id': 'AAA',
                'requestor_id': 'RRR',
                'URL': 'http://this.is/test/',
                'version': 4,
            },
            {
                'platform': pl_org1.short_name,
                'organization': organizations[organization_idx].internal_id,
                'customer_id': 'BBB',
                'requestor_id': 'RRRX',
                'URL': 'http://this.is/test/2',
                'version': 5,
            },
            {
                'platform': pl_org2.short_name,
                'organization': organizations[organization_idx].internal_id,
                'customer_id': 'BBB',
                'requestor_id': 'RRRX',
                'URL': 'http://this.is/test/2',
                'version': 5,
            },
        ]
        stats = import_sushi_credentials(data)
        assert stats['added'] == 2, 'one global and one for org specific platform'
        assert stats['error'] == 1, 'one org specific platform not matching'
        assert SushiCredentials.objects.count() == 2, 'one global and one for org specific platform'
        used_pl_names = [sc.platform.short_name for sc in SushiCredentials.objects.all()]
        used_pl_names.sort()
        if organization_idx == 0:
            assert used_pl_names == ['pl-global', 'pl-org1']
        else:
            assert used_pl_names == ['pl-global', 'pl-org2']
