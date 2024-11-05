from datetime import date

import pytest
from core.models import UL_CONS_STAFF, UL_ORG_ADMIN
from django.urls import reverse
from django.utils import timezone
from freezegun import freeze_time
from logs.fake_data import ImportBatchFullFactory
from organizations.tests.conftest import identity_by_user_type  # noqa
from scheduler.fake_data import FetchIntentionFactory
from scheduler.models import Automatic

from sushi.fake_data import CredentialsFactory, FetchAttemptFactory
from sushi.models import AttemptStatus, CounterReportsToCredentials, SushiCredentials
from sushi.models import BrokenCredentialsMixin as BS
from test_scenarios.basic import (  # noqa - fixtures
    basic1,
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


@pytest.mark.django_db()
class TestSushiCredentialsViewSet:
    @pytest.mark.parametrize("use_org_id", [(True,), (False,)])
    @pytest.mark.parametrize(
        "user,can_list,can_lock",
        (
            ("master_admin", True, True),
            ("master_user", False, False),
            ("admin1", False, False),
            ("admin2", True, False),  # is admin of standalone
            ("user1", False, False),
            ("user2", False, False),  # user2 is part of standalone, but not an admin
        ),
    )
    def test_list_permissions(
        self, basic1, organizations, platforms, clients, user, can_list, use_org_id, can_lock
    ):
        CredentialsFactory(
            organization=organizations["standalone"],
            platform=platforms["standalone"],
            counter_version=5,
            lock_level=SushiCredentials.UNLOCKED,
        )
        params = {"organization": organizations["standalone"].pk} if use_org_id else {}
        resp = clients[user].get(reverse("sushi-credentials-list"), params)
        if can_list:
            assert resp.status_code == 200
            assert len(resp.json()) == 1
            assert resp.json()[0]["can_lock"] == can_lock
        else:
            # there are actually two mechanisms how the access could be denied -
            # either the list is empty or 404 is returned. The latter is used when
            # an organization filter is used which is incompatible with the currently active user
            assert resp.status_code == 404 or len(resp.json()) == 0

    @pytest.mark.parametrize(
        "user,can_see",
        (
            ("master_admin", True),
            ("master_user", False),
            ("admin1", False),
            ("admin2", True),  # is admin of standalone
            ("user1", False),
            ("user2", False),  # user2 is part of standalone, but not an admin
        ),
    )
    def test_detail_permissions(self, basic1, organizations, platforms, clients, user, can_see):
        credentials = CredentialsFactory(
            organization=organizations["standalone"],
            platform=platforms["standalone"],
            counter_version=5,
            lock_level=SushiCredentials.UNLOCKED,
        )
        resp = clients[user].get(reverse("sushi-credentials-detail", args=(credentials.pk,)))
        if can_see:
            assert resp.status_code == 200
        else:
            assert resp.status_code == 404

    def test_lock_action(self, basic1, organizations, platforms, clients):
        credentials = CredentialsFactory(
            organization=organizations["master"],
            platform=platforms["master"],
            counter_version=5,
            lock_level=SushiCredentials.UNLOCKED,
        )
        url = reverse("sushi-credentials-lock", args=(credentials.pk,))
        resp = clients["master_admin"].post(url, {})
        assert resp.status_code == 200
        credentials.refresh_from_db()
        assert credentials.lock_level == UL_CONS_STAFF

    def test_lock_action_no_permission(self, basic1, organizations, platforms, clients):
        credentials = CredentialsFactory(
            organization=organizations["empty"],
            platform=platforms["empty"],
            counter_version=5,
            lock_level=UL_CONS_STAFF,
        )
        url = reverse("sushi-credentials-lock", args=(credentials.pk,))
        resp = clients["user1"].post(url, {})
        assert resp.status_code == 403
        credentials.refresh_from_db()
        assert credentials.lock_level == UL_CONS_STAFF

    def test_create_action(
        self, basic1, organizations, platforms, clients, users, counter_report_types
    ):
        url = reverse("sushi-credentials-list")

        title = "Foo bar credentials"
        resp = clients["admin1"].post(
            url,
            {
                "title": title,
                "platform_id": platforms["root"].pk,
                "organization_id": organizations["root"].pk,
                "url": "http://foo.bar.baz",
                "requestor_id": "xxxxxxx",
                "customer_id": "yyyyy",
                "counter_version": "5",
                "counter_reports": [counter_report_types["tr"].pk],
            },
        )
        assert resp.status_code == 201
        sc = SushiCredentials.objects.get()
        assert sc.last_updated_by == users["admin1"]
        assert sc.counter_reports.count() == 1
        assert sc.title == title

    def test_create_action_with_duplicated_credentials(
        self, basic1, organizations, platforms, clients, users, counter_report_types
    ):
        url = reverse("sushi-credentials-list")
        data = {
            "title": "Foo bar credentials",
            "platform_id": platforms["root"].pk,
            "organization_id": organizations["root"].pk,
            "url": "http://foo.bar.baz",
            "requestor_id": "xxxxxxx",
            "customer_id": "yyyyy",
            "counter_version": "5",
            "counter_reports": [counter_report_types["tr"].pk],
        }
        assert SushiCredentials.objects.count() == 0
        resp = clients["admin1"].post(url, data)
        assert resp.status_code == 201
        assert SushiCredentials.objects.count() == 1
        # now try to create the same credentials again with slightly different data
        data["title"] = "New title"
        data["requestor_id"] = "zzzzzz"
        resp = clients["admin1"].post(url, data)
        assert resp.status_code == 400
        assert SushiCredentials.objects.count() == 1, "No new credentials should be created"

    def test_edit_action(self, basic1, organizations, platforms, clients):
        credentials = CredentialsFactory(
            title="",
            organization=organizations["root"],
            platform=platforms["root"],
            counter_version=5,
            lock_level=UL_ORG_ADMIN,
            url="http://a.b.c/",
        )
        assert credentials.title == ""
        url = reverse("sushi-credentials-detail", args=(credentials.pk,))
        new_url = "http://x.y.com/"
        new_title = "New title"
        resp = clients["admin1"].patch(url, {"url": new_url, "title": new_title})
        assert resp.status_code == 200
        credentials.refresh_from_db()
        assert credentials.url == new_url
        assert credentials.title == new_title

    def test_edit_action_cannot_create_duplicated_credentials(
        self, basic1, organizations, platforms, clients
    ):
        CredentialsFactory(
            organization=organizations["root"], platform=platforms["root"], counter_version=5
        )
        cr4 = CredentialsFactory(
            organization=organizations["root"], platform=platforms["root"], counter_version=4
        )
        url = reverse("sushi-credentials-detail", args=(cr4.pk,))
        # try to change the counter version to 5, which is already used by another credentials
        resp = clients["admin1"].patch(url, {"counter_version": 5})
        assert resp.status_code == 400
        cr4.refresh_from_db()
        assert cr4.counter_version == 4, "The counter version should not be changed"

    def test_edit_action_locked(self, basic1, organizations, platforms, clients):
        """
        The API for updating sushi credentials is accessed by a normal user and thus permission
        denied is returned
        """
        credentials = CredentialsFactory(
            organization=organizations["branch"],
            platform=platforms["branch"],
            counter_version=5,
            lock_level=UL_ORG_ADMIN,
            url="http://a.b.c/",
        )
        url = reverse("sushi-credentials-detail", args=(credentials.pk,))
        new_url = "http://x.y.com/"
        resp = clients["user1"].patch(url, {"url": new_url})
        assert resp.status_code == 404

    def test_edit_action_locked_higher(self, basic1, organizations, platforms, clients):
        """
        The object is locked with consortium staff level lock, so the organization admin cannot
        edit it
        """
        credentials = CredentialsFactory(
            organization=organizations["root"],
            platform=platforms["root"],
            counter_version=5,
            lock_level=UL_CONS_STAFF,
            url="http://a.b.c/",
        )
        url = reverse("sushi-credentials-detail", args=(credentials.pk,))
        new_url = "http://x.y.com/"
        resp = clients["admin1"].patch(url, {"url": new_url})
        assert resp.status_code == 403

    def test_edit_action_with_report_types(
        self, basic1, organizations, platforms, clients, counter_report_type_named
    ):
        """
        Test changing report types using the API update action works
        """
        credentials = CredentialsFactory(
            organization=organizations["root"],
            platform=platforms["root"],
            counter_version=5,
            lock_level=UL_ORG_ADMIN,
            url="http://a.b.c/",
        )
        url = reverse("sushi-credentials-detail", args=(credentials.pk,))
        new_rt1 = counter_report_type_named("new1")
        new_rt2 = counter_report_type_named("new2")
        resp = clients["admin1"].patch(url, {"counter_reports": [new_rt1.pk, new_rt2.pk]})
        assert resp.status_code == 200
        credentials.refresh_from_db()
        assert credentials.counter_reports.count() == 2
        assert {cr.pk for cr in credentials.counter_reports.all()} == {new_rt1.pk, new_rt2.pk}

    def test_destroy_locked_higher(self, basic1, organizations, platforms, clients):
        """
        The object is locked with consortium staff level lock, so the organization admin cannot
        remove it
        """
        credentials = CredentialsFactory(
            organization=organizations["root"],
            platform=platforms["root"],
            counter_version=5,
            lock_level=UL_CONS_STAFF,
            url="http://a.b.c/",
        )
        url = reverse("sushi-credentials-detail", args=(credentials.pk,))
        assert SushiCredentials.objects.count() == 1
        resp = clients["admin1"].delete(url)
        assert resp.status_code == 403
        assert SushiCredentials.objects.count() == 1

    def test_destroy_locked_lower(self, basic1, organizations, platforms, clients):
        """
        The object is locked with consortium staff level lock, so the organization admin cannot
        remove it
        """
        credentials = CredentialsFactory(
            organization=organizations["root"],
            platform=platforms["root"],
            counter_version=5,
            lock_level=UL_ORG_ADMIN,
            url="http://a.b.c/",
        )
        url = reverse("sushi-credentials-detail", args=(credentials.pk,))
        assert SushiCredentials.objects.count() == 1
        resp = clients["admin1"].delete(url)
        assert resp.status_code == 204
        assert SushiCredentials.objects.count() == 0

    def test_month_overview_no_month(self, basic1, clients):
        """
        Test the month-overview custom action - month attr should be given
        """
        url = reverse("sushi-credentials-month-overview")
        resp = clients["master_admin"].get(url)
        assert resp.status_code == 400, "Month URL param must be present"

    def test_month_overview(
        self, basic1, organizations, platforms, counter_report_type_named, clients
    ):
        """
        Test the month-overview custom action
        """
        credentials = CredentialsFactory(
            organization=organizations["empty"],
            platform=platforms["empty"],
            counter_version=5,
            lock_level=UL_ORG_ADMIN,
            url="http://a.b.c/",
        )
        new_rt1 = counter_report_type_named("new1")
        credentials.counter_reports.add(new_rt1)
        FetchIntentionFactory(
            credentials=credentials,
            start_date="2020-01-01",
            end_date="2020-01-31",
            counter_report=new_rt1,
            attempt=FetchAttemptFactory(
                credentials=credentials,
                start_date="2020-01-01",
                end_date="2020-01-31",
                credentials_version_hash=credentials.version_hash,
                counter_report=new_rt1,
                status=AttemptStatus.SUCCESS,
            ),
        )
        # intention without attempt
        FetchIntentionFactory(
            credentials=credentials,
            start_date="2020-01-01",
            end_date="2020-01-31",
            counter_report=new_rt1,
            attempt=None,
        )
        intention2 = FetchIntentionFactory(
            credentials=credentials,
            start_date="2020-01-01",
            end_date="2020-01-31",
            counter_report=new_rt1,
            attempt=FetchAttemptFactory(
                credentials=credentials,
                start_date="2020-01-01",
                end_date="2020-01-31",
                credentials_version_hash=credentials.version_hash,
                counter_report=new_rt1,
                status=AttemptStatus.SUCCESS,
            ),
        )
        url = reverse("sushi-credentials-month-overview")
        resp = clients["master_admin"].get(url, {"month": "2020-01"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1, "there should be one record for one set of credentials"
        rec = data[0]
        assert rec["credentials_id"] == credentials.pk
        assert rec["counter_report_id"] == new_rt1.pk
        assert rec["pk"] == intention2.pk, "the second (newer) attempt should be reported"
        # now disable the credentials and observe the result
        credentials.enabled = False
        credentials.save()
        resp = clients["master_admin"].get(url, {"month": "2020-01"})
        assert len(resp.json()) == 0
        # now add param that says disabled should be included
        resp = clients["master_admin"].get(url, {"month": "2020-01", "disabled": "true"})
        assert len(resp.json()) == 1

    def test_month_overview_long_attempts(
        self, basic1, organizations, platforms, counter_report_type_named, clients
    ):
        """
        Test the month-overview custom action in presence of sushi fetch attempts that span
        more than one month
        """
        credentials = CredentialsFactory(
            organization=organizations["empty"],
            platform=platforms["empty"],
            counter_version=5,
            lock_level=UL_ORG_ADMIN,
            url="http://a.b.c/",
        )
        new_rt1 = counter_report_type_named("new1")
        credentials.counter_reports.add(new_rt1)
        intention1 = FetchIntentionFactory(
            credentials=credentials,
            start_date="2020-01-01",
            end_date="2020-03-31",
            counter_report=new_rt1,
            attempt=FetchAttemptFactory(
                credentials=credentials,
                start_date="2020-01-01",
                end_date="2020-03-31",
                credentials_version_hash=credentials.version_hash,
                counter_report=new_rt1,
                status=AttemptStatus.SUCCESS,
            ),
        )
        intention2 = FetchIntentionFactory(
            credentials=credentials,
            start_date="2020-01-01",
            end_date="2020-01-31",
            counter_report=new_rt1,
            attempt=FetchAttemptFactory(
                credentials=credentials,
                start_date="2020-01-01",
                end_date="2020-01-31",
                credentials_version_hash=credentials.version_hash,
                counter_report=new_rt1,
                status=AttemptStatus.SUCCESS,
            ),
        )
        url = reverse("sushi-credentials-month-overview")
        # 2020-01 - there are two attempts for this month
        resp = clients["master_admin"].get(url, {"month": "2020-01"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1, "there should be one record for this period"
        rec = data[0]
        assert rec["pk"] == intention2.pk, "the second (newer) attempt should be reported"
        # 2020-02 - there is one attempt for this month
        resp = clients["master_admin"].get(url, {"month": "2020-02"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1, "there should be one record for this period"
        rec = data[0]
        assert rec["pk"] == intention1.pk, "the attempt spanning to this month should be reported"
        # 2020-03 - there is one attempt for this month
        resp = clients["master_admin"].get(url, {"month": "2020-03"})
        assert resp.status_code == 200
        assert len(resp.json()) == 1, "there should be one record for this period"
        # 2020-04 - no attempt for this month
        resp = clients["master_admin"].get(url, {"month": "2020-04"})
        assert resp.status_code == 200
        assert len(resp.json()) == 0, "there should be no record for this period"

    def test_unset_broken(self, credentials, clients, counter_report_types):
        attempt_tr = FetchAttemptFactory(
            credentials=credentials["standalone_tr"], counter_report=counter_report_types["tr"]
        )
        credentials["standalone_tr"].broken = BS.BROKEN_HTTP
        credentials["standalone_tr"].first_broken_attempt = attempt_tr
        credentials["standalone_tr"].save()
        cr2c_tr = CounterReportsToCredentials.objects.get(
            credentials=credentials["standalone_tr"], counter_report__code="TR"
        )
        cr2c_tr.broken = BS.BROKEN_SUSHI
        cr2c_tr.first_broken_attempt = attempt_tr
        cr2c_tr.save()

        # unset entire credentials (both reports and mappings are unset)
        url = reverse("sushi-credentials-unset-broken")
        resp = clients["master_admin"].post(
            url, [{"credentials_id": credentials["standalone_tr"].pk}], format="json"
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        credentials["standalone_tr"].refresh_from_db()
        assert credentials["standalone_tr"].broken is None
        assert credentials["standalone_tr"].first_broken_attempt is None
        cr2c_tr.refresh_from_db()
        assert cr2c_tr.broken is None
        assert cr2c_tr.first_broken_attempt is None

        # Broken credentials mapping (only selected mappings are unset
        attempt_jr1 = FetchAttemptFactory(
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["jr1"],
        )
        attempt_br1 = FetchAttemptFactory(
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["jr1"],
        )
        credentials["standalone_br1_jr1"].broken = BS.BROKEN_SUSHI
        credentials["standalone_br1_jr1"].first_broken_attempt = attempt_br1
        credentials["standalone_br1_jr1"].save()
        cr2c_br1 = CounterReportsToCredentials.objects.get(
            credentials=credentials["standalone_br1_jr1"], counter_report__code="BR1"
        )
        cr2c_br1.broken = BS.BROKEN_SUSHI
        cr2c_br1.first_broken_attempt = attempt_br1
        cr2c_br1.save()
        cr2c_jr1 = CounterReportsToCredentials.objects.get(
            credentials=credentials["standalone_br1_jr1"], counter_report__code="JR1"
        )
        cr2c_jr1.broken = BS.BROKEN_SUSHI
        cr2c_jr1.first_broken_attempt = attempt_jr1
        cr2c_jr1.save()
        url = reverse("sushi-credentials-unset-broken")
        resp = clients["master_admin"].post(
            url,
            [{"credentials_id": credentials["standalone_br1_jr1"].pk, "counter_reports": ["JR1"]}],
            format="json",
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        credentials["standalone_br1_jr1"].refresh_from_db()
        assert credentials["standalone_br1_jr1"].broken == BS.BROKEN_SUSHI
        assert credentials["standalone_br1_jr1"].first_broken_attempt == attempt_br1
        cr2c_br1.refresh_from_db()
        assert cr2c_br1.broken == BS.BROKEN_SUSHI
        assert cr2c_br1.first_broken_attempt == attempt_br1
        cr2c_jr1.refresh_from_db()
        assert cr2c_jr1.broken is None
        assert cr2c_jr1.first_broken_attempt is None

        # Wrong type
        resp = clients["master_admin"].post(
            url,
            [
                {
                    "counter_reports": ["WRONG_TYPE"],
                    "credentials_id": credentials["standalone_br1_jr1"].pk,
                }
            ],
            format="json",
        )
        assert resp.status_code == 400

        # Non not assigned report type
        resp = clients["master_admin"].post(
            url,
            [
                {
                    "counter_reports": ["BR1", "DB1"],
                    "credentials_id": credentials["standalone_br1_jr1"].pk,
                }
            ],
            format="json",
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        cr2c_br1.refresh_from_db()
        assert cr2c_br1.broken is None
        assert cr2c_br1.first_broken_attempt is None

        # Credentials not found
        url = reverse("sushi-credentials-unset-broken")
        resp = clients["master_admin"].post(
            url, [{"credentials_id": 99999999, "counter_reports": ["JR1"]}], format="json"
        )
        assert resp.status_code == 200, "no credentials were updated"
        assert len(resp.json()) == 0

    def test_credential_details(self, basic1, credentials, clients, counter_report_types):
        # setup
        credentials["standalone_br1_jr1"].counterreportstocredentials_set.filter(
            counter_report=counter_report_types["jr1"]
        ).update(last_harvestable_month=date(2019, 1, 1))
        attempt_br1 = FetchAttemptFactory(
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["br1"],
        )
        cr2c_br1 = CounterReportsToCredentials.objects.get(
            credentials=credentials["standalone_br1_jr1"], counter_report__code="BR1"
        )
        cr2c_br1.broken = BS.BROKEN_SUSHI
        cr2c_br1.first_broken_attempt = attempt_br1
        cr2c_br1.save()

        url = reverse("sushi-credentials-detail", args=(credentials["standalone_br1_jr1"].pk,))
        resp = clients["master_admin"].get(url)
        assert resp.status_code == 200

        data = resp.json()
        assert data["broken"] is None
        for rec in data["counter_reports_long"]:
            if rec["code"] != "BR1":
                assert rec["broken"] is None
                assert rec["last_harvestable_month"] == "2019-01-01"
            else:
                assert rec["broken"] == BS.BROKEN_SUSHI
                assert rec["last_harvestable_month"] is None

    def test_count_api(self, basic1, credentials, clients, counter_report_types):
        """
        Test that the /count/ special api endpoint works
        """
        attempt_br1 = FetchAttemptFactory(
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["br1"],
        )
        cr2c_br1 = CounterReportsToCredentials.objects.get(
            credentials=credentials["standalone_br1_jr1"], counter_report__code="BR1"
        )
        cr2c_br1.broken = BS.BROKEN_SUSHI
        cr2c_br1.first_broken_attempt = attempt_br1
        cr2c_br1.save()
        credentials["standalone_tr"].broken = BS.BROKEN_HTTP
        credentials["standalone_tr"].save()

        resp = clients["master_admin"].get(reverse("sushi-credentials-count"))
        assert resp.status_code == 200
        assert resp.json() == {"count": 3, "broken": 1, "broken_reports": 1}

    @freeze_time("2020-06-01")
    def test_data(self, basic1, credentials, clients, harvests, counter_report_types):
        # mark credentials
        attempt_tr = FetchAttemptFactory(
            credentials=credentials["standalone_tr"],
            counter_report=counter_report_types["tr"],
            start_date=date(2020, 1, 1),
            status=AttemptStatus.DOWNLOAD_FAILED,
        )
        credentials["standalone_tr"].set_broken(attempt_tr, BS.BROKEN_HTTP)

        # mark broken mapping
        attempt_br1 = FetchAttemptFactory(
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["jr1"],
            start_date=date(2020, 1, 1),
            status=AttemptStatus.DOWNLOAD_FAILED,
        )
        cr2c_br1 = CounterReportsToCredentials.objects.get(
            credentials=credentials["standalone_br1_jr1"], counter_report__code="BR1"
        )
        cr2c_br1.set_broken(attempt_br1, BS.BROKEN_SUSHI)

        # partial download in a queue
        intention_pr = FetchIntentionFactory(
            credentials=credentials["branch_pr"],
            counter_report=counter_report_types["pr"],
            start_date=date(2020, 6, 1),
            attempt__status=AttemptStatus.SUCCESS,
            attempt__partial_data=True,
            attempt__import_batch=None,
            when_processed=timezone.now(),
        )
        FetchIntentionFactory(
            credentials=credentials["branch_pr"],
            counter_report=counter_report_types["pr"],
            start_date=date(2020, 6, 1),
            attempt__status=AttemptStatus.SUCCESS,
            attempt__partial_data=False,
            when_processed=timezone.now(),
            queue=intention_pr.queue,
            attempt__import_batch=ImportBatchFullFactory(
                organization=credentials["branch_pr"].organization,
                platform=credentials["branch_pr"].platform,
                report_type=counter_report_types["pr"].report_type,
                date=date(2020, 6, 1),
            ),
        )

        # Make sure that automatic harvesting is planned
        Automatic.update_for_last_month()

        # Just test premade scenarios
        resp = clients["master_admin"].get(
            reverse("sushi-credentials-data", args=(credentials["standalone_tr"].pk,))
        )
        assert resp.status_code == 200
        data = resp.json()

        assert len(data) == 2
        assert data[0]["year"] == timezone.now().year - 1
        for i in range(1, 13):
            month = f"{i:02d}"
            assert data[0][month][0]["status"] == "untried"
            assert data[0][month][0]["can_harvest"] is True

        assert data[1]["year"] == timezone.now().year
        for i in range(1, 13):
            month = f"{i:02d}"
            assert len(data[1][month]) == 1
            assert data[1][month][0]["planned"] is False
            assert data[1][month][0]["broken"] is False, "mapping not broken, but creds are"
            if month in ["01"]:
                assert data[1][month][0]["status"] == "failed"
                assert data[0][month][0]["can_harvest"] is True
            else:
                assert data[1][month][0]["status"] == "untried"
                assert data[0][month][0]["can_harvest"] is True

        resp = clients["master_admin"].get(
            reverse("sushi-credentials-data", args=(credentials["standalone_br1_jr1"].pk,))
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["year"] == timezone.now().year - 1
        for i in range(1, 13):
            month = f"{i:02d}"
            assert data[0][month][0]["status"] == "untried"
            assert data[0][month][0]["can_harvest"] is False

        assert data[1]["year"] == timezone.now().year
        for i in range(1, 13):
            month = f"{i:02d}"
            assert len(data[1][month]) == 2
            assert data[1][month][0]["broken"] is True, "mapping broken"
            assert data[1][month][1]["broken"] is False
            assert data[1][month][0]["can_harvest"] is False
            assert data[1][month][1]["can_harvest"] is True
            if month in ["01"]:
                assert data[1][month][1]["status"] == "failed"
                assert data[1][month][0]["status"] == "no_data"
                assert data[1][month][1]["planned"] is True
                assert data[1][month][0]["planned"] is True
                assert data[1][month][1]["can_harvest"] is True
                assert data[1][month][0]["can_harvest"] is False
            elif month in ["05"]:
                assert data[1][month][1]["status"] == "untried"
                assert data[1][month][0]["status"] == "untried"
                assert data[1][month][1]["planned"] is True
                assert data[1][month][0]["planned"] is False
                assert data[1][month][1]["can_harvest"] is True
                assert data[1][month][0]["can_harvest"] is False
            else:
                assert data[1][month][1]["status"] == "untried"
                assert data[1][month][0]["status"] == "untried"
                assert data[1][month][1]["planned"] is False
                assert data[1][month][0]["planned"] is False
                assert data[1][month][1]["can_harvest"] is True
                assert data[1][month][0]["can_harvest"] is False

        resp = clients["master_admin"].get(
            reverse("sushi-credentials-data", args=(credentials["branch_pr"].pk,))
        )
        assert resp.status_code == 200
        data = resp.json()

        assert len(data) == 2
        assert data[0]["year"] == timezone.now().year - 1
        for i in range(1, 13):
            month = f"{i:02d}"
            assert data[0][month][0]["status"] == "untried"
            assert data[0][month][0]["can_harvest"] is True

        assert data[1]["year"] == timezone.now().year
        for i in range(1, 13):
            month = f"{i:02d}"
            assert len(data[1][month]) == 1
            assert data[1][month][0]["broken"] is False
            if month in ["01"]:
                assert data[1][month][0]["status"] == "success"
                assert data[1][month][0]["planned"] is False
                assert data[1][month][0]["can_harvest"] is True
            elif month in ["03"]:
                assert data[1][month][0]["status"] == "untried"
                assert data[1][month][0]["planned"] is True
                assert data[1][month][0]["can_harvest"] is True
            elif month in ["05"]:
                assert data[1][month][0]["status"] == "untried"
                assert data[1][month][0]["planned"] is True, "planned via automatic harvesting"
                assert data[1][month][0]["can_harvest"] is True
            elif month in ["06"]:
                assert data[1][month][0]["status"] == "success"
                assert data[1][month][0]["planned"] is False
                assert data[1][month][0]["can_harvest"] is False
            else:
                assert data[1][month][0]["status"] == "untried"
                assert data[1][month][0]["planned"] is False
                assert data[1][month][0]["can_harvest"] is True

    def test_update_assigned_counter_reports(
        self, basic1, credentials, users, clients, counter_report_types
    ):
        # Empty
        resp = clients["admin2"].post(
            reverse("sushi-credentials-update-assigned-counter-reports"), [], format="json"
        )
        assert resp.status_code == 200
        assert resp.json() == {"updated": 0, "unmatched": 0, "matched": 0}
        cr2c_tr = CounterReportsToCredentials.objects.get(
            credentials=credentials["standalone_tr"], counter_report=counter_report_types["tr"]
        )

        cr2c_pr = CounterReportsToCredentials.objects.get(
            credentials=credentials["branch_pr"], counter_report=counter_report_types["pr"]
        )

        # Permission denied for single record
        resp = clients["admin2"].post(
            reverse("sushi-credentials-update-assigned-counter-reports"),
            [
                {
                    "counter_report_id": counter_report_types["tr"].pk,
                    "credentials_id": credentials["standalone_tr"].pk,
                    "last_harvestable_month": "2021-01-01",
                },
                {
                    "counter_report_id": counter_report_types["pr"].pk,
                    "credentials_id": credentials["branch_pr"].pk,
                    "last_harvestable_month": None,
                },
                {
                    "counter_report_id": counter_report_types["pr"].pk,
                    "credentials_id": credentials["standalone_tr"].pk,
                    "last_harvestable_month": "2020-01-01",
                },
            ],
            format="json",
        )
        assert resp.status_code == 403
        cr2c_tr.refresh_from_db()
        assert cr2c_tr.last_harvestable_month is None
        assert cr2c_tr.last_harvestable_month_user is None
        cr2c_pr.refresh_from_db()
        assert cr2c_pr.last_harvestable_month is None
        assert cr2c_pr.last_harvestable_month_user is None

        resp = clients["admin2"].post(
            reverse("sushi-credentials-update-assigned-counter-reports"),
            [
                {
                    "counter_report_id": counter_report_types["tr"].pk,
                    "credentials_id": credentials["standalone_tr"].pk,
                    "last_harvestable_month": "2021-01-01",
                },
                {
                    # this combination of credentials and counter report does not exist
                    "counter_report_id": counter_report_types["pr"].pk,
                    "credentials_id": credentials["standalone_tr"].pk,
                    "last_harvestable_month": "2020-01-01",
                },
            ],
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json() == {"updated": 1, "unmatched": 1, "matched": 1}
        cr2c_tr.refresh_from_db()
        assert cr2c_tr.last_harvestable_month == date(2021, 1, 1)
        assert cr2c_tr.last_harvestable_month_user == users["admin2"]

        test_data = [
            {
                # removes a previously assigned value
                "counter_report_id": counter_report_types["tr"].pk,
                "credentials_id": credentials["standalone_tr"].pk,
                "last_harvestable_month": None,
            },
            {
                # updates a previously assigned value
                "counter_report_id": counter_report_types["pr"].pk,
                "credentials_id": credentials["branch_pr"].pk,
                "last_harvestable_month": "2022-01-01",
            },
            {
                # this combination of credentials and counter report does not exist
                "counter_report_id": counter_report_types["pr"].pk,
                "credentials_id": credentials["standalone_tr"].pk,
                "last_harvestable_month": "2020-01-01",
            },
        ]
        resp = clients["master_admin"].post(
            reverse("sushi-credentials-update-assigned-counter-reports"), test_data, format="json"
        )
        assert resp.status_code == 200
        assert resp.json() == {"updated": 2, "unmatched": 1, "matched": 2}
        cr2c_tr.refresh_from_db()
        assert cr2c_tr.last_harvestable_month is None
        assert cr2c_tr.last_harvestable_month_user == users["master_admin"]
        cr2c_pr.refresh_from_db()
        assert cr2c_pr.last_harvestable_month == date(2022, 1, 1)
        assert cr2c_pr.last_harvestable_month_user == users["master_admin"]

        # retry with the same data - no record should be updated
        resp = clients["master_admin"].post(
            reverse("sushi-credentials-update-assigned-counter-reports"), test_data, format="json"
        )
        assert resp.status_code == 200
        assert resp.json() == {"updated": 0, "unmatched": 1, "matched": 2}

    @pytest.mark.parametrize(
        "consortial,in_org,forced,passed",
        (
            (True, True, True, True),
            (False, True, True, True),
            (True, False, True, True),
            (True, True, False, False),
            (True, False, False, False),
            (False, True, False, False),
            (False, False, True, True),
            (False, False, False, True),
        ),
    )
    def test_create_with_same_hash(
        self,
        basic1,
        organizations,
        platforms,
        clients,
        users,
        counter_report_types,
        settings,
        consortial,
        in_org,
        forced,
        passed,
    ):
        """
        Test creating credentials with the same hash => downloaded data should
        be the same as data from other credentials, which might not be desirable.

        From the user point of view he should be able to store these credentials
        anyways after supressing some warning `forced=True`.

        Also we want to supress the warning in non-consortial installs,
        when the credentails are stored in different organizations
        `consortial=True`

        `in_org=True` says that the credentials with the same hash
        will be stored within the same organization.
        """
        settings.CONSORTIAL_INSTALLATION = consortial
        same_params = {
            "url": "https://example.com/",
            "customer_id": "C1",
            "requestor_id": "R1",
            "api_key": "A",
            "counter_version": 5,
            "http_username": "",
            "http_password": "",
            "extra_params": {},
        }
        if in_org:
            CredentialsFactory(organization=organizations["root"], **same_params)
        else:
            CredentialsFactory(organization=organizations["standalone"], **same_params)
        url = reverse("sushi-credentials-list")
        data = {
            "title": "Foo bar credentials",
            "platform_id": platforms["brain"].pk,
            "organization_id": organizations["root"].pk,
            "counter_reports": [counter_report_types["tr"].pk],
            **same_params,
        }
        if forced:
            data["forced"] = True
        assert SushiCredentials.objects.count() == 1
        resp = clients["master_admin"].post(url, data, format="json")
        if passed:
            assert resp.status_code == 201
            assert SushiCredentials.objects.count() == 2
        else:
            assert resp.status_code == 400
            error_code = "same-exists-within-org" if in_org else "same-exists-globally"
            assert resp.data[0].code == error_code
            assert SushiCredentials.objects.count() == 1

    @pytest.mark.parametrize(
        "consortial,in_org,forced,passed",
        (
            (True, True, True, True),
            (False, True, True, True),
            (True, False, True, True),
            (True, True, False, False),
            (True, False, False, False),
            (False, True, False, False),
            (False, False, True, True),
            (False, False, False, True),
        ),
    )
    def test_update_with_same_hash(
        self,
        basic1,
        organizations,
        platforms,
        clients,
        users,
        counter_report_types,
        settings,
        consortial,
        in_org,
        forced,
        passed,
    ):
        """
        Test updating credentials with the same hash => downloaded data should
        be the same as data from other credentials, which might not be desirable.

        From the user point of view he should be able to store these credentials
        anyways after supressing some warning `forced=True`.

        Also we want to supress the warning in non-consortial installs,
        when the credentails are stored in different organizations
        `consortial=True`

        `in_org=True` says that the credentials with the same hash
        will be stored within the same organization.
        """
        settings.CONSORTIAL_INSTALLATION = consortial
        same_params = {
            "url": "https://example.com/",
            "customer_id": "C1",
            "requestor_id": "R1",
            "api_key": "A",
            "counter_version": 5,
            "http_username": "",
            "http_password": "",
            "extra_params": {},
        }
        cred = CredentialsFactory(platform=platforms["brain"], organization=organizations["root"])
        if in_org:
            CredentialsFactory(
                platform=platforms["shared"], organization=organizations["root"], **same_params
            )
        else:
            CredentialsFactory(
                platform=platforms["shared"], organization=organizations["branch"], **same_params
            )
        url = reverse("sushi-credentials-detail", args=(cred.pk,))
        data = {
            "title": "Foo bar credentials",
            "platform_id": platforms["brain"].pk,
            "organization_id": organizations["root"].pk,
            "counter_reports": [counter_report_types["tr"].pk],
            **same_params,
        }
        if forced:
            data["forced"] = True
        resp = clients["master_admin"].patch(url, data, format="json")
        if passed:
            assert resp.status_code == 200
        else:
            assert resp.status_code == 400
            error_code = "same-exists-within-org" if in_org else "same-exists-globally"
            assert resp.data[0].code == error_code
