import pytest
from core.exceptions import ModelUsageError
from logs.logic.data_import import import_counter_records
from logs.models import AccessLog, ImportBatch
from organizations.tests.conftest import organizations  # noqa  - used as fixture
from publications.models import Platform


@pytest.mark.django_db
class TestDataDeleting:
    def _prepare_accesslogs(self, counter_records, organizations, report_type_nd) -> [ImportBatch]:
        platform = Platform.objects.create(
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
        crs = list(counter_records(data, metric='Hits', platform='Platform1'))
        organization = organizations[0]
        report_type = report_type_nd(3)
        import_batches, stats = import_counter_records(report_type, organization, platform, crs)
        return import_batches

    def test_accesslog_cannot_be_deleted_from_instance(
        self, counter_records, organizations, report_type_nd
    ):
        self._prepare_accesslogs(counter_records, organizations, report_type_nd)
        assert AccessLog.objects.count() > 0
        orig_count = AccessLog.objects.count()
        al = AccessLog.objects.first()
        with pytest.raises(ModelUsageError):
            al.delete()
        assert AccessLog.objects.count() == orig_count, 'still the same number of accesslogs'

    def test_accesslog_cannot_be_deleted_from_query_set(
        self, counter_records, organizations, report_type_nd
    ):
        self._prepare_accesslogs(counter_records, organizations, report_type_nd)
        assert AccessLog.objects.count() > 0
        orig_count = AccessLog.objects.count()
        with pytest.raises(ModelUsageError):
            AccessLog.objects.all().delete()
        assert AccessLog.objects.count() == orig_count, 'still the same number of accesslogs'

    def test_accesslog_cannot_be_deleted_from_related_query_set(
        self, counter_records, organizations, report_type_nd
    ):
        ibs = self._prepare_accesslogs(counter_records, organizations, report_type_nd)
        assert AccessLog.objects.count() > 0
        orig_count = AccessLog.objects.count()
        with pytest.raises(ModelUsageError):
            ibs[0].accesslog_set.delete()
        assert AccessLog.objects.count() == orig_count, 'still the same number of accesslogs'

    def test_accesslog_can_be_deleted_in_cascade_from_import_batch(
        self, counter_records, organizations, report_type_nd
    ):
        ibs = self._prepare_accesslogs(counter_records, organizations, report_type_nd)
        assert AccessLog.objects.count() > 0
        for ib in ibs:
            ib.delete()
        assert AccessLog.objects.count() == 0, 'all accesslogs are deleted'
