import pytest
from core.models import User
from django.db import DatabaseError
from logs.logic.reporting.filters import ExplicitDimensionFilter, ForeignKeyDimensionFilter
from logs.logic.reporting.slicer import FlexibleDataSlicer
from logs.models import Dimension, DimensionText, FlexibleReport, ReportType, ReportTypeToDimension
from organizations.tests.conftest import organizations  # noqa

from test_fixtures.entities.logs import MetricFactory
from test_fixtures.scenarios.basic import data_sources, report_types


@pytest.mark.django_db
class TestReportType:

    """
    Tests basic methods of the TestReport model
    """

    def test_dimension_short_names_ordering(self):
        report = ReportType.objects.create(short_name='A', name='AA')
        dims = ['dim1', 'dim2', 'dim3']
        for i, dim in enumerate(dims):
            dim_obj = Dimension.objects.create(short_name=dim, name=dim)
            ReportTypeToDimension.objects.create(dimension=dim_obj, report_type=report, position=i)
        assert report.dimension_short_names == dims
        # now the other way around
        report2 = ReportType.objects.create(short_name='B', name='BB')
        for i, dim in enumerate(dims):
            dim_obj = Dimension.objects.create(short_name=dim + 'x', name=dim + 'x')
            ReportTypeToDimension.objects.create(
                dimension=dim_obj, report_type=report2, position=5 - i
            )
        assert report2.dimension_short_names == ['dim3x', 'dim2x', 'dim1x']


@pytest.mark.django_db
class TestFlexibleReport:
    @pytest.mark.parametrize(
        ['owner', 'owner_organization', 'ok'],
        [
            (True, True, False),  # cannot set both owner and owner_organization
            (True, False, True),  # all other options are allowed
            (False, True, True),
            (False, False, True),
        ],
    )
    def test_constraints(self, owner, owner_organization, ok, organizations):
        org = organizations[0]
        params = {}
        if owner:
            params['owner'] = User.objects.create(username='aaa')
        if owner_organization:
            params['owner_organization'] = org
        if ok:
            FlexibleReport.objects.create(**params)
        else:
            with pytest.raises(DatabaseError):
                FlexibleReport.objects.create(**params)

    def test_config_serialization_report_type(self, flexible_slicer_test_data):
        slicer = FlexibleDataSlicer(primary_dimension='platform')
        report_type = flexible_slicer_test_data['report_types'][0]
        slicer.add_filter(ForeignKeyDimensionFilter('report_type', report_type))
        slicer.add_group_by('metric')
        fr = FlexibleReport.create_from_slicer(slicer)
        assert fr.report_config['filters'][0]['dimension'] == 'report_type'
        assert fr.report_config['filters'][0]['values'] == [report_type.short_name]

    def test_config_serialization_metric(self, flexible_slicer_test_data):
        slicer = FlexibleDataSlicer(primary_dimension='platform')
        metric = flexible_slicer_test_data['metrics'][0]
        slicer.add_filter(ForeignKeyDimensionFilter('metric', metric))
        slicer.add_group_by('metric')
        fr = FlexibleReport.create_from_slicer(slicer)
        assert fr.report_config['filters'][0]['dimension'] == 'metric'
        assert fr.report_config['filters'][0]['values'] == [metric.short_name]

    def test_config_serialization_explicit_dim(self, flexible_slicer_test_data):
        slicer = FlexibleDataSlicer(primary_dimension='platform')
        dt1 = DimensionText.objects.get(text='A', dimension__short_name='dim1name')
        dt2 = DimensionText.objects.get(text='YY', dimension__short_name='dim2name')
        slicer.add_filter(ExplicitDimensionFilter('dim1', dt1.pk))
        slicer.add_filter(ExplicitDimensionFilter('dim2', dt2.pk))
        slicer.add_group_by('metric')
        fr = FlexibleReport.create_from_slicer(slicer)
        assert fr.report_config['filters'][0]['dimension'] == 'dim1'
        assert fr.report_config['filters'][0]['values'] == [dt1.text]
        assert fr.report_config['filters'][1]['dimension'] == 'dim2'
        assert fr.report_config['filters'][1]['values'] == [dt2.text]

    @pytest.mark.skip(
        reason="We are disabling related functionality in the UI and will probably "
        "resolve this problem using a different approach."
    )
    def test_config_serialization_explicit_dim_int_type(self, flexible_slicer_test_data2):
        """
        Tests that serialization of explicit dimension of type integer works as expected
        """
        slicer = FlexibleDataSlicer(primary_dimension='platform')
        dt1 = DimensionText.objects.get(text='A', dimension__short_name='dim1name')
        slicer.add_filter(ExplicitDimensionFilter('dim1', dt1.pk))
        slicer.add_filter(ExplicitDimensionFilter('dim2', [1999, 2003]))
        slicer.add_group_by('metric')
        fr = FlexibleReport.create_from_slicer(slicer)
        assert fr.report_config['filters'][0]['dimension'] == 'dim1'
        assert fr.report_config['filters'][0]['values'] == [dt1.text]
        assert fr.report_config['filters'][1]['dimension'] == 'dim2'
        assert fr.report_config['filters'][1]['values'] == [1999, 2003]

    def test_config_deserialization(self, flexible_slicer_test_data):
        report_type = flexible_slicer_test_data['report_types'][1]
        metric = flexible_slicer_test_data['metrics'][0]
        dt1 = DimensionText.objects.get(text='A', dimension__short_name='dim1name')
        dt2 = DimensionText.objects.get(text='YY', dimension__short_name='dim2name')
        fr = FlexibleReport.objects.create(
            report_config={
                'filters': [
                    {'dimension': 'report_type', 'values': [report_type.short_name]},
                    {'dimension': 'metric', 'values': [metric.short_name]},
                    {'dimension': 'dim1', 'values': [dt1.text]},
                    {'dimension': 'dim2', 'values': [dt2.text]},
                ]
            }
        )
        config = fr.deserialize_slicer_config()
        assert config['filters'][0]['dimension'] == 'report_type'
        assert config['filters'][0]['values'] == [report_type.pk]
        assert config['filters'][1]['dimension'] == 'metric'
        assert config['filters'][1]['values'] == [metric.pk]
        assert config['filters'][2]['dimension'] == 'dim1'
        assert len(config['filters'][2]['values']) == 1, 'only one value for "A" is allowed'
        assert config['filters'][2]['values'] == [dt1.pk]
        assert config['filters'][3]['dimension'] == 'dim2'
        assert config['filters'][3]['values'] == [dt2.pk]

    def test_resolve_explicit_dimension(self, flexible_slicer_test_data):
        slicer = FlexibleDataSlicer(primary_dimension='platform')
        report_type = flexible_slicer_test_data['report_types'][1]
        dt1 = DimensionText.objects.get(text='A', dimension__short_name='dim1name')
        dt2 = DimensionText.objects.get(text='YY', dimension__short_name='dim2name')
        slicer.add_filter(ForeignKeyDimensionFilter('report_type', report_type))
        slicer.add_filter(ExplicitDimensionFilter('dim1', dt1.pk))
        slicer.add_filter(ExplicitDimensionFilter('dim2', dt2.pk))
        slicer.add_group_by('metric')
        fr = FlexibleReport.create_from_slicer(slicer)
        assert fr.resolve_explicit_dimension('dim1').short_name == 'dim1name'
        assert fr.resolve_explicit_dimension('dim2').short_name == 'dim2name'

    def test_used_report_types(self, flexible_slicer_test_data):
        slicer = FlexibleDataSlicer(primary_dimension='platform')
        report_type = flexible_slicer_test_data['report_types'][0]
        slicer.add_filter(ForeignKeyDimensionFilter('report_type', report_type))
        slicer.add_group_by('metric')
        fr = FlexibleReport.create_from_slicer(slicer)
        assert fr.used_report_types() == [flexible_slicer_test_data['report_types'][0]]

    # TODO: activate this test once we do remapping of order_by during save
    @pytest.mark.skip(reason="temporarily disabled because the code was switched off for demo")
    def test_config_serialization_order_by_explicit_dim(self, flexible_slicer_test_data):
        slicer = FlexibleDataSlicer(primary_dimension='platform')
        dt1 = DimensionText.objects.get(text='A', dimension__short_name='dim1name')
        slicer.add_filter(ExplicitDimensionFilter('dim1', dt1.pk))
        slicer.add_group_by('metric')
        ob_metric = flexible_slicer_test_data['metrics'][0]
        slicer.order_by = f'grp-{ob_metric.pk}'
        fr = FlexibleReport.create_from_slicer(slicer)
        assert fr.report_config['filters'][0]['dimension'] == 'dim1'
        assert fr.report_config['filters'][0]['values'] == [dt1.text]
        assert fr.report_config['order_by'] == [ob_metric.short_name]

    # TODO: activate this test once we do remapping of order_by during save
    @pytest.mark.skip(reason="temporarily disabled because the code was switched off for demo")
    def test_config_serialization_order_by_implicit_dim(self, flexible_slicer_test_data):
        slicer = FlexibleDataSlicer(primary_dimension='platform')
        dt1 = DimensionText.objects.get(text='A', dimension__short_name='dim1name')
        slicer.add_filter(ExplicitDimensionFilter('dim1', dt1.pk))
        slicer.add_group_by('metric')
        ob_metric = flexible_slicer_test_data['metrics'][0]
        slicer.order_by = f'platform'
        fr = FlexibleReport.create_from_slicer(slicer)
        assert fr.report_config['filters'][0]['dimension'] == 'dim1'
        assert fr.report_config['filters'][0]['values'] == [dt1.text]
        assert fr.report_config['order_by'] == ['platform']
