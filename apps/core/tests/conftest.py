import pytest
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
    client.defaults['HTTP_X_IDENTITY'] = valid_identity
    yield client
