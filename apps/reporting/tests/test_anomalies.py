import random

import pytest
from django.urls import reverse
from logs.cubes import AccessLogCube, AccessLogCubeRecord, ch_backend
from logs.models import Dimension, DimensionText, Metric, ReportType, ReportTypeToDimension
from organizations.models import Organization, UserOrganization
from publications.models import Platform, Title

from reporting.apps import ensure_accesslog_zero_fill_view
from test_scenarios.basic import (  # noqa - fixtures
    basic1,
    client_by_user_type,
    clients,
    counter_report_types,
    credentials,
    data_sources,
    harvests,
    identities,
    import_batches,
    organizations,
    platforms,
    report_types,
    schedulers,
    users,
)


@pytest.fixture
def anomaly_test_data():
    """
    Creates 12 months of historical data
    historical 12 months [200,200,200,200,200,200,220,220,220,220,220,220]
        Q1: 200, Q3: 220, IQR: 20
        upper boundary is Q3 + 5*IQR = 320
        lower boundary is Q1 - 5*IQR = 100
    Yields method to add more values.
    Cleans up ClickHouse after the test.
    """
    # Seed dictionary-backed rows in Postgres
    platform = Platform.objects.create(short_name="P1", name="Platform 1", provider="prov")
    organization = Organization.objects.create(short_name="ORG", name="Org 1")
    report_type = ReportType.objects.create(short_name="TR", name="TR report")
    metric = Metric.objects.create(short_name="Hits", name="Hits")
    title = Title.objects.create(name="Test Title")

    # Prepare one explicit dimension linked to this report type so dim-based reasons work
    dim = Dimension.objects.create(short_name="TestDim", name="Test Dimension")
    ReportTypeToDimension.objects.create(report_type=report_type, dimension=dim, position=0)
    dim_text = DimensionText.objects.create(dimension=dim, text="Foo")
    # Reload ClickHouse dictionaries so dictGet sees newly created entries
    with ch_backend.pool.get_client() as client:
        client.execute("SYSTEM RELOAD DICTIONARY dim")
        client.execute("SYSTEM RELOAD DICTIONARY title")

    try:
        records = []
        record_id = 1
        for month in range(1, 13):
            records.append(
                AccessLogCubeRecord(
                    id=record_id,
                    report_type_id=report_type.id,
                    metric_id=metric.id,
                    organization_id=organization.id,
                    platform_id=platform.id,
                    target_id=title.id,
                    item_id=0,
                    date=f"2020-{month:02d}-01",
                    import_batch_id=1,
                    value=200 if month <= 6 else 220,
                    dim1=dim_text.id,
                    dim2=0,
                    dim3=0,
                    dim4=0,
                    dim5=0,
                    dim6=0,
                    dim7=0,
                    dim8=0,
                )
            )
            record_id += 1

        # Seed initial historical data into ClickHouse once
        ch_backend.initialize_storage(AccessLogCube)
        ch_backend.store_records(AccessLogCube, records)
        ensure_accesslog_zero_fill_view()

        def add_value(mdate, value):
            """Insert a value for a given month date"""
            record_id = random.randint(20, 1000000)
            new_record = AccessLogCubeRecord(
                id=record_id,
                report_type_id=report_type.id,
                metric_id=metric.id,
                organization_id=organization.id,
                platform_id=platform.id,
                target_id=title.id,
                item_id=0,
                date=mdate,
                import_batch_id=1,
                value=value,
                dim1=dim_text.id,
                dim2=0,
                dim3=0,
                dim4=0,
                dim5=0,
                dim6=0,
                dim7=0,
                dim8=0,
            )
            ch_backend.store_records(AccessLogCube, [new_record])
            # delete the view and recreate it to reflect the new value
            with ch_backend.pool.get_client() as client:
                client.execute("DROP VIEW IF EXISTS AccessLogCubeZeroFillView")
            ensure_accesslog_zero_fill_view()

        yield add_value, platform, organization, report_type, metric, title
    finally:
        # clean the test setup
        with ch_backend.pool.get_client() as client:
            client.execute("DROP VIEW IF EXISTS AccessLogCubeZeroFillView")
            ch_backend.delete_records(AccessLogCube.query())
            client.execute(
                f"TRUNCATE TABLE IF EXISTS {ch_backend.cube_to_table_name(AccessLogCube)}"
            )


@pytest.mark.clickhouse
@pytest.mark.usefixtures("clickhouse_db")
@pytest.mark.django_db(transaction=True)
class TestAnomaliesAccessOrganizationFiltering:
    def _seed_two_orgs_with_anomaly_in_second(self):
        # Create base entities
        platform = Platform.objects.create(short_name="PX", name="Platform X", provider="prov")
        org_a = Organization.objects.create(short_name="ORGA", name="Org A")
        org_b = Organization.objects.create(short_name="ORGB", name="Org B")
        report_type = ReportType.objects.create(short_name="TRX", name="TR X")
        metric = Metric.objects.create(short_name="Hits", name="Hits")
        title = Title.objects.create(name="Test Title X")

        # Seed 12 months history for both orgs
        ch_backend.initialize_storage(AccessLogCube)
        records = []
        rec_id = 1
        for month in range(1, 13):
            for org in (org_a, org_b):
                records.append(
                    AccessLogCubeRecord(
                        id=rec_id,
                        report_type_id=report_type.id,
                        metric_id=metric.id,
                        organization_id=org.id,
                        platform_id=platform.id,
                        target_id=title.id,
                        item_id=0,
                        date=f"2020-{month:02d}-01",
                        import_batch_id=1,
                        value=200 if month <= 6 else 220,
                        dim1=0,
                        dim2=0,
                        dim3=0,
                        dim4=0,
                        dim5=0,
                        dim6=0,
                        dim7=0,
                        dim8=0,
                    )
                )
                rec_id += 1
        ch_backend.store_records(AccessLogCube, records)
        ensure_accesslog_zero_fill_view()

        # Add outlier only for Org B at 2021-01
        outlier = AccessLogCubeRecord(
            id=999999,
            report_type_id=report_type.id,
            metric_id=metric.id,
            organization_id=org_b.id,
            platform_id=platform.id,
            target_id=title.id,
            item_id=0,
            date="2021-01-01",
            import_batch_id=1,
            value=3000,
            dim1=0,
            dim2=0,
            dim3=0,
            dim4=0,
            dim5=0,
            dim6=0,
            dim7=0,
            dim8=0,
        )
        ch_backend.store_records(AccessLogCube, [outlier])
        with ch_backend.pool.get_client() as client:
            client.execute("DROP VIEW IF EXISTS AccessLogCubeZeroFillView")
        ensure_accesslog_zero_fill_view()

        return org_a, org_b

    def test_no_org_param_filters_to_accessible_orgs_only(self, clients, users):
        org_a, _ = self._seed_two_orgs_with_anomaly_in_second()
        # user1 should not see org_b by default; grant access to org_a only
        UserOrganization.objects.create(user=users["user1"], organization=org_a)
        resp = clients["user1"].get(
            reverse("anomaly-report"), {"month": "2021-01", "month_to": "2021-01"}
        )
        assert resp.status_code == 200
        data = resp.json()
        # anomaly exists only for org_b; user1 has access to org_a only -> empty
        assert isinstance(data, list)
        assert len(data) == 0

    def test_other_org_param_is_rejected(self, clients, users):
        org_a, org_b = self._seed_two_orgs_with_anomaly_in_second()

        UserOrganization.objects.create(user=users["user1"], organization=org_a)
        # Try to access org_b explicitly
        resp = clients["user1"].get(
            reverse("anomaly-report"),
            {"month": "2021-01", "month_to": "2021-01", "organization": org_b.id},
        )
        assert resp.status_code == 403

    def test_own_org_param_allows_access(self, clients, users):
        org_a, _ = self._seed_two_orgs_with_anomaly_in_second()

        UserOrganization.objects.create(user=users["user1"], organization=org_a)
        resp = clients["user1"].get(
            reverse("anomaly-report"),
            {"month": "2021-01", "month_to": "2021-01", "organization": org_a.id},
        )
        assert resp.status_code == 200
        # No anomaly for org_a -> empty list
        assert resp.json() == []


@pytest.mark.clickhouse
@pytest.mark.django_db(transaction=True)
class TestAnomalyReportAccess:
    """
    Test access to the anomaly-report endpoint for different user types.
    """

    @pytest.fixture(autouse=True)
    def ensure_view(self, clickhouse_db):
        """
        Ensure the AccessLogCubeZeroFillView is created and destroyed after the test.
        """
        try:
            ensure_accesslog_zero_fill_view()
            yield
        finally:
            with ch_backend.pool.get_client() as client:
                client.execute("DROP VIEW IF EXISTS AccessLogCubeZeroFillView")

    @pytest.mark.parametrize(
        ["user_type", "expected_status"],
        [
            ["no_user", 401],
            ["invalid", 401],
            ["unrelated", 200],  # Can access and see data from their org
            ["related_user", 200],  # Can access and see data from their org
            ["related_admin", 200],  # Can access and see data from their org
            ["master_user", 200],  # Can access and see data from all accessible orgs
            ["master_admin", 200],  # Can access and see data from all accessible orgs
            ["superuser", 200],  # Can access and see data from all orgs
        ],
    )
    def test_anomaly_report_access_by_user_type(
        self, user_type, expected_status, client_by_user_type
    ):
        """
        Test that different user types have appropriate access to the anomaly-report endpoint.
        """
        client, _ = client_by_user_type(user_type)

        resp = client.get(reverse("anomaly-report"), {"month": "2021-01", "month_to": "2021-01"})
        assert resp.status_code == expected_status

    @pytest.mark.parametrize(
        ["user_type", "expected_status"],
        [
            ["no_user", 401],
            ["invalid", 401],
            ["unrelated", 403],  # Cannot access with org_id parameter from unrelated organization
            ["related_user", 200],  # Can access and see data from their org
            ["related_admin", 200],  # Can access and see data from their org
            ["master_user", 200],  # Can access and see data from all accessible orgs
            ["master_admin", 200],  # Can access and see data from all accessible orgs
            ["superuser", 200],  # Can access and see data from all orgs
        ],
    )
    def test_anomaly_report_access_by_user_type_with_org_param(
        self, user_type, expected_status, client_by_user_type
    ):
        """
        Test that different user types have appropriate access to the anomaly-report endpoint
        with the organization_id parameter.
        The user must be able to access the organization with the given organization_id.
        """
        client, user_org = client_by_user_type(user_type)

        resp = client.get(
            reverse("anomaly-report"),
            {"month": "2021-01", "month_to": "2021-01", "organization": user_org.id},
        )
        assert resp.status_code == expected_status


@pytest.mark.clickhouse
@pytest.mark.usefixtures("clickhouse_db")
@pytest.mark.django_db(transaction=True)
class TestAnomaliesCalculation:
    """
    Test that values outside of the boundaries are flagged as anomalies.
    upper boundary is Q3 + 5*IQR = 320
    lower boundary is Q1 - 5*IQR = 100

    Value 321 should be outlier, 320 should not.
    Value 99 should be outlier, 100 should not.
    """

    def test_outlier_upper(self, admin_client, anomaly_test_data):
        add_value, platform, organization, report_type, metric, _ = anomaly_test_data
        # Add the outlier 321 at the target month
        add_value("2021-01-01", 321)

        resp = admin_client.get(
            reverse("anomaly-report"), {"month": "2021-01", "month_to": "2021-01"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        rec = data[0]
        assert rec["value"] == 321
        assert rec["significance"] >= 5
        assert rec["platform"]["short_name"] == platform.short_name
        assert rec["organization"] == organization.name
        assert rec["reportType"]["short_name"] == report_type.short_name
        assert rec["metric"] == metric.short_name
        assert rec["organizationId"] == organization.id
        assert rec["metricId"] == metric.id

    def test_not_outlier_upper(self, admin_client, anomaly_test_data):
        add_value, _, _, _, _, _ = anomaly_test_data
        add_value("2021-01-01", 320)
        resp = admin_client.get(
            reverse("anomaly-report"), {"month": "2021-01", "month_to": "2021-01"}
        )
        assert resp.status_code == 200
        data = resp.json()

        # This should not be an anomaly
        assert isinstance(data, list)
        assert len(data) == 0

    def test_not_outlier_lower(self, admin_client, anomaly_test_data):
        add_value, _, _, _, _, _ = anomaly_test_data
        add_value("2021-01-01", 100)
        resp = admin_client.get(
            reverse("anomaly-report"), {"month": "2021-01", "month_to": "2021-01"}
        )
        assert resp.status_code == 200
        data = resp.json()

        # This should not be an anomaly
        assert isinstance(data, list)
        assert len(data) == 0

    def test_outlier_lower(self, admin_client, anomaly_test_data):
        add_value, platform, organization, report_type, metric, _ = anomaly_test_data
        # Add the outlier 99 at the target month
        add_value("2021-01-01", 99)
        resp = admin_client.get(
            reverse("anomaly-report"), {"month": "2021-01", "month_to": "2021-01"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        rec = data[0]
        assert rec["value"] == 99
        assert rec["significance"] >= 5
        assert rec["platform"]["short_name"] == platform.short_name
        assert rec["organization"] == organization.name
        assert rec["reportType"]["short_name"] == report_type.short_name
        assert rec["metric"] == metric.short_name

    def test_anomaly_sum(self, admin_client, anomaly_test_data):
        """
        Multiple values in the same month for the same org,platform,report_type,metric
        should be summed.
        When summed together, they should become an outlier.
        """
        add_value, platform, organization, report_type, metric, _ = anomaly_test_data
        add_value("2021-01-01", 200)
        add_value("2021-01-01", 200)
        add_value("2021-01-01", 200)

        resp = admin_client.get(
            reverse("anomaly-report"), {"month": "2021-01", "month_to": "2021-01"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        rec = data[0]
        assert rec["value"] == 600
        assert rec["significance"] > 5
        assert rec["platform"]["short_name"] == platform.short_name
        assert rec["organization"] == organization.name
        assert rec["reportType"]["short_name"] == report_type.short_name
        assert rec["metric"] == metric.short_name

    def test_multiple_months(self, admin_client, anomaly_test_data):
        add_value, _, _, _, _, _ = anomaly_test_data
        add_value("2021-01-01", 321)
        add_value("2021-02-01", 650)
        resp = admin_client.get(
            reverse("anomaly-report"), {"month": "2021-01", "month_to": "2021-03"}
        )
        assert resp.status_code == 200
        data = resp.json()
        # Should be getting 2 anomalies
        assert len(data) == 2
        rec1 = data[0]
        assert rec1["date"] == "2021-01-01"
        assert rec1["value"] == 321
        rec2 = data[1]
        assert rec2["date"] == "2021-02-01"
        assert rec2["value"] == 650


@pytest.mark.clickhouse
@pytest.mark.usefixtures("clickhouse_db")
@pytest.mark.django_db(transaction=True)
class TestAnomaliesHistory:
    """
    For each anomaly, its current month + 12 month historical values should be returned = 13 values.
    If there are missing months, their values should be None.c
    If there are less than 9/12 historical values, the anomaly should not be detected at all.
    """

    def test_anomalies_history_len(self, admin_client, anomaly_test_data):
        add_value, _, _, _, _, _ = anomaly_test_data
        add_value("2021-01-01", 321)

        resp = admin_client.get(
            reverse("anomaly-report"), {"month": "2021-01", "month_to": "2021-01"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        rec = data[0]
        assert len(rec["history"]) == 13
        assert rec["history"]["2020-01-01"] == 200
        assert rec["history"]["2020-02-01"] == 200
        assert rec["history"]["2020-03-01"] == 200
        assert rec["history"]["2020-04-01"] == 200
        assert rec["history"]["2020-05-01"] == 200
        assert rec["history"]["2020-06-01"] == 200
        assert rec["history"]["2020-07-01"] == 220
        assert rec["history"]["2020-08-01"] == 220
        assert rec["history"]["2020-09-01"] == 220
        assert rec["history"]["2020-10-01"] == 220
        assert rec["history"]["2020-11-01"] == 220
        assert rec["history"]["2020-12-01"] == 220
        assert rec["history"]["2021-01-01"] == 321

    def test_anomalies_history_missing_month(self, admin_client, anomaly_test_data):
        add_value, _, _, _, _, _ = anomaly_test_data
        # we skip 2021-01, there is also no import batch for this value ->
        # it should be None for 2021-01
        add_value("2021-02-01", 1000)
        resp = admin_client.get(
            reverse("anomaly-report"), {"month": "2021-02", "month_to": "2021-02"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        rec = data[0]
        assert len(rec["history"]) == 13
        assert rec["history"]["2021-01-01"] is None

    def test_anomalies_history_missing_three_months(self, admin_client, anomaly_test_data):
        # we need at least 9 historical values to define an anomaly
        add_value, _, _, _, _, _ = anomaly_test_data
        # we skip 2021-01, 2021-02, 2021-03, anomaly should still be found for 2021-04
        add_value("2021-04-01", 1000)
        resp = admin_client.get(
            reverse("anomaly-report"), {"month": "2021-04", "month_to": "2021-04"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1

    def test_anomalies_history_missing_five_months(self, admin_client, anomaly_test_data):
        # we need at least 9 historical values to define an anomaly
        add_value, _, _, _, _, _ = anomaly_test_data
        # we skip 2021-01, 2021-02, 2021-03, 2021-04, anomaly should not be found for 2021-05
        add_value("2021-05-01", 1000)
        resp = admin_client.get(
            reverse("anomaly-report"), {"month": "2021-05", "month_to": "2021-05"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 0


@pytest.mark.clickhouse
@pytest.mark.usefixtures("clickhouse_db")
@pytest.mark.django_db(transaction=True)
class TestAnomaliesReasons:
    """
    The search for dimensions/titles that are outliers should have the same logic as
    the search for anomalies.
    With all out test data in the same "dim1", this dim should be defined as outlier,
    from the same value 321. Same for titles.
    """

    def test_reasons(self, admin_client, anomaly_test_data):
        add_value, _, _, _, _, _ = anomaly_test_data
        add_value("2021-01-01", 321)
        # First get the anomaly from the report
        resp = admin_client.get(
            reverse("anomaly-report"), {"month": "2021-01", "month_to": "2021-01"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        anomaly = data[0]

        # Now get the details with reasons
        details_resp = admin_client.get(
            reverse("anomaly-details"),
            {
                "month": "2021-01",
                "organization": anomaly["organizationId"],
                "platform": anomaly["platform"]["id"],
                "report_type": anomaly["reportType"]["id"],
                "metric": anomaly["metricId"],
            },
        )
        assert details_resp.status_code == 200
        rec = details_resp.json()
        assert len(rec["reasons"]) == 2  # 1 for dimension, 1 for title

    def test_reason_dimensions(self, admin_client, anomaly_test_data):
        add_value, _, _, _, _, _ = anomaly_test_data
        add_value("2021-01-01", 321)
        # First get the anomaly from the report
        resp = admin_client.get(
            reverse("anomaly-report"), {"month": "2021-01", "month_to": "2021-01"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        anomaly = data[0]

        # Now get the details with reasons
        details_resp = admin_client.get(
            reverse("anomaly-details"),
            {
                "month": "2021-01",
                "organization": anomaly["organizationId"],
                "platform": anomaly["platform"]["id"],
                "report_type": anomaly["reportType"]["id"],
                "metric": anomaly["metricId"],
            },
        )
        assert details_resp.status_code == 200
        rec = details_resp.json()
        assert len(rec["reasons"]) == 2
        dim_reasons = [r for r in rec["reasons"] if r.get("type") != "title"]
        assert len(dim_reasons) == 1
        reason = dim_reasons[0]
        assert reason["type"] == "TestDim"
        assert reason["target_id_text"] == "Foo"
        assert reason["total_value"] == 321
        assert reason["median"] == 220
        assert reason["median_diff"] == 101
        assert reason["group_count"] == 1
        assert reason["dim"] == "dim1"

    def test_reason_title(self, admin_client, anomaly_test_data):
        add_value, _, _, _, _, title = anomaly_test_data
        add_value("2021-01-01", 321)
        # First get the anomaly from the report
        resp = admin_client.get(
            reverse("anomaly-report"), {"month": "2021-01", "month_to": "2021-01"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        anomaly = data[0]

        # Now get the details with reasons
        details_resp = admin_client.get(
            reverse("anomaly-details"),
            {
                "month": "2021-01",
                "organization": anomaly["organizationId"],
                "platform": anomaly["platform"]["id"],
                "report_type": anomaly["reportType"]["id"],
                "metric": anomaly["metricId"],
            },
        )
        assert details_resp.status_code == 200
        rec = details_resp.json()
        title_reasons = [r for r in rec.get("reasons", []) if r.get("type") == "title"]
        assert len(title_reasons) == 1
        reason = title_reasons[0]
        assert reason["target_id_text"] == title.name
        assert reason["total_value"] == 321
        assert reason["median"] == 220
        assert reason["median_diff"] == 101
        assert reason["group_count"] == 1
        assert reason["dim"] == "target"
