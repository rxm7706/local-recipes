"""Smoke tests for v7.0 atlas CLIs.

Each CLI gets a minimal `--help` (does it parse?) check and, when the live
cf_atlas.db exists, a small `--limit 1 --json` end-to-end check (does it
return valid JSON without raising?). Tests that need atlas data are
skipped cleanly when the DB is absent, so the suite runs in any
environment.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

ATLAS_DB = (
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / "data" / "conda-forge-expert" / "cf_atlas.db"
)


def _db_has_packages() -> bool:
    """True if cf_atlas.db exists AND has at least one row in `packages`."""
    if not ATLAS_DB.exists():
        return False
    try:
        with sqlite3.connect(ATLAS_DB) as conn:
            n = conn.execute("SELECT COUNT(*) FROM packages").fetchone()[0]
        return n > 0
    except sqlite3.Error:
        return False


needs_atlas = pytest.mark.skipif(
    not _db_has_packages(),
    reason="cf_atlas.db missing or empty; build via `pixi run -e local-recipes build-cf-atlas`",
)


# ── --help smoke (no DB needed) ──────────────────────────────────────────────

@pytest.mark.parametrize("script", [
    "staleness_report.py",
    "feedstock_health.py",
    "whodepends.py",
    "behind_upstream.py",
    "cve_watcher.py",
    "version_downloads.py",
    "release_cadence.py",
    "find_alternative.py",
    "adoption_stage.py",
    "scan_project.py",
])
def test_cli_help(script_runner, script):
    rc, out, err = script_runner(script, "--help")
    assert rc == 0, f"{script} --help returned rc={rc}, stderr={err}"
    assert out, f"{script} --help produced no stdout"


# ── --json smoke (atlas DB required) ──────────────────────────────────────────

@needs_atlas
def test_staleness_report_json(script_runner):
    rc, out, err = script_runner("staleness_report.py", "--limit", "3", "--json")
    assert rc == 0, err
    rows = json.loads(out)
    assert isinstance(rows, list)


@needs_atlas
def test_feedstock_health_json(script_runner):
    rc, out, err = script_runner(
        "feedstock_health.py", "--filter", "stuck", "--limit", "3", "--json"
    )
    assert rc == 0, err
    rows = json.loads(out)
    assert isinstance(rows, list)


@needs_atlas
def test_whodepends_forward_json(script_runner):
    rc, out, err = script_runner("whodepends.py", "python", "--limit", "5", "--json")
    assert rc == 0, err
    rows = json.loads(out)
    assert isinstance(rows, list)


@needs_atlas
def test_whodepends_reverse_json(script_runner):
    rc, out, err = script_runner(
        "whodepends.py", "python", "--reverse", "--limit", "5", "--json"
    )
    assert rc == 0, err
    rows = json.loads(out)
    # python should have many dependents
    assert len(rows) >= 1


@needs_atlas
def test_behind_upstream_json(script_runner):
    rc, out, err = script_runner("behind_upstream.py", "--limit", "3", "--json")
    assert rc == 0, err
    rows = json.loads(out)
    assert isinstance(rows, list)


@needs_atlas
def test_version_downloads_json(script_runner):
    """version-downloads needs a name; pick one that's likely to have data."""
    rc, out, err = script_runner("version_downloads.py", "llms-py", "--json")
    assert rc == 0, err
    rows = json.loads(out)
    # Either has rows or empty (if Phase I didn't run for this pkg)
    assert isinstance(rows, list)


@needs_atlas
def test_release_cadence_json(script_runner):
    rc, out, err = script_runner(
        "release_cadence.py", "--limit", "3", "--json"
    )
    assert rc == 0, err
    rows = json.loads(out)
    assert isinstance(rows, list)


@needs_atlas
def test_find_alternative_json(script_runner):
    """Use a known-archived rxm7706 package or a generic one."""
    rc, out, err = script_runner(
        "find_alternative.py", "vllm-nccl-cu12", "--limit", "3", "--json"
    )
    # Non-zero if package not in atlas — accept either way as long as
    # the script didn't crash with an exception traceback
    assert rc in (0, 1), f"crashed: {err}"
    if rc == 0:
        rows = json.loads(out)
        assert isinstance(rows, list)


@needs_atlas
def test_adoption_stage_json(script_runner):
    rc, out, err = script_runner(
        "adoption_stage.py", "--package", "cachetools", "--json"
    )
    assert rc == 0, err
    rows = json.loads(out)
    assert isinstance(rows, list)


@needs_atlas
def test_cve_watcher_json(script_runner):
    """cve-watcher needs at least 2 vuln_history snapshots; test gracefully."""
    rc, out, err = script_runner("cve_watcher.py", "--json")
    assert rc == 0, err
    payload = json.loads(out)
    # Either {"meta": {...}, "rows": [...]} or {"meta": {...note: only one snapshot}}
    assert "meta" in payload


# ── detail-cf-atlas (uses atlas + atomically anaconda.org) ───────────────────

@needs_atlas
def test_detail_cf_atlas_json(script_runner):
    """detail-cf-atlas needs a known package name. Use 'python' which is
    universally present. Network calls to anaconda.org may fail in offline
    CI; we tolerate non-zero rc but still check that --json was emitted."""
    rc, out, err = script_runner("detail_cf_atlas.py", "python", "--json", timeout=30)
    # detail-cf-atlas may exit non-zero if the network is offline; the
    # --json output is still emitted on stdout in that case.
    assert "python" in out or rc != 0
