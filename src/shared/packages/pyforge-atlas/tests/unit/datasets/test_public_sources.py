"""Story 34.6: ``public_sources.fetch_text`` -- one unauthenticated GET over a composed APIDataset."""

from __future__ import annotations

import pytest
from kedro.io import DatasetError

from pyforge.atlas.datasets import public_sources


class _Response:
    def __init__(self, content, content_type="text/html; charset=utf-8", encoding="utf-8"):
        self.content = content
        self.headers = {"content-type": content_type}
        self.encoding = encoding


def _api(monkeypatch, response, calls):
    class _API:
        def __init__(self, *, url, load_args=None, **kwargs):
            calls.append((url, dict(load_args or {}), kwargs))

        def load(self):
            return response

    monkeypatch.setattr(public_sources, "APIDataset", _API)


def test_fetch_text_composes_an_api_dataset_with_a_timeout_and_no_credential(monkeypatch):
    calls: list = []
    _api(monkeypatch, _Response(b"<html>ok</html>"), calls)

    assert public_sources.fetch_text("https://example.invalid/page", timeout=12) == "<html>ok</html>"
    ((url, load_args, kwargs),) = calls
    assert url == "https://example.invalid/page" and load_args["timeout"] == 12 and kwargs == {}
    assert load_args["auth"]("req") == "req"  # a no-op auth: requests never reads ~/.netrc


def test_a_body_with_no_declared_charset_reads_as_utf8(monkeypatch):
    """requests would read a text/* body with no charset as ISO-8859-1 ('cafÃ©')."""
    _api(monkeypatch, _Response("café".encode(), content_type="text/html", encoding="ISO-8859-1"), [])

    assert public_sources.fetch_text("https://example.invalid/page") == "café"


def test_a_declared_charset_is_honoured(monkeypatch):
    _api(monkeypatch, _Response("café".encode("latin-1"), "text/plain; charset=ISO-8859-1", "ISO-8859-1"), [])

    assert public_sources.fetch_text("https://example.invalid/page") == "café"


@pytest.mark.parametrize("content", [None, "already text"])
def test_a_body_that_is_not_bytes_is_a_fetch_failure(monkeypatch, content):
    _api(monkeypatch, _Response(content), [])

    with pytest.raises(DatasetError, match="expected a bytes body"):
        public_sources.fetch_text("https://example.invalid/page")


def test_the_suite_runs_offline():
    """The root conftest pins ``live()`` OFF for every test (Epic 34's hard boundary)."""
    assert public_sources.live() is False


def test_an_unknown_declared_charset_reads_as_utf8(monkeypatch):
    _api(monkeypatch, _Response("café".encode(), "text/html; charset=x-made-up", "x-made-up"), [])

    assert public_sources.fetch_text("https://example.invalid/page") == "café"
