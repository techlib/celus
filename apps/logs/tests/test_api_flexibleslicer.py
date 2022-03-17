import pytest
from django.urls import reverse

from core.logic.serialization import b64json
from organizations.models import UserOrganization

from test_fixtures.scenarios.basic import users  # noqa


@pytest.mark.django_db
class TestSlicerAPI:
    def test_primary_dimension_required(self, flexible_slicer_test_data, admin_client):
        url = reverse('flexible-slicer')
        resp = admin_client.get(url)
        assert resp.status_code == 400
        assert 'error' in resp.json()
        assert resp.json()['error']['code'] == 'E104'

    def test_group_by_required(self, flexible_slicer_test_data, admin_client):
        url = reverse('flexible-slicer')
        resp = admin_client.get(url, {'primary_dimension': 'platform'})
        assert resp.status_code == 400
        assert 'error' in resp.json()
        assert resp.json()['error']['code'] == 'E106'

    def test_user_organization_filtering_no_access(self, flexible_slicer_test_data, users, client):
        """
        Test that organizations in reporting API are properly filtered to only contain those
        accessible by current user.
        """
        user = users['user1']
        assert not user.is_superuser, 'user must be unprivileged'
        assert not user.is_from_master_organization, 'user must be unprivileged'
        client.force_login(user)
        resp = client.get(
            reverse('flexible-slicer'),
            {'primary_dimension': 'organization', 'groups': b64json(['metric'])},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['count'] == 0
        assert len(data['results']) == 0

    def test_user_organization_filtering(self, flexible_slicer_test_data, client, users):
        """
        Test that organizations in reporting API are properly filtered to only contain those
        accessible by current user.
        """
        organization = flexible_slicer_test_data['organizations'][1]
        user = users['user1']
        UserOrganization.objects.create(user=user, organization=organization)
        assert not user.is_superuser, 'user must be unprivileged'
        assert not user.is_from_master_organization, 'user must be unprivileged'
        client.force_login(user)
        resp = client.get(
            reverse('flexible-slicer'),
            {'primary_dimension': 'organization', 'groups': b64json(['metric'])},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['count'] == 1
        assert len(data['results']) == 1
        assert data['results'][0]['pk'] == organization.pk

    def test_parts_api(self, flexible_slicer_test_data, admin_client):
        """
        Tests that the /parts/ endpoint for getting possible parts after splitting works
        """
        resp = admin_client.get(
            reverse('flexible-slicer-split-parts'),
            {
                'primary_dimension': 'organization',
                'groups': b64json(['metric']),
                'split_by': b64json(['platform']),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['count'] == 3
        assert len(data['values']) == 3

    def test_parts_api_with_filter(self, flexible_slicer_test_data, admin_client):
        """
        Tests that the /parts/ endpoint for getting possible parts after splitting works
        """
        pls = flexible_slicer_test_data['platforms']
        resp = admin_client.get(
            reverse('flexible-slicer-split-parts'),
            {
                'primary_dimension': 'organization',
                'groups': b64json(['metric']),
                'split_by': b64json(['platform']),
                'filters': b64json({'platform': [p.pk for p in pls[:2]]}),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['count'] == 2
        assert len(data['values']) == 2

    def test_get_data_with_parts_no_part(self, flexible_slicer_test_data, admin_client):
        """
        Tests that when getting data and `split_by` is active, we need to provide the `part` arg
        """
        pls = flexible_slicer_test_data['platforms']
        resp = admin_client.get(
            reverse('flexible-slicer'),
            {
                'primary_dimension': 'organization',
                'groups': b64json(['metric']),
                'split_by': b64json(['platform']),
                'filters': b64json({'platform': [p.pk for p in pls[:2]]}),
            },
        )
        assert resp.status_code == 400

    def test_get_data_with_parts_part_given(self, flexible_slicer_test_data, admin_client):
        """
        Tests that when getting data and `split_by` is active, we need to provide the `part` arg
        """
        pls = flexible_slicer_test_data['platforms']
        resp = admin_client.get(
            reverse('flexible-slicer'),
            {
                'primary_dimension': 'organization',
                'groups': b64json(['metric']),
                'split_by': b64json(['platform']),
                'filters': b64json({'platform': [p.pk for p in pls[:2]]}),
                'part': b64json([pls[0].pk]),
            },
        )
        assert resp.status_code == 200
