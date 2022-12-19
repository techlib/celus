from unittest import mock

import pytest
from necronomicon.models import Batch, BatchStatus
from necronomicon.tasks import delete_batch_targets, prepare_batch
from organizations.models import Organization, UserOrganization
from publications.models import Platform
from sushi.models import SushiCredentials
from test_fixtures.entities.necronomicon import BatchFactory, CandidateFactory
from test_fixtures.scenarios.basic import (
    basic1,
    clients,
    counter_report_types,
    credentials,
    data_sources,
    identities,
    organizations,
    platforms,
    report_types,
    users,
)


@pytest.mark.django_db
class TestBatch:
    @pytest.mark.django_db(transaction=True)
    def test_prepare_organization(self, basic1, organizations):
        batch = BatchFactory(status=BatchStatus.INITIAL)

        usr_org_qs = UserOrganization.objects.filter(organization=organizations["standalone"])
        org_qs = Organization.objects.filter(pk=organizations["standalone"].pk)

        assert org_qs.count() == 1
        assert usr_org_qs.count() == 2

        CandidateFactory(batch=batch, content_object=organizations["standalone"])

        with mock.patch('necronomicon.models.tasks') as task_mock:
            batch.plan_prepare_batch()
            assert task_mock.prepare_batch.delay.called

        # trigger celery task
        prepare_batch(batch.id)
        batch.refresh_from_db()

        assert org_qs.count() == 1
        assert usr_org_qs.count() == 2

        assert batch.info[0]["stats"][0] == 5
        assert batch.status == BatchStatus.PREPARED

    @pytest.mark.django_db(transaction=True)
    def test_delete_organization(self, basic1, organizations):
        batch = BatchFactory(status=BatchStatus.PREPARED)

        usr_org_qs = UserOrganization.objects.filter(organization=organizations["standalone"])
        org_qs = Organization.objects.filter(pk=organizations["standalone"].pk)

        assert org_qs.count() == 1
        assert usr_org_qs.count() == 2

        CandidateFactory(batch=batch, content_object=organizations["standalone"])

        with mock.patch('necronomicon.models.tasks') as task_mock:
            batch.plan_delete_batch_targets()
            assert task_mock.delete_batch_targets.delay.called

        # trigger celery task
        delete_batch_targets(batch.id)
        batch.refresh_from_db()

        assert org_qs.count() == 0
        assert usr_org_qs.count() == 0

        assert batch.info[0]["stats"][0] == 5
        assert batch.status == BatchStatus.DELETED

    @pytest.mark.django_db(transaction=True)
    def test_prepare_platforms(self, basic1, platforms, credentials):
        batch = BatchFactory(status=BatchStatus.INITIAL)

        cred_qs = SushiCredentials.objects.filter(platform=platforms["standalone"])
        plat_qs = Platform.objects.filter(pk=platforms["standalone"].pk)

        assert plat_qs.count() == 1
        assert cred_qs.count() == 2

        CandidateFactory(batch=batch, content_object=platforms["standalone"])

        with mock.patch('necronomicon.models.tasks') as task_mock:
            batch.plan_prepare_batch()
            assert task_mock.prepare_batch.delay.called

        # trigger celery task
        prepare_batch(batch.id)
        batch.refresh_from_db()

        assert plat_qs.count() == 1
        assert cred_qs.count() == 2

        assert batch.info[0]["stats"][0] == 6
        assert batch.status == BatchStatus.PREPARED

    @pytest.mark.django_db(transaction=True)
    def test_delete_platforms(self, basic1, platforms, credentials):
        batch = BatchFactory(status=BatchStatus.PREPARED)

        cred_qs = SushiCredentials.objects.filter(platform=platforms["standalone"])
        plat_qs = Platform.objects.filter(pk=platforms["standalone"].pk)

        assert plat_qs.count() == 1
        assert cred_qs.count() == 2

        CandidateFactory(batch=batch, content_object=platforms["standalone"])

        with mock.patch('necronomicon.models.tasks') as task_mock:
            batch.plan_delete_batch_targets()
            assert task_mock.delete_batch_targets.delay.called

        # trigger celery task
        delete_batch_targets(batch.id)
        batch.refresh_from_db()

        assert plat_qs.count() == 0
        assert cred_qs.count() == 0

        assert batch.info[0]["stats"][0] == 6
        assert batch.status == BatchStatus.DELETED

    def test_create_from_queryset(self, basic1, organizations, platforms):
        batch = Batch.create_from_queryset(Organization.objects.all())

        assert batch.candidates.count() == Organization.objects.count()
        assert Batch.create_from_queryset(Platform.objects.none()) is None
