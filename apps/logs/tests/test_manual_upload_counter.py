from pathlib import Path

import pytest
from django.core.files.base import ContentFile
from django.urls import reverse

from core.tests.conftest import *  # noqa
from logs.tasks import prepare_preflight
from logs.models import ManualDataUpload
from sushi.tests.conftest import counter_report_type, counter_report_type_named  # noqa
from test_fixtures.scenarios.basic import data_sources, organizations, platforms  # noqa


@pytest.mark.django_db
class TestManualUploadForCounterData:
    @pytest.mark.parametrize(
        ['filename', 'counter_version', 'report_code'],
        (
            ('counter4/counter4_br2.tsv', 4, 'BR2'),
            ('counter5/counter5_table_dr.csv', 5, 'DR'),
            ('counter5/counter5_table_dr.tsv', 5, 'DR'),
            ('counter5/counter5_table_pr.csv', 5, 'PR'),
            ('counter5/counter5_tr_test1.json', 5, 'TR'),
        ),
    )
    def test_counter4_br2_import(
        self,
        organizations,
        counter_report_type_named,
        platforms,
        master_client,
        tmp_path,
        settings,
        filename,
        counter_version,
        report_code,
    ):
        cr_type = counter_report_type_named(report_code, version=counter_version)
        with (Path(__file__).parent / "data" / filename).open() as f:
            data_file = ContentFile(f.read())
            data_file.name = f"something.tsv"

        organization = organizations['master']
        platform = platforms['master']
        settings.MEDIA_ROOT = tmp_path

        # upload the data
        response = master_client.post(
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

        # run celery function to generate preflight
        prepare_preflight(mdu.pk)

        # get preflight data
        response = master_client.get(reverse('manual-data-upload-detail', args=(mdu.pk,)))
        assert response.status_code == 200
        data = response.json()
        assert 'preflight' in data
        assert 'hits_total' in data['preflight']
        assert data['preflight']['log_count'] > 0
