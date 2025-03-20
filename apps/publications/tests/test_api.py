import uuid
from unittest import mock

import pytest
from api.models import OrganizationAPIKey
from celus_nigiri import CounterRecord
from core.fake_data import DataSourceFactory
from core.models import DataSource, Identity
from core.tests.conftest import (  # noqa - fixtures
    authenticated_client,  # noqa - fixtures
    authentication_headers,
    invalid_identity,
    master_user_client,
    master_user_identity,
    valid_identity,
)
from django.core.management import call_command
from django.db.models import Sum
from django.urls import reverse
from logs.fake_data import (
    AccessLogFactory,
    ImportBatchFactory,
    ImportBatchFullFactory,
    InterestGroupFactory,
    MetricFactory,
    ReportTypeFactory,
)
from logs.logic.data_import import (
    create_platformtitle_links_from_accesslogs,
    import_counter_records,
)
from logs.logic.interest.computation import sync_interest_by_import_batches
from logs.models import (
    AccessLog,
    Dimension,
    DimensionFilter,
    DimensionText,
    ImportBatch,
    InterestConfig,
    InterestDimensionValueMapping,
    InterestFilter,
    InterestProfile,
    Metric,
    OrganizationPlatform,
    ReportInterestMetric,
    ReportType,
)
from logs.tests.conftest import report_type_nd  # noqa - fixture
from organizations.fake_data import OrganizationFactory
from organizations.models import UserOrganization
from sushi.fake_data import FetchAttemptFactory
from sushi.models import AttemptStatus, CounterReportType, SushiCredentials
from tags.fake_data import TagForTitleFactory
from tags.models import AccessibleBy

from publications.fake_data import ItemFactory, PlatformFactory, TitleFactory
from publications.models import Platform, PlatformTitle, Title
from test_scenarios.basic import *  # noqa - fixtures

KNOWLEDGEBASE = {
    "notes_url": None,
    "providers": [
        {
            "provider": {
                "pk": 999,
                "url": "https://www.example.com/sushi5/",
                "name": "www.example.com",
                "extra": {},
                "yearly": None,
                "monthly": None,
                "counter_registry_id": "11111111-1111-1111-1111-111111111111",
            },
            "counter_version": 5,
            "assigned_report_types": [
                {"report_type": "PR", "not_valid_after": None, "not_valid_before": None},
                {"report_type": "TR", "not_valid_after": None, "not_valid_before": None},
            ],
        },
        {
            "provider": {
                "pk": 998,
                "url": "https://www.example.com/sushi51/",
                "name": "www.example.com",
                "extra": {},
                "yearly": None,
                "monthly": None,
                "counter_registry_id": "22222222-2222-2222-2222-222222222222",
            },
            "counter_version": 51,
            "assigned_report_types": [
                {"report_type": "IR", "not_valid_after": None, "not_valid_before": None},
                {"report_type": "DR", "not_valid_after": None, "not_valid_before": None},
            ],
        },
    ],
}


class MockTask:
    def __init__(self):
        self.id = uuid.uuid4()


@pytest.fixture
def real_world_data_with_interest(interest_rt):
    call_command("check_report_type_dimensions", "--fix-it")
    call_command("check_interest_definitions", "--fix-it")
    org = OrganizationFactory.create()
    platform = PlatformFactory.create()
    tr = ReportType.objects.get(short_name="TR")
    # load data
    basic_data = {
        "start": "2024-01-01",
        "end": "2024-01-31",
        "title": "Title 1",
        "title_ids": {"ISBN": "9780787960186"},
        "metric": "Total_Item_Requests",
    }
    crs = [
        CounterRecord(
            value=1,
            dimension_data={
                "Data_Type": "Book",
                "Access_Type": "Controlled",
                "Access_Method": "Normal",
            },
            **basic_data,
        ),
        CounterRecord(
            value=2,
            dimension_data={
                "Data_Type": "Book",
                "Access_Type": "OA_Gold",
                "Access_Method": "Normal",
            },
            **basic_data,
        ),
        CounterRecord(
            value=4,
            dimension_data={"Data_Type": "Book", "Access_Type": "OA_Gold", "Access_Method": "TDM"},
            **basic_data,
        ),
        CounterRecord(
            value=8,
            dimension_data={
                "Data_Type": "Book",
                "Access_Type": "Controlled",
                "Access_Method": "TDM",
            },
            **basic_data,
        ),
    ]
    import_counter_records(tr, org, platform, crs)
    return {"organization": org, "platform": platform, "tr": tr, "interest_rt": interest_rt}


def create_interest_configs(org):
    # global config
    interest_filters = {"Access_Type": "Controlled"}
    ic = InterestConfig.objects.default()
    for dim_name, value in interest_filters.items():
        df = DimensionFilter.objects.create(
            dimension=Dimension.objects.get(short_name=dim_name), values=[value]
        )
        InterestFilter.objects.create(interest_config=ic, filter=df)
    # org config
    interest_filters = {"Access_Type": "Controlled", "Access_Method": "Normal"}
    org_ic = InterestConfig.objects.create(
        organization=org, interest_profile=InterestProfile.objects.default()
    )
    for dim_name, value in interest_filters.items():
        df = DimensionFilter.objects.create(
            dimension=Dimension.objects.get(short_name=dim_name), values=[value]
        )
        InterestFilter.objects.create(interest_config=org_ic, filter=df)
    return {"global_interest_config": ic, "org_interest_config": org_ic}


@pytest.fixture
def real_world_data_with_interest_and_configs(real_world_data_with_interest):
    org = real_world_data_with_interest["organization"]
    return {**create_interest_configs(org), **real_world_data_with_interest}


@pytest.fixture
def real_world_item_data_with_interest(interest_rt):
    call_command("check_report_type_dimensions", "--fix-it")
    call_command("check_interest_definitions", "--fix-it")
    org = OrganizationFactory.create()
    platform = PlatformFactory.create()
    ir = ReportType.objects.get(short_name="IR51")
    # load data
    basic_data = {
        "start": "2024-01-01",
        "end": "2024-01-31",
        "title": "Title 1",
        "item": "Item 1",
        "metric": "Total_Item_Requests",
    }
    crs = [
        CounterRecord(
            value=1,
            dimension_data={
                "Data_Type": "Article",
                "Access_Type": "Controlled",
                "Access_Method": "Normal",
            },
            **basic_data,
        ),
        CounterRecord(
            value=2,
            dimension_data={
                "Data_Type": "Article",
                "Access_Type": "Free_To_Read",
                "Access_Method": "Normal",
            },
            **basic_data,
        ),
        CounterRecord(
            value=4,
            dimension_data={
                "Data_Type": "Article",
                "Access_Type": "Free_To_Read",
                "Access_Method": "TDM",
            },
            **basic_data,
        ),
        CounterRecord(
            value=8,
            dimension_data={
                "Data_Type": "Article",
                "Access_Type": "Controlled",
                "Access_Method": "TDM",
            },
            **basic_data,
        ),
    ]
    import_counter_records(ir, org, platform, crs)
    return {"organization": org, "platform": platform, "ir": ir}


@pytest.fixture
def real_world_item_data_with_interest_and_configs(real_world_item_data_with_interest):
    return {
        **create_interest_configs(real_world_item_data_with_interest["organization"]),
        **real_world_item_data_with_interest,
    }


@pytest.mark.django_db
class TestPlatformAPI:
    def test_unauthorized_user(
        self, client, invalid_identity, authentication_headers, organizations
    ):
        resp = client.get(
            reverse("platform-list", args=[organizations["root"].pk]),
            **authentication_headers(invalid_identity),
        )
        assert resp.status_code in (403, 401)  # depends on auth backend

    def test_authorized_user_no_platforms_no_org(self, authenticated_client, organizations):
        resp = authenticated_client.get(reverse("platform-list", args=[organizations["root"].pk]))
        assert resp.status_code == 404

    def test_authorized_user_no_platforms_org(
        self, authenticated_client, organizations, valid_identity
    ):
        identity = Identity.objects.select_related("user").get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations["root"])
        resp = authenticated_client.get(reverse("platform-list", args=[organizations["root"].pk]))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_authorized_user_accessible_empty_platforms(
        self, authenticated_client, organizations, valid_identity
    ):
        identity = Identity.objects.select_related("user").get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations["root"])
        resp = authenticated_client.get(reverse("platform-list", args=[organizations["root"].pk]))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_authorized_user_inaccessible_platforms(
        self, authenticated_client, organizations, platforms, valid_identity
    ):
        identity = Identity.objects.select_related("user").get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations["empty"])
        resp = authenticated_client.get(reverse("platform-list", args=[organizations["empty"].pk]))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_authorized_user_accessible_platforms(
        self, authenticated_client, organizations, platforms, valid_identity
    ):
        identity = Identity.objects.select_related("user").get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations["root"])
        OrganizationPlatform.objects.create(
            organization=organizations["root"], platform=platforms["root"]
        )
        resp = authenticated_client.get(reverse("platform-list", args=[organizations["root"].pk]))
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["pk"] == platforms["root"].pk

    def test_authorized_user_accessible_platforms_through_sushi(
        self, authenticated_client, organizations, platforms, valid_identity
    ):
        """
        Test that sushi credentials based link between organization and platform is enough to make
        the platform accessible through the API
        """
        identity = Identity.objects.select_related("user").get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations["root"])
        SushiCredentials.objects.create(
            organization=organizations["root"], platform=platforms["root"], counter_version=5
        )
        resp = authenticated_client.get(
            reverse("platform-list", args=[organizations["root"].pk]), {"used_only": 1}
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["pk"] == platforms["root"].pk

    def test_authorized_user_platforms_in_inaccessible_org(
        self, authenticated_client, organizations, platforms
    ):
        """
        There is an org and it has platforms, but the user cannot access the org
        """
        OrganizationPlatform.objects.create(
            organization=organizations["root"], platform=platforms["root"]
        )
        resp = authenticated_client.get(reverse("platform-list", args=[organizations["root"].pk]))
        assert resp.status_code == 404

    @pytest.mark.parametrize(
        "client,organization,data_source,code",
        (
            ("su", "standalone", None, 201),  # superuser
            ("master_admin", "standalone", "standalone", 201),
            ("master_admin", "standalone", None, 201),
            # we do not have organizations in brain, but it serves as a random global source
            ("master_admin", "standalone", "brain", 201),
            ("master_user", "standalone", "standalone", 403),
            ("admin2", "standalone", None, 201),  # this admin
            ("admin1", "standalone", "standalone", 403),  # other admin
            ("user2", "standalone", None, 403),  # other user
            ("su", None, None, 201),  # superuser
            ("master_admin", None, None, 201),
            ("master_user", None, None, 403),
            ("admin2", None, None, 403),  # this admin
            ("admin1", None, None, 403),  # other admin
            ("user2", None, None, 403),  # other user
        ),
    )
    def test_create_platform_for_organization(
        self,
        basic1,
        clients,
        organizations,
        client,
        organization,
        code,
        data_sources,
        data_source,
        report_types,
        settings,
    ):
        settings.ALLOW_USER_CREATED_PLATFORMS = True
        # Set data source for the organization
        if organization:
            organizations[organization].source = data_sources[data_source] if data_source else None
            organizations[organization].save()

        # su client
        organization_pk = organizations[organization].pk if organization else -1
        resp = clients[client].post(
            reverse("platform-list", args=[organization_pk]),
            {
                "ext_id": 122,  # ext_id may not be present and will be overriden to None
                "short_name": "platform",
                "name": "long_platform",
                "url": "https://example.com",
                "provider": "provider",
            },
        )
        assert resp.status_code == code
        if resp.status_code == 201:
            new_platform = Platform.objects.order_by("pk").last()
            if organization:
                assert new_platform.source == DataSource.objects.get(
                    organization=organizations[organization], type=DataSource.TYPE_ORGANIZATION
                )
            assert new_platform.ext_id is None
            assert new_platform.short_name == "platform"
            assert new_platform.name == "long_platform"
            assert new_platform.provider == "provider"
            assert new_platform.url == "https://example.com"

        resp = clients[client].post(
            reverse("platform-list", args=[organization_pk]),
            {
                "ext_id": 122,  # ext_id may not be present and will be overriden to None
                "short_name": "platform",
                "name": "long_platform",
                "url": "https://example.com",
                "provider": "provider",
            },
        )
        assert resp.status_code in [400, 403], "Already created"

    def test_create_platform_for_organization_with_no_data_source(
        self, basic1, clients, organizations, client, settings
    ):
        settings.ALLOW_USER_CREATED_PLATFORMS = True
        assert organizations["master"].source is None

        resp = clients["su"].post(
            reverse("platform-list", args=[organizations["master"].pk]),
            {
                "short_name": "platform",
                "name": "long_platform",
                "url": "https://example.com",
                "provider": "provider",
            },
        )
        assert resp.status_code == 201

        organizations["master"].refresh_from_db()
        assert organizations["master"].source is None, "no change to organization source"

        resp = clients["su"].post(
            reverse("platform-list", args=[organizations["master"].pk]),
            {
                "short_name": "platform",
                "name": "long_platform",
                "url": "https://example.com",
                "provider": "provider",
            },
        )
        assert resp.status_code == 400, "Already created"

    def test_create_platform_for_organization_counter_reports_knowledgebase(
        self, basic1, clients, organizations, client, counter_report_types, settings
    ):
        # Override to knowledgebase
        resp = clients["master_admin"].post(
            reverse("platform-list", args=[organizations["master"].pk]),
            {
                "short_name": "platform1",
                "name": "first_platform",
                "url": "https://example.com",
                "provider": "provider",
                "counter_reports_source": "knowledgebase",
                "counter_reports": [
                    counter_report_types["tr"].pk,
                    counter_report_types["jr1"].pk,
                ],  # these counter_report_types should be overriden
                "knowledgebase": KNOWLEDGEBASE,
            },
            format="json",
        )
        assert resp.status_code == 201
        platform = Platform.objects.get(pk=resp.data["pk"])
        assert set(platform.counter_reports.values_list("counter_version", "code")) == {
            (5, "PR"),
            (5, "TR"),
            (51, "IR"),
            (51, "DR"),
        }

    def test_create_platform_for_organization_counter_reports_manual(
        self, basic1, clients, organizations, client, counter_report_types, settings
    ):
        resp = clients["master_admin"].post(
            reverse("platform-list", args=[organizations["master"].pk]),
            {
                "short_name": "platform2",
                "name": "second_platform",
                "url": "https://example2.com",
                "provider": "provider",
                "counter_reports_source": "manual",
                "counter_reports": [counter_report_types["tr"].pk, counter_report_types["jr1"].pk],
                "knowledgebase": KNOWLEDGEBASE,
            },
            format="json",
        )
        assert resp.status_code == 201
        platform = Platform.objects.get(pk=resp.data["pk"])
        assert set(platform.counter_reports.values_list("counter_version", "code")) == {
            (5, "TR"),
            (4, "JR1"),
        }

    def test_create_platform_for_organization_counter_reports_empty_kb(
        self, basic1, clients, organizations, client, counter_report_types, settings
    ):
        resp = clients["master_admin"].post(
            reverse("platform-list", args=[organizations["master"].pk]),
            {
                "short_name": "platform3",
                "name": "third_platform",
                "url": "https://example3.com",
                "provider": "provider",
                "counter_reports_source": "knowledgebase",
                "counter_reports": [counter_report_types["tr"].pk, counter_report_types["jr1"].pk],
                "knowledgebase": None,
            },
            format="json",
        )
        assert resp.status_code == 201
        platform = Platform.objects.get(pk=resp.data["pk"])
        assert set(platform.counter_reports.values_list("counter_version", "code")) == set()

    def test_create_platform_for_two_organizations_with_no_data_source(
        self, basic1, clients, organizations, client, settings
    ):
        """
        This is a test for a bug which caused all auto-created data sources to have empty
        `short_name` field and thus only one data source could be created.
        """
        settings.ALLOW_USER_CREATED_PLATFORMS = True
        # make sure there is no data source for organizations
        DataSource.objects.filter(type=DataSource.TYPE_ORGANIZATION).delete()

        master_org = organizations["master"]
        assert master_org.source is None
        resp = clients["su"].post(
            reverse("platform-list", args=[master_org.pk]),
            {"short_name": "platform", "name": "long_platform", "provider": "provider"},
        )
        assert resp.status_code == 201

        # try it for another organization
        standalone_org = organizations["standalone"]
        assert standalone_org.source is None
        resp = clients["su"].post(
            reverse("platform-list", args=[standalone_org.pk]),
            {"short_name": "platform2", "name": "long_platform2", "provider": "provider"},
        )
        assert resp.status_code == 201

    @pytest.mark.parametrize("user,status", (("admin2", 403), ("master_admin", 201), ("su", 201)))
    def test_create_platform_when_disabled(
        self, basic1, clients, organizations, settings, user, status
    ):
        settings.ALLOW_USER_CREATED_PLATFORMS = False

        resp = clients[user].post(
            reverse("platform-list", args=[organizations["standalone"].pk]),
            {
                "short_name": "platform",
                "name": "long_platform",
                "url": "https://example.com",
                "provider": "provider",
            },
        )
        assert resp.status_code == status

    def test_list_platforms_for_all_organization(self, basic1, clients, organizations, client):
        resp = clients["master_admin"].get(reverse("platform-list", args=[-1]))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 7
        mapped = {e["short_name"]: e for e in data}
        assert mapped["brain"]["source"]["organization"] is None
        assert mapped["branch"]["source"]["organization"]["name"] == "branch"
        assert mapped["empty"]["source"] is None
        assert mapped["master"]["source"]["organization"] is None
        assert mapped["root"]["source"]["organization"]["name"] == "root"
        assert mapped["shared"]["source"] is None
        assert mapped["standalone"]["source"]["organization"]["name"] == "standalone"

        resp = clients["master_admin"].get(reverse("platform-list", args=[-1]) + "?used_only")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        # only those platforms with organization source
        mapped = {e["short_name"]: e for e in data}
        assert mapped["branch"]["source"]["organization"]["name"] == "branch"
        assert mapped["root"]["source"]["organization"]["name"] == "root"
        assert mapped["standalone"]["source"]["organization"]["name"] == "standalone"

    @pytest.mark.parametrize(
        "client,organization,platform,code",
        (
            ("su", "standalone", "standalone", 200),  # superuser
            ("master_admin", "standalone", "standalone", 200),
            ("master_user", "standalone", "standalone", 403),
            ("admin2", "standalone", "standalone", 200),  # this admin
            ("admin1", "standalone", "standalone", 403),  # other admin
            ("user2", "standalone", "standalone", 403),  # other user
        ),
    )
    def test_update_platform_for_organization(
        self,
        basic1,
        clients,
        organizations,
        client,
        organization,
        code,
        data_sources,
        report_types,
        platform,
        platforms,
        settings,
    ):
        settings.ALLOW_USER_CREATED_PLATFORMS = True
        resp = clients[client].patch(
            reverse(
                "platform-detail", args=[organizations[organization].pk, platforms[platform].pk]
            ),
            {
                "ext_id": 122,  # ext_id may not be present and will be overriden to None
                "short_name": "platform",
                "name": "long_platform",
                "url": "https://example.com",
                "provider": "provider",
            },
        )
        assert resp.status_code == code
        if resp.status_code // 100 == 2:
            platform = Platform.objects.get(short_name="platform")
            assert platform.source == data_sources["standalone"]
            assert platform.ext_id is None
            assert platform.name == "long_platform"
            assert platform.provider == "provider"
            assert platform.url == "https://example.com"

    @pytest.mark.parametrize(
        "client,code",
        (
            ("su", 200),
            ("master_admin", 200),
            ("master_user", 403),
            ("admin1", 403),  # this admin
            ("admin2", 403),  # other admin
            ("user1", 403),  # user
        ),
    )
    def test_update_platform_for_organization_with_no_data_source(
        self, basic1, clients, organizations, platforms, client, code
    ):
        OrganizationPlatform.objects.create(
            organization=organizations["master"], platform=platforms["master"]
        )
        resp = clients[client].patch(
            reverse("platform-detail", args=[organizations["master"].pk, platforms["master"].pk]),
            {
                "short_name": "platform",
                "name": "long_platform",
                "url": "https://example.com",
                "provider": "provider",
            },
        )
        assert resp.status_code == code

    @pytest.mark.parametrize("user,status", (("admin2", 403), ("master_admin", 200), ("su", 200)))
    def test_update_platform_when_disabled(
        self, basic1, clients, organizations, platforms, settings, user, status
    ):
        settings.ALLOW_USER_CREATED_PLATFORMS = False

        resp = clients[user].patch(
            reverse(
                "platform-detail", args=[organizations["standalone"].pk, platforms["standalone"].pk]
            ),
            {
                "short_name": "platform",
                "name": "long_platform",
                "url": "https://example.com",
                "provider": "provider",
            },
        )
        assert resp.status_code == status

    @pytest.mark.parametrize("allow_user_created_platforms", (True, False))
    def test_update_platform_for_organization_report_types(
        self,
        basic1,
        clients,
        organizations,
        data_sources,
        report_types,
        counter_report_types,
        platforms,
        credentials,
        settings,
        allow_user_created_platforms,
    ):
        settings.ALLOW_USER_CREATED_PLATFORMS = allow_user_created_platforms
        platform = platforms["standalone"]
        org_id = organizations["standalone"].pk
        credentials["standalone_br1_jr1"].use_counter_reports_from_platform = True
        credentials["standalone_br1_jr1"].save()

        credentials["standalone_tr"].use_counter_reports_from_platform = False
        credentials["standalone_tr"].save()

        credentials["standalone_ir51"].use_counter_reports_from_platform = True
        credentials["standalone_ir51"].save()

        platform.knowledgebase = KNOWLEDGEBASE
        platform.save()

        # Platform counter reports are updated manualy
        resp = clients["master_admin"].patch(
            reverse("platform-detail", args=[org_id, platform.pk]),
            {
                "counter_reports_source": "manual",
                "counter_reports": [counter_report_types["ir"].pk, counter_report_types["tr51"].pk],
            },
        )
        assert resp.status_code == 200
        assert set(platform.counter_reports.values_list("counter_version", "code")) == {
            (5, "IR"),
            (51, "TR"),
        }, "report types are manually set"

        # check credentials to see the updates
        assert (
            len(
                credentials["standalone_br1_jr1"].counter_reports.values_list(
                    "counter_version", "code"
                )
            )
            == 0
        ), "C4 creds were unset"
        assert set(
            credentials["standalone_tr"].counter_reports.values_list("counter_version", "code")
        ) == {(5, "TR")}, "C5 creds were not modified"
        assert set(
            credentials["standalone_ir51"].counter_reports.values_list("counter_version", "code")
        ) == {(51, "TR")}, "C51 creds were update"

        # Platform counter reports are updated from knowledgebase
        resp = clients["master_admin"].patch(
            reverse("platform-detail", args=[org_id, platform.pk]),
            {
                "counter_reports_source": "knowledgebase",
                "counter_reports": [counter_report_types["ir"].pk, counter_report_types["tr51"].pk],
            },
        )
        assert resp.status_code == 200

        assert set(platform.counter_reports.values_list("counter_version", "code")) == {
            (5, "PR"),
            (5, "TR"),
            (51, "DR"),
            (51, "IR"),
        }, "report types are based on knowledgebase"

        # check credentials to see the updates
        assert (
            len(
                credentials["standalone_br1_jr1"].counter_reports.values_list(
                    "counter_version", "code"
                )
            )
            == 0
        ), "C4 creds are still unset"
        assert set(
            credentials["standalone_tr"].counter_reports.values_list("counter_version", "code")
        ) == {(5, "TR")}, "C5 creds were not modified"
        assert set(
            credentials["standalone_ir51"].counter_reports.values_list("counter_version", "code")
        ) == {(51, "IR"), (51, "DR")}, "C51 creds were updated"

    @pytest.mark.parametrize("allow_user_created_platforms", (True, False))
    @pytest.mark.parametrize("delete_credentials", (True, False))
    @pytest.mark.parametrize(
        ["user", "delete_platform", "org_platform", "can_delete"],
        [
            ["user1", False, False, False],
            ["user2", False, False, False],
            ["admin1", False, False, False],
            ["admin2", False, False, True],
            ["master_admin", False, False, True],
            ["master_user", False, False, False],
            ["su", False, False, True],
            ["su", True, False, False],
            ["su", True, True, True],
        ],
    )
    def test_platform_delete_all_data(
        self,
        basic1,
        clients,
        platforms,
        organizations,
        user,
        delete_platform,
        org_platform,
        can_delete,
        settings,
        allow_user_created_platforms,
        delete_credentials,
    ):
        """
        :param org_platform: platform is custom platform for organization
        """
        settings.ALLOW_USER_CREATED_PLATFORMS = allow_user_created_platforms

        platform = platforms["standalone"] if org_platform else platforms["shared"]
        organization = organizations["standalone"]
        ImportBatchFullFactory.create(platform=platform, organization=organization)
        assert AccessLog.objects.filter(organization=organization, platform=platform).count() > 0

        with mock.patch("publications.views.delete_platform_data_task") as task_mock:
            task_mock.delay.return_value = MockTask()
            resp = clients[user].post(
                reverse("platform-delete-all-data", args=[organization.pk, platform.pk]),
                {"delete_platform": delete_platform, "delete_credentials": delete_credentials},
            )
            if can_delete:
                assert resp.status_code == 200
                task_mock.delay.assert_called_once_with(
                    str(platform.pk), [organization.pk], delete_platform, delete_credentials
                )
            else:
                assert resp.status_code in (403, 404, 400)
                task_mock.delay.assert_not_called()

    @pytest.mark.parametrize(
        ["user", "can_delete"],
        [
            ["user1", False],
            ["user2", False],
            ["admin1", False],
            ["admin2", False],
            ["master_admin", True],
            ["master_user", False],
            ["su", True],
        ],
    )
    def test_platform_delete_all_data_all_organizations(
        self, basic1, clients, platforms, organizations, user, can_delete
    ):
        platform = platforms["standalone"]
        org_to_al_count = {}
        for organization in organizations.values():
            ImportBatchFullFactory.create(platform=platform, organization=organization)
            al_count = AccessLog.objects.filter(
                organization=organization, platform=platform
            ).count()
            assert al_count > 0
            org_to_al_count[organization.pk] = al_count

        with mock.patch("publications.views.delete_platform_data_task") as task_mock:
            task_mock.delay.return_value = MockTask()
            resp = clients[user].post(reverse("platform-delete-all-data", args=[-1, platform.pk]))
            if can_delete:
                assert resp.status_code == 200
                task_mock.delay.assert_called()
            else:
                assert resp.status_code in (403, 404)
                task_mock.delay.assert_not_called()


@pytest.mark.django_db
class TestPlatformDetailedAPI:
    def test_unauthorized_user(
        self, client, invalid_identity, authentication_headers, organizations
    ):
        resp = client.get(
            reverse("platform-list", args=[organizations["root"].pk]),
            **authentication_headers(invalid_identity),
        )
        assert resp.status_code in (403, 401)  # depends on auth backend

    def test_authorized_user_no_platforms_no_org(self, authenticated_client, organizations):
        resp = authenticated_client.get(reverse("platform-list", args=[organizations["root"].pk]))
        assert resp.status_code == 404

    def test_authorized_user_no_platforms_org(
        self, authenticated_client, organizations, valid_identity
    ):
        identity = Identity.objects.select_related("user").get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations["root"])
        resp = authenticated_client.get(reverse("platform-list", args=[organizations["root"].pk]))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_authorized_user_accessible_empty_platforms(
        self, authenticated_client, organizations, valid_identity
    ):
        identity = Identity.objects.select_related("user").get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations["root"])
        resp = authenticated_client.get(reverse("platform-list", args=[organizations["root"].pk]))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_authorized_user_inaccessible_platforms(
        self, authenticated_client, organizations, valid_identity
    ):
        identity = Identity.objects.select_related("user").get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations["root"])
        resp = authenticated_client.get(reverse("platform-list", args=[organizations["root"].pk]))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_authorized_user_accessible_platforms(
        self, authenticated_client, organizations, platforms, valid_identity
    ):
        identity = Identity.objects.select_related("user").get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations["root"])
        OrganizationPlatform.objects.create(
            organization=organizations["root"], platform=platforms["root"]
        )
        resp = authenticated_client.get(reverse("platform-list", args=[organizations["root"].pk]))
        assert resp.status_code == 200
        assert len(resp.json()) == 1


@pytest.mark.django_db
class TestPlatformTitleAPI:
    def test_unauthorized_user(
        self, client, invalid_identity, authentication_headers, organizations, platforms
    ):
        OrganizationPlatform.objects.create(
            organization=organizations["root"], platform=platforms["root"]
        )
        resp = client.get(
            reverse("platform-title-list", args=[organizations["root"].pk, platforms["root"].pk]),
            **authentication_headers(invalid_identity),
        )
        assert resp.status_code in (403, 401)  # depends on auth backend

    def test_authorized_user_no_org(self, authenticated_client, organizations, platforms):
        OrganizationPlatform.objects.create(
            organization=organizations["root"], platform=platforms["root"]
        )
        resp = authenticated_client.get(
            reverse("platform-title-list", args=[organizations["root"].pk, platforms["root"].pk])
        )
        assert resp.status_code == 404

    def test_authorized_user_accessible_platforms_no_titles(
        self, authenticated_client, organizations, platforms, valid_identity, titles
    ):
        """
        Titles are created by the 'titles' fixture, but should not appear in the result as they
        are not accessible for an associated platform
        """
        identity = Identity.objects.select_related("user").get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations["root"])
        OrganizationPlatform.objects.create(
            organization=organizations["root"], platform=platforms["root"]
        )
        resp = authenticated_client.get(
            reverse("platform-title-list", args=[organizations["root"].pk, platforms["root"].pk])
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_authorized_user_accessible_platforms_titles(
        self, authenticated_client, organizations, platforms, valid_identity, titles, report_type_nd
    ):
        identity = Identity.objects.select_related("user").get(identity=valid_identity)
        organization = organizations["root"]
        platform = platforms["root"]
        UserOrganization.objects.create(user=identity.user, organization=organization)
        # we need to connect some titles with the platform which is done indirectly through
        # AccessLog instances
        # we create 2 access logs but both for the same title so that we can check that
        # - title is present in the output only once - distinct is used properly
        # - second title is not present - the filtering works OK
        rt = report_type_nd(0)
        metric = Metric.objects.create(short_name="m1", name="Metric1")
        import_batch = ImportBatchFactory(
            platform=platform, organization=organization, report_type=rt
        )
        al1 = AccessLog.objects.create(
            platform=platform,
            target=titles[0],
            value=1,
            date="2019-01-01",
            report_type=rt,
            metric=metric,
            organization=organization,
            import_batch=import_batch,
        )
        al2 = AccessLog.objects.create(
            platform=platform,
            target=titles[0],
            value=1,
            date="2019-02-01",
            report_type=rt,
            metric=metric,
            organization=organization,
            import_batch=import_batch,
        )
        create_platformtitle_links_from_accesslogs([al1, al2])
        resp = authenticated_client.get(
            reverse("platform-title-list", args=[organization.pk, platform.pk])
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["isbn"] == titles[0].isbn
        assert resp.json()[0]["name"] == titles[0].name
        assert resp.json()[0]["proprietary_ids"] == titles[0].proprietary_ids

    def test_authorized_user_accessible_platforms_titles_count_and_interest(
        self,
        authenticated_client,
        organizations,
        platforms,
        valid_identity,
        titles,
        report_type_nd,
        interest_rt,
    ):
        identity = Identity.objects.select_related("user").get(identity=valid_identity)
        organization = organizations["root"]
        platform = platforms["root"]
        UserOrganization.objects.create(user=identity.user, organization=organization)
        # we need to connect some titles with the platform which is done indirectly through
        # AccessLog instances
        # we create 2 access logs but both for the same title so that we can check that
        # - title is present in the output only once - distinct is used properly
        # - second title is not present - the filtering works OK
        rt = report_type_nd(0)
        ig = InterestGroupFactory(short_name="interest1", position=1)
        metric = MetricFactory(short_name="m1", name="Metric1")
        ReportInterestMetric.objects.create(report_type=rt, metric=metric, interest_group=ig)
        import_batch = ImportBatchFactory(
            platform=platform, organization=organization, report_type=rt
        )
        al1 = AccessLog.objects.create(
            platform=platform,
            target=titles[0],
            value=1,
            date="2019-01-01",
            report_type=rt,
            metric=metric,
            organization=organization,
            import_batch=import_batch,
        )
        al2 = AccessLog.objects.create(
            platform=platform,
            target=titles[0],
            value=1,
            date="2019-02-01",
            report_type=rt,
            metric=metric,
            organization=organization,
            import_batch=import_batch,
        )
        create_platformtitle_links_from_accesslogs([al1, al2])
        sync_interest_by_import_batches()
        resp = authenticated_client.get(
            reverse("platform-title-interest-list", args=[organization.pk, platform.pk])
        )
        assert resp.status_code == 200
        assert "results" in resp.json()
        data = resp.json()["results"]
        assert len(data) == 1
        assert data[0]["isbn"] == titles[0].isbn
        assert data[0]["name"] == titles[0].name
        assert data[0]["interests"]["interest1"] == 2

    def test_authorized_user_accessible_platforms_titles_count_organization_filter(
        self,
        authenticated_client,
        organizations,
        platforms,
        valid_identity,
        titles,
        report_type_nd,
        interest_rt,
    ):
        """
        Test that when using the API to get number of accesses to a title on a platform,
        that data for a different organization are not counted in
        """
        identity = Identity.objects.select_related("user").get(identity=valid_identity)
        organization = organizations["root"]
        platform = platforms["root"]
        other_organization = organizations["standalone"]
        UserOrganization.objects.create(user=identity.user, organization=organization)
        # we need to connect some titles with the platform which is done indirectly through
        # AccessLog instances
        # we create 2 access logs but both for the same title so that we can check that
        # - title is present in the output only once - distinct is used properly
        # - second title is not present - the filtering works OK
        rt = report_type_nd(0)
        ig = InterestGroupFactory(short_name="interest1", position=1)
        metric = MetricFactory(short_name="m1", name="Metric1")
        ReportInterestMetric.objects.create(report_type=rt, metric=metric, interest_group=ig)
        import_batch1 = ImportBatchFactory(
            platform=platform, organization=organization, report_type=rt
        )
        import_batch2 = ImportBatchFactory(
            platform=platform, report_type=rt, organization=other_organization
        )
        al1 = AccessLog.objects.create(
            platform=platform,
            target=titles[0],
            value=3,
            date="2019-01-01",
            report_type=rt,
            metric=metric,
            organization=organization,
            import_batch=import_batch1,
        )
        al2 = AccessLog.objects.create(
            platform=platform,
            target=titles[0],
            value=2,
            date="2019-01-01",
            report_type=rt,
            metric=metric,
            organization=other_organization,
            import_batch=import_batch2,
        )
        create_platformtitle_links_from_accesslogs([al1, al2])
        sync_interest_by_import_batches()
        resp = authenticated_client.get(
            reverse("platform-title-interest-list", args=[organization.pk, platform.pk])
        )
        assert resp.status_code == 200
        assert "results" in resp.json()
        data = resp.json()["results"]
        assert len(data) == 1
        assert data[0]["isbn"] == titles[0].isbn
        assert data[0]["name"] == titles[0].name
        assert data[0]["interests"]["interest1"] == 3

    @pytest.mark.parametrize(
        ["org_in_query", "org_has_config", "exp_value"],
        [
            (True, True, 1),  # org has two filters, value is 1
            (True, False, 9),  # org used default config with one filter, value is 9
            (False, True, 9),  # all orgs, global config is used, value is 9
            (False, False, 9),  # all orgs, global config is used, value is 9
            (True, None, 15),  # there is neither org nor global config, value is 15
        ],
    )
    def test_title_interest_with_interest_config(
        self,
        master_user_client,
        real_world_data_with_interest_and_configs,
        org_in_query,
        org_has_config,
        exp_value,
    ):
        platform = real_world_data_with_interest_and_configs["platform"]
        org = real_world_data_with_interest_and_configs["organization"]
        if not org_has_config:
            real_world_data_with_interest_and_configs["org_interest_config"].delete()
            if org_has_config is None:
                real_world_data_with_interest_and_configs["global_interest_config"].delete()
        url = reverse(
            "platform-title-interest-list", args=(org.pk if org_in_query else -1, platform.pk)
        )
        resp = master_user_client.get(url)
        assert resp.status_code == 200
        data = resp.json()["results"]
        assert len(data) == 1, "There is only one title"
        assert data[0]["interests"]["full_text"] == exp_value

    def test_organization_platforms_overlap(
        self, authenticated_client, accesslogs_with_interest, valid_identity, platforms
    ):
        identity = Identity.objects.select_related("user").get(identity=valid_identity)
        organization = accesslogs_with_interest["organization"]
        platform = accesslogs_with_interest["platform"]
        titles = accesslogs_with_interest["titles"]
        UserOrganization.objects.create(user=identity.user, organization=organization)

        # first without any overlap and one platform
        resp = authenticated_client.get(
            reverse("organization-platform-overlap", args=[organization.pk])
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1, "1 self-overlap record"

        # add some usage to platform 2 and title 1 to create overlap
        platform2 = [pl for pl in platforms.values() if pl.pk != platform.pk][0]
        rt = accesslogs_with_interest["rt"]
        ib = ImportBatchFullFactory.create(
            platform=platform2,
            organization=organization,
            date="2020-01-01",
            report_type=rt,
            create_accesslogs__titles=[titles[0]],
            create_accesslogs__metrics=[accesslogs_with_interest["metric"]],
        )
        sync_interest_by_import_batches(ImportBatch.objects.filter(pk=ib.pk))

        resp = authenticated_client.get(
            reverse("organization-platform-overlap", args=[organization.pk])
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 4, "4 overlap records in total"
        assert (
            len([rec for rec in data if rec["platform1"] == rec["platform2"]]) == 2
        ), "2 records for self-overlap"
        assert (
            len([rec for rec in data if rec["platform1"] != rec["platform2"]]) == 2
        ), "2 records for other-overlap"
        check_rec = [
            rec
            for rec in data
            if rec["platform1"] == platform.pk and rec["platform2"] == platform2.pk
        ][0]
        assert check_rec["overlap"] == 1

    def test_organization_platforms_overlap_with_date_filter(
        self, authenticated_client, accesslogs_with_interest, valid_identity, platforms
    ):
        identity = Identity.objects.select_related("user").get(identity=valid_identity)
        organization = accesslogs_with_interest["organization"]
        platform = accesslogs_with_interest["platform"]
        titles = accesslogs_with_interest["titles"]
        UserOrganization.objects.create(user=identity.user, organization=organization)

        # add some usage to platform 2 and title 1 to create overlap
        platform2 = [pl for pl in platforms.values() if pl.pk != platform.pk][0]
        rt = accesslogs_with_interest["rt"]
        ib = ImportBatchFullFactory.create(
            platform=platform2,
            organization=organization,
            date="2019-03-01",
            report_type=rt,
            create_accesslogs__titles=[titles[0]],
            create_accesslogs__metrics=[accesslogs_with_interest["metric"]],
        )
        sync_interest_by_import_batches(ImportBatch.objects.filter(pk=ib.pk))

        # first with start_date allowing all records in
        resp = authenticated_client.get(
            reverse("organization-platform-overlap", args=[organization.pk]), {"start": "2019-01"}
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 4
        # then with start_date which removes the overlapping records
        resp = authenticated_client.get(
            reverse("organization-platform-overlap", args=[organization.pk]), {"start": "2019-03"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1, "only 1 self overlap"
        assert (
            len([rec for rec in data if rec["platform1"] == rec["platform2"]]) == 1
        ), "1 self-overlap"
        # then with end_date which removes the overlapping records
        resp = authenticated_client.get(
            reverse("organization-platform-overlap", args=[organization.pk]),
            {"start": "2019-01", "end": "2019-02"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1, "only 1 self overlap"
        assert (
            len([rec for rec in data if rec["platform1"] == rec["platform2"]]) == 1
        ), "1 self-overlap"

    @pytest.mark.parametrize(
        ["org_in_query", "org_has_config", "exp_value"],
        [
            (True, True, 1),  # org has two filters, value is 1
            (True, False, 9),  # org used default config with one filter, value is 9
            (False, True, 9),  # all orgs, global config is used, value is 9
            (False, False, 9),  # all orgs, global config is used, value is 9
            (True, None, 15),  # there is neither org nor global config, value is 15
        ],
    )
    def test_organization_platform_overlap_with_interest_config(
        self,
        master_user_client,
        real_world_data_with_interest_and_configs,
        org_in_query,
        org_has_config,
        exp_value,
    ):
        if not org_has_config:
            real_world_data_with_interest_and_configs["org_interest_config"].delete()
            if org_has_config is None:
                real_world_data_with_interest_and_configs["global_interest_config"].delete()

        org = real_world_data_with_interest_and_configs["organization"]

        url = reverse("organization-platform-overlap", args=[org.pk if org_in_query else -1])
        resp = master_user_client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1, "only 1 self overlap"
        assert data[0]["interest"] == exp_value

    def test_organization_all_platform_overlap(
        self, authenticated_client, accesslogs_with_interest, valid_identity, platforms, interest_rt
    ):
        identity = Identity.objects.select_related("user").get(identity=valid_identity)
        organization = accesslogs_with_interest["organization"]
        platform = accesslogs_with_interest["platform"]
        titles = accesslogs_with_interest["titles"]
        UserOrganization.objects.create(user=identity.user, organization=organization)

        # add some usage to platform 2 and title 1 to create overlap
        platform2 = [pl for pl in platforms.values() if pl.pk != platform.pk][0]
        rt = accesslogs_with_interest["rt"]
        ib = ImportBatchFullFactory.create(
            platform=platform2,
            organization=organization,
            date="2019-03-01",
            report_type=rt,
            create_accesslogs__titles=[titles[0]],
            create_accesslogs__metrics=[accesslogs_with_interest["metric"]],
            create_accesslogs__value=1,
        )
        sync_interest_by_import_batches(ImportBatch.objects.filter(pk=ib.pk))

        resp = authenticated_client.get(
            reverse("organization-all-platforms-overlap", args=[organization.pk])
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2, "2 records for 2 platforms"
        for rec in data:
            assert rec["overlap"] == 1, "both platforms share the same title"
            if rec["platform"] == platform.pk:
                assert rec["overlap_interest"] == 3
                assert rec["total_interest"] == 7
            else:
                assert rec["overlap_interest"] == 1, "interest is 1 on platform 2"
                assert rec["total_interest"] == 1, "interest is 1 on platform 2"

    def test_organization_all_platform_overlap_2(
        self,
        authenticated_client,
        accesslogs_with_interest,
        valid_identity,
        platforms,
        master_user_client,
    ):
        """
        Create two identical sets of access logs but for different platforms and see what the
        overlap would be
        """
        identity = Identity.objects.select_related("user").get(identity=valid_identity)
        organization = accesslogs_with_interest["organization"]
        platform = accesslogs_with_interest["platform"]
        titles = accesslogs_with_interest["titles"]
        import_batch = accesslogs_with_interest["import_batch"]
        metric = accesslogs_with_interest["metric"]
        platform2 = [pl for pl in platforms.values() if pl.pk != platform.pk][0]
        import_batch2 = ImportBatchFactory(
            platform=platform2, organization=organization, report_type=import_batch.report_type
        )
        # here we create the same accesslogs for a different platform
        accesslog_basics = {
            "report_type": import_batch.report_type,
            "metric": metric,
            "platform": platform2,
            "import_batch": import_batch2,
        }
        accesslogs = [
            AccessLog.objects.create(
                target=titles[0],
                value=1,
                date="2019-01-01",
                organization=organization,
                **accesslog_basics,
            ),
            AccessLog.objects.create(
                target=titles[0],
                value=2,
                date="2019-02-01",
                organization=organization,
                **accesslog_basics,
            ),
            AccessLog.objects.create(
                target=titles[1],
                value=4,
                date="2019-02-01",
                organization=organization,
                **accesslog_basics,
            ),
        ]
        create_platformtitle_links_from_accesslogs(accesslogs)
        sync_interest_by_import_batches()

        UserOrganization.objects.create(user=identity.user, organization=organization)
        resp = authenticated_client.get(
            reverse("organization-all-platforms-overlap", args=[organization.pk])
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2, "2 records for 2 platforms"
        for rec in data:
            assert rec["overlap"] == 2, "both platforms share the same 2 titles"
            assert rec["overlap_interest"] == 7
            assert rec["total_interest"] == 7

    # check that the result is correct regardless of date limits (it the data falls inside it)
    @pytest.mark.parametrize(
        ["start_date", "end_date"],
        [
            ("2023-01", "2023-01"),
            (None, None),
            ("2020-01", "2024-01"),
            (None, "2024-01"),
            ("2020-01", None),
        ],
    )
    def test_organization_all_platform_overlap_3(
        self, interest_rt, platforms, master_user_client, report_type_nd, start_date, end_date
    ):
        """
        Check the calculation of interest overlap in a situation where
        - overlap is requested for all organizations
        - three platforms share the same title
        - two of them share the same organization
        - third platform is not linked to the organization

        In this case the overlap of the third platform should be 0 because it is calculated
        when the same titles are available on different platforms for the same organization.

        This test should guard against a regression where the interest overlap was calculated
        as usage of titles on multiple platforms regardless of the organization.
        """
        org1, org2 = OrganizationFactory.create_batch(2)
        platform1, platform2, platform3 = PlatformFactory.create_batch(3)
        title = TitleFactory.create()
        # create the interest related records
        rt = report_type_nd(0)
        ig = InterestGroupFactory(short_name="interest1", position=1)
        metric = MetricFactory(short_name="m1", name="Metric1")
        ReportInterestMetric.objects.create(report_type=rt, metric=metric, interest_group=ig)
        # create some data
        ib1 = ImportBatchFactory.create(
            platform=platform1, organization=org1, report_type=rt, date="2023-01-01"
        )
        AccessLogFactory.create(import_batch=ib1, value=1, target=title, metric=metric)
        ib2 = ImportBatchFactory.create(
            platform=platform2, organization=org1, report_type=rt, date="2023-01-01"
        )
        AccessLogFactory.create(import_batch=ib2, value=2, target=title, metric=metric)
        # this one is on org2, so it should not overlap with the other two
        ib3 = ImportBatchFactory.create(
            platform=platform3, organization=org2, report_type=rt, date="2023-01-01"
        )
        AccessLogFactory.create(import_batch=ib3, value=5, target=title, metric=metric)
        create_platformtitle_links_from_accesslogs(AccessLog.objects.all())
        sync_interest_by_import_batches()
        assert interest_rt.accesslog_set.aggregate(Sum("value"))["value__sum"] == 8
        # the problem at hand only occurs when all organizations (id=-1) are requested
        resp = master_user_client.get(
            reverse("organization-all-platforms-overlap", args=["-1"]),
            {"start": start_date or "", "end": end_date or ""},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3, "3 records for 3 platforms"
        for rec in data:
            if rec["platform"] == platform3.pk:
                assert rec["overlap"] == 0, "platform 3 has no overlap"
                assert rec["overlap_interest"] == 0, "platform 3 has no overlap"
                assert rec["total_interest"] == 5, "platform 3 has no overlap"
            else:
                assert rec["overlap"] == 1, "both platforms share the same title"
                assert rec["overlap_interest"] in (1, 2)
                assert rec["total_interest"] == rec["overlap_interest"]

    @pytest.mark.parametrize(
        ["org_in_query", "org_has_config", "exp_value"],
        [
            (True, True, 1),  # org has two filters, value is 1
            (True, False, 9),  # org used default config with one filter, value is 9
            (False, True, 9),  # all orgs, global config is used, value is 9
            (False, False, 9),  # all orgs, global config is used, value is 9
            (True, None, 15),  # there is neither org nor global config, value is 15
        ],
    )
    def test_organization_all_platform_overlap_with_interest_config(
        self,
        master_user_client,
        real_world_data_with_interest_and_configs,
        org_in_query,
        org_has_config,
        exp_value,
    ):
        """
        This is a simplified test which checks that the interest config is applied correctly.
        It only uses the `total_interest` field to check the interest config is applied,
        but it should be enough.
        """
        org = real_world_data_with_interest_and_configs["organization"]
        if not org_has_config:
            real_world_data_with_interest_and_configs["org_interest_config"].delete()
            if org_has_config is None:
                real_world_data_with_interest_and_configs["global_interest_config"].delete()
        url = reverse("organization-all-platforms-overlap", args=[org.pk if org_in_query else -1])
        resp = master_user_client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1, "only 1 record - self overlap"
        assert data[0]["overlap"] == 0, "no overlap"
        assert (
            data[0]["total_interest"] == exp_value
        ), "the total interest should reflect the interest config"

    def test_organization_all_platform_overlap_all_orgs(
        self, master_user_client, accesslogs_with_interest, platforms
    ):
        organization = accesslogs_with_interest["organization"]
        platform = accesslogs_with_interest["platform"]
        titles = accesslogs_with_interest["titles"]

        # add some usage to platform 2 and title 1 to create overlap
        platform2 = [pl for pl in platforms.values() if pl.pk != platform.pk][0]
        rt = accesslogs_with_interest["rt"]
        ib = ImportBatchFullFactory.create(
            platform=platform2,
            organization=organization,
            date="2020-01-01",
            report_type=rt,
            create_accesslogs__titles=[titles[0]],
            create_accesslogs__metrics=[accesslogs_with_interest["metric"]],
            create_accesslogs__value=1,
        )
        sync_interest_by_import_batches(ImportBatch.objects.filter(pk=ib.pk))

        resp = master_user_client.get(reverse("organization-all-platforms-overlap", args=["-1"]))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2, "2 records for 2 platforms"
        for rec in data:
            assert rec["overlap"] == 1, "both platforms share the same title"
            if rec["platform"] == platform.pk:
                assert rec["overlap_interest"] == 3
                assert rec["total_interest"] == 15
            else:
                assert rec["overlap_interest"] == 1, "no interest on platform 2"
                assert rec["total_interest"] == 1, "no interest on platform 2"

    def test_platform_title_ids_list(self, master_user_client, accesslogs_with_interest):
        """
        Test the 'title-ids-list' custom action of platform viewset
        """
        url = reverse("platform-title-ids-list", args=[-1])
        resp = master_user_client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        platform = accesslogs_with_interest["platform"]
        assert str(platform.pk) in data
        # the last title is not linked to the platform
        assert set(data[str(platform.pk)]) == {
            title.pk for title in accesslogs_with_interest["titles"][:2]
        }

    def test_platform_title_ids_list_one_organization(
        self, master_user_client, accesslogs_with_interest
    ):
        """
        Test the 'title-ids-list' custom action of platform viewset
        """
        organization = accesslogs_with_interest["organization"]
        url = reverse("platform-title-ids-list", args=[organization.pk])
        resp = master_user_client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        platform = accesslogs_with_interest["platform"]
        assert str(platform.pk) in data
        # the last title is not linked to the platform
        assert set(data[str(platform.pk)]) == {
            title.pk for title in accesslogs_with_interest["titles"][:2]
        }

    def test_platform_title_ids_list_with_filter(
        self, master_user_client, accesslogs_with_interest
    ):
        """
        Test the 'title-ids-list' custom action of platform viewset with publication type filter
        """
        url = reverse("platform-title-ids-list", args=[-1])
        resp = master_user_client.get(url + "?pub_type=U")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 0

    @pytest.mark.clickhouse
    @pytest.mark.usefixtures("clickhouse_on_off")
    @pytest.mark.django_db(transaction=True)
    def test_platform_title_count(self, master_user_client, accesslogs_with_interest):
        """
        Test the 'title-count' custom action of platform viewset
        """
        url = reverse("platform-title-count", args=[-1])
        resp = master_user_client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        record = data[0]
        platform = accesslogs_with_interest["platform"]
        assert record["platform"] == platform.pk
        # the last title is not linked to the platform
        assert record["title_count"] == len(accesslogs_with_interest["titles"]) - 1

    def test_platform_title_count_detail(self, master_user_client, accesslogs_with_interest):
        """
        Test the 'title-count' detail custom action of platform viewset
        """
        platform = accesslogs_with_interest["platform"]
        url = reverse("platform-title-count", args=[-1, platform.pk])
        resp = master_user_client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert data["title_count"] == 2

    @pytest.mark.parametrize(["has_issn"], [(True,), (False,)])
    @pytest.mark.parametrize(["has_isbn"], [(True,), (False,)])
    @pytest.mark.parametrize(["has_eissn"], [(True,), (False,)])
    @pytest.mark.parametrize(["has_doi"], [(True,), (False,)])
    @pytest.mark.parametrize(
        ["matched_field"], [("name",), ("isbn",), ("issn",), ("eissn",), ("doi",), (None,)]
    )
    def test_platform_title_list_filtering_with_eissn(
        self,
        master_user_client,
        platform,
        organizations,
        has_issn,
        has_isbn,
        has_eissn,
        has_doi,
        matched_field,
    ):
        """
        Tests that looking for a title using different attributes works as expected.
        """
        base_attrs = {
            "name": "Foo Bar",
            "issn": "1234-4567",
            "eissn": "2345-6789",
            "isbn": "0801643317",
            "doi": "10.1007/9876.5432",
        }
        t = Title.objects.create(
            name=base_attrs["name"],
            issn=base_attrs["issn"] if has_issn else "",
            eissn=base_attrs["eissn"] if has_eissn else "",
            isbn=base_attrs["isbn"] if has_isbn else "",
            doi=base_attrs["doi"] if has_doi else "",
        )
        org = organizations["master"]
        # connect organization to platform - otherwise the user would get 404
        OrganizationPlatform.objects.create(organization=org, platform=platform)
        # and platform to title, otherwise the title will be missing from the results
        PlatformTitle.objects.create(
            platform=platform, title=t, organization=org, date="2020-01-01"
        )
        q = base_attrs[matched_field][-4:] if matched_field else ""  # end of matched string
        resp = master_user_client.get(
            reverse("platform-title-list", args=[org.pk, platform.pk]), {"q": q}
        )
        assert resp.status_code == 200
        data = resp.json()
        if matched_field is None or matched_field == "name" or locals()["has_" + matched_field]:
            # the matched field is actually filled in, so it should match
            assert len(data) == 1, f'the title should match "{q}"'
            assert data[0]["pk"] == t.pk
        else:
            assert len(data) == 0, f'nothing should match "{q}"'


@pytest.mark.django_db
class TestTitlesOnMultiplePlatforms:
    """
    Tests the `titles-on-multiple-platforms` view because it contains a raw SQL query and thus needs
    more attention.
    """

    @pytest.fixture
    def overlaping_data(self, interest_rt, users):
        """
        Creates 4 titles with some TR usage and corresponding interest. The titles are on multiple
        platforms and have YOP data.
        """
        org = OrganizationFactory()
        tr: ReportType = ReportTypeFactory(short_name="TR", dimensions=["Access_Type", "YOP"])
        yop_attr = tr.dim_name_to_dim_attr("YOP")
        at_attr = tr.dim_name_to_dim_attr("Access_Type")
        yop_dim = tr.dimension_by_attr_name(yop_attr)
        at_dim = tr.dimension_by_attr_name(at_attr)
        # add InterestDimensionValueMapping for Access_Type
        InterestDimensionValueMapping.objects.create(
            interest_rtdim=interest_rt.reporttypetodimension_set.get(dimension=at_dim),
            source_rtdim=tr.reporttypetodimension_set.get(dimension=at_dim),
            default_value="Free",  # what is not Controlled will be mapped to Free
            mapping={"Controlled": ["Controlled"]},
        )
        t1 = TitleFactory(pub_type="J", name="foo", issn="1234-5678", doi="", isbn="", eissn="")
        t2 = TitleFactory(pub_type="J", name="bar", eissn="2345-6789", doi="", isbn="", issn="")
        t3 = TitleFactory(pub_type="J", name="foobar", issn="1234-9876", doi="", isbn="", eissn="")
        t4 = TitleFactory(
            pub_type="B", name="bazooka", doi="10.1007/9876.5432", isbn="", eissn="", issn=""
        )
        p1, p2 = PlatformFactory.create_batch(2)
        ib1 = ImportBatchFactory(report_type=tr, organization=org, platform=p1)
        ib2 = ImportBatchFactory(report_type=tr, organization=org, platform=p2)
        metric = MetricFactory(short_name="Total_Item_Requests")
        yop_2010 = DimensionText.objects.create(text="2010", dimension=yop_dim)
        yop_2011 = DimensionText.objects.create(text="2011", dimension=yop_dim)
        at_controlled = DimensionText.objects.create(text="Controlled", dimension=at_dim)
        # define interest for the TR report type
        ReportInterestMetric.objects.create(
            report_type=tr,
            metric=metric,
            interest_group=InterestGroupFactory(
                short_name="interest1", position=1, implies_availability=True
            ),
        )
        # add tags to some of the titles
        # t1 - tag1, tag2, tag3
        # t2 - tag2
        # t4 - tag3
        tag1, tag2 = TagForTitleFactory.create_batch(2)
        tag3 = TagForTitleFactory(owner=users["admin2"], can_see=AccessibleBy.OWNER)
        tag1.tag(t1, users["admin1"])
        tag1.tag(t2, users["admin1"])
        tag2.tag(t1, users["admin1"])
        tag3.tag(t1, users["admin2"])
        tag3.tag(t4, users["admin2"])
        # t1 will have yop 2010 and 2011 and both platforms
        for ib_idx, ib in enumerate([ib1, ib2]):
            for yop_idx, yop in enumerate([yop_2010, yop_2011]):
                AccessLogFactory(
                    import_batch=ib,
                    target=t1,
                    value=(ib_idx + 2) * (yop_idx + 1),
                    metric=metric,
                    **{yop_attr: yop.pk, at_attr: at_controlled.pk},
                )
        # t2 will have yop 2011 and both platforms
        for ib_idx, ib in enumerate([ib1, ib2]):
            AccessLogFactory(
                import_batch=ib,
                target=t2,
                value=ib_idx + 3,
                metric=metric,
                **{yop_attr: yop_2011.pk, at_attr: at_controlled.pk},
            )
        # t3 will have only one platform
        AccessLogFactory(
            import_batch=ib,
            target=t3,
            value=5,
            metric=metric,
            **{at_attr: at_controlled.pk, yop_attr: yop_2010.pk},
        )
        # t4 will have both platforms and yop 2010 and 2011 but with No_License metric,
        # so it should be included, but not have YOP 2011
        no_license_metric = MetricFactory(short_name="No_License")
        for ib_idx, ib in enumerate([ib1, ib2]):
            AccessLogFactory(
                import_batch=ib,
                target=t4,
                value=(ib_idx + 1) * 7,
                metric=metric,
                **{yop_attr: yop_2010.pk, at_attr: at_controlled.pk},
            )
            AccessLogFactory(
                import_batch=ib,
                target=t4,
                value=(ib_idx + 1) * 11,
                metric=no_license_metric,
                **{yop_attr: yop_2011.pk, at_attr: at_controlled.pk},
            )
            # the following will not have Access_Type 'Controlled' and should not be included
            AccessLogFactory(
                import_batch=ib,
                target=t4,
                value=(ib_idx + 1) * 13,
                metric=metric,
                **{yop_attr: yop_2011.pk},
            )
        sync_interest_by_import_batches()
        create_platformtitle_links_from_accesslogs(AccessLog.objects.all())
        return {
            "org": org,
            "t1": t1,
            "t2": t2,
            "t3": t3,
            "t4": t4,
            "ib1": ib1,
            "ib2": ib2,
            "tr": tr,
            "metric": metric,
            "interest_rt": interest_rt,
            "tag1": tag1,
            "tag2": tag2,
            "tag3": tag3,
        }

    def test_titles_on_multiple_platforms_output_structure(self, admin_client, overlaping_data):
        """
        Tests that `titles-on-multiple-platforms` view returns correct data - both the correct
        list of titles and the correct YOPs for each title
        """
        org = overlaping_data["org"]
        t1 = overlaping_data["t1"]
        t2 = overlaping_data["t2"]
        t4 = overlaping_data["t4"]
        ib1 = overlaping_data["ib1"]
        ib2 = overlaping_data["ib2"]

        resp = admin_client.get(reverse("organization-titles-on-multiple-platforms", args=[org.pk]))
        assert resp.status_code == 200
        assert "results" in resp.json()
        data = resp.json()["results"]
        assert len(data) == 3
        for rec in data:
            if rec["pk"] == t1.pk:
                assert rec["yops"] == {
                    f"{ib1.platform_id}": {"min": 2010, "max": 2011},
                    f"{ib2.platform_id}": {"min": 2010, "max": 2011},
                }
                assert rec["total_interest"] == 2 + 3 + 4 + 6
            elif rec["pk"] == t2.pk:
                assert rec["yops"] == {
                    f"{ib1.platform_id}": {"min": 2011, "max": 2011},
                    f"{ib2.platform_id}": {"min": 2011, "max": 2011},
                }
                assert rec["total_interest"] == 3 + 4
            elif rec["pk"] == t4.pk:
                assert rec["yops"] == {
                    f"{ib1.platform_id}": {"min": 2010, "max": 2010},
                    f"{ib2.platform_id}": {"min": 2010, "max": 2010},
                }, "2011 should be ignored - no No_License metric and no Controlled access type"
                assert rec["total_interest"] == 7 + 14 + 13 + 26

    def test_titles_on_multiple_platforms_output_structure_with_org_config(
        self, admin_client, overlaping_data
    ):
        """
        Tests that `titles-on-multiple-platforms` view returns correct data interest
        in presence of an organization specific interest config.
        """
        org = overlaping_data["org"]
        t1 = overlaping_data["t1"]
        t2 = overlaping_data["t2"]
        t4 = overlaping_data["t4"]
        ib1 = overlaping_data["ib1"]
        ib2 = overlaping_data["ib2"]

        # create an organization specific interest config
        ic = InterestConfig.objects.create(
            organization=org, interest_profile=InterestProfile.objects.default()
        )
        df = DimensionFilter.objects.create(
            dimension=Dimension.objects.get(short_name="Access_Type"), values=["Controlled"]
        )
        InterestFilter.objects.create(interest_config=ic, filter=df)

        # test the API output
        resp = admin_client.get(reverse("organization-titles-on-multiple-platforms", args=[org.pk]))
        assert resp.status_code == 200
        assert "results" in resp.json()
        data = resp.json()["results"]
        assert len(data) == 3
        for rec in data:
            if rec["pk"] == t1.pk:
                assert rec["yops"] == {
                    f"{ib1.platform_id}": {"min": 2010, "max": 2011},
                    f"{ib2.platform_id}": {"min": 2010, "max": 2011},
                }
                assert rec["total_interest"] == 2 + 3 + 4 + 6
            elif rec["pk"] == t2.pk:
                assert rec["yops"] == {
                    f"{ib1.platform_id}": {"min": 2011, "max": 2011},
                    f"{ib2.platform_id}": {"min": 2011, "max": 2011},
                }
                assert rec["total_interest"] == 3 + 4
            elif rec["pk"] == t4.pk:
                assert rec["yops"] == {
                    f"{ib1.platform_id}": {"min": 2010, "max": 2010},
                    f"{ib2.platform_id}": {"min": 2010, "max": 2010},
                }, "2011 should be ignored - no No_License metric and no Controlled access type"
                assert (
                    rec["total_interest"] == 7 + 14
                ), "Access_Type != Controlled (13+26) should be ignored"

    @pytest.mark.parametrize(
        "order_by", ["total_interest", "name", "issn", "isbn", "doi", "platform_count"]
    )
    @pytest.mark.parametrize("desc", [True, False])
    def test_output_ordering(self, admin_client, overlaping_data, order_by, desc):
        """
        Tests that the output of `titles-on-multiple-platforms` view is ordered by total interest
        """
        org = overlaping_data["org"]

        resp = admin_client.get(
            reverse("organization-titles-on-multiple-platforms", args=[org.pk]),
            {"order_by": order_by, "desc": desc},
        )
        assert resp.status_code == 200
        data = resp.json()["results"]
        assert len(data) == 3
        if desc:
            data = list(reversed(data))
        assert data[0][order_by] <= data[1][order_by] <= data[2][order_by]

    @pytest.mark.parametrize(
        ["pub_type", "result"], [("J", ["t1", "t2"]), ("B", ["t4"]), ("N", [])]
    )
    def test_pub_type_filter(self, admin_client, overlaping_data, pub_type, result):
        """
        Tests that the pub_type filter works as expected
        """
        org = overlaping_data["org"]

        resp = admin_client.get(
            reverse("organization-titles-on-multiple-platforms", args=[org.pk]),
            {"pub_type": pub_type},
        )
        assert resp.status_code == 200
        data = resp.json()["results"]
        assert {rec["pk"] for rec in data} == {
            getattr(overlaping_data[title], "pk", None) for title in result
        }

    @pytest.mark.parametrize(
        ["tags", "result"],
        [
            (["tag1"], ["t1", "t2"]),
            (["tag2"], ["t1"]),
            (["tag1", "tag2"], ["t1", "t2"]),
            (["tag3"], []),  # admin1 does not have access to tag3
        ],
    )
    def test_tag_filter(self, admin_client, overlaping_data, tags, result):
        """
        Tests that the tag filter works as expected
        """
        org = overlaping_data["org"]

        resp = admin_client.get(
            reverse("organization-titles-on-multiple-platforms", args=[org.pk]),
            {"tags": ",".join(str(overlaping_data[tag].pk) for tag in tags)},
        )
        assert resp.status_code == 200
        data = resp.json()["results"]
        assert {rec["pk"] for rec in data} == {
            getattr(overlaping_data[title], "pk", None) for title in result
        }

    @pytest.mark.parametrize(
        ["q", "result"],
        [
            ("foo", ["t1"]),
            ("bar", ["t2"]),
            ("baz", ["t4"]),
            ("ba", ["t2", "t4"]),
            ("prase", []),
            ("123", ["t1"]),  # issn
            ("234", ["t1", "t2"]),  # issn and eissn
            ("9876", ["t4"]),  # isbn
            ("1007", ["t4"]),  # doi
            ("foo 1234", ["t1"]),  # name + issn
        ],
    )
    def test_search_filter(self, admin_client, overlaping_data, q, result):
        """
        Tests that the search filter works as expected
        """
        org = overlaping_data["org"]

        resp = admin_client.get(
            reverse("organization-titles-on-multiple-platforms", args=[org.pk]), {"q": q}
        )
        assert resp.status_code == 200
        data = resp.json()["results"]
        assert {rec["pk"] for rec in data} == {
            getattr(overlaping_data[title], "pk", None) for title in result
        }

    @pytest.mark.parametrize(
        ["pub_type", "q", "result"], [("B", "oo", ["t4"]), ("J", "oo", ["t1"])]
    )
    def test_filters_combined(self, admin_client, overlaping_data, pub_type, q, result):
        org = overlaping_data["org"]

        resp = admin_client.get(
            reverse("organization-titles-on-multiple-platforms", args=[org.pk]),
            {"pub_type": pub_type, "q": q},
        )
        assert resp.status_code == 200
        names = {overlaping_data[t].name for t in result}
        data = resp.json()["results"]
        assert {e["name"] for e in data} == names


@pytest.mark.django_db
class TestPlatformInterestAPI:
    @pytest.mark.parametrize("fmt", (None, "csv", "xlsx"))
    def test_platform_interest_list_empty(
        self, master_user_client, interest_rt, organizations, fmt
    ):
        url = reverse("platform-interest-list", args=(organizations["standalone"].pk,))
        if fmt:
            url += f"?format={fmt}"
        resp = master_user_client.get(url)
        assert resp.status_code == 200
        if fmt is None:
            assert resp.json() == []

    @pytest.mark.parametrize("fmt", (None, "csv", "xlsx"))
    def test_platform_interest_list_all_org_empty(self, master_user_client, interest_rt, fmt):
        url = reverse("platform-interest-list", args=(-1,))
        if fmt:
            url += f"?format={fmt}"
        resp = master_user_client.get(url)
        assert resp.status_code == 200
        if fmt is None:
            assert resp.json() == []

    @pytest.mark.parametrize(
        ["interest_filters", "exp_value"],
        [
            ({}, 15),
            ({"Access_Type": "Controlled"}, 9),
            ({"Access_Type": "Free"}, 6),
            ({"Access_Type": "Controlled", "Access_Method": "TDM"}, 8),
            ({"Access_Type": "Controlled", "Access_Method": "Normal"}, 1),
            ({"Access_Type": "Free", "Access_Method": "TDM"}, 4),
            ({"Access_Type": "Free", "Access_Method": "Normal"}, 2),
            ({"Access_Method": "TDM"}, 12),
            ({"Access_Method": "Normal"}, 3),
        ],
    )
    def test_platform_interest_list_real_world_data(
        self, master_user_client, interest_filters, exp_value, real_world_data_with_interest
    ):
        org = real_world_data_with_interest["organization"]
        tr = real_world_data_with_interest["tr"]
        interest_rt = real_world_data_with_interest["interest_rt"]
        assert tr.accesslog_set.count() == 4
        assert tr.accesslog_set.aggregate(Sum("value"))["value__sum"] == 15
        assert interest_rt.accesslog_set.count() == 4
        assert interest_rt.accesslog_set.aggregate(Sum("value"))["value__sum"] == 15
        # configure the interest
        ic = InterestConfig.objects.default()
        for dim_name, value in interest_filters.items():
            df = DimensionFilter.objects.create(
                dimension=Dimension.objects.get(short_name=dim_name), values=[value]
            )
            InterestFilter.objects.create(interest_config=ic, filter=df)
        assert ic.interest_filters.count() == len(interest_filters)
        # check the API
        url = reverse("platform-interest-list", args=(org.pk,))
        resp = master_user_client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["full_text"] == exp_value

    @pytest.mark.parametrize(
        ["org_in_query", "org_has_config", "exp_value"],
        [
            (True, True, 1),  # org has two filters, value is 1
            (True, False, 9),  # org used default config with one filter, value is 9
            (False, True, 9),  # all orgs, global config is used, value is 9
            (False, False, 9),  # all orgs, global config is used, value is 9
            (True, None, 15),  # there is neither org nor global config, value is 15
        ],
    )
    def test_platform_interest_list_real_world_data_org_config(
        self,
        master_user_client,
        real_world_data_with_interest_and_configs,
        org_in_query,
        org_has_config,
        exp_value,
    ):
        """
        Test that the interest list API returns the correct value for the given organization
        depending on the presence of a organization specific interest config.
        """
        org = real_world_data_with_interest_and_configs["organization"]
        tr = real_world_data_with_interest_and_configs["tr"]
        interest_rt = real_world_data_with_interest_and_configs["interest_rt"]
        if not org_has_config:
            real_world_data_with_interest_and_configs["org_interest_config"].delete()
            if org_has_config is None:
                real_world_data_with_interest_and_configs["global_interest_config"].delete()

        assert tr.accesslog_set.count() == 4
        assert tr.accesslog_set.aggregate(Sum("value"))["value__sum"] == 15
        assert interest_rt.accesslog_set.count() == 4
        assert interest_rt.accesslog_set.aggregate(Sum("value"))["value__sum"] == 15
        # check the API
        url = reverse("platform-interest-list", args=(org.pk if org_in_query else -1,))
        resp = master_user_client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["full_text"] == exp_value


@pytest.mark.django_db
@pytest.mark.usefixtures("basic1")
class TestAllPlatformsAPI:
    @pytest.mark.parametrize("public_only", [True, False])
    def test_all_platform_public_only_param(self, clients, data_sources, public_only):
        plat_source_type_not_org = PlatformFactory.create(source=data_sources["api"])
        plat_source_type_org = PlatformFactory.create(source=data_sources["branch"])
        resp = clients["admin1"].get(
            reverse("all-platforms-list", args=[-1]), {"public_only": str(public_only)}
        )
        assert resp.status_code == 200
        resp_pks = {plat["pk"] for plat in resp.data}
        assert plat_source_type_not_org.pk in resp_pks
        if public_only:
            assert plat_source_type_org.pk not in resp_pks
        else:
            assert plat_source_type_org.pk in resp_pks

    @pytest.mark.parametrize(
        ["client", "status", "organization", "available"],
        [
            ["unauthenticated", (401, 403), "empty", None],
            ["master_admin", (200,), "empty", ["brain", "empty", "master", "shared"]],
            ["master_user", (200,), "empty", ["brain", "empty", "master", "shared"]],
            ["admin1", (200,), "root", ["brain", "master", "empty", "root", "shared"]],
            ["admin2", (200,), "master", ["brain", "master", "empty", "shared"]],
            ["user1", (200,), "branch", ["brain", "master", "empty", "branch", "shared"]],
            ["user2", (200,), "standalone", ["brain", "master", "empty", "standalone", "shared"]],
        ],
        ids=[
            "unauthenticated-empty",
            "master_admin-empty",
            "master_user-empty",
            "admin1-root",
            "admin2-master",
            "user1-branch",
            "user2-standalone",
        ],
    )
    def test_all_platform_list(
        self,
        client,
        status,
        organization,
        available,
        clients,
        platforms,
        organizations,
        parser_definitions,
    ):
        resp = clients[client].get(
            reverse("all-platforms-list", args=[organizations[organization].pk])
        )
        assert resp.status_code in status
        if available is not None:
            resp_data = resp.json()
            assert len(resp_data) == len(available)
            for data, platform in zip(resp_data, [platforms[e] for e in sorted(available)]):
                assert data["pk"] == platform.pk
                if platform.name == "brain":
                    assert data["has_raw_parser"] is True
                else:
                    assert data["has_raw_parser"] is False

    @pytest.mark.parametrize(
        ["client", "organization", "available"],
        [
            ["unauthenticated", "empty", set()],
            ["master_admin", "empty", {"brain", "empty", "master", "shared"}],
            ["master_user", "empty", {"brain", "empty", "master", "shared"}],
            ["admin1", "root", {"brain", "master", "empty", "root", "shared"}],
            ["admin2", "master", {"brain", "master", "empty", "shared"}],
            ["user1", "branch", {"brain", "master", "empty", "branch", "shared"}],
            ["user2", "standalone", {"brain", "master", "empty", "standalone", "shared"}],
        ],
        ids=[
            "unauthenticated-empty",
            "master_admin-empty",
            "master_user-empty",
            "admin1-root",
            "admin2-master",
            "user1-branch",
            "user2-standalone",
        ],
    )
    def test_all_platform_detail(
        self, client, organization, available, clients, platforms, organizations
    ):
        for platform in platforms.values():
            resp = clients[client].get(
                reverse("all-platforms-detail", args=[organizations[organization].pk, platform.pk])
            )

            if platform.short_name in available:
                assert resp.status_code == 200
            else:
                assert resp.status_code in (401, 403, 404)

    @pytest.mark.parametrize(
        ["client", "status", "available"],
        [
            ["unauthenticated", (401, 403), None],
            [
                "master_admin",
                (200,),
                ["brain", "empty", "master", "shared", "root", "branch", "standalone"],
            ],
            [
                "master_user",
                (200,),
                ["brain", "empty", "master", "shared", "root", "branch", "standalone"],
            ],
            # root org has access to branch org
            ["admin1", (200,), ["brain", "master", "empty", "root", "shared", "branch"]],
            ["admin2", (200,), ["brain", "master", "empty", "shared", "standalone"]],
            ["user1", (200,), ["brain", "master", "empty", "branch", "shared"]],
            ["user2", (200,), ["brain", "master", "empty", "standalone", "shared"]],
        ],
        ids=[
            "unauthenticated-empty",
            "master_admin-empty",
            "master_user-empty",
            "admin1-root",
            "admin2-master",
            "user1-branch",
            "user2-standalone",
        ],
    )
    def test_all_platform_list_all_organizations(
        self, clients, platforms, client, status, available
    ):
        """
        Test that the all-platforms endpoint works with -1 as organization id, that is when
        all organizations are requested.
        """

        resp = clients[client].get(reverse("all-platforms-list", args=[-1]))
        assert resp.status_code in status
        if available is not None:
            assert {e["pk"] for e in resp.json()} == {platforms[e].pk for e in available}

    def test_all_platforms_detail_report_types(self, basic1, report_type_nd, settings):
        """
        Test that the all-platforms endpoint returns all report types that are not created by other
        organizations.
        """
        # prepare data
        client = basic1["clients"]["admin2"]
        organization = basic1["organizations"]["standalone"]  # admin2 is admin of standalone
        platform = basic1["platforms"]["shared"]
        assert ReportType.objects.count() == 0, "make sure no reports are created upfront"
        kb_source = DataSourceFactory.create()
        other_org = basic1["organizations"]["branch"]

        # create some report types
        rt_counter = report_type_nd(0, short_name="counter")
        rt_counter_no_interest = report_type_nd(0, short_name="counter no interest")
        rt_noncounter = report_type_nd(0, short_name="noncounter")
        # private RTs are not used in the wild now, but I am adding them to the test
        # to make sure that they would be handled correctly
        rt_organization = report_type_nd(
            0, short_name="organization", source=organization.private_data_source
        )
        rt_other_org = report_type_nd(
            0, short_name="other org", source=other_org.private_data_source
        )
        rt_kb = report_type_nd(0, short_name="kb", source=kb_source)

        # create CounterReportType which marks the report as COUNTER report
        CounterReportType.objects.create(
            code="test", name="test", report_type=rt_counter, counter_version=5
        )
        CounterReportType.objects.create(
            code="test2", name="test 2", report_type=rt_counter_no_interest, counter_version=5
        )
        # the test itself
        resp = client.get(
            reverse("all-platforms-get-report-types", args=(organization.pk, platform.pk))
        )
        assert resp.status_code == 200
        data = resp.json()
        assert {rec["pk"] for rec in data} == {
            rt_counter.pk,
            rt_counter_no_interest.pk,
            rt_noncounter.pk,
            rt_organization.pk,  # visible - source is the same organization
            rt_kb.pk,  # visible - source is knowledge base
        }, "5 report types should be visible"
        assert rt_other_org.pk not in {rec["pk"] for rec in data}, "other org should not be visible"

    @pytest.mark.parametrize(
        ["organization", "record_count"], [("branch", 1), ("standalone", 1), (None, 2)]
    )
    def test_use_cases(
        self,
        basic1,
        harvests,
        clients,
        platforms,
        organizations,
        credentials,
        counter_report_types,
        organization,
        record_count,
    ):
        # Some success comes from harvests fixture (pr)
        # and the second is created here (br1)
        FetchAttemptFactory(
            credentials=credentials["standalone_br1_jr1"],
            counter_report=counter_report_types["br1"],
            status=AttemptStatus.SUCCESS,
        )

        resp = clients["su"].get(
            reverse(
                "all-platforms-use-cases",
                args=[organizations[organization].pk if organization else -1],
            )
        )
        assert resp.status_code == 200
        assert len(resp.data) == record_count
        for rec in resp.data:
            assert rec.keys() == {
                "url",
                "organization",
                "platform",
                "counter_version",
                "counter_report",
                "latest",
                "count",
            }


@pytest.mark.django_db
@pytest.mark.usefixtures("basic1")
class TestGlobalPlatformsAPI:
    @pytest.mark.parametrize(
        ["client", "status", "available"],
        [
            ["unauthenticated", (401, 403), None],
            [
                "master_admin",
                (200,),
                {"brain", "master", "empty", "root", "shared", "standalone", "branch"},
            ],
            [
                "master_user",
                (200,),
                {"brain", "master", "empty", "root", "shared", "standalone", "branch"},
            ],
            ["admin1", (200,), {"brain", "master", "empty", "root", "branch", "shared"}],
            ["admin2", (200,), {"brain", "master", "empty", "shared", "standalone"}],
            ["user1", (200,), {"brain", "master", "empty", "branch", "shared"}],
            ["user2", (200,), {"brain", "master", "empty", "standalone", "shared"}],
        ],
        ids=[
            "unauthenticated",
            "master_admin",
            "master_user",
            "admin1",
            "admin2",
            "user1",
            "user2",
        ],
    )
    def test_all_platform_list(self, client, status, available, clients, platforms, organizations):
        resp = clients[client].get(reverse("global-platforms-list"))
        assert resp.status_code in status
        if available is not None:
            assert {e["pk"] for e in resp.json()} == {platforms[e].pk for e in available}

    @pytest.mark.parametrize(
        ["org_name", "expected_platforms"],
        [
            ["root", ["standalone"]],  # explicitly connected
            ["master", []],  # not connected
            ["standalone", ["standalone"]],  # connected by sushi in the credentials fixture
            ["branch", ["branch"]],  # connected by sushi in the credentials fixture
        ],
    )
    def test_all_platform_list_with_apikey(
        self, client, platforms, organizations, org_name, expected_platforms, credentials
    ):
        OrganizationPlatform.objects.create(
            organization=(organizations["root"]), platform=platforms["standalone"]
        )
        org = organizations[org_name]
        api_key, key_val = OrganizationAPIKey.objects.create_key(organization=org, name="test")
        resp = client.get(reverse("global-platforms-list"), HTTP_AUTHORIZATION=f"Api-Key {key_val}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == len(expected_platforms)
        visible_pks = {rec["pk"] for rec in data}
        expected_pks = {platforms[name].pk for name in expected_platforms}
        assert visible_pks == expected_pks

    @pytest.mark.parametrize(
        ["client", "available"],
        [
            ["unauthenticated", set()],
            [
                "master_admin",
                {"brain", "master", "empty", "root", "shared", "standalone", "branch"},
            ],
            ["master_user", {"brain", "master", "empty", "root", "shared", "standalone", "branch"}],
            ["admin1", {"brain", "master", "empty", "root", "branch", "shared"}],
            ["admin2", {"brain", "master", "empty", "shared", "standalone"}],
            ["user1", {"brain", "master", "empty", "branch", "shared"}],
            ["user2", {"brain", "master", "empty", "standalone", "shared"}],
        ],
        ids=[
            "unauthenticated",
            "master_admin",
            "master_user",
            "admin1",
            "admin2",
            "user1",
            "user2",
        ],
    )
    def test_all_platform_detail(self, client, available, clients, platforms, organizations):
        for platform in platforms.values():
            resp = clients[client].get(reverse("global-platforms-detail", args=[platform.pk]))

            if platform.short_name in available:
                assert resp.status_code == 200
            else:
                assert resp.status_code in (401, 403, 404)

    def test_pk_list_filter(self, admin_client, platforms):
        pks = [pl.pk for pl in platforms.values()][:2]
        pks_str = ",".join(map(str, pks))
        resp = admin_client.get(reverse("global-platforms-list") + f"?pks={pks_str}")
        assert resp.status_code == 200
        data = {rec["pk"] for rec in resp.json()}
        assert len(data) == len(pks)
        assert data == set(pks)


@pytest.fixture
def accesslogs_with_interest(organizations, platforms, titles, report_type_nd, interest_rt):
    organization = organizations["root"]
    platform = platforms["root"]
    rt = report_type_nd(0)
    ig = InterestGroupFactory(short_name="interest1", position=1, implies_availability=True)
    metric = Metric.objects.create(short_name="m1", name="Metric1")
    ReportInterestMetric.objects.create(report_type=rt, metric=metric, interest_group=ig)
    import_batch = ImportBatchFactory(platform=platform, organization=organization, report_type=rt)
    accesslog_basics = {
        "report_type": rt,
        "metric": metric,
        "platform": platform,
        "import_batch": import_batch,
    }
    accesslogs = [
        AccessLog.objects.create(
            target=titles[0],
            value=1,
            date="2019-01-01",
            organization=organization,
            **accesslog_basics,
        ),
        AccessLog.objects.create(
            target=titles[0],
            value=2,
            date="2019-02-01",
            organization=organization,
            **accesslog_basics,
        ),
        AccessLog.objects.create(
            target=titles[1],
            value=4,
            date="2019-02-01",
            organization=organization,
            **accesslog_basics,
        ),
        AccessLog.objects.create(
            target=titles[0],
            value=8,
            date="2019-02-01",
            organization=organizations["master"],
            **accesslog_basics,
        ),
    ]
    create_platformtitle_links_from_accesslogs(accesslogs)
    sync_interest_by_import_batches()
    return {
        key: val
        for key, val in locals().items()
        if key
        in ("accesslogs", "titles", "organization", "platform", "import_batch", "metric", "rt")
    }


@pytest.mark.clickhouse
@pytest.mark.usefixtures("clickhouse_on_off")
@pytest.mark.django_db(transaction=True)
class TestTopTitleInterestViewSet:
    def test_all_organizations(self, accesslogs_with_interest, master_user_client):
        titles = accesslogs_with_interest["titles"]
        resp = master_user_client.get(
            reverse("top-title-interest-list", args=["-1"]), {"order_by": "interest1"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2, "we have two titles"
        assert data[0]["isbn"] == titles[0].isbn
        assert data[0]["name"] == titles[0].name
        assert data[0]["interests"]["interest1"] == 11  # 8 + 2 + 1
        assert data[1]["isbn"] == titles[1].isbn
        assert data[1]["name"] == titles[1].name
        assert data[1]["interests"]["interest1"] == 4  # 4

    def test_one_organization(self, accesslogs_with_interest, master_user_client):
        organization = accesslogs_with_interest["organization"]
        titles = accesslogs_with_interest["titles"]
        resp = master_user_client.get(
            reverse("top-title-interest-list", args=[organization.pk]), {"order_by": "interest1"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2, "we have two titles"
        assert data[0]["isbn"] == titles[1].isbn
        assert data[0]["name"] == titles[1].name
        assert data[0]["interests"]["interest1"] == 4  # 4
        assert data[1]["isbn"] == titles[0].isbn
        assert data[1]["interests"]["interest1"] == 3  # 2 + 1

    def test_all_organizations_date_filter(self, accesslogs_with_interest, master_user_client):
        titles = accesslogs_with_interest["titles"]
        resp = master_user_client.get(
            reverse("top-title-interest-list", args=["-1"]),
            {"order_by": "interest1", "start": "2019-02"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2, "we have two titles"
        assert data[0]["isbn"] == titles[0].isbn
        assert data[0]["name"] == titles[0].name
        assert data[0]["interests"]["interest1"] == 10  # 8 + 2
        assert data[1]["isbn"] == titles[1].isbn
        assert data[1]["name"] == titles[1].name
        assert data[1]["interests"]["interest1"] == 4  # 4

    def test_all_organizations_pub_type_filter(self, accesslogs_with_interest, master_user_client):
        titles = accesslogs_with_interest["titles"]
        resp = master_user_client.get(
            reverse("top-title-interest-list", args=["-1"]),
            {"order_by": "interest1", "pub_type": "J"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1, "we have one title with type J"
        assert data[0]["issn"] == titles[1].issn
        assert data[0]["name"] == titles[1].name
        assert data[0]["interests"]["interest1"] == 4  # 4

    @pytest.mark.parametrize(
        ["org_in_query", "org_has_config", "exp_value"],
        [
            (True, True, 1),  # org has two filters, value is 1
            (True, False, 9),  # org used default config with one filter, value is 9
            (False, True, 9),  # all orgs, global config is used, value is 9
            (False, False, 9),  # all orgs, global config is used, value is 9
            (True, None, 15),  # there is neither org nor global config, value is 15
        ],
    )
    def test_all_titles_interest_with_interest_config(
        self,
        master_user_client,
        real_world_data_with_interest_and_configs,
        org_in_query,
        org_has_config,
        exp_value,
    ):
        org = real_world_data_with_interest_and_configs["organization"]
        if not org_has_config:
            real_world_data_with_interest_and_configs["org_interest_config"].delete()
            if org_has_config is None:
                real_world_data_with_interest_and_configs["global_interest_config"].delete()
        url = reverse("top-title-interest-list", args=[org.pk if org_in_query else -1])
        resp = master_user_client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1, "we have one title"
        assert data[0]["interests"]["full_text"] == exp_value

    def test_interest_order_by_nonexistent_interest_type(
        self, master_user_client, accesslogs_with_interest
    ):
        resp = master_user_client.get(
            reverse("top-title-interest-list", args=["-1"]), {"order_by": "nonexistent"}
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == 'Interest type "nonexistent" does not exist'


@pytest.mark.django_db
class TestTitleInterestBrief:
    def test_list(self, master_user_client, accesslogs_with_interest):
        resp = master_user_client.get(reverse("title-interest-brief-list", args=[-1]))
        assert resp.status_code == 200
        data = resp.json()
        # last title is not in the response because it has no interest
        titles = accesslogs_with_interest["titles"][:2]
        assert len(data) == len(titles)
        for rec in data:
            if rec["target_id"] == titles[0].pk:
                assert rec["interest"] == 11  # 1 + 2 + 8
            elif rec["target_id"] == titles[1].pk:
                assert rec["interest"] == 4
            else:
                assert False, "such record should not exist"

    def test_list_one_org(self, master_user_client, accesslogs_with_interest):
        organization = accesslogs_with_interest["organization"]
        resp = master_user_client.get(reverse("title-interest-brief-list", args=[organization.pk]))
        assert resp.status_code == 200
        data = resp.json()
        # last title is not in the response because it has no interest
        titles = accesslogs_with_interest["titles"][:2]
        assert len(data) == len(titles)
        for rec in data:
            if rec["target_id"] == titles[0].pk:
                assert rec["interest"] == 3  # 1 + 2
            elif rec["target_id"] == titles[1].pk:
                assert rec["interest"] == 4
            else:
                assert False, "such record should not exist"

    def test_detail(self, master_user_client, accesslogs_with_interest):
        organization = accesslogs_with_interest["organization"]
        title = accesslogs_with_interest["titles"][0]
        resp = master_user_client.get(
            reverse("title-interest-brief-detail", args=[organization.pk, title.pk])
        )
        assert resp.status_code == 200
        data = resp.json()
        assert type(data) is dict  # noqa E721 - make sure it is a list, not subtype
        assert len(data) == 1, 'just "interest" key'
        assert data["interest"] == 3  # 1 + 2

    @pytest.mark.parametrize(
        ["org_in_query", "org_has_config", "exp_value"],
        [
            (True, True, 1),  # org has two filters, value is 1
            (True, False, 9),  # org used default config with one filter, value is 9
            (False, True, 9),  # all orgs, global config is used, value is 9
            (False, False, 9),  # all orgs, global config is used, value is 9
            (True, None, 15),  # there is neither org nor global config, value is 15
        ],
    )
    def test_list_with_interest_config(
        self,
        master_user_client,
        real_world_data_with_interest_and_configs,
        org_in_query,
        org_has_config,
        exp_value,
    ):
        """
        Test that the interest list API returns the correct value for the given organization
        depending on the presence of a organization specific interest config.
        """
        org = real_world_data_with_interest_and_configs["organization"]
        if not org_has_config:
            real_world_data_with_interest_and_configs["org_interest_config"].delete()
            if org_has_config is None:
                real_world_data_with_interest_and_configs["global_interest_config"].delete()
        # check the API
        url = reverse("title-interest-brief-list", args=(org.pk if org_in_query else -1,))
        resp = master_user_client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1, "There is only one title"
        assert data[0]["interest"] == exp_value


@pytest.mark.django_db()
class TestTitleInterestViewSet:
    @pytest.mark.parametrize("column", ["name", "pub_type", "issn", "interest1"])
    @pytest.mark.parametrize("desc", ["true", "false", "undefined"])
    def test_all_titles_order_by(self, accesslogs_with_interest, master_user_client, column, desc):
        titles = accesslogs_with_interest["titles"]
        resp = master_user_client.get(
            reverse("title-interest-list", args=["-1"]), {"order_by": column, "desc": desc}
        )
        assert resp.status_code == 200
        data = resp.json()["results"]
        assert len(data) == len(titles)
        # to ensure that the sorting is always the same (which is especially important with
        # pagination), we should mix the pk into the sorting on the backend. This is why we use the
        # pk below as a secondary sorting key as well
        if column == "interest1":
            values = [(rec["interests"][column], rec["pk"]) for rec in data]
        else:
            values = [(rec[column], rec["pk"]) for rec in data]
        resorted = sorted(values, reverse=desc == "true")
        assert values == resorted

    @pytest.mark.parametrize(
        ["org_in_query", "org_has_config", "exp_value"],
        [
            (True, True, 1),  # org has two filters, value is 1
            (True, False, 9),  # org used default config with one filter, value is 9
            (False, True, 9),  # all orgs, global config is used, value is 9
            (False, False, 9),  # all orgs, global config is used, value is 9
            (True, None, 15),  # there is neither org nor global config, value is 15
        ],
    )
    def test_all_titles_with_interest_config(
        self,
        master_user_client,
        real_world_data_with_interest_and_configs,
        org_in_query,
        org_has_config,
        exp_value,
    ):
        org = real_world_data_with_interest_and_configs["organization"]
        if not org_has_config:
            real_world_data_with_interest_and_configs["org_interest_config"].delete()
            if org_has_config is None:
                real_world_data_with_interest_and_configs["global_interest_config"].delete()
        url = reverse("title-interest-list", args=(org.pk if org_in_query else -1,))
        resp = master_user_client.get(url)
        assert resp.status_code == 200
        data = resp.json()["results"]
        assert len(data) == 1, "There is only one title"
        assert data[0]["interests"]["full_text"] == exp_value


@pytest.mark.django_db
class TestItemViewSet:
    def test_item_list_no_filter(
        self, master_user_client, interest_rt, django_assert_max_num_queries
    ):
        items = ItemFactory.create_batch(30)
        with django_assert_max_num_queries(25):
            resp = master_user_client.get(reverse("global-items-list"))
        assert resp.status_code == 200
        data = resp.json()["results"]
        assert len(data) == len(items)
        item_ids = {item.pk for item in items}
        for rec in data:
            assert rec["pk"] in item_ids
            item = next(item for item in items if item.pk == rec["pk"])
            assert rec["pk"] == item.pk
            assert rec["doi"] == item.doi
            assert rec["name"] == item.name
            assert rec["issn"] == item.issn
            assert rec["eissn"] == item.eissn
            assert rec["isbn"] == item.isbn
            assert "interests" in rec
            assert "authors" in rec

    @pytest.mark.parametrize(["page_size", "expected_count"], [(5, 5), (15, 10)])
    def test_item_list_no_filter_pagination(
        self, master_user_client, interest_rt, page_size, expected_count
    ):
        items = ItemFactory.create_batch(10)
        resp = master_user_client.get(reverse("global-items-list"), {"page_size": page_size})
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == len(items)
        assert len(data["results"]) == expected_count
        item_ids = {item.pk for item in items}
        for rec in data["results"]:
            assert rec["pk"] in item_ids

    @pytest.mark.parametrize(
        ["order_by", "desc"],
        [("name", "true"), ("name", "false"), ("doi", "true"), ("doi", "false")],
    )
    def test_item_list_no_filter_pagination_order_by(
        self, master_user_client, interest_rt, order_by, desc
    ):
        items = ItemFactory.create_batch(10)
        resp = master_user_client.get(
            reverse("global-items-list"), {"order_by": order_by, "desc": desc}
        )
        assert resp.status_code == 200
        data = resp.json()["results"]
        assert len(data) == len(items)
        item_ids = {item.pk for item in items}
        for i, rec in enumerate(data):
            assert rec["pk"] in item_ids
            if i > 0:
                if desc == "true":
                    assert rec[order_by] <= data[i - 1][order_by]
                else:
                    assert rec[order_by] >= data[i - 1][order_by]

    @pytest.mark.parametrize(
        ["date_from", "date_to", "exp_count"],
        [
            ("2019-01-01", "2020-01-01", 0),
            ("2020-01-01", "2021-01-01", 3),
            ("2020-01-01", "", 10),
            ("", "2020-01-01", 0),
            ("", "", 10),
            ("", "2021-01-01", 3),
        ],
    )
    def test_item_list_date_filter(
        self, master_user_client, interest_rt, date_from, date_to, exp_count
    ):
        ItemFactory.create_batch(3, usage__date="2020-06-01")
        ItemFactory.create_batch(7, usage__date="2021-06-01")
        resp = master_user_client.get(
            reverse("global-items-list"), {"start": date_from, "end": date_to}
        )
        assert resp.status_code == 200
        data = resp.json()["results"]
        assert len(data) == exp_count

    def test_item_list_for_organization(self, master_user_client, interest_rt):
        org = OrganizationFactory()
        items = ItemFactory.create_batch(10, usage__organization=org)
        # create some extra items that should not be in the response
        ItemFactory.create_batch(7)
        resp = master_user_client.get(reverse("organization-item-list", args=[org.pk]))
        assert resp.status_code == 200
        data = resp.json()["results"]
        assert len(data) == len(items)
        item_ids = {item.pk for item in items}
        for rec in data:
            assert rec["pk"] in item_ids

    def test_item_list_for_organization_all_orgs(self, master_user_client, interest_rt):
        org = OrganizationFactory()
        items = ItemFactory.create_batch(10, usage__organization=org)
        # create some extra items that should not be in the response
        extra_items = ItemFactory.create_batch(7)
        resp = master_user_client.get(reverse("organization-item-list", args=[-1]))
        assert resp.status_code == 200
        data = resp.json()["results"]
        assert len(data) == len(items) + len(extra_items)
        item_ids = {item.pk for item in items}
        extra_item_ids = {item.pk for item in extra_items}
        for rec in data:
            assert rec["pk"] in item_ids or rec["pk"] in extra_item_ids

    def test_item_list_for_org_platform(self, master_user_client, interest_rt):
        pl = PlatformFactory()
        org = OrganizationFactory()
        items = ItemFactory.create_batch(10, usage__platform=pl, usage__organization=org)
        # create some extra items that should not be in the response
        ItemFactory.create_batch(3, usage__platform=pl)
        ItemFactory.create_batch(4, usage__organization=org)
        resp = master_user_client.get(
            reverse("organization-platform-items-list", args=[org.pk, pl.pk])
        )
        assert resp.status_code == 200
        data = resp.json()["results"]
        assert len(data) == len(items)
        item_ids = {item.pk for item in items}
        for rec in data:
            assert rec["pk"] in item_ids

    @pytest.mark.parametrize(
        ["org_in_query", "org_has_config", "exp_value"],
        [
            (True, True, 1),  # org has two filters, value is 1
            (True, False, 9),  # org used default config with one filter, value is 9
            (False, True, 9),  # all orgs, global config is used, value is 9
            (False, False, 9),  # all orgs, global config is used, value is 9
            (True, None, 15),  # there is neither org nor global config, value is 15
        ],
    )
    def test_item_list_with_interest_config(
        self,
        master_user_client,
        real_world_item_data_with_interest_and_configs,
        org_in_query,
        org_has_config,
        exp_value,
    ):
        org = real_world_item_data_with_interest_and_configs["organization"]
        if not org_has_config:
            real_world_item_data_with_interest_and_configs["org_interest_config"].delete()
            if org_has_config is None:
                real_world_item_data_with_interest_and_configs["global_interest_config"].delete()
        url = reverse("organization-item-list", args=[org.pk if org_in_query else -1])
        resp = master_user_client.get(url)
        assert resp.status_code == 200
        data = resp.json()["results"]
        assert len(data) == 1, "There is only one item"
        assert data[0]["interests"]["full_text"] == exp_value

    def test_item_list_for_org_platform_title(self, master_user_client, interest_rt):
        pl = PlatformFactory()
        org = OrganizationFactory()
        title = TitleFactory()
        items = ItemFactory.create_batch(
            10, usage__platform=pl, usage__organization=org, usage__title=title
        )
        # create some extra items that should not be in the response
        ItemFactory.create_batch(3, usage__platform=pl)
        ItemFactory.create_batch(4, usage__organization=org)
        ItemFactory.create_batch(5, usage__title=title)
        resp = master_user_client.get(
            reverse("organization-platform-title-items-list", args=[org.pk, pl.pk, title.pk])
        )
        assert resp.status_code == 200
        data = resp.json()["results"]
        assert len(data) == len(items)
        item_ids = {item.pk for item in items}
        for rec in data:
            assert rec["pk"] in item_ids

    def test_item_list_for_org_title(self, master_user_client, interest_rt):
        org = OrganizationFactory()
        title = TitleFactory()
        items = ItemFactory.create_batch(
            10, usage=True, usage__organization=org, usage__title=title
        )
        # create some extra items that should not be in the response
        ItemFactory.create_batch(4, usage__organization=org)
        ItemFactory.create_batch(5, usage__title=title)
        resp = master_user_client.get(
            reverse("organization-title-items-list", args=[org.pk, title.pk])
        )
        assert resp.status_code == 200
        data = resp.json()["results"]
        assert len(data) == len(items)
        item_ids = {item.pk for item in items}
        for rec in data:
            assert rec["pk"] in item_ids

    def test_item_detail(self, master_user_client, interest_rt):
        item = ItemFactory()
        resp = master_user_client.get(reverse("global-items-detail", args=[item.pk]))
        assert resp.status_code == 200
        data = resp.json()
        assert data["pk"] == item.pk
        assert data["doi"] == item.doi
        assert data["name"] == item.name
        assert data["issn"] == item.issn
        assert data["eissn"] == item.eissn
        assert data["isbn"] == item.isbn
        assert "interests" in data
        assert "authors" in data

    @pytest.mark.parametrize(["pub_type", "exp_count"], [("J", 3), ("B", 7), ("", 10), ("X", 0)])
    def test_item_list_filter_by_pub_type(
        self, master_user_client, interest_rt, pub_type, exp_count
    ):
        ItemFactory.create_batch(3, pub_type="J")
        ItemFactory.create_batch(7, pub_type="B")
        resp = master_user_client.get(reverse("global-items-list"), {"pub_type": pub_type})
        assert resp.status_code == 200
        data = resp.json()["results"]
        assert len(data) == exp_count
        if pub_type:
            assert all(rec["pub_type"] == pub_type for rec in data)
