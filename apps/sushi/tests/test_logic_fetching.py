from datetime import timedelta

import pytest
from django.utils.timezone import now

from core.logic.dates import month_start, month_end
from nigiri.client import Sushi5Client
from nigiri.counter5 import Counter5ReportBase
from publications.models import Platform
from ..logic.data_import import import_sushi_credentials
from ..logic.fetching import months_to_cover, find_holes_in_data, retry_holes_with_new_credentials
from sushi.models import CounterReportType, SushiCredentials, SushiFetchAttempt
from organizations.tests.conftest import organizations
from publications.tests.conftest import platforms
from logs.tests.conftest import report_type_nd
from ..tasks import retry_holes_with_new_credentials_task


@pytest.fixture(scope='session')
def celery_config():
    return {
        'task_always_eager': True,
    }


class TestHelperFunctions(object):
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
class TestHoleFillingMachinery(object):
    def test_find_holes_in_data(self, settings, organizations, report_type_nd):
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
        cr1.active_counter_reports.add(report)

        def mock_get_report_data(*args, **kwargs):
            return Counter5ReportBase()

        Sushi5Client.get_report_data = mock_get_report_data
        # test that find_holes_in_data returns the right number of records
        holes = find_holes_in_data()
        assert len(holes) == 3
        # add an attempt and try again
        attempt = cr1.fetch_report(report, start_date=first_month, end_date=month_end(first_month))
        assert attempt.processing_success
        holes = find_holes_in_data()
        assert len(holes) == 2
        assert holes[0].attempt_count == 0
        # add a failed attempt for the same month
        attempt = cr1.fetch_report(report, start_date=first_month, end_date=month_end(first_month))
        attempt.processing_success = False
        attempt.save()
        holes = find_holes_in_data()
        assert len(holes) == 2, 'nothing should change'
        assert holes[0].attempt_count == 0
        # add a failed attempt for the next month
        next_month = month_start(first_month + timedelta(days=45))
        attempt = cr1.fetch_report(report, start_date=next_month, end_date=month_end(next_month))
        attempt.processing_success = False
        attempt.save()
        holes = find_holes_in_data()
        assert len(holes) == 2, 'nothing should change'
        assert holes[0].attempt_count == 1

    def test_retry_holes_with_new_credentials(self, settings, organizations, report_type_nd):
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
        cr1.active_counter_reports.add(report)

        def mock_get_report_data(*args, **kwargs):
            return Counter5ReportBase()

        Sushi5Client.get_report_data = mock_get_report_data
        # test that find_holes_in_data returns the right number of records
        holes = find_holes_in_data()
        assert len(holes) == 3
        # add an attempt and try again
        assert SushiFetchAttempt.objects.count() == 0
        retry_holes_with_new_credentials()
        assert SushiFetchAttempt.objects.count() == 3
        holes = find_holes_in_data()
        assert len(holes) == 0

    def test_retry_holes_with_new_credentials_task(self, settings, organizations, report_type_nd,
                                                   celery_session_worker):
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
        cr1.active_counter_reports.add(report)

        def mock_get_report_data(*args, **kwargs):
            return Counter5ReportBase()

        Sushi5Client.get_report_data = mock_get_report_data
        # test that find_holes_in_data returns the right number of records
        holes = find_holes_in_data()
        assert len(holes) == 3
        # add an attempt and try again
        assert SushiFetchAttempt.objects.count() == 0
        retry_holes_with_new_credentials_task()
        assert SushiFetchAttempt.objects.count() == 3
        holes = find_holes_in_data()
        assert len(holes) == 0
