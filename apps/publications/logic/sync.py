"""
Stuff related to synchronization of organization data between the local database
and an external source
"""

from erms.sync import ERMSSyncer
from ..models import Platform


class PlaformSyncer(ERMSSyncer):

    attr_map = {
        'id': 'ext_id',
        'short name': 'short_name',
    }

    object_class = Platform
