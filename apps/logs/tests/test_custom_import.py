from datetime import date
from io import StringIO

import pytest
from django.core.files import File
from django.core.files.base import ContentFile
from django.urls import reverse

from core.models import Identity, UL_ORG_ADMIN, UL_CONS_STAFF
from core.tests.conftest import *  # noqa
from organizations.tests.conftest import identity_by_user_type, organizations  # noqa
from publications.tests.conftest import platforms  # noqa
from logs.tasks import prepare_preflight, import_manual_upload_data
from logs.logic.custom_import import custom_data_to_records, import_custom_data
from logs.models import AccessLog, ImportBatch, ManualDataUpload
from publications.models import Platform
from test_fixtures.entities.logs import ManualDataUploadFullFactory


@pytest.mark.django_db
class TestCustomImport:

    """
    Tests functionality of the logic.custom_import module
    """

    def test_custom_data_to_records_1(self):
        data = [
            {'Metric': 'M1', 'Jan 2019': 10, 'Feb 2019': 7, 'Mar 2019': 11},
            {'Metric': 'M2', 'Jan 2019': 1, 'Feb 2019': 2, 'Mar 2019': 3},
        ]
        records = [e for e in custom_data_to_records(data)]
        assert len(records) == 6
        for record in records:
            assert record.value in (1, 2, 3, 7, 10, 11)
            assert record.start in (date(2019, 1, 1), date(2019, 2, 1), date(2019, 3, 1))
            if record.value in (10, 7, 11):
                assert record.metric == 'M1'
                if record.start == date(2019, 1, 1):
                    assert record.value == 10
            else:
                assert record.metric == 'M2'

    def test_custom_data_to_records_with_column_map(self):
        data = [
            {'MetricXX': 'M1', 'Jan 2019': 10, 'Feb 2019': 7, 'Mar 2019': 11},
            {'MetricXX': 'M2', 'Jan 2019': 1, 'Feb 2019': 2, 'Mar 2019': 3},
        ]
        records = custom_data_to_records(data, column_map={'MetricXX': 'metric'})
        records = [e for e in records]  # convert generator to a list
        assert len(records) == 6
        for record in records:
            assert record.value in (1, 2, 3, 7, 10, 11)
            assert record.start in (date(2019, 1, 1), date(2019, 2, 1), date(2019, 3, 1))
            if record.value in (10, 7, 11):
                assert record.metric == 'M1'
                if record.start == date(2019, 1, 1):
                    assert record.value == 10
            else:
                assert record.metric == 'M2'

    def test_custom_data_to_records_no_metric(self):
        data = [
            {'Jan 2019': 10, 'Feb 2019': 7, 'Mar 2019': 11},
            {'Jan 2019': 1, 'Feb 2019': 2, 'Mar 2019': 3, 'Metric': 'MX'},
        ]
        records = custom_data_to_records(data, initial_data={'metric': 'MD'})
        records = [e for e in records]  # convert generator to a list
        assert len(records) == 6
        for record in records:
            assert record.value in (1, 2, 3, 7, 10, 11)
            assert record.start in (date(2019, 1, 1), date(2019, 2, 1), date(2019, 3, 1))
            if record.value in (10, 7, 11):
                assert record.metric == 'MD'
            else:
                assert record.metric == 'MX'

    def test_custom_data_import_process(
        self, organizations, report_type_nd, tmp_path, settings, master_client, master_identity
    ):
        """
        Complex test
          - upload data to create ManualDataUpload object using the API
          - calculate preflight via celery
          - process the ManualDataUpload and check the resulting data
          - check that next process does not create new AccessLogs
          - reimport the same data
          - test that the import does not create new AccessLogs
        """
        report_type = report_type_nd(0)
        organization = organizations[0]
        platform = Platform.objects.create(
            ext_id=1234, short_name='Platform1', name='Platform 1', provider='Provider 1'
        )
        csv_content = 'Metric,Jan-2019,Feb 2019,2019-03\nM1,10,7,11\nM2,1,2,3\n'
        file = StringIO(csv_content)
        settings.MEDIA_ROOT = tmp_path

        # upload the data
        response = master_client.post(
            reverse('manual-data-upload-list'),
            data={
                'platform': platform.id,
                'organization': organization.pk,
                'report_type': report_type.pk,
                'data_file': file,
            },
        )
        assert response.status_code == 201
        mdu = ManualDataUpload.objects.get(pk=response.json()['pk'])
        assert mdu.organization == organization
        assert mdu.import_batches.count() == 0, 'no import batches yet'

        # calculate preflight in celery
        prepare_preflight(mdu.pk)

        response = master_client.get(reverse('manual-data-upload-detail', args=(mdu.pk,)))
        assert response.status_code == 200
        data = response.json()
        assert data['preflight']['hits_total'] == 10 + 7 + 11 + 1 + 2 + 3  # see the csv_content

        # let's process the mdu
        assert AccessLog.objects.count() == 0
        response = master_client.post(reverse('manual-data-upload-import-data', args=(mdu.pk,)))
        assert response.status_code == 200
        # import data (this should be handled via celery)
        import_manual_upload_data(mdu.pk, mdu.user.pk)

        mdu.refresh_from_db()
        assert mdu.is_processed
        assert mdu.user_id == Identity.objects.get(identity=master_identity).user_id
        assert AccessLog.objects.count() == 6
        assert mdu.import_batches.count() == 3, '3 months of data'

        # reprocess
        response = master_client.post(reverse('manual-data-upload-import-data', args=(mdu.pk,)))
        assert response.status_code == 200, "already imported, nothing needs to be done"
        assert AccessLog.objects.count() == 6, 'no new AccessLogs'

        # the whole thing once again
        file.seek(0)
        response = master_client.post(
            reverse('manual-data-upload-list'),
            data={
                'platform': platform.id,
                'organization': organization.pk,
                'report_type': report_type.pk,
                'data_file': file,
            },
        )
        assert response.status_code == 201

        mdu = ManualDataUpload.objects.get(pk=response.json()['pk'])

        # calculate preflight in celery
        prepare_preflight(mdu.pk)

        response = master_client.get(reverse('manual-data-upload-detail', args=(mdu.pk,)))
        assert response.status_code == 200
        data = response.json()
        assert data['preflight']['hits_total'] == 10 + 7 + 11 + 1 + 2 + 3  # see the csv_content
        assert len(data['clashing_months']) == 3, 'all 3 months are already there'
        assert data['can_import'] is False, 'preflight signals that import is not possible'
        response = master_client.post(reverse('manual-data-upload-import-data', args=(mdu.pk,)))
        assert response.status_code == 409
        assert AccessLog.objects.count() == 6, 'no new AccessLogs'
        mdu.refresh_from_db()
        assert not mdu.is_processed, 'crash - should not mark mdu as processed'

    def test_manual_data_upload_api_delete(
        self, organizations, report_type_nd, tmp_path, settings, master_client, master_identity
    ):
        """
        When deleting manual data upload, we need to delete the import_batch as well.
        """
        report_type = report_type_nd(0)
        organization = organizations[0]
        platform = Platform.objects.create(
            ext_id=1234, short_name='Platform1', name='Platform 1', provider='Provider 1'
        )
        csv_content = 'Metric,Jan-2019,Feb 2019,2019-03\nM1,10,7,11\nM2,1,2,3\n'
        file = StringIO(csv_content)
        settings.MEDIA_ROOT = tmp_path
        response = master_client.post(
            reverse('manual-data-upload-list'),
            data={
                'platform': platform.id,
                'organization': organization.pk,
                'report_type': report_type.pk,
                'data_file': file,
            },
        )
        assert response.status_code == 201
        mdu = ManualDataUpload.objects.get(pk=response.json()['pk'])
        assert mdu.import_batches.count() == 0
        # let's process the mdu
        assert AccessLog.objects.count() == 0

        # calculate preflight in celery
        prepare_preflight(mdu.pk)

        response = master_client.post(reverse('manual-data-upload-import-data', args=(mdu.pk,)))
        assert response.status_code == 200

        import_manual_upload_data(mdu.pk, mdu.user.pk)

        mdu.refresh_from_db()
        assert mdu.is_processed
        assert mdu.user_id == Identity.objects.get(identity=master_identity).user_id
        assert AccessLog.objects.count() == 6
        assert mdu.import_batches.count() == 3, '3 months of data = 3 import batches'
        assert mdu.accesslogs.count() == 6
        assert ImportBatch.objects.count() == 3
        # let's delete the object
        response = master_client.delete(reverse('manual-data-upload-detail', args=(mdu.pk,)))
        assert response.status_code == 204
        assert ManualDataUpload.objects.filter(pk=mdu.pk).count() == 0
        assert ImportBatch.objects.count() == 0
        assert AccessLog.objects.count() == 0

    @pytest.mark.parametrize(
        ['user_type', 'allowed'],
        [
            ['no_user', False],
            ['invalid', False],
            ['unrelated', False],
            ['related_user', False],
            ['related_admin', True],
            ['master_user', True],
            ['superuser', True],
        ],
    )
    def test_custom_data_import_api_owner_level(
        self,
        user_type,
        allowed,
        settings,
        tmp_path,
        identity_by_user_type,
        report_type_nd,
        platforms,
        client,
        authentication_headers,
    ):
        identity, org = identity_by_user_type(user_type)
        report_type = report_type_nd(0)
        platform = Platform.objects.create(
            ext_id=1234, short_name='Platform1', name='Platform 1', provider='Provider 1'
        )
        csv_content = 'Metric,Jan-2019,Feb 2019,2019-03\nM1,10,7,11\nM2,1,2,3\n'
        file = StringIO(csv_content)
        settings.MEDIA_ROOT = tmp_path

        # upload the data
        response = client.post(
            reverse('manual-data-upload-list'),
            data={
                'platform': platform.id,
                'organization': org.pk,
                'report_type': report_type.pk,
                'data_file': file,
            },
            **authentication_headers(identity),
        )
        assert response.status_code == 201 if allowed else 403
        if allowed:
            mdu = ManualDataUpload.objects.get(pk=response.json()['pk'])

            # calculate preflight in celery
            prepare_preflight(mdu.pk)

            response = client.get(
                reverse('manual-data-upload-detail', args=(mdu.pk,)),
                **authentication_headers(identity),
            )
            assert response.status_code == 200

            # let's process the mdu
            response = client.post(
                reverse('manual-data-upload-import-data', args=(mdu.pk,)),
                **authentication_headers(identity),
            )

            assert response.status_code == 200

    @pytest.mark.parametrize(
        ['user_type', 'owner_level'],
        [
            ['related_admin', UL_ORG_ADMIN],
            ['master_user', UL_CONS_STAFF],
            ['superuser', UL_CONS_STAFF],
        ],
    )
    def test_custom_data_import_owner_level(
        self,
        user_type,
        owner_level,
        settings,
        tmp_path,
        identity_by_user_type,
        report_type_nd,
        platforms,
    ):
        identity, org = identity_by_user_type(user_type)
        rt = report_type_nd(0)
        settings.MEDIA_ROOT = tmp_path
        file = File(StringIO('Source,2019-01\naaaa,9\n'))
        mdu = ManualDataUpload.objects.create(
            organization=org, platform=platforms[0], report_type=rt, owner_level=owner_level,
        )
        mdu.data_file.save('xxx', file)
        assert mdu.import_batches.count() == 0
        user = Identity.objects.get(identity=identity).user
        import_custom_data(mdu, user)
        mdu.refresh_from_db()
        assert mdu.import_batches.count() > 0
        for ib in mdu.import_batches.all():
            assert ib.owner_level == mdu.owner_level

    @pytest.mark.parametrize(['content_prefix'], [[''], ['\ufeff']])
    def test_mdu_data_to_records(
        self, organizations, report_type_nd, tmp_path, settings, content_prefix
    ):
        """
        Check that CSV data are correctly ingested - regardless of BOM presence
        """
        report_type = report_type_nd(0)
        organization = organizations[0]
        platform = Platform.objects.create(
            ext_id=1234, short_name='Platform1', name='Platform 1', provider='Provider 1'
        )
        csv_content = f'{content_prefix}Metric,Jan-2019,Feb 2019,2019-03\nM1,10,7,11\nM2,1,2,3\n'
        file = ContentFile(csv_content)
        file.name = f"something.csv"
        settings.MEDIA_ROOT = tmp_path

        mdu = ManualDataUpload.objects.create(
            report_type=report_type, organization=organization, platform=platform, data_file=file,
        )
        assert len(list(mdu.data_to_records())) == 6

    @pytest.mark.parametrize(
        ['content', 'is_json'],
        [
            ['Whatever', False],
            ['  !', False],
            ['  {', True],
            ['  [', True],
            ['[', True],
            ['{', True],
            ['\t[', True],
            ['\t{', True],
        ],
    )
    def test_mdu_json(self, organizations, report_type_nd, tmp_path, settings, content, is_json):
        """
        Check that JSON data are properly recognized during import
        """
        report_type = report_type_nd(0)
        organization = organizations[0]
        platform = Platform.objects.create(
            ext_id=1234, short_name='Platform1', name='Platform 1', provider='Provider 1'
        )
        file = ContentFile(content)
        file.name = f"something.csv"
        settings.MEDIA_ROOT = tmp_path

        mdu = ManualDataUpload.objects.create(
            report_type=report_type, organization=organization, platform=platform, data_file=file,
        )
        assert mdu.file_is_json() == is_json

    def test_mdu_list_view(self, admin_client):
        """
        Test the manual data upload global api endpoint
        """
        mdus = ManualDataUploadFullFactory.create_batch(5, is_processed=False)
        mdus += ManualDataUploadFullFactory.create_batch(5, is_processed=True)
        resp = admin_client.get(reverse('manual-data-upload-list'))
        assert resp.status_code == 200
        assert len(resp.json()) == 10

    def test_organization_mdu_list_view(self, admin_client):
        """
        Test the manual data upload api endpoint for an organization
        """
        mdus = ManualDataUploadFullFactory.create_batch(5, is_processed=False)
        mdus += ManualDataUploadFullFactory.create_batch(5, is_processed=True)
        resp = admin_client.get(reverse('organization-manual-data-upload-list', args=(-1,)))
        assert resp.status_code == 200
        assert len(resp.json()) == 10
