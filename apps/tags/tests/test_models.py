import pytest
from django.db import DatabaseError, IntegrityError
from tags.logic.fake_data import TagClassFactory, TagFactory
from tags.models import AccessibleBy, Tag, TagClass, TaggingBatch, TaggingBatchState, TagScope

from test_fixtures.entities.titles import TitleFactory
from test_fixtures.entities.users import UserFactory
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
class TestTagging:
    @pytest.mark.parametrize(
        ['tag_scope', 'can_tag'],
        [(TagScope.TITLE, True), (TagScope.ORGANIZATION, False), (TagScope.PLATFORM, False)],
    )
    def test_tag_title(self, tag_scope, can_tag):
        """
        Test that tagging works and that only tag with the correct scope can be added to a title
        """
        tag = TagFactory.create(can_assign=AccessibleBy.EVERYBODY, tag_class__scope=tag_scope)
        title = TitleFactory.create()
        assert tag.titles.count() == 0
        user = UserFactory.create()
        if can_tag:
            tag.tag(title, user=user)
            assert tag.titles.count() == 1
            tt = tag.titletag_set.get()
            assert tt.last_updated_by == user
        else:
            with pytest.raises(ValueError):
                tag.tag(title, user=user)


@pytest.mark.django_db
class TestTagClassVisibility:
    @pytest.mark.parametrize(
        [
            'user_key',
            'can_see_u1',
            'can_see_u2',
            'can_see_org2',
            'can_see_org2_admin',
            'can_see_cons',
            'can_see_evbd',
            'can_see_system',
        ],
        [
            ('user1', True, False, False, False, False, True, False),
            ('user2', False, True, True, False, False, True, False),
            ('admin1', False, False, False, False, False, True, False),
            ('admin2', False, False, True, True, False, True, False),
            ('master_admin', False, False, True, True, True, True, False),
            ('master_user', False, False, True, False, False, True, False),
            ('su', False, False, True, True, True, True, False),
        ],
    )
    def test_user_visible_tag_classes(
        self,
        basic1,
        users,
        organizations,
        user_key,
        can_see_u1,
        can_see_u2,
        can_see_evbd,
        can_see_cons,
        can_see_system,
        can_see_org2,
        can_see_org2_admin,
    ):
        """
        Tests that a list of TagClasses visible by the user only contains those where he can create
        tags
        """
        tags = {
            'u1': TagClassFactory.create(owner=users['user1'], can_create_tags=AccessibleBy.OWNER),
            'u2': TagClassFactory.create(owner=users['user2'], can_create_tags=AccessibleBy.OWNER),
            'evbd': TagClassFactory.create(can_create_tags=AccessibleBy.EVERYBODY),
            'org2': TagClassFactory.create(
                owner_org=organizations['standalone'], can_create_tags=AccessibleBy.ORG_USERS
            ),
            'org2_admin': TagClassFactory.create(
                owner_org=organizations['standalone'], can_create_tags=AccessibleBy.ORG_ADMINS
            ),
            'cons': TagClassFactory.create(can_create_tags=AccessibleBy.CONS_ADMINS),
            'system': TagClassFactory.create(can_create_tags=AccessibleBy.SYSTEM),
        }
        user = users[user_key]
        for key, tag_cls in tags.items():
            if locals()[f'can_see_{key}']:
                assert tag_cls in TagClass.objects.user_accessible_tag_classes(
                    user
                ), f'{user_key} should see {key}'
            else:
                assert tag_cls not in TagClass.objects.user_accessible_tag_classes(
                    user
                ), f'{user_key} should not see {key}'

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
    def test_tag_class_create_access(self, basic1, users, user_key, access_permission, can_create):
        org = basic1['organizations']['root']
        assert (
            TagClass.can_set_access_level(users[user_key], access_permission, organization=org)
            == can_create
        )


@pytest.mark.django_db
class TestTagVisibility:
    @pytest.mark.parametrize(
        [
            'user_key',
            'can_see_u1',
            'can_see_u2',
            'can_see_org2',
            'can_see_org2_admin',
            'can_see_cons',
            'can_see_evbd',
            'can_see_system',
        ],
        [
            ('user1', True, False, False, False, False, True, False),
            ('user2', False, True, True, False, False, True, False),
            ('admin1', False, False, False, False, False, True, False),
            ('admin2', False, False, True, True, False, True, False),
            ('master_admin', False, False, True, True, True, True, False),
            ('master_user', False, False, True, False, False, True, False),
            ('su', False, False, True, True, True, True, False),
        ],
    )
    def test_user_visible_tags(
        self,
        basic1,
        users,
        organizations,
        user_key,
        can_see_u1,
        can_see_u2,
        can_see_evbd,
        can_see_cons,
        can_see_system,
        can_see_org2,
        can_see_org2_admin,
    ):
        tags = {
            'u1': TagFactory.create(owner=users['user1'], can_see=AccessibleBy.OWNER),
            'u2': TagFactory.create(owner=users['user2'], can_see=AccessibleBy.OWNER),
            'evbd': TagFactory.create(can_see=AccessibleBy.EVERYBODY),
            'org2': TagFactory.create(
                owner_org=organizations['standalone'], can_see=AccessibleBy.ORG_USERS
            ),
            'org2_admin': TagFactory.create(
                owner_org=organizations['standalone'], can_see=AccessibleBy.ORG_ADMINS
            ),
            'cons': TagFactory.create(can_see=AccessibleBy.CONS_ADMINS),
            'system': TagFactory.create(can_see=AccessibleBy.SYSTEM),
        }
        user = users[user_key]
        for key, tag in tags.items():
            if locals()[f'can_see_{key}']:
                assert tag in Tag.objects.user_accessible_tags(user), f'{user_key} should see {key}'
            else:
                assert tag not in Tag.objects.user_accessible_tags(
                    user
                ), f'{user_key} should not see {key}'

    @pytest.mark.parametrize(
        [
            'user_key',
            'can_assign_u1',
            'can_assign_u2',
            'can_assign_org2',
            'can_assign_org2_admin',
            'can_assign_cons',
            'can_assign_evbd',
            'can_assign_system',
        ],
        [
            ('user1', True, False, False, False, False, True, False),
            ('user2', False, True, True, False, False, True, False),
            ('admin1', False, False, False, False, False, True, False),
            ('admin2', False, False, True, True, False, True, False),
            ('master_admin', False, False, True, True, True, True, False),
            ('master_user', False, False, True, False, False, True, False),
            ('su', False, False, True, True, True, True, False),
        ],
    )
    def test_user_assignable_tags(
        self,
        basic1,
        users,
        organizations,
        user_key,
        can_assign_u1,
        can_assign_u2,
        can_assign_evbd,
        can_assign_cons,
        can_assign_system,
        can_assign_org2,
        can_assign_org2_admin,
    ):
        tags = {
            'u1': TagFactory.create(name='u1', owner=users['user1'], can_assign=AccessibleBy.OWNER),
            'u2': TagFactory.create(name='u2', owner=users['user2'], can_assign=AccessibleBy.OWNER),
            'evbd': TagFactory.create(name='evbd', can_assign=AccessibleBy.EVERYBODY),
            'org2': TagFactory.create(
                name='org2',
                owner_org=organizations['standalone'],
                can_assign=AccessibleBy.ORG_USERS,
            ),
            'org2_admin': TagFactory.create(
                name='org2_admin',
                owner_org=organizations['standalone'],
                can_assign=AccessibleBy.ORG_ADMINS,
            ),
            'cons': TagFactory.create(name='cons', can_assign=AccessibleBy.CONS_ADMINS),
            'system': TagFactory.create(name='system', can_assign=AccessibleBy.SYSTEM),
        }
        user = users[user_key]
        for key, tag in tags.items():
            if locals()[f'can_assign_{key}']:
                assert tag.can_user_assign(user), f'{user_key} should be able to assign {key}'
            else:
                assert not tag.can_user_assign(
                    user
                ), f'{user_key} should not be able to assign {key}'

    @pytest.mark.parametrize(
        [
            'user_key',
            'can_modify_u1',
            'can_modify_u2',
            'can_modify_org2',
            'can_modify_org2_admin',
            'can_modify_cons',
            'can_modify_evbd',
            'can_modify_system',
        ],
        [
            ('user1', True, False, False, False, False, True, False),
            ('user2', False, True, True, False, False, True, False),
            ('admin1', False, False, False, False, False, True, False),
            ('admin2', False, False, True, True, False, True, False),
            ('master_admin', False, False, True, True, True, True, False),
            ('master_user', False, False, True, False, False, True, False),
            ('su', False, False, True, True, True, True, False),
        ],
    )
    def test_user_modifiable_tags(
        self,
        basic1,
        users,
        organizations,
        user_key,
        can_modify_u1,
        can_modify_u2,
        can_modify_evbd,
        can_modify_cons,
        can_modify_system,
        can_modify_org2,
        can_modify_org2_admin,
    ):
        tag_classes = {
            'u1': TagClassFactory.create(
                name='u1', owner=users['user1'], can_create_tags=AccessibleBy.OWNER
            ),
            'u2': TagClassFactory.create(
                name='u2', owner=users['user2'], can_create_tags=AccessibleBy.OWNER
            ),
            'evbd': TagClassFactory.create(name='evbd', can_create_tags=AccessibleBy.EVERYBODY),
            'org2': TagClassFactory.create(
                name='org2',
                owner_org=organizations['standalone'],
                can_create_tags=AccessibleBy.ORG_USERS,
            ),
            'org2_admin': TagClassFactory.create(
                name='org2_admin',
                owner_org=organizations['standalone'],
                can_create_tags=AccessibleBy.ORG_ADMINS,
            ),
            'cons': TagClassFactory.create(name='cons', can_create_tags=AccessibleBy.CONS_ADMINS),
            'system': TagClassFactory.create(name='system', can_create_tags=AccessibleBy.SYSTEM),
        }
        tags = {key: TagFactory.create(tag_class=tc) for key, tc in tag_classes.items()}
        user = users[user_key]
        for key, tag in tags.items():
            if locals()[f'can_modify_{key}']:
                assert tag.can_user_modify(user), f'{user_key} should be able to modify {key}'
            else:
                assert not tag.can_user_modify(
                    user
                ), f'{user_key} should not be able to modify {key}'


@pytest.mark.django_db
class TestTagClassConstraints:
    @pytest.mark.parametrize(['access_level_attr'], [('can_modify',), ('can_create_tags',)])
    @pytest.mark.parametrize(
        ['access_level', 'is_owner_set', 'is_ok'],
        [
            (AccessibleBy.EVERYBODY, False, True),
            (AccessibleBy.EVERYBODY, True, True),
            (AccessibleBy.ORG_USERS, False, True),
            (AccessibleBy.ORG_USERS, True, True),
            (AccessibleBy.ORG_ADMINS, False, True),
            (AccessibleBy.ORG_ADMINS, True, True),
            (AccessibleBy.CONS_ADMINS, False, True),
            (AccessibleBy.CONS_ADMINS, True, True),
            (AccessibleBy.OWNER, False, False),
            (AccessibleBy.OWNER, True, True),
            (AccessibleBy.SYSTEM, False, True),
            (AccessibleBy.SYSTEM, True, True),
        ],
    )
    def test_owner_is_enforced(
        self, basic1, users, access_level_attr, access_level, is_owner_set, is_ok
    ):
        other_access_level_attr = (
            'can_create_tags' if access_level_attr == 'can_modify' else 'can_modify'
        )
        params = {
            access_level_attr: access_level,
            other_access_level_attr: AccessibleBy.EVERYBODY,
            'default_tag_can_see': AccessibleBy.EVERYBODY,
            'default_tag_can_assign': AccessibleBy.EVERYBODY,
        }
        if is_owner_set:
            params['owner'] = users['user1']
        if access_level in AccessibleBy.org_related():
            # we need to fill in the owner_org because of other constraints
            params['owner_org'] = basic1['organizations']['standalone']
        if is_ok:
            TagClass.objects.create(name='Foo', scope=TagScope.TITLE, **params)
        else:
            with pytest.raises(DatabaseError):
                TagClass.objects.create(name='Foo', scope=TagScope.TITLE, **params)

    @pytest.mark.parametrize(['access_level_attr'], [('can_modify',), ('can_create_tags',)])
    @pytest.mark.parametrize(
        ['access_level', 'is_owner_org_set', 'is_ok'],
        [
            (AccessibleBy.EVERYBODY, False, True),
            (AccessibleBy.EVERYBODY, True, False),
            (AccessibleBy.ORG_USERS, False, False),
            (AccessibleBy.ORG_USERS, True, True),
            (AccessibleBy.ORG_ADMINS, False, False),
            (AccessibleBy.ORG_ADMINS, True, True),
            (AccessibleBy.CONS_ADMINS, False, True),
            (AccessibleBy.CONS_ADMINS, True, False),
            (AccessibleBy.OWNER, False, True),
            (AccessibleBy.OWNER, True, False),
            (AccessibleBy.SYSTEM, False, True),
            (AccessibleBy.SYSTEM, True, False),
        ],
    )
    def test_owner_org_is_enforced(
        self, basic1, users, access_level_attr, access_level, is_owner_org_set, is_ok
    ):
        TagClassFactory.create()
        other_access_level_attr = (
            'can_create_tags' if access_level_attr == 'can_modify' else 'can_modify'
        )
        params = {
            access_level_attr: access_level,
            other_access_level_attr: AccessibleBy.EVERYBODY,
            'owner': users['user1'],
        }
        if is_owner_org_set:
            params['owner_org'] = basic1['organizations']['standalone']
        if is_ok:
            TagClass.objects.create(name='Foo', scope=TagScope.TITLE, **params)
        else:
            with pytest.raises(DatabaseError):
                TagClass.objects.create(name='Foo', scope=TagScope.TITLE, **params)


@pytest.mark.django_db
class TestTagConstraints:
    @pytest.mark.parametrize(['access_level_attr'], [('can_see',), ('can_assign',)])
    @pytest.mark.parametrize(
        ['access_level', 'is_owner_set', 'is_ok'],
        [
            (AccessibleBy.EVERYBODY, False, True),
            (AccessibleBy.EVERYBODY, True, True),
            (AccessibleBy.ORG_USERS, False, True),
            (AccessibleBy.ORG_USERS, True, True),
            (AccessibleBy.ORG_ADMINS, False, True),
            (AccessibleBy.ORG_ADMINS, True, True),
            (AccessibleBy.CONS_ADMINS, False, True),
            (AccessibleBy.CONS_ADMINS, True, True),
            (AccessibleBy.OWNER, False, False),
            (AccessibleBy.OWNER, True, True),
            (AccessibleBy.SYSTEM, False, True),
            (AccessibleBy.SYSTEM, True, True),
        ],
    )
    def test_owner_is_enforced(
        self, basic1, users, access_level_attr, access_level, is_owner_set, is_ok
    ):
        tc = TagClassFactory.create()
        other_access_level_attr = 'can_see' if access_level_attr == 'can_assign' else 'can_assign'
        params = {access_level_attr: access_level, other_access_level_attr: AccessibleBy.EVERYBODY}
        if is_owner_set:
            params['owner'] = users['user1']
        if access_level in AccessibleBy.org_related():
            # we need to fill in the owner_org because of other constraints
            params['owner_org'] = basic1['organizations']['standalone']
        if is_ok:
            Tag.objects.create(name='Foo', tag_class=tc, **params)
        else:
            with pytest.raises(DatabaseError):
                Tag.objects.create(name='Foo', tag_class=tc, **params)

    @pytest.mark.parametrize(['access_level_attr'], [('can_see',), ('can_assign',)])
    @pytest.mark.parametrize(
        ['access_level', 'is_owner_org_set', 'is_ok'],
        [
            (AccessibleBy.EVERYBODY, False, True),
            (AccessibleBy.EVERYBODY, True, False),
            (AccessibleBy.ORG_USERS, False, False),
            (AccessibleBy.ORG_USERS, True, True),
            (AccessibleBy.ORG_ADMINS, False, False),
            (AccessibleBy.ORG_ADMINS, True, True),
            (AccessibleBy.CONS_ADMINS, False, True),
            (AccessibleBy.CONS_ADMINS, True, False),
            (AccessibleBy.OWNER, False, True),
            (AccessibleBy.OWNER, True, False),
            (AccessibleBy.SYSTEM, False, True),
            (AccessibleBy.SYSTEM, True, False),
        ],
    )
    def test_owner_org_is_enforced(
        self, basic1, users, access_level_attr, access_level, is_owner_org_set, is_ok
    ):
        tc = TagClassFactory.create()
        other_access_level_attr = 'can_see' if access_level_attr == 'can_assign' else 'can_assign'
        params = {
            access_level_attr: access_level,
            other_access_level_attr: AccessibleBy.EVERYBODY,
            'owner': users['user1'],
        }
        if is_owner_org_set:
            params['owner_org'] = basic1['organizations']['standalone']
        if is_ok:
            Tag.objects.create(name='Foo', tag_class=tc, **params)
        else:
            with pytest.raises(DatabaseError):
                Tag.objects.create(name='Foo', tag_class=tc, **params)


@pytest.mark.django_db
class TestItemTagConstraints:
    @pytest.mark.parametrize(['is_exclusive', 'can_add_two_tags'], [(True, False), (False, True)])
    def test_exclusive_tag_class_constraint(self, is_exclusive, can_add_two_tags, admin_user):
        tc = TagClassFactory.create(exclusive=is_exclusive, scope=TagScope.TITLE)
        tag1, tag2 = TagFactory.create_batch(2, tag_class=tc)
        title = TitleFactory.create()
        tag1.tag(title, admin_user)
        if can_add_two_tags:
            tag2.tag(title, admin_user)
        else:
            with pytest.raises(DatabaseError):
                tag2.tag(title, admin_user)


@pytest.mark.django_db
class TestTaggingBatchConstraints:
    @pytest.mark.parametrize(
        ['state', 'has_tag', 'has_tag_class', 'ok'],
        [
            (TaggingBatchState.INITIAL, True, True, True),
            (TaggingBatchState.INITIAL, True, False, True),
            (TaggingBatchState.INITIAL, False, True, True),
            (TaggingBatchState.INITIAL, False, False, True),
            (TaggingBatchState.IMPORTED, True, True, False),
            (TaggingBatchState.IMPORTED, True, False, True),
            (TaggingBatchState.IMPORTED, False, True, True),
            (TaggingBatchState.IMPORTED, False, False, False),
        ],
    )
    def test_tag_or_tag_class_is_set(self, state, has_tag, has_tag_class, ok):
        data = {'state': state}
        if has_tag:
            data['tag'] = TagFactory.create()
        if has_tag_class:
            data['tag_class'] = TagClassFactory.create()
        if ok:
            TaggingBatch.objects.create(**data)
        else:
            with pytest.raises(IntegrityError):
                TaggingBatch.objects.create(**data)
