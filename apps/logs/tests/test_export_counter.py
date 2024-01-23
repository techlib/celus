import re
from datetime import date

import pytest
from core.logic.dates import month_end
from organizations.fake_data import OrganizationFactory
from publications.fake_data import PlatformFactory

from logs.logic.export_counter import (
    DRCounter5Export,
    IR_M1Counter5Export,
    PRCounter5Export,
    TRCounter5Export,
)
from test_scenarios.counter_data import (
    dimension_texts,  # noqa
    dimensions,  # noqa
    dr,  # noqa
    dr_dim,  # noqa
    dr_ibs,  # noqa
    ir_m1,  # noqa
    ir_m1_dim,  # noqa
    ir_m1_ibs,  # noqa
    metrics,  # noqa
    pr,  # noqa
    pr_dim,  # noqa
    pr_ibs,  # noqa
    targets,  # noqa
    tr,  # noqa
    tr_dim,  # noqa
    tr_ibs,  # noqa
)

from .test_api_export_counter import sync_import_batches_with_clickhouse


@pytest.fixture
def platform():
    return PlatformFactory()


@pytest.fixture
def organization():
    return OrganizationFactory()


def fixed_created(input: str):
    return re.sub(r"Created,.*\r", "Created,2024-01-01T00:00:00Z\r", input)


@pytest.mark.clickhouse
@pytest.mark.django_db(transaction=True)
class TestTRCounterExport:
    @pytest.mark.parametrize(
        "title_preload_size,csv_line_batch",
        [
            [10, 10],
            [1, 10],
            [10, 1],
            [1, 1],
        ],
    )
    def test_single_month(
        self,
        organization,
        platform,
        tr,
        tr_ibs,
        settings,
        title_preload_size,
        csv_line_batch,
        clickhouse_db,
    ):
        settings.CLICKHOUSE_SYNC_ACTIVE = True
        settings.CELUS_VERSION = "X.Y.Z"
        sync_import_batches_with_clickhouse(*tr_ibs)

        export = TRCounter5Export(organization, platform, tr, date(2020, 2, 1), date(2020, 2, 1))
        export.TITLE_PRELOAD_SIZE = title_preload_size
        export.CSV_LINE_BATCH = csv_line_batch

        assert (
            fixed_created("".join(export.csv()))
            == """\
Report_Name,Title Master Report\r
Report_ID,TR\r
Release,5\r
Institution_Name,Celus\r
Institution_ID,ISNI:0000000000000000\r
Metric_Types,\r
Report_Filters,\r
Report_Attributes,Attributes_To_Show=Data_Type|Section_Type|YOP|Access_Type|Access_Method\r
Exceptions,\r
Reporting_Period,Begin_Date=2020-02-01; End_Date=2020-02-29\r
Created,2024-01-01T00:00:00Z\r
Created_By,Celus X.Y.Z\r
\r
Title,Publisher,Publisher_ID,Platform,DOI,Proprietary_ID,ISBN,Print_ISSN,Online_ISSN,URI,Data_Type,Section_Type,YOP,Access_Type,Access_Method,Metric_Type,Reporting_Period_Total,Feb-2020\r
target1,Pub1,,Plat1,10.4324/9781003185581,,9781003185581,1111-1111,9111-1111,,Book,Book,2020,Controlled,Regular,Total_Item_Requests,1,1\r
target1,Pub1,,Plat1,10.4324/9781003185581,,9781003185581,1111-1111,9111-1111,,Book,Book,2020,Controlled,Regular,No_License,3,3\r
target2,Pub1,,Plat1,,,9781492084884,,,,Journal,Article,2022,Controlled,Regular,Total_Item_Requests,23,23\r
target2,Pub1,,Plat1,,,9781492084884,,,,Journal,Article,2022,Controlled,Regular,No_License,29,29\r
"""
        )

    def test_no_months(
        self,
        organization,
        platform,
        tr,
        tr_ibs,
        settings,
        clickhouse_db,
    ):
        settings.CLICKHOUSE_SYNC_ACTIVE = True
        settings.CELUS_VERSION = "X.Y.Z"
        sync_import_batches_with_clickhouse(*tr_ibs)

        export = TRCounter5Export(organization, platform, tr, None, None)

        assert (
            fixed_created("".join(export.csv()))
            == """\
Report_Name,Title Master Report\r
Report_ID,TR\r
Release,5\r
Institution_Name,Celus\r
Institution_ID,ISNI:0000000000000000\r
Metric_Types,\r
Report_Filters,\r
Report_Attributes,Attributes_To_Show=Data_Type|Section_Type|YOP|Access_Type|Access_Method\r
Exceptions,\r
Reporting_Period,Begin_Date=2019-12-01; End_Date=2021-01-31\r
Created,2024-01-01T00:00:00Z\r
Created_By,Celus X.Y.Z\r
\r
Title,Publisher,Publisher_ID,Platform,DOI,Proprietary_ID,ISBN,Print_ISSN,Online_ISSN,URI,Data_Type,Section_Type,YOP,Access_Type,Access_Method,Metric_Type,Reporting_Period_Total,Dec-2019,Jan-2020,Feb-2020,Mar-2020,Apr-2020,May-2020,Jun-2020,Jul-2020,Aug-2020,Sep-2020,Oct-2020,Nov-2020,Dec-2020,Jan-2021\r
target1,Pub1,,Plat1,10.4324/9781003185581,,9781003185581,1111-1111,9111-1111,,Book,Book,2020,Controlled,Regular,Total_Item_Requests,36,11,0,1,0,5,0,0,0,0,0,0,0,0,19\r
target1,Pub1,,Plat1,10.4324/9781003185581,,9781003185581,1111-1111,9111-1111,,Book,Book,2020,Controlled,Regular,No_License,40,13,0,3,0,7,0,0,0,0,0,0,0,0,17\r
target2,Pub1,,Plat1,,,9781492084884,,,,Journal,Article,2022,Controlled,Regular,Total_Item_Requests,23,0,0,23,0,0,0,0,0,0,0,0,0,0,0\r
target2,Pub1,,Plat1,,,9781492084884,,,,Journal,Article,2022,Controlled,Regular,No_License,29,0,0,29,0,0,0,0,0,0,0,0,0,0,0\r
target3,Pub1,,Plat1,,,,,,,Other,Chapter,2021,Controlled,Regular,Total_Item_Requests,31,0,0,0,0,31,0,0,0,0,0,0,0,0,0\r
target3,Pub1,,Plat1,,,,,,,Other,Chapter,2021,Controlled,Regular,No_License,37,0,0,0,0,37,0,0,0,0,0,0,0,0,0\r
"""
        )

    def test_empty(
        self,
        organization,
        platform,
        tr,
        settings,
        clickhouse_db,
    ):
        settings.CLICKHOUSE_SYNC_ACTIVE = True
        export = TRCounter5Export(organization, platform, tr, None, None)
        content = "".join(export.csv()).splitlines()
        end_date = month_end(date.today()).strftime("%Y-%m-%d")
        assert content[1] == "Report_ID,TR"
        assert content[9] == f"Reporting_Period,Begin_Date=1970-01-01; End_Date={end_date}"
        assert content[-1].startswith("Title")

    def test_errors(
        self,
        organization,
        platform,
        tr,
        tr_ibs,
        settings,
        clickhouse_db,
        caplog,
    ):
        tr_ibs[0].accesslog_set.update(target_id=None)
        settings.CLICKHOUSE_SYNC_ACTIVE = True

        sync_import_batches_with_clickhouse(*tr_ibs)

        export = TRCounter5Export(organization, platform, tr, None, None)

        "".join(export.csv())
        assert caplog.records[-1].msg == "There are structural errors in the data"


@pytest.mark.clickhouse
@pytest.mark.django_db(transaction=True)
class TestDRCounterExport:
    @pytest.mark.parametrize(
        "title_preload_size,csv_line_batch",
        [
            [10, 10],
            [2, 10],  # title_preload_size >= 2 (peeking at next record)
            [10, 1],
            [2, 1],
        ],
    )
    def test_single_month(
        self,
        organization,
        platform,
        dr,
        dr_ibs,
        settings,
        title_preload_size,
        csv_line_batch,
        clickhouse_db,
    ):
        settings.CLICKHOUSE_SYNC_ACTIVE = True
        settings.CELUS_VERSION = "X.Y.Z"
        sync_import_batches_with_clickhouse(*dr_ibs)

        export = DRCounter5Export(organization, platform, dr, date(2020, 2, 1), date(2020, 2, 1))
        export.TITLE_PRELOAD_SIZE = title_preload_size
        export.CSV_LINE_BATCH = csv_line_batch

        assert (
            fixed_created("".join(export.csv()))
            == """\
Report_Name,Database Master Report\r
Report_ID,DR\r
Release,5\r
Institution_Name,Celus\r
Institution_ID,ISNI:0000000000000000\r
Metric_Types,\r
Report_Filters,\r
Report_Attributes,Attributes_To_Show=Data_Type|Access_Method\r
Exceptions,\r
Reporting_Period,Begin_Date=2020-02-01; End_Date=2020-02-29\r
Created,2024-01-01T00:00:00Z\r
Created_By,Celus X.Y.Z\r
\r
Database,Publisher,Publisher_ID,Platform,Proprietary_ID,Data_Type,Access_Method,Metric_Type,Reporting_Period_Total,Feb-2020\r
target1,Pub1,,Plat1,,Journal,Regular,Total_Item_Requests,23,23\r
target1,Pub1,,Plat1,,Journal,Regular,No_License,29,29\r
target2,Pub1,,Plat1,,Book,Regular,Total_Item_Requests,1,1\r
target2,Pub1,,Plat1,,Book,Regular,No_License,3,3\r
"""
        )

    def test_no_months(
        self,
        organization,
        platform,
        dr,
        dr_ibs,
        settings,
        clickhouse_db,
    ):
        settings.CLICKHOUSE_SYNC_ACTIVE = True
        settings.CELUS_VERSION = "X.Y.Z"
        sync_import_batches_with_clickhouse(*dr_ibs)

        export = DRCounter5Export(organization, platform, dr, None, None)

        assert (
            fixed_created("".join(export.csv()))
            == """\
Report_Name,Database Master Report\r
Report_ID,DR\r
Release,5\r
Institution_Name,Celus\r
Institution_ID,ISNI:0000000000000000\r
Metric_Types,\r
Report_Filters,\r
Report_Attributes,Attributes_To_Show=Data_Type|Access_Method\r
Exceptions,\r
Reporting_Period,Begin_Date=2019-12-01; End_Date=2021-01-31\r
Created,2024-01-01T00:00:00Z\r
Created_By,Celus X.Y.Z\r
\r
Database,Publisher,Publisher_ID,Platform,Proprietary_ID,Data_Type,Access_Method,Metric_Type,Reporting_Period_Total,Dec-2019,Jan-2020,Feb-2020,Mar-2020,Apr-2020,May-2020,Jun-2020,Jul-2020,Aug-2020,Sep-2020,Oct-2020,Nov-2020,Dec-2020,Jan-2021\r
target1,Pub1,,Plat1,,Journal,Regular,Total_Item_Requests,23,0,0,23,0,0,0,0,0,0,0,0,0,0,0\r
target1,Pub1,,Plat1,,Journal,Regular,No_License,29,0,0,29,0,0,0,0,0,0,0,0,0,0,0\r
target2,Pub1,,Plat1,,Book,Regular,Total_Item_Requests,36,11,0,1,0,5,0,0,0,0,0,0,0,0,19\r
target2,Pub1,,Plat1,,Book,Regular,No_License,40,13,0,3,0,7,0,0,0,0,0,0,0,0,17\r
target3,Pub1,,Plat1,,Other,Regular,Total_Item_Requests,31,0,0,0,0,31,0,0,0,0,0,0,0,0,0\r
target3,Pub1,,Plat1,,Other,Regular,No_License,37,0,0,0,0,37,0,0,0,0,0,0,0,0,0\r
"""
        )

    def test_empty(
        self,
        organization,
        platform,
        dr,
        settings,
        clickhouse_db,
    ):
        settings.CLICKHOUSE_SYNC_ACTIVE = True
        export = DRCounter5Export(organization, platform, dr, None, None)
        content = "".join(export.csv()).splitlines()
        end_date = month_end(date.today()).strftime("%Y-%m-%d")
        assert content[1] == "Report_ID,DR"
        assert content[9] == f"Reporting_Period,Begin_Date=1970-01-01; End_Date={end_date}"
        assert content[-1].startswith("Database")

    def test_errors(
        self,
        organization,
        platform,
        dr,
        dr_ibs,
        settings,
        clickhouse_db,
        caplog,
    ):
        dr_ibs[0].accesslog_set.update(target_id=None)
        settings.CLICKHOUSE_SYNC_ACTIVE = True

        sync_import_batches_with_clickhouse(*dr_ibs)

        export = DRCounter5Export(organization, platform, dr, None, None)

        "".join(export.csv())
        assert caplog.records[-1].msg == "There are structural errors in the data"


@pytest.mark.clickhouse
@pytest.mark.django_db(transaction=True)
class TestPRCounterExport:
    @pytest.mark.parametrize(
        "title_preload_size,csv_line_batch",
        [
            [10, 10],
            [2, 10],  # title_preload_size >= 2 (peeking at next record)
            [10, 1],
            [2, 1],
        ],
    )
    def test_single_month(
        self,
        organization,
        platform,
        pr,
        pr_ibs,
        settings,
        title_preload_size,
        csv_line_batch,
        clickhouse_db,
    ):
        settings.CLICKHOUSE_SYNC_ACTIVE = True
        settings.CELUS_VERSION = "X.Y.Z"
        sync_import_batches_with_clickhouse(*pr_ibs)

        export = PRCounter5Export(organization, platform, pr, date(2020, 2, 1), date(2020, 2, 1))
        export.TITLE_PRELOAD_SIZE = title_preload_size
        export.CSV_LINE_BATCH = csv_line_batch

        assert (
            fixed_created("".join(export.csv()))
            == """\
Report_Name,Platform Master Report\r
Report_ID,PR\r
Release,5\r
Institution_Name,Celus\r
Institution_ID,ISNI:0000000000000000\r
Metric_Types,\r
Report_Filters,\r
Report_Attributes,Attributes_To_Show=Data_Type|Access_Method\r
Exceptions,\r
Reporting_Period,Begin_Date=2020-02-01; End_Date=2020-02-29\r
Created,2024-01-01T00:00:00Z\r
Created_By,Celus X.Y.Z\r
\r
Platform,Data_Type,Access_Method,Metric_Type,Reporting_Period_Total,Feb-2020\r
Plat1,Book,Regular,Total_Item_Requests,1,1\r
Plat1,Book,Regular,No_License,3,3\r
Plat1,Journal,Regular,Total_Item_Requests,23,23\r
Plat1,Journal,Regular,No_License,29,29\r
"""
        )

    def test_no_months(
        self,
        organization,
        platform,
        pr,
        pr_ibs,
        settings,
        clickhouse_db,
    ):
        settings.CLICKHOUSE_SYNC_ACTIVE = True
        settings.CELUS_VERSION = "X.Y.Z"
        sync_import_batches_with_clickhouse(*pr_ibs)

        export = PRCounter5Export(organization, platform, pr, None, None)

        assert (
            fixed_created("".join(export.csv()))
            == """\
Report_Name,Platform Master Report\r
Report_ID,PR\r
Release,5\r
Institution_Name,Celus\r
Institution_ID,ISNI:0000000000000000\r
Metric_Types,\r
Report_Filters,\r
Report_Attributes,Attributes_To_Show=Data_Type|Access_Method\r
Exceptions,\r
Reporting_Period,Begin_Date=2019-12-01; End_Date=2021-01-31\r
Created,2024-01-01T00:00:00Z\r
Created_By,Celus X.Y.Z\r
\r
Platform,Data_Type,Access_Method,Metric_Type,Reporting_Period_Total,Dec-2019,Jan-2020,Feb-2020,Mar-2020,Apr-2020,May-2020,Jun-2020,Jul-2020,Aug-2020,Sep-2020,Oct-2020,Nov-2020,Dec-2020,Jan-2021\r
Plat1,Other,Regular,Total_Item_Requests,31,0,0,0,0,31,0,0,0,0,0,0,0,0,0\r
Plat1,Other,Regular,No_License,37,0,0,0,0,37,0,0,0,0,0,0,0,0,0\r
Plat1,Book,Regular,Total_Item_Requests,36,11,0,1,0,5,0,0,0,0,0,0,0,0,19\r
Plat1,Book,Regular,No_License,40,13,0,3,0,7,0,0,0,0,0,0,0,0,17\r
Plat1,Journal,Regular,Total_Item_Requests,23,0,0,23,0,0,0,0,0,0,0,0,0,0,0\r
Plat1,Journal,Regular,No_License,29,0,0,29,0,0,0,0,0,0,0,0,0,0,0\r
"""
        )

    def test_empty(
        self,
        organization,
        platform,
        pr,
        settings,
        clickhouse_db,
    ):
        settings.CLICKHOUSE_SYNC_ACTIVE = True
        export = PRCounter5Export(organization, platform, pr, None, None)
        content = "".join(export.csv()).splitlines()
        end_date = month_end(date.today()).strftime("%Y-%m-%d")
        assert content[1] == "Report_ID,PR"
        assert content[9] == f"Reporting_Period,Begin_Date=1970-01-01; End_Date={end_date}"
        assert content[-1].startswith("Platform")

    def test_errors(
        self,
        organization,
        platform,
        pr,
        pr_ibs,
        settings,
        clickhouse_db,
        targets,
        caplog,
    ):
        # Remove required platform dimension
        dim_attr = pr.dim_name_to_dim_attr("Platform")
        pr_ibs[0].accesslog_set.update(**{dim_attr: None})
        settings.CLICKHOUSE_SYNC_ACTIVE = True

        sync_import_batches_with_clickhouse(*pr_ibs)

        export = PRCounter5Export(organization, platform, pr, None, None)

        "".join(export.csv())
        assert caplog.records[-1].msg == "There are structural errors in the data"


@pytest.mark.clickhouse
@pytest.mark.django_db(transaction=True)
class TestIR_M1CounterExport:
    @pytest.mark.parametrize(
        "title_preload_size,csv_line_batch",
        [
            [10, 10],
            [2, 10],  # title_preload_size >= 2 (peeking at next record)
            [10, 1],
            [2, 1],
        ],
    )
    def test_single_month(
        self,
        organization,
        platform,
        ir_m1,
        ir_m1_ibs,
        settings,
        title_preload_size,
        csv_line_batch,
        clickhouse_db,
    ):
        settings.CLICKHOUSE_SYNC_ACTIVE = True
        settings.CELUS_VERSION = "X.Y.Z"
        sync_import_batches_with_clickhouse(*ir_m1_ibs)

        export = IR_M1Counter5Export(
            organization, platform, ir_m1, date(2020, 2, 1), date(2020, 2, 1)
        )
        export.TITLE_PRELOAD_SIZE = title_preload_size
        export.CSV_LINE_BATCH = csv_line_batch

        assert (
            fixed_created("".join(export.csv()))
            == """\
Report_Name,Multimedia Item Requests\r
Report_ID,IR_M1\r
Release,5\r
Institution_Name,Celus\r
Institution_ID,ISNI:0000000000000000\r
Metric_Types,\r
Report_Filters,\r
Report_Attributes,\r
Exceptions,\r
Reporting_Period,Begin_Date=2020-02-01; End_Date=2020-02-29\r
Created,2024-01-01T00:00:00Z\r
Created_By,Celus X.Y.Z\r
\r
Item,Publisher,Publisher_ID,Platform,DOI,Proprietary_ID,URI,Metric_Type,Reporting_Period_Total,Feb-2020\r
target1,Pub1,,Plat1,10.4324/9781003185581,,,Total_Item_Requests,1,1\r
target1,Pub1,,Plat1,10.4324/9781003185581,,,No_License,3,3\r
target2,Pub1,,Plat1,,,,Total_Item_Requests,23,23\r
target2,Pub1,,Plat1,,,,No_License,29,29\r
"""
        )

    def test_no_months(
        self,
        organization,
        platform,
        ir_m1,
        ir_m1_ibs,
        settings,
        clickhouse_db,
    ):
        settings.CLICKHOUSE_SYNC_ACTIVE = True
        settings.CELUS_VERSION = "X.Y.Z"
        sync_import_batches_with_clickhouse(*ir_m1_ibs)

        export = IR_M1Counter5Export(organization, platform, ir_m1, None, None)

        assert (
            fixed_created("".join(export.csv()))
            == """\
Report_Name,Multimedia Item Requests\r
Report_ID,IR_M1\r
Release,5\r
Institution_Name,Celus\r
Institution_ID,ISNI:0000000000000000\r
Metric_Types,\r
Report_Filters,\r
Report_Attributes,\r
Exceptions,\r
Reporting_Period,Begin_Date=2019-12-01; End_Date=2021-01-31\r
Created,2024-01-01T00:00:00Z\r
Created_By,Celus X.Y.Z\r
\r
Item,Publisher,Publisher_ID,Platform,DOI,Proprietary_ID,URI,Metric_Type,Reporting_Period_Total,Dec-2019,Jan-2020,Feb-2020,Mar-2020,Apr-2020,May-2020,Jun-2020,Jul-2020,Aug-2020,Sep-2020,Oct-2020,Nov-2020,Dec-2020,Jan-2021\r
target1,Pub1,,Plat1,10.4324/9781003185581,,,Total_Item_Requests,36,11,0,1,0,5,0,0,0,0,0,0,0,0,19\r
target1,Pub1,,Plat1,10.4324/9781003185581,,,No_License,40,13,0,3,0,7,0,0,0,0,0,0,0,0,17\r
target2,Pub1,,Plat1,,,,Total_Item_Requests,23,0,0,23,0,0,0,0,0,0,0,0,0,0,0\r
target2,Pub1,,Plat1,,,,No_License,29,0,0,29,0,0,0,0,0,0,0,0,0,0,0\r
target3,Pub1,,Plat1,,,,Total_Item_Requests,31,0,0,0,0,31,0,0,0,0,0,0,0,0,0\r
target3,Pub1,,Plat1,,,,No_License,37,0,0,0,0,37,0,0,0,0,0,0,0,0,0\r
"""
        )

    def test_empty(
        self,
        organization,
        platform,
        ir_m1,
        settings,
        clickhouse_db,
    ):
        settings.CLICKHOUSE_SYNC_ACTIVE = True
        export = IR_M1Counter5Export(organization, platform, ir_m1, None, None)
        content = "".join(export.csv()).splitlines()
        end_date = month_end(date.today()).strftime("%Y-%m-%d")
        assert content[1] == "Report_ID,IR_M1"
        assert content[9] == f"Reporting_Period,Begin_Date=1970-01-01; End_Date={end_date}"
        assert content[-1].startswith("Item")

    def test_errors(
        self,
        organization,
        platform,
        ir_m1,
        ir_m1_ibs,
        settings,
        clickhouse_db,
        caplog,
    ):
        ir_m1_ibs[0].accesslog_set.update(target_id=None)
        settings.CLICKHOUSE_SYNC_ACTIVE = True

        sync_import_batches_with_clickhouse(*ir_m1_ibs)

        export = IR_M1Counter5Export(organization, platform, ir_m1, None, None)

        "".join(export.csv())
        assert caplog.records[-1].msg == "There are structural errors in the data"
