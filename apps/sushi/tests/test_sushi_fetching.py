import re
from pathlib import Path

import pytest
import requests_mock
from freezegun import freeze_time
from logs.logic.attempt_import import import_one_sushi_attempt
from sushi.models import AttemptStatus, SushiFetchAttempt
from test_fixtures.entities.credentials import CredentialsFactory
from test_fixtures.scenarios.basic import (  # noqa - fixtures
    counter_report_types,
    data_sources,
    organizations,
    platforms,
    report_types,
)


@pytest.mark.django_db
class TestSushiFetching:
    @pytest.mark.parametrize(
        ('path', 'status1', 'status2', 'log', 'breaks'),
        (
            ('C5_PR_test.json', AttemptStatus.IMPORTING, AttemptStatus.SUCCESS, '', False,),
            (
                'naked_errors.json',
                AttemptStatus.DOWNLOAD_FAILED,
                AttemptStatus.DOWNLOAD_FAILED,
                'Warnings: Warning #1011: Report Queued for Processing; '
                'Warning #3060: Invalid Report Filter Value',
                False,
            ),
            (
                'naked_error.json',
                AttemptStatus.DOWNLOAD_FAILED,
                AttemptStatus.DOWNLOAD_FAILED,
                'Warnings: Warning #1011: Report Queued for Processing',
                False,
            ),
            (
                '5_TR_ProQuestEbookCentral_exception.json',
                AttemptStatus.NO_DATA,
                AttemptStatus.NO_DATA,
                'Error #3030: No Usage Available for Requested Dates.',
                False,
            ),
            (
                'error-in-root.json',
                AttemptStatus.DOWNLOAD_FAILED,
                AttemptStatus.DOWNLOAD_FAILED,
                'Error #2090: Got response code: 404 for request: https://example.com/path/path',
                False,
            ),
            ('no_data.json', AttemptStatus.NO_DATA, AttemptStatus.NO_DATA, '', False,),
            (
                'invalid-customer.json',
                AttemptStatus.DOWNLOAD_FAILED,
                AttemptStatus.DOWNLOAD_FAILED,
                'Fatal #1030: Invalid Customer Id',
                True,
            ),
        ),
        ids=lambda x: "" if isinstance(x, str) and not x.endswith('.json') else x,
    )
    def test_c5_pr(
        self, path, status1, status2, log, breaks, counter_report_types, organizations, platforms,
    ):
        credentials = CredentialsFactory(
            organization=organizations["empty"], platform=platforms["empty"], counter_version=5,
        )
        assert credentials.is_broken() is False
        with requests_mock.Mocker() as m:
            with open(Path(__file__).parent / 'data/counter5' / path) as datafile:
                m.get(re.compile(f'^{credentials.url}.*'), text=datafile.read())
            attempt: SushiFetchAttempt = credentials.fetch_report(
                counter_report_types["pr"], start_date='2019-04-01', end_date='2019-04-30'
            )
            assert m.called
            assert attempt.status == status1
            assert attempt.log == log

            # import the attempt and check the result
            if attempt.can_import_data:
                import_one_sushi_attempt(attempt)
                assert attempt.status == status2
                assert attempt.http_status_code == 200
            else:
                with pytest.raises(ValueError):
                    import_one_sushi_attempt(attempt)

        assert credentials.is_broken() == breaks

    @pytest.mark.parametrize('time', ('2020-08-01', '2020-06-15'))
    def test_c4_3030(self, counter_report_types, organizations, platforms, time):
        credentials = CredentialsFactory(
            organization=organizations["empty"], platform=platforms["empty"], counter_version=4,
        )
        credentials.counter_reports.add(counter_report_types["db1"])
        with requests_mock.Mocker() as m, freeze_time(time):
            with open(Path(__file__).parent / 'data/counter4/sushi_3030.xml') as datafile:
                m.post(re.compile(f'^{credentials.url}.*'), text=datafile.read())
            attempt: SushiFetchAttempt = credentials.fetch_report(
                counter_report_types["db1"], start_date='2020-05-01', end_date='2020-05-31'
            )
            assert m.called
            assert attempt.status == AttemptStatus.NO_DATA

    def test_c4_wrong_namespaces(self, counter_report_types, organizations, platforms):
        credentials = CredentialsFactory(
            organization=organizations["empty"], platform=platforms["empty"], counter_version=4,
        )
        credentials.counter_reports.add(counter_report_types["db1"])
        with requests_mock.Mocker() as m, freeze_time("2021-01-01"):
            with open(
                Path(__file__).parent / 'data/counter4/sushi_exception-with-extra-attrs.xml'
            ) as datafile:
                m.post(re.compile(f'^{credentials.url}.*'), text=datafile.read())
            attempt: SushiFetchAttempt = credentials.fetch_report(
                counter_report_types["db1"], start_date='2020-01-01', end_date='2020-01-31'
            )
            assert m.called
            assert attempt.status == AttemptStatus.DOWNLOAD_FAILED

    def test_c4_non_sushi_exception(self, counter_report_types, organizations, platforms):
        credentials = CredentialsFactory(
            organization=organizations["empty"], platform=platforms["empty"], counter_version=4,
        )
        credentials.counter_reports.add(counter_report_types["jr1"])
        with requests_mock.Mocker() as m, freeze_time("2021-01-01"):
            with open(
                Path(__file__).parent / 'data/counter4/4_JR1_missing_reports_tag.xml'
            ) as datafile:
                m.post(re.compile(f'^{credentials.url}.*'), text=datafile.read())
            attempt: SushiFetchAttempt = credentials.fetch_report(
                counter_report_types["jr1"], start_date='2021-10-01', end_date='2021-10-31'
            )
            assert m.called
            assert attempt.status == AttemptStatus.PARSING_FAILED
            assert "Traceback" not in attempt.log, "no raw exception traceback in the log"
            assert "report not found" in attempt.log

    @pytest.mark.parametrize('time', ('2017-04-01', '2017-02-15'))
    def test_c5_3030(self, counter_report_types, organizations, platforms, time):
        credentials = CredentialsFactory(
            organization=organizations["empty"], platform=platforms["empty"], counter_version=5,
        )
        credentials.counter_reports.add(counter_report_types["tr"])
        with requests_mock.Mocker() as m, freeze_time(time):
            with open(
                Path(__file__).parent / 'data/counter5/5_TR_ProQuestEbookCentral_exception.json'
            ) as datafile:
                m.get(re.compile(f'^{credentials.url}.*'), text=datafile.read())
            attempt: SushiFetchAttempt = credentials.fetch_report(
                counter_report_types["pr"], start_date='2017-01-01', end_date='2017-01-31'
            )
            assert m.called
            assert attempt.status == AttemptStatus.NO_DATA

    @pytest.mark.parametrize(
        ('path', 'http_status', 'error_code', 'status'),
        (
            ('naked_error_3000.json', 400, 3000, AttemptStatus.DOWNLOAD_FAILED,),
            ('naked_error_3000.json', 200, 3000, AttemptStatus.DOWNLOAD_FAILED,),
            ('no_json.txt', 400, 'non-sushi', AttemptStatus.DOWNLOAD_FAILED),
        ),
    )
    def test_c5_with_http_error_codes(
        self, path, http_status, error_code, status, counter_report_types, organizations, platforms,
    ):
        credentials = CredentialsFactory(
            organization=organizations["empty"], platform=platforms["empty"], counter_version=5,
        )
        with requests_mock.Mocker() as m:
            with open(Path(__file__).parent / 'data/counter5' / path) as datafile:
                m.get(
                    re.compile(f'^{credentials.url}.*'),
                    text=datafile.read(),
                    status_code=http_status,
                )
            attempt: SushiFetchAttempt = credentials.fetch_report(
                counter_report_types["pr"], start_date='2019-04-01', end_date='2019-04-30'
            )
            assert m.called
            assert attempt.status == status
            assert attempt.error_code == error_code
            assert attempt.http_status_code == http_status

    @pytest.mark.parametrize(
        ('path', 'error_code', 'partial'),
        (
            ('partial_data1.json', 3210, True,),
            ('partial_data2.json', 3210, True,),
            ('5_TR_with_warning.json', '', True,),
            ('data_simple.json', '', False,),
        ),
    )
    def test_c5_partial_data(
        self, path, error_code, partial, counter_report_types, organizations, platforms,
    ):
        credentials = CredentialsFactory(
            organization=organizations["empty"], platform=platforms["empty"], counter_version=5,
        )
        with requests_mock.Mocker() as m:
            with open(Path(__file__).parent / 'data/counter5' / path) as datafile:
                m.get(
                    re.compile(f'^{credentials.url}.*'), text=datafile.read(), status_code=200,
                )
            attempt: SushiFetchAttempt = credentials.fetch_report(
                counter_report_types["pr"], start_date='2019-04-01', end_date='2019-04-30'
            )
            assert m.called
            assert attempt.error_code == error_code
            assert attempt.partial_data == partial

    @pytest.mark.parametrize(
        ('path', 'import_passes'),
        (
            ('5_DR_ProQuestEbookCentral_exception.json', False,),
            ('5_TR_ProQuestEbookCentral.json', True,),
            ('5_TR_ProQuestEbookCentral_exception.json', False,),
            ('5_TR_with_warning.json', True,),
            ('C5_PR_test.json', True,),
            ('counter5_tr_test1.json', True,),
            ('data_incorrect.json', False,),
            ('data_simple.json', True,),
            ('error-in-root.json', False,),
            ('naked_error.json', False,),
            ('naked_error_3000.json', False,),
            ('naked_error_lowercase.json', False,),
            ('naked_errors.json', False,),
            ('no_data.json', False,),
            ('partial_data1.json', False,),
            ('partial_data2.json', False,),
            ('severity-missing.json', False,),
            ('severity-number.json', False,),
            ('stringified_error.json', False,),
            ('null-in-Item_ID.json', True,),
        ),
    )
    def test_c5_all_cases(
        self, path, import_passes, counter_report_types, organizations, platforms,
    ):
        """ Just test that processing of test data works as excpected """
        credentials = CredentialsFactory(
            organization=organizations["empty"], platform=platforms["empty"], counter_version=5,
        )
        with requests_mock.Mocker() as m:
            with open(Path(__file__).parent / 'data/counter5' / path) as datafile:
                m.get(
                    re.compile(f'^{credentials.url}.*'), text=datafile.read(), status_code=200,
                )
            attempt: SushiFetchAttempt = credentials.fetch_report(
                counter_report_types["pr"], start_date='2019-04-01', end_date='2019-04-30'
            )
            if import_passes:
                import_one_sushi_attempt(attempt)
            else:
                with pytest.raises(ValueError):
                    import_one_sushi_attempt(attempt)
