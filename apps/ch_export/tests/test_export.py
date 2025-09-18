from unittest.mock import Mock, patch

import pytest
from logs.fake_data import ImportBatchFullFactory, InterestGroupFactory, MetricFactory
from logs.logic.data_import import import_counter_records
from logs.models import AccessLog, ReportInterestMetric, ReportMaterializationSpec, ReportType
from logs.tests.conftest import counter_records, report_type_nd  # noqa - fixture
from organizations.models import Organization
from organizations.tests.conftest import organizations  # noqa - fixture
from publications.fake_data import PlatformFactory
from publications.tests.conftest import interest_rt  # noqa - fixture

from ch_export.cubes import ch_export_client
from ch_export.fake_data import AccessLogExportFactory
from ch_export.models import AccessLogExport, AccessLogExportBatch, AccessLogExportTask


@pytest.mark.django_db
class TestAccessLogExportTaskExport:
    @pytest.fixture
    def organization(self):
        return Organization.objects.create(name="Test Org", short_name="test")

    @pytest.fixture
    def report_type(self):
        return ReportType.objects.create(name="Test Report", short_name="tr")

    @pytest.fixture
    def export(self, organization):
        return AccessLogExport.objects.create(organization=organization)

    @pytest.fixture
    def task(self, export, report_type):
        batch = AccessLogExportBatch.objects.create(export=export)
        return AccessLogExportTask.objects.create(batch=batch, report_type=report_type)

    @pytest.fixture
    def mock_setup(self):
        """Central fixture for all mocking setup"""
        with (
            patch("logs.logic.export_analytical.HCubeExport") as mock_hcube,
            patch("ch_export.models.AccessLogExport.ch_backend") as mock_ch_backend,
        ):
            mock_backend = Mock()
            mock_ch_backend.return_value = mock_backend
            mock_instance = Mock()
            mock_hcube.return_value = mock_instance

            yield {
                "hcube": mock_hcube,
                "ch_backend": mock_ch_backend,
                "backend": mock_backend,
                "instance": mock_instance,
            }

    def _assert_common_behavior(self, task, mocks):
        """Helper to assert common behavior across tests"""
        # Verify timestamps are set
        assert task.started is not None
        assert task.finished is not None
        assert task.started <= task.finished

        # Verify HCubeExport was called
        mocks["hcube"].assert_called_once()
        call_kwargs = mocks["hcube"].call_args[1]

        # Verify required parameters
        assert call_kwargs["table"] == "tr"
        assert call_kwargs["report_type"] == task.report_type
        assert call_kwargs["organization"] == task.batch.export.organization
        assert call_kwargs["cube_backend"] == mocks["backend"]
        assert "stderr" in call_kwargs

        return call_kwargs

    def test_export_with_error(self, task, mock_setup):
        mock_setup["instance"].export.side_effect = ValueError("Test error")

        with pytest.raises(ValueError):
            task.export_to_ch()

        assert "Test error" in task.error
        assert "Log follows:" in task.error
        self._assert_common_behavior(task, mock_setup)

    def test_cleanup_on_error(self, task, mock_setup):
        mock_setup["instance"].export.side_effect = ValueError("XXX Test error")

        # Record original values
        original_values = {"started": task.started, "finished": task.finished, "error": task.error}

        with pytest.raises(ValueError):
            task.export_to_ch()

        task.refresh_from_db()
        assert task.started != original_values["started"]
        assert task.finished != original_values["finished"]
        assert task.error != original_values["error"]
        assert task.started < task.finished
        assert "XXX Test error" in task.error


@pytest.mark.clickhouse
@pytest.mark.usefixtures("clickhouse_db", "ch_export_clickhouse")
@pytest.mark.django_db(transaction=True)
class TestRealAccessLogExportTaskExport:
    @classmethod
    def table_exists(cls, db, table):
        return ch_export_client.execute(f"EXISTS TABLE {db}.{table}")[0][0] == 1

    @classmethod
    def table_count(cls, db, table):
        return ch_export_client.execute(f"SELECT COUNT(*) FROM {db}.{table}")[0][0]

    def test_basic_sync(self):
        ib = ImportBatchFullFactory.create()
        exp = AccessLogExportFactory.create(organization=ib.organization)
        assert not self.table_exists(exp.ch_database, ib.report_type.short_name)
        task = AccessLogExportTask.objects.create(
            batch=exp.create_batch(), report_type=ib.report_type
        )
        task.export_to_ch()
        task.refresh_from_db()
        assert task.finished is not None
        assert task.error == ""
        assert self.table_exists(exp.ch_database, ib.report_type.short_name)
        assert self.table_count(exp.ch_database, ib.report_type.short_name) > 0
        assert self.table_count(exp.ch_database, ib.report_type.short_name) == ib.record_count

    def test_export_after_new_data(self):
        ib = ImportBatchFullFactory.create()
        exp = AccessLogExportFactory.create(organization=ib.organization)
        task = AccessLogExportTask.objects.create(
            batch=exp.create_batch(), report_type=ib.report_type, task_id="1"
        )
        task.export_to_ch()
        count = self.table_count(exp.ch_database, ib.report_type.short_name)
        assert task.stats["new_records_count"] == count
        assert task.stats["deleted_ibs_count"] == 0
        assert task.stats["new_ibs_count"] == 1
        assert task.stats["total_ib_count"] == 1

        # create new data
        ImportBatchFullFactory.create(organization=ib.organization, report_type=ib.report_type)
        task = AccessLogExportTask.objects.create(
            batch=exp.create_batch(), report_type=ib.report_type, task_id="2"
        )
        task.export_to_ch()
        task.refresh_from_db()
        assert task.finished is not None
        assert task.error == ""
        new_count = self.table_count(exp.ch_database, ib.report_type.short_name)
        assert new_count > count
        assert task.stats["new_records_count"] == (new_count - count)
        assert task.stats["deleted_ibs_count"] == 0
        assert task.stats["new_ibs_count"] == 1
        assert task.stats["total_ib_count"] == 2

    def test_export_after_deleted_data(self):
        ib = ImportBatchFullFactory.create()
        exp = AccessLogExportFactory.create(organization=ib.organization)
        task = AccessLogExportTask.objects.create(
            batch=exp.create_batch(), report_type=ib.report_type, task_id="1"
        )
        task.export_to_ch()
        task.refresh_from_db()
        assert task.finished is not None
        assert task.error == ""
        assert task.stats["deleted_ibs_count"] == 0
        assert task.stats["new_ibs_count"] == 1
        assert task.stats["total_ib_count"] == 1
        assert task.stats["new_records_count"] == 20

        # delete the data
        ib.delete()
        task = AccessLogExportTask.objects.create(
            batch=exp.create_batch(), report_type=ib.report_type, task_id="2"
        )
        task.export_to_ch()
        task.refresh_from_db()
        assert task.finished is not None
        assert task.stats["deleted_ibs_count"] == 1
        assert task.stats["new_ibs_count"] == 0
        assert task.stats["total_ib_count"] == 0
        assert task.stats["new_records_count"] == 0

    def test_export_with_interest_and_materialization(
        self, counter_records, organizations, report_type_nd, interest_rt
    ):
        """
        Test export in presence of interest and materialized reports.
        The interest should be exported into a separate table, materialized reports should not be
        exported.
        It also tests that a report type without data is not exported.
        """
        platform = PlatformFactory.create()
        report_type = report_type_nd(1)
        rt2 = report_type_nd(1, short_name="rt2")  # this will be empty
        organization = organizations[0]
        # now define the interest
        ReportInterestMetric.objects.create(
            report_type=report_type,
            metric=MetricFactory.create(short_name="Hits"),
            interest_group=InterestGroupFactory(short_name="ig1", position=1),
        )
        # and materialized view
        rt_no_title_spec = ReportMaterializationSpec.objects.create(
            base_report_type=report_type, keep_target=False
        )
        rt_no_title = ReportType.objects.create(
            materialization_spec=rt_no_title_spec, short_name="no_title", name="no_title"
        )
        # and materialized interest to cover all possible cases
        int_no_title_spec = ReportMaterializationSpec.objects.create(
            base_report_type=interest_rt, keep_target=False
        )
        int_no_title = ReportType.objects.create(
            materialization_spec=int_no_title_spec, short_name="int_no_title", name="int_no_title"
        )
        assert rt_no_title.approx_record_count == 0
        # import the data
        data1 = [
            ["Title1", "2018-01-01", "1v1", 1],
            ["Title2", "2018-01-01", "1v2", 2],
            ["Title3", "2018-01-01", "1v2", 4],
        ]
        crs1 = counter_records(data1, metric="Hits", platform="Platform1")
        ibs, _stats = import_counter_records(report_type, organization, platform, crs1)
        assert len(ibs) == 1, "only one import batch created"
        assert AccessLog.objects.count() == 3 + 3 + 2 + 1, (
            "3 normal, 3 interest, 2 materialized, 1 materialized interest"
        )
        # export the data
        exp = AccessLogExportFactory.create(organization=organization)
        assert {rt.short_name for rt in exp.report_types()} == {
            report_type.short_name,
            interest_rt.short_name,
        }, "only report_type and interest have data and are exportable"
        export_batch = exp.create_batch()
        for rt in exp.report_types():
            task = AccessLogExportTask.objects.create(
                batch=export_batch, report_type=rt, task_id=f"{rt.short_name}-1"
            )
            task.export_to_ch()
            task.refresh_from_db()
            assert task.finished is not None
            assert task.stats["deleted_ibs_count"] == 0
            assert task.stats["new_ibs_count"] == 1
            assert task.stats["total_ib_count"] == 1
        assert self.table_exists(exp.ch_database, report_type.short_name)
        assert self.table_count(exp.ch_database, report_type.short_name) == 3
        assert self.table_exists(exp.ch_database, interest_rt.short_name)
        assert self.table_count(exp.ch_database, interest_rt.short_name) == 3
        assert not self.table_exists(exp.ch_database, rt2.short_name)
        assert not self.table_exists(exp.ch_database, rt_no_title.short_name)
        assert not self.table_exists(exp.ch_database, int_no_title.short_name)

        # add more data a check again
        # the export logic is trying to compare old and new import batches, so potential
        # logic errors are possible if some data is already present in the export database.
        data2 = [
            ["Title4", "2018-02-01", "1v1", 1],
            ["Title5", "2018-02-01", "1v2", 2],
            ["Title6", "2018-02-01", "1v2", 4],
        ]
        crs2 = counter_records(data2, metric="Hits", platform="Platform1")
        ibs, _stats = import_counter_records(report_type, organization, platform, crs2)
        assert len(ibs) == 1, "only one import batch created"
        export_batch = exp.create_batch()
        for rt in exp.report_types():
            task = AccessLogExportTask.objects.create(
                batch=export_batch, report_type=rt, task_id=f"{rt.short_name}-2"
            )
            task.export_to_ch()
            task.refresh_from_db()
            assert task.finished is not None
            assert task.stats["deleted_ibs_count"] == 0
            assert task.stats["new_ibs_count"] == 1
            assert task.stats["total_ib_count"] == 2
        assert self.table_count(exp.ch_database, report_type.short_name) == 6
        assert self.table_count(exp.ch_database, interest_rt.short_name) == 6
        assert not self.table_exists(exp.ch_database, rt2.short_name)
        assert not self.table_exists(exp.ch_database, rt_no_title.short_name)
        assert not self.table_exists(exp.ch_database, int_no_title.short_name)
