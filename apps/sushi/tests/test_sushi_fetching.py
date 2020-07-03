import re
from pathlib import Path

import pytest
import requests_mock

from logs.logic.attempt_import import import_one_sushi_attempt
from sushi.models import SushiFetchAttempt
from nigiri.exceptions import SushiException


@pytest.mark.django_db
class TestSushiFetching(object):
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
        ),
        ids=lambda x: "" if isinstance(x, str) and not x.endswith('.json') else x,
    )
    def test_c5_pr(
        self,
        report_type_nd,
        credentials,
        counter_report_type_wrap_report_type,
        path,
        download_success,
        contains_data,
        import_crashed,
        log,
    ):
        rt = report_type_nd(2, short_name='PR', name='Platform report')
        counter_rt = counter_report_type_wrap_report_type(rt, code='PR', name='Platform report')
        with requests_mock.Mocker() as m:
            with open(Path(__file__).parent / 'data/counter5' / path) as datafile:
                m.get(re.compile(f'^{credentials.url}.*'), text=datafile.read())
            attempt: SushiFetchAttempt = credentials.fetch_report(
                counter_rt, start_date='2019-04-01', end_date='2019-04-30'
            )
            assert m.called
            assert attempt.download_success is download_success
            assert attempt.contains_data is contains_data
            assert attempt.log == log

            # import the attempt and check the result
            if attempt.can_import_data:
                import_one_sushi_attempt(attempt)
                assert attempt.import_crashed is import_crashed
            else:
                with pytest.raises(ValueError):
                    import_one_sushi_attempt(attempt)
