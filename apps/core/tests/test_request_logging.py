from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
import pytz
from django.urls import reverse
from django_celery_results.models import TaskResult

from core.request_logging.celery_capture import celery_task_log, create_celery_task_log_dict
from core.tasks import flush_request_logs_to_clickhouse


@pytest.mark.django_db
class TestRequestLogging:
    def test_request_logging(self, settings, admin_client):
        # the setting should be set to True from env - we cannot do it here
        # as there are things which depend on it in settings/base.py
        assert settings.CLICKHOUSE_REQUEST_LOGGING
        assert 'requestlogs.middleware.RequestLogsMiddleware' in settings.MIDDLEWARE
        # I don't know why, but if I do not do the get first, it all crashes down on
        # partially imported module
        # The following seems to force the settings to be completely loaded and I can
        # then mock it without trouble
        admin_client.get(reverse('user_api_view'))
        with patch('core.request_logging.capture.redis.Redis') as redis_mock:
            instance_mock = Mock()
            redis_mock.return_value = instance_mock
            resp = admin_client.get(reverse('user_api_view'))
            assert resp.status_code == 200
            assert redis_mock.called
            assert instance_mock.rpush.called

    def test_flush_request_logs_to_clickhouse_task(self, settings):
        """
        Test that the task gets the corresponding data from redis
        :return:
        """
        with patch('core.tasks.redis.Redis') as redis_mock:
            instance_mock = Mock()
            instance_mock.lpop = MagicMock(side_effect=['a', 'b', None])
            redis_mock.return_value = instance_mock
            flush_request_logs_to_clickhouse()
            assert redis_mock.called
            assert instance_mock.lpop.called
            assert instance_mock.lpop.call_count == 3
            assert instance_mock.lpop.call_args_list[0][0][0] == settings.REQUEST_LOGGING_REDIS_KEY

    @pytest.mark.parametrize('has_data', [True, False])
    @pytest.mark.parametrize('anonymous', [True, False])
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
        client_obj.get(reverse('user_api_view'))
        with patch('core.request_logging.capture.redis.Redis') as redis_mock:
            instance_mock = Mock()
            redis_mock.return_value = instance_mock
            resp = client_obj.get(reverse('user_api_view'))
            assert resp.status_code == (200 if not anonymous else 401)
            assert instance_mock.rpush.called
            redis_stored_record = instance_mock.rpush.call_args[0][1]

        with patch('core.tasks.redis.Redis') as redis_mock, patch(
            'core.request_logging.clickhouse.get_logging_backend'
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
                assert rec.request_url_name == 'user_api_view'
                assert rec.request_method == 'GET'
                assert rec.user_id == (admin_user.pk if not anonymous else 0)
            else:
                assert not get_backend_mock.called
                assert not backend_mock.store_records.called

    @pytest.mark.parametrize('has_task_result', [True, False])
    def test_celery_capture_log_create(self, has_task_result):
        if has_task_result:
            TaskResult(
                task_id=1,
                task_name='test_task',
                status='SUCCESS',
                date_created=datetime(2020, 1, 1, 1, 1, 1, 1, tzinfo=pytz.UTC),
                date_done=datetime(2020, 1, 1, 1, 1, 1, 3000, tzinfo=pytz.UTC),
            )

        out = create_celery_task_log_dict(task_id=1, task=Mock(__name__='test_task'))
        assert set(out.keys()) == {
            'hostname',
            'db_server',
            'clickhouse_db_server',
            'timestamp',
            'debug',
            'celus_version',
            'celus_git_hash',
            'clickhouse_query_active',
            'query_count_django',
            'query_count_clickhouse',
            'execution_time',
            'task_name',
            'task_args',
            'task_kwargs',
            'status',
        }

    @pytest.mark.parametrize('has_task_result', [True, False])
    def test_the_celery_logging(self, has_task_result, settings, clients):
        """
        Make a request, store the data that would be sent to redis, then call the task
        and present it with the data and check that it gets sent to clickhouse
        """
        if has_task_result:
            TaskResult(
                task_id=1,
                task_name='test_task',
                status='SUCCESS',
                date_created=datetime(2020, 1, 1, 1, 1, 1, 1, tzinfo=pytz.UTC),
                date_done=datetime(2020, 1, 1, 1, 1, 1, 3000, tzinfo=pytz.UTC),
            )
        # switch off request logging, so that only celery logging is used
        settings.CLICKHOUSE_REQUEST_LOGGING = False
        settings.CLICKHOUSE_CELERY_TASK_LOGGING = True
        # if we do not do a request first, the mock later will fail with circular import
        # no idea why
        clients['admin1'].get(reverse('user_api_view'))
        with patch('core.request_logging.capture.redis.Redis') as redis_mock:
            instance_mock = Mock()
            redis_mock.return_value = instance_mock
            celery_task_log(task_id=1, task=Mock(__name__='test_task'))
            assert instance_mock.rpush.called
            redis_stored_record = instance_mock.rpush.call_args[0][1]

        with patch('core.tasks.redis.Redis') as redis_mock, patch(
            'core.request_logging.clickhouse.get_logging_backend'
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
