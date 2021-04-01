import pytest

from logs.logic.cleanup import clean_obsolete_platform_title_links
from logs.logic.data_import import import_counter_records
from logs.models import ImportBatch, AccessLog
from organizations.tests.conftest import organizations  # noqa
from publications.models import PlatformTitle


@pytest.mark.django_db
class TestPlatformTitleCleanup:
    def test_cleanup_simple(self, counter_records_0d, report_type_nd, organizations, platform):
        # prepare data
        report_type = report_type_nd(0)
        organization = organizations[0]
        ib = ImportBatch.objects.create(
            organization=organization, platform=platform, report_type=report_type
        )
        import_counter_records(
            report_type, organization, platform, counter_records_0d, import_batch=ib
        )
        assert AccessLog.objects.count() == 1
        assert PlatformTitle.objects.count() == 1
        # remove accesslogs
        ib.delete()
        assert AccessLog.objects.count() == 0
        assert PlatformTitle.objects.count() == 1, 'the platform-title link is still there'
        clean_obsolete_platform_title_links()
        assert PlatformTitle.objects.count() == 0, 'the platform-title link was removed'

    def test_cleanup(self, counter_records, report_type_nd, organizations, platform):
        # prepare data
        report_type = report_type_nd(0)
        organization = organizations[0]
        ib = ImportBatch.objects.create(
            organization=organization, platform=platform, report_type=report_type
        )
        records = list(
            counter_records(
                [['A', '2020-01-01', 1], ['B', '2020-01-01', 2], ['A', '2020-02-01', 4]],
                platform=platform,
                metric='Hits',
            )
        )
        import_counter_records(report_type, organization, platform, records, import_batch=ib)
        assert AccessLog.objects.count() == 3
        assert PlatformTitle.objects.count() == 3
        # remove accesslogs
        AccessLog.objects.filter(date='2020-01-01').delete()
        assert AccessLog.objects.count() == 1
        assert PlatformTitle.objects.count() == 3, 'the platform-title links are all still there'
        clean_obsolete_platform_title_links()
        assert PlatformTitle.objects.count() == 1, 'one platform-title link remains'
        assert PlatformTitle.objects.get().date.isoformat() == '2020-02-01'
