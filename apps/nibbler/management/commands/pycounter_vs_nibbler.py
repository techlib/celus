import itertools
import logging
import re
import time
import typing
from pathlib import Path

from celus_nibbler import Poop, eat
from celus_nigiri import CounterRecord
from django.conf import settings
from django.core.management.base import BaseCommand
from sushi.models import CounterReportType, SushiFetchAttempt

logger = logging.getLogger(__name__)


class Exectime:
    def __enter__(self):
        self.start = time.monotonic()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.time = time.monotonic() - self.start


class Command(BaseCommand):
    help = 'Compares output pycounter and nibbler on all available tsv/csv/json files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--directory', dest='directory', help='directory where to look', default=None, type=Path
        )
        parser.add_argument(
            '--regex',
            dest='regex',
            help='regular expression to extract counter report type name from a file',
            default="^4_([^_]+)_",
        )
        parser.add_argument(
            '--disable-debug-logs', help='disables debug logs', action="store_true", default=False
        )

    def handle(self, *args, **options):
        if options["disable_debug_logs"]:
            logging.disable(logging.WARNING)

        counter_report_types = {e.code: e for e in CounterReportType.objects.all()}

        if directory := options["directory"]:
            for path in (
                list(directory.glob("**/*.tsv"))
                + list(directory.glob("**/*.csv"))
                + list(directory.glob("**/*.json"))
            ):
                self.process_path(path, counter_report_types, regex=options["regex"])
        else:
            # parse files from current nibbler data dir

            # compare files obrained via sushi
            for path in (Path(settings.MEDIA_ROOT) / "counter").glob("**/*.tsv"):
                self.process_path(path, counter_report_types, regex="^4_([^_]+)_")

            # compare manually uploaded
            custom_path = Path(settings.MEDIA_ROOT) / "custom"
            for path in (
                list(custom_path.glob("**/*.tsv"))
                + list(custom_path.glob("**/*.csv"))
                + list(custom_path.glob("**/*.json"))
            ):
                self.process_path(path, counter_report_types, regex="^([^_]+)-")

    def process_path(
        self, path: Path, counter_report_types: typing.Dict[str, CounterReportType], regex: str
    ):

        if crt := re.match(regex, path.name):
            crt = crt.group(1)
            if crt := counter_report_types.get(crt):
                pycounter_count, pycounter_time, nibbler_count, nibbler_time, same = self.compare(
                    path, crt
                )
                print(
                    path,
                    f"P-{pycounter_count}",
                    f"({pycounter_time:.2f})",
                    f"N-{nibbler_count}",
                    f"({nibbler_time:.2f})",
                    not bool(same),
                )
                if same:
                    print(same[0])
                    print(same[1])
            else:
                logger.warn("CounterReportType %s was not found", crt)
                return
        else:
            logger.warn("Failed to detect report type from file name %s", path.name)

    def compare(
        self, path: Path, counter_report_type: CounterReportType
    ) -> typing.Tuple[
        typing.Optional[int],
        int,
        typing.Optional[int],
        int,
        typing.Optional[typing.Tuple[typing.List[str], typing.List[str]]],
    ]:
        with path.open('rb') as f:
            is_json = SushiFetchAttempt.file_is_json_s(f)

        pycounter_output, pycounter_time = self.parse_pycounter(path, counter_report_type, is_json)
        pycounter_count = len(pycounter_output) if pycounter_output else pycounter_output
        nibbler_output, nibbler_time = self.parse_nibbler(path, counter_report_type, is_json)
        nibbler_count = len(nibbler_output) if nibbler_output else nibbler_output

        first_diff = None
        if nibbler_output != pycounter_output and nibbler_output and pycounter_output:
            for py, ni in itertools.zip_longest(pycounter_output, nibbler_output):
                if py != ni:
                    first_diff = py, ni
                    break

        return pycounter_count, pycounter_time, nibbler_count, nibbler_time, first_diff

    def format_record(self, record: CounterRecord) -> typing.List[str]:
        # Skip empty dimensions (None vs "")
        record.dimension_data = {k: v for k, v in record.dimension_data.items() if v}
        # Skip empty titles (None vs "")
        record.title_ids = {k: v for k, v in record.title_ids.items() if v}

        # Strip title (this should happen before storing to db anyways)
        # otherwise this would affect the sorting
        record.title = record.title.strip() if record.title else record.title

        res = list(record.as_csv())
        del res[1]  # pycounter doesn't have end_date set
        return res

    def parse_pycounter(
        self, path, counter_report_type: CounterReportType, is_json: bool
    ) -> (typing.Optional[typing.List[tuple]], float):
        if reader_class := counter_report_type.get_reader_class(is_json):
            reader = reader_class()
            try:
                with Exectime() as ex:
                    records = [self.format_record(r) for r in reader.file_to_records(str(path))]
                return sorted(records), ex.time
            except Exception as e:
                logger.warn("Pycounter crashed: %s", e)
                return None, ex.time

        return None, 0

    def parse_nibbler(
        self, path, counter_report_type: CounterReportType, is_json: bool
    ) -> (typing.Optional[typing.List[tuple]], float):

        try:
            poops = eat(
                path,
                platform="Some",
                parsers=[counter_report_type.get_nibbler_parser(is_json)],
                check_platform=False,
            )
            if poops and isinstance(poops[0], Poop):
                with Exectime() as ex:
                    records = [self.format_record(r) for r in poops[0].records()]
                return sorted(records), ex.time
        except Exception as e:
            logger.warn("Nibbler crashed: %s", e)
            return None, 0

        return None, 0
