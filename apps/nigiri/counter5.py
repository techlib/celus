"""
Module dealing with data in the COUNTER5 format.
"""
import json
import typing
from copy import copy

import ijson.backends.python as ijson  # TODO yalj2 backend can be faster...

from .exceptions import SushiException


# TODO we can try to use  data classes https://docs.python.org/3/library/dataclasses.html
# but newer version o python >= 3.7 is required here
class CounterRecord:
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


class CounterError:
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


class TransportError:
    def __init__(self, http_status=None, message=None):
        self.http_status = http_status
        self.message = message

    def __str__(self):
        http = f' [HTTP {self.http_status}]' if self.http_status else ''
        return f'Transport error{http}: {self.message}'


class Counter5ReportBase:

    dimensions = []  # this should be redefined in subclasses
    allowed_item_ids = ['DOI', 'Online_ISSN', 'Print_ISSN', 'ISBN']

    def __init__(self, report: typing.Optional[typing.IO[bytes]] = None, http_status_code=None):
        self.records = []
        self.queued = False
        self.record_found: bool = False  # is populated once `fd_to_dicts` is called
        self.header = {}
        self.errors: typing.List[typing.Union[CounterError, TransportError]] = []
        self.warnings: typing.List[typing.Union[CounterError, TransportError]] = []
        self.http_status_code = http_status_code

        # Parse it for the first time to extract errors and warnings
        if report:
            self.fd_to_dicts(report)

    def read_report(
        self, header: dict, items: typing.Generator[dict, None, None],
    ) -> typing.Generator[CounterRecord, None, None]:
        """
        Reads in the report as returned by the API using Sushi5Client
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
        self, fd: typing.IO[bytes]
    ) -> typing.Tuple[dict, typing.Generator[dict, None, None]]:
        def empty_generator() -> typing.Generator[dict, None, None]:
            empty: typing.List[dict] = []
            return (e for e in empty)

        # make sure that fd is at the begining
        fd.seek(0)

        # first check whether it is not an error report
        # skip potential leading whitespace
        first_character = fd.read(1)  # type: bytes
        while first_character.isspace():
            first_character = fd.read(1)
        fd.seek(0)

        if first_character == b'[':
            # error report handling
            self.extract_errors(json.load(fd))
            return {}, empty_generator()

        elif first_character == b'"':
            # stringified header with an error recieved
            json_string = json.load(fd)
            data = json.loads(json_string)
            self.extract_errors(data)
            return data, empty_generator()

        elif first_character != b'{':
            self.errors.append(
                TransportError(http_status=self.http_status_code, message='Non SUSHI data returned')
            )
            return {}, empty_generator()

        # try to read the header
        header = dict(ijson.kvitems(fd, "Report_Header"))
        fd.seek(0)

        # check whether the header is not located in 'body' element
        if not header:
            header = dict(ijson.kvitems(fd, "body.Report_Header"))
            fd.seek(0)

        if header:
            # Try to extract exceptions from header
            self.extract_errors(header)

        # Errors still not extracted
        if not self.errors and not self.warnings:
            # Extract exceptions from root
            self.extract_errors(list(ijson.items(fd, "Exceptions.items")))  # In <root>
            fd.seek(0)
            self.extract_errors(dict(ijson.kvitems(fd, "Exception")))  # Single exception in <root>
            fd.seek(0)
            # Extract exception(s) from body
            self.extract_errors(list(ijson.items(fd, "body.Exceptions.items")))
            fd.seek(0)
            self.extract_errors(dict(ijson.kvitems(fd, "body.Exception")))
            fd.seek(0)

        # try to read the first item
        self.record_found = bool(next(ijson.items(fd, "Report_Items.item"), None))
        fd.seek(0)
        if self.record_found:
            # Items found
            items = ijson.items(fd, "Report_Items.item")
        else:
            # Try to seek in body element
            self.record_found = bool(next(ijson.items(fd, "body.Report_Items.item"), None))
            fd.seek(0)  # rewind back
            items = ijson.items(fd, "body.Report_Items.item")

        if not header and not self.record_found:
            # No data and no header -> try to extract an exception
            self.extract_errors(json.load(fd))
            items = empty_generator()

        if not self.record_found:
            # we have no data
            if not self.errors and not self.warnings:
                # check whether Report_Items or body.Report_Items are present
                # if they are present, but empty consider this as a valid input
                fd.seek(0)
                for prefix, e_type, _ in ijson.parse(fd):
                    if e_type == "start_array" and prefix in ("Report_Items", "body.Report_Items"):
                        return header, empty_generator()

                # We didn't find an exception nor data field => json is not correct
                raise SushiException('Incorrect format', content=fd.read())

        return header, items

    def file_to_records(self, filename: str) -> typing.Generator[CounterRecord, None, None]:
        f = open(filename, 'rb')  # file will be closed later (once generator struct is discarded)
        header, items = self.fd_to_dicts(f)
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


class Counter5IRReport(Counter5ReportBase):

    dimensions = ['Access_Type', 'Access_Method', 'Data_Type', 'YOP', 'Publisher']

    @classmethod
    def _item_get_title(cls, item):
        return item.get('Item')
