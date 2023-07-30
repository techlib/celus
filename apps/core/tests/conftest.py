import copy

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from faker import Faker
from organizations.models import Organization

from core.fake_data import MemberFactory, UserFactory
from core.models import Identity
from test_scenarios.basic import *  # noqa

fake = Faker()
fake_first_name = fake.first_name()
fake_last_name = fake.last_name()


NORMAL_USER = settings.MAILCHIMP_REASON_NORMAL_USER
CONSORTIAL_MANAGER = settings.MAILCHIMP_REASON_CONSORTIAL_MANAGER


@pytest.fixture
def preferred_celus_name(settings):
    pref = settings.MAILCHIMP_PREFERRED_CELUS_NAME = 'preferred'
    return pref


@pytest.fixture
def celus_domains(preferred_celus_name):
    this = 'this.celus.net'
    pref = f'{preferred_celus_name}.celus.net'
    other1 = 'other1.celus.net'
    other2 = 'other2.celus.net'
    other3 = 'other3.celus.net'
    other4 = 'other4.celus.net'
    return locals()


@pytest.fixture
def addresses(celus_domains):
    this = f'https://{celus_domains["this"]}/'
    pref = f'https://{celus_domains["pref"]}/'
    other1 = f'https://{celus_domains["other1"]}/'
    other2 = f'https://{celus_domains["other2"]}/'
    other3 = f'https://{celus_domains["other3"]}/'
    other4 = f'https://{celus_domains["other4"]}/'
    empty = ""
    return locals()


@pytest.fixture
def tags(settings):
    DO_NOT_DELETE_TAG = settings.MAILCHIMP_DO_NOT_DELETE_TAG = 1
    STAFF_TAG = settings.MAILCHIMP_STAFF_TAG = 2
    RANDOM_TAG = 3
    del settings
    return locals()


@pytest.fixture
def installations(preferred_celus_name):
    this_normuser = {"name": "this", "reason": NORMAL_USER}
    this_consman = {"name": "this", "reason": CONSORTIAL_MANAGER}
    this_whatever = {"name": "this", "reason": "whatever"}
    this_toolognreason = {"name": "this", "reason": "long reason " * 25}
    other1_normuser = {"name": "other1", "reason": NORMAL_USER}
    other1_consman = {"name": "other1", "reason": CONSORTIAL_MANAGER}
    other1_whatever = {"name": "other1", "reason": "whatever"}
    other2_normuser = {"name": "other2", "reason": NORMAL_USER}
    other3_normuser = {"name": "other3", "reason": NORMAL_USER}
    pref_normuser = {"name": preferred_celus_name, "reason": NORMAL_USER}
    return locals()


@pytest.fixture
def celususers(organizations):
    normuser = UserFactory()
    firstnam_lastnam = UserFactory(first_name=fake_first_name, last_name=fake_last_name)
    consman = UserFactory()
    consman.organizations.add(organizations["master"], through_defaults={'is_admin': True})
    consman.save()
    return locals()


@pytest.fixture
def member(installations, addresses, tags):
    this_normuser_install1_addrs1 = MemberFactory(
        celus_installations=[installations['this_normuser']], celus_address1=addresses['this']
    )
    no_fistnam_no_lastnam_install0_addrs0 = MemberFactory(first_name='', last_name='')

    no_lastnam_this_normuser_install1_addrs1 = MemberFactory(
        first_name=fake_first_name,
        last_name='',
        celus_installations=[installations['this_normuser']],
        celus_address1=addresses['this'],
    )
    no_firstnam_this_normuser_install1_addrs1 = MemberFactory(
        first_name='',
        last_name=fake_last_name,
        celus_installations=[installations['this_normuser']],
        celus_address1=addresses['this'],
    )

    no_fistnam_no_lastnam_this_normuser_install1_addrs1 = MemberFactory(
        first_name='',
        last_name='',
        celus_installations=[installations['this_normuser']],
        celus_address1=addresses['this'],
    )

    this_consman_install1_addrs1 = MemberFactory(
        celus_installations=[installations['this_consman']], celus_address1=addresses['this']
    )
    this_whatever_install1 = MemberFactory(celus_installations=[installations['this_whatever']])
    this_normuser_other_normuser_install2_addrs2 = MemberFactory(
        celus_installations=[installations['this_normuser'], installations['other1_normuser']],
        celus_address1=addresses['this'],
        celus_address2=addresses['other1'],
    )
    this_consman_other_consman_install2_addrs2 = MemberFactory(
        celus_installations=[installations['this_consman'], installations['other1_consman']],
        celus_address1=addresses['this'],
        celus_address2=addresses['other1'],
    )
    this_normuser_other_whatever_install2_addrs1 = MemberFactory(
        celus_installations=[installations['this_normuser'], installations['other1_whatever']],
        celus_address1=addresses['this'],
    )
    this_normuser_this_whatever_install2_addrs1 = MemberFactory(
        celus_installations=[installations['this_normuser'], installations['this_whatever']],
        celus_address1=addresses['this'],
    )
    this_toolongreason_install1_addrs0_staff = MemberFactory(
        celus_installations=[installations['this_toolognreason']], tags=[tags['STAFF_TAG']]
    )
    this_toolongreason_install1_addrs0 = MemberFactory(
        celus_installations=[installations['this_toolognreason']], tags=[tags['RANDOM_TAG']]
    )

    this_normuser_install1_addrs0 = MemberFactory(
        celus_installations=[installations['this_normuser']]
    )
    this_whatever_install1_addrs1 = MemberFactory(
        celus_installations=[installations['this_whatever']], celus_address1=addresses['this']
    )
    other_whatever_install1_addrs1 = MemberFactory(
        celus_installations=[installations['other1_whatever']], celus_address1=addresses['this']
    )
    install2_addrs2_first_empty = MemberFactory(
        celus_installations=[installations['this_normuser'], installations['other1_normuser']],
        celus_address1='',
        celus_address2=addresses['this'],
        celus_address3=addresses['other1'],
    )
    install2_addrs2_second_empty = MemberFactory(
        celus_installations=[installations['this_normuser'], installations['other1_normuser']],
        celus_address1=addresses['this'],
        celus_address2='',
        celus_address3=addresses['other1'],
    )
    install3_addrs3_third_pref = MemberFactory(
        celus_installations=[
            installations['pref_normuser'],
            installations['this_normuser'],
            installations['other1_normuser'],
        ],
        celus_address1=addresses['this'],
        celus_address2=addresses['other1'],
        celus_address3=addresses['pref'],
    )
    install3_addrs3_second_pref = MemberFactory(
        celus_installations=[
            installations['pref_normuser'],
            installations['this_normuser'],
            installations['other1_normuser'],
        ],
        celus_address1=addresses['this'],
        celus_address2=addresses['pref'],
        celus_address3=addresses['other1'],
    )
    install4_addrs3_not_this_staff = MemberFactory(
        celus_installations=[
            installations['other1_normuser'],
            installations['other2_normuser'],
            installations['other3_normuser'],
            installations['this_normuser'],
        ],
        celus_address1=addresses['other1'],
        celus_address2=addresses['other2'],
        celus_address3=addresses['other3'],
        tags=[tags['STAFF_TAG']],
    )

    install4_addrs3_not_this = MemberFactory(
        celus_installations=[
            installations['other1_normuser'],
            installations['other2_normuser'],
            installations['other3_normuser'],
            installations['this_normuser'],
        ],
        celus_address1=addresses['other1'],
        celus_address2=addresses['other2'],
        celus_address3=addresses['other3'],
    )

    install4_addrs3_not_pref_staff = MemberFactory(
        celus_installations=[
            installations['pref_normuser'],
            installations['other1_normuser'],
            installations['other2_normuser'],
            installations['other3_normuser'],
        ],
        celus_address1=addresses['other1'],
        celus_address2=addresses['other2'],
        celus_address3=addresses['other3'],
        tags=[tags['STAFF_TAG']],
    )

    install4_addrs3_not_pref = MemberFactory(
        celus_installations=[
            installations['pref_normuser'],
            installations['other1_normuser'],
            installations['other2_normuser'],
            installations['other3_normuser'],
        ],
        celus_address1=addresses['other1'],
        celus_address2=addresses['other2'],
        celus_address3=addresses['other3'],
    )
    return locals()


@pytest.fixture
def delete_member_test_cases(installations, tags):
    this_normuser_reason = MemberFactory(celus_installations=[installations['this_normuser']])
    other_consman_reason = MemberFactory(celus_installations=[installations['other1_consman']])
    no_reason = MemberFactory()
    no_reason_donotdeletetag = MemberFactory(tags=[tags['DO_NOT_DELETE_TAG']])
    other_normuser_reason = MemberFactory(celus_installations=[installations['other1_normuser']])
    no_reason_randomtag = MemberFactory(tags=[tags['RANDOM_TAG']])
    this_consman_reason = MemberFactory(celus_installations=[installations['this_consman']])
    other_whatever_reason = MemberFactory(celus_installations=[installations['other1_whatever']])
    this_whatever = MemberFactory(celus_installations=[installations['this_whatever']])
    del installations, tags
    return locals()


@pytest.fixture
def update_member_test_cases(member, installations, addresses):

    m = copy.deepcopy(member['no_fistnam_no_lastnam_install0_addrs0'])
    m.first_name = fake_first_name
    m.last_name = fake_last_name
    m.celus_installations.append(installations['this_normuser'])
    m.celus_address1 = addresses['this']
    update_firstnam_lastnam_install_addrs = {
        "tested": member['no_fistnam_no_lastnam_install0_addrs0'],
        "result": m,
    }

    # TESTING NAMES

    m = copy.deepcopy(member['no_firstnam_this_normuser_install1_addrs1'])
    m.first_name = fake_first_name
    update_firstnam = {"tested": member['no_firstnam_this_normuser_install1_addrs1'], "result": m}

    m = copy.deepcopy(member['no_lastnam_this_normuser_install1_addrs1'])
    m.last_name = fake_last_name
    update_lastnam = {"tested": member['no_lastnam_this_normuser_install1_addrs1'], "result": m}

    m = copy.deepcopy(member['no_fistnam_no_lastnam_this_normuser_install1_addrs1'])
    m.first_name = fake_first_name
    m.last_name = fake_last_name
    update_firstnam_lastnam = {
        "tested": member['no_fistnam_no_lastnam_this_normuser_install1_addrs1'],
        "result": m,
    }

    # TESTING INSTALLATIONS

    # member has reason this consman, celususer is consman -> pass
    no_update_consman = {"tested": member['this_consman_install1_addrs1']}

    # member has reason this normuser, celususer is normuser -> pass
    no_update_normuser = {"tested": member['this_normuser_install1_addrs1']}

    # member has reason this consman celususer is normuser -> update
    m = copy.deepcopy(member['this_consman_install1_addrs1'])
    m.celus_installations = [installations['this_normuser']]
    update_usertype_to_normuser = {"tested": member['this_consman_install1_addrs1'], "result": m}

    # member has reason this normuser, celususer is consman -> update
    m = copy.deepcopy(member['this_normuser_install1_addrs1'])
    m.celus_installations = [installations['this_consman']]
    update_usertype_to_consman = {"tested": member['this_normuser_install1_addrs1'], "result": m}

    # member has reason this whatever, celususer is normuser -> update
    m = copy.deepcopy(member['this_whatever_install1'])
    m.celus_installations.insert(0, installations['this_normuser'])
    m.celus_address1 = addresses['this']
    add_usertype_normuser = {"tested": member['this_whatever_install1'], "result": m}

    # member has reason this whatever, celususer is consman -> update
    m = copy.deepcopy(member['this_whatever_install1'])
    m.celus_installations.insert(0, installations['this_consman'])
    m.celus_address1 = addresses['this']
    add_usertype_consman = {"tested": member['this_whatever_install1'], "result": m}

    # member has reason this normuser and other normuser, no celususer -> update
    m = copy.deepcopy(member['this_normuser_other_normuser_install2_addrs2'])
    m.celus_installations.remove(installations['this_normuser'])
    m.celus_address1 = addresses['other1']
    m.celus_address2 = ''
    remove_this_normuser_still_other_normuser = {
        "tested": member['this_normuser_other_normuser_install2_addrs2'],
        "result": m,
    }

    # member has reason this consman and other consman, no celususer -> update
    m = copy.deepcopy(member['this_consman_other_consman_install2_addrs2'])
    m.celus_installations.remove(installations['this_consman'])
    m.celus_address1 = addresses['other1']
    m.celus_address2 = ''
    remove_this_consman_still_other_consman = {
        "tested": member['this_consman_other_consman_install2_addrs2'],
        "result": m,
    }

    # member has reason this normuser and this whatever, no celususer -> update
    m = copy.deepcopy(member['this_normuser_this_whatever_install2_addrs1'])
    m.celus_installations.remove(installations['this_normuser'])
    m.celus_address1 = ''
    remove_this_normuser_still_this_whatever = {
        "tested": member['this_normuser_this_whatever_install2_addrs1'],
        "result": m,
    }

    # member has reason this normuser and other whatever, no celususer -> update
    m = copy.deepcopy(member['this_normuser_other_whatever_install2_addrs1'])
    m.celus_installations.remove(installations['this_normuser'])
    m.celus_address1 = ''
    remove_this_normuser_still_other_whatever = {
        "tested": member['this_normuser_other_whatever_install2_addrs1'],
        "result": m,
    }

    # member has too long reasons, stafftag, celususer normuser -> update + no warning
    m = copy.deepcopy(member['this_toolongreason_install1_addrs0_staff'])
    m.celus_installations = [installations['this_normuser']]
    m.celus_address1 = addresses['this']
    add_this_normuser_remove_toolongreason = {
        "tested": member['this_toolongreason_install1_addrs0_staff'],
        "result": m,
    }

    # member has too long reasons, no stafftag, celususer normuser -> update + warning
    m = copy.deepcopy(member['this_toolongreason_install1_addrs0'])
    m.celus_installations = [installations['this_normuser']]
    m.celus_address1 = addresses['this']
    add_this_normuser_remove_toolongreason_warn = {
        "tested": member['this_toolongreason_install1_addrs0'],
        "result": m,
        'warning': 'WARNINGS:\n\nuser@celus.test\ncelus installations value too long',
    }

    # TESTING ADDRESSES

    # member doesnt have celus addrs, celususer normuser -> update
    m = copy.deepcopy(member['this_normuser_install1_addrs0'])
    m.celus_address1 = addresses['this']
    add_addrs = {"tested": member['this_normuser_install1_addrs0'], "result": m}

    # member has this celus addrs, no celususer -> update
    m = copy.deepcopy(member['this_whatever_install1_addrs1'])
    m.celus_address1 = ''
    remove_addrs_keep_this_whatever = {
        "tested": member['this_whatever_install1_addrs1'],
        "result": m,
    }

    # member has this celus addrs, has other reason whatever, no celususer -> update
    m = copy.deepcopy(member['other_whatever_install1_addrs1'])
    m.celus_address1 = ''
    remove_addrs_keep_other_whatever = {
        "tested": member['other_whatever_install1_addrs1'],
        "result": m,
    }

    # member has first addrs empty, celususer -> update
    m = copy.deepcopy(member['install2_addrs2_first_empty'])
    m.celus_address1 = addresses['this']
    m.celus_address2 = addresses['other1']
    m.celus_address3 = ''
    first_to_last_empty_addrs = {"tested": member['install2_addrs2_first_empty'], "result": m}

    # member has second addrs empty, celususer -> update
    m = copy.deepcopy(member['install2_addrs2_second_empty'])
    m.celus_address1 = addresses['this']
    m.celus_address2 = addresses['other1']
    m.celus_address3 = ''
    second_to_last_empty_addrs = {"tested": member['install2_addrs2_second_empty'], "result": m}

    # member has second addrs pref, celususer -> update
    m = copy.deepcopy(member['install3_addrs3_second_pref'])
    m.celus_address1 = addresses['pref']
    m.celus_address2 = addresses['this']
    m.celus_address3 = addresses['other1']
    second_to_first_pref_addrs = {"tested": member['install3_addrs3_second_pref'], "result": m}

    # member has third addrs pref, celususer -> update
    m = copy.deepcopy(member['install3_addrs3_third_pref'])
    m.celus_address1 = addresses['pref']
    m.celus_address2 = addresses['this']
    m.celus_address3 = addresses['other1']
    third_to_first_pref_addrs = {"tested": member['install3_addrs3_third_pref'], "result": m}

    # member has three addrs but not this is staff, celususer -> pass
    cannt_add_more_addrs = {"tested": member['install4_addrs3_not_this_staff']}

    # member has three addrs but not this is not staff, celususer -> pass + warning
    cannt_add_more_addrs_warn = {
        "tested": member['install4_addrs3_not_this'],
        'warning': 'member is user in more than 3 celuses',
    }

    # member has three addrs but not pref , celususer -> update + warning
    m = copy.deepcopy(member['install4_addrs3_not_pref_staff'])
    m.celus_address1 = addresses['pref']
    m.celus_address2 = addresses['other1']
    m.celus_address3 = addresses['other2']
    cannt_add_more_addrs_pref_added = {
        "tested": member['install4_addrs3_not_pref_staff'],
        "result": m,
    }

    # member has three addrs but not pref, celususer -> update + warning
    m = copy.deepcopy(member['install4_addrs3_not_pref'])
    m.celus_address1 = addresses['pref']
    m.celus_address2 = addresses['other1']
    m.celus_address3 = addresses['other2']
    cannt_add_more_addrs_pref_added_warn = {
        "tested": member['install4_addrs3_not_pref'],
        "result": m,
        'warning': 'member is user in more than 3 celuses',
    }

    del member, installations, addresses, m
    return locals()


@pytest.fixture
def valid_identity():
    id_string = 'valid@user.test'
    user = get_user_model().objects.create(username='test', email=id_string)
    Identity.objects.create(user=user, identity=id_string)
    yield id_string


@pytest.fixture
def invalid_identity():
    yield 'invalid@user.test'


@pytest.fixture
def master_admin_identity():
    id_string = 'masteradmin@user.test'
    user = get_user_model().objects.create(username='master_admin')
    Identity.objects.create(user=user, identity=id_string)
    user.organizations.add(
        Organization.objects.get_or_create(
            internal_id=settings.MASTER_ORGANIZATIONS[0],
            defaults={
                'ext_id': 1235711,
                'parent': None,
                'ico': '12345',
                'name_cs': 'šéf',
                'name_en': 'boss',
                'short_name': 'master_admin',
            },
        )[0],
        through_defaults={"is_admin": True},
    )
    yield id_string


@pytest.fixture
def master_user_identity():
    id_string = 'masteruser@user.test'
    user = get_user_model().objects.create(username='master_user')
    Identity.objects.create(user=user, identity=id_string)
    user.organizations.add(
        Organization.objects.get_or_create(
            internal_id=settings.MASTER_ORGANIZATIONS[0],
            defaults={
                'ext_id': 1235712,
                'parent': None,
                'ico': '65432',
                'name_cs': 'pozorovatel',
                'name_en': 'observer',
                'short_name': 'master_user',
            },
        )[0],
        through_defaults={"is_admin": True},
    )
    yield id_string


@pytest.fixture
def admin_identity():
    id_string = 'admin@user.test'
    user = get_user_model().objects.create(username='admin', is_superuser=True)
    Identity.objects.create(user=user, identity=id_string)
    yield id_string


@pytest.fixture
def authenticated_client(client, valid_identity):
    client.defaults[settings.EDUID_IDENTITY_HEADER] = valid_identity
    client.user = Identity.objects.get(identity=valid_identity).user
    yield client


@pytest.fixture
def master_admin_client(client, master_admin_identity):
    client.defaults[settings.EDUID_IDENTITY_HEADER] = master_admin_identity
    yield client


@pytest.fixture
def master_user_client(client, master_user_identity):
    client.defaults[settings.EDUID_IDENTITY_HEADER] = master_user_identity
    yield client


@pytest.fixture
def unauthenticated_client(client, invalid_identity):
    client.defaults[settings.EDUID_IDENTITY_HEADER] = invalid_identity
    yield client


@pytest.fixture
def authentication_headers():
    def fn(identity):
        return {settings.EDUID_IDENTITY_HEADER: identity}

    return fn


@pytest.fixture
def site():
    return Site.objects.get_or_create(
        id=settings.SITE_ID, defaults={'name': 'Celus test', 'domain': 'test.celus.net'}
    )[0]


__all__ = [
    'admin_identity',
    'master_admin_client',
    'master_user_client',
    'master_admin_identity',
    'master_user_identity',
    'authentication_headers',
    'authentication_headers',
    'authenticated_client',
    'unauthenticated_client',
    'valid_identity',
    'invalid_identity',
]
