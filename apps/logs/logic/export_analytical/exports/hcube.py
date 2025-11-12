import logging
import re
import unicodedata
from collections import namedtuple
from typing import Any, Callable, Dict, List, Optional, Type
from urllib.parse import parse_qs, urlparse

from core.logic.debug import log_memory
from core.logic.type_conversion import strtobool
from django.utils.timezone import now
from hcube.api.backend import CubeBackend
from hcube.api.models.cube import Cube
from hcube.api.models.dimensions import (
    ArrayDimension,
    DateDimension,
    Dimension,
    IntDimension,
    StringDimension,
)
from hcube.api.models.metrics import IntMetric, Metric
from hcube.backends.clickhouse import ClickhouseCubeBackend, IndexDefinition
from hcube.backends.postgres import PostgresCubeBackend

from logs.cubes import AccessLogCube, ch_backend

from .generic import AnalyticalExportBackend

logger = logging.getLogger(__name__)


def sanitize_identifier(s: str) -> str:
    # Normalize accents (e.g., á → a, č → c)
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("utf-8")

    # Replace non-alphanumeric with underscore
    s = re.sub(r"[^0-9a-zA-Z]", "_", s)

    # Remove leading/trailing underscores
    s = s.strip("_")

    return s


def assert_valid_identifier(iden: str):
    if not valid_identifier(iden):
        raise ValueError(f"invalid ClickHouse identifier: {iden}")


def valid_identifier(iden: str) -> bool:
    # hcube doesn't sanitize identifiers, so we do basic enforcement
    # note: we don't check Clickhouse keywords
    return re.fullmatch("[a-zA-Z0-9_]*", iden) is not None


def get_dynamic_cube(
    table_name: str, cols: Dict[str, str], dim_help_texts: Dict[str, str]
) -> Type[Cube]:
    tn = table_name  # scope workaround
    assert_valid_identifier(table_name)

    class ExportCube(Cube):
        organization_id = IntDimension(
            signed=False, bits=32, help_text="Internal CELUS id for the organization"
        )
        organization__name = StringDimension(
            clickhouse={"low_cardinality": True}, help_text="Name of the organization"
        )
        platform_id = IntDimension(
            signed=False, bits=32, help_text="Internal CELUS id for the platform"
        )
        platform__name = StringDimension(
            clickhouse={"low_cardinality": True}, help_text="Name of the platform"
        )
        platform__counter_registry_id = StringDimension(  # TODO UUID Dimension
            clickhouse={"low_cardinality": True}, help_text="Counter registry ID of the platform"
        )
        date = DateDimension(help_text="Date of the usage")
        metric_id = IntDimension(
            signed=False, bits=32, help_text="Internal CELUS id for the metric"
        )
        metric__short_name = StringDimension(
            clickhouse={"low_cardinality": True},
            help_text="Short name of the metric, for COUNTER matches the COUNTER metric name",
        )

        if "title_id" in cols.values():
            title_id = IntDimension(
                signed=False, bits=32, help_text="Internal CELUS id of the title"
            )
            title__name = StringDimension(help_text="Name of the title")
            title__pub_type = StringDimension(help_text="Publication type of the title")
            title__isbn = StringDimension(help_text="ISBN of the title")
            title__issn = StringDimension(help_text="ISSN of the title")
            title__eissn = StringDimension(help_text="e-ISSN of the title")
            title__doi = StringDimension(help_text="DOI of the title")

        if "item_id" in cols.values():
            item_id = IntDimension(signed=False, bits=32, help_text="Internal CELUS id of the item")
            item__name = StringDimension(help_text="Name of the item")
            item__publication_date = DateDimension(help_text="Publication date of the item")
            item__isbn = StringDimension(help_text="ISBN of the item")
            item__eissn = StringDimension(help_text="e-ISSN of the item")
            item__doi = StringDimension(help_text="DOI of the item")

        # explicit dimensions
        for col, translated in cols.items():
            if col.startswith("dim"):
                assert_valid_identifier(translated)
                help_text = dim_help_texts.get(translated, "")
                locals()[translated] = StringDimension(
                    clickhouse={"low_cardinality": True}, help_text=help_text
                )

        value = IntMetric(signed=False, bits=32, help_text="Value of the metric - the usage count")
        import_batch_id = IntDimension(
            signed=False,
            bits=32,
            help_text="Internal CELUS id of the import batch - this groups together data from one "
            "import (harvest, manual upload, etc.). One import batch always covers one month.",
        )

        # tags
        for k in cols:
            if k.endswith("tags"):
                locals()[k] = ArrayDimension(
                    dimension=StringDimension(clickhouse={"low_cardinality": True})
                )

        class Clickhouse:
            table_name = tn
            primary_key = ["organization_id", "platform_id", "date", "metric_id"]
            sorting_key = ["organization_id", "platform_id", "date", "metric_id"]
            if "title_id" in cols.values():
                sorting_key.append("title_id")
            if "item_id" in cols.values():
                sorting_key.append("item_id")

            partition_key = ["toYear(date)"]
            indexes = [
                # skipping index to make finding data by import batch faster
                IndexDefinition(
                    name="idx_import_batch_id",
                    expression="import_batch_id",
                    type="set(0)",
                    granularity=1,
                )
            ]
            engine = "MergeTree"
            use_lightweight_deletes = True

    if set(cols.values()) != (set(ExportCube._dimensions.keys()) | set(ExportCube._metrics.keys())):
        raise ValueError("the requested columns do not match the cube")
    return ExportCube


def url_to_hcube_connection(url: str) -> (CubeBackend, str):
    parsed = urlparse(url)
    path = parsed.path.strip("/").split("/")
    if len(path) != 2:
        raise ValueError("/<database>/<table> required in output URL")
    attrs = {
        "host": parsed.hostname,
        "port": parsed.port or None,
        "user": parsed.username or "",
        "password": parsed.password or "",
        "database": path[0],
        **{
            k: strtobool(v[0]) for k, v in parse_qs(parsed.query).items()
        },  # binary flags from URL params
    }
    if not attrs["host"]:
        raise ValueError("host required in output URL")
    table = path[1]
    if parsed.scheme == "ch":
        cube_backend = ClickhouseCubeBackend(**attrs)
    elif parsed.scheme == "pg":
        cube_backend = PostgresCubeBackend(**attrs)
    else:
        raise ValueError(f"unsupported scheme: {parsed.scheme}")
    return cube_backend, table


def fill_default(row: List, col_defaults: List) -> List:
    for i in range(len(row)):
        if row[i] is None:
            row[i] = col_defaults[i]
    return row


class HCubeExport(AnalyticalExportBackend):
    """Direct hcube export backend."""

    NAME = "hcube"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cube: Optional[Type[Cube]] = None
        self.record: Optional[namedtuple] = None
        self.batch: List[Optional[namedtuple]] = []
        self.batch_size = kwargs.get("batch_size", 100_000)
        # We dont want tag cols here, as they will be exported as separate tables
        self.tags = False

        self.import_batch_ids: Optional[List[int]] = None
        self.cube_backend: Optional[CubeBackend] = None
        self.table: Optional[str] = None
        try:
            if isinstance(self.output, str) and self.output:
                self.cube_backend, self.table = url_to_hcube_connection(self.output)
            else:
                self.table = kwargs["table"]
                self.cube_backend = kwargs["cube_backend"]
        except:
            self.stderr.write(
                "\nExpected cube_backend, table arguments, "
                "or a correct URL in the output argument like: "
                "(ch|pg)://user:password@host:port/database/table?secure=True&verify=True\n"
            )
            raise

        self.cols = {k: sanitize_identifier(v) for k, v in self.cols.items()}
        assert_valid_identifier(self.table)
        dim_help_texts = self._get_dim_help_texts()
        self.cube = get_dynamic_cube(self.table, self.cols, dim_help_texts=dim_help_texts)
        self.record = self.cube.record_type()
        self.cube_backend.initialize_storage(self.cube)
        # if the table exists, we want to make sure its structure is up to date
        # `recreate=True` ensures that the table is dropped and recreated with the new schema
        # if it cannot be synced otherwise (e.g. when dropping sorting key columns)
        self.cube_backend.sync_storage(self.cube, drop=True, recreate=True)
        self.stats = {
            "new_records_count": 0,
            "new_ibs_count": 0,
            "total_ib_count": 0,
            "deleted_ibs_count": 0,
        }
        self._col_defaults = []
        self._col_names = []
        for col in self.cols.values():
            self._col_names.append(col)
            dim: Dimension = getattr(self.cube, col)
            if isinstance(dim, Metric):
                self._col_defaults.append(0)
            elif not dim.null:
                self._col_defaults.append(dim.default)
            else:
                self._col_defaults.append(None)

    def _get_dim_help_texts(self) -> Dict[str, str]:
        dim_help_texts: Dict[str, str] = {}
        for i, dim in enumerate(self.rt.dimensions_sorted):
            col_key = f"dim{i + 1}"
            translated = self.cols.get(col_key)
            if translated:
                dim_help_texts[translated] = getattr(dim, "desc", "")
        return dim_help_texts

    def _export_row(self, row: Dict[str, Any]):
        # fill empty values
        for i, col in enumerate(self._col_names):
            # deal with empty values (mostly 0 instead of None from original query)
            if not row[col]:
                row[col] = self._col_defaults[i]

        self.batch.append(row)
        self.stats["new_records_count"] += 1
        if len(self.batch) >= self.batch_size:
            self._write_batch()

    def _write_batch(self):
        log_memory(f"before store_records: {self.stats}")
        self.cube_backend.store_records(self.cube, self.batch, skip_cleanup=True, dict_records=True)
        self.batch = []

    def _query_filter(self, query):
        query = super()._query_filter(query)
        if self.import_batch_ids is not None:
            query = query.filter(import_batch_id__in=self.import_batch_ids)
        return query

    def _pre_export(self, _):
        self.stderr.write("Loading ImportBatch IDs for a diff...")
        # get the import batch ids from local clickhouse
        where = {"report_type_id": self.rt.id}
        if self.organization:
            where["organization_id"] = self.organization.id
        local_ibs = {
            rec.import_batch_id
            for rec in ch_backend.get_records(
                AccessLogCube.query().filter(**where).group_by("import_batch_id")
            )
        }
        self.stats["total_ib_count"] = len(local_ibs)
        logger.debug(f"Local import batch IDs: {len(local_ibs)}")
        remote_ibs = {
            i.import_batch_id
            for i in self.cube_backend.get_records(self.cube.query().group_by("import_batch_id"))
        }
        logger.debug("Remote import batch IDs: %d", len(remote_ibs))
        to_delete = list(remote_ibs - local_ibs)
        logger.debug("To delete: %d - extra in CH", len(to_delete))
        logger.debug("To add: %d - extra in local", len(local_ibs - remote_ibs))
        logger.debug("Common ibs: %d", len(local_ibs & remote_ibs))

        self.stats["new_ibs_count"] = len(local_ibs - remote_ibs)
        if remote_ibs:
            # set a filter to only export new import batches, unless we are doing a full export
            self.import_batch_ids = list(local_ibs - remote_ibs)

        if to_delete:
            self.stderr.write(f"Deleting {len(to_delete)} import batches from cube...")
            self.cube_backend.delete_records(
                self.cube.query().filter(import_batch_id__in=to_delete)
            )
            self.stats["deleted_ibs_count"] = len(to_delete)

    def export(self, progress_monitor: Optional[Callable[[int, int], None]] = None):
        count = self._export(progress_monitor=progress_monitor)
        self._write_batch()

        comment = f"{self.rt.name}; last update: {now().isoformat(timespec='seconds')}"
        if isinstance(self.cube_backend, ClickhouseCubeBackend):
            try:
                with self.cube_backend.pool.get_client() as client:
                    table_name = self.cube_backend.cube_to_full_table_name(self.cube)
                    client.execute(
                        f"ALTER TABLE {table_name} MODIFY COMMENT %(comment)s", {"comment": comment}
                    )
            except:
                self.stderr.write("Failed to set comment on the table")
                raise
        return count
