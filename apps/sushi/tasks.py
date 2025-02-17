import logging
from collections import defaultdict

import celery
from core.context_managers import logged_task
from core.logic.error_reporting import email_if_fails
from organizations.models import Organization, UserOrganization

from sushi.logic.cleanup import delete_fetchattempts_and_related_importbatches
from sushi.logic.email import send_harvest_reports
from sushi.logic.harvest_reports import make_harvest_reports

logger = logging.getLogger(__name__)


@celery.shared_task
@logged_task
@email_if_fails
def delete_fetchattempts_and_related_importbatches_task(fetch_attempts_pks: list):
    delete_fetchattempts_and_related_importbatches(fetch_attempts_pks)


@celery.shared_task
@email_if_fails
def send_harvesting_reports():
    u2os = UserOrganization.objects.filter(
        is_admin=True, send_harvest_reports=True, user__is_active=True
    ).select_related("organization", "user")

    o2u_map = defaultdict(list)
    for u2o in u2os:
        o2u_map[u2o.organization_id].append(u2o.user)

    harvest_reports = {
        e.organization.pk: e
        for e in make_harvest_reports(Organization.objects.filter(pk__in=o2u_map.keys()))
    }

    for org_id, users in o2u_map.items():
        for user in users:
            harvest_report = harvest_reports[org_id]
            count = send_harvest_reports(user, [harvest_report])
            logger.info("%d harvest reports for %s were sent", count, user)
