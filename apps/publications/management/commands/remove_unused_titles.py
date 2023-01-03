from itertools import islice

from django.core.management.base import BaseCommand
from django.db.models import Exists, OuterRef
from logs.models import AccessLog
from publications.models import Title


class Command(BaseCommand):

    help = (
        'Go over all titles and remove those for which there are no access logs. Useful when '
        'using an older database template for a new installation.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--do-it', dest='do_it', action='store_true')

    def handle(self, *args, **options):
        pretend = not options['do_it']
        related_als = AccessLog.objects.filter(target_id=OuterRef('pk'))
        qs = Title.objects.exclude(Exists(related_als))
        if pretend:
            total = Title.objects.count()
            self.stdout.write(f'There are {qs.count()} titles to remove from {total}.')
            self.stderr.write('Just counting, use --do-it to really perform delete\n')
        else:
            # because deleting many thousands of objects at once takes a lot of memory
            # by the postgres process (not sure why, probably it is about checking all the
            # foreign key constraints), we delete in batches.
            # The batch size was determined by trial and error to give reasonable speed while
            # maintaining a reasonable memory footprint - about 500 MB in tests.
            title_ids = list(qs.values_list('pk', flat=True))
            self.stdout.write(f'Deleting {len(title_ids)} titles')
            i = 0
            batch_size = 2_000
            iterator = iter(title_ids)
            while batch := list(islice(iterator, batch_size)):
                _deletes, stats = Title.objects.filter(pk__in=batch).delete()
                i += stats['publications.Title']
                self.stderr.write(f'Deleting {i}')
            total = Title.objects.count()
            self.stdout.write(f'Removed: {i}; Remaining titles: {total}')
