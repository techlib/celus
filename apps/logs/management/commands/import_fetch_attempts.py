"""
Exports a list of import batches to one file per IB. It uses a format that can be imported back
into any Celus instance - it does not rely on database IDs being the same, nor the order of
report type dimensions being the same.

It only exports the import batches "own data" - no interest and no materialized reports.
"""
import json
import logging
import os.path
from collections import Counter
from time import time
from urllib.parse import unquote
from zipfile import ZipFile

from core.models import SourceFileMixin
from django.conf import settings
from django.core.management import BaseCommand
from organizations.models import Organization
from sushi.models import AttemptStatus, SushiCredentials

from .export_fetch_attempts import SushiFetchAttemptSerializer

logger = logging.getLogger(__name__)


def import_fetch_attempts(filename: str) -> ([int], Counter):
    serializer = SushiFetchAttemptSerializer()
    stats = Counter()
    created_fa_ids = []

    with ZipFile(filename, "r") as inzip:
        with inzip.open("fetch_attempts.json", "r") as infile:
            data = json.load(infile)

        seen_files = set()
        for fa_data in data:
            filename = os.path.relpath(unquote(fa_data["data_file"]), "/media/")
            fa_data["data_file"] = filename
            try:
                inzip.getinfo(filename)
            except KeyError:
                # file not in zip - expecting it to already be in MEDIA_ROOT
                exp_file = os.path.join(settings.MEDIA_ROOT, filename)
                if not os.path.exists(exp_file):
                    logger.error("File %s not found in zip or MEDIA_ROOT", filename)
                    stats["missing_file"] += 1
                    continue
                else:
                    with open(exp_file, "rb") as f:
                        checksum, _size = SourceFileMixin.checksum_fileobj(f)
                    if checksum != fa_data["checksum"]:
                        logger.error(
                            "Checksum mismatch for %s: %s != %s",
                            filename,
                            checksum,
                            fa_data["checksum"],
                        )
                        stats["checksum_mismatch"] += 1
                        continue
                    stats["local_file"] += 1
            else:
                if filename in seen_files:
                    stats["multi_file"] += 1
                else:
                    inzip.extract(filename, settings.MEDIA_ROOT)
                    seen_files.add(filename)
                    stats["extracted_file"] += 1

            fa_data = serializer.validate(fa_data)
            try:
                fa, created = serializer.get_or_create(fa_data, strict=False)
            except ValueError as e:
                logger.error("Error creating SushiFetchAttempt: %s", e)
                stats["error"] += 1
                continue
            except Organization.DoesNotExist as e:
                logger.error("Organization not found: %s", e)
                stats["organization_not_found"] += 1
                continue
            except SushiCredentials.DoesNotExist as e:
                logger.error("SushiCredentials not found: %s", e)
                stats["credentials_not_found"] += 1
                continue

            if not created:
                logger.info("Matching SushiFetchAttempt found #%d, keeping the original", fa.pk)
                stats["fetch_attempts_exists"] += 1
            else:
                # set status to importing to ingest the data
                logger.info("Importing SushiFetchAttempt #%d", fa.pk)
                fa.status = AttemptStatus.IMPORTING
                fa.save()
                if fa.data_file.size != fa_data["file_size"]:
                    logger.warning(
                        "File size mismatch for %s: %s != %s",
                        filename,
                        fa.data_file.size,
                        fa_data["file_size"],
                    )
                stats["fetch_attempts_imported"] += 1
                created_fa_ids.append(fa.pk)
    return created_fa_ids, stats


class Command(BaseCommand):
    help = "Import data from a zip file produced by export_fetch_attempts"

    def add_arguments(self, parser):
        parser.add_argument("input_file", help="Name of zip file to read from")
        parser.add_argument(
            "--fa-ids-file",
            type=str,
            help="File to write created fetch attempt IDs to in JSON format",
        )

    def handle(self, *args, **options):
        start = time()

        ids, stats = import_fetch_attempts(options["input_file"])

        if options["fa_ids_file"]:
            with open(options["fa_ids_file"], "w") as f:
                json.dump(ids, f)
            logger.info("Wrote %d fetch attempt IDs to %s", len(ids), options["fa_ids_file"])

        logger.info("Duration: %s, Stats: %s", time() - start, stats)
