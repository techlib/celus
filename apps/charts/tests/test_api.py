from unittest.mock import patch

import pytest
from django.urls import reverse

from charts.models import ReportDataView, ChartDefinition, ReportViewToChartType
from core.tests.conftest import master_client, master_identity, authenticated_client, valid_identity
from logs.logic.clickhouse import sync_import_batch_with_clickhouse
from logs.logic.data_import import import_counter_records
from logs.models import OrganizationPlatform, AccessLog, Metric, ImportBatch
from logs.tests.conftest import report_type_nd, counter_records_0d
from publications.models import Title, Platform
from publications.tests.conftest import platform
from organizations.tests.conftest import organizations


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
class TestReportViewToChartAPI:
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
class TestReportViewAPI:
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

    def test_api_list_ordering(self, report_type_nd, master_client):
        """
        Check that report data views are ordered by position in reply, not by name or short_name
        """
        rt = report_type_nd(0)
        ReportDataView.objects.create(base_report_type=rt, position=3, short_name='A', name='A')
        ReportDataView.objects.create(base_report_type=rt, position=1, short_name='X', name='X')
        ReportDataView.objects.create(base_report_type=rt, position=2, short_name='M', name='M')
        resp = master_client.get(reverse('report-view-list'))
        assert resp.status_code == 200
        data = resp.json()
        assert [rec['position'] for rec in data] == [1, 2, 3]

    def test_api_list_for_report_type_ordering(self, report_type_nd, master_client):
        """
        Check that report data views are ordered by position in reply, not by name or short_name
        - for report-type-to-report-data-view
        """
        rt = report_type_nd(0)
        ReportDataView.objects.create(base_report_type=rt, position=3, short_name='A', name='A')
        ReportDataView.objects.create(base_report_type=rt, position=1, short_name='X', name='X')
        ReportDataView.objects.create(base_report_type=rt, position=2, short_name='M', name='M')
        resp = master_client.get(reverse('report-type-to-report-data-view', args=(rt.pk,)))
        assert resp.status_code == 200
        data = resp.json()
        assert [rec['position'] for rec in data] == [1, 2, 3]

    @pytest.mark.clickhouse
    @pytest.mark.usefixtures('clickhouse_on_off')
    @pytest.mark.django_db(transaction=True)
    def test_api_list_for_platform_ordering(
        self, report_type_nd, master_client, platform, organizations
    ):
        """
        Check that report data views are ordered by position in reply, not by name or short_name
        - for platform-report-data-views
        """
        rt = report_type_nd(0)
        ReportDataView.objects.create(base_report_type=rt, position=3, short_name='A', name='A')
        ReportDataView.objects.create(base_report_type=rt, position=1, short_name='X', name='X')
        ReportDataView.objects.create(base_report_type=rt, position=2, short_name='M', name='M')
        organization = organizations[0]
        OrganizationPlatform.objects.create(organization=organization, platform=platform)
        # we need to add accesslog in order to connect platform and report-type
        ib = ImportBatch.objects.create(
            report_type=rt, organization=organization, platform=platform
        )
        AccessLog.objects.create(
            report_type=rt,
            organization=organization,
            platform=platform,
            value=1,
            date='2020-01-01',
            metric=Metric.objects.create(short_name='metric'),
            import_batch=ib,
        )
        # sync with clickhouse as we have circumvented the normal creation of accesslogs
        sync_import_batch_with_clickhouse(ib)

        resp = master_client.get(
            reverse(
                'platform-report-data-views-list',
                kwargs={'organization_pk': organization.pk, 'platform_pk': platform.pk},
            )
        )
        assert resp.status_code == 200
        data = resp.json()
        assert [rec['position'] for rec in data] == [1, 2, 3]

    @pytest.mark.clickhouse
    @pytest.mark.usefixtures('clickhouse_on_off')
    @pytest.mark.django_db(transaction=True)
    def test_api_list_for_platform_and_title_ordering(
        self, report_type_nd, master_client, platform, organizations
    ):
        """
        Check that report data views are ordered by position in reply, not by name or short_name
        - for platform-report-data-views
        """
        rt = report_type_nd(0)
        ReportDataView.objects.create(base_report_type=rt, position=3, short_name='A', name='A')
        ReportDataView.objects.create(base_report_type=rt, position=1, short_name='X', name='X')
        ReportDataView.objects.create(base_report_type=rt, position=2, short_name='M', name='M')
        organization = organizations[0]
        OrganizationPlatform.objects.create(organization=organization, platform=platform)
        title = Title.objects.create(name='Journal of Foo Bar')
        # we need to add accesslog in order to connect platform and report-type
        ib = ImportBatch.objects.create(
            report_type=rt, organization=organization, platform=platform
        )
        AccessLog.objects.create(
            report_type=rt,
            organization=organization,
            platform=platform,
            target=title,
            value=1,
            date='2020-01-01',
            metric=Metric.objects.create(short_name='metric'),
            import_batch=ib,
        )
        # sync with clickhouse as we have circumvented the normal creation of accesslogs
        sync_import_batch_with_clickhouse(ib)
        resp = master_client.get(
            reverse(
                'platform-title-report-data-views-list',
                kwargs={
                    'organization_pk': organization.pk,
                    'platform_pk': platform.pk,
                    'title_pk': title.pk,
                },
            )
        )
        assert resp.status_code == 200
        data = resp.json()
        assert [rec['position'] for rec in data] == [1, 2, 3]


@pytest.mark.django_db
class TestChartsAPI:
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
class TestChartDataAPIView:
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

    def test_with_data_no_dashboard(
        self, counter_records_0d, organizations, report_type_nd, authenticated_client, platform
    ):
        """
        Test that recache is not used for normal queries
        """
        organization = organizations[0]
        report_type = report_type_nd(0)  # type: ReportType
        import_batch = ImportBatch.objects.create(
            organization=organization, platform=platform, report_type=report_type
        )
        import_counter_records(
            report_type, organization, platform, counter_records_0d, import_batch
        )
        assert AccessLog.objects.count() == 1
        metric = Metric.objects.get()
        report_view = ReportDataView.objects.create(base_report_type=report_type)
        resp = authenticated_client.get(
            reverse('chart_data', args=(report_view.pk,)),
            {
                'organization': organization.pk,
                'metric': metric.pk,
                'platform': platform.pk,
                'prim_dim': 'date',
            },
        )
        assert resp.status_code == 200
        assert 'data' in resp.json()

    def test_with_data_dashboard(
        self, counter_records_0d, organizations, report_type_nd, authenticated_client, platform
    ):
        """
        Test that recache is used for queries marked with the `dashboard` attribute
        """
        organization = organizations[0]
        report_type = report_type_nd(0)  # type: ReportType
        import_batch = ImportBatch.objects.create(
            organization=organization, platform=platform, report_type=report_type
        )
        import_counter_records(
            report_type, organization, platform, counter_records_0d, import_batch
        )
        assert AccessLog.objects.count() == 1
        metric = Metric.objects.get()
        report_view = ReportDataView.objects.create(base_report_type=report_type)
        resp = authenticated_client.get(
            reverse('chart_data', args=(report_view.pk,)),
            {
                'organization': organization.pk,
                'metric': metric.pk,
                'platform': platform.pk,
                'prim_dim': 'date',
                'dashboard': True,
            },
        )
        assert resp.status_code == 200
        assert 'data' in resp.json()
