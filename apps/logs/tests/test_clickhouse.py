from typing import Union
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.db import connection
from django.db.models import Sum
from hcube.api.models.aggregation import Sum as HSum
from logs.cubes import AccessLogCube, ch_backend
from logs.logic.clickhouse import (
    ComparisonResult,
    compare_db_with_clickhouse,
    process_one_import_batch_sync_log,
    resync_import_batch_with_clickhouse,
    sync_accesslogs_with_clickhouse_superfast,
    sync_import_batch_with_clickhouse,
)
from logs.logic.data_import import import_counter_records
from logs.logic.materialized_interest import smart_interest_sync, sync_interest_by_import_batches
from logs.models import (
    AccessLog,
    ImportBatch,
    ImportBatchSyncLog,
    InterestGroup,
    Metric,
    ReportInterestMetric,
)
from logs.tasks import (
    compare_db_with_clickhouse_task,
    process_outstanding_import_batch_sync_logs_task,
)
from organizations.tests.conftest import organizations  # noqa  - used as fixture
from publications.models import Platform, PlatformInterestReport

from test_fixtures.entities.logs import ImportBatchFullFactory


@pytest.mark.clickhouse
@pytest.mark.usefixtures('clickhouse_db')
class TestClickhouse:
    def test_clickhouse_cube_definition(self):
        from ..cubes import AccessLogCube, ch_backend

        ch_backend.initialize_storage(AccessLogCube)

    def test_clickhouse_add_data(self):
        from ..cubes import AccessLogCube, AccessLogCubeRecord, ch_backend

        ch_backend.initialize_storage(AccessLogCube)
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
        metric: Union[dict, str] = 'Hits',
        lowlevel=False,
        report_type=None,
    ) -> [ImportBatch]:
        """
        if `lowlevel` is given, it uses and internal function for the creation of counter records
        which does not force clickhouse sync on its own.
        """
        platform, _created = Platform.objects.get_or_create(
            ext_id=1234, short_name='Platform1', name='Platform 1', provider='Provider 1'
        )
        # metric may be a dict of name->multiplier or string
        metric_to_multi = metric if type(metric) is dict else {metric: 1}
        crs = []
        for m_name, multi in metric_to_multi.items():
            data = [
                ['Title1', '2018-01-01', '1v1', '2v1', '3v1', multi * 1],
                ['Title1', '2018-01-01', '1v2', '2v1', '3v1', multi * 2],
                ['Title2', '2018-01-01', '1v2', '2v2', '3v1', multi * 4],
                ['Title1', '2018-02-01', '1v1', '2v1', '3v1', multi * 8],
                ['Title2', '2018-02-01', '1v1', '2v2', '3v2', multi * 16],
                ['Title1', '2018-03-01', '1v1', '2v3', '3v2', multi * 32],
            ]
            crs += list(counter_records(data, metric=m_name, platform='Platform1'))
        organization = organizations[0]
        if not report_type:
            report_type = report_type_nd(3)
        import_batches, _stats = import_counter_records(
            report_type, organization, platform, crs, skip_clickhouse_sync=lowlevel
        )
        return platform, report_type, import_batches

    def test_one_import_batch_sync(self, counter_records, organizations, report_type_nd):
        *_, ibs = self._prepare_counter_records(counter_records, organizations, report_type_nd)
        assert AccessLog.objects.count() == 6
        ch_recs = list(ch_backend.get_records(AccessLogCube.query()))
        assert len(ch_recs) == 6
        assert ImportBatchSyncLog.objects.count() == len(ibs)
        for ib in ibs:
            assert (
                ImportBatchSyncLog.objects.get(import_batch_id=ib.pk).state
                == ImportBatchSyncLog.STATE_NO_CHANGE
            )
            ib.refresh_from_db()
            assert ib.last_clickhoused is not None
            assert ib.last_clickhoused > ib.last_updated

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
        platform, report_type, _ibs = self._prepare_counter_records(
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
        *_, ibs = self._prepare_counter_records(counter_records, organizations, report_type_nd)
        assert AccessLog.objects.count() == 6
        ch_recs = list(ch_backend.get_records(AccessLogCube.query()))
        assert len(ch_recs) == 6
        assert ImportBatchSyncLog.objects.count() == len(ibs)
        # delete the import batch
        for ib in ibs:
            ib.delete()
        ch_recs = list(ch_backend.get_records(AccessLogCube.query()))
        assert len(ch_recs) == 0, 'all records should be deleted from clickhouse'
        assert ImportBatchSyncLog.objects.count() == 0, 'sync log was removed as well'

    def test_import_batch_delete_from_queryset_method(
        self, counter_records, organizations, report_type_nd
    ):
        *_, ibs = self._prepare_counter_records(counter_records, organizations, report_type_nd)
        assert AccessLog.objects.count() == 6
        ch_recs = list(ch_backend.get_records(AccessLogCube.query()))
        assert len(ch_recs) == 6
        assert ImportBatchSyncLog.objects.count() == len(ibs)
        for ib in ibs:
            ImportBatch.objects.filter(pk=ib.pk).delete()
        ch_recs = list(ch_backend.get_records(AccessLogCube.query()))
        assert len(ch_recs) == 0, 'all records should be deleted from clickhouse'
        assert ImportBatchSyncLog.objects.count() == 0, 'sync log was removed as well'

    def test_import_batch_outdated_sync_logs(self, counter_records, organizations, report_type_nd):
        """
        We simulate a situation where an import batch was created but not synced with clickhouse
        for some reason.
        """
        *_, ibs = self._prepare_counter_records(
            counter_records, organizations, report_type_nd, lowlevel=True
        )
        assert AccessLog.objects.count() == 6
        assert len(list(ch_backend.get_records(AccessLogCube.query()))) == 0
        assert ImportBatchSyncLog.objects.count() == len(ibs)
        ib = ibs[0]
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
        *_, ibs = self._prepare_counter_records(
            counter_records, organizations, report_type_nd, lowlevel=True
        )
        assert AccessLog.objects.count() == 6
        assert len(list(ch_backend.get_records(AccessLogCube.query()))) == 0
        assert ImportBatchSyncLog.objects.count() == len(ibs)
        ibs.sort(key=lambda obj: obj.date)
        for ib, al_count in zip(ibs, [3, 5, 6]):
            sync_log = ImportBatchSyncLog.objects.get(import_batch_id=ib.pk)
            sync_log.state = ImportBatchSyncLog.STATE_SYNC
            sync_log.save()
            process_one_import_batch_sync_log(sync_log.pk)
            assert len(list(ch_backend.get_records(AccessLogCube.query()))) == al_count

    def test_import_batch_sync_after_interest_recalculation_with_delete(
        self, counter_records, organizations, report_type_nd
    ):
        """
        Test that when we update interest definition and recalculate interest that clickhouse
        will be synced correctly.
        """
        platform, report_type, _ibs = self._prepare_counter_records(
            counter_records, organizations, report_type_nd
        )
        assert AccessLog.objects.count() == 6
        assert len(list(ch_backend.get_records(AccessLogCube.query()))) == 6
        # prepare interest
        report_type_nd(1, short_name='interest')
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
        platform, report_type, _ibs = self._prepare_counter_records(
            counter_records, organizations, report_type_nd, metric={'Hits': 1, 'Visits': 2}
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

    def test_sync_import_batch_with_clickhouse_with_exception(
        self, counter_records, organizations, report_type_nd
    ):
        *_, ibs = self._prepare_counter_records(counter_records, organizations, report_type_nd)
        with pytest.raises(TypeError):
            # value error about string not being comparable to int should be raised
            sync_import_batch_with_clickhouse(ibs[0], batch_size='aaaa')

    def test_resync_import_batch_with_clickhouse(self):
        """
        Tests that resync really works
        """
        ib = ImportBatchFullFactory.create()
        sum_db_orig = AccessLog.objects.filter(import_batch=ib).aggregate(sum=Sum('value'))['sum']
        assert sum_db_orig > 0
        sum_cube = ch_backend.get_one_record(AccessLogCube.query().aggregate(HSum('value'))).sum
        assert sum_db_orig == sum_cube
        # modify one of the accesslogs
        al = AccessLog.objects.filter(import_batch=ib).first()
        diff = al.value + 1
        al.value = al.value + diff
        al.save()
        sum_db = AccessLog.objects.filter(import_batch=ib).aggregate(sum=Sum('value'))['sum']
        assert sum_db == sum_db_orig + diff
        # resync and check
        resync_import_batch_with_clickhouse(ib)
        sum_cube = ch_backend.get_one_record(AccessLogCube.query().aggregate(HSum('value'))).sum
        assert sum_db == sum_cube
        # and once again
        resync_import_batch_with_clickhouse(ib)
        sum_cube = ch_backend.get_one_record(AccessLogCube.query().aggregate(HSum('value'))).sum
        assert sum_db == sum_cube

    def test_resync_import_batch_with_clickhouse_with_al_replacement(self):
        """
        Tests that resync really works when we replace accesslogs inside an import batch
        """
        ib = ImportBatchFullFactory.create()
        sum_db_orig = AccessLog.objects.filter(import_batch=ib).aggregate(sum=Sum('value'))['sum']
        assert sum_db_orig > 0
        sum_cube = ch_backend.get_one_record(AccessLogCube.query().aggregate(HSum('value'))).sum
        assert sum_db_orig == sum_cube
        # modify one of the accesslogs
        al = AccessLog.objects.filter(import_batch=ib).first()
        diff = al.value + 1
        AccessLog.objects.filter(pk=al.id).delete(i_know_what_i_am_doing=True)  # delete original
        al.value = al.value + diff
        al.id = None  # create new al with new id
        al.save()
        sum_db = AccessLog.objects.filter(import_batch=ib).aggregate(sum=Sum('value'))['sum']
        assert sum_db == sum_db_orig + diff
        # resync and check
        resync_import_batch_with_clickhouse(ib)
        sum_cube = ch_backend.get_one_record(AccessLogCube.query().aggregate(HSum('value'))).sum
        assert sum_db == sum_cube, 'first resync'
        # and once again
        resync_import_batch_with_clickhouse(ib)
        sum_cube = ch_backend.get_one_record(AccessLogCube.query().aggregate(HSum('value'))).sum
        assert sum_db == sum_cube, 'second resync'


@pytest.mark.clickhouse
@pytest.mark.usefixtures('clickhouse_db')
@pytest.mark.django_db(transaction=True)
class TestClickhouseCompare:
    @pytest.mark.parametrize(
        ['in_db', 'in_ch'],
        [
            ([0, 1, 2], [0, 1, 2]),  # all ibs are in db and in ch
            ([0, 1, 2], [0, 1]),  # ib 2 is missing in ch
            ([0, 1], [0, 1, 2]),  # ib 2 is missing in db
            ([], [0, 1, 2]),  # all ibs are missing in db
            ([0, 1, 2], []),  # all ibs are missing in ch
            ([0, 1], [0, 2]),  # ib 1 is missing in both db and ch
            ([1], [0, 2]),  # no overlap between db and ch
            ([0, 2], [1]),  # no overlap between db and ch
        ],
    )
    def test_compare_with_clickhouse(
        self, counter_records, organizations, report_type_nd, in_db, in_ch
    ):
        platform, _created = Platform.objects.get_or_create(
            ext_id=1234, short_name='Platform1', name='Platform 1', provider='Provider 1'
        )
        data = [
            ['Title1', '2018-01-01', '1v1', '2v1', '3v1', 1],
            ['Title1', '2018-01-01', '1v2', '2v1', '3v1', 2],
            ['Title2', '2018-01-01', '1v2', '2v2', '3v1', 4],
            ['Title1', '2018-02-01', '1v1', '2v1', '3v1', 8],
            ['Title2', '2018-02-01', '1v1', '2v2', '3v2', 16],
            ['Title1', '2018-03-01', '1v1', '2v3', '3v2', 32],
        ]
        crs = list(counter_records(data, metric='hits', platform='Platform1'))
        organization = organizations[0]
        report_type = report_type_nd(3)
        import_batches, _stats = import_counter_records(
            report_type, organization, platform, crs, skip_clickhouse_sync=False
        )
        assert len(import_batches) == 3
        for ib_idx, ib in enumerate(import_batches):
            if ib_idx not in in_db:
                with connection.cursor() as cursor:
                    # we must do a low level query to delete the ibs from db
                    # without disturbing clickhouse
                    cursor.execute('DELETE FROM logs_accesslog WHERE import_batch_id=%s', [ib.pk])
                    cursor.execute('DELETE FROM logs_importbatch WHERE id = %s', [ib.pk])
                assert ImportBatch.objects.filter(pk=ib.pk).count() == 0
            if ib_idx not in in_ch:
                ch_backend.delete_records(AccessLogCube.query().filter(import_batch_id=ib.pk))
        result = compare_db_with_clickhouse()
        print(result.stats)
        assert len(result.import_batches_to_resync) == len(set(in_db) - set(in_ch))
        assert len(result.import_batches_to_delete) == len(set(in_ch) - set(in_db))

    @pytest.mark.parametrize(
        ['stats', 'is_ok'],
        [({}, True), ({'ok': 1}, True), ({'ok': 1, 'x': 2}, False), ({'x': 2}, False)],
    )
    def test_compare_with_clickhouse_task_problem_detection(self, stats, is_ok):
        with patch('logs.tasks.compare_db_with_clickhouse') as mock, patch(
            'logs.tasks.async_mail_admins'
        ) as mailmock:
            mock.return_value = ComparisonResult(stats=stats)
            compare_db_with_clickhouse_task()
            mock.assert_called_once()
            assert mailmock.delay.call_count == (1 if not is_ok else 0)


class TestManagementCommands:
    @pytest.mark.clickhouse
    @pytest.mark.django_db()
    def test_sync_clickhouse_db(self, clickhouse_raw_on_off, settings):
        client = clickhouse_raw_on_off
        if client is None:
            # just test that there is no crash or something
            call_command('sync_clickhouse_db')
        else:
            client.execute(f"DROP TABLE IF EXISTS {settings.CLICKHOUSE_DB}.AccessLogCube;")

            def access_log_cubes_tables_count():
                return len(
                    client.execute(
                        "SELECT * FROM system.tables WHERE name='AccessLogCube' AND database=%(db)s",
                        {"db": settings.CLICKHOUSE_DB},
                    )
                )

            assert access_log_cubes_tables_count() == 0
            call_command('sync_clickhouse_db')
            assert access_log_cubes_tables_count() == 1
