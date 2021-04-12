from io import StringIO
from unittest.mock import MagicMock

import pytest

from logs.logic.queries import (
    FlexibleDataSlicer,
    SlicerConfigError,
    ForeignKeyDimensionFilter,
    ExplicitDimensionFilter,
    FlexibleDataExporter,
    DateDimensionFilter,
)
from logs.models import Metric, DimensionText, AccessLog, Dimension
from organizations.models import Organization
from publications.models import Platform


def remap_row_keys_to_short_names(row: dict, primary_dimension, dimensions: list) -> dict:
    result = {}
    for key, value in row.items():
        if key.startswith('grp-'):
            parts = key[4:].split(',')
            new_key_parts = []
            for part, dimension in zip(parts, dimensions):
                obj = dimension.objects.get(pk=int(part))
                if hasattr(obj, 'short_name'):
                    new_key_parts.append(obj.short_name)
                else:
                    new_key_parts.append(str(obj))
            new_key = '-'.join(new_key_parts)
            result[new_key] = value
        elif key == 'pk':
            new_value = primary_dimension.objects.get(pk=value).short_name
            result[key] = new_value
    return result


@pytest.mark.django_db
class TestFlexibleDataSlicerComputations:
    def test_data_generator(self, flexible_slicer_test_data):
        # the 1 + 3 bellow is 1 for report type with 1 dimension and 3 for report type with
        # 2 dimensions which contributes 4* the number of records
        assert AccessLog.objects.count() == 3 * 3 * 3 * 3 * 4 * 3 * (1 + 4)

        # # uncomment the following to get the test data in a CSV file
        # # it is useful when you want to use pivot table in a spreadsheet to check the calculations
        # # it will produce a table with primary keys for all dimensions
        # cursor = connection.cursor()
        #
        # with open('/tmp/TestFlexibleDataSlicer.csv', 'w') as out:
        #     cursor.copy_expert(
        #         "COPY (SELECT report_type_id, organization_id, platform_id, metric_id, target_id, "
        #         "date, dim1, dim2, value FROM logs_accesslog) TO stdout WITH CSV HEADER",
        #         out,
        #     )

    def test_org_sum_all(self, flexible_slicer_test_data):
        """
        Primary dimension: organization
        Group by:
        DimensionFilter:
        """
        slicer = FlexibleDataSlicer(primary_dimension='organization')
        # without any groups/columns, the result would not make much sense
        with pytest.raises(SlicerConfigError):
            slicer.get_data()

    def test_org_sum_by_platform(self, flexible_slicer_test_data):
        """
        Primary dimension: organization
        Group by: platform
        DimensionFilter:
        """
        slicer = FlexibleDataSlicer(primary_dimension='organization')
        slicer.add_group_by('platform')
        data = list(slicer.get_data())
        assert len(data) == Organization.objects.count()
        data.sort(key=lambda rec: rec['pk'])
        # the following numbers were obtained by a separate calculation in a spreadsheet pivot table
        assert [remap_row_keys_to_short_names(row, Organization, [Platform]) for row in data] == [
            {'pk': 'org1', 'pl1': 519318, 'pl2': 717606, 'pl3': 915894,},
            {'pk': 'org2', 'pl1': 1114182, 'pl2': 1312470, 'pl3': 1510758,},
            {'pk': 'org3', 'pl1': 1709046, 'pl2': 1907334, 'pl3': 2105622,},
        ]

    def test_org_sum_by_platform_filter_metric(self, flexible_slicer_test_data):
        """
        Primary dimension: organization
        Group by: platform
        DimensionFilter: metric
        """
        slicer = FlexibleDataSlicer(primary_dimension='organization')
        slicer.add_group_by('platform')
        metric = flexible_slicer_test_data['metrics'][0]
        slicer.add_filter(ForeignKeyDimensionFilter('metric', [metric.pk]))
        data = list(slicer.get_data())
        assert len(data) == Organization.objects.count()
        data.sort(key=lambda rec: rec['pk'])
        # the following numbers were obtained by a separate calculation in a spreadsheet pivot table
        assert [remap_row_keys_to_short_names(row, Organization, [Platform]) for row in data] == [
            {'pk': 'org1', 'pl1': 151074, 'pl2': 217170, 'pl3': 283266,},
            {'pk': 'org2', 'pl1': 349362, 'pl2': 415458, 'pl3': 481554,},
            {'pk': 'org3', 'pl1': 547650, 'pl2': 613746, 'pl3': 679842,},
        ]

    def test_org_sum_by_platform_filter_platform(self, flexible_slicer_test_data):
        """
        Primary dimension: organization
        Group by: platform
        DimensionFilter: platform
        """
        slicer = FlexibleDataSlicer(primary_dimension='organization')
        platforms = flexible_slicer_test_data['platforms'][1:]
        slicer.add_filter(ForeignKeyDimensionFilter('platform', platforms), add_group=True)
        data = list(slicer.get_data())
        assert len(data) == Organization.objects.count()
        data.sort(key=lambda rec: rec['pk'])
        # the following numbers were obtained by a separate calculation in a spreadsheet pivot table
        assert [remap_row_keys_to_short_names(row, Organization, [Platform]) for row in data] == [
            {'pk': 'org1', 'pl2': 717606, 'pl3': 915894,},
            {'pk': 'org2', 'pl2': 1312470, 'pl3': 1510758,},
            {'pk': 'org3', 'pl2': 1907334, 'pl3': 2105622,},
        ]

    def test_org_sum_by_platform_filter_platform_metric(self, flexible_slicer_test_data):
        """
        Primary dimension: organization
        Group by: platform
        DimensionFilter: platform, metric
        """
        slicer = FlexibleDataSlicer(primary_dimension='organization')
        platforms = flexible_slicer_test_data['platforms'][1:]
        metrics = flexible_slicer_test_data['metrics'][1:]
        slicer.add_filter(ForeignKeyDimensionFilter('platform', platforms), add_group=True)
        slicer.add_filter(ForeignKeyDimensionFilter('metric', metrics), add_group=False)
        data = list(slicer.get_data())
        assert len(data) == Organization.objects.count()
        data.sort(key=lambda rec: rec['pk'])
        # the following numbers were obtained by a separate calculation in a spreadsheet pivot table
        assert [remap_row_keys_to_short_names(row, Organization, [Platform]) for row in data] == [
            {'pk': 'org1', 'pl2': 500436, 'pl3': 632628,},
            {'pk': 'org2', 'pl2': 897012, 'pl3': 1029204,},
            {'pk': 'org3', 'pl2': 1293588, 'pl3': 1425780,},
        ]

    def test_org_sum_by_platform_filter_organization(self, flexible_slicer_test_data):
        """
        Primary dimension: organization
        Group by: platform
        DimensionFilter: organization
        """
        slicer = FlexibleDataSlicer(primary_dimension='organization')
        organizations = flexible_slicer_test_data['organizations'][1:]
        slicer.add_filter(
            ForeignKeyDimensionFilter('organization', [org.pk for org in organizations]),
            add_group=False,
        )
        slicer.add_group_by('platform')
        data = list(slicer.get_data())
        assert len(data) == len(organizations)
        data.sort(key=lambda rec: rec['pk'])
        # the following numbers were obtained by a separate calculation in a spreadsheet pivot table
        assert [remap_row_keys_to_short_names(row, Organization, [Platform]) for row in data] == [
            {'pk': 'org2', 'pl1': 1114182, 'pl2': 1312470, 'pl3': 1510758,},
            {'pk': 'org3', 'pl1': 1709046, 'pl2': 1907334, 'pl3': 2105622,},
        ]

    def test_org_sum_by_platform_filter_platform_organization(self, flexible_slicer_test_data):
        """
        Primary dimension: organization
        Group by: platform
        DimensionFilter: organization, platform
        """
        slicer = FlexibleDataSlicer(primary_dimension='organization')
        platforms = flexible_slicer_test_data['platforms'][1:]
        organizations = flexible_slicer_test_data['organizations'][1:]
        slicer.add_filter(
            ForeignKeyDimensionFilter('platform', [pl.pk for pl in platforms]), add_group=True
        )
        slicer.add_filter(
            ForeignKeyDimensionFilter('organization', [org.pk for org in organizations]),
            add_group=False,
        )
        data = list(slicer.get_data())
        assert len(data) == len(organizations)
        data.sort(key=lambda rec: rec['pk'])
        # the following numbers were obtained by a separate calculation in a spreadsheet pivot table
        assert [remap_row_keys_to_short_names(row, Organization, [Platform]) for row in data] == [
            {'pk': 'org2', 'pl2': 1312470, 'pl3': 1510758,},
            {'pk': 'org3', 'pl2': 1907334, 'pl3': 2105622,},
        ]

    def test_org_sum_by_platform_metric_filter_platform_metric(self, flexible_slicer_test_data):
        """
        Primary dimension: organization
        Group by: platform, metric
        DimensionFilter: platform, metric
        """
        slicer = FlexibleDataSlicer(primary_dimension='organization')
        platforms = flexible_slicer_test_data['platforms'][1:]
        metrics = flexible_slicer_test_data['metrics'][1:]
        slicer.add_filter(
            ForeignKeyDimensionFilter('platform', [pl.pk for pl in platforms]), add_group=True
        )
        slicer.add_filter(
            ForeignKeyDimensionFilter('metric', [met.pk for met in metrics]), add_group=True,
        )
        data = list(slicer.get_data())
        assert len(data) == Organization.objects.count()
        data.sort(key=lambda rec: rec['pk'])
        # the following numbers were obtained by a separate calculation in a spreadsheet pivot table
        assert [
            remap_row_keys_to_short_names(row, Organization, [Platform, Metric]) for row in data
        ] == [
            {'pk': 'org1', 'pl2-m2': 239202, 'pl3-m2': 305298, 'pl2-m3': 261234, 'pl3-m3': 327330},
            {'pk': 'org2', 'pl2-m2': 437490, 'pl3-m2': 503586, 'pl2-m3': 459522, 'pl3-m3': 525618},
            {'pk': 'org3', 'pl2-m2': 635778, 'pl3-m2': 701874, 'pl2-m3': 657810, 'pl3-m3': 723906},
        ]

    def test_platform_sum_by_metric_filter_dim1(self, flexible_slicer_test_data):
        """
        Primary dimension: platform
        Group by: metric
        DimensionFilter: dim1
        """
        slicer = FlexibleDataSlicer(primary_dimension='platform')
        texts = flexible_slicer_test_data['dimension_values'][0][:2]
        dim1_ids = DimensionText.objects.filter(text__in=texts).values_list('pk', flat=True)
        slicer.add_filter(ExplicitDimensionFilter('dim1', dim1_ids), add_group=False)
        slicer.add_group_by('metric')
        data = list(slicer.get_data())
        assert len(data) == Platform.objects.count()
        data.sort(key=lambda rec: rec['pk'])
        # the following numbers were obtained by a separate calculation in a spreadsheet pivot table
        assert [remap_row_keys_to_short_names(row, Platform, [Metric]) for row in data] == [
            {'pk': 'pl1', 'm1': 698112, 'm2': 742176, 'm3': 786240},
            {'pk': 'pl2', 'm1': 830304, 'm2': 874368, 'm3': 918432},
            {'pk': 'pl3', 'm1': 962496, 'm2': 1006560, 'm3': 1050624},
        ]

    def test_platform_sum_by_metric_dim1_filter_dim1(self, flexible_slicer_test_data):
        """
        Primary dimension: platform
        Group by: metric, dim1
        DimensionFilter: dim1

        This is not possible because dimensions have different meaning under different report types
        so we do not allow group by explicit dimension unless report type is fixed to exactly one
        """
        slicer = FlexibleDataSlicer(primary_dimension='platform')
        texts = flexible_slicer_test_data['dimension_values'][0][:2]
        dim1_ids = DimensionText.objects.filter(text__in=texts).values_list('pk', flat=True)
        slicer.add_filter(ExplicitDimensionFilter('dim1', dim1_ids), add_group=True)
        slicer.add_group_by('metric')
        with pytest.raises(SlicerConfigError):
            slicer.get_data()

    def test_platform_sum_by_metric_filter_dim1_rt(self, flexible_slicer_test_data):
        """
        Primary dimension: platform
        Group by: metric
        DimensionFilter: dim1, report_type
        """
        slicer = FlexibleDataSlicer(primary_dimension='platform')
        texts = flexible_slicer_test_data['dimension_values'][0][:2]
        report_type = flexible_slicer_test_data['report_types'][0]
        dim1_ids = DimensionText.objects.filter(text__in=texts).values_list('pk', flat=True)
        slicer.add_filter(ExplicitDimensionFilter('dim1', dim1_ids), add_group=False)
        slicer.add_filter(ForeignKeyDimensionFilter('report_type', report_type))
        slicer.add_group_by('metric')
        data = list(slicer.get_data())
        assert len(data) == Platform.objects.count()
        data.sort(key=lambda rec: rec['pk'])
        # the following numbers were obtained by a separate calculation in a spreadsheet pivot table
        assert [remap_row_keys_to_short_names(row, Platform, [Metric]) for row in data] == [
            {'pk': 'pl1', 'm1': 24624, 'm2': 27216, 'm3': 29808},
            {'pk': 'pl2', 'm1': 32400, 'm2': 34992, 'm3': 37584},
            {'pk': 'pl3', 'm1': 40176, 'm2': 42768, 'm3': 45360},
        ]

    def test_platform_sum_by_metric_dim1_filter_dim1_rt(self, flexible_slicer_test_data):
        """
        Primary dimension: platform
        Group by: metric, dim1
        DimensionFilter: dim1, report_type
        """
        slicer = FlexibleDataSlicer(primary_dimension='platform')
        texts = flexible_slicer_test_data['dimension_values'][0][:2]
        report_type = flexible_slicer_test_data['report_types'][0]
        dim1_ids = DimensionText.objects.filter(text__in=texts).values_list('pk', flat=True)
        slicer.add_filter(ExplicitDimensionFilter('dim1', dim1_ids), add_group=True)
        slicer.add_filter(ForeignKeyDimensionFilter('report_type', report_type))
        slicer.add_group_by('metric')
        data = list(slicer.get_data())
        assert len(data) == Platform.objects.count()
        data.sort(key=lambda rec: rec['pk'])
        # the following numbers were obtained by a separate calculation in a spreadsheet pivot table
        assert [
            remap_row_keys_to_short_names(row, Platform, [DimensionText, Metric]) for row in data
        ] == [
            {
                'pk': 'pl1',
                'A-m1': 12294,
                'A-m2': 13590,
                'A-m3': 14886,
                'B-m1': 12330,
                'B-m2': 13626,
                'B-m3': 14922,
            },
            {
                'pk': 'pl2',
                'A-m1': 16182,
                'A-m2': 17478,
                'A-m3': 18774,
                'B-m1': 16218,
                'B-m2': 17514,
                'B-m3': 18810,
            },
            {
                'pk': 'pl3',
                'A-m1': 20070,
                'A-m2': 21366,
                'A-m3': 22662,
                'B-m1': 20106,
                'B-m2': 21402,
                'B-m3': 22698,
            },
        ]


@pytest.mark.django_db
class TestFlexibleDataSlicerOther:
    def test_get_possible_dimension_values_unfiltered(self, flexible_slicer_test_data):
        slicer = FlexibleDataSlicer(primary_dimension='platform')
        metric_data = slicer.get_possible_dimension_values('metric')
        assert metric_data['count'] == Metric.objects.count()

    def test_get_possible_dimension_values_with_direct_filter(self, flexible_slicer_test_data):
        slicer = FlexibleDataSlicer(primary_dimension='platform')
        metrics = flexible_slicer_test_data['metrics'][1:]
        slicer.add_filter(ForeignKeyDimensionFilter('metric', metrics))
        metric_data = slicer.get_possible_dimension_values('metric')
        assert metric_data['count'] == len(metrics)

    def test_get_possible_dimension_values_with_indirect_filter(self, flexible_slicer_test_data):
        slicer = FlexibleDataSlicer(primary_dimension='platform')
        metrics = flexible_slicer_test_data['metrics'][1:]
        organization = flexible_slicer_test_data['organizations'][0]
        slicer.add_filter(ForeignKeyDimensionFilter('metric', metrics))
        # let's try for the complete data
        organization_data = slicer.get_possible_dimension_values('organization')
        assert (
            organization_data['count'] == Organization.objects.count()
        ), 'the data is complete so all organizations should be present'
        # let's delete all records related to one organization and the filtered organizations
        AccessLog.objects.filter(metric__in=metrics, organization=organization).delete()
        organization_data = slicer.get_possible_dimension_values('organization')
        assert (
            organization_data['count'] == Organization.objects.count() - 1
        ), 'one organization should not be present in the data anymore'

    def test_get_possible_dimension_values_with_text_filter_implicit_dim(
        self, flexible_slicer_test_data
    ):
        """
        Tests that substring filtering works for `FlexibleDataSlicer.get_possible_dimension_values`
        for implicit dimensions
        """
        slicer = FlexibleDataSlicer(primary_dimension='platform')
        metric_data = slicer.get_possible_dimension_values('metric', text_filter='2')
        assert metric_data['count'] == 1
        assert metric_data['values'][0]['metric'] == Metric.objects.get(name__icontains='2').pk

    def test_get_possible_dimension_values_with_text_filter_explicit_dim(
        self, flexible_slicer_test_data
    ):
        """
        Tests that substring filtering works for `FlexibleDataSlicer.get_possible_dimension_values`
        for explicit dimensions
        """
        slicer = FlexibleDataSlicer(primary_dimension='platform')
        report_type = flexible_slicer_test_data['report_types'][1]
        slicer.add_filter(ForeignKeyDimensionFilter('report_type', report_type.pk))
        metric_data = slicer.get_possible_dimension_values('dim1', text_filter='C')
        assert metric_data['count'] == 1
        assert metric_data['values'][0]['dim1'] == DimensionText.objects.get(text='C').pk

    def test_get_possible_dimension_values_with_list_of_pks(self, flexible_slicer_test_data):
        """
        Tests that a list of pk's for the queried dimension may be used by the slicer to limit
        output of `get_possible_dimension_values`
        """
        slicer = FlexibleDataSlicer(primary_dimension='platform')
        metrics = flexible_slicer_test_data['metrics'][1:]
        metric_data = slicer.get_possible_dimension_values('metric', pks=[m.pk for m in metrics])
        assert metric_data['count'] == 2
        assert {rec['metric'] for rec in metric_data['values']} == {m.pk for m in metrics}

    def test_get_possible_dimension_values_with_list_of_pks_explicit_dim(
        self, flexible_slicer_test_data
    ):
        """
        Tests that a list of pk's for the queried dimension may be used by the slicer to limit
        output of `get_possible_dimension_values`
        """
        slicer = FlexibleDataSlicer(primary_dimension='platform')
        report_type = flexible_slicer_test_data['report_types'][1]
        slicer.add_filter(ForeignKeyDimensionFilter('report_type', report_type.pk))
        dts = DimensionText.objects.filter(text__in=['A', 'B'], dimension__short_name='dim1name')
        metric_data = slicer.get_possible_dimension_values('dim1', pks=[dt.pk for dt in dts])
        assert metric_data['count'] == 2
        assert {rec['dim1'] for rec in metric_data['values']} == {dt.pk for dt in dts}

    def test_create_from_config(self):
        """
        Test that slicer created from config has the same params as the original slicer
        :return:
        """
        slicer = FlexibleDataSlicer(primary_dimension='platform')
        slicer.add_filter(ForeignKeyDimensionFilter('metric', [1, 2, 3]))
        slicer.add_filter(DateDimensionFilter('date', '2020-01-01', '2020-03-31'))
        slicer.add_filter(ExplicitDimensionFilter('dim1', [10, 11]))
        slicer.add_group_by('organization')
        config = slicer.config()
        new_slicer = FlexibleDataSlicer.create_from_config(config)
        assert new_slicer.primary_dimension == slicer.primary_dimension
        assert new_slicer.group_by == slicer.group_by
        assert new_slicer.order_by == slicer.order_by
        assert len(new_slicer.dimension_filters) == len(slicer.dimension_filters)
        for new_fltr, old_fltr in zip(new_slicer.dimension_filters, slicer.dimension_filters):
            assert new_fltr.config() == old_fltr.config()

    def test_computation_from_config(self, flexible_slicer_test_data):
        """
        Test that slicer created from config gives the same result as the original slicer
        :return:
        """
        slicer = FlexibleDataSlicer(primary_dimension='platform')
        texts = flexible_slicer_test_data['dimension_values'][0][:2]
        report_type = flexible_slicer_test_data['report_types'][0]
        dim1_ids = DimensionText.objects.filter(text__in=texts).values_list('pk', flat=True)
        slicer.add_filter(ExplicitDimensionFilter('dim1', dim1_ids), add_group=True)
        slicer.add_filter(ForeignKeyDimensionFilter('report_type', report_type))
        slicer.add_group_by('metric')
        data = list(slicer.get_data())
        new_slicer = FlexibleDataSlicer.create_from_config(slicer.config())
        assert data == list(new_slicer.get_data())


@pytest.mark.django_db
class TestFlexibleDataExporter:
    def test_org_sum_by_platform(self, flexible_slicer_test_data):
        """
        Primary dimension: organization
        Group by: platform
        DimensionFilter:
        """
        slicer = FlexibleDataSlicer(primary_dimension='organization')
        slicer.add_group_by('platform')
        exporter = FlexibleDataExporter(slicer)
        out = StringIO()
        exporter.stream_data_to_sink(out)
        output = out.getvalue()
        assert len(output.splitlines()) == Organization.objects.count() + 1
        assert output.splitlines() == [
            'organization,Platform 1,Platform 2,Platform 3',
            'Organization 1,519318,717606,915894',
            'Organization 2,1114182,1312470,1510758',
            'Organization 3,1709046,1907334,2105622',
        ]

    def test_platform_sum_by_metric_dim1_filter_dim1_rt(self, flexible_slicer_test_data):
        """
        Primary dimension: platform
        Group by: metric, dim1
        DimensionFilter: dim1, report_type
        """
        slicer = FlexibleDataSlicer(primary_dimension='platform')
        texts = flexible_slicer_test_data['dimension_values'][0][:2]
        report_type = flexible_slicer_test_data['report_types'][0]
        dim1_ids = DimensionText.objects.filter(text__in=texts).values_list('pk', flat=True)
        slicer.add_filter(ExplicitDimensionFilter('dim1', dim1_ids), add_group=True)
        slicer.add_filter(ForeignKeyDimensionFilter('report_type', report_type))
        slicer.add_group_by('metric')
        exporter = FlexibleDataExporter(slicer)
        out = StringIO()
        exporter.stream_data_to_sink(out)
        output = out.getvalue()
        assert output.splitlines() == [
            'platform,A / Metric 1,A / Metric 2,A / Metric 3,B / Metric 1,B / Metric 2,B / Metric 3',
            'Platform 1,12294,13590,14886,12330,13626,14922',
            'Platform 2,16182,17478,18774,16218,17514,18810',
            'Platform 3,20070,21366,22662,20106,21402,22698',
        ]

    def test_platform_sum_by_date_filter_rt(self, flexible_slicer_test_data):
        """
        Primary dimension: platform
        Group by: date
        DimensionFilter: report_type
        """
        slicer = FlexibleDataSlicer(primary_dimension='platform')
        report_type = flexible_slicer_test_data['report_types'][0]
        slicer.add_filter(ForeignKeyDimensionFilter('report_type', report_type))
        slicer.add_group_by('date')
        exporter = FlexibleDataExporter(slicer)
        out = StringIO()
        exporter.stream_data_to_sink(out)
        output = out.getvalue()
        assert output.splitlines() == [
            'platform,2019-12-01,2020-01-01,2020-02-01,2020-03-01',
            'Platform 1,30294,30537,30780,31023',
            'Platform 2,39042,39285,39528,39771',
            'Platform 3,47790,48033,48276,48519',
        ]

    def test_platform_sum_by_date__year_filter_rt(self, flexible_slicer_test_data):
        """
        Primary dimension: platform
        Group by: date__year
        DimensionFilter: report_type
        """
        slicer = FlexibleDataSlicer(primary_dimension='platform')
        report_type = flexible_slicer_test_data['report_types'][0]
        slicer.add_filter(ForeignKeyDimensionFilter('report_type', report_type))
        slicer.add_group_by('date__year')
        exporter = FlexibleDataExporter(slicer)
        out = StringIO()
        exporter.stream_data_to_sink(out)
        output = out.getvalue()
        assert output.splitlines() == [
            'platform,2019,2020',
            'Platform 1,30294,92340',
            'Platform 2,39042,118584',
            'Platform 3,47790,144828',
        ]

    def test_platform_sum_by_date__year_filter_rt_with_monitor(self, flexible_slicer_test_data):
        """
        Primary dimension: platform
        Group by: date__year
        DimensionFilter: report_type

        uses monitor function
        """
        slicer = FlexibleDataSlicer(primary_dimension='platform')
        report_type = flexible_slicer_test_data['report_types'][0]
        slicer.add_filter(ForeignKeyDimensionFilter('report_type', report_type))
        slicer.add_group_by('date__year')
        exporter = FlexibleDataExporter(slicer)
        out = StringIO()
        monitor = MagicMock()
        exporter.stream_data_to_sink(out, progress_monitor=monitor)
        assert monitor.call_count == 2  # once at start, once at the end
        monitor.assert_called_with(3, 3)

    def test_platform_sum_by_date__year_filter_date(self, flexible_slicer_test_data):
        """
        Primary dimension: platform
        Group by: date__year
        DimensionFilter: date
        """
        slicer = FlexibleDataSlicer(primary_dimension='platform')
        report_type = flexible_slicer_test_data['report_types'][0]
        slicer.add_filter(ForeignKeyDimensionFilter('report_type', report_type))
        slicer.add_filter(DateDimensionFilter('date', '2020-01-01', '2020-03-31'))
        slicer.add_group_by('date__year')
        exporter = FlexibleDataExporter(slicer)
        out = StringIO()
        exporter.stream_data_to_sink(out)
        output = out.getvalue()
        assert len(output.splitlines()) == 4
        assert len(output.splitlines()[0].split(',')) == 2, 'only two columns'
        assert output.splitlines()[0].split(',')[1] == "2020", 'second column is "2020"'

    def test_year_by_metric(self, flexible_slicer_test_data):
        """
        Primary dimension: date__year
        Group by: metric
        DimensionFilter: report_type
        """
        slicer = FlexibleDataSlicer(primary_dimension='date__year')
        report_type = flexible_slicer_test_data['report_types'][0]
        slicer.add_filter(ForeignKeyDimensionFilter('report_type', report_type))
        slicer.add_group_by('metric')
        slicer.order_by = ['date__year']
        exporter = FlexibleDataExporter(slicer)
        out = StringIO()
        exporter.stream_data_to_sink(out)
        output = out.getvalue()
        assert len(output.splitlines()) == 3
        assert len(output.splitlines()[0].split(',')) == 4, 'three metrics and primary dim'
        assert output.splitlines()[1].split(',')[0] == "2019", 'first row starts with year 2019'

    def test_explicit_dim_by_metric(self, flexible_slicer_test_data):
        """
        Primary dimension: dim1
        Group by: metric
        DimensionFilter: report_type
        """
        slicer = FlexibleDataSlicer(primary_dimension='dim1')
        report_type = flexible_slicer_test_data['report_types'][0]
        slicer.add_filter(ForeignKeyDimensionFilter('report_type', report_type))
        slicer.add_group_by('metric')
        slicer.order_by = ['dim1']
        exporter = FlexibleDataExporter(slicer)
        out = StringIO()
        exporter.stream_data_to_sink(out)
        output = out.getvalue()
        assert len(output.splitlines()) == 4, "3 dim values + header"
        assert len(output.splitlines()[0].split(',')) == 4, 'three metrics and primary dim'
        assert output.splitlines()[1].split(',')[0] == "A", 'first row starts with "A"'

    def test_explicit_dim_without_remap_by_metric(self, flexible_slicer_test_data):
        """
        Primary dimension: dim1 without remap
        Group by: metric
        DimensionFilter: report_type
        """
        # the simplest way how to make a dimension not-remapping is to change its definition
        # and treat the references that are in accesslogs as actual values
        dim1 = Dimension.objects.get(short_name='dim1name')
        dim1.type = Dimension.TYPE_INT
        dim1.save()
        # let's continue
        slicer = FlexibleDataSlicer(primary_dimension='dim1')
        report_type = flexible_slicer_test_data['report_types'][0]
        slicer.add_filter(ForeignKeyDimensionFilter('report_type', report_type))
        slicer.add_group_by('metric')
        slicer.order_by = ['dim1']
        exporter = FlexibleDataExporter(slicer)
        out = StringIO()
        exporter.stream_data_to_sink(out)
        output = out.getvalue()
        assert len(output.splitlines()) == 4, "3 dim values + header"
        assert len(output.splitlines()[0].split(',')) == 4, 'three metrics and primary dim'
        assert output.splitlines()[1].split(',')[0] == str(
            DimensionText.objects.get(text='A', dimension=dim1).pk
        ), 'first row starts with the primary key of "A"'

    def test_platform_by_explicit_dim_without_remap(self, flexible_slicer_test_data):
        """
        Primary dimension: platform
        Group by: dim1 without remap
        DimensionFilter: report_type
        """
        # the simplest way how to make a dimension not-remapping is to change its definition
        # and treat the references that are in accesslogs as actual values
        dim1 = Dimension.objects.get(short_name='dim1name')
        dim1.type = Dimension.TYPE_INT
        dim1.save()
        # let's continue
        slicer = FlexibleDataSlicer(primary_dimension='platform')
        report_type = flexible_slicer_test_data['report_types'][0]
        slicer.add_filter(ForeignKeyDimensionFilter('report_type', report_type))
        slicer.add_group_by('dim1')
        exporter = FlexibleDataExporter(slicer)
        out = StringIO()
        exporter.stream_data_to_sink(out)
        output = out.getvalue()
        assert len(output.splitlines()) == 4, "3 dim values + header"
        assert len(output.splitlines()[0].split(',')) == 4, 'three platforms and primary dim'
        row_names = set(output.splitlines()[0].split(','))
        text_pks = map(
            str, DimensionText.objects.filter(dimension=dim1).values_list('pk', flat=True)
        )
        assert row_names == {'platform', *text_pks}

    def test_org_sum_by_platform_with_org_extra_filter(self, flexible_slicer_test_data):
        """
        Primary dimension: organization
        Group by: platform
        DimensionFilter:
        Extra filter: organization (simulates user with limited org access)
        """
        slicer = FlexibleDataSlicer(primary_dimension='organization')
        slicer.add_group_by('platform')
        slicer.add_extra_organization_filter([flexible_slicer_test_data['organizations'][1].pk])
        exporter = FlexibleDataExporter(slicer)
        out = StringIO()
        exporter.stream_data_to_sink(out)
        output = out.getvalue()
        assert len(output.splitlines()) == 2
        assert output.splitlines() == [
            'organization,Platform 1,Platform 2,Platform 3',
            'Organization 2,1114182,1312470,1510758',
        ]
