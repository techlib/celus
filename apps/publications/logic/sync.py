"""
Stuff related to synchronization of organization data between the local database
and an external source
"""
from core.models import DataSource
from core.task_support import cache_based_lock
from django.conf import settings
from django.db.transaction import atomic
from erms.api import ERMS
from erms.sync import ERMSObjectSyncer

from ..models import Platform


class PlatformSyncer(ERMSObjectSyncer):

    attr_map = {
        'id': 'ext_id',
        'short name': 'short_name',
        'short_name_en': 'short_name',  # short name is not translatable
        'short_name_cs': 'short_name',
        'provider': 'provider',
        'provider_en': 'provider_en',
        'provider_cs': 'provider_cs',
        'name': 'name',
        'name_en': 'name_en',
        'name_cs': 'name_cs',
        'url': 'url',
    }

    object_class = Platform


@atomic()
def erms_sync_platforms() -> dict:
    with cache_based_lock('erms_sync_platforms'):
        erms = ERMS(base_url=settings.ERMS_API_URL)
        erms_records = erms.fetch_objects(ERMS.CLS_PLATFORM)
        data_source, _created = DataSource.objects.get_or_create(
            short_name='ERMS', type=DataSource.TYPE_API
        )
        syncer = PlatformSyncer(data_source)
        return syncer.sync_data(erms_records)
