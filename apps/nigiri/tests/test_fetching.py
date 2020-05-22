from copy import deepcopy

import pytest

from nigiri.counter5 import Counter5ReportBase
from organizations.tests.conftest import organizations
from logs.tests.conftest import report_type_nd

from nigiri.client import Sushi5Client
from publications.models import Platform
from sushi.logic.data_import import import_sushi_credentials
from sushi.models import SushiCredentials, CounterReportType, SushiFetchAttempt


@pytest.mark.django_db
class TestURLComposition(object):
    def test_extra_params_is_not_polluted_by_extra_data(self, organizations, report_type_nd):
        assert SushiCredentials.objects.count() == 0
        data = [
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
        assert stats['added'] == 1
        assert SushiCredentials.objects.count() == 1
        credentials = SushiCredentials.objects.all()
        # let's create
        cr1 = credentials[0]
        cr1.create_sushi_client()
        report = CounterReportType.objects.create(
            code='tr', name='tr', counter_version=5, report_type=report_type_nd(0)
        )
        orig_params = deepcopy(Sushi5Client.EXTRA_PARAMS)

        def mock_get_report_data(*args, **kwargs):
            return Counter5ReportBase()

        Sushi5Client.get_report_data = mock_get_report_data
        cr1.fetch_report(report, start_date='2020-01-01', end_date='2020-01-31')
        assert orig_params == Sushi5Client.EXTRA_PARAMS


@pytest.mark.django_db
class TestCredentialsVersioning(object):
    def test_version_hash_changes(self, organizations):
        """
        Tests that computation of version_hash from `SushiCredentials` can really distinguish
        between different versions of the same object
        """
        data = [
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
        import_sushi_credentials(data)
        assert SushiCredentials.objects.count() == 1
        cr1 = SushiCredentials.objects.get()
        hash1 = cr1.version_hash()
        cr1.requestor_id = 'new_id'
        hash2 = cr1.version_hash()
        assert hash2 != hash1
        cr1.api_key = 'new_api_key'
        assert cr1.version_hash() != hash1
        assert cr1.version_hash() != hash2
        print(hash1, hash2)

    def test_version_hash_does_not_change(self, organizations):
        """
        Tests that value of version_hash from `SushiCredentials` does not change when some
        unrelated changes are made
        """
        data = [
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
        import_sushi_credentials(data)
        assert SushiCredentials.objects.count() == 1
        cr1 = SushiCredentials.objects.get()
        hash1 = cr1.version_hash()
        cr1.last_updated_by = None
        cr1.outside_consortium = True
        cr1.save()
        assert cr1.version_hash() == hash1

    def test_version_info_is_stored_in_fetch_attempt(self, organizations, report_type_nd):
        """
        Tests that when we fetch data using `SushiCredentials`, the `SushiFetchAttempt` that is
        created contains information about the credentials version - both in `processing_info`
        and in `credentials_version_hash`
        """
        data = [
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
        import_sushi_credentials(data)
        assert SushiCredentials.objects.count() == 1
        cr1 = SushiCredentials.objects.get()
        cr1.create_sushi_client()
        report = CounterReportType.objects.create(
            code='tr', name='tr', counter_version=5, report_type=report_type_nd(0)
        )

        def mock_get_report_data(*args, **kwargs):
            return Counter5ReportBase()

        Sushi5Client.get_report_data = mock_get_report_data
        attempt: SushiFetchAttempt = cr1.fetch_report(
            report, start_date='2020-01-01', end_date='2020-01-31'
        )
        assert 'credentials_version' in attempt.processing_info
        assert attempt.credentials_version_hash != ''
        assert attempt.credentials_version_hash == cr1.version_hash()
