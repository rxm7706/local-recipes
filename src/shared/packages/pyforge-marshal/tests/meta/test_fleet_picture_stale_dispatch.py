"""Story 92.1: fleet-picture ATTENTION names stale dispatch runs."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

# Story 116.2 (spec-pyforge-marshal:CAP-305): this module reads the repository outside this package, so it runs in
# the live-tree half; it finds the repository root when a test runs, never at import, so the module imports off
# the tree (the package half collects it before the marker deselects it).
pytestmark = pytest.mark.live_tree


def _fleet_picture_path() -> Path:
    # tests/meta -> tests -> pyforge-marshal -> packages -> shared -> src -> repo root
    return Path(__file__).resolve().parents[6] / "scripts" / "fleet_picture.py"


def _load_fleet_picture():
    spec = importlib.util.spec_from_file_location("fleet_picture_stale_dispatch_test", _fleet_picture_path())
    mod = importlib.util.module_from_spec(spec)
    sys.modules["fleet_picture_stale_dispatch_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_stale_dispatch_runs_watch_line():
    mod = _load_fleet_picture()
    live_row = {
        "dispatch_stale_runs": [
            {
                "run_id": "pyforge-marshal-20261004T165202766Z-fc6ece35",
                "story_key": "86-6",
                "worktree_path": "/tmp/missing",
                "remedy": "quarantine",
            }
        ]
    }
    lines = mod._dispatch_stale_runs_watch_lines(slug="marshal", live_row=live_row)
    assert len(lines) == 1
    assert "1 stale dispatch run" in lines[0]
    assert "dispatch-runs-quarantine" in lines[0]
