"""
Stuff related to synchronization of organization data between the local database
and an external source
"""
from core.task_support import cache_based_lock
from erms.sync import ERMSObjectSyncer
from ..models import Platform

from django.db.transaction import atomic
from django.conf import settings

from core.models import DataSource
from erms.api import ERMS


class PlaformSyncer(ERMSObjectSyncer):

    attr_map = {
        'id': 'ext_id',
        'short name_en': 'short_name',
    }

    object_class = Platform


@atomic()
def erms_sync_platforms() -> dict:
    with cache_based_lock('erms_sync_platforms'):
        erms = ERMS(base_url=settings.ERMS_API_URL)
        erms_records = erms.fetch_objects(ERMS.CLS_PLATFORM)
        data_source, _created = DataSource.objects.get_or_create(short_name='ERMS',
                                                                 type=DataSource.TYPE_API)
        syncer = PlaformSyncer(data_source)
        return syncer.sync_data(erms_records)
