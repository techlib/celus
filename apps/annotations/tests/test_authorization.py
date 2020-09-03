import pytest
from django.urls import reverse

from annotations.models import Annotation
from core.tests.conftest import *
from core.models import UL_CONS_ADMIN, UL_ORG_ADMIN, UL_CONS_STAFF
from organizations.tests.conftest import organizations


@pytest.mark.django_db
class TestAuthorization:

    """
    What we should test:

    |               | create       | modify + delete   | read |
    |===============|==============|===================|======|
    | no user       | N            | N                 |  N   |
    | unrelated     | N            | N                 |  N   |
    | related user  | N            | N                 |  Y   |
    | related admin | Y /fixed org | Y /only own level |  Y   |
    | master user   | Y /all       | Y /not superuser  |  Y   |
    | superuser     | Y /all       | Y /all            |  Y   |

    """

    @pytest.mark.parametrize(
        ['user_type', 'has_access', 'annot_count'],
        [
            ['no_user', False, 0],
            ['invalid', False, 0],
            ['unrelated', True, 0],
            ['related_user', True, 1],
            ['related_admin', True, 1],
            ['master_user', True, 2],
            ['superuser', True, 2],
        ],
    )
    def test_annotation_read_api_access(
        self,
        user_type,
        has_access,
        annot_count,
        identity_by_user_type,
        client,
        organizations,
        authentication_headers,
    ):
        identity, org = identity_by_user_type(user_type)
        # now create two annotations - one related to org and one unrelated
        annot1 = Annotation.objects.create(subject='prase', organization=org)
        annot2 = Annotation.objects.create(subject='hroch', organization=organizations[1])
        url = reverse('annotations-list')
        resp = client.get(url, **authentication_headers(identity))
        if has_access:
            assert resp.status_code == 200
            assert len(resp.json()) == annot_count
        else:
            assert resp.status_code in (403, 401)  # depends on auth backend

    @pytest.mark.parametrize(
        ['user_type', 'can_create_rel', 'can_create_unrel', 'can_create_noorg'],
        [
            ['no_user', False, False, False],
            ['invalid', False, False, False],
            ['unrelated', False, False, False],
            ['related_user', False, False, False],
            ['related_admin', True, False, False],
            ['master_user', True, True, True],
            ['superuser', True, True, True],
        ],
    )
    def test_annotation_create_api_access(
        self,
        user_type,
        can_create_rel,
        can_create_unrel,
        can_create_noorg,
        identity_by_user_type,
        client,
        organizations,
        authentication_headers,
    ):
        identity, org = identity_by_user_type(user_type)
        # test creation of related record
        url = reverse('annotations-list')
        resp = client.post(
            url,
            {'organization_id': org.pk, 'platform_id': None, 'subject_cs': 'X', 'subject_en': 'Y'},
            content_type='application/json',
            **authentication_headers(identity),
        )
        expected_status_codes = (201,) if can_create_rel else (403, 401)
        assert resp.status_code in expected_status_codes
        # test creation of record for unrelated organization
        resp = client.post(
            url,
            {
                'organization_id': organizations[1].pk,
                'platform_id': None,
                'subject_cs': 'X',
                'subject_en': 'Y',
            },
            content_type='application/json',
            **authentication_headers(identity),
        )
        expected_status_codes = (201,) if can_create_unrel else (403, 401)
        assert resp.status_code in expected_status_codes
        # test creation of records without organization
        resp = client.post(
            url,
            {'organization_id': None, 'platform_id': None, 'subject_cs': 'X', 'subject_en': 'Y'},
            content_type='application/json',
            **authentication_headers(identity),
        )
        expected_status_codes = (201,) if can_create_noorg else (403, 401)
        assert resp.status_code in expected_status_codes

    @pytest.mark.parametrize(
        ['user_type', 'can_access_unrel', 'can_access_rel', 'can_access_noorg'],
        [
            ['no_user', False, False, False],
            ['invalid', False, False, False],
            ['unrelated', False, False, True],
            ['related_user', False, True, True],
            ['related_admin', False, True, True],
            ['master_user', True, True, True],
            ['superuser', True, True, True],
        ],
    )
    def test_annotation_get_object_api_access(
        self,
        user_type,
        can_access_unrel,
        can_access_rel,
        can_access_noorg,
        identity_by_user_type,
        client,
        organizations,
        authentication_headers,
    ):
        identity, org = identity_by_user_type(user_type)
        # test creation of related record
        annot_rel = Annotation.objects.create(
            subject='foo2', organization=org, owner_level=UL_ORG_ADMIN
        )
        annot_unrel = Annotation.objects.create(
            subject='foo', organization=organizations[1], owner_level=UL_ORG_ADMIN
        )
        annot_noorg = Annotation.objects.create(
            subject='bar', organization=None, owner_level=UL_CONS_ADMIN
        )
        for i, (annot, can) in enumerate(
            (
                (annot_unrel, can_access_unrel),
                (annot_rel, can_access_rel),
                (annot_noorg, can_access_noorg),
            )
        ):
            url = reverse('annotations-detail', args=(annot.pk,))
            resp = client.get(url, **authentication_headers(identity))
            expected_status_codes = (200,) if can else (403, 401, 404)
            assert resp.status_code in expected_status_codes, f'i = {i}'

    @pytest.mark.parametrize(
        [
            'user_type',
            'can_delete_rel_org_admin',
            'can_delete_unrel_org_admin',
            'can_delete_master',
            'can_delete_superadmin',
        ],
        [
            ['no_user', False, False, False, False],
            ['invalid', False, False, False, False],
            ['unrelated', False, False, False, False],
            ['related_user', False, False, False, False],
            ['related_admin', True, False, False, False],
            ['master_user', True, True, True, False],
            ['superuser', True, True, True, True],
        ],
    )
    def test_annotation_delete_api_access(
        self,
        user_type,
        can_delete_rel_org_admin,
        can_delete_unrel_org_admin,
        can_delete_master,
        can_delete_superadmin,
        identity_by_user_type,
        client,
        organizations,
        authentication_headers,
    ):
        identity, org = identity_by_user_type(user_type)
        # test creation of related record
        annot_rel_admin = Annotation.objects.create(
            subject='foo2', organization=org, owner_level=UL_ORG_ADMIN
        )
        annot_unrel_admin = Annotation.objects.create(
            subject='foo', organization=organizations[1], owner_level=UL_ORG_ADMIN
        )
        annot_master = Annotation.objects.create(
            subject='bar', organization=org, owner_level=UL_CONS_STAFF
        )
        annot_super = Annotation.objects.create(
            subject='baz', organization=org, owner_level=UL_CONS_ADMIN
        )
        for i, (annot, can) in enumerate(
            (
                (annot_rel_admin, can_delete_rel_org_admin),
                (annot_unrel_admin, can_delete_unrel_org_admin),
                (annot_master, can_delete_master),
                (annot_super, can_delete_superadmin),
            )
        ):
            url = reverse('annotations-detail', args=(annot.pk,))
            resp = client.delete(url, **authentication_headers(identity))
            expected_status_codes = (204,) if can else (403, 401, 404)
            assert resp.status_code in expected_status_codes, f'i = {i}'

    @pytest.mark.parametrize(
        [
            'user_type',
            'can_modify_rel_org_admin',
            'can_modify_unrel_org_admin',
            'can_modify_master',
            'can_modify_superadmin',
        ],
        [
            ['no_user', False, False, False, False],
            ['invalid', False, False, False, False],
            ['unrelated', False, False, False, False],
            ['related_user', False, False, False, False],
            ['related_admin', True, False, False, False],
            ['master_user', True, True, True, False],
            ['superuser', True, True, True, True],
        ],
    )
    def test_annotation_modify_api_access(
        self,
        user_type,
        can_modify_rel_org_admin,
        can_modify_unrel_org_admin,
        can_modify_master,
        can_modify_superadmin,
        identity_by_user_type,
        client,
        organizations,
        authentication_headers,
    ):
        identity, org = identity_by_user_type(user_type)
        # test creation of related record
        annot_rel_admin = Annotation.objects.create(
            subject='foo2', organization=org, owner_level=UL_ORG_ADMIN
        )
        annot_unrel_admin = Annotation.objects.create(
            subject='foo', organization=organizations[1], owner_level=UL_ORG_ADMIN
        )
        annot_master = Annotation.objects.create(
            subject='bar', organization=org, owner_level=UL_CONS_STAFF
        )
        annot_super = Annotation.objects.create(
            subject='baz', organization=org, owner_level=UL_CONS_ADMIN
        )
        for i, (annot, can) in enumerate(
            (
                (annot_rel_admin, can_modify_rel_org_admin),
                (annot_unrel_admin, can_modify_unrel_org_admin),
                (annot_master, can_modify_master),
                (annot_super, can_modify_superadmin),
            )
        ):
            url = reverse('annotations-detail', args=(annot.pk,))
            resp = client.patch(
                url,
                {'subject': 'XXX'},
                content_type='application/json',
                **authentication_headers(identity),
            )
            expected_status_codes = (200,) if can else (403, 401, 404)
            assert resp.status_code in expected_status_codes, f'i = {i}'

    @pytest.mark.parametrize(
        ['user_type', 'can_set_rel_org', 'can_set_unrel_org', 'can_set_noorg'],
        [
            ['related_admin', True, False, False],
            ['master_user', True, True, True],
            ['superuser', True, True, True],
        ],
    )
    def test_annotation_modify_organization_api_access(
        self,
        user_type,
        can_set_rel_org,
        can_set_unrel_org,
        can_set_noorg,
        identity_by_user_type,
        client,
        organizations,
        authentication_headers,
    ):
        identity, org = identity_by_user_type(user_type)
        # test creation of related record
        annot = Annotation.objects.create(subject='foo', organization=org, owner_level=UL_ORG_ADMIN)
        for i, (can, org_obj) in enumerate(
            ((can_set_rel_org, org), (can_set_unrel_org, organizations[1]), (can_set_noorg, None))
        ):
            url = reverse('annotations-detail', args=(annot.pk,))
            resp = client.patch(
                url,
                {'organization_id': org_obj.id if org_obj else None},
                content_type='application/json',
                **authentication_headers(identity),
            )
            expected_status_codes = (200,) if can else (403, 401, 404)
            assert resp.status_code in expected_status_codes, f'i = {i}'
