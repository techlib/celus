import pytest

from logs.logic.data_import import import_counter_records
from logs.logic.materialized_interest import sync_interest_for_import_batch
from logs.models import ImportBatch, AccessLog, ReportInterestMetric, Metric, InterestGroup
from logs.models import ReportType
from publications.models import Platform, PlatformInterestReport
from organizations.tests.conftest import organizations


@pytest.mark.django_db()
class TestInterestCalculation(object):

    @pytest.mark.now()
    def test_simple(self, counter_records, organizations, report_type_nd):
        platform = Platform.objects.create(ext_id=1234, short_name='Platform1', name='Platform 1',
                                            provider='Provider 1')
        data1 = [
            ['Title1', '2018-01-01', '1v1', 1],
            ['Title2', '2018-01-01', '1v2', 2],
            ['Title3', '2018-01-01', '1v2', 4],
        ]
        crs1 = list(counter_records(data1, metric='Hits', platform='Platform1'))
        report_type = report_type_nd(1)
        organization = organizations[0]
        ib = ImportBatch.objects.create(organization=organization, platform=platform,
                                        report_type=report_type)
        import_counter_records(report_type, organization, platform, crs1, import_batch=ib)
        assert AccessLog.objects.count() == 3
        # now define the interest
        interest_rt = report_type_nd(1, short_name='interest')
        sync_interest_for_import_batch(ib, interest_rt)
        assert interest_rt.accesslog_set.count() == 0, 'no interest platform and metric yet'
        # now improve it and retry
        PlatformInterestReport.objects.create(platform=platform, report_type=report_type)
        ReportInterestMetric.objects.create(
            report_type=report_type,
            metric=Metric.objects.get(short_name='Hits'),
            interest_group=InterestGroup.objects.create(short_name='ig1', position=1),
        )
        sync_interest_for_import_batch(ib, interest_rt)
        assert interest_rt.accesslog_set.count() == 3, 'now it should work'

