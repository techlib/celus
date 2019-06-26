import logging

from django.core.management.base import BaseCommand
from django.db.transaction import atomic
from django.conf import settings

from ...logic.sync import OrganizationSyncer
from erms.api import ERMS

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Sync organizations between ERMS and the database'

    def add_arguments(self, parser):
        pass

    @atomic
    def handle(self, *args, **options):
        erms = ERMS(base_url=settings.ERMS_API_URL)
        erms_orgs = erms.fetch_objects(ERMS.CLS_ORGANIZATION)
        parent_ids = set()
        internal_ids = set()
        clean_records = []
        # we first do through the records, generate list of parents and also remove
        # records with duplicated internal_id
        for record in erms_orgs:
            internal_id = record['vals'].get('czechelib id')
            if internal_id:
                internal_id = internal_id[0]
            if internal_id and internal_id in internal_ids:
                print(f'Duplicate internal ID "{internal_id}" for {record}')
            else:
                clean_records.append(record)
            internal_ids.add(internal_id)
            if record.get('refs'):
                cb = record['refs'].get('controlled by')
                if cb and record['vals'].get('czechelib id'):
                    parent_ids.add(cb[0])
        # then we do another batch of cleaning where we
        # filter out organizations without ICO or czechelib id, but keep parents
        # of those with czechelib id
        clean_records = [org for org in clean_records
                         if (org['vals'].get('ico') and org['vals'].get('czechelib id')) or
                         org['id'] in parent_ids]
        syncer = OrganizationSyncer()
        stats = syncer.sync_data(clean_records)
        self.stderr.write(self.style.WARNING(f'Import stats: {stats}'))
