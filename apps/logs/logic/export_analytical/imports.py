class DbImport:
    COLS_TYPES = {}

    def __init__(self, cols, report_type, organization=None, platform=None):
        self.cols = cols
        self.rt = report_type
        self.organization = organization
        self.platform = platform

    def _get_col(self, orig, translated):
        for k, v in self.COLS_TYPES.items():
            if orig.startswith(k):
                return translated + " " + v
        raise KeyError

    def generate_table(self, tb_name) -> str:
        raise NotImplementedError

    def generate_import(self, tb_name, db_name, **kwargs) -> str:
        if db_name == "csv":
            return self.generate_csv_import(tb_name, kwargs["path"])
        elif db_name == "parquet":
            return self.generate_parquet_import(tb_name, kwargs["path"])
        else:
            raise ValueError(f"Unknown format name: {db_name}")

    def generate_csv_import(self, tb_name, file):
        raise NotImplementedError

    def generate_parquet_import(self, tb_name, file):
        raise NotImplementedError


class PostgresqlImport(DbImport):
    NAME = "postgresql"
    COLS_TYPES = {
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
        "tags": "text[]",
        "internal_tags": "text[]",
        "organization_tags": "text[]",
        "platform_tags": "text[]",
    }

    def generate_table(self, tb_name):
        s = ",\n  ".join((self._get_col(k, v) for k, v in self.cols.items()))
        return f"CREATE TABLE {tb_name} (\n  {s}\n);"

    def generate_csv_import(self, tb_name, file):
        out = ""
        if "tags" in self.cols:
            out += (
                "WARNING: Postgres cannot import this CSV due to the tags array column, "
                "because it is not wrapped in {}.\n\n"
            )
        if file.endswith(".gz") or file.endswith(".zst") or file.endswith(".zstd"):
            program = "zcat" if file.endswith(".gz") else "zstdcat"
            return out + (
                f"COPY {tb_name} FROM PROGRAM '{program} {file}'"
                " WITH ( FORMAT CSV, DELIMITER ',', HEADER MATCH );\n"
                "-- requires pg_execute_server_program privilege\n"
                "-- or you can use \\copy instead of COPY from psql, or a command with 'FROM STDIN'"
            )
        return out + (
            f"COPY {tb_name} FROM '{file}' WITH ( FORMAT CSV, DELIMITER ',', HEADER MATCH );\n"
            "-- requires pg_read_server_files privilege\n"
            "-- or you can use \\copy instead of COPY from psql, or a command with 'FROM STDIN'"
        )

    def generate_parquet_import(self, tb_name, file):
        return "You need to use an external tool like pg_parquet"


class ClickhouseImport(DbImport):
    NAME = "clickhouse"
    COLS_TYPES = {
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
        "tags": "Array(LowCardinality(String))",
        "internal_tags": "Array(LowCardinality(String))",
        "organization_tags": "Array(LowCardinality(String))",
        "platform_tags": "Array(LowCardinality(String))",
    }

    def generate_table(self, tb_name):
        s = ",\n  ".join((self._get_col(k, v) for k, v in self.cols.items()))
        return (
            f"CREATE TABLE {tb_name} (\n  {s}\n) "
            "ENGINE = MergeTree "
            "PARTITION BY toYear(date) "
            "ORDER BY (organization_id, platform_id, metric_id, title_id, date);"
        )

    def generate_csv_import(self, tb_name, file):
        compression = ""
        if file.endswith(".gz") or file.endswith(".zst") or file.endswith(".zstd"):
            method = "gzip" if file.endswith(".gz") else "zstd"
            compression = f"COMPRESSION '{method}' "
        return f"INSERT INTO {tb_name} FROM INFILE '{file}' {compression}FORMAT CSV;"

    def generate_parquet_import(self, tb_name, file):
        return f"INSERT INTO {tb_name} FROM INFILE '{file}' FORMAT Parquet;"
