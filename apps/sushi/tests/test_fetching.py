from copy import deepcopy

import pytest
from celus_nigiri.client import Sushi5Client
from celus_nigiri.counter5 import Counter5ReportBase
from logs.tests.conftest import report_type_nd  # noqa - fixture
from organizations.tests.conftest import organizations  # noqa - fixture
from publications.models import Platform

from sushi.logic.data_import import import_sushi_credentials_new
from sushi.models import CounterReportType, SushiCredentials


@pytest.mark.django_db
class TestURLComposition:
    def test_extra_params_is_not_polluted_by_extra_data(
        self, organizations, report_type_nd, monkeypatch, counter5_version
    ):
        assert SushiCredentials.objects.count() == 0
        data = [
            {
                "organization": organizations[1].internal_id,
                "publisher/vendor/platform": "XXXX",
                "requestor id": "RRRX",
                "customer id": "BBB",
                "api key": "kekekeyyy",
            }
        ]
        knowledgebase = {
            "providers": [
                {"counter_version": counter5_version, "provider": {"url": "http://this.is/test/2"}}
            ]
        }
        Platform.objects.create(short_name="XXX", name_en="XXXX", knowledgebase=knowledgebase)
        stats = import_sushi_credentials_new(data, counter_version=counter5_version)
        assert stats["added"] == 1
        assert SushiCredentials.objects.count() == 1
        credentials = SushiCredentials.objects.all()
        # let's create
        cr1 = credentials[0]
        cr1.create_sushi_client()
        report = CounterReportType.objects.create(
            code="tr", name="tr", counter_version=counter5_version, report_type=report_type_nd(0)
        )
        orig_params = deepcopy(counter5_version.nigiri.get_report_class("tr").extra_params)

        def mock_get_report_data(*args, **kwargs):
            return Counter5ReportBase()

        monkeypatch.setattr(Sushi5Client, "get_report_data", mock_get_report_data)
        cr1.fetch_report(report, start_date="2020-01-01", end_date="2020-01-31")
        assert orig_params == counter5_version.nigiri.get_report_class("tr").extra_params
