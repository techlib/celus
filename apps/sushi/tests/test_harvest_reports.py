"""
This module should test the functionality of harvest reports.
"""

from datetime import date

import pytest
from core.models import User
from django.urls import reverse
from freezegun import freeze_time
from logs.cubes import ch_backend
from logs.fake_data import ImportBatchFactory, ImportBatchFullFactory
from organizations.models import Organization, UserOrganization
from reporting.apps import ensure_accesslog_zero_fill_view

from sushi import tasks
from sushi.fake_data import CounterReportsToCredentialsFactory, FetchAttemptFactory
from sushi.logic.email import send_grouped_harvest_reports, send_harvest_reports
from sushi.logic.harvest_reports import make_harvest_reports
from sushi.models import AttemptStatus
from test_scenarios.basic import (
    basic1,  # noqa
    clients,  # noqa
    counter_report_types,  # noqa
    data_sources,  # noqa
    identities,  # noqa
    metrics,  # noqa
    organizations,  # noqa
    platforms,  # noqa
    report_types,  # noqa
    users,  # noqa
)


@pytest.fixture
def report_data(organizations, platforms, report_types, counter_report_types, metrics):
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
    cred1 = CounterReportsToCredentialsFactory(
        credentials__organization=organizations["branch"],
        credentials__platform=platforms["brain"],
        counter_report=counter_report_types["jr1"],
    ).credentials
    cred2 = CounterReportsToCredentialsFactory(
        credentials__organization=organizations["standalone"],
        credentials__platform=platforms["shared"],
        counter_report=counter_report_types["pr51"],
    ).credentials

    with freeze_time("2025-02-03 12:00:00"):  # setting timestamp of broken attempt
        # broken report type
        CounterReportsToCredentialsFactory(
            credentials__organization=organizations["standalone"],
            credentials__platform=platforms["shared"],
            counter_report=counter_report_types["dr"],
        ).set_broken(FetchAttemptFactory(start_date="2025-01-01", end_date="2025-01-31"), "sushi")

    # Empty data
    FetchAttemptFactory(
        status=AttemptStatus.NO_DATA,
        import_batch=ImportBatchFactory(
            organization=organizations["branch"],
            platform=platforms["brain"],
            report_type=report_types["jr1"],
            date="2025-01-01",
        ),
        start_date=date(2025, 1, 1),
        credentials=cred1,
    )

    # With data
    FetchAttemptFactory(
        status=AttemptStatus.SUCCESS,
        import_batch=ImportBatchFullFactory(
            organization=organizations["standalone"],
            platform=platforms["shared"],
            report_type=report_types["pr51"],
            date="2025-01-01",
            create_accesslogs__metrics=[metrics["metric1"], metrics["metric2"]],
        ),
        start_date=date(2025, 1, 1),
        credentials=cred2,
    )

    # unrelated data
    FetchAttemptFactory(
        status=AttemptStatus.SUCCESS,
        import_batch=ImportBatchFullFactory(
            organization=organizations["root"],
            platform=platforms["shared"],
            report_type=report_types["pr1"],
            date="2025-01-01",
            create_accesslogs__metrics=[metrics["metric1"]],
        ),
        start_date=date(2025, 1, 1),
    )


@pytest.fixture(autouse=True)
def ensure_view(clickhouse_db):
    """
    Ensure the AccessLogCubeZeroFillView is created and destroyed after the test.
    """
    try:
        ensure_accesslog_zero_fill_view()
        yield
    finally:
        with ch_backend.pool.get_client() as client:
            client.execute("DROP VIEW IF EXISTS AccessLogCubeZeroFillView")


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
        assert reports[0].credentials[0].has_empty_data is False
        assert reports[0].credentials[0].broken_since.date().isoformat() == "2025-01-03"
        assert reports[0].credentials[1].is_verified is False
        assert reports[0].credentials[1].broken_since is None
        assert reports[0].credentials[1].has_empty_data is False
        assert reports[0].credentials[2].is_verified is True
        assert reports[0].credentials[2].broken_since is None
        assert reports[0].credentials[2].has_empty_data is True
        assert reports[0].data_counts.empty == 1
        assert reports[0].data_counts.missing == 2

        assert reports[1].organization.name == "root"
        assert reports[1].month.isoformat() == "2025-01-01"
        assert reports[1].success_rate is None, "no credentials empty success_rate"
        assert len(reports[1].credentials) == 0
        assert reports[1].data_counts.empty == 0
        assert reports[1].data_counts.missing == 0

        assert reports[2].organization.name == "standalone"
        assert reports[2].month.isoformat() == "2025-01-01"
        assert reports[2].success_rate == 50.0, "one out of two"
        assert len(reports[2].credentials) == 2
        assert reports[2].credentials[0].is_verified is True
        assert reports[2].credentials[0].broken_since is None
        assert reports[2].credentials[0].has_empty_data is False
        assert reports[2].credentials[1].is_verified is False
        assert reports[2].credentials[1].broken_since.date().isoformat() == "2025-02-03"
        assert reports[2].credentials[1].has_empty_data is False
        assert reports[2].data_counts.empty == 0
        assert reports[2].data_counts.missing == 1


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

    def test_grouped_email_was_sent(self, users, report_data, organizations, mailoutbox):
        organizations_pks = [
            v.pk for k, v in organizations.items() if k in ["branch", "standalone", "root"]
        ]
        reports = make_harvest_reports(
            Organization.objects.filter(pk__in=organizations_pks).order_by("name")
        )
        assert send_grouped_harvest_reports(users["master_user"], reports) == 1
        assert len(mailoutbox) == 1


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
    def test_send_harvesting_reports_task(
        self, users, basic1, report_data, organizations, mailoutbox, user, sent_count
    ):
        UserOrganization.objects.update(send_harvest_reports=False)
        tasks.send_harvesting_reports_task()
        assert len(mailoutbox) == 0
        UserOrganization.objects.filter(user=users[user]).update(send_harvest_reports=True)

        users[user].is_active = False
        users[user].save()
        tasks.send_harvesting_reports_task()
        assert len(mailoutbox) == 0, "Don't send emails for deactivated users"

        users[user].is_active = True
        users[user].save()
        tasks.send_harvesting_reports_task()
        assert len(mailoutbox) == sent_count

    def test_send_harvest_report_task(self, users, basic1, report_data, organizations, mailoutbox):
        tasks.send_harvesting_report_task(users["master_admin"].pk, organizations["branch"].pk)
        assert len(mailoutbox) == 1

    def test_send_harvest_report_task_deactivated_user(
        self, users, basic1, report_data, organizations, mailoutbox
    ):
        users["master_admin"].is_active = False
        users["master_admin"].save()
        tasks.send_harvesting_report_task(users["master_admin"].pk, organizations["branch"].pk)
        assert len(mailoutbox) == 0, "Don't send emails for deactivated users"

    @pytest.mark.parametrize(
        "user,sent_count",
        (
            ("master_admin", 1),
            ("master_user", 0),
            ("user2", 0),
            ("user1", 0),
            ("admin1", 1),
            ("admin2", 1),
            ("su", 1),
        ),
    )
    def test_send_grouped_harvesting_reports_task(
        self, users, basic1, report_data, organizations, mailoutbox, user, sent_count
    ):
        User.objects.filter(pk=users[user].pk).update(send_grouped_harvest_reports=False)
        tasks.send_grouped_harvesting_reports_task()
        assert len(mailoutbox) == 0

        User.objects.filter(pk=users[user].pk).update(
            send_grouped_harvest_reports=True, is_active=False
        )
        tasks.send_grouped_harvesting_reports_task()
        assert len(mailoutbox) == 0, "Don't send emails for deactivated users"

        User.objects.filter(pk=users[user].pk).update(is_active=True)
        tasks.send_grouped_harvesting_reports_task()
        assert len(mailoutbox) == sent_count

    def test_send_grouped_harvest_report_task(
        self, users, basic1, report_data, organizations, mailoutbox
    ):
        tasks.send_grouped_harvesting_report_task(users["master_admin"].pk)
        assert len(mailoutbox) == 1


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
        monkeypatch,
        user,
        organization,
        status_code,
        was_sent,
    ):
        x = set()

        def handler(*args, **kwargs):
            x.add(True)

        monkeypatch.setattr(tasks.send_harvesting_report_task, "delay", handler)

        resp = clients[user].post(
            reverse("organization-send-harvest-report", args=(organizations[organization].pk,))
        )
        assert resp.status_code == status_code

        if was_sent:
            assert len(x) == 1, "report for organization was planned to send"
        else:
            assert len(x) == 0, "report for organization was not planned to send"

    @pytest.mark.parametrize(
        "user,status_code",
        (
            ("master_admin", 200),
            ("master_user", 200),
            ("user2", 200),
            ("user1", 200),
            ("admin1", 200),
            ("admin2", 200),
            ("su", 200),
        ),
    )
    def test_send_grouped_harvest_report(
        self, basic1, clients, report_data, mailoutbox, monkeypatch, user, status_code
    ):
        x = set()

        def handler(*args, **kwargs):
            x.add(True)

        monkeypatch.setattr(tasks.send_grouped_harvesting_report_task, "delay", handler)

        resp = clients[user].post(reverse("organization-send-grouped-harvest-report"))
        assert resp.status_code == status_code
        assert len(x) == 1, "report was planned to sent"

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

        tasks.send_harvesting_reports_task()
        assert len(mailoutbox) == sent_count

    @pytest.mark.parametrize(
        "user,enabled,status_code,sent_count",
        (
            ("master_admin", False, 200, 0),
            ("master_user", False, 200, 0),
            ("user2", False, 200, 0),
            ("user1", False, 200, 0),
            ("admin1", False, 200, 0),
            ("admin2", False, 200, 0),
            ("su", False, 200, 0),
            ("master_admin", True, 200, 1),
            ("master_user", True, 200, 0),  # no credentials
            ("user2", True, 200, 0),  # no credentials
            ("user1", True, 200, 0),  # no credentials
            ("admin1", True, 200, 1),
            ("admin2", True, 200, 1),
            ("su", True, 200, 1),
        ),
    )
    def test_grouped_harvest_report(
        self,
        basic1,
        clients,
        organizations,
        report_data,
        mailoutbox,
        user,
        enabled,
        status_code,
        sent_count,
    ):
        assert len(mailoutbox) == 0
        resp = clients[user].post(
            reverse("organization-grouped-harvest-reports"), {"enabled": enabled}
        )
        assert resp.status_code == status_code

        tasks.send_grouped_harvesting_reports_task()
        assert len(mailoutbox) == sent_count
