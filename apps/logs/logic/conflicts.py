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
        .annotate(count=models.Count('pk'), score=models.Sum('value'))
        .filter(count__gt=0)
    )

    non_empty = list(qs)

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
                            f"## {platform_obj}({platform_obj.pk}) - {organization_obj}({organization_obj.pk})"
                        )
                        header_printed = True

                    conflict_text = '; '.join(
                        f'#{c["import_batch"]} (recs:{c["count"]}, score:{c["score"]}, '
                        f'{c["import_batch__created"].date()})'
                        for c in conflicts
                    )
                    print(f"{date[0]:04}-{date[1]:02}|{report_type_obj}: {conflict_text}")

        if header_printed:
            print()

    print()
    print("Stats")
    print(counter)
