"""Story 86.6 — `scripts/tea_playwright_check.py` registry wrapper for CAP-5."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "tea_playwright_check.py"


def _load():
    spec = importlib.util.spec_from_file_location("tea_playwright_check", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_declares_repo_scope_for_the_registry() -> None:
    assert _load().DETECTOR == {"scope": "repo"}


def test_missing_generator_is_could_not_run(tmp_path: Path) -> None:
    module = _load()
    code, lines = module.run_check(tmp_path)
    assert code == 2
    assert any("could-not-run" in line and "bmad_tea_playwright.py" in line for line in lines)


def test_committed_matrices_pass_check() -> None:
    proc = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "OK pyforge-marshal:" in proc.stdout


def test_json_shape_on_success() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--json"], capture_output=True, text=True, check=False
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["detector"] == "tea-playwright-check"
    assert payload["status"] == "ok" and payload["exit"] == 0
