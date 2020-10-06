from datetime import timedelta, date
from unittest.mock import patch

import pytest
from django.utils.timezone import now

from core.logic.dates import month_start, month_end
from core.models import UL_ORG_ADMIN
from nigiri.client import Sushi5Client, Sushi4Client
from nigiri.counter5 import Counter5ReportBase
from nigiri.counter4 import CounterReport
from nigiri.error_codes import ErrorCode
from publications.models import Platform
from ..logic.data_import import import_sushi_credentials
from ..logic.fetching import (
    months_to_cover,
    find_holes_in_data,
    retry_holes_with_new_credentials,
    create_fetch_units,
    FetchUnit,
    process_fetch_units,
    retry_queued,
)
from sushi.models import (
    CounterReportType,
    SushiCredentials,
    SushiFetchAttempt,
    CounterReportsToCredentials,
    BrokenCredentialsMixin as BC,
)
from organizations.tests.conftest import organizations
from publications.tests.conftest import platforms
from test_fixtures.scenarios.basic import (
    counter_report_types,
    report_types,
    organizations,
    platforms,
    data_sources,
    credentials,
)
from test_fixtures.entities.credentials import CredentialsFactory
from test_fixtures.entities.fetchattempts import FetchAttemptFactory

from ..tasks import retry_holes_with_new_credentials_task


@pytest.fixture
def fetch_unit(credentials, counter_report_types) -> FetchUnit:
    return FetchUnit(credentials["standalone_tr"], report_type=counter_report_types["tr"])


class TestHelperFunctions:
    def test_months_to_cover_no_first_month(self, settings):
        today = now().date()
        # set the date to 4 months before today
        first_month = month_start(month_start(today) - timedelta(days=100))
        settings.SUSHI_ATTEMPT_LAST_DATE = first_month.isoformat()[:7]
        months = months_to_cover()
        assert len(months) == 4
        assert months[0] == first_month
        assert months[-1] == month_start(month_start(today) - timedelta(days=15))


@pytest.mark.django_db
class TestHoleFillingMachinery:
    def test_find_holes_in_data(self, settings, organizations, counter_report_types, monkeypatch):
        """
        Tests the `find_holes_in_data` function.
        """
        # set the date to 3 months before today
        first_month = month_start(month_start(now().date()) - timedelta(days=80))
        settings.SUSHI_ATTEMPT_LAST_DATE = first_month.isoformat()[:7]
        # create all the prerequisites
        data = [
            {
                'platform': 'XXX',
                'organization': organizations["standalone"].internal_id,
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
        cr1.counter_reports.add(counter_report_types['tr'])

        def mock_get_report_data(*args, **kwargs):
            return Counter5ReportBase()

        monkeypatch.setattr(Sushi5Client, 'get_report_data', mock_get_report_data)
        # test that find_holes_in_data returns the right number of records
        holes = find_holes_in_data()
        assert len(holes) == 3
        # add an attempt and try again
        attempt = cr1.fetch_report(
            counter_report_types['tr'], start_date=first_month, end_date=month_end(first_month)
        )
        assert attempt.processing_success
        holes = find_holes_in_data()
        assert len(holes) == 2
        assert holes[0].attempt_count == 0
        # add a failed attempt for the same month
        attempt = cr1.fetch_report(
            counter_report_types['tr'], start_date=first_month, end_date=month_end(first_month)
        )
        attempt.processing_success = False
        attempt.save()
        holes = find_holes_in_data()
        assert len(holes) == 2, 'nothing should change'
        assert holes[0].attempt_count == 0
        # add a failed attempt for the next month
        next_month = month_start(first_month + timedelta(days=45))
        attempt = cr1.fetch_report(
            counter_report_types['tr'], start_date=next_month, end_date=month_end(next_month)
        )
        attempt.processing_success = False
        attempt.save()
        holes = find_holes_in_data()
        assert len(holes) == 2, 'nothing should change'
        assert holes[0].attempt_count == 1

    def test_retry_holes_with_new_credentials(
        self, settings, organizations, counter_report_types, monkeypatch
    ):
        """
        Tests the `find_holes_in_data` function.
        """
        # set the date to 3 months before today
        first_month = month_start(month_start(now().date()) - timedelta(days=80))
        settings.SUSHI_ATTEMPT_LAST_DATE = first_month.isoformat()[:7]
        # create all the prerequisites
        data = [
            {
                'platform': 'XXX',
                'organization': organizations["standalone"].internal_id,
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
        cr1.counter_reports.add(counter_report_types["tr"])

        def mock_get_report_data(*args, **kwargs):
            return Counter5ReportBase()

        monkeypatch.setattr(Sushi5Client, 'get_report_data', mock_get_report_data)
        # test that find_holes_in_data returns the right number of records
        holes = find_holes_in_data()
        assert len(holes) == 3
        # add an attempt and try again
        assert SushiFetchAttempt.objects.count() == 0
        retry_holes_with_new_credentials()
        assert SushiFetchAttempt.objects.count() == 3
        holes = find_holes_in_data()
        assert len(holes) == 0

    def test_retry_holes_with_new_credentials_task(
        self, settings, organizations, counter_report_types, monkeypatch
    ):
        """
        Tests the task based version of trying data holes
        """
        # set the date to 3 months before today
        first_month = month_start(month_start(now().date()) - timedelta(days=80))
        settings.SUSHI_ATTEMPT_LAST_DATE = first_month.isoformat()[:7]
        # create all the prerequisites
        data = [
            {
                'platform': 'XXX',
                'organization': organizations["standalone"].internal_id,
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
        cr1.counter_reports.add(counter_report_types['tr'])

        def mock_get_report_data(*args, **kwargs):
            return Counter5ReportBase()

        monkeypatch.setattr(Sushi5Client, 'get_report_data', mock_get_report_data)
        # test that find_holes_in_data returns the right number of records
        holes = find_holes_in_data()
        assert len(holes) == 3
        # add an attempt and try again
        assert SushiFetchAttempt.objects.count() == 0
        with patch('sushi.tasks.make_fetch_attempt_task') as task_mock:
            retry_holes_with_new_credentials_task()
            assert task_mock.apply_async.call_count == 3


@pytest.mark.django_db
class TestSushiFetching:
    def test_create_fetch_units(self, organizations, platforms, counter_report_types):
        creds = CredentialsFactory(
            organization=organizations["standalone"],
            platform=platforms["standalone"],
            counter_version=5,
            lock_level=UL_ORG_ADMIN,
            url='http://a.b.c/',
        )
        fus = create_fetch_units()
        assert len(fus) == 0, 'no fetchunits until credentails have some report type active'
        creds.counter_reports.add(counter_report_types["tr"])
        fus = create_fetch_units()
        assert len(fus) == 1, 'newly added report'

        # break credentials
        creds.broken = creds.BROKEN_HTTP
        creds.save()
        fus = create_fetch_units()
        assert len(fus) == 0, 'no fetch units for broken credentials'

        # break report_type to credential
        creds.broken = None
        creds.save()
        cr2c = CounterReportsToCredentials.objects.get(
            credentials=creds, counter_report=counter_report_types["tr"]
        )
        cr2c.broken = cr2c.BROKEN_SUSHI
        cr2c.save()

        fus = create_fetch_units()
        assert len(fus) == 0, 'no fetch units for broken report_type for credentials'

    def test_process_fetch_units_broken(self, fetch_unit: FetchUnit, monkeypatch):
        """
        Test that `process_fetch_units` stops after first attempt if the credentials are broken
        """

        def mock_download(self_: FetchUnit, start_date, end_date, **kwargs):
            """
            simulate broken credentials by returning attempts that is not successful
            """
            mock_download.called = (
                mock_download.called + 1 if hasattr(mock_download, 'called') else 1
            )
            return FetchAttemptFactory(
                credentials=self_.credentials,
                counter_report=self_.report_type,
                start_date=start_date,
                end_date=end_date,
                error_code='3000',
                download_success=True,
                processing_success=False,
            )

        monkeypatch.setattr(FetchUnit, 'download', mock_download)
        process_fetch_units([fetch_unit], start_date=date(2020, 1, 1), end_date=date(2019, 1, 1))
        assert mock_download.called == 1, 'one attempt for 13 months because of broken credentials'

    def test_process_fetch_units_ok(self, fetch_unit: FetchUnit, monkeypatch):
        """
        Test that `process_fetch_units` continues to fetch older data if good data get returned
        from previous attempts.
        """

        def mock_download(self_: FetchUnit, start_date, end_date, **kwargs):
            mock_download.called = (
                mock_download.called + 1 if hasattr(mock_download, 'called') else 1
            )
            return FetchAttemptFactory(
                credentials=self_.credentials,
                counter_report=self_.report_type,
                start_date=start_date,
                end_date=end_date,
                download_success=True,
                processing_success=True,
                contains_data=True,
            )

        monkeypatch.setattr(FetchUnit, 'download', mock_download)
        process_fetch_units([fetch_unit], start_date=date(2020, 1, 1), end_date=date(2019, 1, 1))
        assert mock_download.called == 13, 'thirteen months'

    def test_process_fetch_units_with_successful_conflict(self, fetch_unit: FetchUnit, monkeypatch):
        """
        Test that `process_fetch_units` skips attempts if successful conflicting attempt is
        already present.
        """

        start_date = date(2020, 1, 1)
        end_date = date(2020, 1, 31)
        FetchAttemptFactory(
            credentials=fetch_unit.credentials,
            counter_report=fetch_unit.report_type,
            start_date=start_date,
            end_date=end_date,
            download_success=True,
            processing_success=True,
            contains_data=True,
        )

        def mock_download(*args, **kwargs):
            mock_download.called = True

        monkeypatch.setattr(FetchUnit, 'download', mock_download)
        process_fetch_units([fetch_unit], start_date=start_date, end_date=start_date)
        assert getattr(mock_download, 'called', False) is False, 'attempt should not be made'

    def test_process_fetch_units_with_failed_conflict(self, fetch_unit: FetchUnit, monkeypatch):
        """
        Test that `process_fetch_units` skips attempts if failed conflicting attempt is
        already present and it thinks there is no reason to retry.
        """
        start_date = date(2020, 1, 1)
        end_date = date(2020, 1, 31)
        FetchAttemptFactory(
            credentials=fetch_unit.credentials,
            counter_report=fetch_unit.report_type,
            start_date=start_date,
            end_date=end_date,
            download_success=True,
            processing_success=False,
            contains_data=False,
        )

        def mock_download(*args, **kwargs):
            mock_download.called = True

        monkeypatch.setattr(FetchUnit, 'download', mock_download)
        process_fetch_units([fetch_unit], start_date=start_date, end_date=start_date)
        assert getattr(mock_download, 'called', False) is False, 'attempt should not be made'

    def test_process_fetch_units_with_retriable_failed_conflict(
        self, fetch_unit: FetchUnit, monkeypatch
    ):
        """
        Test that `process_fetch_units` makes attempts if a conflicting attempt is
        already present, when the old attempt was not successful and it seems new attempt may help.
        """
        start_date = date(2020, 1, 1)
        end_date = date(2020, 1, 31)
        sfa = FetchAttemptFactory(
            credentials=fetch_unit.credentials,
            counter_report=fetch_unit.report_type,
            start_date=start_date,
            end_date=end_date,
            download_success=True,
            processing_success=True,
            contains_data=False,
            error_code='3030',
        )
        # override the timestamp of old attempt to make sure retrial is due
        sfa.timestamp = now() - timedelta(days=30)
        sfa.save()

        def mock_download(self_, start, end, **kwargs):
            mock_download.called = True
            return FetchAttemptFactory(
                credentials=self_.credentials,
                counter_report=self_.report_type,
                start_date=start,
                end_date=end,
            )

        monkeypatch.setattr(FetchUnit, 'download', mock_download)
        process_fetch_units([fetch_unit], start_date=start_date, end_date=start_date)
        assert mock_download.called is True, 'attempt should be made'


@pytest.mark.django_db
class TestFetchUnit:
    def test_find_conflicting(self, fetch_unit: FetchUnit):
        """
        Tests that the `FetchUnit.find_conflicting` works as expected. Simple version.
        """
        start_date = date(2020, 1, 1)
        end_date = date(2020, 1, 31)
        assert fetch_unit.find_conflicting(start_date, end_date) is None
        fa = FetchAttemptFactory(
            credentials=fetch_unit.credentials,
            counter_report=fetch_unit.report_type,
            start_date=start_date,
            end_date=end_date,
            credentials_version_hash=fetch_unit.credentials.version_hash,
        )
        assert fetch_unit.find_conflicting(start_date, end_date).pk == fa.pk

    def test_find_conflicting_with_versions_failed(self, fetch_unit: FetchUnit):
        """
        Tests that the `FetchUnit.find_conflicting` works as expected. This version takes
        credentials versions into consideration.
        Existing attempt should not be reported as conflicting, if it was created using
        an old version of credentials and was not successful.
        """
        start_date = date(2020, 1, 1)
        end_date = date(2020, 1, 31)
        assert fetch_unit.find_conflicting(start_date, end_date) is None
        FetchAttemptFactory(
            credentials=fetch_unit.credentials,
            counter_report=fetch_unit.report_type,
            start_date=start_date,
            end_date=end_date,
            credentials_version_hash='foobarbaz',  # definitely not matching credentials
            download_success=False,
        )
        assert (
            fetch_unit.find_conflicting(start_date, end_date) is None
        ), 'should not report attempt with old version of credentials'

    def test_find_conflicting_with_versions_successful(self, fetch_unit: FetchUnit):
        """
        Tests that the `FetchUnit.find_conflicting` works as expected. This version takes
        credentials versions into consideration.
        Existing attempt should be reported as conflicting, if it was created using
        an old version of credentials, but was successful - this prevents redownload of data
        successfully fetched in the past.
        """
        start_date = date(2020, 1, 1)
        end_date = date(2020, 1, 31)
        assert fetch_unit.find_conflicting(start_date, end_date) is None
        fa = FetchAttemptFactory(
            credentials=fetch_unit.credentials,
            counter_report=fetch_unit.report_type,
            start_date=start_date,
            end_date=end_date,
            credentials_version_hash='foobarbaz',  # definitely not matching credentials
            download_success=True,
            processing_success=True,
            contains_data=True,  # this means successful
        )
        assert (
            fetch_unit.find_conflicting(start_date, end_date).pk == fa.pk
        ), 'should report successful attempt with old version of credentials'


@pytest.mark.django_db
class TestQueued:
    def test_retry_queued(self, counter_report_types, credentials, monkeypatch):
        credentials["standalone_tr"].broken = BC.BROKEN_HTTP
        credentials["standalone_tr"].save()

        cr2c = CounterReportsToCredentials.objects.get(
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["br1"],
        )
        cr2c.broken = BC.BROKEN_SUSHI
        cr2c.save()

        kwargs = {
            "start_date": "2020-01-01",
            "end_date": "2020-01-31",
            "download_success": True,
            "processing_success": True,
            "contains_data": True,
            "queued": True,
            "error_code": ErrorCode.DATA_NOT_READY_FOR_DATE_ARGS.value,
            "when_queued": now() - timedelta(days=120),  # random date long ago
        }

        # mock fetching
        def mock_get_report_data_5(*args, **kwargs):
            return Counter5ReportBase()

        monkeypatch.setattr(Sushi5Client, 'get_report_data', mock_get_report_data_5)

        def mock_get_report_data_4(*args, **kwargs):
            report = CounterReport(report_type=args[1], period=(args[2], args[3]))
            return report

        monkeypatch.setattr(Sushi4Client, 'get_report_data', mock_get_report_data_4)

        # no broken
        FetchAttemptFactory(
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["jr1"],
            **kwargs,
        )
        counter = retry_queued()
        assert counter == {'retry_SUCCESS': 1}

        # broken credentials
        FetchAttemptFactory(
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
            **kwargs,
        )
        counter = retry_queued()
        assert counter == {}, "nothing queued"

        # broken report type
        FetchAttemptFactory(
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["br1"],
            **kwargs,
        )
        counter = retry_queued()
        assert counter == {}, "nothing queued"

        # lets try to update broken statuses
        credentials["standalone_tr"].broken = None
        credentials["standalone_tr"].save()
        cr2c.broken = None
        cr2c.save()

        counter = retry_queued()
        assert counter == {'retry_SUCCESS': 1, 'retry_NO_DATA': 1}, "all planned"
