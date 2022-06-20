import pytest
from core.models import UL_CONS_ADMIN, UL_CONS_STAFF, UL_ORG_ADMIN, Identity
from core.tests.conftest import master_identity, valid_identity
from django.utils import timezone
from logs.models import AccessLog, ImportBatch, Metric
from nigiri.client import Sushi4Client, Sushi5Client
from nigiri.counter4 import Counter4ReportBase
from nigiri.counter5 import Counter5ReportBase
from organizations.models import UserOrganization
from organizations.tests.conftest import organizations
from publications.models import Platform
from publications.tests.conftest import platforms
from pycounter.report import CounterReport
from rest_framework.exceptions import PermissionDenied
from sushi.logic.data_import import import_sushi_credentials
from sushi.models import AttemptStatus
from test_fixtures.entities.credentials import CredentialsFactory
from test_fixtures.entities.fetchattempts import FetchAttemptFactory
from test_fixtures.scenarios.basic import counter_report_types, report_types

from ..models import CounterReportType, SushiCredentials, SushiFetchAttempt


@pytest.mark.django_db
class TestLocking:
    @pytest.mark.parametrize(
        ['user_code', 'can_lock_super', 'can_lock_staff', 'can_lock_org_admin'],
        (
            ('org_admin', False, False, True),
            ('staff', False, True, True),
            ('superuser', True, True, True),
        ),
    )
    def test_can_lock_to_level_permissions(
        self,
        admin_user,
        master_identity,
        valid_identity,
        organizations,
        platforms,
        user_code,
        can_lock_super,
        can_lock_org_admin,
        can_lock_staff,
    ):

        org = organizations[0]
        credentials = SushiCredentials.objects.create(
            organization=org, platform=platforms[0], counter_version=5,
        )
        user = self._user_code_to_user(user_code, org, admin_user, master_identity, valid_identity)
        self._test_change_lock(credentials, user, UL_ORG_ADMIN, can_lock_org_admin)
        credentials.lock_level = 0
        credentials.save()
        self._test_change_lock(credentials, user, UL_CONS_STAFF, can_lock_staff)
        credentials.lock_level = 0
        credentials.save()
        self._test_change_lock(credentials, user, UL_CONS_ADMIN, can_lock_super)

    @pytest.mark.parametrize(
        ['user_code', 'can_unlock_super', 'can_unlock_staff', 'can_unlock_org_admin'],
        (
            ('org_admin', False, False, True),
            ('staff', False, True, True),
            ('superuser', True, True, True),
        ),
    )
    def test_can_unlock_from_level(
        self,
        admin_user,
        master_identity,
        valid_identity,
        organizations,
        platforms,
        user_code,
        can_unlock_super,
        can_unlock_org_admin,
        can_unlock_staff,
    ):
        org = organizations[0]
        credentials = SushiCredentials.objects.create(
            organization=org, platform=platforms[0], counter_version=5, lock_level=UL_ORG_ADMIN,
        )
        user = self._user_code_to_user(user_code, org, admin_user, master_identity, valid_identity)
        self._test_change_lock(credentials, user, 0, can_unlock_org_admin)
        credentials.lock_level = UL_CONS_STAFF
        credentials.save()
        self._test_change_lock(credentials, user, 0, can_unlock_staff)
        credentials.lock_level = UL_CONS_ADMIN
        credentials.save()
        self._test_change_lock(credentials, user, 0, can_unlock_super)

    @classmethod
    def _user_code_to_user(
        cls, code: str, organization, admin_user, master_identity, valid_identity
    ):
        if code == 'org_admin':
            user = Identity.objects.get(identity=valid_identity).user
            UserOrganization.objects.create(user=user, organization=organization, is_admin=True)
            return user
        elif code == 'superuser':
            return admin_user
        elif code == 'staff':
            return Identity.objects.get(identity=master_identity).user
        raise ValueError(f'wrong code {code}')

    @classmethod
    def _test_change_lock(cls, credentials, user, level, can):
        if can:
            credentials.change_lock(user, level)
            assert credentials.lock_level == level
        else:
            with pytest.raises(PermissionDenied):
                credentials.change_lock(user, level)


@pytest.mark.django_db
class TestCredentialsVersioning:
    def test_version_hash_is_stored(self, organizations):
        """
        Tests that version_hash is computed and store on save
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
        assert cr1.version_hash != ''
        assert cr1.version_hash == cr1.compute_version_hash()
        old_hash = cr1.version_hash
        cr1.api_key = 'new_api_key'
        assert cr1.compute_version_hash() != cr1.version_hash, 'no change without a save'
        cr1.save()
        assert cr1.compute_version_hash() == cr1.version_hash
        assert cr1.version_hash != old_hash

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
        hash1 = cr1.compute_version_hash()
        cr1.requestor_id = 'new_id'
        hash2 = cr1.compute_version_hash()
        assert hash2 != hash1
        cr1.api_key = 'new_api_key'
        assert cr1.compute_version_hash() != hash1
        assert cr1.compute_version_hash() != hash2

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
        hash1 = cr1.compute_version_hash()
        cr1.last_updated_by = None
        cr1.outside_consortium = True
        cr1.save()
        assert cr1.compute_version_hash() == hash1

    def test_version_info_is_stored_in_fetch_attempt(
        self, organizations, report_type_nd, monkeypatch
    ):
        """
        Tests that when we fetch data using `SushiCredentials`, the `SushiFetchAttempt` that is
        created contains information about the credentials version - both in `processing_info`
        and in `credentials_version_hash`.
        This version tests Counter 5
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

        monkeypatch.setattr(Sushi5Client, 'get_report_data', mock_get_report_data)
        attempt: SushiFetchAttempt = cr1.fetch_report(
            report, start_date='2020-01-01', end_date='2020-01-31'
        )
        assert 'credentials_version' in attempt.processing_info
        assert attempt.credentials_version_hash != ''
        assert attempt.credentials_version_hash == cr1.version_hash

    def test_version_info_is_stored_in_fetch_attempt_c4(
        self, organizations, report_type_nd, monkeypatch
    ):
        """
        Tests that when we fetch data using `SushiCredentials`, the `SushiFetchAttempt` that is
        created contains information about the credentials version - both in `processing_info`
        and in `credentials_version_hash`.
        This version tests Counter 4
        """
        data = [
            {
                'platform': 'XXX',
                'organization': organizations[1].internal_id,
                'customer_id': 'BBB',
                'requestor_id': 'RRRX',
                'URL': 'http://this.is/test/2',
                'version': 4,
                'extra_attrs': 'auth=un,pass;api_key=kekekeyyy;foo=bar',
            },
        ]
        Platform.objects.create(short_name='XXX', name='XXXX', ext_id=10)
        import_sushi_credentials(data)
        assert SushiCredentials.objects.count() == 1
        cr1 = SushiCredentials.objects.get()
        cr1.create_sushi_client()
        report = CounterReportType.objects.create(
            code='tr', name='tr', counter_version=4, report_type=report_type_nd(0)
        )

        def mock_get_report_data(*args, **kwargs):
            return CounterReport(report_type="JR1", perios=("2020-01-01", "2020-01-01"))

        monkeypatch.setattr(Sushi4Client, 'get_report_data', mock_get_report_data)
        attempt: SushiFetchAttempt = cr1.fetch_report(
            report, start_date='2020-01-01', end_date='2020-01-31'
        )
        assert 'credentials_version' in attempt.processing_info
        assert attempt.credentials_version_hash != ''
        assert attempt.credentials_version_hash == cr1.version_hash


@pytest.mark.django_db
class TestCredentialsQuerySet:
    def test_working(self, report_types, counter_report_types):
        # empty
        CredentialsFactory()

        # no data
        no_data = CredentialsFactory()
        FetchAttemptFactory(
            counter_report=counter_report_types["tr"],
            credentials=no_data,
            import_batch=ImportBatch.objects.create(
                report_type=report_types["tr"],
                organization=no_data.organization,
                platform=no_data.platform,
            ),
        )

        has_data = CredentialsFactory()
        ib_with_data = ImportBatch.objects.create(
            report_type=report_types["tr"],
            organization=no_data.organization,
            platform=no_data.platform,
        )
        metric = Metric.objects.create()
        AccessLog.objects.create(
            report_type=report_types["tr"],
            import_batch=ib_with_data,
            organization=no_data.organization,
            platform=no_data.platform,
            value=10,
            date=timezone.now().date(),
            metric=metric,
        )
        FetchAttemptFactory(
            import_batch=ib_with_data,
            credentials=has_data,
            counter_report=counter_report_types["tr"],
        )

        assert SushiCredentials.objects.all().working().count() == 1

    def test_verified(self, report_types, counter_report_types):

        # empty
        cr1 = CredentialsFactory()
        assert cr1.get_verified() is False
        SushiCredentials.objects.verified().filter(pk=cr1.pk).verified is False

        # Successful download
        FetchAttemptFactory(
            credentials=cr1, status=AttemptStatus.SUCCESS, credentials_version_hash=cr1.version_hash
        )
        assert cr1.get_verified() is True
        assert SushiCredentials.objects.verified().get(pk=cr1.pk).verified is True

        # after updating credentials credentials should become unverified
        cr1.requestor_id += "X"
        cr1.save()
        assert cr1.get_verified() is False
        assert SushiCredentials.objects.verified().get(pk=cr1.pk).verified is False

        # Download with no data
        FetchAttemptFactory(
            credentials=cr1, status=AttemptStatus.NO_DATA, credentials_version_hash=cr1.version_hash
        )
        assert cr1.get_verified() is True
        assert SushiCredentials.objects.verified().get(pk=cr1.pk).verified is True

    def test_not_fake(self, report_types, counter_report_types, settings):
        settings.FAKE_SUSHI_URLS = ['https://fake.it', 'https://skip.it']
        c1 = CredentialsFactory(url="https://real.sushi/")
        CredentialsFactory(url="https://skip.it")
        CredentialsFactory(url="https://fake.it/something")
        c2 = CredentialsFactory(url="http://fake.it")
        assert set(SushiCredentials.objects.all().not_fake()) == {c1, c2}
