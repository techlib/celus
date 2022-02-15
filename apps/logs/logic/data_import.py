import gc
import logging
import typing
from collections import Counter, namedtuple
from datetime import date
from typing import Optional, Tuple, Set

from django.conf import settings
from django.db.models import F
from django.db.transaction import atomic, on_commit

from core.logic.debug import log_memory
from core.task_support import cache_based_lock
from logs.logic.validation import clean_and_validate_issn, normalize_isbn
from logs.models import ImportBatch
from nigiri.counter5 import CounterRecord
from organizations.models import Organization
from publications.models import Title, Platform, PlatformTitle
from ..exceptions import DataStructureError
from ..models import ReportType, Metric, DimensionText, AccessLog

logger = logging.getLogger(__name__)

COUNTER_RECORD_BUFFER_SIZE = 10000


def get_or_create_with_map(model, mapping, attr_name, attr_value, other_attrs=None) -> int:
    if attr_value not in mapping:
        data = {attr_name: attr_value}
        if other_attrs:
            data.update(other_attrs)
        obj, created = model.objects.get_or_create(**data)
        data["pk"] = obj.pk
        mapping[attr_value] = data
        return obj.pk
    else:
        return mapping[attr_value]["pk"]


TitleRec = namedtuple('TitleRec', ('name', 'pub_type', 'issn', 'eissn', 'isbn', 'doi'))


class TitleManager:
    def __init__(self):
        self.key_to_title_id_and_pub_type = {}
        self.stats = Counter()

    def prefetch_titles(self, records: [TitleRec]):
        title_qs = Title.objects.all()
        for attr_name in ('issn', 'eissn', 'isbn', 'doi', 'name'):
            attr_values = {getattr(rec, attr_name) for rec in records}
            title_qs = title_qs.filter(**{attr_name + '__in': attr_values})
        self.key_to_title_id_and_pub_type = {
            tuple(t[:5]): tuple(t[5:])
            for t in title_qs.order_by().values_list(
                'name', 'isbn', 'issn', 'eissn', 'doi', 'pk', 'pub_type'
            )
        }
        logger.debug('Prefetched %d records', len(self.key_to_title_id_and_pub_type))

    @classmethod
    def normalize_title_rec(cls, record: TitleRec) -> TitleRec:
        """
        Normalize specific fields in the record and return a new TitleRec with normalized data.
        Should be run before one attempts to ingest the data into the database.
        """
        # normalize issn, eissn and isbn - they are sometimes malformed by whitespace in the data
        issn = record.issn
        if issn:
            issn = clean_and_validate_issn(issn, raise_error=False)
        eissn = record.eissn
        if eissn:
            eissn = clean_and_validate_issn(eissn, raise_error=False)
        isbn = normalize_isbn(record.isbn) if record.isbn else record.isbn
        return TitleRec(
            name=record.name,
            isbn=isbn,
            issn=issn,
            eissn=eissn,
            doi=record.doi,
            pub_type=record.pub_type,
        )

    def get_or_create(self, record: TitleRec) -> Optional[int]:
        if not record.name:
            logger.warning(
                'Record is missing or has empty title: ' 'ISBN: %s, ISSN: %s, eISSN: %s, DOI: %s',
                record.isbn,
                record.issn,
                record.eissn,
                record.doi,
            )
            return None
        key = (record.name, record.isbn, record.issn, record.eissn, record.doi)
        if key in self.key_to_title_id_and_pub_type:
            title_pk, db_pub_type = self.key_to_title_id_and_pub_type[key]
            # check if we need to improve the pub_type from UNKNOWN to something better
            if db_pub_type == Title.PUB_TYPE_UNKNOWN and record.pub_type != Title.PUB_TYPE_UNKNOWN:
                logger.info('Upgrading publication type from unknown to "%s"', record.pub_type)
                Title.objects.filter(pk=title_pk).update(pub_type=record.pub_type)
                self.stats['update'] += 1
            else:
                self.stats['existing'] += 1
            return title_pk
        title, created = Title.objects.get_or_create(
            defaults={"pub_type": record.pub_type},
            name=record.name,
            isbn=record.isbn,
            issn=record.issn,
            eissn=record.eissn,
            doi=record.doi,
        )
        self.key_to_title_id_and_pub_type[key] = (title.pk, record.pub_type)
        if created:
            self.stats['created'] += 1
        else:
            self.stats['existing'] += 1
        return title.pk

    def counter_record_to_title_rec(self, record: CounterRecord) -> TitleRec:
        title = record.title
        isbn = None
        issn = None
        eissn = None
        doi = None
        for key, value in record.title_ids.items():
            if key == 'DOI':
                doi = value
            elif key == 'Online_ISSN':
                eissn = clean_and_validate_issn(value, raise_error=False) if value else value
            elif key == 'Print_ISSN':
                issn = clean_and_validate_issn(value, raise_error=False) if value else value
            elif key == 'ISBN':
                isbn = normalize_isbn(value) if value else value
        pub_type = self.deduce_pub_type(eissn, isbn, issn, record)
        # convert None values for the following attrs to empty strings
        isbn = '' if isbn is None else isbn
        issn = '' if issn is None else issn
        eissn = '' if eissn is None else eissn
        doi = '' if doi is None else doi
        return TitleRec(name=title, pub_type=pub_type, isbn=isbn, issn=issn, eissn=eissn, doi=doi)

    def deduce_pub_type(self, eissn, isbn, issn, record):
        pub_type = Title.PUB_TYPE_UNKNOWN
        if 'Data_Type' in record.dimension_data:
            data_type = record.dimension_data['Data_Type']
            pub_type = Title.data_type_to_pub_type(data_type)
        if pub_type == Title.PUB_TYPE_UNKNOWN:
            # we try harder - based on isbn, issn, etc.
            if (issn or eissn) and not isbn:
                pub_type = Title.PUB_TYPE_JOURNAL
            elif isbn and not issn:
                pub_type = Title.PUB_TYPE_BOOK
        return pub_type

    def get_or_create_from_counter_record(self, record: CounterRecord) -> int:
        title_rec = self.counter_record_to_title_rec(record)
        return self.get_or_create(title_rec)

    @classmethod
    def resolve_unknown_title_pub_types_in_db(cls):
        """
        Assigns publication type to Title which have unknown type and the type can be deduced from
        ISBN and ISSN values
        :return:
        """
        # if there is ISBN and both ISSNs are empty -> it is a book
        Title.objects.filter(pub_type=Title.PUB_TYPE_UNKNOWN, issn='', eissn='').exclude(
            isbn=''
        ).update(pub_type=Title.PUB_TYPE_BOOK)
        # if there is no ISBN and at least one ISSN is there -> it is likely a Journal
        Title.objects.filter(pub_type=Title.PUB_TYPE_UNKNOWN, isbn='').exclude(
            issn='', eissn=''
        ).update(pub_type=Title.PUB_TYPE_JOURNAL)


@atomic
def import_counter_records(
    report_type: ReportType,
    organization: Organization,
    platform: Platform,
    records: typing.Generator[CounterRecord, None, None],
    months: typing.Optional[typing.Iterable[str]] = None,
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

    def process_buffer(record_batch: typing.Iterable[CounterRecord]):
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
        if months:
            months_in_data = {month for month in months_in_data if month in months}
            # filter records down to only those that are present in `months` - we do it early
            # to save as much work as possible
            record_batch = [
                rec
                for rec in record_batch
                if (rec.start.isoformat() if isinstance(rec.start, date) else rec.start)
                in months_in_data
            ]

        # the following would crash if we tried to create an import batch for month that already
        # has an import batch
        for month in months_in_data:
            if month not in month_to_ib:
                month_to_ib[month] = create_import_batch_or_crash(
                    report_type, organization, platform, month, ib_kwargs=import_batch_kwargs
                )
        return _import_counter_records(
            report_type, organization, platform, record_batch, stats, tm, month_to_ib
        )

    buff: typing.List[CounterRecord] = []
    for record in records:
        buff.append(record)
        if len(buff) >= buffer_size:
            process_buffer(buff)
            buff = []
            gc.collect()

    # flush the rest of the buffer
    if buff:
        process_buffer(buff)
    import_batches = list(month_to_ib.values())

    if not skip_clickhouse_sync and settings.CLICKHOUSE_SYNC_ACTIVE:
        from .clickhouse import sync_import_batch_with_clickhouse

        def sync_with_clickhouse():
            # note: sync_import_batch_with_clickhouse is atomic
            for import_batch in import_batches:
                logger.debug(
                    'Synced %d records into ClickHouse',
                    sync_import_batch_with_clickhouse(import_batch),
                )

        on_commit(sync_with_clickhouse)

    return import_batches, stats


def create_import_batch_or_crash(
    report_type: ReportType,
    organization: Organization,
    platform: Platform,
    month: typing.Union[str, date],
    ib_kwargs: Optional[dict] = None,
) -> ImportBatch:
    """
    Creates an import batch if a matching one does not exist yet. Raises an error otherwise.
    Note: In the future, we will have db constraints preventing clashing import batches from
          appearing, but we need to do a cleanup before that, so we cannot add them right now.
    """
    # we need the lock to prevent race conditions in creating the import batch
    with cache_based_lock(
        f'create_import_batch_{report_type.pk}_{organization.pk}_{platform.pk}_{month}',
        blocking_timeout=10,
    ):
        if ImportBatch.objects.filter(
            report_type=report_type, platform=platform, organization=organization, date=month
        ):
            raise DataStructureError(
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


def _import_counter_records(
    report_type: ReportType,
    organization: Organization,
    platform: Platform,
    records: typing.List[CounterRecord],
    stats: Counter,
    tm: TitleManager,
    month_to_import_batch: typing.Dict[str, ImportBatch],
):
    # prepare all remaps
    metrics = {
        metric["short_name"]: {"pk": metric["pk"], "short_name": metric["short_name"]}
        for metric in Metric.objects.values("pk", "short_name")
    }
    text_to_int_remaps = {}
    log_memory('X-2')
    for dim_text in DimensionText.objects.values("dimension_id", "text", "pk"):
        if dim_text["dimension_id"] not in text_to_int_remaps:
            text_to_int_remaps[dim_text["dimension_id"]] = {}
        text_to_int_remaps[dim_text["dimension_id"]][dim_text["text"]] = dim_text
    log_memory('X-1.5')
    title_recs = [tm.counter_record_to_title_rec(rec) for rec in records]
    tm.prefetch_titles(title_recs)
    # prepare raw data to be inserted into the database
    dimensions = report_type.dimensions_sorted
    to_insert = {}
    seen_dates = set()
    log_memory('X-1')
    for title_rec, record in zip(title_recs, records):  # type: TitleRec, CounterRecord
        # attributes that define the identity of the log
        title_id = tm.get_or_create(title_rec)
        if title_id is None:
            # the title could not be found or created (probably missing required field like title)
            stats['warn missing title'] += 1
        if type(record.metric) is int:
            # we can pass a specific metric by numeric ID
            metric_id = record.metric
        else:
            metric_id = get_or_create_with_map(Metric, metrics, 'short_name', record.metric)
        start = record.start if not isinstance(record.start, date) else record.start.isoformat()
        id_attrs = {
            'report_type_id': report_type.pk,
            'metric_id': metric_id,
            'organization_id': organization.pk,
            'platform_id': platform.pk,
            'target_id': title_id,
            'date': start,
        }
        for i, dim in enumerate(dimensions):
            dim_value = record.dimension_data.get(dim.short_name)
            if dim.type != dim.TYPE_INT:
                if dim_value is not None:
                    remap = text_to_int_remaps.get(dim.pk)
                    if not remap:
                        remap = {}
                        text_to_int_remaps[dim.pk] = remap
                    dim_value = get_or_create_with_map(
                        DimensionText,
                        remap,
                        'text',
                        dim_value,
                        other_attrs={'dimension_id': dim.pk},
                    )
            else:
                dim_value = int(dim_value) if dim_value is not None else None
            id_attrs[f'dim{i+1}'] = dim_value
        # here we detect possible duplicated keys and merge matching records
        key = tuple(sorted(id_attrs.items()))
        if key in to_insert:
            to_insert[key] += record.value
        else:
            to_insert[key] = record.value
        seen_dates.add(record.start)
    logger.info('Title statistics: %s', tm.stats)
    # compare the prepared data with current database content
    # get the candidates
    log_memory('XX')
    to_compare = {}
    if to_insert:
        to_check = AccessLog.objects.filter(
            organization=organization,
            platform=platform,
            report_type=report_type,
            date__lte=max(seen_dates),
            date__gte=min(seen_dates),
        )
        for al_rec in to_check.values(
            'pk',
            'organization_id',
            'platform_id',
            'report_type_id',
            'date',
            'value',
            'target_id',
            'metric_id',
            *[f'dim{i+1}' for i, d in enumerate(dimensions)],
        ):
            pk = al_rec.pop('pk')
            value = al_rec.pop('value')
            al_rec['date'] = al_rec['date'].isoformat()
            key = tuple(sorted(al_rec.items()))
            to_compare[key] = (pk, value)
    # make the comparison
    log_memory('XX2')
    als_to_insert = []
    target_date_tuples = set()
    max_batch_size = 100_000
    for key, value in to_insert.items():
        db_pk, db_value = to_compare.get(key, (None, None))
        rec = dict(key)
        import_batch = month_to_import_batch[rec['date']]
        if db_pk:
            # There is an accesslog with the same dimensions.
            # It could belong to the same import batch, which means we got it from the same file
            # but in different batches determined by `buffer_size` in `import_counter_records`.
            # In such case, we need to merge it with the existing record,
            # but if it comes from a different IB, we need to raise an error
            # BTW, this operation is relatively expensive, but it should happen only very seldom,
            # so we do not care that much
            clash = AccessLog.objects.get(pk=db_pk)
            if import_batch.pk == clash.import_batch_id:
                # we have an AL from the same batch, just update
                clash.value = F('value') + value
                clash.save()
                logger.warning(f'Merging duplicated values in import batch #{import_batch.pk}')
            else:
                raise DataStructureError(
                    f'Clashing accesslog even though import batch level checks passed: {rec}; '
                    f'Clashing AL is from IB #{clash.import_batch_id} from '
                    f'{clash.import_batch.created}'
                )
        else:
            rec['value'] = value
            als_to_insert.append(AccessLog(import_batch=import_batch, **rec))
            if rec['target_id'] is not None:
                target_date_tuples.add((rec['target_id'], rec['date']))
        if len(als_to_insert) >= max_batch_size:
            log_memory('Batch create')
            AccessLog.objects.bulk_create(als_to_insert)
            stats['new logs'] += len(als_to_insert)
            als_to_insert = []
    # now insert the records that are clean to be inserted
    log_memory('XX3')
    AccessLog.objects.bulk_create(als_to_insert)
    stats['new logs'] += len(als_to_insert)
    log_memory('XX4')
    # and insert the PlatformTitle links
    stats.update(create_platformtitle_links(organization, platform, target_date_tuples))
    log_memory('XX5')


def create_platformtitle_links(organization, platform, target_date_tuples: Set[Tuple]):
    """
    Takes list of dicts that are used to create AccessLogs in `import_counter_records`
    and creates the explicit PlatformTitle objects from the data
    """
    existing = {
        (pt.title_id, pt.date.isoformat())
        for pt in PlatformTitle.objects.filter(organization=organization, platform=platform)
    }
    pts = []
    before_count = PlatformTitle.objects.count()
    for title_id, rec_date in target_date_tuples - existing:
        pts.append(
            PlatformTitle(
                organization=organization, platform=platform, title_id=title_id, date=rec_date
            )
        )
    PlatformTitle.objects.bulk_create(pts, ignore_conflicts=True)
    after_count = PlatformTitle.objects.count()
    return {'new platformtitles': after_count - before_count}


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
