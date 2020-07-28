import pytest

from django.urls import reverse

from core.tests.conftest import site


@pytest.mark.django_db
class TestDeploymentAPI(object):
    def test_api_is_open(self, client, site):
        resp = client.get(reverse('deployment-overview'))
        assert resp.status_code == 200
