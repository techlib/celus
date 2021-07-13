import pytest

from test_fixtures.scenarios.basic import *  # noqa
from organizations.tests.conftest import organization_random  # noqa - used by local tests
from logs.tests.conftest import flexible_slicer_test_data, report_type_nd  # noqa


@pytest.fixture
def root_platform(platforms):
    return platforms['root']


@pytest.fixture
def tr_report(report_types):
    return report_types['tr']
