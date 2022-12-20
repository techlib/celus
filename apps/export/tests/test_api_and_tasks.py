from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from core.logic.serialization import b64json
from django.urls import reverse
from django.utils.timezone import now
from export.models import FlexibleDataExport

from apps.export.tasks import delete_expired_flexible_data_exports_task
from test_fixtures.scenarios.basic import clients, identities


@pytest.fixture
def exports_for_users(users):
    return (
        FlexibleDataExport.objects.create(owner=users['user1']),
        FlexibleDataExport.objects.create(owner=users['master_admin']),
    )


@pytest.fixture
def export_pk(users, settings):
    user = users['user1']
    not_obsolete = FlexibleDataExport.objects.create(owner=user)
    not_obsolete.created = now() - settings.EXPORT_DELETING_PERIOD + timedelta(days=1)
    not_obsolete.save()

    obsolete = FlexibleDataExport.objects.create(owner=user)
    obsolete.created = now() - settings.EXPORT_DELETING_PERIOD - timedelta(days=1)
    obsolete.save()
    return {"not_obsolete": not_obsolete.pk, "obsolete": obsolete.pk}


@pytest.mark.django_db
class TestFlexibleExportApi:
    def test_list_no_data(self, admin_client):
        resp = admin_client.get(reverse('flexible-export-list'))
        assert resp.status_code == 200

    @pytest.mark.parametrize(
        ['user_name'], [['user1'], ['user2'], ['master_admin'], ['master_user'], ['admin1']]
    )
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

    def test_delete_not_owned_export(self, exports_for_users, clients):
        exported_by_user1_id = exports_for_users[0].id
        url = reverse("flexible-export-detail", args=(exported_by_user1_id,))
        res = clients["user2"].delete(url)
        assert res.status_code == 404

    def test_delete(self, clients, exports_for_users):
        export = exports_for_users[0]
        assert FlexibleDataExport.objects.filter(id=export.id).exists()
        export.create_output_file()
        assert export.output_file is not None
        export.output_file.open('r')
        export.output_file.close()
        res = clients["user1"].delete(reverse("flexible-export-detail", args=(export.id,)))
        assert res.status_code == 204
        assert not FlexibleDataExport.objects.filter(id=export.id).exists()
        assert not Path(export.output_file.path).exists()

    def test_list_not_obsolete_exports(self, client, users, export_pk):
        user = users['user1']
        client.force_login(user)
        resp = client.get(reverse('flexible-export-list'))
        resp_pks = [export['pk'] for export in resp.json()]

        assert export_pk["not_obsolete"] in resp_pks
        assert export_pk["obsolete"] not in resp_pks


@pytest.mark.django_db
class TestFlexibleExportTasks:
    def test_delete_expired_flexible_data_exports_task(self, export_pk):
        assert FlexibleDataExport.objects.filter(pk=export_pk["not_obsolete"]).exists()
        assert FlexibleDataExport.objects.filter(pk=export_pk["obsolete"]).exists()
        delete_expired_flexible_data_exports_task()
        assert FlexibleDataExport.objects.filter(pk=export_pk["not_obsolete"]).exists()
        assert not FlexibleDataExport.objects.filter(pk=export_pk["obsolete"]).exists()
