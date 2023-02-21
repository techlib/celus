"""
Test for reports like the Rebiun report which use platform as rows
"""
from datetime import date

import pytest
from logs.models import ImportBatch
from reporting.logic.computation import Report

from test_fixtures.entities.platforms import PlatformFactory


@pytest.mark.django_db
class TestPlatformReports:
    def test_report_data(self, report_data_tr_jr1):
        assert ImportBatch.objects.count() == 36, '12 months * 3 reports'

    def test_report_definition(self, report_data_tr_jr1, report_def_tr_jr1):
        report = Report.from_definition(report_def_tr_jr1)
        assert len(report.parts) == 2
        assert report.parts[0].name == "PART 1"
        assert report.parts[1].name == "PART 2"

    def test_report_get_data(self, report_data_tr_jr1, report_def_tr_jr1):
        PlatformFactory()  # this will have no data
        report = Report.from_definition(report_def_tr_jr1)
        assert len(report.parts) == 2
        report.retrieve_data(
            organization=report_data_tr_jr1["org"],
            start_date=date(2022, 1, 1),
            end_date=date(2022, 12, 1),
        )
        output = list(report.gen_output())
        assert len(output) == 2, '2 parts'
        # check the first part
        part, data = output[0]
        assert len(data) == 2, '2 platforms - only those connected to the org'
        assert {rec.primary_pk for rec in data} == {
            report_data_tr_jr1["platform1"].pk,
            report_data_tr_jr1["platform2"].pk,
        }
        tr_rec = [rec for rec in data if rec.primary_pk == report_data_tr_jr1["platform1"].pk][0]
        assert tr_rec.used_report_type == report_data_tr_jr1["rt_tr"]
        jr1_rec = [rec for rec in data if rec.primary_pk == report_data_tr_jr1["platform2"].pk][0]
        assert jr1_rec.used_report_type == report_data_tr_jr1["rt_jr1"]
        # check that the data is correct
        assert set(tr_rec.monthly_data.values()) == {300}, 'value is 3*100 for all months'
        assert set(jr1_rec.monthly_data.values()) == {15}, 'value is 3*(10-5) for all months'
        # check the second part - the data for JR1 do not have GOA subtracted
        part, data = output[1]
        tr_rec = [rec for rec in data if rec.primary_pk == report_data_tr_jr1["platform1"].pk][0]
        jr1_rec = [rec for rec in data if rec.primary_pk == report_data_tr_jr1["platform2"].pk][0]
        # check that the data is correct
        assert set(tr_rec.monthly_data.values()) == {300}, 'value is 3*100 for all months'
        assert set(jr1_rec.monthly_data.values()) == {30}, 'value is 3*10 for all months'
