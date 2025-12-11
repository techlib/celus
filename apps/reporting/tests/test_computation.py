"""
Tests for computation logic, particularly the merge operation
"""

from datetime import date

import pandas as pd
import pytest
from organizations.fake_data import OrganizationFactory

from reporting.logic.computation import Report


@pytest.mark.django_db
class TestComputationMerge:
    """Test the cell-by-cell merge operation (| operator)"""

    def test_merge_cell_by_cell(self):
        """Test that merge works cell-by-cell, replacing zeros from left with right values"""
        # Create a simple report definition
        report_def = {
            "id": "test_merge_report",
            "name": "Test merge report",
            "description": "Test description",
            "dataSources": [
                {"id": "left", "reportType": "TR", "metric": "Unique_Item_Requests"},
                {"id": "right", "reportType": "JR1", "metric": "Full Text Article Requests"},
            ],
            "parts": [
                {
                    "name": "PART 1",
                    "description": "Test part",
                    "stages": [{"id": "merge", "name": "Merge", "formula": "left | right"}],
                }
            ],
        }
        report = Report.from_dict(report_def)
        org = OrganizationFactory()

        # Create a context and manually set up test data
        context = report.create_context(org, date(2022, 1, 1), date(2022, 3, 1))
        context.set_current_part("PART 1")

        # Create test dataframes with specific values
        # Left data: has some zeros that should be replaced
        # Right data: has values for all cells
        # Note: source_name is set to report_type, not the id
        left_data = pd.DataFrame(
            {
                "source_name": ["TR", "TR"],
                date(2022, 1, 1): [100, 0],  # first row has value, second is zero
                date(2022, 2, 1): [0, 200],  # first row is zero, second has value
                date(2022, 3, 1): [50, 0],  # first row has value, second is zero
            },
            index=[1, 2],
        )
        left_data["_total_"] = left_data[
            [date(2022, 1, 1), date(2022, 2, 1), date(2022, 3, 1)]
        ].sum(axis=1)

        right_data = pd.DataFrame(
            {
                "source_name": ["JR1", "JR1"],
                date(2022, 1, 1): [10, 20],
                date(2022, 2, 1): [30, 40],
                date(2022, 3, 1): [50, 60],
            },
            index=[1, 2],
        )
        right_data["_total_"] = right_data[
            [date(2022, 1, 1), date(2022, 2, 1), date(2022, 3, 1)]
        ].sum(axis=1)

        # Mock the data sources to return our test data
        left_source = report.sources_by_id["left"]
        right_source = report.sources_by_id["right"]
        left_source.report_data_ = left_data
        right_source.report_data_ = right_data

        # Perform the merge computation
        result = context.perform_computation([["left", "|", "right"]])

        # Verify results
        # Row 1: left has [100, 0, 50], right has [10, 30, 50]
        # Expected: [100, 30, 50] (keep 100, replace 0 with 30, keep 50)
        assert result.loc[1, date(2022, 1, 1)] == 100, "Non-zero left value should be kept"
        assert result.loc[1, date(2022, 2, 1)] == 30, "Zero in left should be replaced with right"
        assert result.loc[1, date(2022, 3, 1)] == 50, "Non-zero left value should be kept"
        assert result.loc[1, "_total_"] == 180, "Total should be recomputed: 100 + 30 + 50"

        # Row 2: left has [0, 200, 0], right has [20, 40, 60]
        # Expected: [20, 200, 60] (replace 0 with 20, keep 200, replace 0 with 60)
        assert result.loc[2, date(2022, 1, 1)] == 20, "Zero in left should be replaced with right"
        assert result.loc[2, date(2022, 2, 1)] == 200, "Non-zero left value should be kept"
        assert result.loc[2, date(2022, 3, 1)] == 60, "Zero in left should be replaced with right"
        assert result.loc[2, "_total_"] == 280, "Total should be recomputed: 20 + 200 + 60"

        # Verify source_name: row 1 had a zero (used right value), row 2 had zeros
        # Both should have "TR | JR1" since right values were used
        assert result.loc[1, "source_name"] == "TR | JR1", (
            "Row 1 used right value, so name should be joined"
        )
        assert result.loc[2, "source_name"] == "TR | JR1", (
            "Row 2 used right values, so name should be joined"
        )

    def test_merge_all_zeros_in_left(self):
        """Test that when left has all zeros, all values come from right"""
        report_def = {
            "id": "test_merge_report",
            "name": "Test merge report",
            "description": "Test description",
            "dataSources": [
                {"id": "left", "reportType": "TR", "metric": "Unique_Item_Requests"},
                {"id": "right", "reportType": "JR1", "metric": "Full Text Article Requests"},
            ],
            "parts": [
                {
                    "name": "PART 1",
                    "description": "Test part",
                    "stages": [{"id": "merge", "name": "Merge", "formula": "left | right"}],
                }
            ],
        }
        report = Report.from_dict(report_def)
        org = OrganizationFactory()

        context = report.create_context(org, date(2022, 1, 1), date(2022, 3, 1))
        context.set_current_part("PART 1")

        # Left data: all zeros
        left_data = pd.DataFrame(
            {
                "source_name": ["TR"],
                date(2022, 1, 1): [0],
                date(2022, 2, 1): [0],
                date(2022, 3, 1): [0],
            },
            index=[1],
        )
        left_data["_total_"] = 0

        # Right data: all have values
        right_data = pd.DataFrame(
            {
                "source_name": ["JR1"],
                date(2022, 1, 1): [10],
                date(2022, 2, 1): [20],
                date(2022, 3, 1): [30],
            },
            index=[1],
        )
        right_data["_total_"] = 60

        report.sources_by_id["left"].report_data_ = left_data
        report.sources_by_id["right"].report_data_ = right_data

        result = context.perform_computation([["left", "|", "right"]])

        # All values should come from right
        assert result.loc[1, date(2022, 1, 1)] == 10
        assert result.loc[1, date(2022, 2, 1)] == 20
        assert result.loc[1, date(2022, 3, 1)] == 30
        assert result.loc[1, "_total_"] == 60, "Total should be recomputed from merged data"
        # All left values were zero, so all data came from right -> use only right name
        assert result.loc[1, "source_name"] == "JR1"

    def test_merge_no_zeros_in_left(self):
        """Test that when left has no zeros, all values come from left"""
        report_def = {
            "id": "test_merge_report",
            "name": "Test merge report",
            "description": "Test description",
            "dataSources": [
                {"id": "left", "reportType": "TR", "metric": "Unique_Item_Requests"},
                {"id": "right", "reportType": "JR1", "metric": "Full Text Article Requests"},
            ],
            "parts": [
                {
                    "name": "PART 1",
                    "description": "Test part",
                    "stages": [{"id": "merge", "name": "Merge", "formula": "left | right"}],
                }
            ],
        }
        report = Report.from_dict(report_def)
        org = OrganizationFactory()

        context = report.create_context(org, date(2022, 1, 1), date(2022, 3, 1))
        context.set_current_part("PART 1")

        # Left data: all have values
        left_data = pd.DataFrame(
            {
                "source_name": ["TR"],
                date(2022, 1, 1): [100],
                date(2022, 2, 1): [200],
                date(2022, 3, 1): [300],
            },
            index=[1],
        )
        left_data["_total_"] = 600

        # Right data: all have values (but should be ignored)
        right_data = pd.DataFrame(
            {
                "source_name": ["JR1"],
                date(2022, 1, 1): [10],
                date(2022, 2, 1): [20],
                date(2022, 3, 1): [30],
            },
            index=[1],
        )
        right_data["_total_"] = 60

        report.sources_by_id["left"].report_data_ = left_data
        report.sources_by_id["right"].report_data_ = right_data

        result = context.perform_computation([["left", "|", "right"]])

        # All values should come from left
        assert result.loc[1, date(2022, 1, 1)] == 100
        assert result.loc[1, date(2022, 2, 1)] == 200
        assert result.loc[1, date(2022, 3, 1)] == 300
        assert result.loc[1, "_total_"] == 600, "Total should be recomputed from merged data"
        # No zeros in left data, so no right values were used -> name should remain from left
        assert result.loc[1, "source_name"] == "TR"

    def test_merge_zeros_in_both(self):
        """Test that when both left and right have zeros, source_name is not joined"""
        report_def = {
            "id": "test_merge_report",
            "name": "Test merge report",
            "description": "Test description",
            "dataSources": [
                {"id": "left", "reportType": "TR", "metric": "Unique_Item_Requests"},
                {"id": "right", "reportType": "JR1", "metric": "Full Text Article Requests"},
            ],
            "parts": [
                {
                    "name": "PART 1",
                    "description": "Test part",
                    "stages": [{"id": "merge", "name": "Merge", "formula": "left | right"}],
                }
            ],
        }
        report = Report.from_dict(report_def)
        org = OrganizationFactory()

        context = report.create_context(org, date(2022, 1, 1), date(2022, 3, 1))
        context.set_current_part("PART 1")

        # Left data: has zeros
        left_data = pd.DataFrame(
            {
                "source_name": ["TR"],
                date(2022, 1, 1): [100],
                date(2022, 2, 1): [0],  # zero in left
                date(2022, 3, 1): [50],
            },
            index=[1],
        )
        left_data["_total_"] = 150

        # Right data: also has zeros in the same places
        right_data = pd.DataFrame(
            {
                "source_name": ["JR1"],
                date(2022, 1, 1): [10],
                date(2022, 2, 1): [0],  # also zero in right
                date(2022, 3, 1): [30],
            },
            index=[1],
        )
        right_data["_total_"] = 40

        report.sources_by_id["left"].report_data_ = left_data
        report.sources_by_id["right"].report_data_ = right_data

        result = context.perform_computation([["left", "|", "right"]])

        # Values: left has [100, 0, 50], right has [10, 0, 30]
        # Expected: [100, 0, 50] (keep 100, keep 0 since right is also 0, keep 50)
        assert result.loc[1, date(2022, 1, 1)] == 100
        assert result.loc[1, date(2022, 2, 1)] == 0, "Both are zero, so zero remains"
        assert result.loc[1, date(2022, 3, 1)] == 50
        assert result.loc[1, "_total_"] == 150, "Total should be recomputed from merged data"
        # Zero in left was not replaced by non-zero from right -> name should remain from left
        assert result.loc[1, "source_name"] == "TR"

    def test_merge_mixed_zeros(self):
        """Test that source_name is joined only when zeros are actually replaced"""
        report_def = {
            "id": "test_merge_report",
            "name": "Test merge report",
            "description": "Test description",
            "dataSources": [
                {"id": "left", "reportType": "TR", "metric": "Unique_Item_Requests"},
                {"id": "right", "reportType": "JR1", "metric": "Full Text Article Requests"},
            ],
            "parts": [
                {
                    "name": "PART 1",
                    "description": "Test part",
                    "stages": [{"id": "merge", "name": "Merge", "formula": "left | right"}],
                }
            ],
        }
        report = Report.from_dict(report_def)
        org = OrganizationFactory()

        context = report.create_context(org, date(2022, 1, 1), date(2022, 3, 1))
        context.set_current_part("PART 1")

        # Left data: has zeros in some places
        left_data = pd.DataFrame(
            {
                "source_name": ["TR"],
                date(2022, 1, 1): [0],  # zero, will be replaced
                date(2022, 2, 1): [0],  # zero, but right is also zero
                date(2022, 3, 1): [50],  # non-zero
            },
            index=[1],
        )
        left_data["_total_"] = 50

        # Right data: has values in some places, zeros in others
        right_data = pd.DataFrame(
            {
                "source_name": ["JR1"],
                date(2022, 1, 1): [20],  # non-zero, will replace left zero
                date(2022, 2, 1): [0],  # also zero
                date(2022, 3, 1): [30],  # non-zero, but left is also non-zero
            },
            index=[1],
        )
        right_data["_total_"] = 50

        report.sources_by_id["left"].report_data_ = left_data
        report.sources_by_id["right"].report_data_ = right_data

        result = context.perform_computation([["left", "|", "right"]])

        # Values: left has [0, 0, 50], right has [20, 0, 30]
        # Expected: [20, 0, 50] (replace 0 with 20, keep 0, keep 50)
        assert result.loc[1, date(2022, 1, 1)] == 20, "Zero replaced by non-zero from right"
        assert result.loc[1, date(2022, 2, 1)] == 0, "Both are zero, so zero remains"
        assert result.loc[1, date(2022, 3, 1)] == 50, "Left is non-zero, so keep it"
        assert result.loc[1, "_total_"] == 70, "Total should be recomputed: 20 + 0 + 50"
        # One zero was replaced by non-zero -> name should be joined
        assert result.loc[1, "source_name"] == "TR | JR1"
