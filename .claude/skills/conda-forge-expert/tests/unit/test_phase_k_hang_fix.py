"""Tests for the 2026-05-23 Phase K hang fix.

Covers the four new pieces:
  - `_phase_k_fetch_with_hard_timeout` — hard wall-clock cutoff
  - `_phase_k_backoff_seconds` — jitter band
  - `_phase_k_github_graphql_batch` — exception classification +
    per-batch progress + per-batch `phase_state` checkpoint
"""
from __future__ import annotations

import importlib.util
import io
import json
import socket
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

import pytest


_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"


def _load(name: str):
    path = _SCRIPTS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def atlas_mod():
    return _load("conda_forge_atlas")


# ──────────────────────────────────────────────────────────────────────
# _phase_k_backoff_seconds
# ──────────────────────────────────────────────────────────────────────


def test_backoff_within_jitter_band(atlas_mod):
    """Backoff should sit in [base × 0.75, base × 1.25] for many draws."""
    for attempt in (0, 1, 2, 5):
        base = min(60.0, float(2 ** attempt + 2))
        samples = [atlas_mod._phase_k_backoff_seconds(attempt) for _ in range(50)]
        assert all(base * 0.75 <= s <= base * 1.25 for s in samples), \
            f"attempt={attempt} samples outside band: {samples}"


def test_backoff_caps_at_60s(atlas_mod):
    """Large attempt counts must be capped at 60s (× jitter)."""
    samples = [atlas_mod._phase_k_backoff_seconds(20) for _ in range(50)]
    assert all(s <= 60.0 * 1.25 for s in samples), samples


# ──────────────────────────────────────────────────────────────────────
# _phase_k_fetch_with_hard_timeout
# ──────────────────────────────────────────────────────────────────────


def _fake_response(payload: dict):
    """Mimic an `urlopen()` context-manager that returns ``payload``."""
    class _Ctx:
        def __init__(self, body):
            self.body = body
        def __enter__(self):
            return io.BytesIO(self.body)
        def __exit__(self, *exc):
            return False
    return _Ctx(json.dumps(payload).encode("utf-8"))


def test_hard_timeout_returns_payload_on_quick_response(atlas_mod):
    req = urllib.request.Request("https://example.invalid/graphql", method="POST")
    with patch.object(atlas_mod.urllib.request, "urlopen",
                      return_value=_fake_response({"data": {"hello": "world"}})):
        out = atlas_mod._phase_k_fetch_with_hard_timeout(req, hard_timeout_s=5.0)
    assert out == {"data": {"hello": "world"}}


def test_hard_timeout_raises_when_runner_blocks(atlas_mod):
    """If urlopen hangs longer than the budget, raise TimeoutError fast."""
    def _slow_urlopen(*a, **kw):
        time.sleep(10)
        return _fake_response({"data": {}})

    req = urllib.request.Request("https://example.invalid/graphql", method="POST")
    t0 = time.monotonic()
    with patch.object(atlas_mod.urllib.request, "urlopen", side_effect=_slow_urlopen):
        with pytest.raises(TimeoutError, match="hard"):
            atlas_mod._phase_k_fetch_with_hard_timeout(req, hard_timeout_s=0.5)
    elapsed = time.monotonic() - t0
    # 0.5s budget + 5s grace = ~5.5s ceiling. Must trip well under 10s
    # (the slow-urlopen sleep) — that's the whole point of the hard cap.
    assert elapsed < 7.0, f"hard timeout didn't fire fast enough: {elapsed:.1f}s"


def test_hard_timeout_propagates_inner_exception(atlas_mod):
    """A real HTTPError inside the runner should bubble up unwrapped."""
    fake_err = urllib.error.HTTPError(
        "https://example.invalid", 403, "rate-limited", {}, None,
    )

    def _err_urlopen(*a, **kw):
        raise fake_err

    req = urllib.request.Request("https://example.invalid/graphql", method="POST")
    with patch.object(atlas_mod.urllib.request, "urlopen", side_effect=_err_urlopen):
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            atlas_mod._phase_k_fetch_with_hard_timeout(req, hard_timeout_s=5.0)
    assert exc_info.value.code == 403


# ──────────────────────────────────────────────────────────────────────
# _phase_k_github_graphql_batch — exception classification + checkpoint
# ──────────────────────────────────────────────────────────────────────


def _ok_graphql_payload(batch: list[tuple[str, str]]) -> dict:
    """Build a payload matching the schema the function expects."""
    data = {}
    for i, (owner, repo) in enumerate(batch):
        data[f"r{i}"] = {
            "releases": {"nodes": [{"tagName": f"v1.0.{i}"}]},
            "refs": {"nodes": []},
        }
    return {"data": data}


def test_batch_success_path_emits_progress_and_checkpoint(atlas_mod, tmp_path, capsys):
    """Normal batched run must log per-batch progress AND write a
    `phase_state` row for every batch, ending in 'completed'-style cursor."""
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE phase_state ("
        " phase_name TEXT, run_started_at INTEGER, last_completed_cursor TEXT,"
        " items_completed INTEGER, items_total INTEGER, run_completed_at INTEGER,"
        " status TEXT, last_error TEXT,"
        " PRIMARY KEY (phase_name, run_started_at))"
    )

    repos = [(f"owner{i}", f"repo{i}") for i in range(7)]

    def _fake_urlopen(req, timeout=None):
        body = req.data
        query = json.loads(body)["query"]
        # parse out how many repos this batch covers
        n = query.count("repository(owner:")
        batch = [(f"owner{j}", f"repo{j}") for j in range(n)]
        return _fake_response(_ok_graphql_payload(batch))

    with patch.object(atlas_mod.urllib.request, "urlopen", side_effect=_fake_urlopen):
        results = atlas_mod._phase_k_github_graphql_batch(
            repos, gh_token="fake",
            batch_size=3,
            conn=conn,
            run_started_at=1700000000,
            progress_every_n_batches=1,
        )

    # 7 repos / 3 per batch = 3 batches (3 + 3 + 1)
    assert len(results) == 7
    # Each entry resolved to a version. _normalize_release_tag strips
    # the leading 'v', so "v1.0.3" → "1.0.3".
    for (owner, repo), (version, err) in results.items():
        assert err is None
        assert version is not None and version.startswith("1.0.")

    # Checkpoints: at least one per batch
    rows = conn.execute(
        "SELECT phase_name, status, last_completed_cursor, items_completed, items_total "
        "FROM phase_state WHERE phase_name='K'"
    ).fetchall()
    assert len(rows) >= 1, rows
    last = rows[-1]
    assert last[0] == "K"
    assert last[1] == "running"  # the helper writes 'running'; outer caller flips to 'completed'
    assert "batch=" in last[2]
    assert last[4] == 7  # items_total matches len(repos)

    # Progress log appeared at least once
    out = capsys.readouterr().out
    assert "GitHub GraphQL [" in out


def test_batch_timeout_classified_as_timeout_and_retried(atlas_mod, capsys):
    """A `socket.timeout` from urlopen should be logged as 'timeout' and
    retried up to 3 times, not silently absorbed."""
    repos = [("foo", "bar")]
    attempts: list[int] = []

    def _flaky_urlopen(req, timeout=None):
        attempts.append(1)
        raise socket.timeout("read timed out")

    with patch.object(atlas_mod.urllib.request, "urlopen", side_effect=_flaky_urlopen):
        with patch.object(atlas_mod.time, "sleep"):  # don't actually sleep
            results = atlas_mod._phase_k_github_graphql_batch(
                repos, gh_token="fake", batch_size=10, hard_timeout_s=1.0,
            )

    # 3 attempts then give up
    assert len(attempts) == 3
    # Result for the repo is marked with the timeout error
    assert results[("foo", "bar")][0] is None
    assert "timeout" in results[("foo", "bar")][1].lower()

    out = capsys.readouterr().out
    assert "timeout" in out.lower()
    assert "retry 1/3" in out
    assert "retry 2/3" in out
    assert "giving up" in out


def test_batch_404_not_retried(atlas_mod, capsys):
    """An HTTP 404 should NOT be retried — that's the existing behavior
    we must preserve."""
    repos = [("foo", "bar")]
    err = urllib.error.HTTPError(
        "https://example.invalid", 404, "not found", {}, None,
    )
    attempts: list[int] = []

    def _err_urlopen(req, timeout=None):
        attempts.append(1)
        raise err

    with patch.object(atlas_mod.urllib.request, "urlopen", side_effect=_err_urlopen):
        with patch.object(atlas_mod.time, "sleep"):
            results = atlas_mod._phase_k_github_graphql_batch(
                repos, gh_token="fake", batch_size=10,
            )
    assert len(attempts) == 1
    assert results[("foo", "bar")][1] == "HTTP 404"


def test_batch_503_retried_with_backoff(atlas_mod):
    """HTTP 503 (transient) should be retried — matches existing behavior."""
    repos = [("foo", "bar")]
    attempts: list[int] = []
    err = urllib.error.HTTPError(
        "https://example.invalid", 503, "unavailable", {}, None,
    )

    def _err_urlopen(req, timeout=None):
        attempts.append(1)
        raise err

    with patch.object(atlas_mod.urllib.request, "urlopen", side_effect=_err_urlopen):
        with patch.object(atlas_mod.time, "sleep"):
            atlas_mod._phase_k_github_graphql_batch(
                repos, gh_token="fake", batch_size=10,
            )
    assert len(attempts) == 3


def test_batch_url_error_classified_as_network(atlas_mod, capsys):
    """URLError → network branch; logged with 'network:' prefix."""
    repos = [("foo", "bar")]

    def _err_urlopen(req, timeout=None):
        raise urllib.error.URLError("dns failure")

    with patch.object(atlas_mod.urllib.request, "urlopen", side_effect=_err_urlopen):
        with patch.object(atlas_mod.time, "sleep"):
            results = atlas_mod._phase_k_github_graphql_batch(
                repos, gh_token="fake", batch_size=10,
            )
    out = capsys.readouterr().out
    assert "network:" in out
    assert "URLError" in results[("foo", "bar")][1]


def test_batch_unexpected_exception_treated_as_fatal(atlas_mod, capsys):
    """A truly unexpected exception (e.g. KeyError) should NOT retry —
    fail fast with 'unexpected' prefix in the log."""
    repos = [("foo", "bar")]
    attempts: list[int] = []

    def _err_urlopen(req, timeout=None):
        attempts.append(1)
        raise KeyError("something broke deep in urllib")

    with patch.object(atlas_mod.urllib.request, "urlopen", side_effect=_err_urlopen):
        with patch.object(atlas_mod.time, "sleep"):
            results = atlas_mod._phase_k_github_graphql_batch(
                repos, gh_token="fake", batch_size=10,
            )
    assert len(attempts) == 1  # no retry
    out = capsys.readouterr().out
    assert "unexpected KeyError" in out or "fatal" in out


def test_checkpoint_records_last_error_when_batch_fails(atlas_mod, tmp_path):
    """When a batch fails fully, the checkpoint row should carry the
    error string so operators can see WHY Phase K hung in postmortem."""
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE phase_state ("
        " phase_name TEXT, run_started_at INTEGER, last_completed_cursor TEXT,"
        " items_completed INTEGER, items_total INTEGER, run_completed_at INTEGER,"
        " status TEXT, last_error TEXT)"
    )

    repos = [("foo", "bar")]
    err = urllib.error.HTTPError("https://example.invalid", 500, "boom", {}, None)

    with patch.object(atlas_mod.urllib.request, "urlopen", side_effect=err):
        with patch.object(atlas_mod.time, "sleep"):
            atlas_mod._phase_k_github_graphql_batch(
                repos, gh_token="fake", batch_size=10,
                conn=conn, run_started_at=1700000000,
            )

    rows = conn.execute(
        "SELECT last_error FROM phase_state WHERE phase_name='K'"
    ).fetchall()
    assert rows
    assert "500" in (rows[-1][0] or "")
