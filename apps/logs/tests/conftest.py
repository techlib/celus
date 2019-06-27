import faker
import pytest

from logs.models import ReportType, Dimension, ReportTypeToDimension
from sushi.counter5 import CounterRecord


@pytest.fixture
def counter_records_0d():
    rec1 = CounterRecord(platform='Platform1', start='2019-01-01', end='2019-01-31',
                         metric='Metric 1', value=50, dimension_data={},
                         title='Title X', title_ids={'Print_ISSN': '1234-5678'})
    return [rec1]


@pytest.fixture
def counter_records_nd():
    def fn(dim_number, record_number=1, title=None, dim_value=None):
        """
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
            rec = CounterRecord(platform=f'Platform{fake.pyint()}',
                                start='2019-01-01',
                                end='2019-01-31',
                                metric=f'Metric {fake.pyint()}',
                                value=fake.pyint(),
                                dimension_data=dim_data,
                                title=title,
                                title_ids={'ISBN': fake.isbn13()})
            yield rec
    return fn


@pytest.fixture
def report_type_nd():
    def fn(dim_number):
        rt = ReportType.objects.create(short_name=f'{dim_number}d',
                                       name=f'{dim_number} dimensional report')
        for i in range(dim_number):
            dim = Dimension.objects.create(short_name=f'dim{i}', name=f'dimension-{i}',
                                           type=Dimension.TYPE_TEXT)
            ReportTypeToDimension.objects.create(report_type=rt, dimension=dim, position=i)
        return rt
    return fn
