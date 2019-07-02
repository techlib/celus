import pytest
from django.conf import settings
from django.contrib.auth import get_user_model

from core.models import Identity


@pytest.fixture
def valid_identity():
    id_string = 'valid@user.test'
    user = get_user_model().objects.create(username='test')
    Identity.objects.create(user=user, identity=id_string)
    yield id_string


@pytest.fixture
def invalid_identity():
    yield 'invalid@user.test'


@pytest.fixture
def authenticated_client(client, valid_identity):
    client.defaults[settings.EDUID_IDENTITY_HEADER] = valid_identity
    yield client


@pytest.fixture
def authentication_headers():
    def fn(identity):
        return {settings.EDUID_IDENTITY_HEADER: identity}
    return fn
