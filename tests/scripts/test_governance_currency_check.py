"""Acceptance tests for scripts/governance_currency_check.py (Story 26.1 / DW-FU-19-1)."""
from __future__ import annotations

import importlib.util
import json
import subprocess
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


def test_main_json_file_flags(tmp_path, monkeypatch, capsys):
    mod = _load_detector()
    empty_root = tmp_path / "repo"
    empty_root.mkdir()
    (empty_root / "AGENTS.md").write_text("@AGENTS.md\n", encoding="utf-8")
    (empty_root / "CLAUDE.md").write_text("@AGENTS.md\n", encoding="utf-8")
    (empty_root / "GEMINI.md").write_text("# gemini\n", encoding="utf-8")
    (empty_root / ".github").mkdir()
    (empty_root / ".github" / "copilot-instructions.md").write_text("# copilot\n", encoding="utf-8")
    (empty_root / ".cursor" / "rules").mkdir(parents=True)
    probe = empty_root / "probe.md"
    probe.write_text("# probe\n", encoding="utf-8")
    monkeypatch.setattr(mod, "ROOT", empty_root)
    rel = probe.name
    assert mod.main(["--json", "--file", rel]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["documents"] == [rel]
    assert payload["findings"] == []


def test_gemini_md_stale_skill_reference_is_a_finding(tmp_path, monkeypatch):
    mod = _load_detector()
    empty_root = tmp_path / "repo"
    empty_root.mkdir()
    (empty_root / "GEMINI.md").write_text("Use `bmad-no-such-skill-ever` here.\n", encoding="utf-8")
    monkeypatch.setattr(mod, "ROOT", empty_root)
    findings = mod._check_document("GEMINI.md")
    assert any(f["kind"] == "skill-not-found" for f in findings)


def test_missing_copilot_instructions_is_a_finding(tmp_path, monkeypatch):
    mod = _load_detector()
    empty_root = tmp_path / "repo"
    empty_root.mkdir()
    monkeypatch.setattr(mod, "ROOT", empty_root)
    findings = mod._check_document(".github/copilot-instructions.md")
    assert findings[0]["kind"] == "missing-document"
    assert findings[0]["reference"] == ".github/copilot-instructions.md"


def test_main_subprocess_json_file_flag():
    proc = subprocess.run(
        [sys.executable, str(DETECTOR_PATH), "--json", "--file", "GEMINI.md"],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["documents"] == ["GEMINI.md"]


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
