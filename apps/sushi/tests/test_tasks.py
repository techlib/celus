import pytest
from sushi.models import ImportBatch, SushiFetchAttempt
from sushi.tasks import delete_fetchattempts_and_related_importbatches_task

from test_fixtures.entities.fetchattempts import FetchAttemptFactory
from test_fixtures.entities.logs import ImportBatchFactory
from test_fixtures.scenarios.basic import *  # noqa


@pytest.mark.django_db
class TestSushiCredentialsTasks:
    @pytest.mark.parametrize('fa1_included', [True, False])
    @pytest.mark.parametrize('fa2_included', [True, False])
    @pytest.mark.parametrize('ib1_included', [True, False])
    @pytest.mark.parametrize('ib2_included', [True, False])
    def test_delete_fetchattempts_and_related_importbatches_task(
        self,
        fa1_included,
        fa2_included,
        ib1_included,
        ib2_included,
    ):
        fa1, fa2 = FetchAttemptFactory.create_batch(2)

        fa_pks = []
        if fa1_included:
            fa_pks.append(fa1.pk)
        if fa2_included:
            fa_pks.append(fa2.pk)

        ib1, ib2 = ImportBatchFactory.create_batch(2)

        if ib1_included:
            fa1.import_batch = ib1
            fa1.save()
        if ib2_included:
            fa2.import_batch = ib2
            fa2.save()

        delete_fetchattempts_and_related_importbatches_task(fa_pks)

        assert SushiFetchAttempt.objects.filter(pk=fa1.pk).exists() != fa1_included
        assert SushiFetchAttempt.objects.filter(pk=fa2.pk).exists() != fa2_included
        assert ImportBatch.objects.filter(pk=ib1.pk).exists() != (ib1_included and fa1_included)
        assert ImportBatch.objects.filter(pk=ib2.pk).exists() != (ib2_included and fa2_included)
