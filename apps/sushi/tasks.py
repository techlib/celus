import logging
from collections import defaultdict

import celery
from core.context_managers import logged_task
from core.logic.error_reporting import email_if_fails
from core.models import User
from organizations.models import Organization, UserOrganization

from sushi.logic.cleanup import delete_fetchattempts_and_related_importbatches
from sushi.logic.email import send_grouped_harvest_reports, send_harvest_reports
from sushi.logic.harvest_reports import make_harvest_reports

logger = logging.getLogger(__name__)


@celery.shared_task
@logged_task
@email_if_fails
def delete_fetchattempts_and_related_importbatches_task(fetch_attempts_pks: list):
    delete_fetchattempts_and_related_importbatches(fetch_attempts_pks)


@celery.shared_task
@email_if_fails
def send_harvesting_report_task(user_id: int, organization_id: int):
    if user := User.objects.filter(pk=user_id, is_active=True).first():
        if organization := Organization.objects.filter(pk=organization_id).first():
            harvest_reports = make_harvest_reports([organization])
            send_harvest_reports(user, harvest_reports)


@celery.shared_task
@email_if_fails
def send_harvesting_reports_task():
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


@celery.shared_task
@email_if_fails
def send_grouped_harvesting_report_task(user_id: int):
    if user := User.objects.filter(pk=user_id).first():
        harvest_reports = make_harvest_reports(user.admin_organizations())
        if not send_grouped_harvest_reports(user, harvest_reports):
            logger.warn(
                "Can't find any organization suitable to create a harvest report for user %s", user
            )


@celery.shared_task
@email_if_fails
def send_grouped_harvesting_reports_task():
    harvest_reports = make_harvest_reports(Organization.objects.all())

    for user in User.objects.filter(send_grouped_harvest_reports=True, is_active=True):
        orgs = {e.pk for e in user.admin_organizations()}
        harvest_reports_filtered = [e for e in harvest_reports if e.organization.pk in orgs]
        if send_grouped_harvest_reports(user, harvest_reports_filtered):
            logger.info("grouped harvest reports for %s was sent", user)
