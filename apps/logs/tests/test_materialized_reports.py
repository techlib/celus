import pytest

from logs.logic.data_import import import_counter_records
from logs.logic.materialized_reports import sync_materialized_reports
from logs.logic.queries import replace_report_type_with_materialized
from logs.models import (
    ImportBatch,
    AccessLog,
    ReportMaterializationSpec,
)
from logs.models import ReportType
from publications.models import Platform
from organizations.tests.conftest import organizations


@pytest.mark.django_db()
class TestMaterializedReport(object):
    def test_not_title(self, counter_records, organizations, report_type_nd):
        platform = Platform.objects.create(
            ext_id=1234, short_name='Platform1', name='Platform 1', provider='Provider 1'
        )
        data1 = [
            ['Title1', '2018-01-01', '1v1', 1],
            ['Title2', '2018-01-01', '1v2', 2],
            ['Title3', '2018-01-01', '1v2', 4],
        ]
        crs1 = list(counter_records(data1, metric='Hits', platform='Platform1'))
        report_type = report_type_nd(1)
        organization = organizations[0]
        ib = ImportBatch.objects.create(
            organization=organization, platform=platform, report_type=report_type
        )
        import_counter_records(report_type, organization, platform, crs1, import_batch=ib)
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

    def test_no_dim1(self, counter_records, organizations, report_type_nd):
        platform = Platform.objects.create(
            ext_id=1234, short_name='Platform1', name='Platform 1', provider='Provider 1'
        )
        data1 = [
            ['Title1', '2018-01-01', '1v1', 1],
            ['Title2', '2018-01-01', '1v2', 2],
            ['Title3', '2018-01-01', '1v2', 4],
        ]
        crs1 = list(counter_records(data1, metric='Hits', platform='Platform1'))
        report_type = report_type_nd(1)
        organization = organizations[0]
        ib = ImportBatch.objects.create(
            organization=organization, platform=platform, report_type=report_type
        )
        import_counter_records(report_type, organization, platform, crs1, import_batch=ib)
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

    def test_no_title_and_dim1(self, counter_records, organizations, report_type_nd):
        platform = Platform.objects.create(
            ext_id=1234, short_name='Platform1', name='Platform 1', provider='Provider 1'
        )
        data1 = [
            ['Title1', '2018-01-01', '1v1', 1],
            ['Title2', '2018-01-01', '1v2', 2],
            ['Title3', '2018-01-01', '1v2', 4],
        ]
        crs1 = list(counter_records(data1, metric='Hits', platform='Platform1'))
        report_type = report_type_nd(1)
        organization = organizations[0]
        ib = ImportBatch.objects.create(
            organization=organization, platform=platform, report_type=report_type
        )
        import_counter_records(report_type, organization, platform, crs1, import_batch=ib)
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
        ReportType.objects.create(materialization_spec=spec, short_name='m', name='m')
        # test the result
        qp = {'report_type': report_type, **query_params}
        assert replace_report_type_with_materialized(qp, other_used_dimensions=other_dims) == result
