import calendar
from itertools import product

import faker
import pytest

from core.logic.dates import parse_date_fuzzy
from logs.models import (
    ReportType,
    Dimension,
    ReportTypeToDimension,
    Metric,
    ImportBatch,
    DimensionText,
    AccessLog,
)
from nigiri.counter5 import CounterRecord
from organizations.models import Organization
from publications.models import Platform, Title


@pytest.fixture
def counter_records_0d():
    rec1 = CounterRecord(
        start='2019-01-01',
        end='2019-01-31',
        metric='Metric 1',
        value=50,
        dimension_data={},
        title='Title X',
        title_ids={'Print_ISSN': '1234-5678'},
    )
    return (e for e in [rec1])


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
            dim_data = {
                f'dim{i}': fake.word() if dim_value is None else dim_value
                for i in range(dim_number)
            }
            if title is None:
                title = f'title {fake.pyint()}'
            rec = CounterRecord(
                start='2019-01-01',
                end='2019-01-31',
                metric=metric if metric else f'Metric {fake.pyint()}',
                value=fake.pyint(),
                dimension_data=dim_data,
                title=title,
                title_ids={'ISBN': fake.isbn13()},
            )
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
            end = parse_date_fuzzy(start)
            end = end.replace(day=calendar.monthrange(end.year, end.month)[1])  # last day of month
            dim_data = {f'dim{i}': value for i, value in enumerate(row[2:-1])}
            value = row[-1]
            rec = CounterRecord(
                start=start,
                end=end.isoformat(),
                metric=metric if metric else f'Metric {fake.pyint()}',
                value=value,
                dimension_data=dim_data,
                title=title,
                title_ids={'Print_ISSN': '1234-5678'},
            )
            yield rec

    return fn


@pytest.fixture()
def report_type_nd():
    def fn(dim_number, dimension_names=None, short_name=None, name=None):
        rt = ReportType.objects.create(
            short_name=short_name or f'{dim_number}d',
            name=name or f'{dim_number} dimensional report',
        )
        for i in range(dim_number):
            if dimension_names and i < len(dimension_names):
                dim_short_name = dimension_names[i]
            else:
                dim_short_name = f'dim{i}'
            dim, _ = Dimension.objects.get_or_create(
                short_name=dim_short_name, name=f'dimension-{i}'
            )
            ReportTypeToDimension.objects.create(report_type=rt, dimension=dim, position=i)
        return rt

    return fn


@pytest.fixture
def platform():
    platform = Platform.objects.create(
        ext_id=1234, short_name='Platform1', name='Platform 1', provider='Provider 1'
    )
    return platform


def value_generator():
    i = 1
    while True:
        yield i
        i += 1


@pytest.fixture
def flexible_slicer_test_data(report_type_nd):
    """
    Creates a 'cube' of AccessLogs for all combinations of organization, platform, report_type, etc.
    """

    organizations = [
        Organization.objects.create(short_name='org1', name='Organization 1'),
        Organization.objects.create(short_name='org2', name='Organization 2'),
        Organization.objects.create(short_name='org3', name='Organization 3'),
    ]
    platforms = [
        Platform.objects.create(short_name='pl1', name='Platform 1'),
        Platform.objects.create(short_name='pl2', name='Platform 2'),
        Platform.objects.create(short_name='pl3', name='Platform 3'),
    ]
    metrics = [
        Metric.objects.create(short_name='m1', name='Metric 1'),
        Metric.objects.create(short_name='m2', name='Metric 2'),
        Metric.objects.create(short_name='m3', name='Metric 3'),
    ]
    targets = [
        Title.objects.create(name='Title 1', isbn='123456789'),
        Title.objects.create(name='Title 2', issn='964326665'),
        Title.objects.create(name='Title 3', issn='656893466'),
    ]
    report_types = [
        report_type_nd(1, ['dim1name'], short_name='rt1', name='Report type 1'),
        report_type_nd(2, ['dim1name', 'dim2name'], short_name='rt2', name='Report type 2'),
    ]
    dates = ['2019-12-01', '2020-01-01', '2020-02-01', '2020-03-01']
    dimension_values = [
        ['A', 'B', 'C'],
        ['XX', 'YY', 'ZZ', 'A'],  # "A" is intentionally in both - we want to check for clashes
    ]
    values = value_generator()
    accesslogs = []
    dimension_texts = {}
    for rt in report_types:
        ib = ImportBatch.objects.create(report_type=rt)
        dim_count = rt.dimensions.count()
        dim_options = dimension_values[:dim_count]
        for i, dim in enumerate(rt.dimensions_sorted):
            for value in dimension_values[i]:
                dimension_texts[(dim.pk, value)], _ = DimensionText.objects.get_or_create(
                    dimension=dim, text=value
                )
        for rec in product(organizations, platforms, metrics, targets, dates, *dim_options):
            organization, platform, metric, target, date = rec[:5]
            dim_data = {}
            for i in range(dim_count):
                attr = f'dim{i+1}'
                value_str = rec[5 + i]
                value_key = dimension_texts[(rt.dimensions_sorted[i].pk, value_str)]
                dim_data[attr] = value_key.pk
            value = next(values)
            accesslogs.append(
                AccessLog(
                    report_type=rt,
                    organization=organization,
                    platform=platform,
                    metric=metric,
                    target=target,
                    date=date,
                    value=value,
                    import_batch=ib,
                    **dim_data,
                )
            )

    AccessLog.objects.bulk_create(accesslogs)
    # uncomment the following to get the test data in a CSV file
    # it is useful when you want to use pivot table in a spreadsheet to check the calculations
    # it will produce a table with names/human friendly values for all dimensions
    # import csv
    #
    # with open('/tmp/TestFlexibleDataSlicer.csv', 'w') as out:
    #     writer = csv.writer(out)
    #     writer.writerow(
    #         [
    #             'report_type',
    #             'organization',
    #             'platform',
    #             'metric',
    #             'target',
    #             'date',
    #             'dim1',
    #             'dim2',
    #             'value',
    #         ]
    #     )
    #     text_reverse_map = {
    #         (dim_id, text.pk): dim_value for ((dim_id, dim_value), text) in dimension_texts.items()
    #     }
    #     for al in accesslogs:
    #         writer.writerow(
    #             [
    #                 al.report_type.name,
    #                 al.organization.name,
    #                 al.platform.name,
    #                 al.metric.name,
    #                 al.target.name,
    #                 al.date,
    #                 text_reverse_map[(al.report_type.dimensions_sorted[0].pk, al.dim1)]
    #                 if al.dim1
    #                 else None,
    #                 text_reverse_map[(al.report_type.dimensions_sorted[1].pk, al.dim2)]
    #                 if al.dim2
    #                 else None,
    #                 al.value,
    #             ]
    #         )
    return {
        'report_types': report_types,
        'organizations': organizations,
        'platforms': platforms,
        'metrics': metrics,
        'targets': targets,
        'dates': dates,
        'dimension_values': dimension_values,
    }


@pytest.fixture
def flexible_slicer_test_data2(report_type_nd):
    """
    Creates a 'cube' of AccessLogs for all combinations of organization, platform, report_type, etc.
    This one is slightly different from `flexible_slicer_test_data` in that it uses one dimension
    of type INT for one of the report types
    """

    organizations = [
        Organization.objects.create(short_name='org1', name='Organization 1'),
        Organization.objects.create(short_name='org2', name='Organization 2'),
    ]
    platforms = [
        Platform.objects.create(short_name='pl1', name='Platform 1'),
        Platform.objects.create(short_name='pl2', name='Platform 2'),
    ]
    metrics = [
        Metric.objects.create(short_name='m1', name='Metric 1'),
        Metric.objects.create(short_name='m2', name='Metric 2'),
    ]
    targets = [
        Title.objects.create(name='Title 1', isbn='123456789'),
        Title.objects.create(name='Title 2', issn='964326665'),
    ]
    report_types = [
        report_type_nd(1, ['dim1name'], short_name='rt1', name='Report type 1'),
        report_type_nd(2, ['dim1name', 'dim2name'], short_name='rt2', name='Report type 2'),
    ]

    dates = ['2019-12-01', '2020-01-01', '2020-02-01']
    dimension_values = [
        ['A', 'B', 'C'],
        [1999, 2000, 2001, 2002, 2003, 2004],
    ]
    values = value_generator()
    accesslogs = []
    dimension_texts = {}
    for rt in report_types:
        ib = ImportBatch.objects.create(report_type=rt)
        dim_count = rt.dimensions.count()
        dim_options = dimension_values[:dim_count]
        for i, dim in enumerate(rt.dimensions_sorted):
            for value in dimension_values[i]:
                dimension_texts[(dim.pk, value)], _ = DimensionText.objects.get_or_create(
                    dimension=dim, text=value
                )
        for rec in product(organizations, platforms, metrics, targets, dates, *dim_options):
            organization, platform, metric, target, date = rec[:5]
            dim_data = {}
            for i in range(dim_count):
                attr = f'dim{i+1}'
                value_str = rec[5 + i]
                if (rt.dimensions_sorted[i].pk, value_str) in dimension_texts:
                    # this is a remapped text value
                    value_key = dimension_texts[(rt.dimensions_sorted[i].pk, value_str)]
                    dim_data[attr] = value_key.pk
                else:
                    dim_data[attr] = value_str
            value = next(values)
            accesslogs.append(
                AccessLog(
                    report_type=rt,
                    organization=organization,
                    platform=platform,
                    metric=metric,
                    target=target,
                    date=date,
                    value=value,
                    import_batch=ib,
                    **dim_data,
                )
            )

    AccessLog.objects.bulk_create(accesslogs)
    return {
        'report_types': report_types,
        'organizations': organizations,
        'platforms': platforms,
        'metrics': metrics,
        'targets': targets,
        'dates': dates,
        'dimension_values': dimension_values,
    }
