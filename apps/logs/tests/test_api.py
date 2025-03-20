import csv
import json
import locale
from datetime import date, timedelta
from io import StringIO
from unittest.mock import Mock, patch

import pytest
from core.logic.dates import month_end, month_start
from core.tests.conftest import (  # noqa - fixtures
    admin_identity,  # noqa - fixtures
    authenticated_client,
    authentication_headers,
    invalid_identity,
    master_admin_client,
    master_admin_identity,
    valid_identity,
)
from django.db.models import Max, Min
from django.urls import reverse
from freezegun import freeze_time
from organizations.models import UserOrganization
from publications.fake_data import ItemFactory, PlatformFactory, TitleFactory
from publications.tests.conftest import interest_rt  # noqa - fixtures
from publications.tests.test_api import (  # noqa - fixtures
    real_world_data_with_interest,
    real_world_data_with_interest_and_configs,
)
from sushi.fake_data import CredentialsFactory, FetchAttemptFactory
from sushi.models import AttemptStatus, CounterReportsToCredentials, SushiFetchAttempt

from logs.fake_data import (
    ImportBatchFactory,
    ImportBatchFullFactory,
    InterestGroupFactory,
    ManualDataUploadFactory,
    ManualDataUploadFullFactory,
    ReportTypeFactory,
)
from logs.logic.interest.computation import (
    sync_interest_by_import_batches,
    sync_interest_for_import_batch,
)
from logs.models import (
    AccessLog,
    Dimension,
    DimensionText,
    ImportBatch,
    MduMethod,
    Metric,
    ReportInterestMetric,
    ReportMaterializationSpec,
    ReportType,
)
from test_scenarios.basic import (  # noqa - fixtures
    basic1,
    client_by_user_type,
    clients,
    counter_report_types,
    data_sources,
    identities,
    interests,
    metrics,
    organizations,
    platforms,
    report_types,
    users,
)

from ..logic.clickhouse import sync_accesslogs_with_clickhouse_superfast
from ..logic.data_import import import_counter_records
from ..logic.export import CSVExport
from ..logic.materialized_reports import sync_materialized_reports


@pytest.mark.django_db
class TestChartDataAPI:
    """
    Tests functionality of the view chart-data
    """

    def test_api_simple_data_0d(
        self, counter_records_0d, organizations, report_type_nd, authenticated_client
    ):
        platform = PlatformFactory(short_name="Platform1")
        organization = organizations["branch"]
        report_type: ReportType = report_type_nd(0)
        import_counter_records(report_type, organization, platform, counter_records_0d)
        assert AccessLog.objects.count() == 1
        metric = Metric.objects.get()
        resp = authenticated_client.get(
            reverse("chart_data_raw", args=(report_type.pk,)),
            {
                "organization": organization.pk,
                "metric": metric.pk,
                "platform": platform.pk,
                "prim_dim": "date",
            },
        )
        assert resp.status_code == 200
        assert "data" in resp.json()

    def test_api_simple_data_0d_with_recache(
        self, counter_records_0d, organizations, report_type_nd, authenticated_client
    ):
        platform = PlatformFactory(short_name="Platform1")
        organization = organizations["branch"]
        report_type: ReportType = report_type_nd(0)
        import_counter_records(report_type, organization, platform, counter_records_0d)
        assert AccessLog.objects.count() == 1
        metric = Metric.objects.get()
        resp = authenticated_client.get(
            reverse("chart_data_raw", args=(report_type.pk,)),
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

    @pytest.mark.parametrize(
        "primary_dim, secondary_dim, count",
        [
            ["date", None, 3],  # three months
            ["date", 1, 4],  # two values in first month
            [1, None, 2],  # two values in first dim
            [2, None, 3],  # three values in first dim
            [2, 3, 4],  # four combinations of dim2 and dim3
            ["platform", None, 1],  # just one platform
        ],
    )
    def test_api_secondary_dim(
        self,
        counter_records,
        organizations,
        report_type_nd,
        primary_dim,
        secondary_dim,
        count,
        authenticated_client,
    ):
        platform = PlatformFactory(short_name="Platform1")
        data = [
            ["Title1", "2018-01-01", "1v1", "2v1", "3v1", 1],
            ["Title1", "2018-01-01", "1v2", "2v1", "3v1", 2],
            ["Title2", "2018-01-01", "1v2", "2v2", "3v1", 4],
            ["Title1", "2018-02-01", "1v1", "2v1", "3v1", 8],
            ["Title2", "2018-02-01", "1v1", "2v2", "3v2", 16],
            ["Title1", "2018-03-01", "1v1", "2v3", "3v2", 32],
        ]
        crs = counter_records(data, metric="Hits", platform="Platform1")
        organization = organizations["branch"]
        report_type = report_type_nd(3)
        import_counter_records(report_type, organization, platform, crs)
        assert AccessLog.objects.count() == 6
        metric = Metric.objects.get(short_name="Hits")
        if isinstance(primary_dim, int):
            primary_dim = report_type.dimensions_sorted[primary_dim - 1].short_name
        params = {
            "organization": organization.pk,
            "metric": metric.pk,
            "platform": platform.pk,
            "prim_dim": primary_dim,
        }
        if secondary_dim:
            params["sec_dim"] = report_type.dimensions_sorted[secondary_dim - 1].short_name
        resp = authenticated_client.get(reverse("chart_data_raw", args=(report_type.pk,)), params)
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert "data" in data
        assert len(data["data"]) == count

    @pytest.mark.parametrize(
        "primary_dim, secondary_dim, result",
        [
            ["date", None, [{"date": "2018-01-01", "count": 3}]],
            ["date", 3, [{"date": "2018-01-01", "dim2": "3v1", "count": 3}]],
            [
                "date",
                1,
                [
                    {"date": "2018-01-01", "dim0": "1v1", "count": 1},
                    {"date": "2018-01-01", "dim0": "1v2", "count": 2},
                ],
            ],
            ["platform", None, [{"platform": "Platform1", "count": 3}]],
            ["platform", "metric", [{"platform": "Platform1", "metric": "Hits", "count": 3}]],
            ["metric", "platform", [{"platform": "Platform1", "metric": "Hits", "count": 3}]],
            ["organization", None, [{"organization": "branch", "count": 3}]],
            ["organization", "metric", [{"organization": "branch", "metric": "Hits", "count": 3}]],
            ["metric", "organization", [{"organization": "branch", "metric": "Hits", "count": 3}]],
        ],
    )
    def test_api_values(
        self,
        counter_records,
        organizations,
        report_type_nd,
        primary_dim,
        secondary_dim,
        result,
        master_admin_client,
        interest_rt,
    ):
        platform = PlatformFactory(short_name="Platform1")
        data = [
            ["Title1", "2018-01-01", "1v1", "2v1", "3v1", 1],
            ["Title1", "2018-01-01", "1v2", "2v1", "3v1", 2],
        ]
        crs = counter_records(data, metric="Hits", platform="Platform1")
        organization = organizations["branch"]
        report_type = report_type_nd(3)
        import_counter_records(report_type, organization, platform, crs)
        assert AccessLog.objects.count() == 2
        metric = Metric.objects.get(short_name="Hits")
        params = {
            "organization": organization.pk,
            "metric": metric.pk,
            "platform": platform.pk,
            "prim_dim": primary_dim,
        }
        if secondary_dim:
            if isinstance(secondary_dim, int):
                params["sec_dim"] = report_type.dimensions_sorted[secondary_dim - 1].short_name
            else:
                params["sec_dim"] = secondary_dim
        resp = master_admin_client.get(reverse("chart_data_raw", args=(report_type.pk,)), params)
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert "data" in data
        assert data["data"] == result

    def test_api_filtering(
        self, counter_records, organizations, report_type_nd, authenticated_client
    ):
        platform1 = PlatformFactory(short_name="Platform1")
        platform2 = PlatformFactory(short_name="Platform2")
        data1 = [
            ["Title1", "2018-01-01", "1v1", "2v1", "3v1", 1],
            ["Title2", "2018-01-01", "1v2", "2v1", "3v1", 2],
            ["Title3", "2018-01-01", "1v2", "2v1", "3v1", 4],
        ]
        data2 = [
            ["Title1", "2018-01-01", "1v1", "2v1", "3v1", 8],
            ["Title2", "2018-02-01", "1v1", "2v1", "3v1", 16],
            ["Title3", "2018-02-01", "1v2", "2v2", "3v1", 32],
        ]
        crs1 = list(counter_records(data1, metric="Hits", platform="Platform1"))
        crs2 = list(counter_records(data2, metric="Big Hits", platform="Platform2"))
        report_type = report_type_nd(3)
        import_counter_records(report_type, organizations["branch"], platform1, crs1)
        import_counter_records(report_type, organizations["branch"], platform2, crs1)
        import_counter_records(report_type, organizations["standalone"], platform1, crs1)
        import_counter_records(report_type, organizations["standalone"], platform2, crs2)
        assert AccessLog.objects.count() == 12
        Metric.objects.get(short_name="Hits")
        Metric.objects.get(short_name="Big Hits")

        def get_data(params):
            resp = authenticated_client.get(
                reverse("chart_data_raw", args=(report_type.pk,)), params
            )
            assert resp.status_code == 200
            result = json.loads(resp.content)
            assert "data" in result
            return result["data"]

        # no filter
        recs = get_data({"prim_dim": "date"})
        assert len(recs) == 2
        assert recs[0]["count"] == 3 * (1 + 2 + 4) + 8
        assert recs[1]["count"] == 16 + 32
        # organization filter
        recs = get_data({"organization": organizations["branch"].pk, "prim_dim": "date"})
        assert len(recs) == 1
        assert recs[0]["count"] == 2 * (1 + 2 + 4)
        # organization dim, platform filter
        recs = get_data({"platform": platform2.pk, "prim_dim": "organization"})
        assert len(recs) == 2
        assert recs[0]["count"] == 1 + 2 + 4
        assert recs[1]["count"] == 8 + 16 + 32
        # filter by dim1, platform dim
        recs = get_data({"dim0": "1v1", "prim_dim": "platform"})
        assert len(recs) == 2
        assert recs[0]["count"] == 2 * 1
        assert recs[1]["count"] == 1 + 8 + 16
        # filter by dim2, platform and title dim
        recs = get_data({"dim0": "1v1", "prim_dim": "platform", "sec_dim": "target"})
        assert len(recs) == 3
        assert recs[0]["count"] == 2 * 1  # platform 1 and title 1
        assert recs[1]["count"] == 1 + 8  # platform 2 and title 1
        assert recs[2]["count"] == 16  # platform 2 and title 2
        # filter by date
        recs = get_data({"date": "2018-02-01", "prim_dim": "target"})
        assert len(recs) == 2
        assert recs[0]["count"] == 16
        assert recs[1]["count"] == 32
        # filter by date range
        recs = get_data({"start": "2018-02", "end": "2018-02", "prim_dim": "target"})
        assert len(recs) == 2
        assert recs[0]["count"] == 16
        assert recs[1]["count"] == 32

    @pytest.mark.parametrize(
        "primary_dim, secondary_dim, count",
        [
            ["date", None, 3],  # three months
            ["date", 1, 4],  # two values in first month
            [1, None, 2],  # two values in first dim
            [2, None, 3],  # three values in first dim
            [2, 3, 4],  # four combinations of dim2 and dim3
            ["platform", None, 1],  # just one platform
        ],
    )
    def test_api_secondary_dim_no_title(
        self,
        counter_records,
        organizations,
        report_type_nd,
        primary_dim,
        secondary_dim,
        count,
        authenticated_client,
    ):
        """
        Copy of the same test as test_api_secondary_dim but with title set to None
        """
        platform = PlatformFactory(short_name="Platform1")
        data = [
            [None, "2018-01-01", "1v1", "2v1", "3v1", 1],
            [None, "2018-01-01", "1v2", "2v1", "3v1", 2],
            [None, "2018-01-01", "1v2", "2v2", "3v1", 4],
            [None, "2018-02-01", "1v1", "2v1", "3v1", 8],
            [None, "2018-02-01", "1v1", "2v2", "3v2", 16],
            [None, "2018-03-01", "1v1", "2v3", "3v2", 32],
        ]
        crs = counter_records(data, metric="Hits", platform="Platform1")
        organization = organizations["branch"]
        report_type = report_type_nd(3)
        import_counter_records(report_type, organization, platform, crs)
        assert AccessLog.objects.count() == 6
        metric = Metric.objects.get(short_name="Hits")
        if isinstance(primary_dim, int):
            primary_dim = report_type.dimensions_sorted[primary_dim - 1].short_name
        params = {
            "organization": organization.pk,
            "metric": metric.pk,
            "platform": platform.pk,
            "prim_dim": primary_dim,
        }
        if secondary_dim:
            params["sec_dim"] = report_type.dimensions_sorted[secondary_dim - 1].short_name
        resp = authenticated_client.get(reverse("chart_data_raw", args=(report_type.pk,)), params)
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert "data" in data
        assert len(data["data"]) == count

    def test_api_date_year_query(
        self, counter_records, organizations, report_type_nd, authenticated_client
    ):
        platform = PlatformFactory(short_name="Platform1")
        data = [
            ["Title1", "2018-01-01", "1v1", 1],
            ["Title1", "2018-02-01", "1v1", 2],
            ["Title2", "2018-03-01", "1v2", 4],
            ["Title1", "2019-01-01", "1v1", 8],
        ]
        crs = counter_records(data, metric="Hits", platform="Platform1")
        organization = organizations["branch"]
        report_type = report_type_nd(1)
        import_counter_records(report_type, organization, platform, crs)
        assert AccessLog.objects.count() == 4
        metric = Metric.objects.get(short_name="Hits")
        # check it without year first
        params = {
            "organization": organization.pk,
            "metric": metric.pk,
            "platform": platform.pk,
            "prim_dim": "date",
        }
        resp = authenticated_client.get(reverse("chart_data_raw", args=(report_type.pk,)), params)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 4
        # now try years
        params["prim_dim"] = "date__year"
        resp = authenticated_client.get(reverse("chart_data_raw", args=(report_type.pk,)), params)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 2
        assert data["data"][0]["count"] == 7

    @pytest.mark.parametrize(
        ("global_interest_config", "org_interest_config", "exp_value"),
        ((True, True, 1), (True, False, 9), (False, True, 1), (False, False, 15)),
    )
    def test_api_interest_config(
        self,
        real_world_data_with_interest_and_configs,
        authenticated_client,
        global_interest_config,
        org_interest_config,
        exp_value,
    ):
        """
        Test that interest is properly filtered by interest config if requested from chart data API
        """
        organization = real_world_data_with_interest_and_configs["organization"]
        platform = real_world_data_with_interest_and_configs["platform"]
        report_type = real_world_data_with_interest_and_configs["interest_rt"]
        # remove unused interest configs
        if not global_interest_config:
            real_world_data_with_interest_and_configs["global_interest_config"].delete()
        if not org_interest_config:
            real_world_data_with_interest_and_configs["org_interest_config"].delete()
        # check that the data is filtered by the interest config
        params = {
            "organization": organization.pk,
            "platform": platform.pk,
            "prim_dim": "date",
            "sec_dim": "metric",
        }
        resp = authenticated_client.get(reverse("chart_data_raw", args=(report_type.pk,)), params)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["count"] == exp_value

    @pytest.mark.parametrize(("global_interest_config", "exp_value"), ((True, 9), (False, 15)))
    def test_api_interest_config_whole_consortium(
        self,
        real_world_data_with_interest_and_configs,
        authenticated_client,
        global_interest_config,
        exp_value,
    ):
        """
        Test that interest is properly filtered by interest config if the organization is set to -1
        """
        platform = real_world_data_with_interest_and_configs["platform"]
        report_type = real_world_data_with_interest_and_configs["interest_rt"]
        # remove unused interest config
        if not global_interest_config:
            real_world_data_with_interest_and_configs["global_interest_config"].delete()
        # check that the data is filtered by the interest config
        params = {
            "organization": "-1",
            "platform": platform.pk,
            "prim_dim": "date",
            "sec_dim": "metric",
        }
        resp = authenticated_client.get(reverse("chart_data_raw", args=(report_type.pk,)), params)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["count"] == exp_value


@pytest.mark.django_db
class TestManualDataUpload:
    def test_create_manual_data_upload(
        self, organizations, master_admin_client, report_type_nd, tmp_path, settings
    ):
        platform = PlatformFactory(short_name="Platform1")
        report_type = report_type_nd(0)
        file = StringIO("Source,2019-01\naaaa,9\n")
        settings.MEDIA_ROOT = tmp_path
        file.name = "input.csv"
        response = master_admin_client.post(
            reverse("manual-data-upload-list"),
            data={
                "platform": platform.id,
                "organization": organizations["branch"].pk,
                "report_type_id": report_type.pk,
                "data_file": file,
                "method": MduMethod.CELUS,
            },
        )
        assert response.status_code == 201

    def test_create_manual_data_upload_wrong_filename(
        self, organizations, master_admin_client, report_type_nd, tmp_path, settings
    ):
        platform = PlatformFactory(short_name="Platform1")
        report_type = report_type_nd(0)
        file = StringIO("Source,2019-01\naaaa,9\n")
        settings.MEDIA_ROOT = tmp_path
        file.name = "input.txt"
        response = master_admin_client.post(
            reverse("manual-data-upload-list"),
            data={
                "platform": platform.id,
                "organization": organizations["branch"].pk,
                "report_type_id": report_type.pk,
                "data_file": file,
                "method": MduMethod.CELUS,
            },
        )
        assert response.status_code == 400
        assert "wrong_file_format" in response.data


@pytest.mark.django_db
class TestReportTypeAPI:
    def test_list_organization_report_types(self, organizations, clients, basic1, report_types):
        organization = organizations["root"]
        response = clients["admin1"].get(
            reverse("organization-report-types-list", kwargs={"organization_pk": organization.pk})
        )
        assert response.status_code == 200
        assert len(response.json()) == ReportType.objects.count()

    def test_list_organization_report_types_used(
        self, organizations, clients, basic1, report_types
    ):
        organization = organizations["root"]
        assert ReportType.objects.count() > 0
        # test with many report types but none connected to organization
        response = clients["admin1"].get(
            reverse("organization-report-types-used", kwargs={"organization_pk": organization.pk})
        )
        assert response.status_code == 200
        assert response.json() == []
        # connect one report type to organization
        ImportBatchFullFactory(report_type=ReportType.objects.first(), organization=organization)
        response = clients["admin1"].get(
            reverse("organization-report-types-used", kwargs={"organization_pk": organization.pk})
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_create_report_type_400(self, organizations, authenticated_client):
        organization = organizations["branch"]
        assert ReportType.objects.count() == 0
        response = authenticated_client.post(
            reverse("organization-report-types-list", kwargs={"organization_pk": organization.pk}),
            {
                "short_name": "TEST",
                "name_cs": "Test report",
                "name_en": "Test report",
                "name": "Test report",
                "dimensions": [],
            },
            content_type="application/json",
        )
        assert response.status_code == 400
        assert b"cannot access" in response.content
        assert ReportType.objects.count() == 0, "no new ReportType was created"

    def test_create_report_type(self, organizations, authenticated_client):
        organization = organizations["branch"]
        # bind the user to the organization
        UserOrganization.objects.create(user=authenticated_client.user, organization=organization)
        assert ReportType.objects.count() == 0
        response = authenticated_client.post(
            reverse("organization-report-types-list", kwargs={"organization_pk": organization.pk}),
            {
                "short_name": "TEST",
                "name_cs": "Test report",
                "name_en": "Test report",
                "name": "Test report",
                "dimensions": [],
            },
            content_type="application/json",
        )
        assert response.status_code == 201
        assert ReportType.objects.count() == 1, "a new ReportType was created"
        rt = ReportType.objects.get()
        assert len(rt.dimensions_sorted) == 0, "no extra dimensions for ReportType"

    def test_create_report_type_with_dimension(self, organizations, authenticated_client):
        organization = organizations["branch"]
        # bind the user to the organization
        UserOrganization.objects.create(user=authenticated_client.user, organization=organization)
        assert ReportType.objects.count() == 0
        dim1 = Dimension.objects.create(short_name="dim1", name="Dimension 1")
        dim2 = Dimension.objects.create(short_name="dim2", name="Dimension 2")
        response = authenticated_client.post(
            reverse("organization-report-types-list", kwargs={"organization_pk": organization.pk}),
            {
                "short_name": "TEST",
                "name_cs": "Test report",
                "name_en": "Test report",
                "name": "Test report",
                "dimensions": [dim1.pk, dim2.pk],
                "public": False,
            },
            content_type="application/json",
        )
        assert response.status_code == 201
        assert ReportType.objects.count() == 1, "a new ReportType was created"
        rt = ReportType.objects.get()
        assert len(rt.dimensions_sorted) == 2

    def test_create_report_type_with_invalid_dimension(self, organizations, authenticated_client):
        organization = organizations["branch"]
        # bind the user to the organization
        UserOrganization.objects.create(user=authenticated_client.user, organization=organization)
        assert ReportType.objects.count() == 0
        dim1 = Dimension.objects.create(short_name="dim1", name="Dimension 1")
        response = authenticated_client.post(
            reverse("organization-report-types-list", kwargs={"organization_pk": organization.pk}),
            {
                "short_name": "TEST",
                "name_cs": "Test report",
                "name_en": "Test report",
                "name": "Test report",
                "dimensions": [dim1.pk, dim1.pk + 1],
            },
            content_type="application/json",
        )
        assert response.status_code == 400
        assert ReportType.objects.count() == 0
        assert "object does not exist" in response.json()["dimensions"][0]


@pytest.mark.django_db
class TestRawDataExport:
    @pytest.mark.parametrize(
        ["user_type", "can_access"],
        [
            ["no_user", False],
            ["invalid", False],
            ["unrelated", False],
            ["related_user", True],
            ["related_admin", True],
            ["master_admin", True],
            ["master_user", True],
            ["superuser", True],
        ],
    )
    def test_raw_export_start_organization_access(self, user_type, can_access, client_by_user_type):
        client, org = client_by_user_type(user_type)
        url = reverse("raw_data_export")
        with patch("logs.views.export_raw_data_task") as export_task:
            resp = client.post(url + f"?organization={org.pk}", content_type="application/json")
            expected_status_code = (200,) if can_access else (401, 403)
            assert resp.status_code in expected_status_code
            if can_access:
                export_task.delay.assert_called()
            else:
                export_task.delay.assert_not_called()

    @pytest.mark.parametrize(
        ["user_type", "can_access"],
        [
            ["no_user", False],
            ["invalid", False],
            ["unrelated", False],
            ["related_user", False],
            ["related_admin", False],
            ["master_admin", True],
            ["master_user", True],
            ["superuser", True],
        ],
    )
    def test_raw_export_start_no_organization_access(
        self, user_type, can_access, client_by_user_type
    ):
        client, org = client_by_user_type(user_type)
        url = reverse("raw_data_export")
        with patch("logs.views.export_raw_data_task") as export_task:
            resp = client.post(url, content_type="application/json")
            expected_status_code = (200,) if can_access else (401, 403)
            assert resp.status_code in expected_status_code
            if can_access:
                export_task.delay.assert_called()
            else:
                export_task.delay.assert_not_called()

    @pytest.mark.clickhouse
    @pytest.mark.django_db(transaction=True)
    def test_raw_export_get_count(
        self, master_admin_client, clickhouse_on_off, flexible_slicer_test_data, interest_rt
    ):
        """
        Test that the raw data export endpoint returns the expected record count. We use the
        test data from the flexible slicer tests.
        """
        if clickhouse_on_off:
            # the data from the flexible_slicer_test_data fixture are not influenced by the
            # clickhouse_on_off fixture, so we need to sync the data manually
            sync_accesslogs_with_clickhouse_superfast()
        url = reverse("raw_data_export")
        resp = master_admin_client.get(url)
        assert resp.status_code == 200
        assert resp["Content-Type"] == "application/json"
        data = resp.json()
        assert data["total_count"] == 4860, "total count of records without any interest"
        rt1 = flexible_slicer_test_data["report_types"][0]
        m1 = flexible_slicer_test_data["metrics"][0]
        ig = InterestGroupFactory.create()
        ReportInterestMetric.objects.create(report_type=rt1, metric=m1, interest_group=ig)
        sync_interest_by_import_batches()
        assert interest_rt.accesslog_set.count() == 108
        # retry the export
        resp = master_admin_client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        # rt1 has 972 records (1/5), from that interest is for
        # (all platforms, 1/3 report types, 1/3 metrics) = 972/9 = 108
        assert data["total_count"] == 4860 + 108, "total count of records with interest"
        # add materialized interest
        mat_spec = ReportMaterializationSpec.objects.create(
            name="x", base_report_type=interest_rt, keep_target=False
        )
        mat_rt = ReportTypeFactory.create(materialization_spec=mat_spec, dimensions=[])
        sync_materialized_reports()
        assert mat_rt.accesslog_set.count() > 0
        # try the export again - the materialized report should not be included
        resp = master_admin_client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 4860 + 108, "total count of records with interest, no mat rt"

    @pytest.mark.clickhouse
    @pytest.mark.django_db(transaction=True)
    def test_raw_export_itself(
        self, master_admin_client, clickhouse_on_off, flexible_slicer_test_data, interest_rt
    ):
        """
        Test that the raw data export produces the expected data - both with and without clickhouse
        """
        if clickhouse_on_off:
            # the data from the flexible_slicer_test_data fixture are not influenced by the
            # clickhouse_on_off fixture, so we need to sync the data manually
            sync_accesslogs_with_clickhouse_superfast()
        # prepare the data similarly to `test_raw_export_get_count` - see that test for details
        rt1 = flexible_slicer_test_data["report_types"][0]
        m1 = flexible_slicer_test_data["metrics"][0]
        ig = InterestGroupFactory.create()
        ReportInterestMetric.objects.create(report_type=rt1, metric=m1, interest_group=ig)
        sync_interest_by_import_batches()
        mat_spec = ReportMaterializationSpec.objects.create(
            name="x", base_report_type=interest_rt, keep_target=False
        )
        ReportTypeFactory.create(materialization_spec=mat_spec, dimensions=[])
        sync_materialized_reports()
        # call the export using API, but mock the important parts to be able to test the internals
        url = reverse("raw_data_export")
        with patch("logs.views.export_raw_data_task") as export_task, patch(
            "logs.views.CSVExport"
        ) as exporter:
            exporter.return_value = Mock(filename_base="foo", file_url="http://foo.bar")
            resp = master_admin_client.post(url)
            assert resp.status_code == 200
            assert export_task.delay.called
            assert exporter.called
            # now we take the exporter and call it directly to get the data
            exp = CSVExport(*exporter.call_args[0], **exporter.call_args[1])
            assert exp.record_count == 4860 + 108
            # the data
            out = StringIO()
            # the code below fails wheh clickhouse is used because it uses dictionaries which are
            # not yet
            # also, we use more internal api in order to be able to use in-memory data storage
            exp.export_raw_accesslogs_to_stream_lowlevel(out)
            out.seek(0)
            reader = csv.reader(out)
            assert len(list(reader)) == 4860 + 108 + 1, "header row + all records"


@pytest.fixture
def dimension_texts():
    dim1 = Dimension.objects.create(short_name="dim1")
    dim2 = Dimension.objects.create(short_name="dim2")
    dt1 = DimensionText.objects.create(text="test1", dimension=dim1)
    dt2 = DimensionText.objects.create(text="test2", dimension=dim1)
    dt3 = DimensionText.objects.create(text="test3", dimension=dim2)
    return {dt1.text: dt1, dt2.text: dt2, dt3.text: dt3}


@pytest.mark.django_db
class TestDimensionTextAPI:
    def test_list_simple(self, admin_client):
        url = reverse("dimension-text-list")
        resp = admin_client.get(url)
        assert resp.status_code == 200

    def test_list_with_data(self, admin_client, dimension_texts):
        url = reverse("dimension-text-list")
        resp = admin_client.get(url)
        assert resp.status_code == 200
        assert resp.json()["count"] == DimensionText.objects.count()
        assert len(resp.json()["results"]) == DimensionText.objects.count()

    def test_list_with_selected_pks(self, admin_client, dimension_texts):
        url = reverse("dimension-text-list")
        dt_ids = [dimension_texts["test1"].pk, dimension_texts["test3"].pk]
        resp = admin_client.get(url, {"pks": ",".join(map(str, dt_ids))})
        assert resp.status_code == 200
        assert "count" not in resp.json(), "we do not paginate when using list of ids"
        assert set(dt_ids) == {rec["pk"] for rec in resp.json()}

    def test_list_via_post_with_selected_pks(self, admin_client, dimension_texts):
        """
        Test that the post method works the same a GET - we need this to support long lists of
        IDs passed to the endpoint
        """
        url = reverse("dimension-text-list")
        dt_ids = [dimension_texts["test1"].pk, dimension_texts["test3"].pk]
        resp = admin_client.post(url, {"pks": dt_ids}, content_type="application/json")
        assert resp.status_code == 200
        assert set(dt_ids) == {rec["pk"] for rec in resp.json()}
        assert "count" not in resp.json(), "we do not paginate POST results"


@pytest.mark.django_db
class TestImportBatchViewSet:
    def test_data_presence(self, admin_client, counter_report_types):
        # create a manual data upload which is one of the things that enter into the data presence
        # calculation
        mdu = ManualDataUploadFullFactory.create()
        assert AccessLog.objects.count() == 20
        mdu_date_range = AccessLog.objects.aggregate(min=Min("date"), max=Max("date"))
        start_date_mdu = mdu_date_range["min"]
        end_date_mdu = mdu_date_range["max"]

        # create fetch attempts - these are used for detecting data from SUSHI
        cr = CredentialsFactory.create(organization=mdu.organization, platform=mdu.platform)
        # the credentials from factory are not connected to the counter report type, do it here

        CounterReportsToCredentials.objects.create(
            credentials=cr, counter_report=counter_report_types["tr"]
        )
        # the counter_report_type should match the report_type created for the mdu
        end_date_fa = month_start(end_date_mdu + timedelta(days=40))
        FetchAttemptFactory.create(
            credentials=cr,
            status=AttemptStatus.SUCCESS,
            start_date=end_date_fa,
            end_date=month_end(end_date_fa),
            import_batch=ImportBatchFullFactory(
                date=end_date_fa,
                organization=cr.organization,
                platform=cr.platform,
                report_type=counter_report_types["tr"].report_type,
            ),
        )

        # test without params
        resp = admin_client.get(reverse("import-batch-data-presence"))
        assert resp.status_code == 400

        # test with params
        resp = admin_client.get(
            reverse("import-batch-data-presence"),
            {"start_date": str(start_date_mdu), "end_date": str(end_date_fa), "credentials": cr.pk},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2, "two months, the same organization, platform and report_type"

    @pytest.mark.parametrize("import_batch", ((True,), (False,)))
    def test_data_presence_attempt_ib(self, admin_client, import_batch):
        cr = CredentialsFactory.create()
        start_date = "2021-10-01"
        fa = FetchAttemptFactory.create(
            credentials=cr,
            status=AttemptStatus.SUCCESS,
            start_date=start_date,
            end_date="2021-10-31",
        )
        if import_batch:
            ib = ImportBatchFullFactory(
                date=start_date,
                platform=cr.platform,
                organization=cr.organization,
                report_type=fa.counter_report.report_type,
            )
            fa.import_batch = ib
            fa.save()

        # the credentials from factory are not connected to the counter report type, do it here
        CounterReportsToCredentials.objects.create(credentials=cr, counter_report=fa.counter_report)

        resp = admin_client.get(
            reverse("import-batch-data-presence"),
            {"start_date": start_date, "end_date": start_date, "credentials": cr.pk},
        )
        assert resp.status_code == 200
        data = resp.json()
        if import_batch:
            assert len(data) == 1, "import_batch present"
        else:
            assert len(data) == 0, "no import_batch => no data"

    @pytest.mark.parametrize(
        ["user_type", "can_access"],
        [
            ["no_user", False],
            ["invalid", False],
            ["unrelated", False],
            ["related_user", False],
            ["related_admin", True],
            ["master_admin", True],
            ["master_user", False],
            ["superuser", True],
        ],
    )
    def test_create_empty_import_batch_access(
        self, client_by_user_type, user_type, can_access, users
    ):
        """
        Test that the API for creating empty import batches works as expected and access rules
        are enforced.

        The API should be accessible only to users with the right permissions - org admins,
        consortial admins, or superusers.
        """
        client, org = client_by_user_type(user_type)
        # create failed harvest
        fa = FetchAttemptFactory.create(
            status=AttemptStatus.DOWNLOAD_FAILED,
            credentials__organization=org,
            start_date=date(2023, 10, 1),
        )
        assert fa.import_batch is None
        ib_check_qs = ImportBatch.objects.filter(
            organization=fa.credentials.organization,
            platform=fa.credentials.platform,
            report_type=fa.counter_report.report_type,
            date=fa.start_date,
        )
        assert ib_check_qs.count() == 0
        # call the API
        resp = client.post(
            reverse("import-batch-create-empty"),
            {
                "organization": fa.credentials.organization.pk,
                "platform": fa.credentials.platform.pk,
                "report_type": fa.counter_report.report_type.pk,
                "date": fa.start_date,
            },
        )
        if can_access:
            assert resp.status_code == 201
            assert ib_check_qs.count() == 1
            ib = ImportBatch.objects.get(pk=resp.json()["pk"])
            assert ib.pk == ib_check_qs.first().pk
            assert ib.manual_empty, "the import batch should be marked as manual empty"
            assert ib.user is not None, "the user should be set"
            assert ib.user == client.user_, "the user should be set"
        else:
            assert resp.status_code in (401, 403)
            assert ib_check_qs.count() == 0

    @pytest.mark.parametrize(
        ["check_date", "allowed"],
        [
            ("2023-10-01", False),
            ("2023-09-01", False),
            ("2023-11-01", False),
            ("2023-12-01", True),
            ("2024-01-01", True),
        ],
    )
    def test_create_empty_import_batch_month_range(self, admin_client, check_date, allowed):
        """
        It should only allow creating of empty import batches if the month is older than the
        currently harvested month.
        """
        # create failed harvest
        fa = FetchAttemptFactory.create(
            status=AttemptStatus.DOWNLOAD_FAILED, start_date=date(2023, 10, 1)
        )
        with freeze_time(check_date):
            resp = admin_client.post(
                reverse("import-batch-create-empty"),
                {
                    "organization": fa.credentials.organization.pk,
                    "platform": fa.credentials.platform.pk,
                    "report_type": fa.counter_report.report_type.pk,
                    "date": fa.start_date,
                },
            )
            if allowed:
                assert resp.status_code == 201
            else:
                assert resp.status_code == 400

    @pytest.mark.parametrize(
        ["matching_attempt", "allowed"],
        [(None, False), (AttemptStatus.SUCCESS, False), (AttemptStatus.DOWNLOAD_FAILED, True)],
    )
    def test_create_empty_import_batch_matching_attempt(
        self, admin_client, matching_attempt, allowed
    ):
        """
        It should only allow creation of empty import batches when there is a failed
        harvest for that organization,platform,report_type and data combination.
        """
        # create failed harvest
        fa = FetchAttemptFactory.create(
            status=matching_attempt or AttemptStatus.DOWNLOAD_FAILED, start_date=date(2023, 10, 1)
        )
        if not matching_attempt:
            # delete the SushiFetchAttempt, but keep the object
            # we do this because it creates all the necessary objects like credentials, etc.
            SushiFetchAttempt.objects.all().delete()
        resp = admin_client.post(
            reverse("import-batch-create-empty"),
            {
                "organization": fa.credentials.organization.pk,
                "platform": fa.credentials.platform.pk,
                "report_type": fa.counter_report.report_type.pk,
                "date": fa.start_date,
            },
        )
        if allowed:
            assert resp.status_code == 201
        else:
            assert resp.status_code == 400


@pytest.mark.django_db
class TestReportInterestMetricAPI:
    def test_get_report_interest_metric(
        self, authenticated_client, platforms, report_types, metrics, interests
    ):
        url = reverse("reporttype-list")
        resp = authenticated_client.get(url)
        assert resp.status_code == 200
        data = {e["short_name"]: e for e in resp.json()}
        assert len(data["TR"]["interest_metric_set"]) == 2
        assert len(data["DR"]["interest_metric_set"]) == 0
        assert len(data["JR1"]["interest_metric_set"]) == 2
        assert len(data["BR2"]["interest_metric_set"]) == 1


@pytest.mark.django_db
class TestRawDataAPI:
    def test_raw_data_ib(
        self, authenticated_client, report_types, interests, interest_rt, platforms
    ):
        # we need to use the right rt, platform and metric so that interest is defined
        ib = ImportBatchFullFactory.create(
            report_type=report_types["jr1"],
            platform=platforms["branch"],
            create_accesslogs__metrics=[Metric.objects.get(short_name="metric1")],
        )
        resp = authenticated_client.get(reverse("raw_data"), {"ib": ib.pk, "format": "json"})
        assert resp.status_code == 200
        data = resp.json()
        log_count = ib.accesslog_set.count()
        assert len(data) == log_count
        sync_interest_for_import_batch(ib, interest_rt)
        assert ib.accesslog_set.count() > log_count, "ib should have extra interest records"
        # recheck that there is no interest in the data
        resp = authenticated_client.get(
            reverse("raw_data"), {"import_batch": ib.pk, "format": "json"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert log_count == len(data), "interest data is not in the output"

    def test_raw_data_mdu(
        self, authenticated_client, report_types, interests, interest_rt, platforms
    ):
        """
        Test that the raw-data endpoint returns the correct data for a manual data upload.
        """
        ib = ImportBatchFullFactory.create(
            report_type=report_types["jr1"],
            platform=platforms["branch"],
            create_accesslogs__metrics=[Metric.objects.get(short_name="metric1")],
        )
        mdu = ManualDataUploadFactory.create(
            import_batches=[ib],
            report_type=report_types["jr1"],
            platform=platforms["branch"],
            organization=ib.organization,
        )
        assert mdu.import_batches.count() == 1
        resp = authenticated_client.get(reverse("raw_data"), {"mdu": mdu.pk, "format": "json"})
        assert resp.status_code == 200
        data = resp.json()
        log_count = mdu.accesslogs.count()
        assert len(data) == log_count
        sync_interest_for_import_batch(ib, interest_rt)
        assert mdu.accesslogs.count() > log_count, "ib should have extra interest records"
        # recheck that there is no interest in the data
        resp = authenticated_client.get(reverse("raw_data"), {"mdu": mdu.pk, "format": "json"})
        assert resp.status_code == 200
        data = resp.json()
        assert log_count == len(data), "interest data is not in the output"
        # check the format of the data
        rec = data[0]
        assert "date" in rec
        assert rec["report_type"] == "JR1"
        assert {"platform", "organization", "metric", "value"}.issubset(rec.keys())


@pytest.mark.django_db
class TestAccessLogListView:
    @pytest.mark.parametrize("page_size", (10, 100))
    @pytest.mark.parametrize(
        ["order_by", "desc"],
        [
            ("date", False),
            ("date", True),
            ("value", False),
            ("value", True),
            ("platform", False),
            ("platform", True),
            ("organization", False),
            ("organization", True),
            ("metric", False),
            ("metric", True),
            ("target", False),
            ("target", True),
        ],
    )
    def test_raw_data_mdu(
        self,
        master_admin_client,
        report_types,
        interests,
        interest_rt,
        platforms,
        order_by,
        desc,
        page_size,
    ):
        """
        Test that the access-log-list endpoint for mdu returns the correct data
        """
        jr1 = report_types["jr1"]
        branch_pl = platforms["branch"]
        ib = ImportBatchFullFactory.create(date="2021-01-01", report_type=jr1, platform=branch_pl)
        ib2 = ImportBatchFullFactory.create(
            date="2021-02-01", report_type=jr1, platform=branch_pl, organization=ib.organization
        )
        mdu = ManualDataUploadFactory.create(
            import_batches=[ib, ib2],
            report_type=jr1,
            platform=branch_pl,
            organization=ib.organization,
        )
        assert mdu.import_batches.count() == 2
        resp = master_admin_client.get(
            reverse("mdu-access-logs", args=[mdu.pk]),
            {"order_by": order_by, "desc": desc, "page_size": page_size},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == mdu.accesslogs.count()
        # check pagination
        assert len(data["results"]) == min(page_size, data["count"])
        # check the format of the data
        rec = data["results"][0]
        assert "date" in rec
        assert rec["report_type"] == "JR1"
        assert {"platform", "organization", "metric", "value", "target"}.issubset(rec.keys())
        # check ordering
        last_value = None
        # we need to set some UTF-8 locale to get correct sorting
        locale.setlocale(locale.LC_ALL, "en_US.UTF8")
        for rec in data["results"]:
            value = rec[order_by]
            if isinstance(value, str):
                # database uses unicode collation, which sorts differently than python
                # in presence of spaces. So we need to use unicode sort order as well
                value = locale.strxfrm(value)
            if last_value is not None:
                if desc:
                    assert value <= last_value
                else:
                    assert value >= last_value
            last_value = value

    @pytest.mark.parametrize("desc", (True, False))
    def test_raw_data_mdu_locale_sorting(
        self, master_admin_client, report_types, interests, interest_rt, platforms, desc
    ):
        """
        Similar to `test_raw_data_mdu` but with hardcoded title names which sort differently
        in unicode (db) and ascii (python)
        """
        jr1 = report_types["jr1"]
        branch_pl = platforms["branch"]
        t1 = TitleFactory.create(name="Evening black section big then thank per.")
        t2 = TitleFactory.create(name="Even owner else daughter series.")
        ib = ImportBatchFullFactory.create(
            date="2021-01-01", report_type=jr1, platform=branch_pl, create_accesslogs__titles=[t1]
        )
        ib2 = ImportBatchFullFactory.create(
            date="2021-02-01",
            report_type=jr1,
            platform=branch_pl,
            organization=ib.organization,
            create_accesslogs__titles=[t2],
        )
        mdu = ManualDataUploadFactory.create(
            import_batches=[ib, ib2],
            report_type=jr1,
            platform=branch_pl,
            organization=ib.organization,
        )
        assert mdu.import_batches.count() == 2
        resp = master_admin_client.get(
            reverse("mdu-access-logs", args=[mdu.pk]),
            {"order_by": "target", "desc": desc, "page_size": 10},
        )
        assert resp.status_code == 200
        data = resp.json()
        last_value = None
        # we need to set some UTF-8 locale to get correct sorting
        locale.setlocale(locale.LC_ALL, "en_US.UTF8")
        for rec in data["results"]:
            value = rec["target"]
            if last_value is not None:
                if desc:
                    assert locale.strcoll(value, last_value) <= 0
                else:
                    assert locale.strcoll(value, last_value) >= 0
            last_value = value

    @pytest.mark.parametrize("has_data", (True, False))
    @pytest.mark.parametrize("page_size", (5, 20))
    @pytest.mark.parametrize(
        ["order_by", "desc"],
        [
            ("date", False),
            ("date", True),
            ("value", False),
            ("value", True),
            ("platform", False),
            ("platform", True),
            ("organization", False),
            ("organization", True),
            ("metric", False),
            ("metric", True),
            ("target", False),
            ("target", True),
            ("item", False),
            ("item", True),
        ],
    )
    def test_raw_data_ib(
        self,
        master_admin_client,
        report_types,
        interests,
        interest_rt,
        platforms,
        order_by,
        desc,
        page_size,
        has_data,
    ):
        """
        Test that the access-log-list endpoint for import batch returns the correct data.
        We are running it with and without data to make sure that the endpoint returns the
        same data structure in both cases.
        """
        factory = ImportBatchFullFactory if has_data else ImportBatchFactory
        params = dict(report_type=report_types["ir"], platform=platforms["branch"])
        if has_data:
            # create 2 titles and 2 items - we need two to test ordering, but we don't need more
            # because we want more items to appear on the same page
            params["create_accesslogs__titles"] = TitleFactory.create_batch(2)
            params["create_accesslogs__items"] = ItemFactory.create_batch(2)
        ib = factory.create(**params)
        resp = master_admin_client.get(
            reverse("ib-access-logs", args=[ib.pk]),
            {"order_by": order_by, "desc": desc, "page_size": page_size},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == ib.accesslog_set.count()
        # check pagination
        assert len(data["results"]) == min(page_size, data["count"])
        if has_data:
            # check the format of the data
            rec = data["results"][0]
            assert "date" in rec
            assert rec["report_type"] == "IR"
            assert {"platform", "organization", "metric", "value", "target", "item"}.issubset(
                rec.keys()
            )
            # check ordering
            # we need to set some UTF-8 locale to get correct sorting
            locale.setlocale(locale.LC_ALL, "en_US.UTF8")
            last_value = None
            for rec in data["results"]:
                value = rec[order_by]
                if isinstance(value, str):
                    # database uses unicode collation, which sorts differently than python
                    # in presence of spaces. So we need to use unicode sort order as well
                    value = locale.strxfrm(value)
                if last_value is not None:
                    if desc:
                        assert value <= last_value
                    else:
                        assert value >= last_value
                last_value = value

    @pytest.mark.parametrize(
        "client,code",
        (
            ("su", 200),
            ("master_admin", 200),
            ("master_user", 200),
            ("admin2", 200),  # admin of the org
            ("admin1", 404),
            ("user2", 200),  # user of the org
            ("user1", 404),
        ),
    )
    def test_raw_data_ib_permissions(
        self,
        basic1,
        report_types,
        organizations,
        interests,
        interest_rt,
        platforms,
        client,
        code,
        clients,
    ):
        """
        Test that only the right users can access the access-log-list endpoint for an import batch
        """
        ib = ImportBatchFullFactory.create(
            report_type=report_types["jr1"],
            platform=platforms["branch"],
            organization=organizations["standalone"],
        )
        resp = clients[client].get(reverse("ib-access-logs", args=[ib.pk]))
        assert resp.status_code == code

    @pytest.mark.parametrize("has_data", (True, False))
    @pytest.mark.parametrize(
        "client,code",
        (
            ("su", 200),
            ("master_admin", 200),
            ("master_user", 200),
            ("admin2", 200),  # admin of the org
            ("admin1", 404),
            ("user2", 200),  # user of the org
            ("user1", 404),
        ),
    )
    def test_raw_data_mdu_permissions(
        self,
        basic1,
        report_types,
        organizations,
        interests,
        interest_rt,
        platforms,
        client,
        code,
        clients,
        has_data,
    ):
        """
        Test that only the right users can access the access-log-list endpoint for an MDU
        """
        factory = ImportBatchFullFactory if has_data else ImportBatchFactory
        ib = factory.create(
            report_type=report_types["jr1"],
            platform=platforms["branch"],
            organization=organizations["standalone"],
        )
        mdu = ManualDataUploadFactory.create(
            import_batches=[ib],
            report_type=report_types["jr1"],
            platform=platforms["branch"],
            organization=organizations["standalone"],
        )
        resp = clients[client].get(reverse("mdu-access-logs", args=[mdu.pk]))
        assert resp.status_code == code
        if code == 200:
            assert "count" in resp.json()
            assert "results" in resp.json()

    @pytest.mark.parametrize(
        "client,code",
        (
            ("su", 200),
            ("master_admin", 200),
            ("master_user", 200),
            ("admin2", 404),
            ("admin1", 404),
            ("user2", 404),
            ("user1", 404),
        ),
    )
    def test_raw_data_mdu_without_org_permissions(
        self,
        basic1,
        report_types,
        organizations,
        interests,
        interest_rt,
        platforms,
        client,
        code,
        clients,
    ):
        """
        If the MDU does not have organization assigned, it should only be accessible to superusers
        """
        ib = ImportBatchFullFactory.create(
            report_type=report_types["jr1"],
            platform=platforms["branch"],
            organization=organizations["standalone"],
        )
        mdu = ManualDataUploadFactory.create(
            import_batches=[ib],
            report_type=report_types["jr1"],
            platform=platforms["branch"],
            organization=None,
        )
        resp = clients[client].get(reverse("mdu-access-logs", args=[mdu.pk]))
        assert resp.status_code == code
