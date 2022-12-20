import logging

from django.core.management.base import BaseCommand
from django.db.transaction import atomic
from tags.logic.scopus_title_list import ScopusTitleListTagger
from tags.models import TaggingBatch

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Tags all titles with topics from scopus title list.'

    def add_arguments(self, parser):
        parser.add_argument('code_file')
        parser.add_argument('title_list_file')
        parser.add_argument(
            '-d',
            '--delete',
            action='store_true',
            help='Delete previous tagging batch only - do not tag again.',
            dest='just_delete',
        )
        parser.add_argument(
            '-l',
            '--level',
            help='Only use topics with this level.',
            dest='level',
            default=None,
            type=int,
        )

    @atomic
    def handle(self, *args, **options):
        try:
            batch = TaggingBatch.objects.get(internal_name='scopus-topics')
        except TaggingBatch.DoesNotExist:
            pass
        else:
            logger.warning('Deleting previous related tagging batch: %d', batch.pk)
            batch.delete()
        if options['just_delete']:
            return
        tagger = ScopusTitleListTagger(options['title_list_file'], options['code_file'])

        def progress_monitor(current, total):
            logger.info('Progress: %d / %d (%.1f %%)', current, total, current / total * 100)

        levels = ['Level {}'.format(options['level'])] if options['level'] else None
        if levels:
            logger.info('Only using level: %s', ', '.join(levels))
        tagger.tag_titles(progress_monitor=progress_monitor, levels=levels)
