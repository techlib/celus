import pytest
from django.urls import reverse

from core.models import DataSource
from tags.logic.fake_data import TagClassFactory, TagFactory, TagForTitleFactory
from tags.models import AccessibleBy, Tag, TagClass, TagScope
from test_fixtures.entities.organizations import OrganizationFactory
from test_fixtures.entities.platforms import PlatformFactory
from test_fixtures.entities.titles import TitleFactory
from test_fixtures.scenarios.basic import (  # noqa - fixtures
    basic1,
    clients,
    data_sources,
    identities,
    organizations,
    platforms,
    users,
)


@pytest.mark.django_db
class TestTagViews:
    def test_tag_list(self, clients, users):
        user = users['user1']
        TagFactory.create_batch(2, can_see=AccessibleBy.EVERYBODY)
        TagFactory.create_batch(4, can_see=AccessibleBy.OWNER, owner=user)
        TagFactory.create_batch(8, can_see=AccessibleBy.OWNER, owner=users['user2'])
        resp = clients['user1'].get(reverse('tag-list'))
        assert resp.status_code == 200
        assert len(resp.json()) == 6, 'everybody + self owned'

    @pytest.mark.parametrize(
        ['scope', 'tag_count'],
        [(TagScope.TITLE, 8), (TagScope.ORGANIZATION, 4), (TagScope.PLATFORM, 2)],
    )
    def test_tag_list_by_scope(self, clients, users, scope, tag_count):
        TagFactory.create_batch(2, tag_class__scope=TagScope.PLATFORM)
        TagFactory.create_batch(4, tag_class__scope=TagScope.ORGANIZATION)
        TagFactory.create_batch(8, tag_class__scope=TagScope.TITLE)
        resp = clients['user1'].get(reverse('tag-list'), {'scope': scope})
        assert resp.status_code == 200
        assert len(resp.json()) == tag_count

    @pytest.mark.parametrize(['assignable_only'], [(True,), (False,)])
    def test_tag_list_assignable_only(self, clients, users, assignable_only):
        user = users['user1']
        TagFactory.create_batch(
            2, can_see=AccessibleBy.EVERYBODY, can_assign=AccessibleBy.EVERYBODY
        )
        TagFactory.create_batch(
            4, can_see=AccessibleBy.OWNER, can_assign=AccessibleBy.OWNER, owner=user
        )
        TagFactory.create_batch(
            8, can_see=AccessibleBy.EVERYBODY, can_assign=AccessibleBy.OWNER, owner=users['user2']
        )
        params = {}
        if assignable_only:
            params['assignable_only'] = 1
        resp = clients['user1'].get(reverse('tag-list'), params)
        assert resp.status_code == 200
        if assignable_only:
            assert len(resp.json()) == 6, 'assignable by everybody + self owned'
        else:
            assert len(resp.json()) == 14, 'visible by everybody + self owned'

    def test_tag_list_user_access_attr(self, clients, users):
        """
        Test that the list returned by tag list api contains the access params related to the
        current user
        """
        user = users['user1']
        TagFactory.create_batch(2, can_assign=AccessibleBy.OWNER, owner=users['user2'])
        TagFactory.create_batch(4, can_assign=AccessibleBy.OWNER, owner=user)
        TagFactory.create_batch(8, can_assign=AccessibleBy.EVERYBODY)
        resp = clients['user1'].get(reverse('tag-list'))
        assert resp.status_code == 200
        assert len(resp.json()) == 14, 'can see all the tags'
        assert len([tag for tag in resp.json() if tag['user_can_assign']]) == 12

    def test_tag_tagged_titles(self, clients, users):
        user = users['user1']
        tag = TagForTitleFactory.create(can_see=AccessibleBy.EVERYBODY)
        for title in TitleFactory.create_batch(5):
            tag.tag(title, user)

        resp = clients['user1'].get(reverse('tagged-titles-list', args=[tag.pk]))
        assert resp.status_code == 200
        data = resp.json()
        assert data['count'] == 5
        assert len(data['results']) == 5

    def test_tag_tagged_platforms(self, clients, users, basic1):
        user = users['user1']
        tag = TagFactory.create(can_see=AccessibleBy.EVERYBODY, tag_class__scope=TagScope.PLATFORM)
        for platform in PlatformFactory.create_batch(5):
            tag.tag(platform, user)
        foreign_source, _ = DataSource.objects.get_or_create(
            type=DataSource.TYPE_ORGANIZATION, organization=basic1['organizations']['root']
        )
        for platform in PlatformFactory.create_batch(3, source=foreign_source):
            tag.tag(platform, users['user2'])

        resp = clients['user1'].get(reverse('tagged-platforms-list', args=[tag.pk]))
        assert resp.status_code == 200
        data = resp.json()
        assert data['count'] == 5, 'sees only accessible platforms'
        assert len(data['results']) == 5, 'sees only accessible platforms'

    def test_tag_tagged_organizations(self, clients, users, basic1):
        tag = TagFactory.create(
            can_see=AccessibleBy.EVERYBODY, tag_class__scope=TagScope.ORGANIZATION
        )
        for org in basic1['organizations'].values():
            tag.tag(org, users['su'])

        resp = clients['user1'].get(reverse('tagged-organizations-list', args=[tag.pk]))
        assert resp.status_code == 200
        data = resp.json()
        assert data['count'] == 1, 'can see only 1 assigned organization'
        assert len(data['results']) == 1, 'can see only 1 assigned organization'

    def test_get_item_tags(self, clients, users):
        user = users['user1']
        title = TitleFactory.create()
        tags = TagForTitleFactory.create_batch(4, can_see=AccessibleBy.EVERYBODY)
        # more tags - the ones below will not be assigned
        TagForTitleFactory.create_batch(8, can_see=AccessibleBy.EVERYBODY)
        for tag in tags:
            tag.tag(title, user)
        resp = clients['user1'].get(
            reverse('tag-list'), {'item_type': 'title', 'item_id': title.pk}
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 4, 'only the 4 related tags should be there'

    def test_get_item_tags_many_items(self, clients, users):
        user = users['user1']
        titles = TitleFactory.create_batch(10)
        tags = TagForTitleFactory.create_batch(4, can_see=AccessibleBy.EVERYBODY)
        # more tags - the ones below will not be assigned
        TagForTitleFactory.create_batch(8, can_see=AccessibleBy.EVERYBODY)
        for i, tag in enumerate(tags):
            for title in titles[: i + 1]:
                tag.tag(title, user)
        resp = clients['user1'].get(
            reverse('tag-list'), {'item_type': 'title', 'item_id': [t.pk for t in titles]}
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 4, 'only the 4 related tags should be there'

    @pytest.mark.parametrize(
        ['send_item_id', 'send_item_type', 'ok'],
        [(True, True, True), (False, False, True), (True, False, False), (False, True, False)],
    )
    def test_get_item_tags_param_handling(self, clients, users, send_item_id, send_item_type, ok):
        """
        Test that the endpoint properly handles filtering by `item_id` by requiring
        both id and type or none of them
        """
        title = TitleFactory.create()
        params = {}
        if send_item_id:
            params['item_id'] = title.pk
        if send_item_type:
            params['item_type'] = 'title'
        resp = clients['user1'].get(reverse('tag-list'), params)
        assert resp.status_code == 200 if ok else 400

    def test_create_tag(self, clients, users):
        tc = TagClassFactory.create(can_create_tags=AccessibleBy.EVERYBODY)
        resp = clients['user1'].post(reverse('tag-list'), data={"name": "FOO", "tag_class": tc.pk})
        assert resp.status_code == 201
        pk = resp.json()['pk']
        tag = Tag.objects.get(pk=pk)
        assert tag.last_updated_by == users['user1']
        assert tag.owner == users['user1']

    def test_create_tag_no_access(self, clients, users):
        # the class belongs to someone else
        tc = TagClassFactory.create(can_create_tags=AccessibleBy.OWNER, owner=users['user2'])
        resp = clients['user1'].post(reverse('tag-list'), data={"name": "FOO", "tag_class": tc.pk})
        assert resp.status_code == 403

    @pytest.mark.parametrize(
        ['user_key', 'can_create_tag'],
        [
            ('user1', False),
            ('user2', False),
            ('admin1', False),
            ('admin2', True),
            ('master_admin', True),
            ('master_user', False),
            ('su', True),
        ],
    )
    def test_create_tag_permissions(
        self, basic1, clients, users, organizations, user_key, can_create_tag
    ):
        """
        Most of this should be tested on model level, but we test it here at least for one type
        anyway to make sure that the API responds correctly.
        """
        tc = TagClassFactory.create(
            can_create_tags=AccessibleBy.ORG_ADMINS, owner_org=organizations['standalone']
        )
        resp = clients[user_key].post(reverse('tag-list'), data={"name": "FOO", "tag_class": tc.pk})
        assert resp.status_code == (201 if can_create_tag else 403)

    @pytest.mark.parametrize(
        ['user_key', 'can_update_tag'],
        [
            ('user1', False),
            ('user2', False),
            ('admin1', False),
            ('admin2', True),
            ('master_admin', True),
            ('master_user', False),
            ('su', True),
        ],
    )
    def test_update_tag_permissions(
        self, basic1, clients, users, organizations, user_key, can_update_tag
    ):
        """
        Most of this should be tested on model level, but we test it here at least for one type
        anyway to make sure that the API responds correctly.
        """
        tc = TagClassFactory.create(
            can_create_tags=AccessibleBy.ORG_ADMINS, owner_org=organizations['standalone']
        )
        tag = TagFactory.create(tag_class=tc, name='FOO')
        resp = clients[user_key].patch(reverse('tag-detail', args=[tag.pk]), data={'name': 'BAR'})
        assert resp.status_code == (200 if can_update_tag else 403)
        tag.refresh_from_db()
        if can_update_tag:
            assert tag.name == 'BAR', 'name was updated'
        else:
            assert tag.name == 'FOO', "name wasn't updated"

    def test_update_tag_cannot_change_class(self, basic1, clients, users, organizations):
        """
        Test that `tag_class` cannot be changed during tag update
        """
        tc1 = TagClassFactory.create(can_create_tags=AccessibleBy.EVERYBODY)
        tc2 = TagClassFactory.create(can_create_tags=AccessibleBy.EVERYBODY)
        tag = TagFactory.create(tag_class=tc1)
        resp = clients['user1'].patch(
            reverse('tag-detail', args=[tag.pk]), data={'tag_class': tc2.pk}
        )
        assert resp.status_code == 400, 'class update is not supported'

    def test_update_tag(self, basic1, clients, users, organizations):
        """
        Test that `tag_class` cannot be changed during tag update
        """
        tag = TagFactory.create(
            name='A',
            text_color='#aabbcc',
            bg_color='#001122',
            can_see=AccessibleBy.EVERYBODY,
            can_assign=AccessibleBy.EVERYBODY,
            desc='AAA',
        )
        new_data = dict(
            name='B',
            text_color='#ffeedd',
            bg_color='#221100',
            desc='BBB',
            can_see=AccessibleBy.ORG_ADMINS,
            can_assign=AccessibleBy.OWNER,
            owner_org=organizations['standalone'].pk,
        )
        resp = clients['user1'].patch(reverse('tag-detail', args=[tag.pk]), data=new_data)
        assert resp.status_code == 200
        tag.refresh_from_db()
        for key, value in new_data.items():
            model_value = getattr(tag, key)
            if hasattr(model_value, 'pk'):
                assert model_value.pk == value, f'value of "{key}" was updated'
            else:
                assert model_value == value, f'value of "{key}" was updated'
            assert resp.json()[key] == value, f'update value of "{key}" is in json response'

    @pytest.mark.parametrize(
        ['user_key', 'can_delete_tag'],
        [
            ('user1', False),
            ('user2', False),
            ('admin1', False),
            ('admin2', True),
            ('master_admin', True),
            ('master_user', False),
            ('su', True),
        ],
    )
    def test_delete_tag_permissions(
        self, basic1, clients, users, organizations, user_key, can_delete_tag
    ):
        """
        Most of this should be tested on model level, but we test it here at least for one type
        anyway to make sure that the API responds correctly.
        """
        tc = TagClassFactory.create(
            can_create_tags=AccessibleBy.ORG_ADMINS, owner_org=organizations['standalone']
        )
        tag = TagFactory.create(tag_class=tc)
        resp = clients[user_key].delete(reverse('tag-detail', args=[tag.pk]))
        assert resp.status_code == (204 if can_delete_tag else 403)
        if can_delete_tag:
            assert not Tag.objects.filter(pk=tag.pk).exists(), 'tag was deleted'
        else:
            assert Tag.objects.filter(pk=tag.pk).exists(), 'tag was not deleted'


@pytest.mark.django_db
class TestTagging:
    def test_add_tag_to_title(self, clients, users):
        tag = TagForTitleFactory.create()
        title = TitleFactory.create()
        resp = clients['user1'].post(
            reverse('tagged-titles-list', args=[tag.pk]) + 'add/', data={"item_id": title.pk}
        )
        assert resp.status_code == 201

    def test_add_tag_to_title_twice(self, clients, users):
        tag = TagForTitleFactory.create()
        title = TitleFactory.create()
        tag.tag(title, users['user1'])
        resp = clients['user1'].post(
            reverse('tagged-titles-list', args=[tag.pk]) + 'add/', data={"item_id": title.pk}
        )
        assert resp.status_code == 400, "cannot add the same tag twice"

    def test_add_tag_with_exclusive_class(self, clients, users):
        tc = TagClassFactory.create(exclusive=True, scope=TagScope.TITLE)
        tag1, tag2 = TagForTitleFactory.create_batch(2, tag_class=tc)
        title = TitleFactory.create()
        tag1.tag(title, users['user1'])
        resp = clients['user1'].post(
            reverse('tagged-titles-list', args=[tag2.pk]) + 'add/', data={"item_id": title.pk}
        )
        assert resp.status_code == 400, "cannot add another tag of exclusive class"
        assert 'violates' not in resp.json()['error'], 'no raw exception in error output'

    @pytest.mark.parametrize(
        ['user_key', 'can_add_user1_tag', 'can_add_admin_tag'],
        [
            ('user1', True, False),
            ('user2', False, False),
            ('admin1', False, False),
            ('admin2', False, False),
            ('master_admin', False, True),
            ('master_user', False, False),
            ('su', False, True),
        ],
    )
    def test_assign_tag_to_title_permissions(
        self, basic1, clients, users, user_key, can_add_user1_tag, can_add_admin_tag
    ):
        user1_tag = TagForTitleFactory.create(can_assign=AccessibleBy.OWNER, owner=users['user1'])
        admin_tag = TagForTitleFactory.create(can_assign=AccessibleBy.CONS_ADMINS)
        title = TitleFactory.create()
        # user1_tag
        resp = clients[user_key].post(
            reverse('tagged-titles-list', args=[user1_tag.pk]) + 'add/', data={"item_id": title.pk},
        )
        assert resp.status_code == (201 if can_add_user1_tag else 403)
        # admin_tag
        resp = clients[user_key].post(
            reverse('tagged-titles-list', args=[admin_tag.pk]) + 'add/', data={"item_id": title.pk},
        )
        assert resp.status_code == (201 if can_add_admin_tag else 403)

    @pytest.mark.parametrize(
        ['user_key', 'can_remove_user1_tag', 'can_remove_admin_tag'],
        [
            ('user1', True, False),
            ('user2', False, False),
            ('admin1', False, False),
            ('admin2', False, False),
            ('master_admin', False, True),
            ('master_user', False, False),
            ('su', False, True),
        ],
    )
    def test_remove_tag_from_title(
        self, basic1, clients, users, user_key, can_remove_user1_tag, can_remove_admin_tag
    ):
        user1_tag = TagForTitleFactory.create(can_assign=AccessibleBy.OWNER, owner=users['user1'])
        admin_tag = TagForTitleFactory.create(can_assign=AccessibleBy.CONS_ADMINS)
        title = TitleFactory.create()
        user1_tag.tag(title, users['user1'])
        admin_tag.tag(title, users['master_admin'])
        # user1_tag
        resp = clients[user_key].delete(
            reverse('tagged-titles-list', args=[user1_tag.pk]) + 'remove/',
            data={"item_id": title.pk},
        )
        assert resp.status_code == (204 if can_remove_user1_tag else 403)
        # admin_tag
        resp = clients[user_key].delete(
            reverse('tagged-titles-list', args=[admin_tag.pk]) + 'remove/',
            data={"item_id": title.pk},
        )
        assert resp.status_code == (204 if can_remove_admin_tag else 403)

    def test_remove_unconnected_tag_from_title(self, clients, users):
        tag = TagForTitleFactory.create()
        title = TitleFactory.create()
        resp = clients['user1'].delete(
            reverse('tagged-titles-list', args=[tag.pk]) + 'remove/', data={'item_id': title.pk}
        )
        assert resp.status_code == 400

    @pytest.mark.parametrize(
        ['user_key', 'organization', 'can_tag'],
        [
            ('user1', 'branch', True),
            ('user1', 'standalone', False),
            ('user2', 'branch', False),
            ('user2', 'standalone', True),
            ('admin1', 'root', True),
            ('admin1', 'standalone', False),
            ('su', 'root', True),
            ('su', 'standalone', True),
        ],
    )
    def test_organization_tagging(self, clients, users, basic1, user_key, organization, can_tag):
        tag = TagFactory.create(tag_class__scope=TagScope.ORGANIZATION)
        org_obj = basic1['organizations'][organization]
        resp = clients[user_key].post(
            reverse('tagged-organizations-list', args=[tag.pk]) + 'add/',
            data={'item_id': org_obj.pk},
        )
        if can_tag:
            assert resp.status_code == 201
        else:
            assert resp.status_code == 404

    @pytest.mark.parametrize(
        ['platform_type', 'can_tag'],
        [('common', True), ('my-private', True), ('foreign-private', False)],
    )
    def test_platform_tagging(self, clients, users, basic1, platform_type, can_tag):
        tag = TagFactory.create(tag_class__scope=TagScope.PLATFORM)
        if platform_type == 'common':
            source = None
        else:
            orgs = basic1['organizations']
            org = orgs['branch'] if platform_type == 'my-private' else orgs['standalone']
            source, _ = DataSource.objects.get_or_create(
                type=DataSource.TYPE_ORGANIZATION, organization=org
            )
        platform = PlatformFactory.create(source=source)
        resp = clients['user1'].post(
            reverse('tagged-platforms-list', args=[tag.pk]) + 'add/', data={'item_id': platform.pk},
        )
        if can_tag:
            assert resp.status_code == 201
        else:
            assert resp.status_code == 404


@pytest.mark.django_db
class TestTagClassViews:
    def test_tag_class_list(self, clients, users):
        user = users['user1']
        TagClassFactory.create_batch(2, can_create_tags=AccessibleBy.EVERYBODY)
        TagClassFactory.create_batch(4, can_create_tags=AccessibleBy.OWNER, owner=user)
        TagClassFactory.create_batch(8, can_create_tags=AccessibleBy.OWNER, owner=users['user2'])
        resp = clients['user1'].get(reverse('tag-class-list'))
        assert resp.status_code == 200
        assert len(resp.json()) == 6, 'everybody + self owned'

    def test_tag_class_list_user_access_attrs(self, clients, users):
        """
        Only classes for which user can add tags are visible, but the can_modify attr is still
        dependent on the class/user combo, so there should be a `user_can_modify` computed attr
        """
        user = users['user1']
        TagClassFactory.create_batch(
            2, can_create_tags=AccessibleBy.EVERYBODY, can_modify=AccessibleBy.CONS_ADMINS
        )
        TagClassFactory.create_batch(
            4, can_create_tags=AccessibleBy.OWNER, owner=user, can_modify=AccessibleBy.OWNER
        )
        TagClassFactory.create_batch(8, can_create_tags=AccessibleBy.OWNER, owner=users['user2'])
        resp = clients['user1'].get(reverse('tag-class-list'))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 6, 'everybody + self owned'
        assert len([rec for rec in data if rec['user_can_modify']]) == 4
        assert len([rec for rec in data if not rec['user_can_modify']]) == 2

    @pytest.mark.parametrize(['permission_type'], [('can_modify',), ('can_create_tags',)])
    @pytest.mark.parametrize(
        ['user_key', 'access_permission', 'can_create'],
        [
            ('user1', AccessibleBy.EVERYBODY, 0),
            ('admin1', AccessibleBy.EVERYBODY, 0),
            ('admin2', AccessibleBy.EVERYBODY, 0),
            ('master_user', AccessibleBy.EVERYBODY, 0),
            ('master_admin', AccessibleBy.EVERYBODY, 1),
            ('su', AccessibleBy.EVERYBODY, 1),
            ('user1', AccessibleBy.ORG_USERS, 0),
            ('admin1', AccessibleBy.ORG_USERS, 1),
            ('admin2', AccessibleBy.ORG_USERS, 0),  # unrelated admin
            ('master_user', AccessibleBy.ORG_USERS, 0),
            ('master_admin', AccessibleBy.ORG_USERS, 1),
            ('su', AccessibleBy.ORG_USERS, 1),
            ('user1', AccessibleBy.ORG_ADMINS, 0),
            ('admin1', AccessibleBy.ORG_ADMINS, 1),
            ('admin2', AccessibleBy.ORG_ADMINS, 0),
            ('master_user', AccessibleBy.ORG_ADMINS, 0),
            ('master_admin', AccessibleBy.ORG_ADMINS, 1),
            ('su', AccessibleBy.ORG_ADMINS, 1),
            ('user1', AccessibleBy.CONS_ADMINS, 0),
            ('admin1', AccessibleBy.CONS_ADMINS, 0),
            ('admin2', AccessibleBy.CONS_ADMINS, 0),
            ('master_user', AccessibleBy.CONS_ADMINS, 0),
            ('master_admin', AccessibleBy.CONS_ADMINS, 1),
            ('su', AccessibleBy.CONS_ADMINS, 1),
            ('user1', AccessibleBy.OWNER, 1),
            ('admin1', AccessibleBy.OWNER, 1),
            ('admin2', AccessibleBy.OWNER, 1),
            ('master_user', AccessibleBy.OWNER, 1),
            ('master_admin', AccessibleBy.OWNER, 1),
            ('su', AccessibleBy.OWNER, 1),
            ('user1', AccessibleBy.SYSTEM, 0),
            ('admin1', AccessibleBy.SYSTEM, 0),
            ('admin2', AccessibleBy.SYSTEM, 0),
            ('master_user', AccessibleBy.SYSTEM, 0),
            ('master_admin', AccessibleBy.SYSTEM, 0),
            ('su', AccessibleBy.SYSTEM, 0),
        ],
    )
    def test_tag_class_create(
        self, basic1, clients, users, user_key, access_permission, can_create, permission_type
    ):
        org = basic1['organizations']['root']
        data = {'name': 'foo', 'scope': 'title', permission_type: access_permission}
        if access_permission in AccessibleBy.org_related():
            data['owner_org'] = org.pk
        resp = clients[user_key].post(reverse('tag-class-list'), data)
        assert resp.status_code == (201 if can_create else 403)
        if can_create:
            data = resp.json()
            assert data['name'] == 'foo'
            assert data['scope'] == 'title'
            assert data[permission_type] == access_permission

    @pytest.mark.parametrize(
        ['attr', 'old_value', 'new_value', 'can_change'],
        [
            ('name', 'foo', 'bar', True),
            ('scope', 'title', 'platform', False),  # cannot change scope
            ('exclusive', True, False, True),  # can make exclusive to non-exclusive
            ('exclusive', False, True, False),  # cannot change non-exclusive to exclusive
            ('desc', 'XXX', 'YYY', True),
            ('can_modify', AccessibleBy.OWNER, AccessibleBy.CONS_ADMINS, True),
            ('can_create_tags', AccessibleBy.OWNER, AccessibleBy.CONS_ADMINS, True),
            # cannot update access level to something the user cannot assign
            ('can_create_tags', AccessibleBy.OWNER, AccessibleBy.SYSTEM, False),
        ],
    )
    def test_tag_class_update(self, basic1, clients, users, attr, old_value, new_value, can_change):
        """
        Test that only some attrs of tag class can be updated.
        """
        user = users['master_admin']
        params = {
            'name': 'foo',
            'scope': TagScope.TITLE,
            'can_modify': AccessibleBy.OWNER,
            'can_create_tags': AccessibleBy.OWNER,
            'owner': user,
        }
        # overwrite the currently tested attr
        params[attr] = old_value
        tc = TagClassFactory.create(**params)
        new_data = {attr: new_value}
        resp = clients['master_admin'].patch(reverse('tag-class-detail', args=[tc.pk]), new_data)
        assert resp.status_code in ([200] if can_change else [400, 403])
        if can_change:
            data = resp.json()
            assert data[attr] == new_value, f'{attr} was updated'

    @pytest.mark.parametrize(
        ['user_key', 'access_permission', 'can_update'],
        [
            ('user1', AccessibleBy.EVERYBODY, 1),
            ('admin1', AccessibleBy.EVERYBODY, 1),
            ('admin2', AccessibleBy.EVERYBODY, 1),
            ('master_user', AccessibleBy.EVERYBODY, 1),
            ('master_admin', AccessibleBy.EVERYBODY, 1),
            ('su', AccessibleBy.EVERYBODY, 1),
            ('user1', AccessibleBy.ORG_USERS, 0),  # user1 is unrelated
            ('admin1', AccessibleBy.ORG_USERS, 1),
            ('admin2', AccessibleBy.ORG_USERS, 0),  # unrelated admin
            ('master_user', AccessibleBy.ORG_USERS, 1),
            ('master_admin', AccessibleBy.ORG_USERS, 1),
            ('su', AccessibleBy.ORG_USERS, 1),
            ('user1', AccessibleBy.ORG_ADMINS, 0),
            ('admin1', AccessibleBy.ORG_ADMINS, 1),
            ('admin2', AccessibleBy.ORG_ADMINS, 0),
            ('master_user', AccessibleBy.ORG_ADMINS, 0),
            ('master_admin', AccessibleBy.ORG_ADMINS, 1),
            ('su', AccessibleBy.ORG_ADMINS, 1),
            ('user1', AccessibleBy.CONS_ADMINS, 0),
            ('admin1', AccessibleBy.CONS_ADMINS, 0),
            ('admin2', AccessibleBy.CONS_ADMINS, 0),
            ('master_user', AccessibleBy.CONS_ADMINS, 0),
            ('master_admin', AccessibleBy.CONS_ADMINS, 1),
            ('su', AccessibleBy.CONS_ADMINS, 1),
            ('user1', AccessibleBy.OWNER, 1),
            ('admin1', AccessibleBy.OWNER, 1),
            ('admin2', AccessibleBy.OWNER, 1),
            ('master_user', AccessibleBy.OWNER, 1),
            ('master_admin', AccessibleBy.OWNER, 1),
            ('su', AccessibleBy.OWNER, 1),
            ('user1', AccessibleBy.SYSTEM, 0),
            ('admin1', AccessibleBy.SYSTEM, 0),
            ('admin2', AccessibleBy.SYSTEM, 0),
            ('master_user', AccessibleBy.SYSTEM, 0),
            ('master_admin', AccessibleBy.SYSTEM, 0),
            ('su', AccessibleBy.SYSTEM, 0),
        ],
    )
    def test_tag_class_update_permissions(
        self, basic1, clients, users, user_key, access_permission, can_update
    ):
        user = users[user_key]
        extra = {}
        org = basic1['organizations']['root']
        if access_permission in AccessibleBy.org_related():
            extra['owner_org'] = org
        elif access_permission == AccessibleBy.OWNER:
            extra['owner'] = user
        tc = TagClassFactory.create(
            name='foo', scope='title', can_modify=access_permission, **extra
        )
        new_data = {
            'name': 'bar',
            'can_create_tags': AccessibleBy.OWNER,
            'text_color': '#abcdef',
        }
        resp = clients[user_key].patch(reverse('tag-class-detail', args=[tc.pk]), new_data)
        assert resp.status_code == (200 if can_update else 403)
        if can_update:
            data = resp.json()
            for key, new_value in new_data.items():
                assert data[key] == new_value, f'{key} was updated'

    @pytest.mark.parametrize(
        ['user_key', 'access_permission', 'can_delete'],
        [
            ('user1', AccessibleBy.EVERYBODY, 1),
            ('admin1', AccessibleBy.EVERYBODY, 1),
            ('admin2', AccessibleBy.EVERYBODY, 1),
            ('master_user', AccessibleBy.EVERYBODY, 1),
            ('master_admin', AccessibleBy.EVERYBODY, 1),
            ('su', AccessibleBy.EVERYBODY, 1),
            ('user1', AccessibleBy.ORG_USERS, 0),  # user1 is unrelated
            ('admin1', AccessibleBy.ORG_USERS, 1),
            ('admin2', AccessibleBy.ORG_USERS, 0),  # unrelated admin
            ('master_user', AccessibleBy.ORG_USERS, 1),
            ('master_admin', AccessibleBy.ORG_USERS, 1),
            ('su', AccessibleBy.ORG_USERS, 1),
            ('user1', AccessibleBy.ORG_ADMINS, 0),
            ('admin1', AccessibleBy.ORG_ADMINS, 1),
            ('admin2', AccessibleBy.ORG_ADMINS, 0),
            ('master_user', AccessibleBy.ORG_ADMINS, 0),
            ('master_admin', AccessibleBy.ORG_ADMINS, 1),
            ('su', AccessibleBy.ORG_ADMINS, 1),
            ('user1', AccessibleBy.CONS_ADMINS, 0),
            ('admin1', AccessibleBy.CONS_ADMINS, 0),
            ('admin2', AccessibleBy.CONS_ADMINS, 0),
            ('master_user', AccessibleBy.CONS_ADMINS, 0),
            ('master_admin', AccessibleBy.CONS_ADMINS, 1),
            ('su', AccessibleBy.CONS_ADMINS, 1),
            ('user1', AccessibleBy.OWNER, 1),
            ('admin1', AccessibleBy.OWNER, 1),
            ('admin2', AccessibleBy.OWNER, 1),
            ('master_user', AccessibleBy.OWNER, 1),
            ('master_admin', AccessibleBy.OWNER, 1),
            ('su', AccessibleBy.OWNER, 1),
            ('user1', AccessibleBy.SYSTEM, 0),
            ('admin1', AccessibleBy.SYSTEM, 0),
            ('admin2', AccessibleBy.SYSTEM, 0),
            ('master_user', AccessibleBy.SYSTEM, 0),
            ('master_admin', AccessibleBy.SYSTEM, 0),
            ('su', AccessibleBy.SYSTEM, 0),
        ],
    )
    def test_tag_class_delete(
        self, basic1, clients, users, user_key, access_permission, can_delete
    ):
        user = users[user_key]
        extra = {}
        org = basic1['organizations']['root']
        if access_permission in AccessibleBy.org_related():
            extra['owner_org'] = org
        elif access_permission == AccessibleBy.OWNER:
            extra['owner'] = user
        tc = TagClassFactory.create(
            name='foo', scope='title', can_modify=access_permission, **extra
        )
        resp = clients[user_key].delete(reverse('tag-class-detail', args=[tc.pk]))
        assert resp.status_code == (204 if can_delete else 403)
        if can_delete:
            assert not TagClass.objects.filter(pk=tc.pk).exists(), 'tag class was deleted'
        else:
            assert TagClass.objects.filter(pk=tc.pk).exists(), 'tag class was not deleted'


@pytest.mark.django_db
class TestTagItemsLinksView:
    """
    Tests a view which allows listing all item-tag links for a specific item type.
    """

    def test_list_tags_for_titles(self, clients, users):
        user = users['user1']
        titles = TitleFactory.create_batch(10)
        tags = TagForTitleFactory.create_batch(4, can_see=AccessibleBy.EVERYBODY)
        # more tags - the ones below will not be assigned
        TagForTitleFactory.create_batch(8, can_see=AccessibleBy.EVERYBODY)
        for i, tag in enumerate(tags):
            for title in titles[: i + 1]:
                tag.tag(title, user)
        resp = clients['user1'].get(
            reverse('tag-item-links'), {'item_type': 'title', 'item_id': [t.pk for t in titles]}
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 4 + 3 + 2 + 1, 'there should be 10 links'

    @pytest.mark.parametrize(
        ['user_key', 'org_count'],
        [('user1', 1), ('user2', 1), ('admin1', 2), ('admin2', 1), ('su', 5)],
    )
    def test_list_tags_for_organizations(self, clients, users, basic1, user_key, org_count):
        user = users['user1']
        tags = TagFactory.create_batch(
            4, can_see=AccessibleBy.EVERYBODY, tag_class__scope=TagScope.ORGANIZATION
        )
        organizations = basic1['organizations'].values()
        for tag in tags:
            for org in organizations:
                tag.tag(org, user)
        resp = clients[user_key].get(
            reverse('tag-item-links'),
            {'item_type': 'organization', 'item_id': [org.pk for org in organizations]},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == org_count * 4, 'there should 4 links per visible organization'

    @pytest.mark.parametrize(
        ['user_key', 'platform_count'],
        [('user1', 1), ('user2', 2), ('admin1', 2), ('admin2', 2), ('su', 3)],
    )
    def test_list_tags_for_platforms(self, clients, users, basic1, user_key, platform_count):
        orgs = basic1['organizations']
        source1, _ = DataSource.objects.get_or_create(
            type=DataSource.TYPE_ORGANIZATION, organization=orgs['root']
        )
        source2, _ = DataSource.objects.get_or_create(
            type=DataSource.TYPE_ORGANIZATION, organization=orgs['standalone']
        )
        platforms = [PlatformFactory.create(source=src) for src in [None, source1, source2]]
        tags = TagFactory.create_batch(
            4, can_see=AccessibleBy.EVERYBODY, tag_class__scope=TagScope.PLATFORM
        )
        for tag in tags:
            for platform in platforms:
                tag.tag(platform, users['su'])  # note, the user is irrelevant here
        resp = clients[user_key].get(
            reverse('tag-item-links'),
            {'item_type': 'platform', 'item_id': [p.pk for p in platforms]},
        )
        assert resp.status_code == 200
        assert (
            len(resp.json()) == 4 * platform_count
        ), 'there should be 4 links per visible platform'
