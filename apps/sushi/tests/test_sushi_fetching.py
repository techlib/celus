import re
from pathlib import Path

import pytest
import requests_mock

from logs.logic.attempt_import import import_one_sushi_attempt
from logs.tests.conftest import report_type_nd
from sushi.models import SushiFetchAttempt


@pytest.mark.now
@pytest.mark.django_db
class TestSushiFetching(object):
    def test_c5_pr(self, report_type_nd, credentials, counter_report_type_wrap_report_type):
        rt = report_type_nd(2, short_name='PR', name='Platform report')
        counter_rt = counter_report_type_wrap_report_type(rt, code='PR', name='Platform report')
        with requests_mock.Mocker() as m:
            with open(Path(__file__).parent / 'data/C5_PR_test.json') as datafile:
                m.get(re.compile(f'^{credentials.url}.*'), text=datafile.read())
            attempt: SushiFetchAttempt = credentials.fetch_report(
                counter_rt, start_date='2019-04-01', end_date='2019-04-30'
            )
            assert m.called
            assert attempt.download_success
            assert attempt.contains_data
            assert attempt.log == ''
            # try to import the attempt to make the test complete
            import_one_sushi_attempt(attempt)
