import uuid
from unittest import mock

import pytest
from api.models import OrganizationAPIKey
from core.models import DataSource, Identity
from core.tests.conftest import authenticated_client  # noqa - fixtures
from core.tests.conftest import (  # noqa - fixtures
    authentication_headers,
    invalid_identity,
    master_user_client,
    master_user_identity,
    valid_identity,
)
from django.urls import reverse
from logs.logic.data_import import create_platformtitle_links_from_accesslogs
from logs.logic.materialized_interest import sync_interest_by_import_batches
from logs.models import (
    AccessLog,
    ImportBatch,
    InterestGroup,
    Metric,
    OrganizationPlatform,
    ReportInterestMetric,
    ReportType,
)
from logs.tests.conftest import report_type_nd  # noqa - fixture
from organizations.models import UserOrganization
from publications.models import Platform, PlatformInterestReport, PlatformTitle, Title
from sushi.models import AttemptStatus, CounterReportType, SushiCredentials

from test_fixtures.entities.fetchattempts import FetchAttemptFactory
from test_fixtures.entities.logs import ImportBatchFullFactory
from test_fixtures.entities.platforms import PlatformFactory
from test_fixtures.scenarios.basic import *  # noqa - fixtures


class MockTask:
    def __init__(self):
        self.id = uuid.uuid4()


@pytest.mark.django_db
class TestPlatformAPI:
    def test_unauthorized_user(
        self, client, invalid_identity, authentication_headers, organizations
    ):
        resp = client.get(
            reverse('platform-list', args=[organizations["root"].pk]),
            **authentication_headers(invalid_identity),
        )
        assert resp.status_code in (403, 401)  # depends on auth backend

    def test_authorized_user_no_platforms_no_org(self, authenticated_client, organizations):
        resp = authenticated_client.get(reverse('platform-list', args=[organizations["root"].pk]))
        assert resp.status_code == 404

    def test_authorized_user_no_platforms_org(
        self, authenticated_client, organizations, valid_identity
    ):
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations["root"])
        resp = authenticated_client.get(reverse('platform-list', args=[organizations["root"].pk]))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_authorized_user_accessible_empty_platforms(
        self, authenticated_client, organizations, valid_identity
    ):
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations["root"])
        resp = authenticated_client.get(reverse('platform-list', args=[organizations["root"].pk]))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_authorized_user_inaccessible_platforms(
        self, authenticated_client, organizations, platforms, valid_identity
    ):
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations["empty"])
        resp = authenticated_client.get(reverse('platform-list', args=[organizations["empty"].pk]))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_authorized_user_accessible_platforms(
        self, authenticated_client, organizations, platforms, valid_identity
    ):
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations["root"])
        OrganizationPlatform.objects.create(
            organization=organizations["root"], platform=platforms["root"]
        )
        resp = authenticated_client.get(reverse('platform-list', args=[organizations["root"].pk]))
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]['pk'] == platforms["root"].pk

    def test_authorized_user_accessible_platforms_through_sushi(
        self, authenticated_client, organizations, platforms, valid_identity
    ):
        """
        Test that sushi credentials based link between organization and platform is enough to make
        the platform accessible through the API
        """
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations["root"])
        SushiCredentials.objects.create(
            organization=organizations['root'], platform=platforms['root'], counter_version=5
        )
        resp = authenticated_client.get(
            reverse('platform-list', args=[organizations["root"].pk]), {'used_only': 1}
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]['pk'] == platforms["root"].pk

    def test_authorized_user_platforms_in_inaccessible_org(
        self, authenticated_client, organizations, platforms
    ):
        """
        There is an org and it has platforms, but the user cannot access the org
        """
        OrganizationPlatform.objects.create(
            organization=organizations["root"], platform=platforms["root"]
        )
        resp = authenticated_client.get(reverse('platform-list', args=[organizations["root"].pk]))
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
            reverse('platform-list', args=[organization_pk]),
            {
                'ext_id': 122,  # ext_id may not be present and will be overriden to None
                'short_name': 'platform',
                'name': "long_platform",
                "url": "https://example.com",
                "provider": "provider",
            },
        )
        assert resp.status_code == code
        if resp.status_code == 201:
            new_platform = Platform.objects.order_by('pk').last()
            if organization:
                assert new_platform.source == DataSource.objects.get(
                    organization=organizations[organization], type=DataSource.TYPE_ORGANIZATION
                )
            assert new_platform.ext_id is None
            assert new_platform.short_name == 'platform'
            assert new_platform.name == 'long_platform'
            assert new_platform.provider == 'provider'
            assert new_platform.url == 'https://example.com'
            assert set(
                new_platform.platforminterestreport_set.values_list(
                    'report_type__short_name', flat=True
                )
            ) == {'TR', 'DR', 'JR1', 'BR2', 'DB1'}, "Interest report types created check"

        resp = clients[client].post(
            reverse('platform-list', args=[organization_pk]),
            {
                'ext_id': 122,  # ext_id may not be present and will be overriden to None
                'short_name': 'platform',
                'name': "long_platform",
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
            reverse('platform-list', args=[organizations["master"].pk]),
            {
                'short_name': 'platform',
                'name': "long_platform",
                "url": "https://example.com",
                "provider": "provider",
            },
        )
        assert resp.status_code == 201

        organizations["master"].refresh_from_db()
        assert organizations["master"].source is None, "no change to organization source"

        resp = clients["su"].post(
            reverse('platform-list', args=[organizations["master"].pk]),
            {
                'short_name': 'platform',
                'name': "long_platform",
                "url": "https://example.com",
                "provider": "provider",
            },
        )
        assert resp.status_code == 400, "Already created"

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
            reverse('platform-list', args=[master_org.pk]),
            {'short_name': 'platform', 'name': "long_platform", "provider": "provider"},
        )
        assert resp.status_code == 201

        # try it for another organization
        standalone_org = organizations["standalone"]
        assert standalone_org.source is None
        resp = clients["su"].post(
            reverse('platform-list', args=[standalone_org.pk]),
            {'short_name': 'platform2', 'name': "long_platform2", "provider": "provider"},
        )
        assert resp.status_code == 201

    def test_create_platform_when_disabled(self, basic1, clients, organizations, client, settings):
        settings.ALLOW_USER_CREATED_PLATFORMS = False

        resp = clients["su"].post(
            reverse('platform-list', args=[organizations["standalone"].pk]),
            {
                'short_name': 'platform',
                'name': "long_platform",
                "url": "https://example.com",
                "provider": "provider",
            },
        )
        assert resp.status_code == 403

    def test_list_platforms_for_all_organization(self, basic1, clients, organizations, client):
        resp = clients["master_admin"].get(reverse('platform-list', args=[-1]))
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

        resp = clients["master_admin"].get(reverse('platform-list', args=[-1]) + "?used_only")
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
                'platform-detail', args=[organizations[organization].pk, platforms[platform].pk]
            ),
            {
                'ext_id': 122,  # ext_id may not be present and will be overriden to None
                'short_name': 'platform',
                'name': "long_platform",
                "url": "https://example.com",
                "provider": "provider",
            },
        )
        assert resp.status_code == code
        if resp.status_code // 100 == 2:
            platform = Platform.objects.get(short_name="platform")
            assert platform.source == data_sources["standalone"]
            assert platform.ext_id is None
            assert platform.name == 'long_platform'
            assert platform.provider == 'provider'
            assert platform.url == 'https://example.com'

    def test_update_platform_for_organization_with_no_data_source(
        self, basic1, clients, organizations, client, platforms
    ):
        resp = clients["su"].patch(
            reverse('platform-detail', args=[organizations["master"].pk, platforms["master"].pk]),
            {
                'short_name': 'platform',
                'name': "long_platform",
                "url": "https://example.com",
                "provider": "provider",
            },
        )
        assert resp.status_code == 403

    def test_update_platform_when_disabled(
        self, basic1, clients, organizations, client, platforms, settings
    ):
        settings.ALLOW_USER_CREATED_PLATFORMS = False

        resp = clients["su"].patch(
            reverse(
                'platform-detail', args=[organizations["standalone"].pk, platforms["standalone"].pk]
            ),
            {
                'short_name': 'platform',
                'name': "long_platform",
                "url": "https://example.com",
                "provider": "provider",
            },
        )
        assert resp.status_code == 403

    @pytest.mark.parametrize(
        ['user', 'delete_platform', 'org_platform', 'can_delete'],
        [
            ['user1', False, False, False],
            ['user2', False, False, False],
            ['admin1', False, False, False],
            ['admin2', False, False, True],
            ['master_admin', False, False, True],
            ['master_user', False, False, False],
            ['su', False, False, True],
            ['su', True, False, False],
            ['su', True, True, True],
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
    ):
        platform = platforms['standalone'] if org_platform else platforms["shared"]
        organization = organizations['standalone']
        ImportBatchFullFactory.create(platform=platform, organization=organization)
        assert AccessLog.objects.filter(organization=organization, platform=platform).count() > 0

        with mock.patch('publications.views.delete_platform_data_task') as task_mock:
            task_mock.delay.return_value = MockTask()
            resp = clients[user].post(
                reverse('platform-delete-all-data', args=[organization.pk, platform.pk]),
                {"delete_platform": delete_platform},
            )
            if can_delete:
                assert resp.status_code == 200
                task_mock.delay.assert_called()
            else:
                assert resp.status_code in (403, 404, 400)
                task_mock.delay.assert_not_called()

    @pytest.mark.parametrize(
        ['user', 'can_delete'],
        [
            ['user1', False],
            ['user2', False],
            ['admin1', False],
            ['admin2', False],
            ['master_admin', True],
            ['master_user', False],
            ['su', True],
        ],
    )
    def test_platform_delete_all_data_all_organizations(
        self, basic1, clients, platforms, organizations, user, can_delete
    ):
        platform = platforms['standalone']
        org_to_al_count = {}
        for organization in organizations.values():
            ImportBatchFullFactory.create(platform=platform, organization=organization)
            al_count = AccessLog.objects.filter(
                organization=organization, platform=platform
            ).count()
            assert al_count > 0
            org_to_al_count[organization.pk] = al_count

        with mock.patch('publications.views.delete_platform_data_task') as task_mock:
            task_mock.delay.return_value = MockTask()
            resp = clients[user].post(reverse('platform-delete-all-data', args=[-1, platform.pk]))
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
            reverse('platform-list', args=[organizations["root"].pk]),
            **authentication_headers(invalid_identity),
        )
        assert resp.status_code in (403, 401)  # depends on auth backend

    def test_authorized_user_no_platforms_no_org(self, authenticated_client, organizations):
        resp = authenticated_client.get(reverse('platform-list', args=[organizations["root"].pk]))
        assert resp.status_code == 404

    def test_authorized_user_no_platforms_org(
        self, authenticated_client, organizations, valid_identity
    ):
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations["root"])
        resp = authenticated_client.get(reverse('platform-list', args=[organizations["root"].pk]))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_authorized_user_accessible_empty_platforms(
        self, authenticated_client, organizations, valid_identity
    ):
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations["root"])
        resp = authenticated_client.get(reverse('platform-list', args=[organizations["root"].pk]))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_authorized_user_inaccessible_platforms(
        self, authenticated_client, organizations, valid_identity
    ):
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations["root"])
        resp = authenticated_client.get(reverse('platform-list', args=[organizations["root"].pk]))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_authorized_user_accessible_platforms(
        self, authenticated_client, organizations, platforms, valid_identity
    ):
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations["root"])
        OrganizationPlatform.objects.create(
            organization=organizations["root"], platform=platforms["root"]
        )
        resp = authenticated_client.get(reverse('platform-list', args=[organizations["root"].pk]))
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
            reverse('platform-title-list', args=[organizations["root"].pk, platforms["root"].pk]),
            **authentication_headers(invalid_identity),
        )
        assert resp.status_code in (403, 401)  # depends on auth backend

    def test_authorized_user_no_org(self, authenticated_client, organizations, platforms):
        OrganizationPlatform.objects.create(
            organization=organizations["root"], platform=platforms["root"]
        )
        resp = authenticated_client.get(
            reverse('platform-title-list', args=[organizations["root"].pk, platforms["root"].pk])
        )
        assert resp.status_code == 404

    def test_authorized_user_accessible_platforms_no_titles(
        self, authenticated_client, organizations, platforms, valid_identity, titles
    ):
        """
        Titles are created by the 'titles' fixture, but should not appear in the result as they
        are not accessible for an associated platform
        """
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        UserOrganization.objects.create(user=identity.user, organization=organizations["root"])
        OrganizationPlatform.objects.create(
            organization=organizations["root"], platform=platforms["root"]
        )
        resp = authenticated_client.get(
            reverse('platform-title-list', args=[organizations["root"].pk, platforms["root"].pk])
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 0

    def test_authorized_user_accessible_platforms_titles(
        self, authenticated_client, organizations, platforms, valid_identity, titles, report_type_nd
    ):
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        organization = organizations["root"]
        platform = platforms["root"]
        UserOrganization.objects.create(user=identity.user, organization=organization)
        OrganizationPlatform.objects.create(organization=organization, platform=platform)
        # we need to connect some titles with the platform which is done indirectly through
        # AccessLog instances
        # we create 2 access logs but both for the same title so that we can check that
        # - title is present in the output only once - distinct is used properly
        # - second title is not present - the filtering works OK
        rt = report_type_nd(0)
        metric = Metric.objects.create(short_name='m1', name='Metric1')
        import_batch = ImportBatch.objects.create(
            platform=platform, organization=organization, report_type=rt
        )
        al1 = AccessLog.objects.create(
            platform=platform,
            target=titles[0],
            value=1,
            date='2019-01-01',
            report_type=rt,
            metric=metric,
            organization=organization,
            import_batch=import_batch,
        )
        al2 = AccessLog.objects.create(
            platform=platform,
            target=titles[0],
            value=1,
            date='2019-02-01',
            report_type=rt,
            metric=metric,
            organization=organization,
            import_batch=import_batch,
        )
        create_platformtitle_links_from_accesslogs([al1, al2])
        resp = authenticated_client.get(
            reverse('platform-title-list', args=[organization.pk, platform.pk])
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]['isbn'] == titles[0].isbn
        assert resp.json()[0]['name'] == titles[0].name

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
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        organization = organizations["root"]
        platform = platforms["root"]
        UserOrganization.objects.create(user=identity.user, organization=organization)
        OrganizationPlatform.objects.create(organization=organization, platform=platform)
        # we need to connect some titles with the platform which is done indirectly through
        # AccessLog instances
        # we create 2 access logs but both for the same title so that we can check that
        # - title is present in the output only once - distinct is used properly
        # - second title is not present - the filtering works OK
        rt = report_type_nd(0)
        ig = InterestGroup.objects.create(short_name='interest1', position=1)
        metric = Metric.objects.create(short_name='m1', name='Metric1')
        ReportInterestMetric.objects.create(report_type=rt, metric=metric, interest_group=ig)
        PlatformInterestReport.objects.create(report_type=rt, platform=platform)
        import_batch = ImportBatch.objects.create(
            platform=platform, organization=organization, report_type=rt
        )
        al1 = AccessLog.objects.create(
            platform=platform,
            target=titles[0],
            value=1,
            date='2019-01-01',
            report_type=rt,
            metric=metric,
            organization=organization,
            import_batch=import_batch,
        )
        al2 = AccessLog.objects.create(
            platform=platform,
            target=titles[0],
            value=1,
            date='2019-02-01',
            report_type=rt,
            metric=metric,
            organization=organization,
            import_batch=import_batch,
        )
        create_platformtitle_links_from_accesslogs([al1, al2])
        sync_interest_by_import_batches()
        resp = authenticated_client.get(
            reverse('platform-title-interest-list', args=[organization.pk, platform.pk])
        )
        assert resp.status_code == 200
        assert 'results' in resp.json()
        data = resp.json()['results']
        assert len(data) == 1
        assert data[0]['isbn'] == titles[0].isbn
        assert data[0]['name'] == titles[0].name
        assert data[0]['interests']['interest1'] == 2

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
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        organization = organizations["root"]
        platform = platforms["root"]
        other_organization = organizations["standalone"]
        UserOrganization.objects.create(user=identity.user, organization=organization)
        OrganizationPlatform.objects.create(organization=organization, platform=platform)
        # we need to connect some titles with the platform which is done indirectly through
        # AccessLog instances
        # we create 2 access logs but both for the same title so that we can check that
        # - title is present in the output only once - distinct is used properly
        # - second title is not present - the filtering works OK
        rt = report_type_nd(0)
        ig = InterestGroup.objects.create(short_name='interest1', position=1)
        metric = Metric.objects.create(short_name='m1', name='Metric1')
        ReportInterestMetric.objects.create(report_type=rt, metric=metric, interest_group=ig)
        PlatformInterestReport.objects.create(report_type=rt, platform=platform)
        import_batch1 = ImportBatch.objects.create(
            platform=platform, organization=organization, report_type=rt
        )
        import_batch2 = ImportBatch.objects.create(
            platform=platform, report_type=rt, organization=other_organization
        )
        al1 = AccessLog.objects.create(
            platform=platform,
            target=titles[0],
            value=3,
            date='2019-01-01',
            report_type=rt,
            metric=metric,
            organization=organization,
            import_batch=import_batch1,
        )
        al2 = AccessLog.objects.create(
            platform=platform,
            target=titles[0],
            value=2,
            date='2019-01-01',
            report_type=rt,
            metric=metric,
            organization=other_organization,
            import_batch=import_batch2,
        )
        create_platformtitle_links_from_accesslogs([al1, al2])
        sync_interest_by_import_batches()
        resp = authenticated_client.get(
            reverse('platform-title-interest-list', args=[organization.pk, platform.pk])
        )
        assert resp.status_code == 200
        assert 'results' in resp.json()
        data = resp.json()['results']
        assert len(data) == 1
        assert data[0]['isbn'] == titles[0].isbn
        assert data[0]['name'] == titles[0].name
        assert data[0]['interests']['interest1'] == 3

    def test_authorized_user_accessible_platforms_interest_by_platform(
        self, authenticated_client, accesslogs_with_interest, valid_identity
    ):
        """
        Tests the view that returns interest summed up by platform for each title
        """
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        organization = accesslogs_with_interest['organization']
        platform = accesslogs_with_interest['platform']
        UserOrganization.objects.create(user=identity.user, organization=organization)
        resp = authenticated_client.get(
            reverse('title-interest-by-platform-list', args=[organization.pk])
        )
        assert resp.status_code == 200
        assert 'results' in resp.json()
        data = resp.json()['results']
        assert len(data) == 2
        assert platform.short_name in data[0]['interests']

    def test_authorized_user_accessible_platforms_interest_by_platform_more_platforms(
        self, authenticated_client, accesslogs_with_interest, valid_identity, platforms
    ):
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        organization = accesslogs_with_interest['organization']
        platform = accesslogs_with_interest['platform']
        titles = accesslogs_with_interest['titles']
        UserOrganization.objects.create(user=identity.user, organization=organization)
        platform2 = [pl for pl in platforms.values() if pl.pk != platform.pk][0]
        PlatformTitle.objects.create(
            platform=platform2, title=titles[0], organization=organization, date='2020-01-01'
        )
        resp = authenticated_client.get(
            reverse('title-interest-by-platform-list', args=[organization.pk])
        )
        assert resp.status_code == 200
        assert 'results' in resp.json()
        data = resp.json()['results']
        assert len(data) == 2
        assert len(data[0]['interests']) == 2, 'there should be interest for two platforms'
        assert platform.short_name in data[0]['interests']
        assert platform2.short_name in data[0]['interests']

    def test_organization_platforms_overlap(
        self, authenticated_client, accesslogs_with_interest, valid_identity, platforms
    ):
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        organization = accesslogs_with_interest['organization']
        platform = accesslogs_with_interest['platform']
        titles = accesslogs_with_interest['titles']
        UserOrganization.objects.create(user=identity.user, organization=organization)
        platform2 = [pl for pl in platforms.values() if pl.pk != platform.pk][0]
        PlatformTitle.objects.create(
            platform=platform2, title=titles[0], organization=organization, date='2020-01-01'
        )
        resp = authenticated_client.get(
            reverse('organization-platform-overlap', args=[organization.pk])
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 4, '4 overlap records in total'
        assert (
            len([rec for rec in data if rec['platform1'] == rec['platform2']]) == 2
        ), '2 records for self-overlap'
        assert (
            len([rec for rec in data if rec['platform1'] != rec['platform2']]) == 2
        ), '2 records for other-overlap'
        check_rec = [
            rec
            for rec in data
            if rec['platform1'] == platform.pk and rec['platform2'] == platform2.pk
        ][0]
        assert check_rec['overlap'] == 1

    def test_organization_platforms_overlap_with_date_filter(
        self, authenticated_client, accesslogs_with_interest, valid_identity, platforms
    ):
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        organization = accesslogs_with_interest['organization']
        platform = accesslogs_with_interest['platform']
        titles = accesslogs_with_interest['titles']
        UserOrganization.objects.create(user=identity.user, organization=organization)
        platform2 = [pl for pl in platforms.values() if pl.pk != platform.pk][0]
        PlatformTitle.objects.create(
            platform=platform2, title=titles[0], organization=organization, date='2019-03-01'
        )
        # first with start_date allowing all records in
        resp = authenticated_client.get(
            reverse('organization-platform-overlap', args=[organization.pk]), {'start': '2019-01'}
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 4
        # then with start_date which removes the overlapping records
        resp = authenticated_client.get(
            reverse('organization-platform-overlap', args=[organization.pk]), {'start': '2019-03'}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1, 'only 1 self overlap'
        assert (
            len([rec for rec in data if rec['platform1'] == rec['platform2']]) == 1
        ), '1 self-overlap'
        # then with end_date which removes the overlapping records
        resp = authenticated_client.get(
            reverse('organization-platform-overlap', args=[organization.pk]),
            {'start': '2019-01', 'end': '2019-02'},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1, 'only 1 self overlap'
        assert (
            len([rec for rec in data if rec['platform1'] == rec['platform2']]) == 1
        ), '1 self-overlap'

    def test_organization_all_platform_overlap(
        self, authenticated_client, accesslogs_with_interest, valid_identity, platforms
    ):
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        organization = accesslogs_with_interest['organization']
        platform = accesslogs_with_interest['platform']
        titles = accesslogs_with_interest['titles']
        UserOrganization.objects.create(user=identity.user, organization=organization)
        platform2 = [pl for pl in platforms.values() if pl.pk != platform.pk][0]
        PlatformTitle.objects.create(
            platform=platform2, title=titles[0], organization=organization, date='2020-01-01'
        )
        resp = authenticated_client.get(
            reverse('organization-all-platforms-overlap', args=[organization.pk])
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2, '2 records for 2 platforms'
        for rec in data:
            assert rec['overlap'] == 1, 'both platforms share the same title'
            if rec['platform'] == platform.pk:
                assert rec['overlap_interest'] == 3
                assert rec['total_interest'] == 7
            else:
                assert rec['overlap_interest'] == 0, 'no interest on platform 2'
                assert rec['total_interest'] == 0, 'no interest on platform 2'

    def test_organization_all_platform_overlap_2(
        self, authenticated_client, accesslogs_with_interest, valid_identity, platforms
    ):
        """
        Create two identical sets of access logs but for different platforms and see what the
        overlap would be
        """
        identity = Identity.objects.select_related('user').get(identity=valid_identity)
        organization = accesslogs_with_interest['organization']
        platform = accesslogs_with_interest['platform']
        titles = accesslogs_with_interest['titles']
        import_batch = accesslogs_with_interest['import_batch']
        metric = accesslogs_with_interest['metric']
        import_batch2 = ImportBatch.objects.create(
            platform=platform, organization=organization, report_type=import_batch.report_type
        )
        platform2 = [pl for pl in platforms.values() if pl.pk != platform.pk][0]
        # here we create the same accesslogs for a different platform
        accesslog_basics = {
            'report_type': import_batch.report_type,
            'metric': metric,
            'platform': platform2,
            'import_batch': import_batch2,
        }
        accesslogs = [
            AccessLog.objects.create(
                target=titles[0],
                value=1,
                date='2019-01-01',
                organization=organization,
                **accesslog_basics,
            ),
            AccessLog.objects.create(
                target=titles[0],
                value=2,
                date='2019-02-01',
                organization=organization,
                **accesslog_basics,
            ),
            AccessLog.objects.create(
                target=titles[1],
                value=4,
                date='2019-02-01',
                organization=organization,
                **accesslog_basics,
            ),
        ]
        create_platformtitle_links_from_accesslogs(accesslogs)
        sync_interest_by_import_batches()

        UserOrganization.objects.create(user=identity.user, organization=organization)
        resp = authenticated_client.get(
            reverse('organization-all-platforms-overlap', args=[organization.pk])
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2, '2 records for 2 platforms'
        for rec in data:
            assert rec['overlap'] == 2, 'both platforms share the same 2 titles'
            assert rec['overlap_interest'] == 7
            assert rec['total_interest'] == 7

    def test_organization_all_platform_overlap_all_orgs(
        self, master_user_client, accesslogs_with_interest, platforms
    ):
        organization = accesslogs_with_interest['organization']
        platform = accesslogs_with_interest['platform']
        titles = accesslogs_with_interest['titles']
        platform2 = [pl for pl in platforms.values() if pl.pk != platform.pk][0]
        PlatformTitle.objects.create(
            platform=platform2, title=titles[0], organization=organization, date='2020-01-01'
        )
        resp = master_user_client.get(reverse('organization-all-platforms-overlap', args=['-1']))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2, '2 records for 2 platforms'
        for rec in data:
            assert rec['overlap'] == 1, 'both platforms share the same title'
            if rec['platform'] == platform.pk:
                assert rec['overlap_interest'] == 11
                assert rec['total_interest'] == 15
            else:
                assert rec['overlap_interest'] == 0, 'no interest on platform 2'
                assert rec['total_interest'] == 0, 'no interest on platform 2'

    def test_platform_title_ids_list(self, master_user_client, accesslogs_with_interest):
        """
        Test the 'title-ids-list' custom action of platform viewset
        """
        url = reverse('platform-title-ids-list', args=[-1])
        resp = master_user_client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        platform = accesslogs_with_interest['platform']
        assert str(platform.pk) in data
        # the last title is not linked to the platform
        assert set(data[str(platform.pk)]) == {
            title.pk for title in accesslogs_with_interest['titles'][:2]
        }

    def test_platform_title_ids_list_one_organization(
        self, master_user_client, accesslogs_with_interest
    ):
        """
        Test the 'title-ids-list' custom action of platform viewset
        """
        organization = accesslogs_with_interest['organization']
        url = reverse('platform-title-ids-list', args=[organization.pk])
        resp = master_user_client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        platform = accesslogs_with_interest['platform']
        assert str(platform.pk) in data
        # the last title is not linked to the platform
        assert set(data[str(platform.pk)]) == {
            title.pk for title in accesslogs_with_interest['titles'][:2]
        }

    def test_platform_title_ids_list_with_filter(
        self, master_user_client, accesslogs_with_interest
    ):
        """
        Test the 'title-ids-list' custom action of platform viewset with publication type filter
        """
        url = reverse('platform-title-ids-list', args=[-1])
        resp = master_user_client.get(url + '?pub_type=U')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 0

    @pytest.mark.clickhouse
    @pytest.mark.usefixtures('clickhouse_on_off')
    @pytest.mark.django_db(transaction=True)
    def test_platform_title_count(self, master_user_client, accesslogs_with_interest):
        """
        Test the 'title-count' custom action of platform viewset
        """
        url = reverse('platform-title-count', args=[-1])
        resp = master_user_client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        record = data[0]
        platform = accesslogs_with_interest['platform']
        assert record['platform'] == platform.pk
        # the last title is not linked to the platform
        assert record['title_count'] == len(accesslogs_with_interest['titles']) - 1

    def test_platform_title_count_detail(self, master_user_client, accesslogs_with_interest):
        """
        Test the 'title-count' detail custom action of platform viewset
        """
        platform = accesslogs_with_interest['platform']
        url = reverse('platform-title-count', args=[-1, platform.pk])
        resp = master_user_client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert data['title_count'] == 2

    @pytest.mark.parametrize(['has_issn'], [(True,), (False,)])
    @pytest.mark.parametrize(['has_isbn'], [(True,), (False,)])
    @pytest.mark.parametrize(['has_eissn'], [(True,), (False,)])
    @pytest.mark.parametrize(['has_doi'], [(True,), (False,)])
    @pytest.mark.parametrize(
        ['matched_field'], [('name',), ('isbn',), ('issn',), ('eissn',), ('doi',), (None,)]
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
            'name': 'Foo Bar',
            'issn': '1234-4567',
            'eissn': '2345-6789',
            'isbn': '0801643317',
            'doi': '10.1007/9876.5432',
        }
        t = Title.objects.create(
            name=base_attrs['name'],
            issn=base_attrs['issn'] if has_issn else '',
            eissn=base_attrs['eissn'] if has_eissn else '',
            isbn=base_attrs['isbn'] if has_isbn else '',
            doi=base_attrs['doi'] if has_doi else '',
        )
        org = organizations['master']
        # connect organization to platform - otherwise the user would get 404
        OrganizationPlatform.objects.create(organization=org, platform=platform)
        # and platform to title, otherwise the title will be missing from the results
        PlatformTitle.objects.create(
            platform=platform, title=t, organization=org, date='2020-01-01'
        )
        q = base_attrs[matched_field][-4:] if matched_field else ''  # end of matched string
        resp = master_user_client.get(
            reverse('platform-title-list', args=[org.pk, platform.pk]), {'q': q}
        )
        assert resp.status_code == 200
        data = resp.json()
        if matched_field is None or matched_field == 'name' or locals()['has_' + matched_field]:
            # the matched field is actually filled in, so it should match
            assert len(data) == 1, f'the title should match "{q}"'
            assert data[0]['pk'] == t.pk
        else:
            assert len(data) == 0, f'nothing should match "{q}"'


@pytest.mark.django_db
class TestPlatformInterestAPI:
    @pytest.mark.parametrize("fmt", (None, "csv", "xlsx"))
    def test_platfrom_interest_list_empty(
        self, master_user_client, interest_rt, organizations, fmt
    ):
        url = reverse('platform-interest-list', args=(organizations["standalone"].pk,))
        if fmt:
            url += f"?format={fmt}"
        resp = master_user_client.get(url)
        assert resp.status_code == 200
        if fmt is None:
            assert resp.json() == []

    @pytest.mark.parametrize("fmt", (None, "csv", "xlsx"))
    def test_platfrom_interest_list_all_org_empty(self, master_user_client, interest_rt, fmt):
        url = reverse('platform-interest-list', args=(-1,))
        if fmt:
            url += f"?format={fmt}"
        resp = master_user_client.get(url)
        assert resp.status_code == 200
        if fmt is None:
            assert resp.json() == []


@pytest.mark.django_db
@pytest.mark.usefixtures("basic1")
class TestAllPlatformsAPI:
    def test_all_platform_public_only_param(self, clients, data_sources):
        plat_source_type_not_org = PlatformFactory.create(source=data_sources['api'])
        plat_source_type_org = PlatformFactory.create(source=data_sources['branch'])
        resp = clients['admin1'].get(
            reverse("all-platforms-list", args=[-1]), {'public_only': 'True'}
        )
        assert resp.status_code == 200
        resp_pks = {plat["pk"] for plat in resp.data}
        assert plat_source_type_not_org.pk in resp_pks
        assert plat_source_type_org.pk not in resp_pks

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
            assert [e["pk"] for e in resp.json()] == [platforms[e].pk for e in sorted(available)]

    @pytest.mark.parametrize(['allow_noncounter'], ((True,), (False,)))
    def test_all_platforms_detail_report_types(
        self, basic1, report_type_nd, settings, allow_noncounter
    ):
        settings.ALLOW_NONCOUNTER_DATA = allow_noncounter  # override settings
        # prepare data
        client = basic1['clients']['admin2']
        organization = basic1['organizations']['standalone']  # admin2 is admin of standalone
        platform = basic1['platforms']['shared']
        assert ReportType.objects.count() == 0, 'make sure not report are created upfront'
        rt_counter = report_type_nd(0, short_name='counter')
        rt_counter_no_interest = report_type_nd(0, short_name='counter no interest')
        rt_noncounter = report_type_nd(0, short_name='noncounter')
        # connect the platform and reports
        PlatformInterestReport.objects.create(platform=platform, report_type=rt_counter)
        PlatformInterestReport.objects.create(platform=platform, report_type=rt_noncounter)
        # create CounterReportType which marks the report as COUNTER report
        CounterReportType.objects.create(
            code='test', name='test', report_type=rt_counter, counter_version=5
        )
        CounterReportType.objects.create(
            code='test2', name='test 2', report_type=rt_counter_no_interest, counter_version=5
        )
        # the test itself
        resp = client.get(
            reverse('all-platforms-get-report-types', args=(organization.pk, platform.pk))
        )
        assert resp.status_code == 200
        data = resp.json()
        if allow_noncounter:
            assert {rec['pk'] for rec in data} == {
                rt_counter.pk,
                rt_counter_no_interest.pk,
                rt_noncounter.pk,
            }
        else:
            assert {rec['pk'] for rec in data} == {rt_counter.pk, rt_counter_no_interest.pk}

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
        for record in resp.data:
            assert record.keys() == {
                'url',
                'organization',
                'platform',
                'counter_version',
                'counter_report',
                'latest',
                'count',
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
        ['org_name', 'expected_platforms'],
        [
            ['root', ['standalone']],  # explicitly connected
            ['master', []],  # not connected
            ['standalone', ['standalone']],  # connected by sushi in the credentials fixture
            ['branch', ['branch']],  # connected by sushi in the credentials fixture
        ],
    )
    def test_all_platform_list_with_apikey(
        self, client, platforms, organizations, org_name, expected_platforms, credentials
    ):
        OrganizationPlatform.objects.create(
            organization=(organizations['root']), platform=platforms['standalone']
        )
        org = organizations[org_name]
        api_key, key_val = OrganizationAPIKey.objects.create_key(organization=org, name='test')
        resp = client.get(reverse('global-platforms-list'), HTTP_AUTHORIZATION=f'Api-Key {key_val}')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == len(expected_platforms)
        visible_pks = {rec['pk'] for rec in data}
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
        pks_str = ','.join(map(str, pks))
        resp = admin_client.get(reverse('global-platforms-list') + f'?pks={pks_str}')
        assert resp.status_code == 200
        data = {rec['pk'] for rec in resp.json()}
        assert len(data) == len(pks)
        assert data == set(pks)


@pytest.fixture
def accesslogs_with_interest(organizations, platforms, titles, report_type_nd, interest_rt):
    organization = organizations["root"]
    platform = platforms["root"]
    OrganizationPlatform.objects.create(organization=organization, platform=platform)
    rt = report_type_nd(0)
    ig = InterestGroup.objects.create(short_name='interest1', position=1)
    metric = Metric.objects.create(short_name='m1', name='Metric1')
    ReportInterestMetric.objects.create(report_type=rt, metric=metric, interest_group=ig)
    PlatformInterestReport.objects.create(report_type=rt, platform=platform)
    import_batch = ImportBatch.objects.create(
        platform=platform, organization=organization, report_type=rt
    )
    accesslog_basics = {
        'report_type': rt,
        'metric': metric,
        'platform': platform,
        'import_batch': import_batch,
    }
    accesslogs = [
        AccessLog.objects.create(
            target=titles[0],
            value=1,
            date='2019-01-01',
            organization=organization,
            **accesslog_basics,
        ),
        AccessLog.objects.create(
            target=titles[0],
            value=2,
            date='2019-02-01',
            organization=organization,
            **accesslog_basics,
        ),
        AccessLog.objects.create(
            target=titles[1],
            value=4,
            date='2019-02-01',
            organization=organization,
            **accesslog_basics,
        ),
        AccessLog.objects.create(
            target=titles[0],
            value=8,
            date='2019-02-01',
            organization=organizations["master"],
            **accesslog_basics,
        ),
    ]
    create_platformtitle_links_from_accesslogs(accesslogs)
    sync_interest_by_import_batches()
    return {
        key: val
        for key, val in locals().items()
        if key in ('accesslogs', 'titles', 'organization', 'platform', 'import_batch', 'metric')
    }


@pytest.mark.clickhouse
@pytest.mark.usefixtures('clickhouse_on_off')
@pytest.mark.django_db(transaction=True)
class TestTopTitleInterestViewSet:
    def test_all_organizations(self, accesslogs_with_interest, master_user_client):
        titles = accesslogs_with_interest['titles']
        resp = master_user_client.get(
            reverse('top-title-interest-list', args=['-1']), {'order_by': 'interest1'}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2, 'we have two titles'
        assert data[0]['isbn'] == titles[0].isbn
        assert data[0]['name'] == titles[0].name
        assert data[0]['interests']['interest1'] == 11  # 8 + 2 + 1
        assert data[1]['isbn'] == titles[1].isbn
        assert data[1]['name'] == titles[1].name
        assert data[1]['interests']['interest1'] == 4  # 4

    def test_one_organization(self, accesslogs_with_interest, master_user_client):
        organization = accesslogs_with_interest['organization']
        titles = accesslogs_with_interest['titles']
        resp = master_user_client.get(
            reverse('top-title-interest-list', args=[organization.pk]), {'order_by': 'interest1'}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2, 'we have two titles'
        assert data[0]['isbn'] == titles[1].isbn
        assert data[0]['name'] == titles[1].name
        assert data[0]['interests']['interest1'] == 4  # 4
        assert data[1]['isbn'] == titles[0].isbn
        assert data[1]['interests']['interest1'] == 3  # 2 + 1

    def test_all_organizations_date_filter(self, accesslogs_with_interest, master_user_client):
        titles = accesslogs_with_interest['titles']
        resp = master_user_client.get(
            reverse('top-title-interest-list', args=['-1']),
            {'order_by': 'interest1', 'start': '2019-02'},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2, 'we have two titles'
        assert data[0]['isbn'] == titles[0].isbn
        assert data[0]['name'] == titles[0].name
        assert data[0]['interests']['interest1'] == 10  # 8 + 2
        assert data[1]['isbn'] == titles[1].isbn
        assert data[1]['name'] == titles[1].name
        assert data[1]['interests']['interest1'] == 4  # 4

    def test_all_organizations_pub_type_filter(self, accesslogs_with_interest, master_user_client):
        titles = accesslogs_with_interest['titles']
        resp = master_user_client.get(
            reverse('top-title-interest-list', args=['-1']),
            {'order_by': 'interest1', 'pub_type': 'J'},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1, 'we have one title with type J'
        assert data[0]['issn'] == titles[1].issn
        assert data[0]['name'] == titles[1].name
        assert data[0]['interests']['interest1'] == 4  # 4


@pytest.mark.django_db
class TestTitleInterestBrief:
    def test_list(self, master_user_client, accesslogs_with_interest):
        resp = master_user_client.get(reverse('title-interest-brief-list', args=[-1]))
        assert resp.status_code == 200
        data = resp.json()
        # last title is not in the response because it has no interest
        titles = accesslogs_with_interest['titles'][:2]
        assert len(data) == len(titles)
        for rec in data:
            if rec['target_id'] == titles[0].pk:
                assert rec['interest'] == 11  # 1 + 2 + 8
            elif rec['target_id'] == titles[1].pk:
                assert rec['interest'] == 4
            else:
                assert False, 'such record should not exist'

    def test_list_one_org(self, master_user_client, accesslogs_with_interest):
        organization = accesslogs_with_interest['organization']
        resp = master_user_client.get(reverse('title-interest-brief-list', args=[organization.pk]))
        assert resp.status_code == 200
        data = resp.json()
        # last title is not in the response because it has no interest
        titles = accesslogs_with_interest['titles'][:2]
        assert len(data) == len(titles)
        for rec in data:
            if rec['target_id'] == titles[0].pk:
                assert rec['interest'] == 3  # 1 + 2
            elif rec['target_id'] == titles[1].pk:
                assert rec['interest'] == 4
            else:
                assert False, 'such record should not exist'

    def test_detail(self, master_user_client, accesslogs_with_interest):
        organization = accesslogs_with_interest['organization']
        title = accesslogs_with_interest['titles'][0]
        resp = master_user_client.get(
            reverse('title-interest-brief-detail', args=[organization.pk, title.pk])
        )
        assert resp.status_code == 200
        data = resp.json()
        assert type(data) is dict
        assert len(data) == 1, 'just "interest" key'
        assert data['interest'] == 3  # 1 + 2


@pytest.mark.django_db
class TestPlatformInterestReport:
    def test_get_platform_interest_report(
        self, authenticated_client, platforms, report_types, metrics, interests
    ):
        url = reverse("platform-interest-report-list")
        resp = authenticated_client.get(url)
        assert resp.status_code == 200
        data = {e["short_name"]: e for e in resp.json()}
        assert len(data["branch"]["interest_reports"]) == 1
        assert len(data["branch"]["interest_reports"][0]['interest_metric_set']) == 2
        assert len(data["standalone"]["interest_reports"]) == 2
        assert (
            len(data["standalone"]["interest_reports"][0]['interest_metric_set'])
            + len(data["standalone"]["interest_reports"][1]['interest_metric_set'])
            == 2
        )


@pytest.mark.django_db()
class TestTitleInterestViewSet:
    @pytest.mark.parametrize('column', ['name', 'pub_type', 'issn', 'interest1'])
    @pytest.mark.parametrize('desc', ['true', 'false', 'undefined'])
    def test_all_titles_order_by(self, accesslogs_with_interest, master_user_client, column, desc):
        titles = accesslogs_with_interest['titles']
        resp = master_user_client.get(
            reverse('title-interest-list', args=['-1']), {'order_by': column, 'desc': desc}
        )
        assert resp.status_code == 200
        data = resp.json()['results']
        assert len(data) == len(titles)
        # to ensure that the sorting is always the same (which is especially important with
        # pagination), we should mix the pk into the sorting on the backend. This is why we use the
        # pk below as a secondary sorting key as well
        if column == 'interest1':
            values = [(rec['interests'][column], rec['pk']) for rec in data]
        else:
            values = [(rec[column], rec['pk']) for rec in data]
        resorted = list(sorted(values, reverse=desc == 'true'))
        assert values == resorted
