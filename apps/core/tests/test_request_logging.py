from unittest.mock import MagicMock, Mock, patch

import pytest
from django.urls import reverse


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

            from core.tasks import flush_request_logs_to_clickhouse

            flush_request_logs_to_clickhouse()
            assert redis_mock.called
            assert instance_mock.lpop.called
            assert instance_mock.lpop.call_count == 3
            assert instance_mock.lpop.call_args_list[0][0][0] == settings.REQUEST_LOGGING_REDIS_KEY

    @pytest.mark.parametrize('anonymous', [True, False])
    def test_the_whole_logging_process(self, settings, admin_client, admin_user, client, anonymous):
        """
        Make a request, store the data that would be sent to redis, then call the task
        and present it with the data and check that it gets sent to clickhouse
        """
        # I don't know why, but if I do not do the get first, it all crashes down on
        # partially imported module
        # The following seems to force the settings to be completely loaded and I can
        # then mock it without trouble
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
            instance_mock.lpop = MagicMock(side_effect=[redis_stored_record, None])
            redis_mock.return_value = instance_mock

            from core.tasks import flush_request_logs_to_clickhouse

            flush_request_logs_to_clickhouse()
            assert get_backend_mock.called
            assert backend_mock.store_records.called
            stored_records = backend_mock.store_records.call_args[0][1]
            assert len(stored_records) == 1
            rec = stored_records[0]
            assert rec.request_url_name == 'user_api_view'
            assert rec.request_method == 'GET'
            assert rec.user_id == (admin_user.pk if not anonymous else 0)
