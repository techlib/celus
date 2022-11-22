import logging
import os
from collections import Counter
from time import time

from django.contrib.postgres.aggregates import ArrayAgg
from django.core.management.base import BaseCommand
from django.db.models import Count, Exists, OuterRef

from logs.logic.materialized_interest import remove_interest
from logs.logic.reimport import reimport_import_batch_with_fa
from logs.models import AccessLog, ImportBatch, ManualDataUploadImportBatch, ReportType
from organizations.models import Organization
from publications.models import Platform
from sushi.models import SushiFetchAttempt

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Finds all import batches which have conflicting IBs'

    def add_arguments(self, parser):
        parser.add_argument('--fix-it', dest='fixit', action='store_true')
        parser.add_argument(
            '--force-fix-it',
            dest='force_fixit',
            action='store_true',
            help='Force fix it, even if it is not solvable - remove all ibs except the one with '
            'the most als',
        )

    def handle(self, *args, **options):
        start = time()
        stats = Counter()
        orgs = {org.pk: org for org in Organization.objects.all()}
        platforms = {pl.pk: pl for pl in Platform.objects.all()}
        rts = {rt.pk: rt for rt in ReportType.objects.all()}
        fixit = options['fixit'] or options['force_fixit']

        qs = (
            ImportBatch.objects.all()
            .order_by()  # remove default ordering
            .values('platform_id', 'organization_id', 'report_type_id', 'date')
            .annotate(ib_count=Count('id'), ib_ids=ArrayAgg('id'))
            .filter(ib_count__gt=1)
        )
        to_delete = []
        for i, rec in enumerate(qs):
            ibs = ImportBatch.objects.filter(id__in=rec['ib_ids']).annotate(
                has_fa=Exists(SushiFetchAttempt.objects.filter(import_batch_id=OuterRef('id'))),
                has_mdu=Exists(
                    ManualDataUploadImportBatch.objects.filter(import_batch_id=OuterRef('id'))
                ),
                has_als=Exists(AccessLog.objects.filter(import_batch_id=OuterRef('id'))),
            )
            for ib in ibs:
                if ib.has_fa:
                    ib.has_source_file = os.path.isfile(ib.sushifetchattempt.data_file.path)
                else:
                    ib.has_source_file = False
            if (
                len([ib.id for ib in ibs if ib.has_als]) == 1
                and len([ib.id for ib in ibs if ib.has_als and ib.has_fa]) == 1
            ):
                # we only take as solvable those where only one IB has data and that IB also has a
                # fetch attempt
                stats['removable'] += 1
                logger.info('IB set #%s: Removable', i)
                for ib in ibs:
                    logger.debug(
                        "  %s: %d: fa: %s, mdu: %s, als: %s ",
                        'keep  ' if ib.has_als else 'delete',
                        ib.pk,
                        ib.has_fa,
                        ib.has_mdu,
                        ib.has_als,
                    )
                    if not ib.has_als:
                        to_delete.append(ib.pk)
            elif any(ib.has_fa and ib.has_source_file for ib in ibs):
                # if there is at least one with a fetch attempt, we can remove the others
                # and reimport
                stats['reimportable'] += 1
                logger.info(
                    'IB set #%s: Reimportable (date: %s, org: %s, pl: %s, rt: %s)',
                    i,
                    rec['date'],
                    orgs[rec['organization_id']].name,
                    platforms[rec['platform_id']].name,
                    rts[rec['report_type_id']].short_name,
                )
                # we prefer the biggest file even though it may not be the best measure
                reimportable = [
                    (ib.sushifetchattempt.file_size, ib.pk, ib)
                    for ib in ibs
                    if ib.has_fa and ib.has_source_file
                ]
                reimportable.sort(reverse=True)
                to_reimport = reimportable[0][2]
                for ib in ibs:
                    logger.debug(
                        "  %s:  %d: als: %s, fa: %s, mdu: %s; filesize: % 7d (%s)",
                        'keep  ' if ib is to_reimport else 'delete',
                        ib.pk,
                        ib.has_als,
                        ib.has_fa,
                        [(mdu.pk, mdu.state) for mdu in ib.mdu.all()] if ib.has_mdu else None,
                        ib.sushifetchattempt.file_size if ib.has_fa else 0,
                        ib.sushifetchattempt.data_file.name if ib.has_fa else '',
                    )
                    if ib is not to_reimport and fixit:
                        ib.delete()
                if fixit:
                    reimport_import_batch_with_fa(to_reimport)
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
                        "  %d: als: %s, fa: %s, mdu: %s, al_count: %d, has_source_file: %s (%s)",
                        ib.pk,
                        ib.has_als,
                        ib.has_fa,
                        [(mdu.pk, mdu.state) for mdu in ib.mdu.all()] if ib.has_mdu else None,
                        ib.accesslog_set.count(),
                        ib.has_source_file,
                        ib.sushifetchattempt.data_file.name if ib.has_fa else '',
                    )
                if options['force_fixit']:
                    # we keep the one with the most access logs
                    sorted_ibs = [(ib.accesslog_set.count(), ib.pk, ib) for ib in ibs]
                    sorted_ibs.sort(reverse=True)
                    to_keep = sorted_ibs[0][2]
                    ImportBatch.objects.filter(
                        id__in=[ib.pk for ib in ibs if ib is not to_keep]
                    ).delete()
                    logger.info('  IBs deleted: %s', [ib.pk for ib in ibs if ib is not to_keep])
                    logger.info('  IB kept: %s', to_keep.pk)
        logger.info('Duration: %s, Stats: %s', time() - start, stats)
        if fixit:
            logger.info('Deleting %d IBs', len(to_delete))
            ImportBatch.objects.filter(pk__in=to_delete).delete()
        else:
            logger.info(
                'Not deleting anything, use --fix-it to actually delete.\n'
                'Using --force-fix-it will fix even the unsolvable ones by deleting all IBs '
                'except the one with the most als.'
            )
