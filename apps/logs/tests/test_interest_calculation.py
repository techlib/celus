import pytest

from logs.logic.data_import import import_counter_records
from logs.logic.materialized_interest import sync_interest_for_import_batch, \
    fast_compare_existing_and_new_records
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

    @pytest.mark.now()
    def test_superseeded_report_types(self, counter_records, organizations, report_type_nd):
        """
        Test that when there are data for two report types from which one obsoletest the other,
        the newer data get precedence in interest values. On the other hand, if there are only
        data for that date in the old batch, take the data from there
        """
        organization = organizations[0]
        platform = Platform.objects.create(ext_id=1234, short_name='Platform1', name='Platform 1',
                                           provider='Provider 1')
        data_old = [
            ['Title1', '2018-01-01', '1v1', 1],
            ['Title2', '2018-01-01', '1v2', 2],
            ['Title3', '2018-02-01', '1v2', 4],  # this is extra - has different date
        ]
        data_new = [
            ['Title1', '2018-01-01', '1v1', 8],
            ['Title2', '2018-01-01', '1v2', 16],
            ['Title3', '2018-01-01', '1v2', 32],  # date differs
        ]
        crs_old = list(counter_records(data_old, metric='Hits', platform='Platform1'))
        crs_new = list(counter_records(data_new, metric='Hits', platform='Platform1'))
        report_type_old = report_type_nd(1, short_name='old')  # type: ReportType
        report_type_new = report_type_nd(1, short_name='new')
        report_type_old.superseeded_by = report_type_new
        report_type_old.save()
        ib_old = ImportBatch.objects.create(organization=organization, platform=platform,
                                            report_type=report_type_old)
        ib_new = ImportBatch.objects.create(organization=organization, platform=platform,
                                            report_type=report_type_new)
        import_counter_records(report_type_old, organization, platform, crs_old,
                               import_batch=ib_old)
        import_counter_records(report_type_new, organization, platform, crs_new,
                               import_batch=ib_new)
        assert AccessLog.objects.count() == 6
        # now define the interest
        interest_rt = report_type_nd(1, short_name='interest')
        PlatformInterestReport.objects.create(platform=platform, report_type=report_type_old)
        PlatformInterestReport.objects.create(platform=platform, report_type=report_type_new)
        hit_metric = Metric.objects.get(short_name='Hits')
        ig = InterestGroup.objects.create(short_name='ig1', position=1)
        ReportInterestMetric.objects.create(report_type=report_type_old, metric=hit_metric,
                                            interest_group=ig)
        ReportInterestMetric.objects.create(report_type=report_type_new, metric=hit_metric,
                                            interest_group=ig)
        # sync and count
        sync_interest_for_import_batch(ib_old, interest_rt)
        assert interest_rt.accesslog_set.count() == 1, '1 of 3 should make it to interest'
        sync_interest_for_import_batch(ib_new, interest_rt)
        assert interest_rt.accesslog_set.count() == 4, '3 of 3 should make it to interest'


class TestSupportCode(object):

    @pytest.mark.now()
    def test_fast_compare_existing_and_new_records(self):
        old_records = [
            {'a': 10, 'b': 20, 'pk': 1},
            {'a': 20, 'b': 30, 'pk': 2},
            {'a': 40, 'b': 60, 'pk': 3},
        ]
        new_records = [
            {'a': 10, 'b': 20},
            {'a': 20, 'b': 30},
            {'a': 50, 'b': 60},
            {'a': 40, 'b': 70},
        ]
        add, remove, same = fast_compare_existing_and_new_records(old_records, new_records, 'ab')
        print(add, remove, same)
        assert same == 2
        assert add == [{'a': 50, 'b': 60}, {'a': 40, 'b': 70}]
        assert remove == {3}
