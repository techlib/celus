import pytest
from django.urls import reverse

from core.models import UL_ORG_ADMIN, UL_CONS_ADMIN, UL_CONS_STAFF, Identity
from organizations.models import UserOrganization
from sushi.models import SushiCredentials
from organizations.tests.conftest import organizations
from publications.tests.conftest import platforms
from core.tests.conftest import master_client, master_identity, valid_identity, \
    authenticated_client


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

    def test_lock_action_no_permission(self, organizations, platforms, valid_identity,
                                       authenticated_client):
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

    def test_create_action(self, organizations, platforms, valid_identity, authenticated_client,
                           counter_report_type):
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
            }
        )
        assert resp.status_code == 201
        sc = SushiCredentials.objects.get()
        assert sc.last_updated_by == identity.user
        assert sc.active_counter_reports.count() == 1

    def test_edit_action(self, organizations, platforms, valid_identity,
                         authenticated_client):
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations[0],
                                        is_admin=True)
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

    def test_edit_action_locked(self, organizations, platforms, valid_identity,
                                authenticated_client):
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

    def test_edit_action_locked_higher(self, organizations, platforms, valid_identity,
                                       authenticated_client):
        """
        The object is locked with consortium staff level lock, so the organization admin cannot
        edit it
        """
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations[0],
                                        is_admin=True)
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

    def test_edit_action_with_report_types(self, organizations, platforms, valid_identity,
                                           authenticated_client, counter_report_type_named):
        """
        Test changing report types using the API update action works
        """
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations[0],
                                        is_admin=True)
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
            content_type='application/json'
        )
        assert resp.status_code == 200
        credentials.refresh_from_db()
        assert credentials.active_counter_reports.count() == 2
        assert {cr.pk for cr in credentials.active_counter_reports.all()} == \
               {new_rt1.pk, new_rt2.pk}

    def test_destroy_locked_higher(self, organizations, platforms, valid_identity,
                                   authenticated_client):
        """
        The object is locked with consortium staff level lock, so the organization admin cannot
        remove it
        """
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations[0],
                                        is_admin=True)
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

    def test_destroy_locked_lower(self, organizations, platforms, valid_identity,
                                  authenticated_client):
        """
        The object is locked with consortium staff level lock, so the organization admin cannot
        remove it
        """
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations[0],
                                        is_admin=True)
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

