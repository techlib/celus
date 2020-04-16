from django.http import HttpResponseBadRequest
from pandas import DataFrame
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from charts.models import ChartDefinition
from charts.models import ReportDataView
from charts.serializers import ChartDefinitionSerializer, ReportDataViewSerializer
from logs.logic.queries import StatsComputer
from logs.models import ReportType
from logs.serializers import DimensionSerializer
from publications.models import Platform


class ChartDefinitionViewSet(ReadOnlyModelViewSet):

    queryset = ChartDefinition.objects.all()
    serializer_class = ChartDefinitionSerializer


class ReportTypeToReportDataViewView(APIView):
    def get_serializer_class(self):
        return ReportDataViewSerializer

    def get(self, request, report_type_pk):
        rdvs = ReportDataView.objects.filter(base_report_type_id=report_type_pk)
        return Response(ReportDataViewSerializer(rdvs, many=True).data)


class ReportDataViewChartDefinitions(APIView):
    def get_serializer_class(self):
        return ChartDefinitionSerializer

    def get(self, request, view_pk):
        chd = ChartDefinition.objects.filter(reportviewtocharttype__report_data_view_id=view_pk).\
            order_by('reportviewtocharttype__position')
        return Response(ChartDefinitionSerializer(chd, many=True).data)


class ChartDataView(APIView):

    def get(self, request, report_view_id):
        report_view = get_object_or_404(ReportDataView, pk=report_view_id)
        computer = StatsComputer()
        data = computer.get_data(report_view, request.GET, request.user)
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
            return Response(data,
                            headers={
                                'Content-Disposition':
                                    f'attachment; filename="export.{data_format}"'
                            })
        # prepare the data to return
        reply = {'data': data}
        if computer.prim_dim_obj:
            reply[computer.prim_dim_name] = DimensionSerializer(computer.prim_dim_obj).data
        if computer.sec_dim_obj:
            reply[computer.sec_dim_name] = DimensionSerializer(computer.sec_dim_obj).data
        return Response(reply)
