import datetime
import logging
import typing

from collections import Counter

from dateutil.relativedelta import relativedelta


from django.db import models
from django.db.models import Value as V
from django.db.models.functions import Concat
from logs.models import AccessLog, ImportBatch, ReportType
from organizations.models import Organization
from publications.models import Platform


logger = logging.getLogger(__name__)


def get_months(start: datetime.date, end: datetime.date) -> typing.List[typing.Tuple[int, int]]:
    start = start.replace(day=1)
    end = end.replace(day=1)
    res = []
    it = start
    while it <= end:
        res.append((it.year, it.month))
        it += relativedelta(months=1)

    return res


def get_conflicts(
    date, organization, platform, report_type, ib_pks
) -> typing.Optional[typing.List[int]]:
    year, month = date
    start_date = datetime.date(year=year, month=month, day=1)
    end_date = start_date + relativedelta(months=1)

    qs = (
        AccessLog.objects.filter(date__gte=start_date, date__lt=end_date, import_batch__in=ib_pks,)
        .values('import_batch', 'import_batch__created')
        .annotate(count=models.Count('pk'), score=models.Sum('value'),)
        .filter(count__gt=0)
    )

    non_empty = list(qs)
    for rec in non_empty:
        # we must add the min, max dates here because the previous query is already date filtered
        rec.update(
            AccessLog.objects.filter(import_batch_id=rec['import_batch']).aggregate(
                min_date=models.Min('date'), max_date=models.Max('date')
            )
        )

    # Only one IB should contain data
    # Otherwise data are mixed from different import batches
    if len(non_empty) > 1:
        return non_empty
    else:
        return None


def print_conflicts(
    organization_pk: typing.Optional[int] = None,
    platform_pk: typing.Optional[int] = None,
    report_type_pk: typing.Optional[int] = None,
):
    ib_filter = {}
    if platform_pk:
        ib_filter["platform_id"] = platform_pk
    if organization_pk:
        ib_filter["organization_id"] = organization_pk
    if report_type_pk:
        ib_filter["report_type_id"] = report_type_pk

    # query db for relevent input batches
    # TODO we could optimize import batch by storing date ranges directly to ImportBatch
    import_batches = (
        ImportBatch.objects.annotate(
            start=models.Min('accesslog__date'), end=models.Max('accesslog__date'),
        )
        .filter(start__isnull=False, end__isnull=False, **ib_filter)
        .values_list('pk', 'platform_id', 'organization_id', 'report_type_id', 'start', 'end')
        .order_by('platform', 'organization', 'report_type')
    )

    overlap = {}
    prev_por = None

    # find overlaping batches
    for record in import_batches.iterator():
        pk, platform, organization, report_type, start, end = record
        por = (platform, organization, report_type)
        if por != prev_por:
            # new report
            overlap[por] = {}
            prev_por = por

        for date in get_months(start, end):
            pks = overlap[por].get(date, [])
            pks.append(pk)
            overlap[por][date] = pks

    counter = Counter()

    for por, record in overlap.items():
        platform, organization, report_type = por

        header_printed = False
        for date, ib_pks in record.items():
            counter["total"] += 1
            if len(ib_pks) > 1:
                counter["overlapping"] += 1
                conflicts = get_conflicts(date, organization, platform, report_type, ib_pks)
                if conflicts:
                    counter["conflicts"] += 1
                    report_type_obj = ReportType.objects.get(pk=report_type)

                    if not header_printed:
                        platform_obj = Platform.objects.get(pk=platform)
                        organization_obj = Organization.objects.get(pk=organization)
                        print(
                            f"## {platform_obj}({platform_obj.pk}) - "
                            f"{organization_obj}({organization_obj.pk})"
                        )
                        header_printed = True
                    start = f"{date[0]:04}-{date[1]:02}|{report_type_obj}"
                    # sort conflicts by pk so that oldest batch goes first
                    conflicts.sort(key=lambda x: x['import_batch'])
                    for i, c in enumerate(conflicts):
                        if i != 0:
                            start = len(start) * " "
                        next_c = conflicts[i + 1] if i < len(conflicts) - 1 else None
                        fully_included = (
                            (
                                c['min_date'] >= next_c['min_date']
                                and c['max_date'] <= next_c['max_date']
                            )
                            if next_c
                            else None
                        )
                        included = ' '
                        if fully_included:
                            counter['fully included'] += 1
                            included = 'Y'
                        elif fully_included is False:
                            counter['not fully included'] += 1
                            included = 'N'
                        ib_date = c["import_batch__created"].date()
                        conflict_text = (
                            '#{import_batch:5} (recs:{count:5}, score:{score:6}, {ib_date}) '
                            'replacable:{included} [{min_date} - {max_date}]'.format(
                                ib_date=ib_date, included=included, **c
                            )
                        )
                        print(f"{start}: {conflict_text}")

        if header_printed:
            print()

    print()
    print("Stats")
    print(counter)
