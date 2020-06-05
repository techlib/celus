from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from core.models import DataSource
from logs.models import ReportType, Metric, DimensionText, AccessLog, Dimension


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
    source = models.ForeignKey(DataSource, on_delete=models.CASCADE, null=True, blank=True)
    metric_allowed_values = JSONField(default=list, blank=True)
    primary_dimension = models.ForeignKey(
        Dimension, null=True, on_delete=models.SET_NULL, blank=True
    )
    is_standard_view = models.BooleanField(
        default=True, help_text='Standard view are shown separately from other views'
    )
    position = models.PositiveIntegerField(default=100)

    class Meta:
        ordering = ('position',)

    def __str__(self):
        return self.short_name

    @property
    def dimensions_sorted(self):
        return []

    @cached_property
    def accesslog_filters(self):
        filters = {}
        if self.metric_allowed_values:
            filters['metric__short_name__in'] = self.metric_allowed_values
        dim_filters = {df.dimension.pk: df.allowed_values for df in self.dimension_filters.all()}
        for i, dim in enumerate(self.base_report_type.dimensions_sorted):
            if dim.pk in dim_filters:
                allowed_values = dim_filters[dim.pk]
                if dim.type == dim.TYPE_TEXT:
                    values = [
                        dt.pk
                        for dt in DimensionText.objects.filter(
                            dimension=dim, text__in=allowed_values
                        )
                    ]
                else:
                    values = allowed_values
                filters[f'dim{i+1}__in'] = values
        return filters

    def logdata_qs(self):
        return AccessLog.objects.filter(
            report_type_id=self.base_report_type_id, **self.accesslog_filters
        ).values('organization', 'metric', 'platform', 'target', 'date')

    @property
    def public(self):
        return self.source is None


class DimensionFilter(models.Model):

    """
    Used to specify how data from one dimension in ReportDataView should be filtered
    """

    report_data_view = models.ForeignKey(
        ReportDataView, on_delete=models.CASCADE, related_name='dimension_filters'
    )
    dimension = models.ForeignKey(Dimension, on_delete=models.CASCADE)
    allowed_values = JSONField(default=list, blank=True)


class ChartDefinition(models.Model):

    IMPLICIT_DIMENSION_CHOICES = (
        ('date', _('date')),
        ('platform', _('platform')),
        ('metric', _('metric')),
        ('organization', _('organization')),
        ('target', _('target')),
    )
    CHART_TYPE_HORIZONTAL_BAR = 'h-bar'
    CHART_TYPE_VERTICAL_BAR = 'v-bar'
    CHART_TYPE_LINE = 'line'
    CHART_TYPE_CHOICES = (
        (CHART_TYPE_HORIZONTAL_BAR, _('horizontal bar')),
        (CHART_TYPE_VERTICAL_BAR, _('vertical bar')),
        (CHART_TYPE_LINE, _('line')),
    )

    SCOPE_ALL = ''
    SCOPE_PLATFORM = 'platform'
    SCOPE_TITLE = 'title'
    SCOPE_CHOICES = (
        (SCOPE_ALL, 'any'),
        (SCOPE_PLATFORM, 'platform'),
        (SCOPE_TITLE, 'title'),
    )

    name = models.CharField(max_length=200)
    desc = models.TextField(blank=True)
    primary_dimension = models.ForeignKey(
        Dimension,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='chart_definitions_primary',
        help_text='The primary dimension when specified by reference',
    )
    primary_implicit_dimension = models.CharField(
        choices=IMPLICIT_DIMENSION_CHOICES,
        max_length=20,
        null=True,
        blank=True,
        help_text='The primary dimension when using implicit dimension',
    )
    secondary_dimension = models.ForeignKey(
        Dimension,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='chart_definitions_secondary',
        help_text='The secondary dimension when specified by reference',
    )
    secondary_implicit_dimension = models.CharField(
        choices=IMPLICIT_DIMENSION_CHOICES,
        max_length=20,
        null=True,
        blank=True,
        help_text='The secondary dimension when using implicit dimension',
    )
    chart_type = models.CharField(
        max_length=20, choices=CHART_TYPE_CHOICES, default=CHART_TYPE_VERTICAL_BAR
    )
    ordering = models.CharField(
        max_length=20,
        blank=True,
        help_text='How to order the values in the chart, blank for '
        'default - primary dimension based - ordering',
    )
    ignore_organization = models.BooleanField(
        default=False,
        help_text='When checked, this chart will ignore selected organization. '
        'Thus it allows creation of charts with organization comparison.',
    )
    ignore_platform = models.BooleanField(
        default=False,
        help_text='When checked, the chart will contain data for all platforms. '
        'This is useful to compare platforms for one title.',
    )
    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES, default=SCOPE_ALL, blank=True)

    def __str__(self):
        return self.name


class ReportViewToChartType(models.Model):

    report_data_view = models.ForeignKey(ReportDataView, on_delete=models.CASCADE)
    chart_definition = models.ForeignKey(ChartDefinition, on_delete=models.CASCADE)
    position = models.PositiveIntegerField(
        default=0, help_text='Used to sort the chart types for ' 'a report view'
    )

    class Meta:
        unique_together = (
            ('report_data_view', 'chart_definition'),
            ('report_data_view', 'position'),
        )

    def __str__(self):
        return f'{self.report_data_view} - {self.chart_definition}'
