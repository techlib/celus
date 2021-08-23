from unittest.mock import patch

import pytest
from django.urls import reverse

from core.models import DataSource, Identity
from logs.logic.data_import import create_platformtitle_links_from_accesslogs
from logs.logic.materialized_interest import sync_interest_by_import_batches
from logs.models import (
    OrganizationPlatform,
    AccessLog,
    Metric,
    ImportBatch,
    InterestGroup,
    ReportInterestMetric,
    ReportType,
)
from logs.tests.conftest import report_type_nd
from organizations.models import UserOrganization
from core.tests.conftest import (
    valid_identity,
    authenticated_client,
    authentication_headers,
    invalid_identity,
    master_client,
    master_identity,
)
from publications.models import PlatformInterestReport, Platform, PlatformTitle
from sushi.models import SushiCredentials, CounterReportType
from test_fixtures.entities.credentials import CredentialsFactory
from test_fixtures.scenarios.basic import *


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
        Test that sushi credentials based link between organization and platform is enough to make the platform
        accessible through the API
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
            ("master", "standalone", "standalone", 201),  # master
            ("admin2", "standalone", None, 201),  # this admin
            ("admin1", "standalone", "standalone", 403),  # other admin
            ("user2", "standalone", None, 403),  # other user
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
        organizations[organization].source = data_sources[data_source] if data_source else None
        organizations[organization].save()

        # su client
        resp = clients[client].post(
            reverse('platform-list', args=[organizations[organization].pk],),
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
            new_platform = Platform.objects.order_by('pk').last()
            assert new_platform.source == data_sources["standalone"]
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
            reverse('platform-list', args=[organizations[organization].pk],),
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
            reverse('platform-list', args=[organizations["master"].pk],),
            {
                'short_name': 'platform',
                'name': "long_platform",
                "url": "https://example.com",
                "provider": "provider",
            },
        )
        assert resp.status_code == 201

        organizations["master"].refresh_from_db()
        assert organizations["master"].source.organization == organizations["master"]
        assert organizations["master"].source.type == DataSource.TYPE_ORGANIZATION

        resp = clients["su"].post(
            reverse('platform-list', args=[organizations["master"].pk],),
            {
                'short_name': 'platform',
                'name': "long_platform",
                "url": "https://example.com",
                "provider": "provider",
            },
        )
        assert resp.status_code == 400, "Already created"

    def test_create_platform_when_disabled(
        self, basic1, clients, organizations, client, settings,
    ):
        settings.ALLOW_USER_CREATED_PLATFORMS = False

        resp = clients["su"].post(
            reverse('platform-list', args=[organizations["standalone"].pk],),
            {
                'short_name': 'platform',
                'name': "long_platform",
                "url": "https://example.com",
                "provider": "provider",
            },
        )
        assert resp.status_code == 403

    def test_list_platforms_for_all_organization(
        self, basic1, clients, organizations, client,
    ):
        resp = clients["master"].get(reverse('platform-list', args=[-1],))
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

        resp = clients["master"].get(reverse('platform-list', args=[-1],) + "?used_only")
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
            ("master", "standalone", "standalone", 200),  # master
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
                'platform-detail', args=[organizations[organization].pk, platforms[platform].pk],
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
            reverse('platform-detail', args=[organizations["master"].pk, platforms["master"].pk],),
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
                'platform-detail',
                args=[organizations["standalone"].pk, platforms["standalone"].pk],
            ),
            {
                'short_name': 'platform',
                'name': "long_platform",
                "url": "https://example.com",
                "provider": "provider",
            },
        )
        assert resp.status_code == 403


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
        print(resp.json())
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
        self, authenticated_client, accesslogs_with_interest, valid_identity, platforms,
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
        self, authenticated_client, accesslogs_with_interest, valid_identity, platforms,
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
        self, authenticated_client, accesslogs_with_interest, valid_identity, platforms,
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
            reverse('organization-platform-overlap', args=[organization.pk]), {'start': '2019-01'},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 4
        # then with start_date which removes the overlapping records
        resp = authenticated_client.get(
            reverse('organization-platform-overlap', args=[organization.pk]), {'start': '2019-03'},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1, 'only 1 self overlap'
        assert (
            len([rec for rec in data if rec['platform1'] == rec['platform2']]) == 1
        ), '1 self-overlap'

    def test_organization_all_platform_overlap(
        self, authenticated_client, accesslogs_with_interest, valid_identity, platforms,
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
        self, authenticated_client, accesslogs_with_interest, valid_identity, platforms,
    ):
        """
        Create two identical sets of access logs but for different platforms and see what the overlap would be
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
        self, master_client, accesslogs_with_interest, platforms,
    ):
        organization = accesslogs_with_interest['organization']
        platform = accesslogs_with_interest['platform']
        titles = accesslogs_with_interest['titles']
        platform2 = [pl for pl in platforms.values() if pl.pk != platform.pk][0]
        PlatformTitle.objects.create(
            platform=platform2, title=titles[0], organization=organization, date='2020-01-01'
        )
        resp = master_client.get(reverse('organization-all-platforms-overlap', args=['-1']))
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

    def test_platform_title_ids_list(self, master_client, accesslogs_with_interest):
        """
        Test the 'title-ids-list' custom action of platform viewset
        """
        url = reverse('platform-title-ids-list', args=[-1])
        resp = master_client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        platform = accesslogs_with_interest['platform']
        assert str(platform.pk) in data
        assert set(data[str(platform.pk)]) == {
            title.pk for title in accesslogs_with_interest['titles']
        }

    def test_platform_title_ids_list_one_organization(
        self, master_client, accesslogs_with_interest
    ):
        """
        Test the 'title-ids-list' custom action of platform viewset
        """
        organization = accesslogs_with_interest['organization']
        url = reverse('platform-title-ids-list', args=[organization.pk])
        resp = master_client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        platform = accesslogs_with_interest['platform']
        assert str(platform.pk) in data
        assert set(data[str(platform.pk)]) == {
            title.pk for title in accesslogs_with_interest['titles']
        }

    def test_platform_title_ids_list_with_filter(self, master_client, accesslogs_with_interest):
        """
        Test the 'title-ids-list' custom action of platform viewset with publication type filter
        """
        url = reverse('platform-title-ids-list', args=[-1])
        resp = master_client.get(url + '?pub_type=U')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 0

    def test_platform_title_count(self, master_client, accesslogs_with_interest):
        """
        Test the 'title-count' custom action of platform viewset
        """
        url = reverse('platform-title-count', args=[-1])
        resp = master_client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        record = data[0]
        platform = accesslogs_with_interest['platform']
        assert record['platform'] == platform.pk
        assert record['title_count'] == len(accesslogs_with_interest['titles'])

    def test_platform_title_count_detail(self, master_client, accesslogs_with_interest):
        """
        Test the 'title-count' detail custom action of platform viewset
        """
        platform = accesslogs_with_interest['platform']
        url = reverse('platform-title-count', args=[-1, platform.pk])
        resp = master_client.get(url)
        assert resp.status_code == 200
        data = resp.json()
        assert data['title_count'] == 2


@pytest.mark.django_db
@pytest.mark.usefixtures("basic1")
class TestAllPlatformsAPI:
    @pytest.mark.parametrize(
        ["client", "status", "organization", "available"],
        [
            ["unauthenticated", (401, 403), "empty", None],
            ["master", (200,), "empty", ["brain", "empty", "master", "shared"]],
            ["admin1", (200,), "root", ["brain", "master", "empty", "root", "shared"]],
            ["admin2", (200,), "master", ["brain", "master", "empty", "shared"]],
            ["user1", (200,), "branch", ["brain", "master", "empty", "branch", "shared"]],
            ["user2", (200,), "standalone", ["brain", "master", "empty", "standalone", "shared"]],
        ],
        ids=[
            "unauthenticated-empty",
            "master-empty",
            "admin1-root",
            "admin2-master",
            "user1-branch",
            "user2-standalone",
        ],
    )
    def test_all_platform_list(
        self, client, status, organization, available, clients, platforms, organizations
    ):

        resp = clients[client].get(
            reverse("all-platforms-list", args=[organizations[organization].pk])
        )
        assert resp.status_code in status
        if available is not None:
            assert [e["pk"] for e in resp.json()] == [platforms[e].pk for e in sorted(available)]
        assert True

    @pytest.mark.parametrize(
        ["client", "organization", "available"],
        [
            ["unauthenticated", "empty", set()],
            ["master", "empty", {"brain", "empty", "master", "shared"}],
            ["admin1", "root", {"brain", "master", "empty", "root", "shared"}],
            ["admin2", "master", {"brain", "master", "empty", "shared"}],
            ["user1", "branch", {"brain", "master", "empty", "branch", "shared"}],
            ["user2", "standalone", {"brain", "master", "empty", "standalone", "shared"}],
        ],
        ids=[
            "unauthenticated-empty",
            "master-empty",
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
                "master",
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
            "master-empty",
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

    def test_all_platfrom_knowledgebase(self, platforms, clients, organizations):

        # any organiztion
        resp = clients["user2"].get(
            reverse("all-platforms-knowledgebase", args=[-1, platforms["standalone"].pk])
        )
        assert resp.status_code == 200
        assert {"knowledgebase": None} == resp.json()

        # no credentials
        resp = clients["admin1"].get(
            reverse(
                "all-platforms-knowledgebase",
                args=[organizations["root"].pk, platforms["root"].pk],
            )
        )
        assert resp.status_code == 200
        assert {"knowledgebase": None} == resp.json()

        # unaccessible organization
        resp = clients["user2"].get(
            reverse(
                "all-platforms-knowledgebase",
                args=[organizations["branch"].pk, platforms["branch"].pk],
            )
        )
        assert resp.status_code == 404

        # same organization
        resp = clients["user1"].get(
            reverse(
                "all-platforms-knowledgebase",
                args=[organizations["branch"].pk, platforms["brain"].pk],
            )
        )
        assert resp.status_code == 200
        assert resp.json() == {
            'knowledgebase': {
                'providers': [
                    {
                        'assigned_report_types': [
                            {
                                'not_valid_after': None,
                                'not_valid_before': None,
                                'report_type': 'JR1',
                            }
                        ],
                        'counter_version': 4,
                        'provider': {
                            'extra': {},
                            'monthly': None,
                            'name': 'c4.brain.celus.net',
                            'pk': 10,
                            'url': 'http://c4.brain.celus.net',
                            'yearly': None,
                        },
                    },
                    {
                        'assigned_report_types': [
                            {
                                'not_valid_after': None,
                                'not_valid_before': None,
                                'report_type': 'TR',
                            },
                            {
                                'not_valid_after': None,
                                'not_valid_before': None,
                                'report_type': 'DR',
                            },
                        ],
                        'counter_version': 5,
                        'provider': {
                            'extra': {},
                            'monthly': None,
                            'name': 'c5.brain.celus.net',
                            'pk': 11,
                            'url': 'https://c5.brain.celus.net/sushi',
                            'yearly': None,
                        },
                    },
                ]
            }
        }

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


@pytest.mark.django_db
@pytest.mark.usefixtures("basic1")
class TestGlobalPlatformsAPI:
    @pytest.mark.parametrize(
        ["client", "status", "available"],
        [
            ["unauthenticated", (401, 403), None],
            [
                "master",
                (200,),
                {"brain", "master", "empty", "root", "shared", "standalone", "branch"},
            ],
            ["admin1", (200,), {"brain", "master", "empty", "root", "branch", "shared"}],
            ["admin2", (200,), {"brain", "master", "empty", "shared", "standalone"}],
            ["user1", (200,), {"brain", "master", "empty", "branch", "shared"}],
            ["user2", (200,), {"brain", "master", "empty", "standalone", "shared"}],
        ],
        ids=["unauthenticated", "master", "admin1", "admin2", "user1", "user2",],
    )
    def test_all_platform_list(self, client, status, available, clients, platforms, organizations):

        resp = clients[client].get(reverse("global-platforms-list"))
        assert resp.status_code in status
        if available is not None:
            diff = {e["pk"] for e in resp.json()} ^ {platforms[e].pk for e in available}
            print([key for key, value in platforms.items() if value.pk in diff])
            assert {e["pk"] for e in resp.json()} == {platforms[e].pk for e in available}
        assert True

    @pytest.mark.parametrize(
        ["client", "available"],
        [
            ["unauthenticated", set()],
            ["master", {"brain", "master", "empty", "root", "shared", "standalone", "branch"}],
            ["admin1", {"brain", "master", "empty", "root", "branch", "shared"}],
            ["admin2", {"brain", "master", "empty", "shared", "standalone"}],
            ["user1", {"brain", "master", "empty", "branch", "shared"}],
            ["user2", {"brain", "master", "empty", "standalone", "shared"}],
        ],
        ids=["unauthenticated", "mastery", "admin1", "admin2", "user1", "user2",],
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


@pytest.mark.django_db
class TestTopTitleInterestViewSet:
    def test_all_organizations(self, accesslogs_with_interest, master_client):
        titles = accesslogs_with_interest['titles']
        resp = master_client.get(
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

    def test_one_organization(self, accesslogs_with_interest, master_client):
        organization = accesslogs_with_interest['organization']
        titles = accesslogs_with_interest['titles']
        resp = master_client.get(
            reverse('top-title-interest-list', args=[organization.pk]), {'order_by': 'interest1'},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2, 'we have two titles'
        assert data[0]['isbn'] == titles[1].isbn
        assert data[0]['name'] == titles[1].name
        assert data[0]['interests']['interest1'] == 4  # 4
        assert data[1]['isbn'] == titles[0].isbn
        assert data[1]['interests']['interest1'] == 3  # 2 + 1

    def test_all_organizations_date_filter(self, accesslogs_with_interest, master_client):
        titles = accesslogs_with_interest['titles']
        resp = master_client.get(
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

    def test_all_organizations_pub_type_filter(self, accesslogs_with_interest, master_client):
        titles = accesslogs_with_interest['titles']
        resp = master_client.get(
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
    def test_list(self, master_client, accesslogs_with_interest):
        resp = master_client.get(reverse('title-interest-brief-list', args=[-1]))
        assert resp.status_code == 200
        data = resp.json()
        titles = accesslogs_with_interest['titles']
        assert len(data) == len(titles)
        for rec in data:
            if rec['target_id'] == titles[0].pk:
                assert rec['interest'] == 11  # 1 + 2 + 8
            elif rec['target_id'] == titles[1].pk:
                assert rec['interest'] == 4
            else:
                assert False, 'such record should not exist'

    def test_list_one_org(self, master_client, accesslogs_with_interest):
        organization = accesslogs_with_interest['organization']
        resp = master_client.get(reverse('title-interest-brief-list', args=[organization.pk]))
        assert resp.status_code == 200
        data = resp.json()
        titles = accesslogs_with_interest['titles']
        assert len(data) == len(titles)
        for rec in data:
            if rec['target_id'] == titles[0].pk:
                assert rec['interest'] == 3  # 1 + 2
            elif rec['target_id'] == titles[1].pk:
                assert rec['interest'] == 4
            else:
                assert False, 'such record should not exist'

    def test_detail(self, master_client, accesslogs_with_interest):
        organization = accesslogs_with_interest['organization']
        title = accesslogs_with_interest['titles'][0]
        resp = master_client.get(
            reverse('title-interest-brief-detail', args=[organization.pk, title.pk])
        )
        assert resp.status_code == 200
        data = resp.json()
        assert type(data) is dict
        assert len(data) == 1, 'just "interest" key'
        assert data['interest'] == 3  # 1 + 2
