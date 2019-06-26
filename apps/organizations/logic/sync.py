"""
Stuff related to synchronization of organization data between the local database
and an external source
"""

from erms.sync import ERMSSyncer
from ..models import Organization


class OrganizationSyncer(ERMSSyncer):

    attr_map = {
        'czechelib id': 'internal_id',
        'short name': 'short_name',
        'address of residence': 'address'
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


