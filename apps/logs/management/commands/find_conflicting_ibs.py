import logging
from collections import Counter
from time import time

from django.contrib.postgres.aggregates import ArrayAgg
from django.core.management.base import BaseCommand
from django.db.models import Count, Exists, OuterRef

from logs.logic.materialized_interest import remove_interest
from logs.models import AccessLog, ImportBatch, ManualDataUploadImportBatch, ReportType
from organizations.models import Organization
from publications.models import Platform
from sushi.models import SushiFetchAttempt

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Finds all import batches which have conflicting IBs'

    def handle(self, *args, **options):
        start = time()
        stats = Counter()
        orgs = {org.pk: org for org in Organization.objects.all()}
        platforms = {pl.pk: pl for pl in Platform.objects.all()}
        rts = {rt.pk: rt for rt in ReportType.objects.all()}

        qs = (
            ImportBatch.objects.all()
            .values('platform_id', 'organization_id', 'report_type_id', 'date')
            .annotate(ib_count=Count('id'), ib_ids=ArrayAgg('id'))
            .filter(ib_count__gt=1)
        )
        for i, rec in enumerate(qs):
            ibs = ImportBatch.objects.filter(id__in=rec['ib_ids']).annotate(
                has_fa=Exists(SushiFetchAttempt.objects.filter(import_batch_id=OuterRef('id'))),
                has_mdu=Exists(
                    ManualDataUploadImportBatch.objects.filter(import_batch_id=OuterRef('id'))
                ),
                has_als=Exists(AccessLog.objects.filter(import_batch_id=OuterRef('id'))),
            )
            if (
                len([ib.id for ib in ibs if ib.has_als]) == 1
                and len([ib.id for ib in ibs if ib.has_als and ib.has_fa]) == 1
            ):
                # we only take as solvable those where only one IB has data and that IB also has a
                # fetch attempt
                stats['solvable'] += 1
                logger.info('IB set #%s: Solvable', i)
                for ib in ibs:
                    logger.debug(
                        "  %s: %d: fa: %s, mdu: %s",
                        'keep  ' if ib.has_als else 'delete',
                        ib.pk,
                        ib.has_fa,
                        ib.has_mdu,
                    )
            else:
                stats['not solvable'] += 1
                logger.error(
                    'IB set #%s: Not solvable (date: %s, org: %s, pl: %s, rt: %s)',
                    i,
                    rec['date'],
                    orgs[rec['organization_id']].name,
                    platforms[rec['platform_id']].name,
                    rts[rec['report_type_id']].short_name,
                )
                for ib in ibs:
                    logger.debug(
                        "  %d: als: %s, fa: %s, mdu: %s",
                        ib.pk,
                        ib.has_als,
                        ib.has_fa,
                        [(mdu.pk, mdu.state) for mdu in ib.mdu.all()] if ib.has_mdu else None,
                    )
        logger.info('Duration: %s, Stats: %s', time() - start, stats)
