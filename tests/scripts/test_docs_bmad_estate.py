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


def test_check_is_bmad_estate_checks_own_verdict(monkeypatch, capsys, tmp_path):
    seen: list[Path] = []

    def fake_run_check(root):
        seen.append(root)
        return 1, ["[bmad-estate] drift: a section moved"]

    monkeypatch.setattr(m.bmad_estate_check, "run_check", fake_run_check)
    assert m.main(["--check", "--root", str(tmp_path)]) == 1
    assert seen == [tmp_path]
    assert "drift" in capsys.readouterr().out


def test_check_reads_a_scribe_cli_that_cannot_start_as_could_not_run(monkeypatch):
    """The false drift bmad_estate_check guards: the package is found, but `-m pyforge.scribe.cli`
    exits 1 because a module cannot be imported. The door must say could-not-run (2), never stale."""
    monkeypatch.setattr(m.bmad_estate_check.importlib.util, "find_spec", lambda name: object())

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="ModuleNotFoundError: No module named 'typer'")

    monkeypatch.setattr(m.bmad_estate_check.subprocess, "run", fake_run)
    assert m.main(["--check"]) == 2


def test_write_mode_calls_the_scribe_cli_entry(monkeypatch, tmp_path):
    monkeypatch.setattr(m.importlib.util, "find_spec", lambda name: object())
    seen: list[list[str]] = []

    def fake_run(command, **kwargs):
        seen.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(m.subprocess, "run", fake_run)
    assert m.main(["--root", str(tmp_path)]) == 0
    assert seen == [[sys.executable, "-m", "pyforge.scribe.cli", "catalog", "bmad-estate", "--write", "--root", str(tmp_path)]]


@pytest.mark.parametrize("scribe_exit", [1, 2, -9])
def test_a_failed_write_is_could_not_run(monkeypatch, scribe_exit):
    monkeypatch.setattr(m.importlib.util, "find_spec", lambda name: object())
    monkeypatch.setattr(
        m.subprocess, "run", lambda command, **kwargs: subprocess.CompletedProcess(command, scribe_exit, "", "")
    )
    assert m.main([]) == 2


def test_write_without_scribe_or_with_an_os_error_is_could_not_run(monkeypatch):
    monkeypatch.setattr(m.importlib.util, "find_spec", lambda name: None)
    assert m.main([]) == 2
    monkeypatch.setattr(m.importlib.util, "find_spec", lambda name: object())

    def boom(command, **kwargs):
        raise OSError("no interpreter")

    monkeypatch.setattr(m.subprocess, "run", boom)
    assert m.main([]) == 2


def test_the_committed_catalog_is_current_in_this_checkout():
    pytest.importorskip("pyforge.scribe")
    assert m.main(["--check", "--root", str(REPO_ROOT)]) == 0
