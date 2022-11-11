import codecs
import csv
import logging
import re
import typing
from pathlib import Path

from celus_nibbler import Poop, eat
from celus_nibbler.definitions.celus_format import (
    CelusFormatAreaDefinition,
    CelusFormatParserDefinition,
    DataFormatDefinition,
)
from celus_nibbler.parsers.base import IDS
from celus_nibbler.sources import ExtractParams
from celus_nigiri import CounterRecord
from celus_nigiri.celus import custom_data_to_records
from celus_nigiri.csv_detect import detect_file_encoding
from django.conf import settings
from django.core.management.base import BaseCommand
from logs.models import ReportType

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Compares output nigiri and nibbler when parsing non-counter celus format'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            dest='source',
            help='directory or file where to look',
            default=None,
            type=Path,
        )
        parser.add_argument(
            '--regex',
            dest='regex',
            help='regular expression to extract counter report type name from a file',
            default="^([^-]+)-.*csv$",
        )

    def handle(self, *args, **options):
        non_counter_report_types = {
            e.short_name: e for e in ReportType.objects.filter(counterreporttype=None)
        }

        if source := options["source"]:
            if source.is_dir():
                for path in source.glob("**/*.csv"):
                    self.process_path(path, non_counter_report_types, regex=options["regex"])
            else:
                self.process_path(source, non_counter_report_types, regex=options["regex"])

        else:
            for path in (Path(settings.MEDIA_ROOT) / "custom").glob("**/*.csv"):
                self.process_path(path, non_counter_report_types, regex=options["regex"])

    def process_path(
        self, path: Path, non_counter_report_types: typing.Dict[str, ReportType], regex: str
    ):
        if rt := re.match(regex, path.name):
            rt = rt.group(1)
            if report_type := non_counter_report_types.get(rt):
                nigiri_count, nibbler_count, same = self.compare(path, report_type)
                print(path, nigiri_count, nibbler_count, same)
            else:
                logger.warn("ReportType %s was not found", rt)
                return
        else:
            logger.warn("Failed to detect report type from file name '%s'", path.name)

    def compare(
        self, path: Path, report_type: ReportType
    ) -> typing.Tuple[
        typing.Optional[int], typing.Optional[int], bool,
    ]:
        nigiri_output = self.parse_nigiri(path, report_type)
        nigiri_count = len(nigiri_output) if nigiri_output else nigiri_output
        nibbler_output = self.parse_nibbler(path, report_type)
        nibbler_count = len(nibbler_output) if nibbler_output else nibbler_output

        return nigiri_count, nibbler_count, nibbler_output == nigiri_output

    def format_record(self, record: CounterRecord) -> typing.List[str]:
        # Skip empty dimensions (None vs "")
        record.dimension_data = {k: v for k, v in record.dimension_data.items() if v}
        # Skip empty titles (None vs "")
        record.title_ids = {k: v for k, v in record.title_ids.items() if v}

        res = list(record.as_csv())
        del res[1]  # pycounter doesn't have end_date set
        return res

    def parse_nigiri(self, path, report_type: ReportType) -> typing.Optional[typing.List[tuple]]:
        with path.open("rb") as f:
            reader = csv.DictReader(codecs.iterdecode(f, detect_file_encoding(f)))
            try:
                records = custom_data_to_records(
                    reader, extra_dims=report_type.dimension_short_names,
                )
                return sorted([self.format_record(r) for r in records])
            except Exception as e:
                logger.warn("Nigiri crashed: %s", e)
                return None

    def parse_nibbler(self, path, report_type: ReportType) -> typing.Optional[typing.List[tuple]]:
        try:
            parser_area = CelusFormatAreaDefinition(
                title_column_names=['title', 'Title', 'source', 'Source'],
                organization_column_names=['Organization', 'organization', 'org', 'Org'],
                metric_column_names=['metric', 'Metric'],
                title_ids_mapping={e: e for e in IDS},
                dimension_mapping={e: e for e in report_type.dimension_short_names},
                value_extract_params=ExtractParams(default=0),
            )

            parser = CelusFormatParserDefinition(
                parser_name="Tabular",
                data_format=DataFormatDefinition(
                    name=report_type.short_name, id=report_type.ext_id,
                ),
                areas=[parser_area],
                platforms=[],
            ).make_parser()

            poops = eat(
                path,
                platform="Some",
                check_platform=False,
                parsers=[f"^{parser.name}$"],
                dynamic_parsers=[parser],
            )

            if poops and isinstance(poops[0], Poop):
                return sorted([self.format_record(r) for r in poops[0].records()])
        except Exception as e:
            logger.warn("Nibbler crashed: %s", e)
            return None

        return None
