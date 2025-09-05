import pytest
from core.logic.serialization import b64json
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from organizations.models import UserOrganization
from organizations.tests.conftest import organizations  # noqa
from tags.fake_data import TagForTitleFactory

from logs.models import FlexibleReport, FlexibleReportUserEmail
from test_scenarios.basic import users  # noqa


@pytest.mark.django_db
class TestFlexibleReportAPI:
    def test_list_simple(self, admin_client):
        url = reverse("flexible-report-list")
        resp = admin_client.get(url)
        assert resp.status_code == 200

    @pytest.mark.parametrize(
        ["user", "accessible_reports"],
        [
            ["user1", {"public", "user1 report"}],
            ["user2", {"public", "user2 report"}],
            ["admin1", {"public", "org1 report"}],
            ["admin2", {"public", "org2 report"}],
            ["empty", {"public", "org1 report", "org2 report"}],
            ["master_admin", {"public"}],
            ["master_user", {"public"}],
            ["su", {"public", "org1 report", "org2 report"}],  # cannot see private
        ],
    )
    def test_list_access(self, client, users, organizations, user, accessible_reports):
        organization1 = organizations[0]
        organization2 = organizations[1]
        FlexibleReport.objects.create(name="public")
        FlexibleReport.objects.create(name="user1 report", owner=users["user1"])
        FlexibleReport.objects.create(name="user2 report", owner=users["user2"])
        FlexibleReport.objects.create(name="org1 report", owner_organization=organization1)
        FlexibleReport.objects.create(name="org2 report", owner_organization=organization2)
        UserOrganization.objects.create(user=users["admin1"], organization=organization1)
        UserOrganization.objects.create(user=users["admin2"], organization=organization2)
        UserOrganization.objects.create(user=users["empty"], organization=organization1)
        UserOrganization.objects.create(user=users["empty"], organization=organization2)

        url = reverse("flexible-report-list")
        client.force_login(users[user])
        resp = client.get(url)
        assert resp.status_code == 200
        assert accessible_reports == {rec["name"] for rec in resp.json()}

    @pytest.mark.parametrize(
        ["access_level", "user_to_count"],
        [
            [
                "consortium",
                {
                    "user1": 1,  # himself
                    "user2": 1,  # himself
                    "admin1": 1,  # himself
                    "admin2": 1,  # himself
                    "master_admin": 6,  # himself + 4 normal users + master_user
                    "master_user": 1,  # himself
                    "su": 6,  # himself + 4 normal users + master_user
                },
            ],
            [
                "organization",
                {
                    "user1": 1,  # himself
                    "user2": 0,  # cannot see
                    "admin1": 2,  # himself + user1
                    "admin2": 0,  # cannot see
                    "master_admin": 3,  # himself + 2 normal users
                    "master_user": 1,  # himself
                    "su": 3,  # himself + 2 normal users
                },
            ],
            [
                "user",
                {
                    "user1": 0,  # cannot see
                    "user2": 0,  # cannot see
                    "admin1": 1,  # himself
                    "admin2": 0,  # cannot see
                    "master_admin": 0,  # cannot see
                    "master_user": 0,  # cannot see
                    "su": 0,  # cannot see
                },
            ],
        ],
    )
    def test_mailing_count(
        self, client, organizations, users, access_level, user_to_count, settings
    ):
        """
        Test that the mailing count is correctly set and reflects who is looking.
        """
        org_master, org_normal, org_normal2 = organizations
        settings.MASTER_ORGANIZATIONS = [org_master.internal_id]

        # link users and organizations - we do not user `basic1` because some of the fixtures
        # conflict with the ones used by `basic1`
        users["master_admin"].organizations.add(org_master, through_defaults={"is_admin": True})
        users["master_user"].organizations.add(org_master, through_defaults={"is_admin": False})
        users["admin1"].organizations.add(org_normal, through_defaults={"is_admin": True})
        users["admin2"].organizations.add(org_normal2, through_defaults={"is_admin": True})
        users["user1"].organizations.add(org_normal, through_defaults={"is_admin": False})
        users["user2"].organizations.add(org_normal2, through_defaults={"is_admin": False})

        # set up the report
        owner = users["admin1"] if access_level == "user" else None
        owner_organization = org_normal if access_level == "organization" else None
        report = FlexibleReport.objects.create(owner=owner, owner_organization=owner_organization)
        # create mailing for all users
        for user, count in user_to_count.items():
            if count == 0:
                with pytest.raises(PermissionDenied):
                    # the user cannot see the report, thus cannot create a mailing
                    FlexibleReportUserEmail.objects.create(flexible_report=report, user=users[user])
            else:
                FlexibleReportUserEmail.objects.create(flexible_report=report, user=users[user])
        # check that the mailing count is correct for the detail view
        url = reverse("flexible-report-detail", args=[report.pk])
        for user, count in user_to_count.items():
            client.force_login(users[user])
            resp = client.get(url)
            if count == 0:
                assert resp.status_code == 404
            else:
                assert resp.status_code == 200
                assert resp.json()["mailing_count"] == count, (
                    f"user {user} should see {count} mailing"
                )
        # check that the mailing count is correct for the list view
        url = reverse("flexible-report-list")
        for user, count in user_to_count.items():
            client.force_login(users[user])
            resp = client.get(url)
            if count == 0:
                assert len(resp.json()) == 0
            else:
                assert len(resp.json()) == 1
                assert resp.json()[0]["mailing_count"] == count, (
                    f"user {user} should see {count} mailing"
                )

    @pytest.mark.parametrize(
        "prim_dim_spec",
        [{"primary_dimension": "platform"}, {"primary_dimensions": b64json(["platform"])}],
    )
    def test_create(self, admin_client, admin_user, prim_dim_spec):
        """
        Test creating a report with different primary dimension specifications
        (one is older with primary_dimension, the other with primary_dimensions is newer for
        multiindex support)
        """
        resp = admin_client.post(
            reverse("flexible-report-list"),
            {
                "name": "test report",
                "description": "description",
                "config": {"groups": b64json(["metric"]), **prim_dim_spec},
            },
            content_type="application/json",
        )
        assert resp.status_code == 201
        report = FlexibleReport.objects.get(pk=resp.json()["pk"])
        assert report.owner == admin_user
        assert report.owner_organization is None
        assert report.last_updated_by == admin_user
        assert report.report_config["primary_dimensions"] == ["platform"], "regardless of the spec"
        assert report.report_config["group_by"] == ["metric"]
        assert report.description == "description"

    def test_create_with_tag_roll_up(self, admin_client, admin_user):
        resp = admin_client.post(
            reverse("flexible-report-list"),
            {
                "name": "test report",
                "config": {
                    "primary_dimensions": b64json(["platform"]),
                    "groups": b64json(["metric"]),
                    "tag_roll_up": "true",
                    "tag_class": 1,
                },
            },
            content_type="application/json",
        )
        assert resp.status_code == 201
        report = FlexibleReport.objects.get(pk=resp.json()["pk"])
        assert report.owner == admin_user
        assert report.owner_organization is None
        assert report.last_updated_by == admin_user
        assert report.report_config["primary_dimensions"] == ["platform"]
        assert report.report_config["group_by"] == ["metric"]
        assert report.report_config["tag_roll_up"] is True
        assert report.report_config["tag_class"] == 1

    def test_create_with_tag_filter(self, admin_client, admin_user):
        tag = TagForTitleFactory.create()
        resp = admin_client.post(
            reverse("flexible-report-list"),
            {
                "name": "test report",
                "config": {
                    "primary_dimensions": b64json(["target"]),
                    "groups": b64json(["metric"]),
                    "filters": b64json({"tag__target": [tag.pk]}),
                },
            },
            content_type="application/json",
        )
        assert resp.status_code == 201
        report = FlexibleReport.objects.get(pk=resp.json()["pk"])
        assert report.owner == admin_user
        assert report.owner_organization is None
        assert report.last_updated_by == admin_user
        assert report.report_config["primary_dimensions"] == ["target"]
        assert report.report_config["group_by"] == ["metric"]
        assert report.report_config["filters"][0]["dimension"] == "target"
        assert report.report_config["filters"][0]["tag_ids"] == [tag.pk]

    def test_create_in_trend_mode(self, admin_client, admin_user):
        resp = admin_client.post(
            reverse("flexible-report-list"),
            {
                "name": "test report",
                "config": {
                    "primary_dimension": "platform",
                    "trend_mode": True,
                    "base_subset_filters": b64json(
                        {"date": {"start": "2019-01", "end": "2019-02"}}
                    ),
                    "compared_subset_filters": b64json(
                        {"date": {"start": "2019-03", "end": "2019-04"}}
                    ),
                },
            },
            content_type="application/json",
        )
        assert resp.status_code == 201
        report = FlexibleReport.objects.get(pk=resp.json()["pk"])
        assert report.owner == admin_user
        assert report.owner_organization is None
        assert report.last_updated_by == admin_user
        assert report.report_config["primary_dimensions"] == ["platform"]
        assert report.report_config["trend_mode"] is True
        assert report.report_config["base_subset_filters"][0]["dimension"] == "date"
        assert report.report_config["base_subset_filters"][0]["start"] == "2019-01-01"
        assert report.report_config["base_subset_filters"][0]["end"] == "2019-02-28"
        assert report.report_config["compared_subset_filters"][0]["dimension"] == "date"
        assert report.report_config["compared_subset_filters"][0]["start"] == "2019-03-01"
        assert report.report_config["compared_subset_filters"][0]["end"] == "2019-04-30"

    @pytest.fixture()
    def user_organizations(self, users, organizations):
        org1 = organizations[0]
        org2 = organizations[1]
        UserOrganization.objects.create(user=users["user1"], organization=org1)
        UserOrganization.objects.create(user=users["user2"], organization=org2)
        UserOrganization.objects.create(user=users["admin1"], organization=org1, is_admin=True)
        UserOrganization.objects.create(user=users["admin2"], organization=org2, is_admin=True)
        UserOrganization.objects.create(
            user=users["master_admin"], organization=org1, is_admin=True
        )
        UserOrganization.objects.create(
            user=users["master_admin"], organization=org2, is_admin=True
        )

    @pytest.mark.parametrize(
        ["user", "can_private", "can_org1", "can_org2", "can_consortium"],
        [
            #         private, org1, org2, consortium
            ["user1", True, False, False, False],  # normal user, connected to org1
            ["user2", True, False, False, False],  # normal user, connected to org2
            ["admin1", True, True, False, False],  # admin of org1
            ["admin2", True, False, True, False],  # admin of org2
            ["master_admin", True, True, True, False],  # admin of org1 and org2
            ["master_user", True, False, False, False],  # only private
            ["su", True, True, True, True],  # superuser
        ],
    )
    def test_create_accesslevel(
        self,
        client,
        users,
        organizations,
        user_organizations,
        user,
        can_private,
        can_org1,
        can_org2,
        can_consortium,
    ):
        """
        Test that when saving a report the user can/cannot set a specific accesslevel
        and also for specific organization when setting organization level access
        """
        org1 = organizations[0]
        org2 = organizations[1]
        data_base = {
            "name": "test report",
            "config": {"primary_dimension": "platform", "groups": b64json(["metric"])},
        }
        url = reverse("flexible-report-list")
        client.force_login(users[user])

        # private
        resp = client.post(url, data_base, content_type="application/json")
        assert resp.status_code == (201 if can_private else 403)
        assert resp.json()["owner"] == users[user].pk
        assert resp.json()["owner_organization"] is None

        # org1
        resp = client.post(
            url,
            {**data_base, "owner_organization": org1.pk, "owner": None},
            content_type="application/json",
        )
        assert resp.status_code == (201 if can_org1 else 403)
        if can_org1:
            assert resp.json()["owner"] is None
            assert resp.json()["owner_organization"] == org1.pk

        # org2
        resp = client.post(
            url,
            {**data_base, "owner_organization": org2.pk, "owner": None},
            content_type="application/json",
        )
        assert resp.status_code == (201 if can_org2 else 403)
        if can_org2:
            assert resp.json()["owner"] is None
            assert resp.json()["owner_organization"] == org2.pk

        # consortium
        resp = client.post(url, {**data_base, "owner": None}, content_type="application/json")
        assert resp.status_code == (201 if can_consortium else 403)
        if can_consortium:
            assert resp.json()["owner"] is None
            assert resp.json()["owner_organization"] is None

    @classmethod
    def access_to_code(cls, access, delete=False):
        if access is None:
            return 404
        elif access:
            return 204 if delete else 200
        return 403

    @pytest.fixture(params=["user1", "user2", "org1", "org2", "admin1", "admin2", "consortium"])
    def flexible_report(self, request, organizations, users):
        data = {"report_config": {"primary_dimension": "platform", "group_by": ["metric"]}}
        if request.param in ("user1", "user2", "admin1", "admin2"):
            # user owned
            data["owner"] = users[request.param]
        elif request.param == "org1":
            # organization owned
            data["owner_organization"] = organizations[0]
        elif request.param == "org2":
            # organization owned
            data["owner_organization"] = organizations[1]
        elif request.param == "consortium":
            # consortium owned
            data["owner"] = None
        return {
            "level": request.param,
            "report": FlexibleReport.objects.create(name=f"test {request.param}", **data),
        }

    @pytest.mark.parametrize(
        ["user", "can"],
        [
            #         change_spec, private, org1, org2, consortium (None => cannot see)
            [
                "user1",  # normal user, connected to org1
                {
                    "user1": (True, True, False, False, False),  # what he can do to report user1
                    "user2": (None, None, None, None, None),  # what he can do to report user2
                    "admin1": (None, None, None, None, None),  # what he can do to report admin1
                    "admin2": (None, None, None, None, None),  # what he can do to report admin2
                    "org1": (False, False, False, False, False),  # what he can do to report org1
                    "org2": (None, None, None, None, None),  # what he can do to report org2
                    "consortium": (False, False, False, False, False),  # what he can do to cons...
                },
            ],
            [
                "user2",  # normal user, connected to org2
                {
                    "user1": (None, None, None, None, None),  # what he can do to report user1
                    "user2": (True, True, False, False, False),  # what he can do to report user2
                    "admin1": (None, None, None, None, None),  # what he can do to report admin1
                    "admin2": (None, None, None, None, None),  # what he can do to report admin2
                    "org1": (None, None, None, None, None),  # what he can do to report org1
                    "org2": (False, False, False, False, False),  # what he can do to report org2
                    "consortium": (False, False, False, False, False),  # what he can do to cons...
                },
            ],
            [
                "admin1",  # admin of org1
                {
                    "user1": (None, None, None, None, None),  # what he can do to report user1
                    "user2": (None, None, None, None, None),  # what he can do to report user2
                    "admin1": (True, True, True, False, False),  # what he can do to report admin1
                    "admin2": (None, None, None, None, None),  # what he can do to report admin2
                    "org1": (True, True, True, False, False),  # what he can do to report org1
                    "org2": (None, None, None, None, None),  # what he can do to report org2
                    "consortium": (False, False, False, False, False),  # what he can do to cons...
                },
            ],
            [
                "admin2",  # admin of org2
                {
                    "user1": (None, None, None, None, None),  # what he can do to report user1
                    "user2": (None, None, None, None, None),  # what he can do to report user2
                    "admin1": (None, None, None, None, None),  # what he can do to report admin1
                    "admin2": (True, True, False, True, False),  # what he can do to report admin2
                    "org1": (None, None, None, None, None),  # what he can do to report org1
                    "org2": (True, True, False, True, False),  # what he can do to report org2
                    "consortium": (False, False, False, False, False),  # what he can do to cons...
                },
            ],
            [
                "master_admin",  # admin of org1 and org2
                {
                    "user1": (None, None, None, None, None),  # what he can do to report user1
                    "user2": (None, None, None, None, None),  # what he can do to report user2
                    "admin1": (None, None, None, None, None),  # what he can do to report admin1
                    "admin2": (None, None, None, None, None),  # what he can do to report admin2
                    "org1": (True, True, True, True, False),  # what he can do to report org1
                    "org2": (True, True, True, True, False),  # what he can do to report org2
                    "consortium": (False, False, False, False, False),  # what he can do to cons...
                },
            ],
            [
                "master_user",  # user of org1 and org2
                {
                    "user1": (None, None, None, None, None),  # what he can do to report user1
                    "user2": (None, None, None, None, None),  # what he can do to report user2
                    "admin1": (None, None, None, None, None),  # what he can do to report admin1
                    "admin2": (None, None, None, None, None),  # what he can do to report admin2
                    "org1": (None, None, None, None, None),  # what he can do to report org1
                    "org2": (None, None, None, None, None),  # what he can do to report org2
                    "consortium": (False, False, False, False, False),  # what he can do to cons...
                },
            ],
            [
                "su",  # superuser
                {
                    "user1": (None, None, None, None, None),  # what he can do to report user1
                    "user2": (None, None, None, None, None),  # what he can do to report user2
                    "admin1": (None, None, None, None, None),  # what he can do to report admin1
                    "admin2": (None, None, None, None, None),  # what he can do to report admin2
                    "org1": (True, True, True, True, True),  # what he can do to report org1
                    "org2": (True, True, True, True, True),  # what he can do to report org2
                    "consortium": (True, True, True, True, True),  # what he can do to cons...
                },
            ],
        ],
    )
    def test_update_accesslevel(
        self, client, users, organizations, user_organizations, user, flexible_report, can
    ):
        """
        Test that when updating a report with specific access level, the user can/cannot
        change the definition and/or access level.
        """
        org1 = organizations[0]
        org2 = organizations[1]
        fr = flexible_report["report"]
        url = reverse("flexible-report-detail", args=(fr.pk,))
        client.force_login(users[user])
        can_change_spec, can_private, can_org1, can_org2, can_consortium = can[
            flexible_report["level"]
        ]

        # change spec
        resp = client.patch(url, {"name": "foobar"}, content_type="application/json")
        assert resp.status_code == self.access_to_code(can_change_spec)
        if can_change_spec:
            assert resp.json()["owner"] == fr.owner_id
            assert resp.json()["owner_organization"] == fr.owner_organization_id

        # private
        resp = client.patch(
            url,
            {"owner": users[user].pk, "owner_organization": None},
            content_type="application/json",
        )
        assert resp.status_code == self.access_to_code(can_private)
        if can_private:
            assert resp.json()["owner"] == users[user].pk
            assert resp.json()["owner_organization"] is None

        # org1
        resp = client.patch(
            url, {"owner_organization": org1.pk, "owner": None}, content_type="application/json"
        )
        assert resp.status_code == self.access_to_code(can_org1)
        if can_org1:
            assert resp.json()["owner"] is None
            assert resp.json()["owner_organization"] == org1.pk

        # org2
        resp = client.patch(
            url, {"owner_organization": org2.pk, "owner": None}, content_type="application/json"
        )
        assert resp.status_code == self.access_to_code(can_org2)
        if can_org2:
            assert resp.json()["owner"] is None
            assert resp.json()["owner_organization"] == org2.pk

        # consortium
        resp = client.patch(
            url, {"owner_organization": None, "owner": None}, content_type="application/json"
        )
        assert resp.status_code == self.access_to_code(can_consortium)
        if can_consortium:
            assert resp.json()["owner"] is None
            assert resp.json()["owner_organization"] is None

    @pytest.mark.parametrize(
        ["user", "can"],
        [
            #         change_spec, private, org1, org2, consortium (None => cannot see)
            [
                "user1",  # normal user, connected to org1
                {
                    "user1": True,  # what he can do to report user1
                    "user2": None,  # what he can do to report user2
                    "admin1": None,  # what he can do to report admin1
                    "admin2": None,  # what he can do to report admin2
                    "org1": False,  # what he can do to report org1
                    "org2": None,  # what he can do to report org2
                    "consortium": False,  # what he can do to cons...
                },
            ],
            [
                "user2",  # normal user, connected to org2
                {
                    "user1": None,  # what he can do to report user1
                    "user2": True,  # what he can do to report user2
                    "admin1": None,  # what he can do to report admin1
                    "admin2": None,  # what he can do to report admin2
                    "org1": None,  # what he can do to report org1
                    "org2": False,  # what he can do to report org2
                    "consortium": False,  # what he can do to cons...
                },
            ],
            [
                "admin1",  # admin of org1
                {
                    "user1": None,  # what he can do to report user1
                    "user2": None,  # what he can do to report user2
                    "admin1": True,  # what he can do to report admin1
                    "admin2": None,  # what he can do to report admin2
                    "org1": True,  # what he can do to report org1
                    "org2": None,  # what he can do to report org2
                    "consortium": False,  # what he can do to cons...
                },
            ],
            [
                "admin2",  # admin of org2
                {
                    "user1": None,  # what he can do to report user1
                    "user2": None,  # what he can do to report user2
                    "admin1": None,  # what he can do to report admin1
                    "admin2": True,  # what he can do to report admin2
                    "org1": None,  # what he can do to report org1
                    "org2": True,  # what he can do to report org2
                    "consortium": False,  # what he can do to cons...
                },
            ],
            [
                "master_admin",  # admin of org1 and org2
                {
                    "user1": None,  # what he can do to report user1
                    "user2": None,  # what he can do to report user2
                    "admin1": None,  # what he can do to report admin1
                    "admin2": None,  # what he can do to report admin2
                    "org1": True,  # what he can do to report org1
                    "org2": True,  # what he can do to report org2
                    "consortium": False,  # what he can do to cons...
                },
            ],
            [
                "master_user",  # user of org1 and org2
                {
                    "user1": None,  # what he can do to report user1
                    "user2": None,  # what he can do to report user2
                    "admin1": None,  # what he can do to report admin1
                    "admin2": None,  # what he can do to report admin2
                    "org1": None,  # what he can do to report org1
                    "org2": None,  # what he can do to report org2
                    "consortium": False,  # what he can do to cons...
                },
            ],
            [
                "su",  # superuser
                {
                    "user1": None,  # what he can do to report user1
                    "user2": None,  # what he can do to report user2
                    "admin1": None,  # what he can do to report admin1
                    "admin2": None,  # what he can do to report admin2
                    "org1": True,  # what he can do to report org1
                    "org2": True,  # what he can do to report org2
                    "consortium": True,  # what he can do to cons...
                },
            ],
        ],
    )
    def test_delete_accesslevel(
        self, client, users, user_organizations, user, flexible_report, can
    ):
        """
        Test that when updating a report with specific access level, the user can/cannot
        change the definition and/or access level.
        """
        fr = flexible_report["report"]
        url = reverse("flexible-report-detail", args=(fr.pk,))
        client.force_login(users[user])
        can_delete = can[flexible_report["level"]]

        resp = client.delete(url)
        assert resp.status_code == self.access_to_code(can_delete, delete=True)
        if can_delete:
            assert FlexibleReport.objects.count() == 0
        else:
            assert FlexibleReport.objects.count() == 1
