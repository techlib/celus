import cProfile
import logging
from time import time

from django.core.management.base import BaseCommand

from logs.logic.export import CSVExport
from logs.models import OrganizationPlatform

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Runs export using CSV Exporter to test its performance"

    def add_arguments(self, parser):
        parser.add_argument("-p", "--platform", type=int, help="Platform ID")
        parser.add_argument("-o", "--org", type=int, help="Organization ID")
        parser.add_argument("filename", type=str, help="Filename to export to")
        parser.add_argument("--nc", action="store_true", help="Do not use clickhouse")
        parser.add_argument("--profile", action="store_true", help="Profile the export")

    def handle(self, *args, **options):
        start = time()
        params = {}
        if options["platform"]:
            params["platform_id"] = options["platform"]
        else:
            params["platform_id"] = OrganizationPlatform.objects.first().platform_id
            logger.warning(
                "Platform ID not provided, using first platform: %s", params["platform_id"]
            )

        if options["org"]:
            params["organization_id"] = options["org"]
        else:
            params["organization_id"] = (
                OrganizationPlatform.objects.filter(platform_id=params["platform_id"])
                .first()
                .organization_id
            )
            logger.warning(
                "Organization ID not provided, using first organization of selected platform: %s",
                params["organization_id"],
            )

        exporter = CSVExport(
            params,
            filename_base=options["filename"],
            zip_compress=False,
            use_clickhouse=not options["nc"],
        )
        if options["profile"]:
            logger.info("Profiling info will be written into %s.pstat", options["filename"])
            cProfile.runctx(
                "exporter.export_raw_accesslogs_to_file()",
                globals(),
                locals(),
                filename=f"{options['filename']}.pstat",
            )
        else:
            exporter.export_raw_accesslogs_to_file()
        logger.info("time to export: %s", time() - start)
