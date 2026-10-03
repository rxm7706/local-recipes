"""Tests for _bmad/skf/shared/scripts/skf-structural-diff.py (Story 27.1)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = REPO_ROOT / "_bmad/skf/shared/scripts/skf-structural-diff.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("skf_structural_diff", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_structural_diff_keys_exports_by_file_and_name():
    m = _load_module()
    baseline = [
        {"name": "main", "type": "function", "file": "a.py", "line": 1},
        {"name": "main", "type": "function", "file": "b.py", "line": 2},
    ]
    current = baseline + [
        {"name": "main", "type": "function", "file": "c.py", "line": 3},
        {"name": "main", "type": "function", "file": "d.py", "line": 4},
    ]
    diff = m.diff_inventories(baseline, current)
    assert diff["summary"]["added"] == 2
    assert diff["summary"]["removed"] == 0
    assert diff["summary"]["unchanged"] == 2


def test_structural_diff_reports_export_move_by_name():
    m = _load_module()
    baseline = [{"name": "helper", "type": "function", "file": "old.py", "line": 1}]
    current = [{"name": "helper", "type": "function", "file": "new.py", "line": 1}]
    diff = m.diff_inventories(baseline, current)
    assert diff["summary"]["moved"] == 1
    assert diff["summary"]["added"] == 0
    assert diff["summary"]["removed"] == 0
    assert diff["moved"][0]["name"] == "helper"
    assert "\0" not in diff["moved"][0]["name"]


def test_structural_diff_fileless_inventory_still_diffs():
    m = _load_module()
    baseline = [{"name": "orphan", "type": "function", "line": 1}]
    current = baseline + [{"name": "other", "type": "function", "line": 2}]
    diff = m.diff_inventories(baseline, current)
    assert diff["summary"]["added"] == 1
    assert diff["added"][0]["name"] == "other"
