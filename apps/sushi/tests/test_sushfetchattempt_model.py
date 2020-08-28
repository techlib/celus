import pytest
from core.models import UL_ORG_ADMIN
from django.core.files.base import ContentFile
from freezegun import freeze_time
from organizations.models import Organization
from publications.models import Platform
from sushi.models import SushiCredentials, SushiFetchAttempt
from test_fixtures.entities.fetchattempts import FetchAttemptFactory


@pytest.mark.django_db
class TestFileName:
    """ Test class for checking whether setting the file name
        work as expected
    """

    @pytest.mark.parametrize(
        ('internal_id', 'platform_name', 'version', 'code', 'ext'),
        (
            ('internal1', 'platform_1', 5, 'TR', 'json'),
            (None, 'platform_2', 5, 'TR', 'json'),
            (None, 'platform_1', 4, 'JR1', 'tsv'),
            ('internal2', 'platform_1', 4, 'JR1', 'tsv'),
        ),
    )
    def test_file_name(
        self, counter_report_type_named, internal_id, platform_name, version, code, ext,
    ):
        counter_report_type = counter_report_type_named(code, version)
        platform = Platform.objects.create(short_name=platform_name, name=platform_name, ext_id=10)

        organization = Organization.objects.create(
            # ext_id=1,
            # parent=None,
            internal_id=internal_id,
            # ico='123',
            # name_cs='AAA',
            # name_en='AAA',
            # short_name='AA',
        )

        credentials = SushiCredentials.objects.create(
            organization=organization,
            platform=platform,
            counter_version=version,
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
            f"counter/{internal_id or organization.pk}/{ platform_name }/{ version }_{code}"
        )


@pytest.mark.django_db
class TestSushiFetchAttemptModelManager(object):
    def test_custom_manager_methods_exist(self):
        """
        Test that custom manager methods exist at all
        """
        SushiFetchAttempt.objects.all()
        SushiFetchAttempt.objects.current()
        SushiFetchAttempt.objects.current_or_successful()

    def test_custom_manager_methods_exist_on_queryset(self):
        """
        Test that custom manager methods are also available on querysets for SushiFetchAttempts
        """
        SushiFetchAttempt.objects.filter(download_success=True).current()
        SushiFetchAttempt.objects.filter(download_success=True).current_or_successful()


@pytest.mark.django_db
class TestSushiFetchAttemptModel(object):
    def test_conflicting_fully_enclosing(self, credentials, counter_report_type):
        fa = SushiFetchAttempt.objects.create(
            credentials=credentials,
            counter_report=counter_report_type,
            start_date='2020-01-01',
            end_date='2020-01-31',
        )
        assert fa.conflicting(fully_enclosing=True).count() == 0, 'no conflicts'
        fa2 = SushiFetchAttempt.objects.create(
            credentials=credentials,
            counter_report=counter_report_type,
            start_date='2020-01-01',
            end_date='2020-03-31',
        )
        assert fa.conflicting(fully_enclosing=True).count() == 1, 'one conflict'
        # results do not have to be symmetrical because of different date ranges
        assert fa.conflicting(fully_enclosing=True).get().pk == fa2.pk
        assert fa2.conflicting(fully_enclosing=True).count() == 0

    def test_conflicting_not_fully_enclosing(self, credentials, counter_report_type):
        fa = SushiFetchAttempt.objects.create(
            credentials=credentials,
            counter_report=counter_report_type,
            start_date='2020-01-01',
            end_date='2020-01-31',
        )
        # fully_enclosing is False by default, so no need to specify it
        assert fa.conflicting().count() == 0, 'no conflicts'
        fa2 = SushiFetchAttempt.objects.create(
            credentials=credentials,
            counter_report=counter_report_type,
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
