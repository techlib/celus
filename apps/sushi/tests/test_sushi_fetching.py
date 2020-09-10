import re
from pathlib import Path

import pytest
import requests_mock
from freezegun import freeze_time

from logs.logic.attempt_import import import_one_sushi_attempt
from sushi.models import SushiFetchAttempt
from test_fixtures.entities.credentials import CredentialsFactory
from test_fixtures.scenarios.basic import (
    counter_report_types,
    data_sources,
    report_types,
    organizations,
    platforms,
)


@pytest.mark.django_db
class TestSushiFetching:
    @pytest.mark.parametrize(
        ('path', 'download_success', 'contains_data', 'import_crashed', 'log'),
        (
            ('C5_PR_test.json', True, True, False, ''),
            (
                'naked_errors.json',
                True,
                False,
                False,
                'Warnings: Warning #1011: Report Queued for Processing; '
                'Warning #3060: Invalid Report Filter Value',
            ),
            (
                'naked_error.json',
                True,
                False,
                False,
                'Warnings: Warning #1011: Report Queued for Processing',
            ),
            (
                '5_TR_ProQuestEbookCentral_exception.json',
                True,
                False,
                True,
                'Error #3030: No Usage Available for Requested Dates.',
            ),
            (
                'error-in-root.json',
                True,
                False,
                True,
                'Error #2090: Got response code: 404 for request: https://example.com/path/path',
            ),
            ('no_data.json', True, False, False, '',),
        ),
        ids=lambda x: "" if isinstance(x, str) and not x.endswith('.json') else x,
    )
    def test_c5_pr(
        self,
        path,
        download_success,
        contains_data,
        import_crashed,
        log,
        counter_report_types,
        organizations,
        platforms,
    ):
        credentials = CredentialsFactory(
            organization=organizations["empty"], platform=platforms["empty"], counter_version=5,
        )
        with requests_mock.Mocker() as m:
            with open(Path(__file__).parent / 'data/counter5' / path) as datafile:
                m.get(re.compile(f'^{credentials.url}.*'), text=datafile.read())
            attempt: SushiFetchAttempt = credentials.fetch_report(
                counter_report_types["pr"], start_date='2019-04-01', end_date='2019-04-30'
            )
            assert m.called
            assert attempt.download_success is download_success
            assert attempt.contains_data is contains_data
            assert attempt.log == log

            # import the attempt and check the result
            if attempt.can_import_data:
                import_one_sushi_attempt(attempt)
                assert attempt.import_crashed is import_crashed
                assert attempt.http_status_code == 200
            else:
                with pytest.raises(ValueError):
                    import_one_sushi_attempt(attempt)

    @pytest.mark.parametrize(('time', 'queued'), (('2020-08-01', False), ('2020-06-15', True),))
    def test_c4_3030(self, counter_report_types, organizations, platforms, time, queued):
        credentials = CredentialsFactory(
            organization=organizations["empty"], platform=platforms["empty"], counter_version=4,
        )
        credentials.active_counter_reports.add(counter_report_types["db1"])
        with requests_mock.Mocker() as m, freeze_time(time):
            with open(Path(__file__).parent / 'data/counter4/sushi_3030.xml') as datafile:
                m.post(re.compile(f'^{credentials.url}.*'), text=datafile.read())
            attempt: SushiFetchAttempt = credentials.fetch_report(
                counter_report_types["db1"], start_date='2020-05-01', end_date='2020-05-31'
            )
            assert m.called
            assert attempt.download_success is True
            assert attempt.contains_data is False
            assert attempt.queued is queued
            assert attempt.is_processed is not queued

    @pytest.mark.parametrize(('time', 'queued'), (('2017-04-01', False), ('2017-02-15', True),))
    def test_c5_3030(self, counter_report_types, organizations, platforms, time, queued):
        credentials = CredentialsFactory(
            organization=organizations["empty"], platform=platforms["empty"], counter_version=5,
        )
        credentials.active_counter_reports.add(counter_report_types["tr"])
        with requests_mock.Mocker() as m, freeze_time(time):
            with open(
                Path(__file__).parent / 'data/counter5/5_TR_ProQuestEbookCentral_exception.json'
            ) as datafile:
                m.get(re.compile(f'^{credentials.url}.*'), text=datafile.read())
            attempt: SushiFetchAttempt = credentials.fetch_report(
                counter_report_types["pr"], start_date='2017-01-01', end_date='2017-01-31'
            )
            assert m.called
            assert attempt.download_success is True
            assert attempt.contains_data is False
            assert attempt.queued is queued
            assert attempt.is_processed is not queued

    @pytest.mark.parametrize(
        ('path', 'http_status', 'error_code', 'download_success'),
        (
            ('naked_error_3000.json', 400, 3000, True,),
            ('naked_error_3000.json', 200, 3000, True,),
            ('no_json.txt', 400, 'non-sushi', False),
        ),
    )
    def test_c5_with_http_error_codes(
        self,
        path,
        http_status,
        error_code,
        download_success,
        counter_report_types,
        organizations,
        platforms,
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
            assert attempt.download_success is download_success
            assert attempt.error_code == error_code
            assert attempt.http_status_code == http_status
