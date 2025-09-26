from unittest.mock import Mock, patch

import pytest
from logs.fake_data import ImportBatchFullFactory
from logs.models import ReportType
from organizations.models import Organization

from ch_export.models import AccessLogExport, AccessLogExportTask
from ch_export.tasks import start_export_tasks


@pytest.mark.django_db
class TestChExportTasks:
    @pytest.fixture
    def organization(self):
        return Organization.objects.create(name="Test Org", short_name="test")

    @pytest.fixture
    def report_type(self):
        return ReportType.objects.create(name="TR", short_name="tr")

    @pytest.fixture
    def export(self, organization, report_type):
        ImportBatchFullFactory.create(organization=organization, report_type=report_type)
        return AccessLogExport.objects.create(organization=organization, enabled=True)

    @pytest.mark.clickhouse
    @pytest.mark.usefixtures("clickhouse_db")
    @patch("ch_export.tasks.export_to_ch_task.apply_async")
    def test_start_export_tasks(self, mock_apply_async, export, report_type):
        mock_celery_task = Mock()
        mock_celery_task.id = "celery-task-id"
        mock_apply_async.return_value = mock_celery_task

        start_export_tasks()

        tasks = (
            AccessLogExportTask.objects.select_related("batch")
            .filter(batch__export=export)
            .order_by("-created")
        )

        # Check that the newest task was created with the correct ID
        newest_task = tasks.first()
        assert newest_task.task_id == "celery-task-id"

        mock_apply_async.assert_called_once_with((newest_task.id,), countdown=2)

    def test_start_export_tasks_disabled_export(self, export, report_type):
        export.enabled = False
        export.save()

        with patch("ch_export.tasks.export_to_ch_task.apply_async") as mock_apply_async:
            start_export_tasks()
            mock_apply_async.assert_not_called()

        assert AccessLogExportTask.objects.count() == 0
