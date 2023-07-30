import pytest
from core.fake_data import DataSourceFactory
from core.models import DATA_SOURCE_TYPE_ORGANIZATION
from django.conf import settings
from hcube.api.models.aggregation import Count as HCount
from logs.cubes import AccessLogCube, ch_backend
from logs.fake_data import ImportBatchFullFactory
from logs.models import AccessLog, ImportBatch, OrganizationPlatform
from organizations.fake_data import OrganizationFactory
from organizations.models import Organization
from scheduler.fake_data import FetchIntentionFactory
from scheduler.models import FetchIntention
from sushi.fake_data import CredentialsFactory
from sushi.models import SushiCredentials, SushiFetchAttempt

from publications.fake_data import PlatformFactory
from publications.logic.cleanup import delete_platform_data
from publications.models import Platform, PlatformTitle


@pytest.mark.django_db
class TestDeletePlatformData:
    @pytest.mark.clickhouse
    @pytest.mark.usefixtures('clickhouse_on_off')
    @pytest.mark.django_db(transaction=True)
    @pytest.mark.parametrize('delete_credentials', (True, False))
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
        self, org_source, org_source_matches, delete_platform, platform_deleted, delete_credentials
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
        # extra credentials for the same platform, but for another organization
        # these should not be deleted in any case
        CredentialsFactory.create(platform=platform)
        # fetch intention without attempt - it will be kept for future
        FetchIntentionFactory(attempt=None, credentials=fi.credentials)
        # check the data before delete
        fltr = {'organization': ib.organization, 'platform': ib.platform}
        cr_fltr = {'credentials': fi.credentials}
        assert AccessLog.objects.filter(**fltr).count() > 0
        assert ImportBatch.objects.filter(**fltr).count() > 0
        assert PlatformTitle.objects.filter(**fltr).count() > 0
        assert OrganizationPlatform.objects.filter(**fltr).count() > 0
        assert FetchIntention.objects.filter(**cr_fltr).count() == 2
        assert SushiFetchAttempt.objects.filter(**cr_fltr).count() == 1
        old_credentials_ids = set(
            SushiCredentials.objects.filter(platform=ib.platform).values_list('pk', flat=True)
        )
        assert len(old_credentials_ids) > 1, 'at least 2 credentials should be present'

        def get_ch_count():
            return ch_backend.get_one_record(
                AccessLogCube.query()
                .filter(organization_id=ib.organization_id, platform_id=ib.platform_id)
                .aggregate(count=HCount())
            ).count

        if settings.CLICKHOUSE_SYNC_ACTIVE:
            assert get_ch_count() > 0

        delete_platform_data(
            ib.platform,
            Organization.objects.filter(pk=ib.organization.pk),
            delete_platform,
            delete_credentials=delete_credentials,
        )

        assert not Platform.objects.filter(pk=platform.pk).exists() == platform_deleted
        assert AccessLog.objects.filter(**fltr).count() == 0
        assert ImportBatch.objects.filter(**fltr).count() == 0
        assert PlatformTitle.objects.filter(**fltr).count() == 0
        assert OrganizationPlatform.objects.filter(**fltr).count() == 0
        assert FetchIntention.objects.filter(**cr_fltr).count() == (
            0 if platform_deleted or delete_credentials else 1
        )
        assert SushiFetchAttempt.objects.filter(**cr_fltr).count() == 0
        if delete_credentials or platform_deleted:
            # when platform is deleted, credentials are deleted too, otherwise the unrelated
            # credentials should be kept
            assert SushiCredentials.objects.filter(platform=ib.platform).count() == (
                0 if platform_deleted else 1
            )
        else:
            assert (
                set(
                    SushiCredentials.objects.filter(platform=ib.platform).values_list(
                        'pk', flat=True
                    )
                )
                == old_credentials_ids
            ), 'credentials should be kept'
        if settings.CLICKHOUSE_SYNC_ACTIVE:
            assert get_ch_count() == 0

    def test_for_more_organizations(self):
        ib = ImportBatchFullFactory.create()
        org2 = OrganizationFactory.create()
        ImportBatchFullFactory.create(organization=org2)
        fltr = {'organization__in': [ib.organization, org2], 'platform': ib.platform}
        assert AccessLog.objects.filter(**fltr).count() > 0
        assert ImportBatch.objects.filter(**fltr).count() > 0
        assert PlatformTitle.objects.filter(**fltr).count() > 0
        delete_platform_data(
            ib.platform, Organization.objects.filter(pk__in=[ib.organization.pk, org2.pk])
        )
        assert AccessLog.objects.filter(**fltr).count() == 0
        assert ImportBatch.objects.filter(**fltr).count() == 0
        assert PlatformTitle.objects.filter(**fltr).count() == 0
