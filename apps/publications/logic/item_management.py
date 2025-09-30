import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, Generator, List, Optional, Set, Tuple, Union

from celus_nigiri import CounterRecord
from celus_nigiri.record import Author
from core.logic.dates import parse_date
from django.contrib.postgres.expressions import ArraySubquery
from django.db.models import OuterRef
from django.db.models.functions import Lower

from publications import models

from ..models import Item
from .title_management import Cache, TitleManager
from .validation import (
    normalize_author_id,
    normalize_author_name,
    normalize_isbn,
    normalize_issn,
    normalize_title,
)

logger = logging.getLogger(__name__)


@dataclass(eq=False)
class ItemRec:
    name: str = ""
    doi: str = ""
    issn: str = ""
    eissn: str = ""
    isbn: str = ""
    proprietary_ids: Set[str] = field(default_factory=set)
    uris: Set[str] = field(default_factory=set)
    publication_date: str = ""
    authors: List[Author] = field(default_factory=list)
    pub_type: str = Item.PUB_TYPE_UNKNOWN

    def __post_init__(self):
        # ensure set is used
        self.name = normalize_title(self.name)
        self.proprietary_ids = set(self.proprietary_ids)
        self.uris = set(self.uris)
        self.isbn = self.isbn and normalize_isbn(self.isbn)
        self.issn = self.issn and normalize_issn(self.issn)
        self.eissn = self.eissn and normalize_issn(self.eissn)
        if isinstance(self.publication_date, date):
            self.publication_date = self.publication_date.isoformat()
        else:
            # the date as string may contain strange things, like "-", etc.
            # we want to normalize it in order not to crash the import into database
            try:
                self.publication_date = parse_date(self.publication_date).isoformat()
            except ValueError:
                self.publication_date = ""
        for author in self.authors:
            author.ISNI = normalize_author_id(author.ISNI or "")
            author.ORCID = normalize_author_id(author.ORCID or "")
            author.name = normalize_author_name(author.name or "")

    @classmethod
    def from_counter_record(
        cls, record: CounterRecord, pub_type: Optional[str] = Item.PUB_TYPE_UNKNOWN
    ) -> Optional["ItemRec"]:
        if not record.item:
            return None

        name = record.item
        doi = record.item_ids.DOI or ""
        isbn = record.item_ids.ISBN or ""
        issn = record.item_ids.Print_ISSN or ""
        eissn = record.item_ids.Online_ISSN or ""
        publication_date = record.item_publication_date or ""
        authors = record.item_authors or []
        if proprietary_id := record.item_ids.Proprietary:
            proprietary_ids = {proprietary_id.strip()}
        else:
            proprietary_ids = {}
        if uri := record.item_ids.URI:
            uris = {uri.strip()}
        else:
            uris = {}

        return ItemRec(
            name=name,
            doi=doi,
            isbn=isbn,
            issn=issn,
            eissn=eissn,
            proprietary_ids=proprietary_ids,
            uris=uris,
            publication_date=publication_date,
            authors=authors,
            pub_type=pub_type,
        )

    def update(self, other: "ItemRec"):
        # Update only when records are same
        if self == other:
            # merge uris and proprietary_ids
            self.proprietary_ids |= other.proprietary_ids
            self.uris |= other.uris
            if self.pub_type == Item.PUB_TYPE_UNKNOWN:
                self.pub_type = other.pub_type
        return

    def __eq__(self, other: "ItemRec"):
        # pub_type is derived from usage data, so we don't compare it
        if (
            self.name == other.name  # normalized names should match
            and self.doi == other.doi
            and self.isbn == other.isbn
            and self.issn == other.issn
            and self.eissn == other.eissn
            and self.publication_date == other.publication_date
            and self.authors == other.authors
        ):
            return True

        return False

    @property
    def no_ids(self) -> bool:
        return not (
            self.doi
            or self.isbn
            or self.issn
            or self.eissn
            or self.uris
            or self.proprietary_ids
            or self.publication_date
            or self.authors
        )

    def ids_to_set(self):
        return {(attr, getattr(self, attr)) for attr in ItemManager.id_attrs if getattr(self, attr)}

    def matches(self, ic: "ItemCompareRec", am: "AuthorManager") -> bool:
        """Makes sure that there are no conflicts with compared record"""
        authors_ids = [am.get(e) for e in self.authors]

        # Not in conflict when one is empty
        for i_id in ["doi", "isbn", "issn", "eissn"]:
            self_value = getattr(self, i_id) or ""
            ic_value = getattr(ic, i_id) or ""
            if ic_value and self_value and self_value != ic_value:
                return False

        # Needs to be exactly same
        for i_id in ["publication_date"]:
            self_value = getattr(self, i_id) or ""
            ic_value = getattr(ic, i_id) or ""
            if self_value != ic_value:
                return False

        # Authors are different
        if ic.authors != authors_ids:
            return False

        # proprietary ids with the same prefix are not in conflict
        if self.proprietary_ids and ic.proprietary_ids:
            my_pids = defaultdict(list)
            # create dict of prefixes and values stored in self.proprietary_ids
            for pid in self.proprietary_ids:
                split = pid.split(":", 1)
                if len(split) == 2:
                    prefix, value = split
                    my_pids[prefix].append(value)

            # compare with ic.proprietary_ids
            for pid in ic.proprietary_ids:
                split = pid.split(":", 1)
                if len(split) == 2:
                    prefix, value = split
                    if prefix in my_pids and value not in my_pids[prefix]:
                        return False

        return True

    def compare_score(self, ic: "ItemCompareRec", am: "AuthorManager") -> Tuple[int, ...]:
        # Get score of extra fields in ic
        # in case of same score extras will be used to pick the best match
        authors_ids = [am.get(e) for e in self.authors]
        ic_extras: Tuple[int, ...] = (
            int(bool(ic.doi) and not self.doi),
            int(bool(ic.isbn) and not self.isbn),
            int(bool(ic.uris) and not self.isbn),
            int(bool(ic.issn) and not self.issn) + int(bool(ic.issn) and not self.issn),
            len(authors_ids),  # more authors the better
            len(ic.uris - self.uris),
            len(ic.proprietary_ids - self.proprietary_ids),
        )
        return (
            int(self.doi == ic.doi),
            int(self.isbn == ic.isbn),
            int(self.issn == ic.issn) + int(self.eissn == ic.eissn),
            len(self.uris & ic.uris),
            len(self.proprietary_ids & ic.proprietary_ids),
            int(self.publication_date == ic.publication_date),
            int(bool(authors_ids) and authors_ids == ic.authors),
            ic_extras,
        )


@dataclass
class ItemCompareRec:
    """
    Such a record is created from the database record and is optimized for further comparing
    with incoming item records
    """

    pk: int
    uris: Set[str] = field(default_factory=set)
    id_set: Set[Tuple[str, str]] = field(default_factory=set)
    proprietary_ids: Set[str] = field(default_factory=set)
    authors: List[int] = field(default_factory=list)
    pub_type: str = Item.PUB_TYPE_UNKNOWN

    def __post_init__(self):
        # ensure all sets are sets
        self.proprietary_ids = set(self.proprietary_ids)
        self.uris = set(self.uris)
        self.id_set = {
            # convert date to string
            (k, v.isoformat()) if isinstance(v, date) else (k, v)
            for k, v in self.id_set
        }
        self.authors = list(self.authors)

    def _get_id(self, id_name: str) -> Optional[str]:
        for k, v in self.id_set:
            if k == id_name:
                return v or None

        return None

    @property
    def doi(self) -> Optional[str]:
        return self._get_id("doi")

    @property
    def isbn(self) -> Optional[str]:
        return self._get_id("isbn")

    @property
    def issn(self) -> Optional[str]:
        return self._get_id("issn")

    @property
    def eissn(self) -> Optional[str]:
        return self._get_id("eissn")

    @property
    def publication_date(self) -> Optional[str]:
        return self._get_id("publication_date")

    @property
    def no_ids(self) -> bool:
        return (
            not self.id_set
            and not self.proprietary_ids
            and not self.uris
            and not self.authors
            and not self.publication_date
        )


class AuthorManager:
    def __init__(self):
        self.author_to_id: Cache
        self.stats = Counter()

    def prefetch_authors(self, authors: List[Author]):
        self.author_to_id = Cache()
        prefetched_authors = {
            self.prefetched_key(name, isni, orcid): pk
            for name, isni, orcid, pk in models.Author.objects.annotate(lname=Lower("name"))
            .filter(lname__in=[TitleManager.normalize_title(e.name) for e in authors])
            .values_list("name", "isni", "orcid", "pk")
        }
        for author in authors:
            key = self.key(author)
            if pk := prefetched_authors.get(key):
                self.author_to_id[key] = pk
            else:
                author_obj = models.Author.from_nigiri_author(author)
                author_obj.save()
                self.author_to_id[key] = author_obj.pk

    @classmethod
    def prefetched_key(cls, name: str, isni: str, orcid: str) -> str:
        return f"{TitleManager.normalize_title(name)}|{isni}|{orcid}"

    @classmethod
    def key(cls, author: Author) -> str:
        return (
            f"{TitleManager.normalize_title(author.name)}|"
            f"{normalize_author_id(author.ISNI).lower()}|"
            f"{normalize_author_id(author.ORCID).lower()}"
        )

    def get(self, author: Author) -> int:
        return self.author_to_id[self.key(author)]


class ItemManager:
    id_attrs = ("isbn", "issn", "eissn", "doi", "publication_date")

    def __init__(self):
        self.authors = AuthorManager()
        self.stats = Counter()
        self._prefetch_done = False
        self._counter_rec_to_item_rec_cache = Cache()
        self._item_rec_to_item_cache = Cache()
        self.name_to_records: Dict[str, List[ItemCompareRec]] = defaultdict(list)

    def prefetch_items(self, records: Union[List[ItemRec], Generator[ItemRec, None, None]]):
        authors = []
        names = set()
        for record in records:
            names.add(TitleManager.normalize_title(record.name))
            for author in record.authors:
                if author not in authors:
                    authors.append(author)

        # Make sure that all authors exists
        self.authors.prefetch_authors(authors)

        self.name_to_records = defaultdict(list)
        authors = (
            models.AuthorToItem.objects.filter(item=OuterRef("pk"))
            .order_by("position")
            .values_list("author_id", flat=True)
        )
        for row in (
            models.Item.objects.annotate(lname=Lower("name"), authors_ids=ArraySubquery(authors))
            .filter(lname__in=names)
            .order_by("name", "pk")
            .values(
                "name",
                "isbn",
                "issn",
                "eissn",
                "doi",
                "pk",
                "publication_date",
                "proprietary_ids",
                "authors_ids",
                "uris",
                "pub_type",
            )
        ):
            authors = row.pop("authors_ids")
            name = row.pop("name").lower()
            id_set = {(attr, row[attr]) for attr in self.id_attrs if row[attr]}
            self.name_to_records[name].append(
                ItemCompareRec(
                    pk=row["pk"],
                    id_set=id_set,
                    uris=row["uris"],
                    proprietary_ids=row["proprietary_ids"],
                    authors=authors,
                    pub_type=row["pub_type"],
                )
            )
        self._prefetch_done = True
        logger.debug("Prefetched %d items", len(self.name_to_records))

    @classmethod
    def normalize_item(cls, name: str) -> str:
        return TitleManager.normalize_title(name)

    @classmethod
    def deduce_pub_type(cls, eissn, isbn, issn, record):
        pub_type = Item.PUB_TYPE_UNKNOWN
        if "Data_Type" in record.dimension_data:
            data_type = record.dimension_data["Data_Type"]
            pub_type = Item.data_type_to_pub_type(data_type)
        if pub_type == Item.PUB_TYPE_UNKNOWN:
            # we try harder - based on isbn, issn, etc.
            if (issn or eissn) and not isbn:
                pub_type = Item.PUB_TYPE_ARTICLE
            elif isbn and not (issn or eissn):
                pub_type = Item.PUB_TYPE_BOOK_SEGMENT
        return pub_type

    def counter_record_to_item_rec(self, record: CounterRecord) -> Optional[ItemRec]:
        # short-circuit if there is no item
        if not record.item:
            return None
        cache_key = (record.item, frozenset(record.item_ids.items()))
        if item_rec := self._counter_rec_to_item_rec_cache.get(cache_key):
            return item_rec

        pub_type = self.deduce_pub_type(
            record.item_ids.Online_ISSN, record.item_ids.ISBN, record.item_ids.Print_ISSN, record
        )
        item = ItemRec.from_counter_record(record, pub_type=pub_type)
        self._counter_rec_to_item_rec_cache[cache_key] = item
        return item

    def find_matching_item(self, record: ItemRec) -> Optional[ItemCompareRec]:
        if not self._prefetch_done:
            raise ValueError(".prefetch_items was not done - you must do it before calling this")
        candidates = self.name_to_records.get(record.name.lower(), [])
        if candidates:
            return self.select_best_candidate(record, candidates, self.authors)
        return None

    @classmethod
    def select_best_candidate(
        cls, record: ItemRec, candidates: List[ItemCompareRec], authors: AuthorManager
    ) -> Optional[ItemCompareRec]:
        # Pick only candidates without conflict
        candidates = [e for e in candidates if record.matches(e, authors)]

        if not candidates:
            return None

        candidates_with_scores = [(record.compare_score(c, authors), c) for c in candidates]

        max_score, best_candidate = max(candidates_with_scores, key=lambda c: c[0])
        if max_score >= (0, 0, 0, 0, 0, 1, 1, tuple()):
            # at least one same attribute
            return best_candidate
        else:
            if best_candidate.no_ids and record.no_ids:
                # No ids present
                return best_candidate
            else:
                # Don't merge when there is not a least one common id
                return None

    def get_or_create(self, record: ItemRec) -> Optional[int]:
        if not record.name:
            return None

        cache_key = id(record)
        if cache_key in self._item_rec_to_item_cache:
            self.stats["existing"] += 1
            return self._item_rec_to_item_cache[cache_key]

        # make sure that `prefetch_items` was called at least for this record
        if not self._prefetch_done:
            self.prefetch_items([record])

        winner = self.find_matching_item(record)

        if not winner:
            # let's create the item
            item: models.Item = models.Item.objects.create(
                name=record.name,
                isbn=record.isbn,
                issn=record.issn,
                eissn=record.eissn,
                doi=record.doi or "",
                pub_type=record.pub_type,
                uris=list(record.uris),
                proprietary_ids=list(record.proprietary_ids),
                publication_date=record.publication_date or None,
            )
            # we use normalized name in the `name_to_records` cache
            name = item.name.lower()
            if name not in self.name_to_records:
                self.name_to_records[name] = []
            self.name_to_records[name].append(
                ItemCompareRec(
                    pk=item.pk,
                    uris=item.uris,
                    proprietary_ids=item.proprietary_ids,
                    id_set=record.ids_to_set(),
                    authors=[self.authors.get(e) for e in record.authors],
                    pub_type=record.pub_type,
                )
            )
            self.stats["created"] += 1
            self._item_rec_to_item_cache[cache_key] = item.pk
            processed_authors = []
            for idx, author in enumerate(record.authors):
                if author not in processed_authors:
                    models.AuthorToItem.objects.create(
                        position=idx, item=item, author_id=self.authors.get(author)
                    )
                    processed_authors.append(author)

            return item.pk

        # we have a winner - we must merge record with the winner
        rec_id_set = record.ids_to_set()
        extra_ids = rec_id_set - winner.id_set
        extra_prop_ids = record.proprietary_ids - winner.proprietary_ids
        if (
            extra_ids
            or extra_prop_ids
            or (record.uris and not record.uris & winner.uris)
            or (winner.pub_type != record.pub_type and winner.pub_type == Item.PUB_TYPE_UNKNOWN)
        ):
            item = models.Item.objects.get(pk=winner.pk)
            item.proprietary_ids = item.proprietary_ids + list(extra_prop_ids)
            winner.proprietary_ids |= extra_prop_ids
            if extra_ids:
                for id_name, id_value in extra_ids:
                    setattr(item, id_name, id_value)
                winner.id_set |= extra_ids
            if record.uris and not set(record.uris) & winner.uris:
                merged_uris = set(item.uris) | record.uris
                item.uris = list(merged_uris)
                winner.uris = merged_uris
            if winner.pub_type == Item.PUB_TYPE_UNKNOWN:
                item.pub_type = record.pub_type
                winner.pub_type = record.pub_type
            item.save()
            self.stats["update"] += 1
        else:
            self.stats["existing"] += 1
        self._item_rec_to_item_cache[cache_key] = winner.pk
        return winner.pk
