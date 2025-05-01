import csv
import threading
from io import StringIO
from typing import Dict, List

from core.models import UL_ROBOT
from django.utils.timezone import now
from postgres_copy import CopyMapping

from logs.models import AccessLog


class ThreadSafeCopyMapping(CopyMapping):
    """
    A thread-safe version of CopyMapping that uses a temporary table name dependent on the
    current thread ID.
    """

    def __init__(self, model, csv_path_or_obj, **kwargs):
        super().__init__(model, csv_path_or_obj, {}, **kwargs)
        self.temp_table_name = f"{self.temp_table_name}_{threading.get_ident()}"


class IBCopyMapping(CopyMapping):
    """
    The original CopyMapping is not thread-safe as it always uses the same temporary
    table. This version uses a table name dependent on the import batch ID, which should
    be safe enough for our use case.
    """

    def __init__(self, model, csv_path_or_obj, ib_id, **kwargs):
        # the third argument is mapping, which is detected automatically from the CSV
        # header, so we just pass an empty dict here
        super().__init__(model, csv_path_or_obj, {}, **kwargs)
        self.temp_table_name = f"{self.temp_table_name}_{ib_id}"


def insert_new_accesslogs(new_log_dicts: List[Dict], **kwargs):
    """
    Add interest to postgres using a very efficient bulk insert by COPY FROM.

    **kwargs are params which are passed statically to all the records.
    """
    if not new_log_dicts:
        return
    csv_data = StringIO()
    writer = csv.writer(csv_data)
    writer.writerow(sorted(new_log_dicts[0].keys()))
    for rec in new_log_dicts:
        writer.writerow([rec[k] for k in sorted(rec.keys())])

    static_mapping = {"created": now(), "owner_level": UL_ROBOT, **kwargs}
    csv_data.seek(0)
    c = ThreadSafeCopyMapping(AccessLog, csv_data, static_mapping=static_mapping)
    c.save()
