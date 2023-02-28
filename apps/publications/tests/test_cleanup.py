import pytest
from core.models import DATA_SOURCE_TYPE_ORGANIZATION
from django.conf import settings
from hcube.api.models.aggregation import Count as HCount
from logs.cubes import AccessLogCube, ch_backend
from logs.models import AccessLog, ImportBatch, OrganizationPlatform
from organizations.models import Organization
from publications.logic.cleanup import delete_platform_data
from publications.models import Platform, PlatformTitle
from scheduler.models import FetchIntention
from sushi.models import SushiFetchAttempt

from test_fixtures.entities.data_souces import DataSourceFactory
from test_fixtures.entities.logs import ImportBatchFullFactory
from test_fixtures.entities.organizations import OrganizationFactory
from test_fixtures.entities.platforms import PlatformFactory
from test_fixtures.entities.scheduler import FetchIntentionFactory


@pytest.mark.django_db
class TestDeletePlatformData:
    @pytest.mark.clickhouse
    @pytest.mark.usefixtures('clickhouse_on_off')
    @pytest.mark.django_db(transaction=True)
    @pytest.mark.parametrize(
        "org_source,org_source_matches,delete_platform,platform_deleted",
        (
            (True, True, True, True),
            (True, False, True, False),
            (False, False, True, False),
            (True, True, False, False),
            (True, False, False, False),
            (False, False, False, False),
        ),
    )
    def test_for_one_organization_with_fis(
        self, org_source, org_source_matches, delete_platform, platform_deleted
    ):
        # fetch intention with some data - it will be removed
        organization = OrganizationFactory()
        if org_source and not org_source_matches:
            platform = PlatformFactory(
                source=DataSourceFactory(
                    organization=OrganizationFactory(), type=DATA_SOURCE_TYPE_ORGANIZATION
                )
            )
        elif org_source and org_source_matches:
            platform = PlatformFactory(
                source=DataSourceFactory(
                    organization=organization, type=DATA_SOURCE_TYPE_ORGANIZATION
                )
            )
        else:
            platform = PlatformFactory(source=None)
        fi = FetchIntentionFactory.create(
            credentials__organization=organization, credentials__platform=platform
        )
        ib = ImportBatchFullFactory.create(organization=organization, platform=platform)
        fi.attempt.import_batch = ib
        fi.attempt.save()
        # fetch intention without attempt - it will be kept for future
        FetchIntentionFactory(attempt=None, credentials=fi.credentials)
        # check the data before delete
        fltr = dict(organization=ib.organization, platform=ib.platform)
        cr_fltr = dict(credentials=fi.credentials)
        assert AccessLog.objects.filter(**fltr).count() > 0
        assert ImportBatch.objects.filter(**fltr).count() > 0
        assert PlatformTitle.objects.filter(**fltr).count() > 0
        assert OrganizationPlatform.objects.filter(**fltr).count() > 0
        assert FetchIntention.objects.filter(**cr_fltr).count() == 2
        assert SushiFetchAttempt.objects.filter(**cr_fltr).count() == 1

        def get_ch_count():
            return ch_backend.get_one_record(
                AccessLogCube.query()
                .filter(organization_id=ib.organization_id, platform_id=ib.platform_id)
                .aggregate(count=HCount())
            ).count

        if settings.CLICKHOUSE_SYNC_ACTIVE:
            assert get_ch_count() > 0

        delete_platform_data(
            ib.platform, Organization.objects.filter(pk=ib.organization.pk), delete_platform
        )

        assert not Platform.objects.filter(pk=platform.pk).exists() == platform_deleted
        assert AccessLog.objects.filter(**fltr).count() == 0
        assert ImportBatch.objects.filter(**fltr).count() == 0
        assert PlatformTitle.objects.filter(**fltr).count() == 0
        assert OrganizationPlatform.objects.filter(**fltr).count() == 0
        assert FetchIntention.objects.filter(**cr_fltr).count() == (0 if platform_deleted else 1)
        assert SushiFetchAttempt.objects.filter(**cr_fltr).count() == 0
        if settings.CLICKHOUSE_SYNC_ACTIVE:
            assert get_ch_count() == 0

    def test_for_more_organizations(self):
        ib = ImportBatchFullFactory.create()
        org2 = OrganizationFactory.create()
        ImportBatchFullFactory.create(organization=org2)
        fltr = dict(organization__in=[ib.organization, org2], platform=ib.platform)
        assert AccessLog.objects.filter(**fltr).count() > 0
        assert ImportBatch.objects.filter(**fltr).count() > 0
        assert PlatformTitle.objects.filter(**fltr).count() > 0
        delete_platform_data(
            ib.platform, Organization.objects.filter(pk__in=[ib.organization.pk, org2.pk])
        )
        assert AccessLog.objects.filter(**fltr).count() == 0
        assert ImportBatch.objects.filter(**fltr).count() == 0
        assert PlatformTitle.objects.filter(**fltr).count() == 0
