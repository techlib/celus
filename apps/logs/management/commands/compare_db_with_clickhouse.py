import logging
import sys
from collections import Counter
from time import time

from django.core.management.base import BaseCommand
from django.db.models import Sum
from hcube.api.models.aggregation import Sum as HSum

from logs.cubes import AccessLogCube, ch_backend
from logs.models import AccessLog

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = (
        'Compares the data from django db with configured clickhouse by importbatches and '
        'reports differences'
    )

    def handle(self, *args, **options):
        start = time()
        stats = Counter()

        in_db = (
            AccessLog.objects.values('import_batch_id', 'metric_id')
            .filter(report_type__materialization_spec__isnull=True)
            .order_by('import_batch_id', 'metric_id')
            .annotate(score=Sum('value'))
        )
        in_ch = ch_backend.get_records(
            AccessLogCube.query()
            .group_by('import_batch_id', 'metric_id')
            .order_by('import_batch_id', 'metric_id')
            .aggregate(score=HSum('value'))
        )

        def ch_next():
            try:
                return next(in_ch)
            except StopIteration:
                return None

        ch_rec = ch_next()
        for db_rec in in_db:
            db_ib_id = db_rec['import_batch_id']
            db_m_id = db_rec['metric_id']
            db_score = db_rec['score']
            if ch_rec and (db_ib_id, db_m_id) == (ch_rec.import_batch_id, ch_rec.metric_id):
                # we are on the same record
                if db_score != ch_rec.score:
                    print(f'!! {db_ib_id}, {db_m_id}: DB: {db_score}, CH: {ch_rec.score}')
                    stats['value mismatch'] += 1
                else:
                    stats['ok'] += 1
                ch_rec = ch_next()
            elif ch_rec and (db_ib_id, db_m_id) > (ch_rec.import_batch_id, ch_rec.metric_id):
                # this record is only in CH
                while ch_rec and (db_ib_id, db_m_id) > (ch_rec.import_batch_id, ch_rec.metric_id):
                    print(f'CH {ch_rec.import_batch_id}, {ch_rec.metric_id}: {ch_rec.score}')
                    stats['ch extra'] += 1
                    ch_rec = ch_next()
            else:
                # this record is only in DB
                print(f'DB {db_ib_id}, {db_m_id}: {db_score}')
                stats['db extra'] += 1

        logger.info('Duration: %.2f s, Stats: %s', time() - start, stats)
        if list(stats.keys()) != ['ok']:
            logger.error('FOUND DIFFERENCES BETWEEN DB AND CH!')
            sys.exit(100)
        logger.info('OK')
        sys.exit(0)
