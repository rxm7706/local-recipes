"""CI surfaces tile vs steward ci-status schema (Story 39.1 AC6)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCHEMA_REL = "src/shared/packages/pyforge-steward/src/pyforge/steward/data/ci-status-schema.json"


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (
            candidate / "src" / "shared" / "packages" / "pyforge-herald"
        ).is_dir():
            return candidate
    raise AssertionError("repo root not found")


def _load_ci_surfaces_tool():
    root = _repo_root()
    path = root / "docsite" / "tools" / "ci_surfaces_tile.py"
    spec = importlib.util.spec_from_file_location("ci_surfaces_tile_contract", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_row_verdict_enum_matches_tile_known_verdicts() -> None:
    cst = _load_ci_surfaces_tool()
    schema = json.loads((_repo_root() / SCHEMA_REL).read_text(encoding="utf-8"))
    schema_verdicts = set(schema["$defs"]["row"]["properties"]["verdict"]["enum"])
    assert schema_verdicts == cst.KNOWN_VERDICTS


def test_fixture_rows_use_only_schema_defined_keys() -> None:
    schema = json.loads((_repo_root() / SCHEMA_REL).read_text(encoding="utf-8"))
    allowed = set(schema["$defs"]["row"]["properties"].keys())
    sample_rows = [
        {
            "id": "unregistered:PAUSE_X",
            "switch": None,
            "declared_state": "live",
            "live_switch_value": None,
            "paused_since": None,
            "review_by": None,
            "review_days_left": None,
            "owner": None,
            "last_green_run": None,
            "verdict": "drift",
            "detail": "not in registry",
        },
        {
            "id": "dashboard.deploy",
            "switch": "PAUSE_DASHBOARD",
            "declared_state": "paused",
            "live_switch_value": "true",
            "paused_since": "2026-10-06",
            "review_by": "2026-10-12",
            "review_days_left": -3,
            "owner": "pyforge-steward",
            "last_green_run": None,
            "verdict": "overdue",
        },
    ]
    for row in sample_rows:
        extra = set(row.keys()) - allowed
        assert not extra, f"fixture row {row.get('id')!r} has undefined keys: {extra}"
