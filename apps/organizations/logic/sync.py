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
