import typing
from collections import defaultdict

import mrml
from core.models import User
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import translation
from reporting.logic.anomalies import AnomalyDetector

from .harvest_reports import DataCounts, HarvestReport


def _get_anomaly_summary(month: str, organization_ids: typing.List[int]) -> typing.List[dict]:
    """
    Fetch anomalies for the given month and organization(s).
    Returns list of dicts with platform_name, organization_name, and count.
    Returns empty list if ClickHouse is not available.
    """
    detector = AnomalyDetector(month, month, organization_ids)
    anomalies = detector.get_anomalies()

    # Group by platform and organization
    grouped = defaultdict(lambda: {"count": 0, "platform_name": "", "organization_name": ""})
    for anomaly in anomalies:
        key = (anomaly["platform_id"], anomaly["organization_id"])
        grouped[key]["count"] += 1
        grouped[key]["platform_name"] = anomaly["platform_name"]
        grouped[key]["organization_name"] = anomaly["organization"]
        grouped[key]["platform_id"] = anomaly["platform_id"]
        grouped[key]["organization_id"] = anomaly["organization_id"]

    return sorted(grouped.values(), key=lambda x: (x["organization_name"], x["platform_name"]))


def _make_harvest_report_missing_credentials_message(
    user: User, harvest_report: HarvestReport
) -> EmailMultiAlternatives:
    subject = render_to_string(
        "sushi/email/harvest_report_missing_credentials_subject.txt",
        context={
            "month": harvest_report.month + relativedelta(months=1),
            "organization": harvest_report.organization,
        },
    )
    subject = subject.strip()

    body_txt = render_to_string(
        "sushi/email/harvest_report_missing_credentials_body.txt",
        context={"organization": harvest_report.organization},
    )

    body_mjml = render_to_string(
        "sushi/email/harvest_report_missing_credentials_body.mjml",
        context={"organization": harvest_report.organization},
    )

    body_html = mrml.to_html(body_mjml, mrml.ParserOptions(), mrml.RenderOptions())

    msg = EmailMultiAlternatives(subject, body_txt, settings.SERVER_EMAIL, [user.email])
    msg.attach_alternative(body_html.content, "text/html")

    return msg


def _make_harvest_report_message(
    user: User, harvest_report: HarvestReport, celus_url: str
) -> EmailMultiAlternatives:
    newly_broken = [
        e
        for e in harvest_report.credentials
        if e.broken_since
        and e.broken_since.date() >= harvest_report.month + relativedelta(months=1)
    ]
    broken = [e for e in harvest_report.credentials if e.broken_since]
    unverified = [e for e in harvest_report.credentials if not e.is_verified]
    empty_data = [e for e in harvest_report.credentials if e.has_empty_data]

    subject = render_to_string(
        "sushi/email/harvest_report_subject.txt",
        context={
            "month": harvest_report.month + relativedelta(months=1),
            "new_issues": len(newly_broken),
            "organization": harvest_report.organization,
        },
    )
    subject = subject.strip()

    # Fetch anomaly summary for the data month (same as success rate)
    anomaly_month = harvest_report.month.strftime("%Y-%m-%d")
    anomaly_summary = _get_anomaly_summary(anomaly_month, [harvest_report.organization.pk])
    anomaly_count = sum(a["count"] for a in anomaly_summary)

    body_context = {
        "month": harvest_report.month,
        "last_month": harvest_report.month + relativedelta(months=1),
        "harvest_report": harvest_report,
        "celus_url": celus_url,
        "newly_broken": newly_broken,
        "empty_data": empty_data,
        "unverified_count": len(unverified),
        "broken_count": len(broken),
        "issue_count": len(broken) + len(unverified),
        "anomaly_summary": anomaly_summary,
        "anomaly_count": anomaly_count,
    }

    body_txt = render_to_string("sushi/email/harvest_report_body.txt", context=body_context)

    body_mjml = render_to_string("sushi/email/harvest_report_body.mjml", context=body_context)

    body_html = mrml.to_html(body_mjml, mrml.ParserOptions(), mrml.RenderOptions())

    msg = EmailMultiAlternatives(subject, body_txt, settings.SERVER_EMAIL, [user.email])
    msg.attach_alternative(body_html.content, "text/html")

    return msg


def send_harvest_reports(user: User, harvest_reports: typing.List[HarvestReport]):
    res = 0

    with translation.override(user.language):
        site = Site.objects.get(pk=settings.SITE_ID)
        celus_url = f"https://{site.domain}"
        for harvest_report in harvest_reports:
            if not harvest_report.credentials:
                msg = _make_harvest_report_missing_credentials_message(user, harvest_report)
            else:
                msg = _make_harvest_report_message(user, harvest_report, celus_url)
            res += msg.send()

    return res


def _make_grouped_harvest_report_message(
    user: User, harvest_reports: typing.List[HarvestReport], celus_url: str
) -> typing.Optional[EmailMultiAlternatives]:
    if not harvest_reports:
        return None
    month = harvest_reports[0].month
    all_credentials = [c for hr in harvest_reports for c in hr.credentials]

    newly_broken = [
        e
        for e in all_credentials
        if e.broken_since and e.broken_since.date() >= month + relativedelta(months=1)
    ]
    broken = [e for e in all_credentials if e.broken_since]
    unverified = [e for e in all_credentials if not e.is_verified]
    empty_data = [e for e in all_credentials if e.has_empty_data]

    subject = render_to_string(
        "sushi/email/harvest_report_grouped_subject.txt",
        context={"month": month + relativedelta(months=1), "new_issues": len(newly_broken)},
    )
    subject = subject.strip()

    overall_success_rate = sum((e.data_counts for e in harvest_reports), DataCounts()).success_rate

    # Fetch anomaly summary for all organizations in the data month (same as success rate)
    org_ids = [hr.organization.pk for hr in harvest_reports]
    anomaly_month = month.strftime("%Y-%m-%d")
    anomaly_summary = _get_anomaly_summary(anomaly_month, org_ids)
    anomaly_count = sum(a["count"] for a in anomaly_summary)

    body_context = {
        "month": month,
        "last_month": month + relativedelta(months=1),
        "harvest_reports": harvest_reports,
        "celus_url": celus_url,
        "newly_broken": newly_broken,
        "empty_data": empty_data,
        "unverified_count": len(unverified),
        "broken_count": len(broken),
        "issue_count": len(broken) + len(unverified),
        "overall_success_rate": overall_success_rate,
        "anomaly_summary": anomaly_summary,
        "anomaly_count": anomaly_count,
    }

    body_txt = render_to_string("sushi/email/harvest_report_grouped_body.txt", context=body_context)

    body_mjml = render_to_string(
        "sushi/email/harvest_report_grouped_body.mjml", context=body_context
    )

    body_html = mrml.to_html(body_mjml, mrml.ParserOptions(), mrml.RenderOptions())

    msg = EmailMultiAlternatives(subject, body_txt, settings.SERVER_EMAIL, [user.email])
    msg.attach_alternative(body_html.content, "text/html")

    return msg


def send_grouped_harvest_reports(user: User, harvest_reports: typing.List[HarvestReport]):
    with translation.override(user.language):
        site = Site.objects.get(pk=settings.SITE_ID)
        celus_url = f"https://{site.domain}"
        if not any(e.credentials for e in harvest_reports):
            # No credentials for any org
            # Don't sent anything
            return 0
        if msg := _make_grouped_harvest_report_message(user, harvest_reports, celus_url):
            return msg.send()
    return 0
