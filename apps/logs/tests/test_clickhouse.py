from collections import Counter
from unittest.mock import patch

import pytest
from django.db.models import Sum
from hcube.api.models.aggregation import Sum as HSum

from logs.cubes import ch_backend, AccessLogCube
from logs.logic.clickhouse import (
    sync_accesslogs_with_clickhouse_superfast,
    process_one_import_batch_sync_log,
)
from logs.logic.data_import import import_counter_records, _import_counter_records, TitleManager
from logs.logic.materialized_interest import sync_interest_by_import_batches, smart_interest_sync
from logs.models import (
    ImportBatch,
    AccessLog,
    ReportInterestMetric,
    Metric,
    InterestGroup,
    ImportBatchSyncLog,
)
from logs.tasks import process_outstanding_import_batch_sync_logs_task
from organizations.tests.conftest import organizations  # noqa  - used as fixture
from publications.models import Platform, PlatformInterestReport


@pytest.mark.clickhouse
@pytest.mark.usefixtures('clickhouse_db')
class TestClickhouse:
    def test_clickhouse_cube_definition(self):
        from ..cubes import AccessLogCube, ch_backend

        ch_backend.create_table(AccessLogCube)

    def test_clickhouse_add_data(self):
        from ..cubes import AccessLogCube, ch_backend, AccessLogCubeRecord

        ch_backend.create_table(AccessLogCube)
        ch_backend.store_records(
            AccessLogCube,
            [
                AccessLogCubeRecord(
                    id=1,
                    report_type_id=2,
                    metric_id=3,
                    organization_id=4,
                    platform_id=5,
                    target_id=6,
                    dim1=1,
                    dim2=2,
                    dim3=3,
                    dim4=4,
                    dim5=5,
                    dim6=6,
                    dim7=0,
                    date='2021-10-10',
                    import_batch_id=1,
                    value=1243,
                )
            ],
        )
        result = list(
            ch_backend.get_records(
                AccessLogCube.query().group_by('report_type_id').aggregate(HSum('value'))
            )
        )
        assert len(result) == 1
        rec = result[0]
        assert rec.report_type_id == 2
        assert rec.sum == 1243


@pytest.mark.clickhouse
@pytest.mark.usefixtures('clickhouse_db')
@pytest.mark.django_db(transaction=True)
class TestClickhouseSync:
    def _prepare_counter_records(
        self,
        counter_records,
        organizations,
        report_type_nd,
        metric='Hits',
        multiplier=1,
        lowlevel=False,
        report_type=None,
    ):
        """
        if `lowlevel` is given, it uses and internal function for the creation of counter records
        which does not force clickhouse sync on its own.
        """
        platform, _created = Platform.objects.get_or_create(
            ext_id=1234, short_name='Platform1', name='Platform 1', provider='Provider 1'
        )
        data = [
            ['Title1', '2018-01-01', '1v1', '2v1', '3v1', multiplier * 1],
            ['Title1', '2018-01-01', '1v2', '2v1', '3v1', multiplier * 2],
            ['Title2', '2018-01-01', '1v2', '2v2', '3v1', multiplier * 4],
            ['Title1', '2018-02-01', '1v1', '2v1', '3v1', multiplier * 8],
            ['Title2', '2018-02-01', '1v1', '2v2', '3v2', multiplier * 16],
            ['Title1', '2018-03-01', '1v1', '2v3', '3v2', multiplier * 32],
        ]
        crs = list(counter_records(data, metric=metric, platform='Platform1'))
        organization = organizations[0]
        if not report_type:
            report_type = report_type_nd(3)
        import_batch = ImportBatch.objects.create(
            organization=organization, platform=platform, report_type=report_type
        )
        if lowlevel:
            stats = Counter()
            tm = TitleManager()
            _import_counter_records(
                report_type, organization, platform, crs, import_batch, stats, tm
            )
        else:
            import_counter_records(report_type, organization, platform, crs, import_batch)
        return platform, report_type, import_batch

    def test_one_import_batch_sync(self, counter_records, organizations, report_type_nd):
        self._prepare_counter_records(counter_records, organizations, report_type_nd)
        assert AccessLog.objects.count() == 6
        ch_recs = list(ch_backend.get_records(AccessLogCube.query()))
        assert len(ch_recs) == 6
        assert ImportBatchSyncLog.objects.count() == 1, 'the import batch is still there'
        assert ImportBatchSyncLog.objects.get().state == ImportBatchSyncLog.STATE_NO_CHANGE

    def test_general_accesslog_sync(self, counter_records, organizations, report_type_nd):
        self._prepare_counter_records(counter_records, organizations, report_type_nd, lowlevel=True)
        assert AccessLog.objects.count() == 6
        count = sync_accesslogs_with_clickhouse_superfast()
        ch_recs = list(ch_backend.get_records(AccessLogCube.query()))
        assert len(ch_recs) == 6
        assert count == 6
        # retry to check no more syncs will be done
        assert sync_accesslogs_with_clickhouse_superfast() == 0, 'no more syncs'

    def test_one_import_batch_sync_interest_calculation(
        self, counter_records, organizations, report_type_nd
    ):
        platform, report_type, ib = self._prepare_counter_records(
            counter_records, organizations, report_type_nd
        )
        assert AccessLog.objects.count() == 6
        ch_recs = list(ch_backend.get_records(AccessLogCube.query()))
        assert len(ch_recs) == 6
        assert ch_backend.get_one_record(AccessLogCube.query().aggregate(HSum('value'))).sum == 63
        # prepare interest
        report_type_nd(1, short_name='interest')
        PlatformInterestReport.objects.create(platform=platform, report_type=report_type)
        ReportInterestMetric.objects.create(
            report_type=report_type,
            metric=Metric.objects.get(short_name='Hits'),
            interest_group=InterestGroup.objects.create(short_name='aaa', position=1),
        )
        sync_interest_by_import_batches()
        assert AccessLog.objects.count() == 11, "6 orig + 5 interest"
        ch_recs = list(ch_backend.get_records(AccessLogCube.query()))
        assert len(ch_recs) == 11
        assert (
            ch_backend.get_one_record(AccessLogCube.query().aggregate(HSum('value'))).sum == 126
        ), 'sum must be twice what it was before as interest will double it'

    def test_import_batch_delete_from_model_instance(
        self, counter_records, organizations, report_type_nd
    ):
        platform, report_type, ib = self._prepare_counter_records(
            counter_records, organizations, report_type_nd
        )
        assert AccessLog.objects.count() == 6
        ch_recs = list(ch_backend.get_records(AccessLogCube.query()))
        assert len(ch_recs) == 6
        assert ImportBatchSyncLog.objects.count() == 1
        # delete the import batch
        ib.delete()
        ch_recs = list(ch_backend.get_records(AccessLogCube.query()))
        assert len(ch_recs) == 0, 'all records should be deleted from clickhouse'
        assert ImportBatchSyncLog.objects.count() == 0, 'sync log was removed as well'

    def test_import_batch_delete_from_queryset_method(
        self, counter_records, organizations, report_type_nd
    ):
        platform, report_type, ib = self._prepare_counter_records(
            counter_records, organizations, report_type_nd
        )
        assert AccessLog.objects.count() == 6
        ch_recs = list(ch_backend.get_records(AccessLogCube.query()))
        assert len(ch_recs) == 6
        assert ImportBatchSyncLog.objects.count() == 1
        ImportBatch.objects.filter(pk=ib.pk).delete()
        ch_recs = list(ch_backend.get_records(AccessLogCube.query()))
        assert len(ch_recs) == 0, 'all records should be deleted from clickhouse'
        assert ImportBatchSyncLog.objects.count() == 0, 'sync log was removed as well'

    def test_import_batch_outdated_sync_logs(self, counter_records, organizations, report_type_nd):
        """
        We simulate a situation where an import batch was created but not synced with clickhouse
        for some reason.
        """
        platform, report_type, ib = self._prepare_counter_records(
            counter_records, organizations, report_type_nd, lowlevel=True
        )
        assert AccessLog.objects.count() == 6
        assert len(list(ch_backend.get_records(AccessLogCube.query()))) == 0
        assert ImportBatchSyncLog.objects.count() == 1
        sync_log = ImportBatchSyncLog.objects.get(import_batch_id=ib.pk)
        sync_log.state = ImportBatchSyncLog.STATE_SYNC
        sync_log.save()
        with patch('logs.tasks.process_one_import_batch_sync_log_task') as sync_task, patch(
            'logs.tasks.async_mail_admins'
        ) as mail_task:
            process_outstanding_import_batch_sync_logs_task(age_threshold=0)
            sync_task.delay.assert_called_once()
            sync_task.delay.assert_called_with(sync_log.pk)
            mail_task.delay.assert_called_once()

    def test_import_batch_outdated_sync_logs_task_internals(
        self, counter_records, organizations, report_type_nd
    ):
        """
        Tests the code that is run from `process_outstanding_import_batch_sync_logs_task` because
        it is hard to test otherwise
        """
        platform, report_type, ib = self._prepare_counter_records(
            counter_records, organizations, report_type_nd, lowlevel=True
        )
        assert AccessLog.objects.count() == 6
        assert len(list(ch_backend.get_records(AccessLogCube.query()))) == 0
        assert ImportBatchSyncLog.objects.count() == 1
        sync_log = ImportBatchSyncLog.objects.get(import_batch_id=ib.pk)
        sync_log.state = ImportBatchSyncLog.STATE_SYNC
        sync_log.save()
        process_one_import_batch_sync_log(sync_log.pk)
        assert len(list(ch_backend.get_records(AccessLogCube.query()))) == 6, 'accesslogs synced'

    def test_import_batch_sync_after_interest_recalculation_with_delete(
        self, counter_records, organizations, report_type_nd
    ):
        """
        Test that when we update interest definition and recalculate interest that clickhouse
        will be synced correctly.
        """
        platform, report_type, ib = self._prepare_counter_records(
            counter_records, organizations, report_type_nd
        )
        assert AccessLog.objects.count() == 6
        assert len(list(ch_backend.get_records(AccessLogCube.query()))) == 6
        # prepare interest
        interest_rt = report_type_nd(1, short_name='interest')
        PlatformInterestReport.objects.create(platform=platform, report_type=report_type)
        rim = ReportInterestMetric.objects.create(
            report_type=report_type,
            metric=Metric.objects.get(short_name='Hits'),
            interest_group=InterestGroup.objects.create(short_name='aaa', position=1),
        )
        sync_interest_by_import_batches()
        # check result
        assert AccessLog.objects.count() == 11, "6 orig + 5 interest"
        assert len(list(ch_backend.get_records(AccessLogCube.query()))) == 11
        # redefine interest by dropping the ReportInterestMetric - it will remove all the interest
        rim.delete()
        smart_interest_sync()
        # check again
        assert AccessLog.objects.count() == 6, "6 orig + 0 interest"
        assert len(list(ch_backend.get_records(AccessLogCube.query()))) == 6, 'back to 6 in CH'

    def test_import_batch_sync_after_interest_recalculation_with_change(
        self, counter_records, organizations, report_type_nd
    ):
        """
        Test that when we update interest definition and recalculate interest that clickhouse
        will be synced correctly.
        """
        platform, report_type, ib = self._prepare_counter_records(
            counter_records, organizations, report_type_nd
        )
        platform, report_type, ib = self._prepare_counter_records(
            counter_records,
            organizations,
            report_type_nd,
            multiplier=2,
            metric='Visits',
            report_type=report_type,
        )
        assert AccessLog.objects.count() == 12
        assert len(list(ch_backend.get_records(AccessLogCube.query()))) == 12
        # prepare interest
        interest_rt = report_type_nd(1, short_name='interest')
        PlatformInterestReport.objects.create(platform=platform, report_type=report_type)
        rim = ReportInterestMetric.objects.create(
            report_type=report_type,
            metric=Metric.objects.get(short_name='Hits'),
            interest_group=InterestGroup.objects.create(short_name='aaa', position=1),
        )
        sync_interest_by_import_batches()
        # check result
        assert AccessLog.objects.count() == 17, "12 orig + 5 interest"
        interest_al_pks = set(
            AccessLog.objects.filter(report_type=interest_rt).values_list('pk', flat=True)
        )
        assert len(list(ch_backend.get_records(AccessLogCube.query()))) == 17
        old_sum_db = interest_rt.accesslog_set.aggregate(int_sum=Sum('value'))['int_sum']
        old_sum_cube = ch_backend.get_one_record(
            AccessLogCube.query()
            .filter(report_type_id__in=[interest_rt.pk])
            .aggregate(HSum('value'))
        ).sum
        assert old_sum_cube == old_sum_db
        # redefine interest by dropping the ReportInterestMetric - it will remove all the interest
        rim.metric = Metric.objects.get(short_name='Visits')
        rim.save()
        smart_interest_sync()
        # check again
        assert AccessLog.objects.count() == 17, "12 orig + 5 new interest"
        assert len(list(ch_backend.get_records(AccessLogCube.query()))) == 17, 'also 17 in CH'
        new_interest_al_pks = set(
            AccessLog.objects.filter(report_type=interest_rt).values_list('pk', flat=True)
        )
        assert (
            len(new_interest_al_pks & interest_al_pks) == 0
        ), 'all interest accesslogs were removed and recreated'
        assert (
            interest_rt.accesslog_set.aggregate(int_sum=Sum('value'))['int_sum'] == 2 * old_sum_db
        ), 'the interest with the new metric should be doubled'
        assert (
            ch_backend.get_one_record(
                AccessLogCube.query()
                .filter(report_type_id__in=[interest_rt.pk])
                .aggregate(HSum('value'))
            ).sum
            == 2 * old_sum_cube
        ), 'the interest with the new metric should be doubled'
