import csv
import gc
import logging
from collections import Counter
from datetime import date
from io import StringIO
from typing import Dict, Generator, Iterable, List, Optional, Set, Union

from celus_nigiri import CounterRecord
from core.logic.debug import log_memory
from core.models import UL_ROBOT
from core.task_support import cache_based_lock
from django.conf import settings
from django.db.transaction import atomic, on_commit
from django.utils.timezone import now
from organizations.models import Organization
from postgres_copy import CopyMapping
from publications.logic.title_management import TitleManager, TitleRec
from publications.models import Platform, PlatformTitle
from sushi.models import SushiFetchAttempt

from logs.models import ImportBatch

from ..exceptions import DataStructureError, UnknownMetric, UnsupportedMetric
from ..models import AccessLog, DimensionText, Metric, ReportType
from .materialized_interest import (
    find_superseeded_import_batches,
    recompute_interest_by_batch,
    sync_interest_for_import_batch,
)
from .materialized_reports import sync_materialized_reports_for_import_batch

logger = logging.getLogger(__name__)

COUNTER_RECORD_BUFFER_SIZE = settings.COUNTER_RECORD_BUFFER_SIZE


def get_or_create_with_map(model, mapping, attr_name, attr_value, other_attrs=None) -> int:
    if attr_value in mapping:
        return mapping[attr_value]["pk"]
    data = {attr_name: attr_value}
    if other_attrs:
        data.update(other_attrs)
    obj, created = model.objects.get_or_create(**data)
    data["pk"] = obj.pk
    mapping[attr_value] = data
    return obj.pk


def get_or_create_metric(mapping, value, controlled_metrics: List[str] = None) -> int:
    # already in mapping
    if record := mapping.get(value):
        return record["pk"]

    if settings.AUTOMATICALLY_CREATE_METRICS and not controlled_metrics:
        # When metric auto create of metrics is allowed and metrics doesn't
        # need to be check just create it without further checking
        return get_or_create_with_map(Metric, mapping, "short_name", value)
    else:
        try:
            # Metric is supposed to exist
            metric = Metric.objects.get(short_name=value)
        except Metric.DoesNotExist:
            raise UnknownMetric(value) from None

        if controlled_metrics:
            # check for controlled metrics
            if value not in controlled_metrics:
                raise UnsupportedMetric(value)

        # update mapping
        mapping[value] = {"short_name": metric.short_name, "pk": metric.pk}

        return metric.pk


@atomic
def import_empty_batches(
    report_type: ReportType,
    organization: Organization,
    platform: Platform,
    months: Iterable[str],
    import_batch_kwargs: dict,
) -> [ImportBatch]:
    return [
        create_import_batch_or_crash(
            report_type, organization, platform, month, ib_kwargs=import_batch_kwargs
        )
        for month in months
    ]


@atomic
def import_counter_records(
    report_type: ReportType,
    organization: Organization,
    platform: Platform,
    records: Union[Generator[CounterRecord, None, None], Iterable[CounterRecord]],
    months: Optional[Iterable[str]] = None,
    import_batch_kwargs: Optional[dict] = None,
    skip_clickhouse_sync: bool = False,
    buffer_size: int = COUNTER_RECORD_BUFFER_SIZE,
) -> ([ImportBatch], Counter):
    """
    If `months` are given, then only import data for the months listed in there, skip others.
    Months are given as strings in ISO format.
    """
    stats = Counter()
    tm = TitleManager()
    # mapping of months to import batches - has to be shared between calls to
    # _import_counter_record so that the same import batches are used for all data
    month_to_ib = {}
    # the following accumulates values to be inserted later on
    # the data there are not subject to splitting to buffers because they are relatively
    # small anyway
    ib_id_to_key_to_value = {}
    # the key in the above dict of dicts will be as follows:
    ib_id_to_key_structure = ["metric_id", "target_id"] + [
        f"dim{i+1}" for i, dim in enumerate(report_type.dimensions_sorted)
    ]

    def process_buffer(record_batch: Iterable[CounterRecord]):
        """
        Internal function not to repeat the same code twice.
        Please note that we do not create all the import batches upfront because we do not want
        to evaluate the whole `records` generator as it may be quite large. This is why we do all
        by chunks/buffer
        """
        # check and prepare import batches
        months_in_data = {
            rec.start.isoformat() if isinstance(rec.start, date) else rec.start
            for rec in record_batch
        }

        # the following would crash if we tried to create an import batch for month that already
        # has an import batch
        for month in months_in_data:
            if month not in month_to_ib:
                month_to_ib[month] = create_import_batch_or_crash(
                    report_type, organization, platform, month, ib_kwargs=import_batch_kwargs
                )
        for ib in month_to_ib.values():
            if ib.pk not in ib_id_to_key_to_value:
                ib_id_to_key_to_value[ib.pk] = {}
        return _preprocess_counter_records(
            report_type,
            record_batch,
            stats,
            tm,
            month_to_ib,
            ib_id_to_key_to_value,
            ib_id_to_key_structure,
        )

    buff: List[CounterRecord] = []
    for record in records:
        # check months and skip early to avoid extra work on multi-month files
        if (
            months
            and (record.start.isoformat() if isinstance(record.start, date) else record.start)
            not in months
        ):
            continue

        buff.append(record)
        if len(buff) >= buffer_size:
            process_buffer(buff)
            buff = []
            gc.collect()

    # flush the rest of the buffer
    if buff:
        process_buffer(buff)

    # after this, the ib_id_to_key_to_value is full and we can process it
    import_batches = list(month_to_ib.values())
    interest_rt = ReportType.objects.get_interest_rt()
    ibs_for_interest_recompute = set()
    for ib in import_batches:
        csv_data = StringIO()
        writer = csv.writer(csv_data)
        target_ids = set()
        for i, (key, value) in enumerate(ib_id_to_key_to_value[ib.pk].items()):
            rec = dict(zip(ib_id_to_key_structure, key))
            rec["value"] = value
            if rec["target_id"]:
                target_ids.add(rec["target_id"])
            if i == 0:
                # write the CSV header
                writer.writerow(sorted(rec.keys()))
            writer.writerow([v for k, v in sorted(rec.items())])
            stats["new logs"] += 1
        ingest_import_batch_data(ib, csv_data)
        # and insert the PlatformTitle links
        stats += create_platformtitle_links_from_import_batch(ib, target_ids)
        # sync interest
        sync_interest_for_import_batch(ib, interest_rt, skip_clickhouse_sync=True)
        # if interest of this ib supersedes interest of other ibs, then we need to recompute
        # but we only do it in `on_commit` to leave it after the current transaction
        ibs_for_interest_recompute.update(
            set(find_superseeded_import_batches(ib).values_list("pk", flat=True))
        )
        # compute materialized report types
        sync_materialized_reports_for_import_batch(ib)

    log_memory("XX3")

    def sync_interest():
        recompute_interest_by_batch(ImportBatch.objects.filter(pk__in=ibs_for_interest_recompute))

    if ibs_for_interest_recompute:
        on_commit(sync_interest)

    if not skip_clickhouse_sync and settings.CLICKHOUSE_SYNC_ACTIVE:
        from .clickhouse import sync_import_batch_with_clickhouse

        def sync_with_clickhouse():
            # note: sync_import_batch_with_clickhouse is atomic
            for import_batch in import_batches:
                logger.debug(
                    "Synced %d records into ClickHouse",
                    sync_import_batch_with_clickhouse(import_batch),
                )

        on_commit(sync_with_clickhouse)
    for i, cache in enumerate([tm._counter_rec_to_title_rec_cache, tm._title_rec_to_title_cache]):
        logger.info(
            f"Title manager: step #{i+1} cache hits: {cache._hits}, misses: {cache._misses}, "
            f"size: {len(cache)}"
        )

    return import_batches, stats


def create_import_batch_or_crash(
    report_type: ReportType,
    organization: Organization,
    platform: Platform,
    month: Union[str, date],
    ib_kwargs: Optional[dict] = None,
) -> ImportBatch:
    """
    Creates an import batch if a matching one does not exist yet. Raises an error otherwise.
    Note: In the future, we will have db constraints preventing clashing import batches from
          appearing, but we need to do a cleanup before that, so we cannot add them right now.
    """
    # we need the lock to prevent race conditions in creating the import batch
    with cache_based_lock(
        f"create_import_batch_{report_type.pk}_{organization.pk}_{platform.pk}_{month}",
        blocking_timeout=10,
    ):
        if ImportBatch.objects.filter(
            report_type=report_type, platform=platform, organization=organization, date=month
        ):
            raise DataStructureError(
                f'Clashing import batch exists for report type "{report_type}"'
                f', platform "{platform}", organization "{organization}" and date "{month}"'
            )
        kwargs = ib_kwargs or {}
        return ImportBatch.objects.create(
            report_type=report_type,
            platform=platform,
            organization=organization,
            date=month,
            **kwargs,
        )


def wipe_empty_or_partial_import_batches(
    report_type: ReportType, organization: Organization, platform: Platform, month: Union[str, date]
) -> int:
    """
    Whipes all empty or partial_data import batches which are conlicting with function arguments
    """
    count = 0

    # Note that there should be only one ib,
    # but DB constraint haven't been introduced yet.
    #
    # Still iterating over ib will be quite efficient here,
    # because the number of conflicting ib's should be really low.
    for ib in ImportBatch.objects.filter(
        report_type=report_type, platform=platform, organization=organization, date=month
    ):
        if (
            SushiFetchAttempt.objects.filter(import_batch_id=ib.pk, partial_data=True).exists()
        ) or not ib.accesslog_set.all().exists():
            ib.delete()
            count += 1

    return count


def _preprocess_counter_records(
    report_type: ReportType,
    records: Iterable[CounterRecord],
    stats: Counter,
    tm: TitleManager,
    month_to_import_batch: Dict[str, ImportBatch],
    ib_id_to_key_to_value: Dict[int, Dict],
    ib_id_to_key_structure: list,
):
    # prepare controlled metrics filtering
    controlled_metrics = list(report_type.controlled_metrics.values_list("short_name", flat=True))

    # prepare all remaps
    metrics = {
        metric["short_name"]: metric
        for metric in Metric.objects.values("pk", "short_name")
        if not controlled_metrics or metric["short_name"] in controlled_metrics
    }

    text_to_int_remaps = {}
    log_memory("X-2")
    for dim_text in DimensionText.objects.values("dimension_id", "text", "pk"):
        if dim_text["dimension_id"] not in text_to_int_remaps:
            text_to_int_remaps[dim_text["dimension_id"]] = {}
        text_to_int_remaps[dim_text["dimension_id"]][dim_text["text"]] = dim_text
    log_memory("X-1.5")
    title_recs = [tm.counter_record_to_title_rec(rec) for rec in records]
    tm.prefetch_titles(title_recs)
    # prepare raw data to be inserted into the database
    dimensions = report_type.dimensions_sorted
    log_memory("X-1")

    title_rec: TitleRec
    record: CounterRecord
    for title_rec, record in zip(title_recs, records):
        # attributes that define the identity of the log
        title_id = tm.get_or_create(title_rec)
        if title_id is None:
            # the title could not be found or created (probably missing required field like title)
            stats["warn missing title"] += 1
        if isinstance(record.metric, int):
            # we can pass a specific metric by numeric ID
            metric_id = record.metric
        else:
            metric_id = get_or_create_metric(metrics, record.metric, controlled_metrics)
        start = record.start.isoformat() if isinstance(record.start, date) else record.start
        import_batch = month_to_import_batch[start]
        id_attrs = {"metric_id": metric_id, "target_id": title_id}
        for i, dim in enumerate(dimensions):
            dim_value = record.dimension_data.get(dim.short_name)
            if dim_value is not None:
                remap = text_to_int_remaps.get(dim.pk)
                if not remap:
                    remap = {}
                    text_to_int_remaps[dim.pk] = remap
                dim_value = get_or_create_with_map(
                    DimensionText, remap, "text", dim_value, other_attrs={"dimension_id": dim.pk}
                )
            id_attrs[f"dim{i+1}"] = dim_value
        # here we detect possible duplicated keys and merge matching records
        key = tuple(id_attrs[k] for k in ib_id_to_key_structure)
        # we prepare the data to insert already split by individual import batch
        to_insert = ib_id_to_key_to_value[import_batch.pk]
        if key in to_insert:
            to_insert[key] += record.value
        else:
            to_insert[key] = record.value
    logger.info("Title statistics: %s", tm.stats)


def create_platformtitle_links_from_import_batch(import_batch: ImportBatch, target_ids: Set[int]):
    """
    Based on the platform and organization from the import_batch and a list of unique
    title_ids creates the corresponding PlatformTitle records
    and creates the explicit PlatformTitle objects from the data
    """
    pt_qs = PlatformTitle.objects.filter(
        organization_id=import_batch.organization_id,
        platform_id=import_batch.platform_id,
        date=import_batch.date,
    )
    existing = set(pt_qs.values_list("title_id", flat=True))
    pts = []
    before_count = len(existing)
    for title_id in target_ids - existing:
        pts.append(
            PlatformTitle(
                organization_id=import_batch.organization_id,
                platform_id=import_batch.platform_id,
                title_id=title_id,
                date=import_batch.date,
            )
        )
    PlatformTitle.objects.bulk_create(pts, ignore_conflicts=True)
    after_count = pt_qs.count()
    return {"new platformtitles": after_count - before_count}


def create_platformtitle_links_from_accesslogs(accesslogs: [AccessLog]) -> [PlatformTitle]:
    """
    Creates all the required platformtitle objects from a list of accesslogs
    :param accesslogs:
    :return:
    """
    data = {(al.organization_id, al.platform_id, al.target_id, al.date) for al in accesslogs}
    possible_clashing = {
        (pt.organization_id, pt.platform_id, pt.target_id, pt.date)
        for pt in PlatformTitle.objects.filter(
            organization_id__in={rec[0] for rec in data},
            platform_id__in={rec[1] for rec in data},
            title_id__in={rec[2] for rec in data},
            date__in={rec[3] for rec in data},
        )
    }
    to_create = [
        PlatformTitle(organization_id=rec[0], platform_id=rec[1], title_id=rec[2], date=rec[3])
        for rec in (data - possible_clashing)
    ]
    return PlatformTitle.objects.bulk_create(to_create, ignore_conflicts=True)


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


def ingest_import_batch_data(import_batch: ImportBatch, file_content: StringIO):
    """
    Look for a CSV file with the preprocessed data to be ingested into the AccessLog table.
    """
    log_memory("XX6")
    file_content.seek(0)
    c = IBCopyMapping(
        AccessLog,
        file_content,
        import_batch.pk,
        static_mapping={
            "created": now(),
            "owner_level": UL_ROBOT,
            "import_batch_id": import_batch.pk,
            "date": import_batch.date,
            "platform_id": import_batch.platform_id,
            "report_type_id": import_batch.report_type_id,
            "organization_id": import_batch.organization_id,
        },
    )
    c.save()
    log_memory("XX7")
