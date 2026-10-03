"""Acceptance tests for scripts/governance_currency_check.py (Story 26.1 / DW-FU-19-1)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DETECTOR_PATH = REPO_ROOT / "scripts" / "governance_currency_check.py"


def _load_detector():
    spec = importlib.util.spec_from_file_location("governance_currency_under_test", DETECTOR_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["governance_currency_under_test"] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_governed_documents_include_pointer_files():
    mod = _load_detector()
    docs = mod.governed_documents(REPO_ROOT)
    assert "GEMINI.md" in docs
    assert ".github/copilot-instructions.md" in docs
    assert any(d.startswith(".cursor/rules/") and d.endswith(".mdc") for d in docs)


def test_main_exits_zero_on_live_tree(capsys):
    mod = _load_detector()
    assert mod.main() == 0
    capsys.readouterr()
