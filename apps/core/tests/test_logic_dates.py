from datetime import date

import pytest

from core.logic.dates import month_end, parse_counter_month
from core.logic.dates import parse_month


class TestParseMonth:
    def test_parse_valid(self):
        assert parse_month('2019-02') == date(2019, 2, 1)
        assert parse_month('2019-02-03') == date(2019, 2, 1)
        assert parse_month('1123-02-28') == date(1123, 2, 1)
        assert parse_month('2019-01-40') == date(2019, 1, 1)  # 40 is ok - day does not matter

    def test_parse_invalid(self):
        assert parse_month('2019-13-02') is None
        assert parse_month('XXXX-01-01') is None
        assert parse_month(None) is None


class TestMonthEnd:
    @pytest.mark.parametrize(
        'value, result',
        [
            (date(2019, 2, 1), date(2019, 2, 28)),
            (date(2019, 2, 15), date(2019, 2, 28)),
            (date(2019, 7, 15), date(2019, 7, 31)),
            (date(2019, 7, 31), date(2019, 7, 31)),
            (date(2020, 2, 1), date(2020, 2, 29)),
        ],
    )
    def test_month_end(self, value, result):
        assert month_end(value) == result


class TestParseCounterMonth:
    @pytest.mark.parametrize(
        ['text', 'output'],
        [
            ('Jun-2020', date(2020, 6, 1)),
            ('Jun-20', date(2020, 6, 1)),
            ('Jul-89', date(1989, 7, 1)),
            ('Apr-1234', date(1234, 4, 1)),
            ('Dec-2080', date(2080, 12, 1)),
            ('Foo-2020', None),
            ('adfjldskfj', None),
        ],
    )
    def test_parse(self, text, output):
        assert parse_counter_month(text) == output
