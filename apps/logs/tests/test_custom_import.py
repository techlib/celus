from datetime import date

import pytest

from logs.logic.custom_import import custom_data_to_records
from logs.models import ReportType, AccessLog, DimensionText, ImportBatch
from publications.models import Platform, Title

from ..logic.data_import import import_counter_records
from organizations.tests.conftest import organizations


@pytest.mark.django_db
class TestCustomImport(object):

    """
    Tests functionality of the logic.custom_import module
    """

    def test_custom_data_to_records_1(self):
        data = [
            {'Metric': 'M1', 'Jan 2019': 10, 'Feb 2019': 7, 'Mar 2019': 11},
            {'Metric': 'M2', 'Jan 2019':  1, 'Feb 2019': 2, 'Mar 2019':  3},
        ]
        records = custom_data_to_records(data)
        assert len(records) == 6
        for record in records:
            assert record.value in (1, 2, 3, 7, 10, 11)
            assert record.start in (date(2019, 1, 1), date(2019, 2, 1), date(2019, 3, 1))
            if record.value in (10, 7, 11):
                assert record.metric == 'M1'
                if record.start == date(2019, 1, 1):
                    assert record.value == 10
            else:
                assert record.metric == 'M2'

    def test_custom_data_to_records_with_init_data(self):
        data = [
            {'MetricXX': 'M1', 'Jan 2019': 10, 'Feb 2019': 7, 'Mar 2019': 11},
            {'MetricXX': 'M2', 'Jan 2019':  1, 'Feb 2019': 2, 'Mar 2019':  3},
        ]
        records = custom_data_to_records(data, initial_data={'platform_name': 'PLA1'},
                                         column_map={'MetricXX': 'metric'})
        assert len(records) == 6
        for record in records:
            assert record.value in (1, 2, 3, 7, 10, 11)
            assert record.platform_name == 'PLA1'
            assert record.start in (date(2019, 1, 1), date(2019, 2, 1), date(2019, 3, 1))
            if record.value in (10, 7, 11):
                assert record.metric == 'M1'
                if record.start == date(2019, 1, 1):
                    assert record.value == 10
            else:
                assert record.metric == 'M2'
