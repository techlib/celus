from unittest.mock import patch

import pytest
from django.urls import reverse

from core.logic.serialization import b64json
from export.models import FlexibleDataExport


@pytest.fixture
def exports_for_users(users):
    FlexibleDataExport.objects.create(owner=users['user1'])
    FlexibleDataExport.objects.create(owner=users['master'])


@pytest.mark.django_db
class TestFlexibleExportApi:
    def test_list_no_data(self, admin_client):
        resp = admin_client.get(reverse('flexible-export-list'))
        assert resp.status_code == 200

    @pytest.mark.parametrize(['user_name'], [['user1'], ['user2'], ['master'], ['admin1']])
    def test_list_user_access(self, exports_for_users, users, user_name, client):
        """Check that user has only access to export created by himself"""
        user = users[user_name]
        client.force_login(user)
        resp = client.get(reverse('flexible-export-list'))
        assert resp.status_code == 200
        for rec in resp.json():
            export = FlexibleDataExport.objects.get(pk=rec['pk'])
            assert export.owner == user

    def test_list_user_only_authenticated(self, exports_for_users, client):
        resp = client.get(reverse('flexible-export-list'))
        assert resp.status_code in (401, 403)

    def test_create(self, admin_client, admin_user):
        with patch('export.views.process_flexible_export_task') as export_task:
            resp = admin_client.post(
                reverse('flexible-export-list'),
                {'primary_dimension': 'platform', 'groups': b64json(['metric'])},
                content_type='application/json',
            )
            export_task.apply_async.assert_called_once()
        assert resp.status_code == 201
        export = FlexibleDataExport.objects.get(pk=resp.json()['pk'])
        assert export.owner == admin_user

    def test_create_with_date_filter(self, admin_client, admin_user):
        with patch('export.views.process_flexible_export_task') as export_task:
            resp = admin_client.post(
                reverse('flexible-export-list'),
                {
                    'primary_dimension': 'platform',
                    'groups': b64json(['metric']),
                    'filters': b64json({'date': {'start': '2020-01'}}),
                },
                content_type='application/json',
            )
            export_task.apply_async.assert_called_once()
        assert resp.status_code == 201
        export = FlexibleDataExport.objects.get(pk=resp.json()['pk'])
        assert export.owner == admin_user
