"""Unit tests -- ``scripts/refresh_kev_feed.py`` (Story 6.4): the opt-in,
dev/ops-only CISA KEV provisioning script. Loaded via ``importlib`` (mirrors
``tests/conformance/test_kev_enrichment.py``'s ``_load_osv_builder`` pattern)
since ``scripts/`` sits outside the installed package. All network calls are
mocked -- no socket ever opens in this suite.
"""

from __future__ import annotations

import importlib.util
import json
import urllib.error
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"


def _load_refresh_kev_feed():
    module_path = _SCRIPTS_DIR / "refresh_kev_feed.py"
    spec = importlib.util.spec_from_file_location("refresh_kev_feed", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def refresh_kev_feed():
    return _load_refresh_kev_feed()


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def read(self) -> bytes:
        return self._body


_VALID_DOCUMENT = {
    "catalogVersion": "2026.07.18",
    "dateReleased": "2026-07-18T00:00:00Z",
    "vulnerabilities": [
        {"cveID": "CVE-1970-00001", "dateAdded": "2026-01-01"},
    ],
}


# --- fetch_kev_document -----------------------------------------------------


def test_fetch_kev_document_returns_the_parsed_document(monkeypatch, refresh_kev_feed):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **k: _FakeResponse(json.dumps(_VALID_DOCUMENT).encode("utf-8")),
    )
    assert refresh_kev_feed.fetch_kev_document() == _VALID_DOCUMENT


def test_fetch_kev_document_rejects_a_non_object_top_level(monkeypatch, refresh_kev_feed):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **k: _FakeResponse(json.dumps([1, 2, 3]).encode("utf-8")),
    )
    with pytest.raises(ValueError, match="expected shape"):
        refresh_kev_feed.fetch_kev_document()


def test_fetch_kev_document_rejects_a_missing_vulnerabilities_list(
    monkeypatch, refresh_kev_feed
):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **k: _FakeResponse(json.dumps({"unexpected": "shape"}).encode("utf-8")),
    )
    with pytest.raises(ValueError, match="expected shape"):
        refresh_kev_feed.fetch_kev_document()


def test_fetch_kev_document_propagates_a_network_failure(monkeypatch, refresh_kev_feed):
    def _raise(*_a, **_k):
        raise urllib.error.URLError("network unreachable")

    monkeypatch.setattr("urllib.request.urlopen", _raise)
    with pytest.raises(urllib.error.URLError):
        refresh_kev_feed.fetch_kev_document()


# --- refresh -----------------------------------------------------------------


def test_refresh_writes_the_cache_and_reports_stats(monkeypatch, tmp_path, refresh_kev_feed):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **k: _FakeResponse(json.dumps(_VALID_DOCUMENT).encode("utf-8")),
    )
    cache_dir = tmp_path / "kev-cache"

    result = refresh_kev_feed.refresh(str(cache_dir))

    assert result["catalog_version"] == "2026.07.18"
    assert result["date_released"] == "2026-07-18T00:00:00Z"
    assert result["vulnerability_count"] == 1
    written = json.loads(Path(result["cache_path"]).read_text(encoding="utf-8"))
    assert written == _VALID_DOCUMENT


# --- main ----------------------------------------------------------------------


def test_main_exits_2_when_no_cache_dir_is_available(
    monkeypatch, refresh_kev_feed, capsys
):
    monkeypatch.delenv(refresh_kev_feed.FEED_CACHE_DIR_ENV_VAR, raising=False)
    monkeypatch.setattr("sys.argv", ["refresh_kev_feed.py"])

    with pytest.raises(SystemExit) as exc_info:
        refresh_kev_feed.main()

    assert exc_info.value.code == 2
    assert "no cache dir given" in capsys.readouterr().err


def test_main_exits_1_when_refresh_fails(monkeypatch, tmp_path, refresh_kev_feed, capsys):
    def _raise(*_a, **_k):
        raise urllib.error.URLError("network unreachable")

    monkeypatch.setattr("urllib.request.urlopen", _raise)
    monkeypatch.setattr(
        "sys.argv", ["refresh_kev_feed.py", "--cache-dir", str(tmp_path / "cache")]
    )

    with pytest.raises(SystemExit) as exc_info:
        refresh_kev_feed.main()

    assert exc_info.value.code == 1
    assert "refresh-kev-feed FAILED" in capsys.readouterr().err


def test_main_prints_stats_and_returns_on_success(
    monkeypatch, tmp_path, refresh_kev_feed, capsys
):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **k: _FakeResponse(json.dumps(_VALID_DOCUMENT).encode("utf-8")),
    )
    monkeypatch.setattr(
        "sys.argv", ["refresh_kev_feed.py", "--cache-dir", str(tmp_path / "cache")]
    )

    refresh_kev_feed.main()  # must not raise

    out = capsys.readouterr().out
    assert "vulnerability_count: 1" in out
