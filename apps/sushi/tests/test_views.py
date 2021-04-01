from unittest.mock import patch

import pytest
from django.urls import reverse

from core.models import UL_ORG_ADMIN, UL_CONS_ADMIN, UL_CONS_STAFF, Identity
from organizations.models import UserOrganization
from sushi.models import SushiCredentials, SushiFetchAttempt
from organizations.tests.conftest import organizations, identity_by_user_type
from publications.tests.conftest import platforms
from core.tests.conftest import (
    master_client,
    master_identity,
    valid_identity,
    authenticated_client,
    authentication_headers,
    admin_identity,
    invalid_identity,
)


@pytest.mark.django_db()
class TestSushiCredentialsViewSet(object):
    def test_lock_action(self, master_client, organizations, platforms):
        credentials = SushiCredentials.objects.create(
            organization=organizations[0],
            platform=platforms[0],
            counter_version=5,
            lock_level=SushiCredentials.UNLOCKED,
        )
        url = reverse('sushi-credentials-lock', args=(credentials.pk,))
        resp = master_client.post(url, {})
        assert resp.status_code == 200
        credentials.refresh_from_db()
        assert credentials.lock_level == UL_CONS_STAFF

    def test_lock_action_no_permission(
        self, organizations, platforms, valid_identity, authenticated_client
    ):
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations[0])
        credentials = SushiCredentials.objects.create(
            organization=organizations[0],
            platform=platforms[0],
            counter_version=5,
            lock_level=UL_CONS_STAFF,
        )
        url = reverse('sushi-credentials-lock', args=(credentials.pk,))
        resp = authenticated_client.post(url, {})
        assert resp.status_code == 403
        credentials.refresh_from_db()
        assert credentials.lock_level == UL_CONS_STAFF

    def test_create_action(
        self, organizations, platforms, valid_identity, authenticated_client, counter_report_type
    ):
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations[0])

        url = reverse('sushi-credentials-list')
        resp = authenticated_client.post(
            url,
            {
                'platform_id': platforms[0].pk,
                'organization_id': organizations[0].pk,
                'url': 'http://foo.bar.baz',
                'requestor_id': 'xxxxxxx',
                'customer_id': 'yyyyy',
                'counter_version': '5',
                'active_counter_reports': [counter_report_type.pk],
            },
        )
        assert resp.status_code == 201
        sc = SushiCredentials.objects.get()
        assert sc.last_updated_by == identity.user
        assert sc.active_counter_reports.count() == 1

    def test_edit_action(self, organizations, platforms, valid_identity, authenticated_client):
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        UserOrganization.objects.create(
            user=identity.user, organization=organizations[0], is_admin=True
        )
        credentials = SushiCredentials.objects.create(
            organization=organizations[0],
            platform=platforms[0],
            counter_version=5,
            lock_level=UL_ORG_ADMIN,
            url='http://a.b.c/',
        )
        url = reverse('sushi-credentials-detail', args=(credentials.pk,))
        new_url = 'http://x.y.com/'
        resp = authenticated_client.patch(url, {'url': new_url}, content_type='application/json')
        assert resp.status_code == 200
        credentials.refresh_from_db()
        assert credentials.url == new_url

    def test_edit_action_locked(
        self, organizations, platforms, valid_identity, authenticated_client
    ):
        """
        The API for updating sushi credentials is accessed by a normal user and thus permission
        denied is returned
        """
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations[0])
        credentials = SushiCredentials.objects.create(
            organization=organizations[0],
            platform=platforms[0],
            counter_version=5,
            lock_level=UL_ORG_ADMIN,
            url='http://a.b.c/',
        )
        url = reverse('sushi-credentials-detail', args=(credentials.pk,))
        new_url = 'http://x.y.com/'
        resp = authenticated_client.patch(url, {'url': new_url}, content_type='application/json')
        assert resp.status_code == 403

    def test_edit_action_locked_higher(
        self, organizations, platforms, valid_identity, authenticated_client
    ):
        """
        The object is locked with consortium staff level lock, so the organization admin cannot
        edit it
        """
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        UserOrganization.objects.create(
            user=identity.user, organization=organizations[0], is_admin=True
        )
        credentials = SushiCredentials.objects.create(
            organization=organizations[0],
            platform=platforms[0],
            counter_version=5,
            lock_level=UL_CONS_STAFF,
            url='http://a.b.c/',
        )
        url = reverse('sushi-credentials-detail', args=(credentials.pk,))
        new_url = 'http://x.y.com/'
        resp = authenticated_client.patch(url, {'url': new_url}, content_type='application/json')
        assert resp.status_code == 403

    def test_edit_action_with_report_types(
        self,
        organizations,
        platforms,
        valid_identity,
        authenticated_client,
        counter_report_type_named,
    ):
        """
        Test changing report types using the API update action works
        """
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        UserOrganization.objects.create(
            user=identity.user, organization=organizations[0], is_admin=True
        )
        credentials = SushiCredentials.objects.create(
            organization=organizations[0],
            platform=platforms[0],
            counter_version=5,
            lock_level=UL_ORG_ADMIN,
            url='http://a.b.c/',
        )
        url = reverse('sushi-credentials-detail', args=(credentials.pk,))
        new_rt1 = counter_report_type_named('new1')
        new_rt2 = counter_report_type_named('new2')
        resp = authenticated_client.patch(
            url,
            {'active_counter_reports': [new_rt1.pk, new_rt2.pk]},
            content_type='application/json',
        )
        assert resp.status_code == 200
        credentials.refresh_from_db()
        assert credentials.active_counter_reports.count() == 2
        assert {cr.pk for cr in credentials.active_counter_reports.all()} == {
            new_rt1.pk,
            new_rt2.pk,
        }

    def test_destroy_locked_higher(
        self, organizations, platforms, valid_identity, authenticated_client
    ):
        """
        The object is locked with consortium staff level lock, so the organization admin cannot
        remove it
        """
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        UserOrganization.objects.create(
            user=identity.user, organization=organizations[0], is_admin=True
        )
        credentials = SushiCredentials.objects.create(
            organization=organizations[0],
            platform=platforms[0],
            counter_version=5,
            lock_level=UL_CONS_STAFF,
            url='http://a.b.c/',
        )
        url = reverse('sushi-credentials-detail', args=(credentials.pk,))
        assert SushiCredentials.objects.count() == 1
        resp = authenticated_client.delete(url)
        assert resp.status_code == 403
        assert SushiCredentials.objects.count() == 1

    def test_destroy_locked_lower(
        self, organizations, platforms, valid_identity, authenticated_client
    ):
        """
        The object is locked with consortium staff level lock, so the organization admin cannot
        remove it
        """
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        UserOrganization.objects.create(
            user=identity.user, organization=organizations[0], is_admin=True
        )
        credentials = SushiCredentials.objects.create(
            organization=organizations[0],
            platform=platforms[0],
            counter_version=5,
            lock_level=UL_ORG_ADMIN,
            url='http://a.b.c/',
        )
        url = reverse('sushi-credentials-detail', args=(credentials.pk,))
        assert SushiCredentials.objects.count() == 1
        resp = authenticated_client.delete(url)
        assert resp.status_code == 204
        assert SushiCredentials.objects.count() == 0


@pytest.mark.django_db()
class TestSushiFetchAttemptStatsView(object):
    def test_no_dates_mode_all(
        self, organizations, platforms, counter_report_type_named, master_client
    ):
        """
        Test that the api view works when the requested data does not contain dates and all
        attempts are requested
        """
        credentials = SushiCredentials.objects.create(
            organization=organizations[0],
            platform=platforms[0],
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
        resp = master_client.get(url + '?mode=all')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]['failure_count'] == 1

    def test_no_dates_mode_current(
        self, organizations, platforms, counter_report_type_named, master_client
    ):
        """
        Test that the api view works when the requested data does not contain dates and all
        attempts are requested
        """
        credentials = SushiCredentials.objects.create(
            organization=organizations[0],
            platform=platforms[0],
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
        resp = master_client.get(url + '?mode=current')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 0

    def test_no_dates_mode_current_2(
        self, organizations, platforms, counter_report_type_named, master_client
    ):
        """
        Test that the api view works when the requested data does not contain dates and all
        attempts are requested
        """
        credentials = SushiCredentials.objects.create(
            organization=organizations[0],
            platform=platforms[0],
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
        resp = master_client.get(url + '?mode=current')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]['failure_count'] == 1
        # let's check that with mode=all there would be two
        resp = master_client.get(url + '?mode=all')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]['failure_count'] == 2

    def test_no_dates_mode_success_and_current(
        self, organizations, platforms, counter_report_type_named, master_client
    ):
        """
        Test that the api view works when the requested data does not contain dates and all
        attempts are requested
        """
        credentials = SushiCredentials.objects.create(
            organization=organizations[0],
            platform=platforms[0],
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
        resp = master_client.get(url + '?mode=success_and_current&success_metric=contains_data')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]['success_count'] == 1
        assert data[0]['failure_count'] == 1
        # let's check that with mode=current there would be only one
        resp = master_client.get(url + '?mode=current&success_metric=contains_data')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]['success_count'] == 0
        assert data[0]['failure_count'] == 1
        # let's check that with mode=all there would be three
        resp = master_client.get(url + '?mode=all&success_metric=contains_data')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]['success_count'] == 1
        assert data[0]['failure_count'] == 2


@pytest.mark.django_db()
class TestSushiFetchAttemptView(object):
    def test_create(self, master_client, credentials, counter_report_type):
        # we must patch the run_sushi_fetch_attempt_task task in order to prevent stalling
        # during tests by CI
        with patch('sushi.views.run_sushi_fetch_attempt_task') as task_mock:
            resp = master_client.post(
                reverse('sushi-fetch-attempt-list'),
                {
                    'credentials': credentials.pk,
                    'start_date': '2020-01-01',
                    'end_date': '2020-01-31',
                    'counter_report': counter_report_type.pk,
                },
            )
            assert task_mock.apply_async.call_count == 1
            assert resp.status_code == 201
            assert 'pk' in resp.json()

    @pytest.mark.parametrize(
        ['user_type', 'can_create', 'return_code'],
        [
            ['no_user', False, 403],
            ['invalid', False, 403],
            ['unrelated', False, 403],
            ['related_user', False, 403],
            ['related_admin', True, 201],
            ['master_user', True, 201],
            ['superuser', True, 201],
        ],
    )
    def test_create_api_access(
        self,
        user_type,
        can_create,
        return_code,
        client,
        authentication_headers,
        credentials,
        counter_report_type,
        identity_by_user_type,
    ):
        identity, org = identity_by_user_type(user_type)

        with patch('sushi.views.run_sushi_fetch_attempt_task') as task_mock:
            resp = client.post(
                reverse('sushi-fetch-attempt-list'),
                {
                    'credentials': credentials.pk,
                    'start_date': '2020-01-01',
                    'end_date': '2020-01-31',
                    'counter_report': counter_report_type.pk,
                },
                **authentication_headers(identity),
            )
            assert resp.status_code == return_code
            if can_create:
                assert task_mock.apply_async.call_count == 1
            else:
                assert task_mock.apply_async.call_count == 0

    def test_detail_available_after_create(self, master_client, credentials, counter_report_type):
        """
        Check that if we create an attempt, it will be available using the same API later.
        This test was created because after introducing default filtering of attempts
        to successful+current, this was not true
        """
        with patch('sushi.views.run_sushi_fetch_attempt_task') as task_mock:
            resp = master_client.post(
                reverse('sushi-fetch-attempt-list'),
                {
                    'credentials': credentials.pk,
                    'start_date': '2020-01-01',
                    'end_date': '2020-01-31',
                    'counter_report': counter_report_type.pk,
                },
            )
            assert task_mock.apply_async.call_count == 1
        assert resp.status_code == 201
        create_data = resp.json()
        pk = create_data['pk']
        # now get the details of the attempt using GET
        resp = master_client.get(reverse('sushi-fetch-attempt-detail', args=(pk,)))
        assert resp.status_code == 200
        assert resp.json() == create_data
