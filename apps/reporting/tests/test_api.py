from unittest import mock

import pytest
from core.fake_data import UserFactory
from django.urls import reverse
from organizations.fake_data import OrganizationFactory

from test_scenarios.basic import (  # noqa - fixtures
    basic1,
    client_by_user_type,
    clients,
    data_sources,
    identities,
    organizations,
    platforms,
    users,
)


@pytest.mark.django_db
class TestReportsAPI:
    def test_report_list(self, admin_client, settings):
        # explicitly disable preview specialized reports so that the test is not affected by
        # local settings
        settings.SHOW_PREVIEW_SPECIALIZED_REPORTS = False
        response = admin_client.get(reverse("report-list"))
        assert response.status_code == 200
        assert len(response.data) == 6
        assert response.data[0]["name"] == "ACRL IPEDS 2024"
        assert response.data[1]["name"] == "ACRL IPEDS 2023"
        assert response.data[2]["name"] == "ACRL IPEDS 2022"
        assert response.data[3]["name"] == "ARL Statistics survey"
        assert (
            response.data[4]["name"] == "CAUL (Council of Australian University Librarians) report"
        )
        assert response.data[5]["name"] == "Rebiun report"
        # check structure of the first report
        r1 = response.data[0]
        for key in ["name", "description", "dataSources", "parts", "infoUrl"]:
            assert key in r1
        sources = r1["dataSources"]
        assert isinstance(sources, list)
        # check source
        s1 = sources[0]
        for key in ["id", "name", "reportType", "metric", "filters", "fallbackFor"]:
            assert key in s1
        # check part
        p1 = r1["parts"][0]
        for key in ["name", "description", "explanation", "stages", "implementationNote"]:
            assert key in p1
        # check stage
        s1 = p1["stages"][0]
        for key in ["id", "name", "description", "formula", "usedDataSources"]:
            assert key in s1

    @pytest.mark.parametrize("show_preview_reports", [True, False])
    @pytest.mark.parametrize(
        ["user_type", "can_see_preview"],
        [
            ["unrelated", False],
            ["related_user", False],
            ["related_admin", False],
            ["master_user", False],
            ["master_admin", True],
            ["superuser", True],
        ],
    )
    def test_preview_reports(
        self, client_by_user_type, settings, show_preview_reports, user_type, can_see_preview
    ):
        """
        Test that preview reports are shown when SHOW_PREVIEW_SPECIALIZED_REPORTS is True,
        and hidden when it is False. When preview reports are visible, they should be shown to
        consortium admins only.
        """
        settings.SHOW_PREVIEW_SPECIALIZED_REPORTS = show_preview_reports
        client, _org = client_by_user_type(user_type)
        response = client.get(reverse("report-list"))
        assert response.status_code == 200
        assert len(response.data) == (7 if show_preview_reports and can_see_preview else 6)
        if show_preview_reports and can_see_preview:
            assert response.data[0]["name"] == "CzechELib report"
        else:
            assert response.data[0]["name"] == "ACRL IPEDS 2024"

    @pytest.mark.parametrize(
        ["language", "expected_in_desc"], [("en", "interest"), ("cs", "zájmu"), ("de", "interest")]
    )
    def test_localized_report_list(self, client, settings, language, expected_in_desc):
        """
        Test that the report list is localized to the user's language - using the CzechELib report
        which is the only localized report for now. The `de` language is used to test that the
        default language is used when the user's language is not available.
        """
        settings.SHOW_PREVIEW_SPECIALIZED_REPORTS = True

        user = UserFactory(is_superuser=True, language=language)
        assert user.language == language
        client.force_login(user)
        response = client.get(reverse("report-list"))
        assert response.status_code == 200
        assert len(response.data) == 7
        assert response.data[0]["name"] == "CzechELib report"
        assert expected_in_desc in response.data[0]["description"]

    @pytest.mark.parametrize("new_organization", [True, False])
    def test_report_output(
        self, admin_client, report_data_tr_jr1, report_def_tr_jr1, new_organization
    ):
        # if new organization is True, we will create a new organization and use it in the request.
        # it will have empty data, but the result structure should be the same
        # - except for the total and the used report type
        if new_organization:
            org = OrganizationFactory()
        else:
            org = report_data_tr_jr1["org"]
        with mock.patch("reporting.views.get_report_def_by_name") as mock_get_report_def_by_name:
            # we replace the stored report by our own
            mock_get_report_def_by_name.return_value = report_def_tr_jr1
            response = admin_client.get(
                reverse("report-data", args=["Test report"]),
                {"start_date": "2022-01", "end_date": "2022-03", "organization": org.pk},
            )
        assert response.status_code == 200
        assert len(response.data) == 4, "4 parts"
        part1_stages = response.data["PART 1"]["stages"]
        if new_organization:
            assert len(part1_stages[0]["data"]) == 0, "org not connected to any platform"
        else:
            assert len(part1_stages[0]["data"]) == 2, "2 platforms"
            platform1 = report_data_tr_jr1["platform1"]
            platform2 = report_data_tr_jr1["platform2"]
            assert {rec["primary_pk"] for rec in part1_stages[0]["data"]} == {
                platform1.pk,
                platform2.pk,
            }
            # get data for platform1 and check it against the expected structure
            pl1_data = next(
                rec for rec in part1_stages[0]["data"] if rec["primary_pk"] == platform1.pk
            )
            assert set(pl1_data["monthly_data"].keys()) == {"2022-01", "2022-02", "2022-03"}
            assert pl1_data["primary_obj"] == platform1.short_name
            assert pl1_data["total"] > 0
            assert pl1_data["source_name"] == "TR"
            assert part1_stages[0]["used_data_sources"] == ["tr", "jr1", "jr1goa"]
            # get data for platform2 and check it against the expected structure
            pl2_data = next(
                rec for rec in part1_stages[0]["data"] if rec["primary_pk"] == platform2.pk
            )
            assert set(pl2_data["monthly_data"].keys()) == {"2022-01", "2022-02", "2022-03"}
            assert pl2_data["primary_obj"] == platform2.short_name
            assert pl2_data["total"] > 0
            assert pl2_data["source_name"] == "JR1 - JR1GOA"
            assert part1_stages[0]["used_data_sources"] == ["tr", "jr1", "jr1goa"]

    def test_report_export(self, admin_client, report_data_tr_jr1, report_def_tr_jr1):
        org = report_data_tr_jr1["org"]
        with mock.patch("reporting.views.get_report_def_by_name") as mock_get_report_def_by_name:
            # we replace the stored report by our own
            mock_get_report_def_by_name.return_value = report_def_tr_jr1
            response = admin_client.get(
                reverse("report-export", args=["Test report"]),
                {"start_date": "2022-01", "end_date": "2022-03", "organization": org.pk},
            )
        assert response.status_code == 200
        assert (
            response["Content-Type"]
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert response["Content-Disposition"] == 'attachment; filename="Test report.xlsx"'
