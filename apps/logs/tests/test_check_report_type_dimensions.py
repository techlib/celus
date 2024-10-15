import pytest
from django.core.management import call_command
from sushi.models import COUNTER_REPORTS

from logs.models import ReportType


@pytest.mark.django_db
class TestCheckReportTypeDimensions:
    def test_with_items_enabled(self, settings):
        settings.ENABLE_ITEMS = True
        assert ReportType.objects.count() == 0, "no report types"
        call_command("check_report_type_dimensions", "--fix-it")
        assert ReportType.objects.count() == len(COUNTER_REPORTS), "all counter report types added"
        assert ReportType.objects.filter(short_name="IR").exists(), "IR added"

    def test_with_items_disabled(self, settings):
        settings.ENABLE_ITEMS = False
        assert ReportType.objects.count() == 0, "no report types"
        call_command("check_report_type_dimensions", "--fix-it")
        assert ReportType.objects.count() == len(COUNTER_REPORTS) - 1, "IR not added"
        assert not ReportType.objects.filter(short_name="IR").exists(), "IR not added"
