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
        ('path', 'status1', 'status2', 'log', 'breaks', 'checksum'),
        (
            (
                'C5_PR_test.json',
                AttemptStatus.IMPORTING,
                AttemptStatus.SUCCESS,
                '',
                False,
                '9f8a4abbfdc601d9a35e0904c896d843ffd488ee2f7ac0f4cd46e2ab61e2549a',
            ),
            (
                'naked_errors.json',
                AttemptStatus.DOWNLOAD_FAILED,
                AttemptStatus.DOWNLOAD_FAILED,
                'Warnings: Warning #1011: Report Queued for Processing; '
                'Warning #3060: Invalid Report Filter Value\n\n',
                False,
                '74214e7abef5686360a1533d63e271663a502709d7790bf2bc966d781bf403d6',
            ),
            (
                'naked_error.json',
                AttemptStatus.DOWNLOAD_FAILED,
                AttemptStatus.DOWNLOAD_FAILED,
                'Warnings: Warning #1011: Report Queued for Processing\n\n',
                False,
                'f2bf80be20ec7f320482bb1e59c58f4aa203e47c5761325935955233a4a51f19',
            ),
            (
                '5_TR_ProQuestEbookCentral_exception.json',
                AttemptStatus.NO_DATA,
                AttemptStatus.NO_DATA,
                'Errors: Error #3030: No Usage Available for Requested Dates.\n\n',
                False,
                '2cff6104b7d2104724425361eeeb5868e99e46b4d663194edcd1813fa4829070',
            ),
            (
                'error-in-root.json',
                AttemptStatus.DOWNLOAD_FAILED,
                AttemptStatus.DOWNLOAD_FAILED,
                'Errors: Error #2090: Got response code: 404 for request: '
                'https://example.com/path/path\n\n',
                False,
                '121bf930d8c54b14e8b6361a68ad77d5cdb1e580133449734c5b6cce532ab81f',
            ),
            (
                'no_data.json',
                AttemptStatus.NO_DATA,
                AttemptStatus.NO_DATA,
                '',
                False,
                '18b7e642cc4e6ffee79da0b42fb824167d2aa3781757c852ec7ef1436b96bd85',
            ),
            (
                'invalid-customer.json',
                AttemptStatus.DOWNLOAD_FAILED,
                AttemptStatus.DOWNLOAD_FAILED,
                'Errors: Error #1030: Invalid Customer Id\n\n',
                True,
                '5c8cea51a470656c1ac4f89c3bf7bbc74d4ad797693e6e4834a9665963963b8c',
            ),
            (
                'code-zero.json',
                AttemptStatus.NO_DATA,
                AttemptStatus.NO_DATA,
                'Infos: Info #0: Some description\n\n',
                False,
                '4eef561dbeb38022d1f2b171fc51365d87b56f3c6b941b2ac900740d4385e363',
            ),
            (
                'no_data_3062.json',
                AttemptStatus.NO_DATA,
                AttemptStatus.NO_DATA,
                'Infos: Info #3062: Invalid ReportAttribute Value\n\n',
                False,
                '46c1b2d43465cd53df256b96ae87b770a1a8d2d3aa7837c6de024cf2ebe1502c',
            ),
            (
                'some_data_3062.json',
                AttemptStatus.IMPORTING,
                AttemptStatus.SUCCESS,
                'Infos: Info #3062: Invalid ReportAttribute Value\n\n',
                False,
                '21300b16301c0d696e6c8ea986efc14362c54ba21fd633bbdfac9bb1461470e7',
            ),
            (
                'no_data_3050.json',
                AttemptStatus.NO_DATA,
                AttemptStatus.NO_DATA,
                'Infos: Info #3050: Parameter Not Recognized in this Context\n\n',
                False,
                '38ac8db30e72f965b221004ddd9500acad6b1db0b2fda23c8c718ed45042df3c',
            ),
            (
                'some_data_3050.json',
                AttemptStatus.IMPORTING,
                AttemptStatus.SUCCESS,
                'Infos: Info #3050: Parameter Not Recognized in this Context; '
                'Info #0: In order to be consistent with chapter-only COUNTER '
                'metrics available for other publishers, the non-standard '
                'tandfeBooks:Total_Chapter_Requests metric has been included\n\n',
                False,
                'e20be08f4fd0d3a81f37aa6d0a53ee91ec2e5c55d05f8518cae5d858c0a2cb7b',
            ),
        ),
        ids=lambda x: "" if isinstance(x, str) and not x.endswith('.json') else x,
    )
    def test_c5_pr(
        self,
        path,
        status1,
        status2,
        log,
        breaks,
        counter_report_types,
        organizations,
        platforms,
        checksum,
    ):
        credentials = CredentialsFactory(
            organization=organizations["empty"], platform=platforms["empty"], counter_version=5,
        )
        assert credentials.is_broken() is False
        with requests_mock.Mocker() as m:
            with open(Path(__file__).parent / 'data/counter5' / path) as datafile:
                content = datafile.read()
                m.get(re.compile(f'^{credentials.url}.*'), text=content)
                file_size = len(content)
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

            assert attempt.checksum == checksum
            assert attempt.file_size == file_size

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
            assert (
                attempt.checksum
                == 'c5f4a28d70b72005b4e6862a62fe1fb534745c0cc3039688851e312f2622c740'
            )

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
            assert (
                attempt.checksum
                == '85e1fd64816d7bd022e38c8beec58c952db793e96d727e997802c66177f51eee'
            )

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

    @pytest.mark.parametrize(
        ('path', 'error_code', 'partial'), (('sushi_3040.xml', '3040', True,),),
    )
    def test_c4_partial_data(
        self, path, error_code, partial, counter_report_types, organizations, platforms,
    ):
        credentials = CredentialsFactory(
            organization=organizations["empty"], platform=platforms["empty"], counter_version=4,
        )
        with requests_mock.Mocker() as m:
            with open(Path(__file__).parent / 'data/counter4' / path) as datafile:
                m.post(
                    re.compile(f'^{credentials.url}.*'), text=datafile.read(), status_code=200,
                )
            attempt: SushiFetchAttempt = credentials.fetch_report(
                counter_report_types["db1"], start_date='2020-05-01', end_date='2020-05-31'
            )
            assert m.called
            assert str(attempt.error_code) == error_code
            assert attempt.partial_data == partial
            assert attempt.status == AttemptStatus.NO_DATA

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
            ('naked_error_3000.json', 400, '3000', AttemptStatus.DOWNLOAD_FAILED,),
            ('naked_error_3000.json', 200, '3000', AttemptStatus.DOWNLOAD_FAILED,),
            ('severity-wrong.json', 200, '1011', AttemptStatus.DOWNLOAD_FAILED,),
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
            ('partial_data1.json', '3210', True,),
            ('partial_data2.json', '3210', True,),
            ('partial_data3.json', '3040', True,),
            ('5_TR_with_warning.json', '3032', True,),
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
            if error_code == "3040":
                assert attempt.status == AttemptStatus.NO_DATA

    @pytest.mark.parametrize(
        ('path', 'import_passes'),
        (
            ('5_DR_ProQuestEbookCentral_exception.json', False,),
            ('5_TR_ProQuestEbookCentral.json', True,),
            ('5_TR_ProQuestEbookCentral_exception.json', False,),
            ('5_TR_with_warning.json', False,),
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
