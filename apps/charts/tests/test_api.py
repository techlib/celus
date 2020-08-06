import pytest
from django.urls import reverse

from charts.models import ReportDataView, ChartDefinition, ReportViewToChartType
from core.tests.conftest import master_client, master_identity, authenticated_client, valid_identity
from logs.tests.conftest import report_type_nd


@pytest.fixture
def charts():
    ch1 = ChartDefinition.objects.create(name='chart 1', primary_implicit_dimension='metric')
    ch2 = ChartDefinition.objects.create(
        name='chart 1', primary_implicit_dimension='date', secondary_implicit_dimension='metric'
    )
    return [ch1, ch2]


@pytest.fixture
def simple_report_view(report_type_nd):
    return ReportDataView.objects.create(base_report_type=report_type_nd(0))


@pytest.mark.django_db
class TestReportViewToChartAPI(object):
    def test_api_list_simple(self, master_client):
        resp = master_client.get(reverse('report-view-to-chart-list'))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_api_list_full(self, simple_report_view, master_client, charts):
        rvch1 = ReportViewToChartType.objects.create(
            report_data_view=simple_report_view, chart_definition=charts[0], position=10
        )
        rvch2 = ReportViewToChartType.objects.create(
            report_data_view=simple_report_view, chart_definition=charts[1], position=20
        )
        resp = master_client.get(reverse('report-view-to-chart-list'))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        data.sort(key=lambda x: x['position'])
        assert data == [
            {
                'report_data_view': simple_report_view.pk,
                'chart_definition': charts[0].pk,
                'position': 10,
                'pk': rvch1.pk,
            },
            {
                'report_data_view': simple_report_view.pk,
                'chart_definition': charts[1].pk,
                'position': 20,
                'pk': rvch2.pk,
            },
        ]

    def test_patch(self, simple_report_view, master_client, charts):
        rvch = ReportViewToChartType.objects.create(
            report_data_view=simple_report_view, chart_definition=charts[0], position=10
        )
        resp = master_client.patch(
            reverse('report-view-to-chart-detail', args=(rvch.pk,)),
            {'position': 100},
            content_type='application/json',
        )
        assert resp.status_code == 200
        rvch.refresh_from_db()
        assert rvch.position == 100

    def test_post(self, simple_report_view, master_client, charts):
        assert ReportViewToChartType.objects.count() == 0
        resp = master_client.post(
            reverse('report-view-to-chart-list'),
            dict(
                report_data_view=simple_report_view.pk, chart_definition=charts[0].pk, position=10
            ),
        )
        assert resp.status_code == 201
        assert ReportViewToChartType.objects.count() == 1


@pytest.mark.django_db
class TestReportViewAPI(object):
    def test_api_list_simple(self, master_client):
        resp = master_client.get(reverse('report-view-list'))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_api_list_full(self, simple_report_view, master_client):
        resp = master_client.get(reverse('report-view-list'))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]['pk'] == simple_report_view.pk


@pytest.mark.django_db
class TestChartsAPI(object):
    def test_api_list_simple(self, master_client):
        """
        Simply test that the endpoint exists and returns some response
        """
        resp = master_client.get(reverse('chart-definition-list'))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_api_list_full(self, master_client, charts):
        """
        Test that the endpoint reports the currently defined charts
        """
        resp = master_client.get(reverse('chart-definition-list'))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert {rec['pk'] for rec in data} == {ch.pk for ch in charts}


@pytest.mark.django_db
class TestChartDataAPIView(object):
    def test_working_data(self, authenticated_client, simple_report_view):
        """
        Simply test that the endpoint exists and returns some response
        """
        response = authenticated_client.get(reverse('chart_data', args=(simple_report_view.pk,)))
        assert response.status_code == 200
        assert response.json()['data'] == []

    def test_bad_request(self, authenticated_client, simple_report_view):
        """
        Test that requesting a dimension that it not present in the requested ReportDateView
        return an error response
        """
        url = f"{reverse('chart_data', args=(simple_report_view.pk,))}?prim_dim=foobar"
        response = authenticated_client.get(url)
        assert response.status_code == 400
        error = response.json()['error']
        assert 'foobar' in error
