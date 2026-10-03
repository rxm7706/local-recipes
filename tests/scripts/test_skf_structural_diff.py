"""Tests for _bmad/skf/shared/scripts/skf-structural-diff.py (Story 27.1)."""

from __future__ import annotations

import importlib.util
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


def test_structural_diff_move_plus_signature_change_reports_both():
    """A moved export is still compared field by field (main reported
    changed=1, moved=1 for this input; the move pairing must too)."""
    m = _load_module()
    baseline = [{"name": "helper", "type": "function", "signature": "(a)", "file": "old.py"}]
    current = [{"name": "helper", "type": "function", "signature": "(a, b)", "file": "new.py"}]
    diff = m.diff_inventories(baseline, current)
    assert diff["summary"] == {"added": 0, "removed": 0, "changed": 1, "moved": 1, "unchanged": 0}
    assert diff["changed"] == [{
        "name": "helper",
        "field": "signature",
        "baseline_value": "(a)",
        "current_value": "(a, b)",
    }]


def test_structural_diff_pure_move_counts_unchanged_as_main_did():
    m = _load_module()
    baseline = [{"name": "helper", "type": "function", "file": "old.py", "line": 1}]
    current = [{"name": "helper", "type": "function", "file": "new.py", "line": 1}]
    diff = m.diff_inventories(baseline, current)
    assert diff["summary"] == {"added": 0, "removed": 0, "changed": 0, "moved": 1, "unchanged": 1}


def test_structural_diff_counts_each_changed_same_named_export():
    """summary.changed counts distinct changed (file, name) entries: four
    `main` exports whose signatures all changed are four, not one, and every
    changed[] name is the bare export name (no composite key, no NUL)."""
    m = _load_module()
    files = ("a.py", "b.py", "c.py", "d.py")
    baseline = [{"name": "main", "type": "function", "signature": "()", "file": f} for f in files]
    current = [{"name": "main", "type": "function", "signature": "(argv)", "file": f} for f in files]
    diff = m.diff_inventories(baseline, current)
    assert diff["summary"]["changed"] == 4
    assert diff["summary"]["unchanged"] == 0
    assert len(diff["changed"]) == 4
    assert {c["name"] for c in diff["changed"]} == {"main"}


def test_structural_diff_mixed_shape_file_on_one_side_reports_unchanged():
    """A `file` on only one side is the same entry in another inventory
    shape: matched and unchanged, as main reported it -- never added plus
    removed, never a move."""
    m = _load_module()
    baseline = [{"name": "main", "type": "function", "line": 1}]
    current = [{"name": "main", "type": "function", "file": "a.py", "line": 1}]
    diff = m.diff_inventories(baseline, current)
    assert diff["summary"] == {"added": 0, "removed": 0, "changed": 0, "moved": 0, "unchanged": 1}

    reverse = m.diff_inventories(current, baseline)
    assert reverse["summary"] == {"added": 0, "removed": 0, "changed": 0, "moved": 0, "unchanged": 1}
