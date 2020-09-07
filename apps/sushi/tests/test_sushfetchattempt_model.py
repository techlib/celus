import pytest
from core.models import UL_ORG_ADMIN
from django.core.files.base import ContentFile
from django.conf import settings
from django.utils import timezone
from freezegun import freeze_time
from organizations.models import Organization
from publications.models import Platform
from sushi.models import SushiCredentials, SushiFetchAttempt
from test_fixtures.entities.fetchattempts import FetchAttemptFactory
from test_fixtures.entities.platforms import PlatformFactory
from test_fixtures.entities.organizations import OrganizationFactory
from test_fixtures.entities.credentials import CredentialsFactory
from test_fixtures.scenarios.basic import (
    credentials,
    data_sources,
    organizations,
    report_types,
    platforms,
    counter_report_types,
)


@pytest.mark.django_db
class TestFileName:
    """ Test class for checking whether setting the file name
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

        organization = OrganizationFactory(internal_id=internal_id,)
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
            credentials_version_hash=credentials.compute_version_hash(),
        )

        assert fetch_attempt.data_file.name.startswith(
            f"counter/{internal_id or organization.pk}/{platform_name}/"
            f"{counter_report_type.counter_version}_{counter_report_type.code.upper()}"
        )


@pytest.mark.django_db
class TestSushiFetchAttemptModelManager:
    def test_custom_manager_methods_exist(self):
        """
        Test that custom manager methods exist at all
        """
        SushiFetchAttempt.objects.all()
        SushiFetchAttempt.objects.current()
        SushiFetchAttempt.objects.current_or_successful()
        SushiFetchAttempt.objects.last_queued()

    def test_custom_manager_methods_exist_on_queryset(self):
        """
        Test that custom manager methods are also available on querysets for SushiFetchAttempts
        """
        SushiFetchAttempt.objects.filter(download_success=True).current()
        SushiFetchAttempt.objects.filter(download_success=True).current_or_successful()
        SushiFetchAttempt.objects.filter(download_success=True).last_queued()

    def test_last_queued(self, credentials, counter_report_types):
        fa1 = SushiFetchAttempt.objects.create(
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
            start_date='2020-01-01',
            end_date='2020-01-31',
        )

        fa2 = SushiFetchAttempt.objects.create(
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
            start_date='2020-01-01',
            end_date='2020-01-31',
            queue_previous=fa1,
        )

        fa3 = SushiFetchAttempt.objects.create(
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
            start_date='2020-01-01',
            end_date='2020-01-31',
            queue_previous=fa2,
        )

        fa4 = SushiFetchAttempt.objects.create(
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
            start_date='2020-01-01',
            end_date='2020-01-31',
        )

        assert SushiFetchAttempt.objects.last_queued().count() == 2
        assert {fa4.pk, fa3.pk} == set(
            SushiFetchAttempt.objects.last_queued().values_list('pk', flat=True)
        )


@pytest.mark.django_db
class TestSushiFetchAttemptModel:
    def test_conflicting_fully_enclosing(self, credentials, counter_report_types):
        fa = SushiFetchAttempt.objects.create(
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
            start_date='2020-01-01',
            end_date='2020-01-31',
        )
        assert fa.conflicting(fully_enclosing=True).count() == 0, 'no conflicts'
        fa2 = SushiFetchAttempt.objects.create(
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
        fa = SushiFetchAttempt.objects.create(
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
            start_date='2020-01-01',
            end_date='2020-01-31',
        )
        # fully_enclosing is False by default, so no need to specify it
        assert fa.conflicting().count() == 0, 'no conflicts'
        fa2 = SushiFetchAttempt.objects.create(
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
            start_date='2020-01-01',
            end_date='2020-03-31',
        )
        assert fa.conflicting().count() == 1, 'one conflict'
        # results should be symmetrical - fa conflicts with fa2, fa2 conflicts with fa
        assert fa.conflicting().get().pk == fa2.pk
        assert fa2.conflicting().get().pk == fa.pk

    @pytest.mark.parametrize(
        ('end_date', 'timestamp', 'is_fetched_near_end_date'),
        (
            ('2020-01-01', '2020-02-14 23:59:59', True),  # within 15 days
            ('2020-01-01', '2020-02-15 00:00:00', False),  # after 15 days
        ),
    )
    def test_fetched_near_end_date(self, end_date, timestamp, is_fetched_near_end_date):
        with freeze_time(timestamp):
            attempt = FetchAttemptFactory(end_date=end_date,)

        attempt.refresh_from_db()  # will convert strings to datetimes

        assert attempt.is_fetched_near_end_date is is_fetched_near_end_date
        assert (
            SushiFetchAttempt.objects.fetched_near_end_date().exists() is is_fetched_near_end_date
        )

    @pytest.mark.parametrize(
        ("end_date", "timestamp", "scheduled_time", "prev_count"),
        (
            (
                "2019-12-31",
                "2020-01-01 12:00:00+0000",
                None,
                settings.QUEUED_SUSHI_MAX_RETRY_COUNT + 1,
            ),
            # start of the month
            ("2019-12-31", "2020-01-01 00:00:00+0000", "2020-01-08 00:00:00+0000", 0),
            ("2019-11-30", "2020-01-01 00:00:00+0000", "2020-01-08 00:00:00+0000", 0),
            ("2020-01-31", "2020-01-01 00:00:00+0000", "2020-01-08 00:00:00+0000", 0),
            # within few dates
            ("2019-12-31", "2020-01-05 00:00:00+0000", "2020-01-12 00:00:00+0000", 0),
            ("2019-11-30", "2020-01-05 00:00:00+0000", "2020-01-12 00:00:00+0000", 0),
            ("2020-01-31", "2020-01-05 00:00:00+0000", "2020-01-12 00:00:00+0000", 0),
            # in the middle
            ("2019-12-31", "2020-01-15 00:00:00+0000", "2020-01-22 00:00:00+0000", 0),
            ("2019-11-30", "2020-01-15 00:00:00+0000", "2020-01-22 00:00:00+0000", 0),
            ("2020-01-31", "2020-01-15 00:00:00+0000", "2020-01-22 00:00:00+0000", 0),
            # at the end of the month
            ("2019-12-31", "2020-01-31 00:00:00+0000", "2020-02-07 00:00:00+0000", 0),
            ("2019-11-30", "2020-01-31 00:00:00+0000", "2020-02-07 00:00:00+0000", 0),
            ("2020-01-31", "2020-01-31 00:00:00+0000", "2020-02-07 00:00:00+0000", 0),
            # iterate through counts ready
            ("2019-12-31", "2020-01-01 00:00:00+0000", "2020-01-15 00:00:00+0000", 1),
            ("2019-12-31", "2020-01-01 00:00:00+0000", "2020-01-29 00:00:00+0000", 2),
            ("2019-12-31", "2020-01-01 00:00:00+0000", "2020-02-26 00:00:00+0000", 3),
            ("2019-12-31", "2020-01-01 00:00:00+0000", "2020-04-22 00:00:00+0000", 4),
            ("2019-12-31", "2020-01-01 00:00:00+0000", "2020-08-12 00:00:00+0000", 5),
            # iterate through counts noready
            ("2020-01-31", "2020-01-05 00:00:00+0000", "2020-01-19 00:00:00+0000", 1),
            ("2020-01-31", "2020-01-05 00:00:00+0000", "2020-02-02 00:00:00+0000", 2),
            ("2020-01-31", "2020-01-05 00:00:00+0000", "2020-03-01 00:00:00+0000", 3),
            ("2020-01-31", "2020-01-05 00:00:00+0000", "2020-04-26 00:00:00+0000", 4),
            ("2020-01-31", "2020-01-05 00:00:00+0000", "2020-08-16 00:00:00+0000", 5),
        ),
    )
    def test_when_to_retry(self, end_date, timestamp, scheduled_time, prev_count):
        with freeze_time(timestamp):
            attempt = FetchAttemptFactory(
                end_date=end_date,
                when_queued=timestamp,
                error_code="3031",
                processing_success=True,
            )
            attempt.refresh_from_db()
            for _ in range(prev_count):
                attempt = FetchAttemptFactory(
                    credentials=attempt.credentials,
                    counter_report=attempt.counter_report,
                    end_date=end_date,
                    when_queued=timestamp,
                    error_code="3031",
                    processing_success=True,
                    queue_previous=attempt,
                )

            attempt.refresh_from_db()
            if scheduled_time:
                assert attempt.when_to_retry().strftime("%Y-%m-%d %H:%M:%S%z") == scheduled_time
            else:
                assert attempt.when_to_retry() is None
