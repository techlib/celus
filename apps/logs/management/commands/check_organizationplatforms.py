import logging

from django.core.management.base import BaseCommand

from logs.logic.cleanup import (
    find_organizationplatform_differences,
    fix_organizationplatform_differences,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        'Checks that OrganizationPlatform records match what it should be according to the '
        'import batches'
    )

    def add_arguments(self, parser):
        parser.add_argument('--fix-it', dest='fix_it', action='store_true')

    def handle(self, *args, **options):
        missing, extra = find_organizationplatform_differences()
        logger.info('Missing %d OrganizationPlatform records', len(missing))
        logger.info('Extra %d OrganizationPlatform records', len(extra))

        if options['fix_it']:
            logger.info('Fixing found problems')
            fix_organizationplatform_differences(missing, extra)
