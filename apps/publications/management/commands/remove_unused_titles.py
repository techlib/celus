from django.core.management.base import BaseCommand
from django.db.models import Exists, OuterRef
from django.db.transaction import atomic
from logs.models import AccessLog
from publications.models import Title


class Command(BaseCommand):

    help = (
        'Go over all titles and remove those for which there are no access logs. Useful when '
        'using an older database template for a new installation.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--do-it', dest='do_it', action='store_true')

    @atomic
    def handle(self, *args, **options):
        pretend = not options['do_it']
        related_als = AccessLog.objects.filter(target_id=OuterRef('pk'))
        qs = Title.objects.exclude(Exists(related_als))
        if pretend:
            total = Title.objects.count()
            self.stdout.write(f'There are {qs.count()} titles to remove from {total}.')
            self.stderr.write('Just counting, use --do-it to really perform delete\n')
        else:
            result = qs.delete()
            total = Title.objects.count()
            self.stdout.write(f'Removed the following: {result}; Remaining titles: {total}')
