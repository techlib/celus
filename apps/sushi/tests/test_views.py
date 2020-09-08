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
from sushi.models import SushiCredentials, SushiFetchAttempt

from test_fixtures.entities.credentials import CredentialsFactory
from test_fixtures.scenarios.basic import (
    basic1,
    clients,
    data_sources,
    identities,
    organizations,
    platforms,
    users,
    counter_report_types,
    report_types,
)


@pytest.mark.django_db()
class TestSushiCredentialsViewSet:
    def test_lock_action(self, basic1, organizations, platforms, clients):
        credentials = SushiCredentials.objects.create(
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
        credentials = SushiCredentials.objects.create(
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
                'active_counter_reports': [counter_report_types["tr"].pk],
            },
        )
        assert resp.status_code == 201
        sc = SushiCredentials.objects.get()
        assert sc.last_updated_by == users["admin1"]
        assert sc.active_counter_reports.count() == 1
        assert sc.title == title

    def test_edit_action(self, basic1, organizations, platforms, clients):
        credentials = SushiCredentials.objects.create(
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
        credentials = SushiCredentials.objects.create(
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
        credentials = SushiCredentials.objects.create(
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
        credentials = SushiCredentials.objects.create(
            organization=organizations["root"],
            platform=platforms["root"],
            counter_version=5,
            lock_level=UL_ORG_ADMIN,
            url='http://a.b.c/',
        )
        url = reverse('sushi-credentials-detail', args=(credentials.pk,))
        new_rt1 = counter_report_type_named('new1')
        new_rt2 = counter_report_type_named('new2')
        resp = clients["admin1"].patch(url, {'active_counter_reports': [new_rt1.pk, new_rt2.pk]},)
        assert resp.status_code == 200
        credentials.refresh_from_db()
        assert credentials.active_counter_reports.count() == 2
        assert {cr.pk for cr in credentials.active_counter_reports.all()} == {
            new_rt1.pk,
            new_rt2.pk,
        }

    def test_destroy_locked_higher(self, basic1, organizations, platforms, clients):
        """
        The object is locked with consortium staff level lock, so the organization admin cannot
        remove it
        """
        credentials = SushiCredentials.objects.create(
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
        credentials = SushiCredentials.objects.create(
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
        credentials = SushiCredentials.objects.create(
            organization=organizations["empty"],
            platform=platforms["empty"],
            counter_version=5,
            lock_level=UL_ORG_ADMIN,
            url='http://a.b.c/',
        )
        new_rt1 = counter_report_type_named('new1')
        credentials.active_counter_reports.add(new_rt1)
        SushiFetchAttempt.objects.create(
            credentials=credentials,
            start_date='2020-01-01',
            end_date='2020-01-31',
            credentials_version_hash=credentials.version_hash,
            counter_report=new_rt1,
        )
        attempt2 = SushiFetchAttempt.objects.create(
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


@pytest.mark.django_db()
class TestSushiFetchAttemptStatsView:
    def test_no_dates_mode_all(
        self, basic1, organizations, platforms, clients, counter_report_type_named
    ):
        """
        Test that the api view works when the requested data does not contain dates and all
        attempts are requested
        """
        credentials = SushiCredentials.objects.create(
            organization=organizations["empty"],
            platform=platforms["empty"],
            counter_version=5,
            lock_level=UL_ORG_ADMIN,
            url='http://a.b.c/',
        )
        new_rt1 = counter_report_type_named('new1')
        SushiFetchAttempt.objects.create(
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
        credentials = SushiCredentials.objects.create(
            organization=organizations["empty"],
            platform=platforms["empty"],
            counter_version=5,
            lock_level=UL_ORG_ADMIN,
            url='http://a.b.c/',
        )
        new_rt1 = counter_report_type_named('new1')
        SushiFetchAttempt.objects.create(
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
        credentials = SushiCredentials.objects.create(
            organization=organizations["empty"],
            platform=platforms["empty"],
            counter_version=5,
            lock_level=UL_ORG_ADMIN,
            url='http://a.b.c/',
        )
        new_rt1 = counter_report_type_named('new1')
        SushiFetchAttempt.objects.create(
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
        SushiFetchAttempt.objects.create(
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
        credentials = SushiCredentials.objects.create(
            organization=organizations["empty"],
            platform=platforms["empty"],
            counter_version=5,
            lock_level=UL_ORG_ADMIN,
            url='http://a.b.c/',
        )
        new_rt1 = counter_report_type_named('new1')
        # one success
        SushiFetchAttempt.objects.create(
            credentials=credentials,
            start_date='2020-01-01',
            end_date='2020-01-31',
            credentials_version_hash=credentials.version_hash,
            counter_report=new_rt1,
            contains_data=True,
        )
        # one failure
        SushiFetchAttempt.objects.create(
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
        SushiFetchAttempt.objects.create(
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
    def test_create(self, basic1, organizations, platforms, clients, counter_report_types):
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
        SushiFetchAttempt.objects.create(
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
        a1 = SushiFetchAttempt.objects.create(
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

        a2 = SushiFetchAttempt.objects.create(
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

        a3 = SushiFetchAttempt.objects.create(
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
        b1 = SushiFetchAttempt.objects.create(
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

        b2 = SushiFetchAttempt.objects.create(
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
        c1 = SushiFetchAttempt.objects.create(
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
