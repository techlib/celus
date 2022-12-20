import json
import logging
import pathlib

from core.models import DATA_SOURCE_TYPE_ORGANIZATION
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand
from django.db.models import Exists, OuterRef
from logs.models import AccessLog
from publications.models import Platform
from sushi.models import SushiCredentials

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Create export for celus brain'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output', '-o', dest='output', required=True, type=lambda x: pathlib.Path(x).open("w")
        )
        parser.add_argument(
            '--all',
            dest='all',
            action='store_true',
            help="Export all platforms - including those which were made by users",
        )

    def handle(self, *args, **options):

        # try to get site domain
        domain_name = Site.objects.get(pk=settings.SITE_ID).domain

        all_platforms = options.get("all", False)
        platform_exclude = {} if all_platforms else {"source__type": DATA_SOURCE_TYPE_ORGANIZATION}

        platforms = Platform.objects.exclude(**platform_exclude)

        converted_credentials = []
        for creds in SushiCredentials.objects.working().filter(platform__in=platforms).not_fake():
            new_credentials = {
                "pk": creds.pk,
                "platform_id": creds.platform_id,
                "url": creds.url,
                "counter_version": creds.counter_version,
                "report_types": [],
            }
            report_types = (
                creds.sushifetchattempt_set.annotate(
                    has_access_log=Exists(
                        AccessLog.objects.filter(import_batch__sushifetchattempt__pk=OuterRef('pk'))
                    )
                )
                .filter(has_access_log=True, credentials__counter_version=creds.counter_version)
                .values_list('counter_report__code', flat=True)
            )

            new_credentials["report_types"] = list(set(report_types))
            converted_credentials.append(new_credentials)

        result = {
            "origin": domain_name,
            "platforms": list(platforms.values("pk", "name", "short_name", "provider", "url")),
            "credentials": converted_credentials,
        }

        # store result into a file into file
        json.dump(result, options["output"])
