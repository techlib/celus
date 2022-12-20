from collections import Counter
from datetime import date, timedelta

import pytest
from core.logic.dates import month_start
from hcube.api.models.aggregation import Sum as HSum
from logs.cubes import AccessLogCube, ch_backend
from logs.logic.reimport import (
    find_import_batches_to_reimport,
    reimport_import_batch_with_fa,
    reimport_mdu_batch,
)
from logs.models import ImportBatch, ManualDataUpload, MduState
from organizations.tests.conftest import organizations  # noqa  - used as fixture
from scheduler.models import FetchIntention
from sushi.models import AttemptStatus, SushiFetchAttempt

from test_fixtures.entities.fetchattempts import FetchAttemptFactory
from test_fixtures.entities.logs import ImportBatchFullFactory, ManualDataUploadFullFactory
from test_fixtures.entities.scheduler import FetchIntentionFactory


def fi_for_fa(fa: SushiFetchAttempt) -> FetchIntention:
    fi = FetchIntentionFactory.create(
        attempt=fa,
        credentials=fa.credentials,
        counter_report=fa.counter_report,
        start_date=fa.start_date,
        end_date=fa.end_date,
    )
    return fi


@pytest.fixture()
def clashing_fis():
    fa1 = FetchAttemptFactory.create()  # type: SushiFetchAttempt
    ib1, ib2 = ImportBatchFullFactory.create_batch(
        2,
        organization=fa1.credentials.organization,
        platform=fa1.credentials.platform,
        report_type=fa1.counter_report.report_type,
        date=fa1.start_date,
    )
    fa1.import_batch = ib1
    fa1.save()
    fi1 = fi_for_fa(fa1)
    fa2 = FetchAttemptFactory.create(
        credentials=fa1.credentials,
        counter_report=fa1.counter_report,
        start_date=fa1.start_date,
        end_date=fa1.end_date,
    )
    fa2.import_batch = ib2
    fa2.save()
    fi2 = fi_for_fa(fa2)
    return locals()


@pytest.fixture()
def clashing_mdu(clashing_fis):
    """
    just modify the data created by `clashing_fis` so that the newer IB is connected to an MDU
    rather than a FA
    """
    fa2 = clashing_fis['fa2']
    FetchIntention.objects.filter(attempt=fa2).delete()
    fa2.delete()
    ib2 = clashing_fis['ib2']
    mdu = ManualDataUploadFullFactory.create(
        organization=ib2.organization,
        platform=ib2.platform,
        report_type=ib2.report_type,
        state=MduState.INITIAL,
    )
    mdu.import_batches.set([ib2])
    mdu.state = MduState.IMPORTED
    mdu.save()
    return {**clashing_fis, **locals()}


def import_one_attempt_mock(fa: SushiFetchAttempt):
    fa.import_batch = ImportBatchFullFactory.create(
        date=fa.start_date,
        organization=fa.credentials.organization,
        platform=fa.credentials.platform,
        report_type=fa.counter_report.report_type,
    )
    fa.status = AttemptStatus.SUCCESS
    fa.save()
    return fa


def import_counter_records_mock(
    report_type, organization, platform, records, months=None, **kwargs
):
    import_batches = [
        ImportBatchFullFactory.create(
            date=month, organization=organization, platform=platform, report_type=report_type
        )
        for month in months or []
    ]
    return import_batches, Counter()


@pytest.mark.django_db
class TestReimport:
    def test_find_import_batches_to_reimport(self, clashing_fis):
        reimport = find_import_batches_to_reimport(ImportBatch.objects.all())
        assert reimport.reimportable.count() == 1
        assert reimport.obsolete.count() == 1
        assert reimport.reimportable[0].pk == clashing_fis['ib2'].pk, 'reimport the newer ib'

    def test_find_import_batches_to_reimport_fa_missing(self, clashing_fis):
        """
        Newer IB does not have FA, so the older should be selected for reimport
        """
        # delete the newer fetch attempt, thus making it impossible to reimport the newer ib2
        fa2 = clashing_fis['fa2']
        fa2.delete()
        reimport = find_import_batches_to_reimport(ImportBatch.objects.all())
        assert reimport.reimportable.count() == 1
        assert reimport.obsolete.count() == 1
        assert reimport.reimportable[0].pk == clashing_fis['ib1'].pk, 'reimport older ib with fa'
        assert reimport.no_source.count() == 0, 'the 1 without source is in obsolete'

    def test_find_import_batches_to_reimport_no_source(self, clashing_fis):
        """
        One IB does not have FA and is not clashing with anything that has FA
        """
        ib1 = clashing_fis['ib1']
        # ib3 should not by accident clash with ib1 or ib2, we ensure it by using a different data
        ib3 = ImportBatchFullFactory.create(date=month_start(ib1.date + timedelta(days=45)))
        reimport = find_import_batches_to_reimport(ImportBatch.objects.all())
        assert reimport.reimportable.count() == 1
        assert reimport.obsolete.count() == 1
        assert reimport.no_source.count() == 1
        assert reimport.no_source[0].pk == ib3.pk

    def test_find_import_batches_to_reimport_no_source_blocked(self, clashing_fis):
        """
        One IB does not have FA and is not clashing with anything that has FA
        """
        # make ib1 and ib2 no_source
        clashing_fis['fa1'].delete()
        clashing_fis['fa2'].delete()
        ib1 = clashing_fis['ib1']
        # ib3 should not by accident clash with ib1 or ib2, we ensure it by using a different data
        ImportBatchFullFactory.create(date=month_start(ib1.date + timedelta(days=45)))
        reimport = find_import_batches_to_reimport(ImportBatch.objects.all())
        assert reimport.reimportable.count() == 0
        assert reimport.obsolete.count() == 0
        assert reimport.no_source.count() == 2
        assert reimport.blocked.count() == 1
        assert reimport.blocked[0].pk == clashing_fis['ib1'].pk

    def test_find_import_batches_to_reimport_with_mdu(self, clashing_mdu):
        reimport = find_import_batches_to_reimport(ImportBatch.objects.all())
        assert reimport.reimportable.count() == 1
        assert reimport.obsolete.count() == 1
        assert reimport.reimportable[0].pk == clashing_mdu['ib2'].pk, 'reimport the newer ib'
        assert reimport.reimportable[0].mdu

    @staticmethod
    def _clickhouse_ib_sum(ib_id):
        if type(ib_id) is int:
            fltr = {'import_batch_id': ib_id}
        else:
            fltr = {'import_batch_id__in': ib_id}
        return ch_backend.get_one_record(
            AccessLogCube.query().filter(**fltr).aggregate(sum=HSum('value'))
        ).sum

    @pytest.mark.clickhouse
    @pytest.mark.usefixtures('clickhouse_on_off')
    @pytest.mark.django_db(transaction=True)
    def test_reimport_batch_with_fa(self, clashing_fis, monkeypatch, settings):
        reimport = find_import_batches_to_reimport(ImportBatch.objects.all())
        assert reimport.reimportable.count() == 1
        assert ImportBatch.objects.count() == 2
        assert FetchIntention.objects.count() == 2
        assert SushiFetchAttempt.objects.count() == 2
        old_ib_id = reimport.reimportable[0].pk
        # check clickhouse
        if settings.CLICKHOUSE_SYNC_ACTIVE:
            assert self._clickhouse_ib_sum(old_ib_id) > 0, "there is data in the original IB in CH"

        # we do not have the source file, etc. so we mock the `import_one_sushi_attempt` function
        import os.path

        import django.db.models.fields.files
        import logs.logic.reimport as reimport_module

        monkeypatch.setattr(reimport_module, 'import_one_sushi_attempt', import_one_attempt_mock)
        monkeypatch.setattr(os.path, 'isfile', lambda x: True)
        monkeypatch.setattr(
            django.db.models.fields.files.FieldFile, '_require_file', lambda x: None
        )
        new_ib = reimport_import_batch_with_fa(reimport.reimportable[0])

        assert ImportBatch.objects.count() == 1
        assert FetchIntention.objects.count() == 1
        assert SushiFetchAttempt.objects.count() == 1
        assert ImportBatch.objects.filter(pk=old_ib_id).count() == 0, 'old IB is deleted'
        assert ImportBatch.objects.filter(pk=new_ib.pk).count() == 1, 'new IB is there'

        # check clickhouse
        if settings.CLICKHOUSE_SYNC_ACTIVE:
            assert self._clickhouse_ib_sum(old_ib_id) in (0, None), "no data for the deleted IB"
            assert self._clickhouse_ib_sum(new_ib.pk) > 0, "some data for the new IB in CH"

    @pytest.mark.clickhouse
    @pytest.mark.usefixtures('clickhouse_on_off')
    @pytest.mark.django_db(transaction=True)
    def test_reimport_batch_with_mdu(self, clashing_mdu, monkeypatch, settings):
        reimport = find_import_batches_to_reimport(ImportBatch.objects.all())
        assert reimport.reimportable.count() == 1
        assert ImportBatch.objects.count() == 2
        assert FetchIntention.objects.count() == 1
        assert SushiFetchAttempt.objects.count() == 1
        old_ib_id = reimport.reimportable[0].pk
        # check clickhouse
        if settings.CLICKHOUSE_SYNC_ACTIVE:
            assert self._clickhouse_ib_sum(old_ib_id) > 0, "there is data in the original IB in CH"

        # we do not have the source file, etc. so we mock the `import_counter_records` fn
        # and the `data_to_records` method
        import os.path

        import django.db.models.fields.files
        import logs.logic.custom_import as module

        monkeypatch.setattr(module, 'import_counter_records', import_counter_records_mock)
        monkeypatch.setattr(ManualDataUpload, 'data_to_records', lambda x: [])
        monkeypatch.setattr(os.path, 'isfile', lambda x: True)
        monkeypatch.setattr(
            django.db.models.fields.files.FieldFile, '_require_file', lambda x: None
        )
        mdu_batch = next(reimport.gen_mdu_batches())
        reimport_mdu_batch(mdu_batch)

        assert ImportBatch.objects.count() == 1
        assert FetchIntention.objects.count() == 0
        assert SushiFetchAttempt.objects.count() == 0
        assert ImportBatch.objects.filter(pk=old_ib_id).count() == 0, 'old IB is deleted'
        assert ImportBatch.objects.filter(mdu__pk=mdu_batch.mdu.pk).count() == 1, 'new IB is there'
        new_ib = mdu_batch.mdu.import_batches.get()

        # check clickhouse
        if settings.CLICKHOUSE_SYNC_ACTIVE:
            assert self._clickhouse_ib_sum(old_ib_id) in (0, None), "no data for the deleted IB"
            assert self._clickhouse_ib_sum(new_ib.pk) > 0, "some data for the new IB in CH"

    def test_reimport_batch_with_fa_no_data(self, clashing_fis, monkeypatch):
        # prepare no-data attempts
        for fi in (clashing_fis['fi1'], clashing_fis['fi2']):
            fi.attempt.status = AttemptStatus.NO_DATA
            fi.attempt.save()
            fi.attempt.import_batch.accesslog_set.all().delete(i_know_what_i_am_doing=True)
        reimport = find_import_batches_to_reimport(ImportBatch.objects.all())
        assert reimport.reimportable.count() == 1
        assert ImportBatch.objects.count() == 2
        assert FetchIntention.objects.count() == 2
        assert SushiFetchAttempt.objects.count() == 2
        old_ib_id = reimport.reimportable[0].pk

        # we do not have the source file, etc. so we mock the `import_one_sushi_attempt` function
        import os.path

        import django.db.models.fields.files
        import logs.logic.reimport as reimport_module

        monkeypatch.setattr(reimport_module, 'import_one_sushi_attempt', import_one_attempt_mock)
        monkeypatch.setattr(os.path, 'isfile', lambda x: True)
        monkeypatch.setattr(
            django.db.models.fields.files.FieldFile, '_require_file', lambda x: None
        )
        new_ib = reimport_import_batch_with_fa(reimport.reimportable[0])

        assert ImportBatch.objects.count() == 1
        assert FetchIntention.objects.count() == 1
        assert SushiFetchAttempt.objects.count() == 1
        assert new_ib.pk == old_ib_id, 'IB should be the same'
        assert SushiFetchAttempt.objects.get().status == AttemptStatus.NO_DATA

    def test_reimport_batch_with_multimonth_mdu(self, monkeypatch, settings):
        """
        Here we create an MDU for several months and then try to reimport it to make sure all
        months are covered.
        """
        ib1 = ImportBatchFullFactory.create(date='2021-01-01')
        ib2 = ImportBatchFullFactory.create(
            organization=ib1.organization,
            platform=ib1.platform,
            report_type=ib1.report_type,
            date='2021-02-01',
        )
        ib3 = ImportBatchFullFactory.create(
            organization=ib1.organization,
            platform=ib1.platform,
            report_type=ib1.report_type,
            date='2021-03-01',
        )
        mdu = ManualDataUploadFullFactory.create(
            organization=ib1.organization,
            platform=ib1.platform,
            report_type=ib1.report_type,
            state=MduState.INITIAL,
        )
        mdu.import_batches.set([ib1, ib2, ib3])
        mdu.state = MduState.IMPORTED
        mdu.save()

        reimport = find_import_batches_to_reimport(ImportBatch.objects.all())
        assert reimport.reimportable.count() == 3
        assert ImportBatch.objects.count() == 3

        mdu_batches = list(reimport.gen_mdu_batches())
        assert len(mdu_batches) == 1
        mdu_batch = mdu_batches[0]
        assert mdu_batch.mdu.pk == mdu.pk
        assert mdu_batch.to_reimport.count() == 3
        assert mdu_batch.to_delete.count() == 0

    @pytest.mark.clickhouse
    @pytest.mark.usefixtures('clickhouse_on_off')
    @pytest.mark.django_db(transaction=True)
    def test_reimport_batch_with_multimonth_mdu_and_clashing_data(self, monkeypatch, settings):
        """
        Here we create an MDU for several months and also a FA for one of the months.
        Then try to reimport it to make sure all months are properly covered.
        """
        ib1 = ImportBatchFullFactory.create(date='2021-01-01')
        ib2 = ImportBatchFullFactory.create(
            organization=ib1.organization,
            platform=ib1.platform,
            report_type=ib1.report_type,
            date='2021-02-01',
        )
        ib3 = ImportBatchFullFactory.create(
            organization=ib1.organization,
            platform=ib1.platform,
            report_type=ib1.report_type,
            date='2021-03-01',
        )
        ib2c = ImportBatchFullFactory.create(
            organization=ib1.organization,
            platform=ib1.platform,
            report_type=ib1.report_type,
            date='2021-02-01',
        )
        FetchAttemptFactory.create(
            start_date=date(2021, 2, 1),
            import_batch=ib2c,
            credentials__organization=ib2c.organization,
            credentials__platform=ib2c.platform,
        )
        mdu = ManualDataUploadFullFactory.create(
            organization=ib1.organization,
            platform=ib1.platform,
            report_type=ib1.report_type,
            state=MduState.INITIAL,
        )
        mdu.import_batches.set([ib1, ib2, ib3])
        mdu.state = MduState.IMPORTED
        mdu.save()

        reimport = find_import_batches_to_reimport(ImportBatch.objects.all())
        assert reimport.reimportable.count() == 3
        assert ImportBatch.objects.count() == 4

        mdu_batches = list(reimport.gen_mdu_batches())
        assert len(mdu_batches) == 1
        mdu_batch = mdu_batches[0]
        assert mdu_batch.mdu.pk == mdu.pk
        assert mdu_batch.to_reimport.count() == 2
        assert mdu_batch.to_delete.count() == 1

        # now really try the reimport to see if it really works
        # we do not have the source file, etc. so we mock the `import_counter_records` fn
        # and the `data_to_records` method
        import os.path

        import django.db.models.fields.files
        import logs.logic.custom_import as module

        monkeypatch.setattr(module, 'import_counter_records', import_counter_records_mock)
        monkeypatch.setattr(ManualDataUpload, 'data_to_records', lambda x: [])
        monkeypatch.setattr(os.path, 'isfile', lambda x: True)
        monkeypatch.setattr(
            django.db.models.fields.files.FieldFile, '_require_file', lambda x: None
        )
        reimport_mdu_batch(mdu_batch)

        assert ImportBatch.objects.count() == 3
        assert SushiFetchAttempt.objects.count() == 1
        assert ImportBatch.objects.filter(sushifetchattempt__isnull=False).count() == 1
        assert ImportBatch.objects.filter(mdu__pk=mdu_batch.mdu.pk).count() == 2, '2 IBs remain'
        new_ib_ids = [ib.pk for ib in mdu_batch.mdu.import_batches.all()]

        # check clickhouse
        if settings.CLICKHOUSE_SYNC_ACTIVE:
            assert self._clickhouse_ib_sum([ib1.pk, ib2.pk, ib3.pk]) in (
                0,
                None,
            ), "data for old IBs was removed from CH"
            assert self._clickhouse_ib_sum(new_ib_ids) > 0, "some data for the new IB in CH"
            assert self._clickhouse_ib_sum(ib2c.pk) > 0, "some data for the FA IB"
