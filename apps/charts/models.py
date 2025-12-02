import typing
from dataclasses import dataclass, field

from core.models import DataSource
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from logs.models import AccessLog, Dimension, DimensionText, ReportType


@dataclass
class CounterDimensionFilter:
    dimension: str
    allowed_values: typing.List[str]


@dataclass
class CounterReportDataView:
    base_report_type_short_name: str
    short_name: str
    is_standard_view: bool
    position: int
    name: str = ""
    name_en: str = ""
    name_cs: str = ""
    desc: str = ""
    desc_en: str = ""
    desc_cs: str = ""
    metric_allowed_values: typing.List[str] = field(default_factory=lambda: [])
    filters: typing.List[CounterDimensionFilter] = field(default_factory=lambda: [])


COUNTER_REPORT_DATA_VIEWS = [
    # Counter 4
    CounterReportDataView("JR1", "JR1", False, 11, name="COUNTER 4 - Journal Report 1"),
    CounterReportDataView("JR1a", "JR1a", False, 12, name="COUNTER 4 - Journal Report 1a"),
    CounterReportDataView("JR1GOA", "JR1GOA", False, 13, name="COUNTER 4 - Journal Report 1GOA"),
    CounterReportDataView("JR2", "JR2", False, 14, name="COUNTER 4 - Journal Report 2"),
    CounterReportDataView("BR1", "BR1", False, 15, name="COUNTER 4 - Book Report 1"),
    CounterReportDataView("BR2", "BR2", False, 16, name="COUNTER 4 - Book Report 2"),
    CounterReportDataView("BR3", "BR3", False, 17, name="COUNTER 4 - Book Report 3"),
    CounterReportDataView("DB1", "DB1", False, 18, name="COUNTER 4 - Database Report 1"),
    CounterReportDataView("DB2", "DB2", False, 19, name="COUNTER 4 - Database Report 2"),
    CounterReportDataView("PR1", "PR1", False, 20, name="COUNTER 4 - Platform Report 1"),
    CounterReportDataView("MR1", "MR1", False, 21, name="COUNTER 4 - Multimedia Report 1"),
    # Counter 5 PR
    CounterReportDataView(
        "PR",
        "PR_P1",
        True,
        50,
        name="COUNTER 5 - Platform Report 1",
        desc="Platform Usage",
        metric_allowed_values=[
            "Searches_Platform",
            "Total_Item_Requests",
            "Unique_Item_Requests",
            "Unique_Title_Requests",
        ],
        filters=[CounterDimensionFilter("Access_Method", ["Regular"])],
    ),
    CounterReportDataView(
        "PR",
        "PR",
        False,
        120,
        name="COUNTER 5 - Platform Report Full",
        desc="Platform Master Report",
    ),
    # Counter 5 DR
    CounterReportDataView(
        "DR",
        "DR_D1",
        True,
        30,
        name="COUNTER 5 - Database Report 1",
        desc="Database Search and Item Usage",
        metric_allowed_values=[
            "Searches_Automated",
            "Searches_Federated",
            "Searches_Regular",
            "Total_Item_Investigations",
            "Total_Item_Requests",
        ],
        filters=[CounterDimensionFilter("Access_Method", ["Regular"])],
    ),
    CounterReportDataView(
        "DR",
        "DR_D2",
        True,
        31,
        name="COUNTER 5 - Database Report 2",
        desc="Database Access Denied",
        metric_allowed_values=["Limit_Exceeded", "No_License"],
        filters=[CounterDimensionFilter("Access_Method", ["Regular"])],
    ),
    CounterReportDataView(
        "DR",
        "DR",
        False,
        110,
        name="COUNTER 5 - Database Report Full",
        desc="Database Master Report",
    ),
    # Counter 5 TR
    CounterReportDataView(
        "TR",
        "TR_J1",
        True,
        10,
        name="COUNTER 5 - Journal Report 1",
        desc="Journal Requests (Excluding OA_Gold)",
        metric_allowed_values=["Total_Item_Requests", "Unique_Item_Requests"],
        filters=[
            CounterDimensionFilter("Data_Type", ["Journal"]),
            CounterDimensionFilter("Access_Type", ["Controlled"]),
            CounterDimensionFilter("Access_Method", ["Regular"]),
        ],
    ),
    CounterReportDataView(
        "TR",
        "TR_J2",
        True,
        11,
        name="COUNTER 5 - Journal Report 2",
        desc="Journal Access Denied",
        metric_allowed_values=["No_License", "Limit_Exceeded"],
        filters=[
            CounterDimensionFilter("Data_Type", ["Journal"]),
            CounterDimensionFilter("Access_Method", ["Regular"]),
        ],
    ),
    CounterReportDataView(
        "TR",
        "TR_J3",
        True,
        12,
        name="COUNTER 5 - Journal Report 3",
        desc="Journal Usage by Access Type",
        metric_allowed_values=[
            "Total_Item_Investigations",
            "Total_Item_Requests",
            "Unique_Item_Investigations",
            "Unique_Item_Requests",
        ],
        filters=[
            CounterDimensionFilter("Data_Type", ["Journal"]),
            CounterDimensionFilter("Access_Method", ["Regular"]),
        ],
    ),
    CounterReportDataView(
        "TR",
        "TR_J4",
        True,
        13,
        name="COUNTER 5 - Journal Report 4",
        desc="Journal Requests by YOP (Excluding OA_Gold)",
        metric_allowed_values=["Total_Item_Requests", "Unique_Item_Requests"],
        filters=[
            CounterDimensionFilter("Data_Type", ["Journal"]),
            CounterDimensionFilter("Access_Type", ["Controlled"]),
            CounterDimensionFilter("Access_Method", ["Regular"]),
        ],
    ),
    CounterReportDataView(
        "TR",
        "TR_B1",
        True,
        20,
        name="COUNTER 5 - Book Report 1",
        desc="Book Requests (Excluding OA_Gold)",
        metric_allowed_values=["Total_Item_Requests", "Unique_Title_Requests"],
        filters=[
            CounterDimensionFilter("Data_Type", ["Book"]),
            CounterDimensionFilter("Access_Type", ["Controlled"]),
            CounterDimensionFilter("Access_Method", ["Regular"]),
        ],
    ),
    CounterReportDataView(
        "TR",
        "TR_B2",
        True,
        21,
        name="COUNTER 5 - Book Report 2",
        desc="Book Access Denied",
        metric_allowed_values=["Limit_Exceeded", "No_License"],
        filters=[
            CounterDimensionFilter("Data_Type", ["Book"]),
            CounterDimensionFilter("Access_Method", ["Regular"]),
        ],
    ),
    CounterReportDataView(
        "TR",
        "TR_B3",
        True,
        22,
        name="COUNTER 5 - Book Report 3",
        desc="Book Usage by Access Type",
        metric_allowed_values=[
            "Total_Item_Investigations",
            "Total_Item_Requests",
            "Unique_Item_Investigations",
            "Unique_Item_Requests",
            "Unique_Title_Investigations",
            "Unique_Title_Requests",
        ],
        filters=[
            CounterDimensionFilter("Data_Type", ["Book"]),
            CounterDimensionFilter("Access_Method", ["Regular"]),
        ],
    ),
    CounterReportDataView(
        "TR", "TR", False, 100, name="COUNTER 5 - Title Report Full", desc="Title Master Report"
    ),
    # Counter 5 IR_M1
    CounterReportDataView(
        "IR_M1",
        "IR_M1",
        True,
        100,
        name="COUNTER 5 - Multimedia Report 1",
        desc="Multimedia Item Requests",
        metric_allowed_values=["Total_Item_Requests"],
        filters=[],  # No filter because IR_M1 should be already filtered
    ),
    # Counter 5.1 PR
    CounterReportDataView(
        "PR51",
        "PR_P1",
        True,
        50,
        name="COUNTER 5.1 - Platform Report 1",
        desc="Platform Usage",
        metric_allowed_values=[
            "Searches_Platform",
            "Total_Item_Requests",
            "Unique_Item_Requests",
            "Unique_Title_Requests",
        ],
        filters=[CounterDimensionFilter("Access_Method", ["Regular"])],
    ),
    CounterReportDataView(
        "PR51", "PR", False, 120, name="COUNTER 5.1 - Platform Report Full", desc="Platform Report"
    ),
    # Counter 5.1 DR
    CounterReportDataView(
        "DR51",
        "DR_D1",
        True,
        30,
        name="COUNTER 5.1 - Database Report 1",
        desc="Database Search and Item Usage",
        metric_allowed_values=[
            "Searches_Automated",
            "Searches_Federated",
            "Searches_Regular",
            "Total_Item_Investigations",
            "Total_Item_Requests",
            "Unique_Item_Investigations",
            "Unique_Item_Requests",
        ],
        filters=[CounterDimensionFilter("Access_Method", ["Regular"])],
    ),
    CounterReportDataView(
        "DR51",
        "DR_D2",
        True,
        31,
        name="COUNTER 5.1 - Database Report 2",
        desc="Database Access Denied",
        metric_allowed_values=["Limit_Exceeded", "No_License"],
        filters=[CounterDimensionFilter("Access_Method", ["Regular"])],
    ),
    CounterReportDataView(
        "DR51", "DR", False, 110, name="COUNTER 5.1 - Database Report Full", desc="Database Report"
    ),
    # Counter 5.1 TR
    CounterReportDataView(
        "TR51",
        "TR_J1",
        True,
        10,
        name="COUNTER 5.1 - Journal Report 1",
        desc="Journal Requests (Controlled)",
        metric_allowed_values=["Total_Item_Requests", "Unique_Item_Requests"],
        filters=[
            CounterDimensionFilter("Data_Type", ["Journal"]),
            CounterDimensionFilter("Access_Type", ["Controlled"]),
            CounterDimensionFilter("Access_Method", ["Regular"]),
        ],
    ),
    CounterReportDataView(
        "TR51",
        "TR_J2",
        True,
        11,
        name="COUNTER 5.1 - Journal Report 2",
        desc="Journal Access Denied",
        metric_allowed_values=["No_License", "Limit_Exceeded"],
        filters=[
            CounterDimensionFilter("Data_Type", ["Journal"]),
            CounterDimensionFilter("Access_Method", ["Regular"]),
        ],
    ),
    CounterReportDataView(
        "TR51",
        "TR_J3",
        True,
        12,
        name="COUNTER 5.1 - Journal Report 3",
        desc="Journal Usage by Access Type",
        metric_allowed_values=[
            "Total_Item_Investigations",
            "Total_Item_Requests",
            "Unique_Item_Investigations",
            "Unique_Item_Requests",
        ],
        filters=[
            CounterDimensionFilter("Data_Type", ["Journal"]),
            CounterDimensionFilter("Access_Method", ["Regular"]),
        ],
    ),
    CounterReportDataView(
        "TR51",
        "TR_J4",
        True,
        13,
        name="COUNTER 5.1 - Journal Report 4",
        desc="Journal Requests by YOP (Controlled)",
        metric_allowed_values=["Total_Item_Requests", "Unique_Item_Requests"],
        filters=[
            CounterDimensionFilter("Data_Type", ["Journal"]),
            CounterDimensionFilter("Access_Type", ["Controlled"]),
            CounterDimensionFilter("Access_Method", ["Regular"]),
        ],
    ),
    CounterReportDataView(
        "TR51",
        "TR_B1",
        True,
        20,
        name="COUNTER 5.1 - Book Report 1",
        desc="Book Requests (Controlled)",
        metric_allowed_values=["Total_Item_Requests", "Unique_Title_Requests"],
        filters=[
            CounterDimensionFilter("Data_Type", ["Book", "Reference_Work"]),
            CounterDimensionFilter("Access_Type", ["Controlled"]),
            CounterDimensionFilter("Access_Method", ["Regular"]),
        ],
    ),
    CounterReportDataView(
        "TR51",
        "TR_B2",
        True,
        21,
        name="COUNTER 5.1 - Book Report 2",
        desc="Book Access Denied",
        metric_allowed_values=["Limit_Exceeded", "No_License"],
        filters=[
            CounterDimensionFilter("Data_Type", ["Book", "Reference_Work"]),
            CounterDimensionFilter("Access_Method", ["Regular"]),
        ],
    ),
    CounterReportDataView(
        "TR51",
        "TR_B3",
        True,
        22,
        name="COUNTER 5.1 - Book Report 3",
        desc="Book Usage by Access Type",
        metric_allowed_values=[
            "Total_Item_Investigations",
            "Total_Item_Requests",
            "Unique_Item_Investigations",
            "Unique_Item_Requests",
            "Unique_Title_Investigations",
            "Unique_Title_Requests",
        ],
        filters=[
            CounterDimensionFilter("Data_Type", ["Book", "Reference_Work"]),
            CounterDimensionFilter("Access_Method", ["Regular"]),
        ],
    ),
    CounterReportDataView(
        "TR51", "TR", False, 100, name="COUNTER 5.1 - Title Report Full", desc="Title Report"
    ),
    # Counter 5.1 IR
    CounterReportDataView(
        "IR51",
        "IR_A1",
        True,
        100,
        name="COUNTER 5.1 - Article Report 1",
        desc="Journal Article Requests",
        metric_allowed_values=["Total_Item_Requests", "Unique_Items_Requests"],
        filters=[
            CounterDimensionFilter("Data_Type", ["Article"]),
            CounterDimensionFilter("Access_Method", ["Regular"]),
        ],
    ),
    CounterReportDataView(
        "IR51",
        "IR_M1",
        True,
        101,
        name="COUNTER 5.1 - Multimedia Report 1",
        desc="Multimedia Item Requests - computed from full IR report",
        metric_allowed_values=["Total_Item_Requests", "Unique_Items_Requests"],
        filters=[
            CounterDimensionFilter(
                "Data_Type", ["Audiovisual", "Image", "Interactive_Resource", "Multimedia", "Sound"]
            ),
            CounterDimensionFilter("Access_Method", ["Regular"]),
        ],
    ),
    CounterReportDataView(
        "IR51_M1",
        "IR_M1",
        True,
        105,
        name="COUNTER 5.1 - Multimedia Report 1",
        desc="Multimedia Item Requests - standalone report",
    ),
    CounterReportDataView(
        "IR51", "IR", False, 120, name="COUNTER 5.1 - Item Report Full", desc="Item Report"
    ),
]


class ReportDataView(models.Model):
    """
    A view of the report type - it is used to expose a report type filtered in some way.
    This is the default object to be used to obtain data for charts.
    In the most trivial case, it does not do anything, just proxies the underlying report
    data.
    It is also the point which is used to attach chart params to the report
    """

    base_report_type = models.ForeignKey(ReportType, on_delete=models.CASCADE)
    short_name = models.CharField(max_length=100)
    name = models.CharField(max_length=250)
    desc = models.TextField(blank=True)
    source = models.ForeignKey(DataSource, on_delete=models.SET_NULL, null=True, blank=True)
    metric_allowed_values = models.JSONField(default=list, blank=True)
    is_standard_view = models.BooleanField(
        default=True, help_text="Standard view are shown separately from other views"
    )
    position = models.PositiveIntegerField(default=100)

    class Meta:
        ordering = ("short_name",)

    def __str__(self):
        return self.short_name

    @property
    def dimensions_sorted(self):
        return []

    @cached_property
    def accesslog_filters(self):
        filters = {}
        if self.metric_allowed_values:
            filters["metric__short_name__in"] = self.metric_allowed_values
        dim_filters = {df.dimension.pk: df.allowed_values for df in self.dimension_filters.all()}
        for i, dim in enumerate(self.base_report_type.dimensions_sorted):
            if dim.pk in dim_filters:
                allowed_values = dim_filters[dim.pk]
                values = [
                    dt.pk
                    for dt in DimensionText.objects.filter(dimension=dim, text__in=allowed_values)
                ]
                filters[f"dim{i + 1}__in"] = values
        return filters

    def logdata_qs(self):
        return AccessLog.objects.filter(
            report_type_id=self.base_report_type_id, **self.accesslog_filters
        ).values("organization", "metric", "platform", "target", "date")

    @property
    def public(self):
        return self.source is None

    @property
    def is_interest(self) -> bool:
        return self.base_report_type.short_name == "interest"

    @property
    def counter_version(self) -> typing.Optional[int]:
        try:
            return self.base_report_type.counterreporttype.counter_version
        except self.DoesNotExist:
            return None


class DimensionFilter(models.Model):
    """
    Used to specify how data from one dimension in ReportDataView should be filtered
    """

    report_data_view = models.ForeignKey(
        ReportDataView, on_delete=models.CASCADE, related_name="dimension_filters"
    )
    dimension = models.ForeignKey(Dimension, on_delete=models.CASCADE)
    allowed_values = models.JSONField(default=list, blank=True)


class ChartDefinition(models.Model):
    IMPLICIT_DIMENSION_CHOICES = (
        ("date", _("date")),
        ("platform", _("platform")),
        ("metric", _("metric")),
        ("organization", _("organization")),
        ("target", _("target")),
    )
    CHART_TYPE_HORIZONTAL_BAR = "h-bar"
    CHART_TYPE_VERTICAL_BAR = "v-bar"
    CHART_TYPE_LINE = "line"
    CHART_TYPE_CHOICES = (
        (CHART_TYPE_HORIZONTAL_BAR, _("horizontal bar")),
        (CHART_TYPE_VERTICAL_BAR, _("vertical bar")),
        (CHART_TYPE_LINE, _("line")),
    )

    SCOPE_ALL = ""
    SCOPE_PLATFORM = "platform"
    SCOPE_TITLE = "title"
    SCOPE_CHOICES = ((SCOPE_ALL, "any"), (SCOPE_PLATFORM, "platform"), (SCOPE_TITLE, "title"))

    name = models.CharField(max_length=200)
    desc = models.TextField(blank=True)
    primary_dimension = models.ForeignKey(
        Dimension,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="chart_definitions_primary",
        help_text="The primary dimension when specified by reference",
    )
    primary_implicit_dimension = models.CharField(  # noqa: DJ001
        choices=IMPLICIT_DIMENSION_CHOICES,
        max_length=20,
        null=True,
        blank=True,
        help_text="The primary dimension when using implicit dimension",
    )
    secondary_dimension = models.ForeignKey(
        Dimension,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="chart_definitions_secondary",
        help_text="The secondary dimension when specified by reference",
    )
    secondary_implicit_dimension = models.CharField(  # noqa: DJ001
        choices=IMPLICIT_DIMENSION_CHOICES,
        max_length=20,
        null=True,
        blank=True,
        help_text="The secondary dimension when using implicit dimension",
    )
    chart_type = models.CharField(
        max_length=20, choices=CHART_TYPE_CHOICES, default=CHART_TYPE_VERTICAL_BAR
    )
    ordering = models.CharField(
        max_length=20,
        blank=True,
        help_text="How to order the values in the chart, blank for "
        "default - primary dimension based - ordering",
    )
    ignore_organization = models.BooleanField(
        default=False,
        help_text="When checked, this chart will ignore selected organization. "
        "Thus it allows creation of charts with organization comparison.",
    )
    ignore_platform = models.BooleanField(
        default=False,
        help_text="When checked, the chart will contain data for all platforms. "
        "This is useful to compare platforms for one title.",
    )
    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES, default=SCOPE_ALL, blank=True)
    is_generic = models.BooleanField(
        default=False,
        help_text="A generic chart will be used implicitly for reports which do not have a chart "
        "explicitly assigned",
    )

    def __str__(self):
        return self.name


class ReportViewToChartType(models.Model):
    report_data_view = models.ForeignKey(ReportDataView, on_delete=models.CASCADE)
    chart_definition = models.ForeignKey(ChartDefinition, on_delete=models.CASCADE)
    position = models.PositiveIntegerField(
        default=0, help_text="Used to sort the chart types for a report view"
    )

    class Meta:
        unique_together = (
            ("report_data_view", "chart_definition"),
            ("report_data_view", "position"),
        )

    def __str__(self):
        return f"{self.report_data_view} - {self.chart_definition}"
