from datetime import timedelta
from pathlib import Path

import pytest
from celus_nigiri.error_codes import ErrorCode
from core.models import UL_ORG_ADMIN
from django.core.files.base import ContentFile
from django.utils import timezone
from freezegun import freeze_time
from sushi.models import AttemptStatus
from sushi.models import BrokenCredentialsMixin as BC
from sushi.models import CounterReportsToCredentials, SushiFetchAttempt

from test_fixtures.entities.credentials import CredentialsFactory
from test_fixtures.entities.fetchattempts import FetchAttemptFactory
from test_fixtures.entities.logs import ImportBatchFactory
from test_fixtures.entities.organizations import OrganizationFactory
from test_fixtures.entities.platforms import PlatformFactory
from test_fixtures.scenarios.basic import (  # noqa - fixtures
    counter_report_types,
    credentials,
    data_sources,
    organizations,
    platforms,
    report_types,
)


@pytest.mark.django_db
class TestFileName:
    """Test class for checking whether setting the file name
    work as expected
    """

    @pytest.mark.parametrize(
        ('internal_id', 'platform_name', 'code', 'ext'),
        (
            ('internal1', 'platform_1', 'tr', 'json'),
            (None, 'platform_2', 'tr', 'json'),
            (None, 'platform_1', 'jr1', 'tsv'),
            ('internal2', 'platform_1', 'jr1', 'tsv'),
        ),
    )
    def test_file_name(self, internal_id, platform_name, code, ext, counter_report_types):
        platform = PlatformFactory(short_name=platform_name, name=platform_name)

        organization = OrganizationFactory(internal_id=internal_id)
        counter_report_type = counter_report_types[code]

        credentials = CredentialsFactory(
            organization=organization,
            platform=platform,
            counter_version=counter_report_type.counter_version,
            lock_level=UL_ORG_ADMIN,
            url='http://a.b.c/',
        )

        data_file = ContentFile("b")
        data_file.name = f"report.{ext}"

        fetch_attempt = SushiFetchAttempt.objects.create(
            credentials=credentials,
            counter_report=counter_report_type,
            start_date="2020-01-01",
            end_date="2020-02-01",
            data_file=data_file,
            checksum='foo',
            file_size=1,
            credentials_version_hash=credentials.compute_version_hash(),
        )

        assert fetch_attempt.data_file.name.startswith(
            f"counter/{internal_id or organization.pk}/{platform_name}/"
            f"{counter_report_type.counter_version}_{counter_report_type.code.upper()}"
        )


@pytest.mark.django_db
class TestSushiFetchAttemptModel:
    def test_conflicting_fully_enclosing(self, credentials, counter_report_types):
        fa = FetchAttemptFactory.create(
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
            start_date='2020-01-01',
            end_date='2020-01-31',
        )
        assert fa.conflicting(fully_enclosing=True).count() == 0, 'no conflicts'
        fa2 = FetchAttemptFactory.create(
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
            start_date='2020-01-01',
            end_date='2020-03-31',
        )
        assert fa.conflicting(fully_enclosing=True).count() == 1, 'one conflict'
        # results do not have to be symmetrical because of different date ranges
        assert fa.conflicting(fully_enclosing=True).get().pk == fa2.pk
        assert fa2.conflicting(fully_enclosing=True).count() == 0

    def test_conflicting_not_fully_enclosing(self, credentials, counter_report_types):
        fa = FetchAttemptFactory.create(
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
            start_date='2020-01-01',
            end_date='2020-01-31',
        )
        # fully_enclosing is False by default, so no need to specify it
        assert fa.conflicting().count() == 0, 'no conflicts'
        fa2 = FetchAttemptFactory.create(
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
            start_date='2020-01-01',
            end_date='2020-03-31',
        )
        assert fa.conflicting().count() == 1, 'one conflict'
        # results should be symmetrical - fa conflicts with fa2, fa2 conflicts with fa
        assert fa.conflicting().get().pk == fa2.pk
        assert fa2.conflicting().get().pk == fa.pk

    def test_any_success_lately(self, credentials, counter_report_types):
        now = timezone.now()

        with freeze_time(now):
            # add unsuccessful attempt which happened right now
            attempt = FetchAttemptFactory(
                credentials=credentials["standalone_tr"],
                end_date="2020-01-31",
                when_processed=now,
                status=AttemptStatus.DOWNLOAD_FAILED,
                counter_report=counter_report_types["tr"],
            )
            assert attempt.any_success_lately() is False

            # add unsuccessful in lately period
            attempt = FetchAttemptFactory(
                credentials=credentials["standalone_tr"],
                end_date="2020-01-31",
                when_processed=now - timedelta(days=5),
                status=AttemptStatus.DOWNLOAD_FAILED,
                counter_report=counter_report_types["tr"],
            )
            assert attempt.any_success_lately() is False

            # successful after lately period
            attempt = FetchAttemptFactory(
                credentials=credentials["standalone_tr"],
                end_date="2020-01-31",
                when_processed=now - timedelta(days=16),
                status=AttemptStatus.SUCCESS,
                counter_report=counter_report_types["tr"],
            )
            assert attempt.any_success_lately() is False

            # successful in lately period
            attempt = FetchAttemptFactory(
                credentials=credentials["standalone_tr"],
                end_date="2020-01-31",
                when_processed=now - timedelta(days=15),
                status=AttemptStatus.SUCCESS,
                counter_report=counter_report_types["tr"],
            )
            assert attempt.any_success_lately() is True

    def test_any_import_batch_lately(self, credentials, counter_report_types):
        now = timezone.now()

        with freeze_time(now):
            # add unsuccessful attempt which happened right now
            attempt = FetchAttemptFactory(
                credentials=credentials["standalone_tr"],
                end_date="2020-01-31",
                when_processed=now,
                status=AttemptStatus.SUCCESS,
                counter_report=counter_report_types["tr"],
            )
            assert attempt.any_import_batch_lately() is False

            # add unsuccessful in lately period
            attempt = FetchAttemptFactory(
                credentials=credentials["standalone_tr"],
                end_date="2020-01-31",
                when_processed=now - timedelta(days=5),
                status=AttemptStatus.SUCCESS,
                counter_report=counter_report_types["tr"],
            )
            assert attempt.any_import_batch_lately() is False

            # successful after lately period
            attempt = FetchAttemptFactory(
                credentials=credentials["standalone_tr"],
                end_date="2020-01-31",
                when_processed=now - timedelta(days=91),
                status=AttemptStatus.SUCCESS,
                counter_report=counter_report_types["tr"],
                import_batch=ImportBatchFactory(report_type=counter_report_types["tr"].report_type),
            )
            assert attempt.any_import_batch_lately() is False

            # successful in lately period
            attempt = FetchAttemptFactory(
                credentials=credentials["standalone_tr"],
                end_date="2020-01-31",
                when_processed=now - timedelta(days=90),
                status=AttemptStatus.SUCCESS,
                counter_report=counter_report_types["tr"],
                import_batch=ImportBatchFactory(report_type=counter_report_types["tr"].report_type),
            )
            assert attempt.any_import_batch_lately() is True

    def test_broken_credentials(self, credentials, counter_report_types):
        attempt = FetchAttemptFactory(
            credentials=credentials["standalone_tr"],
            end_date="2020-01-31",
            status=AttemptStatus.SUCCESS,
            counter_report=counter_report_types["tr"],
            import_batch=ImportBatchFactory(report_type=counter_report_types["tr"].report_type),
        )
        assert attempt.broken_credentials is False
        credentials["standalone_tr"].set_broken(FetchAttemptFactory(), 'http')
        assert attempt.broken_credentials is True

        attempt = FetchAttemptFactory(
            credentials=credentials["branch_pr"],
            end_date="2020-01-31",
            status=AttemptStatus.SUCCESS,
            counter_report=counter_report_types["pr"],
            import_batch=ImportBatchFactory(report_type=counter_report_types["tr"].report_type),
        )
        assert attempt.broken_credentials is False
        CounterReportsToCredentials.objects.get(
            counter_report=counter_report_types["pr"], credentials=credentials["branch_pr"]
        ).set_broken(FetchAttemptFactory(), 'sushi')
        assert attempt.broken_credentials is True

    @pytest.mark.parametrize(
        "status,http_status,sushi_status,lately,broken_credentials,broken_cr2c",
        (
            ("NO_DATA", 400, ErrorCode.INVALID_API_KEY, False, None, None),
            ("SUCCESS", 401, ErrorCode.REPORT_NOT_SUPPORTED, False, None, None),
            ("QUEUED", 400, ErrorCode.NOT_AUTHORIZED, False, None, None),
            ("NO_DATA", 400, ErrorCode.NOT_AUTHORIZED_INSTITUTION, False, None, None),
            ("SUCCESS", 400, ErrorCode.INVALID_API_KEY, False, None, None),
            ("NO_DATA", 400, ErrorCode.INSUFFICIENT_DATA, False, None, None),
            # cred broken testing
            ("FAILURE", 401, ErrorCode.TOO_MANY_REQUESTS, False, BC.BROKEN_HTTP, None),
            ("FAILURE", 403, ErrorCode.TOO_MANY_REQUESTS, False, BC.BROKEN_HTTP, None),
            ("FAILURE", 500, ErrorCode.TOO_MANY_REQUESTS, False, BC.BROKEN_HTTP, None),
            ("FAILURE", 400, ErrorCode.TOO_MANY_REQUESTS, False, BC.BROKEN_HTTP, None),
            ("FAILURE", 500, ErrorCode.TOO_MANY_REQUESTS, True, None, None),
            ("FAILURE", 400, ErrorCode.TOO_MANY_REQUESTS, True, None, None),
            ("FAILURE", 200, ErrorCode.NOT_AUTHORIZED, False, BC.BROKEN_SUSHI, None),
            ("FAILURE", 200, ErrorCode.INVALID_API_KEY, False, BC.BROKEN_SUSHI, None),
            ("FAILURE", 200, ErrorCode.NOT_AUTHORIZED_INSTITUTION, False, BC.BROKEN_SUSHI, None),
            ("FAILURE", 200, ErrorCode.INSUFFICIENT_DATA, False, BC.BROKEN_SUSHI, None),
            # cred to report type testing
            ("FAILURE", 404, ErrorCode.TOO_MANY_REQUESTS, False, None, BC.BROKEN_HTTP),
            ("FAILURE", 200, ErrorCode.REPORT_NOT_SUPPORTED, False, None, BC.BROKEN_SUSHI),
            ("FAILURE", 200, ErrorCode.REPORT_VERSION_NOT_SUPPORTED, False, None, BC.BROKEN_SUSHI),
            ("FAILURE", 400, ErrorCode.INVALID_REPORT_FILTER, False, BC.BROKEN_HTTP, None),
        ),
    )
    def test_update_broken(
        self,
        status,
        http_status,
        sushi_status,
        lately,
        broken_credentials,
        broken_cr2c,
        credentials,
        counter_report_types,
    ):
        creds = credentials["standalone_br1_jr1"]
        assert creds.broken is None
        assert creds.first_broken_attempt is None

        cr2c = CounterReportsToCredentials.objects.get(
            counter_report=counter_report_types["br1"], credentials=creds
        )
        assert cr2c.broken is None
        assert cr2c.first_broken_attempt is None

        # Different credentials
        FetchAttemptFactory(
            credentials=credentials["standalone_tr"],
            end_date="2020-01-31",
            when_processed=timezone.now() - timedelta(days=1),
            status=AttemptStatus.SUCCESS,
            counter_report=counter_report_types["jr1"],
        )

        if lately:
            FetchAttemptFactory(
                credentials=creds,
                end_date="2020-01-31",
                when_processed=timezone.now() - timedelta(days=1),
                status=AttemptStatus.SUCCESS,
                counter_report=counter_report_types["br1"],
                http_status_code=200,
            )

        if status == 'SUCCESS':
            status = AttemptStatus.SUCCESS
        elif status == 'NO_DATA':
            status = AttemptStatus.NO_DATA
        elif status == 'QUEUED':
            status = AttemptStatus.DOWNLOADING
        elif status == 'FAILURE':
            status = AttemptStatus.DOWNLOAD_FAILED
        else:
            raise NotImplementedError()

        # First broken attempt
        attempt = FetchAttemptFactory(
            credentials=creds,
            end_date="2020-01-31",
            when_processed=timezone.now(),
            counter_report=counter_report_types["br1"],
            error_code=sushi_status.value,
            http_status_code=http_status,
            status=AttemptStatus.DOWNLOAD_FAILED
            if broken_credentials or broken_cr2c
            else AttemptStatus.SUCCESS,
        )
        attempt.update_broken()
        creds.refresh_from_db()
        cr2c.refresh_from_db()
        assert creds.broken == broken_credentials
        assert creds.first_broken_attempt == (attempt if broken_credentials else None)
        assert cr2c.broken == broken_cr2c
        assert cr2c.first_broken_attempt == (attempt if broken_cr2c else None)

        # Test whether first_broken_attempt is not overriden
        second_attempt = FetchAttemptFactory(
            credentials=creds,
            end_date="2020-01-31",
            when_processed=timezone.now(),
            counter_report=counter_report_types["br1"],
            error_code=sushi_status.value,
            http_status_code=http_status,
            status=status,
        )
        second_attempt.update_broken()
        creds.refresh_from_db()
        cr2c.refresh_from_db()
        assert creds.broken == broken_credentials
        assert creds.first_broken_attempt == (attempt if broken_credentials else None)
        assert cr2c.broken == broken_cr2c
        assert cr2c.first_broken_attempt == (attempt if broken_cr2c else None)

        # Change credentials hash => all will be unbroken
        creds.url += "/something/"
        creds.save()
        cr2c.refresh_from_db()
        assert creds.broken is None
        assert creds.first_broken_attempt is None
        assert cr2c.broken is None
        assert cr2c.first_broken_attempt is None

        # Rerun update broken should keep the creds and cr2c unbroken
        attempt.update_broken()
        creds.refresh_from_db()
        cr2c.refresh_from_db()
        assert creds.broken is None
        assert creds.first_broken_attempt is None
        assert cr2c.broken is None
        assert cr2c.first_broken_attempt is None

    @pytest.mark.parametrize('status', ('SUCCESS', 'NO_DATA', 'QUEUED', 'FAILURE'))
    def test_reextract_header_data(self, status, inmemory_media):
        """
        Tests that the FA object has a method for re-extracting header data from the stored
        file and that it does what it should do.
        """
        with (Path(__file__).parent / 'data/counter5/5_TR_ProQuestEbookCentral.json').open(
            'rb'
        ) as f:
            data_file = ContentFile(f.read())
            data_file.name = f"something.json"

        fa = FetchAttemptFactory.create(data_file=data_file, status=status)
        assert fa.extracted_data == {}
        fa.reextract_header_data()
        assert fa.extracted_data == {
            'Institution_Name': 'Hidden',
            'Institution_ID': [{"Type": "Proprietary", "Value": "EBC:hidden"}],
            'Created_By': 'ProQuest Ebook Central',
        }
