import base64
import json

import pytest
from core.tests.conftest import (  # noqa - fixtures
    authenticated_client,
    master_admin_client,
    master_admin_identity,
    valid_identity,
)
from django.db.models import Sum
from django.urls import reverse
from logs.fake_data import DimensionTextFactory, ImportBatchFactory, ManualDataUploadFullFactory
from logs.logic.clickhouse import sync_import_batch_with_clickhouse
from logs.logic.data_import import import_counter_records
from logs.logic.materialized_reports import sync_materialized_reports
from logs.models import AccessLog, MduState, Metric, ReportMaterializationSpec, ReportType
from logs.tests.conftest import counter_records_0d, report_type_nd  # noqa - fixture
from organizations.tests.conftest import organizations  # noqa - fixture
from publications.models import Title
from publications.tests.conftest import interest_rt, platform  # noqa - fixture
from tags.models import Tag, TagClass

from charts.fake_data import ChartDefinitionFactory, ReportDataViewFactory
from charts.models import ChartDefinition, DimensionFilter, ReportDataView, ReportViewToChartType


@pytest.fixture
def charts():
    ch1 = ChartDefinition.objects.create(name="chart 1", primary_implicit_dimension="metric")
    ch2 = ChartDefinition.objects.create(
        name="chart 1", primary_implicit_dimension="date", secondary_implicit_dimension="metric"
    )
    return [ch1, ch2]


@pytest.fixture
def simple_report_view(report_type_nd):
    return ReportDataView.objects.create(base_report_type=report_type_nd(0))


@pytest.mark.django_db
class TestReportViewToChartAPI:
    def test_api_list_simple(self, master_admin_client):
        resp = master_admin_client.get(reverse("report-view-to-chart-list"))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_api_list_full(self, simple_report_view, master_admin_client, charts):
        rvch1 = ReportViewToChartType.objects.create(
            report_data_view=simple_report_view, chart_definition=charts[0], position=10
        )
        rvch2 = ReportViewToChartType.objects.create(
            report_data_view=simple_report_view, chart_definition=charts[1], position=20
        )
        resp = master_admin_client.get(reverse("report-view-to-chart-list"))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        data.sort(key=lambda x: x["position"])
        assert data == [
            {
                "report_data_view": simple_report_view.pk,
                "chart_definition": charts[0].pk,
                "position": 10,
                "pk": rvch1.pk,
            },
            {
                "report_data_view": simple_report_view.pk,
                "chart_definition": charts[1].pk,
                "position": 20,
                "pk": rvch2.pk,
            },
        ]

    def test_patch(self, simple_report_view, master_admin_client, charts):
        rvch = ReportViewToChartType.objects.create(
            report_data_view=simple_report_view, chart_definition=charts[0], position=10
        )
        resp = master_admin_client.patch(
            reverse("report-view-to-chart-detail", args=(rvch.pk,)),
            {"position": 100},
            content_type="application/json",
        )
        assert resp.status_code == 200
        rvch.refresh_from_db()
        assert rvch.position == 100

    def test_post(self, simple_report_view, master_admin_client, charts):
        assert ReportViewToChartType.objects.count() == 0
        resp = master_admin_client.post(
            reverse("report-view-to-chart-list"),
            {
                "report_data_view": simple_report_view.pk,
                "chart_definition": charts[0].pk,
                "position": 10,
            },
        )
        assert resp.status_code == 201
        assert ReportViewToChartType.objects.count() == 1


@pytest.mark.django_db
class TestReportViewAPI:
    def test_api_list_simple(self, master_admin_client):
        resp = master_admin_client.get(reverse("report-view-list"))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_api_list_full(self, simple_report_view, master_admin_client):
        resp = master_admin_client.get(reverse("report-view-list"))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["pk"] == simple_report_view.pk

    def test_api_list_ordering(self, report_type_nd, master_admin_client):
        """
        Check that report data views are ordered by position in reply, not by name or short_name
        """
        rt = report_type_nd(0)
        ReportDataView.objects.create(base_report_type=rt, position=3, short_name="A", name="A")
        ReportDataView.objects.create(base_report_type=rt, position=1, short_name="X", name="X")
        ReportDataView.objects.create(base_report_type=rt, position=2, short_name="M", name="M")
        resp = master_admin_client.get(reverse("report-view-list"))
        assert resp.status_code == 200
        data = resp.json()
        assert [rec["position"] for rec in data] == [1, 2, 3]

    def test_api_list_for_report_type_ordering(self, report_type_nd, master_admin_client):
        """
        Check that report data views are ordered by position in reply, not by name or short_name
        - for report-type-to-report-data-view
        """
        rt = report_type_nd(0)
        ReportDataView.objects.create(base_report_type=rt, position=3, short_name="A", name="A")
        ReportDataView.objects.create(base_report_type=rt, position=1, short_name="X", name="X")
        ReportDataView.objects.create(base_report_type=rt, position=2, short_name="M", name="M")
        resp = master_admin_client.get(reverse("report-type-to-report-data-view", args=(rt.pk,)))
        assert resp.status_code == 200
        data = resp.json()
        assert [rec["position"] for rec in data] == [1, 2, 3]

    @pytest.mark.parametrize("full", [True, False])
    def test_api_list_for_report_type_full_detail(self, report_type_nd, master_admin_client, full):
        """
        Check that the full detail of the report data view is returned when a `full` query
        parameter is passed. This should include the dimension and metric filters.

        """
        rt = report_type_nd(1)
        ReportDataView.objects.create(
            base_report_type=rt,
            position=3,
            short_name="A",
            name="A",
            metric_allowed_values=["m1", "m2"],
        )
        DimensionFilter.objects.create(
            report_data_view=rt.reportdataview_set.first(),
            dimension=rt.dimensions_sorted[0],
            allowed_values=["d1", "d2"],
        )
        resp = master_admin_client.get(
            reverse("report-type-to-report-data-view", args=(rt.pk,)), {"full": full}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        if full:
            assert "metric_allowed_values" in data[0]
            assert "dimension_filters" in data[0]
            assert data[0]["metric_allowed_values"] == ["m1", "m2"]
            df = data[0]["dimension_filters"]
            assert len(df) == 1
            assert df[0]["allowed_values"] == ["d1", "d2"]
            assert df[0]["dimension"]["pk"] == rt.dimensions_sorted[0].pk
        else:
            assert "metric_allowed_values" not in data[0]
            assert "dimension_filters" not in data[0]

    def test_api_list_for_report_type_without_report_view(
        self, report_type_nd, master_admin_client
    ):
        """
        Tests that an on-the-fly created view will be returned if no explicit view is created
        """
        rt = report_type_nd(0)
        resp = master_admin_client.get(reverse("report-type-to-report-data-view", args=(rt.pk,)))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        view = data[0]
        assert view["pk"] == rt.pk
        assert view["short_name"] == rt.short_name
        assert view["name"] == rt.name
        assert view["position"] == 1
        assert view["is_proxy"] is True
        assert view["is_standard_view"] is False

    @pytest.mark.clickhouse
    @pytest.mark.usefixtures("clickhouse_on_off")
    @pytest.mark.django_db(transaction=True)
    def test_api_list_for_platform_with_proxy_views(
        self, report_type_nd, master_admin_client, platform, organizations
    ):
        """
        Check that if report_type does not have a report data view defined, a proxy view is created
        on the fly and returned in the list of report data views.

        We also need to make sure that proxy views are not created for materialized report types.
        """
        rt = report_type_nd(0)
        mat_spec = ReportMaterializationSpec.objects.create(base_report_type=rt)
        ReportType.objects.create(materialization_spec=mat_spec, name="mat_rt", short_name="mat_rt")
        organization = organizations[0]
        # we need to add accesslog in order to connect platform and report-type
        ib = ImportBatchFactory(report_type=rt, organization=organization, platform=platform)
        AccessLog.objects.create(
            report_type=rt,
            organization=organization,
            platform=platform,
            value=1,
            date=ib.date,
            metric=Metric.objects.create(short_name="metric"),
            import_batch=ib,
        )
        # make sure materialized report types are populated as well
        sync_materialized_reports()
        # sync with clickhouse as we have circumvented the normal creation of accesslogs
        sync_import_batch_with_clickhouse(ib)

        resp = master_admin_client.get(
            reverse(
                "platform-report-data-views-list",
                kwargs={"organization_pk": organization.pk, "platform_pk": platform.pk},
            )
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        view = data[0]
        assert view["pk"] == rt.pk
        assert view["is_proxy"] is True
        assert view["is_standard_view"] is False

    @pytest.mark.clickhouse
    @pytest.mark.usefixtures("clickhouse_on_off")
    @pytest.mark.django_db(transaction=True)
    def test_api_list_for_platform_ordering(
        self, report_type_nd, master_admin_client, platform, organizations
    ):
        """
        Check that report data views are ordered by position in reply, not by name or short_name
        - for platform-report-data-views
        """
        rt = report_type_nd(0)
        ReportDataView.objects.create(base_report_type=rt, position=3, short_name="A", name="A")
        ReportDataView.objects.create(base_report_type=rt, position=1, short_name="X", name="X")
        ReportDataView.objects.create(base_report_type=rt, position=2, short_name="M", name="M")
        organization = organizations[0]
        # we need to add accesslog in order to connect platform and report-type
        ib = ImportBatchFactory(report_type=rt, organization=organization, platform=platform)
        AccessLog.objects.create(
            report_type=rt,
            organization=organization,
            platform=platform,
            value=1,
            date=ib.date,
            metric=Metric.objects.create(short_name="metric"),
            import_batch=ib,
        )
        # sync with clickhouse as we have circumvented the normal creation of accesslogs
        sync_import_batch_with_clickhouse(ib)

        resp = master_admin_client.get(
            reverse(
                "platform-report-data-views-list",
                kwargs={"organization_pk": organization.pk, "platform_pk": platform.pk},
            )
        )
        assert resp.status_code == 200
        data = resp.json()
        assert [rec["position"] for rec in data] == [1, 2, 3]

    @pytest.mark.clickhouse
    @pytest.mark.usefixtures("clickhouse_on_off")
    @pytest.mark.django_db(transaction=True)
    def test_api_list_for_platform_and_title_ordering(
        self, report_type_nd, master_admin_client, platform, organizations
    ):
        """
        Check that report data views are ordered by position in reply, not by name or short_name
        - for platform-report-data-views
        """
        rt = report_type_nd(0)
        ReportDataView.objects.create(base_report_type=rt, position=3, short_name="A", name="A")
        ReportDataView.objects.create(base_report_type=rt, position=1, short_name="X", name="X")
        ReportDataView.objects.create(base_report_type=rt, position=2, short_name="M", name="M")
        organization = organizations[0]
        title = Title.objects.create(name="Journal of Foo Bar")
        # we need to add accesslog in order to connect platform and report-type
        ib = ImportBatchFactory(report_type=rt, organization=organization, platform=platform)
        AccessLog.objects.create(
            report_type=rt,
            organization=organization,
            platform=platform,
            target=title,
            value=1,
            date=ib.date,
            metric=Metric.objects.create(short_name="metric"),
            import_batch=ib,
        )
        # sync with clickhouse as we have circumvented the normal creation of accesslogs
        sync_import_batch_with_clickhouse(ib)
        resp = master_admin_client.get(
            reverse(
                "platform-title-report-data-views-list",
                kwargs={
                    "organization_pk": organization.pk,
                    "platform_pk": platform.pk,
                    "title_pk": title.pk,
                },
            )
        )
        assert resp.status_code == 200
        data = resp.json()
        assert [rec["position"] for rec in data] == [1, 2, 3]


@pytest.mark.django_db
class TestChartsAPI:
    def test_api_list_simple(self, master_admin_client):
        """
        Simply test that the endpoint exists and returns some response
        """
        resp = master_admin_client.get(reverse("chart-definition-list"))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_api_list_full(self, master_admin_client, charts):
        """
        Test that the endpoint reports the currently defined charts
        """
        resp = master_admin_client.get(reverse("chart-definition-list"))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert {rec["pk"] for rec in data} == {ch.pk for ch in charts}

    @pytest.mark.parametrize("empty_view_id", [True, False])
    def test_api_report_data_view_list(self, master_admin_client, empty_view_id):
        """
        Test that the endpoint listing charts for a report_view works as expected
        """
        rv = ReportDataViewFactory.create()
        chart1, chart2 = ChartDefinitionFactory.create_batch(2)
        chart3 = ChartDefinitionFactory.create(is_generic=True)
        ReportViewToChartType.objects.create(
            report_data_view=rv, chart_definition=chart1, position=1
        )
        ReportViewToChartType.objects.create(
            report_data_view=rv, chart_definition=chart3, position=2
        )

        resp = master_admin_client.get(
            reverse("report-data-view-chart-definitions", args=(-1 if empty_view_id else rv.pk,))
        )
        assert resp.status_code == 200
        data = resp.json()
        if empty_view_id:
            assert len(data) == 1
            assert {rec["pk"] for rec in data} == {chart3.pk}
        else:
            assert len(data) == 2
            assert {rec["pk"] for rec in data} == {chart1.pk, chart3.pk}


@pytest.mark.django_db
class TestChartDataAPIView:
    def test_working_data(self, authenticated_client, simple_report_view):
        """
        Simply test that the endpoint exists and returns some response
        """
        response = authenticated_client.get(reverse("chart_data", args=(simple_report_view.pk,)))
        assert response.status_code == 200
        assert response.json()["data"] == []

    def test_bad_request(self, authenticated_client, simple_report_view):
        """
        Test that requesting a dimension that it not present in the requested ReportDateView
        return an error response
        """
        url = f"{reverse('chart_data', args=(simple_report_view.pk,))}?prim_dim=foobar"
        response = authenticated_client.get(url)
        assert response.status_code == 400
        error = response.json()["error"]
        assert "foobar" in error

    def test_with_data_no_dashboard(
        self, counter_records_0d, organizations, report_type_nd, authenticated_client, platform
    ):
        """
        Test that recache is not used for normal queries
        """
        organization = organizations[0]
        report_type: ReportType = report_type_nd(0)
        import_counter_records(report_type, organization, platform, counter_records_0d)
        assert AccessLog.objects.count() == 1
        metric = Metric.objects.get(interest_group__isnull=True)
        report_view = ReportDataView.objects.create(base_report_type=report_type)
        resp = authenticated_client.get(
            reverse("chart_data", args=(report_view.pk,)),
            {
                "organization": organization.pk,
                "metric": metric.pk,
                "platform": platform.pk,
                "prim_dim": "date",
            },
        )
        assert resp.status_code == 200
        assert "data" in resp.json()

    def test_with_data_dashboard(
        self,
        counter_records_0d,
        organizations,
        report_type_nd,
        authenticated_client,
        platform,
        interest_rt,
    ):
        """
        Test that recache is used for queries marked with the `dashboard` attribute
        """
        organization = organizations[0]
        report_type: ReportType = report_type_nd(0)
        import_counter_records(report_type, organization, platform, counter_records_0d)
        assert AccessLog.objects.count() == 1
        metric = Metric.objects.get(
            interest_group__isnull=True
        )  # the metric not connected to interest
        report_view = ReportDataView.objects.create(base_report_type=report_type)
        resp = authenticated_client.get(
            reverse("chart_data", args=(report_view.pk,)),
            {
                "organization": organization.pk,
                "metric": metric.pk,
                "platform": platform.pk,
                "prim_dim": "date",
                "dashboard": True,
            },
        )
        assert resp.status_code == 200
        assert "data" in resp.json()

    def test_available_metrics(
        self,
        counter_records_0d,
        organizations,
        report_type_nd,
        authenticated_client,
        platform,
        interest_rt,
    ):
        """
        Test the api for getting list of metrics used in a chart
        """
        organization = organizations[0]
        report_type: ReportType = report_type_nd(0)
        import_counter_records(report_type, organization, platform, counter_records_0d)
        assert AccessLog.objects.count() == 1
        metric = Metric.objects.get(interest_group__isnull=True)
        report_view = ReportDataView.objects.create(base_report_type=report_type)
        resp = authenticated_client.get(
            reverse("chart_data_metrics", args=(report_view.pk,)),
            {"organization": organization.pk, "platform": platform.pk, "prim_dim": "date"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["pk"] == metric.pk

    @pytest.mark.parametrize("use_materialized", [True, False])
    def test_with_mdu_filter(self, admin_client, use_materialized):
        """
        Test that MDU filter works properly when other data is present. Because of an issue
        we found with materialized report types, we are testing both with and without the use
        of materialized report types.
        """
        mdu1 = ManualDataUploadFullFactory.create(state=MduState.IMPORTED)
        ManualDataUploadFullFactory.create(state=MduState.IMPORTED, report_type=mdu1.report_type)
        if use_materialized:
            ms = ReportMaterializationSpec.objects.create(
                base_report_type=mdu1.report_type, name="mr", keep_target=False
            )
            mr = ReportType.objects.create(materialization_spec=ms, name="mr", short_name="mr")
            sync_materialized_reports()
            assert (
                AccessLog.objects.filter(report_type=mr).aggregate(Sum("value"))["value__sum"]
                == AccessLog.objects.filter(report_type=mdu1.report_type).aggregate(Sum("value"))[
                    "value__sum"
                ]
            ), "the materialized report should have the same data as the original report"

        report_view = ReportDataView.objects.create(base_report_type=mdu1.report_type)
        resp = admin_client.get(
            reverse("chart_data", args=(report_view.pk,)), {"prim_dim": "date", "mdu": mdu1.pk}
        )
        assert resp.status_code == 200
        assert "data" in resp.json()
        assert len(resp.json()["data"]) > 0
        assert (
            sum(rec["count"] for rec in resp.json()["data"])
            == AccessLog.objects.filter(
                import_batch__mdu=mdu1, report_type=mdu1.report_type
            ).aggregate(Sum("value"))["value__sum"]
        )


@pytest.mark.django_db
class TestReportingUrlAPI:
    """Test the reporting URL generation endpoints for both ReportDataView and ReportType"""

    def test_report_data_view_reporting_url_basic(self, master_admin_client, simple_report_view):
        """Test basic reporting URL generation for ReportDataView"""
        resp = master_admin_client.get(
            reverse("report-data-view-reporting-url", args=(simple_report_view.pk,)),
            {"primary_dimension": "date"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "params" in data
        params = data["params"]

        # Check that basic parameters are present
        assert "rt" in params
        assert "r" in params
        assert "c" in params
        assert "f" in params

        # Verify the primary dimension is correct
        assert params["r"] == "date"

        # Verify report type is encoded
        assert base64.b64decode(params["rt"]).decode("utf-8") == json.dumps(
            [simple_report_view.base_report_type.pk]
        )

    def test_report_data_view_reporting_url_with_all_params(
        self, master_admin_client, simple_report_view, organizations, platform
    ):
        """Test reporting URL generation with all possible parameters"""
        organization = organizations[0]
        metric = Metric.objects.create(short_name="test_metric")
        title = Title.objects.create(name="Test Title")

        resp = master_admin_client.get(
            reverse("report-data-view-reporting-url", args=(simple_report_view.pk,)),
            {
                "primary_dimension": "date",
                "secondary_dimension": "platform",
                "organization": organization.pk,
                "platform": platform.pk,
                "metric": metric.pk,
                "start_date": "2023-01",
                "end_date": "2023-12",
                "title": title.pk,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "params" in data
        params = data["params"]

        # Check all parameters are present
        assert "rt" in params  # report type
        assert "r" in params  # primary dimension
        assert "c" in params  # secondary dimension (groups)
        assert "org" in params  # organization
        assert "p" in params  # platform
        assert "m" in params  # metric
        assert "dr" in params  # date range
        assert "tt" in params  # title tag
        assert "f" in params  # filters

        # Verify primary dimension
        assert params["r"] == "date"

        # Verify secondary dimension is encoded as list
        decoded_secondary = json.loads(base64.b64decode(params["c"]).decode())
        assert decoded_secondary == ["platform"]

        # Verify organization is encoded
        decoded_org = json.loads(base64.b64decode(params["org"]).decode())
        assert decoded_org == [organization.pk]

        # Verify platform is encoded
        decoded_platform = json.loads(base64.b64decode(params["p"]).decode())
        assert decoded_platform == [platform.pk]

        # Verify metric is encoded
        decoded_metric = json.loads(base64.b64decode(params["m"]).decode())
        assert decoded_metric == [metric.pk]

        # Verify date range
        decoded_date_range = json.loads(base64.b64decode(params["dr"]).decode())
        assert decoded_date_range == {"start": "2023-01", "end": "2023-12"}

        # Verify title tag was created and encoded
        assert params["tt"].startswith("--")
        decoded_title_tag = json.loads(base64.b64decode(params["tt"]).decode())
        title_tag = Tag.objects.filter(name=f"ID_{title.pk}").first()
        assert title_tag is not None
        assert decoded_title_tag == [title_tag.pk]

    def test_report_data_view_reporting_url_with_dimension_filters(
        self, master_admin_client, report_type_nd
    ):
        """Test reporting URL generation with dimension filters"""
        rt = report_type_nd(1)  # Create report type with 1 dimension
        report_view = ReportDataView.objects.create(
            base_report_type=rt, metric_allowed_values=["metric1", "metric2"]
        )

        # Create a dimension filter
        DimensionFilter.objects.create(
            report_data_view=report_view,
            dimension=rt.dimensions_sorted[0],
            allowed_values=["value1", "value2"],
        )

        dt = DimensionTextFactory(dimension=rt.dimensions_sorted[0], text="value2")

        resp = master_admin_client.get(
            reverse("report-data-view-reporting-url", args=(report_view.pk,)),
            {"primary_dimension": "date"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "params" in data
        params = data["params"]

        # Check dimension values are present
        assert "dv" in params
        decoded_dv = json.loads(base64.b64decode(params["dv"]).decode())
        # Should be a list of lists for each dimension
        assert isinstance(decoded_dv, dict)
        assert any(e == [dt.pk] for e in decoded_dv.values()), (
            "At least one dimension should have value2"
        )

    def test_report_type_reporting_url_basic(self, master_admin_client, report_type_nd):
        """Test basic reporting URL generation for ReportType"""
        rt = report_type_nd(0)

        resp = master_admin_client.get(
            reverse("report-type-reporting-url", args=(rt.pk,)), {"primary_dimension": "date"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "params" in data
        params = data["params"]

        # Check that basic parameters are present
        assert "rt" in params
        assert "r" in params
        assert "c" in params
        assert "f" in params

        # Verify the primary dimension is correct
        assert params["r"] == "date"

        # Verify report type is encoded
        decoded_rt = json.loads(base64.b64decode(params["rt"]).decode())
        assert decoded_rt == [rt.pk]

    def test_report_type_reporting_url_with_controlled_metrics(
        self, master_admin_client, report_type_nd
    ):
        """Test reporting URL generation for ReportType with controlled metrics"""
        rt = report_type_nd(0)
        metric1 = Metric.objects.create(short_name="controlled_metric1")
        metric2 = Metric.objects.create(short_name="controlled_metric2")
        rt.controlled_metrics.add(metric1, metric2)

        resp = master_admin_client.get(
            reverse("report-type-reporting-url", args=(rt.pk,)),
            {"primary_dimension": "date", "metric": metric1.pk},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "params" in data
        params = data["params"]

        # Verify metric is included
        assert "m" in params
        decoded_metric = json.loads(base64.b64decode(params["m"]).decode())
        assert [metric1.pk] == decoded_metric

    def test_reporting_url_default_secondary_dimension(
        self, master_admin_client, simple_report_view
    ):
        """Test that default secondary dimension is 'platform' when not specified"""
        resp = master_admin_client.get(
            reverse("report-data-view-reporting-url", args=(simple_report_view.pk,)),
            {"primary_dimension": "date"},  # No secondary_dimension specified
        )
        assert resp.status_code == 200
        data = resp.json()
        params = data["params"]

        # Verify default secondary dimension is platform
        decoded_secondary = json.loads(base64.b64decode(params["c"]).decode())
        assert decoded_secondary == ["platform"]

    def test_reporting_url_with_only_start_date(self, master_admin_client, simple_report_view):
        """Test reporting URL with only start_date (no end_date)"""
        resp = master_admin_client.get(
            reverse("report-data-view-reporting-url", args=(simple_report_view.pk,)),
            {"primary_dimension": "date", "start_date": "2023-01"},
        )
        assert resp.status_code == 200
        data = resp.json()
        params = data["params"]

        # Verify date range contains only start
        decoded_date_range = json.loads(base64.b64decode(params["dr"]).decode())
        assert decoded_date_range == {"start": "2023-01"}

    def test_reporting_url_with_only_end_date(self, master_admin_client, simple_report_view):
        """Test reporting URL with only end_date (no start_date)"""
        resp = master_admin_client.get(
            reverse("report-data-view-reporting-url", args=(simple_report_view.pk,)),
            {"primary_dimension": "date", "end_date": "2023-12"},
        )
        assert resp.status_code == 200
        data = resp.json()
        params = data["params"]

        # Verify date range contains only end
        decoded_date_range = json.loads(base64.b64decode(params["dr"]).decode())
        assert decoded_date_range == {"end": "2023-12"}

    def test_reporting_primary_secondary_dimension_conversion(
        self, master_admin_client, report_type_nd
    ):
        """Tests that primary and secondary dimensions are converted (Data_Type -> dim1)"""

        rt = report_type_nd(2, ["First", "Second"])

        resp = master_admin_client.get(
            reverse("report-type-reporting-url", args=(rt.pk,)),
            {"primary_dimension": "First", "secondary_dimension": "Second"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "params" in data
        params = data["params"]

        assert params["r"] == "dim1", "Primary dimension converted"
        assert json.loads(base64.b64decode(params["c"])) == ["dim2"], (
            "Secondary dimension converted"
        )

    def test_reporting_url_nonexistent_title(self, master_admin_client, simple_report_view):
        """Test that nonexistent title is handled gracefully (no title tag created)"""
        resp = master_admin_client.get(
            reverse("report-data-view-reporting-url", args=(simple_report_view.pk,)),
            {
                "primary_dimension": "date",
                "title": 999999,  # Non-existent title
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        params = data["params"]

        # Should not contain title tag parameter
        assert "tt" not in params or params["tt"] == ""
        assert params.get("tt", "") == ""

    def test_reporting_url_metric_combination(self, master_admin_client, simple_report_view):
        """Test that metric from params is combined with allowed metrics from view"""
        # Create a report view with allowed metrics
        rt = simple_report_view.base_report_type
        report_view = ReportDataView.objects.create(
            base_report_type=rt, metric_allowed_values=["allowed_metric1", "allowed_metric2"]
        )

        # Create metrics
        param_metric = Metric.objects.create(short_name="param_metric")
        Metric.objects.create(short_name="allowed_metric1")
        allowed_metric2 = Metric.objects.create(short_name="allowed_metric2")

        resp = master_admin_client.get(
            reverse("report-data-view-reporting-url", args=(report_view.pk,)),
            {"primary_dimension": "date", "metric": param_metric.pk},
        )
        assert resp.status_code == 200
        data = resp.json()
        params = data["params"]

        # Verify that no metric is included
        decoded_metric = json.loads(base64.b64decode(params["m"]).decode())
        assert decoded_metric == []

        resp = master_admin_client.get(
            reverse("report-data-view-reporting-url", args=(report_view.pk,)),
            {"primary_dimension": "date", "metric": allowed_metric2.pk},
        )
        assert resp.status_code == 200
        data = resp.json()
        params = data["params"]

        # Verify allowed_metric2 is included
        decoded_metric = json.loads(base64.b64decode(params["m"]).decode())
        assert decoded_metric == [allowed_metric2.pk]

    def test_reporting_url_tag_class_creation(self, master_admin_client, simple_report_view):
        """Test that TagClass for title filtering is created properly"""
        title = Title.objects.create(name="Test Title for Tags")

        # Ensure no tag class exists initially
        assert not TagClass.objects.filter(name="Title Filter").exists()

        resp = master_admin_client.get(
            reverse("report-data-view-reporting-url", args=(simple_report_view.pk,)),
            {"primary_dimension": "date", "title": title.pk},
        )
        assert resp.status_code == 200

        # Verify TagClass was created with correct properties
        tag_class = TagClass.objects.get(name="Title Filter")
        assert tag_class.internal is True
        assert tag_class.exclusive is True

        # Verify Tag was created
        tag = Tag.objects.get(name=f"ID_{title.pk}")
        assert tag.tag_class == tag_class
