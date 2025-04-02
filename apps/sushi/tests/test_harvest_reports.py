"""
This module should test the functionality of harvest reports.
"""

import pytest
from core.models import User
from django.urls import reverse
from freezegun import freeze_time
from logs.fake_data import ImportBatchFactory
from organizations.models import Organization, UserOrganization

from sushi.fake_data import CounterReportsToCredentialsFactory, FetchAttemptFactory
from sushi.logic.email import send_harvest_reports
from sushi.logic.harvest_reports import make_harvest_reports
from sushi.tasks import send_harvesting_reports
from test_scenarios.basic import (
    basic1,  # noqa
    clients,  # noqa
    counter_report_types,  # noqa
    data_sources,  # noqa
    identities,  # noqa
    organizations,  # noqa
    platforms,  # noqa
    report_types,  # noqa
    users,  # noqa
)


@pytest.fixture
def report_data(organizations, platforms, report_types, counter_report_types):
    with freeze_time("2025-01-03 12:00:00"):  # setting timestamp of broken attempt
        # broken credentials
        CounterReportsToCredentialsFactory(
            credentials__organization=organizations["branch"],
            credentials__platform=platforms["shared"],
            counter_report=counter_report_types["tr"],
        ).credentials.set_broken(
            FetchAttemptFactory(start_date="2024-12-01", end_date="2024-12-31"), "sushi"
        )

    CounterReportsToCredentialsFactory(
        credentials__organization=organizations["branch"],
        credentials__platform=platforms["empty"],
        counter_report=counter_report_types["dr51"],
    )
    CounterReportsToCredentialsFactory(
        credentials__organization=organizations["branch"],
        credentials__platform=platforms["brain"],
        counter_report=counter_report_types["jr1"],
    )
    CounterReportsToCredentialsFactory(
        credentials__organization=organizations["standalone"],
        credentials__platform=platforms["shared"],
        counter_report=counter_report_types["pr51"],
    )

    with freeze_time("2025-02-03 12:00:00"):  # setting timestamp of broken attempt
        # broken report type
        CounterReportsToCredentialsFactory(
            credentials__organization=organizations["standalone"],
            credentials__platform=platforms["shared"],
            counter_report=counter_report_types["dr"],
        ).set_broken(FetchAttemptFactory(start_date="2025-01-01", end_date="2025-01-31"), "sushi")

    ImportBatchFactory(
        organization=organizations["branch"],
        platform=platforms["brain"],
        report_type=report_types["jr1"],
        date="2025-01-01",
    )

    ImportBatchFactory(
        organization=organizations["root"],
        platform=platforms["shared"],
        report_type=report_types["pr1"],
        date="2025-01-01",
    )


@pytest.mark.django_db
class TestMakingReports:
    @freeze_time("2025-03-05")
    def test_make_harvest_reports(self, report_data, organizations):
        organizations_pks = [
            v.pk for k, v in organizations.items() if k in ["branch", "standalone", "root"]
        ]
        reports = make_harvest_reports(
            Organization.objects.filter(pk__in=organizations_pks).order_by("name")
        )
        assert len(reports) == 3
        assert reports[0].organization.name == "branch"
        assert reports[0].month.isoformat() == "2025-01-01"
        assert reports[0].success_rate == 1 / 3 * 100, "one out of three"
        assert len(reports[0].credentials) == 3
        assert reports[0].credentials[0].is_verified is False
        assert reports[0].credentials[0].broken_since.date().isoformat() == "2025-01-03"
        assert reports[0].credentials[1].is_verified is False
        assert reports[0].credentials[1].broken_since is None
        assert reports[0].credentials[2].is_verified is False
        assert reports[0].credentials[2].broken_since is None

        assert reports[1].organization.name == "root"
        assert reports[1].month.isoformat() == "2025-01-01"
        assert reports[1].success_rate is None, "no credentials empty success_rate"
        assert len(reports[1].credentials) == 0

        assert reports[2].organization.name == "standalone"
        assert reports[2].month.isoformat() == "2025-01-01"
        assert reports[2].success_rate == 0.0, "no successfull downloads"
        assert len(reports[2].credentials) == 2
        assert reports[2].credentials[0].is_verified is False
        assert reports[2].credentials[0].broken_since is None
        assert reports[2].credentials[1].is_verified is False
        assert reports[2].credentials[1].broken_since.date().isoformat() == "2025-02-03"


@pytest.mark.django_db
class TestSendingEmails:
    @freeze_time("2025-03-05")
    def test_email_was_sent(self, users, report_data, organizations, mailoutbox):
        """Tests the emails were sent"""

        organizations_pks = [
            v.pk for k, v in organizations.items() if k in ["branch", "standalone", "root"]
        ]
        reports = make_harvest_reports(
            Organization.objects.filter(pk__in=organizations_pks).order_by("name")
        )
        assert send_harvest_reports(users["master_user"], reports) == 3
        assert len(mailoutbox) == 3, "email is sent even for organization without credentials"


@pytest.mark.django_db
class TestTask:
    @freeze_time("2025-03-05")
    @pytest.mark.parametrize(
        "user,sent_count",
        (
            ("master_admin", 1),  # no credentials
            ("master_user", 0),
            ("user2", 0),
            ("user1", 0),
            ("admin1", 2),  # branch + root
            ("admin2", 1),
            ("su", 0),
        ),
    )
    def test_sending_task(
        self, users, basic1, report_data, organizations, mailoutbox, user, sent_count
    ):
        UserOrganization.objects.update(send_harvest_reports=False)
        send_harvesting_reports()
        assert len(mailoutbox) == 0
        UserOrganization.objects.filter(user=users[user]).update(send_harvest_reports=True)

        User.objects.filter(pk=users[user].pk).update(is_active=False)
        send_harvesting_reports()
        assert len(mailoutbox) == 0, "Don't send emails for deactivated users"

        User.objects.filter(pk=users[user].pk).update(is_active=True)
        send_harvesting_reports()
        assert len(mailoutbox) == sent_count


@pytest.mark.django_db
class TestApi:
    @pytest.mark.parametrize(
        "user,organization,status_code,was_sent",
        (
            ("master_admin", "standalone", 200, True),
            ("master_user", "standalone", 404, False),
            ("user2", "standalone", 404, False),
            ("user1", "branch", 404, False),
            ("admin1", "root", 200, True),  # no credentials
            ("admin2", "standalone", 200, True),
            ("su", "standalone", 200, True),
        ),
    )
    def test_send_harvest_report(
        self,
        basic1,
        clients,
        organizations,
        report_data,
        mailoutbox,
        user,
        organization,
        status_code,
        was_sent,
    ):
        resp = clients[user].post(
            reverse("organization-send-harvest-report", args=(organizations[organization].pk,))
        )
        assert resp.status_code == status_code

        if was_sent:
            assert len(mailoutbox) == 1, "report for organization was sent"
        else:
            assert len(mailoutbox) == 0, "no report was sent for organization"

    @pytest.mark.parametrize(
        "user,organization,enabled,status_code,sent_count",
        (
            ("master_admin", "standalone", False, 200, 0),
            ("master_user", "standalone", False, 404, 0),
            ("user2", "standalone", False, 404, 0),
            ("user1", "branch", False, 404, 0),
            ("admin1", "root", False, 200, 0),
            ("admin2", "standalone", False, 200, 0),
            ("su", "standalone", False, 200, 0),
            ("master_admin", "standalone", True, 200, 1),
            ("master_user", "standalone", True, 404, 0),
            ("user2", "standalone", True, 404, 0),
            ("user1", "branch", True, 404, 0),
            ("admin1", "root", True, 200, 1),  # no credentials
            ("admin2", "standalone", True, 200, 1),
            ("su", "standalone", True, 200, 1),
        ),
    )
    def test_harvest_report(
        self,
        basic1,
        clients,
        organizations,
        report_data,
        mailoutbox,
        user,
        organization,
        enabled,
        status_code,
        sent_count,
    ):
        assert len(mailoutbox) == 0
        resp = clients[user].post(
            reverse("organization-harvest-reports", args=(organizations[organization].pk,)),
            {"enabled": enabled},
        )
        assert resp.status_code == status_code

        send_harvesting_reports()
        assert len(mailoutbox) == sent_count
