"""Story 34.6: ``public_sources.fetch_text`` -- one unauthenticated GET over a composed APIDataset."""

from __future__ import annotations

import pytest
from kedro.io import DatasetError

from pyforge.atlas.datasets import public_sources


class _Response:
    def __init__(self, text):
        self.text = text


def _api(monkeypatch, body, calls):
    class _API:
        def __init__(self, *, url, load_args=None, **kwargs):
            calls.append((url, load_args, kwargs))

        def load(self):
            return _Response(body)

    monkeypatch.setattr(public_sources, "APIDataset", _API)


def test_fetch_text_composes_an_api_dataset_with_a_timeout_and_no_credential(monkeypatch):
    calls: list = []
    _api(monkeypatch, "<html>ok</html>", calls)

    assert public_sources.fetch_text("https://example.invalid/page", timeout=12) == "<html>ok</html>"
    assert calls == [("https://example.invalid/page", {"timeout": 12}, {})]  # no credentials passed


def test_a_body_with_no_text_is_a_fetch_failure(monkeypatch):
    _api(monkeypatch, None, [])

    with pytest.raises(DatasetError, match="expected a text body"):
        public_sources.fetch_text("https://example.invalid/page")


def test_the_suite_runs_offline():
    """The root conftest pins ``live()`` OFF for every test (Epic 34's hard boundary)."""
    assert public_sources.live() is False
