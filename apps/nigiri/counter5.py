"""
Module dealing with data in the COUNTER5 format.
"""
import json
import io
import typing
from copy import copy

import ijson.backends.python as ijson  # TODO yalj2 backend can be faster...

from .exceptions import SushiException


# TODO we can try to use  data classes https://docs.python.org/3/library/dataclasses.html
# but newer version o python >= 3.7 is required here
class CounterRecord(object):
    __slots__ = (
        "platform_name",
        "start",
        "end",
        "title",
        "title_ids",
        "dimension_data",
        "metric",
        "value",
    )

    def __init__(
        self,
        platform_name=None,
        start=None,
        end=None,
        title=None,
        title_ids=None,
        metric=None,
        value=None,
        dimension_data=None,
    ):
        self.platform_name = platform_name
        self.start = start
        self.end = end
        self.title = title
        self.title_ids = title_ids if title_ids else {}
        self.dimension_data = dimension_data if dimension_data is not None else {}
        self.metric = metric
        self.value = value

    @classmethod
    def empty_generator(cls) -> typing.Generator['CounterRecord', None, None]:
        empty: typing.List['CounterRecord'] = []
        return (e for e in empty)


class CounterError(object):
    def __init__(self, code=None, severity=None, message=None, data=None):
        self.code = code
        self.severity = severity
        self.message = message
        self.data = data

    @classmethod
    def from_sushi_dict(cls, rec):
        return cls(
            code=rec.get('Code'),
            severity=rec.get('Severity'),
            message=rec.get('Message'),
            data=rec.get('Data'),
        )

    def to_sushi_dict(self):
        return dict(Code=self.code, Severity=self.severity, Message=self.message, Data=self.data,)

    def __str__(self):
        return f'{self.severity or "Error"} #{self.code}: {self.message}'

    def raise_me(self):
        raise SushiException(str(self), content=self.data)


class Counter5ReportBase(object):

    dimensions = []  # this should be redefined in subclasses
    allowed_item_ids = ['DOI', 'Online_ISSN', 'Print_ISSN', 'ISBN']

    def __init__(self, report: typing.Optional[bytes] = None):
        self.records = []
        self.queued = False
        self.header = {}
        self.errors: typing.List[CounterError] = []
        self.warnings: typing.List[CounterError] = []
        self.raw_data = report  # TODO raw data are supposed to be removed

        # Parse it for the first time to extract errors and warnings
        if self.raw_data:
            fd = io.StringIO(self.raw_data.decode())
            self.fd_to_dicts(fd)

    def read_report(
        self, header: dict, items: typing.Generator[dict, None, None],
    ) -> typing.Generator[CounterRecord, None, None]:
        """
        Reads in the report as returned by the API using Sushi5Client
        :param report:
        :return:
        """

        self.header = header

        for item in items:
            record = CounterRecord()
            record.platform_name = item.get('Platform')
            record.title = self._item_get_title(item)
            record.title_ids = self._extract_title_ids(item.get('Item_ID', []))
            record.dimension_data = self._extract_dimension_data(self.dimensions, item)
            performances = item.get('Performance')
            for performance in performances:
                period = performance.get('Period', {})
                record.start = period.get('Begin_Date')
                record.end = period.get('End_Date')
                for metric in performance.get('Instance', []):
                    this_rec = copy(record)
                    this_rec.metric = metric.get('Metric_Type')
                    this_rec.value = int(metric.get('Count'))
                    yield this_rec

    def extract_errors(self, data):
        if type(data) is list:
            [self.extract_errors(item) for item in data]
        else:
            if 'Exceptions' in data:
                return self.extract_errors(data['Exceptions'])
            elif 'Exception' in data:
                return self.extract_errors(data['Exception'])
            if 'Code' in data or 'Severity' in data:
                error = CounterError.from_sushi_dict(data)
                if error.severity in ('Warning', 'Info'):
                    self.warnings.append(error)
                    if error.code and int(error.code) == 1011:
                        # special warning telling us we should retry later
                        self.queued = True
                else:
                    self.errors.append(error)

    def fd_to_dicts(
        self, fd: typing.TextIO
    ) -> typing.Tuple[bool, dict, typing.Generator[dict, None, None]]:
        def empty_generator() -> typing.Generator[dict, None, None]:
            empty: typing.List[dict] = []
            return (e for e in empty)

        # first check whether it is not an error report
        first_character = fd.read(1)
        while first_character not in '[{"':
            first_character = fd.read(1)
        fd.seek(0)

        if first_character == '[':
            # error report handling
            self.extract_errors(json.load(fd))
            return False, {}, empty_generator()

        elif first_character == '"':
            # stringified header with an error recieved
            json_string = json.load(fd)
            data = json.loads(json_string)
            self.extract_errors(data)
            return False, data, empty_generator()

        # try to read the header
        header = dict(ijson.kvitems(fd, "Report_Header"))
        fd.seek(0)

        # check whether the header is not located in 'body' element
        if not header:
            header = dict(ijson.kvitems(fd, "body.Report_Header"))
            fd.seek(0)
        else:
            # Try to extract exceptions from header
            self.extract_errors(header)

        # Try to Read exceptions
        self.extract_errors(header.get('Exceptions', []))  # In header
        self.extract_errors(list(ijson.items(fd, "Exceptions.items")))  # In <root>
        fd.seek(0)
        self.extract_errors(list(ijson.items(fd, "body.Exceptions.items")))  # In body element
        fd.seek(0)

        # try to read the first item
        record_found = bool(next(ijson.items(fd, "Report_Items.item"), None))
        fd.seek(0)
        if record_found:
            # Items found
            items = ijson.items(fd, "Report_Items.item")
        else:
            # Try to seek in body element
            record_found = bool(next(ijson.items(fd, "body.Report_Items.item"), None))
            fd.seek(0)  # rewind back
            items = ijson.items(fd, "body.Report_Items.item")

        if not header and not record_found:
            # No data and no header -> try to extract an exception
            self.extract_errors(json.load(fd))
            items = empty_generator()

        if not record_found:
            # we have no data
            if not self.errors and not self.warnings:
                # if there is no other reason why there should be no data, we raise exception
                raise SushiException('Incorrect format', content=fd.read())

        return record_found, header, items

    def file_to_records(self, filename: str) -> typing.Generator[CounterRecord, None, None]:
        f = open(filename, 'r')  # file will be closed later (once generator struct is discarded)
        record_found, header, items = self.fd_to_dicts(f)
        self.record_found = record_found
        return self.read_report(header, items)

    @classmethod
    def file_to_input(cls, filename: str):
        with open(filename, 'r', encoding='utf-8') as infile:
            return json.load(infile)

    @classmethod
    def _item_get_title(cls, item):
        return item.get('Title')

    def _extract_title_ids(self, values: list) -> dict:
        ret = {}
        for value in values:
            if value.get('Type') in self.allowed_item_ids:
                ret[value.get('Type')] = value.get('Value')
        return ret

    @classmethod
    def _extract_dimension_data(cls, dimensions: list, record: dict):
        ret = {}
        for dim in dimensions:
            if dim in record:
                ret[dim] = record[dim]
        return ret


class Counter5DRReport(Counter5ReportBase):

    dimensions = ['Access_Method', 'Data_Type', 'Publisher']

    @classmethod
    def _item_get_title(cls, item):
        return item.get('Database')


class Counter5TRReport(Counter5ReportBase):

    dimensions = ['Access_Type', 'Access_Method', 'Data_Type', 'Section_Type', 'YOP', 'Publisher']


class Counter5PRReport(Counter5ReportBase):

    dimensions = ['Access_Method', 'Data_Type']

    @classmethod
    def _item_get_title(cls, item):
        # there are not titles in the platform report
        return None
