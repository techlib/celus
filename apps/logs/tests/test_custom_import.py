from datetime import date
from io import StringIO

import pytest
from django.core.files import File
from django.urls import reverse

from core.models import User, Identity, UL_ORG_ADMIN, UL_CONS_STAFF
from logs.logic.custom_import import custom_data_to_records, import_custom_data
from logs.models import ReportType, AccessLog, DimensionText, ImportBatch, ManualDataUpload
from publications.models import Platform, Title

from ..logic.data_import import import_counter_records
from organizations.tests.conftest import *
from publications.tests.conftest import *
from core.tests.conftest import authenticated_client, valid_identity, master_identity, master_client


@pytest.mark.django_db
class TestCustomImport(object):

    """
    Tests functionality of the logic.custom_import module
    """

    def test_custom_data_to_records_1(self):
        data = [
            {'Metric': 'M1', 'Jan 2019': 10, 'Feb 2019': 7, 'Mar 2019': 11},
            {'Metric': 'M2', 'Jan 2019': 1, 'Feb 2019': 2, 'Mar 2019': 3},
        ]
        records = custom_data_to_records(data)
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

    def test_custom_data_to_records_with_init_data(self):
        data = [
            {'MetricXX': 'M1', 'Jan 2019': 10, 'Feb 2019': 7, 'Mar 2019': 11},
            {'MetricXX': 'M2', 'Jan 2019': 1, 'Feb 2019': 2, 'Mar 2019': 3},
        ]
        records = custom_data_to_records(
            data, initial_data={'platform_name': 'PLA1'}, column_map={'MetricXX': 'metric'}
        )
        assert len(records) == 6
        for record in records:
            assert record.value in (1, 2, 3, 7, 10, 11)
            assert record.platform_name == 'PLA1'
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
        records = custom_data_to_records(
            data, initial_data={'platform_name': 'PLA1', 'metric': 'MD'}
        )
        assert len(records) == 6
        for record in records:
            assert record.value in (1, 2, 3, 7, 10, 11)
            assert record.platform_name == 'PLA1'
            assert record.start in (date(2019, 1, 1), date(2019, 2, 1), date(2019, 3, 1))
            if record.value in (10, 7, 11):
                assert record.metric == 'MD'
            else:
                assert record.metric == 'MX'

    def test_custom_data_import_process(
        self, organizations, report_type_nd, tmp_path, settings, master_client, master_identity
    ):
        """
        Complex text
          - upload data to create ManualDataUpload object using the API
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
        # let's process the mdu
        assert AccessLog.objects.count() == 0
        response = master_client.post(reverse('manual-data-upload-process', args=(mdu.pk,)))
        assert response.status_code == 200
        mdu.refresh_from_db()
        assert mdu.is_processed
        assert mdu.user_id == Identity.objects.get(identity=master_identity).user_id
        assert AccessLog.objects.count() == 6
        # reprocess
        response = master_client.post(reverse('manual-data-upload-process', args=(mdu.pk,)))
        assert response.status_code == 200
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
        response = master_client.post(reverse('manual-data-upload-process', args=(mdu.pk,)))
        assert response.status_code == 200
        assert AccessLog.objects.count() == 6, 'no new AccessLogs'

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
        assert mdu.import_batch is None
        # let's process the mdu
        assert AccessLog.objects.count() == 0
        response = master_client.post(reverse('manual-data-upload-process', args=(mdu.pk,)))
        assert response.status_code == 200
        mdu.refresh_from_db()
        assert mdu.is_processed
        assert mdu.user_id == Identity.objects.get(identity=master_identity).user_id
        assert AccessLog.objects.count() == 6
        assert mdu.import_batch is not None
        assert mdu.import_batch.accesslog_count == 6
        assert ImportBatch.objects.count() == 1
        # let's delete the object
        response = master_client.delete(reverse('manual-data-upload-detail', args=(mdu.pk,)))
        assert response.status_code == 204
        assert ManualDataUpload.objects.filter(pk=mdu.pk).count() == 0
        assert ImportBatch.objects.count() == 0
        assert AccessLog.objects.count() == 0

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
        client,
        organizations,
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
        assert mdu.import_batch is None
        user = Identity.objects.get(identity=identity).user
        import_custom_data(mdu, user)
        mdu.refresh_from_db()
        assert mdu.import_batch is not None
        assert mdu.import_batch.owner_level == mdu.owner_level
