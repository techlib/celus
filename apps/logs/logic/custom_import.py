import typing
import statistics

from collections import Counter
from datetime import date
from functools import lru_cache

from core.logic.dates import parse_date_fuzzy
from core.models import User
from django.conf import settings
from django.db.transaction import atomic
from django.utils.timezone import now
from django.utils.translation import gettext as _
from logs.logic.data_import import import_counter_records
from logs.logic.materialized_reports import sync_materialized_reports_for_import_batch
from logs.models import ImportBatch, ManualDataUpload, MduState, OrganizationPlatform
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


def histograms_with_stats(
    attrs: typing.List[str], iterable
) -> typing.Tuple[typing.Dict[str, Counter], Counter]:
    histograms = {e: {} for e in attrs}
    cnt = Counter()
    for x in iterable:
        for attr in attrs:
            value = str(getattr(x, attr))
            rec = histograms[attr].get(value, {"sum": 0, "count": 0})
            rec["sum"] += x.value
            rec["count"] += 1
            histograms[attr][value] = rec
        cnt["sum"] += x.value
        cnt["count"] += 1
    return histograms, cnt


def custom_import_preflight_check(mdu: ManualDataUpload):
    histograms, counts = histograms_with_stats(['start', 'metric', 'title'], mdu.data_to_records())
    months = {
        k: {"new": v, "this_month": None, "prev_year_avg": None, "prev_year_month": 0}
        for k, v in histograms["start"].items()
    }

    # prepare month statistics
    related_months, used_metrics = mdu.related_months_data()

    for year_month, data in months.items():
        year, month, *_ = [int(e) for e in year_month.split('-')]
        last_year_month = f"{year - 1}-{month:02d}-01"
        last_year_months = {f"{year - 1}-{i:02d}-01" for i in range(1, 13)}
        data['this_month'] = related_months.get(year_month)

        # Display last year average only when all months contain data
        if last_year_months.issubset(related_months.keys()):
            data['prev_year_avg'] = {"sum": 0, "count": 0}
            for ymonth in last_year_months:
                data['prev_year_avg']['sum'] += related_months[ymonth]['sum']
                data['prev_year_avg']['count'] += related_months[ymonth]['count']
            data['prev_year_avg']['sum'] = round(data['prev_year_avg']['sum'] / 12)
            data['prev_year_avg']['count'] = round(data['prev_year_avg']['count'] / 12)
        else:
            data['prev_year_avg'] = None
        data['prev_year_month'] = related_months.get(last_year_month)

    return {
        'format_version': mdu.PREFLIGHT_FORMAT_VERSION,
        'celus_version': settings.CELUS_VERSION,
        'git_hash': settings.SENTRY_RELEASE,
        'generated': now().isoformat(),
        'log_count': counts["count"],
        'hits_total': counts["sum"],
        'months': months,
        'metrics': histograms["metric"],
        'used_metrics': used_metrics,
        'title_count': len(histograms["title"]),
    }


@atomic
def import_custom_data(
    mdu: ManualDataUpload, user: User, months: typing.Optional[typing.Iterable[str]] = None
) -> dict:
    """
    :param mdu:
    :param user:
    :param months: Can be used to limit which months of data will be loaded from the file -
                   see `import_counter_records` for more details how this works
    :return: import statistics
    """
    records = mdu.data_to_records()
    # TODO: the owner level should be derived from the user and the organization at hand
    import_batches, stats = import_counter_records(
        mdu.report_type,
        mdu.organization,
        mdu.platform,
        records,
        months=months,
        import_batch_kwargs=dict(user=user, owner_level=mdu.owner_level),
    )
    # explicitly connect the organization and the platform
    OrganizationPlatform.objects.get_or_create(platform=mdu.platform, organization=mdu.organization)
    mdu.import_batches.set(import_batches)
    mdu.mark_processed()  # this also saves the model

    for import_batch in import_batches:
        sync_materialized_reports_for_import_batch(import_batch)
    # the following could be used to debug the speed of this code chunk
    # from django.db import connection
    # qs = connection.queries
    # qs.sort(key=lambda x: -float(x['time']))
    # for q in qs[:3]:
    #     print(q['time'], q)
    return stats
