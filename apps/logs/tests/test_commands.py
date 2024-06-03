import pytest
from django.core.files.base import ContentFile
from django.core.management import call_command
from publications.fake_data import TitleFactory
from publications.models import Item
from sushi.fake_data import FetchAttemptFactory
from sushi.models import AttemptStatus

from logs.fake_data import (
    AccessLogFactory,
    DimensionFactory,
    DimensionTextFactory,
    ImportBatchFactory,
    ManualDataUploadFactory,
    MetricFactory,
)
from logs.models import (
    AccessLog,
    ImportBatch,
    ManualDataUploadImportBatch,
    MduMethod,
    MduState,
    ReportTypeToDimension,
)
from logs.tasks import import_manual_upload_data, import_new_sushi_attempts_task
from test_scenarios.basic import (
    counter_report_types,  # noqa
    credentials,  # noqa
    data_sources,  # noqa
    organizations,  # noqa
    platforms,  # noqa
    report_types,  # noqa
)


@pytest.fixture
def ir_m1_setup(counter_report_types, report_types, users, organizations, platforms, credentials):
    metric = MetricFactory(short_name="Total_Item_Requests")
    dim1 = DimensionFactory(short_name="Platform")
    dim2 = DimensionFactory(short_name="Publisher")
    dt1 = DimensionTextFactory(text="Plat1", dimension=dim1)
    dt2 = DimensionTextFactory(text="Pub1", dimension=dim2)
    ReportTypeToDimension.objects.create(
        dimension_id=dim1.pk, report_type=report_types["ir_m1"], position=0
    )
    ReportTypeToDimension.objects.create(
        dimension_id=dim2.pk, report_type=report_types["ir_m1"], position=1
    )

    # Prepare attempts and data
    title1 = TitleFactory(name="Item1")
    ib = ImportBatchFactory(
        report_type=report_types["ir_m1"],
        platform=platforms["standalone"],
        organization=organizations["standalone"],
        date="2020-01-01",
    )
    data = b"""\
Report_Name,Multimedia Item Requests,
Report_ID,IR_M1,
Release,5,
Institution_Name,My Institution,
Institution_ID,
Metric_Types,Total_Item_Requests,
Report_Filters,Data_Type=Multimedia; Access_Method=Regular,
Report_Attributes,
Exceptions,
Reporting_Period,2020-01-01 to 2020-01-31,
Created,2022-10-01,
Created_By,My Platform,

Item,Publisher,Publisher_ID,Platform,Metric_Type,Reporting_Period_Total,Jan-2020
Item1,Pub1,,Plat1,Total_Item_Requests,1,1,
"""
    credentials["standalone_tr"].counter_reports.add(counter_report_types["ir_m1"])

    attempt = FetchAttemptFactory(
        status=AttemptStatus.SUCCESS,
        credentials=credentials["standalone_tr"],
        counter_report=counter_report_types["ir_m1"],
        start_date="2020-01-01",
        end_date="2020-01-31",
        import_batch_id=ib.pk,
        data_file=ContentFile(data, name="data-attempt.csv"),
    )
    AccessLogFactory(
        report_type=report_types["ir_m1"],
        metric=metric,
        platform=platforms["standalone"],
        organization=organizations["standalone"],
        date="2020-01-01",
        value=1,
        dim1=dt1.pk,
        dim2=dt2.pk,
        import_batch=ib,
        target=title1,
    )

    # Prepare mdu and data
    data = b"""\
Report_Name,Multimedia Item Requests,
Report_ID,IR_M1,
Release,5,
Institution_Name,My Institution,
Institution_ID,
Metric_Types,Total_Item_Requests,
Report_Filters,Data_Type=Multimedia; Access_Method=Regular,
Report_Attributes,
Exceptions,
Reporting_Period,2020-02-01 to 2020-02-28,
Created,2022-10-01,
Created_By,My Platform,

Item,Publisher,Publisher_ID,Platform,Metric_Type,Reporting_Period_Total,Feb-2020
Item2,Pub1,,Plat1,Total_Item_Requests,1,1,
"""
    title2 = TitleFactory(name="Item2")
    # monkey patch file name derivation, otherwise the code crashes
    user = users["admin2"]
    mdu = ManualDataUploadFactory(
        report_type=report_types["ir_m1"],
        platform=platforms["standalone"],
        organization=organizations["standalone"],
        data_file=ContentFile(data, name="data-mdu.csv"),
        user=user,
        state=MduState.IMPORTED,
        preflight={"log_count": 1},
        method=MduMethod.COUNTER,
    )
    ib = ImportBatchFactory(
        report_type=report_types["ir_m1"],
        platform=platforms["standalone"],
        organization=organizations["standalone"],
        date="2020-02-01",
    )
    ManualDataUploadImportBatch.objects.create(import_batch_id=ib.pk, mdu_id=mdu.pk)
    AccessLogFactory(
        report_type=report_types["ir_m1"],
        metric=metric,
        platform=platforms["standalone"],
        organization=organizations["standalone"],
        date="2020-01-01",
        value=1,
        dim1=dt1.pk,
        dim2=dt2.pk,
        import_batch=ib,
        target=title2,
    )

    return locals()


@pytest.mark.django_db
class TestIrM1FromTitlesToItemsTest:
    @pytest.mark.usefixtures("clickhouse_on_off")
    def test_command_with_credentials(self, ir_m1_setup):
        call_command("ir_m1_from_titles_to_items", "--do-it")

        ir_m1_setup["attempt"].refresh_from_db()
        ir_m1_setup["mdu"].refresh_from_db()
        assert ir_m1_setup["attempt"].status == AttemptStatus.IMPORTING, "Reimport planned"
        assert ir_m1_setup["mdu"].state == MduState.IMPORTING
        assert not AccessLog.objects.all().exists()
        assert not ImportBatch.objects.all().exists()

        import_new_sushi_attempts_task()
        import_manual_upload_data(ir_m1_setup["mdu"].id, ir_m1_setup["mdu"].user_id)

        ir_m1_setup["attempt"].refresh_from_db()
        ir_m1_setup["mdu"].refresh_from_db()

        assert ir_m1_setup["attempt"].status == AttemptStatus.SUCCESS
        assert ir_m1_setup["mdu"].state == MduState.IMPORTED

        assert Item.objects.filter(name="Item1").exists(), "Item Item1 was created"
        assert Item.objects.filter(name="Item2").exists(), "Item Item2 was created"

        assert not AccessLog.objects.filter(target__name="Item1").exists()
        assert not AccessLog.objects.filter(target__name="Item2").exists()

    @pytest.mark.usefixtures("clickhouse_on_off")
    def test_command_without_credentials(self, ir_m1_setup):
        ir_m1_setup["attempt"].credentials.delete()

        call_command("ir_m1_from_titles_to_items", "--do-it")

        ir_m1_setup["attempt"].refresh_from_db()
        ir_m1_setup["mdu"].refresh_from_db()

        # The attempt without credentials is reimported immediately because
        # the necessary information is available in the import batch which is
        # deleted in the process, so we cannot easily use celery to reimport it
        assert ir_m1_setup["attempt"].status == AttemptStatus.SUCCESS, "Immediate reimport"
        assert ir_m1_setup["mdu"].state == MduState.IMPORTING, "Reimport planned"

        assert Item.objects.filter(name="Item1").exists(), "Item Item1 was created"
        assert not Item.objects.filter(name="Item2").exists(), "Item Item2 was not created"

        assert not AccessLog.objects.filter(target__name="Item1").exists()
        assert not AccessLog.objects.filter(target__name="Item2").exists()

        # For MDU we need to run the import manually
        import_manual_upload_data(ir_m1_setup["mdu"].id, ir_m1_setup["mdu"].user_id)

        ir_m1_setup["mdu"].refresh_from_db()
        assert ir_m1_setup["mdu"].state == MduState.IMPORTED, "Reimported"

        assert Item.objects.filter(name="Item2").exists(), "Item Item2 was created"
        assert not AccessLog.objects.filter(target__name="Item2").exists()
