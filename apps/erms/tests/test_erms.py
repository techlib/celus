import pytest

from erms.api import ERMS, ERMSError


def test_wrong_url():
    WRONG_URLS = ["", "afsdf", "http:/example.com"]
    for url in WRONG_URLS:
        with pytest.raises(ERMSError):
            erms = ERMS(url)

        with pytest.raises(ERMSError):
            ERMS.check_url(url)

        erms = ERMS("https://example.com")
        erms.base_url = ""  # bypass url check in __init()___
        with pytest.raises(ERMSError):
            erms.fetch_objects()

        with pytest.raises(ERMSError):
            erms.fetch_endpoint("endp/")


def test_correct_url():
    ERMS.check_url("https://erms.czechelib.cz/api/")
