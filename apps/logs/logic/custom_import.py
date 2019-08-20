from datetime import date, datetime
import dateparser

from django.utils.translation import gettext as _

# en_month_matcher = re.compile(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})')
# iso_month_matcher = re.compile(r'(\d{4})-(\d{1,2})')


def col_name_to_month(row_name: str) -> date:
    """
    >>> col_name_to_month('Jan 2019')
    datetime.date(2019, 1, 1)
    >>> col_name_to_month('2019-02')
    datetime.date(2019, 2, 1)
    >>> col_name_to_month('prase') is None
    True
    """
    dt = dateparser.parse(row_name)  # type: datetime
    if not dt:
        return dt
    return dt.date().replace(day=1)


def custom_data_import_precheck(header, rows, expected_dimensions=('Institution',)) -> list:
    problems = []
    month_columns = []
    # check that we understand all the column names
    for i, col_name in enumerate(header):
        if col_name in expected_dimensions:
            pass
        else:
            month = col_name_to_month(col_name)
            if month is None:
                problems.append(_('Column name not understood: "{}"').format(col_name))
            else:
                month_columns.append(i)
    # check that there are numbers in the columns we expect them
    for i, row in enumerate(rows):
        for j in month_columns:
            cell = row[j]
            try:
                int(cell)
            except ValueError:
                problems.append(_('Value cannot be converted into integer, row {row}, '
                                  'column "{column}", value: "{value}"').
                                format(row=i+1, column=header[j], value=cell))
    return problems

