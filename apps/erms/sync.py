"""
Stuff related to synchronization of organization data between the local database
and an external source
"""

from collections import Counter
from enum import Enum

from django.db import models

from core.models import DataSource


class SyncerError(Exception):

    pass


class Syncer:

    attr_map = {}
    primary_id = 'id'  # used to find if a value is in the database or not
    object_class = None

    class Status(Enum):
        UNCHANGED = 0
        SYNCED = 1
        NEW = 2

    def __init__(self, data_source: DataSource):
        self.data_source = data_source
        self.db_key_to_obj = {}
        self._seen_pks = set()

    def prefetch_db_objects(self):
        if self.object_class:
            self.db_key_to_obj = {
                getattr(obj, self.primary_id): obj
                for obj in self.object_class.objects.filter(source=self.data_source)
            }

    def sync_data(self, records: [dict]) -> dict:
        self.prefetch_db_objects()
        self._screen_records(records)
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
            if out_key is not None:
                # skip values for which the key maps to None
                output[out_key] = self.translate_value(out_key, value)
        return output

    def translate_value(self, key, value):
        return value

    def translate_key(self, key):
        return self.attr_map.get(key)

    def sync_record(self, record: dict) -> Status:
        pid = record[self.primary_id]
        if pid in self.db_key_to_obj:
            obj = self.db_key_to_obj[pid]
            self._seen_pks.add(obj.pk)
            save = False
            for key, value in record.items():
                if type(value) is not dict and not isinstance(value, models.Model):
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
            obj = self.object_class.objects.create(source=self.data_source, **record)
            self.db_key_to_obj[pid] = obj
            self._seen_pks.add(obj.pk)
            return self.Status.NEW

    def _screen_records(self, records: [dict]) -> None:
        """
        Is run at start of sync_data to do some potential checks on the data before they are
        processed - can be used to collect statistics about the content, etc.
        :param records:
        :return:
        """
        pass


class ERMSSyncer(Syncer):

    primary_id = 'ext_id'

    def translate_value(self, key, value):
        if type(value) is list:
            return value[0]
        return value

    def translate_key(self, key):
        if '@' in key:
            start, end = key.split('@')
            start = super().translate_key(start)
            if start is None:
                return None  # we skip those
            key = f'{start}_{end}'
        return super().translate_key(key)


class ERMSObjectSyncer(ERMSSyncer):
    def translate_record(self, record: dict) -> dict:
        output = super().translate_record(record['vals'])
        output['ext_id'] = record['id']
        return output
