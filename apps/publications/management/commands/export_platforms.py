import json

import logging
import pathlib

from django.contrib.sites.models import Site
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import OuterRef, Exists

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

    def handle(self, *args, **options):

        # try to get site domain
        domain_name = Site.objects.get(pk=settings.SITE_ID).domain

        platforms = Platform.objects.all().values("pk", "name", "short_name", "provider", "url",)

        converted_credentials = []
        for creds in SushiCredentials.objects.working():
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
                        AccessLog.objects.filter(
                            import_batch__sushifetchattempt__pk=OuterRef('pk'),
                        )
                    )
                )
                .filter(has_access_log=True, credentials__counter_version=creds.counter_version)
                .values_list('counter_report__code', flat=True)
            )

            new_credentials["report_types"] = list(set(report_types))
            converted_credentials.append(new_credentials)

        result = {
            "origin": domain_name,
            "platforms": list(platforms),
            "credentials": converted_credentials,
        }

        # store result into a file into file
        json.dump(result, options["output"])
