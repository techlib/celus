"""
Stuff related to synchronization of user and identity data between the local database
and an external source
"""
from django.conf import settings
from django.contrib.auth import get_user_model
import logging

from core.models import DataSource
from erms.api import ERMS
from erms.sync import ERMSObjectSyncer, ERMSSyncer
from ..models import User, Identity

logger = logging.getLogger(__name__)


class IdentitySyncer(ERMSSyncer):

    attr_map = {
    }

    object_class = Identity
    primary_id = 'identity'

    def __init__(self, data_source):
        super().__init__(data_source)
        self.user_id_to_user = {}

    def prefetch_db_objects(self):
        super().prefetch_db_objects()
        self.user_id_to_user = {user.ext_id: user for user in get_user_model().objects.all()}

    def translate_record(self, record: dict) -> dict:
        return {
            'user': self.user_id_to_user.get(record.get('person')),
            'identity': record.get('identity')
        }


class UserSyncer(ERMSObjectSyncer):

    object_class = User

    allowed_attrs = ['username', 'first_name', 'last_name', 'ext_id', 'email']

    attr_map = {
        'name_en': None,  # none is removed
        'description_en': None,
        'description_cs': None,
        'system administrator': None,
        'mobile': None,
        'note': None,
    }

    def translate_record(self, record: dict) -> dict:
        result = super().translate_record(record)
        result['username'] = result.get('name_cs', '') + str(result['ext_id'])
        if 'name_cs' in result:
            parts = result['name_cs'].split()
            if parts:
                result['first_name'] = ' '.join(parts[:-1])
                result['last_name'] = parts[-1]
        if 'first_name' not in result:
            result['first_name'] = ''
        if 'last_name' not in result:
            result['last_name'] = ''
        if 'email' not in result:
            result['email'] = ''
        # create output with only attrs in allowed_attrs
        new_result = {}
        for key in self.allowed_attrs:
            new_result[key] = result.get(key)
        return new_result


def sync_users_with_erms(data_source: DataSource) -> dict:
    erms = ERMS(base_url=settings.ERMS_API_URL)
    erms_persons = erms.fetch_objects(ERMS.CLS_PERSON)
    return sync_users(data_source, erms_persons)


def sync_users(data_source: DataSource, records: [dict]) -> dict:
    syncer = UserSyncer(data_source)
    stats = syncer.sync_data(records)
    # let's deal with users that are no longer present in the ERMS
    # we remove them, but only those from the same data_source
    # this means that manually created users will not be removed
    # and users from other source neither
    seen_external_ids = {int(rec['id']) for rec in records}
    info = get_user_model().objects.filter(source=data_source). \
        exclude(ext_id__in=seen_external_ids).delete()
    stats['removed'] = info
    return stats


def sync_identities_with_erms(data_source: DataSource) -> dict:
    erms = ERMS(base_url=settings.ERMS_API_URL)
    erms_idents = erms.fetch_endpoint(ERMS.EP_IDENTITY)
    return sync_identities(data_source, erms_idents)


def sync_identities(data_source: DataSource, records: [dict]) -> dict:
    syncer = IdentitySyncer(data_source)
    stats = syncer.sync_data(records)
    return stats
