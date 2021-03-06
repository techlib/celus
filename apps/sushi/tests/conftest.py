import pytest

from core.models import UL_ORG_ADMIN
from logs.tests.conftest import report_type_nd
from sushi.models import CounterReportType, SushiCredentials


@pytest.fixture()
def counter_report_type_named(report_type_nd):
    def fn(name, version=5):
        rt = report_type_nd(0, short_name=name + 'rt')
        return CounterReportType.objects.create(
            code=name, counter_version=version, name=name + ' title', report_type=rt
        )

    yield fn


@pytest.fixture()
def counter_report_type(report_type_nd):
    report_type = report_type_nd(0)
    yield CounterReportType.objects.create(
        code='TR', counter_version=5, name='Title report', report_type=report_type
    )


@pytest.fixture()
def credentials(organizations, platforms):
    credentials = SushiCredentials.objects.create(
        organization=organizations[0],
        platform=platforms[0],
        counter_version=5,
        lock_level=UL_ORG_ADMIN,
        url='http://a.b.c/',
    )
    yield credentials
