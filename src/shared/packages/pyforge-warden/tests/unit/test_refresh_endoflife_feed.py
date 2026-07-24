"""Unit tests -- ``scripts/refresh_endoflife_feed.py`` (Story 6.3): the
opt-in, dev/ops-only endoflife.date provisioning script. Mirrors ``tests/
unit/test_refresh_kev_feed.py`` exactly. Loaded via ``importlib`` since
``scripts/`` sits outside the installed package. All network calls are
mocked -- no socket ever opens in this suite.
"""

from __future__ import annotations

import importlib.util
import json
import urllib.error
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"


def _load_refresh_endoflife_feed():
    module_path = _SCRIPTS_DIR / "refresh_endoflife_feed.py"
    spec = importlib.util.spec_from_file_location(
        "refresh_endoflife_feed", module_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def refresh_endoflife_feed():
    return _load_refresh_endoflife_feed()


class _FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def read(self) -> bytes:
        return self._body


_VALID_CYCLES = [
    {
        "cycle": "3.12",
        "releaseDate": "2023-10-02",
        "eol": "2028-10-31",
        "latest": "3.12.5",
        "latestReleaseDate": "2024-08-01",
    },
]


# --- default_product_slugs -----------------------------------------------------


def test_default_product_slugs_reads_the_bundled_registry(refresh_endoflife_feed):
    """The real bundled registry's own ``source: endoflife``/``source:
    heuristic-seed`` slugs -- ``source: manual`` entries (spring-framework)
    are excluded (they carry their own ``lts_lines``, no endoflife.date
    fetch needed)."""
    slugs = refresh_endoflife_feed.default_product_slugs()
    assert "python" in slugs
    assert "django" in slugs
    assert "spring-framework" not in slugs  # source: manual, excluded


def test_default_product_slugs_is_sorted_and_deduplicated(refresh_endoflife_feed):
    slugs = refresh_endoflife_feed.default_product_slugs()
    assert slugs == sorted(set(slugs))


def test_default_product_slugs_empty_on_unreadable_registry(
    monkeypatch, refresh_endoflife_feed
):
    monkeypatch.setattr(
        refresh_endoflife_feed, "_REGISTRY_PATH", Path("/does/not/exist.yaml")
    )
    assert refresh_endoflife_feed.default_product_slugs() == []


# --- fetch_product_cycles -------------------------------------------------------


def test_fetch_product_cycles_returns_the_parsed_array(
    monkeypatch, refresh_endoflife_feed
):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **k: _FakeResponse(json.dumps(_VALID_CYCLES).encode("utf-8")),
    )
    assert refresh_endoflife_feed.fetch_product_cycles("python") == _VALID_CYCLES


def test_fetch_product_cycles_rejects_a_non_array_top_level(
    monkeypatch, refresh_endoflife_feed
):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **k: _FakeResponse(json.dumps({"unexpected": "shape"}).encode("utf-8")),
    )
    with pytest.raises(ValueError, match="expected shape"):
        refresh_endoflife_feed.fetch_product_cycles("python")


def test_fetch_product_cycles_propagates_a_network_failure(
    monkeypatch, refresh_endoflife_feed
):
    def _raise(*_a, **_k):
        raise urllib.error.URLError("network unreachable")

    monkeypatch.setattr("urllib.request.urlopen", _raise)
    with pytest.raises(urllib.error.URLError):
        refresh_endoflife_feed.fetch_product_cycles("python")


def test_fetch_product_cycles_url_escapes_the_slug(monkeypatch, refresh_endoflife_feed):
    """A slug containing URL-special characters (whether from the bundled
    registry's own default list or an operator-supplied ``--product``
    value) must not produce a malformed or unintended request URL."""
    captured: dict[str, str] = {}

    def _capture(request, *a, **k):
        captured["url"] = request.full_url
        return _FakeResponse(json.dumps(_VALID_CYCLES).encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", _capture)
    refresh_endoflife_feed.fetch_product_cycles("weird/slug value")
    assert captured["url"] == "https://endoflife.date/api/weird%2Fslug%20value.json"


def test_fetch_product_cycles_rejects_an_empty_slug_without_a_request(
    monkeypatch, refresh_endoflife_feed
):
    """An empty slug (e.g. an operator's ``--product ''``) is a usage
    error, not a request worth making -- it would otherwise fetch the API
    root's ``.json`` and surface as a baffling HTTP error (review finding,
    2026-07-23). No socket call may even be attempted."""

    def _never(*_a, **_k):
        raise AssertionError("no request should be made for an empty slug")

    monkeypatch.setattr("urllib.request.urlopen", _never)
    with pytest.raises(ValueError, match="empty product slug"):
        refresh_endoflife_feed.fetch_product_cycles("")


def test_fetch_product_cycles_preserves_the_lexical_form_of_numeric_cycles(
    monkeypatch, refresh_endoflife_feed
):
    """A bare-number ``cycle`` in the real API response keeps its LEXICAL
    form through parsing (``3.10`` stays ``"3.10"``, never float-truncated
    to ``"3.1"``) -- the writer-side fix for the ``str(3.10) == "3.1"``
    misroute (review finding, 2026-07-23). Raw JSON is used deliberately:
    ``json.dumps`` of a Python float would itself round-trip the value."""
    raw = b'[{"cycle": 3.10, "releaseDate": "2021-10-04", "eol": "2026-10-31", "latest": 3.10}]'
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda *a, **k: _FakeResponse(raw)
    )
    (cycle_record,) = refresh_endoflife_feed.fetch_product_cycles("python")
    assert cycle_record["cycle"] == "3.10"
    assert cycle_record["latest"] == "3.10"


# --- refresh -----------------------------------------------------------------


def test_refresh_writes_the_cache_and_reports_stats(
    monkeypatch, tmp_path, refresh_endoflife_feed
):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **k: _FakeResponse(json.dumps(_VALID_CYCLES).encode("utf-8")),
    )
    cache_dir = tmp_path / "endoflife-cache"

    result = refresh_endoflife_feed.refresh(
        str(cache_dir), product_slugs=["python", "django"]
    )

    assert result["product_count"] == 2
    assert result["products"] == ["django", "python"]
    written = json.loads(Path(result["cache_path"]).read_text(encoding="utf-8"))
    assert written == {"python": _VALID_CYCLES, "django": _VALID_CYCLES}


def test_refresh_aborts_the_whole_run_on_one_products_failure(
    monkeypatch, tmp_path, refresh_endoflife_feed
):
    """A single product's fetch failure aborts the WHOLE refresh -- never a
    partially-written snapshot that looks complete."""

    def _selective_urlopen(request, *a, **k):
        if "django" in request.full_url:
            raise urllib.error.URLError("network unreachable")
        return _FakeResponse(json.dumps(_VALID_CYCLES).encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", _selective_urlopen)
    cache_dir = tmp_path / "endoflife-cache"

    with pytest.raises(urllib.error.URLError):
        refresh_endoflife_feed.refresh(str(cache_dir), product_slugs=["python", "django"])

    assert not (cache_dir / "endoflife" / "endoflife_snapshot.json").exists()


# --- main ----------------------------------------------------------------------


def test_main_exits_2_when_no_cache_dir_is_available(
    monkeypatch, refresh_endoflife_feed, capsys
):
    monkeypatch.delenv(refresh_endoflife_feed.FEED_CACHE_DIR_ENV_VAR, raising=False)
    monkeypatch.setattr("sys.argv", ["refresh_endoflife_feed.py"])

    with pytest.raises(SystemExit) as exc_info:
        refresh_endoflife_feed.main()

    assert exc_info.value.code == 2
    assert "no cache dir given" in capsys.readouterr().err


def test_main_exits_1_when_refresh_fails(
    monkeypatch, tmp_path, refresh_endoflife_feed, capsys
):
    def _raise(*_a, **_k):
        raise urllib.error.URLError("network unreachable")

    monkeypatch.setattr("urllib.request.urlopen", _raise)
    monkeypatch.setattr(
        "sys.argv",
        [
            "refresh_endoflife_feed.py",
            "--cache-dir",
            str(tmp_path / "cache"),
            "--product",
            "python",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        refresh_endoflife_feed.main()

    assert exc_info.value.code == 1
    assert "refresh-endoflife-feed FAILED" in capsys.readouterr().err


def test_main_prints_stats_and_returns_on_success(
    monkeypatch, tmp_path, refresh_endoflife_feed, capsys
):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **k: _FakeResponse(json.dumps(_VALID_CYCLES).encode("utf-8")),
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "refresh_endoflife_feed.py",
            "--cache-dir",
            str(tmp_path / "cache"),
            "--product",
            "python",
        ],
    )

    refresh_endoflife_feed.main()  # must not raise

    out = capsys.readouterr().out
    assert "fetched 1 product(s): python" in out


def test_main_defaults_products_to_the_bundled_registry(
    monkeypatch, tmp_path, refresh_endoflife_feed, capsys
):
    """No ``--product`` flags at all -- every registry ``source: endoflife``/
    ``source: heuristic-seed`` slug is fetched."""
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **k: _FakeResponse(json.dumps(_VALID_CYCLES).encode("utf-8")),
    )
    monkeypatch.setattr(
        "sys.argv",
        ["refresh_endoflife_feed.py", "--cache-dir", str(tmp_path / "cache")],
    )

    refresh_endoflife_feed.main()  # must not raise

    out = capsys.readouterr().out
    assert "python" in out
    assert "django" in out


def test_main_fails_loud_and_preserves_the_cache_when_zero_default_products_resolve(
    monkeypatch, tmp_path, refresh_endoflife_feed, capsys
):
    """No ``--product`` flags AND an unreadable/malformed bundled registry
    (``default_product_slugs()`` degrades to ``[]``, never raises) --
    ``refresh()`` now REFUSES to write and raises before touching the
    cache (review finding, 2026-07-23: the old warn-but-write-{} behavior
    atomically clobbered a previously provisioned, still-good snapshot
    with the most complete-looking partial snapshot possible). ``main()``
    exits 1 with the FAILED banner; an existing cache file survives
    byte-for-byte."""
    from pyforge.warden.feeds import endoflife_cache_path, write_endoflife_cache

    cache_dir = tmp_path / "cache"
    write_endoflife_cache(cache_dir, {"python": _VALID_CYCLES})
    provisioned = endoflife_cache_path(cache_dir).read_bytes()

    monkeypatch.setattr(
        refresh_endoflife_feed, "_REGISTRY_PATH", Path("/does/not/exist.yaml")
    )
    monkeypatch.setattr(
        "sys.argv",
        ["refresh_endoflife_feed.py", "--cache-dir", str(cache_dir)],
    )

    with pytest.raises(SystemExit) as excinfo:
        refresh_endoflife_feed.main()

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "FAILED" in captured.err
    assert "no product slugs to fetch" in captured.err
    assert captured.out == ""
    assert endoflife_cache_path(cache_dir).read_bytes() == provisioned


def test_refresh_refuses_an_explicitly_empty_product_list(
    tmp_path, refresh_endoflife_feed
):
    """``refresh(product_slugs=[])`` from a direct caller hits the same
    zero-slug refusal BEFORE any write -- no cache file appears at all."""
    from pyforge.warden.feeds import endoflife_cache_path

    cache_dir = tmp_path / "cache"
    with pytest.raises(ValueError, match="no product slugs to fetch"):
        refresh_endoflife_feed.refresh(str(cache_dir), product_slugs=[])
    assert not endoflife_cache_path(cache_dir).exists()


def test_main_does_not_warn_when_product_is_explicitly_narrow(
    monkeypatch, tmp_path, refresh_endoflife_feed, capsys
):
    """A deliberately narrow ``--product`` selection never hits the
    zero-slug refusal, even though the registry is unreadable here too --
    the refusal is specifically about the DEFAULT (no ``--product``) path;
    stderr stays clean on a successful explicit run."""
    monkeypatch.setattr(
        refresh_endoflife_feed, "_REGISTRY_PATH", Path("/does/not/exist.yaml")
    )
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **k: _FakeResponse(json.dumps(_VALID_CYCLES).encode("utf-8")),
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "refresh_endoflife_feed.py",
            "--cache-dir",
            str(tmp_path / "cache"),
            "--product",
            "python",
        ],
    )

    refresh_endoflife_feed.main()  # must not raise

    assert capsys.readouterr().err == ""
