import pytest

from logs.logic.validation import normalize_isbn, normalize_issn


class TestNormalizeISBN:
    @pytest.mark.parametrize(
        ['inp', 'expected'],
        [
            pytest.param('9780787960186', '9780787960186', id='simple match'),
            pytest.param('0787960187', '9780787960186', id='isbn10 to isbn13'),
            pytest.param(' 9780787960186 ', '9780787960186', id='whitespace removal'),
            pytest.param(' 0787960187 ', '9780787960186', id='whitespace removal with isbn10->13'),
            pytest.param('978-078796-018-6 ', '9780787960186', id='hyphen removal'),
            pytest.param('078796-018-7 ', '9780787960186', id='hyphen removal with isbn10->13'),
        ],
    )
    def test_normalize_isbn(self, inp, expected):
        assert normalize_isbn(inp) == expected


class TestNormalizeISSN:
    @pytest.mark.parametrize(
        ['inp', 'expected'],
        [
            pytest.param('1234-5676', '1234-5676', id='simple match'),
            pytest.param('1050-124x', '1050-124X', id='case normalization'),
            pytest.param('12345676', '1234-5676', id='missing hyphen'),
            pytest.param('1050124x', '1050-124X', id='missing hyphen with case normalization'),
            pytest.param('foobarbazbarfoo', 'foobarbaz', id='shortening of invalid'),
            pytest.param('ISSN=1234-5676', '1234-5676', id='finding in text'),
            pytest.param(
                'ISSN=1050124xFOO', '1050-124X', id='finding in text with case normalization'
            ),
        ],
    )
    def test_normalize_issn(self, inp, expected):
        assert normalize_issn(inp, raise_error=False) == expected
