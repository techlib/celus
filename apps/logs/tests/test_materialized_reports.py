import pytest
from django.core.management import call_command
from django.utils.timezone import now

from logs.logic.data_import import import_counter_records
from logs.logic.materialized_interest import sync_interest_for_import_batch
from logs.logic.materialized_reports import (
    sync_materialized_reports,
    materialized_import_batch_queryset,
)
from logs.logic.queries import replace_report_type_with_materialized
from logs.models import (
    ImportBatch,
    AccessLog,
    ReportMaterializationSpec,
    ReportInterestMetric,
    Metric,
    InterestGroup,
)
from logs.models import ReportType
from nigiri.counter5 import CounterRecord
from publications.models import Platform, PlatformInterestReport
from organizations.tests.conftest import organizations
from publications.tests.conftest import platform


@pytest.mark.django_db()
class TestMaterializedReport:
    def test_not_title(self, counter_records, organizations, report_type_nd, platform):
        data1 = [
            ['Title1', '2018-01-01', '1v1', 1],
            ['Title2', '2018-01-01', '1v2', 2],
            ['Title3', '2018-01-01', '1v2', 4],
        ]
        crs1 = list(counter_records(data1, metric='Hits', platform=platform.short_name))
        report_type = report_type_nd(1)
        organization = organizations[0]
        import_counter_records(report_type, organization, platform, crs1)
        assert AccessLog.objects.count() == 3
        # now define materialized report
        spec = ReportMaterializationSpec.objects.create(
            base_report_type=report_type, keep_target=False
        )
        mat_report = ReportType.objects.create(materialization_spec=spec, short_name='m', name='m')
        assert mat_report.accesslog_set.count() == 0
        # let's calculate the data
        sync_materialized_reports()
        # test it
        assert mat_report.accesslog_set.count() == 2
        assert {rec['value'] for rec in mat_report.accesslog_set.values('value')} == {1, 6}

    def test_no_dim1(self, counter_records, organizations, report_type_nd, platform):
        data1 = [
            ['Title1', '2018-01-01', '1v1', 1],
            ['Title2', '2018-01-01', '1v2', 2],
            ['Title3', '2018-01-01', '1v2', 4],
        ]
        crs1 = list(counter_records(data1, metric='Hits', platform=platform.short_name))
        report_type = report_type_nd(1)
        organization = organizations[0]
        import_counter_records(report_type, organization, platform, crs1)
        assert AccessLog.objects.count() == 3
        # now define materialized report
        spec = ReportMaterializationSpec.objects.create(
            base_report_type=report_type, keep_dim1=False
        )
        mat_report = ReportType.objects.create(materialization_spec=spec, short_name='m', name='m')
        assert mat_report.accesslog_set.count() == 0
        # let's calculate the data
        sync_materialized_reports()
        # test it
        assert mat_report.accesslog_set.count() == 3
        assert {rec['value'] for rec in mat_report.accesslog_set.values('value')} == {1, 2, 4}

    def test_no_title_and_dim1(self, counter_records, organizations, report_type_nd, platform):
        data1 = [
            ['Title1', '2018-01-01', '1v1', 1],
            ['Title2', '2018-01-01', '1v2', 2],
            ['Title3', '2018-01-01', '1v2', 4],
        ]
        crs1 = list(counter_records(data1, metric='Hits', platform=platform.short_name))
        report_type = report_type_nd(1)
        organization = organizations[0]
        import_counter_records(report_type, organization, platform, crs1)
        assert AccessLog.objects.count() == 3
        # now define materialized report
        spec = ReportMaterializationSpec.objects.create(
            base_report_type=report_type, keep_dim1=False, keep_target=False
        )
        mat_report = ReportType.objects.create(materialization_spec=spec, short_name='m', name='m')
        assert mat_report.accesslog_set.count() == 0
        # let's calculate the data
        sync_materialized_reports()
        # test it
        assert mat_report.accesslog_set.count() == 1
        assert {rec['value'] for rec in mat_report.accesslog_set.values('value')} == {7}

    @pytest.mark.parametrize(
        ['query_params', 'other_dims', 'result'],
        [
            ({}, set(), True),
            ({}, {'target'}, False),
            ({}, {'target', 'dim1'}, False),
            ({}, {'target', 'dim2'}, False),
            ({}, {'target', 'date'}, False),
            ({}, {'date'}, True),
            ({}, {'dim2'}, True),
            ({}, {'dim2', 'date'}, True),
            ({'target_id': 10}, set(), False),
            ({'date__lt': '2020-01-01'}, set(), True),
            ({'target_id': 10, 'dim2': 5}, set(), False),
            ({'dim2': 5}, set(), True),
            ({'dim2': 5, 'date__gt': '2010-05-05'}, set(), True),
            ({'date__lt': '2020-01-01'}, {'dim1'}, False),
        ],
    )
    def test_replace_report_type_with_materialized(
        self, report_type_nd, query_params, other_dims, result
    ):
        report_type = report_type_nd(1)
        # prepare the materialized report
        spec = ReportMaterializationSpec.objects.create(
            base_report_type=report_type, keep_dim1=False, keep_target=False
        )
        ReportType.objects.create(
            materialization_spec=spec, short_name='m', name='m', approx_record_count=1
        )
        # test the result
        qp = {'report_type': report_type, **query_params}
        assert replace_report_type_with_materialized(qp, other_used_dimensions=other_dims) == result

    def test_recomputation_after_interest_changes(self, organizations, report_type_nd, platform):
        """
        When interest definition changes and interest is thus recomputed after materialization
        occurs, we need to recompute materialized reports as well.
        """
        cr = lambda **kw: CounterRecord(platform_name=platform.name, **kw)
        crs1 = [
            cr(start='2018-01-01', end='2018-01-31', metric='m1', value=1, title='Title1',),
            cr(start='2018-01-01', end='2018-01-31', metric='m2', value=2, title='Title2',),
            cr(start='2018-03-01', end='2018-03-31', metric='m2', value=4, title='Title3',),
        ]
        report_type = report_type_nd(1)
        organization = organizations[0]
        ibs, _stats = import_counter_records(report_type, organization, platform, crs1)
        assert AccessLog.objects.count() == 3

        # now define the interest
        interest_rt = report_type_nd(1, short_name='interest')
        PlatformInterestReport.objects.create(platform=platform, report_type=report_type)
        # we use metric m1 with one record - we will switch to m2 later
        rim = ReportInterestMetric.objects.create(
            report_type=report_type,
            metric=Metric.objects.get(short_name='m1'),
            interest_group=InterestGroup.objects.create(short_name='ig1', position=1),
        )
        for ib in ibs:
            sync_interest_for_import_batch(ib, interest_rt)
        assert interest_rt.accesslog_set.count() == 1, '1 record for metric m1'

        # now define materialized report for interest
        spec = ReportMaterializationSpec.objects.create(
            base_report_type=interest_rt, keep_target=False
        )
        mat_report = ReportType.objects.create(materialization_spec=spec, short_name='m', name='m')
        sync_materialized_reports()
        assert mat_report.accesslog_set.count() == 1, '1 record for interest in metric m1'
        old_mat_pks = {al.pk for al in mat_report.accesslog_set.all()}

        # now recompute the interest with the right metric
        rim.metric = Metric.objects.get(short_name='m2')
        rim.save()
        for ib in ibs:
            ib.refresh_from_db()  # this is needed because materialization_data was added to the ib
            sync_interest_for_import_batch(ib, interest_rt)
        assert interest_rt.accesslog_set.count() == 2, '2 interest records for metric m2'

        # and check that the materialization is up to date as well
        sync_materialized_reports()
        assert old_mat_pks != {al.pk for al in mat_report.accesslog_set.all()}
        assert mat_report.accesslog_set.count() == 2, '2 access logs without title for metric m2'

    def test_recomputation_after_date_change(
        self, organizations, report_type_nd, platform, counter_records
    ):
        """
        Tests that when `materialization_date` changes, older data will be recomputed
        """
        data1 = [
            ['Title1', '2018-01-01', '1v1', 1],
            ['Title2', '2018-01-01', '1v2', 2],
            ['Title3', '2018-01-01', '1v2', 4],
        ]
        crs1 = list(counter_records(data1, metric='Hits', platform=platform.short_name))
        report_type = report_type_nd(1)
        organization = organizations[0]
        import_counter_records(report_type, organization, platform, crs1)
        assert AccessLog.objects.count() == 3
        # now define materialized report
        spec = ReportMaterializationSpec.objects.create(
            base_report_type=report_type, keep_dim1=False, keep_target=False
        )
        mat_report = ReportType.objects.create(materialization_spec=spec, short_name='m', name='m')
        assert mat_report.accesslog_set.count() == 0
        # let's calculate the data
        sync_materialized_reports()
        # test it
        assert mat_report.accesslog_set.count() == 1
        assert materialized_import_batch_queryset(mat_report).count() == 0
        # update the date and test again
        mat_report.materialization_date = now()
        mat_report.save()
        assert materialized_import_batch_queryset(mat_report).count() == 1


@pytest.mark.django_db()
class TestMaterializedReportManagementCommands:
    def test_recompute_materialized_reports(
        self, counter_records, organizations, report_type_nd, platform
    ):
        data1 = [
            ['Title1', '2018-01-01', '1v1', 1],
            ['Title2', '2018-01-01', '1v2', 2],
            ['Title3', '2018-01-01', '1v2', 4],
        ]
        crs1 = list(counter_records(data1, metric='Hits', platform=platform.short_name))
        report_type = report_type_nd(1)
        organization = organizations[0]
        import_counter_records(report_type, organization, platform, crs1)
        # now define materialized report
        spec = ReportMaterializationSpec.objects.create(
            base_report_type=report_type, keep_target=False
        )
        mat_report = ReportType.objects.create(materialization_spec=spec, short_name='m', name='m')
        sync_materialized_reports()
        # test it
        assert mat_report.accesslog_set.count() == 2
        mat_logs_ids = {al.pk for al in mat_report.accesslog_set.all()}
        values = {rec['value'] for rec in mat_report.accesslog_set.values('value')}
        # now run the command and see if the ids have changed but have the same values
        call_command('recompute_materialized_reports')
        assert mat_report.accesslog_set.count() == 2
        assert mat_logs_ids != {al.pk for al in mat_report.accesslog_set.all()}
        assert {rec['value'] for rec in mat_report.accesslog_set.values('value')} == values
