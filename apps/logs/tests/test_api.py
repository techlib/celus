import json

import pytest
from django.urls import reverse

from logs.models import ReportType, AccessLog, Metric
from publications.models import Platform

from ..logic.data_import import import_counter_records
from organizations.tests.conftest import organizations
from core.tests.conftest import valid_identity, authenticated_client, authentication_headers,\
    invalid_identity, master_identity, master_client


@pytest.mark.django_db
class TestChartDataAPI(object):

    """
    Tests functionality of the view chart-data
    """

    def test_api_simple_data_0d(self, counter_records_0d, organizations, report_type_nd,
                                authenticated_client):
        platform = Platform.objects.create(ext_id=1234, short_name='Platform1', name='Platform 1',
                                           provider='Provider 1')
        organization = organizations[0]
        report_type = report_type_nd(0)  # type: ReportType
        import_counter_records(report_type, organization, platform, counter_records_0d)
        assert AccessLog.objects.count() == 1
        metric = Metric.objects.get()
        resp = authenticated_client.get(
            reverse('chart_data', args=(report_type.short_name,)),
            {'organization': organization.pk,
             'metric': metric.pk,
             'platform': platform.pk,
             'prim_dim': 'date'})
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
                                 ['platform', None, 1],  # just one platform
                             ])
    def test_api_secondary_dim(self, counter_records, organizations, report_type_nd,
                               primary_dim, secondary_dim, count, authenticated_client):
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
        if type(primary_dim) is int:
            primary_dim = report_type.dimensions_sorted[primary_dim-1].short_name
        params = {'organization': organization.pk,
                  'metric': metric.pk,
                  'platform': platform.pk,
                  'prim_dim': primary_dim
                  }
        if secondary_dim:
            params['sec_dim'] = report_type.dimensions_sorted[secondary_dim-1].short_name
        resp = authenticated_client.get(reverse('chart_data', args=(report_type.short_name,)),
                                        params)
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert 'data' in data
        assert len(data['data']) == count

    @pytest.mark.parametrize('primary_dim, secondary_dim, result',
                             [
                                 ['date', None, [{'date': '2018-01-01', 'count': 3}]],
                                 ['date', 3, [{'date': '2018-01-01', 'dim2': '3v1', 'count': 3}]],
                                 ['date', 1, [{'date': '2018-01-01', 'dim0': '1v1', 'count': 1},
                                              {'date': '2018-01-01', 'dim0': '1v2', 'count': 2}]],
                                 ['platform', None, [{'platform': 'Platform1', 'count': 3}]],
                                 ['platform', 'metric', [{'platform': 'Platform1',
                                                          'metric': 'Hits', 'count': 3}]],
                                 ['metric', 'platform', [{'platform': 'Platform1',
                                                          'metric': 'Hits', 'count': 3}]],
                                 ['organization', None, [{'organization': 'AAA', 'count': 3}]],
                                 ['organization', 'metric', [{'organization': 'AAA',
                                                              'metric': 'Hits',
                                                              'count': 3}]],
                                 ['metric', 'organization', [{'organization': 'AAA',
                                                              'metric': 'Hits',
                                                              'count': 3}]],
                             ])
    def test_api_values(self, counter_records, organizations, report_type_nd,
                        primary_dim, secondary_dim, result, master_client):
        platform = Platform.objects.create(ext_id=1234, short_name='Platform1', name='Platform 1',
                                           provider='Provider 1')
        data = [
            ['Title1', '2018-01-01', '1v1', '2v1', '3v1', 1],
            ['Title1', '2018-01-01', '1v2', '2v1', '3v1', 2],
        ]
        crs = list(counter_records(data, metric='Hits', platform='Platform1'))
        organization = organizations[0]
        report_type = report_type_nd(3)
        import_counter_records(report_type, organization, platform, crs)
        assert AccessLog.objects.count() == 2
        metric = Metric.objects.get(short_name='Hits')
        params = {'organization': organization.pk,
                  'metric': metric.pk,
                  'platform': platform.pk,
                  'prim_dim': primary_dim,
                  }
        if secondary_dim:
            if type(secondary_dim) is int:
                params['sec_dim'] = report_type.dimensions_sorted[secondary_dim-1].short_name
            else:
                params['sec_dim'] = secondary_dim
        resp = master_client.get(reverse('chart_data', args=(report_type.short_name,)),
                                 params)
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert 'data' in data
        assert data['data'] == result

    def test_api_filtering(self, counter_records, organizations, report_type_nd,
                           authenticated_client):
        platform1 = Platform.objects.create(ext_id=1234, short_name='Platform1', name='Platform 1',
                                            provider='Provider 1')
        platform2 = Platform.objects.create(ext_id=1235, short_name='Platform2', name='Platform 2',
                                            provider='Provider 2')
        data1 = [
            ['Title1', '2018-01-01', '1v1', '2v1', '3v1', 1],
            ['Title2', '2018-01-01', '1v2', '2v1', '3v1', 2],
            ['Title3', '2018-01-01', '1v2', '2v1', '3v1', 4],
        ]
        data2 = [
            ['Title1', '2018-01-01', '1v1', '2v1', '3v1', 8],
            ['Title2', '2018-02-01', '1v1', '2v1', '3v1', 16],
            ['Title3', '2018-02-01', '1v2', '2v2', '3v1', 32],
        ]
        crs1 = list(counter_records(data1, metric='Hits', platform='Platform1'))
        crs2 = list(counter_records(data2, metric='Big Hits', platform='Platform2'))
        report_type = report_type_nd(3)
        import_counter_records(report_type, organizations[0], platform1, crs1)
        import_counter_records(report_type, organizations[0], platform2, crs1)
        import_counter_records(report_type, organizations[1], platform1, crs1)
        import_counter_records(report_type, organizations[1], platform2, crs2)
        assert AccessLog.objects.count() == 12
        metric1 = Metric.objects.get(short_name='Hits')
        metric2 = Metric.objects.get(short_name='Big Hits')

        def get_data(params):
            resp = authenticated_client.get(reverse('chart_data', args=(report_type.short_name,)),
                                            params)
            assert resp.status_code == 200
            result = json.loads(resp.content)
            assert 'data' in result
            return result['data']
        # no filter
        recs = get_data({'prim_dim': 'date'})
        assert len(recs) == 2
        assert recs[0]['count'] == 3*(1+2+4)+8
        assert recs[1]['count'] == 16+32
        # organization filter
        recs = get_data({'organization': organizations[0].pk,
                         'prim_dim': 'date'})
        assert len(recs) == 1
        assert recs[0]['count'] == 2*(1+2+4)
        # organization dim, platform filter
        recs = get_data({'platform': platform2.pk,
                         'prim_dim': 'organization'})
        assert len(recs) == 2
        assert recs[0]['count'] == 1+2+4
        assert recs[1]['count'] == 8+16+32
        # filter by dim1, platform dim
        recs = get_data({'dim0': '1v1',
                         'prim_dim': 'platform'})
        assert len(recs) == 2
        assert recs[0]['count'] == 2*1
        assert recs[1]['count'] == 1+8+16
        # filter by dim2, platform and title dim
        recs = get_data({'dim0': '1v1',
                         'prim_dim': 'platform',
                         'sec_dim': 'target'})
        assert len(recs) == 3
        assert recs[0]['count'] == 2*1  # platform 1 and title 1
        assert recs[1]['count'] == 1+8  # platform 2 and title 1
        assert recs[2]['count'] == 16   # platform 2 and title 2
        # filter by date
        recs = get_data({'date': '2018-02-01',
                         'prim_dim': 'target'})
        assert len(recs) == 2
        assert recs[0]['count'] == 16
        assert recs[1]['count'] == 32
        # filter by date range
        recs = get_data({'start': '2018-02',
                         'end': '2018-02',
                         'prim_dim': 'target'})
        assert len(recs) == 2
        assert recs[0]['count'] == 16
        assert recs[1]['count'] == 32
