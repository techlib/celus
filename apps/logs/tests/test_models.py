import pytest

from logs.models import ReportType, Dimension, ReportTypeToDimension


@pytest.mark.django_db
class TestReportType:

    """
    Tests basic methods of the TestReport model
    """

    def test_dimension_short_names_ordering(self):
        report = ReportType.objects.create(short_name='A', name='AA')
        dims = ['dim1', 'dim2', 'dim3']
        for i, dim in enumerate(dims):
            dim_obj = Dimension.objects.create(short_name=dim, name=dim, type=Dimension.TYPE_INT)
            ReportTypeToDimension.objects.create(dimension=dim_obj, report_type=report, position=i)
        assert report.dimension_short_names == dims
        # now the other way around
        report2 = ReportType.objects.create(short_name='B', name='BB')
        for i, dim in enumerate(dims):
            dim_obj = Dimension.objects.create(
                short_name=dim + 'x', name=dim + 'x', type=Dimension.TYPE_INT
            )
            ReportTypeToDimension.objects.create(
                dimension=dim_obj, report_type=report2, position=5 - i
            )
        assert report2.dimension_short_names == ['dim3x', 'dim2x', 'dim1x']
