"""
Module dealing with data in the COUNTER5 format.
"""
import csv
import json
import typing
from copy import copy

import ijson.backends.yajl2_c as ijson
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
        # by using a dict below, we do not allow more than one proprietary ID
        # this should be OK, but in most of the code below, we allow more than one prop. ID
        # In case we wanted to actually support it, we would need to change this code
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


ALLOWED_ITEM_IDS = {
    'DR': {'Proprietary': 'Proprietary', 'Proprietary_ID': 'Proprietary'},
    'TR': {
        'DOI': 'DOI',
        'Online_ISSN': 'Online_ISSN',
        'Print_ISSN': 'Print_ISSN',
        'ISBN': 'ISBN',
        'Proprietary': 'Proprietary',
        'Proprietary_ID': 'Proprietary_ID',
        'URI': 'URI',
    },
    'PR': {'Proprietary': 'Proprietary', 'Proprietary_ID': 'Proprietary'},
    'IR': {
        'DOI': 'DOI',
        'Online_ISSN': 'Online_ISSN',
        'Print_ISSN': 'Print_ISSN',
        'ISBN': 'ISBN',
        'Proprietary': 'Proprietary',
        'Proprietary_ID': 'Proprietary_ID',
        'URI': 'URI',
    },
    'IR_M1': {
        'DOI': 'DOI',
        'Online_ISSN': 'Online_ISSN',
        'Print_ISSN': 'Print_ISSN',
        'ISBN': 'ISBN',
        'Proprietary': 'Proprietary',
        'Proprietary_ID': 'Proprietary_ID',
        'URI': 'URI',
    },
}


class Counter5ReportBase:

    dimensions = []  # this should be redefined in subclasses
    allowed_item_ids: typing.Dict[str, str] = {}  # this should be redefined in subclasses

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
            self.check_item(item)
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

    def check_header(self, header, fd):
        lower_keys = [e.lower() for e in header]
        for field in ['report_id', 'customer_id']:  # mandatory header fields
            if field not in lower_keys:
                raise SushiException('Incorrect format', content=fd.read())

    def check_item(self, item: dict):
        """ Check whether the item is valid """
        self.check_no_extra_ids(item)

    def check_no_extra_ids(self, item: dict):
        """ Check that there are no extra title IDs """
        allowed = {e.lower() for e in self.allowed_item_ids}
        ids_keys = {e["Type"].lower() for e in (item.get("Item_ID", []) or [])}
        extra = ids_keys - allowed
        if extra:
            raise SushiException(f"Extra IDs not allowed {extra}", content=json.dumps(item))

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
            # entire json can be a list of errors
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

        # Try to read the data
        self.record_found = bool(next(ijson.items(fd, "Report_Items.item"), None))
        fd.seek(0)
        if self.record_found:
            items = ijson.items(fd, "Report_Items.item")
        else:
            self.record_found = bool(next(ijson.items(fd, "body.Report_Items.item"), None))
            if self.record_found:
                items = ijson.items(fd, "body.Report_Items.item")
            else:
                items = empty_generator()
        fd.seek(0)

        # try to read the header
        header = next(ijson.items(fd, "Report_Header"), None)
        fd.seek(0)
        # check whether the header is not located in 'body' element
        if not header:
            header = dict(ijson.kvitems(fd, "body.Report_Header"))
            fd.seek(0)

        if not self.record_found and not header:
            # not data and header not found entire json could be a header
            header = json.load(fd)
        fd.seek(0)

        # Extract errors
        if header:
            # Try to extract exceptions from header
            self.extract_errors(header)
            if not any((self.errors, self.warnings, self.infos)):
                # no  error/warning/info = > file has to contain a valid header
                self.check_header(header, fd)
                fd.seek(0)
        elif not self.record_found:
            # Header is missing and no data
            raise SushiException('Incorrect format', content=fd.read())
        else:
            # Header is empty, but data are present
            pass

        # error can be placed outside of header
        # look for them only if the header is missing or there are no data records
        # - if we look for them in each case, it can add quite some overhead for large files
        #   (like 20s for a 50 MB file)
        if (
            (not header or not self.record_found)
            and not self.errors
            and not self.warnings
            and not self.infos
        ):
            # Extract exceptions from root
            self.extract_errors(list(ijson.items(fd, "Exceptions.item")))  # In <root>
            fd.seek(0)
            self.extract_errors(dict(ijson.kvitems(fd, "Exception")))  # Single exception in <root>
            fd.seek(0)
            # Extract exception(s) from body
            self.extract_errors(list(ijson.items(fd, "body.Exceptions.item")))
            fd.seek(0)
            self.extract_errors(dict(ijson.kvitems(fd, "body.Exception")))
            fd.seek(0)

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
            if id_type := self.allowed_item_ids.get(value.get('Type')):
                ret[id_type] = value.get('Value')
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
    allowed_item_ids = ALLOWED_ITEM_IDS["DR"]

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
    allowed_item_ids = ALLOWED_ITEM_IDS["TR"]


class Counter5PRReport(Counter5ReportBase):

    dimensions = ['Access_Method', 'Data_Type', 'Platform']
    allowed_item_ids = ALLOWED_ITEM_IDS["PR"]

    @classmethod
    def _item_get_title(cls, item):
        # there are not titles in the platform report
        return None


class Counter5IRReport(Counter5ReportBase):

    dimensions = ['Access_Type', 'Access_Method', 'Data_Type', 'YOP', 'Publisher', 'Platform']
    allowed_item_ids = ALLOWED_ITEM_IDS["IR"]

    @classmethod
    def _item_get_title(cls, item):
        return item.get('Item')


class Counter5IRM1Report(Counter5IRReport):

    dimensions = ['Publisher', 'Platform']
    allowed_item_ids = ALLOWED_ITEM_IDS["IR_M1"]


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

    title_id_columns = {
        'DOI': 'DOI',
        'ISBN': 'ISBN',
        'Print_ISSN': 'Print_ISSN',
        'Online_ISSN': 'Online_ISSN',
        'Proprietary_ID': 'Proprietary',
        'Proprietary': 'Proprietary',
        'URI': 'URI',
    }

    ignored_columns = [
        'Reporting_Period_Total',
        'Publisher_ID',
        'Linking_ISSN',
    ]

    def file_to_records(self, filename: str) -> typing.Generator[CounterRecord, None, None]:
        with open(filename, 'r') as infile:
            for rec in self._fd_to_records(infile):
                yield rec

    def check_title_ids(self, report_type: str, title_ids: typing.Dict[str, str]):
        extra = set(title_ids.keys()) - set(ALLOWED_ITEM_IDS[report_type])
        if extra:
            raise ValueError("Unsupported IDs ({extra}) for report_type {report_type}")

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
                        title_ids[self.title_id_columns[key]] = value
                    else:
                        raise KeyError(f'We don\'t know how to interpret the column "{key}"')

            self.check_title_ids(report_type, title_ids)

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
