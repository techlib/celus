import csv
import gzip
import io
import os.path
from functools import partial
from typing import Any, Dict, List, Optional

import zstandard

from ..imports import ClickhouseImport, PostgresqlImport
from .generic import AnalyticalExportBackend


def convert_list_to_csv_row(items) -> str:
    with io.StringIO() as output:
        writer = csv.writer(output)
        writer.writerow(items)
        return output.getvalue().strip()


CSV_IMPORTS = [PostgresqlImport, ClickhouseImport]


class CsvExport(AnalyticalExportBackend):
    NAME = "csv"

    def __init__(self, force_overwrite=False, **kwargs):
        super().__init__(**kwargs)
        self.force_overwrite = force_overwrite
        self.path = self.output
        if self.path is None:
            self.path = os.path.abspath(self.rt.short_name + ".csv.zst")
        self._writer = None
        self._header_done = False
        self._cols = []

    def _pre_export(self, cols):
        self._cols = cols
        self._writer.writerow(cols)

    def _export_row(self, row: Dict[str, Any]):
        # remap empty values to None unless it's the value column
        self._writer.writerow([row[k] or (None if k != "value" else 0) for k in self._cols])

    def from_list(self, lst: Optional[List]):
        if lst is None:
            return None
        return convert_list_to_csv_row(lst)

    def export(self):
        o = open
        if self.path.endswith(".gz"):
            o = gzip.open
        elif self.path.endswith(".zst") or self.path.endswith(".zstd"):
            # level=6 seems to give a very good compression ratio while not slowing down the
            # export too much
            cctx = zstandard.ZstdCompressor(level=6)
            o = partial(zstandard.open, cctx=cctx)
        try:
            fp = o(self.path, "wt" if self.force_overwrite else "xt", newline="")
        except FileExistsError:
            self.stderr.write(
                self.style.ERROR("The file already exists! Use -f to force overwrite")
            )
            self.stderr.write(self.style.ERROR(self.path))
            raise
        try:
            self._writer = csv.writer(fp, dialect="excel")
            count = self._export()
        finally:
            fp.close()
        self.show_import_instructions(CSV_IMPORTS, path=self.path)
        return count
