"""
Stuff related to synchronization of organization data between the local database
and an external source
"""

from erms.sync import ERMSObjectSyncer
from ..models import Platform


class PlaformSyncer(ERMSObjectSyncer):

    attr_map = {
        'id': 'ext_id',
        'short name_en': 'short_name',
    }

    object_class = Platform
