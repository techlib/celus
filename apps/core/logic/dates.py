import re
import datetime
import calendar
from typing import Optional

month_matcher = re.compile(r'^(?P<year>\d{4})-(?P<month>\d{1,2})(-\d{1,2})?$')


def parse_month(text: str) -> Optional[datetime.date]:
    """
    Return a date object representing the first day of a month specified as text in iso or
    iso-like format
    """
    if not text:
        return None
    m = month_matcher.match(str(text).strip())
    if m:
        year = int(m.group('year'))
        month = int(m.group('month'))
        try:
            return datetime.date(year, month, 1)
        except ValueError:
            return None
    return None


def month_end(date: datetime.date) -> datetime.date:
    """
    Returns the last day in a month
    :param date:
    :return:
    """
    wd, last = calendar.monthrange(date.year, date.month)
    return datetime.date(date.year, date.month, last)


def month_start(date: datetime.date) -> datetime.date:
    if isinstance(date, datetime.datetime):
        return date.replace(day=1).date()
    return date.replace(day=1)


def date_range_from_params(params: dict) -> (datetime.date, datetime.date):
    """
    Returns start and end dates based on data provided in the params dict.
    This dict will typically be the GET dict from a request
    :param params:
    :return:
    """
    start_date = parse_month(params.get('start'))
    end_date = parse_month(params.get('end'))
    if end_date:
        end_date = month_end(end_date)
    return start_date, end_date


def date_filter_from_params(params: dict, key_start='', str_date=False) -> dict:
    """
    Returns dict with params suitable for the filter method of an object specifying dates
    as the are given in the params dict. This dict will typically be the GET dict from a request
    :param params:
    :param key_start: when give, the dict keys will have this value prepended
    :param str_date: when True, dates will be converted to strings
    :return:
    """
    result = {}
    start_date = parse_month(params.get('start'))
    if start_date:
        if str_date:
            start_date = str(start_date)
        result[key_start + 'date__gte'] = start_date

    end_date = parse_month(params.get('end'))
    if end_date:
        end_date = month_end(end_date)
        if str_date:
            end_date = str(end_date)
        result[key_start + 'date__lte'] = end_date
    return result


def parse_date(date_str: str) -> datetime.date:
    """ Converts '2020-01-01' to date(2020, 1, 1)

    raises an exception if string is not in given format

    :param date_str: string in `YYYY-mm-dd` format
    """
    return datetime.datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=None).date()
