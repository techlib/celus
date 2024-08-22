import logging
import operator
from collections import Counter
from dataclasses import dataclass, field
from functools import reduce
from itertools import combinations
from time import time
from typing import Dict, Generator, List, Optional, Set, Union

from celus_nigiri import CounterRecord
from django.conf import settings
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Count
from django.db.models.functions import Lower
from logs.logic.clickhouse import resync_import_batch_with_clickhouse
from logs.models import AccessLog, ImportBatch

from publications.logic.validation import normalize_isbn, normalize_issn, normalize_title
from publications.models import PlatformTitle, Title

logger = logging.getLogger(__name__)


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

    def stats(self) -> str:
        return f"cache hits: {self._hits}, misses: {self._misses}, size: {len(self)}"


@dataclass
class TitleRec:
    name: str = ""
    pub_type: str = Title.PUB_TYPE_UNKNOWN
    issn: str = ""
    eissn: str = ""
    isbn: str = ""
    doi: str = ""
    # according to the CoP, there must be max one proprietary ID per title,
    # but I do not believe it 100%, so I prepared this model for the possibility
    # of more than one value
    proprietary_ids: Set[str] = field(default_factory=set)
    uri: str = ""

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


class TitleManager:
    id_attrs = ("isbn", "issn", "eissn", "doi")

    def __init__(self):
        self.name_to_records: Dict[str, List[TitleCompareRec]] = {}
        self._prefetch_done = False
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
        if "İ" in name and len("İ".lower()) == 2:
            remove = "İ".lower()[1]
            return ret.replace(remove, "")
        return ret

    def prefetch_titles(self, records: [TitleRec]):
        title_qs = Title.objects.all()
        names = [self.normalize_title(rec.name) if rec.name else rec.name for rec in records]
        title_qs = title_qs.annotate(lname=Lower("name")).filter(lname__in=names)
        self.name_to_records = {}
        for row in title_qs.order_by("name", "pk").values(
            "name", "isbn", "issn", "eissn", "doi", "pk", "pub_type", "proprietary_ids", "uris"
        ):
            name = row.pop("name").lower()
            if name not in self.name_to_records:
                self.name_to_records[name] = []
            id_set = {(attr, row[attr]) for attr in self.id_attrs if row[attr]}
            self.name_to_records[name].append(
                TitleCompareRec(
                    pk=row["pk"],
                    pub_type=row["pub_type"],
                    id_set=id_set,
                    uris=row["uris"],
                    proprietary_ids=row["proprietary_ids"],
                )
            )
        self._prefetch_done = True
        logger.debug("Prefetched %d records", len(self.name_to_records))

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
            issn = normalize_issn(issn)
        eissn = record.eissn
        if eissn:
            eissn = normalize_issn(eissn)
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
            return None

        cache_key = id(record)
        if cache_key in self._title_rec_to_title_cache:
            self.stats["existing"] += 1
            return self._title_rec_to_title_cache[cache_key]

        # make sure that `prefetch_titles` was called at least for this record
        if not self.name_to_records:
            logger.warning("prefetch_titles was not done - doing it now")
            self.prefetch_titles([record])

        winner = self.find_matching_title(record)

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
                self.stats["created"] += 1
            else:
                self.stats["existing"] += 1
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
            self.stats["update"] += 1
        else:
            self.stats["existing"] += 1
        self._title_rec_to_title_cache[cache_key] = winner.pk
        return winner.pk

    def find_matching_title(self, record: TitleRec) -> Optional[TitleCompareRec]:
        if not self._prefetch_done:
            raise ValueError(".prefetch_titles was not done - you must do it before calling this")
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
            if key == "DOI":
                doi = value
            elif key == "Online_ISSN":
                eissn = normalize_issn(value) if value else value
            elif key == "Print_ISSN":
                issn = normalize_issn(value) if value else value
            elif key == "ISBN":
                isbn = normalize_isbn(value) if value else value
            elif key == "Proprietary" and value:
                proprietary_ids.add(value)
            elif key == "URI":
                uri = value
        pub_type = self.deduce_pub_type(eissn, isbn, issn, record)
        # convert None values for the following attrs to empty strings
        isbn = "" if isbn is None else isbn
        issn = "" if issn is None else issn
        eissn = "" if eissn is None else eissn
        doi = "" if doi is None else doi
        uri = "" if uri is None else uri
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
        if "Data_Type" in record.dimension_data:
            data_type = record.dimension_data["Data_Type"]
            pub_type = Title.data_type_to_pub_type(data_type)
        if pub_type == Title.PUB_TYPE_UNKNOWN:
            # we try harder - based on isbn, issn, etc.
            if (issn or eissn) and not isbn:
                pub_type = Title.PUB_TYPE_JOURNAL
            elif isbn and not (issn or eissn):
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
        Title.objects.filter(pub_type=Title.PUB_TYPE_UNKNOWN, issn="", eissn="").exclude(
            isbn=""
        ).update(pub_type=Title.PUB_TYPE_BOOK)
        # if there is no ISBN and at least one ISSN is there -> it is likely a Journal
        Title.objects.filter(pub_type=Title.PUB_TYPE_UNKNOWN, isbn="").exclude(
            issn="", eissn=""
        ).update(pub_type=Title.PUB_TYPE_JOURNAL)


def find_mergeable_titles(batch_size: int = 100) -> Generator[List[Title], None, None]:
    """
    Goes over all titles and identifies those that could be merged.
    :return: List of lists of titles - first title in a list is the one that should be preserved
    """
    # the order_by('lname') replaces the default ordering which would mess up the grouping
    start = time()
    qs = (
        Title.objects.all()
        .annotate(lname=Lower("name"))
        .values("lname")
        .order_by("lname")
        .annotate(title_count=Count("pk"), title_ids=ArrayAgg("pk"))
        .filter(title_count__gt=1)
    )
    logger.info("Found %d potentially mergeable title groups", qs.count())
    logger.info("Query took %f seconds", time() - start)
    start = time()

    # because there may be a large number of candidates (tens of thousands), we do not want
    # to make a db query for each group. Therefor we use a buffer to group several groups
    # together for query. It makes the code more complicated, but much faster
    buffer = []

    def process_buffer():
        buffer_ids = reduce(operator.add, [buf_rec["title_ids"] for buf_rec in buffer])
        buffer_titles = {t.pk: t for t in Title.objects.filter(pk__in=buffer_ids)}
        for record in buffer:
            titles = [buffer_titles[t_id] for t_id in record["title_ids"]]
            for group in titles_to_matching_groups(titles):
                yield sort_mergeable_titles(group)

    for i, rec in enumerate(qs):
        buffer.append(rec)
        if len(buffer) == batch_size:
            for grp in process_buffer():
                yield grp
            buffer = []
        if i % 1000 == 0:
            logger.info("Processed %d groups in %f seconds", i, time() - start)
    if buffer:
        for grp in process_buffer():
            yield grp


def titles_to_matching_groups(titles: List[Title]) -> List[List[Title]]:
    """
    Takes a list of possibly matching titles and returns a list of groups where the titles
    really match. The groups are disjunct
    """
    id_groups = []
    for t1, t2 in combinations(titles, 2):
        t1rec = TitleManager.title_to_titlerec(t1)
        t1cand = TitleManager.title_to_titlecomparerec(t2)
        # we only use one candidate for selection, so if something returns, there is a match
        if TitleManager.select_best_candidate(t1rec, [t1cand]):
            id_groups.append({t1.pk, t2.pk})
    # we have all the tuples as sets in id_groups
    # now we need to merge the groups together if there is an overlap
    # we go over the groups and if there is an overlap, we join them together
    # we do it as long as there are no changes anymore
    new_groups = []
    while id_groups:
        grp = id_groups.pop(0)
        change = True
        while change:
            # we try while there is some change because the last group we merge into grp
            # may cause it to overlap with some it did not match before
            unmatched_groups = []
            change = False
            for other in id_groups:
                if grp & other:
                    grp |= other
                    change = True
                else:
                    unmatched_groups.append(other)
            id_groups = unmatched_groups
        new_groups.append(grp)

    # now recode and return
    id_to_obj = {t.pk: t for t in titles}
    return [[id_to_obj[pk] for pk in grp] for grp in new_groups]


def sort_mergeable_titles(titles: List[Title]) -> List[Title]:
    """
    Sorts the titles so that the first one will be the one to be kept when merging titles.
    It tries to determine which of the titles is used the most and keep it, so that the
    changes in the database will be as small as possible.
    """
    return list(
        Title.objects.filter(pk__in=[t.pk for t in titles])
        .annotate(pt_count=Count("platformtitle"))
        .order_by("-pt_count")
    )


def merge_titles(titles: List[Title], skip_ch_sync=False) -> (Title, Set[int]):
    """
    Joins data from given titles under the first title and changes other data
    (AccessLogs, PlatformTitles) to match the new title and deletes the other titles.

    if `skip_ch_sync` is given, no sync with Clickhouse will be performed. It is up to the
    calling code to do it for all the import batches involved (their ids are returned as part 2).

    :return: (remaining title, set of import batch ids modified by the merge)
    """
    dest, *to_remove = titles
    save = False
    # these import batches should be resynced with CH after the merge because AccessLogs inside
    # have been modified
    ibs_to_resync = set()
    for title in to_remove:
        for attr in ("issn", "eissn", "isbn", "doi"):
            if not getattr(dest, attr) and (update := getattr(title, attr)):
                setattr(dest, attr, update)
                save = True
        if pid_extra := set(title.proprietary_ids) - set(dest.proprietary_ids):
            dest.proprietary_ids += list(pid_extra)
            save = True
        if uris_extra := set(title.uris) - set(dest.uris):
            dest.uris += list(uris_extra)
            save = True
        ibs_to_resync |= replace_title(title, dest)
    logger.debug(
        "Deleting merged titles: %s",
        Title.objects.filter(pk__in=[t.pk for t in to_remove]).delete(),
    )
    if save:
        dest.save()
    # deal with clickhouse
    if settings.CLICKHOUSE_SYNC_ACTIVE and not skip_ch_sync:
        for ib in ImportBatch.objects.filter(pk__in=ibs_to_resync):
            resync_import_batch_with_clickhouse(ib)
    return dest, ibs_to_resync


def replace_title(source: Title, dest: Union[Title, int]) -> Set[int]:
    """
    Replaces the `source` title with the `dest` title in all related models. `dest` may be either
    a Title instance or a pk of one.

    Returns a set of IDs of import batches touched by the change
    """
    dest_pk = dest.pk if isinstance(dest, Title) else dest
    ibs_to_resync = set(
        AccessLog.objects.filter(target=source).values_list("import_batch_id", flat=True).distinct()
    )
    logger.debug(
        "AccessLog title update: %s",
        AccessLog.objects.filter(target=source).update(target_id=dest_pk),
    )
    logger.debug(
        "PlatformTitle title update: %d",
        len(
            PlatformTitle.objects.bulk_create(
                [
                    PlatformTitle(title_id=dest_pk, **rec)
                    for rec in PlatformTitle.objects.filter(title=source).values(
                        "platform_id", "organization_id", "date"
                    )
                ],
                ignore_conflicts=True,  # PlatformTitles may already exist, so ignore conflicts
            )
        ),
    )
    return ibs_to_resync
