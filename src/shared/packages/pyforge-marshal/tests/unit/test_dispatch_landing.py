"""Unit tests for dispatch landing (Story 22.4, CAP-4)."""

from __future__ import annotations

import sys
import types
from pathlib import Path

from pyforge.core.process import ProcessError, ProcessResult

from pyforge.marshal.adapters.vcs_git import VcsCommandError
from pyforge.marshal.core import policy, promotion
from pyforge.marshal.core.dispatch_landing import (
    DispatchLandingVerdict,
    blocked_twin_promotion_text,
    ledger_status_precedence,
    may_attempt_dispatch_landing,
    merge_subject_is_marshal_native,
    refuse_unverified_landing,
    union_sprint_ledger_maps,
)
from pyforge.marshal.core.dispatch_verification import DispatchVerificationVerdict
from pyforge.marshal.core.identity import normalize, render_merge_subject
from pyforge.marshal.core.model import Severity
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
    ) -> None:
        self._merged = merged
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
        if self._merged:
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
        self.pushed.append(branch)

    def resolve_ref(self, repo_root: Path, ref: str) -> str:
        return "abc123"

    def fetch(self, repo_root: Path, remote: str, ref: str) -> None:
        """Story 51.1: safe no-op default so every pre-existing ``FakeVcs()``
        construction keeps working now that ``execute_dispatch_land``
        unconditionally fetches ``origin/main`` before landing."""
        return None

    def commits_behind(self, worktree_path: Path, tip_ref: str) -> int:
        """Story 51.1: ``0`` by default -- "already even with origin/main",
        the byte-identical-to-pre-51.1 path every pre-existing test in this
        file implicitly exercises (the merge-tree-preview check
        short-circuits immediately). Fixtures that need the check to
        actually fire use ``MergeTreePreviewVcs`` below."""
        return 0


class FakeForge:
    def find_open_pr(self, repo, head_branch):
        return None

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
        self._head_sha = "abc123"

    def file_text_at_ref(self, repo_root: Path, ref: str, path: str):
        if path.endswith("sprint-status-ledger.yaml"):
            if ref == "main":
                return self.main_ledger
            return self.branch_ledger
        return None

    def commit_paths(self, repo_root: Path, paths: tuple[Path, ...], message: str):
        self.commits.append((repo_root, paths, message))
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
    assert vcs.merged == [("dispatch/pyforge-marshal/28.20", "main", result.subject)]
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
    assert len(vcs.commits) == 1
    assert vcs.commits[0][0] == worktree
    written = (worktree / ledger_rel).read_text(encoding="utf-8")
    assert "28-19-x: done" in written
    assert "28-20-y: backlog" in written


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
    assert vcs.fetch_calls == [("origin", "main")]
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
