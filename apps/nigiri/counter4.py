"""
Module dealing with data in the COUNTER4 format as provided by the pycounter library
"""

import typing
from copy import copy

from pycounter import report
from pycounter.report import CounterEresource, CounterReport

from .counter5 import CounterRecord


class Counter4ReportBase(object):

    dimensions = []  # this should be redefined in subclasses
    allowed_item_ids = ['DOI', 'Online_ISSN', 'Print_ISSN', 'ISBN']

    dimension_to_attr = {
        'Publisher': 'publisher',
    }
    title_id_to_attr = {
        'Print_ISSN': 'issn',
        'Online_ISSN': 'eissn',
        'ISBN': 'isbn',
        'DOI': 'doi',
    }

    def __init__(self):
        self.records = []

    def read_report(self, report: CounterReport) -> typing.Generator[CounterRecord, None, None]:
        """
        Reads in the report as returned by the API using Sushi5Client
        :param report:
        :return:
        """
        for journal in report:  # type: CounterEresource
            for start, metric, value in journal:
                record = CounterRecord()
                record.platform_name = journal.platform
                record.title = journal.title
                record.title_ids = self._extract_title_ids(journal)
                record.dimension_data = self._extract_dimension_data(self.dimensions, journal)
                record.start = start
                record.metric = metric
                record.value = value
                yield record

    def file_to_records(self, filename: str) -> typing.Generator[CounterRecord, None, None]:
        data = self.file_to_input(filename)
        return self.read_report(data)

    @classmethod
    def file_to_input(cls, filename: str):
        return report.parse(filename)

    def _extract_title_ids(self, record) -> dict:
        ret = {}
        for title_id in self.allowed_item_ids:
            attr = self.title_id_to_attr.get(title_id, title_id)
            if hasattr(record, attr):
                ret[title_id] = getattr(record, attr)
        return ret

    @classmethod
    def _extract_dimension_data(cls, dimensions: list, record: CounterEresource) -> dict:
        ret = {}
        for dimension in dimensions:
            attr_name = cls.dimension_to_attr.get(dimension, dimension)
            if hasattr(record, attr_name):
                ret[dimension] = getattr(record, attr_name)
        return ret


class Counter4JR1Report(Counter4ReportBase):

    dimensions = ['Publisher']


class Counter4JR2Report(Counter4ReportBase):

    dimensions = ['Publisher']


class Counter4BR1Report(Counter4ReportBase):

    dimensions = ['Publisher']


class Counter4BR2Report(Counter4ReportBase):

    dimensions = ['Publisher']


class Counter4BR3Report(Counter4ReportBase):

    dimensions = ['Publisher']


class Counter4DB1Report(Counter4ReportBase):

    dimensions = ['Publisher']


class Counter4DB2Report(Counter4ReportBase):

    dimensions = ['Publisher', 'Access Denied Category']


class Counter4PR1Report(Counter4ReportBase):

    dimensions = ['Publisher']
