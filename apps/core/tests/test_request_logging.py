import pickle
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest
import pytz
import redis
from api.models import OrganizationAPIKey
from django.urls import reverse
from django_celery_results.models import TaskResult
from freezegun import freeze_time
from organizations.fake_data import OrganizationFactory

from core.request_logging.celery_capture import celery_task_log, create_celery_task_log_dict
from core.tasks import flush_request_logs_to_clickhouse

# Common test data for resilient logging tests
COMMON_TEST_RECORD_DATA = {
    "hostname": "test-host",
    "db_server": "test-db",
    "clickhouse_db_server": "test-clickhouse",
    "debug": False,
    "celus_version": "test-version",
    "celus_git_hash": "test-hash",
    "clickhouse_query_active": False,
    "query_count_django": 0,
    "query_count_clickhouse": 0,
    "task_name": "test_task",
    "task_args": [],
    "task_kwargs": {},
    "status": "SUCCESS",
}


@pytest.fixture
def redis_connection(settings):
    """
    Fixture that provides a Redis connection for testing with automatic cleanup.
    Uses DB 7 to avoid conflicts with other tests.
    """
    # Override Redis DB to use DB 7 for testing
    settings.REQUEST_LOGGING_REDIS_DB = 7
    settings.CELERY_LOGGING_REDIS_DB = 7

    # Create Redis connection
    r = redis.Redis(
        host=settings.REQUEST_LOGGING_REDIS_HOST,
        port=settings.REQUEST_LOGGING_REDIS_PORT,
        db=settings.REQUEST_LOGGING_REDIS_DB,
    )

    # Clean up any existing data before the test
    r.delete(settings.CELERY_LOGGING_REDIS_KEY)

    yield r

    # Clean up after the test
    r.delete(settings.CELERY_LOGGING_REDIS_KEY)


@pytest.mark.django_db
class TestRequestLogging:
    def test_request_logging(self, settings, admin_client):
        # the setting should be set to True from env - we cannot do it here
        # as there are things which depend on it in settings/base.py
        assert settings.CLICKHOUSE_REQUEST_LOGGING
        assert "requestlogs.middleware.RequestLogsMiddleware" in settings.MIDDLEWARE
        # I don't know why, but if I do not do the get first, it all crashes down on
        # partially imported module
        # The following seems to force the settings to be completely loaded and I can
        # then mock it without trouble
        admin_client.get(reverse("user_api_view"))
        with patch("core.request_logging.capture.redis.Redis") as redis_mock:
            instance_mock = Mock()
            redis_mock.return_value = instance_mock
            resp = admin_client.get(reverse("user_api_view"))
            assert resp.status_code == 200
            assert redis_mock.called
            assert instance_mock.rpush.called

    def test_flush_request_logs_to_clickhouse_task(self, settings):
        """
        Test that the task gets the corresponding data from redis
        :return:
        """
        with patch("core.tasks.redis.Redis") as redis_mock:
            instance_mock = Mock()
            instance_mock.lpop = MagicMock(side_effect=["a", "b", None])
            redis_mock.return_value = instance_mock
            flush_request_logs_to_clickhouse()
            assert redis_mock.called
            assert instance_mock.lpop.called
            assert instance_mock.lpop.call_count == 3
            assert instance_mock.lpop.call_args_list[0][0][0] == settings.REQUEST_LOGGING_REDIS_KEY

    @pytest.mark.parametrize("has_data", [True, False])
    @pytest.mark.parametrize("anonymous", [True, False])
    def test_the_whole_logging_process(
        self, settings, admin_client, admin_user, client, anonymous, has_data
    ):
        """
        Make a request, store the data that would be sent to redis, then call the task
        and present it with the data and check that it gets sent to clickhouse
        """
        # I don't know why, but if I do not do the get first, it all crashes down on
        # partially imported module
        # The following seems to force the settings to be completely loaded and I can
        # then mock it without trouble
        settings.CLICKHOUSE_CELERY_TASK_LOGGING = False  # need to disable this for the test
        client_obj = admin_client if not anonymous else client
        client_obj.get(reverse("user_api_view"))
        with patch("core.request_logging.capture.redis.Redis") as redis_mock:
            instance_mock = Mock()
            redis_mock.return_value = instance_mock
            resp = client_obj.get(reverse("user_api_view"))
            assert resp.status_code == (200 if not anonymous else 401)
            assert instance_mock.rpush.called
            redis_stored_record = instance_mock.rpush.call_args[0][1]

        with patch("core.tasks.redis.Redis") as redis_mock, patch(
            "core.request_logging.clickhouse.get_logging_backend"
        ) as get_backend_mock:
            backend_mock = Mock()
            get_backend_mock.return_value = backend_mock
            instance_mock = Mock()
            instance_mock.lpop = MagicMock(
                side_effect=[redis_stored_record, None] if has_data else [None]
            )
            redis_mock.return_value = instance_mock
            flush_request_logs_to_clickhouse()
            if has_data:
                assert get_backend_mock.called
                assert backend_mock.store_records.called
                stored_records = backend_mock.store_records.call_args[0][1]
                assert len(stored_records) == 1
                rec = stored_records[0]
                assert rec.request_url_name == "user_api_view"
                assert rec.request_method == "GET"
                assert rec.user_id == (admin_user.pk if not anonymous else 0)
                if anonymous:
                    assert rec.response_data != ""
                else:
                    assert rec.response_data == ""
                assert rec.api_key_prefix == ""
                assert rec.api_key_org_id == 0
            else:
                assert not get_backend_mock.called
                assert not backend_mock.store_records.called

    def test_the_whole_logging_process_with_apikey(self, settings, client):
        """
        Mock the whole process of logging a request and check that it properly stores Api-Key info
        """
        org = OrganizationFactory.create()
        api_key, key_val = OrganizationAPIKey.objects.create_key(organization=org, name="test")

        # I don't know why, but if I do not do the get first, it all crashes down on
        # partially imported module
        # The following seems to force the settings to be completely loaded and I can
        # then mock it without trouble
        settings.CLICKHOUSE_CELERY_TASK_LOGGING = False  # need to disable this for the test
        client_obj = client
        client_obj.get(reverse("global-platforms-list"))
        with patch("core.request_logging.capture.redis.Redis") as redis_mock:
            instance_mock = Mock()
            redis_mock.return_value = instance_mock
            resp = client_obj.get(
                reverse("global-platforms-list"), headers={"Authorization": f"Api-Key {key_val}"}
            )
            assert resp.status_code == 200
            assert instance_mock.rpush.called
            redis_stored_record = instance_mock.rpush.call_args[0][1]

        with patch("core.tasks.redis.Redis") as redis_mock, patch(
            "core.request_logging.clickhouse.get_logging_backend"
        ) as get_backend_mock:
            backend_mock = Mock()
            get_backend_mock.return_value = backend_mock
            instance_mock = Mock()
            instance_mock.lpop = MagicMock(side_effect=[redis_stored_record, None])
            redis_mock.return_value = instance_mock
            flush_request_logs_to_clickhouse()
            assert get_backend_mock.called
            assert backend_mock.store_records.called
            stored_records = backend_mock.store_records.call_args[0][1]
            assert len(stored_records) == 1
            rec = stored_records[0]
            assert rec.request_url_name == "global-platforms-list"
            assert rec.request_method == "GET"
            assert rec.user_id == 0
            assert rec.api_key_org_id == api_key.organization_id
            assert rec.api_key_prefix == api_key.prefix

    @pytest.mark.parametrize("has_task_result", [True, False])
    def test_celery_capture_log_create(self, has_task_result):
        if has_task_result:
            TaskResult(
                task_id=1,
                task_name="test_task",
                status="SUCCESS",
                date_created=datetime(2020, 1, 1, 1, 1, 1, 1, tzinfo=pytz.UTC),
                date_done=datetime(2020, 1, 1, 1, 1, 1, 3000, tzinfo=pytz.UTC),
            )

        out = create_celery_task_log_dict(task_id=1, task=Mock(__name__="test_task"))
        assert set(out.keys()) == {
            "hostname",
            "db_server",
            "clickhouse_db_server",
            "timestamp",
            "debug",
            "celus_version",
            "celus_git_hash",
            "clickhouse_query_active",
            "query_count_django",
            "query_count_clickhouse",
            "execution_time",
            "task_name",
            "task_args",
            "task_kwargs",
            "status",
        }

    @pytest.mark.parametrize("has_task_result", [True, False])
    def test_the_celery_logging(self, has_task_result, settings, clients):
        """
        Make a request, store the data that would be sent to redis, then call the task
        and present it with the data and check that it gets sent to clickhouse
        """
        if has_task_result:
            TaskResult(
                task_id=1,
                task_name="test_task",
                status="SUCCESS",
                date_created=datetime(2020, 1, 1, 1, 1, 1, 1, tzinfo=pytz.UTC),
                date_done=datetime(2020, 1, 1, 1, 1, 1, 3000, tzinfo=pytz.UTC),
            )
        # switch off request logging, so that only celery logging is used
        settings.CLICKHOUSE_REQUEST_LOGGING = False
        settings.CLICKHOUSE_CELERY_TASK_LOGGING = True
        # if we do not do a request first, the mock later will fail with circular import
        # no idea why
        clients["admin1"].get(reverse("user_api_view"))
        with patch("core.request_logging.capture.redis.Redis") as redis_mock:
            instance_mock = Mock()
            redis_mock.return_value = instance_mock
            celery_task_log(task_id=1, task=Mock(__name__="test_task"))
            assert instance_mock.rpush.called
            redis_stored_record = instance_mock.rpush.call_args[0][1]

        with patch("core.tasks.redis.Redis") as redis_mock, patch(
            "core.request_logging.clickhouse.get_logging_backend"
        ) as get_backend_mock:
            backend_mock = Mock()
            get_backend_mock.return_value = backend_mock
            instance_mock = Mock()
            instance_mock.lpop = MagicMock(side_effect=[redis_stored_record, None])
            redis_mock.return_value = instance_mock
            flush_request_logs_to_clickhouse()
            assert get_backend_mock.called
            assert backend_mock.store_records.called
            stored_records = backend_mock.store_records.call_args[0][1]
            assert len(stored_records) == 1

    def test_resilient_flush_request_logs_to_clickhouse_rollback(self, settings):
        """
        Test that when ClickHouse write fails, the data is put back into Redis and sync is canceled
        """
        # Create test data for celery task logging (simpler than request logging)
        test_record_data = pickle.dumps(
            {**COMMON_TEST_RECORD_DATA, "timestamp": datetime.now(), "execution_time": 1.0}
        )

        with patch("core.tasks.redis.Redis") as redis_mock, patch(
            "core.request_logging.clickhouse.get_logging_backend"
        ) as get_backend_mock:
            # Mock Redis instance
            instance_mock = Mock()
            instance_mock.lpop = MagicMock(side_effect=[test_record_data, None])
            redis_mock.return_value = instance_mock

            # Mock backend that raises an exception on store_records
            backend_mock = Mock()
            backend_mock.store_records.side_effect = Exception("ClickHouse connection failed")
            get_backend_mock.return_value = backend_mock

            # Enable celery task logging for this test (simpler than request logging)
            settings.CLICKHOUSE_REQUEST_LOGGING = False
            settings.CLICKHOUSE_CELERY_TASK_LOGGING = True

            # Call the function
            flush_request_logs_to_clickhouse()

            # Verify that the backend was called
            assert get_backend_mock.called
            assert backend_mock.store_records.called

            # Verify that the data was put back into Redis using rpush
            assert instance_mock.rpush.called
            # Check that rpush was called with the correct key and data
            rpush_calls = instance_mock.rpush.call_args_list
            assert len(rpush_calls) == 1
            assert rpush_calls[0][0][0] == settings.CELERY_LOGGING_REDIS_KEY
            assert rpush_calls[0][0][1] == test_record_data

    def test_resilient_flush_request_logs_to_clickhouse_success(self, settings):
        """
        Test that when ClickHouse write succeeds, the data is not put back into Redis
        """
        # Create test data for celery task logging (simpler than request logging)
        test_record_data = pickle.dumps(
            {**COMMON_TEST_RECORD_DATA, "timestamp": datetime.now(), "execution_time": 1.0}
        )

        with patch("core.tasks.redis.Redis") as redis_mock, patch(
            "core.request_logging.clickhouse.get_logging_backend"
        ) as get_backend_mock:
            # Mock Redis instance
            instance_mock = Mock()
            instance_mock.lpop = MagicMock(side_effect=[test_record_data, None])
            redis_mock.return_value = instance_mock

            # Mock backend that succeeds
            backend_mock = Mock()
            backend_mock.store_records.return_value = None  # Success
            get_backend_mock.return_value = backend_mock

            # Enable celery task logging for this test
            settings.CLICKHOUSE_REQUEST_LOGGING = False
            settings.CLICKHOUSE_CELERY_TASK_LOGGING = True

            # Call the function
            flush_request_logs_to_clickhouse()

            # Verify that the backend was called
            assert get_backend_mock.called
            assert backend_mock.store_records.called

            # Verify that rpush was NOT called (no rollback needed)
            assert not instance_mock.rpush.called

    def test_resilient_flush_request_logs_to_clickhouse_multiple_batches(self, settings):
        """
        Test that when ClickHouse write fails, the data is put back into Redis and sync is canceled
        """
        # Create test data for celery task logging
        test_record_data = pickle.dumps(
            {**COMMON_TEST_RECORD_DATA, "timestamp": datetime.now(), "execution_time": 1.0}
        )

        with patch("core.tasks.redis.Redis") as redis_mock, patch(
            "core.request_logging.clickhouse.get_logging_backend"
        ) as get_backend_mock:
            # Mock Redis instance
            instance_mock = Mock()
            instance_mock.lpop = MagicMock(side_effect=[test_record_data, None])
            redis_mock.return_value = instance_mock

            # Mock backend that raises an exception on store_records
            backend_mock = Mock()
            backend_mock.store_records.side_effect = Exception("ClickHouse connection failed")
            get_backend_mock.return_value = backend_mock

            # Enable celery task logging for this test
            settings.CLICKHOUSE_REQUEST_LOGGING = False
            settings.CLICKHOUSE_CELERY_TASK_LOGGING = True

            # Call the function
            flush_request_logs_to_clickhouse()

            # Verify that the backend was called
            assert get_backend_mock.called
            assert backend_mock.store_records.called

            # Verify that the data was put back into Redis using rpush
            assert instance_mock.rpush.called
            # Check that rpush was called with the correct key and data
            rpush_calls = instance_mock.rpush.call_args_list
            assert len(rpush_calls) == 1
            assert rpush_calls[0][0][0] == settings.CELERY_LOGGING_REDIS_KEY
            assert rpush_calls[0][0][1] == test_record_data

    def test_resilient_flush_request_logs_to_clickhouse_rollback_real_redis(
        self, settings, redis_connection
    ):
        """
        Test that when ClickHouse write fails, the data is put back into Redis and sync is canceled
        Uses real Redis instead of mocks
        """
        # Create test data for celery task logging (simpler than request logging)
        test_record_data = pickle.dumps(
            {**COMMON_TEST_RECORD_DATA, "timestamp": datetime.now(), "execution_time": 1.0}
        )

        # Put test data into Redis
        redis_connection.rpush(settings.CELERY_LOGGING_REDIS_KEY, test_record_data)

        with patch("core.request_logging.clickhouse.get_logging_backend") as get_backend_mock:
            # Mock backend that raises an exception on store_records
            backend_mock = Mock()
            backend_mock.store_records.side_effect = Exception("ClickHouse connection failed")
            get_backend_mock.return_value = backend_mock

            # Enable celery task logging for this test (simpler than request logging)
            settings.CLICKHOUSE_REQUEST_LOGGING = False
            settings.CLICKHOUSE_CELERY_TASK_LOGGING = True

            # Call the function
            flush_request_logs_to_clickhouse()

            # Verify that the backend was called
            assert get_backend_mock.called
            assert backend_mock.store_records.called

            # Verify that the data was put back into Redis using rpush
            # Check that the data is still in Redis (was put back)
            remaining_data = redis_connection.lrange(settings.CELERY_LOGGING_REDIS_KEY, 0, -1)
            assert len(remaining_data) == 1
            assert remaining_data[0] == test_record_data

    def test_resilient_flush_request_logs_to_clickhouse_success_real_redis(
        self, settings, redis_connection
    ):
        """
        Test that when ClickHouse write succeeds, the data is not put back into Redis
        Uses real Redis instead of mocks
        """
        # Create test data for celery task logging (simpler than request logging)
        test_record_data = pickle.dumps(
            {**COMMON_TEST_RECORD_DATA, "timestamp": datetime.now(), "execution_time": 1.0}
        )

        # Put test data into Redis
        redis_connection.rpush(settings.CELERY_LOGGING_REDIS_KEY, test_record_data)

        with patch("core.request_logging.clickhouse.get_logging_backend") as get_backend_mock:
            # Mock backend that succeeds
            backend_mock = Mock()
            backend_mock.store_records.return_value = None  # Success
            get_backend_mock.return_value = backend_mock

            # Enable celery task logging for this test
            settings.CLICKHOUSE_REQUEST_LOGGING = False
            settings.CLICKHOUSE_CELERY_TASK_LOGGING = True

            # Call the function
            flush_request_logs_to_clickhouse()

            # Verify that the backend was called
            assert get_backend_mock.called
            assert backend_mock.store_records.called

            # Verify that the data was removed from Redis (successful processing)
            remaining_data = redis_connection.lrange(settings.CELERY_LOGGING_REDIS_KEY, 0, -1)
            assert len(remaining_data) == 0

    def test_resilient_flush_request_logs_to_clickhouse_multiple_batches_real_redis(
        self, settings, redis_connection
    ):
        """
        Test that when ClickHouse write fails, the data is put back into Redis and sync is canceled
        Uses real Redis instead of mocks
        """
        # Create test data for celery task logging
        test_record_data = pickle.dumps(
            {**COMMON_TEST_RECORD_DATA, "timestamp": datetime.now(), "execution_time": 1.0}
        )

        # Put test data into Redis
        redis_connection.rpush(settings.CELERY_LOGGING_REDIS_KEY, test_record_data)

        with patch("core.request_logging.clickhouse.get_logging_backend") as get_backend_mock:
            # Mock backend that raises an exception on store_records
            backend_mock = Mock()
            backend_mock.store_records.side_effect = Exception("ClickHouse connection failed")
            get_backend_mock.return_value = backend_mock

            # Enable celery task logging for this test
            settings.CLICKHOUSE_REQUEST_LOGGING = False
            settings.CLICKHOUSE_CELERY_TASK_LOGGING = True

            # Call the function
            flush_request_logs_to_clickhouse()

            # Verify that the backend was called
            assert get_backend_mock.called
            assert backend_mock.store_records.called

            # Verify that the data was put back into Redis using rpush
            # Check that the data is still in Redis (was put back)
            remaining_data = redis_connection.lrange(settings.CELERY_LOGGING_REDIS_KEY, 0, -1)
            assert len(remaining_data) == 1
            assert remaining_data[0] == test_record_data

    @pytest.mark.parametrize(
        "record_age_hours,should_send_email",
        [
            (0.5, False),  # 30 minutes old - should not send email
            (1.5, True),  # 1.5 hours old - should send email
            (2.0, True),  # 2 hours old - should send email
        ],
    )
    def test_resilient_flush_request_logs_to_clickhouse_email_on_old_records(
        self, settings, record_age_hours, should_send_email, redis_connection
    ):
        """
        Test that when ClickHouse write fails and records are older than 1 hour,
        an email is sent to admins
        Uses real Redis and freezegun to test different time scenarios
        """
        # Freeze time to ensure consistent testing
        with freeze_time("2023-01-01 12:00:00"):
            # Create test data with a specific timestamp (timezone-aware)
            # Use the frozen time directly, then subtract the age
            base_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=pytz.UTC)
            record_timestamp = base_time - timedelta(hours=record_age_hours)

            # Create test data that matches the actual CeleryTaskLogRecord structure
            # Based on create_celery_task_log_dict function
            test_record_data = pickle.dumps(
                {
                    **COMMON_TEST_RECORD_DATA,
                    "timestamp": record_timestamp,
                    "execution_time": 10,  # milliseconds
                }
            )

            # Put test data into Redis
            redis_connection.rpush(settings.CELERY_LOGGING_REDIS_KEY, test_record_data)

            with patch(
                "core.request_logging.clickhouse.get_logging_backend"
            ) as get_backend_mock, patch("core.tasks.async_mail_admins") as mail_admins_mock:
                # Mock backend that raises an exception on store_records
                backend_mock = Mock()
                backend_mock.store_records.side_effect = Exception("ClickHouse connection failed")
                get_backend_mock.return_value = backend_mock

                # Enable celery task logging for this test
                settings.CLICKHOUSE_REQUEST_LOGGING = False
                settings.CLICKHOUSE_CELERY_TASK_LOGGING = True

                # Call the function
                flush_request_logs_to_clickhouse()

            # Verify that the backend was called
            assert get_backend_mock.called
            assert backend_mock.store_records.called

            # Verify that the data was put back into Redis using rpush
            # Check that the data is still in Redis (was put back)
            remaining_data = redis_connection.lrange(settings.CELERY_LOGGING_REDIS_KEY, 0, -1)
            assert len(remaining_data) == 1
            assert remaining_data[0] == test_record_data

            # Check if email was sent based on record age
            if should_send_email:
                assert (
                    mail_admins_mock.called
                ), f"Email should have been sent for record age {record_age_hours} hours"
                # Verify email content
                call_args = mail_admins_mock.call_args
                assert (
                    "Sync canceled for celery logs due to Clickhouse write failure"
                    in call_args[0][0]
                )
                assert "older than 1 hour" in call_args[0][1]
                assert "should be investigated" in call_args[0][1]
            else:
                assert (
                    not mail_admins_mock.called
                ), f"Email should not have been sent for record age {record_age_hours} hours"
