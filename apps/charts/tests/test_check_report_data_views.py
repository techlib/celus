import pytest
from django.core.management import call_command
from logs.fake_data import DimensionFactory
from logs.models import Dimension, ReportType

from charts.fake_data import ChartDefinitionFactory
from charts.models import (
    COUNTER_REPORT_DATA_VIEWS,
    DimensionFilter,
    ReportDataView,
    ReportViewToChartType,
)


@pytest.mark.django_db
class TestCheckReportDataViews:
    @pytest.mark.parametrize(
        "items_enabled,count",
        ((True, len(COUNTER_REPORT_DATA_VIEWS)), (False, len(COUNTER_REPORT_DATA_VIEWS) - 4)),
    )
    def test_trigger(self, settings, items_enabled, count):
        settings.ENABLE_ITEMS = items_enabled
        ChartDefinitionFactory(is_generic=True)
        assert ReportViewToChartType.objects.count() == 0

        assert ReportType.objects.count() == 0, "no report types"
        assert ReportDataView.objects.count() == 0, "no report data views"

        # prereq
        call_command("check_report_type_dimensions", "--fix-it")
        call_command("check_report_data_views", "--fix-it")

        assert ReportDataView.objects.count() == count
        assert ReportViewToChartType.objects.count() == 0

        jr1_rdv = ReportDataView.objects.get(short_name="JR1")
        assert jr1_rdv.metric_allowed_values == []
        assert jr1_rdv.dimension_filters.count() == 0

        tr_jr1_rdv = ReportDataView.objects.get(
            base_report_type__short_name="TR", short_name="TR_J1"
        )
        assert tr_jr1_rdv.metric_allowed_values == ["Total_Item_Requests", "Unique_Item_Requests"]
        assert tr_jr1_rdv.dimension_filters.count() == 3

        dr_d1_rdv = ReportDataView.objects.get(
            base_report_type__short_name="DR51", short_name="DR_D1"
        )
        assert dr_d1_rdv.metric_allowed_values == [
            "Searches_Automated",
            "Searches_Federated",
            "Searches_Regular",
            "Total_Item_Investigations",
            "Total_Item_Requests",
            "Unique_Item_Investigations",
            "Unique_Item_Requests",
        ]
        assert dr_d1_rdv.dimension_filters.count() == 1

        # update of dimension filters
        extra_dim = DimensionFactory()
        tr_jr1_rdv.dimension_filters.last().delete()
        DimensionFilter.objects.create(
            dimension=extra_dim, report_data_view=tr_jr1_rdv, allowed_values=["X1", "X2"]
        )
        DimensionFilter.objects.create(
            dimension=extra_dim, report_data_view=dr_d1_rdv, allowed_values=["X1", "X2"]
        )
        assert tr_jr1_rdv.dimension_filters.count() == 3
        assert dr_d1_rdv.dimension_filters.count() == 2

        call_command("check_report_data_views", "--fix-it")
        assert ReportViewToChartType.objects.count() == 0
        tr_jr1_rdv.refresh_from_db()
        dr_d1_rdv.refresh_from_db()
        assert tr_jr1_rdv.dimension_filters.count() == 3
        assert dr_d1_rdv.dimension_filters.count() == 1
        assert not tr_jr1_rdv.dimension_filters.filter(dimension=extra_dim).exists()
        assert not dr_d1_rdv.dimension_filters.filter(dimension=extra_dim).exists()

    def test_c5_to_c51_charts(self, settings):
        settings.ENABLE_ITEMS = False
        ChartDefinitionFactory(is_generic=True)
        chart1 = ChartDefinitionFactory(is_generic=False)
        chart2 = ChartDefinitionFactory(is_generic=False)
        chart3 = ChartDefinitionFactory(is_generic=False)
        chart4 = ChartDefinitionFactory(is_generic=False)
        chart5 = ChartDefinitionFactory(is_generic=False)

        # prereq
        call_command("check_report_type_dimensions", "--fix-it")
        call_command("check_report_data_views", "--fix-it")

        # section type was dropped in C5.1, so we test that it is not linked from TR to TR51
        section_type = Dimension.objects.filter(short_name="Section_Type").first()
        chart_section_type = ChartDefinitionFactory(
            is_generic=True, primary_dimension=section_type, primary_implicit_dimension=None
        )

        assert ReportDataView.objects.count() == 38
        assert ReportViewToChartType.objects.count() == 0

        tr = ReportDataView.objects.get(base_report_type__short_name="TR", short_name="TR")
        tr51 = ReportDataView.objects.get(base_report_type__short_name="TR51", short_name="TR")
        tr_j1 = ReportDataView.objects.get(base_report_type__short_name="TR", short_name="TR_J1")
        tr51_j1 = ReportDataView.objects.get(
            base_report_type__short_name="TR51", short_name="TR_J1"
        )
        jr1 = ReportDataView.objects.get(base_report_type__short_name="JR1")

        ReportViewToChartType.objects.create(
            report_data_view=tr, chart_definition=chart1, position=0
        )
        ReportViewToChartType.objects.create(
            report_data_view=tr, chart_definition=chart_section_type, position=1
        )
        ReportViewToChartType.objects.create(
            report_data_view=tr51, chart_definition=chart2, position=0
        )
        ReportViewToChartType.objects.create(
            report_data_view=jr1, chart_definition=chart3, position=0
        )
        ReportViewToChartType.objects.create(
            report_data_view=tr_j1, chart_definition=chart1, position=1
        )
        ReportViewToChartType.objects.create(
            report_data_view=tr_j1, chart_definition=chart4, position=0
        )
        ReportViewToChartType.objects.create(
            report_data_view=tr51_j1, chart_definition=chart5, position=0
        )
        assert ReportViewToChartType.objects.count() == 7

        call_command("link_charts_for_c51_based_on_c5", "--fix-it")

        assert ReportDataView.objects.count() == 38
        assert ReportViewToChartType.objects.count() == 10

        tr.refresh_from_db()
        tr51.refresh_from_db()
        tr_j1.refresh_from_db()
        tr51_j1.refresh_from_db()
        jr1.refresh_from_db()

        assert [e.chart_definition for e in tr.reportviewtocharttype_set.order_by("position")] == [
            chart1,
            chart_section_type,
        ]
        assert [
            e.chart_definition for e in tr51.reportviewtocharttype_set.order_by("position")
        ] == [chart2, chart1], "chart_section_type should not be copied"
        assert [
            e.chart_definition for e in tr_j1.reportviewtocharttype_set.order_by("position")
        ] == [chart4, chart1]
        assert [
            e.chart_definition for e in tr51_j1.reportviewtocharttype_set.order_by("position")
        ] == [chart5, chart4, chart1]
        assert [e.chart_definition for e in jr1.reportviewtocharttype_set.order_by("position")] == [
            chart3
        ]
