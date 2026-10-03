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
