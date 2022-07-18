import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.transaction import atomic

from core.models import DataSource
from logs.logic.reimport import reimport_import_batch_with_fa
from logs.models import ImportBatch
from publications.models import Platform, PlatformInterestReport
from sushi.models import SushiCredentials

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = (
        'Solves the problem of several credentials for one platform by splitting the credentials '
        'given to it into a separate custom platform. It deletes and reimports all the associated '
        'usage.'
    )

    def add_arguments(self, parser):
        parser.add_argument('credentials_id', help='Database ID of the credentials to split off')
        parser.add_argument(
            '-n',
            '--name',
            dest='new_platform_name',
            help='Name to give to the newly created platform - if not given, the name of the '
            'credentials object will be used.',
        )
        parser.add_argument('--do-it', dest='doit', action='store_true')

    @atomic
    def handle(self, *args, **options):
        creds = SushiCredentials.objects.get(id=options['credentials_id'])
        logger.info('Found credentials: %s', creds)
        name = options.get('new_platform_name') or creds.title
        name = name.strip()
        if not name:
            logger.error('Give an explicit platform name, credentials do not have title to use')
            raise CommandError('Platform name missing')
        source, _ = DataSource.objects.get_or_create(
            type=DataSource.TYPE_ORGANIZATION, organization=creds.organization
        )
        # it will crash with error if the platform already exists
        names = {f'name_{lang[0]}': name for lang in settings.LANGUAGES}
        new_platform = Platform.objects.create(short_name=name, name=name, source=source, **names)
        logger.info('Migrating to new platform: %s', new_platform)
        old_platform_id = creds.platform_id
        # change platform for credentials
        creds.platform = new_platform
        creds.save()
        # change import batches and reimport
        ib_count = 0
        for ib in ImportBatch.objects.filter(sushifetchattempt__credentials=creds):
            ib.platform = new_platform
            ib.save()
            reimport_import_batch_with_fa(ib)
            ib_count += 1

        logger.info('Reimported %d import batches', ib_count)

        # define the same interest for new platform as for the old one
        for pir in PlatformInterestReport.objects.filter(platform_id=old_platform_id):
            pir.pk = None  # this will create new record instead of modifying the current one
            pir.platform = new_platform
            pir.save()

        if not options['doit']:
            raise ValueError('preventing db commit, use --do-it to really do it ;)')
