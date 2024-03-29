import pytest
from django.db.models import Sum
from django.utils.timezone import now
from logs.logic.data_import import import_counter_records
from logs.logic.materialized_interest import (
    _find_metric_interest_changes,
    _find_platform_interest_changes,
    _find_platform_report_type_disconnect,
    _find_report_type_metric_disconnect,
    _find_superseeded_import_batches,
    _find_unprocessed_batches,
    fast_compare_existing_and_new_records,
    smart_interest_sync,
    sync_interest_for_import_batch,
)
from logs.logic.materialized_reports import create_materialized_accesslogs
from logs.models import (
    AccessLog,
    ImportBatch,
    InterestGroup,
    Metric,
    ReportInterestMetric,
    ReportMaterializationSpec,
    ReportType,
)
from organizations.tests.conftest import organizations  # noqa - fixture
from publications.models import Platform, PlatformInterestReport


@pytest.mark.django_db()
class TestInterestCalculation:
    def test_simple(self, counter_records, organizations, report_type_nd):
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
        ibs, _stats = import_counter_records(report_type, organization, platform, crs1)
        assert AccessLog.objects.count() == 3
        assert len(ibs) == 1, 'only one import batch created'
        # now define the interest
        interest_rt = report_type_nd(1, short_name='interest')
        sync_interest_for_import_batch(ibs[0], interest_rt)
        assert interest_rt.accesslog_set.count() == 0, 'no interest platform and metric yet'
        # now improve it and retry
        PlatformInterestReport.objects.create(platform=platform, report_type=report_type)
        ReportInterestMetric.objects.create(
            report_type=report_type,
            metric=Metric.objects.get(short_name='Hits'),
            interest_group=InterestGroup.objects.create(short_name='ig1', position=1),
        )
        sync_interest_for_import_batch(ibs[0], interest_rt)
        assert interest_rt.accesslog_set.count() == 3, 'now it should work'
        assert interest_rt.accesslog_set.aggregate(sum=Sum('value'))['sum'] == 7

    def test_superseeded_report_types(self, counter_records, organizations, report_type_nd):
        """
        Test that when there are data for two report types from which one obsoletes the other,
        the newer data get precedence in interest values. On the other hand, if there are only
        data for that date in the old batch, take the data from there
        """
        organization = organizations[0]
        platform = Platform.objects.create(
            ext_id=1234, short_name='Platform1', name='Platform 1', provider='Provider 1'
        )
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
        ibs_old, _stats = import_counter_records(report_type_old, organization, platform, crs_old)
        ibs_new, _stats = import_counter_records(report_type_new, organization, platform, crs_new)
        assert AccessLog.objects.count() == 6
        # now define the interest
        interest_rt = report_type_nd(1, short_name='interest')
        PlatformInterestReport.objects.create(platform=platform, report_type=report_type_old)
        PlatformInterestReport.objects.create(platform=platform, report_type=report_type_new)
        hit_metric = Metric.objects.get(short_name='Hits')
        ig = InterestGroup.objects.create(short_name='ig1', position=1)
        ReportInterestMetric.objects.create(
            report_type=report_type_old, metric=hit_metric, interest_group=ig
        )
        ReportInterestMetric.objects.create(
            report_type=report_type_new, metric=hit_metric, interest_group=ig
        )
        # sync and count
        for ib_old in ibs_old:
            sync_interest_for_import_batch(ib_old, interest_rt)
        assert interest_rt.accesslog_set.count() == 1, '1 of 3 should make it to interest'
        for ib_new in ibs_new:
            sync_interest_for_import_batch(ib_new, interest_rt)
        assert interest_rt.accesslog_set.count() == 4, '3 of 3 should make it to interest'

    def test_superseeded_report_types_with_different_titles(
        self, counter_records, organizations, report_type_nd
    ):
        """
        Test that when there are data for two report types from which one obsoletes the other,
        the newer data get precedence in interest values.
        This should also work if there are different titles in the two batches because the
        detection should not work on title level
        """
        organization = organizations[0]
        platform = Platform.objects.create(
            ext_id=1234, short_name='Platform1', name='Platform 1', provider='Provider 1'
        )
        data_old = [
            ['Title1', '2018-01-01', '1v1', 1],
            ['Title2', '2018-01-01', '1v2', 2],
            ['Title3', '2018-01-01', '1v2', 4],
        ]
        data_new = [
            ['Title1', '2018-01-01', '1v1', 8],
            ['Title4', '2018-01-01', '1v2', 16],  # new title
            ['Title5', '2018-01-01', '1v2', 32],  # new title
        ]
        crs_old = list(counter_records(data_old, metric='Hits', platform='Platform1'))
        crs_new = list(counter_records(data_new, metric='Hits', platform='Platform1'))
        report_type_old = report_type_nd(1, short_name='old')  # type: ReportType
        report_type_new = report_type_nd(1, short_name='new')
        report_type_old.superseeded_by = report_type_new
        report_type_old.save()
        ibs_old, _stats = import_counter_records(report_type_old, organization, platform, crs_old)
        ibs_new, _stats = import_counter_records(report_type_new, organization, platform, crs_new)
        assert AccessLog.objects.count() == 6
        # now define the interest
        interest_rt = report_type_nd(1, short_name='interest')
        PlatformInterestReport.objects.create(platform=platform, report_type=report_type_old)
        PlatformInterestReport.objects.create(platform=platform, report_type=report_type_new)
        hit_metric = Metric.objects.get(short_name='Hits')
        ig = InterestGroup.objects.create(short_name='ig1', position=1)
        ReportInterestMetric.objects.create(
            report_type=report_type_old, metric=hit_metric, interest_group=ig
        )
        ReportInterestMetric.objects.create(
            report_type=report_type_new, metric=hit_metric, interest_group=ig
        )
        # sync and count
        for ib_old in ibs_old:
            sync_interest_for_import_batch(ib_old, interest_rt)
        assert interest_rt.accesslog_set.count() == 0, '0 of 3 should make it to interest'
        for ib_new in ibs_new:
            sync_interest_for_import_batch(ib_new, interest_rt)
        assert interest_rt.accesslog_set.count() == 3, '3 of 3 should make it to interest'

    def test_with_materialized_reports(self, counter_records, organizations, report_type_nd):
        """
        Test that when there are materialized report data present in import batch that they
        are not counted into interest.
        """
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
        ibs, _stats = import_counter_records(report_type, organization, platform, crs1)
        assert AccessLog.objects.count() == 3
        assert len(ibs) == 1, 'only one import batch'
        # create materialized report
        mat_def = ReportMaterializationSpec.objects.create(
            base_report_type=report_type, keep_dim1=False
        )
        mat_rt = ReportType.objects.create(short_name='materialized', materialization_spec=mat_def)
        mat_rec_count = create_materialized_accesslogs(mat_rt)
        assert mat_rec_count == 3
        ib = ibs[0]
        assert ib.accesslog_set.count() == 6
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
        assert interest_rt.accesslog_set.aggregate(sum=Sum('value'))['sum'] == 7


@pytest.mark.django_db()
class TestInterestRecomputationDetection:
    """
    Tests that code to detect ImportBatches that need to have their interest recomputed
    works properly
    """

    def test_find_unprocessed_batches(self, organizations, report_type_nd):
        organization = organizations[0]
        platform = Platform.objects.create(
            ext_id=1234, short_name='Platform1', name='Platform 1', provider='Provider 1'
        )
        report_type = report_type_nd(1)  # type: ReportType
        ib1 = ImportBatch.objects.create(
            organization=organization, platform=platform, report_type=report_type
        )
        ImportBatch.objects.create(
            organization=organization,
            platform=platform,
            report_type=report_type,
            interest_timestamp=now(),
        )
        # now define the interest
        PlatformInterestReport.objects.create(platform=platform, report_type=report_type)
        hit_metric = Metric.objects.create(short_name='Hits')
        ig = InterestGroup.objects.create(short_name='ig1', position=1)
        ReportInterestMetric.objects.create(
            report_type=report_type, metric=hit_metric, interest_group=ig
        )
        # let's test the function
        qs = _find_unprocessed_batches()
        assert {obj.pk for obj in qs} == {ib1.pk}

    def test_find_platform_interest_changes(self, organizations, report_type_nd):
        organization = organizations[0]
        platform = Platform.objects.create(
            ext_id=1234, short_name='Platform1', name='Platform 1', provider='Provider 1'
        )
        report_type = report_type_nd(1)  # type: ReportType
        ib1 = ImportBatch.objects.create(
            organization=organization,
            platform=platform,
            report_type=report_type,
            interest_timestamp=now(),
        )
        # now define the interest
        PlatformInterestReport.objects.create(platform=platform, report_type=report_type)
        # now create the second one - this one is newer than PlatformInterestReport, so its ok
        ImportBatch.objects.create(
            organization=organization,
            platform=platform,
            report_type=report_type,
            interest_timestamp=now(),
        )
        hit_metric = Metric.objects.create(short_name='Hits')
        ig = InterestGroup.objects.create(short_name='ig1', position=1)
        ReportInterestMetric.objects.create(
            report_type=report_type, metric=hit_metric, interest_group=ig
        )
        # let's test the function
        qs = _find_platform_interest_changes()
        assert {obj.pk for obj in qs} == {ib1.pk}

    def test_find_platform_interest_changes2(self, organizations, report_type_nd):
        """
        Test that when changing report type of PlatformInterestReport, import batches for that
        platform are recomputed.
        """
        organization = organizations[0]
        platform = Platform.objects.create(
            ext_id=1234, short_name='Platform1', name='Platform 1', provider='Provider 1'
        )
        report_type = report_type_nd(1, short_name='rt1')  # type: ReportType
        report_type2 = report_type_nd(1, short_name='rt2')  # type: ReportType
        assert report_type.pk != report_type2.pk
        # now define the interest
        pir = PlatformInterestReport.objects.create(platform=platform, report_type=report_type)
        ib1 = ImportBatch.objects.create(
            organization=organization,
            platform=platform,
            report_type=report_type,
            interest_timestamp=now(),
        )
        # update pir - it should invalidate ib1
        pir.report_type = report_type2
        pir.save()
        assert pir.last_modified > ib1.interest_timestamp
        # now create the second one - this one is newer than PlatformInterestReport, so its ok
        ImportBatch.objects.create(
            organization=organization,
            platform=platform,
            report_type=report_type,
            interest_timestamp=now(),
        )
        hit_metric = Metric.objects.create(short_name='Hits')
        ig = InterestGroup.objects.create(short_name='ig1', position=1)
        ReportInterestMetric.objects.create(
            report_type=report_type, metric=hit_metric, interest_group=ig
        )
        # let's test the function
        qs = _find_platform_interest_changes()
        assert {obj.pk for obj in qs} == {ib1.pk}

    def test_find_platform_interest_changes3(self, organizations, report_type_nd):
        """
        Test that when changing platform of PlatformInterestReport, import batches for that
        report type do not change - it would be pointless as only data for ib.platform can
        influence the ib interest.
        """
        organization = organizations[0]
        platform = Platform.objects.create(
            ext_id=1234, short_name='Platform1', name='Platform 1', provider='Provider 1'
        )
        report_type = report_type_nd(1, short_name='rt1')  # type: ReportType
        # now define the interest
        pir = PlatformInterestReport.objects.create(platform=platform, report_type=report_type)
        ib1 = ImportBatch.objects.create(
            organization=organization,
            platform=platform,
            report_type=report_type,
            interest_timestamp=now(),
        )
        # update pir - it should invalidate ib1
        pir.platform = Platform.objects.create(
            ext_id=1235, short_name='P2', name='P2', provider='P2'
        )
        pir.save()
        assert pir.last_modified > ib1.interest_timestamp
        qs = _find_platform_interest_changes()
        assert qs.count() == 0, 'nothing to recompute'

    def test_find_metric_interest_changes(self, organizations, report_type_nd):
        organization = organizations[0]
        platform = Platform.objects.create(
            ext_id=1234, short_name='Platform1', name='Platform 1', provider='Provider 1'
        )
        report_type = report_type_nd(1, short_name='rt1')  # type: ReportType
        report_type2 = report_type_nd(1, short_name='rt2')  # type: ReportType
        assert report_type.pk != report_type2.pk
        # now define the interest
        PlatformInterestReport.objects.create(platform=platform, report_type=report_type)
        ib1 = ImportBatch.objects.create(
            organization=organization,
            platform=platform,
            report_type=report_type,
            interest_timestamp=now(),
        )
        hit_metric = Metric.objects.create(short_name='Hits')
        ig = InterestGroup.objects.create(short_name='ig1', position=1)
        ReportInterestMetric.objects.create(
            report_type=report_type, metric=hit_metric, interest_group=ig
        )
        ImportBatch.objects.create(
            organization=organization,
            platform=platform,
            report_type=report_type,
            interest_timestamp=now(),
        )
        # let's test the function
        qs = _find_metric_interest_changes()
        assert {obj.pk for obj in qs} == {ib1.pk}

    def test_find_platform_report_type_disconnect(self, organizations, report_type_nd):
        organization = organizations[0]
        platform = Platform.objects.create(
            ext_id=1234, short_name='Platform1', name='Platform 1', provider='Provider 1'
        )
        report_type = report_type_nd(1)  # type: ReportType
        interest_rt = report_type_nd(1, short_name='interest')
        # now define the interest
        pir = PlatformInterestReport.objects.create(platform=platform, report_type=report_type)
        ib1 = ImportBatch.objects.create(
            organization=organization,
            platform=platform,
            report_type=report_type,
            interest_timestamp=now(),
        )
        hit_metric = Metric.objects.create(short_name='Hits')
        ig = InterestGroup.objects.create(short_name='ig1', position=1)
        ReportInterestMetric.objects.create(
            report_type=report_type, metric=hit_metric, interest_group=ig
        )
        AccessLog.objects.create(
            report_type=interest_rt,
            platform=platform,
            import_batch=ib1,
            organization=organization,
            value=10,
            date='2019-01-01',
            metric=hit_metric,
        )
        # let's test the function
        qs = _find_platform_report_type_disconnect()
        assert {obj.pk for obj in qs} == set()
        # let's do the disconnect and retry
        pir.delete()
        qs = _find_platform_report_type_disconnect()
        assert {obj.pk for obj in qs} == {ib1.pk}

    def test_find_report_type_metric_disconnect(self, organizations, report_type_nd):
        organization = organizations[0]
        platform = Platform.objects.create(
            ext_id=1234, short_name='Platform1', name='Platform 1', provider='Provider 1'
        )
        report_type = report_type_nd(1)  # type: ReportType
        interest_rt = report_type_nd(1, short_name='interest')
        # now define the interest
        PlatformInterestReport.objects.create(platform=platform, report_type=report_type)
        ib1 = ImportBatch.objects.create(
            organization=organization,
            platform=platform,
            report_type=report_type,
            interest_timestamp=now(),
        )
        hit_metric = Metric.objects.create(short_name='Hits')
        ig = InterestGroup.objects.create(short_name='ig1', position=1)
        rim = ReportInterestMetric.objects.create(
            report_type=report_type, metric=hit_metric, interest_group=ig
        )
        AccessLog.objects.create(
            report_type=report_type,
            platform=platform,
            import_batch=ib1,
            organization=organization,
            value=10,
            date='2019-01-01',
            metric=hit_metric,
        )
        stats = sync_interest_for_import_batch(ib1, interest_rt)
        assert stats['new_logs'] == 1
        # let's test the function - this time it is generator as there are more queries returned
        qs = next(_find_report_type_metric_disconnect())
        assert {obj.pk for obj in qs} == set()
        # let's do the disconnect and retry
        rim.delete()
        qs = next(_find_report_type_metric_disconnect())
        assert {obj.pk for obj in qs} == {ib1.pk}

    def test_find_superseeded_import_batches(self, organizations, report_type_nd):
        organization = organizations[0]
        platform = Platform.objects.create(
            ext_id=1234, short_name='Platform1', name='Platform 1', provider='Provider 1'
        )
        rt_old = report_type_nd(1, short_name='old')  # type: ReportType
        interest_rt = report_type_nd(1, short_name='interest')
        # now define the interest
        PlatformInterestReport.objects.create(platform=platform, report_type=rt_old)
        ib_old = ImportBatch.objects.create(
            organization=organization,
            platform=platform,
            report_type=rt_old,
            interest_timestamp=now(),
        )
        hit_metric = Metric.objects.create(short_name='Hits')
        ig = InterestGroup.objects.create(short_name='ig1', position=1)
        ReportInterestMetric.objects.create(
            report_type=rt_old, metric=hit_metric, interest_group=ig
        )
        AccessLog.objects.create(
            report_type=rt_old,
            platform=platform,
            import_batch=ib_old,
            organization=organization,
            value=10,
            date='2019-01-01',
            metric=hit_metric,
        )
        ib_old_unrel = ImportBatch.objects.create(
            organization=organization,
            platform=platform,
            report_type=rt_old,
            interest_timestamp=now(),
        )
        AccessLog.objects.create(
            report_type=rt_old,
            platform=platform,
            import_batch=ib_old_unrel,
            organization=organization,
            value=20,
            date='2019-02-01',
            metric=hit_metric,
        )
        stats = sync_interest_for_import_batch(ib_old, interest_rt)
        assert stats['new_logs'] == 1
        stats = sync_interest_for_import_batch(ib_old_unrel, interest_rt)
        assert stats['new_logs'] == 1
        # now nothing should be returned
        qs = _find_superseeded_import_batches()
        assert {obj.pk for obj in qs} == set()
        # let's add a newer data and check that we detect it
        rt_new = report_type_nd(1, short_name='new')  # type: ReportType
        rt_old.superseeded_by = rt_new
        rt_old.save()
        PlatformInterestReport.objects.create(platform=platform, report_type=rt_new)
        ReportInterestMetric.objects.create(
            report_type=rt_new, metric=hit_metric, interest_group=ig
        )
        ib_new = ImportBatch.objects.create(
            organization=organization,
            platform=platform,
            report_type=rt_new,
            interest_timestamp=now(),
        )
        AccessLog.objects.create(
            report_type=rt_new,
            platform=platform,
            import_batch=ib_new,
            organization=organization,
            value=20,
            date='2019-01-01',
            metric=hit_metric,
        )
        stats = sync_interest_for_import_batch(ib_new, interest_rt)
        assert stats['new_logs'] == 1
        qs = _find_superseeded_import_batches()
        assert {obj.pk for obj in qs} == {ib_old.pk}

    def test_superseeded_interest_deleted_with_different_titles(
        self, counter_records, organizations, report_type_nd
    ):
        """
        Test that there are old data for obsolete interest and I import new ones for the
        obsoleting RT, the old interest data will be removed even if the titles are different.
        """
        organization = organizations[0]
        platform = Platform.objects.create(
            ext_id=1234, short_name='Platform1', name='Platform 1', provider='Provider 1'
        )
        data_old = [
            ['Title1', '2018-01-01', '1v1', 1],
            ['Title2', '2018-01-01', '1v2', 2],
            ['Title3', '2018-01-01', '1v2', 4],
        ]
        data_new = [
            ['Title1', '2018-01-01', '1v1', 8],
            ['Title4', '2018-01-01', '1v2', 16],  # new title
            ['Title5', '2018-01-01', '1v2', 32],  # new title
        ]
        crs_old = list(counter_records(data_old, metric='Hits', platform='Platform1'))
        crs_new = list(counter_records(data_new, metric='Hits', platform='Platform1'))
        report_type_old = report_type_nd(1, short_name='old')  # type: ReportType
        report_type_new = report_type_nd(1, short_name='new')
        report_type_old.superseeded_by = report_type_new
        report_type_old.save()
        ibs_old, _stats = import_counter_records(report_type_old, organization, platform, crs_old)
        assert AccessLog.objects.count() == 3
        assert len(ibs_old) == 1
        ib_old = ibs_old[0]
        # now define the interest
        interest_rt = report_type_nd(1, short_name='interest')
        PlatformInterestReport.objects.create(platform=platform, report_type=report_type_old)
        PlatformInterestReport.objects.create(platform=platform, report_type=report_type_new)
        hit_metric = Metric.objects.get(short_name='Hits')
        ig = InterestGroup.objects.create(short_name='ig1', position=1)
        ReportInterestMetric.objects.create(
            report_type=report_type_old, metric=hit_metric, interest_group=ig
        )
        ReportInterestMetric.objects.create(
            report_type=report_type_new, metric=hit_metric, interest_group=ig
        )
        # sync old data
        sync_interest_for_import_batch(ib_old, interest_rt)
        assert interest_rt.accesslog_set.count() == 3, '3 of 3 should make it to interest'
        assert (
            ib_old.accesslog_set.filter(report_type=interest_rt).count() == 3
        ), '3 new interest records'
        ibs_new, _stats = import_counter_records(report_type_new, organization, platform, crs_new)
        assert len(ibs_new) == 1
        ib_new = ibs_new[0]
        sync_interest_for_import_batch(ib_new, interest_rt)
        assert interest_rt.accesslog_set.count() == 6, '3 of 3 should make it to interest'
        # let's run the detection code and see if it removes the old stuff
        smart_interest_sync()
        assert interest_rt.accesslog_set.count() == 3, 'only 3 of 6 should remain'
        assert (
            ib_new.accesslog_set.filter(report_type=interest_rt).count() == 3
        ), '# new interest records from new data'
        assert (
            ib_old.accesslog_set.filter(report_type=interest_rt).count() == 0
        ), 'old interest should be removed'


class TestSupportCode:
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
        assert same == 2
        assert add == [{'a': 50, 'b': 60}, {'a': 40, 'b': 70}]
        assert remove == {3}
