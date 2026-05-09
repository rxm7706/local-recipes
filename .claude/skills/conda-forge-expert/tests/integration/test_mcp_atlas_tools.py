"""Integration smoke tests for the v7.0 atlas MCP tools.

Exercises each MCP tool function through the FastMCP server module by
direct call (not through an MCP client). Each test asserts: the tool
returns valid JSON without raising. Tests that need atlas data are
auto-skipped when the DB is missing.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
ATLAS_DB = REPO_ROOT / ".claude" / "data" / "conda-forge-expert" / "cf_atlas.db"
TOOLS_DIR = REPO_ROOT / ".claude" / "tools"


def _db_has_packages() -> bool:
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
    reason="cf_atlas.db missing or empty",
)


@pytest.fixture(scope="module")
def srv():
    """Import the MCP server module once per module."""
    if str(TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(TOOLS_DIR))
    try:
        import conda_forge_server
    except ImportError as e:
        pytest.skip(f"MCP server not importable (missing fastmcp?): {e}")
    return conda_forge_server


@needs_atlas
def test_query_atlas_basic(srv):
    out = srv.query_atlas(limit=3)
    payload = json.loads(out)
    assert "rows" in payload
    assert len(payload["rows"]) <= 3


@needs_atlas
def test_query_atlas_blocks_writes(srv):
    out = srv.query_atlas(where="DROP TABLE packages", limit=1)
    payload = json.loads(out)
    assert "error" in payload, "DROP TABLE should be rejected"


@needs_atlas
def test_my_feedstocks(srv):
    out = srv.my_feedstocks("rxm7706")
    payload = json.loads(out)
    assert "rows" in payload


@needs_atlas
def test_staleness_report_tool(srv):
    out = srv.staleness_report(limit=3)
    rows = json.loads(out)
    assert isinstance(rows, list)


@needs_atlas
def test_feedstock_health_tool(srv):
    out = srv.feedstock_health(filter_kind="stuck", limit=3)
    rows = json.loads(out)
    assert isinstance(rows, list)


@needs_atlas
def test_whodepends_tool(srv):
    out = srv.whodepends("python", reverse=True, limit=5)
    rows = json.loads(out)
    assert isinstance(rows, list)


@needs_atlas
def test_behind_upstream_tool(srv):
    out = srv.behind_upstream(limit=3)
    rows = json.loads(out)
    assert isinstance(rows, list)


@needs_atlas
def test_cve_watcher_tool(srv):
    out = srv.cve_watcher(limit=3)
    payload = json.loads(out)
    assert "meta" in payload


@needs_atlas
def test_version_downloads_tool(srv):
    out = srv.version_downloads("llms-py", limit=5)
    rows = json.loads(out)
    assert isinstance(rows, list)


@needs_atlas
def test_release_cadence_tool(srv):
    out = srv.release_cadence(limit=3)
    rows = json.loads(out)
    assert isinstance(rows, list)


@needs_atlas
def test_find_alternative_tool(srv):
    out = srv.find_alternative("vllm-nccl-cu12", limit=3)
    rows = json.loads(out)
    assert isinstance(rows, list)


@needs_atlas
def test_adoption_stage_tool(srv):
    out = srv.adoption_stage(package="cachetools")
    rows = json.loads(out)
    assert isinstance(rows, list)
    if rows:
        assert "stage" in rows[0]


@needs_atlas
def test_package_health_tool(srv):
    """package_health calls detail-cf-atlas which may hit network; tolerate."""
    out = srv.package_health("python")
    # Either a real card or a `_run_script` error wrapper — both are valid JSON
    payload = json.loads(out)
    assert isinstance(payload, dict)
