"""
Module dealing with data in the COUNTER5 format.
"""
import csv
import json
import typing
from copy import copy

from core.logic.dates import parse_counter_month
from .exceptions import SushiException


class CounterRecord(object):
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

    def __str__(self):
        return f'{self.severity or "Error"} #{self.code}: {self.message}'

    def raise_me(self):
        raise SushiException(str(self), content=self.data)


class Counter5ReportBase(object):

    dimensions = []  # this should be redefined in subclasses
    allowed_item_ids = ['DOI', 'Online_ISSN', 'Print_ISSN', 'ISBN']

    def __init__(self, report=None):
        self.records = []
        self.queued = False
        self.header = {}
        self.errors = []
        self.warnings = []
        self.raw_data = None
        if report:
            self.read_report(report)

    def read_report(self, report: dict) -> [CounterRecord]:
        """
        Reads in the report as returned by the API using Sushi5Client
        :param report:
        :return:
        """
        self.raw_data = report
        if type(report) is list:
            self.extract_errors(report)
            return []
        # check for messed up report with extra wrapping 'body' element
        if (
            'Report_Header' not in report
            and 'body' in report
            and report['body']
            and 'Report_Header' in report['body']
        ):
            report = report['body']

        self.header = report.get('Report_Header')
        if not self.header:
            self.extract_errors(report)
        else:
            self.extract_errors(self.header.get('Exceptions', []))
        records = []
        items = report.get('Report_Items')
        if items is not None:
            for item in items:
                record = CounterRecord()
                record.platform_name = item.get('Platform')
                record.title = self._item_get_title(item)
                # Item_ID can (should not, but can) be null, so we use get() or [] to handle it
                record.title_ids = self._extract_title_ids(item.get('Item_ID') or [])
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
                        records.append(this_rec)
        else:
            # we have no data
            if not self.errors and not self.warnings:
                # if there is no other reason why there should be no data, we raise exception
                raise SushiException('Incorrect format', content=report)
        self.records = records
        return records

    def extract_errors(self, data):
        if type(data) is list:
            [self.extract_errors(item) for item in data]
        else:
            if 'Exceptions' in data:
                return self.extract_errors(data['Exceptions'])
            if 'Code' in data or 'Severity' in data:
                error = CounterError.from_sushi_dict(data)
                if error.severity in ('Warning', 'Info'):
                    self.warnings.append(error)
                    if error.code and int(error.code) == 1011:
                        # special warning telling us we should retry later
                        self.queued = True
                else:
                    self.errors.append(error)

    def file_to_records(self, filename: str):
        data = self.file_to_input(filename)
        return self.read_report(data)

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


class Counter5TableReport:
    """
    Implements reading of C5 reports stored in a CSV/TSV tabular format
    """

    dimensions = []

    column_map = {
        'Metric_Type': 'metric',
        'Organization': 'organization',
        'Database': 'title',
        'Platform': 'platform_name',
        'Title': 'title',
        'Item': 'title',
    }

    report_type_to_dimensions = {
        'DR': ['Access_Method', 'Data_Type', 'Publisher'],
        'TR': ['Access_Type', 'Access_Method', 'Data_Type', 'Section_Type', 'YOP', 'Publisher'],
        'PR': ['Access_Method', 'Data_Type'],
        'IR': ['Access_Type', 'Access_Method', 'Data_Type', 'YOP', 'Publisher'],
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
        # guess TSV or CSV
        dialect = csv.Sniffer().sniff(infile.read(1024))
        infile.seek(0)

        # read the header
        header = {}
        reader = csv.reader(infile, dialect=dialect)
        for header_line in reader:
            if not header_line[0].strip():
                # we break on empty line - it means end of header and start of data
                break
            header[header_line[0].strip()] = header_line[1].strip()
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
