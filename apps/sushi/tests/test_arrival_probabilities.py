from math import floor

import pytest
from core.fake_data import DataSourceFactory
from freezegun import freeze_time
from logs.fake_data import ImportBatchFactory
from publications.fake_data import PlatformFactory
from publications.logic import arrival_probabilities
from publications.logic.arrival_probabilities import update_all_arrival_curves
from publications.models import DEFAULT_ARRIVAL_STATS, Platform

from ..fake_data import CredentialsFactory, FetchAttemptFactory


@pytest.mark.django_db
class TestGetArrivalProbabilities:
    @pytest.fixture()
    def setup(self):
        p1 = PlatformFactory.create(name="P1", source=DataSourceFactory())
        p2 = PlatformFactory.create(name="P2", source=DataSourceFactory())

        # create credentials
        credentials1 = CredentialsFactory(platform=p1, counter_version=5)
        credentials4 = CredentialsFactory(platform=p1, counter_version=5)
        credentials2 = CredentialsFactory(platform=p2, counter_version=5)

        # create sushi fetch attempts
        FetchAttemptFactory.create(
            credentials=credentials1,
            start_date="2020-01-01",
            end_date="2020-01-31",
            import_batch=ImportBatchFactory(),
            when_processed="2020-02-01 22:00",
        )

        FetchAttemptFactory.create(
            credentials=credentials1,
            start_date="2022-05-01",
            end_date="2022-05-30",
            import_batch=None,  # test if None batch will be ignored
            when_processed="2022-06-05 22:00",
        )

        FetchAttemptFactory.create(
            credentials=credentials1,
            start_date="2021-04-01",
            end_date="2021-04-30",
            import_batch=ImportBatchFactory(),
            when_processed="2021-05-15 22:00",
        )

        FetchAttemptFactory.create(
            credentials=credentials1,
            start_date="2021-08-01",
            end_date="2021-08-31",
            import_batch=ImportBatchFactory(),
            when_processed="2021-09-15 22:00",
        )

        FetchAttemptFactory.create(
            credentials=credentials1,
            start_date="2021-08-01",
            end_date="2021-08-31",
            import_batch=ImportBatchFactory(),
            when_processed="2021-09-22 22:00",  # should be ignored as there is lower value
        )

        FetchAttemptFactory.create(
            credentials=credentials4,  # test different credentials
            start_date="2021-08-01",  # for the same month
            end_date="2021-08-31",
            import_batch=ImportBatchFactory(),
            when_processed="2021-09-11 22:00",
        )

        # add 2nd platform
        FetchAttemptFactory.create(  # test of year-end
            credentials=credentials2,
            start_date="2021-12-01",
            end_date="2021-12-31",
            import_batch=ImportBatchFactory(),
            when_processed="2022-01-06 22:00",
        )

        FetchAttemptFactory.create(
            credentials=credentials2,
            start_date="2020-11-01",
            end_date="2020-11-30",
            import_batch=ImportBatchFactory(),
            when_processed="2020-12-28 22:00",
        )

        FetchAttemptFactory.create(
            credentials=credentials2,
            start_date="2020-11-01",
            end_date="2020-11-30",
            import_batch=None,
            when_processed="2020-12-15 22:00",
        )

        FetchAttemptFactory.create(
            credentials=credentials2,
            start_date="2023-01-01",
            end_date="2023-01-31",
            import_batch=ImportBatchFactory(),
            when_processed="2023-02-02 22:00",
        )
        return locals()

    def test_computation(self, setup, settings):
        # set the quantiles to something shorter for testing
        settings.SUSHI_ARRIVAL_STATS_QUANTILES = [0.1, 0.25, 0.5, 0.75, 0.9, 1]

        # test one platform
        p1 = setup["p1"]
        result = arrival_probabilities.get_probabilities(p1.pk, lookback_days=None)
        assert result[0] == 4  # n=4
        # don't want to compare floats, so floor them
        assert [floor(x) for x in result[1]] == [3, 8, 12, 14, 14, 14]

        # add 2nd platform
        p2 = setup["p2"]
        result2 = arrival_probabilities.get_probabilities(p2.pk, lookback_days=None)
        assert result2[0] == 3
        # don't want to compare floats, so floor them
        assert [floor(x) for x in result2[1]] == [2, 3, 5, 16, 23, 27]

        # test universal model
        uni_model1 = arrival_probabilities.get_probabilities(None, lookback_days=None)

        FetchAttemptFactory.create(
            credentials=CredentialsFactory(
                counter_version=4
            ),  # counter4 -> should be ignored in universal model
            start_date="2022-09-01",
            end_date="2022-09-30",
            import_batch=ImportBatchFactory(),
            when_processed="2022-10-02 22:00",
        )

        uni_model2 = arrival_probabilities.get_probabilities(None, lookback_days=None)
        # counter 4 platform should not change the universal model
        assert uni_model1 == uni_model2

        # test with lookback days - data from 2020 will be ignored
        with freeze_time("2022-01-01"):
            result3 = arrival_probabilities.get_probabilities(p1.pk, lookback_days=365)
            assert result3[0] == 3  # n=3
            assert [floor(x) for x in result3[1]] == [11, 12, 14, 14, 14, 14]

    def test_model_update(self, setup, settings):
        # set the quantiles to something shorter for testing
        settings.SUSHI_ARRIVAL_STATS_QUANTILES = [0.1, 0.25, 0.5, 0.75, 0.9, 1]

        p1: Platform = setup["p1"]
        assert (
            p1.sushi_arrival_stats["probabs"] == DEFAULT_ARRIVAL_STATS["probabs"]
        ), "default values"
        # test with threshold 10 - there is not enough data, so the data should be the same
        update_all_arrival_curves(attempt_count_threshold=10, lookback_days=None)
        p1.refresh_from_db()
        assert (
            p1.sushi_arrival_stats["probabs"] == DEFAULT_ARRIVAL_STATS["probabs"]
        ), "default values"

        # test with threshold 5 - there is enough data for generic model, but not for specific one
        update_all_arrival_curves(attempt_count_threshold=5, lookback_days=None)
        p1.refresh_from_db()

        assert (
            p1.sushi_arrival_stats["probabs"] == settings.SUSHI_ARRIVAL_STATS_QUANTILES
        ), "updated probabilities"
        assert p1.sushi_arrival_stats["source"] == "generic", "source should be generic"

        # test with threshold 3 - there is enough data for specific model
        update_all_arrival_curves(attempt_count_threshold=3, lookback_days=None)
        p1.refresh_from_db()
        assert p1.sushi_arrival_stats["source"] == "specific", "source should be specific"
