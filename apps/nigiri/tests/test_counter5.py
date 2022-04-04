from pathlib import Path

import pytest

from ..counter5 import Counter5ReportBase, Counter5TableReport, Counter5TRReport
from ..exceptions import SushiException


class TestCounter5Reading:
    def test_record_simple(self):
        reader = Counter5ReportBase()
        records = [
            e
            for e in reader.file_to_records(
                Path(__file__).parent / 'data/counter5/data_simple.json'
            )
        ]
        assert len(records) == 2
        assert records[0].title == 'Title1'
        assert records[0].metric == 'Total_Item_Investigations'
        assert records[0].value == 10
        assert records[0].start == '2019-05-01'
        assert records[0].end == '2019-05-31'
        assert records[0].dimension_data == {}
        assert records[1].value == 8
        # both records should have the same values for these attributes as they come from the
        # same item in the data
        for attr in ('title', 'start', 'end'):
            assert getattr(records[0], attr) == getattr(records[1], attr)

    def test_record_simple_tr(self):
        reader = Counter5TRReport()
        records = [
            e
            for e in reader.file_to_records(
                Path(__file__).parent / 'data/counter5/data_simple.json'
            )
        ]
        assert len(records) == 2
        assert records[0].value == 10
        # just test what is different in TR report
        assert records[0].dimension_data == {
            'Access_Type': 'OA_Gold',
            'Publisher': 'Pub1',
            'Access_Method': 'Regular',
            'YOP': '2009',
            'Section_Type': 'Chapter',
            'Data_Type': 'Book',
            'Platform': 'PlOne',
        }

    def test_reading_incorrect_data(self):
        """
        Test that data that do not have the proper format are not imported and raise an error
        """
        reader = Counter5TRReport()
        with pytest.raises(SushiException):
            [
                e
                for e in reader.file_to_records(
                    Path(__file__).parent / 'data/counter5/data_incorrect.json'
                )
            ]

    def test_reading_messed_up_data_proquest_ebooks(self):
        """
        The data from Proquest Ebook Central come messed up by being wrapped in an extra
        element 'body'.
        Check that we can properly parse this type of data.
        """
        reader = Counter5TRReport()
        records = [
            e
            for e in reader.file_to_records(
                Path(__file__).parent / 'data/counter5/5_TR_ProQuestEbookCentral.json'
            )
        ]
        assert len(records) == 30  # 7 titles, metrics - 1, 5, 5, 2, 6, 5, 6

    def test_reading_messed_up_data_proquest_ebooks_exception(self):
        """
        The data from Proquest Ebook Central come messed up by being wrapped in an extra
        element 'body'.
        Check that we can properly parse this type of data.
        """
        reader = Counter5TRReport()
        records = [
            e
            for e in reader.file_to_records(
                Path(__file__).parent / 'data/counter5/5_TR_ProQuestEbookCentral_exception.json'
            )
        ]
        assert len(records) == 0
        assert len(reader.errors) == 1
        error = reader.errors[0]
        assert error.code == '3030'

    def test_reading_messed_up_data_proquest_ebooks_exception_dr(self):
        """
        Another way to mess up the data - body is null and there are exceptions somewhere else :(
        """
        reader = Counter5TRReport()
        records = [
            e
            for e in reader.file_to_records(
                Path(__file__).parent / 'data/counter5/5_TR_ProQuestEbookCentral_exception.json'
            )
        ]
        assert len(records) == 0
        assert len(reader.errors) == 1
        error = reader.errors[0]
        assert error.code == '3030'

    def test_no_exception_no_data(self):
        """
        There is no exception in the header, but also no data (no data found for such period)
        """
        reader = Counter5TRReport()
        records = [
            e for e in reader.file_to_records(Path(__file__).parent / 'data/counter5/no_data.json')
        ]
        assert len(records) == 0
        assert len(reader.warnings) == 0
        assert not reader.queued

    def test_reading_messed_up_data_error_directly_in_data(self):
        """
        There is no header, just the error in the json
        """
        reader = Counter5TRReport()
        records = [
            e
            for e in reader.file_to_records(
                Path(__file__).parent / 'data/counter5/naked_error.json'
            )
        ]
        assert len(records) == 0
        assert len(reader.warnings) == 1
        assert reader.queued

    def test_reading_messed_up_data_error_list_directly_in_data(self):
        """
        There is no header, just the error in the json
        """
        reader = Counter5TRReport()
        records = [
            e
            for e in reader.file_to_records(
                Path(__file__).parent / 'data/counter5/naked_errors.json'
            )
        ]
        assert len(records) == 0
        assert len(reader.warnings) == 1
        assert len(reader.errors) == 1
        assert reader.queued

    def test_reading_strigified_exception(self):
        """
        Body is stringified json - header containing error
        """
        reader = Counter5TRReport()
        records = [
            e
            for e in reader.file_to_records(
                Path(__file__).parent / 'data/counter5/stringified_error.json'
            )
        ]
        assert len(records) == 0
        assert len(reader.errors) == 1
        error = reader.errors[0]
        assert str(error.code) == '2090'

    def test_severity_as_number(self):
        """
        Severity of error is a number
        """
        reader = Counter5TRReport()
        records = [
            e
            for e in reader.file_to_records(
                Path(__file__).parent / 'data/counter5/severity-number.json'
            )
        ]
        assert len(records) == 0
        assert len(reader.errors) == 1
        error = reader.errors[0]
        assert str(error.code) == '3010'
        assert str(error.severity.lower()) == 'error'

    def test_severity_is_missing(self):
        reader = Counter5TRReport()
        records = [
            e
            for e in reader.file_to_records(
                Path(__file__).parent / 'data/counter5/severity-missing.json'
            )
        ]
        assert len(records) == 0
        assert len(reader.errors) == 1
        error = reader.errors[0]
        assert str(error.code) == '3010'
        assert str(error.severity.lower()) == 'error'


@pytest.mark.django_db
class TestCounter5TableReports:
    def test_dr_csv(self):
        reader = Counter5TableReport()
        records = list(
            reader.file_to_records(Path(__file__).parent / 'data/counter5/counter5_table_dr.csv')
        )
        assert len(records) == 121
        assert records[0].value == 42
        assert records[-1].value == 1

    def test_dr_tsv(self):
        reader = Counter5TableReport()
        records = list(
            reader.file_to_records(Path(__file__).parent / 'data/counter5/counter5_table_dr.tsv')
        )
        assert len(records) == 121
        assert records[0].value == 42
        assert records[-1].value == 1

    @pytest.mark.parametrize(
        ['rt', 'count', 'first_number'], [('PR', 42, 10), ('TR', 24, 100), ('DR', 30, 1),]
    )
    def test_official_example(self, rt, count, first_number):
        """
        Takes slightly modified version of the official example reports from COUNTER and tries
        to read them.
        """
        reader = Counter5TableReport()
        records = list(
            reader.file_to_records(
                Path(__file__).parent / f'data/counter5/COUNTER_R5_Report_Examples_{rt}.csv'
            )
        )
        assert len(records) == count
        assert records[0].value == first_number
