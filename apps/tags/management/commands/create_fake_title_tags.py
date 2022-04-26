import logging
import random
from collections import Counter
from itertools import cycle

from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from publications.models import Title
from tags.logic.fake_data import TagForTitleFactory, TitleTagFactoryExistingTitles
from tags.models import TagClass, TitleTag

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Creates tags with a different number of tagged titles'

    BATCH_SIZES = [10, 100, 1000, 10_000, 100_000]

    def add_arguments(self, parser):
        parser.add_argument(
            '-d', dest='delete_existing', action='store_true', help='Delete existing tags'
        )
        parser.add_argument('-c', dest='tag_count', type=int, default=10)
        parser.add_argument('-l', dest='tag_class', type=str, default=None)

    @atomic
    def handle(self, *args, **options):
        stats = Counter()
        if options['delete_existing']:
            logger.warning('Deleted existing stuff: %s', TagClass.objects.all().delete())
        size_gen = cycle(self.BATCH_SIZES)
        tc = None
        all_title_ids = list(Title.objects.all().order_by('pk').values_list('pk', flat=True))
        if tag_class := options['tag_class']:
            if tag_class.isdigit():
                tc = TagClass.objects.get(pk=tag_class)
            else:
                tc, _ = TagClass.objects.get_or_create(name=tag_class)
            print(f'Using tag class "{tc}" for all created tags')
        for i in range(options['tag_count']):
            tag = TagForTitleFactory.create(tag_class=tc) if tc else TagForTitleFactory.create()
            stats['tags'] += 1
            count = next(size_gen)
            print(f"Creating tag '{tag.name}' with {count} titles")
            tts = []
            for title_id in random.sample(all_title_ids, count):
                tts.append(TitleTagFactoryExistingTitles.build(tag=tag, target_id=title_id))
                stats['titletags'] += 1
            TitleTag.objects.bulk_create(tts)
        print('Stats:', stats)
