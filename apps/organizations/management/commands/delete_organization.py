import logging
from time import time

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.db.transaction import atomic
from organizations.models import Organization

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Delete organization given by its PK, name or short_name'

    def add_arguments(self, parser):
        parser.add_argument('organization_id')
        parser.add_argument('--do-it', dest='doit', action='store_true')

    @atomic
    def handle(self, *args, **options):
        org_id = options['organization_id']
        if org_id.isdigit():
            org = Organization.objects.get(pk=org_id)
        else:
            org = Organization.objects.get(Q(name=org_id) | Q(short_name=org_id))

        logger.info('Deleting organization: %s', org)
        if options['doit']:
            start = time()
            count, stats = org.delete()
            logger.warning(f'Stats: {stats}')

            def oncommit():
                logger.info('Time: %.2f s', time() - start)

            transaction.on_commit(oncommit)
        else:
            logger.info('Delete was not made - use --do-it to really do it ;)')
