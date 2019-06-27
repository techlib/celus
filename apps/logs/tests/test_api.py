import json

import pytest
from django.urls import reverse

from logs.models import ReportType, AccessLog, Metric
from publications.models import Platform

from ..logic.data_import import import_counter_records
from organizations.tests.conftest import organizations


@pytest.mark.django_db
class TestChartDataAPI(object):

    """
    Tests functionality of the view chart-data
    """

    def test_api_simple_data_0d(self, counter_records_0d, organizations, report_type_nd, client):
        platform = Platform.objects.create(ext_id=1234, short_name='Platform1', name='Platform 1',
                                           provider='Provider 1')
        organization = organizations[0]
        report_type = report_type_nd(0)  # type: ReportType
        import_counter_records(report_type, organization, platform, counter_records_0d)
        assert AccessLog.objects.count() == 1
        metric = Metric.objects.get()
        resp = client.get(reverse('chart_data'),
                          {'organization': organization.pk,
                           'metric': metric.pk,
                           'platform': platform.pk,
                           'prim_dim': 'date',
                           'report_type': report_type.short_name})
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert 'data' in data

    @pytest.mark.parametrize('primary_dim, secondary_dim, count',
                             [
                                 ['date', None, 3],  # three months
                                 ['date', 1, 4],  # two values in first month
                                 [1, None, 2],  # two values in first dim
                                 [2, None, 3],  # three values in first dim
                                 [2, 3, 4],  # four combinations of dim2 and dim3
                             ])
    def test_api_secondary_dim(self, counter_records, organizations, report_type_nd, client,
                               primary_dim, secondary_dim, count):
        platform = Platform.objects.create(ext_id=1234, short_name='Platform1', name='Platform 1',
                                           provider='Provider 1')
        data = [
            ['Title1', '2018-01-01', '1v1', '2v1', '3v1', 1],
            ['Title1', '2018-01-01', '1v2', '2v1', '3v1', 2],
            ['Title2', '2018-01-01', '1v2', '2v2', '3v1', 4],
            ['Title1', '2018-02-01', '1v1', '2v1', '3v1', 8],
            ['Title2', '2018-02-01', '1v1', '2v2', '3v2', 16],
            ['Title1', '2018-03-01', '1v1', '2v3', '3v2', 32],
        ]
        crs = list(counter_records(data, metric='Hits', platform='Platform1'))
        organization = organizations[0]
        report_type = report_type_nd(3)
        import_counter_records(report_type, organization, platform, crs)
        assert AccessLog.objects.count() == 6
        metric = Metric.objects.get(short_name='Hits')
        params = {'organization': organization.pk,
                  'metric': metric.pk,
                  'platform': platform.pk,
                  'prim_dim': primary_dim,
                  'report_type': report_type.short_name}
        if secondary_dim:
            params['sec_dim'] = secondary_dim
        resp = client.get(reverse('chart_data'), params)
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert 'data' in data
        print(data)
        assert len(data['data']) == count




