import json
from pathlib import Path

import pytest

from dpe_pipeline.client import AdemeApiError, AdemeDpeClient
from dpe_pipeline.config import DATASETS

FIXTURES = Path(__file__).parent / "fixtures"


class FakeResponse:
    def __init__(self, payload, status_code=200, headers=None):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}
        self.text = json.dumps(payload) if payload is not None else ""

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    """Replays a scripted sequence of responses, one per call to .get()."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.headers = {}
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params))
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def load_fixture(name):
    return json.loads((FIXTURES / name).read_text())


def test_iter_lines_follows_next_cursor_until_exhausted():
    session = FakeSession(
        [
            FakeResponse(load_fixture("lines_page1.json")),
            FakeResponse(load_fixture("lines_page2.json")),
        ]
    )
    client = AdemeDpeClient(DATASETS["existant"], session=session, max_retries=1)

    records = list(client.iter_lines(page_size=2))

    assert [r["N°DPE"] for r in records] == ["2400E1234567A", "2400E1234567B", "2400E1234567C"]
    assert len(session.calls) == 2
    # First call carries our params; the second call follows the "next" URL verbatim.
    assert session.calls[0][1]["size"] == 2
    assert session.calls[1][1] is None


def test_get_retries_on_5xx_then_succeeds(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    session = FakeSession(
        [
            FakeResponse({"error": "boom"}, status_code=503),
            FakeResponse({"results": [], "next": None}),
        ]
    )
    client = AdemeDpeClient(DATASETS["existant"], session=session, max_retries=3)

    records = list(client.iter_lines())

    assert records == []
    assert len(session.calls) == 2


def test_get_gives_up_after_max_retries(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    session = FakeSession([FakeResponse({}, status_code=500) for _ in range(3)])
    client = AdemeDpeClient(DATASETS["existant"], session=session, max_retries=3)

    with pytest.raises(AdemeApiError):
        list(client.iter_lines())


def test_get_respects_retry_after_on_429(monkeypatch):
    sleeps = []
    monkeypatch.setattr("time.sleep", lambda s: sleeps.append(s))
    session = FakeSession(
        [
            FakeResponse({}, status_code=429, headers={"Retry-After": "1.5"}),
            FakeResponse({"results": [], "next": None}),
        ]
    )
    client = AdemeDpeClient(DATASETS["existant"], session=session, max_retries=3)

    list(client.iter_lines())

    assert sleeps == [1.5]
