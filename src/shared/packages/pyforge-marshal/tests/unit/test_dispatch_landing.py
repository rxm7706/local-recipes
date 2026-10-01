"""Unit tests for dispatch landing (Story 22.4, CAP-4)."""

from __future__ import annotations

import sys
import time
import types
from pathlib import Path

import pytest
from pyforge.core.process import ProcessError, ProcessResult

from pyforge.marshal.adapters.vcs_git import VcsCommandError
from pyforge.marshal.core import policy, promotion
from pyforge.marshal.core.dispatch_harness_done import FollowupReview
from pyforge.marshal.core.dispatch_landing import (
    DispatchLandingVerdict,
    blocked_twin_promotion_text,
    landing_refusal_superseded,
    landing_was_refused,
    ledger_status_precedence,
    may_attempt_dispatch_landing,
    merge_subject_is_marshal_native,
    refuse_unverified_landing,
    union_sprint_ledger_maps,
)
from pyforge.marshal.core.dispatch_verification import DispatchVerificationVerdict
from pyforge.marshal.core.identity import normalize, render_merge_subject
from pyforge.marshal.core.journal import resolve_landing_checks_from_payload
from pyforge.marshal.core.landing_checks import CheckRun
from pyforge.marshal.core.model import Severity, Status, status_for
from pyforge.marshal.core.refs import ORIGIN_MAIN, ORIGIN_MAIN_SHORT, local_branch_ref
from pyforge.marshal.dispatch_land import (
    _SPEC_SURFACE_NAME_RE,
    _reconcile_spec_surface_drift,
    execute_dispatch_land,
)
from pyforge.marshal.ports.forge import ForgeCommandError, PrInfo


def test_refuse_unverified_landing() -> None:
    assert refuse_unverified_landing(DispatchVerificationVerdict.REFUSED) is True
    assert refuse_unverified_landing(DispatchVerificationVerdict.VERIFIED) is False


def test_union_sprint_ledger_maps_done_beats_backlog() -> None:
    merged = union_sprint_ledger_maps(
        {"a": "done", "b": "backlog"},
        {"a": "backlog", "c": "done"},
    )
    assert merged["a"] == "done"
    assert merged["b"] == "backlog"
    assert merged["c"] == "done"
    assert ledger_status_precedence("backlog", "done") == "done"


def test_may_attempt_only_when_verified_and_not_merged() -> None:
    assert may_attempt_dispatch_landing(DispatchVerificationVerdict.VERIFIED, story_merged_on_main=False)
    assert not may_attempt_dispatch_landing(DispatchVerificationVerdict.REFUSED, story_merged_on_main=False)
    assert not may_attempt_dispatch_landing(DispatchVerificationVerdict.VERIFIED, story_merged_on_main=True)


_REFUSAL = ({"code": "MRS-DISP-020", "severity": "error", "message": "merge of PR #1585 failed"},)
_WARN_ONLY = ({"code": "MRS-DISP-047", "severity": "warn", "message": "reconciled"},)


def test_only_an_error_severity_finding_is_a_refusal() -> None:
    """Story 56.1 (CAP-266)."""
    assert landing_was_refused(_REFUSAL)
    assert landing_was_refused((*_WARN_ONLY, *_REFUSAL))
    assert not landing_was_refused(_WARN_ONLY)
    assert not landing_was_refused(())


def test_a_refusal_is_superseded_only_once_its_story_is_on_main() -> None:
    """Story 56.1 (CAP-266): both a refusal and the merge are required; a
    WARN-only landing is never superseded, whatever `main` says."""
    assert landing_refusal_superseded(_REFUSAL, story_merged_on_main=True)
    assert not landing_refusal_superseded(_REFUSAL, story_merged_on_main=False)
    assert not landing_refusal_superseded(_WARN_ONLY, story_merged_on_main=True)
    assert not landing_refusal_superseded((), story_merged_on_main=True)


def test_merge_subject_is_marshal_native_with_policy_template() -> None:
    effective, _ = policy.compose(
        project_slug="pyforge-marshal",
        project={},
        flags={},
    )
    template = effective.merge_subject_template.value
    story_key = normalize("22-4-a-verified-story-lands-through-the-existing-machinery-classified-marshal-native")
    subject = render_merge_subject(story_key, template, "pyforge-marshal")
    assert merge_subject_is_marshal_native(subject, template, "pyforge-marshal")
    native = promotion.marshal_native_merged_keys((subject,), template, "pyforge-marshal")
    assert story_key in native


class FakeVcs:
    def __init__(
        self,
        *,
        merged: bool = False,
        branches: set[str] | None = None,
        worktrees: dict[str, Path] | None = None,
        conflict_paths: tuple[str, ...] | None = None,
        merged_at: frozenset[str] | None = None,
        fetch_fails: bool = False,
        unreadable_refs: frozenset[str] = frozenset(),
    ) -> None:
        """``merged_at`` (Story 72.1, CAP-280) makes ``commit_subjects`` ref-aware: the story's merge subject
        shows only at the full refs listed, never at another. Left ``None``, ``merged`` answers for any ref.
        ``fetch_fails`` makes ``fetch`` raise; ``unreadable_refs`` makes ``commit_subjects`` raise for a ref.
        ``calls`` logs the fetches, merge reads and pushes in order."""
        self._merged = merged
        self.merged_at = merged_at
        self.fetch_fails = fetch_fails
        self.unreadable_refs = unreadable_refs
        self.calls: list[tuple[str, ...]] = []
        self.pushed: list[str] = []
        # Story 22.9: branch resolution reads which branches exist and where
        # git has each checked out.
        self.branches: set[str] = set(branches or ())
        self.worktrees: dict[str, Path] = dict(worktrees or {})
        self.conflict_paths = conflict_paths if conflict_paths is not None else ()

    def merge_tree_conflict_paths(self, repo_root: Path, base: str, branch: str):
        return self.conflict_paths

    def file_text_at_ref(self, repo_root: Path, ref: str, path: str):
        return None

    def commit_subjects(self, repo_root: Path, ref: str):
        self.calls.append(("commit_subjects", ref))
        if ref in self.unreadable_refs:
            raise VcsCommandError(f"git log {ref} failed (test double)")
        merged_here = self._merged if self.merged_at is None else ref in self.merged_at
        if merged_here:
            effective, _ = policy.compose(project_slug="pyforge-marshal", project={}, flags={})
            key = normalize("22-4-example")
            subject = render_merge_subject(key, effective.merge_subject_template.value, "pyforge-marshal")
            return (subject,)
        return ()

    def branch_exists(self, _repo_root: Path, branch: str) -> bool:
        return branch in self.branches

    def worktree_path_for_branch(self, _repo_root: Path, branch: str) -> Path | None:
        return self.worktrees.get(branch)

    def push(self, repo_root: Path, branch: str) -> None:
        self.calls.append(("push", branch))
        self.pushed.append(branch)

    def resolve_ref(self, repo_root: Path, ref: str) -> str:
        return "abc123"

    def fetch(self, repo_root: Path, remote: str, ref: str) -> None:
        """Story 51.1: safe no-op default so every pre-existing ``FakeVcs()``
        construction keeps working now that ``execute_dispatch_land``
        unconditionally fetches ``origin/main`` before landing."""
        self.calls.append(("fetch", remote, ref))
        if self.fetch_fails:
            raise VcsCommandError("could not read from remote repository")

    def commits_behind(self, worktree_path: Path, tip_ref: str) -> int:
        """Story 51.1: ``0`` by default -- "already even with origin/main",
        the byte-identical-to-pre-51.1 path every pre-existing test in this
        file implicitly exercises (the merge-tree-preview check
        short-circuits immediately). Fixtures that need the check to
        actually fire use ``MergeTreePreviewVcs`` below."""
        return 0


# Story 80.1 (CAP-284): the landing reads the PR head's check runs before it merges. Every landing
# fixture in this file answers green, so the wait ends on its first poll without ever sleeping.
_GREEN_RUNS = (
    CheckRun(name="Lint / ruff", status="completed", conclusion="success"),
    CheckRun(name="Station tests / marshal", status="completed", conclusion="success"),
)


class FakeForge:
    def find_open_pr(self, repo, head_branch):
        return None

    def check_runs(self, repo, ref):
        return _GREEN_RUNS

    def create_pr(self, repo, base, head_branch, title, body):
        return PrInfo(number=42, url="https://example/pr/42", state="open", base="main")

    def update_pr(self, repo, number, title, body):
        return PrInfo(number=number, url="https://example/pr/42", state="open", base="main")

    def add_labels(self, repo, number, labels):
        return None

    def merge_pr(self, repo, number, strategy, *, expected_head_sha, delete_branch, subject):
        return None

    def pr_merge_state(self, repo, number):
        return "MERGEABLE"

    def close_pr(self, repo, number):
        return None


class FakeProcess:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], Path]] = []

    def run(self, tokens, *, cwd: Path):
        self.calls.append((list(tokens), cwd))
        return ProcessResult(returncode=0, stdout="", stderr="")


class BrokenProcess:
    """Story 51.2: a ``ProcessPort`` whose ``.run()`` always raises --
    simulates ``dispatch_land_finalize`` failing as a subprocess AFTER the
    PR has already been merged (``data["merged"] = True``)."""

    def run(self, tokens, *, cwd: Path):
        raise ProcessError("dispatch land finalize subprocess failed")


class BrokenForge(FakeForge):
    def merge_pr(self, repo, number, strategy, *, expected_head_sha, delete_branch, subject):
        raise ForgeCommandError("merge blocked")


# Story 53.2 (spec-pyforge-marshal CAP-261b): fixtures for
# `_reconcile_spec_surface_drift` -- the landing reconciles spec-surface
# drift on its own governed files before merging.


class _SurfaceFinding:
    """Duck-typed stand-in for ``pyforge.doctor.models.Finding`` -- only
    ``.check``/``.message``/``.evidence`` are read by
    ``_reconcile_spec_surface_drift``."""

    def __init__(self, check: str, message: str, path: str) -> None:
        self.check = check
        self.message = message
        self.evidence = {"path": path}


def _install_fake_spec_surface(monkeypatch, findings: tuple) -> None:
    """Install a fake ``pyforge.doctor.sources.chain`` module into
    ``sys.modules`` so ``_reconcile_spec_surface_drift``'s own
    ``from pyforge.doctor.sources.chain import gather_spec_surface``
    (re-resolved fresh on every call) finds a controllable stand-in.
    ``pyforge.doctor`` is not on this package's own pixi env (confirmed
    live: a real dispatch worktree reaches it only via the ``sys.path``
    insert onto its OWN checked-out doctor source tree), so patching the
    real module by dotted path isn't an option here."""
    fake_chain = types.ModuleType("pyforge.doctor.sources.chain")
    fake_chain.gather_spec_surface = lambda target: findings  # noqa: ARG005
    monkeypatch.setitem(sys.modules, "pyforge.doctor.sources.chain", fake_chain)


class _ReconcileVcs(FakeVcs):
    """``FakeVcs`` plus the ``changed_files``/``commit_paths`` surface
    ``_reconcile_spec_surface_drift`` needs, and a ``resolve_ref`` that
    returns a different sha on its second call -- proving the post-reconcile
    refresh in ``execute_dispatch_land`` actually re-resolves the tip rather
    than reusing the pre-reconcile sha."""

    def __init__(self, *, changed: tuple[str, ...], **kwargs) -> None:
        super().__init__(**kwargs)
        self.changed = changed
        self.committed: list[tuple[Path, tuple[Path, ...], str]] = []
        self._resolve_calls = 0

    def changed_files(self, repo_root: Path, worktree: Path, *, base: str) -> tuple[str, ...]:
        return self.changed

    def commit_paths(self, worktree: Path, paths: tuple[Path, ...], message: str) -> str:
        self.committed.append((worktree, paths, message))
        return "reconcile-commit-sha"

    def resolve_ref(self, repo_root: Path, ref: str) -> str:
        self._resolve_calls += 1
        return "pre-reconcile-sha" if self._resolve_calls == 1 else "post-reconcile-sha"


class _RaisingReconcileProcess:
    """A ``ProcessPort`` whose ``.run()`` always raises -- simulates the
    memlog-append subprocess failing to even launch."""

    def run(self, tokens, *, cwd: Path):
        raise ProcessError("memlog subprocess failed to launch")


class _RecordingForge(FakeForge):
    def __init__(self) -> None:
        self.merge_calls: list[str] = []

    def merge_pr(self, repo, number, strategy, *, expected_head_sha, delete_branch, subject):
        self.merge_calls.append(expected_head_sha.value)
        return None


def test_reconcile_spec_surface_drift_noop_when_no_drift_findings(tmp_path: Path, monkeypatch) -> None:
    """No 'drift'/'drift-presumed' findings at all -- nothing to reconcile,
    no side effects."""
    _install_fake_spec_surface(monkeypatch, ())
    worktree = tmp_path / "wt"
    worktree.mkdir()
    vcs = _ReconcileVcs(changed=())
    process = FakeProcess()
    outcome = _reconcile_spec_surface_drift(
        git_repo_root=tmp_path,
        worktree=worktree,
        head_branch="dispatch/pyforge-marshal/53.2",
        key=normalize("53-2-example"),
        run_id="run-1",
        vcs=vcs,
        process=process,
    )
    assert outcome.finding is None
    assert outcome.refuse is False
    assert process.calls == []
    assert vcs.committed == []


def test_reconcile_spec_surface_drift_skips_unrelated_pre_existing_drift(tmp_path: Path, monkeypatch) -> None:
    """A spec's drift with ZERO overlap against this branch's own changed
    files is pre-existing and unrelated -- not this landing's to reconcile
    or refuse on."""
    findings = (
        _SurfaceFinding(
            "drift",
            "path drifted — reconcile the spec, then --write-baseline --spec pyforge-marshal/spec-unrelated",
            "some/unrelated/file.py",
        ),
    )
    _install_fake_spec_surface(monkeypatch, findings)
    worktree = tmp_path / "wt"
    worktree.mkdir()
    vcs = _ReconcileVcs(changed=("this/branch/file.py",))
    process = FakeProcess()
    outcome = _reconcile_spec_surface_drift(
        git_repo_root=tmp_path,
        worktree=worktree,
        head_branch="dispatch/pyforge-marshal/53.2",
        key=normalize("53-2-example"),
        run_id=None,
        vcs=vcs,
        process=process,
    )
    assert outcome.finding is None
    assert outcome.refuse is False
    assert process.calls == []
    assert vcs.committed == []


def test_reconcile_spec_surface_drift_refuses_no_baseline_spec_this_branch_touched(tmp_path: Path, monkeypatch) -> None:
    """Story 53.2 review (B2/E1): a spec with no stamped baseline has no
    per-file drift breakdown to diff against ``changed`` at all -- fail
    closed rather than silently skip it, but only when this branch actually
    touched that spec's own tracked folder (an unrelated repo-wide
    never-baselined spec stays none of this landing's business, same as
    zero-overlap drift)."""
    _install_fake_spec_surface(
        monkeypatch,
        (
            _SurfaceFinding(
                "no-baseline",
                "pyforge-marshal/spec-gamma: run --write-baseline --spec pyforge-marshal/spec-gamma",
                "",
            ),
        ),
    )
    worktree = tmp_path / "wt"
    worktree.mkdir()
    touched = "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-gamma/spec-gamma.md"
    vcs = _ReconcileVcs(changed=(touched,))
    process = FakeProcess()
    outcome = _reconcile_spec_surface_drift(
        git_repo_root=tmp_path,
        worktree=worktree,
        head_branch="dispatch/pyforge-marshal/53.2",
        key=normalize("53-2-example"),
        run_id=None,
        vcs=vcs,
        process=process,
    )
    assert outcome.refuse is True
    assert outcome.finding is not None
    assert outcome.finding.code == "MRS-DISP-048"
    assert "pyforge-marshal/spec-gamma" in outcome.finding.message
    assert process.calls == []
    assert vcs.committed == []


def test_reconcile_spec_surface_drift_skips_no_baseline_spec_this_branch_did_not_touch(
    tmp_path: Path, monkeypatch
) -> None:
    """Story 53.2 review (B2/E1): a never-baselined spec this branch did
    not touch at all is not this landing's business -- no-op, same as
    zero-overlap drift on an already-baselined spec."""
    _install_fake_spec_surface(
        monkeypatch,
        (
            _SurfaceFinding(
                "no-baseline",
                "pyforge-marshal/spec-gamma: run --write-baseline --spec pyforge-marshal/spec-gamma",
                "",
            ),
        ),
    )
    worktree = tmp_path / "wt"
    worktree.mkdir()
    vcs = _ReconcileVcs(changed=("src/unrelated.py",))
    process = FakeProcess()
    outcome = _reconcile_spec_surface_drift(
        git_repo_root=tmp_path,
        worktree=worktree,
        head_branch="dispatch/pyforge-marshal/53.2",
        key=normalize("53-2-example"),
        run_id=None,
        vcs=vcs,
        process=process,
    )
    assert outcome.finding is None
    assert outcome.refuse is False
    assert process.calls == []
    assert vcs.committed == []


def test_reconcile_spec_surface_drift_reconciles_own_drift_across_specs(tmp_path: Path, monkeypatch) -> None:
    """The 2026-09-20 fixture shape: own drift spans more than one
    co-governing spec -- each gets its own memlog append, one scoped stamp
    names every drifted spec, the reconcile is committed and pushed, and a
    single aggregate MRS-DISP-047 names every path."""
    findings = (
        _SurfaceFinding(
            "drift",
            "path drifted — reconcile the spec, then --write-baseline --spec pyforge-marshal/spec-alpha",
            "src/a.py",
        ),
        _SurfaceFinding(
            "drift-presumed",
            "path presumed drifted — confirm it was reconciled, then --write-baseline --spec pyforge-marshal/spec-beta",
            "src/b.py",
        ),
    )
    _install_fake_spec_surface(monkeypatch, findings)
    worktree = tmp_path / "wt"
    worktree.mkdir()
    vcs = _ReconcileVcs(changed=("src/a.py", "src/b.py"))
    process = FakeProcess()
    outcome = _reconcile_spec_surface_drift(
        git_repo_root=tmp_path,
        worktree=worktree,
        head_branch="dispatch/pyforge-marshal/53.2",
        key=normalize("53-2-example"),
        run_id="run-7",
        vcs=vcs,
        process=process,
    )
    assert outcome.refuse is False
    assert outcome.finding is not None
    assert outcome.finding.code == "MRS-DISP-047"
    assert outcome.finding.severity == Severity.WARN
    assert "spec-alpha" in outcome.finding.message
    assert "spec-beta" in outcome.finding.message
    assert "src/a.py" in outcome.finding.message
    assert "src/b.py" in outcome.finding.message

    memlog_calls = [c for c in process.calls if "memlog.py" in c[0][1]]
    stamp_calls = [c for c in process.calls if "spec_surface_check.py" in c[0][1]]
    assert len(memlog_calls) == 2
    assert len(stamp_calls) == 1
    # Story 53.2 review (V1): the caller-supplied `run_id` must actually
    # reach the memlog `--text` argv, not just be accepted as a parameter.
    for tokens, _cwd in memlog_calls:
        text_arg = tokens[tokens.index("--text") + 1]
        assert "(run run-7)" in text_arg
    stamp_argv = stamp_calls[0][0]
    assert stamp_argv.count("--spec") == 2
    assert "pyforge-marshal/spec-alpha" in stamp_argv
    assert "pyforge-marshal/spec-beta" in stamp_argv
    assert "--write-baseline" in stamp_argv

    # Story 53.2 review (B4/E2): each spec's memlog append is committed
    # immediately inside the loop -- so this fixture (two specs) produces
    # three commits: one per-spec memlog commit plus the final baseline
    # -stamp commit, not one batched commit.
    assert len(vcs.committed) == 3
    for _committed_worktree, _committed_paths, commit_message in vcs.committed:
        assert "53.2" in commit_message
    assert vcs.pushed == ["dispatch/pyforge-marshal/53.2"]


def test_spec_surface_name_re_matches_doctor_message_formats() -> None:
    """Story 53.2 review (B8): ``_SPEC_SURFACE_NAME_RE`` is documented only by
    a code comment as matching doctor's exact message text -- pin that
    coupling with a test built from the three literal formats
    ``pyforge.doctor.sources.chain._drift_findings`` emits today (the
    ``no-baseline``, ``drift``, and ``drift-presumed`` kinds), so a future
    edit to either side that breaks the match fails loudly here instead of
    only inside a real dispatch landing."""
    name = "pyforge-marshal/spec-alpha"
    messages = (
        f"{name}: run --write-baseline --spec {name}",
        f"{name}: src/a.py changed but the spec's memlog did not move — "
        f"reconcile the spec, then --write-baseline --spec {name}",
        f"{name}: src/a.py changed; the memlog moved but does not name "
        f"this path — confirm it was reconciled, then --write-baseline "
        f"--spec {name}",
    )
    for message in messages:
        match = _SPEC_SURFACE_NAME_RE.search(message)
        assert match is not None, message
        assert match.group(1) == name


def test_reconcile_spec_surface_drift_reconciles_cross_project_co_governor(tmp_path: Path, monkeypatch) -> None:
    """Story 53.2 review (S3): a drifted spec named by a DIFFERENT project
    than the one being landed is handled by the same generic
    ``name.partition("/")`` string logic as an own-project spec -- this
    covers that already-correct path rather than leaving it proven only by
    inspection."""
    findings = (
        _SurfaceFinding(
            "drift",
            "other-project/spec-zeta: src/a.py changed but the spec's "
            "memlog did not move — reconcile the spec, then "
            "--write-baseline --spec other-project/spec-zeta",
            "src/a.py",
        ),
    )
    _install_fake_spec_surface(monkeypatch, findings)
    worktree = tmp_path / "wt"
    worktree.mkdir()
    vcs = _ReconcileVcs(changed=("src/a.py",))
    process = FakeProcess()
    outcome = _reconcile_spec_surface_drift(
        git_repo_root=tmp_path,
        worktree=worktree,
        head_branch="dispatch/pyforge-marshal/53.2",
        key=normalize("53-2-example"),
        run_id=None,
        vcs=vcs,
        process=process,
    )
    assert outcome.refuse is False
    assert outcome.finding is not None
    assert outcome.finding.code == "MRS-DISP-047"
    assert "other-project/spec-zeta" in outcome.finding.message

    stamp_calls = [c for c in process.calls if "spec_surface_check.py" in c[0][1]]
    assert len(stamp_calls) == 1
    assert "other-project/spec-zeta" in stamp_calls[0][0]


def test_reconcile_spec_surface_drift_refuses_foreign_drift(tmp_path: Path, monkeypatch) -> None:
    """A spec's drift names a path this branch did NOT change -- foreign
    drift is refused (MRS-DISP-048) naming the foreign path, never absorbed
    into a scoped stamp, and nothing is committed or pushed."""
    findings = (
        _SurfaceFinding(
            "drift",
            "--write-baseline --spec pyforge-marshal/spec-shared",
            "src/mine.py",
        ),
        _SurfaceFinding(
            "drift",
            "--write-baseline --spec pyforge-marshal/spec-shared",
            "src/not-mine.py",
        ),
    )
    _install_fake_spec_surface(monkeypatch, findings)
    worktree = tmp_path / "wt"
    worktree.mkdir()
    vcs = _ReconcileVcs(changed=("src/mine.py",))
    process = FakeProcess()
    outcome = _reconcile_spec_surface_drift(
        git_repo_root=tmp_path,
        worktree=worktree,
        head_branch="dispatch/pyforge-marshal/53.2",
        key=normalize("53-2-example"),
        run_id=None,
        vcs=vcs,
        process=process,
    )
    assert outcome.refuse is True
    assert outcome.finding is not None
    assert outcome.finding.code == "MRS-DISP-048"
    assert "src/not-mine.py" in outcome.finding.message
    assert process.calls == []
    assert vcs.committed == []


def test_reconcile_spec_surface_drift_refuses_when_memlog_append_exits_nonzero(tmp_path: Path, monkeypatch) -> None:
    """The memlog append subprocess runs but refuses (locked file, missing
    frontmatter, ...) -- refused (MRS-DISP-048), never silently skipped,
    nothing stamped or committed."""
    findings = (
        _SurfaceFinding(
            "drift",
            "--write-baseline --spec pyforge-marshal/spec-alpha",
            "src/a.py",
        ),
    )
    _install_fake_spec_surface(monkeypatch, findings)
    worktree = tmp_path / "wt"
    worktree.mkdir()
    vcs = _ReconcileVcs(changed=("src/a.py",))

    class _RefusingProcess:
        def __init__(self) -> None:
            self.calls: list[tuple[list[str], Path]] = []

        def run(self, tokens, *, cwd: Path):
            self.calls.append((list(tokens), cwd))
            return ProcessResult(returncode=1, stdout="", stderr="memlog locked")

    process = _RefusingProcess()
    outcome = _reconcile_spec_surface_drift(
        git_repo_root=tmp_path,
        worktree=worktree,
        head_branch="dispatch/pyforge-marshal/53.2",
        key=normalize("53-2-example"),
        run_id=None,
        vcs=vcs,
        process=process,
    )
    assert outcome.refuse is True
    assert outcome.finding is not None
    assert outcome.finding.code == "MRS-DISP-048"
    assert "spec-alpha" in outcome.finding.message
    assert vcs.committed == []


def test_reconcile_spec_surface_drift_refuses_when_memlog_process_errors(tmp_path: Path, monkeypatch) -> None:
    """The memlog append subprocess fails to even launch -- refused
    (MRS-DISP-048), same as a non-zero exit."""
    findings = (
        _SurfaceFinding(
            "drift",
            "--write-baseline --spec pyforge-marshal/spec-alpha",
            "src/a.py",
        ),
    )
    _install_fake_spec_surface(monkeypatch, findings)
    worktree = tmp_path / "wt"
    worktree.mkdir()
    vcs = _ReconcileVcs(changed=("src/a.py",))
    outcome = _reconcile_spec_surface_drift(
        git_repo_root=tmp_path,
        worktree=worktree,
        head_branch="dispatch/pyforge-marshal/53.2",
        key=normalize("53-2-example"),
        run_id=None,
        vcs=vcs,
        process=_RaisingReconcileProcess(),
    )
    assert outcome.refuse is True
    assert outcome.finding is not None
    assert outcome.finding.code == "MRS-DISP-048"
    assert vcs.committed == []


def test_reconcile_spec_surface_drift_refuses_when_per_spec_commit_fails(tmp_path: Path, monkeypatch) -> None:
    """Story 53.2 review (V2): the per-spec memlog commit (inside the
    B4/E2 loop) raising ``VcsCommandError`` refuses the landing
    (MRS-DISP-048) naming the spec, rather than proceeding to the stamp
    step with an uncommitted memlog edit left behind."""
    findings = (
        _SurfaceFinding(
            "drift",
            "--write-baseline --spec pyforge-marshal/spec-alpha",
            "src/a.py",
        ),
    )
    _install_fake_spec_surface(monkeypatch, findings)
    worktree = tmp_path / "wt"
    worktree.mkdir()

    class _CommitFailsVcs(_ReconcileVcs):
        def commit_paths(self, worktree: Path, paths: tuple[Path, ...], message: str) -> str:
            raise VcsCommandError("commit rejected")

    vcs = _CommitFailsVcs(changed=("src/a.py",))
    process = FakeProcess()
    outcome = _reconcile_spec_surface_drift(
        git_repo_root=tmp_path,
        worktree=worktree,
        head_branch="dispatch/pyforge-marshal/53.2",
        key=normalize("53-2-example"),
        run_id=None,
        vcs=vcs,
        process=process,
    )
    assert outcome.refuse is True
    assert outcome.finding is not None
    assert outcome.finding.code == "MRS-DISP-048"
    assert "spec-alpha" in outcome.finding.message
    stamp_calls = [c for c in process.calls if "spec_surface_check.py" in c[0][1]]
    assert stamp_calls == []
    assert vcs.pushed == []


def test_reconcile_spec_surface_drift_refuses_when_stamp_subprocess_exits_nonzero(tmp_path: Path, monkeypatch) -> None:
    """Story 53.2 review (V2): a non-zero exit from the scoped
    ``spec_surface_check.py --write-baseline`` stamp refuses the landing
    (MRS-DISP-048), after the per-spec memlog append/commit already
    succeeded."""
    findings = (
        _SurfaceFinding(
            "drift",
            "--write-baseline --spec pyforge-marshal/spec-alpha",
            "src/a.py",
        ),
    )
    _install_fake_spec_surface(monkeypatch, findings)
    worktree = tmp_path / "wt"
    worktree.mkdir()
    vcs = _ReconcileVcs(changed=("src/a.py",))

    class _StampRefusingProcess:
        def __init__(self) -> None:
            self.calls: list[tuple[list[str], Path]] = []

        def run(self, tokens, *, cwd: Path):
            self.calls.append((list(tokens), cwd))
            if "spec_surface_check.py" in tokens[1]:
                return ProcessResult(returncode=1, stdout="", stderr="baseline stamp refused")
            return ProcessResult(returncode=0, stdout="", stderr="")

    process = _StampRefusingProcess()
    outcome = _reconcile_spec_surface_drift(
        git_repo_root=tmp_path,
        worktree=worktree,
        head_branch="dispatch/pyforge-marshal/53.2",
        key=normalize("53-2-example"),
        run_id=None,
        vcs=vcs,
        process=process,
    )
    assert outcome.refuse is True
    assert outcome.finding is not None
    assert outcome.finding.code == "MRS-DISP-048"
    assert "baseline stamp refused" in outcome.finding.message
    assert vcs.pushed == []


def test_reconcile_spec_surface_drift_refuses_when_final_push_fails(tmp_path: Path, monkeypatch) -> None:
    """Story 53.2 review (V2): the final baseline-stamp commit succeeds
    but the push to ``head_branch`` raises ``VcsCommandError`` -- refused
    (MRS-DISP-048), never treated as a landed reconcile."""
    findings = (
        _SurfaceFinding(
            "drift",
            "--write-baseline --spec pyforge-marshal/spec-alpha",
            "src/a.py",
        ),
    )
    _install_fake_spec_surface(monkeypatch, findings)
    worktree = tmp_path / "wt"
    worktree.mkdir()

    class _PushFailsVcs(_ReconcileVcs):
        def push(self, repo_root: Path, branch: str) -> None:
            raise VcsCommandError("push rejected")

    vcs = _PushFailsVcs(changed=("src/a.py",))
    process = FakeProcess()
    outcome = _reconcile_spec_surface_drift(
        git_repo_root=tmp_path,
        worktree=worktree,
        head_branch="dispatch/pyforge-marshal/53.2",
        key=normalize("53-2-example"),
        run_id=None,
        vcs=vcs,
        process=process,
    )
    assert outcome.refuse is True
    assert outcome.finding is not None
    assert outcome.finding.code == "MRS-DISP-048"
    assert "cannot commit/push" in outcome.finding.message
    assert vcs.pushed == []


def test_execute_dispatch_land_refuses_when_resolve_ref_fails_after_reconcile_push(tmp_path: Path, monkeypatch) -> None:
    """Story 53.2 review (V2): the reconcile committed and pushed onto
    ``head_branch`` (a non-refusing MRS-DISP-047), but re-resolving the
    branch's tip afterward raises ``VcsCommandError`` -- refused
    (MRS-DISP-048) rather than merging on a stale, pre-reconcile sha."""
    _install_fake_spec_surface(
        monkeypatch,
        (
            _SurfaceFinding(
                "drift",
                "--write-baseline --spec pyforge-marshal/spec-alpha",
                "src/a.py",
            ),
        ),
    )
    worktree = tmp_path / "wt"
    worktree.mkdir()

    class _ResolveFailsAfterPushVcs(_ReconcileVcs):
        def resolve_ref(self, repo_root: Path, ref: str) -> str:
            self._resolve_calls += 1
            if self._resolve_calls == 1:
                return "pre-reconcile-sha"
            raise VcsCommandError("cannot resolve ref")

    vcs = _ResolveFailsAfterPushVcs(merged=False, changed=("src/a.py",))
    process = FakeProcess()
    forge = _RecordingForge()
    result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="22-4-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        vcs=vcs,
        forge=forge,
        process=process,
    )
    assert result.verdict == DispatchLandingVerdict.REFUSED
    findings_048 = [f for f in envelope.findings if f.code == "MRS-DISP-048"]
    assert len(findings_048) == 1
    assert "cannot resolve" in findings_048[0].message
    assert forge.merge_calls == []


def test_reconcile_spec_surface_drift_degrades_when_doctor_unreachable(tmp_path: Path, monkeypatch) -> None:
    """`pyforge.doctor` is not importable at all here (no fake module
    installed, and this package's own pixi env doesn't ship it) -- this is
    the exact path a real dispatch worktree never hits (always a full
    checkout with doctor's own source tree in place), but must degrade to
    a non-blocking MRS-DISP-047 rather than refuse the landing on an
    environment gap this story is not scoped to fix."""
    for mod in (
        "pyforge.doctor.sources.chain",
        "pyforge.doctor.sources",
        "pyforge.doctor",
    ):
        monkeypatch.delitem(sys.modules, mod, raising=False)
    worktree = tmp_path / "wt"
    worktree.mkdir()
    outcome = _reconcile_spec_surface_drift(
        git_repo_root=tmp_path,
        worktree=worktree,
        head_branch="dispatch/pyforge-marshal/53.2",
        key=normalize("53-2-example"),
        run_id=None,
        vcs=_ReconcileVcs(changed=()),
        process=FakeProcess(),
    )
    assert outcome.refuse is False
    assert outcome.finding is not None
    assert outcome.finding.code == "MRS-DISP-047"


def test_execute_dispatch_land_reconciles_own_drift_before_merging(tmp_path: Path, monkeypatch) -> None:
    """End-to-end: a landing whose branch left drift on its OWN governed
    files reconciles it before ``forge.merge_pr`` -- and the sha handed to
    ``forge.merge_pr`` (and reported in the envelope) is the POST-reconcile
    tip, not the sha resolved before the reconcile commit was pushed onto
    the branch."""
    _install_fake_spec_surface(
        monkeypatch,
        (
            _SurfaceFinding(
                "drift",
                "--write-baseline --spec pyforge-marshal/spec-alpha",
                "src/a.py",
            ),
        ),
    )
    worktree = tmp_path / "wt"
    worktree.mkdir()
    vcs = _ReconcileVcs(merged=False, changed=("src/a.py",))
    process = FakeProcess()
    forge = _RecordingForge()
    result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="22-4-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        vcs=vcs,
        forge=forge,
        process=process,
    )
    assert result.verdict == DispatchLandingVerdict.LANDED
    findings_047 = [f for f in envelope.findings if f.code == "MRS-DISP-047"]
    assert len(findings_047) == 1
    assert "spec-alpha" in findings_047[0].message
    assert forge.merge_calls == ["post-reconcile-sha"]
    assert envelope.data["head_sha"] == "post-reconcile-sha"
    # Story 53.2 review (B4/E2): one per-spec memlog commit plus the
    # final baseline-stamp commit -- two commits for this single-spec
    # fixture, not one batched commit.
    assert len(vcs.committed) == 2
    assert vcs.pushed.count("dispatch/pyforge-marshal/22.4") == 2


def test_execute_dispatch_land_refuses_on_foreign_spec_surface_drift(tmp_path: Path, monkeypatch) -> None:
    """End-to-end: foreign drift on a shared spec refuses the landing
    (MRS-DISP-048) and never reaches ``forge.merge_pr``."""
    _install_fake_spec_surface(
        monkeypatch,
        (
            _SurfaceFinding(
                "drift",
                "--write-baseline --spec pyforge-marshal/spec-shared",
                "src/mine.py",
            ),
            _SurfaceFinding(
                "drift",
                "--write-baseline --spec pyforge-marshal/spec-shared",
                "src/not-mine.py",
            ),
        ),
    )
    worktree = tmp_path / "wt"
    worktree.mkdir()
    vcs = _ReconcileVcs(merged=False, changed=("src/mine.py",))
    process = FakeProcess()
    forge = _RecordingForge()
    result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="22-4-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        vcs=vcs,
        forge=forge,
        process=process,
    )
    assert result.verdict == DispatchLandingVerdict.REFUSED
    findings_048 = [f for f in envelope.findings if f.code == "MRS-DISP-048"]
    assert len(findings_048) == 1
    assert "src/not-mine.py" in findings_048[0].message
    assert forge.merge_calls == []
    assert vcs.committed == []


def test_execute_dispatch_land_refuses_unverified(tmp_path: Path) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="22-4-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.REFUSED,
        vcs=FakeVcs(),
        forge=FakeForge(),
        process=FakeProcess(),
    )
    assert result.verdict == DispatchLandingVerdict.SKIPPED_UNVERIFIED
    assert any(f.code == "MRS-DISP-014" for f in envelope.findings)


def test_execute_dispatch_land_refuses_unknown_merge_conflicts(tmp_path: Path) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    vcs = FakeVcs(
        merged=False,
        conflict_paths=("recipes/foo/recipe.yaml",),
    )
    result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="28-20-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        vcs=vcs,
        forge=BrokenForge(),
        process=FakeProcess(),
    )
    assert result.verdict == DispatchLandingVerdict.REFUSED
    disp038 = [f for f in envelope.findings if f.code == "MRS-DISP-038"]
    assert len(disp038) == 1
    assert "recipes/foo/recipe.yaml" in disp038[0].message
    assert result.pr_number == 42
    effective, _ = policy.compose(project_slug="pyforge-marshal", project={}, flags={})
    expected_subject = render_merge_subject(
        normalize("28-20-example"), effective.merge_subject_template.value, "pyforge-marshal"
    )
    assert result.subject == expected_subject
    assert result.marshal_native is True


def test_execute_dispatch_land_refused_result_keeps_pr_facts_when_heal_fails(
    tmp_path: Path,
) -> None:
    """Story 51.2: when the forge merge fails and the heal attempt neither
    finds an escalated (non-mechanical) conflict path nor manages to heal
    (``heal.healed=False``, ``heal.escalated_paths=()`` -- no ledger-only
    conflicts to union and no stale-GitHub-state to locally advance past),
    the REFUSED result must still carry ``pr_number``/``subject``/
    ``marshal_native=True`` -- not the dataclass's ``None``/``False``
    defaults."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="28-20-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        vcs=FakeVcs(merged=False),
        forge=BrokenForge(),
        process=FakeProcess(),
    )
    assert result.verdict == DispatchLandingVerdict.REFUSED
    assert result.pr_number == 42
    effective, _ = policy.compose(project_slug="pyforge-marshal", project={}, flags={})
    expected_subject = render_merge_subject(
        normalize("28-20-example"), effective.merge_subject_template.value, "pyforge-marshal"
    )
    assert result.subject == expected_subject
    assert result.marshal_native is True
    assert any(f.code == "MRS-DISP-020" for f in envelope.findings)


def _ledger_yaml(*pairs: tuple[str, str]) -> str:
    lines = ["development_status:"]
    for key, status in pairs:
        lines.append(f"  {key}: {status}")
    lines.append("")
    return "\n".join(lines)


class HealCapableVcs(FakeVcs):
    def __init__(
        self,
        *,
        conflict_paths: tuple[str, ...],
        main_ledger: str,
        branch_ledger: str,
    ) -> None:
        super().__init__(merged=False, conflict_paths=conflict_paths)
        self.main_ledger = main_ledger
        self.branch_ledger = branch_ledger
        self.commits: list[tuple[Path, tuple[Path, ...], str]] = []
        self.merges: list[tuple[Path, str, dict[str, str]]] = []
        self.probed: list[str] = []
        self._head_sha = "abc123"

    def merge_tree_conflict_paths(self, repo_root: Path, base: str, branch: str):
        self.probed.append(base)
        return super().merge_tree_conflict_paths(repo_root, base, branch)

    def merge_base(self, repo_root: Path, a: str, b: str) -> str:
        return "base000"

    def file_text_at_ref(self, repo_root: Path, ref: str, path: str):
        if path.endswith("sprint-status-ledger.yaml"):
            if ref == "base000":
                return ""
            if ref == "refs/remotes/origin/main":
                return self.main_ledger
            return self.branch_ledger
        return None

    def commit_paths(self, repo_root: Path, paths: tuple[Path, ...], message: str):
        self.commits.append((repo_root, paths, message))
        self._head_sha = "healed222"
        return self._head_sha

    def merge_ref_resolving(self, worktree_path: Path, ref: str, *, resolutions, message: str) -> str:
        self.merges.append((worktree_path, ref, dict(resolutions)))
        for rel, text in resolutions.items():
            (worktree_path / rel).parent.mkdir(parents=True, exist_ok=True)
            (worktree_path / rel).write_text(text, encoding="utf-8")
        self._head_sha = "healed222"
        return self._head_sha

    def resolve_ref(self, repo_root: Path, ref: str) -> str:
        return self._head_sha


class HealRetryForge(BrokenForge):
    def __init__(self) -> None:
        self.merge_calls = 0

    def merge_pr(self, repo, number, strategy, *, expected_head_sha, delete_branch, subject):
        self.merge_calls += 1
        if self.merge_calls == 1:
            raise ForgeCommandError("pull request is not mergeable")


class DirtyHealVcs(FakeVcs):
    def __init__(self) -> None:
        super().__init__(merged=False, conflict_paths=())
        self.merged: list[tuple[str, str, str]] = []
        self.deleted: list[str] = []

    def merge_branch(self, repo_root: Path, branch: str, *, into: str, subject: str) -> str:
        self.merged.append((branch, into, subject))
        return "localmerge999"

    def delete_branch(self, repo_root: Path, branch: str, *, force: bool = False) -> None:
        self.deleted.append(branch)


class DirtyHealForge(BrokenForge):
    def __init__(self) -> None:
        super().__init__()
        self.closed: list[int] = []

    def pr_merge_state(self, repo, number: int) -> str:
        return "DIRTY"

    def close_pr(self, repo, number: int) -> None:
        self.closed.append(number)


def test_execute_dispatch_land_advances_main_when_merge_tree_clean_and_github_dirty(
    tmp_path: Path,
) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    vcs = DirtyHealVcs()
    forge = DirtyHealForge()
    result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="28-20-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        vcs=vcs,
        forge=forge,
        process=FakeProcess(),
    )
    assert result.verdict == DispatchLandingVerdict.LANDED
    assert envelope.data.get("local_main_advance") is True
    assert vcs.merged == [("refs/heads/dispatch/pyforge-marshal/28.20", "main", result.subject)]
    assert "main" in vcs.pushed
    assert forge.closed == [42]


def test_execute_dispatch_land_heals_ledger_only_conflict(tmp_path: Path) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    ledger_rel = "_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml"
    vcs = HealCapableVcs(
        conflict_paths=(ledger_rel,),
        main_ledger=_ledger_yaml(("28-19-x", "done")),
        branch_ledger=_ledger_yaml(("28-20-y", "backlog")),
    )
    forge = HealRetryForge()
    result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="28-20-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        vcs=vcs,
        forge=forge,
        process=FakeProcess(),
    )
    assert result.verdict == DispatchLandingVerdict.LANDED
    assert envelope.data.get("ledger_union_heal") is True
    assert forge.merge_calls == 2
    # Story 59.1 (CAP-269): probed and merged against the fetched full refname, as a merge.
    assert vcs.probed == ["refs/remotes/origin/main"]
    assert vcs.commits == []
    assert [(wt, ref) for wt, ref, _ in vcs.merges] == [(worktree, "refs/remotes/origin/main")]
    written = (worktree / ledger_rel).read_text(encoding="utf-8")
    assert "28-19-x: done" in written
    assert "28-20-y: backlog" in written


_MEMLOG_REL = "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md"


def _memlog_text(*entries: str, updated: str) -> str:
    return "---\ntopic: Marshal\nupdated: " + updated + "\n---\n\n" + "\n".join(entries) + "\n"


class _MemlogHealVcs(HealCapableVcs):
    """Story 78.1: a memlog conflicts beside the ledger; the merge base has one entry, `main` a
    second and the branch a third, each restamped."""

    def file_text_at_ref(self, repo_root: Path, ref: str, path: str):
        if path != _MEMLOG_REL:
            return super().file_text_at_ref(repo_root, ref, path)
        if ref == "base000":
            return _memlog_text("- (event) a", updated="2026-09-30T10:00")
        if ref == "refs/remotes/origin/main":
            return _memlog_text("- (event) a", "- (event) from main", updated="2026-09-30T12:00")
        return _memlog_text("- (event) a", "- (event) from branch", updated="2026-09-30T11:00")


def test_execute_dispatch_land_records_the_healed_memlog_paths(tmp_path: Path) -> None:
    """Story 78.1 (CAP-283): a landing whose conflicts are a ledger and a memlog heals both in the
    one merge, and its record names the memlog beside `ledger_union_heal`."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    ledger_rel = "_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml"
    vcs = _MemlogHealVcs(
        conflict_paths=(ledger_rel, _MEMLOG_REL),
        main_ledger=_ledger_yaml(("28-19-x", "done")),
        branch_ledger=_ledger_yaml(("28-20-y", "backlog")),
    )
    forge = HealRetryForge()
    result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="28-20-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        vcs=vcs,
        forge=forge,
        process=FakeProcess(),
    )
    assert result.verdict == DispatchLandingVerdict.LANDED
    assert envelope.data.get("ledger_union_heal") is True
    assert envelope.data.get("memlog_union_heal") == [_MEMLOG_REL]
    assert forge.merge_calls == 2
    assert [(ref, sorted(res)) for _, ref, res in vcs.merges] == [
        ("refs/remotes/origin/main", sorted([ledger_rel, _MEMLOG_REL]))
    ]
    assert (worktree / _MEMLOG_REL).read_text(encoding="utf-8") == _memlog_text(
        "- (event) a", "- (event) from main", "- (event) from branch", updated="2026-09-30T12:00"
    )


def test_execute_dispatch_land_records_no_memlog_paths_for_a_ledger_only_heal(tmp_path: Path) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    ledger_rel = "_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml"
    vcs = HealCapableVcs(
        conflict_paths=(ledger_rel,),
        main_ledger=_ledger_yaml(("28-19-x", "done")),
        branch_ledger=_ledger_yaml(("28-20-y", "backlog")),
    )
    _result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="28-20-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        vcs=vcs,
        forge=HealRetryForge(),
        process=FakeProcess(),
    )
    assert envelope.data.get("ledger_union_heal") is True
    assert "memlog_union_heal" not in envelope.data


class _HealFetchFailsVcs(HealCapableVcs):
    """The landing's first two fetches (the ALREADY_LANDED read's, Story 72.1, then the 51.1 preview
    gate's) succeed; the heal's fetch fails."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.fetches = 0

    def fetch(self, repo_root: Path, remote: str, ref: str) -> None:
        self.fetches += 1
        if self.fetches > 2:
            raise VcsCommandError("could not read from remote repository")


def test_execute_dispatch_land_skips_the_heal_when_its_fetch_fails(tmp_path: Path) -> None:
    """Story 59.1 (CAP-269): the heal never measures against a ref it could not refresh -- the
    landing refuses with MRS-DISP-020 as it would have without a heal."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    ledger_rel = "_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml"
    vcs = _HealFetchFailsVcs(
        conflict_paths=(ledger_rel,),
        main_ledger=_ledger_yaml(("28-19-x", "done")),
        branch_ledger=_ledger_yaml(("28-20-y", "backlog")),
    )
    forge = HealRetryForge()
    result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="28-20-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        vcs=vcs,
        forge=forge,
        process=FakeProcess(),
    )
    assert result.verdict == DispatchLandingVerdict.REFUSED
    refusal = [f for f in envelope.findings if f.code == "MRS-DISP-020"]
    assert refusal and "heal skipped: could not fetch origin/main" in refusal[0].message
    assert vcs.fetches == 3
    assert vcs.probed == [] and vcs.merges == []
    assert forge.merge_calls == 1


def test_execute_dispatch_land_skips_when_already_on_main(tmp_path: Path) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="22-4-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        vcs=FakeVcs(merged=True),
        forge=FakeForge(),
        process=FakeProcess(),
    )
    assert result.verdict == DispatchLandingVerdict.ALREADY_LANDED
    assert envelope.data.get("already_landed") is True


class _CreatePrSpyForge(FakeForge):
    def __init__(self) -> None:
        self.created: list[str] = []

    def create_pr(self, repo, base, head_branch, title, body):
        self.created.append(head_branch)
        return super().create_pr(repo, base, head_branch, title, body)


def _land_example(tmp_path: Path, vcs: FakeVcs, forge: FakeForge | None = None):
    worktree = tmp_path / "wt"
    worktree.mkdir()
    return execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="22-4-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        vcs=vcs,
        forge=forge if forge is not None else FakeForge(),
        process=FakeProcess(),
    )


def test_execute_dispatch_land_answers_already_landed_from_origin_main_while_local_main_lags(tmp_path: Path) -> None:
    """Story 72.1 (CAP-280): a story merged on GitHub reads landed from `origin/main`, after a fetch,
    though local `main` (the primary checkout, not yet fast-forwarded) lacks the merge -- no push, no PR."""
    vcs = FakeVcs(merged_at=frozenset({ORIGIN_MAIN}))
    forge = _CreatePrSpyForge()

    result, envelope = _land_example(tmp_path, vcs, forge)

    assert result.verdict == DispatchLandingVerdict.ALREADY_LANDED
    assert envelope.data.get("already_landed") is True
    assert vcs.pushed == []
    assert forge.created == []
    assert vcs.calls.index(("fetch", "origin", "main")) < vcs.calls.index(("commit_subjects", ORIGIN_MAIN))
    assert ("commit_subjects", local_branch_ref("main")) not in vcs.calls


def test_execute_dispatch_land_does_not_read_a_merge_only_local_main_carries_as_landed(tmp_path: Path) -> None:
    """The reverse: a merge at `refs/heads/main` alone is no merge on `origin/main`, so the landing proceeds."""
    vcs = FakeVcs(merged_at=frozenset({local_branch_ref("main")}))

    result, envelope = _land_example(tmp_path, vcs)

    assert result.verdict == DispatchLandingVerdict.LANDED
    assert envelope.data.get("already_landed") is not True
    assert vcs.pushed == ["dispatch/pyforge-marshal/22.4"]


def test_execute_dispatch_land_still_reads_origin_main_when_its_fetch_fails(tmp_path: Path) -> None:
    vcs = FakeVcs(merged_at=frozenset({ORIGIN_MAIN}), fetch_fails=True)

    result, _envelope = _land_example(tmp_path, vcs)

    assert result.verdict == DispatchLandingVerdict.ALREADY_LANDED
    assert ("fetch", "origin", "main") in vcs.calls
    assert ("commit_subjects", ORIGIN_MAIN) in vcs.calls
    assert vcs.pushed == []


def test_execute_dispatch_land_refuses_naming_origin_main_when_its_history_is_unreadable(tmp_path: Path) -> None:
    # Local `main` carries the merge: an unreadable `origin/main` is neither landed nor read from local.
    vcs = FakeVcs(merged_at=frozenset({local_branch_ref("main")}), unreadable_refs=frozenset({ORIGIN_MAIN}))
    forge = _CreatePrSpyForge()

    result, envelope = _land_example(tmp_path, vcs, forge)

    assert result.verdict == DispatchLandingVerdict.REFUSED
    refusal = [finding for finding in envelope.findings if finding.code == "MRS-DISP-016"]
    assert len(refusal) == 1
    assert ORIGIN_MAIN_SHORT in refusal[0].message
    assert "'main' history" not in refusal[0].message
    assert vcs.pushed == []
    assert forge.created == []


# -- Story 73.1 (CAP-281): a follow-up review run is landed by its own head ---------------------------


class _OwnHeadVcs(FakeVcs):
    """``FakeVcs`` plus the ancestry read a follow-up landing makes: the run's own head (``resolve_ref``'s
    ``abc123``) is an ancestor of ``origin/main`` exactly when ``own_head_on_origin_main``. ``merge_base``
    answers the head itself when it is (``git merge-base head origin/main == head``), another commit when
    it is not."""

    def __init__(self, *, own_head_on_origin_main: bool, merge_base_fails: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self.own_head_on_origin_main = own_head_on_origin_main
        self.merge_base_fails = merge_base_fails

    def merge_base(self, repo_root: Path, a: str, b: str) -> str:
        self.calls.append(("merge_base", a, b))
        if self.merge_base_fails:
            raise VcsCommandError("git merge-base failed (test double)")
        return a if self.own_head_on_origin_main else "0ldbase"


class _RecordingProcess(FakeProcess):
    """``FakeProcess`` that the finalize subprocess's argv can be read back from."""

    @property
    def finalize_argv(self) -> list[str]:
        [(tokens, _cwd)] = self.calls
        return tokens


def _land_followup(
    tmp_path: Path,
    vcs: FakeVcs,
    *,
    followup_review: FollowupReview | None,
    forge: FakeForge | None = None,
    process: FakeProcess | None = None,
):
    worktree = tmp_path / "wt"
    worktree.mkdir(exist_ok=True)
    kwargs = {"followup_review": followup_review} if followup_review is not None else {}
    return execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="22-4-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        vcs=vcs,
        forge=forge if forge is not None else FakeForge(),
        process=process if process is not None else FakeProcess(),
        **kwargs,
    )


def _example_merge_subject() -> str:
    effective, _ = policy.compose(project_slug="pyforge-marshal", project={}, flags={})
    return render_merge_subject(normalize("22-4-example"), effective.merge_subject_template.value, "pyforge-marshal")


def test_a_follow_up_run_merges_its_branch_though_the_stories_first_merge_is_on_origin_main(tmp_path: Path) -> None:
    """The story's merge subject is on `origin/main` (its first landing); the run's own head is not."""
    vcs = _OwnHeadVcs(merged_at=frozenset({ORIGIN_MAIN}), own_head_on_origin_main=False)
    forge = _CreatePrSpyForge()
    process = _RecordingProcess()

    result, envelope = _land_followup(
        tmp_path, vcs, followup_review=FollowupReview(dw_id="DW-FRR-22-4"), forge=forge, process=process
    )

    assert result.verdict == DispatchLandingVerdict.LANDED
    assert envelope.data.get("already_landed") is not True
    assert vcs.pushed == ["dispatch/pyforge-marshal/22.4"]
    assert [ref.value for ref in forge.created] == ["dispatch/pyforge-marshal/22.4"]
    assert result.subject == _example_merge_subject()
    # The run's own head is what is judged -- against the full `origin/main` ref.
    assert ("merge_base", "abc123", ORIGIN_MAIN) in vcs.calls


def test_a_follow_up_run_whose_head_is_on_origin_main_is_already_landed(tmp_path: Path) -> None:
    # The story's key is on NO merge subject here: the head's ancestry alone answers.
    vcs = _OwnHeadVcs(merged=False, own_head_on_origin_main=True)
    forge = _CreatePrSpyForge()
    process = _RecordingProcess()

    result, envelope = _land_followup(
        tmp_path, vcs, followup_review=FollowupReview(dw_id="DW-FRR-22-4"), forge=forge, process=process
    )

    assert result.verdict == DispatchLandingVerdict.ALREADY_LANDED
    assert envelope.data.get("already_landed") is True
    assert vcs.pushed == []
    assert forge.created == []
    assert process.calls == []


def test_a_follow_up_run_is_judged_by_its_head_even_when_the_stories_merge_is_on_origin_main_and_the_head_is_too(
    tmp_path: Path,
) -> None:
    vcs = _OwnHeadVcs(merged_at=frozenset({ORIGIN_MAIN}), own_head_on_origin_main=True)

    result, _envelope = _land_followup(tmp_path, vcs, followup_review=FollowupReview(dw_id=None))

    assert result.verdict == DispatchLandingVerdict.ALREADY_LANDED
    assert vcs.pushed == []


def test_a_follow_up_landing_names_the_row_and_the_merge_subject_to_finalize(tmp_path: Path) -> None:
    process = _RecordingProcess()

    result, _envelope = _land_followup(
        tmp_path,
        _OwnHeadVcs(merged_at=frozenset({ORIGIN_MAIN}), own_head_on_origin_main=False),
        followup_review=FollowupReview(dw_id="DW-FRR-22-4"),
        process=process,
    )

    assert result.verdict == DispatchLandingVerdict.LANDED
    argv = process.finalize_argv
    assert argv[-5:] == [
        str(tmp_path / "wt"),
        "--followup-review-id",
        "DW-FRR-22-4",
        "--landing-subject",
        _example_merge_subject(),
    ]


def test_a_follow_up_landing_with_no_row_passes_finalize_neither_flag(tmp_path: Path) -> None:
    process = _RecordingProcess()

    result, _envelope = _land_followup(
        tmp_path,
        _OwnHeadVcs(merged_at=frozenset({ORIGIN_MAIN}), own_head_on_origin_main=False),
        followup_review=FollowupReview(dw_id=None),
        process=process,
    )

    assert result.verdict == DispatchLandingVerdict.LANDED
    assert process.finalize_argv[-1] == str(tmp_path / "wt")
    assert "--followup-review-id" not in process.finalize_argv
    assert "--landing-subject" not in process.finalize_argv


def test_a_follow_up_landing_refuses_when_it_cannot_read_its_own_ancestry(tmp_path: Path) -> None:
    vcs = _OwnHeadVcs(merged_at=frozenset({ORIGIN_MAIN}), own_head_on_origin_main=False, merge_base_fails=True)
    forge = _CreatePrSpyForge()

    result, envelope = _land_followup(tmp_path, vcs, followup_review=FollowupReview(dw_id="DW-FRR-22-4"), forge=forge)

    assert result.verdict == DispatchLandingVerdict.REFUSED
    [refusal] = [finding for finding in envelope.findings if finding.code == "MRS-DISP-017"]
    assert ORIGIN_MAIN_SHORT in refusal.message
    assert vcs.pushed == []
    assert forge.created == []


def test_a_normal_run_is_still_already_landed_from_the_stories_merge_and_never_reads_ancestry(tmp_path: Path) -> None:
    """The normal run on the very repository the follow-up tests use: judged by the key, as today."""
    vcs = _OwnHeadVcs(merged_at=frozenset({ORIGIN_MAIN}), own_head_on_origin_main=False)

    result, envelope = _land_followup(tmp_path, vcs, followup_review=None)

    assert result.verdict == DispatchLandingVerdict.ALREADY_LANDED
    assert envelope.data.get("already_landed") is True
    assert not any(call[0] == "merge_base" for call in vcs.calls)
    assert vcs.pushed == []


def test_a_normal_landing_hands_finalize_the_same_argv_as_before(tmp_path: Path) -> None:
    process = _RecordingProcess()

    result, envelope = _land_followup(tmp_path, FakeVcs(merged=False), followup_review=None, process=process)

    assert result.verdict == DispatchLandingVerdict.LANDED
    assert process.finalize_argv[1:] == [
        "-m",
        "pyforge.marshal.dispatch_land_finalize",
        "pyforge-marshal",
        "22.4",
        str(tmp_path / "wt"),
    ]
    assert "followup_review" not in envelope.data


def test_execute_dispatch_land_pushes_branch_when_verified(tmp_path: Path) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    vcs = FakeVcs(merged=False)
    process = FakeProcess()
    result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="22-4-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        vcs=vcs,
        forge=FakeForge(),
        process=process,
    )
    assert vcs.pushed == ["dispatch/pyforge-marshal/22.4"]
    assert result.verdict == DispatchLandingVerdict.LANDED
    assert result.marshal_native is True
    assert result.pr_number == 42
    # Story 51.2 / Verification Gap: the dispatch_land_finalize subprocess
    # boundary must actually receive the worktree it was given.
    assert len(process.calls) == 1
    assert process.calls[0][0][-1] == str(worktree)


def test_execute_dispatch_land_refused_result_keeps_pr_facts_after_merge(
    tmp_path: Path,
) -> None:
    """Story 51.2: when the PR is already merged (``data["merged"] = True``)
    but the ``dispatch_land_finalize`` subprocess then raises
    ``ProcessError``, the REFUSED result must still carry the ``pr_number``
    and ``subject`` that were already known at that point in execution, and
    ``marshal_native=True`` (the check that gates ``merge_pr`` already
    passed) -- not the dataclass's ``None``/``False`` defaults."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    vcs = FakeVcs(merged=False)
    result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="22-4-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        vcs=vcs,
        forge=FakeForge(),
        process=BrokenProcess(),
    )
    assert result.verdict == DispatchLandingVerdict.REFUSED
    assert result.pr_number == 42
    effective, _ = policy.compose(project_slug="pyforge-marshal", project={}, flags={})
    expected_subject = render_merge_subject(
        normalize("22-4-example"), effective.merge_subject_template.value, "pyforge-marshal"
    )
    assert result.subject == expected_subject
    assert result.marshal_native is True
    assert any(f.code == "MRS-DISP-020" for f in envelope.findings)
    assert envelope.data.get("merged") is True


class ExitingProcess:
    """Story 68.1: a ``ProcessPort`` whose ``.run()`` returns a finalize that EXITED non-zero -- the
    real ``PosixProcess.run`` does not raise on a non-zero exit, it returns the ``ProcessResult``."""

    def __init__(self, *, returncode: int = 1, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.calls: list[list[str]] = []

    def run(self, tokens, *, cwd):
        self.calls.append(list(tokens))
        return ProcessResult(returncode=self.returncode, stdout=self.stdout, stderr=self.stderr)


_FINALIZE_STDERR = (
    "finding MRS-DISP-051: the landed story's ledger key does not read done on origin/main: "
    "64-1-a-landing reads 'backlog' -- the promote + ledger is still owed"
)


def _land_with(tmp_path: Path, process):
    worktree = tmp_path / "wt"
    worktree.mkdir()
    return execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="22-4-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        vcs=FakeVcs(merged=False),
        forge=FakeForge(),
        process=process,
    )


def test_execute_dispatch_land_refuses_when_finalize_exits_non_zero(tmp_path: Path) -> None:
    """Story 68.1 AC 7 (CAP-277): finalize exiting 1 (its `MRS-DISP-051`: the landed key does not read `done`
    on `origin/main`) is REFUSED with the PR facts and `MRS-DISP-020` naming the exit code and finalize's
    stderr -- the result a finalize launch failure already produces, which `marshal status` and
    `fleet-picture` render as the promote + ledger still owed. Removing the exit-code read lands it
    `landed` and fails this test (mutation)."""
    process = ExitingProcess(returncode=1, stderr=_FINALIZE_STDERR)

    result, envelope = _land_with(tmp_path, process)

    assert len(process.calls) == 1
    assert result.verdict == DispatchLandingVerdict.REFUSED
    assert result.pr_number == 42
    assert result.marshal_native is True
    effective, _ = policy.compose(project_slug="pyforge-marshal", project={}, flags={})
    assert result.subject == render_merge_subject(
        normalize("22-4-example"), effective.merge_subject_template.value, "pyforge-marshal"
    )
    assert envelope.data.get("merged") is True
    [finding] = [f for f in envelope.findings if f.code == "MRS-DISP-020"]
    assert finding.severity.name == "ERROR"
    assert "exited with code 1" in finding.message
    assert _FINALIZE_STDERR in finding.message
    assert "22.4" in finding.message
    assert status_for(envelope.verdict) is not Status.OK


def test_execute_dispatch_land_names_finalize_stdout_when_it_wrote_no_stderr(tmp_path: Path) -> None:
    _result, envelope = _land_with(tmp_path, ExitingProcess(returncode=3, stdout="promotion refused"))

    [finding] = [f for f in envelope.findings if f.code == "MRS-DISP-020"]
    assert "exited with code 3" in finding.message
    assert "promotion refused" in finding.message


def test_execute_dispatch_land_names_only_the_exit_code_when_finalize_wrote_nothing(tmp_path: Path) -> None:
    _result, envelope = _land_with(tmp_path, ExitingProcess(returncode=70))

    [finding] = [f for f in envelope.findings if f.code == "MRS-DISP-020"]
    assert finding.message.endswith("finalize exited with code 70")


def test_execute_dispatch_land_keeps_the_tail_of_a_crashed_finalizes_traceback(tmp_path: Path) -> None:
    """A crashed finalize's traceback can run to kilobytes; the finding keeps its tail (the exception)."""
    traceback = "Traceback (most recent call last):\n" + ('  File "x.py", line 1, in f\n' * 400) + "ValueError: boom"
    _result, envelope = _land_with(tmp_path, ExitingProcess(returncode=1, stderr=traceback))

    [finding] = [f for f in envelope.findings if f.code == "MRS-DISP-020"]
    assert finding.message.endswith("ValueError: boom")
    assert "..." in finding.message
    assert len(finding.message) < 2_000


def test_execute_dispatch_land_is_landed_and_clean_when_finalize_exits_zero(tmp_path: Path) -> None:
    """Story 68.1 AC 9: a promotion that reaches `origin/main` leaves finalize at exit 0 and the landing
    `landed`, with no ERROR finding."""
    result, envelope = _land_with(tmp_path, ExitingProcess(returncode=0))

    assert result.verdict == DispatchLandingVerdict.LANDED
    assert result.merge_sha == "abc123"
    # (A WARN such as MRS-DISP-047 -- no doctor source tree in this env -- never refuses a landing.)
    assert [f for f in envelope.findings if f.severity is Severity.ERROR] == []
    assert not any(f.code == "MRS-DISP-020" for f in envelope.findings)
    assert status_for(envelope.verdict) is Status.OK


def test_execute_dispatch_land_refused_result_keeps_pr_facts_before_merge_native_check(
    tmp_path: Path, monkeypatch
) -> None:
    """Story 51.2: when the rendered merge subject fails the marshal-native
    check (``MRS-DISP-019``, before any merge is attempted), the REFUSED
    result must still carry the ``pr_number``/``subject`` already known at
    that point -- but ``marshal_native`` stays the dataclass default
    ``False``, since that's the check's real (failed) outcome here, not a
    guess."""
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land.merge_subject_is_marshal_native",
        lambda *args, **kwargs: False,
    )
    worktree = tmp_path / "wt"
    worktree.mkdir()
    result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="22-4-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        vcs=FakeVcs(merged=False),
        forge=FakeForge(),
        process=FakeProcess(),
    )
    assert result.verdict == DispatchLandingVerdict.REFUSED
    assert result.pr_number == 42
    effective, _ = policy.compose(project_slug="pyforge-marshal", project={}, flags={})
    expected_subject = render_merge_subject(
        normalize("22-4-example"), effective.merge_subject_template.value, "pyforge-marshal"
    )
    assert result.subject == expected_subject
    assert result.marshal_native is False
    assert any(f.code == "MRS-DISP-019" for f in envelope.findings)


def test_unverified_never_lands(tmp_path: Path) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    result, _ = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="22-4-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.REFUSED,
        vcs=FakeVcs(),
        forge=BrokenForge(),
        process=FakeProcess(),
    )
    assert result.verdict != DispatchLandingVerdict.LANDED
    assert result.pr_number is None


# --------------------------------------------------------------------------
# Story 22.9: landing resolves the station-scoped branch, and still finds an
# in-flight run left on the pre-22.9 `marshal/<key>` name.
# --------------------------------------------------------------------------


def test_execute_dispatch_land_lands_an_in_flight_legacy_branch(tmp_path: Path) -> None:
    """A run that started before 22.9 lands from `marshal/<key>` -- git has
    that branch checked out at THIS run's worktree, so it is attributable."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    vcs = FakeVcs(merged=False, worktrees={"marshal/22.4": worktree})
    result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="22-4-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        vcs=vcs,
        forge=FakeForge(),
        process=FakeProcess(),
    )
    assert vcs.pushed == ["marshal/22.4"]
    assert envelope.data["branch"] == "marshal/22.4"
    assert result.verdict == DispatchLandingVerdict.LANDED


def test_execute_dispatch_land_refuses_another_stations_legacy_branch(
    tmp_path: Path,
) -> None:
    """A legacy branch checked out somewhere that is NOT this run's worktree
    is never pushed and merged under this station's story key."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    theirs = tmp_path / "someone-elses-tree"
    theirs.mkdir()
    vcs = FakeVcs(merged=False, worktrees={"marshal/22.4": theirs})
    result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="22-4-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        vcs=vcs,
        forge=FakeForge(),
        process=FakeProcess(),
    )
    assert vcs.pushed == []
    assert result.verdict == DispatchLandingVerdict.REFUSED
    refusals = [f for f in envelope.findings if f.code == "MRS-DISP-030"]
    assert len(refusals) == 1
    assert "marshal/22.4" in refusals[0].message
    assert "Land that branch first" in refusals[0].message


def test_execute_dispatch_land_refuses_an_unattributable_preserved_branch(
    tmp_path: Path,
) -> None:
    """A preserved legacy branch with no worktree cannot be attributed, so
    landing refuses rather than pushing a branch it did not verify."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    vcs = FakeVcs(merged=False, branches={"marshal/22.4"})
    result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="22-4-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        vcs=vcs,
        forge=FakeForge(),
        process=FakeProcess(),
    )
    assert vcs.pushed == []
    assert result.verdict == DispatchLandingVerdict.REFUSED
    assert any(f.code == "MRS-DISP-030" for f in envelope.findings)


# --------------------------------------------------------------------------
# Story 51.1: verification sees the merge result -- `dispatch land` re-runs
# `verify_commands` against the tree `git merge-tree --write-tree` would
# actually produce whenever the branch is behind `origin/main`, catching a
# break the branch's own tree never exposes (the 2026-09-18 50.4/27.5
# incident: an operator-composed merge commit called `bare_merge.py` with 2
# args against a rewired 3-arg signature, and no verification pass -- every
# one of which only ever ran against the branch's own tree -- ever saw it).
# --------------------------------------------------------------------------


class MergeTreePreviewVcs(FakeVcs):
    """Layers Story 51.1's four merge-tree-preview primitives on top of
    ``FakeVcs`` -- mirrors ``HealCapableVcs``'s own pattern of adding
    fixture-specific behavior in a subclass rather than widening the shared
    ``FakeVcs`` construction every other test in this file already relies
    on."""

    def __init__(
        self,
        *,
        behind: int = 1,
        tree_oid: str | None = "preview-tree-oid",
        fetch_raises: bool = False,
        add_worktree_raises: bool = False,
        remove_worktree_raises: bool = False,
    ) -> None:
        super().__init__(merged=False)
        self.behind = behind
        self.tree_oid = tree_oid
        self.fetch_raises = fetch_raises
        self.add_worktree_raises = add_worktree_raises
        self.remove_worktree_raises = remove_worktree_raises
        self.fetch_calls: list[tuple[str, str]] = []
        self.merge_tree_write_calls: list[tuple[str, str]] = []
        self.add_worktree_for_tree_calls: list[tuple[Path, str, str]] = []
        self.removed_worktrees: list[Path] = []
        self.pruned_repo_roots: list[Path] = []
        self.preview_home: Path | None = None

    def fetch(self, repo_root: Path, remote: str, ref: str) -> None:
        self.fetch_calls.append((remote, ref))
        if self.fetch_raises:
            raise VcsCommandError("network unreachable")

    def commits_behind(self, worktree_path: Path, tip_ref: str) -> int:
        return self.behind

    def merge_tree_write(self, repo_root: Path, base: str, branch: str) -> str | None:
        self.merge_tree_write_calls.append((base, branch))
        return self.tree_oid

    def add_worktree_for_tree(self, repo_root: Path, home: Path, tree_oid: str, *, parent: str) -> None:
        self.add_worktree_for_tree_calls.append((home, tree_oid, parent))
        self.preview_home = home
        if self.add_worktree_raises:
            raise VcsCommandError("git worktree add --detach failed: disk full")

    def remove_worktree(self, repo_root: Path, home: Path, *, force: bool = False) -> None:
        self.removed_worktrees.append(home)
        if self.remove_worktree_raises:
            raise VcsCommandError("git worktree remove failed: resource busy")

    def prune_worktrees(self, repo_root: Path) -> None:
        self.pruned_repo_roots.append(repo_root)


class PreviewAwareProcess(FakeProcess):
    """A ``ProcessPort`` that fails only when ``cwd`` is the merge-tree
    preview worktree -- ``vcs.preview_home`` is set by
    ``add_worktree_for_tree`` before ``run_verify_commands_only`` ever calls
    ``process.run(..., cwd=preview_home)`` (Story 51.1's execution order),
    so this reproduces the 50.4/27.5 incident precisely: the branch's own
    verification (a different ``cwd``) stays green, and only the merge-tree
    preview's own run breaks."""

    def __init__(self, *, vcs: MergeTreePreviewVcs, stderr: str) -> None:
        super().__init__()
        self._vcs = vcs
        self._stderr = stderr

    def run(self, tokens, *, cwd: Path):
        self.calls.append((list(tokens), cwd))
        if self._vcs.preview_home is not None and cwd == self._vcs.preview_home:
            return ProcessResult(returncode=1, stdout="", stderr=self._stderr)
        return ProcessResult(returncode=0, stdout="ok", stderr="")


def test_execute_dispatch_land_refuses_when_merge_tree_preview_is_red(
    tmp_path: Path,
) -> None:
    """The 50.4/27.5 fixture: branch verification is already green
    (``verification_verdict=VERIFIED``) and the merge itself is git-clean,
    but the tree ``git merge-tree --write-tree origin/main <head>`` would
    actually produce breaks a verify command with a runtime error no
    branch-only verification pass ever saw."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    vcs = MergeTreePreviewVcs(behind=2, tree_oid="preview-tree-oid")
    process = PreviewAwareProcess(
        vcs=vcs,
        stderr="TypeError: bare_merge() takes 2 positional arguments but 3 were given",
    )
    effective, _ = policy.compose(
        project_slug="pyforge-marshal",
        project={"verify_commands": ["pixi run pyforge-marshal-test"]},
        flags={},
    )
    result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="51-1-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        effective=effective,
        vcs=vcs,
        forge=FakeForge(),
        process=process,
    )
    assert result.verdict == DispatchLandingVerdict.REFUSED
    disp044 = [f for f in envelope.findings if f.code == "MRS-DISP-044"]
    assert len(disp044) == 1
    assert "TypeError: bare_merge()" in disp044[0].message
    assert "pixi run pyforge-marshal-test" in disp044[0].message
    assert result.pr_number == 42
    assert result.marshal_native is True
    # the throwaway worktree is always removed, even though it refused.
    assert vcs.removed_worktrees == [vcs.preview_home]


def test_execute_dispatch_land_lands_when_merge_tree_preview_is_clean(
    tmp_path: Path,
) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    vcs = MergeTreePreviewVcs(behind=3, tree_oid="preview-tree-oid")
    process = FakeProcess()
    effective, _ = policy.compose(project_slug="pyforge-marshal", project={"verify_commands": ["true"]}, flags={})
    result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="51-1-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        effective=effective,
        vcs=vcs,
        forge=FakeForge(),
        process=process,
    )
    assert result.verdict == DispatchLandingVerdict.LANDED
    assert not any(f.code == "MRS-DISP-044" for f in envelope.findings)
    assert len(vcs.add_worktree_for_tree_calls) == 1
    assert vcs.removed_worktrees == [vcs.preview_home]


def test_execute_dispatch_land_skips_merge_tree_check_when_even_with_origin_main(
    tmp_path: Path,
) -> None:
    """``commits_behind == 0`` must verify exactly once, byte-identical to
    pre-51.1 behavior -- no ``merge_tree_write``/``add_worktree_for_tree``
    calls at all."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    vcs = MergeTreePreviewVcs(behind=0)
    result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="51-1-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        vcs=vcs,
        forge=FakeForge(),
        process=FakeProcess(),
    )
    assert result.verdict == DispatchLandingVerdict.LANDED
    assert vcs.merge_tree_write_calls == []
    assert vcs.add_worktree_for_tree_calls == []
    assert vcs.removed_worktrees == []
    # The ALREADY_LANDED read's fetch (Story 72.1), then the preview gate's own.
    assert vcs.fetch_calls == [("origin", "main"), ("origin", "main")]
    assert not any(f.code == "MRS-DISP-044" for f in envelope.findings)


def test_execute_dispatch_land_falls_through_on_a_real_merge_tree_conflict(
    tmp_path: Path,
) -> None:
    """``merge_tree_write`` returning ``None`` is a real git-detected
    conflict -- already owned by the existing ``MRS-DISP-038``/heal path,
    not this story's concern. Lands normally here because the forge merge
    itself succeeds without ever needing to heal anything."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    vcs = MergeTreePreviewVcs(behind=1, tree_oid=None)
    result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="51-1-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        vcs=vcs,
        forge=FakeForge(),
        process=FakeProcess(),
    )
    assert result.verdict == DispatchLandingVerdict.LANDED
    assert vcs.add_worktree_for_tree_calls == []
    assert not any(f.code == "MRS-DISP-044" for f in envelope.findings)


def test_execute_dispatch_land_refuses_when_behind_check_is_unevaluable(
    tmp_path: Path,
) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    vcs = MergeTreePreviewVcs(fetch_raises=True)
    result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="51-1-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        vcs=vcs,
        forge=FakeForge(),
        process=FakeProcess(),
    )
    assert result.verdict == DispatchLandingVerdict.REFUSED
    disp044 = [f for f in envelope.findings if f.code == "MRS-DISP-044"]
    assert len(disp044) == 1
    assert result.pr_number == 42
    assert result.marshal_native is True


def test_execute_dispatch_land_refuses_when_merge_tree_write_raises(
    tmp_path: Path,
) -> None:
    """Review finding (2026-09-19): the ``merge_tree_write``-raises branch
    had no orchestration-level test at all -- unlike the ``fetch``-raises
    branch, which shares its ``except`` block with ``commits_behind``."""
    worktree = tmp_path / "wt"
    worktree.mkdir()

    class RaisingMergeTreeWriteVcs(MergeTreePreviewVcs):
        def merge_tree_write(self, repo_root: Path, base: str, branch: str) -> str | None:
            self.merge_tree_write_calls.append((base, branch))
            raise VcsCommandError("git merge-tree crashed")

    vcs = RaisingMergeTreeWriteVcs(behind=1)
    result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="51-1-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        vcs=vcs,
        forge=FakeForge(),
        process=FakeProcess(),
    )
    assert result.verdict == DispatchLandingVerdict.REFUSED
    disp044 = [f for f in envelope.findings if f.code == "MRS-DISP-044"]
    assert len(disp044) == 1
    assert "cannot preview the merge" in disp044[0].message
    assert vcs.add_worktree_for_tree_calls == []


def test_execute_dispatch_land_cleans_up_when_add_worktree_for_tree_raises(
    tmp_path: Path,
) -> None:
    """Review finding (2026-09-19): the ORIGINAL code returned immediately
    when ``add_worktree_for_tree`` raised, with no cleanup attempt at all --
    violating the spec's own "always removed (best-effort)" acceptance
    criterion. Cleanup must now be attempted on this path too."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    vcs = MergeTreePreviewVcs(behind=1, tree_oid="preview-tree-oid", add_worktree_raises=True)
    result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="51-1-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        vcs=vcs,
        forge=FakeForge(),
        process=FakeProcess(),
    )
    assert result.verdict == DispatchLandingVerdict.REFUSED
    disp044 = [f for f in envelope.findings if f.code == "MRS-DISP-044"]
    assert len(disp044) == 1
    assert "cannot materialize the merge-tree preview" in disp044[0].message
    assert vcs.removed_worktrees == [vcs.preview_home]


def test_execute_dispatch_land_falls_back_to_rmtree_when_remove_worktree_raises(
    tmp_path: Path,
) -> None:
    """Review finding (2026-09-19): a failed ``remove_worktree`` was
    swallowed with no fallback, unlike ``merge_branch``'s own precedent
    (``adapters/vcs_git.py``), which falls back to a raw ``shutil.rmtree``
    plus ``git worktree prune`` -- otherwise the preview worktree is
    permanently orphaned rather than just invisible."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    vcs = MergeTreePreviewVcs(behind=3, tree_oid="preview-tree-oid", remove_worktree_raises=True)
    process = FakeProcess()
    effective, _ = policy.compose(project_slug="pyforge-marshal", project={"verify_commands": ["true"]}, flags={})
    result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="51-1-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        effective=effective,
        vcs=vcs,
        forge=FakeForge(),
        process=process,
    )
    assert result.verdict == DispatchLandingVerdict.LANDED
    assert vcs.removed_worktrees == [vcs.preview_home]
    assert vcs.pruned_repo_roots == [tmp_path]


def test_execute_dispatch_land_mutation_without_merge_tree_check_lands_green(tmp_path: Path, monkeypatch) -> None:
    """Mutation test: stubbing the merge-tree-preview check to a no-op makes
    the 50.4/27.5 fixture land GREEN -- proving THIS check, not some other
    mechanism, is what refuses it."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    vcs = MergeTreePreviewVcs(behind=2, tree_oid="preview-tree-oid")
    process = PreviewAwareProcess(
        vcs=vcs,
        stderr="TypeError: bare_merge() takes 2 positional arguments but 3 were given",
    )
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land._refuse_via_merge_tree_preview",
        lambda **_kwargs: None,
    )
    effective, _ = policy.compose(
        project_slug="pyforge-marshal",
        project={"verify_commands": ["pixi run pyforge-marshal-test"]},
        flags={},
    )
    result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="51-1-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        effective=effective,
        vcs=vcs,
        forge=FakeForge(),
        process=process,
    )
    assert result.verdict == DispatchLandingVerdict.LANDED
    assert not any(f.code == "MRS-DISP-044" for f in envelope.findings)


# --------------------------------------------------------------------------
# blocked_twin_promotion_text (Story 51.11, CAP-258)
# --------------------------------------------------------------------------


def test_blocked_twin_promotion_text_promotes_differing_primary() -> None:
    worktree_text = "---\nstatus: blocked\n---\n"
    promoted = blocked_twin_promotion_text(
        primary_text="---\nstatus: in-progress\n---\n",
        worktree_text=worktree_text,
    )
    assert promoted == worktree_text


def test_blocked_twin_promotion_text_none_when_unreadable_primary() -> None:
    assert blocked_twin_promotion_text(primary_text=None, worktree_text="---\nstatus: blocked\n---\n") is None


def test_blocked_twin_promotion_text_none_when_already_matching() -> None:
    text = "---\nstatus: blocked\n---\n"
    assert blocked_twin_promotion_text(primary_text=text, worktree_text=text) is None


# --------------------------------------------------------------------------
# The landing waits for its PR head's check runs (Story 80.1, CAP-284)
# --------------------------------------------------------------------------
#
# `main` has no branch protection and the landing never evaluated `landing_rules`, so on 2026-10-01
# doctor 38.3 merged over a failing `Detectors / scripts-suite` and steward 80.1 merged with Platform
# CI and Detectors still pending. Every test below drives the real `execute_dispatch_land` with a
# fake clock (`sleep` advances it, nothing ever really sleeps) and a forge whose `check_runs`
# answers one scripted step per read.


class _FakeClock:
    """``monotonic`` reads ``now``; ``sleep`` records the request and advances ``now`` by it."""

    def __init__(self) -> None:
        self.now = 5_000.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class _ChecksForge(FakeForge):
    """``check_runs`` answers ``steps`` in order, the last one repeating: a tuple of ``CheckRun`` is
    the forge's answer, an ``Exception`` is raised. Records every read, merge and close."""

    def __init__(self, *steps: object) -> None:
        self.steps: list[object] = list(steps)
        self.reads: list[str] = []
        self.merge_calls: list[str] = []
        self.closed: list[int] = []

    def check_runs(self, repo, ref):
        self.reads.append(ref.value)
        step = self.steps.pop(0) if len(self.steps) > 1 else self.steps[0]
        if isinstance(step, Exception):
            raise step
        return step

    def merge_pr(self, repo, number, strategy, *, expected_head_sha, delete_branch, subject):
        self.merge_calls.append(expected_head_sha.value)

    def close_pr(self, repo, number):
        self.closed.append(number)


def _run(name: str, status: str = "completed", conclusion: str | None = "success") -> CheckRun:
    return CheckRun(name=name, status=status, conclusion=conclusion)


_GREEN = (_run("Lint / ruff"), _run("Station tests / marshal"))
_PENDING = (_run("Lint / ruff"), _run("Platform CI / platform-ci", "in_progress", None))


def _land_waiting(
    tmp_path: Path,
    forge: FakeForge,
    clock: _FakeClock,
    monkeypatch,
    *,
    dispatch: dict | None = None,
    vcs=None,
    surface: tuple = (),
    on_wait_tick=None,
    seams: bool = True,
):
    """Run the real landing. The spec-surface verdict is faked (``surface``, clean by default): the
    marshal env has no `pyforge.doctor`, so an unfaked reconcile adds a WARN MRS-DISP-047 to every
    landing -- noise these tests' exact finding-code assertions must not depend on."""
    _install_fake_spec_surface(monkeypatch, surface)
    worktree = tmp_path / "wt"
    worktree.mkdir(exist_ok=True)
    effective, findings = policy.compose(
        project_slug="pyforge-marshal", project={"dispatch": dispatch} if dispatch is not None else {}, flags={}
    )
    assert findings == ()
    return execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="80-1-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        effective=effective,
        vcs=vcs if vcs is not None else FakeVcs(merged=False),
        forge=forge,
        process=FakeProcess(),
        **({"sleep": clock.sleep, "monotonic": clock.monotonic} if seams else {}),
        on_wait_tick=on_wait_tick,
    )


def _codes(envelope) -> list[str]:
    return [f.code for f in envelope.findings]


def test_landing_merges_when_every_check_run_is_green_and_journals_the_runs(tmp_path: Path, monkeypatch) -> None:
    """AC1: every run `success`/`skipped`/`neutral` -> it merges and the record lists the runs."""
    runs = (_run("Lint / ruff"), _run("Docs", conclusion="skipped"), _run("Optional", conclusion="neutral"))
    forge, clock = _ChecksForge(runs), _FakeClock()
    result, envelope = _land_waiting(tmp_path, forge, clock, monkeypatch)
    assert result.verdict == DispatchLandingVerdict.LANDED
    assert forge.merge_calls == ["abc123"]
    assert forge.reads == ["abc123"]
    assert clock.sleeps == []
    assert _codes(envelope) == []
    assert envelope.data["landing_checks"] == {
        "head_sha": "abc123",
        "outcome": "green",
        "polls": 1,
        "waited_seconds": 0.0,
        "runs": [
            {"name": "Lint / ruff", "status": "completed", "conclusion": "success"},
            {"name": "Docs", "status": "completed", "conclusion": "skipped"},
            {"name": "Optional", "status": "completed", "conclusion": "neutral"},
        ],
    }


@pytest.mark.parametrize("conclusion", ["failure", "cancelled", "timed_out", "action_required"])
def test_landing_refuses_on_a_red_run_names_it_and_leaves_the_pr_open(
    tmp_path: Path, monkeypatch, conclusion: str
) -> None:
    """AC2: a red run refuses with a finding naming it, merges nothing, and leaves the PR open."""
    forge = _ChecksForge((_run("Lint / ruff"), _run("Detectors / scripts-suite", conclusion=conclusion)))
    clock = _FakeClock()
    result, envelope = _land_waiting(tmp_path, forge, clock, monkeypatch)
    assert result.verdict == DispatchLandingVerdict.REFUSED
    assert result.merge_sha is None
    assert result.pr_number == 42
    assert forge.merge_calls == []
    assert forge.closed == []
    assert clock.sleeps == []
    assert _codes(envelope) == ["MRS-DISP-056"]
    (finding,) = envelope.findings
    assert finding.severity is Severity.ERROR
    assert f"Detectors / scripts-suite ({conclusion})" in finding.message
    assert "Lint / ruff" not in finding.message
    assert "PR #42" in finding.message and "abc123" in finding.message
    assert envelope.data["landing_checks"]["outcome"] == "red"
    assert "merged" not in envelope.data


def test_landing_refuses_on_a_red_run_at_once_even_with_other_runs_still_pending(tmp_path: Path, monkeypatch) -> None:
    forge = _ChecksForge(_PENDING + (_run("Detectors / scripts-suite", conclusion="failure"),))
    clock = _FakeClock()
    result, envelope = _land_waiting(tmp_path, forge, clock, monkeypatch)
    assert result.verdict == DispatchLandingVerdict.REFUSED
    assert _codes(envelope) == ["MRS-DISP-056"]
    assert clock.sleeps == []
    assert forge.reads == ["abc123"]


def test_landing_refuses_when_runs_are_still_pending_at_the_timeout_and_names_them(tmp_path: Path, monkeypatch) -> None:
    """AC3: still in progress at `landing_check_timeout_minutes` -> refuse naming the pending runs;
    the defaults poll every 60s for 45 minutes (46 reads, 45 sleeps of 60s)."""
    forge, clock = _ChecksForge(_PENDING), _FakeClock()
    result, envelope = _land_waiting(tmp_path, forge, clock, monkeypatch)
    assert result.verdict == DispatchLandingVerdict.REFUSED
    assert forge.merge_calls == []
    assert forge.closed == []
    assert len(forge.reads) == 46
    assert clock.sleeps == [60.0] * 45
    assert _codes(envelope) == ["MRS-DISP-057"]
    (finding,) = envelope.findings
    assert finding.severity is Severity.ERROR
    assert "Platform CI / platform-ci (in_progress)" in finding.message
    assert "Lint / ruff" not in finding.message
    assert "45 minute(s)" in finding.message
    record = envelope.data["landing_checks"]
    assert (record["outcome"], record["polls"], record["waited_seconds"]) == ("timeout", 46, 2700.0)
    assert [r["status"] for r in record["runs"]] == ["completed", "in_progress"]


def test_the_last_sleep_is_clipped_to_the_time_left(tmp_path: Path, monkeypatch) -> None:
    """A timeout that is not a multiple of the poll: the wait never overshoots it (60 + 30 = 90s)."""
    forge, clock = _ChecksForge(_PENDING), _FakeClock()
    result, envelope = _land_waiting(
        tmp_path, forge, clock, monkeypatch, dispatch={"landing_check_timeout_minutes": 1.5}
    )
    assert result.verdict == DispatchLandingVerdict.REFUSED
    assert clock.sleeps == [60.0, 30.0]
    assert _codes(envelope) == ["MRS-DISP-057"]


def test_landing_merges_on_the_next_poll_once_the_runs_go_green(tmp_path: Path, monkeypatch) -> None:
    """AC4: runs that conclude green between two polls -> merge on the next poll."""
    forge, clock = _ChecksForge(_PENDING, _PENDING, _GREEN), _FakeClock()
    result, envelope = _land_waiting(tmp_path, forge, clock, monkeypatch)
    assert result.verdict == DispatchLandingVerdict.LANDED
    assert forge.merge_calls == ["abc123"]
    assert len(forge.reads) == 3
    assert clock.sleeps == [60.0, 60.0]
    assert _codes(envelope) == []
    record = envelope.data["landing_checks"]
    assert (record["outcome"], record["polls"], record["waited_seconds"]) == ("green", 3, 120.0)
    assert [r["conclusion"] for r in record["runs"]] == ["success", "success"]


def test_landing_refuses_when_a_pending_run_turns_red_while_waiting(tmp_path: Path, monkeypatch) -> None:
    red = (_run("Lint / ruff"), _run("Platform CI / platform-ci", conclusion="failure"))
    forge, clock = _ChecksForge(_PENDING, red), _FakeClock()
    result, envelope = _land_waiting(tmp_path, forge, clock, monkeypatch)
    assert result.verdict == DispatchLandingVerdict.REFUSED
    assert _codes(envelope) == ["MRS-DISP-056"]
    assert clock.sleeps == [60.0]
    assert forge.merge_calls == []


def test_an_empty_head_keeps_waiting_through_the_grace_then_counts_as_green(tmp_path: Path, monkeypatch) -> None:
    """AC5: no runs and less than `landing_check_grace_seconds` (120) elapsed -> keep waiting; at the
    grace the empty set counts as green (the polls land at 0s, 60s, 120s)."""
    forge, clock = _ChecksForge(()), _FakeClock()
    result, envelope = _land_waiting(tmp_path, forge, clock, monkeypatch)
    assert result.verdict == DispatchLandingVerdict.LANDED
    assert len(forge.reads) == 3
    assert clock.sleeps == [60.0, 60.0]
    assert forge.merge_calls == ["abc123"]
    assert envelope.data["landing_checks"] == {
        "head_sha": "abc123",
        "outcome": "no-runs",
        "polls": 3,
        "waited_seconds": 120.0,
        "runs": [],
    }


def test_an_empty_head_inside_the_grace_never_merges(tmp_path: Path, monkeypatch) -> None:
    """The grace is a floor: with a timeout shorter than it, the empty set refuses at the timeout
    (the timeout wins over a grace that outlasts it -- an empty set never merges past it)."""
    forge, clock = _ChecksForge(()), _FakeClock()
    result, envelope = _land_waiting(
        tmp_path,
        forge,
        clock,
        monkeypatch,
        dispatch={"landing_check_grace_seconds": 600, "landing_check_timeout_minutes": 2},
    )
    assert result.verdict == DispatchLandingVerdict.REFUSED
    assert forge.merge_calls == []
    assert clock.sleeps == [60.0, 60.0]
    assert _codes(envelope) == ["MRS-DISP-057"]
    assert "no check run was reported" in envelope.findings[0].message
    assert envelope.data["landing_checks"]["outcome"] == "timeout"


def test_a_zero_grace_merges_an_empty_head_on_the_first_poll(tmp_path: Path, monkeypatch) -> None:
    forge, clock = _ChecksForge(()), _FakeClock()
    result, _ = _land_waiting(tmp_path, forge, clock, monkeypatch, dispatch={"landing_check_grace_seconds": 0})
    assert result.verdict == DispatchLandingVerdict.LANDED
    assert clock.sleeps == []
    assert len(forge.reads) == 1


def test_runs_registering_during_the_grace_are_judged_not_waved_through(tmp_path: Path, monkeypatch) -> None:
    """An empty first read then a red run: the grace never turns a head with real checks into a pass."""
    red = (_run("Detectors / scripts-suite", conclusion="failure"),)
    forge, clock = _ChecksForge((), red), _FakeClock()
    result, envelope = _land_waiting(tmp_path, forge, clock, monkeypatch)
    assert result.verdict == DispatchLandingVerdict.REFUSED
    assert _codes(envelope) == ["MRS-DISP-056"]
    assert forge.merge_calls == []


def test_landing_refuses_when_the_forge_read_fails_and_never_merges(tmp_path: Path, monkeypatch) -> None:
    """AC6: an unreadable head is not a green head. Reuses MRS-DISP-018, the landing's own forge refusal."""
    forge = _ChecksForge(ForgeCommandError("gh api ... failed: HTTP 502"))
    clock = _FakeClock()
    result, envelope = _land_waiting(tmp_path, forge, clock, monkeypatch)
    assert result.verdict == DispatchLandingVerdict.REFUSED
    assert result.pr_number == 42
    assert forge.merge_calls == []
    assert forge.closed == []
    assert _codes(envelope) == ["MRS-DISP-018"]
    assert "HTTP 502" in envelope.findings[0].message
    record = envelope.data["landing_checks"]
    assert (record["outcome"], record["polls"], record["runs"]) == ("read-error", 1, [])
    assert "HTTP 502" in record["error"]


def test_landing_refuses_when_the_forge_read_fails_mid_wait(tmp_path: Path, monkeypatch) -> None:
    forge = _ChecksForge(_PENDING, ForgeCommandError("rate limited"))
    clock = _FakeClock()
    result, envelope = _land_waiting(tmp_path, forge, clock, monkeypatch)
    assert result.verdict == DispatchLandingVerdict.REFUSED
    assert _codes(envelope) == ["MRS-DISP-018"]
    assert forge.merge_calls == []
    assert clock.sleeps == [60.0]
    record = envelope.data["landing_checks"]
    assert (record["outcome"], record["polls"]) == ("read-error", 2)
    assert [r["name"] for r in record["runs"]] == ["Lint / ruff", "Platform CI / platform-ci"]


def test_a_refused_landing_merges_when_rerun_once_its_ci_is_green(tmp_path: Path, monkeypatch) -> None:
    """AC7: a refusal leaves the PR open, so re-running the landing merges once CI is green."""
    forge = _ChecksForge((_run("Detectors / scripts-suite", conclusion="failure"),))
    first, first_envelope = _land_waiting(tmp_path, forge, _FakeClock(), monkeypatch)
    assert first.verdict == DispatchLandingVerdict.REFUSED
    assert forge.merge_calls == [] and forge.closed == []

    forge.steps = [(_run("Detectors / scripts-suite"),)]
    second, second_envelope = _land_waiting(tmp_path, forge, _FakeClock(), monkeypatch)
    assert second.verdict == DispatchLandingVerdict.LANDED
    assert forge.merge_calls == ["abc123"]
    assert _codes(first_envelope) == ["MRS-DISP-056"]
    assert _codes(second_envelope) == []


def test_the_wait_uses_the_policy_declared_bounds(tmp_path: Path, monkeypatch) -> None:
    forge, clock = _ChecksForge(_PENDING), _FakeClock()
    result, envelope = _land_waiting(
        tmp_path,
        forge,
        clock,
        monkeypatch,
        dispatch={"landing_check_poll_seconds": 5, "landing_check_timeout_minutes": 0.25},
    )
    assert result.verdict == DispatchLandingVerdict.REFUSED
    assert clock.sleeps == [5.0] * 3
    assert len(forge.reads) == 4
    assert "0.25 minute(s)" in envelope.findings[0].message


def test_the_wait_reads_the_post_reconcile_head_not_the_stale_one(tmp_path: Path, monkeypatch) -> None:
    """The spec-surface reconcile pushes a new commit, so the head whose checks gate the merge is the
    POST-reconcile tip -- the wait must read that sha, the one `forge.merge_pr` is pinned to."""
    forge, clock = _ChecksForge(_GREEN), _FakeClock()
    result, envelope = _land_waiting(
        tmp_path,
        forge,
        clock,
        monkeypatch,
        vcs=_ReconcileVcs(merged=False, changed=("src/a.py",)),
        surface=(_SurfaceFinding("drift", "--write-baseline --spec pyforge-marshal/spec-alpha", "src/a.py"),),
    )
    assert result.verdict == DispatchLandingVerdict.LANDED
    assert _codes(envelope) == ["MRS-DISP-047"]  # the reconcile ran: it pushed the commit whose checks gate the merge
    assert forge.reads == ["post-reconcile-sha"]
    assert forge.merge_calls == ["post-reconcile-sha"]


def test_the_wait_runs_after_the_other_pre_merge_refusals_not_before(tmp_path: Path, monkeypatch) -> None:
    """The wait sits immediately before `forge.merge_pr`: a landing the spec-surface reconcile already
    refuses (MRS-DISP-048) never polls the forge for checks."""
    forge, clock = _ChecksForge(_GREEN), _FakeClock()
    result, envelope = _land_waiting(
        tmp_path,
        forge,
        clock,
        monkeypatch,
        vcs=_ReconcileVcs(merged=False, changed=("src/mine.py",)),
        surface=(
            _SurfaceFinding("drift", "--write-baseline --spec pyforge-marshal/spec-shared", "src/mine.py"),
            _SurfaceFinding("drift", "--write-baseline --spec pyforge-marshal/spec-shared", "src/not-mine.py"),
        ),
    )
    assert result.verdict == DispatchLandingVerdict.REFUSED
    assert _codes(envelope) == ["MRS-DISP-048"]
    assert forge.reads == []
    assert "landing_checks" not in envelope.data


def test_the_checks_record_survives_a_failed_merge(tmp_path: Path, monkeypatch) -> None:
    """A merge that fails AFTER a green wait (MRS-DISP-020) still reports what was waited on."""
    forge = _BrokenChecksForge(_GREEN)
    result, envelope = _land_waiting(tmp_path, forge, _FakeClock(), monkeypatch)
    assert result.verdict == DispatchLandingVerdict.REFUSED
    assert "MRS-DISP-020" in _codes(envelope)
    assert envelope.data["landing_checks"]["outcome"] == "green"


class _BrokenChecksForge(_ChecksForge):
    def merge_pr(self, repo, number, strategy, *, expected_head_sha, delete_branch, subject):
        raise ForgeCommandError("merge blocked")


def test_default_clock_is_real_time_but_a_green_head_never_sleeps(tmp_path: Path, monkeypatch) -> None:
    """No injected clock: a green head returns on its first poll, never reaching `time.sleep`."""
    worktree = tmp_path / "wt"
    worktree.mkdir()
    result, envelope = execute_dispatch_land(
        project_slug="pyforge-marshal",
        story_key="80-1-example",
        worktree=worktree,
        repo_root=tmp_path,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        vcs=FakeVcs(merged=False),
        forge=FakeForge(),
        process=FakeProcess(),
    )
    assert result.verdict == DispatchLandingVerdict.LANDED
    assert envelope.data["landing_checks"]["outcome"] == "green"


def test_the_landing_checks_record_round_trips_through_the_journal_resolver(tmp_path: Path, monkeypatch) -> None:
    forge, clock = _ChecksForge(_PENDING, _GREEN), _FakeClock()
    _, envelope = _land_waiting(tmp_path, forge, clock, monkeypatch)
    payload = {"landing_checks": envelope.to_json_dict()["data"]["landing_checks"]}
    assert resolve_landing_checks_from_payload(payload) == envelope.data["landing_checks"]


def test_mutation_without_the_wait_a_red_head_lands_green(tmp_path: Path, monkeypatch) -> None:
    """Mutation test: stubbing the wait to a no-op lets the red fixture of
    `test_landing_refuses_on_a_red_run_names_it_and_leaves_the_pr_open` merge -- proving THIS wait,
    not some other mechanism, is what refuses it (and that the new tests above fail without it)."""
    from pyforge.marshal import dispatch_land

    monkeypatch.setattr(
        dispatch_land,
        "_wait_for_landing_checks",
        lambda **_kwargs: dispatch_land._LandingChecksOutcome(finding=None, record={}),
    )
    forge = _ChecksForge((_run("Detectors / scripts-suite", conclusion="failure"),))
    result, envelope = _land_waiting(tmp_path, forge, _FakeClock(), monkeypatch)
    assert result.verdict == DispatchLandingVerdict.LANDED
    assert forge.merge_calls == ["abc123"]
    assert "MRS-DISP-056" not in _codes(envelope)


# --------------------------------------------------------------------------
# Review loop 1 (Story 80.1): the real default clock, the wait tick, the union-healed head
# --------------------------------------------------------------------------


class _GuardedClock(_FakeClock):
    """A fake clock that fails loudly instead of hanging: a wait whose sleep does nothing never
    reaches its timeout, so a mutation of the sleep must read as a red test, not a stuck suite."""

    def monotonic(self) -> float:
        self.reads = getattr(self, "reads", 0) + 1
        if self.reads > 500:
            raise AssertionError("the check wait did not terminate -- nothing advanced the clock")
        return super().monotonic()


def test_without_clock_seams_the_real_time_sleep_receives_the_poll_interval(tmp_path: Path, monkeypatch) -> None:
    """No `sleep`/`monotonic` injected: the defaults are `time.sleep`/`time.monotonic`. The module's
    own clock functions are swapped for a fake for the duration, so a pending head waits through
    the DEFAULT sleep -- a default that sleeps nothing (the mutation) turns this red."""
    forge, clock = _ChecksForge(_PENDING), _GuardedClock()
    with monkeypatch.context() as patched:
        patched.setattr(time, "sleep", clock.sleep)
        patched.setattr(time, "monotonic", clock.monotonic)
        result, envelope = _land_waiting(
            tmp_path,
            forge,
            clock,
            monkeypatch,
            dispatch={"landing_check_poll_seconds": 20, "landing_check_timeout_minutes": 1},
            seams=False,
        )
    assert result.verdict == DispatchLandingVerdict.REFUSED
    assert clock.sleeps == [20.0, 20.0, 20.0]
    assert _codes(envelope) == ["MRS-DISP-057"]


def _ticking(clock: _FakeClock) -> tuple[list[float], object]:
    """``(ticks, on_wait_tick)``: every tick records the fake clock's reading."""
    ticks: list[float] = []
    return ticks, lambda: ticks.append(clock.now)


def test_the_wait_ticks_after_every_poll(tmp_path: Path, monkeypatch) -> None:
    """The supervisor's heartbeat rides this tick: with the default 60 s poll it fires once per
    poll -- after each read, none extra in between."""
    forge, clock = _ChecksForge(_PENDING), _FakeClock()
    ticks, on_wait_tick = _ticking(clock)
    _land_waiting(
        tmp_path, forge, clock, monkeypatch, dispatch={"landing_check_timeout_minutes": 3}, on_wait_tick=on_wait_tick
    )
    assert len(forge.reads) == 4
    assert ticks == [5_000.0, 5_060.0, 5_120.0, 5_180.0]


def test_a_poll_interval_shorter_than_a_minute_ticks_at_that_interval(tmp_path: Path, monkeypatch) -> None:
    forge, clock = _ChecksForge(_PENDING), _FakeClock()
    ticks, on_wait_tick = _ticking(clock)
    _land_waiting(
        tmp_path,
        forge,
        clock,
        monkeypatch,
        dispatch={"landing_check_poll_seconds": 20, "landing_check_timeout_minutes": 1},
        on_wait_tick=on_wait_tick,
    )
    assert [b - a for a, b in zip(ticks, ticks[1:])] == [20.0, 20.0, 20.0]


def test_a_long_poll_interval_is_sliced_so_the_wait_still_ticks_every_minute(tmp_path: Path, monkeypatch) -> None:
    """`landing_check_poll_seconds = 150` would sleep 150 s in one piece -- past the portal's 300 s
    heartbeat limit within two polls. The sleep is sliced and ticks between the slices: a tick at
    least every `min(poll_seconds, 60)` seconds, whatever the operator sets."""
    forge, clock = _ChecksForge(_PENDING), _FakeClock()
    ticks, on_wait_tick = _ticking(clock)
    result, _ = _land_waiting(
        tmp_path,
        forge,
        clock,
        monkeypatch,
        dispatch={"landing_check_poll_seconds": 150, "landing_check_timeout_minutes": 5},
        on_wait_tick=on_wait_tick,
    )
    assert result.verdict == DispatchLandingVerdict.REFUSED
    assert clock.sleeps == [60.0, 60.0, 30.0, 60.0, 60.0, 30.0]
    assert len(forge.reads) == 3  # the polls themselves still land every 150 s
    assert ticks == [5_000.0, 5_060.0, 5_120.0, 5_150.0, 5_210.0, 5_270.0, 5_300.0]
    assert max(b - a for a, b in zip(ticks, ticks[1:])) <= 60.0


def test_a_landing_driven_without_a_tick_waits_exactly_as_before(tmp_path: Path, monkeypatch) -> None:
    """The CLI landing path has no run to keep alive and passes no tick."""
    forge, clock = _ChecksForge(_PENDING, _GREEN), _FakeClock()
    result, envelope = _land_waiting(tmp_path, forge, clock, monkeypatch)
    assert result.verdict == DispatchLandingVerdict.LANDED
    assert clock.sleeps == [60.0]
    assert envelope.data["landing_checks"]["polls"] == 2


# --- the head a union heal pushes ---------------------------------------------------------------------

_LEDGER_REL = "_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml"
_FAILED_SCRIPTS = (_run("Detectors / scripts-suite", conclusion="failure"),)


def _heal_vcs() -> HealCapableVcs:
    """`origin/main` and the branch each added a ledger row: the first merge fails, the union heal
    pushes `healed222` (a head CI has never seen) and retries the merge on it."""
    return HealCapableVcs(
        conflict_paths=(_LEDGER_REL,),
        main_ledger=_ledger_yaml(("28-19-x", "done")),
        branch_ledger=_ledger_yaml(("28-20-y", "backlog")),
    )


class _HealChecksForge(HealRetryForge):
    """The first merge fails (so the landing heals); `check_runs` answers per head sha, one scripted
    step per read, the last repeating. Records every read, merge and close."""

    def __init__(self, **by_head: list[object]) -> None:
        super().__init__()
        self.by_head = by_head
        self.reads: list[str] = []
        self.merged_heads: list[str] = []
        self.closed: list[int] = []

    def check_runs(self, repo, ref):
        self.reads.append(ref.value)
        steps = self.by_head[ref.value]
        step = steps.pop(0) if len(steps) > 1 else steps[0]
        if isinstance(step, Exception):
            raise step
        return step

    def merge_pr(self, repo, number, strategy, *, expected_head_sha, delete_branch, subject):
        self.merged_heads.append(expected_head_sha.value)
        super().merge_pr(
            repo, number, strategy, expected_head_sha=expected_head_sha, delete_branch=delete_branch, subject=subject
        )

    def close_pr(self, repo, number):
        self.closed.append(number)


def test_the_union_healed_head_is_waited_on_before_the_retried_merge(tmp_path: Path, monkeypatch) -> None:
    """The head the heal pushes is a new commit: its runs are read (here pending, then green) and
    only then does the retried merge run -- on THAT sha. The journal records both heads."""
    forge = _HealChecksForge(abc123=[_GREEN], healed222=[_PENDING, _GREEN])
    clock = _FakeClock()
    ticks, on_wait_tick = _ticking(clock)
    result, envelope = _land_waiting(tmp_path, forge, clock, monkeypatch, vcs=_heal_vcs(), on_wait_tick=on_wait_tick)
    assert result.verdict == DispatchLandingVerdict.LANDED
    assert _codes(envelope) == []
    assert envelope.data["ledger_union_heal"] is True
    assert forge.reads == ["abc123", "healed222", "healed222"]
    assert forge.merged_heads == ["abc123", "healed222"]
    assert clock.sleeps == [60.0]
    assert len(ticks) == 3  # one per poll, across both heads
    record = envelope.data["landing_checks"]
    assert (record["head_sha"], record["outcome"], record["polls"]) == ("abc123", "green", 1)
    heal = record["heal"]
    assert (heal["head_sha"], heal["outcome"], heal["polls"], heal["waited_seconds"]) == ("healed222", "green", 2, 60.0)
    assert [run["conclusion"] for run in heal["runs"]] == ["success", "success"]


def test_a_union_healed_landing_reports_the_healed_head_not_the_pre_heal_one(tmp_path: Path, monkeypatch) -> None:
    """The retried merge landed the head the heal pushed (`healed222`), so `merge_sha` and
    `data["head_sha"]` name it -- the pre-heal head (`abc123`) is not what is on `main`."""
    forge = _HealChecksForge(abc123=[_GREEN], healed222=[_GREEN])
    result, envelope = _land_waiting(tmp_path, forge, _FakeClock(), monkeypatch, vcs=_heal_vcs())
    assert result.verdict == DispatchLandingVerdict.LANDED
    assert forge.merged_heads == ["abc123", "healed222"]
    assert result.merge_sha == "healed222"
    assert envelope.data["head_sha"] == "healed222"
    assert envelope.data["landing_checks"]["head_sha"] == "abc123"  # the first wait still names its own head


def test_a_local_main_advance_still_reports_the_pre_heal_head(tmp_path: Path, monkeypatch) -> None:
    """The local-`main` advance merges the head the pre-merge wait cleared: nothing to re-point."""
    result, envelope = _land_waiting(tmp_path, _DirtyChecksForge(), _FakeClock(), monkeypatch, vcs=DirtyHealVcs())
    assert result.verdict == DispatchLandingVerdict.LANDED
    assert envelope.data["local_main_advance"] is True
    assert result.merge_sha == "abc123"
    assert envelope.data["head_sha"] == "abc123"


@pytest.mark.parametrize("conclusion", ["failure", "cancelled", "timed_out", "action_required"])
def test_a_red_union_healed_head_refuses_with_the_checks_finding_and_never_retries_the_merge(
    tmp_path: Path, monkeypatch, conclusion: str
) -> None:
    forge = _HealChecksForge(abc123=[_GREEN], healed222=[(_run("Detectors / scripts-suite", conclusion=conclusion),)])
    result, envelope = _land_waiting(tmp_path, forge, _FakeClock(), monkeypatch, vcs=_heal_vcs())
    assert result.verdict == DispatchLandingVerdict.REFUSED
    assert result.pr_number == 42
    assert _codes(envelope) == ["MRS-DISP-056"]  # not MRS-DISP-020: the first merge's failure is not the story
    assert f"Detectors / scripts-suite ({conclusion})" in envelope.findings[0].message
    assert "healed222" in envelope.findings[0].message
    assert forge.merged_heads == ["abc123"]  # the retried merge never ran
    assert forge.closed == []
    assert "merged" not in envelope.data
    record = envelope.data["landing_checks"]
    assert (record["outcome"], record["heal"]["outcome"]) == ("green", "red")


def test_a_union_healed_head_still_pending_at_the_timeout_refuses_and_never_retries_the_merge(
    tmp_path: Path, monkeypatch
) -> None:
    forge = _HealChecksForge(abc123=[_GREEN], healed222=[_PENDING])
    clock = _FakeClock()
    result, envelope = _land_waiting(
        tmp_path, forge, clock, monkeypatch, vcs=_heal_vcs(), dispatch={"landing_check_timeout_minutes": 2}
    )
    assert result.verdict == DispatchLandingVerdict.REFUSED
    assert _codes(envelope) == ["MRS-DISP-057"]
    assert "Platform CI / platform-ci (in_progress)" in envelope.findings[0].message
    assert forge.merged_heads == ["abc123"]
    assert forge.closed == []
    assert clock.sleeps == [60.0, 60.0]  # the healed head's own 2-minute timeout
    assert envelope.data["landing_checks"]["heal"]["outcome"] == "timeout"


def test_a_union_healed_head_whose_checks_cannot_be_read_refuses_and_never_retries_the_merge(
    tmp_path: Path, monkeypatch
) -> None:
    forge = _HealChecksForge(abc123=[_GREEN], healed222=[ForgeCommandError("HTTP 502")])
    result, envelope = _land_waiting(tmp_path, forge, _FakeClock(), monkeypatch, vcs=_heal_vcs())
    assert result.verdict == DispatchLandingVerdict.REFUSED
    assert _codes(envelope) == ["MRS-DISP-018"]
    assert forge.merged_heads == ["abc123"]
    assert envelope.data["landing_checks"]["heal"]["outcome"] == "read-error"


class _DirtyChecksForge(DirtyHealForge):
    """The merge always fails and GitHub reads DIRTY: the heal advances `main` locally with the head
    the pre-merge wait already cleared. Counts the check reads."""

    def __init__(self) -> None:
        super().__init__()
        self.reads: list[str] = []

    def check_runs(self, repo, ref):
        self.reads.append(ref.value)
        return _GREEN_RUNS


def test_the_local_main_advance_merges_the_head_already_cleared_and_waits_no_second_time(
    tmp_path: Path, monkeypatch
) -> None:
    forge = _DirtyChecksForge()
    result, envelope = _land_waiting(tmp_path, forge, _FakeClock(), monkeypatch, vcs=DirtyHealVcs())
    assert result.verdict == DispatchLandingVerdict.LANDED
    assert envelope.data["local_main_advance"] is True
    assert forge.reads == ["abc123"]  # one wait: the pre-merge one
    assert "heal" not in envelope.data["landing_checks"]


def test_mutation_without_the_heals_wait_a_red_union_head_lands(tmp_path: Path, monkeypatch) -> None:
    """Mutation test: the heal's `await_checks` hook is what gates the retried merge. Handing the
    heal no hook (the pre-review code) lets the red union head merge."""
    from pyforge.marshal import dispatch_land

    real_heal = dispatch_land.try_heal_dispatch_land_merge
    monkeypatch.setattr(
        dispatch_land,
        "try_heal_dispatch_land_merge",
        lambda **kwargs: real_heal(**{**kwargs, "await_checks": None}),
    )
    forge = _HealChecksForge(abc123=[_GREEN], healed222=[_FAILED_SCRIPTS])
    result, envelope = _land_waiting(tmp_path, forge, _FakeClock(), monkeypatch, vcs=_heal_vcs())
    assert result.verdict == DispatchLandingVerdict.LANDED
    assert forge.merged_heads == ["abc123", "healed222"]
    assert "MRS-DISP-056" not in _codes(envelope)
