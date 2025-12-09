from datetime import timedelta

import pytest
from core.fake_data import IdentityFactory
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from logs.models import ReportType
from organizations.models import Organization, UserOrganization
from rest_framework import status

from ch_export.models import AccessLogExport, AccessLogExportBatch, AccessLogExportTask
from test_scenarios.basic import make_client

User = get_user_model()


@pytest.fixture
def admin_user():
    user = User.objects.create_user(username="user", email="admin@test.com", password="testpass")
    user.is_superuser = True
    user.save()
    return user


@pytest.fixture
def org_admin_user(organization):
    user = User.objects.create_user(username="user", email="orgadmin@test.com", password="testpass")
    UserOrganization.objects.create(user=user, organization=organization, is_admin=True)
    return user


@pytest.fixture
def regular_user():
    return User.objects.create_user(username="user", email="user@test.com", password="testpass")


@pytest.fixture
def organization():
    return Organization.objects.create(name="Test Org", short_name="test")


@pytest.fixture
def report_type():
    return ReportType.objects.create(name="TR", short_name="tr")


@pytest.fixture
def export(organization):
    return AccessLogExport.objects.create(organization=organization, enabled=True)


@pytest.fixture
def export_task(export, report_type):
    batch = AccessLogExportBatch.objects.create(export=export)
    return AccessLogExportTask.objects.create(
        batch=batch, report_type=report_type, task_id="test-task-id"
    )


@pytest.fixture
def other_organization():
    return Organization.objects.create(name="Other Org", short_name="other")


@pytest.fixture
def other_export(other_organization):
    return AccessLogExport.objects.create(organization=other_organization, enabled=True)


@pytest.mark.django_db
class TestAccessLogExportAPI:
    def test_admin_can_view_all_exports(self, admin_user, export_task):
        response = make_client(IdentityFactory(user=admin_user)).get(
            reverse("ch-export-exports-list")
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_org_admin_can_view_own_exports(self, org_admin_user, export_task):
        response = make_client(IdentityFactory(user=org_admin_user)).get(
            reverse("ch-export-exports-list")
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_filter_by_organization_works(self, export_task, org_admin_user):
        response = make_client(IdentityFactory(user=org_admin_user)).get(
            reverse("ch-export-exports-list"),
            {"organization": org_admin_user.admin_organizations().first().id},
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["id"] == export_task.batch.export.id

    def test_filter_by_organization_works_for_non_related_organization(
        self, export_task, org_admin_user, other_organization
    ):
        """
        Make sure that when filtering by organization, we only get exports for that organization.
        """
        response = make_client(IdentityFactory(user=org_admin_user)).get(
            reverse("ch-export-exports-list"), {"organization": other_organization.id}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthorized_access_denied(self, export_task, client, regular_user):
        response = client.get(reverse("ch-export-exports-list"))
        assert response.status_code in (401, 404)
        response = make_client(IdentityFactory(user=regular_user)).get(
            reverse("ch-export-exports-list")
        )
        assert response.data == []

    def test_export_serialization(self, admin_user, export_task):
        response = make_client(IdentityFactory(user=admin_user)).get(
            reverse("ch-export-exports-list")
        )
        export_data = response.data[0]

        assert export_data["id"] == export_task.batch.export.id
        assert export_data["organization"] == export_task.batch.export.organization.name
        assert export_data["status"] == "running"
        assert export_data["latest_batch"]["id"] == export_task.batch.id
        assert export_data["latest_batch"]["report_types"] == ["tr"]

    def test_admin_can_start_export(self, admin_user, export):
        response = make_client(IdentityFactory(user=admin_user)).post(
            reverse("ch-export-exports-start-export", kwargs={"pk": export.id})
        )
        assert response.status_code == status.HTTP_201_CREATED
        batch = response.data
        assert batch["id"] == export.latest_batch().id

    def test_superuser_can_start_export_when_no_task_running(self, admin_user, export):
        """Superuser can start export when no task is running."""
        response = make_client(IdentityFactory(user=admin_user)).post(
            reverse("ch-export-exports-start-export", kwargs={"pk": export.id})
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert "id" in response.data

    def test_superuser_cannot_start_export_when_task_running(self, admin_user, export, report_type):
        """Superuser cannot start export when a task is already running."""
        # Create a running task
        batch = AccessLogExportBatch.objects.create(export=export)
        AccessLogExportTask.objects.create(
            batch=batch, report_type=report_type, started=timezone.now(), finished=None
        )

        response = make_client(IdentityFactory(user=admin_user)).post(
            reverse("ch-export-exports-start-export", kwargs={"pk": export.id})
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already running" in response.data["detail"].lower()

    def test_admin_can_start_export_after_cooldown(self, org_admin_user, export, report_type):
        """Normal admin can start export after cooldown period has passed."""
        # Create a batch that was created more than cooldown hours ago
        cooldown_hours = getattr(settings, "CLICKHOUSE_EXPORT_MANUAL_COOLDOWN_HOURS", 10)
        old_time = timezone.now() - timedelta(hours=cooldown_hours + 1)
        batch = AccessLogExportBatch.objects.create(export=export)
        batch.created = old_time
        batch.save()
        AccessLogExportTask.objects.create(
            batch=batch,
            report_type=report_type,
            started=old_time,
            finished=old_time + timedelta(minutes=5),
        )

        response = make_client(IdentityFactory(user=org_admin_user)).post(
            reverse("ch-export-exports-start-export", kwargs={"pk": export.id})
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_admin_cannot_start_export_before_cooldown(self, org_admin_user, export, report_type):
        """Normal admin cannot start export before cooldown period has passed."""
        # Create a batch that was created recently (within cooldown)
        cooldown_hours = getattr(settings, "CLICKHOUSE_EXPORT_MANUAL_COOLDOWN_HOURS", 10)
        recent_time = timezone.now() - timedelta(hours=cooldown_hours - 1)
        batch = AccessLogExportBatch.objects.create(export=export)
        batch.created = recent_time
        batch.save()
        AccessLogExportTask.objects.create(
            batch=batch,
            report_type=report_type,
            started=recent_time,
            finished=recent_time + timedelta(minutes=5),
        )

        response = make_client(IdentityFactory(user=org_admin_user)).post(
            reverse("ch-export-exports-start-export", kwargs={"pk": export.id})
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "cooldown" in response.data["detail"].lower()
        assert "next_export_available_at" in response.data

    def test_serializer_includes_availability_fields(self, admin_user, export):
        """Serializer includes can_start_export and next_export_available_at fields."""
        response = make_client(IdentityFactory(user=admin_user)).get(
            reverse("ch-export-exports-list")
        )
        assert response.status_code == status.HTTP_200_OK
        export_data = response.data[0]
        assert "can_start_export" in export_data
        assert "next_export_available_at" in export_data
        assert isinstance(export_data["can_start_export"], bool)

    def test_next_export_available_at_calculation(self, org_admin_user, export, report_type):
        """Test that next_export_available_at is calculated correctly."""
        cooldown_hours = getattr(settings, "CLICKHOUSE_EXPORT_MANUAL_COOLDOWN_HOURS", 10)
        recent_time = timezone.now() - timedelta(hours=cooldown_hours - 2)
        batch = AccessLogExportBatch.objects.create(export=export)
        batch.created = recent_time
        batch.save()
        AccessLogExportTask.objects.create(
            batch=batch,
            report_type=report_type,
            started=recent_time,
            finished=recent_time + timedelta(minutes=5),
        )

        response = make_client(IdentityFactory(user=org_admin_user)).get(
            reverse("ch-export-exports-list")
        )
        assert response.status_code == status.HTTP_200_OK
        export_data = response.data[0]
        assert export_data["can_start_export"] is False
        assert export_data["next_export_available_at"] is not None

        # Verify the next_export_available_at is approximately cooldown hours from batch creation
        from datetime import datetime

        next_available = datetime.fromisoformat(
            export_data["next_export_available_at"].replace("Z", "+00:00")
        )
        expected_time = recent_time + timedelta(hours=cooldown_hours)
        # Allow 1 minute tolerance for test execution time
        assert abs((next_available - expected_time).total_seconds()) < 60


@pytest.mark.django_db
class TestAccessLogExportBatchProgressAPI:
    @pytest.fixture
    def batch(self, export, report_type):
        batch = AccessLogExportBatch.objects.create(export=export)
        AccessLogExportTask.objects.create(
            batch=batch,
            report_type=report_type,
            task_id="test-task-id",
            started=None,
            finished=None,
        )
        return batch

    def test_progress_endpoint_returns_correct_structure(self, admin_user, batch):
        response = make_client(IdentityFactory(user=admin_user)).get(
            reverse("ch-export-batch-progress", kwargs={"pk": batch.id})
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert "id" in data
        assert "created" in data
        assert "status" in data
        assert "tasks" in data
        assert isinstance(data["tasks"], list)
        assert len(data["tasks"]) == 1

        task = data["tasks"][0]
        assert "id" in task
        assert "report_type" in task
        assert "started" in task
        assert "finished" in task
        assert "error" in task
        assert "progress_current" in task
        assert "progress_total" in task
        assert "eta" in task
        assert "status" in task

    def test_progress_endpoint_respects_permissions(self, org_admin_user, batch, other_export):
        # Org admin can access their own export batch
        client = make_client(IdentityFactory(user=org_admin_user))
        response = client.get(reverse("ch-export-batch-progress", kwargs={"pk": batch.id}))
        assert response.status_code == status.HTTP_200_OK

        # Org admin cannot access other organization's export batch
        other_batch = AccessLogExportBatch.objects.create(export=other_export)
        response = client.get(reverse("ch-export-batch-progress", kwargs={"pk": other_batch.id}))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_progress_endpoint_returns_404_for_nonexistent_batch(self, admin_user):
        client = make_client(IdentityFactory(user=admin_user))
        response = client.get(reverse("ch-export-batch-progress", kwargs={"pk": 99999}))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_progress_values_correctly_calculated(self, admin_user, batch, report_type):
        from django.core.cache import cache

        # Set progress in cache
        task = batch.tasks.first()
        task.started = timezone.now()
        task.save()
        cache.set(f"ch_export_task_{task.id}_current", 50)
        cache.set(f"ch_export_task_{task.id}_total", 100)

        response = make_client(IdentityFactory(user=admin_user)).get(
            reverse("ch-export-batch-progress", kwargs={"pk": batch.id})
        )
        assert response.status_code == status.HTTP_200_OK

        task_data = response.data["tasks"][0]
        assert task_data["progress_current"] == 50
        assert task_data["progress_total"] == 100

    def test_progress_status_correctly_determined(self, admin_user, batch, report_type):
        task = batch.tasks.first()
        client = make_client(IdentityFactory(user=admin_user))

        # Test pending status (not started)
        response = client.get(reverse("ch-export-batch-progress", kwargs={"pk": batch.id}))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["tasks"][0]["status"] == "pending"

        # Test running status
        from django.utils import timezone

        task.started = timezone.now()
        task.save()
        response = client.get(reverse("ch-export-batch-progress", kwargs={"pk": batch.id}))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["tasks"][0]["status"] == "running"

        # Test completed status
        task.finished = timezone.now()
        task.save()
        response = client.get(reverse("ch-export-batch-progress", kwargs={"pk": batch.id}))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["tasks"][0]["status"] == "completed"

        # Test failed status
        task.error = "Some error"
        task.save()
        response = client.get(reverse("ch-export-batch-progress", kwargs={"pk": batch.id}))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["tasks"][0]["status"] == "failed"
