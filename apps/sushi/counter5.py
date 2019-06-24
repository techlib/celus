"""
Module dealing with data in the COUNTER5 format.
"""
from copy import copy


class CounterRecord(object):

    def __init__(self, platform=None, start=None, end=None, title=None, title_ids=None):
        self.platform = platform
        self.start = start
        self.end = end
        self.title = title
        self.title_ids = title_ids if title_ids else {}
        self.dimension_data = {}
        self.metric = None
        self.value = None


class Counter5ReportBase(object):

    dimensions = []  # this should be redefined in subclasses
    allowed_item_ids = ['DOI', 'Online_ISSN', 'Print_ISSN']

    def __init__(self):
        self.records = []

    def read_report(self, report: dict) -> [CounterRecord]:
        """
        Reads in the report as returned by the API using Sushi5Client
        :param report:
        :return:
        """
        records = []
        for item in report.get('Report_Items', []):
            record = CounterRecord()
            record.platform = item.get('Platform')
            record.title = item.get('Title')
            record.title_ids = self._extract_title_ids(item.get('Item_ID'))
            record.dimension_data = self._extract_dimension_data(self.dimensions, item)
            performances = item.get('Performance')
            assert len(performances) == 1, 'no idea what would it mean if there were more than 1'
            performance = performances[0]
            period = performance.get('Period', {})
            record.start = period.get('Begin_Date')
            record.end = period.get('End_Date')
            for metric in performance.get('Instance', []):
                this_rec = copy(record)
                this_rec.metric = metric.get('Metric_Type')
                this_rec.value = int(metric.get('Count'))
                records.append(this_rec)
        return records

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


class Counter5TRReport(Counter5ReportBase):

    dimensions = ['Access_Type', 'Access_Method', 'Data_Type', 'Section_Type', 'YOP', 'Publisher']
