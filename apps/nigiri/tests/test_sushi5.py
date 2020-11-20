import re
from io import BytesIO
from pathlib import Path

import pytest
import requests_mock

from nigiri.client import Sushi5Client
from nigiri.counter5 import TransportError


@pytest.mark.django_db
class TestSushi5:

    data_dir = Path('apps/nigiri/tests/data/counter5/')

    def test_successful_request(self):
        url = 'mock://foo.bar.baz/'
        url_re = re.compile(url.replace('.', r'\.') + '.*')
        content = open(self.data_dir / 'counter5_tr_test1.json', 'r').read()

        with requests_mock.Mocker() as mock:
            mock.register_uri('GET', url_re, text=content)
            client = Sushi5Client(url, 'foo')
            buffer = BytesIO()
            report = client.get_report_data('tr', '2020-01', '2020-01', output_content=buffer)
        records = list(report.fd_to_dicts(buffer)[1])
        assert len(records) == 3

    def test_request_400_with_data(self):
        url = 'mock://foo.bar.baz/'
        url_re = re.compile(url.replace('.', r'\.') + '.*')
        content = open(self.data_dir / 'naked_error_3000.json', 'r').read()

        with requests_mock.Mocker() as mock:
            mock.register_uri('GET', url_re, text=content, status_code=400)
            client = Sushi5Client(url, 'foo')
            buffer = BytesIO()
            report = client.get_report_data('tr', '2020-01', '2020-01', output_content=buffer)
        assert len(report.errors) == 1
        assert report.errors[0].code == 3000
        assert report.http_status_code == 400

    def test_request_exception_in_lowercase(self):
        url = 'mock://foo.bar.baz/'
        url_re = re.compile(url.replace('.', r'\.') + '.*')
        content = open(self.data_dir / 'naked_error_lowercase.json', 'r').read()

        with requests_mock.Mocker() as mock:
            mock.register_uri('GET', url_re, text=content, status_code=200)
            client = Sushi5Client(url, 'foo')
            buffer = BytesIO()
            report = client.get_report_data('tr', '2020-01', '2020-01', output_content=buffer)
        assert len(report.errors) == 1
        assert report.errors[0].code == 1001
        assert report.http_status_code == 200

    def test_request_400_without_data(self):
        url = 'mock://foo.bar.baz/'
        url_re = re.compile(url.replace('.', r'\.') + '.*')
        content = 'HTTP 400: Bad request'

        with requests_mock.Mocker() as mock:
            mock.register_uri('GET', url_re, text=content, status_code=400)
            client = Sushi5Client(url, 'foo')
            buffer = BytesIO()
            report = client.get_report_data('tr', '2020-01', '2020-01', output_content=buffer)
        assert len(report.errors) == 1
        error = report.errors[0]
        assert isinstance(error, TransportError)
        assert error.http_status == 400
        assert report.http_status_code == 400
