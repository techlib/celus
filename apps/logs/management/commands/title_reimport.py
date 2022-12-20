import logging

from django.conf import settings
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Exists, F, OuterRef, Value
from django.db.models.functions import Concat
from django.db.transaction import atomic, on_commit
from logs.logic.clickhouse import resync_import_batch_with_clickhouse
from logs.logic.data_import import TitleManager
from logs.models import AccessLog, ImportBatch
from publications.logic.title_management import replace_title
from publications.models import Title

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = (
        'Helper script for reimport which fixes titles erroneously mixed together. It contains '
        'code for two stages of the process - preparation and cleanup.'
    )

    title_prefix = '_foo42_'

    def add_arguments(self, parser):
        parser.add_argument('--details', dest='details', action='store_true')
        parser.add_argument('--do-it', dest='do_it', action='store_true')
        parser.add_argument(
            'phase',
            choices=['prepare', 'cleanup', 'resolve_remaining'],
            help='Which phase should be run',
        )

    @atomic
    def handle(self, *args, **options):
        self.options = options
        if options['phase'] == 'prepare':
            self.prepare()
        elif options['phase'] == 'cleanup':
            self.cleanup()
        elif options['phase'] == 'resolve_remaining':
            self.resolve_remaining()
        if not options['do_it']:
            raise CommandError('Not doing anything - use --do-it to really make the changes')

    def prepare(self):
        """
        adds a prefix to all title names so that it will not be using during reimport and
        can be easily recognized afterwards.
        """
        if Title.objects.filter(name__startswith=self.title_prefix).exists():
            raise CommandError(
                f'Some title with "{self.title_prefix}" prefix already exists - the prepare phase '
                f'was already performed'
            )
        info = Title.objects.update(name=Concat(Value(self.title_prefix), F('name')))
        logger.info(f'Updated {info} records')

    def cleanup(self):
        """
        Remove all titles which are not references from elsewhere.
        """
        deleted = Title.objects.filter(
            ~Exists(AccessLog.objects.filter(target_id=OuterRef('pk')))
        ).delete()
        logger.info(f'Deleted: {deleted}')
        foo_count = Title.objects.filter(name__startswith=self.title_prefix).count()
        logger.info(f'Original titles with prefix still existing: {foo_count}')
        if foo_count:
            if self.options['details']:
                for title in Title.objects.filter(name__startswith=self.title_prefix).annotate(
                    al_count=Count('accesslog'),
                    ibs=ArrayAgg('accesslog__import_batch_id', distinct=True),
                ):
                    logger.info(f'{title.pk},{title.name},{title.al_count},{title.ibs}')
            else:
                logger.info(
                    'To get more info about these titles, run with --details. To resolve them '
                    '(merge with existing or rename), run the `resolve_remaining` phase.'
                )

    def resolve_remaining(self):
        """
        Go over all 'foobar' titles and:

        * rename them to the original name if no matching title exists
        * replace them by new title if it exists - without merging the IDs
        """
        ibs_to_resync = set()
        to_remove = set()
        renamed_count = 0
        tt2s = []
        for title in Title.objects.filter(name__startswith=self.title_prefix):
            name_clean = title.name[len(self.title_prefix) :]
            title_rec = TitleManager.title_to_titlerec(title)
            title_rec.name = name_clean
            tt2s.append((title, title_rec))

        tm = TitleManager()
        tm.prefetch_titles([title_rec for _title, title_rec in tt2s])
        for title, title_rec in tt2s:
            newer = tm.find_matching_title(title_rec)
            if newer:
                logger.debug(f'Replacing "{title}" (#{title.pk}) with #{newer.pk}')
                ibs_to_resync |= replace_title(title, newer.pk)
                to_remove.add(title.pk)
            else:
                logger.debug(f'Renaming "{title}" back to "{title_rec.name}"')
                title.name = title_rec.name
                title.save()
                renamed_count += 1
        if to_remove:
            logger.debug(
                'Removing replaced titles: %s', Title.objects.filter(pk__in=to_remove).delete()
            )

        def resync_clickhouse():
            if ibs_to_resync and settings.CLICKHOUSE_SYNC_ACTIVE:
                for ib in ImportBatch.objects.filter(pk__in=ibs_to_resync):
                    resync_import_batch_with_clickhouse(ib)

        on_commit(resync_clickhouse)

        logger.info('Renamed %d titles; replaced %d titles', renamed_count, len(to_remove))
        foo_count = Title.objects.filter(name__startswith=self.title_prefix).count()
        logger.info(f'Original titles with prefix still existing: {foo_count}')
