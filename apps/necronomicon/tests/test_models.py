from datetime import datetime
from unittest import mock

import pytest
from freezegun import freeze_time
from necronomicon.fake_data import BatchFactory, CandidateFactory
from necronomicon.models import Batch, BatchStatus
from necronomicon.tasks import delete_batch_targets, prepare_batch
from organizations.models import Organization, UserOrganization
from publications.models import Platform
from sushi.models import SushiCredentials

from test_scenarios.basic import (  # noqa - fixtures
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

        with mock.patch("necronomicon.models.tasks") as task_mock:
            batch.plan_prepare_batch()
            assert task_mock.prepare_batch.delay.called

        # trigger celery task
        prepare_batch(batch.id)

        batch.refresh_from_db()

        assert org_qs.count() == 1
        assert usr_org_qs.count() == 2

        assert batch.info[0]["stats"][0] == 5
        assert batch.status == BatchStatus.PREPARED
        assert batch.prepared is not None

    @pytest.mark.django_db(transaction=True)
    def test_delete_organization(self, basic1, organizations):
        batch = BatchFactory(status=BatchStatus.PREPARED)

        usr_org_qs = UserOrganization.objects.filter(organization=organizations["standalone"])
        org_qs = Organization.objects.filter(pk=organizations["standalone"].pk)

        assert org_qs.count() == 1
        assert usr_org_qs.count() == 2

        CandidateFactory(
            batch=batch,
            content_object=organizations["standalone"],
            info={
                "model": "organizations.Organization",
                "stats": [
                    5,
                    {
                        "organizations.UserOrganization": 2,
                        "organizations.Organization": 1,
                        "core.DataSource": 1,
                        "publications.Platform": 1,
                    },
                ],
            },
        )

        with mock.patch("necronomicon.models.tasks") as task_mock:
            batch.plan_delete_batch_targets()
            assert task_mock.delete_batch_targets.delay.called

        # trigger celery task
        delete_batch_targets(batch.id)
        batch.refresh_from_db()

        assert org_qs.count() == 0
        assert usr_org_qs.count() == 0

        assert batch.info[0]["stats"][0] == 5
        assert batch.status == BatchStatus.DELETED
        assert batch.deleted is not None

    @pytest.mark.django_db(transaction=True)
    def test_prepare_platforms(self, basic1, platforms, credentials):
        batch = BatchFactory(status=BatchStatus.INITIAL)

        cred_qs = SushiCredentials.objects.filter(platform=platforms["standalone"])
        plat_qs = Platform.objects.filter(pk=platforms["standalone"].pk)

        assert plat_qs.count() == 1
        assert cred_qs.count() == 3

        CandidateFactory(batch=batch, content_object=platforms["standalone"])

        with mock.patch("necronomicon.models.tasks") as task_mock:
            batch.plan_prepare_batch()
            assert task_mock.prepare_batch.delay.called

        # trigger celery task
        prepare_batch(batch.id)
        batch.refresh_from_db()

        assert plat_qs.count() == 1
        assert cred_qs.count() == 3

        assert batch.info[0]["stats"][0] == 8
        assert batch.status == BatchStatus.PREPARED
        assert batch.prepared is not None

    @pytest.mark.django_db(transaction=True)
    def test_delete_platforms(self, basic1, platforms, credentials):
        batch = BatchFactory(status=BatchStatus.PREPARED)

        cred_qs = SushiCredentials.objects.filter(platform=platforms["standalone"])
        plat_qs = Platform.objects.filter(pk=platforms["standalone"].pk)

        assert plat_qs.count() == 1
        assert cred_qs.count() == 3

        CandidateFactory(
            batch=batch,
            content_object=platforms["standalone"],
            info={
                "model": "publications.Platform",
                "stats": [
                    8,
                    {
                        "sushi.CounterReportsToCredentials": 4,
                        "sushi.SushiCredentials": 3,
                        "publications.Platform": 1,
                    },
                ],
            },
        )

        with mock.patch("necronomicon.models.tasks") as task_mock:
            batch.plan_delete_batch_targets()
            assert task_mock.delete_batch_targets.delay.called

        # trigger celery task
        delete_batch_targets(batch.id)
        batch.refresh_from_db()

        assert plat_qs.count() == 0
        assert cred_qs.count() == 0

        assert batch.info[0]["stats"][0] == 8
        assert batch.status == BatchStatus.DELETED
        assert batch.deleted is not None

    def test_create_from_queryset(self, basic1, organizations, platforms):
        batch = Batch.create_from_queryset(Organization.objects.all())

        assert batch.candidates.count() == Organization.objects.count()
        assert Batch.create_from_queryset(Platform.objects.none()) is None

    def test_delete_outdated_stats(self, basic1, organizations):
        batch = BatchFactory(status=BatchStatus.INITIAL)
        CandidateFactory(batch=batch, content_object=organizations["standalone"])

        batch.plan_prepare_batch()
        prepare_batch(batch.id)
        batch.refresh_from_db()

        assert batch.status == BatchStatus.PREPARED

        Platform.objects.all().delete()  # Alter stats

        batch.plan_delete_batch_targets()
        delete_batch_targets(batch.id)
        batch.refresh_from_db()

        assert batch.status == BatchStatus.OUTDATED
        assert batch.deleted is None
        assert Organization.objects.filter(
            pk=organizations["standalone"].pk
        ).exists(), "Organiztion wasn't deleted"

    def test_delete_expired(self, basic1, organizations):
        with freeze_time(datetime(2020, 1, 1, 0, 0, 0)):
            batch = BatchFactory(status=BatchStatus.INITIAL)
            CandidateFactory(batch=batch, content_object=organizations["standalone"])

        with freeze_time(datetime(2020, 1, 3, 0, 0, 0)):
            batch.plan_prepare_batch()
            prepare_batch(batch.id)

        batch.refresh_from_db()

        assert batch.status == BatchStatus.PREPARED

        with freeze_time(datetime(2020, 1, 3, 0, 0, 0)):
            batch.plan_delete_batch_targets()
            delete_batch_targets(batch.id)
            batch.refresh_from_db()

        assert batch.status == BatchStatus.OUTDATED
        assert batch.deleted is None
        assert Organization.objects.filter(
            pk=organizations["standalone"].pk
        ).exists(), "Organiztion wasn't deleted"
