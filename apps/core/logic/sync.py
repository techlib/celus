"""
Stuff related to synchronization of user and identity data between the local database
and an external source
"""
from django.conf import settings
from django.contrib.auth import get_user_model
import logging

from erms.api import ERMS
from erms.sync import ERMSObjectSyncer, ERMSSyncer
from ..models import User, Identity

logger = logging.getLogger(__name__)


class IdentitySyncer(ERMSSyncer):

    attr_map = {
    }

    object_class = Identity
    primary_id = 'identity'

    def __init__(self):
        super().__init__()
        self.user_id_to_user = {}

    def prefetch_db_objects(self):
        super().prefetch_db_objects()
        self.user_id_to_user = {user.ext_id: user for user in get_user_model().objects.all()}

    def translate_record(self, record: dict) -> dict:
        result = super().translate_record(record)
        result['user'] = self.user_id_to_user.get(result.get('person'))
        del result['person']
        return result


class UserSyncer(ERMSObjectSyncer):

    object_class = User

    attr_map = {
        'name_en': None,
    }

    def translate_record(self, record: dict) -> dict:
        result = super().translate_record(record)
        result['username'] = result.get('name_cs', '') + str(result['ext_id'])
        if 'name_cs' in result:
            parts = result['name_cs'].split()
            if parts:
                result['first_name'] = ' '.join(parts[:-1])
                result['last_name'] = parts[-1]
            del result['name_cs']
        if 'name_en' in result:
            del result['name_en']
        return result


def sync_users_with_erms() -> dict:
    erms = ERMS(base_url=settings.ERMS_API_URL)
    erms_persons = erms.fetch_objects(ERMS.CLS_PERSON)
    return sync_users(erms_persons)


def sync_users(records: [dict]) -> dict:
    syncer = UserSyncer()
    stats = syncer.sync_data(records)
    # let's deal with users that are no longer present in the ERMS
    # we remove them, but only those that had ext_id set before
    # this means that manually created users will not be removed
    # NOTE: one side effect of this is that if there were two different
    #       external sources of user data, they would remove their data
    #       during sync because we do not distinguish between users from
    #       different sources
    seen_external_ids = {int(rec['id']) for rec in records}
    info = get_user_model().objects.filter(ext_id__isnull=False). \
        exclude(ext_id__in=seen_external_ids).delete()
    stats['removed'] = info
    return stats


def sync_identities_with_erms() -> dict:
    erms = ERMS(base_url=settings.ERMS_API_URL)
    erms_idents = erms.fetch_endpoint(ERMS.EP_IDENTITY)
    return sync_users(erms_idents)


def sync_identities(records: [dict]) -> dict:
    syncer = IdentitySyncer()
    stats = syncer.sync_data(records)
    return stats
