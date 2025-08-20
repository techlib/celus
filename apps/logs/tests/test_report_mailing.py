import datetime
from datetime import date, timedelta
from unittest import mock

import pytest
from core.fake_data import UserFactory
from django.core.exceptions import PermissionDenied
from django.forms import ValidationError
from django.urls import reverse
from freezegun import freeze_time
from organizations.fake_data import OrganizationFactory
from organizations.models import UserOrganization

from logs.fake_data import ReportTypeFactory
from logs.models import FlexibleReport, FlexibleReportUserEmail, FrequencyChoices
from logs.tasks import send_due_report_mailings_task, send_report_mailing_raw_task


@pytest.fixture
def flexible_reports():
    """
    Creates a set of 3 flexible reports:
    - one owned by an organization
    - one owned by a user
    - not owned by anyone - consortium level report
    """
    org = OrganizationFactory()
    rt = ReportTypeFactory()
    user = UserFactory()
    config = {
        "primary_dimension": "platform",
        "group_by": ["metric"],
        "filters": [
            {"dimension": "report_type", "values": [rt.short_name]},
            {"dimension": "date", "start": "2020-01-01", "end": "2020-01-31"},
        ],
    }
    fr_org = FlexibleReport.objects.create(
        name="Test Report Org", owner_organization=org, report_config=config
    )
    fr_user = FlexibleReport.objects.create(
        name="Test Report User", owner=user, report_config=config
    )
    fr_consortium = FlexibleReport.objects.create(
        name="Test Report Consortium", report_config=config
    )
    return {
        "report_org": fr_org,
        "report_user": fr_user,
        "report_consortium": fr_consortium,
        "org": org,
        "rt": rt,
        "user": user,
    }


@pytest.mark.django_db
class TestReportMailingModel:
    @pytest.mark.parametrize(
        ("today", "end_monthly", "end_quarterly", "end_half_yearly", "end_yearly"),
        [
            ("2025-01-01", "2024-12-31", "2024-12-31", "2024-12-31", "2024-12-31"),
            ("2025-01-31", "2024-12-31", "2024-12-31", "2024-12-31", "2024-12-31"),
            ("2025-02-01", "2025-01-31", "2024-12-31", "2024-12-31", "2024-12-31"),
            ("2025-04-20", "2025-03-31", "2025-03-31", "2024-12-31", "2024-12-31"),
            ("2025-07-20", "2025-06-30", "2025-06-30", "2025-06-30", "2024-12-31"),
            ("2025-10-20", "2025-09-30", "2025-09-30", "2025-06-30", "2024-12-31"),
            ("2025-12-20", "2025-11-30", "2025-09-30", "2025-06-30", "2024-12-31"),
        ],
    )
    def test_last_period_end(
        self, flexible_reports, today, end_monthly, end_quarterly, end_half_yearly, end_yearly
    ):
        """
        Test that the next send date is calculated correctly - it should be one month
        after the last period end date.
        """
        fr = flexible_reports["report_user"]
        with freeze_time(today):
            for period, exp in zip(
                [
                    FrequencyChoices.MONTHLY,
                    FrequencyChoices.QUARTERLY,
                    FrequencyChoices.HALF_YEARLY,
                    FrequencyChoices.YEARLY,
                ],
                [end_monthly, end_quarterly, end_half_yearly, end_yearly],
            ):
                fru = FlexibleReportUserEmail.objects.create(
                    user=flexible_reports["user"], flexible_report=fr, frequency=period
                )
                assert str(fru.last_period_end) == exp

    # we will test with a fiscal year starting in May
    @pytest.mark.parametrize(
        ("today", "end_monthly", "end_quarterly", "end_half_yearly", "end_yearly"),
        [
            ("2025-01-01", "2024-12-31", "2024-10-31", "2024-10-31", "2024-04-30"),
            ("2025-01-31", "2024-12-31", "2024-10-31", "2024-10-31", "2024-04-30"),
            ("2025-02-01", "2025-01-31", "2025-01-31", "2024-10-31", "2024-04-30"),
            ("2025-04-20", "2025-03-31", "2025-01-31", "2024-10-31", "2024-04-30"),
            ("2025-07-20", "2025-06-30", "2025-04-30", "2025-04-30", "2025-04-30"),
            ("2025-10-20", "2025-09-30", "2025-07-31", "2025-04-30", "2025-04-30"),
            ("2025-12-20", "2025-11-30", "2025-10-31", "2025-10-31", "2025-04-30"),
        ],
    )
    def test_last_period_end_with_fiscal_year(
        self, flexible_reports, today, end_monthly, end_quarterly, end_half_yearly, end_yearly
    ):
        """
        Test that the next send date is calculated correctly - it should be one month
        after the last period end date.
        """
        fr = flexible_reports["report_user"]
        fr.owner.extra_data["fiscal_year_start_month"] = 4  # May
        fr.owner.save()
        with freeze_time(today):
            for period, exp in zip(
                [
                    FrequencyChoices.MONTHLY,
                    FrequencyChoices.QUARTERLY,
                    FrequencyChoices.HALF_YEARLY,
                    FrequencyChoices.YEARLY,
                ],
                [end_monthly, end_quarterly, end_half_yearly, end_yearly],
            ):
                fru = FlexibleReportUserEmail.objects.create(
                    user=flexible_reports["user"],
                    flexible_report=fr,
                    frequency=period,
                    fiscal_period=True,
                )
                assert str(fru.last_period_end) == exp

    @pytest.mark.parametrize(
        ("today", "exp_monthly", "exp_quarterly", "exp_half_yearly", "exp_yearly"),
        [
            ("2025-01-01", "2025-01-31", "2025-01-31", "2025-01-31", "2025-01-31"),
            ("2025-01-31", "2025-01-31", "2025-01-31", "2025-01-31", "2025-01-31"),
            ("2025-02-01", "2025-02-28", "2025-04-30", "2025-07-31", "2026-01-31"),
            ("2025-02-02", "2025-02-28", "2025-04-30", "2025-07-31", "2026-01-31"),
            ("2025-04-20", "2025-04-30", "2025-04-30", "2025-07-31", "2026-01-31"),
            ("2025-10-20", "2025-10-31", "2025-10-31", "2026-01-31", "2026-01-31"),
        ],
    )
    def test_plan_next_send_date(
        self, flexible_reports, today, exp_monthly, exp_quarterly, exp_half_yearly, exp_yearly
    ):
        """
        Test that the next send date is calculated correctly - it should be one month
        after the last period end date.
        """
        fr = flexible_reports["report_user"]
        with freeze_time(today):
            for period, exp in zip(
                [
                    FrequencyChoices.MONTHLY,
                    FrequencyChoices.QUARTERLY,
                    FrequencyChoices.HALF_YEARLY,
                    FrequencyChoices.YEARLY,
                ],
                [exp_monthly, exp_quarterly, exp_half_yearly, exp_yearly],
            ):
                fru = FlexibleReportUserEmail.objects.create(
                    user=flexible_reports["user"], flexible_report=fr, frequency=period
                )
                assert str(fru.plan_next_send()) == exp

    @pytest.mark.parametrize(
        ("ref_date", "exp_monthly", "exp_quarterly", "exp_half_yearly", "exp_yearly"),
        [
            ("2025-01-01", "2025-01-31", "2025-01-31", "2025-01-31", "2025-01-31"),
            ("2025-01-31", "2025-01-31", "2025-01-31", "2025-01-31", "2025-01-31"),
            ("2025-02-01", "2025-02-28", "2025-04-30", "2025-07-31", "2026-01-31"),
            ("2025-02-02", "2025-02-28", "2025-04-30", "2025-07-31", "2026-01-31"),
            ("2025-04-20", "2025-04-30", "2025-04-30", "2025-07-31", "2026-01-31"),
            ("2025-10-20", "2025-10-31", "2025-10-31", "2026-01-31", "2026-01-31"),
        ],
    )
    def test_plan_next_send_ref_date(
        self, flexible_reports, ref_date, exp_monthly, exp_quarterly, exp_half_yearly, exp_yearly
    ):
        """
        Test that the next send date is calculated correctly when a different reference date
        is used.
        """
        fr = flexible_reports["report_user"]
        with freeze_time("2024-01-01"):
            for period, exp in zip(
                [
                    FrequencyChoices.MONTHLY,
                    FrequencyChoices.QUARTERLY,
                    FrequencyChoices.HALF_YEARLY,
                    FrequencyChoices.YEARLY,
                ],
                [exp_monthly, exp_quarterly, exp_half_yearly, exp_yearly],
            ):
                fru = FlexibleReportUserEmail.objects.create(
                    user=flexible_reports["user"], flexible_report=fr, frequency=period
                )
                assert str(fru.plan_next_send(date.fromisoformat(ref_date))) == exp


@pytest.mark.django_db
class TestReportMailingCreationAndAccess:
    def test_create_report_mailing_user_owned(self, flexible_reports):
        """
        Test that user who owns the report can create a mailing for it.
        """
        user = flexible_reports["user"]
        FlexibleReportUserEmail.objects.create(
            user=user, flexible_report=flexible_reports["report_user"]
        )
        assert user.flexible_report_emails.count() == 1

    def test_create_report_mailing_org_owned(self, flexible_reports):
        """
        Test that user can create a mailing for a report its organization owns.
        """
        org = flexible_reports["org"]
        user = UserFactory()
        UserOrganization.objects.create(user=user, organization=org, is_admin=True)
        FlexibleReportUserEmail.objects.create(
            user=user, flexible_report=flexible_reports["report_org"]
        )
        assert user.flexible_report_emails.count() == 1

    def test_create_report_mailing_consortium_owned(self, flexible_reports):
        """
        Test that any user can create a mailing for a consortium-owned report.
        """
        user = UserFactory()  # any user at all
        FlexibleReportUserEmail.objects.create(
            user=user, flexible_report=flexible_reports["report_consortium"]
        )
        assert user.flexible_report_emails.count() == 1

    def test_create_report_mailing_different_owner(self, flexible_reports):
        """
        Test that user cannot create a mailing for a report owned by another user.
        """
        user = UserFactory()
        with pytest.raises(PermissionDenied):
            FlexibleReportUserEmail.objects.create(
                user=user, flexible_report=flexible_reports["report_user"]
            )
        assert user.flexible_report_emails.count() == 0

    def test_create_report_mailing_different_owner_org(self, flexible_reports):
        """
        Test that user cannot create a mailing for a report owned by another organization.
        """
        user = UserFactory()
        with pytest.raises(PermissionDenied):
            FlexibleReportUserEmail.objects.create(
                user=user, flexible_report=flexible_reports["report_org"]
            )
        assert user.flexible_report_emails.count() == 0

    def test_incompatible_access_level(self, flexible_reports):
        """
        Test that if user loses access to a report, the mailing model cannot be used
        for sending emails.
        """
        user = flexible_reports["user"]
        fr = flexible_reports["report_user"]
        fru = FlexibleReportUserEmail.objects.create(user=user, flexible_report=fr)
        assert user.flexible_report_emails.count() == 1

        # remove access to the report by changing the owner
        fr.owner = UserFactory()
        fr.save()
        with pytest.raises(PermissionDenied):
            with mock.patch("core.tasks.async_mail_admins.delay") as mock_mail_admins:
                fru.send_email()
                # email should be sent to admins about the failed attempt
                mock_mail_admins.assert_called_once()

    def test_change_in_access_level(self, flexible_reports):
        """
        Test that if the report is changed so that the user does not have access to it,
        the mailing object is removed.
        """
        # create a new user with access to the organization report
        org = flexible_reports["org"]
        user = UserFactory()
        UserOrganization.objects.create(user=user, organization=org, is_admin=False)
        # create a mailing for the report
        fr = flexible_reports["report_org"]
        fru = FlexibleReportUserEmail.objects.create(user=user, flexible_report=fr)
        # modify the report so that the user does not have access to it anymore
        fr.owner = UserFactory()
        fr.owner_organization = None
        fr.save()
        # check that the mailing object is removed
        assert not FlexibleReportUserEmail.objects.filter(pk=fru.pk).exists()


@pytest.mark.django_db
class TestReportMailingSending:
    def test_send_mailing(self, flexible_reports, mailoutbox):
        """
        Test that a mailing can be sent.
        """
        user = flexible_reports["user"]
        fr = flexible_reports["report_user"]
        fru = FlexibleReportUserEmail.objects.create(user=user, flexible_report=fr)
        assert fru.last_sent is None
        assert fru.next_send is not None
        prev_next_send = fru.next_send
        with freeze_time(prev_next_send):
            fru.send_email()
        assert fru.last_sent is not None
        assert fru.next_send > prev_next_send
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [user.email]
        assert mailoutbox[0].subject == 'Report "Test Report User"'
        assert mailoutbox[0].attachments[0][0] == "Test Report User.xlsx"

    @pytest.mark.parametrize(
        ("period", "period_count", "today", "exp_start", "exp_end"),
        [
            (FrequencyChoices.MONTHLY, 1, "2025-01-20", "2024-12-01", "2024-12-31"),
            (FrequencyChoices.MONTHLY, 12, "2025-01-20", "2024-01-01", "2024-12-31"),
            (FrequencyChoices.QUARTERLY, 1, "2025-01-20", "2024-10-01", "2024-12-31"),
            (FrequencyChoices.QUARTERLY, 1, "2025-03-20", "2024-10-01", "2024-12-31"),
            (FrequencyChoices.HALF_YEARLY, 1, "2025-01-20", "2024-07-01", "2024-12-31"),
            (FrequencyChoices.HALF_YEARLY, 1, "2025-05-20", "2024-07-01", "2024-12-31"),
            (FrequencyChoices.HALF_YEARLY, 1, "2025-07-20", "2025-01-01", "2025-06-30"),
            (FrequencyChoices.YEARLY, 1, "2025-01-20", "2024-01-01", "2024-12-31"),
            (FrequencyChoices.YEARLY, 1, "2025-07-20", "2024-01-01", "2024-12-31"),
        ],
    )
    def test_date_adjustment(
        self, flexible_reports, period, period_count, today, exp_start, exp_end
    ):
        """
        Test that the dates in the report are adjusted correctly
        """
        user = flexible_reports["user"]
        fr = flexible_reports["report_user"]
        fru = FlexibleReportUserEmail(
            user=user, flexible_report=fr, frequency=period, number_of_periods=period_count
        )  # using the model without saving should work as well
        with (
            mock.patch(
                "logs.logic.reporting.slicer.FlexibleDataSlicer.create_from_config"
            ) as mock_create,
            freeze_time(today),
        ):
            # make sure to stop processing after create_from_config is called
            # - we just want to test the config passed to it, not the subsequent code
            mock_create.side_effect = ValueError("test")
            with pytest.raises(ValueError):
                fru.send_email()
            mock_create.assert_called_once()
            config = mock_create.call_args[0][0]
            date_filter = next(filter(lambda f: f["dimension"] == "date", config["filters"]))
            assert date_filter is not None
            assert date_filter["start"] == exp_start
            assert date_filter["end"] == exp_end

    @pytest.mark.parametrize(
        ("period", "period_count", "today", "exp_start1", "exp_start2"),
        [
            (FrequencyChoices.MONTHLY, 12, "2025-01-20", "2024-01-01", "2024-07-01"),
            (FrequencyChoices.QUARTERLY, 2, "2025-01-20", "2024-07-01", "2024-10-01"),
            (FrequencyChoices.HALF_YEARLY, 4, "2025-05-20", "2023-01-01", "2024-01-01"),
            (FrequencyChoices.YEARLY, 4, "2025-07-20", "2021-01-01", "2023-01-01"),
        ],
    )
    def test_date_adjustment_with_trend_mode(
        self, flexible_reports, period, period_count, today, exp_start1, exp_start2
    ):
        """
        Test that the dates in the report are adjusted correctly when trend-mode is active
        (in such case, the date filters are different)
        """
        user = flexible_reports["user"]
        fr: FlexibleReport = flexible_reports["report_user"]
        fr.report_config["trend_mode"] = True
        fr.save()

        fru = FlexibleReportUserEmail(
            user=user, flexible_report=fr, frequency=period, number_of_periods=period_count
        )  # using the model without saving should work as well
        with (
            mock.patch(
                "logs.logic.reporting.slicer.FlexibleDataSlicer.create_from_config"
            ) as mock_create,
            freeze_time(today),
        ):
            # make sure to stop processing after create_from_config is called
            # - we just want to test the config passed to it, not the subsequent code
            mock_create.side_effect = ValueError("test")
            with pytest.raises(ValueError):
                fru.send_email()
            mock_create.assert_called_once()
            config = mock_create.call_args[0][0]
            date_filter1 = next(
                filter(lambda f: f["dimension"] == "date", config["base_subset_filters"])
            )
            assert date_filter1 is not None
            assert date_filter1["start"] == exp_start1
            assert date_filter1["end"] == str(date.fromisoformat(exp_start2) - timedelta(days=1))
            date_filter2 = next(
                filter(lambda f: f["dimension"] == "date", config["compared_subset_filters"])
            )
            assert date_filter2 is not None
            assert date_filter2["start"] == exp_start2

    def test_odd_number_of_periods_in_trend_mode_not_allowed(self, flexible_reports):
        """
        Test that the dates in the report are adjusted correctly when trend-mode is active
        (in such case, the date filters are different)
        """
        user = flexible_reports["user"]
        fr: FlexibleReport = flexible_reports["report_user"]
        fr.report_config["trend_mode"] = True
        fr.save()
        # no problem with even number of periods
        FlexibleReportUserEmail.objects.create(
            user=user, flexible_report=fr, frequency=FrequencyChoices.MONTHLY, number_of_periods=2
        )
        # but odd number of periods should fail
        with pytest.raises(ValidationError):
            FlexibleReportUserEmail.objects.create(
                user=user,
                flexible_report=fr,
                frequency=FrequencyChoices.MONTHLY,
                number_of_periods=3,
            )

    @pytest.mark.django_db(
        transaction=True
    )  # needed to make select_for_update work as in production
    def test_send_due_mailing(self, flexible_reports, mailoutbox):
        """
        Test that a due mailing task performs as expected
        """
        user = flexible_reports["user"]
        fr = flexible_reports["report_user"]
        fru = FlexibleReportUserEmail.objects.create(user=user, flexible_report=fr)
        with freeze_time("2025-01-31"):
            fru.save()
            # run the task manually and check that the email is sent
            send_due_report_mailings_task()
            # check that the email is sent
            assert len(mailoutbox) == 1
            assert mailoutbox[0].to == [user.email]
            assert mailoutbox[0].subject == 'Report "Test Report User"'
            # check that the last sent date is set
            fru.refresh_from_db()
            assert str(fru.last_sent).startswith("2025-01-31")
            # check that the next send date is set
            assert str(fru.next_send) == "2025-02-28"


@pytest.mark.django_db
class TestReportMailingSendingAPI:
    expected_fields = {
        "pk",
        "user",
        "flexible_report",
        "frequency",
        "number_of_periods",
        "last_sent",
        "next_send",
        "last_updated",
        "last_updated_by",
        "fiscal_period",
    }

    def test_send_mailing(self, flexible_reports, mailoutbox, client):
        """
        Test that a mailing can be sent via the API
        """
        user = UserFactory()
        url = reverse("report-mailing-test")
        client.force_login(user)
        assert not FlexibleReportUserEmail.objects.filter(user=user).exists()
        with mock.patch("logs.views.send_report_mailing_raw_task.delay") as mock_send:
            response = client.post(
                url,
                data={
                    "flexible_report": flexible_reports["report_consortium"].pk,
                    "user": user.pk,
                    "frequency": FrequencyChoices.MONTHLY,
                    "number_of_periods": 1,
                },
            )
            assert response.status_code == 200
            assert response.json() == {"message": "Email sent", "success": True}
            mock_send.assert_called_once()
        # now run the task manually and check that the email is sent
        send_report_mailing_raw_task(mock_send.call_args[0][0])
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [user.email]
        assert mailoutbox[0].subject == 'Report "Test Report Consortium"'
        assert mailoutbox[0].attachments[0][0] == "Test Report Consortium.xlsx"
        assert not FlexibleReportUserEmail.objects.filter(user=user).exists()

    def test_mail_sending_permission_check(self, flexible_reports, client):
        """
        Test that the mail sending without save checks the permissions as well
        """
        user = UserFactory()
        url = reverse("report-mailing-test")
        client.force_login(user)
        response = client.post(
            url,
            data={
                "flexible_report": flexible_reports["report_user"].pk,
                "user": user.pk,
                "frequency": FrequencyChoices.MONTHLY,
                "number_of_periods": 1,
            },
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "You do not have permission to perform this action."

    def test_mail_sending_to_foreign_user_fails(self, flexible_reports, admin_client):
        """
        Test that the mail sending by legitimate user to a foreign user
        (who has no access to the report) fails
        """
        user = UserFactory()
        url = reverse("report-mailing-test")
        # even superuser cannot send to a user who has no access to the report
        response = admin_client.post(
            url,
            data={
                "flexible_report": flexible_reports["report_user"].pk,
                "user": user.pk,
                "frequency": FrequencyChoices.MONTHLY,
                "number_of_periods": 1,
            },
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "You do not have permission to perform this action."

    def test_mail_sending_to_invisible_user_fails(self, flexible_reports, client):
        """
        Test that the mail sending by legitimate user to another legitimate user
        fails if the sending user has no access to the target user
        """
        user = UserFactory()
        url = reverse("report-mailing-test")
        client.force_login(flexible_reports["user"])
        # anybody can access the consortium report
        response = client.post(
            url,
            data={
                "flexible_report": flexible_reports["report_consortium"].pk,
                "user": user.pk,
                "frequency": FrequencyChoices.MONTHLY,
                "number_of_periods": 1,
            },
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "You do not have permission to perform this action."

    def test_test_mail_with_odd_number_of_periods_fails(self, flexible_reports, client):
        """
        Test that the number of periods is validated correctly - it cannot be odd
        if trend mode is active.
        (The restriction is also enforced on the model level in save method, but when the model is
        not saved in the `test` method, the validation is needed in the serializer as well. This is
        what we test here.)
        """
        user = flexible_reports["user"]
        fr = flexible_reports["report_user"]
        fr.report_config["trend_mode"] = True
        fr.save()
        url = reverse("report-mailing-test")
        client.force_login(user)
        response = client.post(
            url,
            data={
                "flexible_report": fr.pk,
                "user": user.pk,
                "frequency": FrequencyChoices.MONTHLY,
                "number_of_periods": 3,
            },
        )
        assert response.status_code == 400
        assert (
            response.json()["non_field_errors"][0]
            == "Number of periods cannot be odd if trend mode is active"
        )

    def test_create_mailing(self, flexible_reports, client):
        """
        Test that a mailing can be created via the API
        """
        user = flexible_reports["user"]
        url = reverse("report-mailing-list")
        client.force_login(user)
        response = client.post(
            url,
            data={
                "flexible_report": flexible_reports["report_user"].pk,
                "user": user.pk,
                "frequency": FrequencyChoices.MONTHLY,
                "number_of_periods": 1,
            },
        )
        assert response.status_code == 201
        assert FlexibleReportUserEmail.objects.filter(user=user).count() == 1
        assert set(response.json().keys()) == self.expected_fields
        assert response.json()["next_send"] is not None

    def test_list(self, flexible_reports, client):
        """
        Test that the list of mailings can be accessed, but only for the user's own mailings
        """
        # create a foreign mailing
        FlexibleReportUserEmail.objects.create(
            user=UserFactory(), flexible_report=flexible_reports["report_consortium"]
        )

        # test that the user can see only their own mailings
        user = flexible_reports["user"]
        url = reverse("report-mailing-list")
        client.force_login(user)
        assert FlexibleReportUserEmail.objects.filter(user=user).count() == 0
        assert FlexibleReportUserEmail.objects.count() == 1
        response = client.get(url)
        assert response.status_code == 200
        assert len(response.json()) == 0

        # create a mailing for the user and check again
        FlexibleReportUserEmail.objects.create(
            user=user, flexible_report=flexible_reports["report_user"]
        )
        response = client.get(url)
        assert response.status_code == 200
        assert len(response.json()) == 1
        # test the output data structure
        mailing = response.json()[0]
        assert set(mailing.keys()) == self.expected_fields
        assert mailing["user"]["pk"] == user.pk
        assert mailing["user"]["email"] == user.email
        assert mailing["last_updated_by"] is None
        assert mailing["flexible_report"] == flexible_reports["report_user"].pk
        assert mailing["frequency"] == FrequencyChoices.MONTHLY
        assert mailing["number_of_periods"] == 1
        assert mailing["fiscal_period"] is False
        assert mailing["last_updated"] is not None
        assert mailing["last_sent"] is None
        assert mailing["next_send"] is not None

    def test_list_filtered_by_report_consortial_level(self, flexible_reports, client, settings):
        """
        Test that the list of mailings can be filtered by report. In that case,
        even mailings for other users should be returned, but there are some rules
        based on the report access level.

        Note: this API endpoint is on the report detail view, not on the mailing list view.

        - personal report: only the user can create a mailing for it, so it is easy
          - the user can see only his own mailings
        - organization report:
          - if the user is organization admin, they can see all mailings for the report
          - otherwise, they can only see their own mailings
        - consortium report:
          - if the user is consortium admin, they can see all mailings for the report
          - otherwise, they can only see their own mailings
        """
        master_org = OrganizationFactory(internal_id="foobar")
        settings.MASTER_ORGANIZATIONS = [master_org.internal_id]
        user1 = UserFactory(is_superuser=True)  # superuser
        user2 = UserFactory()  # plain user
        user3 = UserFactory()  # consortium admin
        UserOrganization.objects.create(user=user3, organization=master_org, is_admin=True)
        # create a mailing for the consortium report
        FlexibleReportUserEmail.objects.create(
            user=user1, flexible_report=flexible_reports["report_consortium"]
        )
        FlexibleReportUserEmail.objects.create(
            user=user2, flexible_report=flexible_reports["report_consortium"]
        )
        FlexibleReportUserEmail.objects.create(
            user=user3, flexible_report=flexible_reports["report_consortium"]
        )
        # test that superuser can see all mailings, just not the other consortium admins
        url = reverse("flexible-report-mailings", args=[flexible_reports["report_consortium"].pk])
        client.force_login(user1)
        response = client.get(url)
        assert response.status_code == 200
        assert len(response.json()) == 2
        user_ids = [r["user"]["pk"] for r in response.json()]
        assert user1.pk in user_ids
        assert user2.pk in user_ids
        assert user3.pk not in user_ids

        # test that normal user can see only their own mailings
        client.force_login(user2)
        response = client.get(url)
        assert response.status_code == 200
        assert len(response.json()) == 1
        user_ids = [r["user"]["pk"] for r in response.json()]
        assert user1.pk not in user_ids
        assert user2.pk in user_ids
        assert user3.pk not in user_ids

        # test that consortium admin can see all mailings, just not the superuser
        client.force_login(user3)
        response = client.get(url)
        assert response.status_code == 200
        assert len(response.json()) == 2
        user_ids = [r["user"]["pk"] for r in response.json()]
        assert user1.pk not in user_ids
        assert user2.pk in user_ids
        assert user3.pk in user_ids

    def test_list_filtered_by_report_organization_level(self, flexible_reports, client, settings):
        """
        Test that the list of mailings can be filtered by report. In that case,
        even mailings for other users should be returned, but there are some rules
        based on the report access level.
        """
        org = flexible_reports["org"]
        user1 = UserFactory(is_superuser=True)  # superuser
        user2 = UserFactory()  # plain user
        user3 = UserFactory()  # organization admin
        UserFactory(is_superuser=True)  # another superuser - should not be visible anywhere

        UserOrganization.objects.create(user=user2, organization=org, is_admin=False)
        UserOrganization.objects.create(user=user3, organization=org, is_admin=True)
        # create a mailing for the organization report
        FlexibleReportUserEmail.objects.create(
            user=user1, flexible_report=flexible_reports["report_org"]
        )
        FlexibleReportUserEmail.objects.create(
            user=user2, flexible_report=flexible_reports["report_org"]
        )
        FlexibleReportUserEmail.objects.create(
            user=user3, flexible_report=flexible_reports["report_org"]
        )
        # test that superuser can see all mailings
        url = reverse("flexible-report-mailings", args=[flexible_reports["report_org"].pk])
        client.force_login(user1)
        response = client.get(url)
        assert response.status_code == 200
        assert len(response.json()) == 3
        user_ids = [r["user"]["pk"] for r in response.json()]
        assert user1.pk in user_ids
        assert user2.pk in user_ids
        assert user3.pk in user_ids

        # test that normal user can see only their own mailings
        client.force_login(user2)
        response = client.get(url)
        assert response.status_code == 200
        assert len(response.json()) == 1
        user_ids = [r["user"]["pk"] for r in response.json()]
        assert user1.pk not in user_ids
        assert user2.pk in user_ids
        assert user3.pk not in user_ids

        # test that organization admin can see all mailings, but not the superusers
        client.force_login(user3)
        response = client.get(url)
        assert response.status_code == 200
        assert len(response.json()) == 2
        user_ids = [r["user"]["pk"] for r in response.json()]
        assert user1.pk not in user_ids
        assert user2.pk in user_ids
        assert user3.pk in user_ids

    def test_list_filtered_by_report_user_level(self, flexible_reports, client):
        """
        Test that the list of mailings can be filtered by report. In that case,
        even mailings for other users should be returned, but there are some rules
        based on the report access level.
        """
        user1 = UserFactory(is_superuser=True)  # superuser
        user2 = flexible_reports["user"]
        user3 = UserFactory()  # another user
        # create a mailing for the user report
        with pytest.raises(PermissionDenied):
            # even superuser should not be able to create a mailing for the user report
            FlexibleReportUserEmail.objects.create(
                user=user1, flexible_report=flexible_reports["report_user"]
            )
        FlexibleReportUserEmail.objects.create(
            user=user2, flexible_report=flexible_reports["report_user"]
        )
        with pytest.raises(PermissionDenied):
            # user3 should not be able to create a mailing for the user report
            FlexibleReportUserEmail.objects.create(
                user=user3, flexible_report=flexible_reports["report_user"]
            )
        # test that superuser can see all mailings
        url = reverse("flexible-report-mailings", args=[flexible_reports["report_user"].pk])
        client.force_login(user1)
        response = client.get(url)
        assert response.status_code == 404

        # test that normal user can see only their own mailings
        client.force_login(user2)
        response = client.get(url)
        assert response.status_code == 200
        assert len(response.json()) == 1
        user_ids = [r["user"]["pk"] for r in response.json()]
        assert user1.pk not in user_ids
        assert user2.pk in user_ids
        assert user3.pk not in user_ids

        # test that another user cannot see the report
        client.force_login(user3)
        response = client.get(url)
        assert response.status_code == 404

    def test_flexible_report_users_with_view_permission(self, flexible_reports):
        """
        Test that the users with view permission can see the mailings
        """
        org = flexible_reports["org"]
        user_admin = UserFactory()
        user_ro = UserFactory()
        user_foreign = UserFactory()
        su = UserFactory(is_superuser=True)
        UserOrganization.objects.create(user=user_admin, organization=org, is_admin=True)
        UserOrganization.objects.create(user=user_ro, organization=org, is_admin=False)
        fr = flexible_reports["report_org"]
        assert fr.users_with_view_access().count() == 3, "1 org admin + 1 org user + 1 su"
        assert user_ro in fr.users_with_view_access()
        assert user_admin in fr.users_with_view_access()
        assert su in fr.users_with_view_access()
        assert user_foreign not in fr.users_with_view_access()
        # test users with edit access
        assert fr.users_with_edit_access().count() == 2, "1 org admin + 1 su"
        assert user_admin in fr.users_with_edit_access()
        assert su in fr.users_with_edit_access()
        assert user_foreign not in fr.users_with_edit_access()
        assert user_ro not in fr.users_with_edit_access()

    def test_flexible_report_mailing_detail(self, flexible_reports, client):
        """
        Test that the detail of a mailing can be accessed
        """
        user = flexible_reports["user"]
        fru = FlexibleReportUserEmail.objects.create(
            user=user, flexible_report=flexible_reports["report_user"]
        )
        url = reverse("report-mailing-detail", args=[fru.pk])
        client.force_login(user)
        response = client.get(url)
        assert response.status_code == 200
        assert set(response.json().keys()) == self.expected_fields

    def test_flexible_report_mailing_update(self, flexible_reports, client):
        """
        Test that a mailing can be updated via the API and that it updates the next_send date
        if the frequency is changed.
        """
        user = flexible_reports["user"]
        with freeze_time("2025-02-20"):
            fru = FlexibleReportUserEmail.objects.create(
                user=user, flexible_report=flexible_reports["report_user"]
            )
            # check the next_send date
            assert fru.next_send == datetime.date(2025, 2, 28)

            url = reverse("report-mailing-detail", args=[fru.pk])
            client.force_login(user)

            # update the frequency
            response = client.patch(
                url, data={"frequency": FrequencyChoices.QUARTERLY}, content_type="application/json"
            )
            assert response.status_code == 200
            fru.refresh_from_db()
            assert fru.frequency == FrequencyChoices.QUARTERLY
            assert set(response.json().keys()) == self.expected_fields
            assert response.json()["frequency"] == FrequencyChoices.QUARTERLY
            assert response.json()["next_send"] == "2025-04-30", "month after quarter end"
