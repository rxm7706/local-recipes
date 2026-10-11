"""Story 92.1: fleet-picture ATTENTION names stale dispatch runs."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[6]
FLEET_PICTURE = REPO_ROOT / "scripts" / "fleet_picture.py"


def _load_fleet_picture():
    spec = importlib.util.spec_from_file_location("fleet_picture_stale_dispatch_test", FLEET_PICTURE)
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
