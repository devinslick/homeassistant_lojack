import types
from datetime import datetime, timedelta

from custom_components.lojack.__init__ import LoJackDataUpdateCoordinator


class FakeError(Exception):
    def __init__(self, headers=None, response=None, status=None):
        super().__init__("fake")
        self.headers = headers
        self.response = response
        self.status = status


def test_extract_retry_after_seconds():
    err = FakeError(headers={"Retry-After": "10"})
    coord = object.__new__(LoJackDataUpdateCoordinator)
    # method does not require initialized instance attributes for this test
    secs = coord._extract_retry_after(err)
    assert secs == 10


def test_extract_retry_after_from_response_headers():
    resp = types.SimpleNamespace(headers={"Retry-After": "20"})
    err = FakeError(response=resp)
    coord = object.__new__(LoJackDataUpdateCoordinator)
    secs = coord._extract_retry_after(err)
    assert secs == 20
