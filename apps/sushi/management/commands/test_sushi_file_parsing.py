import logging
import math
import pathlib
import sys
from collections import Counter

from celus_nigiri.client import SushiException
from core.models import SourceFileMixin
from django.conf import settings
from django.core.files.base import File
from django.core.management.base import BaseCommand
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import Coalesce
from sushi.models import AttemptStatus, CounterReportType, SushiFetchAttempt

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Goes through all successfully downloaded sushi files and retries to parse them'

    def add_arguments(self, parser):
        parser.add_argument('--print', dest='print', action='store_true', help='print each file')
        parser.add_argument('file', nargs="*", help='only process those files')

    def handle(self, *args, **options):
        stats = Counter()
        qs = (
            SushiFetchAttempt.objects.filter(
                status=AttemptStatus.SUCCESS, import_batch__isnull=False
            )
            .values('data_file', 'counter_report', 'checksum')
            .annotate(
                log_count=Count(
                    'import_batch__accesslog',
                    filter=Q(import_batch__accesslog__report_type=F('counter_report__report_type')),
                ),
                log_sum=Coalesce(
                    Sum(
                        'import_batch__accesslog__value',
                        filter=Q(
                            import_batch__accesslog__report_type=F('counter_report__report_type')
                        ),
                    ),
                    0,
                ),
            )
        )
        if options['file']:
            qs = qs.filter(data_file__in=options['file'])
        counter_report_types = {e.pk: e for e in CounterReportType.objects.all()}
        total = qs.count()
        total_indent = int(math.log10(total)) + 1
        for idx, attempt in enumerate(qs.iterator()):
            log_sum = 0
            path = pathlib.Path(settings.MEDIA_ROOT) / attempt['data_file']
            if options["print"]:
                print(f"{idx + 1:0{total_indent}}/{total} {path} - ", end="")

            if not path.exists():
                stats["missing"] += 1
                if options["print"]:
                    print("MISSING")
                continue

            with path.open('rb') as f:
                is_json = SushiFetchAttempt.file_is_json_s(f)

            reader = counter_report_types[attempt['counter_report']].get_reader_class(is_json)()
            if not reader:
                stats["unsupported"] += 1
                if options["print"]:
                    print("UNSUPPORTED")
                continue

            with path.open('rb') as f:
                checksum, _ = SourceFileMixin.checksum_fileobj(File(f))

            if checksum != attempt["checksum"]:
                stats["wrong_checksum"] += 1
                if options["print"]:
                    print("WRONG CHECKSUM")
                continue

            try:
                records = reader.file_to_records(str(path))
                for idx, record in enumerate(records):
                    log_sum += record.value
            except SushiException as exc:
                stats["error"] += 1
                if options["print"]:
                    print("ERROR")
                    print(exc, file=sys.stderr)
            except Exception:
                stats["unhandled_error"] += 1
                if options["print"]:
                    print("UNHANDLED ERROR")
            else:
                log_count = idx + 1
                if attempt["log_sum"] == log_sum:
                    stats["ok"] += 1
                    if options["print"]:
                        print(f"OK (SUM {log_sum}, COUNT {log_count})")
                else:
                    stats["wrong_sum"] += 1
                    if options["print"]:
                        print(
                            f"WRONG SUM (SUM {log_sum}!={attempt['log_sum']}, COUNT "
                            f"{log_count}!={attempt['log_count']})"
                        )

        print(stats)
