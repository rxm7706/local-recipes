"""Unit tests for ``pyforge.doctor.sources.pixi_currency`` (Story 21.7).

Covers the spec I/O matrix: within-threshold, past-threshold, unreadable
ledger, unreadable ``pixi.toml``. Uses real tmp git repos (mirrors
``test_sources_frozen_path.py``).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import pixi_currency

_LEAKY_GIT_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_CEILING_DIRECTORIES",
    "GIT_COMMON_DIR",
)

_MINIMAL_DREAM = """\
---
title: test
type: dream
status: dreamt
---

# test

## The full candidate ledger

candidate body

## The version currency ledger

version body

## The channel-sourcing debt ledger

channel body

## The external-tracking gap ledger

tracking body

## Constraints

constraints
"""


@pytest.fixture(autouse=True)
def _isolate_git_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _LEAKY_GIT_VARS:
        monkeypatch.delenv(var, raising=False)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q", "--initial-branch=main")
    _git(repo, "config", "user.email", "doctor-test@example.com")
    _git(repo, "config", "user.name", "Doctor Test")
    _git(repo, "config", "commit.gpgsign", "false")
    _git(repo, "config", "core.hooksPath", "/dev/null")


def _commit_all(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD").strip()


def _write_dream_and_pixi(repo: Path) -> None:
    dream = repo / "docs" / "dreams"
    dream.mkdir(parents=True, exist_ok=True)
    (dream / "pixi-candidate-currency.md").write_text(_MINIMAL_DREAM, encoding="utf-8")
    (repo / "pixi.toml").write_text('[project]\nname = "test"\n', encoding="utf-8")


def test_within_threshold_reports_ok(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write_dream_and_pixi(tmp_path)
    _commit_all(tmp_path, "seed dream and pixi together")
    findings = pixi_currency.gather(tmp_path)
    assert len(findings) == 1
    assert findings[0].status == DoctorStatus.OK
    assert findings[0].check == "pixi-currency-ledger-current"


def test_past_threshold_reports_warn_per_ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pixi_currency, "PIXI_CURRENCY_LEDGER_STALENESS_PIXI_COMMITS", 1)
    _init_repo(tmp_path)
    _write_dream_and_pixi(tmp_path)
    _commit_all(tmp_path, "seed dream and pixi")
    pixi = tmp_path / "pixi.toml"
    for i in range(3):
        pixi.write_text(f'[project]\nname = "test-{i}"\n', encoding="utf-8")
        _commit_all(tmp_path, f"pixi bump {i}")
    findings = pixi_currency.gather(tmp_path)
    stale = [f for f in findings if f.check == "pixi-currency-ledger-stale"]
    assert stale
    assert all(f.status == DoctorStatus.WARN for f in stale)
    assert all(f.source == Source.PIXI_CURRENCY_LEDGER for f in stale)


def test_unreadable_dream_degrades_to_named_finding(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / "pixi.toml").write_text('[project]\nname = "x"\n', encoding="utf-8")
    _commit_all(tmp_path, "pixi only")
    findings = pixi_currency.gather(tmp_path)
    assert len(findings) == 1
    assert findings[0].check == "pixi-currency-dream-unreadable"
    assert findings[0].status == DoctorStatus.WARN


def test_unreadable_pixi_toml_degrades_to_named_finding(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    dream = tmp_path / "docs" / "dreams"
    dream.mkdir(parents=True, exist_ok=True)
    (dream / "pixi-candidate-currency.md").write_text(_MINIMAL_DREAM, encoding="utf-8")
    _commit_all(tmp_path, "dream only")
    findings = pixi_currency.gather(tmp_path)
    assert len(findings) == 1
    assert findings[0].check == "pixi-currency-pixi-toml-unreadable"
    assert findings[0].status == DoctorStatus.WARN


def test_unreadable_ledger_section_degrades_to_named_finding(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    dream = tmp_path / "docs" / "dreams"
    dream.mkdir(parents=True, exist_ok=True)
    (dream / "pixi-candidate-currency.md").write_text(
        "# missing ledger headings\n",
        encoding="utf-8",
    )
    (tmp_path / "pixi.toml").write_text('[project]\nname = "x"\n', encoding="utf-8")
    _commit_all(tmp_path, "broken dream")
    findings = pixi_currency.gather(tmp_path)
    unreadable = [f for f in findings if f.check == "pixi-currency-ledger-unreadable"]
    assert unreadable
    assert all(f.status == DoctorStatus.WARN for f in unreadable)


def test_policy_threshold_is_module_level_constant() -> None:
    assert pixi_currency.PIXI_CURRENCY_LEDGER_STALENESS_PIXI_COMMITS == 30
