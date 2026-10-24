"""Unit tests for ``scripts/docs_bmad_estate.py`` (doctor Story 30.4, spec-pyforge-doctor CAP-84):
the ``scripts/docs_*.py`` door that lets ``docs/map.yaml`` name a generator for
``docs/reference/bmad-estate-llms-full.md``, whose real generator is ``scribe catalog bmad-estate``.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import docs_bmad_estate as m  # noqa: E402


def test_each_mode_calls_the_scribe_cli_entry_with_its_flag(tmp_path):
    for check, flag in ((True, "--check"), (False, "--write")):
        command = m.scribe_command(tmp_path, check=check)
        assert command[:6] == [sys.executable, "-m", "pyforge.scribe.cli", "catalog", "bmad-estate", flag]
        assert command[-2:] == ["--root", str(tmp_path)]


def test_no_scribe_package_is_could_not_run(monkeypatch, capsys):
    monkeypatch.setattr(m.importlib.util, "find_spec", lambda name: None)
    assert m.main(["--check"]) == 2
    assert "could-not-run" in capsys.readouterr().out


@pytest.mark.parametrize(("scribe_exit", "expected"), [(0, 0), (1, 1), (2, 2), (3, 2), (-9, 2)])
def test_the_verdict_is_scribes_and_anything_else_is_could_not_run(monkeypatch, scribe_exit, expected):
    monkeypatch.setattr(m.importlib.util, "find_spec", lambda name: object())
    seen: list[list[str]] = []

    def fake_run(command, **kwargs):
        seen.append(command)
        return subprocess.CompletedProcess(command, scribe_exit, stdout="", stderr="")

    monkeypatch.setattr(m.subprocess, "run", fake_run)
    assert m.main(["--check", "--root", "/judged"]) == expected
    assert seen and seen[0][5] == "--check" and seen[0][-1] == "/judged"


def test_an_os_error_is_could_not_run(monkeypatch):
    monkeypatch.setattr(m.importlib.util, "find_spec", lambda name: object())

    def boom(command, **kwargs):
        raise OSError("no interpreter")

    monkeypatch.setattr(m.subprocess, "run", boom)
    assert m.main(["--check"]) == 2


def test_the_committed_catalog_is_current_in_this_checkout():
    pytest.importorskip("pyforge.scribe")
    assert m.main(["--check", "--root", str(REPO_ROOT)]) == 0
