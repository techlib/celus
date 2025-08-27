import pytest

from logs.models import FlexibleReport


@pytest.mark.django_db
class TestMigrations:
    def test_flexiblereports_0096_irm1_titles_to_items(self, migrator):
        old_state = migrator.apply_initial_migration(("logs", "0095_importbatch_record_count"))
        FlexibleReportOld = old_state.apps.get_model("logs", "FlexibleReport")
        ReportType = old_state.apps.get_model("logs", "ReportType")
        rt = ReportType.objects.create(short_name="IR_M1")
        report = FlexibleReportOld.objects.create(
            name="IRM1 titles",
            # we need to use real FlexibleReport class here because
            # the migration based class does not have the serialize_slicer_config method
            report_config=FlexibleReport.serialize_slicer_config(
                {
                    "primary_dimension": "title",
                    "filters": [{"dimension": "report_type", "values": [rt.pk]}],
                }
            ),
        )
        assert report.report_config["primary_dimension"] == "title"
        migrator.apply_tested_migration(("logs", "0096_flexiblereports_for_irm1_titles_to_items"))
        report.refresh_from_db()
        assert report.report_config["primary_dimension"] == "item"

    def test_flexiblereports_0096_irm1_items_to_titles_reversion(self, migrator):
        old_state = migrator.apply_initial_migration(
            ("logs", "0096_flexiblereports_for_irm1_titles_to_items")
        )
        FlexibleReportOld = old_state.apps.get_model("logs", "FlexibleReport")
        ReportType = old_state.apps.get_model("logs", "ReportType")
        rt = ReportType.objects.create(short_name="IR_M1")
        report = FlexibleReportOld.objects.create(
            name="IRM1 items",
            report_config=FlexibleReport.serialize_slicer_config(
                {
                    "primary_dimension": "item",
                    "filters": [{"dimension": "report_type", "values": [rt.pk]}],
                }
            ),
        )
        assert report.report_config["primary_dimension"] == "item"
        migrator.apply_tested_migration(("logs", "0095_importbatch_record_count"))
        report.refresh_from_db()
        assert report.report_config["primary_dimension"] == "title"
