import pytest
from core.fake_data import IdentityFactory
from django.contrib.auth import get_user_model
from django.urls import reverse
from logs.models import ReportType
from organizations.models import Organization, UserOrganization
from rest_framework import status

from ch_export.models import AccessLogExport, AccessLogExportBatch, AccessLogExportTask
from test_scenarios.basic import *  # noqa - fixtures
from test_scenarios.basic import make_client

User = get_user_model()


@pytest.mark.django_db
class TestAccessLogExportAPI:
    @pytest.fixture
    def admin_user(self):
        user = User.objects.create_user(
            username="user", email="admin@test.com", password="testpass"
        )
        user.is_superuser = True
        user.save()
        return user

    @pytest.fixture
    def org_admin_user(self, organization):
        user = User.objects.create_user(
            username="user", email="orgadmin@test.com", password="testpass"
        )
        UserOrganization.objects.create(user=user, organization=organization, is_admin=True)
        return user

    @pytest.fixture
    def regular_user(self):
        return User.objects.create_user(username="user", email="user@test.com", password="testpass")

    @pytest.fixture
    def organization(self):
        return Organization.objects.create(name="Test Org", short_name="test")

    @pytest.fixture
    def report_type(self):
        return ReportType.objects.create(name="TR", short_name="tr")

    @pytest.fixture
    def export(self, organization):
        return AccessLogExport.objects.create(organization=organization, enabled=True)

    @pytest.fixture
    def export_task(self, export, report_type):
        batch = AccessLogExportBatch.objects.create(export=export)
        return AccessLogExportTask.objects.create(
            batch=batch, report_type=report_type, task_id="test-task-id"
        )

    def test_admin_can_view_all_exports(self, clients, admin_user, export_task):
        response = clients["su"].get(reverse("ch-export-exports-list"))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_org_admin_can_view_own_exports(self, org_admin_user, export_task):
        response = make_client(IdentityFactory(user=org_admin_user)).get(
            reverse("ch-export-exports-list")
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_unauthorized_access_denied(self, clients, export_task):
        response = clients["unauthenticated"].get(reverse("ch-export-exports-list"))
        assert response.status_code in (401, 404)
        response = clients["user1"].get(reverse("ch-export-exports-list"))
        assert response.data == []

    def test_export_serialization(self, clients, export_task):
        response = clients["su"].get(reverse("ch-export-exports-list"))
        export_data = response.data[0]

        assert export_data["id"] == export_task.batch.export.id
        assert export_data["organization"] == export_task.batch.export.organization.name
        assert export_data["status"] == "running"
        assert export_data["latest_batch"]["id"] == export_task.batch.id
        assert export_data["latest_batch"]["report_types"] == ["tr"]
