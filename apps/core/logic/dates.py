import re
import datetime
import calendar
from typing import Optional

import dateparser
from django.utils import timezone

month_matcher = re.compile(r'^(?P<year>\d{4})-(?P<month>\d{1,2})(-\d{1,2})?$')
counter_month_matcher = re.compile(r'^(?P<month>\w{3})-(?P<year>\d{2}(\d{2})?)$')


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


def parse_counter_month(text: str) -> Optional[datetime.date]:
    """
    Returns a date object extracted from date formatted according to the specification of COUNTER 5
    i. e. Mmm-YYYY. It also allows Mmm-YY to be more flexible
    :param text:
    :return:
    """
    if not text:
        return None
    m = counter_month_matcher.match(text)
    if m:
        year = int(m.group('year'))
        month = m.group('month')
        if year < 50:
            year += 2000
        elif 50 <= year < 100:
            year += 1900
        month_abbrs = list(calendar.month_abbr)
        if month not in month_abbrs:
            return None
        try:
            return datetime.date(year, month_abbrs.index(month), 1)
        except ValueError:
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


def this_month() -> datetime.date:
    # make sure that we are in current timezone
    # timezone.now() returns UTC
    return month_start(timezone.now().astimezone(timezone.get_current_timezone()))


def next_month() -> datetime.date:
    return month_start(this_month() + datetime.timedelta(days=32))


def last_month() -> datetime.date:
    return month_start(this_month() - datetime.timedelta(days=1))


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


def parse_date_fuzzy(date_str: str) -> Optional[datetime.date]:
    """
    Uses dateparser to try to parse a date. Uses only specific locales to make dateparser
    faster, so we extracted it as a function to use throughout the code
    """
    dt = dateparser.parse(date_str, languages=['en'])
    if not dt:
        return dt
    return dt.date()
