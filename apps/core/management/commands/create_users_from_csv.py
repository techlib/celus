import csv
import logging
from collections import Counter
from distutils.util import strtobool

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.db.transaction import atomic

from core.models import User
from organizations.models import UserOrganization, Organization

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = (
        'Create/sync users with a CSV table. Columns can be: '
        '"name","email","superuser","staff","organization","org_admin"'
    )

    def add_arguments(self, parser):
        parser.add_argument('csv_file')
        parser.add_argument('--do-it', dest='doit', action='store_true')

    @atomic
    def handle(self, *args, **options):
        stats = Counter()
        with open(options['csv_file'], 'r') as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                email = row.get('email')
                if not email:
                    raise ValueError('Row "email" is required')
                email = email.strip()
                username = row.get('username', email)
                superuser = bool(strtobool(row.get('superuser', 'False')))
                staff = strtobool(row.get('staff', 'False'))
                name = row.get('name', '')
                first_name = row.get('first_name') or (name.split()[0] if name else '')
                last_name = row.get('last_name') or (name.split()[-1] if name else '')
                user_params = {
                    'username': username.strip(),
                    'is_superuser': superuser,
                    'is_staff': staff,
                    'first_name': first_name.strip(),
                    'last_name': last_name.strip(),
                }
                user, created = User.objects.update_or_create(email=email, defaults=user_params)
                if created:
                    stats['user_created'] += 1
                    logger.debug('created user %s: %s', email, user_params)
                else:
                    stats['user_existed'] += 1
                    logger.debug('updating user %s: %s', email, user_params)
                org_name = row.get('org_id') or row.get('organization')
                if org_name:
                    organization = Organization.objects.get(
                        Q(internal_id=org_name.strip()) | Q(ext_id=org_name.strip())
                    )
                    is_admin = strtobool(row.get('org_admin', 'False'))
                    uo, created = UserOrganization.objects.update_or_create(
                        user=user, organization=organization, defaults={'is_admin': is_admin}
                    )
                    if created:
                        stats['user-org_created'] += 1
                    else:
                        stats['user-org_existed'] += 1
                else:
                    self.stderr.write(
                        self.style.WARNING(f'No organization specified for user: {email}')
                    )

        self.stderr.write(self.style.WARNING(f'Import stats: {stats}'))
        if not options['doit']:
            raise ValueError('preventing db commit, use --do-it to really do it ;)')
