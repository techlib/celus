"""
Stuff related to synchronization of organization data between the local database
and an external source
"""
import logging

from django.conf import settings
from django.db.transaction import atomic

from core.models import DataSource
from core.task_support import cache_based_lock
from erms.api import ERMS
from erms.sync import ERMSObjectSyncer
from ..models import Organization

logger = logging.getLogger(__name__)


class OrganizationSyncer(ERMSObjectSyncer):

    attr_map = {
        'czechelib id': 'internal_id',
        'short name': 'short_name',
        'short_name_cs': 'short_name_cs',
        'short_name_en': 'short_name_en',
        'address of residence': 'address',
        'ico': 'ico',
        'url': 'url',
        'fte': 'fte',
        'name': 'name',
        'name_cs': 'name_cs',
        'name_en': 'name_en',
    }

    object_class = Organization

    def translate_record(self, record: dict) -> dict:
        result = super().translate_record(record)
        # we need to take care of parents
        if record.get('refs'):
            cb = record['refs'].get('controlled by')
            if cb:
                assert len(cb) == 1, 'only one parent allowed, otherwise there cannot be a tree'
                result['parent_id'] = self.db_key_to_obj[cb[0]].pk
        return result


@atomic
def erms_sync_organizations() -> dict:
    with cache_based_lock('sync_organizations_with_erms'):
        erms = ERMS(base_url=settings.ERMS_API_URL)
        data_source, _created = DataSource.objects.get_or_create(short_name='ERMS',
                                                                 type=DataSource.TYPE_API)
        erms_orgs = erms.fetch_objects(ERMS.CLS_ORGANIZATION)
        parent_ids = set()
        internal_ids = set()
        clean_records = []
        # we first go through the records, generate list of parents and also remove
        # records with duplicated internal_id
        for record in erms_orgs:
            internal_id = record['vals'].get('czechelib id')
            if internal_id:
                internal_id = internal_id[0]
            if internal_id and internal_id in internal_ids:
                logger.warning(f'Duplicate internal ID "{internal_id}" for {record}')
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
        syncer = OrganizationSyncer(data_source)
        stats = syncer.sync_data(clean_records)
        return stats
