import abc
import codecs
import csv
import itertools
import operator
from collections import defaultdict
from dataclasses import dataclass, field
from functools import reduce
from typing import Any, BinaryIO, Callable, Dict, Generator, Iterable, List, Optional, Set

from django.db.models import Q
from nibbler.logic.dict_reader import get_dict_reader_from_csv
from publications.logic.title_management import TitleRec
from publications.logic.validation import normalize_isbn, normalize_issn
from publications.models import Title


@dataclass
class TitleTaggingRecord:
    title_rec: TitleRec = None
    tag_names: [str] = field(default_factory=list)
    title_ids: Set[int] = field(default_factory=set)
    source_data: Dict = None  # the original data from input
    extra_data: Dict = None  # extra data to be added to the dump file


class TitleListReader(abc.ABC):
    def process_source(
        self,
        source: Any,
        merge_issns: bool = True,
        batch_size: int = 100,
        dump_file: Optional[BinaryIO] = None,
    ) -> Generator[TitleTaggingRecord, None, None]:
        dump_writer = None

        for rec in self.add_title_ids_to_records(
            self.parse_data(source), merge_issns=merge_issns, batch_size=batch_size
        ):
            if dump_file:
                if not dump_writer:
                    dump_stream = codecs.getwriter("utf-8")(dump_file)
                    dump_writer = csv.writer(dump_stream)
                    dump_writer.writerow(list(rec.source_data.keys()) + self.extra_column_names())
                annotations = self.annotate_dump_record(rec)
                dump_writer.writerow(list(rec.source_data.values()) + annotations)
            yield rec

    def extra_column_names(self) -> [str]:
        return []

    def annotate_dump_record(self, record: TitleTaggingRecord) -> List[str]:
        return []

    def add_extra_data_to_rec_batch(self, records: [TitleTaggingRecord]):  # noqa: B027
        """
        Override this method to add extra data to the records. This method is called
        after the titles have been matched to the records, so `title_ids` is guaranteed
        to be populated.
        The size of the batch matches the `batch_size` param of `process_source`.
        """

    @abc.abstractmethod
    def parse_data(self, source: Any) -> Generator[TitleTaggingRecord, None, None]:
        """
        Reads from the source and yields individual TitleTaggingRecords.
        """

    def title_qs(self):
        return Title.objects.all()

    def add_title_ids_to_records(
        self, records: Iterable[TitleTaggingRecord], merge_issns=True, batch_size=100
    ) -> Generator[TitleTaggingRecord, None, None]:
        """
        Takes a stream of TitleTaggingRecords (usually from `parse_data`) and fills in the
        `title_ids` field if it is empty.

        :param records - usually `.parse_data()` generator
        :param merge_issns - if True, both issn and eissn will be compared to both issn and eissn
                             thus potentially returning more results
        :param batch_size - internally the resolving of titles is done in batches to reduce
                            the number of database queries. This param controls the size of the
                            batch
        """

        irecords = iter(records)
        while batch := list(itertools.islice(irecords, batch_size)):
            yield from self._add_title_ids_to_records_one_chunk(batch, merge_issns=merge_issns)

    def _add_title_ids_to_records_one_chunk(
        self, records: [TitleTaggingRecord], merge_issns=True
    ) -> Generator[TitleTaggingRecord, None, None]:
        if merge_issns:
            issn_set = eissn_set = set()
        else:
            issn_set, eissn_set = set(), set()
        filters = {
            "isbn": set(),
            "issn": issn_set,
            "eissn": eissn_set,
            "doi": set(),
            "proprietary_ids": set(),
        }
        # we collect all the IDs from individual title records
        for record in records:
            if not record.title_ids:
                for attr, array in filters.items():
                    if value := getattr(record.title_rec, attr, ""):
                        if attr == "proprietary_ids":
                            array.update(value)  # proprietary_ids is a set
                        else:
                            array.add(value)

        # prepare a mapping between some title identifier (like issn, isbn) and title pks
        if merge_issns:
            issn_dict = eissn_dict = defaultdict(set)
        else:
            issn_dict, eissn_dict = defaultdict(set), defaultdict(set)

        id_to_titles = {
            "isbn": defaultdict(set),
            "issn": issn_dict,
            "eissn": eissn_dict,
            "doi": defaultdict(set),
            "proprietary_ids": defaultdict(set),
        }
        # then we query titles for the whole set of collected ids
        # at first attrs which are not proprietary_ids
        q_filters = [
            Q(**{f"{attr}__in": array})
            for attr, array in filters.items()
            if attr != "proprietary_ids" and array
        ]
        # then proprietary_ids which are a bit different as they are stored as lists
        if filters["proprietary_ids"]:
            q_filters.append(Q(proprietary_ids__has_any_keys=list(filters["proprietary_ids"])))

        if q_filters:
            for title_rec in (
                self.title_qs()
                .filter(reduce(operator.or_, q_filters))
                .values("pk", *id_to_titles.keys())
            ):
                for attr, storage in id_to_titles.items():
                    if value := title_rec.get(attr):
                        if attr == "proprietary_ids":
                            for v in value:
                                storage[v].add(title_rec["pk"])
                        else:
                            storage[value].add(title_rec["pk"])
        # now process the records
        for record in records:
            title_ids = set()
            for attr, storage in id_to_titles.items():
                if value := getattr(record.title_rec, attr):
                    if attr == "proprietary_ids":
                        for v in value:
                            title_ids |= storage.get(v, set())
                    else:
                        title_ids |= storage.get(value, set())
            record.title_ids = title_ids
        self.add_extra_data_to_rec_batch(records)
        for record in records:
            yield record


class CsvReaderMixin:
    attrs = {
        "isbn": {"normalize": normalize_isbn},
        "issn": {"normalize": lambda x: normalize_issn(x)},
        "eissn": {"normalize": lambda x: normalize_issn(x)},
        "doi": {"normalize": None},
        "proprietary_ids": {"normalize": lambda x: {x}},
    }

    col_to_attr = {
        "isbn": "isbn",
        "issn": "issn",
        "eissn": "eissn",
        "doi": "doi",
        "proprietary id": "proprietary_ids",
    }

    def _remove_django_file_wrappers(self, source):
        file = getattr(source, "file", source)
        file = getattr(file, "file", file)
        return file

    def __init__(self, tag_name_column: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.tag_name_column = tag_name_column
        # the following will hold the column name that contains the tag name as seen in the data
        self._used_tag_name_column = None
        # the following will hold the column names found in the data. The key is always one of
        # `self.attrs`, the value is the actual column name
        self.column_names = {}

    def fieldnames(self, source) -> Iterable[str]:
        file = self._remove_django_file_wrappers(source)
        reader = get_dict_reader_from_csv(file)
        return reader.fieldnames

    def record_count(self, source) -> int:
        file = self._remove_django_file_wrappers(source)
        reader = get_dict_reader_from_csv(file)
        return sum(1 for _ in reader)

    def parse_data(self, source: Any) -> Generator[TitleTaggingRecord, None, None]:
        file = self._remove_django_file_wrappers(source)
        reader = get_dict_reader_from_csv(file)
        # find which columns are present and find the actual form of the name (case and whitespace)
        for column_name in reader.fieldnames:
            if attr_name := self.col_to_attr.get(column_name.strip().lower()):
                self.column_names[attr_name] = column_name
            elif self.tag_name_column and column_name.strip().lower() == self.tag_name_column:
                self._used_tag_name_column = column_name
        if self.tag_name_column and not self._used_tag_name_column:
            raise ValueError(
                f'The tag name column "{self.tag_name_column}" was not found in the data'
            )
        rec: dict
        for rec in reader:
            data = {}
            for attr_name, column_name in self.column_names.items():
                if value := rec.get(column_name, "").strip():
                    if normalizer := self.attrs[attr_name].get("normalize"):
                        value = normalizer(value)
                data[attr_name] = value
            tag_names = []
            if self._used_tag_name_column:
                if tag_name := rec.get(self._used_tag_name_column):
                    tag_names = [tag_name.strip()]
            yield TitleTaggingRecord(
                title_rec=TitleRec(**data), tag_names=tag_names, source_data=rec
            )


class CsvTitleListReader(CsvReaderMixin, TitleListReader):
    matches_column = "_Matched titles_"

    def __init__(self, dump_id_formatter: Callable[[int], str] = str, **kwargs):
        super().__init__(**kwargs)
        self.dump_id_formatter = dump_id_formatter

    def extra_column_names(self) -> [str]:
        return [self.matches_column]

    def annotate_dump_record(self, record: TitleTaggingRecord) -> List[str]:
        count = len(record.title_ids)
        return [count] + list(map(self.dump_id_formatter, sorted(record.title_ids)))
