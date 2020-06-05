import pytest

from logs.tests.conftest import report_type_nd
from sushi.models import CounterReportType


@pytest.fixture()
def counter_report_type_named(report_type_nd):
    def fn(name):
        rt = report_type_nd(0, short_name=name + 'rt')
        return CounterReportType.objects.create(
            code=name, counter_version=5, name=name + ' title', report_type=rt
        )

    yield fn


@pytest.fixture()
def counter_report_type(report_type_nd):
    report_type = report_type_nd(0)
    yield CounterReportType.objects.create(
        code='TR', counter_version=5, name='Title report', report_type=report_type
    )
