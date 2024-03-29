import pytest
from core.models import Identity
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from organizations.models import Organization


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
            defaults=dict(
                ext_id=1235711,
                parent=None,
                ico='12345',
                name_cs='šéf',
                name_en='boss',
                short_name='master_admin',
            ),
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
            defaults=dict(
                ext_id=1235712,
                parent=None,
                ico='65432',
                name_cs='pozorovatel',
                name_en='observer',
                short_name='master_user',
            ),
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
