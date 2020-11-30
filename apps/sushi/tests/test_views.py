import json
import pytest

from freezegun import freeze_time
from datetime import timedelta
from unittest.mock import patch
from urllib.parse import quote

from django.urls import reverse
from django.utils import timezone

from core.models import UL_CONS_STAFF, UL_ORG_ADMIN, Identity
from logs.models import ImportBatch
from organizations.models import UserOrganization
from organizations.tests.conftest import identity_by_user_type
from sushi.models import (
    SushiCredentials,
    SushiFetchAttempt,
    BrokenCredentialsMixin as BS,
    CounterReportsToCredentials,
)

from test_fixtures.entities.credentials import CredentialsFactory
from test_fixtures.entities.fetchattempts import FetchAttemptFactory
from test_fixtures.scenarios.basic import (
    basic1,
    clients,
    counter_report_types,
    credentials,
    data_sources,
    harvests,
    identities,
    import_batches,
    organizations,
    platforms,
    report_types,
    schedulers,
    users,
)


@pytest.mark.django_db()
class TestSushiCredentialsViewSet:
    def test_lock_action(self, basic1, organizations, platforms, clients):
        credentials = CredentialsFactory(
            organization=organizations["master"],
            platform=platforms["master"],
            counter_version=5,
            lock_level=SushiCredentials.UNLOCKED,
        )
        url = reverse('sushi-credentials-lock', args=(credentials.pk,))
        resp = clients["master"].post(url, {})
        assert resp.status_code == 200
        credentials.refresh_from_db()
        assert credentials.lock_level == UL_CONS_STAFF

    def test_lock_action_no_permission(self, basic1, organizations, platforms, clients):
        credentials = CredentialsFactory(
            organization=organizations["empty"],
            platform=platforms["empty"],
            counter_version=5,
            lock_level=UL_CONS_STAFF,
        )
        url = reverse('sushi-credentials-lock', args=(credentials.pk,))
        resp = clients["user1"].post(url, {})
        assert resp.status_code == 403
        credentials.refresh_from_db()
        assert credentials.lock_level == UL_CONS_STAFF

    def test_create_action(
        self, basic1, organizations, platforms, clients, users, counter_report_types
    ):
        url = reverse('sushi-credentials-list')

        title = 'Foo bar credentials'
        resp = clients["admin1"].post(
            url,
            {
                'title': title,
                'platform_id': platforms["root"].pk,
                'organization_id': organizations["root"].pk,
                'url': 'http://foo.bar.baz',
                'requestor_id': 'xxxxxxx',
                'customer_id': 'yyyyy',
                'counter_version': '5',
                'counter_reports': [counter_report_types["tr"].pk],
            },
        )
        assert resp.status_code == 201
        sc = SushiCredentials.objects.get()
        assert sc.last_updated_by == users["admin1"]
        assert sc.counter_reports.count() == 1
        assert sc.title == title

    def test_edit_action(self, basic1, organizations, platforms, clients):
        credentials = CredentialsFactory(
            title='',
            organization=organizations["root"],
            platform=platforms["root"],
            counter_version=5,
            lock_level=UL_ORG_ADMIN,
            url='http://a.b.c/',
        )
        assert credentials.title == ''
        url = reverse('sushi-credentials-detail', args=(credentials.pk,))
        new_url = 'http://x.y.com/'
        new_title = 'New title'
        resp = clients["admin1"].patch(url, {'url': new_url, 'title': new_title})
        assert resp.status_code == 200
        credentials.refresh_from_db()
        assert credentials.url == new_url
        assert credentials.title == new_title

    def test_edit_action_locked(self, basic1, organizations, platforms, clients):
        """
        The API for updating sushi credentials is accessed by a normal user and thus permission
        denied is returned
        """
        credentials = CredentialsFactory(
            organization=organizations["branch"],
            platform=platforms["branch"],
            counter_version=5,
            lock_level=UL_ORG_ADMIN,
            url='http://a.b.c/',
        )
        url = reverse('sushi-credentials-detail', args=(credentials.pk,))
        new_url = 'http://x.y.com/'
        resp = clients["user1"].patch(url, {'url': new_url})
        assert resp.status_code == 403

    def test_edit_action_locked_higher(self, basic1, organizations, platforms, clients):
        """
        The object is locked with consortium staff level lock, so the organization admin cannot
        edit it
        """
        credentials = CredentialsFactory(
            organization=organizations["root"],
            platform=platforms["root"],
            counter_version=5,
            lock_level=UL_CONS_STAFF,
            url='http://a.b.c/',
        )
        url = reverse('sushi-credentials-detail', args=(credentials.pk,))
        new_url = 'http://x.y.com/'
        resp = clients["admin1"].patch(url, {'url': new_url})
        assert resp.status_code == 403

    def test_edit_action_with_report_types(
        self, basic1, organizations, platforms, clients, counter_report_type_named,
    ):
        """
        Test changing report types using the API update action works
        """
        credentials = CredentialsFactory(
            organization=organizations["root"],
            platform=platforms["root"],
            counter_version=5,
            lock_level=UL_ORG_ADMIN,
            url='http://a.b.c/',
        )
        url = reverse('sushi-credentials-detail', args=(credentials.pk,))
        new_rt1 = counter_report_type_named('new1')
        new_rt2 = counter_report_type_named('new2')
        resp = clients["admin1"].patch(url, {'counter_reports': [new_rt1.pk, new_rt2.pk]},)
        assert resp.status_code == 200
        credentials.refresh_from_db()
        assert credentials.counter_reports.count() == 2
        assert {cr.pk for cr in credentials.counter_reports.all()} == {
            new_rt1.pk,
            new_rt2.pk,
        }

    def test_destroy_locked_higher(self, basic1, organizations, platforms, clients):
        """
        The object is locked with consortium staff level lock, so the organization admin cannot
        remove it
        """
        credentials = CredentialsFactory(
            organization=organizations["root"],
            platform=platforms["root"],
            counter_version=5,
            lock_level=UL_CONS_STAFF,
            url='http://a.b.c/',
        )
        url = reverse('sushi-credentials-detail', args=(credentials.pk,))
        assert SushiCredentials.objects.count() == 1
        resp = clients["admin1"].delete(url)
        assert resp.status_code == 403
        assert SushiCredentials.objects.count() == 1

    def test_destroy_locked_lower(self, basic1, organizations, platforms, clients):
        """
        The object is locked with consortium staff level lock, so the organization admin cannot
        remove it
        """
        credentials = CredentialsFactory(
            organization=organizations["root"],
            platform=platforms["root"],
            counter_version=5,
            lock_level=UL_ORG_ADMIN,
            url='http://a.b.c/',
        )
        url = reverse('sushi-credentials-detail', args=(credentials.pk,))
        assert SushiCredentials.objects.count() == 1
        resp = clients["admin1"].delete(url)
        assert resp.status_code == 204
        assert SushiCredentials.objects.count() == 0

    def test_month_overview_no_month(self, basic1, clients):
        """
        Test the month-overview custom action - month attr should be given
        """
        url = reverse('sushi-credentials-month-overview')
        resp = clients["master"].get(url)
        assert resp.status_code == 400, 'Month URL param must be present'

    def test_month_overview(
        self, basic1, organizations, platforms, counter_report_type_named, clients
    ):
        """
        Test the month-overview custom action
        """
        credentials = CredentialsFactory(
            organization=organizations["empty"],
            platform=platforms["empty"],
            counter_version=5,
            lock_level=UL_ORG_ADMIN,
            url='http://a.b.c/',
        )
        new_rt1 = counter_report_type_named('new1')
        credentials.counter_reports.add(new_rt1)
        FetchAttemptFactory(
            credentials=credentials,
            start_date='2020-01-01',
            end_date='2020-01-31',
            credentials_version_hash=credentials.version_hash,
            counter_report=new_rt1,
        )
        attempt2 = FetchAttemptFactory(
            credentials=credentials,
            start_date='2020-01-01',
            end_date='2020-01-31',
            credentials_version_hash=credentials.version_hash,
            counter_report=new_rt1,
        )
        url = reverse('sushi-credentials-month-overview')
        resp = clients["master"].get(url, {'month': '2020-01'})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1, 'there should be one record for one set of credentials'
        rec = data[0]
        assert rec['credentials_id'] == credentials.pk
        assert rec['counter_report_id'] == new_rt1.pk
        assert rec['pk'] == attempt2.pk, 'the second (newer) attempt should be reported'
        # now disable the credentials and observe the result
        credentials.enabled = False
        credentials.save()
        resp = clients["master"].get(url, {'month': '2020-01'})
        assert len(resp.json()) == 0
        # now add param that says disabled should be included
        resp = clients["master"].get(url, {'month': '2020-01', 'disabled': 'true'})
        assert len(resp.json()) == 1

    def test_month_overview_long_attempts(
        self, basic1, organizations, platforms, counter_report_type_named, clients
    ):
        """
        Test the month-overview custom action in presence of sushi fetch attempts that span
        more than one month
        """
        credentials = CredentialsFactory(
            organization=organizations["empty"],
            platform=platforms["empty"],
            counter_version=5,
            lock_level=UL_ORG_ADMIN,
            url='http://a.b.c/',
        )
        new_rt1 = counter_report_type_named('new1')
        credentials.counter_reports.add(new_rt1)
        attempt1 = FetchAttemptFactory(
            credentials=credentials,
            start_date='2020-01-01',
            end_date='2020-03-31',
            credentials_version_hash=credentials.version_hash,
            counter_report=new_rt1,
        )
        attempt2 = FetchAttemptFactory(
            credentials=credentials,
            start_date='2020-01-01',
            end_date='2020-01-31',
            credentials_version_hash=credentials.version_hash,
            counter_report=new_rt1,
        )
        url = reverse('sushi-credentials-month-overview')
        # 2020-01 - there are two attempts for this month
        resp = clients["master"].get(url, {'month': '2020-01'})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1, 'there should be one record for this period'
        rec = data[0]
        assert rec['pk'] == attempt2.pk, 'the second (newer) attempt should be reported'
        # 2020-02 - there is one attempt for this month
        resp = clients["master"].get(url, {'month': '2020-02'})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1, 'there should be one record for this period'
        rec = data[0]
        assert rec['pk'] == attempt1.pk, 'the attempt spanning to this month should be reported'
        # 2020-03 - there is one attempt for this month
        resp = clients["master"].get(url, {'month': '2020-03'})
        assert resp.status_code == 200
        assert len(resp.json()) == 1, 'there should be one record for this period'
        # 2020-04 - no attempt for this month
        resp = clients["master"].get(url, {'month': '2020-04'})
        assert resp.status_code == 200
        assert len(resp.json()) == 0, 'there should be no record for this period'

    def test_unset_broken(self, credentials, clients, counter_report_types):

        attempt_tr = FetchAttemptFactory(
            credentials=credentials["standalone_tr"], counter_report=counter_report_types["tr"]
        )
        credentials["standalone_tr"].broken = BS.BROKEN_HTTP
        credentials["standalone_tr"].first_broken_attempt = attempt_tr
        credentials["standalone_tr"].save()
        cr2c_tr = CounterReportsToCredentials.objects.get(
            credentials=credentials["standalone_tr"], counter_report__code="TR"
        )
        cr2c_tr.broken = BS.BROKEN_SUSHI
        cr2c_tr.first_broken_attempt = attempt_tr
        cr2c_tr.save()

        # unset entire credentials (both reports and mappings are unset)
        url = reverse('sushi-credentials-unset-broken', args=(credentials["standalone_tr"].pk,))
        resp = clients["master"].post(url, None)
        assert resp.status_code == 200
        credentials["standalone_tr"].refresh_from_db()
        assert credentials["standalone_tr"].broken is None
        assert credentials["standalone_tr"].first_broken_attempt is None
        cr2c_tr.refresh_from_db()
        assert cr2c_tr.broken is None
        assert cr2c_tr.first_broken_attempt is None

        # Broken credentials mapping (only selected mappings are unset
        attempt_jr1 = FetchAttemptFactory(
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["jr1"],
        )
        attempt_br1 = FetchAttemptFactory(
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["jr1"],
        )
        credentials["standalone_br1_jr1"].broken = BS.BROKEN_SUSHI
        credentials["standalone_br1_jr1"].first_broken_attempt = attempt_br1
        credentials["standalone_br1_jr1"].save()
        cr2c_br1 = CounterReportsToCredentials.objects.get(
            credentials=credentials["standalone_br1_jr1"], counter_report__code="BR1"
        )
        cr2c_br1.broken = BS.BROKEN_SUSHI
        cr2c_br1.first_broken_attempt = attempt_br1
        cr2c_br1.save()
        cr2c_jr1 = CounterReportsToCredentials.objects.get(
            credentials=credentials["standalone_br1_jr1"], counter_report__code="JR1"
        )
        cr2c_jr1.broken = BS.BROKEN_SUSHI
        cr2c_jr1.first_broken_attempt = attempt_jr1
        cr2c_jr1.save()
        url = reverse(
            'sushi-credentials-unset-broken', args=(credentials["standalone_br1_jr1"].pk,)
        )
        resp = clients["master"].post(url, {"counter_reports": ["JR1"]})
        assert resp.status_code == 200
        credentials["standalone_br1_jr1"].refresh_from_db()
        assert credentials["standalone_br1_jr1"].broken == BS.BROKEN_SUSHI
        assert credentials["standalone_br1_jr1"].first_broken_attempt == attempt_br1
        cr2c_br1.refresh_from_db()
        assert cr2c_br1.broken == BS.BROKEN_SUSHI
        assert cr2c_br1.first_broken_attempt == attempt_br1
        cr2c_jr1.refresh_from_db()
        assert cr2c_jr1.broken is None
        assert cr2c_jr1.first_broken_attempt is None

        # Wrong type
        resp = clients["master"].post(url, {"counter_reports": ["WRONG_TYPE"]})
        assert resp.status_code == 400

        # Non not assigned report type
        resp = clients["master"].post(url, {"counter_reports": ["BR1", "DB1"]})
        assert resp.status_code == 200
        cr2c_br1.refresh_from_db()
        assert cr2c_br1.broken is None
        assert cr2c_br1.first_broken_attempt is None

        # Credentials not found
        url = reverse('sushi-credentials-unset-broken', args=(0,))
        resp = clients["master"].post(url, {"counter_reports": ["JR1"]})
        assert resp.status_code == 404

    def test_credential_details(self, basic1, credentials, clients, counter_report_types):
        attempt_br1 = FetchAttemptFactory(
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["br1"],
        )
        cr2c_br1 = CounterReportsToCredentials.objects.get(
            credentials=credentials["standalone_br1_jr1"], counter_report__code="BR1"
        )
        cr2c_br1.broken = BS.BROKEN_SUSHI
        cr2c_br1.first_broken_attempt = attempt_br1
        cr2c_br1.save()

        url = reverse('sushi-credentials-detail', args=(credentials["standalone_br1_jr1"].pk,))
        resp = clients["master"].get(url)
        assert resp.status_code == 200

        data = resp.json()
        assert data['broken'] is None
        for rec in data['counter_reports_long']:
            if rec['code'] != 'BR1':
                assert rec['broken'] is None
            else:
                assert rec['broken'] == BS.BROKEN_SUSHI

    def test_count_api(self, basic1, credentials, clients, counter_report_types):
        """
        Test that the /count/ special api endpoint works
        """
        attempt_br1 = FetchAttemptFactory(
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["br1"],
        )
        cr2c_br1 = CounterReportsToCredentials.objects.get(
            credentials=credentials["standalone_br1_jr1"], counter_report__code="BR1"
        )
        cr2c_br1.broken = BS.BROKEN_SUSHI
        cr2c_br1.first_broken_attempt = attempt_br1
        cr2c_br1.save()
        credentials['standalone_tr'].broken = BS.BROKEN_HTTP
        credentials['standalone_tr'].save()

        resp = clients["master"].get(reverse('sushi-credentials-count'))
        assert resp.status_code == 200
        assert resp.json() == {'count': 3, 'broken': 1, 'broken_reports': 1}

    @freeze_time("2020-06-01")
    def test_downloads(self, basic1, credentials, clients, harvests, counter_report_types):

        # mark credentials
        attempt_tr = FetchAttemptFactory(
            credentials=credentials["standalone_tr"], counter_report=counter_report_types["tr"]
        )
        credentials["standalone_tr"].set_broken(attempt_tr, BS.BROKEN_HTTP)

        # mark broken mapping
        attempt_br1 = FetchAttemptFactory(
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["jr1"],
        )
        cr2c_br1 = CounterReportsToCredentials.objects.get(
            credentials=credentials["standalone_br1_jr1"], counter_report__code="BR1"
        )
        cr2c_br1.set_broken(attempt_br1, BS.BROKEN_SUSHI)

        # Just test premade scenarios
        resp = clients["master"].get(
            reverse('sushi-credentials-data', args=(credentials["standalone_tr"].pk,))
        )
        assert resp.status_code == 200
        data = resp.json()

        assert len(data) == 1
        assert data[0]["year"] == timezone.now().year
        for i in range(1, 13):
            month = f"{i:02d}"
            assert len(data[0][month]) == 1
            assert data[0][month][0]["planned"] is False
            assert data[0][month][0]["broken"] is False, "mapping not broken, but creds are"
            if month in ["01"]:
                assert data[0][month][0]["status"] == "failed"
            else:
                assert data[0][month][0]["status"] == "untried"

        resp = clients["master"].get(
            reverse('sushi-credentials-data', args=(credentials["standalone_br1_jr1"].pk,))
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["year"] == timezone.now().year
        assert len(data) == 1
        for i in range(1, 13):
            month = f"{i:02d}"
            assert len(data[0][month]) == 2
            assert data[0][month][0]["broken"] is False
            assert data[0][month][1]["broken"] is True, "mapping broken"
            if month in ["01"]:
                assert data[0][month][0]["status"] == "failed"
                assert data[0][month][1]["status"] == "no_data"
                assert data[0][month][0]["planned"] is True
                assert data[0][month][1]["planned"] is True
            else:
                assert data[0][month][0]["status"] == "untried"
                assert data[0][month][1]["status"] == "untried"
                assert data[0][month][0]["planned"] is False
                assert data[0][month][1]["planned"] is False

        resp = clients["master"].get(
            reverse('sushi-credentials-data', args=(credentials["branch_pr"].pk,))
        )
        assert resp.status_code == 200
        data = resp.json()

        assert len(data) == 1
        assert data[0]["year"] == timezone.now().year
        for i in range(1, 13):
            month = f"{i:02d}"
            assert len(data[0][month]) == 1
            assert data[0][month][0]["broken"] is False
            if month in ["01"]:
                assert data[0][month][0]["status"] == "success"
                assert data[0][month][0]["planned"] is False
            elif month in ["03"]:
                assert data[0][month][0]["status"] == "untried"
                assert data[0][month][0]["planned"] is True
            else:
                assert data[0][month][0]["status"] == "untried"
                assert data[0][month][0]["planned"] is False


@pytest.mark.django_db()
class TestSushiFetchAttemptStatsView:
    def test_no_dates_mode_all(
        self, basic1, organizations, platforms, clients, counter_report_type_named
    ):
        """
        Test that the api view works when the requested data does not contain dates and all
        attempts are requested
        """
        credentials = CredentialsFactory(
            organization=organizations["empty"],
            platform=platforms["empty"],
            counter_version=5,
            lock_level=UL_ORG_ADMIN,
            url='http://a.b.c/',
        )
        new_rt1 = counter_report_type_named('new1')
        FetchAttemptFactory(
            credentials=credentials,
            start_date='2020-01-01',
            end_date='2020-01-31',
            credentials_version_hash=credentials.version_hash,
            counter_report=new_rt1,
        )
        assert SushiFetchAttempt.objects.count() == 1
        url = reverse('sushi-fetch-attempt-stats')
        resp = clients["master"].get(url + '?mode=all')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]['failure_count'] == 1

    def test_no_dates_mode_current(
        self, basic1, organizations, platforms, clients, counter_report_type_named
    ):
        """
        Test that the api view works when the requested data does not contain dates and all
        attempts are requested
        """
        credentials = CredentialsFactory(
            organization=organizations["empty"],
            platform=platforms["empty"],
            counter_version=5,
            lock_level=UL_ORG_ADMIN,
            url='http://a.b.c/',
        )
        new_rt1 = counter_report_type_named('new1')
        FetchAttemptFactory(
            credentials=credentials,
            start_date='2020-01-01',
            end_date='2020-01-31',
            credentials_version_hash=credentials.version_hash,
            counter_report=new_rt1,
        )
        assert SushiFetchAttempt.objects.count() == 1
        # now update the credentials so that the attempt is no longer related to the current
        # version
        credentials.customer_id = 'new_id'
        credentials.save()
        # let's try it - there should be nothing
        url = reverse('sushi-fetch-attempt-stats')
        resp = clients["master"].get(url + '?mode=current')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 0

    def test_no_dates_mode_current_2(
        self, basic1, organizations, platforms, clients, counter_report_type_named
    ):
        """
        Test that the api view works when the requested data does not contain dates and all
        attempts are requested
        """
        credentials = CredentialsFactory(
            organization=organizations["empty"],
            platform=platforms["empty"],
            counter_version=5,
            lock_level=UL_ORG_ADMIN,
            url='http://a.b.c/',
        )
        new_rt1 = counter_report_type_named('new1')
        FetchAttemptFactory(
            credentials=credentials,
            start_date='2020-01-01',
            end_date='2020-01-31',
            credentials_version_hash=credentials.version_hash,
            counter_report=new_rt1,
        )
        assert SushiFetchAttempt.objects.count() == 1
        # now update the credentials so that the attempt is no longer related to the current
        # version
        credentials.customer_id = 'new_id'
        credentials.save()
        # create a second attempt, this one with current version
        FetchAttemptFactory(
            credentials=credentials,
            start_date='2020-01-01',
            end_date='2020-01-31',
            credentials_version_hash=credentials.version_hash,
            counter_report=new_rt1,
        )
        assert SushiFetchAttempt.objects.count() == 2
        # let's try it - there should be nothing
        url = reverse('sushi-fetch-attempt-stats')
        resp = clients["master"].get(url + '?mode=current')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]['failure_count'] == 1
        # let's check that with mode=all there would be two
        resp = clients["master"].get(url + '?mode=all')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]['failure_count'] == 2

    def test_no_dates_mode_success_and_current(
        self, basic1, organizations, platforms, clients, counter_report_type_named
    ):
        """
        Test that the api view works when the requested data does not contain dates and all
        attempts are requested
        """
        credentials = CredentialsFactory(
            organization=organizations["empty"],
            platform=platforms["empty"],
            counter_version=5,
            lock_level=UL_ORG_ADMIN,
            url='http://a.b.c/',
        )
        new_rt1 = counter_report_type_named('new1')
        # one success
        FetchAttemptFactory(
            credentials=credentials,
            start_date='2020-01-01',
            end_date='2020-01-31',
            credentials_version_hash=credentials.version_hash,
            counter_report=new_rt1,
            contains_data=True,
        )
        # one failure
        FetchAttemptFactory(
            credentials=credentials,
            start_date='2020-01-01',
            end_date='2020-01-31',
            credentials_version_hash=credentials.version_hash,
            counter_report=new_rt1,
            contains_data=False,
        )
        assert SushiFetchAttempt.objects.count() == 2
        # now update the credentials so that the attempt is no longer related to the current
        # version
        credentials.customer_id = 'new_id'
        credentials.save()
        # create a second attempt, this one with current version
        # one new failure
        FetchAttemptFactory(
            credentials=credentials,
            start_date='2020-01-01',
            end_date='2020-01-31',
            credentials_version_hash=credentials.version_hash,
            counter_report=new_rt1,
            contains_data=False,
        )
        assert SushiFetchAttempt.objects.count() == 3
        # let's try it - there should be nothing
        url = reverse('sushi-fetch-attempt-stats')
        resp = clients["master"].get(url + '?mode=success_and_current&success_metric=contains_data')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]['success_count'] == 1
        assert data[0]['failure_count'] == 1
        # let's check that with mode=current there would be only one
        resp = clients["master"].get(url + '?mode=current&success_metric=contains_data')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]['success_count'] == 0
        assert data[0]['failure_count'] == 1
        # let's check that with mode=all there would be three
        resp = clients["master"].get(url + '?mode=all&success_metric=contains_data')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]['success_count'] == 1
        assert data[0]['failure_count'] == 2


@pytest.mark.django_db()
class TestSushiFetchAttemptView:
    def test_create(self, basic1, organizations, platforms, clients, users, counter_report_types):
        credentials = CredentialsFactory(
            organization=organizations["root"], platform=platforms["root"],
        )

        # we must patch the run_sushi_fetch_attempt_task task in order to prevent stalling
        # during tests by CI
        with patch('sushi.views.run_sushi_fetch_attempt_task') as task_mock:
            resp = clients["master"].post(
                reverse('sushi-fetch-attempt-list'),
                {
                    'credentials': credentials.pk,
                    'start_date': '2020-01-01',
                    'end_date': '2020-01-31',
                    'counter_report': counter_report_types["tr"].pk,
                },
            )
            assert task_mock.apply_async.call_count == 1
            assert resp.status_code == 201
            assert 'pk' in resp.json()
            attempt = SushiFetchAttempt.objects.last()
            assert attempt.triggered_by == users["master"]

    def test_create_broken(self, basic1, clients, counter_report_types, credentials):
        # broken credentials
        attempt_tr = FetchAttemptFactory(
            credentials=credentials["standalone_tr"], counter_report=counter_report_types["tr"]
        )
        credentials["standalone_tr"].broken = BS.BROKEN_HTTP
        credentials["standalone_tr"].first_broken_attempt = attempt_tr
        credentials["standalone_tr"].save()

        resp = clients["master"].post(
            reverse('sushi-fetch-attempt-list'),
            {
                'credentials': credentials["standalone_tr"].pk,
                'start_date': '2020-01-01',
                'end_date': '2020-01-31',
                'counter_report': counter_report_types["tr"].pk,
            },
        )
        assert resp.status_code == 400

        # broken report type
        attempt_br1 = FetchAttemptFactory(
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["jr1"],
        )
        cr2c_br1 = CounterReportsToCredentials.objects.get(
            credentials=credentials["standalone_br1_jr1"], counter_report__code="BR1"
        )
        cr2c_br1.broken = BS.BROKEN_SUSHI
        cr2c_br1.first_broken_attempt = attempt_br1
        cr2c_br1.save()

        resp = clients["master"].post(
            reverse('sushi-fetch-attempt-list'),
            {
                'credentials': credentials["standalone_br1_jr1"].pk,
                'start_date': '2020-01-01',
                'end_date': '2020-01-31',
                'counter_report': counter_report_types["br1"].pk,
            },
        )
        assert resp.status_code == 400

        # other report type still working
        with patch('sushi.views.run_sushi_fetch_attempt_task') as task_mock:
            resp = clients["master"].post(
                reverse('sushi-fetch-attempt-list'),
                {
                    'credentials': credentials["standalone_br1_jr1"].pk,
                    'start_date': '2020-01-01',
                    'end_date': '2020-01-31',
                    'counter_report': counter_report_types["jr1"].pk,
                },
            )
            assert task_mock.apply_async.call_count == 1
        assert resp.status_code == 201

    @pytest.mark.parametrize(
        ['user', 'can_create', 'return_code'],
        [
            ['unauthenticated', False, 401],
            ['invalid', False, 401],
            ['user1', False, 403],
            ['user2', False, 403],
            ['admin2', True, 201],
            ['master', True, 201],
            ['su', True, 201],
        ],
    )
    def test_create_api_access(
        self,
        user,
        can_create,
        return_code,
        basic1,
        organizations,
        platforms,
        clients,
        counter_report_types,
    ):
        credentials = CredentialsFactory(
            organization=organizations["standalone"], platform=platforms["standalone"],
        )

        with patch('sushi.views.run_sushi_fetch_attempt_task') as task_mock:
            resp = clients[user].post(
                reverse('sushi-fetch-attempt-list'),
                {
                    'credentials': credentials.pk,
                    'start_date': '2020-01-01',
                    'end_date': '2020-01-31',
                    'counter_report': counter_report_types["tr"].pk,
                },
            )
            assert resp.status_code == return_code
            if can_create:
                assert task_mock.apply_async.call_count == 1
            else:
                assert task_mock.apply_async.call_count == 0

    def test_create_in_no_data_period(
        self, basic1, organizations, platforms, clients, counter_report_types
    ):
        credentials = CredentialsFactory(
            organization=organizations["root"], platform=platforms["root"],
        )

        with freeze_time("2020-01-31"):
            with patch('sushi.views.run_sushi_fetch_attempt_task'):
                resp = clients["master"].post(
                    reverse('sushi-fetch-attempt-list'),
                    {
                        'credentials': credentials.pk,
                        'start_date': '2020-01-01',
                        'end_date': '2020-01-31',
                        'counter_report': counter_report_types["tr"].pk,
                    },
                )
                assert resp.status_code == 400

        with freeze_time("2020-02-07"):
            with patch('sushi.views.run_sushi_fetch_attempt_task'):
                resp = clients["master"].post(
                    reverse('sushi-fetch-attempt-list'),
                    {
                        'credentials': credentials.pk,
                        'start_date': '2020-01-01',
                        'end_date': '2020-01-31',
                        'counter_report': counter_report_types["tr"].pk,
                    },
                )
                assert resp.status_code == 400

        with freeze_time("2020-02-08"):
            with patch('sushi.views.run_sushi_fetch_attempt_task'):
                resp = clients["master"].post(
                    reverse('sushi-fetch-attempt-list'),
                    {
                        'credentials': credentials.pk,
                        'start_date': '2020-01-01',
                        'end_date': '2020-01-31',
                        'counter_report': counter_report_types["tr"].pk,
                    },
                )
                assert resp.status_code == 201

    def test_detail_available_after_create(
        self, basic1, clients, organizations, platforms, counter_report_types
    ):
        """
        Check that if we create an attempt, it will be available using the same API later.
        This test was created because after introducing default filtering of attempts
        to successful+current, this was not true
        """
        credentials = CredentialsFactory(
            organization=organizations["standalone"], platform=platforms["standalone"],
        )

        with patch('sushi.views.run_sushi_fetch_attempt_task') as task_mock:
            resp = clients["master"].post(
                reverse('sushi-fetch-attempt-list'),
                {
                    'credentials': credentials.pk,
                    'start_date': '2020-01-01',
                    'end_date': '2020-01-31',
                    'counter_report': counter_report_types["tr"].pk,
                },
            )
            assert task_mock.apply_async.call_count == 1
        assert resp.status_code == 201
        create_data = resp.json()
        pk = create_data['pk']
        # now get the details of the attempt using GET
        resp = clients["master"].get(reverse('sushi-fetch-attempt-detail', args=(pk,)))
        assert resp.status_code == 200
        assert resp.json() == create_data

    @pytest.mark.parametrize(
        'batch_present,download_success,contains_data,processing_success,queued,remained,older_than',
        (
            (True, False, False, False, False, True, None),  # has data
            (False, False, False, False, False, False, None),  # all failed
            (False, True, False, False, False, False, None),  # download ok processing failed
            (False, False, False, True, False, False, None),  # download failed processing ok
            (False, True, False, True, False, True, None),  # download ok processing ok
            (False, False, False, False, False, True, -1),  # not old enough
            (False, False, False, False, False, False, 1),  # old enough
        ),
    )
    def test_cleanup(
        self,
        basic1,
        organizations,
        platforms,
        clients,
        users,
        counter_report_types,
        batch_present,
        download_success,
        contains_data,
        processing_success,
        queued,
        remained,
        older_than,
    ):
        batch = (
            ImportBatch.objects.create(
                platform=platforms["standalone"],
                organization=organizations["standalone"],
                report_type=counter_report_types["tr"].report_type,
            )
            if batch_present
            else None
        )

        credentials = CredentialsFactory(
            organization=organizations["standalone"],
            platform=platforms["standalone"],
            counter_version=5,
            url='http://a.b.c/',
        )
        FetchAttemptFactory(
            credentials=credentials,
            start_date='2020-01-01',
            end_date='2020-01-31',
            credentials_version_hash=credentials.version_hash,
            counter_report=counter_report_types["tr"],
            import_batch=batch,
            download_success=download_success,
            contains_data=contains_data,
            queued=queued,
            processing_success=processing_success,
        )

        url = reverse('sushi-fetch-attempt-cleanup')
        params = {"organization": organizations["standalone"].pk}

        if older_than:
            params["older_than"] = (timezone.now() + timedelta(minutes=older_than)).isoformat()

        get_resp = clients["admin2"].get(url, params)
        assert get_resp.status_code == 200

        post_resp = clients["admin2"].post(url, params)
        assert post_resp.status_code == 200

        # is attempt present
        if remained:
            assert get_resp.json() == post_resp.json() == {"count": 0}
            assert SushiFetchAttempt.objects.count() == 1
        else:
            assert get_resp.json() == post_resp.json() == {"count": 1}
            assert SushiFetchAttempt.objects.count() == 0

    @pytest.mark.parametrize(
        ['client', "organization", 'return_code'],
        [
            # particular standalone organization
            ['unauthenticated', "standalone", 401],
            ['invalid', "standalone", 401],
            ['user1', "standalone", 403],
            ['user2', "standalone", 403],
            ['admin2', "standalone", 200],
            ['master', "standalone", 200],
            ['su', "standalone", 200],
            # all organizations (organization not defined)
            ['unauthenticated', None, 401],
            ['invalid', None, 401],
            ['user1', None, 403],
            ['user2', None, 403],
            ['admin2', None, 403],
            ['master', None, 200],
            ['su', None, 200],
            # all organizations (special -1 organization)
            ['unauthenticated', -1, 401],
            ['invalid', -1, 401],
            ['user1', -1, 403],
            ['user2', -1, 403],
            ['admin2', -1, 403],
            ['master', -1, 200],
            ['su', -1, 200],
        ],
    )
    def test_cleanup_permissions(
        self, basic1, client, organization, return_code, organizations, clients,
    ):
        url = reverse('sushi-fetch-attempt-cleanup')
        params = {}
        if organization == -1:
            params = {"organization": "-1"}
        elif organization is not None:
            params = {"organization": organizations["standalone"].pk}

        get_resp = clients[client].get(url, params)
        assert get_resp.status_code == return_code

        post_resp = clients[client].post(url, params)
        assert post_resp.status_code == return_code

    def test_cleanup_queue(
        basic1, organizations, platforms, clients, counter_report_types,
    ):
        credentials = CredentialsFactory(
            organization=organizations["standalone"], platform=platforms["standalone"],
        )

        # Failed chain
        a1 = FetchAttemptFactory(
            credentials=credentials,
            start_date='2020-01-01',
            end_date='2020-01-31',
            credentials_version_hash=credentials.version_hash,
            counter_report=counter_report_types["tr"],
            import_batch=None,
            download_success=True,
            contains_data=False,
            queued=True,
            processing_success=True,
        )
        a1.queue_id = a1.pk
        a1.save()

        a2 = FetchAttemptFactory(
            credentials=credentials,
            start_date='2020-01-01',
            end_date='2020-01-31',
            credentials_version_hash=credentials.version_hash,
            counter_report=counter_report_types["tr"],
            import_batch=None,
            download_success=True,
            contains_data=False,
            queued=True,
            processing_success=True,
            queue_id=a1.queue_id,
            queue_previous=a1,
        )

        a3 = FetchAttemptFactory(
            credentials=credentials,
            start_date='2020-01-01',
            end_date='2020-01-31',
            credentials_version_hash=credentials.version_hash,
            counter_report=counter_report_types["tr"],
            import_batch=None,
            download_success=False,
            contains_data=False,
            queued=False,
            processing_success=True,
            queue_id=a1.queue_id,
            queue_previous=a2,
        )

        # ongoing chain
        b1 = FetchAttemptFactory(
            credentials=credentials,
            start_date='2020-01-01',
            end_date='2020-01-31',
            credentials_version_hash=credentials.version_hash,
            counter_report=counter_report_types["tr"],
            import_batch=None,
            download_success=True,
            contains_data=False,
            queued=True,
            processing_success=True,
        )
        b1.queue_id = b1.pk
        b1.save()

        b2 = FetchAttemptFactory(
            credentials=credentials,
            start_date='2020-01-01',
            end_date='2020-01-31',
            credentials_version_hash=credentials.version_hash,
            counter_report=counter_report_types["tr"],
            import_batch=None,
            download_success=True,
            contains_data=False,
            queued=True,
            processing_success=True,
            queue_id=b1.queue_id,
            queue_previous=b1,
        )

        # non chain
        c1 = FetchAttemptFactory(
            credentials=credentials,
            start_date='2020-01-01',
            end_date='2020-01-31',
            credentials_version_hash=credentials.version_hash,
            counter_report=counter_report_types["tr"],
            import_batch=None,
            download_success=True,
            contains_data=False,
            queued=False,
            processing_success=True,
        )

        assert SushiFetchAttempt.objects.all().count() == 6

        url = reverse('sushi-fetch-attempt-cleanup')

        get_resp = clients["su"].get(url, {})
        assert get_resp.status_code == 200

        post_resp = clients["su"].post(url, {})
        assert post_resp.status_code == 200

        # count = 1 - only unique chains
        assert get_resp.json() == post_resp.json() == {"count": 1}

        # three attempts actually removed
        assert {e.pk for e in SushiFetchAttempt.objects.all()} == {b1.pk, b2.pk, c1.pk}
