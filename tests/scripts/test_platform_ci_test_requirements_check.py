"""Tests for scripts/platform_ci_test_requirements_check.py (Story 16.1 guard)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "platform_ci_test_requirements_check.py"


def _import_module():
    spec = importlib.util.spec_from_file_location(
        "platform_ci_test_requirements_check", SCRIPT_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["platform_ci_test_requirements_check"] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


mod = _import_module()


def test_live_repo_is_clean():
    findings, stats = mod.run()
    assert findings == []
    assert stats["resurrected"] == []


def test_detects_resurrected_base(tmp_path, monkeypatch):
    req_dir = tmp_path / "requirements"
    req_dir.mkdir()
    (req_dir / "base.txt").write_text("django==5.1.11\n")
    monkeypatch.setattr(mod, "REQUIREMENTS_DIR", req_dir)
    findings, stats = mod.run()
    assert any(f["kind"] == "resurrected-requirements-file" for f in findings)
    assert any(name.endswith("base.txt") for name in stats["resurrected"])


def test_fix_flag_is_rejected(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["platform-ci-test-requirements-check", "--fix"])
    assert mod.main() == 2
