import csv
import gzip
import os.path
from functools import partial

import zstandard
from django.core.exceptions import MultipleObjectsReturned

from logs.models import AccessLog, DimensionText, ReportType


class NoopMeta(type):
    def noop(*_, **__):
        pass

    def __getattr__(self, _):
        return self.noop


class Noop(metaclass=NoopMeta):
    pass


class AnalyticalExportBackend:
    NAME = "dummy"
    COLS = {
        "id": "id",
        "metric_id": "metric_id",
        "metric__short_name": "metric__short_name",
        "organization_id": "organization_id",
        "organization__name": "organization__name",
        "platform_id": "platform_id",
        "platform__name": "platform__name",
        "target_id": "title_id",
        "target__name": "title__name",
        "target__pub_type": "title__pub_type",
        "target__isbn": "title__isbn",
        "target__issn": "title__issn",
        "target__eissn": "title__eissn",
        "target__doi": "title__doi",
        "value": "value",
        "date": "date",
        "import_batch_id": "import_batch_id",
    }

    DIM_BEFORE = ("value", "date", "import_batch_id")

    def __init__(self, **kwargs):
        self.rt = kwargs.get("report_type", None)
        self.stdout = kwargs.get("stdout", Noop)
        self.stderr = kwargs.get("stderr", Noop)
        self.style = kwargs.get("style", Noop)
        self.cols = self.COLS.copy()

    def _pre_export(self):
        pass

    def _export_row(self, row):
        pass

    def _export(self):
        append = {k: self.cols.pop(k) for k in self.DIM_BEFORE}

        self.stderr.write("Waiting for DB...")

        dim_text = []
        for n, dim in enumerate(self.rt.dimensions_sorted):
            self.cols[f"dim{n + 1}"] = str(dim).lower()
            d = {}
            for text in (
                DimensionText.objects.filter(dimension=dim).values_list("id", "text").iterator()
            ):
                d[text[0]] = text[1]
            dim_text.append(d)

        self.cols.update(append)

        self._pre_export()

        dim_pos = list(self.cols).index("dim1")
        c = 0
        for al in (
            AccessLog.objects.filter(report_type=self.rt)
            .values_list(*self.cols)
            .iterator(chunk_size=1000)
        ):
            al = list(al)
            for n, dim in enumerate(dim_text):
                if al[dim_pos + n] is not None:
                    al[dim_pos + n] = dim[al[dim_pos + n]]
            self._export_row(al)
            c += 1
            if c % 10000 == 1:
                percent = ""
                if self.rt.approx_record_count > 0:
                    percent = f" {c / self.rt.approx_record_count * 100: >6.2f}%"
                self.stderr.write("\r" + "/-\\|"[c // 10000 % 4] + percent, ending="")

    def export(self):
        raise NotImplementedError


class DbBackend(AnalyticalExportBackend):
    COLS_TYPES = {}

    def _get_col(self, orig, translated):
        for k, v in self.COLS_TYPES.items():
            if orig.startswith(k):
                return translated + " " + v
        raise KeyError

    def generate_table(self, tb_name):
        raise NotImplementedError

    def generate_csv_import(self, tb_name, file):
        raise NotImplementedError


class PostgresqlBackend(DbBackend):
    NAME = "postgresql"
    COLS_TYPES = {
        "id": "integer NOT NULL",
        "metric_id": "integer",
        "metric__short_name": "character varying(100)",
        "organization_id": "integer",
        "organization__name": "character varying(250)",
        "platform_id": "integer",
        "platform__name": "character varying(250)",
        "target_id": "integer",
        "target__name": "text",
        "target__pub_type": "character varying(1)",
        "target__isbn": "character varying(20)",
        "target__issn": "character varying(9)",
        "target__eissn": "character varying(9)",
        "target__doi": "character varying(250)",
        "value": "integer NOT NULL",
        "date": "date NOT NULL",
        "import_batch_id": "integer NOT NULL",
        "dim": "text",
    }

    def generate_table(self, tb_name):
        s = ",\n  ".join((self._get_col(k, v) for k, v in self.cols.items()))
        return f"CREATE TABLE {tb_name} (\n  {s}\n);"

    def generate_csv_import(self, tb_name, file):
        if file.endswith(".gz") or file.endswith(".zst") or file.endswith(".zstd"):
            program = "zcat" if file.endswith(".gz") else "zstdcat"
            return (
                f"COPY {tb_name} FROM PROGRAM '{program} {file}'"
                " WITH ( FORMAT CSV, DELIMITER ',', HEADER MATCH );\n"
                "-- requires pg_execute_server_program privilege\n"
                "-- or you can use \\copy instead of COPY from psql, or a command with 'FROM STDIN'"
            )
        return (
            f"COPY {tb_name} FROM '{file}' WITH ( FORMAT CSV, DELIMITER ',', HEADER MATCH );\n"
            "-- requires pg_read_server_files privilege\n"
            "-- or you can use \\copy instead of COPY from psql, or a command with 'FROM STDIN'"
        )


class ClickhouseBackend(DbBackend):
    NAME = "clickhouse"
    COLS_TYPES = {
        "id": "Int32",
        "metric_id": "Int32",
        "metric__short_name": "LowCardinality(String)",
        "organization_id": "Int32",
        "organization__name": "LowCardinality(String)",
        "platform_id": "Int32",
        "platform__name": "LowCardinality(String)",
        "target_id": "Int32",
        "target__name": "String",
        "target__pub_type": "String",
        "target__isbn": "String",
        "target__issn": "String",
        "target__eissn": "String",
        "target__doi": "String",
        "value": "UInt32",
        "date": "Date",
        "import_batch_id": "Int32",
        "dim": "LowCardinality(String)",
    }

    def generate_table(self, tb_name):
        s = ",\n  ".join((self._get_col(k, v) for k, v in self.cols.items()))
        return f"CREATE TABLE {tb_name} (\n  {s}\n) ENGINE = MergeTree ORDER BY id;"

    def generate_csv_import(self, tb_name, file):
        compression = ""
        if file.endswith(".gz") or file.endswith(".zst") or file.endswith(".zstd"):
            method = "gzip" if file.endswith(".gz") else "zstd"
            compression = f"COMPRESSION '{method}' "
        return f"INSERT INTO {tb_name} FROM INFILE '{file}' {compression}FORMAT CSV;"


class CsvBackend(AnalyticalExportBackend):
    NAME = "csv"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.path = kwargs["path"]
        if self.path is None:
            self.path = os.path.abspath(self.rt.short_name + ".csv.zst")
        self._writer = None
        self._header_done = False

    def _pre_export(self):
        self._writer.writerow(self.cols.values())

    def _export_row(self, row):
        self._writer.writerow(row)

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
            fp = o(self.path, "xt", newline="")
        except FileExistsError:
            self.stderr.write(self.style.ERROR("The file already exists! Exiting"))
            self.stderr.write(self.style.ERROR(self.path))
            return
        else:
            try:
                self._writer = csv.writer(fp, dialect="excel")
                self._export()
            finally:
                fp.close()

        for db in CSV_IMPORTS:
            self.stderr.style_func = None
            self.stderr.write("\n---")
            self.stderr.write(self.style.WARNING(f"Import to: {db.NAME}"))
            self.stderr.write("")
            db = db()
            db.cols = self.cols
            tb_name = "report_" + self.rt.short_name
            try:
                ReportType.objects.get(short_name=self.rt.short_name)
            except MultipleObjectsReturned:
                self.stderr.write(
                    self.style.WARNING(
                        "Warning: There are multiple ReportTypes with the same short name"
                    )
                )
            self.stderr.write(db.generate_table(tb_name))
            self.stderr.write("")
            self.stderr.write(db.generate_csv_import(tb_name, self.path))


BACKENDS = [CsvBackend]

BACKENDS = {b.NAME: b for b in BACKENDS}

CSV_IMPORTS = [PostgresqlBackend, ClickhouseBackend]
