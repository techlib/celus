from unittest.mock import patch

import pytest
from django.urls import reverse
from export.models import FlexibleDataAPIExport
from logs.models import FlexibleReport

from api.models import OrganizationAPIKey
from api.throttling import APIKeyBasedThrottle


@pytest.mark.django_db
class TestAPI:
    def test_apikey_access_report_no_key(self, client, root_platform, tr_report):
        resp = client.get(
            reverse(
                "api_platform_report_data",
                kwargs={"platform_id": root_platform.pk, "report_type": tr_report.short_name},
            )
        )
        assert resp.status_code == 401

    def test_apikey_access_report_no_key_with_user(self, admin_client, root_platform, tr_report):
        resp = admin_client.get(
            reverse(
                "api_platform_report_data",
                kwargs={"platform_id": root_platform.pk, "report_type": tr_report.short_name},
            )
        )
        assert resp.status_code == 403, "even admin cannot access without a key"

    def test_apikey_access_report_bad_key(self, client, root_platform, tr_report):
        resp = client.get(
            reverse(
                "api_platform_report_data",
                kwargs={"platform_id": root_platform.pk, "report_type": tr_report.short_name},
            ),
            HTTP_AUTHORIZATION="Api-Key RANDOM.value",
        )
        assert resp.status_code == 401, "invalid key"

    def test_apikey_access_report_good_key(self, client, root_platform, tr_report, organizations):
        api_key, key_val = OrganizationAPIKey.objects.create_key(
            organization=organizations["root"], name="test"
        )
        resp = client.get(
            reverse(
                "api_platform_report_data",
                kwargs={"platform_id": root_platform.pk, "report_type": tr_report.short_name},
            ),
            HTTP_AUTHORIZATION=f"Api-Key {key_val}",
        )
        assert resp.status_code == 400, "allowed, but missing arg"

    def test_apikey_access_report_good_key_good_request(
        self, client, root_platform, tr_report, organizations
    ):
        api_key, key_val = OrganizationAPIKey.objects.create_key(
            organization=organizations["root"], name="test"
        )
        resp = client.get(
            reverse(
                "api_platform_report_data",
                kwargs={"platform_id": root_platform.pk, "report_type": tr_report.short_name},
            ),
            {"month": "2020-01", "dims": ""},
            HTTP_AUTHORIZATION=f"Api-Key {key_val}",
        )
        assert resp.status_code == 200

    def test_apikey_access_report_good_key_good_request_no_dimensions(
        self, client, root_platform, tr_report, organizations
    ):
        api_key, key_val = OrganizationAPIKey.objects.create_key(
            organization=organizations["root"], name="test"
        )
        resp = client.get(
            reverse(
                "api_platform_report_data",
                kwargs={"platform_id": root_platform.pk, "report_type": tr_report.short_name},
            ),
            {"month": "2020-01"},
            HTTP_AUTHORIZATION=f"Api-Key {key_val}",
        )
        assert resp.status_code == 400

    @pytest.mark.clickhouse
    @pytest.mark.parametrize("use_registry_id", [True, False])
    @pytest.mark.usefixtures("clickhouse_on_off")
    @pytest.mark.django_db(transaction=True)
    def test_platform_report_view_response(
        self, client, flexible_slicer_test_data, use_registry_id
    ):
        org = flexible_slicer_test_data["organizations"][0]
        platform = flexible_slicer_test_data["platforms"][0]
        report = flexible_slicer_test_data["report_types"][0]
        api_key, key_val = OrganizationAPIKey.objects.create_key(organization=org, name="test")
        platform_id = str(platform.counter_registry_id) if use_registry_id else platform.pk
        resp = client.get(
            reverse(
                "api_platform_report_data",
                kwargs={"platform_id": platform_id, "report_type": report.short_name},
            ),
            {"month": "2020-01", "dims": "dim1name"},
            HTTP_AUTHORIZATION=f"Api-Key {key_val}",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "OK"
        assert data["complete_data"] is True
        records = data["records"]
        assert len(records) == 3 * 3 * 3, "3 titles; 3 metrics; 3 dim1 values"
        # the following data was created in a spreadsheet based on flexible_slicer_test_data
        expected = {
            ("Title 1", "m1", "A", 28),
            ("Title 1", "m1", "B", 29),
            ("Title 1", "m1", "C", 30),
            ("Title 1", "m2", "A", 37),
            ("Title 1", "m2", "B", 38),
            ("Title 1", "m2", "C", 39),
            ("Title 1", "m3", "A", 46),
            ("Title 1", "m3", "B", 47),
            ("Title 1", "m3", "C", 48),
            ("Title 2", "m1", "A", 31),
            ("Title 2", "m1", "B", 32),
            ("Title 2", "m1", "C", 33),
            ("Title 2", "m2", "A", 40),
            ("Title 2", "m2", "B", 41),
            ("Title 2", "m2", "C", 42),
            ("Title 2", "m3", "A", 49),
            ("Title 2", "m3", "B", 50),
            ("Title 2", "m3", "C", 51),
            ("Title 3", "m1", "A", 34),
            ("Title 3", "m1", "B", 35),
            ("Title 3", "m1", "C", 36),
            ("Title 3", "m2", "A", 43),
            ("Title 3", "m2", "B", 44),
            ("Title 3", "m2", "C", 45),
            ("Title 3", "m3", "A", 52),
            ("Title 3", "m3", "B", 53),
            ("Title 3", "m3", "C", 54),
        }
        assert {
            (rec["title"], rec["metric"], rec["dim1name"], rec["hits"]) for rec in records
        } == expected

    @pytest.mark.clickhouse
    @pytest.mark.usefixtures("clickhouse_on_off")
    @pytest.mark.django_db(transaction=True)
    def test_platform_report_view_excluded_dim(self, client, flexible_slicer_test_data):
        org = flexible_slicer_test_data["organizations"][0]
        platform = flexible_slicer_test_data["platforms"][0]
        report = flexible_slicer_test_data["report_types"][1]
        api_key, key_val = OrganizationAPIKey.objects.create_key(organization=org, name="test")
        resp = client.get(
            reverse(
                "api_platform_report_data",
                kwargs={"platform_id": platform.pk, "report_type": report.short_name},
            ),
            {"month": "2020-01", "dims": "dim2name"},
            HTTP_AUTHORIZATION=f"Api-Key {key_val}",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "OK"
        assert data["complete_data"] is True
        records = data["records"]
        assert len(records) == 3 * 3 * 4, "3 titles; 3 metrics; 4 dim2 values"
        # the following data was created in a spreadsheet based on flexible_slicer_test_data
        expected = {
            ("Title 1", "m1", "A", 3264),
            ("Title 1", "m1", "XX", 3255),
            ("Title 1", "m1", "YY", 3258),
            ("Title 1", "m1", "ZZ", 3261),
            ("Title 1", "m2", "A", 3372),
            ("Title 1", "m2", "XX", 3363),
            ("Title 1", "m2", "YY", 3366),
            ("Title 1", "m2", "ZZ", 3369),
            ("Title 1", "m3", "A", 3480),
            ("Title 1", "m3", "XX", 3471),
            ("Title 1", "m3", "YY", 3474),
            ("Title 1", "m3", "ZZ", 3477),
            ("Title 2", "m1", "A", 3300),
            ("Title 2", "m1", "XX", 3291),
            ("Title 2", "m1", "YY", 3294),
            ("Title 2", "m1", "ZZ", 3297),
            ("Title 2", "m2", "A", 3408),
            ("Title 2", "m2", "XX", 3399),
            ("Title 2", "m2", "YY", 3402),
            ("Title 2", "m2", "ZZ", 3405),
            ("Title 2", "m3", "A", 3516),
            ("Title 2", "m3", "XX", 3507),
            ("Title 2", "m3", "YY", 3510),
            ("Title 2", "m3", "ZZ", 3513),
            ("Title 3", "m1", "A", 3336),
            ("Title 3", "m1", "XX", 3327),
            ("Title 3", "m1", "YY", 3330),
            ("Title 3", "m1", "ZZ", 3333),
            ("Title 3", "m2", "A", 3444),
            ("Title 3", "m2", "XX", 3435),
            ("Title 3", "m2", "YY", 3438),
            ("Title 3", "m2", "ZZ", 3441),
            ("Title 3", "m3", "A", 3552),
            ("Title 3", "m3", "XX", 3543),
            ("Title 3", "m3", "YY", 3546),
            ("Title 3", "m3", "ZZ", 3549),
        }
        assert {
            (rec["title"], rec["metric"], rec["dim2name"], rec["hits"]) for rec in records
        } == expected

    def test_platform_report_view_no_data_no_sushi(
        self, client, root_platform, tr_report, organizations
    ):
        """
        Report has no data for the requested period and there is no SUSHI active for this
        combination of platform, organization and report
        """
        api_key, key_val = OrganizationAPIKey.objects.create_key(
            organization=organizations["root"], name="test"
        )
        resp = client.get(
            reverse(
                "api_platform_report_data",
                kwargs={"platform_id": root_platform.pk, "report_type": tr_report.short_name},
            ),
            {"month": "2020-01", "dims": ""},
            HTTP_AUTHORIZATION=f"Api-Key {key_val}",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["complete_data"] is False
        assert data["status"] == "SUSHI credentials not present for this report"

    def test_platform_report_view_incorrect_dims(
        self, client, root_platform, tr_report, organizations
    ):
        """
        User requested dimensions that are not supported by the report type
        """
        api_key, key_val = OrganizationAPIKey.objects.create_key(
            organization=organizations["root"], name="test"
        )
        resp = client.get(
            reverse(
                "api_platform_report_data",
                kwargs={"platform_id": root_platform.pk, "report_type": tr_report.short_name},
            ),
            {"month": "2020-01", "dims": "foo,bar"},
            HTTP_AUTHORIZATION=f"Api-Key {key_val}",
        )
        assert resp.status_code == 400
        assert b"Unknown dimensions" in resp.content

    @pytest.mark.parametrize("throttling", [True, False])
    def test_platform_report_view_throttling(
        self, client, root_platform, tr_report, organizations, throttling
    ):
        """
        Test throttling of the platform report view
        """
        # at this point, it is not possible to adjust the throttling rate via settings
        # so we have to set it on the class directly
        APIKeyBasedThrottle.rate = "1/minute" if throttling else "2/minute"
        api_key, key_val = OrganizationAPIKey.objects.create_key(
            organization=organizations["root"], name="test"
        )

        def make_request():
            return client.get(
                reverse(
                    "api_platform_report_data",
                    kwargs={"platform_id": root_platform.pk, "report_type": tr_report.short_name},
                ),
                {"month": "2020-01", "dims": ""},
                HTTP_AUTHORIZATION=f"Api-Key {key_val}",
            )

        # first request should always succeed
        resp = make_request()
        assert resp.status_code == 200
        # second request should fail if throttling is enabled
        resp2 = make_request()
        assert resp2.status_code == (429 if throttling else 200)
        # remove the rate attr from APIKeyBasedThrottle so that it doesn't affect other tests
        del APIKeyBasedThrottle.rate


@pytest.mark.django_db()
class TestFlexibleExportAPI:
    @pytest.mark.parametrize("correct_org", [True, False, None])
    def test_platform_report_view_response_org_based(
        self, client, flexible_slicer_test_data, inmemory_media, correct_org
    ):
        """
        Test that the org can only access its own data
        """
        org = flexible_slicer_test_data["organizations"][0]
        rt = flexible_slicer_test_data["report_types"][0]
        incorrect_org = flexible_slicer_test_data["organizations"][1]
        fr_org = None
        if correct_org:
            fr_org = org
        elif correct_org is False:
            fr_org = incorrect_org
        fr = FlexibleReport.objects.create(
            owner_organization=fr_org,
            report_config={
                "primary_dimension": "platform",
                "group_by": ["metric"],
                "filters": [
                    {"dimension": "report_type", "values": [rt.short_name]},
                    {"dimension": "date", "start": "2020-01-01", "end": "2020-01-31"},
                ],
            },
        )
        api_key, key_val = OrganizationAPIKey.objects.create_key(organization=org, name="test")
        with patch("export.tasks.process_flexible_api_export_task.apply_async") as mock_task:
            resp = client.post(
                reverse("flexible-export-api-list"),
                {
                    "report": fr.pk,
                    "file_format": "ZIP_CSV",
                },
                HTTP_AUTHORIZATION=f"Api-Key {key_val}",
                content_type="application/json",
            )
            assert resp.status_code == (201 if correct_org else 403)
            assert mock_task.call_count == (1 if correct_org else 0)

    @pytest.mark.parametrize(
        ["start_date", "end_date", "present_months"],
        [
            # there is rows only from 2019-12 to 2020-03, so anything outside should have no rows
            # None = do not add the parameter to the request
            # "" =  use empty value for the parameter
            # present_months == None => exception because of invalid input
            ("2020-01-01", "2020-01-31", ["2020-01-01"]),
            (None, None, ["2020-01-01"]),
            ("", "", ["2020-01-01"]),
            ("2018-01-01", "2020-01-31", ["2019-12-01", "2020-01-01"]),
            ("", "2019-01-31", None),  # invalid input - both dates must be present or absent
            ("2020-01-01", "2022-01-01", ["2020-01-01", "2020-02-01", "2020-03-01"]),
            ("2021-01-01", "2022-01-01", []),
            ("2021-01-01", "2021-01-31", []),
            ("2020-01-01", None, None),  # invalid input - both dates must be present or absent
            (None, "2020-01-31", None),  # invalid input - both dates must be present or absent
        ],
    )
    def test_platform_report_view_response_dates(
        self,
        client,
        flexible_slicer_test_data,
        inmemory_media,
        start_date,
        end_date,
        present_months,
    ):
        """
        Test that the date range is properly passed to the slicer
        """
        org = flexible_slicer_test_data["organizations"][0]
        rt = flexible_slicer_test_data["report_types"][0]
        fr = FlexibleReport.objects.create(
            owner_organization=org,
            report_config={
                "primary_dimension": "platform",
                "group_by": ["date"],
                "filters": [
                    {"dimension": "report_type", "values": [rt.short_name]},
                    {"dimension": "date", "start": "2020-01-01", "end": "2020-01-31"},
                ],
            },
        )
        api_key, key_val = OrganizationAPIKey.objects.create_key(organization=org, name="test")
        dates = {}
        if start_date is not None:
            dates["start_date"] = start_date or None
        if end_date is not None:
            dates["end_date"] = end_date or None
        with patch("export.tasks.process_flexible_api_export_task.apply_async") as mock_task:
            resp = client.post(
                reverse("flexible-export-api-list"),
                {
                    "report": fr.pk,
                    "file_format": "ZIP_CSV",
                    **dates,
                },
                HTTP_AUTHORIZATION=f"Api-Key {key_val}",
                content_type="application/json",
            )

        assert resp.status_code == (201 if present_months is not None else 400)
        if present_months is None:
            assert mock_task.call_count == 0
            assert FlexibleDataAPIExport.objects.count() == 0
            return  # nothing more to check

        assert mock_task.call_count == 1
        assert FlexibleDataAPIExport.objects.count() == 1
        exp_obj = FlexibleDataAPIExport.objects.first()
        assert exp_obj.pk == resp.json()["pk"]
        # call the task manually to check if it works
        from export.tasks import process_flexible_api_export_task

        process_flexible_api_export_task(exp_obj.pk)
        exp_obj.refresh_from_db()
        assert exp_obj.status == exp_obj.FINISHED

        resp = client.get(
            reverse("flexible-export-api-detail", args=[exp_obj.pk]),
            HTTP_AUTHORIZATION=f"Api-Key {key_val}",
        )
        assert resp.status_code == 200
        assert resp.json()["output_file"].endswith(".zip")
        import zipfile

        with zipfile.ZipFile(exp_obj.output_file) as z:
            assert len(z.filelist) == 2, "one file metadata, one rows"
            with z.open("report.csv") as f:
                rows = f.read().decode("utf-8").splitlines()
                assert len(rows) == (4 if present_months else 0)
                if present_months:
                    cols = rows[0].split(",")
                    assert cols[2:] == present_months
