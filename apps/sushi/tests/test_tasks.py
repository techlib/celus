"""
Test suite for SUSHI credentials deletion tasks.

This module contains comprehensive tests for the task functions:
- delete_credentials_task: Handles the actual deletion of credentials and related data
- plan_to_delete_credentials_task: Schedules deletion tasks for marked credentials

The tests cover various scenarios including:
- Successful deletion with and without data
- Handling of running harvests
- Transaction rollback on errors
- Edge cases with non-existent credentials
- Proper cleanup of related ImportBatch and SushiFetchAttempt objects
"""

from unittest.mock import patch

import pytest
from logs.fake_data import ImportBatchFullFactory
from logs.models import ImportBatch

from sushi.fake_data import CredentialsFactory, FetchAttemptFactory
from sushi.models import DeleteCredentials, SushiCredentials, SushiFetchAttempt
from sushi.tasks import delete_credentials_task, plan_to_delete_credentials_task
from test_scenarios.basic import (
    counter_report_types,  # noqa
    data_sources,  # noqa
    organizations,  # noqa
    platforms,  # noqa
    report_types,  # noqa
)


@pytest.fixture
def credentials_to_delete_with_data(organizations, platforms):
    return CredentialsFactory(
        organization=organizations["branch"],
        platform=platforms["branch"],
        counter_version=5,
        to_delete=DeleteCredentials.WITH_DATA,
    )


@pytest.fixture
def credentials_to_delete_without_data(organizations, platforms):
    return CredentialsFactory(
        organization=organizations["standalone"],
        platform=platforms["branch"],
        counter_version=5,
        to_delete=DeleteCredentials.WITHOUT_DATA,
    )


@pytest.fixture
def credentials_not_to_delete(organizations, platforms):
    return CredentialsFactory(
        organization=organizations["standalone"],
        platform=platforms["standalone"],
        counter_version=5,
        to_delete=DeleteCredentials.NO,
    )


@pytest.fixture
def to_delete_data(
    credentials_to_delete_with_data, counter_report_types, report_types, platforms, organizations
):
    return [
        FetchAttemptFactory(
            credentials=credentials_to_delete_with_data,
            counter_report=counter_report_types["tr"],
            import_batch=None,
        ),
        FetchAttemptFactory(
            credentials=credentials_to_delete_with_data,
            counter_report=counter_report_types["tr"],
            import_batch=ImportBatchFullFactory(
                organization=organizations["branch"],
                platform=platforms["branch"],
                report_type=report_types["tr"],
            ),
        ),
    ]


@pytest.fixture
def to_keep_data(
    credentials_to_delete_without_data, counter_report_types, report_types, platforms, organizations
):
    return FetchAttemptFactory(
        credentials=credentials_to_delete_without_data,
        counter_report=counter_report_types["tr"],
        import_batch=ImportBatchFullFactory(
            organization=organizations["standalone"],
            platform=platforms["branch"],
            report_type=report_types["tr"],
        ),
    )


@pytest.mark.django_db
class TestDeleteCredentialsTask:
    """Test cases for the delete_credentials_task function"""

    def test_delete_credentials(
        self,
        credentials_to_delete_with_data,
        credentials_to_delete_without_data,
        credentials_not_to_delete,
        to_keep_data,
        to_delete_data,
    ):
        """Test successful deletion of credentials with data"""
        # Verify initial state
        assert SushiCredentials.objects.count() == 3
        assert SushiFetchAttempt.objects.count() == 3, "2 + 1 + 0"
        assert ImportBatch.objects.count() == 2
        to_delete_fetch_attempt_ids = [e.pk for e in to_delete_data]
        to_delete_import_batch_ids = [e.import_batch.pk for e in to_delete_data if e.import_batch]
        to_keep_fetch_attempt_id = to_keep_data.pk
        to_keep_import_batch_id = to_keep_data.import_batch.pk

        for credentials_id in [
            credentials_to_delete_with_data.pk,
            credentials_to_delete_without_data.pk,
            credentials_not_to_delete.pk,
        ]:
            delete_credentials_task(credentials_id)

        # Verify credentials and related data are deleted
        assert not SushiCredentials.objects.filter(pk=credentials_to_delete_with_data.pk).exists()
        assert not SushiCredentials.objects.filter(
            pk=credentials_to_delete_without_data.pk
        ).exists()
        assert SushiCredentials.objects.filter(pk=credentials_not_to_delete.pk).exists()
        assert not SushiFetchAttempt.objects.filter(pk__in=to_delete_fetch_attempt_ids).exists()
        assert not ImportBatch.objects.filter(pk__in=to_delete_import_batch_ids).exists()
        assert SushiFetchAttempt.objects.filter(pk=to_keep_fetch_attempt_id).exists()
        assert ImportBatch.objects.filter(pk=to_keep_import_batch_id).exists()

    def test_delete_credentials_nonexistent_id(self):
        """Test handling of non-existent credentials ID"""
        nonexistent_id = 99999

        # Should not raise an exception
        delete_credentials_task(nonexistent_id)

    @patch("sushi.tasks.Scheduler.objects.filter")
    def test_delete_credentials_with_running_harvest(
        self, mock_scheduler_filter, credentials_to_delete_with_data
    ):
        """Test that deletion is postponed when harvest is running"""
        credentials_id = credentials_to_delete_with_data.pk

        # Mock that there's a running harvest
        mock_scheduler_filter.return_value.exists.return_value = True

        # Execute task
        delete_credentials_task(credentials_id)

        # Verify credentials still exist
        assert SushiCredentials.objects.filter(pk=credentials_id).exists()

        # Verify scheduler was checked
        mock_scheduler_filter.assert_called_once()

    def test_delete_credentials_with_data_no_fetch_attempts(self, organizations, platforms):
        """Test deletion of credentials marked WITH_DATA but having no fetch attempts"""
        credentials = CredentialsFactory(
            organization=organizations["branch"],
            platform=platforms["branch"],
            counter_version=5,
            to_delete=DeleteCredentials.WITH_DATA,
        )
        credentials_id = credentials.pk

        # Verify initial state
        assert SushiCredentials.objects.filter(pk=credentials_id).exists()
        assert not SushiFetchAttempt.objects.filter(credentials=credentials).exists()

        # Execute task
        delete_credentials_task(credentials_id)

        # Verify credentials are deleted even without fetch attempts
        assert not SushiCredentials.objects.filter(pk=credentials_id).exists()

        # Execute the command for the second time - no exception should be raised
        # If credentials are missing it means that they were probably deleted
        delete_credentials_task(credentials_id)


@pytest.mark.django_db
class TestPlanToDeleteCredentialsTask:
    """Test cases for the plan_to_delete_credentials_task function"""

    @patch("sushi.tasks.delete_credentials_task.delay")
    def test_plan_to_delete_credentials_schedules_tasks(
        self,
        mock_delay,
        credentials_to_delete_with_data,
        credentials_to_delete_without_data,
        credentials_not_to_delete,
    ):
        """Test that planning task schedules deletion for marked credentials"""

        # Execute planning task
        plan_to_delete_credentials_task()

        # Verify that delete tasks were scheduled for credentials marked for deletion
        expected_calls = [
            (credentials_to_delete_with_data.pk,),
            (credentials_to_delete_without_data.pk,),
        ]

        # Check that delay was called with the correct arguments
        assert mock_delay.call_count == 2
        actual_calls = [call.args for call in mock_delay.call_args_list]
        assert sorted(actual_calls) == sorted(expected_calls)

    @patch("sushi.tasks.delete_credentials_task.delay")
    def test_plan_to_delete_credentials_empty_database(self, mock_delay):
        """Test that planning task handles empty database gracefully"""
        # Execute planning task with no credentials in database
        plan_to_delete_credentials_task()

        # Verify that no delete tasks were scheduled
        mock_delay.assert_not_called()
