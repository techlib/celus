"""
Stuff related to synchronization of organization data between the local database
and an external source
"""

from collections import Counter
from enum import Enum


class Syncer(object):

    attr_map = {}
    primary_id = 'id'  # used to find if a value is in the database or not
    object_class = None

    class Status(Enum):
        UNCHANGED = 0
        SYNCED = 1
        NEW = 2

    def __init__(self):
        self.db_key_to_obj = {}

    def prefetch_db_objects(self):
        if self.object_class:
            self.db_key_to_obj = {getattr(obj, self.primary_id): obj
                                  for obj in self.object_class.objects.all()}

    def sync_data(self, records: [dict]) -> dict:
        self.prefetch_db_objects()
        stats = Counter()
        for record in records:
            record_tr = self.translate_record(record)
            status = self.sync_record(record_tr)
            stats[status] += 1
        return stats

    def translate_record(self, record: dict) -> dict:
        output = {}
        for key, value in record.items():
            out_key = self.translate_key(key)
            output[out_key] = self.translate_value(out_key, value)
        return output

    def translate_value(self, key, value):
        return value

    def translate_key(self, key):
        return self.attr_map.get(key, key)

    def sync_record(self, record: dict) -> Status:
        pid = record[self.primary_id]
        if pid in self.db_key_to_obj:
            obj = self.db_key_to_obj[pid]
            save = False
            for key, value in record.items():
                if type(value) is not dict:
                    # we do not translate value for dicts as it messes the JSON field somehow
                    value = self.object_class._meta._forward_fields_map[key].get_prep_value(value)
                if getattr(obj, key) != value:
                    setattr(obj, key, value)
                    save = True
            if save:
                obj.save()
                return self.Status.SYNCED
            return self.Status.UNCHANGED
        else:
            obj = self.object_class.objects.create(**record)
            self.db_key_to_obj[pid] = obj
            return self.Status.NEW


class ERMSSyncer(Syncer):

    primary_id = 'ext_id'

    def translate_record(self, record: dict) -> dict:
        output = super().translate_record(record['vals'])
        output['ext_id'] = record['id']
        return output

    def translate_value(self, key, value):
        if type(value) is list:
            return value[0]
        return value

    def translate_key(self, key):
        if '@' in key:
            start, end = key.split('@')
            start = super().translate_key(start)
            return f'{start}_{end}'
        return super().translate_key(key)
