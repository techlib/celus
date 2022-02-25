from pathlib import Path

import pytest
from django.core.files.base import ContentFile
from django.urls import reverse

from core.tests.conftest import *  # noqa
from logs.tasks import prepare_preflight, import_manual_upload_data
from logs.models import ManualDataUpload
from test_fixtures.scenarios.basic import (
    data_sources,
    organizations,
    platforms,
    counter_report_types,
    report_types,
    clients,
    identities,
    users,
    basic1,
)  # noqa


@pytest.mark.django_db
class TestManualUploadForCounterData:
    @pytest.mark.parametrize(
        ['filename', 'report_code'],
        (
            ('counter4/counter4_br2.tsv', 'br2'),
            ('counter5/counter5_table_dr.csv', 'dr'),
            ('counter5/counter5_table_dr.tsv', 'dr'),
            ('counter5/counter5_table_pr.csv', 'pr'),
            ('counter5/counter5_tr_test1.json', 'tr'),
        ),
    )
    def test_counter_uploads(
        self,
        basic1,
        organizations,
        platforms,
        counter_report_types,
        clients,
        tmp_path,
        settings,
        filename,
        report_code,
    ):
        cr_type = counter_report_types[report_code]
        with (Path(__file__).parent / "data" / filename).open() as f:
            data_file = ContentFile(f.read())
            data_file.name = f"something.{filename.split('.')[-1]}"

        organization = organizations['master']
        platform = platforms['master']
        settings.MEDIA_ROOT = tmp_path

        # upload the data
        response = clients["master"].post(
            reverse('manual-data-upload-list'),
            data={
                'platform': platform.id,
                'organization': organization.pk,
                'report_type': cr_type.report_type_id,
                'data_file': data_file,
            },
        )
        assert response.status_code == 201
        mdu = ManualDataUpload.objects.get(pk=response.json()['pk'])

        # calculate preflight in celery
        prepare_preflight(mdu.pk)

        response = clients["master"].get(reverse('manual-data-upload-detail', args=(mdu.pk,)))
        assert response.status_code == 200
        data = response.json()
        assert 'preflight' in data
        assert 'hits_total' in data['preflight']
        assert data['preflight']['log_count'] > 0


@pytest.mark.django_db
class TestManualUploadConflicts:
    def test_import_same_file_twice(
        self,
        organizations,
        platforms,
        settings,
        tmp_path,
        counter_report_types,
        report_types,
        clients,
        basic1,
    ):
        with (Path(__file__).parent / "data/counter4/counter4_br2.tsv").open() as f:
            data_file = ContentFile(f.read())
            data_file.name = "something.tsv"

        organization = organizations['master']
        platform = platforms['master']
        settings.MEDIA_ROOT = tmp_path

        response = clients["master"].post(
            reverse('manual-data-upload-list'),
            data={
                'platform': platform.id,
                'organization': organization.pk,
                'report_type': report_types['br2'].pk,
                'data_file': data_file,
            },
        )
        assert response.status_code == 201
        mdu = ManualDataUpload.objects.get(pk=response.json()['pk'])

        # calculate preflight in celery
        prepare_preflight(mdu.pk)

        # process data
        response = clients["master"].post(reverse('manual-data-upload-import-data', args=(mdu.pk,)))
        assert response.status_code == 200

        # import data (this should be handled via celery)
        import_manual_upload_data(mdu.pk, mdu.user.pk)

        response = clients["master"].get(reverse('manual-data-upload-detail', args=(mdu.pk,)))
        assert response.status_code == 200
        batches = sorted(e['pk'] for e in response.data["import_batches"])
        batches_months = sorted(e['date'] for e in response.data["import_batches"])

        # Upload the same data
        data_file.seek(0)

        response = clients["master"].post(
            reverse('manual-data-upload-list'),
            data={
                'platform': platform.id,
                'organization': organization.pk,
                'report_type': report_types['br2'].pk,
                'data_file': data_file,
            },
        )
        assert response.status_code == 201
        mdu = ManualDataUpload.objects.get(pk=response.json()['pk'])

        # calculate preflight in celery
        prepare_preflight(mdu.pk)

        # fail preflight
        response = clients["master"].get(reverse('manual-data-upload-detail', args=(mdu.pk,)))
        assert response.status_code == 200
        assert response.data["can_import"] is False
        assert batches_months == sorted(
            e.strftime("%Y-%m-%d") for e in response.data["clashing_months"]
        )

        # fail processing
        response = clients["master"].post(reverse('manual-data-upload-import-data', args=(mdu.pk,)))
        assert response.status_code == 409
        assert batches == sorted(
            e["pk"] for e in response.data["clashing_import_batches"]
        ), "all import batches are in conflict"

    @pytest.mark.skip()
    def test_conflict_with_sushi(self):
        raise NotImplementedError()
