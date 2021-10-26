import os

import pytest

from nigiri.client import Sushi5Client


class TestProxy:
    @pytest.mark.parametrize(
        ['proxy', 'result'],
        [
            (
                'foo.bar.baz,proxy.com,1234,username,pwd',
                {'proxy': 'proxy.com', 'port': 1234, 'username': 'username', 'password': 'pwd'},
            ),
            ('foo.bar.baz,proxy.com,1234,,x', None),
            ('foo.bar.baz,proxy.com,abc,username,', None),
            ('foo.bar.baz,proxy.com,1234', None),
            ('whatever', None),
        ],
    )
    def test_proxy_definition(self, proxy, result):
        os.environ['SUSHI_PROXIES'] = proxy
        client = Sushi5Client('https://foo.bar.baz/sushi/', 'a', 'b')
        assert client._get_proxy('https://foo.bar.baz/sushi/') == result
