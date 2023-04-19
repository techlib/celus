import logging
from typing import Set

from logs.models import ImportBatch, OrganizationPlatform

logger = logging.getLogger(__name__)


def find_organizationplatform_differences() -> (Set, Set):
    ops = {
        tuple(rec)
        for rec in OrganizationPlatform.objects.all().values_list('organization_id', 'platform_id')
    }
    logger.debug('Found %d OrganizationPlatform records', len(ops))
    ibs = {
        tuple(rec)
        for rec in ImportBatch.objects.all()
        .values_list('organization_id', 'platform_id')
        .distinct()
    }
    logger.debug('Found %d ImportBatch records', len(ibs))

    missing = ibs - ops
    extra = ops - ibs
    return missing, extra


def fix_organizationplatform_differences(missing: Set, extra: Set):
    for org_id, platform_id in missing:
        OrganizationPlatform.objects.create(organization_id=org_id, platform_id=platform_id)
    for org_id, platform_id in extra:
        OrganizationPlatform.objects.filter(
            organization_id=org_id, platform_id=platform_id
        ).delete()
