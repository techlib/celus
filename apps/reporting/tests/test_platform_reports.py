"""
Test for reports like the Rebiun report which use platform as rows
"""

from datetime import date

import pytest
from logs.models import ImportBatch
from publications.fake_data import PlatformFactory

from reporting.logic.computation import Report


@pytest.mark.django_db
class TestPlatformReports:
    def test_report_data(self, report_data_tr_jr1):
        assert ImportBatch.objects.count() == 36, "12 months * 3 reports"

    def test_report_definition(self, report_data_tr_jr1, report_def_tr_jr1):
        report = Report.from_dict(report_def_tr_jr1)
        assert len(report.parts) == 4
        assert report.parts[0].name == "PART 1"
        assert report.parts[1].name == "PART 2"
        assert report.parts[2].name == "PART 3"
        assert report.parts[3].name == "PART 4"

    def test_report_retrieve_data(self, report_data_tr_jr1, report_def_tr_jr1):
        PlatformFactory(name="C")  # this will have no data
        report = Report.from_dict(report_def_tr_jr1)
        assert len(report.parts) == 4
        report.retrieve_data(
            organization=report_data_tr_jr1["org"],
            start_date=date(2022, 1, 1),
            end_date=date(2022, 12, 1),
        )
        # TR report
        tr_source = report.sources_by_id["tr"]
        assert tr_source.report_data_ is not None
        # platforms are sorted by name, so platform1 (name=A) is first
        pl1_pk = report_data_tr_jr1["platform1"].pk
        pl2_pk = report_data_tr_jr1["platform2"].pk
        month_cols = report.context.covered_months
        assert tr_source.report_data_.index.to_list() == [pl1_pk, pl2_pk]
        assert tr_source.report_data_.loc[pl1_pk][0] == "TR"
        assert set(tr_source.report_data_.loc[pl1_pk][month_cols]) == {
            300
        }, "value is 3*100 for all months"
        # JR1 report
        jr1_source = report.sources_by_id["jr1"]
        assert jr1_source.report_data_ is not None
        assert jr1_source.report_data_.loc[pl2_pk][0] == "JR1"
        assert set(jr1_source.report_data_.loc[pl2_pk][month_cols]) == {
            30
        }, "value is 3*10 for all months"
        # JR1GOA report
        jr1goa_source = report.sources_by_id["jr1goa"]
        assert jr1goa_source.report_data_ is not None
        assert jr1goa_source.report_data_.loc[pl2_pk][0] == "JR1GOA"
        assert set(jr1goa_source.report_data_.loc[pl2_pk][month_cols]) == set(
            range(3, 37, 3)
        ), "value is 3*month_index for each months"

    def test_stages_compute_data(self, report_data_tr_jr1, report_def_tr_jr1):
        report = Report.from_dict(report_def_tr_jr1)
        report.retrieve_data(
            organization=report_data_tr_jr1["org"],
            start_date=date(2022, 1, 1),
            end_date=date(2022, 12, 1),
        )
        pl1_pk = report_data_tr_jr1["platform1"].pk
        pl2_pk = report_data_tr_jr1["platform2"].pk
        month_cols = report.context.covered_months
        # stage 1 of report 1 does TR | (JR1-JR1GOA) operation
        stage1 = report.parts[0].stages[0]
        assert stage1.report_data_.index.to_list() == [pl1_pk, pl2_pk]
        assert stage1.report_data_.loc[pl1_pk][0] == "TR", "platform1 uses TR"
        assert stage1.report_data_.loc[pl2_pk][0] == "JR1 - JR1GOA", "platform2 uses JR1 - JR1GOA"
        assert set(stage1.report_data_.loc[pl1_pk][month_cols]) == {
            300
        }, "value is 3*100 for all months"
        assert set(stage1.report_data_.loc[pl2_pk][month_cols]) == set(
            range(0, 30, 3)
        ), "value is 3*(10-month) for each month, but cannot be negative"
        # stage 1 of part 2 only does TR | JR1 operation
        stage2 = report.parts[1].stages[0]
        assert stage2.report_data_.index.to_list() == [pl1_pk, pl2_pk]
        assert stage2.report_data_.loc[pl1_pk][0] == "TR", "platform1 uses TR"
        assert stage2.report_data_.loc[pl2_pk][0] == "JR1", "platform2 uses JR1"
        assert set(stage2.report_data_.loc[pl1_pk][month_cols]) == {
            300
        }, "value is 3*100 for all months"
        assert set(stage2.report_data_.loc[pl2_pk][month_cols]) == {
            30
        }, "value is 3*10 for all months"
        # stage 1 of part 3 tests summation of 2 reports
        stage3 = report.parts[2].stages[0]
        assert stage3.report_data_.index.to_list() == [pl1_pk, pl2_pk]
        assert stage3.report_data_.loc[pl1_pk][0] == "JR1 + GOA"
        assert stage3.report_data_.loc[pl2_pk][0] == "JR1 + GOA"
        assert set(stage3.report_data_.loc[pl1_pk][month_cols]) == {0}, "value is 0 for all months"
        assert set(stage3.report_data_.loc[pl2_pk][month_cols]) == set(
            range(33, 69, 3)
        ), "value is 3*(10+month) for each month"
        # stage 2 of part 3 only has data from TR, thus for pl1 only
        stage32 = report.parts[2].stages[1]
        assert stage32.report_data_.index.to_list() == [pl1_pk, pl2_pk]
        assert stage32.report_data_.loc[pl1_pk][0] == "TR"
        assert stage32.report_data_.loc[pl2_pk][0] == "TR"
        assert set(stage32.report_data_.loc[pl1_pk][month_cols]) == {
            300
        }, "value is 0 for all months"
        assert set(stage32.report_data_.loc[pl2_pk][month_cols]) == {0}, "no data for pl2"
        # stage 3 of part 3 merges source with previous stage
        stage33 = report.parts[2].stages[2]
        assert stage33.report_data_.index.to_list() == [pl1_pk, pl2_pk]
        assert stage33.report_data_.loc[pl1_pk][0] == "TR", "platform1 uses TR"
        assert stage33.report_data_.loc[pl2_pk][0] == "JR1 + GOA", "platform2 uses prev stage"
        assert set(stage33.report_data_.loc[pl1_pk][month_cols]) == {
            300
        }, "value is 3*100 for all months"
        assert set(stage33.report_data_.loc[pl2_pk][month_cols]) == set(
            range(33, 69, 3)
        ), "value is 3*(10+month) for each month"

    def test_report_output(self, report_data_tr_jr1, report_def_tr_jr1):
        PlatformFactory()  # this will have no data
        report = Report.from_dict(report_def_tr_jr1)
        assert len(report.parts) == 4
        report.retrieve_data(
            organization=report_data_tr_jr1["org"],
            start_date=date(2022, 1, 1),
            end_date=date(2022, 12, 1),
        )
        output = report.get_output()
        assert len(output) == 4, "4 parts"
        # check the first part
        part1 = output["PART 1"]
        assert len(part1["stages"]) == 1, "1 stage"
        stage1 = part1["stages"][0]["data"]
        assert len(stage1) == 2, "2 platforms - only those connected to the org"
        assert {rec.primary_pk for rec in stage1} == {
            report_data_tr_jr1["platform1"].pk,
            report_data_tr_jr1["platform2"].pk,
        }
        pl1_rec = [rec for rec in stage1 if rec.primary_pk == report_data_tr_jr1["platform1"].pk][0]
        assert pl1_rec.source_name == "TR"
        pl2_rec = [rec for rec in stage1 if rec.primary_pk == report_data_tr_jr1["platform2"].pk][0]
        assert pl2_rec.source_name == "JR1 - JR1GOA"
        # check that the data is correct
        assert set(pl1_rec.monthly_data.values()) == {300}, "value is 3*100 for all months"
        assert set(pl2_rec.monthly_data.values()) == set(
            range(0, 30, 3)
        ), "value is 3*(10-month) for each month, but cannot be negative"
        assert part1["stages"][0]["used_data_sources"] == ["tr", "jr1", "jr1goa"]
        # check the second part - the data for JR1 do not have GOA subtracted
        part2 = output["PART 2"]
        assert len(part2["stages"]) == 1, "1 stage"
        stage2 = part2["stages"][0]["data"]
        pl1_rec = [rec for rec in stage2 if rec.primary_pk == report_data_tr_jr1["platform1"].pk][0]
        pl2_rec = [rec for rec in stage2 if rec.primary_pk == report_data_tr_jr1["platform2"].pk][0]
        # check that the data is correct
        assert set(pl1_rec.monthly_data.values()) == {300}, "value is 3*100 for all months"
        assert set(pl2_rec.monthly_data.values()) == {30}, "value is 3*10 for all months"
        assert part2["stages"][0]["used_data_sources"] == ["tr", "jr1"]
        # check the third part - used data sources
        assert output["PART 3"]["stages"][0]["used_data_sources"] == ["jr1", "jr1goa"]
        assert output["PART 3"]["stages"][1]["used_data_sources"] == ["tr"]
        assert output["PART 3"]["stages"][2]["used_data_sources"] == ["tr", "jr1", "jr1goa"]
        # check the fourth part - used data sources
        assert output["PART 4"]["stages"][0]["used_data_sources"] == ["jr1"]
        assert output["PART 4"]["stages"][1]["used_data_sources"] == ["tr"]
        assert output["PART 4"]["stages"][2]["used_data_sources"] == ["tr", "jr1"]
