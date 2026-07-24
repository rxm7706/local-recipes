"""Unit tests -- ``scripts/refresh_epss_feed.py`` (Story 6.7): the opt-in,
dev/ops-only FIRST.org EPSS provisioning script. Loaded via ``importlib``
(mirrors ``tests/unit/test_refresh_kev_feed.py``'s ``_load_refresh_kev_
feed`` pattern) since ``scripts/`` sits outside the installed package. All
network calls are mocked -- no socket ever opens in this suite. Adapted for
gzip-CSV instead of JSON: the fake response body is real gzip bytes.
"""

from __future__ import annotations

import csv
import gzip
import importlib.util
import io
import json
import urllib.error
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"


def _load_refresh_epss_feed():
    module_path = _SCRIPTS_DIR / "refresh_epss_feed.py"
    spec = importlib.util.spec_from_file_location("refresh_epss_feed", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def refresh_epss_feed():
    return _load_refresh_epss_feed()


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def read(self) -> bytes:
        return self._body


def _gzip_csv(rows: list[dict[str, str]], *, header: list[str] | None = None) -> bytes:
    buffer = io.StringIO()
    buffer.write("#model_version:v2023.03.01,score_date:2026-01-01T00:00:00+0000\n")
    fieldnames = header if header is not None else ["cve", "epss", "percentile"]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return gzip.compress(buffer.getvalue().encode("utf-8"))


_VALID_ROWS = [
    {"cve": "CVE-1970-00001", "epss": "0.7", "percentile": "0.9"},
    {"cve": "CVE-1970-00002", "epss": "0.1", "percentile": "0.2"},
]


# --- fetch_epss_scores -------------------------------------------------------


def test_fetch_epss_scores_returns_the_parsed_rows(monkeypatch, refresh_epss_feed):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **k: _FakeResponse(_gzip_csv(_VALID_ROWS)),
    )
    assert refresh_epss_feed.fetch_epss_scores() == [
        {"cve": "CVE-1970-00001", "epss": 0.7, "percentile": 0.9},
        {"cve": "CVE-1970-00002", "epss": 0.1, "percentile": 0.2},
    ]


def test_fetch_epss_scores_rejects_undecodable_gzip(monkeypatch, refresh_epss_feed):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **k: _FakeResponse(b"not actually gzip data"),
    )
    with pytest.raises(ValueError, match="gzip-compressed"):
        refresh_epss_feed.fetch_epss_scores()


def test_fetch_epss_scores_rejects_the_wrong_header(monkeypatch, refresh_epss_feed):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **k: _FakeResponse(
            _gzip_csv(
                [{"cve": "CVE-1970-00001", "unexpected": "shape"}],
                header=["cve", "unexpected"],
            )
        ),
    )
    with pytest.raises(ValueError, match="expected shape"):
        refresh_epss_feed.fetch_epss_scores()


def test_fetch_epss_scores_skips_malformed_rows_without_aborting(
    monkeypatch, refresh_epss_feed
):
    rows = [
        {"cve": "CVE-1970-00003", "epss": "not-a-number", "percentile": "0.5"},
        {"cve": "CVE-1970-00004", "epss": "0.4", "percentile": "0.6"},
    ]
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda *a, **k: _FakeResponse(_gzip_csv(rows))
    )
    assert refresh_epss_feed.fetch_epss_scores() == [
        {"cve": "CVE-1970-00004", "epss": 0.4, "percentile": 0.6}
    ]


def test_fetch_epss_scores_tolerates_an_extra_column(monkeypatch, refresh_epss_feed):
    """Review finding: a subset check, not an exact-match -- FIRST.org adding
    a new column to the public feed must not hard-fail provisioning."""
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **k: _FakeResponse(
            _gzip_csv(
                [{"cve": "CVE-1970-00001", "epss": "0.7", "percentile": "0.9",
                  "model_version": "v1"}],
                header=["cve", "epss", "percentile", "model_version"],
            )
        ),
    )
    assert refresh_epss_feed.fetch_epss_scores() == [
        {"cve": "CVE-1970-00001", "epss": 0.7, "percentile": 0.9}
    ]


def test_fetch_epss_scores_skips_a_row_with_an_empty_cve(monkeypatch, refresh_epss_feed):
    """Review finding: an empty ``cve`` must be skipped like any other
    malformed row -- never silently cached with a useless empty key, which
    would inflate the reported score_count without any usable data behind
    it (mirrors ``feeds.load_epss_scores``'s own non-empty-string check on
    the read side)."""
    rows = [
        {"cve": "", "epss": "0.5", "percentile": "0.5"},
        {"cve": "CVE-1970-00006", "epss": "0.4", "percentile": "0.6"},
    ]
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda *a, **k: _FakeResponse(_gzip_csv(rows))
    )
    assert refresh_epss_feed.fetch_epss_scores() == [
        {"cve": "CVE-1970-00006", "epss": 0.4, "percentile": 0.6}
    ]


def test_fetch_epss_scores_skips_non_finite_and_out_of_domain_rows(
    monkeypatch, refresh_epss_feed
):
    """Review finding (follow-up pass): ``float()`` happily parses
    ``"nan"``/``"inf"``/out-of-range strings, so without a domain check the
    provisioning script caches unusable rows (inflating ``score_count``) --
    and a cached ``NaN`` would not even be strict JSON. Every row outside
    the finite ``[0, 1]`` probability domain is skipped, mirroring
    ``feeds.load_epss_scores``'s read-side domain filter."""
    rows = [
        {"cve": "CVE-1970-00010", "epss": "nan", "percentile": "0.5"},
        {"cve": "CVE-1970-00011", "epss": "inf", "percentile": "0.5"},
        {"cve": "CVE-1970-00012", "epss": "0.5", "percentile": "-inf"},
        {"cve": "CVE-1970-00013", "epss": "2.0", "percentile": "0.9"},
        {"cve": "CVE-1970-00014", "epss": "-0.1", "percentile": "0.9"},
        {"cve": "CVE-1970-00015", "epss": "0.9", "percentile": "1.5"},
        {"cve": "CVE-1970-00016", "epss": "0.0", "percentile": "1.0"},
    ]
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda *a, **k: _FakeResponse(_gzip_csv(rows))
    )
    # Only the boundary-valid row survives (0.0 and 1.0 are both legal).
    assert refresh_epss_feed.fetch_epss_scores() == [
        {"cve": "CVE-1970-00016", "epss": 0.0, "percentile": 1.0}
    ]


def test_fetch_epss_scores_rejects_a_zero_row_result(monkeypatch, refresh_epss_feed):
    rows = [{"cve": "CVE-1970-00005", "epss": "bad", "percentile": "bad"}]
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda *a, **k: _FakeResponse(_gzip_csv(rows))
    )
    with pytest.raises(ValueError, match="zero usable"):
        refresh_epss_feed.fetch_epss_scores()


def test_fetch_epss_scores_propagates_a_network_failure(monkeypatch, refresh_epss_feed):
    def _raise(*_a, **_k):
        raise urllib.error.URLError("network unreachable")

    monkeypatch.setattr("urllib.request.urlopen", _raise)
    with pytest.raises(urllib.error.URLError):
        refresh_epss_feed.fetch_epss_scores()


# --- refresh -----------------------------------------------------------------


def test_refresh_writes_the_cache_and_reports_stats(
    monkeypatch, tmp_path, refresh_epss_feed
):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **k: _FakeResponse(_gzip_csv(_VALID_ROWS)),
    )
    cache_dir = tmp_path / "epss-cache"

    result = refresh_epss_feed.refresh(str(cache_dir))

    assert result["score_count"] == 2
    written = json.loads(Path(result["cache_path"]).read_text(encoding="utf-8"))
    assert written == {
        "scores": [
            {"cve": "CVE-1970-00001", "epss": 0.7, "percentile": 0.9},
            {"cve": "CVE-1970-00002", "epss": 0.1, "percentile": 0.2},
        ]
    }


# --- main ----------------------------------------------------------------------


def test_main_exits_2_when_no_cache_dir_is_available(
    monkeypatch, refresh_epss_feed, capsys
):
    monkeypatch.delenv(refresh_epss_feed.FEED_CACHE_DIR_ENV_VAR, raising=False)
    monkeypatch.setattr("sys.argv", ["refresh_epss_feed.py"])

    with pytest.raises(SystemExit) as exc_info:
        refresh_epss_feed.main()

    assert exc_info.value.code == 2
    assert "no cache dir given" in capsys.readouterr().err


def test_main_exits_1_when_refresh_fails(monkeypatch, tmp_path, refresh_epss_feed, capsys):
    def _raise(*_a, **_k):
        raise urllib.error.URLError("network unreachable")

    monkeypatch.setattr("urllib.request.urlopen", _raise)
    monkeypatch.setattr(
        "sys.argv", ["refresh_epss_feed.py", "--cache-dir", str(tmp_path / "cache")]
    )

    with pytest.raises(SystemExit) as exc_info:
        refresh_epss_feed.main()

    assert exc_info.value.code == 1
    assert "refresh-epss-feed FAILED" in capsys.readouterr().err


def test_main_rejects_a_non_positive_timeout_as_a_usage_error(
    monkeypatch, tmp_path, refresh_epss_feed, capsys
):
    """Review finding (follow-up pass): ``--timeout -5`` must be a USAGE
    error (exit 2, argparse's own channel), not a runtime ``ValueError``
    dressed up as a failed refresh (exit 1) -- the same usage-vs-runtime
    split ``cli._min_epss_type`` establishes for ``--min-epss``."""
    monkeypatch.setattr(
        "sys.argv",
        [
            "refresh_epss_feed.py",
            "--cache-dir",
            str(tmp_path / "cache"),
            "--timeout",
            "-5",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        refresh_epss_feed.main()

    assert exc_info.value.code == 2
    assert "--timeout" in capsys.readouterr().err


def test_main_prints_stats_and_returns_on_success(
    monkeypatch, tmp_path, refresh_epss_feed, capsys
):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **k: _FakeResponse(_gzip_csv(_VALID_ROWS)),
    )
    monkeypatch.setattr(
        "sys.argv", ["refresh_epss_feed.py", "--cache-dir", str(tmp_path / "cache")]
    )

    refresh_epss_feed.main()  # must not raise

    out = capsys.readouterr().out
    assert "score_count: 2" in out
