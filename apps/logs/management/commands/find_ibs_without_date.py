import logging
from collections import Counter
from time import time

from django.core.management.base import BaseCommand
from django.db.models import Exists, OuterRef
from logs.models import AccessLog, ImportBatch, ManualDataUploadImportBatch, ReportType
from organizations.models import Organization
from publications.models import Platform
from sushi.models import SushiFetchAttempt

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Finds all import batches which do not have date - the are remnants of old data'

    def add_arguments(self, parser):
        parser.add_argument('--fix-it', dest='fixit', action='store_true')

    def handle(self, *args, **options):
        start = time()
        stats = Counter()
        orgs = {org.pk: org for org in Organization.objects.all()}
        platforms = {pl.pk: pl for pl in Platform.objects.all()}
        rts = {rt.pk: rt for rt in ReportType.objects.all()}

        ibs = ImportBatch.objects.filter(date__isnull=True).annotate(
            has_fa=Exists(SushiFetchAttempt.objects.filter(import_batch_id=OuterRef('id'))),
            has_mdu=Exists(
                ManualDataUploadImportBatch.objects.filter(import_batch_id=OuterRef('id'))
            ),
            has_als=Exists(AccessLog.objects.filter(import_batch_id=OuterRef('id'))),
        )
        for i, ib in enumerate(ibs):
            if ib.has_als:
                stats['not solvable'] += 1
                logger.error(
                    "Not solvable:  %d: als: %s, fa: %s, mdu: %s",
                    ib.pk,
                    ib.has_als,
                    ib.has_fa,
                    [(mdu.pk, mdu.state) for mdu in ib.mdu.all()] if ib.has_mdu else None,
                )
            else:
                stats['solvable'] += 1
                logger.debug(
                    "Solvable:  %d: fa: %s, mdu: %s   (created: %s, org: %s, pl: %s, rt: %s)",
                    ib.pk,
                    ib.has_fa,
                    ib.has_mdu,
                    ib.created.date(),
                    orgs[ib.organization_id].name,
                    platforms[ib.platform_id].name,
                    rts[ib.report_type_id].short_name,
                )

        logger.info('Duration: %s, Stats: %s', time() - start, stats)
        if options['fixit']:
            logger.info('Deleting solvable IBs')
            ibs.filter(has_als=False).delete()
        else:
            logger.info('Not deleting solvable IBs, use --fix-it to do so')
