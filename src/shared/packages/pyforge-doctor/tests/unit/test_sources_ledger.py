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

import pytest

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import ledger

# A contributor's own git config must not decide whether this suite passes.
# `git init` inherits GIT_DIR/GIT_WORK_TREE from the environment, commit signing
# turns every fixture commit into a gpg prompt or failure, and a global
# core.hooksPath can reject the commit outright.
#
# The scrub is an AUTOUSE FIXTURE mutating os.environ, not a private env dict
# handed to the helper below, because the helper is not the only git caller
# here: `cli_bridge.run_git` -- which the module under test goes through -- does
# `env = dict(os.environ)` at call time, so a dict scrubbed at the fixture
# boundary never reaches it. Verified: with GIT_DIR exported, the previous
# fixture-local form left 13 of these tests failing, including
# `test_non_repository_target_warns_instead_of_accusing`, which returned FAIL
# instead of WARN -- exactly the regression that test exists to catch.
_LEAKY_GIT_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_CEILING_DIRECTORIES",
    "GIT_COMMON_DIR",
)


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
    # --initial-branch pins the default branch regardless of the contributor's
    # own init.defaultBranch; these tests name `origin/main` explicitly, but a
    # deterministic starting branch keeps failures readable.
    _git(repo, "init", "-q", "--initial-branch=main")
    _git(repo, "config", "user.email", "doctor-test@example.com")
    _git(repo, "config", "user.name", "Doctor Test")
    _git(repo, "config", "commit.gpgsign", "false")
    _git(repo, "config", "core.hooksPath", "/dev/null")


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


# --- Cannot-evaluate names its real cause ----------------------------------


def test_non_repository_target_names_the_repository_not_the_ref(
    tmp_path: Path,
) -> None:
    """Both cases WARN, but the message must not send an operator hunting for
    a ref problem when the real state is "this isn't a git repository."."""
    plain_dir = tmp_path / "not-a-repo"
    plain_dir.mkdir()

    findings = ledger.gather(plain_dir, base="origin/main", head="HEAD")

    assert len(findings) == 1
    finding = findings[0]
    assert finding.status is DoctorStatus.WARN
    assert "not a repository" in finding.message
    assert "not resolvable" not in finding.message


# --- The same-commit fallback announces itself ------------------------------


def test_base_substitution_is_recorded_in_evidence(tmp_path: Path) -> None:
    """When base==head the comparison silently moves to ``head^``. A --json
    consumer that asked for ``origin/main`` must be able to tell that it got a
    substituted base back, not the one it requested."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_ledger(repo, "doctor", {"1-1-foo": "done"})
    _commit_all(repo, "seed ledger")

    _write_ledger(repo, "doctor", {"1-1-foo": "done", "1-2-bar": "done"})
    head_sha = _commit_all(repo, "add another done story")
    _branch_at(repo, "origin/main", head_sha)

    findings = ledger.gather(repo, base="origin/main", head="HEAD")

    assert len(findings) == 1
    finding = findings[0]
    assert finding.status is DoctorStatus.OK
    assert finding.evidence["base_substituted"] is True
    assert finding.evidence["base_requested"] == "origin/main"
    assert finding.evidence["base"] != "origin/main"


def test_no_substitution_flag_when_base_is_used_as_requested(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_ledger(repo, "doctor", {"1-1-foo": "done"})
    base_sha = _commit_all(repo, "seed ledger")
    _branch_at(repo, "origin/main", base_sha)

    (repo / "unrelated.txt").write_text("noop\n", encoding="utf-8")
    _commit_all(repo, "unrelated change")

    findings = ledger.gather(repo, base="origin/main", head="HEAD")

    assert len(findings) == 1
    assert "base_substituted" not in findings[0].evidence
    assert findings[0].evidence["base"] == "origin/main"


# --- Never raises, even on a non-UTF-8 committed blob -----------------------


def test_non_utf8_ledger_blob_degrades_instead_of_raising(tmp_path: Path) -> None:
    """The spec's Always boundary is "degrade to a WARN/OK Finding on any
    unreadable/missing input, never raise". ``cli_bridge.run_git`` decodes with
    ``text=True`` and catches only TimeoutExpired/OSError, so a tracked ledger
    holding a non-UTF-8 byte used to raise UnicodeDecodeError straight out of
    ``gather``. The blob is unreadable, so the ledger reads as absent at head --
    a FAIL is an acceptable verdict here; an exception is not."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_ledger(repo, "doctor", {"1-1-foo": "done"})
    base_sha = _commit_all(repo, "seed ledger")
    _branch_at(repo, "origin/main", base_sha)

    bad = (
        repo / "_bmad-output" / "projects" / "doctor"
        / "planning-artifacts" / "sprint-status-ledger.yaml"
    )
    bad.write_bytes(b"development_status:\n  1-1-f\xe9o: done\n")
    _commit_all(repo, "ledger with a non-utf8 byte")

    findings = ledger.gather(repo, base="origin/main", head="HEAD")

    assert findings  # the point is that it RETURNED rather than raised
    assert all(f.source is Source.LEDGER_REGRESSION for f in findings)


# --- Evidence shape is uniform across both cannot-evaluate WARNs -----------


def test_both_warn_paths_carry_the_same_evidence_keys(tmp_path: Path) -> None:
    """Same source, same check, same status -- a consumer reading
    evidence["target"] must not KeyError depending on which WARN fired."""
    unresolvable = tmp_path / "unresolvable"
    _init_repo(unresolvable)
    _write_ledger(unresolvable, "doctor", {"1-1-foo": "done"})
    _commit_all(unresolvable, "seed ledger")  # no origin/main branch created

    no_parent = tmp_path / "no-parent"
    _init_repo(no_parent)
    _write_ledger(no_parent, "doctor", {"1-1-foo": "done"})
    only_sha = _commit_all(no_parent, "the only commit")
    _branch_at(no_parent, "origin/main", only_sha)

    a = ledger.gather(unresolvable, base="origin/main", head="HEAD")[0]
    b = ledger.gather(no_parent, base="origin/main", head="HEAD")[0]

    assert a.status is DoctorStatus.WARN
    assert b.status is DoctorStatus.WARN
    assert set(a.evidence) == set(b.evidence) == {"base", "head", "target"}


# --- Evidence is machine-shaped, not print-shaped --------------------------


def test_regression_evidence_carries_structured_transitions(tmp_path: Path) -> None:
    """``keys`` is bare story keys under BOTH check kinds; the old->new
    transition travels beside it already parsed, so a --json consumer never has
    to re-parse a display string."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_ledger(repo, "doctor", {"1-1-foo": "done"})
    base_sha = _commit_all(repo, "seed ledger")
    _branch_at(repo, "origin/main", base_sha)

    _write_ledger(repo, "doctor", {"1-1-foo": "in-progress"})
    _commit_all(repo, "regress the story")

    finding = ledger.gather(repo, base="origin/main", head="HEAD")[0]

    assert finding.evidence["keys"] == ["1-1-foo"]
    assert finding.evidence["transitions"] == [
        {"key": "1-1-foo", "from": "done", "to": "in-progress"}
    ]


# --- A green verdict says how much it measured ------------------------------


def test_ok_finding_reports_how_many_ledgers_were_compared(tmp_path: Path) -> None:
    """"Clean" and "found nothing to look at" are the same empty finding list.
    Both still report OK (that verdict question is deferred), but the count
    makes them distinguishable in the report."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_ledger(repo, "doctor", {"1-1-foo": "done"})
    _write_ledger(repo, "warden", {"2-1-bar": "done"})
    base_sha = _commit_all(repo, "seed two ledgers")
    _branch_at(repo, "origin/main", base_sha)

    (repo / "unrelated.txt").write_text("noop\n", encoding="utf-8")
    _commit_all(repo, "unrelated change")

    finding = ledger.gather(repo, base="origin/main", head="HEAD")[0]
    assert finding.status is DoctorStatus.OK
    assert finding.evidence["ledgers_compared"] == 2

    empty = tmp_path / "empty"
    _init_repo(empty)
    (empty / "x.txt").write_text("x\n", encoding="utf-8")
    empty_base = _commit_all(empty, "no ledgers at all")
    _branch_at(empty, "origin/main", empty_base)
    (empty / "y.txt").write_text("y\n", encoding="utf-8")
    _commit_all(empty, "still no ledgers")

    vacuous = ledger.gather(empty, base="origin/main", head="HEAD")[0]
    assert vacuous.status is DoctorStatus.OK
    assert vacuous.evidence["ledgers_compared"] == 0
