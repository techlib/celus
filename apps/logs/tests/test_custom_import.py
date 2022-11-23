from datetime import date
from io import StringIO
from pathlib import Path

import pytest
from core.models import UL_CONS_STAFF, UL_ORG_ADMIN, Identity, SourceFileMixin
from core.tests.conftest import *  # noqa
from django.core.files import File
from django.core.files.base import ContentFile
from django.urls import reverse
from logs.exceptions import OrganizationNotAllowedToImportRawData
from logs.logic.custom_import import import_custom_data
from logs.models import AccessLog, ImportBatch, ManualDataUpload, MduMethod, MduState
from logs.tasks import import_manual_upload_data, prepare_preflight
from publications.models import Platform
from test_fixtures.entities.logs import ManualDataUploadFactory, ManualDataUploadFullFactory
from test_fixtures.scenarios.basic import (
    basic1,
    clients,
    data_sources,
    identities,
    metrics,
    organizations,
    parser_definitions,
    platforms,
    report_types,
    users,
)


@pytest.fixture(params=[True, False])
def enable_nibbler_for_celus_format(request):
    yield request.param


@pytest.mark.django_db
class TestCustomImport:

    """
    Tests functionality of the logic.custom_import module
    """

    def test_custom_data_import_process(
        self,
        organizations,
        report_types,
        tmp_path,
        settings,
        clients,
        users,
        basic1,
        platforms,
        enable_nibbler_for_celus_format,
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
        settings.ENABLE_NIBBLER_FOR_CELUS_FORMAT = enable_nibbler_for_celus_format
        report_type = report_types['custom1']
        organization = organizations['standalone']
        platform = platforms['standalone']
        csv_content = 'Metric,Jan-2019,Feb 2019,2019-03\nM1,10,7,11\nM2,1,2,3\n'
        file = ContentFile(csv_content)
        file.name = "something.csv"
        settings.MEDIA_ROOT = tmp_path

        # upload the data
        response = clients['master_admin'].post(
            reverse('manual-data-upload-list'),
            data={
                'platform': platform.id,
                'organization': organization.pk,
                'report_type_id': report_type.pk,
                'data_file': file,
                'method': MduMethod.CELUS,
            },
        )
        assert response.status_code == 201
        mdu = ManualDataUpload.objects.get(pk=response.json()['pk'])
        assert mdu.organization == organization
        assert mdu.import_batches.count() == 0, 'no import batches yet'

        # calculate preflight in celery
        prepare_preflight(mdu.pk)

        response = clients['master_admin'].get(reverse('manual-data-upload-detail', args=(mdu.pk,)))
        assert response.status_code == 200
        data = response.json()
        assert data['preflight']['hits_total'] == 10 + 7 + 11 + 1 + 2 + 3  # see the csv_content

        # let's process the mdu
        assert AccessLog.objects.count() == 0
        response = clients['master_admin'].post(
            reverse('manual-data-upload-import-data', args=(mdu.pk,))
        )
        assert response.status_code == 200
        # import data (this should be handled via celery)
        import_manual_upload_data(mdu.pk, mdu.user.pk)

        mdu.refresh_from_db()
        assert mdu.is_processed
        assert mdu.user == users['master_admin']
        assert AccessLog.objects.count() == 6
        assert mdu.import_batches.count() == 3, '3 months of data'

        # reprocess
        response = clients['master_admin'].post(
            reverse('manual-data-upload-import-data', args=(mdu.pk,))
        )
        assert response.status_code == 200, "already imported, nothing needs to be done"
        assert AccessLog.objects.count() == 6, 'no new AccessLogs'

        # the whole thing once again
        file.seek(0)
        response = clients['master_admin'].post(
            reverse('manual-data-upload-list'),
            data={
                'platform': platform.id,
                'organization': organization.pk,
                'report_type_id': report_type.pk,
                'data_file': file,
                'method': MduMethod.CELUS,
            },
        )
        assert response.status_code == 201

        mdu = ManualDataUpload.objects.get(pk=response.json()['pk'])

        # calculate preflight in celery
        prepare_preflight(mdu.pk)

        response = clients['master_admin'].get(reverse('manual-data-upload-detail', args=(mdu.pk,)))
        assert response.status_code == 200
        data = response.json()
        assert data['preflight']['hits_total'] == 10 + 7 + 11 + 1 + 2 + 3  # see the csv_content
        assert len(data['clashing_months']) == 3, 'all 3 months are already there'
        assert data['can_import'] is False, 'preflight signals that import is not possible'
        response = clients['master_admin'].post(
            reverse('manual-data-upload-import-data', args=(mdu.pk,))
        )
        assert response.status_code == 409
        assert AccessLog.objects.count() == 6, 'no new AccessLogs'
        mdu.refresh_from_db()
        assert not mdu.is_processed, 'crash - should not mark mdu as processed'

    def test_manual_data_upload_api_delete(
        self, organizations, platforms, report_types, tmp_path, settings, clients, users, basic1,
    ):
        """
        When deleting manual data upload, we need to delete the import_batch as well.
        """
        report_type = report_types['custom1']
        organization = organizations['standalone']
        platform = platforms['standalone']

        csv_content = 'Metric,Jan-2019,Feb 2019,2019-03\nM1,10,7,11\nM2,1,2,3\n'
        file = ContentFile(csv_content)
        file.name = "something.csv"
        settings.MEDIA_ROOT = tmp_path

        response = clients['master_admin'].post(
            reverse('manual-data-upload-list'),
            data={
                'platform': platform.id,
                'organization': organization.pk,
                'report_type_id': report_type.pk,
                'data_file': file,
                'method': MduMethod.CELUS,
            },
        )
        assert response.status_code == 201
        mdu = ManualDataUpload.objects.get(pk=response.json()['pk'])
        assert mdu.import_batches.count() == 0
        # let's process the mdu
        assert AccessLog.objects.count() == 0

        # calculate preflight in celery
        prepare_preflight(mdu.pk)

        response = clients['master_admin'].post(
            reverse('manual-data-upload-import-data', args=(mdu.pk,))
        )
        assert response.status_code == 200

        import_manual_upload_data(mdu.pk, mdu.user.pk)

        mdu.refresh_from_db()
        assert mdu.is_processed
        assert mdu.user == users['master_admin']
        assert AccessLog.objects.count() == 6
        assert mdu.import_batches.count() == 3, '3 months of data = 3 import batches'
        assert mdu.accesslogs.count() == 6
        assert ImportBatch.objects.count() == 3
        # let's delete the object
        response = clients['master_admin'].delete(
            reverse('manual-data-upload-detail', args=(mdu.pk,))
        )
        assert response.status_code == 204
        assert ManualDataUpload.objects.filter(pk=mdu.pk).count() == 0
        assert ImportBatch.objects.count() == 0
        assert AccessLog.objects.count() == 0

    @pytest.mark.parametrize(
        ['client', 'allowed'],
        [
            ['user1', False],  # unrelated user
            ['user2', False],  # related user
            ['admin1', False],  # unrelated admin
            ['admin2', True],  # related admin
            ['master_admin', True],  # master admin
            ['master_user', False],  # master user
            ['su', True],
        ],
    )
    def test_custom_data_import_api_owner_level(
        self,
        allowed,
        settings,
        tmp_path,
        report_types,
        platforms,
        clients,
        client,
        basic1,
        organizations,
        enable_nibbler_for_celus_format,
    ):
        settings.ENABLE_NIBBLER_FOR_CELUS_FORMAT = enable_nibbler_for_celus_format

        organization = organizations['standalone']
        platform = platforms['standalone']
        report_type = report_types['custom1']

        csv_content = 'Metric,Jan-2019,Feb 2019,2019-03\nM1,10,7,11\nM2,1,2,3\n'
        file = ContentFile(csv_content)
        file.name = "something.csv"
        settings.MEDIA_ROOT = tmp_path

        # upload the data
        response = clients[client].post(
            reverse('manual-data-upload-list'),
            data={
                'platform': platform.id,
                'organization': organization.pk,
                'report_type_id': report_type.pk,
                'data_file': file,
                'method': MduMethod.CELUS,
            },
        )
        assert response.status_code == 201 if allowed else 403
        if allowed:
            mdu = ManualDataUpload.objects.get(pk=response.json()['pk'])

            # calculate preflight in celery
            prepare_preflight(mdu.pk)

            response = clients[client].get(reverse('manual-data-upload-detail', args=(mdu.pk,)),)
            assert response.status_code == 200

            # let's process the mdu
            response = clients[client].post(
                reverse('manual-data-upload-import-data', args=(mdu.pk,)),
            )

            assert response.status_code == 200

    @pytest.mark.parametrize(
        ['user', 'owner_level'],
        [['admin2', UL_ORG_ADMIN], ['master_user', UL_CONS_STAFF], ['su', UL_CONS_STAFF],],
    )
    def test_custom_data_import_owner_level(
        self,
        users,
        report_types,
        organizations,
        platforms,
        user,
        owner_level,
        settings,
        basic1,
        tmp_path,
    ):
        settings.ENABLE_NIBBLER_FOR_CELUS_FORMAT = True
        organization = organizations['standalone']
        platform = platforms['standalone']
        report_type = report_types['custom1']

        csv_content = "Source,2019-01\naaaa,9\n'"
        file = ContentFile(csv_content)
        file.name = "something.csv"
        settings.MEDIA_ROOT = tmp_path
        checksum, size = SourceFileMixin.checksum_fileobj(file)

        mdu = ManualDataUpload.objects.create(
            organization=organization,
            platform=platform,
            report_type=report_type,
            owner_level=owner_level,
            checksum=checksum,
            file_size=size,
            data_file=file,
            user=users[user],
        )
        assert mdu.import_batches.count() == 0
        import_custom_data(mdu, users[user])
        mdu.refresh_from_db()
        assert mdu.import_batches.count() > 0
        for ib in mdu.import_batches.all():
            assert ib.owner_level == mdu.owner_level

    @pytest.mark.parametrize(
        ['settings_value', 'raw_enabled', 'passed'],
        [
            ['None', True, False],
            ['None', False, False],
            ['All', True, True],
            ['All', False, True],
            ['PerOrg', False, False],
            ['PerOrg', True, True],
        ],
    )
    def test_custom_data_organization_permissions(
        self,
        users,
        report_types,
        platforms,
        organizations,
        settings_value,
        raw_enabled,
        passed,
        tmp_path,
        settings,
        parser_definitions,
    ):
        settings.ENABLE_RAW_DATA_IMPORT = settings_value

        with (Path(__file__).parent / "data/custom/custom_data-nibbler-simple.csv").open() as f:
            data_file = ContentFile(f.read())
            data_file.name = "nibbler.csv"

        organization = organizations['standalone']
        platform = platforms['brain']
        settings.MEDIA_ROOT = tmp_path

        checksum, size = SourceFileMixin.checksum_fileobj(data_file)

        mdu = ManualDataUploadFactory.create(
            platform=platform,
            organization=organization,
            method=MduMethod.RAW,
            checksum=checksum,
            file_size=size,
            data_file=data_file,
            user=users['su'],
        )

        mdu.organization.raw_data_import_enabled = raw_enabled
        mdu.organization.save()

        assert mdu.import_batches.count() == 0

        if passed:
            import_custom_data(mdu, users['su'])
            assert mdu.import_batches.count() == 1
        else:
            with pytest.raises(OrganizationNotAllowedToImportRawData):
                import_custom_data(mdu, users['su'])
            assert mdu.import_batches.count() == 0

    @pytest.mark.parametrize(['content_prefix'], [[''], ['\ufeff']])
    def test_mdu_data_to_records(
        self,
        organizations,
        platforms,
        report_types,
        tmp_path,
        settings,
        content_prefix,
        enable_nibbler_for_celus_format,
    ):
        """
        Check that CSV data are correctly ingested - regardless of BOM presence
        """
        settings.ENABLE_NIBBLER_FOR_CELUS_FORMAT = enable_nibbler_for_celus_format
        report_type = report_types['custom1']
        organization = organizations['standalone']
        platform = platforms['standalone']

        csv_content = f'{content_prefix}Metric,Jan-2019,Feb 2019,2019-03\nM1,10,7,11\nM2,1,2,3\n'
        file = ContentFile(csv_content)
        file.name = "something.csv"
        settings.MEDIA_ROOT = tmp_path
        checksum, size = SourceFileMixin.checksum_fileobj(file)

        mdu = ManualDataUploadFactory.create(
            report_type=report_type,
            organization=organization,
            platform=platform,
            data_file=file,
            checksum=checksum,
            file_size=size,
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
    def test_mdu_json(
        self, organizations, platforms, report_types, tmp_path, settings, content, is_json
    ):
        """
        Check that JSON data are properly recognized during import
        """
        report_type = report_types['custom1']
        organization = organizations['standalone']
        platform = platforms['standalone']

        file = ContentFile(content)
        file.name = "something.csv"
        settings.MEDIA_ROOT = tmp_path
        checksum, size = SourceFileMixin.checksum_fileobj(file)

        mdu = ManualDataUploadFactory.create(
            report_type=report_type,
            organization=organization,
            platform=platform,
            data_file=file,
            checksum=checksum,
            file_size=size,
        )
        assert mdu.file_is_json() == is_json

    def test_mdu_list_view(self, clients):
        """
        Test the manual data upload global api endpoint
        """
        mdus = ManualDataUploadFullFactory.create_batch(5, state=MduState.INITIAL)
        mdus += ManualDataUploadFullFactory.create_batch(5, state=MduState.IMPORTED)
        resp = clients['su'].get(reverse('manual-data-upload-list'))
        assert resp.status_code == 200
        assert len(resp.json()) == 10

    def test_organization_mdu_list_view(self, clients):
        """
        Test the manual data upload api endpoint for an organization
        """
        mdus = ManualDataUploadFullFactory.create_batch(5, state=MduState.INITIAL)
        mdus += ManualDataUploadFullFactory.create_batch(5, state=MduState.IMPORTED)
        resp = clients['su'].get(reverse('organization-manual-data-upload-list', args=(-1,)))
        assert resp.status_code == 200
        assert len(resp.json()) == 10
