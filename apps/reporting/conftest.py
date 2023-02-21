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
    "parts": [
        {
            "name": "PART 1",
            "description": "Whatever",
            "mainReportDefinition": {
                "reportType": "TR",
                "metric": "Unique_Item_Requests",
                "filters": {"Access_Method": "Regular"},
            },
            "fallbackReportDefinition": {
                "reportType": "JR1",
                "metric": "Full Text Article Requests",
            },
            "subtractedFallbackReportDefinition": {
                "reportType": "JR1GOA",
                "metric": "Full Text Article Requests",
            },
        },
        {
            "name": "PART 2",
            "description": "Same as PART 1 but no subtracted fallback report",
            "mainReportDefinition": {
                "reportType": "TR",
                "metric": "Unique_Item_Requests",
                "filters": {"Access_Method": "Regular"},
            },
            "fallbackReportDefinition": {
                "reportType": "JR1",
                "metric": "Full Text Article Requests",
            },
        },
    ],
}


@pytest.fixture()
def report_data_tr_jr1():
    rt_tr = ReportTypeFactory(short_name="TR", dimensions=Counter5TRReport.dimensions)
    rt_jr1 = ReportTypeFactory(short_name="JR1", dimensions=Counter4JR1Report.dimensions)
    rt_jr1goa = ReportTypeFactory(short_name="JR1GOA", dimensions=Counter4JR1Report.dimensions)
    org = OrganizationFactory()
    platform1 = PlatformFactory()  # this will have TR data
    platform2 = PlatformFactory()  # this will have JR1 data
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
            create_accesslogs__value=5,
        )
    return locals()


@pytest.fixture
def report_def_tr_jr1():
    return TEST_REPORT
