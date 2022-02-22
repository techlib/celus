"""
Module dealing with data in the COUNTER5 format.
"""
import csv
import json
import typing
from copy import copy

import ijson.backends.python as ijson  # TODO yalj2 backend can be faster...

from core.logic.dates import parse_counter_month
from .error_codes import ErrorCode, error_code_to_severity
from .exceptions import SushiException


# TODO we can try to use  data classes https://docs.python.org/3/library/dataclasses.html
# but newer version o python >= 3.7 is required here
class CounterRecord:
    __slots__ = (
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
        start=None,
        end=None,
        title=None,
        title_ids=None,
        metric=None,
        value=None,
        dimension_data=None,
    ):
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
        self.severity = severity if isinstance(severity, str) else error_code_to_severity(code)
        self.message = message
        self.data = data

    @classmethod
    def from_sushi_error(cls, sushi_error):
        return cls(
            code=sushi_error.code,
            severity=sushi_error.severity,
            message=sushi_error.text,
            data=sushi_error.data,
        )

    @classmethod
    def from_sushi_dict(cls, rec):
        severity = rec.get('Severity')
        severity = (
            severity if isinstance(severity, str) else error_code_to_severity(rec.get('Code'))
        )
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
        self.warnings: typing.List[CounterError] = []
        self.infos: typing.List[CounterError] = []
        self.http_status_code = http_status_code

        # Parse it for the first time to extract errors, warnings and infos
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
            record.title = self._item_get_title(item)
            record.title_ids = self._extract_title_ids(item.get('Item_ID', []) or [])
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
        from .client import Sushi5Client

        sushi_errors = Sushi5Client.extract_errors_from_data(data)

        if any(str(e.code) == str(ErrorCode.PREPARING_DATA.value) for e in sushi_errors):
            # special status telling us we should retry later
            self.queued = True

        for sushi_error in sushi_errors:
            counter_error = CounterError.from_sushi_error(sushi_error)
            if sushi_error.is_warning:
                self.warnings.append(counter_error)
            elif sushi_error.is_info:
                self.infos.append(counter_error)
            else:
                self.errors.append(counter_error)

    def fd_to_dicts(
        self, fd: typing.IO[bytes]
    ) -> typing.Tuple[dict, typing.Generator[dict, None, None]]:
        def empty_generator() -> typing.Generator[dict, None, None]:
            empty: typing.List[dict] = []
            return (e for e in empty)

        # make sure that fd is at the beginning
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
            # stringified header with an error received
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
        if not self.errors and not self.warnings and not self.infos:
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

    dimensions = ['Access_Method', 'Data_Type', 'Publisher', 'Platform']

    @classmethod
    def _item_get_title(cls, item):
        return item.get('Database')


class Counter5TRReport(Counter5ReportBase):

    dimensions = [
        'Access_Type',
        'Access_Method',
        'Data_Type',
        'Section_Type',
        'YOP',
        'Publisher',
        'Platform',
    ]


class Counter5PRReport(Counter5ReportBase):

    dimensions = ['Access_Method', 'Data_Type', 'Platform']

    @classmethod
    def _item_get_title(cls, item):
        # there are not titles in the platform report
        return None


class Counter5IRReport(Counter5ReportBase):

    dimensions = ['Access_Type', 'Access_Method', 'Data_Type', 'YOP', 'Publisher', 'Platform']

    @classmethod
    def _item_get_title(cls, item):
        return item.get('Item')


class Counter5IRM1Report(Counter5IRReport):

    dimensions = ['Publisher', 'Platform']


class Counter5TableReport:
    """
    Implements reading of C5 reports stored in a CSV/TSV tabular format
    """

    dimensions = []

    column_map = {
        'Metric_Type': 'metric',
        'Organization': 'organization',
        'Database': 'title',
        'Title': 'title',
        'Item': 'title',
    }

    report_type_to_dimensions = {
        'DR': ['Access_Method', 'Data_Type', 'Publisher', 'Platform'],
        'TR': [
            'Access_Type',
            'Access_Method',
            'Data_Type',
            'Section_Type',
            'YOP',
            'Publisher',
            'Platform',
        ],
        'PR': ['Access_Method', 'Data_Type', 'Platform'],
        'IR': ['Access_Type', 'Access_Method', 'Data_Type', 'YOP', 'Publisher', 'Platform'],
        'IR_M1': ['Publisher', 'Platform'],
    }

    title_id_columns = ['DOI', 'ISBN', 'Print_ISSN', 'Online_ISSN']

    ignored_columns = [
        'Reporting_Period_Total',
        'Publisher_ID',
        'Proprietary_ID',
        'Linking_ISSN',
        'URI',
    ]

    def file_to_records(self, filename: str) -> typing.Generator[CounterRecord, None, None]:
        with open(filename, 'r') as infile:
            for rec in self._fd_to_records(infile):
                yield rec

    def _fd_to_records(self, infile) -> typing.Generator[CounterRecord, None, None]:
        # guess TSV or CSV and other csv stuff (e.g. how strings are escaped)
        dialect = csv.Sniffer().sniff(infile.read(10 * 1024 * 1024))  # first 10MB
        infile.seek(0)

        # read the header
        header = {}
        reader = csv.reader(infile, dialect=dialect)
        for header_line in reader:
            if not header_line or not header_line[0].strip():
                # we break on empty line - it means end of header and start of data
                break
            header[header_line[0].strip()] = header_line[1].strip() if len(header_line) > 1 else ''
        report_type = header.get('Report_ID')
        if not report_type or report_type not in self.report_type_to_dimensions:
            raise ValueError(f'Unsupported report type: {report_type}')
        if header.get('Release') != '5':
            raise ValueError(f'Unsupported COUNTER release: {header.get("Release")}')

        # we continue reading using a dict reader
        reader = csv.DictReader(infile, dialect=dialect)
        extra_dims = self.report_type_to_dimensions[report_type]
        # process the records
        for record in reader:
            implicit_dimensions = {}
            explicit_dimensions = {}
            monthly_values = {}
            title_ids = {}
            for key, value in record.items():
                key = key.strip()
                value = value.strip()
                if not value:
                    continue
                month = parse_counter_month(key)
                if month:
                    monthly_values[month] = int(value)
                else:
                    if not key or key in self.ignored_columns:
                        pass
                    elif key in self.column_map:
                        implicit_dimensions[self.column_map[key]] = value
                    elif key in extra_dims:
                        explicit_dimensions[key] = value
                    elif key in self.title_id_columns:
                        title_ids[key] = value
                    else:
                        raise KeyError(f'We don\'t know how to interpret the column "{key}"')
            # we put initial data into the data we read - these are usually dimensions that are fixed
            # for the whole import and are not part of the data itself
            # for key, value in initial_data.items():
            #     if key not in implicit_dimensions:
            #         implicit_dimensions[key] = value  # only update if the value is not present
            for month, value in monthly_values.items():
                yield CounterRecord(
                    value=value,
                    start=month,
                    dimension_data=explicit_dimensions,
                    title_ids=title_ids,
                    **implicit_dimensions,
                )
