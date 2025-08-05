import pytest
from django.core.management import call_command
from sushi.fake_data import CounterReportTypeFactory
from sushi.models import COUNTER_REPORTS, CounterVersionChoices

from logs.models import ReportType


@pytest.mark.django_db
class TestCheckReportTypeDimensions:
    def test_with_items_enabled(self, settings):
        settings.ENABLE_ITEMS = True
        assert ReportType.objects.count() == 0, "no report types"
        call_command("check_report_type_dimensions", "--fix-it")
        assert ReportType.objects.count() == len(COUNTER_REPORTS), "all counter report types added"
        assert not ReportType.objects.filter(short_name="IR").exists(), (
            "IR not added (excluded for C5)"
        )
        assert ReportType.objects.filter(short_name="IR51").exists(), "IR51 added"
        assert ReportType.objects.get(short_name="IR51").uses_items
        assert ReportType.objects.get(short_name="IR51").uses_titles
        assert not ReportType.objects.get(short_name="TR51").uses_items
        assert ReportType.objects.get(short_name="TR51").uses_titles
        assert not ReportType.objects.get(short_name="TR").uses_items
        assert ReportType.objects.get(short_name="TR").uses_titles
        assert not ReportType.objects.get(short_name="IR_M1").uses_titles
        assert ReportType.objects.get(short_name="IR_M1").uses_items
        assert all(
            ReportType.objects.filter(short_name__in=["IR51", "IR_M1"]).values_list(
                "uses_items", flat=True
            )
        ), "only IR_M1 and IR51 use items"
        assert not any(
            ReportType.objects.exclude(short_name__in=["IR51", "IR_M1"]).values_list(
                "uses_items", flat=True
            )
        ), "others should not use items"

        assert not any(
            ReportType.objects.filter(short_name__in=["PR", "PR1", "PR51", "IR_M1"]).values_list(
                "uses_titles", flat=True
            )
        ), "PR, PR1 and IR_M1 should not use titles"
        assert all(
            ReportType.objects.exclude(short_name__in=["PR", "PR1", "PR51", "IR_M1"]).values_list(
                "uses_titles", flat=True
            )
        ), "others should use titles"

    def test_with_items_disabled(self, settings):
        settings.ENABLE_ITEMS = False
        assert ReportType.objects.count() == 0, "no report types"
        call_command("check_report_type_dimensions", "--fix-it")
        assert ReportType.objects.count() == len(COUNTER_REPORTS) - 1, "IR51 not added"
        assert not ReportType.objects.filter(short_name="IR").exists(), (
            "IR not added (excluded for C5)"
        )
        assert not ReportType.objects.filter(short_name="IR51").exists(), "IR51 not added"
        assert not ReportType.objects.get(short_name="TR51").uses_items
        assert ReportType.objects.get(short_name="TR51").uses_titles
        assert not ReportType.objects.get(short_name="TR").uses_items
        assert ReportType.objects.get(short_name="TR").uses_titles
        assert not ReportType.objects.get(short_name="IR_M1").uses_titles
        assert ReportType.objects.get(short_name="IR_M1").uses_items
        assert all(
            ReportType.objects.filter(short_name__in=["IR51", "IR_M1"]).values_list(
                "uses_items", flat=True
            )
        ), "only IR_M1 and IR51 use items"
        assert not any(
            ReportType.objects.exclude(short_name__in=["IR51", "IR_M1"]).values_list(
                "uses_items", flat=True
            )
        ), "others should not use items"

        assert not any(
            ReportType.objects.filter(short_name__in=["PR", "PR1", "PR51", "IR_M1"]).values_list(
                "uses_titles", flat=True
            )
        ), "PR, PR1 and IR_M1 should not use titles"
        assert all(
            ReportType.objects.exclude(short_name__in=["PR", "PR1", "PR51", "IR_M1"]).values_list(
                "uses_titles", flat=True
            )
        ), "others should use titles"

    def test_metric_order_c5_c51(self):
        CounterReportTypeFactory(
            counter_version=CounterVersionChoices.C5,
            code="TR",
            report_type__dimensions=[  # order should be somehow mixed
                "Access_Method",
                "YOP",
                "Data_Type",
                "Publisher",
                "Section_Type",
                "Platform",
                "Access_Type",
            ],
        )
        CounterReportTypeFactory(
            counter_version=CounterVersionChoices.C5,
            code="DR",
            report_type__dimensions=[  # order should be somehow mixed
                "Platform",
                "Data_Type",
                "Access_Method",
                "Publisher",
            ],
        )
        CounterReportTypeFactory(
            counter_version=CounterVersionChoices.C5,
            code="PR",
            report_type__dimensions=[  # order should be somehow mixed
                "Data_Type",
                "Platform",
                "Access_Method",
            ],
        )
        call_command("check_report_type_dimensions", "--fix-it")

        tr_51 = ReportType.objects.get(short_name="TR51")
        dr_51 = ReportType.objects.get(short_name="DR51")
        pr_51 = ReportType.objects.get(short_name="PR51")

        assert list(
            tr_51.reporttypetodimension_set.order_by("position").values_list(
                "position", "dimension__short_name"
            )
        ) == [
            (0, "Access_Method"),
            (1, "YOP"),
            (2, "Data_Type"),
            (3, "Publisher"),
            (4, "Platform"),
            (5, "Access_Type"),
        ], "No hole is created last two dimensions are moved for TR"

        assert list(
            dr_51.reporttypetodimension_set.order_by("position").values_list(
                "position", "dimension__short_name"
            )
        ) == [(0, "Platform"), (1, "Data_Type"), (2, "Access_Method"), (3, "Publisher")]

        assert list(
            pr_51.reporttypetodimension_set.order_by("position").values_list(
                "position", "dimension__short_name"
            )
        ) == [(0, "Data_Type"), (1, "Platform"), (2, "Access_Method")]
