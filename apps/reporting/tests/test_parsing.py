from datetime import date

import pytest
from organizations.fake_data import OrganizationFactory
from reporting.logic.computation import Report, ReportDataSource
from reporting.logic.parsing import ReportSerializer, parse_formula
from rest_framework.exceptions import ValidationError


class TestFormulaParsing:
    @pytest.mark.parametrize(
        "formula, expected",
        [
            ("tr | (jr1 - jr1goa)", [['tr', '|', ['jr1', '-', 'jr1goa']]]),
            # operator precedence is respected
            ("tr | jr1 - jr1goa", [['tr', '|', ['jr1', '-', 'jr1goa']]]),
            ("tr", ['tr']),
            ("tr | jr1", [['tr', '|', 'jr1']]),
            ("tr + jr1", [['tr', '+', 'jr1']]),
            (
                'tr | jr1 - jr1goa | dr + pr',
                [['tr', '|', ['jr1', '-', 'jr1goa'], '|', ['dr', '+', 'pr']]],
            ),
        ],
    )
    def test_parse_formula(self, formula, expected):
        parsed = parse_formula(formula)
        assert parsed == expected


class TestReportDataSourceParsing:
    @pytest.mark.parametrize(
        ['report_def', 'is_valid'],
        [
            (
                {
                    "reportType": "TR",
                    "metric": "Unique_Item_Requests",
                    "filters": {"Access_Method": "Regular"},
                },
                True,
            ),
            (
                {"reportType": "JR1", "metric": "Full Text Article Requests", "fallbackFor": "tr"},
                True,
            ),
            (
                {
                    "reportType": "JR1GOA",
                    "metric": "Full Text Article Requests",
                    "fallbackFor": "tr",
                },
                True,
            ),
            (
                {
                    "reportType": "JR1GOA",
                    "metric": "Full Text Article Requests",
                    "fallbackFor": "tr",
                    "filters": {"Access_Method": "Regular"},
                },
                True,
            ),
            # Extra data are simply ignored
            ({"reportType": "JR1GOA", "metric": "Full Text Article Requests", "foo": "bar"}, True),
            # Incorrect format for metric
            ({"reportType": "JR1GOA", "metric": ["Full Text Article Requests"]}, False),
            # Missing required reportType
            (
                {"metric": "Full Text Article Requests", "filters": {"Access_Method": "Regular"}},
                False,
            ),
        ],
    )
    def test_report_validation(self, report_def, is_valid):
        if is_valid:
            ReportDataSource.from_dict(report_def, None)
        else:
            with pytest.raises(ValidationError):
                ReportDataSource.from_dict(report_def, None)

    @pytest.mark.parametrize(
        ['report_def', 'name', 'id', 'report_type'],
        [
            ({"reportType": "TR", "metric": "Unique_Item_Requests"}, 'TR', 'TR', 'TR'),
            ({"id": "tr", "reportType": "TR", "metric": "Unique_Item_Requests"}, 'TR', 'tr', 'TR'),
            (
                {"id": "tr", "name": "foo", "reportType": "TR", "metric": "Unique_Item_Requests"},
                'foo',
                'tr',
                'TR',
            ),
            (
                {"name": "foo", "reportType": "TR", "metric": "Unique_Item_Requests"},
                'foo',
                'foo',
                'TR',
            ),
        ],
    )
    def test_report_parsing(self, report_def, name, id, report_type):
        # we use None the report as it is not used in this test
        report = ReportDataSource.from_dict(report_def, None)
        assert report.name == name
        assert report.id == id
        assert report.report_type == report_type


class TestReportParsing:
    def test_report_serializer(self, report_def_tr_jr1):
        s = ReportSerializer(data=report_def_tr_jr1)
        assert s.is_valid(raise_exception=True)

    def test_report_from_dict(self, report_def_tr_jr1):
        report = Report.from_dict(report_def_tr_jr1)
        assert report.name == 'Test report'
        assert report.description == 'Test report description'
        assert set(report.sources_by_id.keys()) == {'tr', 'jr1', 'jr1goa'}
        assert report.sources_by_id['tr'].report_type == 'TR'
        assert report.sources_by_id['tr'].metric == 'Unique_Item_Requests'
        assert len(report.parts) == 4

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        ['report', 'is_valid'],
        [
            # 0: the report is missing name, description and other attrs
            ({}, False),
            # 1: the report is missing description and other attrs
            ({'name': 'Test report'}, False),
            # 2: this is OK
            (
                {
                    'name': 'Test report',
                    'description': 'Test report description',
                    'dataSources': [],
                    'parts': [],
                },
                True,
            ),
            # 3: data source is missing reportType
            (
                {
                    'name': 'Test report',
                    'description': 'Test report description',
                    'dataSources': [{}],
                    'parts': [],
                },
                False,
            ),
            # 4: data source is missing metric
            # (even if all metrics should be accepted, it's still required and may be None)
            (
                {
                    'name': 'Test report',
                    'description': 'Test report description',
                    'dataSources': [{'reportType': 'TR'}],
                    'parts': [],
                },
                False,
            ),
            # 5: this is OK
            (
                {
                    'name': 'Test report',
                    'description': 'Test report description',
                    'dataSources': [{'reportType': 'TR', 'metric': 'Unique_Item_Requests'}],
                    'parts': [],
                },
                True,
            ),
            # 6: data source reportType / id must be unique
            (
                {
                    'name': 'Test report',
                    'description': 'Test report description',
                    'dataSources': [
                        {'reportType': 'TR', 'metric': 'Unique_Item_Requests'},
                        {'id': 'TR', 'reportType': 'Foo', 'metric': 'Unique_Item_Requests'},
                    ],
                    'parts': [],
                },
                False,
            ),
            # 7: part is missing required attrs
            (
                {
                    'name': 'Test report',
                    'description': 'Test report description',
                    'dataSources': [{'reportType': 'TR', 'metric': 'Unique_Item_Requests'}],
                    'parts': [{}],
                },
                False,
            ),
            # 8: stages must not be empty
            (
                {
                    'name': 'Test report',
                    'description': 'Test report description',
                    'dataSources': [{'reportType': 'TR', 'metric': 'Unique_Item_Requests'}],
                    'parts': [{'name': 'Test part', 'description': 'AAA', 'stages': []}],
                },
                False,
            ),
            # 9: stage must have a formula
            (
                {
                    'name': 'Test report',
                    'description': 'Test report description',
                    'dataSources': [{'reportType': 'TR', 'metric': 'Unique_Item_Requests'}],
                    'parts': [{'name': 'Test part', 'description': 'AAA', 'stages': [{}]}],
                },
                False,
            ),
            # 10: stage must have a name
            (
                {
                    'name': 'Test report',
                    'description': 'Test report description',
                    'dataSources': [{'reportType': 'TR', 'metric': 'Unique_Item_Requests'}],
                    'parts': [
                        {'name': 'Test part', 'description': 'AAA', 'stages': [{'formula': 'tr'}]}
                    ],
                },
                False,
            ),
            # 11: this would be OK, but formula has incorrect reference
            (
                {
                    'name': 'Test report',
                    'description': 'Test report description',
                    'dataSources': [{'reportType': 'TR', 'metric': 'Unique_Item_Requests'}],
                    'parts': [
                        {
                            'name': 'Test part',
                            'description': 'AAA',
                            'stages': [{'name': 'xx', 'formula': 'tr'}],
                        }
                    ],
                },
                False,
            ),
            # 12: stage must not have the same name as a data source
            (
                {
                    'name': 'Test report',
                    'description': 'Test report description',
                    'dataSources': [{'reportType': 'TR', 'metric': 'Unique_Item_Requests'}],
                    'parts': [
                        {
                            'name': 'Test part',
                            'description': 'AAA',
                            'stages': [{'name': 'TR', 'formula': 'TR'}],
                        }
                    ],
                },
                False,
            ),
            # 13: two stages must not have the same id (by default it's the name)
            (
                {
                    'name': 'Test report',
                    'description': 'Test report description',
                    'dataSources': [{'reportType': 'TR', 'metric': 'Unique_Item_Requests'}],
                    'parts': [
                        {
                            'name': 'Test part',
                            'description': 'AAA',
                            'stages': [
                                # id is inferred from name
                                {'name': 'TR', 'formula': 'TR'},
                                # id is explicitly set
                                {'id': 'TR', 'name': 'TR2', 'formula': 'TR'},
                            ],
                        }
                    ],
                },
                False,
            ),
        ],
    )
    def test_incorrect_report_definitions(self, report, is_valid):
        if is_valid:
            report_obj = Report.from_dict(report)
            org = OrganizationFactory()
            report_obj.retrieve_data(org, date(2018, 1, 1), date(2018, 1, 31))
        else:
            with pytest.raises(ValidationError):
                Report.from_dict(report)
