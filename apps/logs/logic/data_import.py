import csv
import gc
import logging
from collections import Counter
from datetime import date
from io import StringIO
from time import time
from typing import Dict, Generator, Iterable, List, Optional, Set, Tuple, Union

from celus_nigiri import CounterRecord
from core.logic.debug import log_memory
from core.models import UL_ROBOT
from core.task_support import cache_based_lock
from django.conf import settings
from django.db.transaction import atomic, on_commit
from django.utils.timezone import now
from organizations.models import Organization
from publications.logic.item_management import ItemManager
from publications.logic.title_management import TitleManager
from publications.models import Platform, PlatformTitle
from sushi.models import SushiFetchAttempt

from logs.logic.copy_from_saving import IBCopyMapping
from logs.logic.get_or_create_with_map import get_or_create_with_map
from logs.logic.interest.computation import (
    find_superseded_import_batches,
    recompute_interest_by_batch,
    sync_interest_for_import_batch,
)
from logs.models import ImportBatch

from ..exceptions import (
    DataAlreadyPresent,
    ReportDataValidityError,
    UnknownMetric,
    UnsupportedMetric,
)
from ..models import AccessLog, DimensionText, Metric, ReportType
from .materialized_reports import sync_materialized_reports_for_import_batch

logger = logging.getLogger(__name__)

COUNTER_RECORD_BUFFER_SIZE = settings.COUNTER_RECORD_BUFFER_SIZE


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
) -> List[ImportBatch]:
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
) -> Tuple[List[ImportBatch], Counter]:
    """
    If `months` are given, then only import data for the months listed in there, skip others.
    Months are given as strings in ISO format.
    """

    # Make sure that title is not present in IR_M1 reports
    if report_type.short_name == "IR_M1":

        def convert_records(records):
            for record in records:
                record: CounterRecord
                record.title = None
                record.title_ids = {}
                yield record

        records = (e for e in convert_records(records))

    stats = Counter()
    tm = TitleManager()
    im = ItemManager()
    # mapping of months to import batches - has to be shared between calls to
    # _import_counter_record so that the same import batches are used for all data
    month_to_ib = {}
    # the following accumulates values to be inserted later on
    # the data there are not subject to splitting to buffers because they are relatively
    # small anyway
    ib_id_to_key_to_value = {}
    # the key in the above dict of dicts will be as follows:
    ib_id_to_key_structure = ["metric_id", "target_id", "item_id"] + [
        f"dim{i + 1}" for i, dim in enumerate(report_type.dimensions_sorted)
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
            im,
            month_to_ib,
            ib_id_to_key_to_value,
            ib_id_to_key_structure,
        )

    buff: List[CounterRecord] = []
    buff_idx = 0
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
            logger.info("Preprocessed buffer #%d", buff_idx)
            buff_idx += 1
            buff = []
            gc.collect()

    # flush the rest of the buffer
    if buff:
        logger.info("Preprocessed buffer #%d", buff_idx)
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
            rec = dict(zip(ib_id_to_key_structure, key, strict=True))
            rec["value"] = value
            if rec["target_id"]:
                target_ids.add(rec["target_id"])
            if i == 0:
                # write the CSV header
                writer.writerow(sorted(rec.keys()))
            writer.writerow([v for k, v in sorted(rec.items())])
            stats["new logs"] += 1
        ib.record_count = stats["new logs"]
        ib.save(update_fields=["record_count"])
        ingest_import_batch_data(ib, csv_data)
        # and insert the PlatformTitle links
        stats += create_platformtitle_links_from_import_batch(ib, target_ids)
        # sync interest
        sync_interest_for_import_batch(ib, interest_rt, skip_clickhouse_sync=True)
        # if interest of this ib supersedes interest of other ibs, then we need to recompute
        # but we only do it in `on_commit` to leave it after the current transaction
        ibs_for_interest_recompute.update({ib.pk for ib in find_superseded_import_batches(ib)})
        # compute materialized report types
        sync_materialized_reports_for_import_batch(ib)

    log_memory("XX3")

    def sync_interest():
        recompute_interest_by_batch(ImportBatch.objects.filter(pk__in=ibs_for_interest_recompute))

    if ibs_for_interest_recompute:
        on_commit(sync_interest, robust=True)

    if not skip_clickhouse_sync and settings.CLICKHOUSE_SYNC_ACTIVE:
        from .clickhouse import sync_import_batch_with_clickhouse

        def sync_with_clickhouse():
            # note: sync_import_batch_with_clickhouse is atomic
            for import_batch in import_batches:
                logger.debug(
                    "Synced %d records into ClickHouse",
                    sync_import_batch_with_clickhouse(import_batch),
                )

        on_commit(sync_with_clickhouse, robust=True)
    for i, cache in enumerate([tm._counter_rec_to_title_rec_cache, tm._title_rec_to_title_cache]):
        logger.info(f"Title manager: step #{i + 1} {cache.stats()}")
    for i, cache in enumerate([im._counter_rec_to_item_rec_cache, im._item_rec_to_item_cache]):
        logger.info(f"Item manager: step #{i + 1} {cache.stats()}")

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
        if clashing_ib := ImportBatch.objects.filter(
            report_type=report_type, platform=platform, organization=organization, date=month
        ).first():
            raise DataAlreadyPresent(
                clashing_ib,
                f'Clashing import batch exists for report type "{report_type}"'
                f', platform "{platform}", organization "{organization}" and date "{month}"',
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
    Wipes all empty or partial_data import batches which are conflicting with function arguments
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


def prepare_titles(
    tm: TitleManager, records: Iterable[CounterRecord], stats: Counter
) -> List[Optional[int]]:
    title_recs = [tm.counter_record_to_title_rec(rec) for rec in records]
    tm.prefetch_titles(e for e in title_recs if e)
    res = [title_rec and tm.get_or_create(title_rec) for title_rec in title_recs]
    stats["warn missing title"] += sum(not e for e in res)
    return res


def prepare_items(im, records: Iterable[CounterRecord], stats: Counter):
    item_recs = [im.counter_record_to_item_rec(e) for e in records]
    im.prefetch_items(e for e in item_recs if e)
    res = [item_rec and im.get_or_create(item_rec) for item_rec in item_recs]
    stats["warn missing item"] += sum(not e for e in res)
    return res


# According to the COUNTER CoP (
# https://cop5.projectcounter.org/en/5.1/03-specifications/03-counter-report-common-attributes-and-elements.html#data-types
# Table 3.q), the following Data_Types should have Parent_Data_Types and thus
# require title_id to be present when item_id is present:
#
# - Article
# - Book_Segment
# - Conference_Item
# - Database_Full_Item
# - News_Item
# - Reference_Item
#
# The same is true for Data_Types which should only be in title report (mapped from the above),
# but if we find them in item report, we should expect parent data to be present as well:
#
# - Journal
# - Book
# - Conference
# - Database_Full
# - Newspaper_or_Newsletter
# - Reference_Work
#
# According to Tasha, any Data_Type not present in the above linked table should not have
# Parent_Data_Type and thus should not require title_id to be present when item_id is present.


PARENT_REQUIRING_DATA_TYPES = [
    # Data_Types
    "Article",
    "Book_Segment",
    "Conference_Item",
    "Database_Full_Item",
    "News_Item",
    "Reference_Item",
    # Parent_Data_Types
    "Journal",
    "Book",
    "Conference",
    "Database_Full",
    "Newspaper_or_Newsletter",
    "Reference_Work",
]


def check_item_and_title_presence(
    record: CounterRecord, title_id: Optional[int], item_id: Optional[int]
):
    """
    Ensures that - when the record requires it - title_id is present when item_id is present.
    This ensures that we do not ingest IR data without corresponding title data (when the SUSHI
    provider does not respect Include_Parent_Details) which would not allow
    us to compute interest on the title level from the item report.
    """
    if item_id and not title_id:
        # check that the data type does not belong to the list of data types that require parent
        if (dt := record.dimension_data.get("Data_Type")) in PARENT_REQUIRING_DATA_TYPES:
            raise ReportDataValidityError(
                "Parent identificaton is missing in record containing item which requires it "
                f"(Data_Type={dt}). Item='{record.item}', {record.item_ids}. "
                "This is likely caused by the SUSHI provider not respecting "
                "Include_Parent_Details, which means the item level data is unusable as it would "
                "cause inconsistencies between the Item and Title reports."
            )


def _preprocess_counter_records(
    report_type: ReportType,
    records: Iterable[CounterRecord],
    stats: Counter,
    tm: TitleManager,
    im: ItemManager,
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
    log_memory("X-1.3")
    title_ids = prepare_titles(tm, records, stats)
    item_ids = prepare_items(im, records, stats)
    # prepare raw data to be inserted into the database
    dimensions = report_type.dimensions_sorted
    log_memory("X-1")

    record: CounterRecord
    last_log = time()
    for title_id, item_id, record in zip(title_ids, item_ids, records, strict=True):
        # check if the record is valid first
        check_item_and_title_presence(record, title_id, item_id)
        # attributes that define the identity of the log
        if isinstance(record.metric, int):
            # we can pass a specific metric by numeric ID
            metric_id = record.metric
        else:
            metric_id = get_or_create_metric(metrics, record.metric, controlled_metrics)
        start = record.start.isoformat() if isinstance(record.start, date) else record.start
        import_batch = month_to_import_batch[start]
        id_attrs = {"metric_id": metric_id, "target_id": title_id, "item_id": item_id}
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
            id_attrs[f"dim{i + 1}"] = dim_value
        # here we detect possible duplicated keys and merge matching records
        key = tuple(id_attrs[k] for k in ib_id_to_key_structure)
        # we prepare the data to insert already split by individual import batch
        to_insert = ib_id_to_key_to_value[import_batch.pk]
        if key in to_insert:
            to_insert[key] += record.value
        else:
            to_insert[key] = record.value
        if time() - last_log > 10:
            # log statistics every 10 seconds so that we can see the progress and celerus
            # does not try to kill us :)
            logger.info("Title statistics sofar: %s", tm.stats)
            last_log = time()
    logger.info("Title statistics: %s", tm.stats)
    logger.info("Item statistics: %s", im.stats)


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


def create_platformtitle_links_from_accesslogs(accesslogs: List[AccessLog]) -> List[PlatformTitle]:
    """
    Creates all the required platformtitle objects from a list of accesslogs
    :param accesslogs:
    :return:
    """
    data = {(al.organization_id, al.platform_id, al.target_id, al.date) for al in accesslogs}
    possible_clashing = {
        (pt.organization_id, pt.platform_id, pt.title_id, pt.date)
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
