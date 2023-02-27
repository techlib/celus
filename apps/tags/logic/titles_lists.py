import abc
import codecs
import csv
import itertools
import operator
from collections import defaultdict
from dataclasses import dataclass, field
from functools import reduce
from gettext import ngettext
from typing import Any, BinaryIO, Callable, Dict, Generator, Iterable, Optional, Set

from django.db.models import Q
from logs.logic.data_import import TitleRec
from logs.logic.validation import normalize_isbn, normalize_issn
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
                    dump_stream = codecs.getwriter('utf-8')(dump_file)
                    dump_writer = csv.DictWriter(
                        dump_stream,
                        fieldnames=list(rec.source_data.keys()) + self.extra_column_names(),
                    )
                    dump_writer.writeheader()
                annotations = self.annotate_dump_record(rec)
                dump_writer.writerow({**rec.source_data, **annotations})
            yield rec

    def extra_column_names(self) -> [str]:
        return []

    def annotate_dump_record(self, record: TitleTaggingRecord) -> dict:
        return {}

    def add_extra_data_to_rec_batch(self, records: [TitleTaggingRecord]):
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
        filters = {'isbn': set(), 'issn': issn_set, 'eissn': eissn_set, 'doi': set()}
        for record in records:
            if not record.title_ids:
                for attr, array in filters.items():
                    if value := getattr(record.title_rec, attr, ''):
                        array.add(value)

        # prepare a mapping between some title identifier (like issn, isbn) and title pks
        if merge_issns:
            issn_dict = eissn_dict = defaultdict(set)
        else:
            issn_dict, eissn_dict = defaultdict(set), defaultdict(set)

        id_to_titles = {
            'isbn': defaultdict(set),
            'issn': issn_dict,
            'eissn': eissn_dict,
            'doi': defaultdict(set),
        }
        q_filters = [Q(**{f'{attr}__in': array}) for attr, array in filters.items() if array]
        if q_filters:
            for title_rec in (
                self.title_qs()
                .filter(reduce(operator.or_, q_filters))
                .values('pk', *id_to_titles.keys())
            ):
                for attr, storage in id_to_titles.items():
                    if value := title_rec.get(attr):
                        storage[value].add(title_rec['pk'])
        # now process the records
        for record in records:
            title_ids = set()
            for attr, storage in id_to_titles.items():
                if value := getattr(record.title_rec, attr):
                    title_ids |= storage.get(value, set())
            record.title_ids = title_ids
        self.add_extra_data_to_rec_batch(records)
        for record in records:
            yield record


class CsvReaderMixin:

    attrs = {
        'isbn': {'normalize': normalize_isbn},
        'issn': {'normalize': lambda x: normalize_issn(x, raise_error=False)},
        'eissn': {'normalize': lambda x: normalize_issn(x, raise_error=False)},
        'doi': {'normalize': None},
        'name': {'normalize': None},
    }

    def __init__(self):
        super().__init__()
        # the following will hold the column names found in the data. The key is always one of
        # `self.attrs`, the value is the actual column name
        self.column_names = {}

    def parse_data(self, source: Iterable[str]) -> Generator[TitleTaggingRecord, None, None]:
        reader = csv.DictReader(source)
        # find which columns are present and find the actual form of the name (case and whitespace)
        for column_name in reader.fieldnames:
            for attr_name in self.attrs:
                if column_name.strip().lower() == attr_name:
                    self.column_names[attr_name] = column_name
        for rec in reader:
            data = {}
            for attr_name, column_name in self.column_names.items():
                if value := rec.get(column_name, '').strip():
                    if normalizer := self.attrs[attr_name].get('normalize'):
                        value = normalizer(value)
                data[attr_name] = value
            yield TitleTaggingRecord(title_rec=TitleRec(**data), tag_names=[], source_data=rec)


class CsvTitleListReader(CsvReaderMixin, TitleListReader):

    has_explicit_tags = False
    annotation_column = '_Celus info_'

    def __init__(self, dump_id_formatter: Callable[[int], str] = str):
        super().__init__()
        self.dump_id_formatter = dump_id_formatter

    def extra_column_names(self) -> [str]:
        return [self.annotation_column]

    def annotate_dump_record(self, record: TitleTaggingRecord) -> dict:
        count = len(record.title_ids)
        annotation = ngettext('{} match', '{} matches', count).format(count)
        if count:
            title_ids = ', '.join(map(self.dump_id_formatter, sorted(record.title_ids)))
            annotation += f' ({title_ids})'
        return {self.annotation_column: annotation}
