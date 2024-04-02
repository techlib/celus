import pytest
from celus_nigiri.client import Sushi5Client
from celus_nigiri.counter5 import Counter5ReportBase
from core.models import UL_CONS_ADMIN, UL_CONS_STAFF, UL_ORG_ADMIN, Identity
from core.tests.conftest import master_admin_identity, valid_identity  # noqa - fixtures
from django.utils import timezone
from logs.models import AccessLog, ImportBatch, Metric
from organizations.models import UserOrganization
from publications.fake_data import PlatformFactory
from publications.models import Platform
from publications.tests.conftest import platforms  # noqa - fixture
from rest_framework.exceptions import PermissionDenied

from sushi.fake_data import CredentialsFactory, FetchAttemptFactory
from sushi.logic.data_import import import_sushi_credentials_new
from sushi.models import AttemptStatus
from test_scenarios.basic import (  # noqa - fixtures
    counter_report_types,
    data_sources,
    organizations,
    report_types,
)

from ..models import CounterReportType, SushiCredentials, SushiFetchAttempt


@pytest.mark.django_db
class TestUrl:
    def test_knowledgebase_url(self):
        platform_no_knowledgebase = PlatformFactory(knowledgebase=None)
        platform_knowledgebase = PlatformFactory(
            knowledgebase={
                "providers": [
                    {
                        "counter_version": 5,
                        "provider": {
                            "url": "https://knowledgebase.example.com",
                        },
                    }
                ]
            }
        )

        assert (
            CredentialsFactory(
                platform=platform_knowledgebase,
                counter_version=5,
            ).knowledgebase_url
            == "https://knowledgebase.example.com"
        ), "Knowledgebase has appropriate url"
        assert (
            CredentialsFactory(
                platform=platform_knowledgebase,
                counter_version=4,
            ).knowledgebase_url
            is None
        ), "No C4 url in knowledgebase"
        assert (
            CredentialsFactory(
                platform=platform_no_knowledgebase,
                counter_version=5,
            ).knowledgebase_url
            is None
        ), "Platform doesn't have knowledgebase"

    @pytest.mark.parametrize(
        ["in_url", "out_url"],
        (
            ("https://example.com", "https://example.com"),
            ("https://example.com/", "https://example.com/"),
            ("https://example.com//", "https://example.com/"),
            ("https://example.com///path/", "https://example.com/path/"),
            ("https://example.com/path///sub//", "https://example.com/path/sub/"),
        ),
    )
    def test_url_normalization(self, in_url, out_url):
        cred = CredentialsFactory(
            url=in_url,
        )
        cred.url = in_url
        cred.save()
        cred.refresh_from_db()
        assert cred.url == out_url


@pytest.mark.django_db
class TestLocking:
    @pytest.mark.parametrize(
        ["user_code", "can_lock_super", "can_lock_staff", "can_lock_org_admin"],
        (
            ("org_admin", False, False, True),
            ("staff", False, True, True),
            ("superuser", True, True, True),
        ),
    )
    def test_can_lock_to_level_permissions(
        self,
        admin_user,
        master_admin_identity,
        valid_identity,
        organizations,
        platforms,
        user_code,
        can_lock_super,
        can_lock_org_admin,
        can_lock_staff,
    ):
        org = organizations["branch"]
        credentials = SushiCredentials.objects.create(
            organization=org, platform=platforms[0], counter_version=5
        )
        user = self._user_code_to_user(
            user_code, org, admin_user, master_admin_identity, valid_identity
        )
        self._test_change_lock(credentials, user, UL_ORG_ADMIN, can_lock_org_admin)
        credentials.lock_level = 0
        credentials.save()
        self._test_change_lock(credentials, user, UL_CONS_STAFF, can_lock_staff)
        credentials.lock_level = 0
        credentials.save()
        self._test_change_lock(credentials, user, UL_CONS_ADMIN, can_lock_super)

    @pytest.mark.parametrize(
        ["user_code", "can_unlock_super", "can_unlock_staff", "can_unlock_org_admin"],
        (
            ("org_admin", False, False, True),
            ("staff", False, True, True),
            ("superuser", True, True, True),
        ),
    )
    def test_can_unlock_from_level(
        self,
        admin_user,
        master_admin_identity,
        valid_identity,
        organizations,
        platforms,
        user_code,
        can_unlock_super,
        can_unlock_org_admin,
        can_unlock_staff,
    ):
        org = organizations["branch"]
        credentials = SushiCredentials.objects.create(
            organization=org, platform=platforms[0], counter_version=5, lock_level=UL_ORG_ADMIN
        )
        user = self._user_code_to_user(
            user_code, org, admin_user, master_admin_identity, valid_identity
        )
        self._test_change_lock(credentials, user, 0, can_unlock_org_admin)
        credentials.lock_level = UL_CONS_STAFF
        credentials.save()
        self._test_change_lock(credentials, user, 0, can_unlock_staff)
        credentials.lock_level = UL_CONS_ADMIN
        credentials.save()
        self._test_change_lock(credentials, user, 0, can_unlock_super)

    @classmethod
    def _user_code_to_user(
        cls, code: str, organization, admin_user, master_admin_identity, valid_identity
    ):
        if code == "org_admin":
            user = Identity.objects.get(identity=valid_identity).user
            UserOrganization.objects.create(user=user, organization=organization, is_admin=True)
            return user
        elif code == "superuser":
            return admin_user
        elif code == "staff":
            return Identity.objects.get(identity=master_admin_identity).user
        raise ValueError(f"wrong code {code}")

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
                "organization": organizations["empty"].internal_id,
                "publisher/vendor/platform": "XXXX",
                "requestor id": "RRRX",
                "customer id": "BBB",
                "api key": "kekekeyyy",
            }
        ]
        knowledgebase = {
            "providers": [{"counter_version": 5, "provider": {"url": "http://this.is/test/2"}}]
        }
        Platform.objects.create(
            short_name="XXX", name_en="XXXX", ext_id=10, knowledgebase=knowledgebase
        )
        import_sushi_credentials_new(data)
        assert SushiCredentials.objects.count() == 1
        cr1 = SushiCredentials.objects.get()
        assert cr1.version_hash != ""
        assert cr1.version_hash == cr1.compute_version_hash()
        old_hash = cr1.version_hash
        cr1.api_key = "new_api_key"
        assert cr1.compute_version_hash() != cr1.version_hash, "no change without a save"
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
                "organization": organizations["empty"].internal_id,
                "publisher/vendor/platform": "XXXX",
                "requestor id": "RRRX",
                "customer id": "BBB",
                "api key": "kekekeyyy",
            }
        ]
        knowledgebase = {
            "providers": [{"counter_version": 5, "provider": {"url": "http://this.is/test/2"}}]
        }
        Platform.objects.create(
            short_name="XXX", name_en="XXXX", ext_id=10, knowledgebase=knowledgebase
        )
        import_sushi_credentials_new(data)
        assert SushiCredentials.objects.count() == 1
        cr1 = SushiCredentials.objects.get()
        hash1 = cr1.compute_version_hash()
        cr1.requestor_id = "new_id"
        hash2 = cr1.compute_version_hash()
        assert hash2 != hash1
        cr1.api_key = "new_api_key"
        assert cr1.compute_version_hash() != hash1
        assert cr1.compute_version_hash() != hash2

    def test_version_hash_does_not_change(self, organizations):
        """
        Tests that value of version_hash from `SushiCredentials` does not change when some
        unrelated changes are made
        """
        data = [
            {
                "organization": organizations["empty"].internal_id,
                "publisher/vendor/platform": "XXXX",
                "requestor id": "RRRX",
                "customer id": "BBB",
                "api key": "kekekeyyy",
            }
        ]
        knowledgebase = {
            "providers": [{"counter_version": 5, "provider": {"url": "http://this.is/test/2"}}]
        }
        Platform.objects.create(
            short_name="XXX", name_en="XXXX", ext_id=10, knowledgebase=knowledgebase
        )
        import_sushi_credentials_new(data)
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
                "organization": organizations["empty"].internal_id,
                "publisher/vendor/platform": "XXXX",
                "requestor id": "RRRX",
                "customer id": "BBB",
                "api key": "kekekeyyy",
            }
        ]
        knowledgebase = {
            "providers": [{"counter_version": 5, "provider": {"url": "http://this.is/test/2"}}]
        }
        Platform.objects.create(
            short_name="XXX", name_en="XXXX", ext_id=10, knowledgebase=knowledgebase
        )
        import_sushi_credentials_new(data)
        assert SushiCredentials.objects.count() == 1
        cr1 = SushiCredentials.objects.get()
        cr1.create_sushi_client()
        report = CounterReportType.objects.create(
            code="tr", name="tr", counter_version=5, report_type=report_type_nd(0)
        )

        def mock_get_report_data(*args, **kwargs):
            return Counter5ReportBase()

        monkeypatch.setattr(Sushi5Client, "get_report_data", mock_get_report_data)
        attempt: SushiFetchAttempt = cr1.fetch_report(
            report, start_date="2020-01-01", end_date="2020-01-31"
        )
        assert "credentials_version" in attempt.processing_info
        assert attempt.credentials_version_hash != ""
        assert attempt.credentials_version_hash == cr1.version_hash


@pytest.mark.django_db
class TestCredentialsQuerySet:
    def test_force_current_version_verified(self):
        creds1 = CredentialsFactory()
        creds2 = CredentialsFactory()
        creds3 = CredentialsFactory()

        assert creds1.is_verified is False
        assert creds2.is_verified is False
        assert creds3.is_verified is False

        assert list(
            SushiCredentials.objects.annotate_verified()
            .order_by("pk")
            .values_list("verified", flat=True)
        ) == [False, False, False]

        FetchAttemptFactory(
            credentials=creds1,
            status=AttemptStatus.SUCCESS,
            credentials_version_hash=creds1.version_hash,
        )
        creds2.force_current_version_verified()

        # is verified is cached property, we need to recreate models from db
        creds1 = SushiCredentials.objects.get(pk=creds1.pk)
        creds2 = SushiCredentials.objects.get(pk=creds2.pk)
        creds3 = SushiCredentials.objects.get(pk=creds3.pk)

        assert creds1.is_verified is True, "First is verified by successful attempt"
        assert creds2.is_verified is True, "Second is forced verified"
        assert creds3.is_verified is False, "Third remained unverified"

        assert list(
            SushiCredentials.objects.annotate_verified()
            .order_by("pk")
            .values_list("verified", flat=True)
        ) == [True, True, False]

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
        assert cr1.is_verified is False
        assert SushiCredentials.objects.annotate_verified().get(pk=cr1.pk).verified is False

        # Successful download
        FetchAttemptFactory(
            credentials=cr1, status=AttemptStatus.SUCCESS, credentials_version_hash=cr1.version_hash
        )
        cr1 = SushiCredentials.objects.get(pk=cr1.pk)
        assert cr1.is_verified is True
        assert SushiCredentials.objects.annotate_verified().get(pk=cr1.pk).verified is True

        # after updating credentials, credentials should become unverified
        cr1.requestor_id += "X"
        cr1.save()
        cr1 = SushiCredentials.objects.get(pk=cr1.pk)
        assert cr1.is_verified is False
        assert SushiCredentials.objects.annotate_verified().get(pk=cr1.pk).verified is False

        # Download with no data
        FetchAttemptFactory(
            credentials=cr1, status=AttemptStatus.NO_DATA, credentials_version_hash=cr1.version_hash
        )
        cr1 = SushiCredentials.objects.get(pk=cr1.pk)
        assert cr1.is_verified is True
        assert SushiCredentials.objects.annotate_verified().get(pk=cr1.pk).verified is True

    def test_not_fake(self, report_types, counter_report_types, settings):
        settings.FAKE_SUSHI_URLS = ["https://fake.it", "https://skip.it"]
        # Real sushi url
        c1 = CredentialsFactory(url="https://real.sushi/")
        # Fake url
        CredentialsFactory(url="https://skip.it")
        # Fake url with path
        CredentialsFactory(url="https://fake.it/something")
        # Real sushi - protocol mismatch
        c2 = CredentialsFactory(url="http://fake.it")
        assert set(SushiCredentials.objects.all().not_fake()) == {c1, c2}
