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


def _write_ledger(repo: Path, project: str, statuses: dict[str, str]) -> Path:
    ledger_path = repo / "_bmad-output" / "projects" / project / "planning-artifacts" / "sprint-status-ledger.yaml"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["development_status:"]
    lines.extend(f"  {key}: {value}" for key, value in statuses.items())
    ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ledger_path


def _delete_ledger(repo: Path, project: str) -> None:
    ledger_path = repo / "_bmad-output" / "projects" / project / "planning-artifacts" / "sprint-status-ledger.yaml"
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
    assert "merge_base" not in findings[0].evidence
    assert "base_requested" not in findings[0].evidence
    assert findings[0].evidence["base"] == "origin/main"


# --- Story 27.1: a PR is judged at its merge-base, not base's own tip ------


def test_pr1465_shape_stale_head_after_unattended_main_promotion_is_ok(
    tmp_path: Path,
) -> None:
    """Herald PR #1465's exact shape: a story branch forks from ``main``,
    then ``main`` advances on its own (an unattended dispatch promoting a
    SIBLING story to `done`) before the PR's own detectors lane runs. Judged
    against ``base``'s tip, the promoted row reads as something this branch
    "un-finished," even though the branch never touched it. Judged against
    ``merge-base(base, head)`` -- the fork point -- there is nothing to see.
    """
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_ledger(repo, "herald", {"23-6-landing-fallout": "in-progress"})
    fork_sha = _commit_all(repo, "fork point")

    # The PR branch: an unrelated change, never touching 23-6.
    (repo / "pr-change.txt").write_text("noop\n", encoding="utf-8")
    head_sha = _commit_all(repo, "PR: unrelated change")

    # `main` advances independently from the SAME fork point, promoting the
    # sibling story to done -- this is the commit the stale PR head never saw.
    _git(repo, "checkout", "-q", fork_sha)
    _write_ledger(repo, "herald", {"23-6-landing-fallout": "done"})
    _commit_all(repo, "marshal: promote 23-6 to done")
    _git(repo, "branch", "-f", "origin/main", "HEAD")
    _git(repo, "checkout", "-q", head_sha)

    findings = ledger.gather(repo, base="origin/main", head="HEAD")

    assert len(findings) == 1
    finding = findings[0]
    assert finding.status is DoctorStatus.OK
    assert finding.check == "ledger-regression"
    assert finding.evidence["merge_base"] == fork_sha
    assert finding.evidence["base_requested"] == "origin/main"
    assert finding.evidence["base"] == fork_sha


def test_genuine_regression_survives_merge_base_substitution(tmp_path: Path) -> None:
    """The merge-base fix must not mask a regression the PR branch itself
    introduces -- only the false one caused by `main` moving independently."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_ledger(repo, "doctor", {"1-1-foo": "done"})
    fork_sha = _commit_all(repo, "fork point")

    # The PR branch itself regresses the story.
    _write_ledger(repo, "doctor", {"1-1-foo": "in-progress"})
    head_sha = _commit_all(repo, "PR: regress the story")

    # `main` independently advances with an unrelated change.
    _git(repo, "checkout", "-q", fork_sha)
    (repo / "unrelated.txt").write_text("noop\n", encoding="utf-8")
    _commit_all(repo, "unrelated change on main")
    _git(repo, "branch", "-f", "origin/main", "HEAD")
    _git(repo, "checkout", "-q", head_sha)

    findings = ledger.gather(repo, base="origin/main", head="HEAD")

    assert len(findings) == 1
    finding = findings[0]
    assert finding.status is DoctorStatus.FAIL
    assert finding.check == "done-key-regressed"
    assert finding.evidence["merge_base"] == fork_sha


def test_merge_base_equal_to_base_tip_is_not_a_substitution(tmp_path: Path) -> None:
    """An ordinary linear PR (``base`` is already an ancestor of ``head``,
    the common case) must not be reported as substituted -- the merge-base
    IS ``base``'s own tip here, so ``effective_base`` stays the literal ref."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_ledger(repo, "doctor", {"1-1-foo": "done"})
    base_sha = _commit_all(repo, "seed ledger")
    _branch_at(repo, "origin/main", base_sha)

    (repo / "unrelated.txt").write_text("noop\n", encoding="utf-8")
    _commit_all(repo, "PR: unrelated change")

    findings = ledger.gather(repo, base="origin/main", head="HEAD")

    assert len(findings) == 1
    assert "merge_base" not in findings[0].evidence
    assert "base_substituted" not in findings[0].evidence
    assert findings[0].evidence["base"] == "origin/main"


def test_no_common_ancestor_reports_warn(tmp_path: Path) -> None:
    """Unrelated histories: ``git merge-base`` itself cannot resolve. This
    must degrade to a cannot-evaluate WARN, never silently fall back to
    comparing against ``base``'s tip (the bug this story fixes)."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_ledger(repo, "doctor", {"1-1-foo": "done"})
    _commit_all(repo, "main history")
    _git(repo, "branch", "-f", "origin/main", "HEAD")

    _git(repo, "checkout", "-q", "--orphan", "unrelated")
    _git(repo, "rm", "-rf", "-q", ".")
    (repo / "other.txt").write_text("x\n", encoding="utf-8")
    _commit_all(repo, "an entirely unrelated root commit")

    findings = ledger.gather(repo, base="origin/main", head="HEAD")

    assert len(findings) == 1
    finding = findings[0]
    assert finding.status is DoctorStatus.WARN
    assert finding.check == "ledger-regression"
    assert "no common ancestor" in finding.message
    assert set(finding.evidence) == {"base", "head", "target"}


# --- Never raises, even on a non-UTF-8 committed blob -----------------------


def test_non_utf8_ledger_blob_at_head_warns_and_never_accuses(
    tmp_path: Path,
) -> None:
    """The spec's Always boundary is "degrade to a WARN/OK Finding on any
    unreadable/missing input, never raise". ``cli_bridge.run_git`` decodes with
    ``text=True`` and catches only TimeoutExpired/OSError, so a tracked ledger
    holding a non-UTF-8 byte used to raise UnicodeDecodeError straight out of
    ``gather``.

    Not raising is only half of it: ``_git`` maps the decode failure to None,
    which reads identically to "absent at head" -- so a purely COSMETIC edit
    that happened to introduce a non-UTF-8 byte was reported as a
    ``ledger-deleted`` FAIL, carrying a ``git checkout <base> -- <path>``
    remedy that would discard the head ledger. Nothing un-finished here, so a
    FAIL is not an acceptable verdict; a cannot-evaluate WARN is."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_ledger(repo, "doctor", {"1-1-foo": "done"})
    base_sha = _commit_all(repo, "seed ledger")
    _branch_at(repo, "origin/main", base_sha)

    bad = repo / "_bmad-output" / "projects" / "doctor" / "planning-artifacts" / "sprint-status-ledger.yaml"
    bad.write_bytes(b"development_status:\n  1-1-f\xe9o: done\n")
    _commit_all(repo, "ledger with a non-utf8 byte")

    findings = ledger.gather(repo, base="origin/main", head="HEAD")

    assert findings  # it RETURNED rather than raised
    assert all(f.source is Source.LEDGER_REGRESSION for f in findings)
    assert [f.status for f in findings] == [DoctorStatus.WARN]
    assert findings[0].check == "ledger-unreadable"
    # A cannot-evaluate must never hand out a destructive remedy.
    assert "remedy" not in findings[0].evidence


def test_an_unreadable_base_blob_is_not_mistaken_for_a_new_ledger(
    tmp_path: Path,
) -> None:
    """The mirror-image of the case above, and the more dangerous direction.
    An unreadable blob at BASE looks exactly like "this ledger did not exist at
    base" -- which ``_check`` skips as "nothing to regress" -- so a ledger that
    un-finished two stories between the two revisions was reported as a clean
    OK, with ``ledgers_compared`` positively asserting the ledger HAD been
    compared. The listings distinguish the two cases; nothing else does."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    path = _write_ledger(repo, "doctor", {"1-1-foo": "done", "1-2-bar": "done"})
    path.write_bytes(b"development_status:\n  # caf\xe9\n  1-1-foo: done\n  1-2-bar: done\n")
    base_sha = _commit_all(repo, "seed ledger with a non-utf8 comment")
    _branch_at(repo, "origin/main", base_sha)

    path.write_bytes(b"development_status:\n  # caf\xe9\n  1-1-foo: backlog\n  1-2-bar: backlog\n")
    _commit_all(repo, "un-finish both stories")

    findings = ledger.gather(repo, base="origin/main", head="HEAD")

    assert [f.status for f in findings] == [DoctorStatus.WARN]
    assert findings[0].check == "ledger-unreadable"
    # The green that used to be reported here claimed a comparison that never
    # happened; a ledger whose blob was never read is not a ledger compared.
    assert findings[0].evidence["ledgers_compared"] == 0


def test_gather_uses_origin_main_and_head_when_no_range_is_given(
    tmp_path: Path,
) -> None:
    """The spec's Design Notes make the defaults a contract ("exactly match
    each original script's own hardcoded behavior"), and every other test in
    this file passes ``base``/``head`` explicitly -- so ``"main"`` for
    ``"origin/main"`` would have shipped green. Called with neither argument,
    against a repo whose only resolvable base ref is ``origin/main``."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_ledger(repo, "doctor", {"1-1-foo": "done"})
    base_sha = _commit_all(repo, "seed ledger")
    _branch_at(repo, "origin/main", base_sha)

    _write_ledger(repo, "doctor", {"1-1-foo": "in-progress"})
    _commit_all(repo, "un-finish the story")

    findings = ledger.gather(repo)

    assert [f.status for f in findings] == [DoctorStatus.FAIL]
    assert findings[0].check == "done-key-regressed"
    assert findings[0].evidence["base"] == "origin/main"
    assert findings[0].evidence["head"] == "HEAD"


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
    assert finding.evidence["transitions"] == [{"key": "1-1-foo", "from": "done", "to": "in-progress"}]


# --- A green verdict says how much it measured ------------------------------


def test_ok_finding_reports_how_many_ledgers_were_compared(tmp_path: Path) -> None:
    """ "Clean" and "found nothing to look at" are the same empty finding list.
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


# --- Story 25.3: the fold PR's re-key map ------------------------------------
#
# spec-one-chain-per-station CAP-3(g): a station fold renumbers every key and
# ships planning-artifacts/rekey-<date>.md. A `done` row whose key moves per
# the map -- INCLUDING a slug change, which `_tail` continuity cannot see --
# is the same row; a status flip through the map is still a regression; a map
# line naming a key that exists on neither side is dangling.


def _write_rekey(repo: Path, project: str, text: str, name: str = "rekey-2026-09-20.md") -> Path:
    p = repo / "_bmad-output" / "projects" / project / "planning-artifacts" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def _rebased_repo(tmp_path: Path) -> Path:
    """Base: a 3-epic ledger with legacy numbering and one divergent slug.
    Head: renumbered sequentially, slug fixed, map shipped."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_ledger(
        repo,
        "pyforge-marshal",
        {
            "46-1-old-slug": "done",
            "46-2-keep": "done",
            "47-1-thing": "backlog",
            "epic-46": "done",
        },
    )
    base_sha = _commit_all(repo, "seed legacy numbering")
    _branch_at(repo, "origin/main", base_sha)
    return repo


def test_rekey_pure_renumber_with_slug_change_is_continuity(tmp_path: Path) -> None:
    repo = _rebased_repo(tmp_path)
    _write_ledger(
        repo,
        "pyforge-marshal",
        {
            "1-1-new-slug": "done",  # number AND slug changed -- only the map can see it
            "1-2-keep": "done",
            "2-1-thing": "backlog",
            "epic-1": "done",
        },
    )
    _write_rekey(
        repo,
        "pyforge-marshal",
        "# fold\n46-1-old-slug -> 1-1-new-slug\n46-2-keep -> 1-2-keep\n47-1-thing -> 2-1-thing\nepic-46 -> epic-1\n",
    )
    _commit_all(repo, "rebase marshal chain")

    findings = ledger.gather(repo, base="origin/main", head="HEAD")
    assert [f.check for f in findings] == ["ledger-regression"]
    assert findings[0].status is DoctorStatus.OK


def test_rekey_without_a_map_a_slug_change_still_regresses(tmp_path: Path) -> None:
    """Pins that the map is load-bearing: `_tail` continuity covers a numeric
    prefix change on a story key, not a slug change -- and never an epic
    row (`epic-46` -> `epic-1` has no tail), so both regress without it."""
    repo = _rebased_repo(tmp_path)
    _write_ledger(
        repo,
        "pyforge-marshal",
        {
            "1-1-new-slug": "done",
            "1-2-keep": "done",
            "2-1-thing": "backlog",
            "epic-1": "done",
        },
    )
    _commit_all(repo, "rebase without shipping the map")
    findings = ledger.gather(repo, base="origin/main", head="HEAD")
    (f,) = findings
    assert f.check == "done-key-regressed" and f.status is DoctorStatus.FAIL
    assert f.evidence["keys"] == ["46-1-old-slug", "epic-46"]


def test_rekey_status_flip_through_the_map_is_still_a_regression(tmp_path: Path) -> None:
    repo = _rebased_repo(tmp_path)
    _write_ledger(
        repo,
        "pyforge-marshal",
        {
            "1-1-new-slug": "backlog",  # moved AND un-finished
            "1-2-keep": "done",
            "2-1-thing": "backlog",
            "epic-1": "done",
        },
    )
    _write_rekey(
        repo,
        "pyforge-marshal",
        "46-1-old-slug -> 1-1-new-slug\n46-2-keep -> 1-2-keep\n47-1-thing -> 2-1-thing\nepic-46 -> epic-1\n",
    )
    _commit_all(repo, "rebase and regress one row")
    findings = ledger.gather(repo, base="origin/main", head="HEAD")
    (f,) = findings
    assert f.check == "done-key-regressed" and f.status is DoctorStatus.FAIL
    assert f.evidence["transitions"] == [{"key": "1-1-new-slug", "from": "done", "to": "backlog"}]


def test_rekey_dangling_line_is_its_own_fail(tmp_path: Path) -> None:
    repo = _rebased_repo(tmp_path)
    _write_ledger(
        repo,
        "pyforge-marshal",
        {
            "1-1-new-slug": "done",
            "1-2-keep": "done",
            "2-1-thing": "backlog",
            "epic-1": "done",
        },
    )
    _write_rekey(
        repo,
        "pyforge-marshal",
        "46-1-old-slug -> 1-1-new-slug\n46-2-keep -> 1-2-keep\n"
        "47-1-thing -> 2-1-thing\nepic-46 -> epic-1\n"
        "99-9-never-existed -> 1-9-nope\n"  # old key not on base
        "46-2-keep -> 1-2-keep\n",
    )  # duplicate old key -> malformed map
    _commit_all(repo, "rebase with a bad map")
    checks = sorted(f.check for f in ledger.gather(repo, base="origin/main", head="HEAD"))
    assert checks == ["rekey-map-dangling", "rekey-map-malformed"]


def test_rekey_map_already_on_base_is_inert(tmp_path: Path) -> None:
    """Once merged, the map is in both revisions; its old keys no longer
    exist anywhere, and that must NOT read as dangling forever."""
    repo = _rebased_repo(tmp_path)
    _write_ledger(
        repo,
        "pyforge-marshal",
        {
            "1-1-new-slug": "done",
            "1-2-keep": "done",
            "2-1-thing": "backlog",
            "epic-1": "done",
        },
    )
    _write_rekey(
        repo,
        "pyforge-marshal",
        "46-1-old-slug -> 1-1-new-slug\n46-2-keep -> 1-2-keep\n47-1-thing -> 2-1-thing\nepic-46 -> epic-1\n",
    )
    merged = _commit_all(repo, "fold merged")
    _git(repo, "branch", "-f", "origin/main", merged)
    (repo / "later.txt").write_text("x\n", encoding="utf-8")
    _commit_all(repo, "a later, unrelated PR")
    findings = ledger.gather(repo, base="origin/main", head="HEAD")
    assert [f.check for f in findings] == ["ledger-regression"]
    assert findings[0].status is DoctorStatus.OK
