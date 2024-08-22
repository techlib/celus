import pytest
from django.core.management import call_command
from publications.tests.conftest import interest_rt  # noqa - fixture

from logs.models import ReportMaterializationSpec, ReportType


@pytest.mark.django_db
class TestCheckMaterializedReportTypes:
    @pytest.fixture(autouse=True)
    def setup(self, interest_rt):
        assert ReportType.objects.count() == 1, "just interest"
        call_command("check_report_type_dimensions", "--fix-it")
        assert ReportType.objects.count() > 1, "all counter report types added"

    def test_check_materialized_report_types_empty_db(self):
        assert ReportMaterializationSpec.objects.count() == 0
        call_command("check_materialized_report_types", "--fix-it")
        assert ReportMaterializationSpec.objects.count() == 4
        call_command("check_materialized_report_types", "--fix-it")
        assert ReportMaterializationSpec.objects.count() == 4, "no duplicates"

    def test_check_materialized_report_types_preexisting_specs(self):
        """
        Check that if a spec exists, but does not belong to a report type, it will be used
        """
        tr = ReportType.objects.get(short_name="TR")
        # a spec that matches what would be created
        spec_matching = ReportMaterializationSpec.objects.create(
            base_report_type=tr,
            name="TR without item and title",
            keep_item=False,
            keep_target=False,
        )
        # extra spec that does not match and should be deleted
        spec_extra = ReportMaterializationSpec.objects.create(
            base_report_type=tr, name="TR without item", keep_item=False
        )
        assert not hasattr(
            spec_matching, "reporttype"
        ), "convoluted way to check that reporttype is not set"
        call_command("check_materialized_report_types", "--fix-it")
        assert ReportMaterializationSpec.objects.count() == 4
        spec_matching.refresh_from_db()
        assert hasattr(
            spec_matching, "reporttype"
        ), "convoluted way to check that reporttype is set"
        assert spec_matching.reporttype is not None
        # the extra spec should have been deleted
        assert ReportMaterializationSpec.objects.filter(pk=spec_extra.pk).count() == 0

    def test_check_materialized_report_types_preexisting_report_types(self):
        """
        Test that when a report type already exists with the matching name, the script will
        gracefully skip it
        """
        rt = ReportType.objects.create(short_name="Interest without title and item")
        # the test is that the script will not raise an error
        call_command("check_materialized_report_types", "--fix-it")
        assert ReportMaterializationSpec.objects.count() == 4
        assert ReportType.objects.filter(pk=rt.pk).count() == 1, "rt still exists"
