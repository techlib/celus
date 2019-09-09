from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.functional import cached_property

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
    primary_dimension = models.ForeignKey(Dimension, null=True, on_delete=models.SET_NULL,
                                          blank=True)

    def __str__(self):
        return self.short_name

    @property
    def dimensions_sorted(self):
        return []

    @cached_property
    def accesslog_filters(self):
        filters = {}
        if self.metric_allowed_values:
            filters['metric__in'] = [metric.pk for metric in
                                     Metric.objects.filter(
                                         short_name__in=self.metric_allowed_values)]
        dim_filters = {df.dimension.pk: df.allowed_values for df in self.dimension_filters.all()}
        for i, dim in enumerate(self.base_report_type.dimensions_sorted):
            if dim.pk in dim_filters:
                allowed_values = dim_filters[dim.pk]
                if dim.type == dim.TYPE_TEXT:
                    values = [dt.pk for dt in
                              DimensionText.objects.filter(dimension=dim, text__in=allowed_values)]
                else:
                    values = allowed_values
                filters[f'dim{i+1}__in'] = values
        return filters

    def logdata_qs(self):
        return AccessLog.objects.\
            filter(report_type_id=self.base_report_type_id, **self.accesslog_filters).\
            values('organization', 'metric', 'platform', 'target', 'date')

    @property
    def public(self):
        return self.source is None


class DimensionFilter(models.Model):

    """
    Used to specify how data from one dimension in ReportDataView should be filtered
    """

    report_data_view = models.ForeignKey(ReportDataView, on_delete=models.CASCADE,
                                         related_name='dimension_filters')
    dimension = models.ForeignKey(Dimension, on_delete=models.CASCADE)
    allowed_values = JSONField(default=list, blank=True)

#
# class ChartDefinition(models.Model):
#
#     pass
