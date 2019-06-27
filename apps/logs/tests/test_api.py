import json

import pytest
from django.urls import reverse

from logs.models import ReportType, OrganizationPlatform, AccessLog, DimensionText, Metric
from publications.models import Platform, Title

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
        assert len(data['data']) == 1

    def _test_data_import_mutli_3d(self, counter_records_nd, organizations, report_type_nd):
        platform = Platform.objects.create(ext_id=1234, short_name='Platform1', name='Platform 1',
                                           provider='Provider 1')
        op = OrganizationPlatform.objects.create(organization=organizations[0], platform=platform)
        assert AccessLog.objects.count() == 0
        assert Title.objects.count() == 0
        crs = list(counter_records_nd(3, record_number=10))
        stats = import_counter_records(report_type_nd(3), op, crs)
        assert stats['skipped logs'] == 0
        assert stats['new logs'] == 10
        assert AccessLog.objects.count() == 10
        assert Title.objects.count() > 0
        al = AccessLog.objects.order_by('pk')[0]
        assert al.value == crs[0].value
        # check that the remap of the value is the same as the original text value
        assert DimensionText.objects.get(pk=al.dim1).text == crs[0].dimension_data['dim0']
        assert DimensionText.objects.get(pk=al.dim2).text == crs[0].dimension_data['dim1']
        assert DimensionText.objects.get(pk=al.dim3).text == crs[0].dimension_data['dim2']
        assert al.dim4 is None

