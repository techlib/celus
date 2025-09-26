import os.path
from datetime import datetime
from typing import Any, Dict

import pyarrow as pa
import pyarrow.parquet as pq

from ..imports import ClickhouseImport, PostgresqlImport
from .generic import AnalyticalExportBackend

PARQUET_IMPORTS = [PostgresqlImport, ClickhouseImport]


class ParquetExport(AnalyticalExportBackend):
    NAME = "parquet"

    def __init__(self, force_overwrite=False, **kwargs):
        super().__init__(**kwargs)
        self.force_overwrite = force_overwrite
        self.path = self.output
        if self.path is None:
            self.path = os.path.abspath(self.rt.short_name + ".parquet")
        self._writer = None
        self._schema = None
        self._batch_size = 10000  # Write in batches for memory efficiency
        self._current_batch = []

    def _pre_export(self, cols):
        # Create schema based on column types
        schema_fields = []
        for col in cols:
            if col in ("internal_tags", "tags"):
                # Tags will be list of strings
                schema_fields.append(pa.field(col, pa.list_(pa.string())))
            elif col in [
                "metric_id",
                "organization_id",
                "platform_id",
                "target_id",
                "title_id",
                "import_batch_id",
            ]:
                schema_fields.append(pa.field(col, pa.int32()))
            elif col == "value":
                schema_fields.append(pa.field(col, pa.uint32()))
            elif col == "date":
                schema_fields.append(pa.field(col, pa.date32()))
            else:
                # All other fields as strings
                schema_fields.append(pa.field(col, pa.string()))

        self._schema = pa.schema(schema_fields)

        # Create ParquetWriter for streaming
        self._writer = pq.ParquetWriter(self.path, self._schema, compression="snappy")

    def _export_row(self, row: Dict[str, Any]):
        # Convert row data to appropriate types for Arrow
        arrow_row = []
        for i, value in enumerate(row.values()):
            field_type = self._schema.field(i).type

            if field_type == pa.list_(pa.string()):
                # Handle tags list
                if value is None or value == []:
                    arrow_row.append([])
                else:
                    arrow_row.append(value if isinstance(value, list) else [str(value)])
            elif field_type == pa.int32():
                arrow_row.append(int(value) if value is not None else 0)
            elif field_type == pa.uint32():
                arrow_row.append(int(value) if value is not None else 0)
            elif field_type == pa.date32():
                if value is not None:
                    # Convert date string to Arrow date
                    if isinstance(value, str):
                        date_obj = datetime.strptime(value, "%Y-%m-%d").date()
                        arrow_row.append(date_obj)
                    else:
                        arrow_row.append(value)
                else:
                    arrow_row.append(None)
            else:
                # All other fields as strings
                arrow_row.append(str(value) if value is not None else "")

        # Add to current batch
        self._current_batch.append(arrow_row)

        # Write batch if it reaches the batch size
        if len(self._current_batch) >= self._batch_size:
            self._write_batch()

    def _write_batch(self):
        if not self._current_batch:
            return

        # Create Arrow arrays from batch
        arrays = []
        for col_idx in range(len(self._schema)):
            col_values = [row[col_idx] for row in self._current_batch]
            field_type = self._schema.field(col_idx).type

            arrays.append(pa.array(col_values, type=field_type))

        # Create record batch and write
        batch = pa.RecordBatch.from_arrays(arrays, schema=self._schema)
        self._writer.write_batch(batch)

        # Clear the batch
        self._current_batch = []

    def export(self):
        try:
            if not self.force_overwrite and os.path.exists(self.path):
                self.stderr.write(
                    self.style.ERROR("The file already exists! Use -f to force overwrite")
                )
                self.stderr.write(self.style.ERROR(self.path))
                raise FileExistsError(self.path)

            # Run the export process
            count = self._export()

            # Write any remaining rows in the batch
            self._write_batch()

            # Close the writer
            if self._writer:
                self._writer.close()

            self.stderr.write(f"Exported data to {self.path}")

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error exporting to parquet: {e}"))
            if self._writer:
                self._writer.close()
            raise
        self.show_import_instructions(PARQUET_IMPORTS, path=self.path)
        return count
