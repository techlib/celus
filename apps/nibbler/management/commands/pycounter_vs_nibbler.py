import logging
import re
import typing
from pathlib import Path

from celus_nibbler import Poop, eat
from celus_nigiri import CounterRecord
from django.conf import settings
from django.core.management.base import BaseCommand
from sushi.models import CounterReportType, SushiFetchAttempt

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Compares output pycounter and nibbler on all available tsv/csv files'

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

    def handle(self, *args, **options):
        counter_report_types = {e.code: e for e in CounterReportType.objects.all()}

        if directory := options["directory"]:
            for path in directory.glob("**/*.tsv"):
                self.process_path(path, counter_report_types, regex=options["regex"])
        else:
            # parse files from current nibbler data dir

            # compare files obrained via sushi
            for path in (Path(settings.MEDIA_ROOT) / "counter").glob("**/*.tsv"):
                self.process_path(path, counter_report_types, regex="^4_([^_]+)_")

            # compare manually uploaded
            for path in (Path(settings.MEDIA_ROOT) / "custom").glob("**/*.tsv"):
                self.process_path(path, counter_report_types, regex="^([^_]+)-")

    def process_path(
        self, path: Path, counter_report_types: typing.Dict[str, CounterReportType], regex: str
    ):

        if crt := re.match(regex, path.name):
            crt = crt.group(1)
            if crt := counter_report_types.get(crt):
                pycounter_count, nibbler_count, same = self.compare(path, crt)
                print(path, pycounter_count, nibbler_count, not bool(same))
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
        typing.Optional[int],
        typing.Optional[typing.Tuple[typing.List[str], typing.List[str]]],
    ]:
        pycounter_output = self.parse_pycounter(path, counter_report_type)
        pycounter_count = len(pycounter_output) if pycounter_output else pycounter_output
        nibbler_output = self.parse_nibbler(path)
        nibbler_count = len(nibbler_output) if nibbler_output else nibbler_output

        if nibbler_output != pycounter_output and nibbler_output and pycounter_output:
            first_diff = pycounter_output[0], nibbler_output[0]
        else:
            first_diff = None

        return pycounter_count, nibbler_count, first_diff

    def format_record(self, record: CounterRecord) -> typing.List[str]:
        # Skip empty dimensions (None vs "")
        record.dimension_data = {k: v for k, v in record.dimension_data.items() if v}
        # Skip empty titles (None vs "")
        record.title_ids = {k: v for k, v in record.title_ids.items() if v}

        res = list(record.as_csv())
        del res[1]  # pycounter doesn't have end_date set
        return res

    def parse_pycounter(
        self, path, counter_report_type: CounterReportType
    ) -> typing.Optional[typing.List[tuple]]:
        with path.open('rb') as f:
            is_json = SushiFetchAttempt.file_is_json_s(f)
        if reader_class := counter_report_type.get_reader_class(is_json):
            reader = reader_class()
            try:
                return sorted([self.format_record(r) for r in reader.file_to_records(str(path))])
            except Exception as e:
                logger.warn("Pycounter crashed: %s", e)
                return None
        return None

    def parse_nibbler(self, path) -> typing.Optional[typing.List[tuple]]:

        try:
            poops = eat(path, platform="Some", check_platform=False)
            if poops and isinstance(poops[0], Poop):
                return sorted([self.format_record(r) for r in poops[0].records()])
        except Exception as e:
            logger.warn("Nibbler crashed: %s", e)
            return None

        return None
