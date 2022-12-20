from time import monotonic

from charts.models import ChartDefinition, ReportDataView, ReportViewToChartType
from charts.serializers import (
    ChartDefinitionSerializer,
    ReportDataViewSerializer,
    ReportViewToChartTypeSerializer,
)
from core.permissions import SuperuserOrAdminPermission
from core.prometheus import report_access_time_summary, report_access_total_counter
from logs.logic.queries import BadRequestError, StatsComputer, TooMuchDataError
from logs.models import ReportType
from logs.serializers import DimensionSerializer, MetricSerializer
from pandas import DataFrame
from rest_framework import serializers, status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet


class ChartDefinitionViewSet(ReadOnlyModelViewSet):

    queryset = ChartDefinition.objects.all()
    serializer_class = ChartDefinitionSerializer


class ReportTypeToReportDataViewView(APIView):
    def get_serializer_class(self):
        return ReportDataViewSerializer

    def get(self, request, report_type_pk):
        rdvs = ReportDataView.objects.filter(base_report_type_id=report_type_pk).order_by(
            'position'
        )
        serializer_class = self.get_serializer_class()
        if rdvs.count():
            return Response(serializer_class(rdvs, many=True).data)
        else:
            # if no data view is defined for the current report type, return a proxy based
            # on the report_type itself
            proxy_data_view = ReportType.objects.get(pk=report_type_pk)
            data = serializer_class(proxy_data_view).data
            data['position'] = 1
            data['is_proxy'] = True
            data['is_standard_view'] = True
            return Response([data])


class ReportDataViewChartDefinitions(APIView):
    def get_serializer_class(self):
        return ChartDefinitionSerializer

    def get(self, request, view_pk):
        if int(view_pk) == -1:
            chd = ChartDefinition.objects.filter(is_generic=True)
        else:
            chd = ChartDefinition.objects.filter(
                reportviewtocharttype__report_data_view_id=view_pk
            ).order_by('reportviewtocharttype__position')
        return Response(self.get_serializer_class()(chd, many=True).data)


class ChartDataView(APIView):
    def get(self, request, report_view_id):
        report_view = get_object_or_404(ReportDataView, pk=report_view_id)
        start = monotonic()
        # special attribute signaling that this view is used on dashboard and thus we
        # want to cache the data for extra speed using recache
        dashboard_view = 'dashboard' in request.GET
        try:
            computer = StatsComputer(report_view, request.GET)
            data = computer.get_data(request.user, recache=dashboard_view)
        except TooMuchDataError:
            return Response({'too_much_data': True})
        except BadRequestError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        # prometheus stats
        label_attrs = dict(view_type='chart_data', report_type=computer.used_report_type.pk)
        report_access_total_counter.labels(**label_attrs).inc()
        report_access_time_summary.labels(**label_attrs).observe(monotonic() - start)

        data_format = request.GET.get('format')
        if data_format in ('csv', 'xlsx'):
            # for the bare result, we do not add any extra information, just output the list
            data = DataFrame(data)
            new_keys = [computer.io_prim_dim_name]
            if computer.io_sec_dim_name:
                new_keys.append(computer.io_sec_dim_name)
            # we set the queried dimensions as index so that the default integer index is not
            # added to the result
            data.set_index(new_keys, drop=True, inplace=True)
            return Response(
                data,
                headers={'Content-Disposition': f'attachment; filename="export.{data_format}"'},
            )
        # prepare the data to return
        reply = {'data': data}
        if computer.prim_dim_obj:
            reply[computer.prim_dim_name] = DimensionSerializer(computer.prim_dim_obj).data
        if computer.sec_dim_obj:
            reply[computer.sec_dim_name] = DimensionSerializer(computer.sec_dim_obj).data
        reply['reported_metrics'] = MetricSerializer(
            computer.reported_metrics.values(), many=True
        ).data
        return Response(reply)


class ChartDataAvailableMetricsView(APIView):
    class Serializer(MetricSerializer):
        is_interest_metric = serializers.BooleanField()

        class Meta(MetricSerializer.Meta):
            fields = MetricSerializer.Meta.fields + ('is_interest_metric',)

    def get(self, request, report_view_id):
        report_view = get_object_or_404(ReportDataView, pk=report_view_id)
        try:
            computer = StatsComputer(report_view, request.GET)
            data = computer.get_available_metrics()
        except BadRequestError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(self.Serializer(data, many=True).data)


class ReportViewToChartTypeViewSet(ModelViewSet):

    """
    Simple ViewSet for mapping of `ReportDataView`s to `ChartDefinition` - `ReportViewToChartType`.
    It is only accessible to superusers because it is only used to view and change how charts
    are assigned to report views - normal users get this data using other views in this module.
    """

    permission_classes = [SuperuserOrAdminPermission]
    queryset = ReportViewToChartType.objects.all()
    serializer_class = ReportViewToChartTypeSerializer


class ReportDataViewViewSet(ReadOnlyModelViewSet):

    """
    ViewSet with `ReportDataView`s. It is read-only as we do not want to support editing using
    the API at this stage.
    """

    queryset = ReportDataView.objects.all().order_by('position')
    serializer_class = ReportDataViewSerializer
