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
    assert mod.main([]) == 0
    capsys.readouterr()


def test_main_json_file_flags(tmp_path, capsys):
    mod = _load_detector()
    doc = REPO_ROOT / ".cursor" / "governance-currency-probe-test.md"
    doc.write_text("# probe\nEmpty probe document for --file / --json wiring.\n", encoding="utf-8")
    try:
        rel = doc.relative_to(REPO_ROOT).as_posix()
        assert mod.main(["--json", "--file", rel]) == 0
        payload = __import__("json").loads(capsys.readouterr().out)
        assert payload["documents"] == [rel]
        assert payload["findings"] == []
    finally:
        doc.unlink(missing_ok=True)


def test_missing_cursor_rules_glob_is_a_finding(tmp_path, monkeypatch):
    mod = _load_detector()
    empty_root = tmp_path / "repo"
    empty_root.mkdir()
    (empty_root / ".cursor" / "rules").mkdir(parents=True)
    monkeypatch.setattr(mod, "ROOT", empty_root)
    findings = mod._missing_cursor_rules_findings()
    assert len(findings) == 1
    assert findings[0]["kind"] == "missing-document"
    assert findings[0]["reference"] == mod._CURSOR_RULES_GLOB
