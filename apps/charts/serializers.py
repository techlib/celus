from rest_framework.fields import BooleanField
from rest_framework.serializers import ModelSerializer

from .models import ReportDataView
from logs.serializers import DimensionSerializer


class ReportDataViewSerializer(ModelSerializer):

    public = BooleanField(default=False)
    primary_dimension = DimensionSerializer(read_only=True)

    class Meta:
        model = ReportDataView
        fields = ('pk', 'short_name', 'name', 'name_cs', 'name_en', 'desc', 'public',
                  'primary_dimension')
