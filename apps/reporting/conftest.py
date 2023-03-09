import pytest
from celus_nigiri.counter4 import Counter4JR1Report
from celus_nigiri.counter5 import Counter5TRReport
from logs.models import DimensionText
from publications.logic.fake_data import TitleFactory

from test_fixtures.entities.logs import ImportBatchFullFactory, MetricFactory
from test_fixtures.entities.organizations import OrganizationFactory
from test_fixtures.entities.platforms import PlatformFactory
from test_fixtures.entities.report_types import ReportTypeFactory

TEST_REPORT = {
    "name": "Test report",
    "description": "Test report description",
    "dataSources": [
        {
            "name": "tr",
            "reportType": "TR",
            "metric": "Unique_Item_Requests",
            "filters": {"Access_Method": "Regular"},
        },
        {
            "name": "jr1",
            "reportType": "JR1",
            "metric": "Full Text Article Requests",
            "fallbackFor": "tr",
        },
        {
            "name": "jr1goa",
            "reportType": "JR1GOA",
            "metric": "Full Text Article Requests",
            "fallbackFor": "tr",
        },
    ],
    "parts": [
        {
            "name": "PART 1",
            "description": "Whatever",
            "stages": [{"id": "part1", "name": "PART 1", "formula": "tr | (jr1 - jr1goa)"}],
        },
        {
            "name": "PART 2",
            "description": "Same as PART 1 but no subtracted fallback report",
            "stages": [{"id": "part2", "name": "PART 2", "formula": "tr | jr1"}],
        },
        {
            "name": "PART 3",
            "description": "Tests summation of reports",
            "stages": [
                {"id": "stage1", "name": "JR1 + GOA", "formula": "jr1 + jr1goa"},
                {"id": "tr_stage", "name": "TR", "formula": "tr"},
                {"id": "result", "name": "PART 3", "formula": "tr_stage | stage1"},
            ],
        },
        {
            "name": "PART 4",
            "description": "Tests clashing stage IDs",
            # the id of the first stage "clashes" with the stage of PART 3, but as part stages
            # should be evaluated independently, this should not be a problem.
            # In fact, this is what we want to test here.
            "stages": [
                {"id": "stage1", "name": "JR1 only", "formula": "jr1"},
                {"id": "tr_stage", "name": "TR", "formula": "tr"},
                {"id": "result", "name": "PART 4", "formula": "tr_stage | stage1"},
            ],
        },
    ],
}

# The final value is always a sum of the last stage

IPEDS = {
    "name": "IPEDS",
    "description": "IPEDS report",
    "dataSources": {
        "tr_b1": {
            "reportType": "TR",
            "metric": "Unique_Item_Requests",
            "filters": {"Access_Method": "Regular", "Data_Type": "Book"},
        },
        "ir_m1": {"reportType": "IR_M1", "metric": "Total_Item_Investigations"},
        "br1": {"reportType": "BR1", "metric": "Book Chapter Downloads", "fallbackFor": "tr_b1"},
        "br2": {"reportType": "BR2", "metric": "Book Chapter Downloads", "fallbackFor": "br1"},
        "mr1": {"reportType": "MR1", "metric": "Multimedia Downloads", "fallbackFor": "ir_m1"},
        "mr2": {"reportType": "MR2", "metric": "Multimedia Downloads", "fallbackFor": "mr1"},
        "tr_j": {
            "reportType": "TR",
            "metric": "Unique_Item_Requests",
            "filters": {
                "Access_Method": "Regular",
                "Access_Type": ["Controlled", "OA_Gold"],
                "Data_Type": "Journal",
            },
        },
        "jr1": {"reportType": "JR1", "metric": "Full Text Article Requests", "fallbackFor": "tr_j"},
    },
    "parts": [
        {
            "name": "60B",
            "description": "60B",
            "stages": [
                {"name": "TR_B1", "formula": "tr_b1"},
                {"name": "IR_M1", "formula": "ir_m1"},
                {"name": "60B", "formula": "TR_B1 + IR_M1"},
            ],
        },
        {
            "name": "61B",
            "description": "61B",
            "stages": [
                {"name": "BR1", "formula": "br1"},
                {"name": "MR1", "formula": "mr1"},
                {"name": "61B", "formula": "BR1 + MR1"},
            ],
        },
        {
            "name": "62B",
            "description": "62B",
            "stages": [
                {"name": "BR2", "formula": "br2"},
                {"name": "MR2", "formula": "mr2"},
                {"name": "62B", "formula": "BR2 + MR2"},
            ],
        },
        {
            "name": "63B",
            "description": "63B",
            "stages": [
                {"id": "TR_J", "name": "TR_J1+GOA", "formula": "tr_j"},
                {"name": "JR1", "formula": "jr1"},
                {"name": "63B", "formula": "TR_J | JR1"},
            ],
        },
    ],
}


@pytest.fixture()
def report_data_tr_jr1():
    rt_tr = ReportTypeFactory(short_name="TR", dimensions=Counter5TRReport.dimensions)
    rt_jr1 = ReportTypeFactory(short_name="JR1", dimensions=Counter4JR1Report.dimensions)
    rt_jr1goa = ReportTypeFactory(short_name="JR1GOA", dimensions=Counter4JR1Report.dimensions)
    org = OrganizationFactory()
    platform1 = PlatformFactory(name="A")  # this will have TR data
    platform2 = PlatformFactory(name="B")  # this will have JR1 data
    metric_tr1 = MetricFactory(short_name="Unique_Item_Requests")
    metric_jr1 = MetricFactory(short_name="Full Text Article Requests")
    # dimensions
    dim_am_idx, dim_am = [
        (i, dim)
        for i, dim in enumerate(rt_tr.dimensions_sorted)
        if dim.short_name == "Access_Method"
    ][0]
    val_regular_text = DimensionText.objects.create(dimension=dim_am, text="Regular")
    titles = TitleFactory.create_batch(3)
    # create import batches for 12 months in 2022
    for month_num in range(12):
        month = f"2022-{month_num + 1:02d}-01"
        ImportBatchFullFactory(
            organization=org,
            report_type=rt_tr,
            date=month,
            platform=platform1,
            create_accesslogs__metrics=[metric_tr1],
            create_accesslogs__titles=titles,
            create_accesslogs__value=100,
            **{f'create_accesslogs__dim{dim_am_idx + 1}': val_regular_text.pk},
        )
        ImportBatchFullFactory(
            organization=org,
            report_type=rt_jr1,
            date=month,
            platform=platform2,
            create_accesslogs__metrics=[metric_jr1],
            create_accesslogs__titles=titles,
            create_accesslogs__value=10,
        )
        ImportBatchFullFactory(
            organization=org,
            report_type=rt_jr1goa,
            date=month,
            platform=platform2,
            create_accesslogs__metrics=[metric_jr1],
            create_accesslogs__titles=titles,
            create_accesslogs__value=month_num + 1,
        )
    return locals()


@pytest.fixture
def report_def_tr_jr1():
    return TEST_REPORT
