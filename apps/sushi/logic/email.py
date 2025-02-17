import typing

import mrml
from core.models import User
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import translation

from .harvest_reports import HarvestReport


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

    subject = render_to_string(
        "sushi/email/harvest_report_subject.txt",
        context={
            "month": harvest_report.month + relativedelta(months=1),
            "new_issues": len(newly_broken),
            "organization": harvest_report.organization,
        },
    )
    subject = subject.strip()

    body_context = {
        "month": harvest_report.month,
        "last_month": harvest_report.month + relativedelta(months=1),
        "harvest_report": harvest_report,
        "celus_url": celus_url,
        "newly_broken": newly_broken,
        "unverified_count": len(unverified),
        "broken_count": len(broken),
        "issue_count": len(broken) + len(unverified),
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
