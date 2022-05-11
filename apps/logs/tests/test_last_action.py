from unittest.mock import patch

import pytest

from logs.logic.materialized_interest import smart_interest_sync
from logs.models import LastAction, ImportBatch, ReportInterestMetric, InterestGroup
from publications.models import PlatformInterestReport
from test_fixtures.entities.logs import MetricFactory


@pytest.mark.django_db()
class TestLastActionInterestChange:
    def test_update(self):
        """
        Test that the `update` method works as expected.
        """
        a1 = LastAction.objects.create(action='foo')
        t1 = a1.last_updated
        a1.update()
        assert a1.last_updated > t1

    @pytest.mark.parametrize(
        ['self_action', 'ref_action', 'newer'],
        [
            ('foo', 'bar', False),
            ('bar', 'foo', True),
            ('bar', 'bar', False),
            ('bar', 'bar', False),
            ('bar', 'baz', True),  # anything is newer than something non-existent
            ('foo', 'baz', True),  # anything is newer than something non-existent
        ],
    )
    def test_is_newer(self, self_action, ref_action, newer):
        LastAction.objects.create(action='foo')
        LastAction.objects.create(action='bar')
        self_obj = LastAction.objects.get(action=self_action)
        assert self_obj.is_newer(ref_action) is newer

    @pytest.mark.parametrize(
        ['self_action', 'trigger_action', 'should_run'],
        [
            ('foo', 'bar', True),
            ('bar', 'foo', False),
            ('bar', 'bar', False),
            ('bar', 'bar', False),
            ('bar', 'baz', False),  # non-existent trigger_action
            ('baz', 'foo', True),  # non-existent self_action
            ('baz', 'goo', True),  # non-existent both
        ],
    )
    def test_should_run(self, self_action, trigger_action, should_run):
        LastAction.objects.create(action='foo')
        LastAction.objects.create(action='bar')
        assert LastAction.should_run(self_action, trigger_action) is should_run

    def test_last_interest_change_marked_when_platformreporttype_changes(
        self, platform, report_type_nd
    ):
        rt = report_type_nd(0)
        report_type_nd(0, short_name='interest')
        assert ImportBatch.objects.count() == 0
        with patch('logs.logic.materialized_interest._find_platform_interest_changes') as mock:
            mock.return_value = ImportBatch.objects.none()
            smart_interest_sync()
            mock.assert_called_once()
        # try again - now it should be skipped because interest definition did not change in the meantime
        with patch('logs.logic.materialized_interest._find_platform_interest_changes') as mock:
            smart_interest_sync()
            mock.assert_not_called()
        # now create PlatformInterestReport, thus changing interest definition
        pir = PlatformInterestReport.objects.create(platform=platform, report_type=rt)
        with patch('logs.logic.materialized_interest._find_platform_interest_changes') as mock:
            mock.return_value = ImportBatch.objects.none()
            smart_interest_sync()
            mock.assert_called_once()
        # try again - now it should be skipped because interest definition did not change in the meantime
        with patch('logs.logic.materialized_interest._find_platform_interest_changes') as mock:
            smart_interest_sync()
            mock.assert_not_called()
        # delete the PlatformInterestReport - changes interest definition again
        pir.delete()
        with patch('logs.logic.materialized_interest._find_platform_interest_changes') as mock:
            mock.return_value = ImportBatch.objects.none()
            smart_interest_sync()
            mock.assert_called_once()

    def test_last_interest_change_marked_when_reportinterestmetric_changes(
        self, platform, report_type_nd
    ):
        rt = report_type_nd(0)
        report_type_nd(0, short_name='interest')
        metric = MetricFactory.create()
        ig = InterestGroup.objects.create(short_name='foo', name='FOO', position=1)
        assert ImportBatch.objects.count() == 0
        PlatformInterestReport.objects.create(platform=platform, report_type=rt)
        with patch('logs.logic.materialized_interest._find_metric_interest_changes') as mock:
            mock.return_value = ImportBatch.objects.none()
            smart_interest_sync()
            mock.assert_called_once()
        # try again - now it should be skipped because interest definition did not change in the meantime
        with patch('logs.logic.materialized_interest._find_metric_interest_changes') as mock:
            smart_interest_sync()
            mock.assert_not_called()
        # now create ReportInterestMetric, thus changing interest definition
        rim = ReportInterestMetric.objects.create(report_type=rt, metric=metric, interest_group=ig)
        with patch('logs.logic.materialized_interest._find_metric_interest_changes') as mock:
            mock.return_value = ImportBatch.objects.none()
            smart_interest_sync()
            mock.assert_called_once()
        # try again - now it should be skipped because interest definition did not change in the meantime
        with patch('logs.logic.materialized_interest._find_metric_interest_changes') as mock:
            smart_interest_sync()
            mock.assert_not_called()
        # delete the ReportInterestMetric - changes interest definition again
        rim.delete()
        with patch('logs.logic.materialized_interest._find_metric_interest_changes') as mock:
            mock.return_value = ImportBatch.objects.none()
            smart_interest_sync()
            mock.assert_called_once()
