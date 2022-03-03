import typing
from collections import Counter
from datetime import date
from functools import lru_cache

from django.db.transaction import atomic
from django.utils.translation import gettext as _

from core.logic.dates import parse_date_fuzzy
from logs.logic.data_import import import_counter_records
from logs.logic.materialized_reports import sync_materialized_reports_for_import_batch
from logs.models import ImportBatch, ManualDataUpload, OrganizationPlatform
from nigiri.counter5 import CounterRecord


@lru_cache
def col_name_to_month(row_name: str) -> typing.Optional[date]:
    """
    >>> col_name_to_month('Jan 2019')
    datetime.date(2019, 1, 1)
    >>> col_name_to_month('2019-02')
    datetime.date(2019, 2, 1)
    >>> col_name_to_month('prase') is None
    True
    """
    _date = parse_date_fuzzy(row_name)
    if _date:
        return _date.replace(day=1)
    return None


def custom_data_import_precheck(
    header, rows, expected_dimensions=('Institution', 'Source', 'Title', 'Metric')
) -> list:
    problems = []
    month_columns = []
    # check that we understand all the column names
    for i, col_name in enumerate(header):
        if col_name in expected_dimensions:
            pass
        else:
            month = parse_date_fuzzy(col_name)
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
                problems.append(
                    _(
                        'Value cannot be converted into integer, row {row}, '
                        'column "{column}", value: "{value}"'
                    ).format(row=i + 1, column=header[j], value=cell)
                )
    return problems


DEFAULT_COLUMN_MAP = {
    'Metric': 'metric',
    'Organization': 'organization',
    'Source': 'title',
    'Platform': 'platform_name',
    'Title': 'title',
}


def custom_data_to_records(
    records: [dict], column_map=None, extra_dims=None, initial_data=None
) -> typing.Generator[CounterRecord, None, None]:
    # prepare the keyword arguments
    if initial_data is None:
        initial_data = {}
    if column_map is None:
        column_map = DEFAULT_COLUMN_MAP
    if extra_dims is None:
        extra_dims = []
    # process the records
    result = []
    for record in records:
        implicit_dimensions = {}
        explicit_dimensions = {}
        monthly_values = {}
        for key, value in record.items():
            month = col_name_to_month(key)
            if month:
                monthly_values[month] = int(value)
            else:
                if key in column_map:
                    implicit_dimensions[column_map[key]] = value
                elif key in extra_dims:
                    explicit_dimensions[key] = value
                else:
                    raise KeyError(
                        _('We don\'t know how to interpret the column "{column}"').format(
                            column=key
                        )
                    )
        # we put initial data into the data we read - these are usually dimensions that are fixed
        # for the whole import and are not part of the data itself
        for key, value in initial_data.items():
            if key not in implicit_dimensions:
                implicit_dimensions[key] = value  # only update if the value is not present
        for month, value in monthly_values.items():
            result.append(
                CounterRecord(
                    value=value,
                    start=month,
                    dimension_data=explicit_dimensions,
                    **implicit_dimensions,
                )
            )
    return (e for e in result)  # TODO convert this into a propper generator


def histogram(iterable) -> Counter:
    out = Counter()
    for x in iterable:
        out[x] += 1
    return out


def histogram_with_count(iterable) -> Counter:
    out = Counter()
    for x, count in iterable:
        out[x] += count
    return out


def custom_import_preflight_check(mdu: ManualDataUpload):
    records = list(mdu.data_to_records())  # type: [CounterRecord]
    month_to_count = histogram_with_count([(str(record.start), record.value) for record in records])
    clashing_months = (
        ImportBatch.objects.filter(
            report_type=mdu.report_type,
            platform=mdu.platform,
            organization=mdu.organization,
            date__in=month_to_count.keys(),
        )
        .values_list('date', flat=True)
        .distinct()
    )
    can_import = not clashing_months
    return {
        'log_count': len(records),
        'hits_total': sum((record.value for record in records), 0),
        'months': month_to_count,
        'clashing_months': clashing_months,
        'metrics': histogram_with_count([(record.metric, record.value) for record in records]),
        'titles': histogram_with_count([(record.title, record.value) for record in records]),
        'can_import': can_import,
    }


@atomic
def import_custom_data(mdu: ManualDataUpload, user) -> dict:
    records = mdu.data_to_records()
    # TODO: the owner level should be derived from the user and the organization at hand
    import_batches, stats = import_counter_records(
        mdu.report_type,
        mdu.organization,
        mdu.platform,
        records,
        import_batch_kwargs=dict(user=user, owner_level=mdu.owner_level),
    )
    # explicitly connect the organization and the platform
    OrganizationPlatform.objects.get_or_create(platform=mdu.platform, organization=mdu.organization)
    mdu.import_batches.set(import_batches)
    mdu.mark_processed()
    for import_batch in import_batches:
        sync_materialized_reports_for_import_batch(import_batch)
    # the following could be used to debug the speed of this code chunk
    # qs = connection.queries
    # qs.sort(key=lambda x: -float(x['time']))
    # for q in qs[:3]:
    #     print(q['time'], q)
    return stats
