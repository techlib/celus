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
