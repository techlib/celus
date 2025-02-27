import json
from unittest.mock import patch
from urllib.parse import quote

import pytest
from core.fake_data import IdentityFactory
from core.models import Identity, User
from core.tests.conftest import (  # noqa - fixtures
    authenticated_client,  # noqa - fixtures
    authentication_headers,
    invalid_identity,
    valid_identity,
)
from django.urls import reverse
from logs.fake_data import ImportBatchFactory
from logs.models import AccessLog, Metric
from publications.tests.conftest import interest_rt  # noqa - fixture

from organizations.fake_data import OrganizationAltNameFactory
from organizations.models import Organization, UserOrganization
from test_scenarios.basic import (  # noqa - fixtures
    basic1,
    clients,
    data_sources,
    identities,
    make_client,
    organizations,
    platforms,
    users,
)


@pytest.mark.django_db
class TestOrganizationAPI:
    def test_unauthorized_user(self, client, invalid_identity, authentication_headers):
        resp = client.get(reverse("organization-list"), **authentication_headers(invalid_identity))
        assert resp.status_code in (403, 401)  # depends on auth backend

    def test_authorized_user_no_orgs(self, authenticated_client):
        resp = authenticated_client.get(reverse("organization-list"))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_authorized_user_no_authorization(self, authenticated_client, organizations):
        """
        User is authenticated but does not belong to any org - the list should be empty
        :param authenticated_client:
        :param organizations:
        :return:
        """
        resp = authenticated_client.get(reverse("organization-list"))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_authorized_user_part_authorization(
        self, authenticated_client, organizations, valid_identity
    ):
        """
        User is authenticated and belongs to a single organization
        """
        identity = Identity.objects.select_related("user").get(identity=valid_identity)
        UserOrganization.objects.create(
            user=identity.user, organization=organizations["standalone"]
        )
        resp = authenticated_client.get(reverse("organization-list"))
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["pk"] == organizations["standalone"].pk

    @pytest.mark.parametrize(
        ["settings_nibbler", "result"],
        (
            ("All", [True, True, True, True, True]),
            ("None", [False, False, False, False, False]),
            ("PerOrg", [False, False, False, False, True]),
        ),
    )
    def test_list_nibbler(self, clients, organizations, settings, settings_nibbler, result):
        """
        Check whether organization is allowed to use nibbler
        """
        settings.ENABLE_RAW_DATA_IMPORT = settings_nibbler
        organizations["standalone"].raw_data_import_enabled = True
        organizations["standalone"].save()
        a1 = OrganizationAltNameFactory(organization=organizations["standalone"], name="Alt1")
        a2 = OrganizationAltNameFactory(organization=organizations["standalone"], name="Alt2")
        resp = clients["su"].get(reverse("organization-list"))
        assert resp.status_code == 200
        data = sorted(resp.json(), key=lambda x: x["pk"])
        assert len(data) == 5
        assert [e["is_raw_data_import_enabled"] for e in data] == result
        assert data[4]["alt_names"] == [
            {"pk": a1.pk, "name": "Alt1"},
            {"pk": a2.pk, "name": "Alt2"},
        ]

    def test_authorized_user_no_authorization_detail(self, authenticated_client, organizations):
        """
        User is authenticated but does not belong to any org - the list should be empty
        :param authenticated_client:
        :param organizations:
        :return:
        """
        resp = authenticated_client.get(
            reverse("organization-detail", args=[organizations["standalone"].pk])
        )
        assert resp.status_code == 404

    def test_user_default_organization_creation(self, authenticated_client, settings):
        settings.ALLOW_USER_REGISTRATION = True
        url = reverse("organization-create-user-default")
        assert Organization.objects.count() == 0
        with patch("organizations.views.async_mail_customer_care_admins") as email_task:
            resp = authenticated_client.post(
                url, {"name": "test organization"}, content_type="application/json"
            )
            assert (
                email_task.delay.called
            ), "email about a default organization created by user was sent to admin"
        assert resp.status_code == 201
        assert Organization.objects.count() == 1
        org = Organization.objects.get()
        assert org.name == "test organization"
        # All language mutations are supposed to be set to the same name
        assert org.name_en == "test organization"
        assert org.name_cs == "test organization"
        assert org.internal_id == "test#test-organization"
        assert org in authenticated_client.user.organizations.all()
        assert (
            org.private_data_source == org.source
        ), "organization object data source should be the organizations own private data-source"
        userorg = UserOrganization.objects.get(organization=org, user=authenticated_client.user)
        assert (
            org.private_data_source == userorg.source
        ), "user-organization data source should be the organizations own private data-source"

    def test_user_default_organization_creation_not_allowed(self, authenticated_client, settings):
        settings.ALLOW_USER_REGISTRATION = False
        url = reverse("organization-create-user-default")
        assert Organization.objects.count() == 0
        resp = authenticated_client.post(
            url, {"name": "test organization"}, content_type="application/json"
        )
        assert resp.status_code == 400
        assert Organization.objects.count() == 0

    def test_user_default_organization_creation_twice(self, authenticated_client, settings):
        settings.ALLOW_USER_REGISTRATION = True
        url = reverse("organization-create-user-default")
        assert Organization.objects.count() == 0
        resp = authenticated_client.post(
            url, {"name": "test organization"}, content_type="application/json"
        )
        assert resp.status_code == 201
        assert Organization.objects.count() == 1
        # second time
        resp = authenticated_client.post(
            url, {"name": "test organization"}, content_type="application/json"
        )
        assert resp.status_code == 400, "only one organization per user"
        assert Organization.objects.count() == 1

    def test_user_default_organization_different_users(
        self, admin_client, authenticated_client, settings
    ):
        settings.ALLOW_USER_REGISTRATION = True
        url = reverse("organization-create-user-default")
        assert Organization.objects.count() == 0
        resp = admin_client.post(
            url, {"name": "test organization"}, content_type="application/json"
        )
        assert resp.status_code == 201
        assert Organization.objects.count() == 1
        # second time
        resp = authenticated_client.post(
            url, {"name": "test organization"}, content_type="application/json"
        )
        assert resp.status_code == 201, "no problem for different user"
        assert Organization.objects.count() == 2
        # each user should have one organization
        assert authenticated_client.user.organizations.count() == 1
        admin_user = User.objects.get(is_superuser=True)
        assert admin_user.organizations.count() == 1

    def test_organization_interest_no_data(self, master_user_client, interest_rt):
        """
        Test the `interest` custom action of organization ViewSet without any data
        """
        resp = master_user_client.get(reverse("organization-interest", args=("-1",)))
        assert resp.status_code == 200
        assert resp.json() == {"days": 0, "interest_sum": None, "max_date": None, "min_date": None}

    def test_organization_interest_data(self, master_user_client, interest_rt):
        """
        Test the `interest` custom action of organization ViewSet with some data
        """
        metric = Metric.objects.create(short_name="a", name="a")
        ib = ImportBatchFactory(report_type=interest_rt)
        AccessLog.objects.create(
            report_type=interest_rt, value=5, date="2020-01-01", metric=metric, import_batch=ib
        )
        resp = master_user_client.get(reverse("organization-interest", args=("-1",)))
        assert resp.status_code == 200
        assert resp.json() == {
            "days": 31,
            "interest_sum": 5,
            "max_date": "2020-01-31",
            "min_date": "2020-01-01",
        }

    def test_organization_interest_data_organizations(
        self, master_user_client, interest_rt, organizations
    ):
        """
        Test the `interest` custom action of organization ViewSet with some data and a specific
        organization
        """
        metric = Metric.objects.create(short_name="a", name="a")
        ib = ImportBatchFactory(report_type=interest_rt)
        AccessLog.objects.create(
            report_type=interest_rt,
            value=5,
            date="2020-01-01",
            metric=metric,
            import_batch=ib,
            organization=organizations["standalone"],
        )
        AccessLog.objects.create(
            report_type=interest_rt,
            value=7,
            date="2020-02-01",
            metric=metric,
            import_batch=ib,
            organization=organizations["standalone"],
        )
        resp = master_user_client.get(
            reverse("organization-interest", args=(organizations["standalone"].pk,))
        )
        assert resp.status_code == 200
        assert resp.json() == {
            "days": 60,
            "interest_sum": 12,
            "max_date": "2020-02-29",
            "min_date": "2020-01-01",
        }
        resp = master_user_client.get(
            reverse("organization-interest", args=(organizations["branch"].pk,))
        )
        assert resp.status_code == 200
        assert resp.json() == {"days": 0, "interest_sum": None, "max_date": None, "min_date": None}


@pytest.mark.django_db
class TestOrganizationAltNameAPI:
    @pytest.mark.parametrize(
        ["client", "passes"],
        (
            ("su", True),
            ("master_admin", True),
            ("admin1", False),
            ("admin2", False),
            ("master_user", False),
        ),
    )
    def test_create(self, clients, organizations, basic1, client, passes):
        org_id = organizations["standalone"].pk

        OrganizationAltNameFactory(organization=organizations["standalone"], name="alt1")

        # Success
        resp = clients[client].post(reverse("alt-name-list", args=(org_id,)), {"name": "alt2"})
        if passes:
            assert resp.status_code == 201
        else:
            assert resp.status_code == 403

        # Organization not found
        resp = clients[client].post(reverse("alt-name-list", args=(0,)), {"name": "alt2"})
        if passes:
            assert resp.status_code == 404
        else:
            assert resp.status_code == 403

        # Name conflict with existing alt name
        resp = clients[client].post(reverse("alt-name-list", args=(org_id,)), {"name": "alt1"})
        if passes:
            assert resp.status_code == 400
        else:
            assert resp.status_code == 403

        # Name conflict with existing organization name
        resp = clients[client].post(
            reverse("alt-name-list", args=(org_id,)), {"name": "standalone"}
        )
        if passes:
            assert resp.status_code == 400
        else:
            assert resp.status_code == 403

    @pytest.mark.parametrize(
        ["client", "passes"],
        (
            ("su", True),
            ("master_admin", True),
            ("admin1", False),
            ("admin2", False),
            ("master_user", False),
        ),
    )
    def test_delete(self, clients, organizations, basic1, client, passes):
        org_id = organizations["standalone"].pk

        alt_id = OrganizationAltNameFactory(
            organization=organizations["standalone"], name="alt1"
        ).id

        # Organization not found
        resp = clients[client].delete(reverse("alt-name-detail", args=(0, alt_id)))
        if passes:
            assert resp.status_code == 404
        else:
            assert resp.status_code == 403

        # Alt name not found
        resp = clients[client].delete(reverse("alt-name-detail", args=(org_id, 0)))
        if passes:
            assert resp.status_code == 404
        else:
            assert resp.status_code == 403

        # Success
        resp = clients[client].delete(reverse("alt-name-detail", args=(org_id, alt_id)))
        if passes:
            assert resp.status_code == 204
        else:
            assert resp.status_code == 403

        # Already deleted
        resp = clients[client].delete(reverse("alt-name-detail", args=(org_id, alt_id)))
        if passes:
            assert resp.status_code == 404
        else:
            assert resp.status_code == 403


@pytest.mark.django_db
class TestAutocompletes:
    @pytest.mark.parametrize(
        "url_name,forward,is_staff,is_superuser,empty",
        (
            ("country-autocomplete", None, False, False, True),
            ("country-autocomplete", None, True, True, False),
            ("country-autocomplete", None, True, False, False),
            ("country-autocomplete", None, True, True, False),
            ("state-autocomplete", {"country": "US"}, False, False, True),
            ("state-autocomplete", {"country": "US"}, True, True, False),
            ("state-autocomplete", {"country": "US"}, True, False, False),
            ("state-autocomplete", {"country": "US"}, True, True, False),
        ),
    )
    def test_autocomplete_perissions(self, url_name, forward, is_staff, is_superuser, empty):
        identity = IdentityFactory(user__is_staff=is_staff, user__is_superuser=is_superuser)
        client = make_client(identity, True)
        query = f"?forward={quote(json.dumps(forward))}" if forward else ""
        resp = client.get(f"{reverse(url_name)}{query}")
        assert resp.status_code == 200
        data = resp.json()
        if empty:
            assert data["results"] == []
        else:
            assert len(data["results"]) > 0
