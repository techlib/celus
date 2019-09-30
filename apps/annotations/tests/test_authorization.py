import pytest
from django.urls import reverse

from annotations.models import Annotation
from core.tests.conftest import *
from organizations.tests.conftest import organizations


@pytest.mark.now
@pytest.mark.django_db
class TestAuthorization(object):

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

    @pytest.mark.parametrize(['user_type', 'has_access', 'annot_count'],
                             [['no_user', False, 0],
                              ['invalid', False, 0],
                              ['unrelated', True, 0],
                              ['related_user', True, 1],
                              ['related_admin', True, 1],
                              ['master_user', True, 2],
                              ['superuser', True, 2]])
    def test_annotation_read_api_access(self, user_type, has_access, annot_count,
                                        identity_by_user_type, client, organizations,
                                        authentication_headers):
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
            assert resp.status_code == 403

    @pytest.mark.parametrize(['user_type', 'can_create_rel', 'can_create_unrel',
                              'can_create_noorg'],
                             [['no_user', False, False, False],
                              ['invalid', False, False, False],
                              ['unrelated', False, False, False],
                              ['related_user', False, False, False],
                              ['related_admin', True, False, False],
                              ['master_user', True, True, True],
                              ['superuser', True, True, True]])
    def test_annotation_create_api_access(self, user_type, can_create_rel, can_create_unrel,
                                          can_create_noorg,
                                          identity_by_user_type, client, organizations,
                                          authentication_headers):
        identity, org = identity_by_user_type(user_type)
        # test creation of related record
        url = reverse('annotations-list')
        resp = client.post(url, {'organization_id': org.pk, 'platform_id': None,
                                 'subject_cs': 'X', 'subject_en': 'Y'},
                           content_type='application/json',
                           **authentication_headers(identity))
        expected_status_code = 201 if can_create_rel else 403
        assert resp.status_code == expected_status_code
        # test creation of record for unrelated organization
        resp = client.post(url, {'organization_id': organizations[1].pk, 'platform_id': None,
                                 'subject_cs': 'X', 'subject_en': 'Y'},
                           content_type='application/json',
                           **authentication_headers(identity))
        expected_status_code = 201 if can_create_unrel else 403
        assert resp.status_code == expected_status_code
        # test creation of records without organization
        resp = client.post(url, {'organization_id': None, 'platform_id': None,
                                 'subject_cs': 'X', 'subject_en': 'Y'},
                           content_type='application/json',
                           **authentication_headers(identity))
        expected_status_code = 201 if can_create_noorg else 403
        assert resp.status_code == expected_status_code
