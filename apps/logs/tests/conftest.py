import calendar
from datetime import date

import dateparser
import faker
import pytest

from logs.models import ReportType, Dimension, ReportTypeToDimension
from nigiri.counter5 import CounterRecord
from publications.models import Platform


@pytest.fixture
def counter_records_0d():
    rec1 = CounterRecord(platform_name='Platform1', start='2019-01-01', end='2019-01-31',
                         metric='Metric 1', value=50, dimension_data={},
                         title='Title X', title_ids={'Print_ISSN': '1234-5678'})
    return [rec1]


@pytest.fixture
def counter_records_nd():
    def fn(dim_number, record_number=1, title=None, dim_value=None, metric=None):
        """
        :param metric:
        :param dim_number: number of dimensions
        :param record_number: number of records
        :param title: if given, used for all titles, otherwise random value will be created
        :param dim_value: use this for all dimensions values, if None, a random word will be used
        :return:
        """
        fake = faker.Faker()
        for i in range(record_number):
            dim_data = {f'dim{i}': fake.word() if dim_value is None else dim_value
                        for i in range(dim_number)}
            if title is None:
                title = f'title {fake.pyint()}'
            rec = CounterRecord(platform_name=f'Platform{fake.pyint()}',
                                start='2019-01-01',
                                end='2019-01-31',
                                metric=metric if metric else f'Metric {fake.pyint()}',
                                value=fake.pyint(),
                                dimension_data=dim_data,
                                title=title,
                                title_ids={'ISBN': fake.isbn13()})
            yield rec
    return fn


@pytest.fixture
def counter_records():
    def fn(datapoints, metric=None, platform=None):
        """
        :param platform:
        :param metric:
        :param datapoints: matrix of data,
          the first column must be title (or None to generate fake),
          the second column is date,
          last column is the actual value,
          columns in between are for the additional dimensions
        :return:
        """
        fake = faker.Faker()
        for row in datapoints:
            assert len(row) >= 3
            title = row[0] if row[0] else fake.sentence()
            start = row[1]
            end = dateparser.parse(start)  # type: date
            end = end.replace(day=calendar.monthrange(end.year, end.month)[1])  # last day of month
            dim_data = {f'dim{i}': value for i, value in enumerate(row[2:-1])}
            value = row[-1]
            rec = CounterRecord(platform_name=platform if platform else f'Platform{fake.pyint()}',
                                start=start,
                                end=end.isoformat(),
                                metric=metric if metric else f'Metric {fake.pyint()}',
                                value=value,
                                dimension_data=dim_data,
                                title=title,
                                title_ids={'Print_ISSN': '1234-5678'})
            yield rec
    return fn


@pytest.fixture
def report_type_nd():
    def fn(dim_number, dimension_names=None, short_name=None):
        rt = ReportType.objects.create(short_name=short_name or f'{dim_number}d',
                                       name=f'{dim_number} dimensional report')
        for i in range(dim_number):
            if dimension_names and i < len(dimension_names):
                dim_short_name = dimension_names[i]
            else:
                dim_short_name = f'dim{i}'
            dim = Dimension.objects.create(short_name=dim_short_name, name=f'dimension-{i}',
                                           type=Dimension.TYPE_TEXT)
            ReportTypeToDimension.objects.create(report_type=rt, dimension=dim, position=i)
        return rt
    return fn


@pytest.fixture
def platform():
    platform = Platform.objects.create(ext_id=1234, short_name='Platform1', name='Platform 1',
                                       provider='Provider 1')
    return platform
