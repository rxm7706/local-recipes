"""Unit tests for gather_ledger_staleness (Story 15.2 / FR-137..138)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import ledger


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    (repo / "README").write_text("x\n", encoding="utf-8")
    _git(repo, "add", "README")
    _git(repo, "commit", "-m", "init")
    _git(repo, "branch", "-M", "main")
    return repo


def _write_ledger(repo: Path, project: str, body: str) -> None:
    path = (
        repo
        / "_bmad-output"
        / "projects"
        / project
        / "planning-artifacts"
        / "sprint-status-ledger.yaml"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# GENERATED\ndevelopment_status:\n" + body, encoding="utf-8"
    )


def test_landed_but_unpromoted_is_fail(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    _write_ledger(repo, "pyforge-acme", "  1-1-alpha: backlog\n")
    _git(repo, "add", "-A")
    _git(
        repo,
        "commit",
        "-m",
        "Merge bmad-loop/run/1-1-alpha into loop/pyforge-acme (bmad-loop)",
    )
    findings = ledger.gather_ledger_staleness(repo)
    fails = [f for f in findings if f.status is DoctorStatus.FAIL]
    assert fails
    assert all(f.source is Source.LEDGER_STALENESS for f in fails)
    assert fails[0].evidence["direction"] == "MERGED_NOT_DONE_IN_LEDGER"


def test_done_without_merge_is_warn_with_direction(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    _write_ledger(repo, "pyforge-acme", "  2-2-beta: done\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "chore: no story merge")
    findings = ledger.gather_ledger_staleness(repo)
    warns = [f for f in findings if f.status is DoctorStatus.WARN]
    assert warns
    assert warns[0].evidence["direction"] == "DONE_IN_LEDGER_NOT_MERGED"


def test_agreement_is_ok(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    _write_ledger(repo, "pyforge-acme", "  3-3-gamma: done\n")
    _git(repo, "add", "-A")
    _git(
        repo,
        "commit",
        "-m",
        "Merge bmad-loop/run/3-3-gamma into loop/pyforge-acme (bmad-loop)",
    )
    findings = ledger.gather_ledger_staleness(repo)
    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK


def test_never_reads_tier3_feed(tmp_path: Path) -> None:
    """A done-only-in-feed story must not affect the check (FR-138)."""
    repo = _init_repo(tmp_path)
    _write_ledger(repo, "pyforge-acme", "  4-4-delta: backlog\n")
    feed = (
        repo
        / "_bmad-output"
        / "projects"
        / "pyforge-acme"
        / "implementation-artifacts"
        / "sprint-status.yaml"
    )
    feed.parent.mkdir(parents=True, exist_ok=True)
    feed.write_text("development_status:\n  4-4-delta: done\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "chore: feed lies, no merge")
    findings = ledger.gather_ledger_staleness(repo)
    # No merge → no MERGED_NOT_DONE FAIL from the feed's false done.
    assert not any(
        f.status is DoctorStatus.FAIL
        and f.evidence.get("direction") == "MERGED_NOT_DONE_IN_LEDGER"
        for f in findings
    )
