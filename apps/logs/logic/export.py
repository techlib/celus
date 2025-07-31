import codecs
import csv
import logging
import os
from time import monotonic
from typing import IO
from zipfile import ZIP_DEFLATED, ZipFile

from cachalot.api import cachalot_disabled
from core.logic.debug import log_memory
from django.conf import settings
from django.core.cache import cache
from django.utils.timezone import now
from hcube.api.models.aggregation import Count as HCount
from hcube.api.models.transforms import StoredMap

from ..cubes import AccessLogCube, AccessLogCubeRecord, ch_backend
from ..models import DIMENSION_COUNT, AccessLog, DimensionText, ReportType

logger = logging.getLogger(__name__)


class CSVExport:
    implicit_dims = {
        "platform": "name",
        "metric": "short_name",
        "organization": "name",
        "target": "name",
        "report_type": "short_name",
        "date": None,
    }
    title_attrs = ["isbn", "issn", "eissn"]
    outdir = "export"

    def __init__(
        self,
        query_params: dict,
        zip_compress: bool = False,
        filename_base=None,
        use_clickhouse=False,
    ):
        self.query_params = query_params
        self.zip_compress = zip_compress
        self.use_clickhouse = use_clickhouse
        if filename_base:
            self.filename_base = filename_base
        else:
            self.filename_base = self.create_filename_base()

    def create_filename_base(self) -> str:
        ts = now().strftime("%Y%m%d-%H%M%S.%f")
        filename = f"raw-data-{ts}"
        return filename

    @property
    def filename(self) -> str:
        if self.zip_compress:
            fname = self.filename_base + ".zip"
        else:
            fname = self.filename_base + ".csv"
        return os.path.join(self.outdir, fname)

    @property
    def file_url(self) -> str:
        return settings.MEDIA_URL + self.filename

    @property
    def file_path(self) -> str:
        return os.path.join(settings.MEDIA_ROOT, self.filename)

    @classmethod
    def create_outdir(cls):
        outdir = os.path.join(settings.MEDIA_ROOT, cls.outdir)
        if not os.path.exists(outdir):
            os.mkdir(outdir)

    def create_queryset(self):
        # we do not want to export materialized reports
        # the following query performs slightly better than adding the report_type filter
        # report_type__materialization_spec__isnull=True directly to the query
        # probably because it avoids a join
        mrts = list(ReportType.objects.only_materialized().values_list("id", flat=True))
        return AccessLog.objects.filter(**self.query_params).exclude(report_type_id__in=mrts)

    @property
    def record_count(self):
        if self.use_clickhouse:
            # here we use the fact that access log ids are stored in clickhouse in the `id` field
            return ch_backend.get_one_record(
                AccessLogCube.query().filter(**self.query_params).aggregate(HCount(distinct="id"))
            ).count
        return self.create_queryset().count()

    def export_raw_accesslogs_to_file(self):
        self.create_outdir()
        if self.zip_compress:
            with ZipFile(self.file_path, "w", compression=ZIP_DEFLATED) as outzip:
                with outzip.open(self.filename_base + ".csv", "w", force_zip64=True) as outfile:
                    writer = codecs.getwriter("utf-8")
                    encoder = writer(outfile)
                    self.export_raw_accesslogs_to_stream_lowlevel(encoder)
        else:
            with open(self.file_path, "w") as outfile:
                self.export_raw_accesslogs_to_stream_lowlevel(outfile)

    def store_error(self):
        self.store_progress(-1)

    def store_progress(self, value):
        cache.set(self.filename_base, value)

    def get_used_report_types(self):
        if self.use_clickhouse:
            return ReportType.objects.filter(
                pk__in=[
                    rec.report_type_id
                    for rec in ch_backend.get_records(
                        AccessLogCube.query().filter(**self.query_params).group_by("report_type_id")
                    )
                ]
            )
        return ReportType.objects.filter(
            pk__in=self.create_queryset().distinct("report_type_id").values("report_type_id")
        )

    def export_raw_accesslogs_to_stream_lowlevel(self, stream: IO):
        if self.use_clickhouse:
            self.export_raw_accesslogs_to_stream_lowlevel_clickhouse(stream)
            return
        queryset = self.create_queryset()
        start = monotonic()
        log_memory("1")
        text_id_to_text = {
            dt["id"]: dt["text"] for dt in DimensionText.objects.all().values("id", "text")
        }
        logger.debug("Finished loading text remaps: %.2f s", monotonic() - start)
        log_memory("2")
        rt_to_dimensions = {rt.pk: rt.dimensions_sorted for rt in self.get_used_report_types()}
        logger.debug("Finished loading report_types and dimensions: %.2f s", monotonic() - start)
        # get all field names for the CSV
        field_name_map = {
            (f"{dim}__{attr}" if attr else dim): dim for dim, attr in self.implicit_dims.items()
        }
        field_name_map.update({f"target__{attr}": attr for attr in self.title_attrs})
        field_names = list(field_name_map.values())
        for dims in rt_to_dimensions.values():
            field_names += [dim.short_name for dim in dims if dim.short_name not in field_names]
        field_names.append("value")
        logger.debug("Finished preparing field names: %.2f s", monotonic() - start)
        log_memory("3")
        # values that will be retrieved from the accesslogs
        values = ["value", "report_type_id"]
        values += list(field_name_map.keys())
        values += [f"dim{i + 1}" for i in range(DIMENSION_COUNT)]
        # crate the writer
        writer = csv.DictWriter(stream, field_names)
        writer.writeheader()
        logger.debug("Finished preparing CSV writer: %.2f s", monotonic() - start)
        # write the records
        rec_num = 0
        with cachalot_disabled(True):
            # disable cachalot for this query because it returns a potentially huge number
            # of records and would clog the cache
            rec_num: int
            log: dict
            for rec_num, log in enumerate(queryset.values(*values).iterator()):
                record = {
                    attr_out: log.get(attr_in) for attr_in, attr_out in field_name_map.items()
                }
                record["value"] = log["value"]
                record["date"] = log["date"]
                for i, dim in enumerate(rt_to_dimensions[log["report_type_id"]]):
                    value = log.get(f"dim{i + 1}")
                    record[dim.short_name] = text_id_to_text.get(value, value)
                writer.writerow(record)
                if rec_num % 999 == 0:
                    self.store_progress(rec_num + 1)
                if rec_num % 99999 == 0:
                    logger.debug("Stored %d records: %.2f s", rec_num, monotonic() - start)
                    log_memory(f"4: {rec_num}")
            logger.debug("Stored %d records: %.2f s", rec_num, monotonic() - start)
            log_memory(f"5: {rec_num}")
        self.store_progress(rec_num + 1)

    def export_raw_accesslogs_to_stream_lowlevel_clickhouse(self, stream: IO):
        dim_texts = {
            f"dim{i + 1}_text": StoredMap(f"dim{i + 1}", "dim", "text")
            for i in range(DIMENSION_COUNT)
        }
        query = (
            AccessLogCube.query()
            .filter(**self.query_params)
            .transform(
                report_type=StoredMap("report_type_id", "report_type", "short_name"),
                platform=StoredMap("platform_id", "platform", "name"),
                target=StoredMap("target_id", "title", "name"),
                target__issn=StoredMap("target_id", "title", "issn"),
                target__eissn=StoredMap("target_id", "title", "eissn"),
                target__isbn=StoredMap("target_id", "title", "isbn"),
                target__doi=StoredMap("target_id", "title", "doi"),
                organization=StoredMap("organization_id", "organization", "name"),
                metric=StoredMap("metric_id", "metric", "short_name"),
                **dim_texts,
            )
        )
        start = monotonic()
        log_memory("1")
        rt_to_dimensions = {rt.pk: rt.dimensions_sorted for rt in self.get_used_report_types()}
        logger.debug("Finished loading report_types and dimensions: %.2f s", monotonic() - start)
        # get all field names for the CSV
        field_name_map = {dim: dim for dim, attr in self.implicit_dims.items()}
        field_name_map.update({f"target__{attr}": attr for attr in self.title_attrs})
        field_names = list(field_name_map.values())

        for dims in rt_to_dimensions.values():
            field_names += [dim.short_name for dim in dims if dim.short_name not in field_names]
        field_names.append("value")
        logger.debug("Finished preparing field names: %.2f s", monotonic() - start)
        log_memory("3")
        # values that will be retrieved from the accesslogs
        values = ["value", "report_type_id"]
        values += list(field_name_map.keys())
        values += [f"dim{i + 1}" for i in range(DIMENSION_COUNT)]
        # crate the writer
        writer = csv.DictWriter(stream, field_names)
        writer.writeheader()
        logger.debug("Finished preparing CSV writer: %.2f s", monotonic() - start)
        # write the records
        rec_num: int = 0
        log: AccessLogCubeRecord
        records = []
        for rec_num, log in enumerate(ch_backend.get_records(query, streaming=True)):
            record = {
                attr_out: getattr(log, attr_in) for attr_in, attr_out in field_name_map.items()
            }
            record["value"] = log.value
            record["date"] = log.date
            for i, dim in enumerate(rt_to_dimensions[log.report_type_id]):
                record[dim.short_name] = getattr(log, f"dim{i + 1}_text")
            records.append(record)
            if rec_num % 1000 == 0:
                self.store_progress(rec_num)
                writer.writerows(records)
                records = []
            if rec_num % 100_000 == 0:
                logger.debug("Stored %d records: %.2f s", rec_num, monotonic() - start)
                log_memory(f"4: {rec_num}")
        writer.writerows(records)
        logger.debug("Stored %d records: %.2f s", rec_num, monotonic() - start)
        log_memory(f"5: {rec_num}")
        self.store_progress(rec_num + 1)
