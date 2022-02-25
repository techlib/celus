from collections import namedtuple
from io import StringIO

from django.urls import reverse

from core.models import UL_CONS_ADMIN, UL_ORG_ADMIN, UL_CONS_STAFF
from core.tests.conftest import *  # noqa  - test fixtures
from logs.models import ManualDataUpload
from organizations.tests.conftest import *  # noqa  - test fixtures
from publications.tests.conftest import *

from test_fixtures.entities.logs import ManualDataUploadFullFactory


@pytest.fixture()
def mdu_api_post(platforms, report_type_nd, tmp_path, settings, client, authentication_headers):
    def do_it(organization, identity):
        report_type = report_type_nd(0)
        file = StringIO('Source,2019-01\naaaa,9\n')
        settings.MEDIA_ROOT = tmp_path
        response = client.post(
            reverse('manual-data-upload-list'),
            data={
                'platform': platforms[0].id,
                'organization': organization.pk,
                'report_type': report_type.pk,
                'data_file': file,
            },
            **authentication_headers(identity),
        )
        return response

    return do_it


MDUSet = namedtuple('MDUSet', ['rel_admin', 'unrel_admin', 'master', 'super'])


@pytest.fixture()
def mdu_with_user_levels(platforms, report_type_nd, identity_by_user_type, organizations):
    def do_it(org):
        rt = report_type_nd(0)
        mdu_rel_admin = ManualDataUploadFullFactory(
            organization=org, platform=platforms[0], report_type=rt, owner_level=UL_ORG_ADMIN
        )
        mdu_unrel_admin = ManualDataUploadFullFactory(
            organization=organizations[1],
            platform=platforms[0],
            report_type=rt,
            owner_level=UL_ORG_ADMIN,
        )
        mdu_master = ManualDataUploadFullFactory(
            organization=org, platform=platforms[0], report_type=rt, owner_level=UL_CONS_STAFF
        )
        mdu_super = ManualDataUploadFullFactory(
            organization=org, platform=platforms[0], report_type=rt, owner_level=UL_CONS_ADMIN
        )
        return MDUSet(
            rel_admin=mdu_rel_admin, unrel_admin=mdu_unrel_admin, master=mdu_master, super=mdu_super
        )

    return do_it


@pytest.mark.django_db
class TestAuthorization:

    """
    What we should test:

    |               | create       | modify + delete   | read |
    |===============|==============|===================|======|
    | no user       | N            | N                 |  N   |
    | unrelated     | N            | N                 |  N   |
    | related user  | N            | N                 |  Y   |
    | related admin | Y            | Y /only own level |  Y   |
    | master user   | Y            | Y /not superuser  |  Y   |
    | superuser     | Y            | Y /all            |  Y   |

    """

    @pytest.mark.parametrize(
        ['user_type', 'has_access'],
        [
            ['no_user', False],
            ['invalid', False],
            ['unrelated', False],
            ['related_user', False],
            ['related_admin', True],
            ['master_user', True],
            ['superuser', True],
        ],
    )
    def test_mdu_create_access(self, mdu_api_post, user_type, has_access, identity_by_user_type):
        identity, org = identity_by_user_type(user_type)
        resp = mdu_api_post(org, identity)
        if has_access:
            assert resp.status_code == 201
        else:
            assert resp.status_code in (403, 401)  # depends on auth backend

    @pytest.mark.parametrize(
        ['user_type', 'owner_level'],
        [
            ['related_admin', UL_ORG_ADMIN],
            ['master_user', UL_CONS_STAFF],
            ['superuser', UL_CONS_STAFF],
        ],
    )
    def test_mdu_create_owner_level(
        self, mdu_api_post, user_type, owner_level, identity_by_user_type
    ):
        identity, org = identity_by_user_type(user_type)
        resp = mdu_api_post(org, identity)
        assert resp.status_code == 201
        obj = ManualDataUpload.objects.get(pk=resp.json()['pk'])
        assert obj.owner_level == owner_level

    @pytest.mark.parametrize(
        ['user_type', 'can_access_unrel', 'can_access_rel'],
        [
            ['no_user', False, False],
            ['invalid', False, False],
            ['unrelated', False, False],
            ['related_user', False, True],
            ['related_admin', False, True],
            ['master_user', True, True],
            ['superuser', True, True],
        ],
    )
    def test_mdu_get_object_api_access(
        self,
        user_type,
        can_access_unrel,
        can_access_rel,
        identity_by_user_type,
        client,
        organizations,
        authentication_headers,
        platforms,
        report_type_nd,
    ):
        identity, org = identity_by_user_type(user_type)
        rt = report_type_nd(0)
        mdu_rel = ManualDataUploadFullFactory(
            organization=org, platform=platforms[0], report_type=rt, owner_level=UL_ORG_ADMIN
        )
        mdu_unrel = ManualDataUploadFullFactory(
            organization=organizations[1],
            platform=platforms[0],
            report_type=rt,
            owner_level=UL_ORG_ADMIN,
        )
        for i, (mdu, can) in enumerate(((mdu_unrel, can_access_unrel), (mdu_rel, can_access_rel))):
            url = reverse('manual-data-upload-detail', args=(mdu.pk,))
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
    def test_mdu_delete_api_access(
        self,
        user_type,
        can_delete_rel_org_admin,
        can_delete_unrel_org_admin,
        can_delete_master,
        can_delete_superadmin,
        identity_by_user_type,
        client,
        authentication_headers,
        mdu_with_user_levels,
    ):
        identity, org = identity_by_user_type(user_type)
        mdu_set = mdu_with_user_levels(org)
        for i, (mdu, can) in enumerate(
            (
                (mdu_set.rel_admin, can_delete_rel_org_admin),
                (mdu_set.unrel_admin, can_delete_unrel_org_admin),
                (mdu_set.master, can_delete_master),
                (mdu_set.super, can_delete_superadmin),
            )
        ):
            url = reverse('manual-data-upload-detail', args=(mdu.pk,))
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
        authentication_headers,
        platforms,
        mdu_with_user_levels,
    ):
        identity, org = identity_by_user_type(user_type)
        mdu_set = mdu_with_user_levels(org)
        for i, (mdu, can) in enumerate(
            (
                (mdu_set.rel_admin, can_modify_rel_org_admin),
                (mdu_set.unrel_admin, can_modify_unrel_org_admin),
                (mdu_set.master, can_modify_master),
                (mdu_set.super, can_modify_superadmin),
            )
        ):
            url = reverse('manual-data-upload-detail', args=(mdu.pk,))
            resp = client.patch(
                url,
                {'platform': platforms[1].pk},
                content_type='application/json',
                **authentication_headers(identity),
            )
            expected_status_codes = (200,) if can else (403, 401, 404)
            assert resp.status_code in expected_status_codes, f'i = {i}'

    @pytest.mark.parametrize(
        ['user_type', 'can_set_rel_org', 'can_set_unrel_org'],
        [['related_admin', True, False], ['master_user', True, True], ['superuser', True, True]],
    )
    def test_annotation_modify_organization_api_access(
        self,
        user_type,
        can_set_rel_org,
        can_set_unrel_org,
        identity_by_user_type,
        client,
        organizations,
        authentication_headers,
        report_type_nd,
        platforms,
    ):
        identity, org = identity_by_user_type(user_type)
        rt = report_type_nd(0)
        mdu = ManualDataUploadFullFactory(
            organization=org, platform=platforms[0], report_type=rt, owner_level=UL_ORG_ADMIN
        )
        for i, (can, org_obj) in enumerate(
            ((can_set_rel_org, org), (can_set_unrel_org, organizations[1]))
        ):
            url = reverse('manual-data-upload-detail', args=(mdu.pk,))
            resp = client.patch(
                url,
                {'organization_id': org_obj.id},
                content_type='application/json',
                **authentication_headers(identity),
            )
            expected_status_codes = (200,) if can else (403, 401, 404)
            assert resp.status_code in expected_status_codes, f'i = {i}'
