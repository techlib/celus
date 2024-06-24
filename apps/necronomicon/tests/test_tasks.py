from datetime import datetime

import pytest
from freezegun import freeze_time
from necronomicon.fake_data import BatchFactory
from necronomicon.models import Batch, BatchStatus
from necronomicon.tasks import clean_expired


@pytest.mark.django_db
class TestTaks:
    def test_clean_expired(self):
        with freeze_time(datetime(2020, 1, 1, 0, 0, 0)):
            BatchFactory(status=BatchStatus.INITIAL)
            BatchFactory(status=BatchStatus.PREPARING)
            BatchFactory(status=BatchStatus.PREPARED)
            BatchFactory(status=BatchStatus.DELETE)
            BatchFactory(status=BatchStatus.OUTDATED)
            deleted_batch = BatchFactory(status=BatchStatus.DELETED)

        with freeze_time(datetime(2020, 1, 1, 23, 59, 59)):
            clean_expired()
            assert Batch.objects.count() == 6, "Not expired yet - all present"

        with freeze_time(datetime(2020, 1, 2, 0, 0, 1)):
            clean_expired()
            assert Batch.objects.count() == 1, "All except one are expired"
            assert Batch.objects.last().pk == deleted_batch.pk
