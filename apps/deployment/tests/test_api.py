import pytest
from core.tests.conftest import site  # noqa - fixture
from django.urls import reverse


@pytest.mark.django_db
class TestDeploymentAPI:
    def test_api_is_open(self, client, site):
        resp = client.get(reverse('deployment-overview'))
        assert resp.status_code == 200
