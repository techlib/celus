from collections import Counter

from django.core.management.base import BaseCommand
from django.db.transaction import atomic
from logs.logic.attempt_import import reprocess_attempt
from logs.models import DIMENSION_COUNT, ImportBatch

from sushi.models import AttemptStatus, SushiFetchAttempt

DB_ITER_SIZE = 5_000


class Command(BaseCommand):
    help = "Checks whether the data are the same after reimport"

    def add_arguments(self, parser):
        parser.add_argument("-a", dest="attempt_id", type=int, help="Attempt ID", required=True)

    def handle(self, *args, **options):
        attempt = SushiFetchAttempt.objects.get(pk=options["attempt_id"])

        if attempt.status != AttemptStatus.SUCCESS:
            raise ValueError("Attempt was not successfully imported")

        try:
            with atomic():
                # store import batch to compare it later
                old_ib = attempt.import_batch
                SushiFetchAttempt.objects.filter(pk=attempt.pk).update(import_batch=None)

                # We need to be sure that unique constraint of ImportBatch is no violated
                # so we alter the date here
                ImportBatch.objects.filter(pk=old_ib.pk).update(date="2000-01-01")

                attempt.refresh_from_db()
                reprocess_attempt(attempt)

                order_bys = [
                    "organization",
                    "platform",
                    "report_type",
                    "target",
                    "metric",
                    "date",
                ] + [f"dim{i + 1}" for i in range(DIMENSION_COUNT)]

                # Compare ibs (assuming that accesslogs are created in the same order)
                old_iter = old_ib.accesslog_set.order_by(*order_bys).iterator(DB_ITER_SIZE)
                new_iter = attempt.import_batch.accesslog_set.order_by(*order_bys).iterator(
                    DB_ITER_SIZE
                )

                counter = Counter()
                while True:
                    old = next(old_iter, None)
                    new = next(new_iter, None)

                    if old:
                        counter["old"] += 1
                        if new:
                            # Compare records
                            if different := old.compare(new):
                                for item in different:
                                    counter[item] += 1
                            else:
                                counter["same"] += 1

                            counter["new"] += 1
                        else:
                            pass
                    else:
                        if new:
                            counter["new"] += 1
                        else:
                            break
                raise RuntimeError("Terminate transaction")
        except RuntimeError:
            pass

        print(counter)
