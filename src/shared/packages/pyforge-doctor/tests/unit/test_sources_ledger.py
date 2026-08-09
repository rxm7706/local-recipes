"""Unit tests for ``pyforge.doctor.sources.ledger.gather`` (Story 6.4) --
covers every row of the spec's I/O & Edge-Case Matrix against REAL tmp git
repositories (this test file is not restricted to ``cli_bridge.py`` -- only
the package source under ``pyforge/doctor/`` is; a test file driving real
``git`` directly to set up fixtures is fine).

``base="origin/main"`` is made resolvable without a real git remote by
creating a local branch literally named ``origin/main`` -- git allows
slashes in branch names, so ``git branch origin/main <sha>`` creates
``refs/heads/origin/main``, which ``git rev-parse origin/main`` resolves
exactly like a remote-tracking ref would.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import ledger


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    )
    return result.stdout


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "doctor-test@example.com")
    _git(repo, "config", "user.name", "Doctor Test")


def _write_ledger(
    repo: Path, project: str, statuses: dict[str, str]
) -> Path:
    ledger_path = (
        repo
        / "_bmad-output"
        / "projects"
        / project
        / "planning-artifacts"
        / "sprint-status-ledger.yaml"
    )
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["development_status:"]
    lines.extend(f"  {key}: {value}" for key, value in statuses.items())
    ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ledger_path


def _delete_ledger(repo: Path, project: str) -> None:
    ledger_path = (
        repo
        / "_bmad-output"
        / "projects"
        / project
        / "planning-artifacts"
        / "sprint-status-ledger.yaml"
    )
    ledger_path.unlink()


def _commit_all(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD").strip()


def _branch_at(repo: Path, name: str, sha: str) -> None:
    _git(repo, "branch", name, sha)


# --- Clean revision range --------------------------------------------------


def test_clean_revision_range_reports_ok(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_ledger(repo, "doctor", {"1-1-foo": "done"})
    base_sha = _commit_all(repo, "seed ledger")
    _branch_at(repo, "origin/main", base_sha)

    (repo / "unrelated.txt").write_text("noop\n", encoding="utf-8")
    _commit_all(repo, "unrelated change")

    findings = ledger.gather(repo, base="origin/main", head="HEAD")

    assert len(findings) == 1
    assert findings[0].source is Source.LEDGER_REGRESSION
    assert findings[0].check == "ledger-regression"
    assert findings[0].status is DoctorStatus.OK


def test_new_ledger_at_head_is_not_a_regression(tmp_path: Path) -> None:
    """A ledger that doesn't exist at ``base`` yet has nothing to regress
    against -- ``_check``'s own ``before_text is None: continue`` branch."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "unrelated.txt").write_text("noop\n", encoding="utf-8")
    base_sha = _commit_all(repo, "seed, no ledger yet")
    _branch_at(repo, "origin/main", base_sha)

    _write_ledger(repo, "doctor", {"1-1-foo": "done"})
    _commit_all(repo, "add the ledger for the first time")

    findings = ledger.gather(repo, base="origin/main", head="HEAD")

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK


# --- Regression --------------------------------------------------------


def test_done_key_regressed_reports_fail(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_ledger(repo, "doctor", {"1-1-foo": "done"})
    base_sha = _commit_all(repo, "seed ledger")
    _branch_at(repo, "origin/main", base_sha)

    _write_ledger(repo, "doctor", {"1-1-foo": "in-progress"})
    _commit_all(repo, "regress the story")

    findings = ledger.gather(repo, base="origin/main", head="HEAD")

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.LEDGER_REGRESSION
    assert finding.check == "done-key-regressed"
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["project"] == "doctor"
    assert any("1-1-foo" in key for key in finding.evidence["keys"])


# --- Renamed-but-still-done ----------------------------------------------


def test_renamed_but_still_done_key_is_not_a_regression(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_ledger(repo, "doctor", {"1-1-scaffold-the-kedro": "done"})
    base_sha = _commit_all(repo, "seed ledger")
    _branch_at(repo, "origin/main", base_sha)

    _write_ledger(repo, "doctor", {"a1-scaffold-the-kedro": "done"})
    _commit_all(repo, "normalize id to alias form")

    findings = ledger.gather(repo, base="origin/main", head="HEAD")

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK
    assert findings[0].check == "ledger-regression"


# --- Ledger deleted while holding a done key -------------------------------


def test_ledger_deleted_while_holding_done_key_reports_fail(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_ledger(repo, "doctor", {"1-1-foo": "done"})
    base_sha = _commit_all(repo, "seed ledger")
    _branch_at(repo, "origin/main", base_sha)

    _delete_ledger(repo, "doctor")
    _commit_all(repo, "delete the ledger")

    findings = ledger.gather(repo, base="origin/main", head="HEAD")

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.LEDGER_REGRESSION
    assert finding.check == "ledger-deleted"
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["project"] == "doctor"
    assert "1-1-foo" in finding.evidence["keys"]


# --- Base ref unresolvable --------------------------------------------------


def test_unresolvable_base_ref_reports_warn(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_ledger(repo, "doctor", {"1-1-foo": "done"})
    _commit_all(repo, "seed ledger")
    # deliberately never create an "origin/main" branch/ref

    findings = ledger.gather(repo, base="origin/main", head="HEAD")

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.LEDGER_REGRESSION
    assert finding.check == "ledger-regression"
    assert finding.status is DoctorStatus.WARN
    assert "origin/main" in finding.message


# --- base == head, no parent ------------------------------------------------


def test_base_equals_head_with_no_parent_reports_warn(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_ledger(repo, "doctor", {"1-1-foo": "done"})
    only_sha = _commit_all(repo, "the only commit, no parent")
    _branch_at(repo, "origin/main", only_sha)

    findings = ledger.gather(repo, base="origin/main", head="HEAD")

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.LEDGER_REGRESSION
    assert finding.check == "ledger-regression"
    assert finding.status is DoctorStatus.WARN
    assert "same commit" in finding.message


def test_base_equals_head_falls_back_to_parent_when_one_exists(tmp_path: Path) -> None:
    """Same-commit push-event shape (Design Notes): a real parent exists, so
    the fallback silently compares against it rather than warning."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_ledger(repo, "doctor", {"1-1-foo": "done"})
    _commit_all(repo, "seed ledger")

    _write_ledger(repo, "doctor", {"1-1-foo": "in-progress"})
    head_sha = _commit_all(repo, "regress the story")
    _branch_at(repo, "origin/main", head_sha)

    findings = ledger.gather(repo, base="origin/main", head="HEAD")

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "done-key-regressed"
    assert finding.status is DoctorStatus.FAIL


# --- Multi-project aggregation ----------------------------------------------


def test_regressions_across_multiple_projects_are_all_reported_independently(
    tmp_path: Path,
) -> None:
    """The base/head ledger-path union spans every project's ledger, not
    just one -- a regression in "doctor" must not suppress or merge with a
    regression in "warden", and a clean third project must not produce a
    spurious finding of its own."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_ledger(repo, "doctor", {"1-1-foo": "done"})
    _write_ledger(repo, "warden", {"2-1-bar": "done"})
    _write_ledger(repo, "mason", {"3-1-baz": "done"})
    base_sha = _commit_all(repo, "seed three ledgers")
    _branch_at(repo, "origin/main", base_sha)

    _write_ledger(repo, "doctor", {"1-1-foo": "in-progress"})
    _write_ledger(repo, "warden", {"2-1-bar": "backlog"})
    # "mason" is left untouched -- must not appear as a false positive.
    _commit_all(repo, "regress doctor and warden, leave mason clean")

    findings = ledger.gather(repo, base="origin/main", head="HEAD")

    assert len(findings) == 2
    assert {f.evidence["project"] for f in findings} == {"doctor", "warden"}
    assert all(f.check == "done-key-regressed" for f in findings)
    assert all(f.status is DoctorStatus.FAIL for f in findings)
