"""
Exports a list of import batches to one file per IB. It uses a format that can be imported back
into any CELUS instance - it does not rely on database IDs being the same, nor the order of
report type dimensions being the same.

It only exports the import batches "own data" - no interest and no materialized reports.
"""

import json
import logging
import os.path
from collections import Counter
from time import time
from zipfile import ZIP_DEFLATED, ZipFile

from core.models import User
from django.conf import settings
from django.core.management import BaseCommand
from django.db.models import Count, QuerySet
from organizations.models import Organization
from publications.models import Platform
from rest_framework.serializers import ModelSerializer
from sushi.models import CounterReportType, SushiCredentials, SushiFetchAttempt


class PlatformSerializer(ModelSerializer):
    class Meta:
        model = Platform
        fields = ["pk", "short_name", "name", "counter_registry_id"]


class OrganizationSerializer(ModelSerializer):
    class Meta:
        model = Organization
        fields = ["pk", "name", "short_name", "internal_id", "ext_id"]


class CounterReportTypeSerializer(ModelSerializer):
    class Meta:
        model = CounterReportType
        fields = ["pk", "name", "code", "counter_version"]


class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ["pk", "username", "email"]


class SushiCredentialsSerializer(ModelSerializer):
    platform = PlatformSerializer()
    organization = OrganizationSerializer()

    class Meta:
        model = SushiCredentials
        fields = ["pk", "platform", "organization", "counter_version"]


class SushiFetchAttemptSerializer(ModelSerializer):
    credentials = SushiCredentialsSerializer()
    counter_report = CounterReportTypeSerializer()
    triggered_by = UserSerializer()

    class Meta:
        model = SushiFetchAttempt
        fields = [
            "pk",
            "credentials",
            "counter_report",
            "start_date",
            "end_date",
            "log",
            "error_code",
            "http_status_code",
            "partial_data",
            "when_processed",
            "credentials_version_hash",
            "processing_info",
            "triggered_by",
            "data_file",
            "checksum",
            "file_size",
        ]

    def get_or_create(self, validated_data, strict=False) -> (SushiFetchAttempt, bool):
        credentials_data = validated_data.pop("credentials")
        org_name = credentials_data["organization"]["name"]
        org_id = credentials_data["organization"]["pk"]
        platform_name = credentials_data["platform"]["name"]
        platform_id = credentials_data["platform"]["pk"]
        pl_reg_id = credentials_data["platform"]["counter_registry_id"]
        # we use registry_id as the primary key for platforms, but not all have it
        if pl_reg_id:
            platform = Platform.objects.get(counter_registry_id=pl_reg_id)
        else:
            # there may be more than one platform with the same name
            # so we need to additionally check the pk
            platforms = Platform.objects.filter(name=platform_name)
            if platforms.count() == 1:
                platform = platforms.first()
            elif platforms.count() > 1:
                try:
                    platform = platforms.get(pk=platform_id)
                except Platform.DoesNotExist:
                    logger.warning(
                        "Multiple platforms found with name %s, but none with pk %d - "
                        "cannot continue",
                        platform_name,
                        platform_id,
                    )
                    raise ValueError("Multiple platforms but none has the correct pk") from None
            else:
                logger.warning("Platform %s not found", platform_name)
                raise ValueError("Platform not found")
        if platform.pk != platform_id and pl_reg_id != str(platform.counter_registry_id):
            logger.warning(
                "Platform %s was found, but it has a different pk (%d vs %d) "
                "and registry_id (%s vs %s)",
                platform_name,
                platform.pk,
                platform_id,
                platform.counter_registry_id,
                pl_reg_id,
            )
            if strict:
                raise ValueError("Platform not matched perfectly")
        # organization
        try:
            organization = Organization.objects.get(name=org_name)
        except Organization.DoesNotExist:
            logger.warning("Organization %s not found", org_name)
            raise
        if organization.pk != org_id:
            logger.warning(
                "Organization %s was found, but it has a different pk (%d vs %d)",
                org_name,
                organization.pk,
                org_id,
            )
            if strict:
                raise ValueError("Organization not matched perfectly")

        credentials = SushiCredentials.objects.get(
            organization=organization,
            platform=platform,
            counter_version=credentials_data["counter_version"],
        )

        counter_report_data = validated_data.pop("counter_report")
        counter_report = CounterReportType.objects.get(
            code=counter_report_data["code"], counter_version=counter_report_data["counter_version"]
        )

        triggered_by_data = validated_data.pop("triggered_by")
        if triggered_by_data and (tb_email := triggered_by_data.get("email")):
            triggered_by = User.objects.get(email=tb_email)
            if triggered_by.pk != triggered_by_data["pk"]:
                logger.warning(
                    "User %s was found, but it has a different pk (%d vs %d)",
                    triggered_by,
                    triggered_by.pk,
                    triggered_by_data["pk"],
                )
                if strict:
                    raise ValueError("User not matched perfectly")
        else:
            triggered_by = None

        validated_data.pop("pk")  # Remove 'pk' from validated_data
        start_date = validated_data.pop("start_date")
        end_date = validated_data.pop("end_date")

        try:
            # we simulate get_or_create, but only if the FA has an IB
            return SushiFetchAttempt.objects.filter(
                credentials=credentials,
                counter_report=counter_report,
                start_date=start_date,
                end_date=end_date,
            ).filter(record_count__gt=0).get(), False
        except SushiFetchAttempt.DoesNotExist:
            pass

        return SushiFetchAttempt.objects.create(
            credentials=credentials,
            counter_report=counter_report,
            start_date=start_date,
            end_date=end_date,
            triggered_by=triggered_by,
            **validated_data,
        ), True


logger = logging.getLogger(__name__)


def export_fetch_attempts(
    filename: str, fetch_attempts: QuerySet[SushiFetchAttempt], include_files=True
) -> Counter:
    serializer = SushiFetchAttemptSerializer(fetch_attempts, many=True)
    data = serializer.data

    stats = Counter()
    seen_files = set()

    with ZipFile(filename, "w", compression=ZIP_DEFLATED) as outzip:
        with outzip.open("fetch_attempts.json", "w", force_zip64=True) as outfile:
            outfile.write(json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8"))

        if include_files:
            for fa in fetch_attempts:
                arcname = os.path.relpath(fa.data_file.path, settings.MEDIA_ROOT)
                if arcname in seen_files:
                    logger.warning(
                        "Duplicate file %s for fa %d (probably split multimonth file), skipping",
                        arcname,
                        fa.pk,
                    )
                    stats["files_skipped"] += 1
                    continue
                try:
                    outzip.write(fa.data_file.path, arcname)
                    stats["files_exported"] += 1
                except FileNotFoundError:
                    logger.warning("File %s not found", fa.data_file.path)
                    stats["files_not_found"] += 1
                seen_files.add(arcname)
        else:
            logger.info("Skipping data files")

    return stats


class Command(BaseCommand):
    help = (
        "Export selected fetch attempts including their data into a zip file "
        "for import into another CELUS instance"
    )

    def add_arguments(self, parser):
        parser.add_argument("output_file", help="Name of zip file to write to")
        parser.add_argument(
            "--fetch-attempts", nargs="+", type=int, help="Fetch attempts to export"
        )
        parser.add_argument("--credentials", nargs="+", type=int, help="Credentials to export")
        parser.add_argument("--all", action="store_true", help="Export all fetch attempts")
        parser.add_argument(
            "--exclude-files",
            action="store_true",
            help="Do not include data files in the output zip file - assumes they are already "
            "present in the target system",
        )
        parser.add_argument(
            "--status", nargs="+", type=str, help="Fetch attempts with the specified status"
        )
        parser.add_argument(
            "--import-batch-only",
            action="store_true",
            help="Export only fetch attempts with import batch",
        )

    def handle(self, *args, **options):
        start = time()
        if options["all"]:
            fa_qs = SushiFetchAttempt.objects.all()
            if options["fetch_attempts"]:
                logger.warning(
                    "Ignoring --fetch-attempts because --all was specified. Exporting all fetch "
                    "attempts."
                )
            if options["credentials"]:
                logger.warning(
                    "Ignoring --credentials because --all was specified. Exporting all fetch "
                    "attempts."
                )
        elif options["fetch_attempts"]:
            fa_qs = SushiFetchAttempt.objects.filter(pk__in=options["fetch_attempts"])
            if options["credentials"]:
                logger.warning(
                    "Ignoring --credentials because --fetch-attempts was specified. Exporting "
                    "only the specified fetch attempts."
                )
        elif options["credentials"]:
            fa_qs = SushiFetchAttempt.objects.filter(credentials_id__in=options["credentials"])
        else:
            logger.error(
                "You must specify either --all, --fetch-attempts or --credentials. Exiting."
            )
            return

        # print some stats about the fetch attempts
        logger.info("Fetch attempts with ib: %d", fa_qs.filter(import_batch__isnull=False).count())
        logger.info(
            "Fetch attempts without ib: %d", fa_qs.filter(import_batch__isnull=True).count()
        )
        if options["import_batch_only"]:
            fa_qs = fa_qs.filter(import_batch__isnull=False)

        for rec in fa_qs.values("status").annotate(count=Count("pk")).order_by("status"):
            if not options["status"] or rec["status"] in options["status"]:
                logger.info("Including status: '%s', Count: %s", rec["status"], rec["count"])
            else:
                logger.warning("Excluding status: '%s', Count: %s", rec["status"], rec["count"])

        if options["status"]:
            fa_qs = fa_qs.filter(status__in=options["status"])

        logger.info("Exporting %s fetch attempts", fa_qs.count())

        fa_qs = fa_qs.select_related(
            "credentials",
            "credentials__organization",
            "credentials__platform",
            "counter_report",
            "triggered_by",
        )
        stats = export_fetch_attempts(
            options["output_file"], fa_qs, include_files=not options["exclude_files"]
        )

        logger.info("Duration: %s, Stats: %s", time() - start, stats)
