from copy import deepcopy

import pytest

from nigiri.counter5 import Counter5ReportBase

from nigiri.client import Sushi5Client
from publications.models import Platform
from sushi.logic.data_import import import_sushi_credentials
from sushi.models import SushiCredentials, CounterReportType
from organizations.tests.conftest import organizations
from logs.tests.conftest import report_type_nd


@pytest.mark.django_db
class TestURLComposition(object):
    def test_extra_params_is_not_polluted_by_extra_data(
        self, organizations, report_type_nd, monkeypatch
    ):
        assert SushiCredentials.objects.count() == 0
        data = [
            {
                'platform': 'XXX',
                'organization': organizations[1].internal_id,
                'customer_id': 'BBB',
                'requestor_id': 'RRRX',
                'URL': 'http://this.is/test/2',
                'version': 5,
                'extra_attrs': 'auth=un,pass;api_key=kekekeyyy;foo=bar',
            },
        ]
        Platform.objects.create(short_name='XXX', name='XXXX', ext_id=10)
        stats = import_sushi_credentials(data)
        assert stats['added'] == 1
        assert SushiCredentials.objects.count() == 1
        credentials = SushiCredentials.objects.all()
        # let's create
        cr1 = credentials[0]
        cr1.create_sushi_client()
        report = CounterReportType.objects.create(
            code='tr', name='tr', counter_version=5, report_type=report_type_nd(0)
        )
        orig_params = deepcopy(Sushi5Client.EXTRA_PARAMS)

        def mock_get_report_data(*args, **kwargs):
            return Counter5ReportBase()

        monkeypatch.setattr(Sushi5Client, 'get_report_data', mock_get_report_data)
        cr1.fetch_report(report, start_date='2020-01-01', end_date='2020-01-31')
        assert orig_params == Sushi5Client.EXTRA_PARAMS
