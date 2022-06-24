from pathlib import Path
from unittest.mock import patch

import pytest
from core.tests.conftest import *  # noqa
from django.core.files.base import ContentFile
from django.urls import reverse
from logs.models import ManualDataUpload
from logs.tasks import import_manual_upload_data, prepare_preflight
from test_fixtures.entities.logs import MetricFactory
from test_fixtures.scenarios.basic import clients  # noqa
from test_fixtures.scenarios.basic import (
    basic1,
    counter_report_types,
    data_sources,
    identities,
    organizations,
    platforms,
    report_types,
    users,
)


@pytest.mark.django_db
class TestManualUploadForCounterData:
    @pytest.mark.parametrize(['hash_matches'], [(True,), (False,)])
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
        hash_matches,
    ):
        cr_type = counter_report_types[report_code]
        with (Path(__file__).parent / "data" / filename).open() as f:
            data_file = ContentFile(f.read())
            data_file.name = f"something.{filename.split('.')[-1]}"

        organization = organizations['master']
        platform = platforms['master']
        settings.MEDIA_ROOT = tmp_path

        # upload the data
        response = clients["master_admin"].post(
            reverse('manual-data-upload-list'),
            data={
                'platform': platform.id,
                'organization': organization.pk,
                'report_type_id': cr_type.report_type_id,
                'data_file': data_file,
            },
        )
        assert response.status_code == 201
        mdu = ManualDataUpload.objects.get(pk=response.json()['pk'])
        if not hash_matches:
            mdu.checksum = 'foobarbaz'
            mdu.save()

        # calculate preflight in celery
        with patch('core.models.SourceFileMixin._send_error_mail') as mail_mock:
            prepare_preflight(mdu.pk)

        response = clients["master_admin"].get(reverse('manual-data-upload-detail', args=(mdu.pk,)))
        assert response.status_code == 200
        data = response.json()
        assert 'preflight' in data
        if hash_matches:
            assert 'hits_total' in data['preflight']
            assert data['preflight']['log_count'] > 0
            for month_data in data['preflight']['months'].values():
                assert set(month_data.keys()) == {
                    'new',
                    'this_month',
                    'prev_year_avg',
                    'prev_year_month',
                }
            assert not mail_mock.called, 'email to admin was not sent'
        else:
            assert data['error'] == 'general'
            assert mail_mock.called, 'email to admin was sent'

    @pytest.mark.parametrize(['hash_matches'], [(True,), (False,)])
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
    def test_counter_manual_import(
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
        hash_matches,
    ):
        cr_type = counter_report_types[report_code]
        with (Path(__file__).parent / "data" / filename).open() as f:
            data_file = ContentFile(f.read())
            data_file.name = f"something.{filename.split('.')[-1]}"

        organization = organizations['master']
        platform = platforms['master']
        settings.MEDIA_ROOT = tmp_path

        # upload the data
        response = clients["master_admin"].post(
            reverse('manual-data-upload-list'),
            data={
                'platform': platform.id,
                'organization': organization.pk,
                'report_type_id': cr_type.report_type_id,
                'data_file': data_file,
            },
        )
        assert response.status_code == 201
        mdu = ManualDataUpload.objects.get(pk=response.json()['pk'])

        # calculate preflight in celery
        prepare_preflight(mdu.pk)

        mdu.refresh_from_db()
        if not hash_matches:
            mdu.checksum = 'foobarbaz'
            mdu.save()

        # try the import - the following just starts the import
        response = clients["master_admin"].post(
            reverse('manual-data-upload-import-data', args=(mdu.pk,))
        )
        assert response.status_code == 200
        assert 'msg' in response.json()
        # without celery, we need to process it ourselves
        with patch('core.models.SourceFileMixin._send_error_mail') as mail_mock:
            import_manual_upload_data(mdu.pk, mdu.user.pk)

        # now we can get the details
        response = clients["master_admin"].get(reverse('manual-data-upload-detail', args=(mdu.pk,)))
        assert response.status_code == 200
        data = response.json()
        print(data)
        if hash_matches:
            assert data['error'] is None
            assert not mail_mock.called, 'email to admin was not sent'
        else:
            assert data['error'] == 'import-error'
            assert 'checksum' in data['error_details']['exception']
            assert mail_mock.called, 'email to admin was sent'


@pytest.mark.django_db
class TestManualUploadControlledMetrics:
    def test_can_import(
        self, basic1, organizations, platforms, counter_report_types, clients, tmp_path, settings,
    ):
        cr_type = counter_report_types["tr"]
        with (Path(__file__).parent / "data/counter5/counter5_tr_test1.json").open() as f:
            data_file = ContentFile(f.read())
            data_file.name = "counter5_tr_test1.json"

        organization = organizations['master']
        platform = platforms['master']
        settings.MEDIA_ROOT = tmp_path

        metrics = [
            'Total_Item_Investigations',
            'Total_Item_Requests',
            'Unique_Item_Investigations',
            'Unique_Item_Requests',
            'Unique_Title_Investigations',
            'Unique_Title_Requests',
        ]
        metrics_objs = [MetricFactory(short_name=e) for e in metrics]

        # upload the data
        response = clients["master_admin"].post(
            reverse('manual-data-upload-list'),
            data={
                'platform': platform.id,
                'organization': organization.pk,
                'report_type_id': cr_type.report_type_id,
                'data_file': data_file,
            },
        )
        assert response.status_code == 201
        mdu = ManualDataUpload.objects.get(pk=response.json()['pk'])

        response = clients["master_admin"].post(
            reverse('manual-data-upload-preflight', args=(mdu.pk,))
        )
        assert response.status_code == 200
        prepare_preflight(mdu.pk)

        response = clients["master_admin"].get(reverse('manual-data-upload-detail', args=(mdu.pk,)))
        assert response.status_code == 200
        # Should be able to import
        assert response.data["can_import"] is True
        assert len(response.data["report_type"]["controlled_metrics"]) == 0
        assert set(response.data["preflight"]["metrics"].keys()) == set(metrics)

        # mark report type as controlled
        cr_type.report_type.controlled_metrics.set(metrics_objs[:2])

        # regenerate preflight
        response = clients["master_admin"].post(
            reverse('manual-data-upload-preflight', args=(mdu.pk,))
        )
        assert response.status_code == 200
        prepare_preflight(mdu.pk)

        response = clients["master_admin"].get(reverse('manual-data-upload-detail', args=(mdu.pk,)))
        assert response.status_code == 200
        # Should be able to import
        assert response.data["can_import"] is False
        assert len(response.data["report_type"]["controlled_metrics"]) > 0
        assert set(response.data["preflight"]["metrics"].keys()) == set(metrics)

        # Should fail to import data
        response = clients["master_admin"].post(
            reverse('manual-data-upload-import-data', args=(mdu.pk,))
        )
        assert response.status_code == 400
        assert response.data == {'error': 'can-not-import'}

        # add all required metrics
        cr_type.report_type.controlled_metrics.set(metrics_objs)

        # Get mdu again
        response = clients["master_admin"].get(reverse('manual-data-upload-detail', args=(mdu.pk,)))
        assert response.status_code == 200
        assert response.data["can_import"] is True
        assert len(response.data["report_type"]["controlled_metrics"]) > 0
        assert set(response.data["preflight"]["metrics"].keys()) == set(metrics)

        # Import should pass
        response = clients["master_admin"].post(
            reverse('manual-data-upload-import-data', args=(mdu.pk,))
        )
        assert response.status_code == 200


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

        response = clients["master_admin"].post(
            reverse('manual-data-upload-list'),
            data={
                'platform': platform.id,
                'organization': organization.pk,
                'report_type_id': report_types['br2'].pk,
                'data_file': data_file,
            },
        )
        assert response.status_code == 201
        mdu = ManualDataUpload.objects.get(pk=response.json()['pk'])

        # calculate preflight in celery
        prepare_preflight(mdu.pk)

        # process data
        response = clients["master_admin"].post(
            reverse('manual-data-upload-import-data', args=(mdu.pk,))
        )
        assert response.status_code == 200

        # import data (this should be handled via celery)
        import_manual_upload_data(mdu.pk, mdu.user.pk)

        response = clients["master_admin"].get(reverse('manual-data-upload-detail', args=(mdu.pk,)))
        assert response.status_code == 200
        batches = sorted(e['pk'] for e in response.data["import_batches"])
        batches_months = sorted(e['date'] for e in response.data["import_batches"])

        # Upload the same data
        data_file.seek(0)

        response = clients["master_admin"].post(
            reverse('manual-data-upload-list'),
            data={
                'platform': platform.id,
                'organization': organization.pk,
                'report_type_id': report_types['br2'].pk,
                'data_file': data_file,
            },
        )
        assert response.status_code == 201
        mdu = ManualDataUpload.objects.get(pk=response.json()['pk'])

        # calculate preflight in celery
        prepare_preflight(mdu.pk)

        # fail preflight
        response = clients["master_admin"].get(reverse('manual-data-upload-detail', args=(mdu.pk,)))
        assert response.status_code == 200
        assert response.data["can_import"] is False
        assert batches_months == sorted(e for e in response.data["clashing_months"])

        # fail processing
        response = clients["master_admin"].post(
            reverse('manual-data-upload-import-data', args=(mdu.pk,))
        )
        assert response.status_code == 409
        assert batches == sorted(
            e["pk"] for e in response.data["clashing_import_batches"]
        ), "all import batches are in conflict"

    @pytest.mark.skip()
    def test_conflict_with_sushi(self):
        raise NotImplementedError()
