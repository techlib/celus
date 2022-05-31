import csv
import gc
import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from io import StringIO
from typing import Optional, Set, Iterable, Dict, Generator, List, Union

from django.conf import settings
from django.db.models.functions import Lower
from django.db.transaction import atomic, on_commit
from django.utils.timezone import now
from postgres_copy import CopyMapping

from core.logic.debug import log_memory
from core.models import UL_ROBOT
from core.task_support import cache_based_lock
from logs.logic.validation import normalize_issn, normalize_isbn, normalize_title
from logs.models import ImportBatch
from nigiri.counter5 import CounterRecord
from organizations.models import Organization
from publications.models import Title, Platform, PlatformTitle
from ..exceptions import DataStructureError, UnknownMetric, UnsupportedMetric
from ..models import ReportType, Metric, DimensionText, AccessLog

logger = logging.getLogger(__name__)

COUNTER_RECORD_BUFFER_SIZE = settings.COUNTER_RECORD_BUFFER_SIZE


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


@dataclass
class TitleRec:
    name: str = ''
    pub_type: str = Title.PUB_TYPE_UNKNOWN
    issn: str = ''
    eissn: str = ''
    isbn: str = ''
    doi: str = ''
    # according to the CoP, there must be max one proprietary ID per title,
    # but I do not believe it 100%, so I prepared this model for the possibility
    # of more than one value
    proprietary_ids: Set[str] = field(default_factory=set)
    uri: str = ''

    def __post_init__(self):
        # ensure proprietary_ids is a set
        self.proprietary_ids = set(self.proprietary_ids)

    def ids_to_set(self):
        return {
            (attr, getattr(self, attr)) for attr in TitleManager.id_attrs if getattr(self, attr)
        }


@dataclass
class TitleCompareRec:
    """
    Such a record is created from the database record and is optimized for further comparing
    with incoming title records
    """

    pk: int
    pub_type: str
    uris: Set[str] = field(default_factory=set)
    id_set: Set[str] = field(default_factory=set)
    proprietary_ids: Set[str] = field(default_factory=set)

    def __post_init__(self):
        # ensure all sets are sets
        self.proprietary_ids = set(self.proprietary_ids)
        self.uris = set(self.uris)
        self.id_set = set(self.id_set)


class Cache(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._hits = 0
        self._misses = 0

    def __contains__(self, item):
        if result := super().__contains__(item):
            self._hits += 1
        else:
            self._misses += 1
        return result


def get_or_create_metric(mapping, value, controlled_metrics: List[str] = None) -> int:
    # already in mapping
    if record := mapping.get(value):
        return record["pk"]

    if settings.AUTOMATICALLY_CREATE_METRICS and not controlled_metrics:
        # When metric auto create of metrics is allowed and metrics doesn't
        # need to be check just create it without further checking
        return get_or_create_with_map(Metric, mapping, 'short_name', value)
    else:
        try:
            # Metric is supposed to exist
            metric = Metric.objects.get(short_name=value)
        except Metric.DoesNotExist:
            raise UnknownMetric(value)

        if controlled_metrics:
            # check for controlled metrics
            if value not in controlled_metrics:
                raise UnsupportedMetric(value)

        # update mapping
        mapping[value] = {"short_name": metric.short_name, "pk": metric.pk}

        return metric.pk


class TitleManager:
    id_attrs = ('isbn', 'issn', 'eissn', 'doi')

    def __init__(self):
        self.name_to_records: Dict[str, List[TitleCompareRec]] = {}
        self.stats = Counter()
        # below we cache the incoming name and ids and map them to the TitleRecord to speed up
        # processing. We similarly cache the TitleRecord -> Title conversion
        #
        # The basic idea of the caching is that many rows come from the same JSON record
        # and thus have a copy of the same title information. Thus it does not make sense
        # to resolve the title each time if we have already done it for the previous record
        # This type of caching is especially effective when there are many records created for
        # one title, such as when a TR report with YOP and other dimensions is imported
        self._counter_rec_to_title_rec_cache = Cache()
        self._title_rec_to_title_cache = Cache()

    @classmethod
    def normalize_title(cls, name: str) -> str:
        """
        Normalize title for comparison with the database.
        Does some strange things to Turkish I to make it compatible with Postgres lower
        """
        if not name:
            return name
        ret = name.lower()
        # get around a strange unicode case where the turkish İ forms two chars
        if 'İ' in name and len('İ'.lower()) == 2:
            remove = 'İ'.lower()[1]
            return ret.replace(remove, '')
        return ret

    def prefetch_titles(self, records: [TitleRec]):
        title_qs = Title.objects.all()
        names = [self.normalize_title(rec.name) if rec.name else rec.name for rec in records]
        title_qs = title_qs.annotate(lname=Lower('name')).filter(lname__in=names)
        self.name_to_records = {}
        for row in title_qs.order_by('name').values(
            'name', 'isbn', 'issn', 'eissn', 'doi', 'pk', 'pub_type', 'proprietary_ids', 'uris'
        ):
            name = row.pop('name').lower()
            if name not in self.name_to_records:
                self.name_to_records[name] = []
            id_set = {(attr, row[attr]) for attr in self.id_attrs if row[attr]}
            self.name_to_records[name].append(
                TitleCompareRec(
                    pk=row['pk'],
                    pub_type=row['pub_type'],
                    id_set=id_set,
                    uris=row['uris'],
                    proprietary_ids=row['proprietary_ids'],
                )
            )
        logger.debug('Prefetched %d records', len(self.name_to_records))

    @classmethod
    def title_to_titlecomparerec(cls, title: Title) -> TitleCompareRec:
        id_set = {(attr, getattr(title, attr)) for attr in cls.id_attrs if getattr(title, attr)}
        return TitleCompareRec(
            pk=title.pk,
            pub_type=title.pub_type,
            id_set=id_set,
            uris=title.uris,
            proprietary_ids=title.proprietary_ids,
        )

    @classmethod
    def title_to_titlerec(cls, title: Title) -> TitleRec:
        return TitleRec(
            name=title.name,
            pub_type=title.pub_type,
            issn=title.issn,
            eissn=title.eissn,
            isbn=title.isbn,
            doi=title.doi,
            proprietary_ids=title.proprietary_ids,
        )

    @classmethod
    def normalize_title_rec(cls, record: TitleRec) -> TitleRec:
        """
        Normalize specific fields in the record and return a new TitleRec with normalized data.
        Should be run before one attempts to ingest the data into the database.
        """
        # normalize issn, eissn and isbn - they are sometimes malformed by whitespace in the data
        issn = record.issn
        if issn:
            issn = normalize_issn(issn, raise_error=False)
        eissn = record.eissn
        if eissn:
            eissn = normalize_issn(eissn, raise_error=False)
        isbn = normalize_isbn(record.isbn) if record.isbn else record.isbn
        return TitleRec(
            name=normalize_title(record.name) if record.name else record.name,
            isbn=isbn,
            issn=issn,
            eissn=eissn,
            doi=record.doi,
            pub_type=record.pub_type,
            proprietary_ids=record.proprietary_ids,
            uri=record.uri,
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

        cache_key = id(record)
        if cache_key in self._title_rec_to_title_cache:
            self.stats['existing'] += 1
            return self._title_rec_to_title_cache[cache_key]

        # make sure that `prefetch_titles` was called at least for this record
        if not self.name_to_records:
            self.prefetch_titles([record])

        winner = self._find_matching_title(record)

        if not winner:
            # let's create the title
            title: Title
            title, created = Title.objects.get_or_create(
                defaults={"pub_type": record.pub_type},
                name=record.name,
                isbn=record.isbn,
                issn=record.issn,
                eissn=record.eissn,
                doi=record.doi,
                uris=[record.uri] if record.uri else [],
                proprietary_ids=list(record.proprietary_ids),
            )
            # we use normalized name in the `name_to_records` cache
            name = title.name.lower() if title.name else title.name
            if name not in self.name_to_records:
                self.name_to_records[name] = []
            self.name_to_records[name].append(
                TitleCompareRec(
                    pk=title.pk,
                    pub_type=title.pub_type,
                    uris=title.uris,
                    proprietary_ids=title.proprietary_ids,
                    id_set=record.ids_to_set(),
                )
            )
            if created:
                self.stats['created'] += 1
            else:
                self.stats['existing'] += 1
            self._title_rec_to_title_cache[cache_key] = title.pk
            return title.pk

        # we have a winner - we must merge record with the winner
        rec_id_set = record.ids_to_set()
        extra_ids = rec_id_set - winner.id_set
        extra_prop_ids = record.proprietary_ids - winner.proprietary_ids
        if (
            extra_ids
            or extra_prop_ids
            or (
                winner.pub_type == Title.PUB_TYPE_UNKNOWN
                and record.pub_type != Title.PUB_TYPE_UNKNOWN
            )
            or (record.uri and record.uri not in winner.uris)
        ):
            title = Title.objects.get(pk=winner.pk)
            title.proprietary_ids = title.proprietary_ids + list(extra_prop_ids)
            winner.proprietary_ids |= extra_prop_ids
            if extra_ids:
                for id_name, id_value in extra_ids:
                    setattr(title, id_name, id_value)
                winner.id_set |= extra_ids
            if record.uri and record.uri not in winner.uris:
                title.uris = title.uris + [record.uri]
                winner.uris.add(record.uri)
            if title.pub_type == title.PUB_TYPE_UNKNOWN:
                title.pub_type = record.pub_type
                winner.pub_type = record.pub_type
            title.save()
            self.stats['update'] += 1
        else:
            self.stats['existing'] += 1
        self._title_rec_to_title_cache[cache_key] = winner.pk
        return winner.pk

    def _find_matching_title(self, record: TitleRec) -> Optional[TitleCompareRec]:
        candidates = self.name_to_records.get(record.name.lower(), [])
        if candidates:
            return self.select_best_candidate(record, candidates)
        return None

    @classmethod
    def select_best_candidate(
        cls, record: TitleRec, candidates: List[TitleCompareRec]
    ) -> Optional[TitleCompareRec]:
        """
        Go over the candidates and select the one with which record should be merged. Return None
        if no candidate is suitable
        """
        rec_id_set = record.ids_to_set()
        winner = None
        winner_miss_score = (1000, 0)
        # first go over all the candidates and try to find one with the least difference with
        # our record - this should make it more probable to find a match that will not need
        # an upgrade later. It also protects against clashes created by upgrading a worse
        # candidate to the same state as a better one
        for candidate in candidates:
            if rec_id_set and candidate.id_set:
                # we need at least one value in both id_sets to be able to meaningfully match them
                rec_extra = rec_id_set - candidate.id_set
                cand_extra = candidate.id_set - rec_id_set
                clashing_id_names = {x for x, y in rec_extra if y} & {x for x, y in cand_extra if y}
                common_ids = rec_id_set & candidate.id_set
                # the first part of score is the number of new values - the lower, the better
                # because we do not want to update the candidate if possible
                # the second part of the score is the total number of set IDs in the candidate
                # here the higher, the better as we want to merge with the most populated title
                miss_score = (len(rec_extra), -len(cand_extra))
                if common_ids and not clashing_id_names and miss_score < winner_miss_score:
                    # we have a match - if the records do not match, it is on the same fields
                    winner = candidate
                    winner_miss_score = miss_score
        if not winner:
            # could not find winner using ids
            if record.proprietary_ids:
                # let 's try proprietary ids
                # we only allow this if either the in-memory or in-db record does not have any
                # other ids - if they had, we would have matched it above, if we did not, they must
                # clash
                for candidate in candidates:
                    if (record.proprietary_ids & candidate.proprietary_ids) and (
                        not rec_id_set or not candidate.id_set
                    ):
                        return candidate
                # another step - if the other candidate
            if not rec_id_set:
                # no match using proprietary ids and other ids failed above
                # here we try the last resort and match together records with only name and nothing
                # else - if proprietary ids on one side are empty, we match it, if they are
                # disjunct, we do not match
                for candidate in candidates:
                    if not candidate.id_set and (
                        not candidate.proprietary_ids or not record.proprietary_ids
                    ):
                        return candidate
        return winner

    def counter_record_to_title_rec(self, record: CounterRecord) -> TitleRec:
        cache_key = (record.title, frozenset(record.title_ids.items()))
        if cache_key in self._counter_rec_to_title_rec_cache:
            return self._counter_rec_to_title_rec_cache[cache_key]
        title = normalize_title(record.title) if record.title else record.title
        isbn = None
        issn = None
        eissn = None
        doi = None
        uri = None
        proprietary_ids = set()
        for key, value in record.title_ids.items():
            value = value.strip() if value else value
            if key == 'DOI':
                doi = value
            elif key == 'Online_ISSN':
                eissn = normalize_issn(value, raise_error=False) if value else value
            elif key == 'Print_ISSN':
                issn = normalize_issn(value, raise_error=False) if value else value
            elif key == 'ISBN':
                isbn = normalize_isbn(value) if value else value
            elif key == 'Proprietary' and value:
                proprietary_ids.add(value)
            elif key == 'URI':
                uri = value
        pub_type = self.deduce_pub_type(eissn, isbn, issn, record)
        # convert None values for the following attrs to empty strings
        isbn = '' if isbn is None else isbn
        issn = '' if issn is None else issn
        eissn = '' if eissn is None else eissn
        doi = '' if doi is None else doi
        uri = '' if uri is None else uri
        ret = TitleRec(
            name=title,
            pub_type=pub_type,
            isbn=isbn,
            issn=issn,
            eissn=eissn,
            doi=doi,
            proprietary_ids=proprietary_ids,
            uri=uri,
        )
        self._counter_rec_to_title_rec_cache[cache_key] = ret
        return ret

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
    records: Generator[CounterRecord, None, None],
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
    ib_id_to_key_structure = ['metric_id', 'target_id'] + [
        f'dim{i+1}' for i, dim in enumerate(report_type.dimensions_sorted)
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
    for ib in import_batches:
        csv_data = StringIO()
        writer = csv.writer(csv_data)
        target_ids = set()
        for i, (key, value) in enumerate(ib_id_to_key_to_value[ib.pk].items()):
            rec = dict(zip(ib_id_to_key_structure, key))
            rec['value'] = value
            if rec['target_id']:
                target_ids.add(rec['target_id'])
            if i == 0:
                # write the CSV header
                writer.writerow(list(sorted(rec.keys())))
            writer.writerow([v for k, v in sorted(rec.items())])
            stats['new logs'] += 1
        ingest_import_batch_data(ib, csv_data)
        # and insert the PlatformTitle links
        stats += create_platformtitle_links_from_import_batch(ib, target_ids)

    log_memory('XX3')

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
    for i, cache in enumerate([tm._counter_rec_to_title_rec_cache, tm._title_rec_to_title_cache]):
        logger.info(
            f'Title manager: step #{i+1} cache hits: {cache._hits}, misses: {cache._misses}, '
            f'size: {len(cache)}'
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
    controlled_metrics = list(report_type.controlled_metrics.values_list('short_name', flat=True))

    # prepare all remaps
    metrics = {
        metric["short_name"]: metric
        for metric in Metric.objects.values("pk", "short_name")
        if not controlled_metrics or metric["short_name"] in controlled_metrics
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
            metric_id = get_or_create_metric(metrics, record.metric, controlled_metrics)
        start = record.start if not isinstance(record.start, date) else record.start.isoformat()
        import_batch = month_to_import_batch[start]
        id_attrs = {
            'metric_id': metric_id,
            'target_id': title_id,
        }
        for i, dim in enumerate(dimensions):
            dim_value = record.dimension_data.get(dim.short_name)
            if dim_value is not None:
                remap = text_to_int_remaps.get(dim.pk)
                if not remap:
                    remap = {}
                    text_to_int_remaps[dim.pk] = remap
                dim_value = get_or_create_with_map(
                    DimensionText, remap, 'text', dim_value, other_attrs={'dimension_id': dim.pk},
                )
            id_attrs[f'dim{i+1}'] = dim_value
        # here we detect possible duplicated keys and merge matching records
        key = tuple(id_attrs[k] for k in ib_id_to_key_structure)
        # we prepare the data to insert already split by individual import batch
        to_insert = ib_id_to_key_to_value[import_batch.pk]
        if key in to_insert:
            to_insert[key] += record.value
        else:
            to_insert[key] = record.value
    logger.info('Title statistics: %s', tm.stats)


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
    existing = set(pt_qs.values_list('title_id', flat=True))
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
    log_memory('XX6')
    file_content.seek(0)
    c = IBCopyMapping(
        AccessLog,
        file_content,
        import_batch.pk,
        static_mapping={
            'created': now(),
            'owner_level': UL_ROBOT,
            'import_batch_id': import_batch.pk,
            'date': import_batch.date,
            'platform_id': import_batch.platform_id,
            'report_type_id': import_batch.report_type_id,
            'organization_id': import_batch.organization_id,
        },
    )
    c.save()
    log_memory('XX7')
