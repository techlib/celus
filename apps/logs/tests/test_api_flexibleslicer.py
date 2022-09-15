import pytest
from django.urls import reverse

from core.logic.serialization import b64json
from organizations.models import UserOrganization
from tags.logic.fake_data import TagFactory
from tags.models import TagScope

from test_fixtures.scenarios.basic import users, clients, identities  # noqa


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
        assert not user.is_user_of_master_organization, 'user must be unprivileged'
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
        assert not user.is_user_of_master_organization, 'user must be unprivileged'
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

    @pytest.mark.parametrize('sorted_dim', ['organization', 'platform', 'metric', 'target', 'dim1'])
    @pytest.mark.parametrize('desc', [True, False])
    @pytest.mark.parametrize('col_idx', [0, 1, 2])
    def test_order_by(self, flexible_slicer_test_data, admin_client, desc, col_idx, sorted_dim):
        """
        Test that ordering by both explicit and implicit dimensions works
        """
        rt = flexible_slicer_test_data['report_types'][0]  # type: ReportType
        slicer_def = {
            'primary_dimension': 'organization' if sorted_dim != 'organization' else 'platform',
            'groups': b64json([sorted_dim]),
            'filters': b64json({'report_type': rt.pk}),
        }
        resp = admin_client.get(
            reverse('flexible-slicer-possible-values'), {'dimension': sorted_dim, **slicer_def}
        )
        assert resp.status_code == 200
        groups = resp.json()['values']
        assert len(groups) == 3
        col_name = f'grp-{groups[col_idx][sorted_dim]}'
        sign = '-' if desc else ''
        resp = admin_client.get(
            reverse('flexible-slicer'), {'order_by': f'{sign}{col_name}', **slicer_def}
        )
        assert resp.status_code == 200
        data = resp.json()['results']
        assert len(data) == 3
        if desc:
            assert data[0][col_name] >= data[1][col_name] >= data[2][col_name]
        else:
            assert data[0][col_name] <= data[1][col_name] <= data[2][col_name]

    # tags
    def test_parts_api_with_tags(self, flexible_slicer_test_data, admin_client, admin_user):
        """
        Tests that the /parts/ endpoint for getting possible parts works properly with tag filter
        """
        tag = TagFactory.create(name='my_platforms', tag_class__scope=TagScope.PLATFORM)
        for platform in flexible_slicer_test_data['platforms'][1:]:
            tag.tag(platform, admin_user)
        resp = admin_client.get(
            reverse('flexible-slicer-split-parts'),
            {
                'primary_dimension': 'organization',
                'groups': b64json(['metric']),
                'split_by': b64json(['platform']),
                'filters': b64json({'tag__platform': tag.pk}),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['count'] == 2
        assert len(data['values']) == 2

    @pytest.mark.parametrize('show_zero', [True, False])
    def test_parts_api_with_tag_roll_up(
        self, flexible_slicer_test_data_with_tags, clients, show_zero
    ):
        """
        Test that tag_roll_up is properly applied to the data. Also checks that only visible
        tags are returned.
        """
        resp = clients['su'].get(
            reverse('flexible-slicer'),
            {
                'primary_dimension': 'target',
                'groups': b64json(['metric']),
                'tag_roll_up': 'true',
                'zero_rows': str(show_zero).lower(),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['count'] == (2 if show_zero else 1)
        tags = flexible_slicer_test_data_with_tags['tags']
        assert [row['pk'] for row in data['results']] == (
            [tags[0].pk, tags[2].pk] if show_zero else [tags[0].pk]
        )

    @pytest.mark.parametrize(['sort_desc'], [(True,), (False,)])
    def test_parts_api_with_tag_roll_up_order_by_tag(
        self, flexible_slicer_test_data_with_tags, clients, sort_desc
    ):
        """
        Test that it is possible to sort by tag when tag_roll_up is used.
        """
        resp = clients['su'].get(
            reverse('flexible-slicer'),
            {
                'primary_dimension': 'target',
                'groups': b64json(['metric']),
                'tag_roll_up': 'true',
                'order_by': ('-' if sort_desc else '') + 'tag',
                'zero_rows': 'true',
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['count'] == 2
        if sort_desc:
            assert data['results'][0]['pk'] == flexible_slicer_test_data_with_tags['tags'][2].pk
        else:
            assert data['results'][0]['pk'] == flexible_slicer_test_data_with_tags['tags'][0].pk

    def test_parts_api_with_tag_roll_up_tag_class_filter(
        self, flexible_slicer_test_data_with_tags, clients
    ):
        """
        Test that tag_class filter works in the api when tag_roll_up is used.
        """
        resp = clients['su'].get(
            reverse('flexible-slicer'),
            {
                'primary_dimension': 'target',
                'groups': b64json(['metric']),
                'tag_roll_up': 'true',
                'zero_rows': 'true',
                'tag_class': flexible_slicer_test_data_with_tags['tag_classes'][0].pk,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['count'] == 1
        assert data['results'][0]['pk'] == flexible_slicer_test_data_with_tags['tags'][0].pk

    @pytest.mark.parametrize(
        ['user_type', 'expected'],
        [
            ('su', 1268406),  # cannot see tag2
            ('admin1', 224514),  # cannot see tag2, can only see org1
            ('admin2', 0),  # can see all tags, remainder should be zero
        ],
    )
    def test_tag_remainder(self, flexible_slicer_test_data_with_tags, user_type, expected, clients):
        """
        Tests the computation of the remaining usage for stuff without any tag

        Primary dimension: title/target
        Group by: metric
        Tag roll-up: True
        """
        metric_pk = flexible_slicer_test_data_with_tags['metrics'][0].pk
        resp = clients[user_type].get(
            reverse('flexible-slicer-remainder'),
            {
                'primary_dimension': 'target',
                'groups': b64json(['metric']),
                'filters': b64json({'metric': [metric_pk]}),
                'tag_roll_up': 'true',
                'zero_rows': 'false',
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data[f'grp-{metric_pk}'] == expected
