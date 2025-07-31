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
        assert ReportMaterializationSpec.objects.count() == 5
        call_command("check_materialized_report_types", "--fix-it")
        assert ReportMaterializationSpec.objects.count() == 5, "no duplicates"

    @pytest.mark.parametrize(
        "config_value",
        [
            "Interest without title and item;C5 TR without title;C51 TR without title",
            "C5 TR without title;C51 TR without title",
            "Interest without title and item",
            "",
        ],
    )
    def test_check_materialized_report_types_with_settings(self, config_value, settings):
        settings.ACTIVE_MATERIALIZED_REPORTS = config_value
        assert ReportMaterializationSpec.objects.count() == 0
        call_command("check_materialized_report_types", "--fix-it")
        assert ReportMaterializationSpec.objects.count() == (
            (config_value.count(";") + 1) if config_value else 0
        )

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
        assert not hasattr(spec_matching, "reporttype"), (
            "convoluted way to check that reporttype is not set"
        )
        call_command("check_materialized_report_types", "--fix-it")
        assert ReportMaterializationSpec.objects.count() == 6, "nothing deleted, no --delete-extra"
        call_command("check_materialized_report_types", "--fix-it", "--delete-extra")
        assert ReportMaterializationSpec.objects.count() == 5, "extra spec deleted"
        spec_matching.refresh_from_db()
        assert hasattr(spec_matching, "reporttype"), (
            "convoluted way to check that reporttype is set"
        )
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
        assert ReportMaterializationSpec.objects.count() == 5
        assert ReportType.objects.filter(pk=rt.pk).count() == 1, "rt still exists"

    @pytest.mark.parametrize("delete_extra", [True, False])
    def test_check_materialized_report_types_preexisting_report_types_delete(self, delete_extra):
        """
        Test that when an extra report type already exists, the script will delete it or not,
        depending on the flag
        """
        tr = ReportType.objects.get(short_name="TR")
        spec = ReportMaterializationSpec.objects.create(
            base_report_type=tr, name="TR without dim1", keep_item=False, keep_dim1=False
        )
        mat_rt = ReportType.objects.create(short_name="TR without dim1", materialization_spec=spec)
        assert ReportType.objects.filter(materialization_spec__isnull=False).count() == 1
        args = ["--fix-it"]
        if delete_extra:
            args.append("--delete-extra")
        call_command("check_materialized_report_types", *args)
        assert ReportType.objects.filter(materialization_spec__isnull=False).count() == (
            5 if delete_extra else 6
        )
        assert ReportType.objects.filter(pk=mat_rt.pk).exists() == (not delete_extra)
