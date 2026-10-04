"""Ports-driven unit tests for ``dispatch_supervisor.__main__`` (Story 53.3).

Story 53.3 (``spec-pyforge-marshal`` CAP-264) retires the dated per-module
coverage exception this entry point carried since Story 53.2. Every sequence
the supervisor actually runs -- attach, finalize, push, verify, land, blocked
halt, completion, timing, preserve -- is exercised here through the station's
own ports (``FsPort`` / ``VcsPort`` / ``ProcessPort`` / ``RunPublisherPort``),
with no live harness, no subprocess and no network: the process boundary is
faked, exactly as the sibling ``test_dispatch_supervisor_*.py`` modules do.

The tick loop's own ``time`` is injected too (``_FakeClock``), so no test ever
sleeps a real ``_TICK_SECONDS`` and a loop that fails to reach a terminal
verdict raises ``_LoopGuard`` instead of hanging the suite.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from pyforge.marshal.adapters.fs_local import FsError, LocalFs
from pyforge.marshal.adapters.vcs_git import GitVcs, VcsCommandError
from pyforge.marshal.core import dispatch as dispatch_core
from pyforge.marshal.core.dispatch_completion import (
    DispatchCompletionInput,
    DispatchGitFacts,
    DispatchSessionVerdict,
    judge_dispatch_completion,
)
from pyforge.marshal.core.dispatch_harness_done import FollowupReview
from pyforge.marshal.core.dispatch_landing import DispatchLandingVerdict
from pyforge.marshal.core.dispatch_verification import DispatchVerificationVerdict
from pyforge.marshal.core.egress import Redacted
from pyforge.marshal.core.journal import (
    SCOPE_VIOLATION_ADVISORIES_SIDECAR_REF,
    JournalEntryId,
    Phase,
    build_entry,
    prepare_for_write,
)
from pyforge.marshal.core.model import Finding, Severity, build_envelope
from pyforge.marshal.core.refs import ORIGIN_MAIN, local_branch_ref
from pyforge.marshal.dispatch_land import DispatchLandingResult
from pyforge.marshal.dispatch_supervisor import __main__ as supervisor_main
from pyforge.marshal.ports.commit import VcsRef

_SLUG = "pyforge-marshal"


@pytest.fixture(autouse=True)
def _hermetic_flag_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Story 85.1: pin ``PYFORGE_ENVIRONMENT`` so an operator shell's value cannot leak in.

    The supervisor reads ``pyforge.marshal.verify_fix_loop`` for real, from
    ``<repo_root>/src/platform/config/flags.json``; the read is never stubbed here, so
    the flag-off decision and the broken-tree warning stay reachable. A ``_repo`` tree
    carries no flag tree, so the flag reads its default, off -- the shipped state in
    every environment. ``test_dispatch_supervisor_verify_fix.py`` seeds flag trees and
    drives both states and the broken-tree cases.
    """
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")


_STORY_KEY = "51.11"
_RUN_ID = "run-53-3"
_BASELINE = "c8277c03c117ff4779d54a2ff9d900f519415971"
_MOVED = "feedfacecafebabe0000000000000000deadbeef"
_TEMPLATE = "Merge {slug}/{key} into main"
_SESSION_PID = 4242


# --------------------------------------------------------------------------
# Fakes -- the supervisor's whole process boundary
# --------------------------------------------------------------------------


class _LoopGuard(RuntimeError):
    """Raised by ``_FakeClock`` when a tick loop refuses to terminate."""


class _FakeClock:
    """``time`` stand-in for the tick loop: no real sleeping, bounded ticks."""

    def __init__(self, *, mono_step: float = 0.0, max_sleeps: int = 12) -> None:
        self.sleeps: list[float] = []
        self._mono = 1_000.0
        self._mono_step = mono_step
        self._max_sleeps = max_sleeps

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        if len(self.sleeps) > self._max_sleeps:
            raise _LoopGuard(f"supervisor tick loop did not terminate after {len(self.sleeps)} sleeps")

    def monotonic(self) -> float:
        self._mono += self._mono_step
        return self._mono


class FakeFs:
    """In-memory overlay over the real tree.

    ``append_line``/``write_text_atomic`` land in ``files``; ``read_text``
    checks the overlay FIRST and only then falls through to disk. The
    read-after-write the tick loop performs (re-reading ``journal.jsonl``
    after finalize/land) is what makes the overlay-first order load-bearing.
    """

    def __init__(
        self,
        *,
        append_fails_for: frozenset[str] = frozenset(),
        write_fails_for: frozenset[str] = frozenset(),
        read_fails_for: frozenset[str] = frozenset(),
        fail_append_after: int | None = None,
    ) -> None:
        self.files: dict[Path, str] = {}
        self.appended: list[tuple[Path, str, bool]] = []
        self.ensured: list[Path] = []
        self.append_calls = 0
        self._append_fails_for = append_fails_for
        self._write_fails_for = write_fails_for
        self._read_fails_for = read_fails_for
        self._fail_append_after = fail_append_after

    def read_text(self, path: Path) -> str | None:
        key = Path(path)
        # Keyed by basename *or* by full posix path: the blocked-twin promotion
        # reads two files that share one basename (the story spec in the
        # primary checkout and its worktree twin), and only a path key can
        # refuse the second read while the first succeeds.
        if key.name in self._read_fails_for or key.as_posix() in self._read_fails_for:
            raise FsError(f"read refused (test double): {key}")
        if key in self.files:
            return self.files[key]
        try:
            return key.read_text(encoding="utf-8")
        except OSError:
            return None

    def write_text_atomic(self, path: Path, content: str) -> None:
        key = Path(path)
        if key.name in self._write_fails_for:
            raise FsError(f"write refused (test double): {key}")
        self.files[key] = content

    def append_line(self, path: Path, line: str, *, fsync: bool) -> None:
        key = Path(path)
        self.append_calls += 1
        too_many = self._fail_append_after is not None and self.append_calls > self._fail_append_after
        if key.name in self._append_fails_for or too_many:
            raise FsError(f"append refused (test double): {key}")
        self.appended.append((key, line, fsync))
        existing = self.files.get(key)
        if existing is None:
            try:
                existing = key.read_text(encoding="utf-8")
            except OSError:
                existing = ""
        if existing and not existing.endswith("\n"):
            existing += "\n"
        self.files[key] = f"{existing}{line}\n"

    def ensure_dir(self, path: Path) -> None:
        self.ensured.append(Path(path))

    def journal_text(self, run_dir: Path) -> str:
        return self.read_text(run_dir / "journal.jsonl") or ""


class FakeVcs:
    """``VcsPort`` stand-in -- every method the supervisor actually reaches."""

    def __init__(
        self,
        *,
        head_sha: str = _BASELINE,
        head_shas: tuple[str, ...] | None = None,
        changed: tuple[str, ...] = (),
        changed_vs_head: tuple[str, ...] = ("src/pyforge/marshal/thing.py",),
        branches: frozenset[str] = frozenset(),
        branch_worktrees: dict[str, Path] | None = None,
        branch_merged: bool = False,
        subjects: tuple[str, ...] = (),
        spec_at_ref: str | None = None,
        spec_at_ref_raises: bool = False,
        dirty: bool = True,
        patch: str = "",
        head_sha_raises_times: int = 0,
        fetch_raises: bool = False,
        commit_paths_raises: bool = False,
        changed_files_raises: bool = False,
        uncommitted_raises: bool = False,
        push_raises: bool = False,
        patch_raises: bool = False,
        remote_tip_raises: bool = False,
        subjects_by_ref: dict[str, tuple[str, ...]] | None = None,
        merged_into_refs: frozenset[str] | None = None,
        unreadable_refs: dict[str, int] | None = None,
    ) -> None:
        """``subjects_by_ref`` / ``merged_into_refs`` / ``unreadable_refs`` (Story 72.1, CAP-280) make the
        merge reads ref-aware: ``commit_subjects`` answers per full ref (an unlisted ref is an empty
        history), ``is_branch_merged`` answers true only for a target in ``merged_into_refs`` (the full
        ref given as ``into_ref``, else ``refs/heads/{into}``), and ``unreadable_refs`` maps a ref to how
        many ``commit_subjects`` reads of it raise ``VcsCommandError`` before it reads again. Left unset,
        ``subjects`` / ``branch_merged`` answer for any ref, as before. ``calls`` logs every merge read
        and every fetch, in order."""
        self._head_shas = list(head_shas) if head_shas is not None else None
        self.head_sha = head_sha
        self.changed = changed
        self.changed_vs_head = changed_vs_head
        self.branches = branches
        self.branch_worktrees = branch_worktrees or {}
        self.branch_merged = branch_merged
        self.subjects = subjects
        self.spec_at_ref = spec_at_ref
        self._spec_at_ref_raises = spec_at_ref_raises
        self.dirty = dirty
        self.patch = patch
        self._head_sha_raises_times = head_sha_raises_times
        self._fetch_raises = fetch_raises
        self._commit_paths_raises = commit_paths_raises
        self._changed_files_raises = changed_files_raises
        self._uncommitted_raises = uncommitted_raises
        self._push_raises = push_raises
        self._patch_raises = patch_raises
        self._remote_tip_raises = remote_tip_raises
        self.fetches: list[tuple[Path, str, str]] = []
        self.commits: list[tuple[Path, tuple[Path, ...], str]] = []
        self.pushes: list[tuple[Path, str]] = []
        self.remote_tip_writes: list[tuple[str, ...]] = []
        self.remote_tip_reasons: list[str | None] = []
        self.subjects_by_ref = subjects_by_ref
        self.merged_into_refs = merged_into_refs
        self._unreadable_refs = dict(unreadable_refs or {})
        self.calls: list[tuple[str, ...]] = []

    # -- reads ------------------------------------------------------------
    def worktree_head_sha(self, worktree_path: Path) -> str:
        if self._head_sha_raises_times > 0:
            self._head_sha_raises_times -= 1
            raise VcsCommandError("git rev-parse failed (test double)")
        if self._head_shas:
            return self._head_shas.pop(0) if len(self._head_shas) > 1 else self._head_shas[0]
        return self.head_sha

    def changed_files(self, repo_root: Path, worktree_path: Path, *, base: str) -> tuple[str, ...]:
        if self._changed_files_raises:
            raise VcsCommandError("git diff failed (test double)")
        return self.changed_vs_head if base == "HEAD" else self.changed

    def branch_exists(self, repo_root: Path, branch: str) -> bool:
        return branch in self.branches

    def worktree_path_for_branch(self, repo_root: Path, branch: str) -> Path | None:
        return self.branch_worktrees.get(branch)

    def is_branch_merged(self, repo_root: Path, branch: str, *, into: str, into_ref: str | None = None) -> bool:
        target = into_ref if into_ref is not None else f"refs/heads/{into}"
        self.calls.append(("is_branch_merged", target))
        if self.merged_into_refs is not None:
            return target in self.merged_into_refs
        return self.branch_merged

    def commit_subjects(self, repo_root: Path, ref: str) -> tuple[str, ...]:
        self.calls.append(("commit_subjects", ref))
        if self._unreadable_refs.get(ref, 0) > 0:
            self._unreadable_refs[ref] -= 1
            raise VcsCommandError(f"git log {ref} failed (test double)")
        if self.subjects_by_ref is not None:
            return self.subjects_by_ref.get(ref, ())
        return self.subjects

    def file_text_at_ref(self, repo_root: Path, ref: str, path: str) -> str | None:
        if self._spec_at_ref_raises:
            raise VcsCommandError("git show failed (test double)")
        return self.spec_at_ref

    def has_uncommitted_changes(self, worktree_path: Path) -> bool:
        if self._uncommitted_raises:
            raise VcsCommandError("git status failed (test double)")
        return self.dirty

    def worktree_unified_patch(self, worktree_path: Path, *, baseline_sha: str) -> str:
        if self._patch_raises:
            raise VcsCommandError("git diff failed (test double)")
        return self.patch

    # -- writes -----------------------------------------------------------
    def fetch(self, repo_root: Path, remote: str, ref: str) -> None:
        self.calls.append(("fetch", remote, ref))
        if self._fetch_raises:
            raise VcsCommandError("git fetch failed (test double)")
        self.fetches.append((repo_root, remote, ref))

    def commit_paths(self, repo_root: Path, paths: tuple[Path, ...], message: Redacted) -> str:
        if self._commit_paths_raises:
            raise VcsCommandError("git commit failed (test double)")
        self.commits.append((repo_root, tuple(paths), message.text))
        return _MOVED

    def push(self, repo_root: Path, branch: str) -> None:
        if self._push_raises:
            raise VcsCommandError("git push failed: non-fast-forward (test double)")
        self.pushes.append((repo_root, branch))

    def commit_paths_onto_remote_tip(
        self,
        repo_root: Path,
        *,
        remote: VcsRef,
        ref: VcsRef,
        writes: tuple[tuple[str, str], ...],
        message: Redacted,
        preflight_skip_reason: Redacted | None = None,
    ) -> str:
        self.remote_tip_reasons.append((preflight_skip_reason.text if preflight_skip_reason is not None else None))
        if self._remote_tip_raises:
            raise VcsCommandError("git commit-tree failed (test double)")
        self.remote_tip_writes.append(tuple(path for path, _ in writes))
        return _MOVED


class FakeProcess:
    """``ProcessPort`` stand-in: scripted liveness, never a real subprocess."""

    def __init__(self, alive: bool | list[bool] = False) -> None:
        if isinstance(alive, list) and not alive:
            # An empty script would IndexError on the first tick, which reads
            # as a fake defect rather than the supervisor assertion the test
            # meant to make.
            raise ValueError("FakeProcess(alive=[]) has no liveness to script")
        self._script = list(alive) if isinstance(alive, list) else None
        self._constant = alive if isinstance(alive, bool) else False
        self.is_alive_calls = 0

    def is_alive(self, pid: int) -> bool:
        self.is_alive_calls += 1
        if self._script is None:
            return self._constant
        if len(self._script) > 1:
            return self._script.pop(0)
        return self._script[0]

    def process_start_time(self, _pid: int) -> float | None:
        return None

    def run(self, argv, *, cwd=None, env=None, timeout=None):  # pragma: no cover - never reached
        raise AssertionError("no verify command may run in a unit test")


class FakePublisher:
    """``RunPublisherPort`` stand-in -- records, never reaches a host."""

    def __init__(self, *, handle: str | None = "handle-1") -> None:
        self._handle = handle
        self.published: list[object] = []
        self.heartbeats: list[str] = []
        self.completions: list[tuple[str, str, dict]] = []

    def publish(self, record) -> str | None:
        self.published.append(record)
        return self._handle

    def heartbeat(self, handle: str) -> None:
        self.heartbeats.append(handle)

    def complete(self, handle: str, *, status: str, result) -> None:
        self.completions.append((handle, status, dict(result)))


# --------------------------------------------------------------------------
# Fixtures / seeding helpers
# --------------------------------------------------------------------------


_BLOCKED_SPEC_TEMPLATE = (
    "---\n"
    "status: blocked\n"
    "baseline_revision: '{baseline}'\n"
    'blocking_condition: "an intent gap the harness could not close"\n'
    "---\n"
    "\n"
    "## Auto Run Result\n"
    "\n"
    "Status: escalated\n"
)

_READY_SPEC_TEXT = "---\nstatus: ready\n---\n\n## Intent\n\nDo the thing.\n"


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _worktree(repo_root: Path) -> Path:
    path = dispatch_core.dispatch_worktree_path(repo_root, _SLUG, _STORY_KEY)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _run_dir(repo_root: Path) -> Path:
    path = dispatch_core.dispatch_run_dir(repo_root, _SLUG, _RUN_ID)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _line(
    *,
    kind: str,
    phase: Phase,
    payload: dict,
    counter: int,
    run_id: str = _RUN_ID,
    ts: str = "2026-09-20T10:00:00.000Z",
    intent_id: JournalEntryId | None = None,
) -> str:
    entry = build_entry(
        id=JournalEntryId("dispatch-launcher-1", counter),
        ts=ts,
        run_id=run_id,
        kind=kind,
        phase=phase,
        payload=payload,
        intent_id=intent_id,
    )
    return prepare_for_write(entry).line


def _outcome_pair(*, kind: str, payload: dict, counter: int, run_id: str = _RUN_ID) -> tuple[str, str]:
    """An INTENT/OUTCOME pair -- ``fold`` refuses an orphaned outcome."""
    intent_id = JournalEntryId("dispatch-launcher-1", counter)
    intent = _line(kind=kind, phase=Phase.INTENT, payload=dict(payload), counter=counter, run_id=run_id)
    outcome = _line(
        kind=kind,
        phase=Phase.OUTCOME,
        payload=payload,
        counter=counter + 1,
        run_id=run_id,
        intent_id=intent_id,
    )
    return intent, outcome


def _launch_line(counter: int = 0, run_id: str = _RUN_ID) -> str:
    return _line(
        kind=dispatch_core.KIND_DISPATCH_LAUNCH,
        phase=Phase.INTENT,
        payload={"story_key": _STORY_KEY},
        counter=counter,
        run_id=run_id,
    )


def _seed_journal(run_dir: Path, lines: tuple[str, ...]) -> Path:
    path = run_dir / "journal.jsonl"
    path.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")
    return path


def _seed_spec(repo_root: Path, worktree: Path, *, primary: str, worktree_text: str | None = None) -> str:
    specs_dir = dispatch_core.planning_specs_dir(repo_root, _SLUG)
    specs_dir.mkdir(parents=True, exist_ok=True)
    spec_path = specs_dir / f"spec-{_STORY_KEY.replace('.', '-')}.md"
    spec_path.write_text(primary, encoding="utf-8")
    relocated = dispatch_core.relocated_spec_path(spec_path, repo_root, worktree)
    relocated.parent.mkdir(parents=True, exist_ok=True)
    relocated.write_text(worktree_text if worktree_text is not None else primary, encoding="utf-8")
    return str(relocated.resolve().relative_to(worktree.resolve()))


def _git_facts(
    *,
    baseline: str = _BASELINE,
    current: str = _MOVED,
    changed: tuple[str, ...] = ("src/pyforge/marshal/thing.py",),
    branch_merged: bool = False,
    story_merged: bool = False,
) -> DispatchGitFacts:
    return DispatchGitFacts(
        baseline_head_sha=baseline,
        current_head_sha=current,
        changed_paths=changed,
        branch_merged=branch_merged,
        story_merged_on_main=story_merged,
    )


def _clean_envelope():
    return build_envelope(command="dispatch verify", verdict="clean", data={"slug": _SLUG})


def _refused_envelope():
    return build_envelope(
        command="dispatch verify",
        verdict="gate-failed",
        data={"slug": _SLUG},
        findings=(Finding(code="MRS-GATE-001", severity=Severity.ERROR, message="verify command failed"),),
    )


def _advisory_envelope():
    return build_envelope(
        command="dispatch verify",
        verdict="warn",
        data={"slug": _SLUG},
        findings=(
            Finding(
                code="MRS-GATE-012",
                severity=Severity.WARN,
                message="touched a path outside the declared surface",
                path="src/other/thing.py",
            ),
        ),
    )


def _patch_verification(monkeypatch: pytest.MonkeyPatch, envelope_factory) -> None:
    monkeypatch.setattr(
        supervisor_main,
        "evaluate_dispatch_verification",
        lambda **_kwargs: envelope_factory(),
    )


def _patch_landing(
    monkeypatch: pytest.MonkeyPatch,
    *,
    verdict: DispatchLandingVerdict = DispatchLandingVerdict.LANDED,
    findings: tuple[Finding, ...] = (),
    wait_ticks: int = 0,
) -> list[dict]:
    """``wait_ticks``: how many times the fake landing calls the ``on_wait_tick`` it was handed --
    standing in for a check wait that polled that many times (Story 80.1, CAP-284)."""
    calls: list[dict] = []

    def _fake_execute(**kwargs):
        calls.append(kwargs)
        for _ in range(wait_ticks):
            kwargs["on_wait_tick"]()
        envelope = build_envelope(
            command="dispatch land",
            verdict="warn" if findings else "clean",
            data={"slug": _SLUG},
            findings=findings,
        )
        return (
            DispatchLandingResult(verdict=verdict, merge_sha=_MOVED, pr_number=7, subject="Merge", marshal_native=True),
            envelope,
        )

    monkeypatch.setattr(supervisor_main, "execute_dispatch_land", _fake_execute)
    return calls


# ==========================================================================
# Small helpers
# ==========================================================================


def test_append_entry_offloads_an_oversized_field_to_a_sidecar(tmp_path: Path) -> None:
    fs = FakeFs()
    run_dir = _run_dir(_repo(tmp_path))
    findings = [
        Finding(code="MRS-DISP-037", severity=Severity.WARN, message=f"padding finding {index:04d} " * 6).to_json_dict()
        for index in range(60)
    ]
    entry = build_entry(
        id=JournalEntryId("dispatch-supervisor-1", 1),
        ts="2026-09-20T10:00:00.000Z",
        run_id=_RUN_ID,
        kind=dispatch_core.KIND_DISPATCH_LAND,
        phase=Phase.OUTCOME,
        payload={"verdict": "landed", "ok": True, "land_findings": findings},
        intent_id=JournalEntryId("dispatch-supervisor-1", 0),
    )

    supervisor_main._append_entry(fs, run_dir, entry, fsync=False, offload_fields=frozenset({"land_findings"}))

    sidecars = [path for path in fs.files if path.name != "journal.jsonl"]
    assert sidecars, "an oversized land_findings payload must be offloaded to a sidecar"
    assert fs.appended and fs.appended[-1][2] is False


def test_fold_dispatch_journal_reads_sidecars_through_the_fs_port(tmp_path: Path) -> None:
    fs = FakeFs()
    run_dir = _run_dir(_repo(tmp_path))
    _seed_journal(run_dir, (_launch_line(),))
    findings = [
        Finding(code="MRS-DISP-037", severity=Severity.WARN, message=f"padding finding {index:04d} " * 6).to_json_dict()
        for index in range(60)
    ]
    payload = {"verdict": "landed", "ok": True, "land_findings": findings}

    def _land(counter: int, **offload) -> None:
        supervisor_main._append_entry(
            fs,
            run_dir,
            build_entry(
                id=JournalEntryId("dispatch-supervisor-1", counter),
                ts=f"2026-09-20T10:00:0{counter}.000Z",
                run_id=_RUN_ID,
                kind=dispatch_core.KIND_DISPATCH_LAND,
                phase=Phase.OUTCOME,
                payload=payload,
                intent_id=JournalEntryId("dispatch-supervisor-1", 0),
            ),
            fsync=False,
            **offload,
        )

    # An offloaded entry is what puts a sidecar reference in the journal line;
    # a journal with none folds identically whether or not the sidecar read
    # works, which is why this test writes both offload shapes first.
    #
    # Counter 1 takes the WHOLE payload to a sidecar (``prepare_for_write``,
    # AD-30: the line carries `{"sidecar_ref": ...}` in the payload's place),
    # so the folded entry is readable at all only because
    # ``_fold_dispatch_journal`` read that blob back through the ``FsPort``.
    _land(1)
    # Counter 2 is the dispatch-supervisor hotfix shape: only the named field
    # moves out, and the verdict-driving keys stay on the line.
    _land(2, offload_fields=frozenset({"land_findings"}))

    folded = supervisor_main._fold_dispatch_journal(fs, run_dir, fs.journal_text(run_dir))

    assert [entry.kind for entry in folded.by_kind(dispatch_core.KIND_DISPATCH_LAUNCH)] == ["dispatch-launch"]
    landed = folded.by_kind(dispatch_core.KIND_DISPATCH_LAND)
    assert [entry.payload["verdict"] for entry in landed] == ["landed", "landed"]
    whole, per_field = landed
    # Resolved from the blob: the placeholder line carries no findings at all.
    assert len(whole.payload["land_findings"]) == len(findings)
    # Field offload: the findings left the line, the verdict did not.
    assert "land_findings" not in per_field.payload
    assert per_field.payload[SCOPE_VIOLATION_ADVISORIES_SIDECAR_REF].endswith(".json")


def test_maybe_fetch_origin_main_only_fetches_on_the_fifth_tick(tmp_path: Path) -> None:
    vcs = FakeVcs()
    repo_root = _repo(tmp_path)

    supervisor_main._maybe_fetch_origin_main(vcs, repo_root, tick=4)
    assert vcs.fetches == []

    supervisor_main._maybe_fetch_origin_main(vcs, repo_root, tick=5)
    assert vcs.fetches == [(repo_root, "origin", "main")]


def test_maybe_fetch_origin_main_swallows_a_git_failure(tmp_path: Path) -> None:
    vcs = FakeVcs(fetch_raises=True)

    supervisor_main._maybe_fetch_origin_main(vcs, _repo(tmp_path), tick=10)

    assert vcs.fetches == []


def test_commit_pre_verify_wip_skips_a_clean_worktree(tmp_path: Path) -> None:
    vcs = FakeVcs(dirty=False)
    repo_root = _repo(tmp_path)

    supervisor_main._commit_pre_verify_wip(vcs, repo_root=repo_root, worktree=_worktree(repo_root))

    assert vcs.commits == []


def test_commit_pre_verify_wip_skips_an_empty_diff(tmp_path: Path) -> None:
    vcs = FakeVcs(dirty=True, changed_vs_head=())
    repo_root = _repo(tmp_path)

    supervisor_main._commit_pre_verify_wip(vcs, repo_root=repo_root, worktree=_worktree(repo_root))

    assert vcs.commits == []


def test_commit_pre_verify_wip_commits_the_dirty_paths(tmp_path: Path) -> None:
    vcs = FakeVcs(dirty=True, changed_vs_head=("a.py", "b.py"))
    repo_root = _repo(tmp_path)

    supervisor_main._commit_pre_verify_wip(vcs, repo_root=repo_root, worktree=_worktree(repo_root))

    assert vcs.commits and vcs.commits[0][1] == (Path("a.py"), Path("b.py"))


def test_commit_pre_verify_wip_reports_a_git_failure(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    vcs = FakeVcs(dirty=True, commit_paths_raises=True)
    repo_root = _repo(tmp_path)

    supervisor_main._commit_pre_verify_wip(vcs, repo_root=repo_root, worktree=_worktree(repo_root))

    assert "pre-verify WIP commit skipped" in capsys.readouterr().err


def test_launch_story_started_ts_reads_the_launch_intent(tmp_path: Path) -> None:
    fs = FakeFs()
    run_dir = _run_dir(_repo(tmp_path))
    _seed_journal(run_dir, (_launch_line(),))
    folded = supervisor_main._fold_dispatch_journal(fs, run_dir, fs.journal_text(run_dir))

    assert supervisor_main._launch_story_started_ts(folded, _RUN_ID) == "2026-09-20T10:00:00.000Z"
    assert supervisor_main._launch_story_started_ts(folded, "some-other-run") is None


def test_journal_dispatch_timing_writes_an_intent_and_an_outcome(tmp_path: Path) -> None:
    fs = FakeFs()
    run_dir = _run_dir(_repo(tmp_path))

    counter = supervisor_main._journal_dispatch_timing(
        fs=fs,
        run_dir=run_dir,
        run_id=_RUN_ID,
        writer_id="dispatch-supervisor-1",
        counter=0,
        story_key=_STORY_KEY,
        story_started_at="2026-09-20T10:00:00.000Z",
        story_ended_at="2026-09-20T10:30:00.000Z",
        baseline_revision=_BASELINE,
        final_revision=_MOVED,
    )

    assert counter == 2
    assert len(fs.appended) == 2


def test_journal_dispatch_timing_reports_an_fs_failure(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    fs = FakeFs(append_fails_for=frozenset({"journal.jsonl"}))
    run_dir = _run_dir(_repo(tmp_path))

    supervisor_main._journal_dispatch_timing(
        fs=fs,
        run_dir=run_dir,
        run_id=_RUN_ID,
        writer_id="dispatch-supervisor-1",
        counter=0,
        story_key=_STORY_KEY,
        story_started_at="2026-09-20T10:00:00.000Z",
        story_ended_at="2026-09-20T10:30:00.000Z",
        baseline_revision=_BASELINE,
        final_revision=_MOVED,
    )

    assert "cannot journal timing" in capsys.readouterr().err


def _preserve(fs: FakeFs, vcs: FakeVcs, run_dir: Path, worktree: Path) -> int:
    return supervisor_main._journal_dispatch_preserve(
        fs=fs,
        vcs=vcs,
        run_dir=run_dir,
        run_id=_RUN_ID,
        writer_id="dispatch-supervisor-1",
        counter=0,
        story_key=_STORY_KEY,
        worktree=worktree,
        baseline_head_sha=_BASELINE,
    )


def test_journal_dispatch_preserve_reports_a_capture_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_root = _repo(tmp_path)

    assert _preserve(FakeFs(), FakeVcs(patch_raises=True), _run_dir(repo_root), _worktree(repo_root)) == 0
    assert "preserve capture failed" in capsys.readouterr().err


def test_journal_dispatch_preserve_skips_an_empty_patch(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    fs = FakeFs()

    assert _preserve(fs, FakeVcs(patch="   \n"), _run_dir(repo_root), _worktree(repo_root)) == 0
    assert fs.appended == []


def test_journal_dispatch_preserve_reports_a_write_failure(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo_root = _repo(tmp_path)
    run_dir = _run_dir(repo_root)
    patch_name = supervisor_main.failed_patch_path(run_dir, _STORY_KEY).name
    fs = FakeFs(write_fails_for=frozenset({patch_name}))

    assert _preserve(fs, FakeVcs(patch="diff --git a/x b/x\n"), run_dir, _worktree(repo_root)) == 0
    assert "cannot write preserve patch" in capsys.readouterr().err


def test_journal_dispatch_preserve_writes_the_patch_and_journals_it(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    run_dir = _run_dir(repo_root)
    fs = FakeFs()

    counter = _preserve(fs, FakeVcs(patch="diff --git a/x b/x\n"), run_dir, _worktree(repo_root))

    assert counter == 2
    assert any(path.suffix == ".patch" for path in fs.files)
    assert len(fs.appended) == 2


def test_journal_dispatch_preserve_reports_a_journal_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_root = _repo(tmp_path)
    fs = FakeFs(append_fails_for=frozenset({"journal.jsonl"}))

    _preserve(fs, FakeVcs(patch="diff --git a/x b/x\n"), _run_dir(repo_root), _worktree(repo_root))

    assert "cannot journal preserve" in capsys.readouterr().err


def _ledger_path(repo_root: Path) -> Path:
    path = repo_root / "_bmad-output" / "projects" / _SLUG / "planning-artifacts" / "sprint-status-ledger.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@pytest.mark.parametrize(
    "ledger_text",
    [
        None,
        "development_status: [unbalanced\n",
        "- a list, not a mapping\n",
        "development_status: not-a-mapping\n",
    ],
)
def test_load_known_story_keys_degrades_closed(tmp_path: Path, ledger_text: str | None) -> None:
    repo_root = _repo(tmp_path)
    if ledger_text is not None:
        _ledger_path(repo_root).write_text(ledger_text, encoding="utf-8")

    keys = supervisor_main._load_known_story_keys(FakeFs(), repo_root=repo_root, project_slug=_SLUG)

    assert keys == frozenset()


def test_load_known_story_keys_skips_epic_and_malformed_rows(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    _ledger_path(repo_root).write_text(
        "development_status:\n"
        "  epic-51: done\n"
        "  51-11-a-real-story: done\n"
        "  not a story key at all: done\n"
        "  12: done\n",
        encoding="utf-8",
    )

    keys = supervisor_main._load_known_story_keys(FakeFs(), repo_root=repo_root, project_slug=_SLUG)

    assert {str(key) for key in keys} == {"51.11"}


# ==========================================================================
# gather_dispatch_git_facts
# ==========================================================================


def _gather(repo_root: Path, worktree: Path, vcs: FakeVcs, fs: FakeFs | None = None) -> DispatchGitFacts:
    return supervisor_main.gather_dispatch_git_facts(
        vcs,
        fs=fs if fs is not None else FakeFs(),
        repo_root=repo_root,
        worktree=worktree,
        story_key=_STORY_KEY,
        project_slug=_SLUG,
        baseline_head_sha=_BASELINE,
        merge_subject_template=_TEMPLATE,
    )


def test_gather_git_facts_never_trusts_a_merge_without_divergence(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    branch = dispatch_core.dispatch_worktree_branch(_SLUG, _STORY_KEY)

    facts = _gather(repo_root, worktree, FakeVcs(branches=frozenset({branch}), branch_merged=True))

    assert facts.branch_merged is False


def test_gather_git_facts_trusts_a_merge_once_the_branch_diverged(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    branch = dispatch_core.dispatch_worktree_branch(_SLUG, _STORY_KEY)

    facts = _gather(
        repo_root,
        worktree,
        FakeVcs(branches=frozenset({branch}), branch_merged=True, head_sha=_MOVED),
    )

    assert facts.branch_merged is True


def test_gather_git_facts_adopts_a_legacy_branch_checked_out_at_this_worktree(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    legacy = dispatch_core.legacy_dispatch_worktree_branch(_STORY_KEY)

    facts = _gather(
        repo_root,
        worktree,
        FakeVcs(branch_worktrees={legacy: worktree}, branch_merged=True, head_sha=_MOVED),
    )

    assert facts.branch_merged is True


def test_gather_git_facts_corroborates_a_station_branch_pr_against_the_tracked_spec(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    _seed_spec(repo_root, worktree, primary=_READY_SPEC_TEXT)
    subject = "Merge pull request #1477 from rxm7706/marshal/51-11-halt"

    merged = _gather(
        repo_root,
        worktree,
        FakeVcs(subjects=(subject,), spec_at_ref="---\nstatus: done\n---\n"),
    )
    not_merged = _gather(
        repo_root,
        worktree,
        FakeVcs(subjects=(subject,), spec_at_ref="---\nstatus: ready\n---\n"),
    )
    unreadable = _gather(
        repo_root,
        worktree,
        FakeVcs(subjects=(subject,), spec_at_ref_raises=True),
    )

    assert merged.story_merged_on_main is True
    assert not_merged.story_merged_on_main is False
    assert unreadable.story_merged_on_main is False


# -- Story 72.1 (CAP-280): every merge fact reads `origin/main`, never local `main` ----------------

_LOCAL_MAIN = local_branch_ref("main")
_PR_MERGE_SUBJECT = "Merge pull request #1477 from rxm7706/marshal/51-11-halt"
_SPEC_DONE = "---\nstatus: done\n---\n"


def _merge_vcs(*, on_origin: bool, on_local: bool, **kwargs: object) -> FakeVcs:
    """A ``FakeVcs`` whose story merge shows on ``origin/main``, on local ``main``, on both or on neither."""
    refs = ([ORIGIN_MAIN] if on_origin else []) + ([_LOCAL_MAIN] if on_local else [])
    branch = dispatch_core.dispatch_worktree_branch(_SLUG, _STORY_KEY)
    return FakeVcs(
        branches=frozenset({branch}),
        head_sha=_MOVED,
        subjects_by_ref={ref: (_PR_MERGE_SUBJECT,) for ref in refs},
        merged_into_refs=frozenset(refs),
        spec_at_ref=_SPEC_DONE,
        **kwargs,  # type: ignore[arg-type]
    )


def test_gather_git_facts_reads_the_merge_from_origin_main_when_local_main_lags(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    _seed_spec(repo_root, worktree, primary=_READY_SPEC_TEXT)
    vcs = _merge_vcs(on_origin=True, on_local=False)

    facts = _gather(repo_root, worktree, vcs)

    assert facts.story_merged_on_main is True
    assert facts.branch_merged is True
    # The branch is asked about through the full remote-tracking ref, and the subjects are read from
    # it -- local `main` is never consulted.
    assert ("is_branch_merged", ORIGIN_MAIN) in vcs.calls
    assert ("commit_subjects", ORIGIN_MAIN) in vcs.calls
    assert not any(_LOCAL_MAIN in call for call in vcs.calls)


def test_gather_git_facts_ignores_a_merge_only_local_main_carries(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    _seed_spec(repo_root, worktree, primary=_READY_SPEC_TEXT)

    facts = _gather(repo_root, worktree, _merge_vcs(on_origin=False, on_local=True))

    assert facts.story_merged_on_main is False
    assert facts.branch_merged is False


def test_gather_git_facts_raises_when_origin_main_is_unreadable(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    _seed_spec(repo_root, worktree, primary=_READY_SPEC_TEXT)
    # Local `main` carries the merge: an unreadable `origin/main` is neither merged nor read from local.
    vcs = _merge_vcs(on_origin=False, on_local=True, unreadable_refs={ORIGIN_MAIN: 1})

    with pytest.raises(VcsCommandError):
        _gather(repo_root, worktree, vcs)


# ==========================================================================
# Journal-reading predicates
# ==========================================================================


def _folded_from(tmp_path: Path, lines: tuple[str, ...]):
    fs = FakeFs()
    run_dir = _run_dir(_repo(tmp_path))
    _seed_journal(run_dir, lines)
    return supervisor_main._fold_dispatch_journal(fs, run_dir, fs.journal_text(run_dir))


def _land_outcome_lines(payload: dict, counter: int = 1) -> tuple[str, str]:
    return _outcome_pair(kind=dispatch_core.KIND_DISPATCH_LAND, payload=payload, counter=counter)


def test_landing_outcome_verdict_ignores_a_not_ok_outcome(tmp_path: Path) -> None:
    folded = _folded_from(tmp_path, (_launch_line(), *_land_outcome_lines({"verdict": "refused", "ok": False})))

    assert supervisor_main._landing_outcome_verdict(folded, _RUN_ID) is None
    assert supervisor_main._landing_succeeded(folded, _RUN_ID) is False
    assert supervisor_main._landing_already_journaled(folded, _RUN_ID) is True


def test_landing_outcome_verdict_ignores_a_non_string_verdict(tmp_path: Path) -> None:
    folded = _folded_from(tmp_path, (_launch_line(), *_land_outcome_lines({"verdict": 7, "ok": True})))

    assert supervisor_main._landing_outcome_verdict(folded, _RUN_ID) is None


def test_landing_outcome_verdict_reads_a_landed_outcome(tmp_path: Path) -> None:
    folded = _folded_from(tmp_path, (_launch_line(), *_land_outcome_lines({"verdict": "landed", "ok": True})))

    assert supervisor_main._landing_outcome_verdict(folded, _RUN_ID) == "landed"
    assert supervisor_main._landing_succeeded(folded, _RUN_ID) is True


def test_landing_predicates_are_empty_on_a_bare_launch(tmp_path: Path) -> None:
    folded = _folded_from(tmp_path, (_launch_line(),))

    assert supervisor_main._landing_outcome_verdict(folded, _RUN_ID) is None
    assert supervisor_main._landing_already_journaled(folded, _RUN_ID) is False
    assert supervisor_main._verification_already_journaled(folded, _RUN_ID) is False
    assert supervisor_main._dispatch_push_already_journaled(folded, _RUN_ID) is False
    assert supervisor_main._verification_outcome_verdict(folded, _RUN_ID) is None


def test_verification_outcome_verdict_reads_the_latest_outcome(tmp_path: Path) -> None:
    folded = _folded_from(
        tmp_path,
        (
            _launch_line(),
            *_outcome_pair(
                kind=dispatch_core.KIND_DISPATCH_VERIFICATION,
                payload={"verdict": "refused", "ok": False},
                counter=1,
            ),
            *_outcome_pair(
                kind=dispatch_core.KIND_DISPATCH_VERIFICATION,
                payload={"verdict": "verified", "ok": True},
                counter=3,
            ),
        ),
    )

    assert supervisor_main._verification_outcome_verdict(folded, _RUN_ID) == "verified"


def test_verification_outcome_verdict_reads_the_outcome_entry(tmp_path: Path) -> None:
    folded = _folded_from(
        tmp_path,
        (
            _launch_line(),
            *_outcome_pair(
                kind=dispatch_core.KIND_DISPATCH_VERIFICATION,
                payload={"verdict": "verified", "ok": True},
                counter=1,
            ),
            *_outcome_pair(
                kind=dispatch_core.KIND_DISPATCH_PUSH,
                payload={"branch": "dispatch/x", "outcome": "pushed", "ok": True},
                counter=3,
            ),
        ),
    )

    assert supervisor_main._verification_outcome_verdict(folded, _RUN_ID) == "verified"
    assert supervisor_main._verification_already_journaled(folded, _RUN_ID) is True
    assert supervisor_main._dispatch_push_already_journaled(folded, _RUN_ID) is True


def test_verification_outcome_verdict_ignores_a_non_string_payload(tmp_path: Path) -> None:
    folded = _folded_from(
        tmp_path,
        (
            _launch_line(),
            *_outcome_pair(
                kind=dispatch_core.KIND_DISPATCH_VERIFICATION,
                payload={"verdict": None, "ok": False},
                counter=1,
            ),
        ),
    )

    assert supervisor_main._verification_outcome_verdict(folded, _RUN_ID) is None


def test_session_awaits_verification_needs_a_dead_session_with_unmerged_progress() -> None:
    git = _git_facts()

    assert supervisor_main._session_awaits_verification(False, git) is True
    assert supervisor_main._session_awaits_verification(True, git) is False
    assert supervisor_main._session_awaits_verification(False, _git_facts(current=_BASELINE, changed=())) is False
    assert supervisor_main._session_awaits_verification(False, _git_facts(story_merged=True)) is False


# ==========================================================================
# _journal_finalize_attempt / _journal_dispatch_blocked
# ==========================================================================


def _finalize_attempt(fs: FakeFs, run_dir: Path, worktree: Path, **overrides) -> int:
    kwargs: dict = {
        "fs": fs,
        "run_dir": run_dir,
        "run_id": _RUN_ID,
        "writer_id": "dispatch-supervisor-1",
        "counter": 0,
        "story_key": _STORY_KEY,
        "worktree": worktree,
        "trigger": "harness-done",
        "committed": True,
        "pushed": True,
        "verified": True,
        "ok": True,
    }
    kwargs.update(overrides)
    return supervisor_main._journal_finalize_attempt(**kwargs)


def test_journal_finalize_attempt_records_a_failed_step(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    run_dir = _run_dir(repo_root)
    fs = FakeFs()

    counter = _finalize_attempt(
        fs,
        run_dir,
        _worktree(repo_root),
        ok=False,
        failed_step="push",
        failed_message="non-fast-forward",
    )

    assert counter == 2
    assert "non-fast-forward" in fs.appended[-1][1]


def test_journal_finalize_attempt_reports_an_fs_failure(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo_root = _repo(tmp_path)
    fs = FakeFs(append_fails_for=frozenset({"journal.jsonl"}))

    _finalize_attempt(fs, _run_dir(repo_root), _worktree(repo_root))

    assert "cannot journal finalize" in capsys.readouterr().err


def test_journal_dispatch_blocked_reports_an_fs_failure(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo_root = _repo(tmp_path)
    fs = FakeFs(append_fails_for=frozenset({"journal.jsonl"}))

    supervisor_main._journal_dispatch_blocked(
        fs=fs,
        run_dir=_run_dir(repo_root),
        run_id=_RUN_ID,
        writer_id="dispatch-supervisor-1",
        counter=0,
        story_key=_STORY_KEY,
        worktree=_worktree(repo_root),
        reason="an intent gap",
    )

    assert "cannot journal blocked halt" in capsys.readouterr().err


# ==========================================================================
# _worktree_story_spec / _spec_land_block_reason
# ==========================================================================


def _worktree_spec(repo_root: Path, worktree: Path, fs: FakeFs | None = None):
    return supervisor_main._worktree_story_spec(
        fs=fs if fs is not None else FakeFs(),
        repo_root=repo_root,
        slug=_SLUG,
        story_key=_STORY_KEY,
        worktree=worktree,
    )


def test_worktree_story_spec_is_silent_when_no_spec_exists(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)

    assert _worktree_spec(repo_root, _worktree(repo_root)) == (None, None)


def test_worktree_story_spec_reports_no_text_when_the_relocated_copy_is_absent(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    _seed_spec(repo_root, worktree, primary=_READY_SPEC_TEXT)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()

    relative, text = _worktree_spec(repo_root, elsewhere)

    assert text is None
    assert relative is None or not relative.startswith("..")


def test_worktree_story_spec_reads_the_relocated_copy(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    relative = _seed_spec(repo_root, worktree, primary=_READY_SPEC_TEXT)

    resolved_relative, text = _worktree_spec(repo_root, worktree)

    assert resolved_relative == relative
    assert text == _READY_SPEC_TEXT


def _block_reason(repo_root: Path, worktree: Path, git: DispatchGitFacts) -> str | None:
    return supervisor_main._spec_land_block_reason(
        fs=FakeFs(),
        repo_root=repo_root,
        slug=_SLUG,
        story_key=_STORY_KEY,
        worktree=worktree,
        git_facts=git,
    )


def test_spec_land_block_reason_is_none_without_a_spec(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)

    assert _block_reason(repo_root, _worktree(repo_root), _git_facts()) is None


def test_spec_land_block_reason_is_none_for_ordinary_work(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    _seed_spec(repo_root, worktree, primary=_READY_SPEC_TEXT)

    assert _block_reason(repo_root, worktree, _git_facts()) is None


def test_spec_land_block_reason_reads_a_blocked_spec(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    _seed_spec(repo_root, worktree, primary=_BLOCKED_SPEC_TEMPLATE.format(baseline=_BASELINE))

    assert _block_reason(repo_root, worktree, _git_facts()) == "an intent gap the harness could not close"


def test_spec_land_block_reason_refuses_spec_only_narration(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    relative = _seed_spec(repo_root, worktree, primary=_READY_SPEC_TEXT)

    reason = _block_reason(repo_root, worktree, _git_facts(changed=(relative,)))

    assert reason == "harness produced no changes beyond the tracked spec"


# ==========================================================================
# _blocked_halt_reason / _attempted_change_patch_paths / _promote_blocked_twin
# ==========================================================================


def _halt_reason(repo_root: Path, worktree: Path) -> tuple[str | None, bool]:
    return supervisor_main._blocked_halt_reason(
        fs=FakeFs(),
        repo_root=repo_root,
        slug=_SLUG,
        story_key=_STORY_KEY,
        worktree=worktree,
        git_facts=_git_facts(),
    )


def test_blocked_halt_reason_is_silent_without_an_auto_run_result(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    _seed_spec(repo_root, worktree, primary="---\nstatus: blocked\n---\n\nNo auto run result here.\n")

    assert _halt_reason(repo_root, worktree) == (None, False)


def test_blocked_halt_reason_is_stale_on_a_baseline_mismatch(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    _seed_spec(repo_root, worktree, primary=_BLOCKED_SPEC_TEMPLATE.format(baseline="0" * 40))

    assert _halt_reason(repo_root, worktree) == (None, True)


def test_attempted_change_patch_paths_skips_the_tier_three_store(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    kept = worktree / "notes" / "51-11-attempted-change.patch"
    kept.parent.mkdir(parents=True, exist_ok=True)
    kept.write_text("diff\n", encoding="utf-8")
    skipped = worktree / "implementation-artifacts" / "51-11-attempted-change.patch"
    skipped.parent.mkdir(parents=True, exist_ok=True)
    skipped.write_text("diff\n", encoding="utf-8")

    assert supervisor_main._attempted_change_patch_paths(worktree) == (kept,)


def _promote(repo_root: Path, worktree: Path, vcs: FakeVcs, fs: FakeFs | None = None) -> int:
    return supervisor_main._promote_blocked_twin(
        fs=fs if fs is not None else FakeFs(),
        vcs=vcs,
        run_dir=_run_dir(repo_root),
        run_id=_RUN_ID,
        writer_id="dispatch-supervisor-1",
        counter=0,
        repo_root=repo_root,
        slug=_SLUG,
        story_key=_STORY_KEY,
        worktree=worktree,
    )


def test_promote_blocked_twin_is_a_no_op_without_a_spec(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    vcs = FakeVcs()

    _promote(repo_root, _worktree(repo_root), vcs)

    assert vcs.remote_tip_writes == []


def test_promote_blocked_twin_is_a_no_op_when_the_twin_already_matches(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    _seed_spec(repo_root, worktree, primary=_BLOCKED_SPEC_TEMPLATE.format(baseline=_BASELINE))
    vcs = FakeVcs()

    _promote(repo_root, worktree, vcs)

    assert vcs.remote_tip_writes == []


def test_promote_blocked_twin_pushes_the_worktree_text_onto_the_remote_tip(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    _seed_spec(
        repo_root,
        worktree,
        primary=_READY_SPEC_TEXT,
        worktree_text=_BLOCKED_SPEC_TEMPLATE.format(baseline=_BASELINE),
    )
    vcs = FakeVcs()

    _promote(repo_root, worktree, vcs)

    assert vcs.remote_tip_writes and vcs.remote_tip_writes[0][0].endswith("spec-51-11.md")


def test_promote_blocked_twin_swallows_a_git_failure(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    _seed_spec(
        repo_root,
        worktree,
        primary=_READY_SPEC_TEXT,
        worktree_text=_BLOCKED_SPEC_TEMPLATE.format(baseline=_BASELINE),
    )
    vcs = FakeVcs(remote_tip_raises=True)
    fs = FakeFs()

    counter = _promote(repo_root, worktree, vcs, fs)

    assert vcs.remote_tip_writes == []
    # Story 68.1 (CAP-277): swallowed as far as the caller is concerned -- but journaled as a WARN.
    assert counter == 1
    journal = fs.journal_text(_run_dir(repo_root))
    assert "dispatch-blocked-twin-publish" in journal
    assert "MRS-LAND-011" in journal
    assert "git commit-tree failed (test double)" in journal


def test_promote_blocked_twin_gives_up_on_an_unreadable_spec(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    _seed_spec(repo_root, worktree, primary=_READY_SPEC_TEXT)
    vcs = FakeVcs()

    _promote(repo_root, worktree, vcs, FakeFs(read_fails_for=frozenset({"spec-51-11.md"})))

    assert vcs.remote_tip_writes == []


def test_promote_blocked_twin_gives_up_when_only_the_primary_spec_is_unreadable(
    tmp_path: Path,
) -> None:
    """The worktree twin reads clean and the primary checkout's copy refuses.

    Both files carry the same basename, so this is the one arm that needs a
    path-keyed refusal: it proves the promotion stops at the second read
    rather than pushing a twin it never diffed.
    """
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    _seed_spec(
        repo_root,
        worktree,
        primary=_READY_SPEC_TEXT,
        worktree_text=_BLOCKED_SPEC_TEMPLATE.format(baseline=_BASELINE),
    )
    primary = dispatch_core.resolve_story_spec_path(repo_root, _SLUG, _STORY_KEY)
    assert primary is not None
    vcs = FakeVcs()

    _promote(repo_root, worktree, vcs, FakeFs(read_fails_for=frozenset({primary.as_posix()})))

    assert vcs.remote_tip_writes == []


# ==========================================================================
# _commit_and_journal_blocked_halt
# ==========================================================================


def _commit_blocked(fs: FakeFs, vcs: FakeVcs, repo_root: Path, worktree: Path) -> tuple[int, bool]:
    return supervisor_main._commit_and_journal_blocked_halt(
        fs=fs,
        vcs=vcs,
        run_dir=_run_dir(repo_root),
        run_id=_RUN_ID,
        writer_id="dispatch-supervisor-1",
        counter=0,
        repo_root=repo_root,
        slug=_SLUG,
        story_key=_STORY_KEY,
        worktree=worktree,
        reason="an intent gap",
    )


def test_commit_and_journal_blocked_halt_refuses_on_a_diff_failure(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)

    assert _commit_blocked(FakeFs(), FakeVcs(changed_files_raises=True), repo_root, _worktree(repo_root)) == (0, False)


def test_commit_and_journal_blocked_halt_refuses_with_nothing_to_commit(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)

    assert _commit_blocked(FakeFs(), FakeVcs(changed_vs_head=()), repo_root, _worktree(repo_root)) == (0, False)


def test_commit_and_journal_blocked_halt_refuses_on_a_commit_failure(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)

    assert _commit_blocked(FakeFs(), FakeVcs(commit_paths_raises=True), repo_root, _worktree(repo_root)) == (0, False)


def test_commit_and_journal_blocked_halt_commits_and_journals(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    fs = FakeFs()

    counter, committed = _commit_blocked(fs, FakeVcs(), repo_root, _worktree(repo_root))

    assert (counter, committed) == (2, True)
    assert len(fs.appended) == 2


# ==========================================================================
# _run_and_journal_dispatch_push
# ==========================================================================


def _push(fs: FakeFs, vcs: FakeVcs, repo_root: Path, worktree: Path, git: DispatchGitFacts | None = None) -> int:
    return supervisor_main._run_and_journal_dispatch_push(
        fs=fs,
        vcs=vcs,
        run_dir=_run_dir(repo_root),
        run_id=_RUN_ID,
        writer_id="dispatch-supervisor-1",
        counter=0,
        repo_root=repo_root,
        slug=_SLUG,
        story_key=_STORY_KEY,
        worktree=worktree,
        git_facts=git if git is not None else _git_facts(),
    )


class _BranchResolveFailingVcs(FakeVcs):
    def branch_exists(self, repo_root: Path, branch: str) -> bool:
        raise VcsCommandError("git show-ref failed (test double)")


def test_dispatch_push_reports_a_branch_resolution_failure(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo_root = _repo(tmp_path)

    assert _push(FakeFs(), _BranchResolveFailingVcs(), repo_root, _worktree(repo_root)) == 0
    assert "cannot resolve branch before push" in capsys.readouterr().err


def test_dispatch_push_stays_silent_without_git_progress(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    vcs = FakeVcs(branches=frozenset({dispatch_core.dispatch_worktree_branch(_SLUG, _STORY_KEY)}))

    counter = _push(FakeFs(), vcs, repo_root, _worktree(repo_root), _git_facts(current=_BASELINE, changed=()))

    assert (counter, vcs.pushes) == (0, [])


def test_dispatch_push_journals_a_successful_push(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    branch = dispatch_core.dispatch_worktree_branch(_SLUG, _STORY_KEY)
    vcs = FakeVcs(branches=frozenset({branch}))
    fs = FakeFs()

    counter = _push(fs, vcs, repo_root, _worktree(repo_root))

    assert counter == 2
    assert vcs.pushes and vcs.pushes[0][1] == branch
    assert '"outcome": "pushed"' in fs.appended[-1][1]


def test_dispatch_push_journals_a_failure_with_a_finding(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    branch = dispatch_core.dispatch_worktree_branch(_SLUG, _STORY_KEY)
    fs = FakeFs()

    counter = _push(fs, FakeVcs(branches=frozenset({branch}), push_raises=True), repo_root, _worktree(repo_root))

    assert counter == 2
    assert "MRS-DISP-037" in fs.appended[-1][1]


def test_dispatch_push_reports_a_journal_failure(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo_root = _repo(tmp_path)
    branch = dispatch_core.dispatch_worktree_branch(_SLUG, _STORY_KEY)
    fs = FakeFs(append_fails_for=frozenset({"journal.jsonl"}))

    _push(fs, FakeVcs(branches=frozenset({branch})), repo_root, _worktree(repo_root))

    assert "cannot journal dispatch push" in capsys.readouterr().err


# ==========================================================================
# _run_and_journal_verification
# ==========================================================================


def _verify(fs: FakeFs, repo_root: Path, worktree: Path, *, story_key: str = _STORY_KEY) -> int:
    return supervisor_main._run_and_journal_verification(
        fs=fs,
        vcs=FakeVcs(),
        process=FakeProcess(),
        run_dir=_run_dir(repo_root),
        run_id=_RUN_ID,
        writer_id="dispatch-supervisor-1",
        counter=0,
        repo_root=repo_root,
        slug=_SLUG,
        story_key=story_key,
        worktree=worktree,
    )


def test_verification_refuses_an_unresolvable_story_key(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    fs = FakeFs()

    assert _verify(fs, repo_root, _worktree(repo_root), story_key="not a story key") == 0
    assert fs.appended == []


def test_verification_journals_a_clean_gate_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    _seed_spec(repo_root, worktree, primary=_READY_SPEC_TEXT)
    _patch_verification(monkeypatch, _clean_envelope)
    fs = FakeFs()

    counter = _verify(fs, repo_root, worktree)

    assert counter == 2
    assert '"verdict": "verified"' in fs.appended[-1][1]


def test_verification_journals_a_refusal_with_the_failed_gate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    _patch_verification(monkeypatch, _refused_envelope)
    fs = FakeFs()

    _verify(fs, repo_root, worktree)

    assert '"verdict": "refused"' in fs.appended[-1][1]
    assert "MRS-GATE-001" in fs.appended[-1][1]


def test_verification_threads_scope_violation_advisories(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    _patch_verification(monkeypatch, _advisory_envelope)
    fs = FakeFs()

    _verify(fs, repo_root, worktree)

    assert "MRS-GATE-012" in fs.appended[-1][1]


def test_verification_reports_a_journal_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_root = _repo(tmp_path)
    _patch_verification(monkeypatch, _clean_envelope)
    fs = FakeFs(append_fails_for=frozenset({"journal.jsonl"}))

    _verify(fs, repo_root, _worktree(repo_root))

    assert "cannot journal verification" in capsys.readouterr().err


# ==========================================================================
# _run_and_journal_landing / _land_or_journal_block
# ==========================================================================


def _land(fs: FakeFs, repo_root: Path, worktree: Path) -> int:
    return supervisor_main._run_and_journal_landing(
        fs=fs,
        vcs=FakeVcs(),
        process=FakeProcess(),
        run_dir=_run_dir(repo_root),
        run_id=_RUN_ID,
        writer_id="dispatch-supervisor-1",
        counter=0,
        repo_root=repo_root,
        slug=_SLUG,
        story_key=_STORY_KEY,
        worktree=worktree,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        merge_subject_template=_TEMPLATE,
    )


def test_landing_journals_the_land_verdict_and_its_findings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = _repo(tmp_path)
    findings = (Finding(code="MRS-DISP-037", severity=Severity.WARN, message="an advisory"),)
    calls = _patch_landing(monkeypatch, findings=findings)
    fs = FakeFs()

    counter = _land(fs, repo_root, _worktree(repo_root))

    assert counter == 2
    assert calls and calls[0]["story_key"] == _STORY_KEY
    assert "MRS-DISP-037" in fs.appended[-1][1]


def test_landing_reports_a_journal_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_root = _repo(tmp_path)
    _patch_landing(monkeypatch)
    fs = FakeFs(append_fails_for=frozenset({"journal.jsonl"}))

    _land(fs, repo_root, _worktree(repo_root))

    assert "cannot journal landing" in capsys.readouterr().err


def _land_or_block(fs: FakeFs, repo_root: Path, worktree: Path, git: DispatchGitFacts) -> int:
    return supervisor_main._land_or_journal_block(
        fs=fs,
        vcs=FakeVcs(),
        process=FakeProcess(),
        run_dir=_run_dir(repo_root),
        run_id=_RUN_ID,
        writer_id="dispatch-supervisor-1",
        counter=0,
        repo_root=repo_root,
        slug=_SLUG,
        story_key=_STORY_KEY,
        worktree=worktree,
        git_facts=git,
        verification_verdict=DispatchVerificationVerdict.VERIFIED,
        merge_subject_template=_TEMPLATE,
    )


def test_land_or_journal_block_halts_on_a_blocked_worktree_spec(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    _seed_spec(repo_root, worktree, primary=_BLOCKED_SPEC_TEMPLATE.format(baseline=_BASELINE))
    calls = _patch_landing(monkeypatch)
    fs = FakeFs()

    counter = _land_or_block(fs, repo_root, worktree, _git_facts())

    assert (counter, calls) == (2, [])
    assert "dispatch-blocked" in fs.appended[-1][1]


def test_land_or_journal_block_lands_ordinary_work(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    _seed_spec(repo_root, worktree, primary=_READY_SPEC_TEXT)
    calls = _patch_landing(monkeypatch)

    counter = _land_or_block(FakeFs(), repo_root, worktree, _git_facts())

    assert counter == 2
    assert len(calls) == 1


# ==========================================================================
# _run_supervisor_finalize_sequence
# ==========================================================================


def _finalize(
    fs: FakeFs,
    vcs: FakeVcs,
    repo_root: Path,
    worktree: Path,
    *,
    journal_lines: tuple[str, ...] = (),
    session_log: str | None = "implementation done",
    git: DispatchGitFacts | None = None,
) -> tuple[int, bool]:
    run_dir = _run_dir(repo_root)
    _seed_journal(run_dir, (_launch_line(),) + journal_lines)
    folded = supervisor_main._fold_dispatch_journal(fs, run_dir, fs.journal_text(run_dir))
    return supervisor_main._run_supervisor_finalize_sequence(
        fs=fs,
        vcs=vcs,
        process=FakeProcess(),
        run_dir=run_dir,
        run_id=_RUN_ID,
        writer_id="dispatch-supervisor-1",
        counter=0,
        repo_root=repo_root,
        slug=_SLUG,
        story_key=_STORY_KEY,
        worktree=worktree,
        git_facts=git if git is not None else _git_facts(),
        session_log=session_log,
        merge_subject_template=_TEMPLATE,
        folded=folded,
    )


def test_finalize_sequence_gives_up_when_the_commit_fails(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    fs = FakeFs()

    counter, ok = _finalize(fs, FakeVcs(commit_paths_raises=True), repo_root, _worktree(repo_root))

    assert (counter, ok) == (2, False)
    assert '"failed_step": "commit"' in fs.appended[-1][1]


def test_finalize_sequence_gives_up_when_the_push_fails(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    branch = dispatch_core.dispatch_worktree_branch(_SLUG, _STORY_KEY)
    fs = FakeFs()

    counter, ok = _finalize(
        fs,
        FakeVcs(branches=frozenset({branch}), push_raises=True, head_sha=_MOVED),
        repo_root,
        _worktree(repo_root),
    )

    assert ok is False
    assert '"failed_step": "push"' in fs.appended[-1][1]
    assert counter > 0


def test_finalize_sequence_reads_an_already_journaled_push(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    _seed_spec(repo_root, worktree, primary=_READY_SPEC_TEXT)
    _patch_verification(monkeypatch, _clean_envelope)
    branch = dispatch_core.dispatch_worktree_branch(_SLUG, _STORY_KEY)
    push_lines = _outcome_pair(
        kind=dispatch_core.KIND_DISPATCH_PUSH,
        payload={"branch": branch, "outcome": "pushed", "ok": True},
        counter=1,
    )
    vcs = FakeVcs(branches=frozenset({branch}), head_sha=_MOVED)
    fs = FakeFs()

    counter, ok = _finalize(fs, vcs, repo_root, worktree, journal_lines=push_lines)

    assert ok is True
    assert vcs.pushes == []
    assert '"pushed": true' in fs.appended[-1][1]
    assert counter > 0


def test_finalize_sequence_reads_an_already_journaled_push_failure(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    branch = dispatch_core.dispatch_worktree_branch(_SLUG, _STORY_KEY)
    push_lines = _outcome_pair(
        kind=dispatch_core.KIND_DISPATCH_PUSH,
        payload={"branch": branch, "outcome": "push-failed", "ok": False, "failed_message": "rejected"},
        counter=1,
    )
    fs = FakeFs()

    _counter, ok = _finalize(
        fs,
        FakeVcs(branches=frozenset({branch}), head_sha=_MOVED),
        repo_root,
        _worktree(repo_root),
        journal_lines=push_lines,
    )

    assert ok is False
    assert '"failed_message": "rejected"' in fs.appended[-1][1]


def test_finalize_sequence_stops_before_verify_on_a_blocked_spec(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    _seed_spec(repo_root, worktree, primary=_BLOCKED_SPEC_TEMPLATE.format(baseline=_BASELINE))
    branch = dispatch_core.dispatch_worktree_branch(_SLUG, _STORY_KEY)
    fs = FakeFs()

    _counter, ok = _finalize(fs, FakeVcs(branches=frozenset({branch}), head_sha=_MOVED), repo_root, worktree)

    assert ok is False
    assert "dispatch-blocked" in fs.appended[-1][1]


def test_finalize_sequence_verifies_and_journals_a_successful_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    _seed_spec(repo_root, worktree, primary=_READY_SPEC_TEXT)
    _patch_verification(monkeypatch, _clean_envelope)
    branch = dispatch_core.dispatch_worktree_branch(_SLUG, _STORY_KEY)
    vcs = FakeVcs(branches=frozenset({branch}), head_sha=_MOVED)
    fs = FakeFs()

    _counter, ok = _finalize(fs, vcs, repo_root, worktree)

    assert ok is True
    assert vcs.commits and vcs.pushes
    assert '"verified": true' in fs.appended[-1][1]


def test_finalize_sequence_reuses_an_already_journaled_verification(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    _seed_spec(repo_root, worktree, primary=_READY_SPEC_TEXT)
    branch = dispatch_core.dispatch_worktree_branch(_SLUG, _STORY_KEY)
    lines = (
        *_outcome_pair(
            kind=dispatch_core.KIND_DISPATCH_PUSH,
            payload={"branch": branch, "outcome": "pushed", "ok": True},
            counter=1,
        ),
        *_outcome_pair(
            kind=dispatch_core.KIND_DISPATCH_VERIFICATION,
            payload={"verdict": "verified", "ok": True},
            counter=3,
        ),
    )
    fs = FakeFs()

    _counter, ok = _finalize(
        fs,
        FakeVcs(branches=frozenset({branch}), head_sha=_MOVED),
        repo_root,
        worktree,
        journal_lines=lines,
    )

    assert ok is True
    assert '"verified": true' in fs.appended[-1][1]


def test_finalize_sequence_survives_a_git_fact_regather_failure(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    _seed_spec(repo_root, worktree, primary=_BLOCKED_SPEC_TEMPLATE.format(baseline=_BASELINE))
    fs = FakeFs()

    _counter, ok = _finalize(fs, FakeVcs(head_sha_raises_times=1), repo_root, worktree)

    assert ok is False


# ==========================================================================
# run_dispatch_supervisor -- the tick loop
# ==========================================================================


def _run(
    repo_root: Path,
    *,
    fs: FakeFs,
    vcs: FakeVcs,
    process: FakeProcess,
    publisher: FakePublisher | None,
    worktree: Path | None = None,
    story_key: str = _STORY_KEY,
) -> int:
    return supervisor_main.run_dispatch_supervisor(
        repo_root=repo_root,
        slug=_SLUG,
        run_id=_RUN_ID,
        session_pid=_SESSION_PID,
        worktree=worktree if worktree is not None else _worktree(repo_root),
        story_key=story_key,
        baseline_head_sha=_BASELINE,
        merge_subject_template=_TEMPLATE,
        fs=fs,
        vcs=vcs,
        process=process,
        publisher=publisher,
    )


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> _FakeClock:
    fake = _FakeClock()
    monkeypatch.setattr(supervisor_main, "time", fake)
    return fake


def test_supervisor_exits_inert_without_a_journal(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo_root = _repo(tmp_path)
    _run_dir(repo_root)

    code = _run(repo_root, fs=FakeFs(), vcs=FakeVcs(), process=FakeProcess(), publisher=FakePublisher())

    assert code == 0
    assert "no journal at" in capsys.readouterr().err


def test_supervisor_exits_inert_without_a_launch_entry(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo_root = _repo(tmp_path)
    _seed_journal(_run_dir(repo_root), (_launch_line(run_id="a-different-run"),))

    code = _run(repo_root, fs=FakeFs(), vcs=FakeVcs(), process=FakeProcess(), publisher=FakePublisher())

    assert code == 0
    assert "no dispatch-launch for run" in capsys.readouterr().err


def test_supervisor_fails_when_the_attach_entry_cannot_be_journaled(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_root = _repo(tmp_path)
    _seed_journal(_run_dir(repo_root), (_launch_line(),))
    fs = FakeFs(append_fails_for=frozenset({"journal.jsonl"}))

    code = _run(repo_root, fs=fs, vcs=FakeVcs(), process=FakeProcess(), publisher=FakePublisher())

    assert code == 1
    assert "cannot journal attach" in capsys.readouterr().err


def test_supervisor_journals_a_publish_finding_through_the_host_publisher(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    """``publisher=None`` builds the real ``HostPublisher``; with no bearer
    file it reports a finding through the supervisor's own callback and never
    reaches the network."""
    repo_root = _repo(tmp_path)
    _seed_journal(_run_dir(repo_root), (_launch_line(),))
    monkeypatch.delenv("PYFORGE_IDP_BEARER_FILE", raising=False)
    fs = FakeFs()

    code = _run(repo_root, fs=fs, vcs=FakeVcs(), process=FakeProcess(), publisher=None)

    assert code == 0
    assert any("MRS-SUPV-010" in line for _path, line, _fsync in fs.appended)


def test_supervisor_journals_a_failed_run_to_completion(tmp_path: Path, clock: _FakeClock) -> None:
    repo_root = _repo(tmp_path)
    _seed_journal(_run_dir(repo_root), (_launch_line(),))
    fs = FakeFs()
    publisher = FakePublisher()

    code = _run(
        repo_root,
        fs=fs,
        vcs=FakeVcs(head_sha=_BASELINE, changed=()),
        process=FakeProcess(alive=False),
        publisher=publisher,
    )

    assert code == 0
    assert publisher.completions and publisher.completions[0][1] == DispatchSessionVerdict.FAILED.value
    journal = fs.journal_text(_run_dir(repo_root))
    assert '"stop_reason": "failed"' in journal
    assert dispatch_core.KIND_DISPATCH_TIMING in journal


def test_supervisor_retries_after_a_git_fact_gather_failure(
    tmp_path: Path, clock: _FakeClock, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_root = _repo(tmp_path)
    _seed_journal(_run_dir(repo_root), (_launch_line(),))

    code = _run(
        repo_root,
        fs=FakeFs(),
        vcs=FakeVcs(head_sha=_BASELINE, changed=(), head_sha_raises_times=1),
        process=FakeProcess(alive=False),
        publisher=FakePublisher(),
    )

    assert code == 0
    assert clock.sleeps == [supervisor_main._TICK_SECONDS]
    assert "git fact gather failed" in capsys.readouterr().err


def test_supervisor_heartbeats_a_live_session_then_terminalizes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    repo_root = _repo(tmp_path)
    run_dir = _run_dir(repo_root)
    _seed_journal(run_dir, (_launch_line(),))
    (run_dir / "session.log").write_text("working…\n", encoding="utf-8")
    monkeypatch.setattr(supervisor_main, "should_checkpoint_on_idle", lambda **_kwargs: True)
    vcs = FakeVcs(head_sha=_BASELINE, changed=(), dirty=True)
    publisher = FakePublisher()

    code = _run(
        repo_root,
        fs=FakeFs(),
        vcs=vcs,
        process=FakeProcess(alive=[True, False]),
        publisher=publisher,
    )

    assert code == 0
    assert publisher.heartbeats == ["handle-1"]
    assert clock.sleeps == [supervisor_main._TICK_SECONDS]
    assert any("auto-checkpoint" in message for _root, _paths, message in vcs.commits)


def test_supervisor_checkpoints_a_live_session_only_once_idle_reaches_the_threshold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real idle predicate, driven by a real monotonic interval.

    The ``clock`` fixture steps ``monotonic()`` by 0.0, so in every other
    tick-loop test ``idle_elapsed_s = time.monotonic() -
    last_session_activity_monotonic`` is 0.0 and the threshold comparison
    decides nothing -- the heartbeat test above has to stub
    ``should_checkpoint_on_idle`` to reach the checkpoint at all. Here the
    predicate is the real one and the clock advances, so the arithmetic is
    what decides: frozen, no checkpoint; a tick's worth of idle, a
    checkpoint.
    """

    def _one_run(*, mono_step: float) -> FakeVcs:
        repo_root = _repo(tmp_path / f"step-{mono_step}")
        run_dir = _run_dir(repo_root)
        _seed_journal(run_dir, (_launch_line(),))
        (run_dir / "session.log").write_text("working…\n", encoding="utf-8")
        monkeypatch.setattr(supervisor_main, "time", _FakeClock(mono_step=mono_step))
        vcs = FakeVcs(head_sha=_BASELINE, changed=(), dirty=True)
        _run(
            repo_root,
            fs=FakeFs(),
            vcs=vcs,
            process=FakeProcess(alive=[True, False]),
            publisher=FakePublisher(),
        )
        return vcs

    frozen = _one_run(mono_step=0.0)
    advancing = _one_run(mono_step=float(supervisor_main._TICK_SECONDS))

    assert not any("auto-checkpoint" in message for _root, _paths, message in frozen.commits)
    assert any("auto-checkpoint" in message for _root, _paths, message in advancing.commits)


def test_supervisor_treats_an_unreadable_worktree_status_as_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    repo_root = _repo(tmp_path)
    run_dir = _run_dir(repo_root)
    _seed_journal(run_dir, (_launch_line(),))
    vcs = FakeVcs(head_sha=_BASELINE, changed=(), uncommitted_raises=True)

    code = _run(
        repo_root,
        fs=FakeFs(),
        vcs=vcs,
        process=FakeProcess(alive=[True, False]),
        publisher=FakePublisher(),
    )

    assert code == 0
    assert vcs.commits == []


def test_supervisor_finalizes_verifies_and_lands_a_finished_harness_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    repo_root = _repo(tmp_path)
    run_dir = _run_dir(repo_root)
    worktree = _worktree(repo_root)
    _seed_journal(run_dir, (_launch_line(),))
    (run_dir / "session.log").write_text("implementation done\n", encoding="utf-8")
    _seed_spec(repo_root, worktree, primary=_READY_SPEC_TEXT)
    _patch_verification(monkeypatch, _clean_envelope)
    land_calls = _patch_landing(monkeypatch)
    branch = dispatch_core.dispatch_worktree_branch(_SLUG, _STORY_KEY)
    vcs = FakeVcs(branches=frozenset({branch}), head_sha=_MOVED)
    fs = FakeFs()
    publisher = FakePublisher()

    code = _run(repo_root, fs=fs, vcs=vcs, process=FakeProcess(alive=False), publisher=publisher)

    assert code == 0
    assert len(land_calls) == 1
    journal = fs.journal_text(run_dir)
    assert dispatch_core.KIND_DISPATCH_FINALIZE in journal
    assert '"verdict": "landed"' in journal
    # Local `main` never shows the merge here (the fake primary was not
    # fast-forwarded), so the repository facts alone read `stopped_externally`;
    # the journaled land is what makes the run `completed` (Story 67.1).
    assert publisher.completions[0][1] == DispatchSessionVerdict.COMPLETED.value


def _completion_payload(fs: FakeFs, run_dir: Path, phase: Phase) -> dict[str, object]:
    """The payload of the run's ``dispatch-completion`` entry for ``phase``."""
    for line in fs.journal_text(run_dir).splitlines():
        entry = json.loads(line)
        if entry["kind"] == dispatch_core.KIND_DISPATCH_COMPLETION and entry["phase"] == phase.value:
            return entry["payload"]
    raise AssertionError(f"no dispatch-completion {phase.value} journaled")


@pytest.mark.parametrize("branch_present", [False, True], ids=["branch-retired", "branch-present"])
def test_a_landed_run_reads_completed_when_local_main_lacks_the_merge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _FakeClock, branch_present: bool
) -> None:
    repo_root = _repo(tmp_path)
    run_dir = _run_dir(repo_root)
    worktree = _worktree(repo_root)
    _seed_journal(run_dir, (_launch_line(),))
    (run_dir / "session.log").write_text("implementation done\n", encoding="utf-8")
    _seed_spec(repo_root, worktree, primary=_READY_SPEC_TEXT)
    _patch_verification(monkeypatch, _clean_envelope)
    land_calls = _patch_landing(monkeypatch)
    branch = dispatch_core.dispatch_worktree_branch(_SLUG, _STORY_KEY)
    branches = frozenset({branch}) if branch_present else frozenset()
    fs = FakeFs()
    publisher = FakePublisher()

    code = _run(
        repo_root,
        fs=fs,
        vcs=FakeVcs(branches=branches, head_sha=_MOVED),
        process=FakeProcess(alive=False),
        publisher=publisher,
    )

    assert code == 0
    assert len(land_calls) == 1
    assert publisher.completions[0][1] == DispatchSessionVerdict.COMPLETED.value
    outcome = _completion_payload(fs, run_dir, Phase.OUTCOME)
    assert outcome["verdict"] == DispatchSessionVerdict.COMPLETED.value
    assert outcome["stop_reason"] is None
    # The journal decides the process verdict; git keeps the repository facts
    # as gathered, never overwritten from the journal (AD-33).
    intent = _completion_payload(fs, run_dir, Phase.INTENT)
    assert intent["story_merged_on_main"] is False
    assert intent["branch_merged"] is False


def test_a_landed_run_reads_completed_when_the_repository_reread_after_the_land_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    repo_root = _repo(tmp_path)
    run_dir = _run_dir(repo_root)
    worktree = _worktree(repo_root)
    _seed_journal(run_dir, (_launch_line(),))
    (run_dir / "session.log").write_text("implementation done\n", encoding="utf-8")
    _seed_spec(repo_root, worktree, primary=_READY_SPEC_TEXT)
    _patch_verification(monkeypatch, _clean_envelope)
    _patch_landing(monkeypatch)
    fs = FakeFs()
    # Refuses every repository re-read once the land is journaled: only the
    # journal can say the run is done.
    vcs = _HeadShaFailsOnceJournaledVcs(
        fs=fs, run_dir=run_dir, marker=dispatch_core.KIND_DISPATCH_LAND, head_sha=_MOVED
    )
    publisher = FakePublisher()

    code = _run(repo_root, fs=fs, vcs=vcs, process=FakeProcess(alive=False), publisher=publisher)

    assert code == 0
    assert vcs.refused >= 1
    assert publisher.completions[0][1] == DispatchSessionVerdict.COMPLETED.value
    assert _completion_payload(fs, run_dir, Phase.OUTCOME)["stop_reason"] is None
    # The facts recorded are the ones gathered before the land.
    intent = _completion_payload(fs, run_dir, Phase.INTENT)
    assert intent["baseline_head_sha"] == _BASELINE
    assert intent["current_head_sha"] == _MOVED
    assert intent["story_merged_on_main"] is False
    assert intent["branch_merged"] is False


class _AlreadyLandedOkFs(FakeFs):
    """Journals the supervisor's ``already_landed`` land OUTCOME as ``ok``.

    The supervisor's own journaling writes ``ok`` only for ``landed``, so an
    ``already_landed`` outcome reading ``ok`` is a journal shape the
    supervisor does not itself produce; the verdict predicate
    (``landing_journal_indicates_complete``) accepts it, and this pins that the
    terminal re-read honours it."""

    def append_line(self, path: Path, line: str, *, fsync: bool) -> None:
        if dispatch_core.KIND_DISPATCH_LAND in line and '"verdict": "already_landed"' in line:
            line = line.replace('"ok": false', '"ok": true')
        super().append_line(path, line, fsync=fsync)


def test_an_already_landed_run_reads_completed_when_local_main_lacks_the_merge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    repo_root = _repo(tmp_path)
    run_dir = _run_dir(repo_root)
    worktree = _worktree(repo_root)
    _seed_journal(run_dir, (_launch_line(),))
    (run_dir / "session.log").write_text("implementation done\n", encoding="utf-8")
    _seed_spec(repo_root, worktree, primary=_READY_SPEC_TEXT)
    _patch_verification(monkeypatch, _clean_envelope)
    _patch_landing(monkeypatch, verdict=DispatchLandingVerdict.ALREADY_LANDED)
    branch = dispatch_core.dispatch_worktree_branch(_SLUG, _STORY_KEY)
    fs = _AlreadyLandedOkFs()
    publisher = FakePublisher()

    code = _run(
        repo_root,
        fs=fs,
        vcs=FakeVcs(branches=frozenset({branch}), head_sha=_MOVED),
        process=FakeProcess(alive=False),
        publisher=publisher,
    )

    assert code == 0
    assert publisher.completions[0][1] == DispatchSessionVerdict.COMPLETED.value
    assert _completion_payload(fs, run_dir, Phase.OUTCOME)["stop_reason"] is None


@pytest.mark.parametrize(
    "land_verdict",
    [DispatchLandingVerdict.REFUSED, DispatchLandingVerdict.SKIPPED_UNVERIFIED],
    ids=lambda verdict: verdict.value,
)
def test_a_land_that_did_not_succeed_still_reads_from_repository_facts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _FakeClock, land_verdict: DispatchLandingVerdict
) -> None:
    repo_root = _repo(tmp_path)
    run_dir = _run_dir(repo_root)
    worktree = _worktree(repo_root)
    _seed_journal(run_dir, (_launch_line(),))
    (run_dir / "session.log").write_text("implementation done\n", encoding="utf-8")
    _seed_spec(repo_root, worktree, primary=_READY_SPEC_TEXT)
    _patch_verification(monkeypatch, _clean_envelope)
    _patch_landing(monkeypatch, verdict=land_verdict)
    branch = dispatch_core.dispatch_worktree_branch(_SLUG, _STORY_KEY)
    fs = FakeFs()
    publisher = FakePublisher()

    code = _run(
        repo_root,
        fs=fs,
        vcs=FakeVcs(branches=frozenset({branch}), head_sha=_MOVED),
        process=FakeProcess(alive=False),
        publisher=publisher,
    )

    assert code == 0
    # Exactly the verdict the repository facts give today (local `main` lacks
    # the merge): the journal override does not fire for a land that is not `ok`.
    assert publisher.completions[0][1] == DispatchSessionVerdict.STOPPED_EXTERNALLY.value
    outcome = _completion_payload(fs, run_dir, Phase.OUTCOME)
    assert outcome["verdict"] == DispatchSessionVerdict.STOPPED_EXTERNALLY.value
    assert outcome["stop_reason"] == "external-operator-stop"


class _LandsDuringFinalizeFs(FakeFs):
    """A second journal writer lands the story while finalize runs.

    The run journal is multi-writer: the dispatch CLI can land a story and
    journal the outcome between the supervisor's own reads. That is why
    ``__main__.py:1523-1525`` re-folds the journal after the finalize
    sequence, and why ``:1540-1542`` terminalizes as ``COMPLETED`` from the
    re-read instead of re-deriving a terminal verdict -- the finalize
    sequence itself only commits, pushes, and verifies, so it can never be
    the writer of that land entry.
    """

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.injected = False

    def append_line(self, path: Path, line: str, *, fsync: bool) -> None:
        super().append_line(path, line, fsync=fsync)
        if self.injected or dispatch_core.KIND_DISPATCH_FINALIZE not in line:
            return
        if '"phase": "outcome"' not in line:
            return
        self.injected = True
        for extra in _land_outcome_lines({"verdict": "landed", "ok": True}, counter=900):
            super().append_line(path, extra, fsync=False)


class _HeadShaFailsOnceJournaledVcs(FakeVcs):
    """``worktree_head_sha`` refuses once the journal names ``marker``.

    Keyed on journal state, not on a call count: the mid-tick git re-reads
    (``__main__.py:1527-1539``, ``:1600-1619``, ``:1682-1701``) each sit
    behind ``except VcsCommandError, ValueError: pass``, and a count-keyed
    double would pin how many reads the loop performs instead of the
    survival those arms exist for.
    """

    def __init__(
        self,
        *,
        fs: FakeFs,
        run_dir: Path,
        marker: str,
        refusals: int | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self._fs = fs
        self._run_dir = run_dir
        self._marker = marker
        self._refusals = refusals
        self.refused = 0

    def worktree_head_sha(self, worktree_path: Path) -> str:
        spent = self._refusals is not None and self.refused >= self._refusals
        if not spent and self._marker in self._fs.journal_text(self._run_dir):
            self.refused += 1
            raise VcsCommandError("git rev-parse failed (test double)")
        return super().worktree_head_sha(worktree_path)


def test_supervisor_survives_a_git_read_failure_after_finalize(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    repo_root = _repo(tmp_path)
    run_dir = _run_dir(repo_root)
    worktree = _worktree(repo_root)
    _seed_journal(run_dir, (_launch_line(),))
    (run_dir / "session.log").write_text("implementation done\n", encoding="utf-8")
    _seed_spec(repo_root, worktree, primary=_READY_SPEC_TEXT)
    _patch_verification(monkeypatch, _clean_envelope)
    _patch_landing(monkeypatch)
    branch = dispatch_core.dispatch_worktree_branch(_SLUG, _STORY_KEY)
    fs = FakeFs()
    vcs = _HeadShaFailsOnceJournaledVcs(
        fs=fs,
        run_dir=run_dir,
        marker=dispatch_core.KIND_DISPATCH_FINALIZE,
        branches=frozenset({branch}),
        head_sha=_MOVED,
    )
    publisher = FakePublisher()

    code = _run(repo_root, fs=fs, vcs=vcs, process=FakeProcess(alive=False), publisher=publisher)

    # The re-read raises, the loop keeps the facts it already has, and the
    # tick still terminalizes and publishes -- a git failure between finalize
    # and the verdict is survivable, not a supervisor crash.
    assert code == 0
    assert dispatch_core.KIND_DISPATCH_FINALIZE in fs.journal_text(run_dir)
    assert publisher.completions


def test_supervisor_survives_a_git_read_failure_after_the_live_branch_land(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    """The LIVE-branch land re-reads git to re-derive the verdict; when that
    read refuses, the tick keeps ``LIVE``, heartbeats, and tries again."""
    repo_root = _repo(tmp_path)
    run_dir = _run_dir(repo_root)
    worktree = _worktree(repo_root)
    _seed_journal(
        run_dir,
        (
            _launch_line(),
            *_outcome_pair(
                kind=dispatch_core.KIND_DISPATCH_VERIFICATION,
                payload={"verdict": "verified", "ok": True},
                counter=1,
            ),
        ),
    )
    (run_dir / "session.log").write_text("budget-stop reached; idle-defer\n", encoding="utf-8")
    _seed_spec(repo_root, worktree, primary=_READY_SPEC_TEXT)
    land_calls = _patch_landing(monkeypatch)
    fs = FakeFs()
    vcs = _HeadShaFailsOnceJournaledVcs(
        fs=fs,
        run_dir=run_dir,
        marker=dispatch_core.KIND_DISPATCH_LAND,
        refusals=1,
        head_sha=_MOVED,
    )
    publisher = FakePublisher()

    code = _run(repo_root, fs=fs, vcs=vcs, process=FakeProcess(alive=False), publisher=publisher)

    assert code == 0
    assert vcs.refused == 1
    # The land still happened exactly once: the refused re-read costs the tick
    # its verdict, not the landing, and the next tick reads the journal that
    # already holds it.
    assert len(land_calls) == 1
    assert publisher.completions[0][1] == DispatchSessionVerdict.COMPLETED.value


def test_supervisor_completes_when_another_writer_lands_during_finalize(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    repo_root = _repo(tmp_path)
    run_dir = _run_dir(repo_root)
    worktree = _worktree(repo_root)
    _seed_journal(run_dir, (_launch_line(),))
    (run_dir / "session.log").write_text("implementation done\n", encoding="utf-8")
    _seed_spec(repo_root, worktree, primary=_READY_SPEC_TEXT)
    _patch_verification(monkeypatch, _clean_envelope)
    land_calls = _patch_landing(monkeypatch)
    branch = dispatch_core.dispatch_worktree_branch(_SLUG, _STORY_KEY)
    vcs = FakeVcs(branches=frozenset({branch}), head_sha=_MOVED)
    fs = _LandsDuringFinalizeFs()
    publisher = FakePublisher()

    code = _run(repo_root, fs=fs, vcs=vcs, process=FakeProcess(alive=False), publisher=publisher)

    assert code == 0
    assert fs.injected
    # This supervisor never landed: the concurrent outcome is what the
    # post-finalize re-fold reads, so COMPLETED comes from the landing the
    # other writer journaled, not from a second land attempt on top of it.
    assert land_calls == []
    assert publisher.completions[0][1] == DispatchSessionVerdict.COMPLETED.value


def test_supervisor_lands_from_the_live_branch_then_completes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    """A marshal-initiated stop keeps the verdict ``LIVE`` while verification
    already read ``verified`` -- the tick loop's own land trigger (not the
    finalize sequence) is what must fire."""
    repo_root = _repo(tmp_path)
    run_dir = _run_dir(repo_root)
    worktree = _worktree(repo_root)
    _seed_journal(
        run_dir,
        (
            _launch_line(),
            *_outcome_pair(
                kind=dispatch_core.KIND_DISPATCH_VERIFICATION,
                payload={"verdict": "verified", "ok": True},
                counter=1,
            ),
        ),
    )
    (run_dir / "session.log").write_text("budget-stop reached; idle-defer\n", encoding="utf-8")
    _seed_spec(repo_root, worktree, primary=_READY_SPEC_TEXT)
    land_calls = _patch_landing(monkeypatch)
    fs = FakeFs()
    publisher = FakePublisher()

    code = _run(
        repo_root,
        fs=fs,
        vcs=FakeVcs(head_sha=_MOVED),
        process=FakeProcess(alive=False),
        publisher=publisher,
    )

    assert code == 0
    assert len(land_calls) == 1
    assert publisher.heartbeats == ["handle-1"]
    assert publisher.completions and publisher.completions[0][1] == DispatchSessionVerdict.COMPLETED.value


def test_supervisor_heartbeats_a_marshal_initiated_stop_with_no_verification_yet(
    tmp_path: Path, clock: _FakeClock
) -> None:
    repo_root = _repo(tmp_path)
    run_dir = _run_dir(repo_root)
    _seed_journal(
        run_dir,
        (
            _launch_line(),
            *_outcome_pair(
                kind=dispatch_core.KIND_DISPATCH_FINALIZE,
                payload={"story_key": _STORY_KEY, "trigger": "harness-done", "ok": True},
                counter=1,
            ),
        ),
    )
    (run_dir / "session.log").write_text("escalation-paused\n", encoding="utf-8")
    publisher = FakePublisher()

    code = _run(
        repo_root,
        fs=FakeFs(),
        vcs=FakeVcs(head_shas=(_MOVED, _MOVED, _BASELINE), head_sha=_BASELINE, changed=()),
        process=FakeProcess(alive=False),
        publisher=publisher,
    )

    assert code == 0
    assert publisher.heartbeats and set(publisher.heartbeats) == {"handle-1"}


def test_supervisor_commits_and_promotes_a_blocked_halt(tmp_path: Path, clock: _FakeClock) -> None:
    repo_root = _repo(tmp_path)
    run_dir = _run_dir(repo_root)
    worktree = _worktree(repo_root)
    _seed_journal(
        run_dir,
        (
            _launch_line(),
            *_outcome_pair(
                kind=dispatch_core.KIND_DISPATCH_FINALIZE,
                payload={"story_key": _STORY_KEY, "trigger": "harness-done", "ok": True},
                counter=1,
            ),
        ),
    )
    _seed_spec(
        repo_root,
        worktree,
        primary=_READY_SPEC_TEXT,
        worktree_text=_BLOCKED_SPEC_TEMPLATE.format(baseline=_BASELINE),
    )
    vcs = FakeVcs(head_sha=_MOVED)
    fs = FakeFs()
    publisher = FakePublisher()

    code = _run(repo_root, fs=fs, vcs=vcs, process=FakeProcess(alive=False), publisher=publisher)

    assert code == 0
    assert dispatch_core.KIND_DISPATCH_BLOCKED in fs.journal_text(run_dir)
    assert vcs.remote_tip_writes, "the primary's tracked twin must be promoted to blocked"
    assert vcs.remote_tip_reasons == [f"marshal blocked-twin promotion for story {_STORY_KEY}"]
    assert "dispatch-blocked-twin-publish" not in fs.journal_text(run_dir)
    assert publisher.completions and publisher.completions[0][1] == DispatchSessionVerdict.BLOCKED.value


def test_supervisor_journals_a_warn_when_the_blocked_twin_cannot_be_published(
    tmp_path: Path, clock: _FakeClock
) -> None:
    repo_root = _repo(tmp_path)
    run_dir = _run_dir(repo_root)
    worktree = _worktree(repo_root)
    _seed_journal(
        run_dir,
        (
            _launch_line(),
            *_outcome_pair(
                kind=dispatch_core.KIND_DISPATCH_FINALIZE,
                payload={"story_key": _STORY_KEY, "trigger": "harness-done", "ok": True},
                counter=1,
            ),
        ),
    )
    _seed_spec(
        repo_root,
        worktree,
        primary=_READY_SPEC_TEXT,
        worktree_text=_BLOCKED_SPEC_TEMPLATE.format(baseline=_BASELINE),
    )
    vcs = FakeVcs(head_sha=_MOVED, remote_tip_raises=True)
    fs = FakeFs()
    publisher = FakePublisher()

    code = _run(repo_root, fs=fs, vcs=vcs, process=FakeProcess(alive=False), publisher=publisher)

    assert code == 0
    assert dispatch_core.KIND_DISPATCH_BLOCKED in fs.journal_text(run_dir)
    # Story 68.1 (CAP-277): the failed twin publish is never silent -- a WARN observation names the
    # story and the error, and the blocked verdict is unaffected.
    journal = fs.journal_text(run_dir)
    assert "dispatch-blocked-twin-publish" in journal
    assert "MRS-LAND-011" in journal
    assert _STORY_KEY in journal
    assert "git commit-tree failed (test double)" in journal
    assert vcs.remote_tip_writes == []
    assert publisher.completions and publisher.completions[0][1] == DispatchSessionVerdict.BLOCKED.value
    # The twin WARN consumed a journal counter: the call site must carry the advanced counter on, or
    # the next supervisor entry reuses the WARN's (writer_id, counter) id -- a duplicate id in an
    # append-only journal.
    entries = [json.loads(line) for line in journal.splitlines() if line]
    ids = [(e["id"]["writer_id"], e["id"]["counter"]) for e in entries]
    assert len(ids) == len(set(ids)), f"duplicate journal entry ids: {ids}"
    [twin] = [e for e in entries if e["kind"] == "dispatch-blocked-twin-publish"]
    [completion_intent] = [
        e for e in entries if e["kind"] == dispatch_core.KIND_DISPATCH_COMPLETION and e["phase"] == Phase.INTENT.value
    ]
    assert twin["id"]["writer_id"] == completion_intent["id"]["writer_id"]
    assert twin["id"]["counter"] < completion_intent["id"]["counter"]


def test_supervisor_records_a_stale_blocked_spec_as_an_advisory_only(tmp_path: Path, clock: _FakeClock) -> None:
    repo_root = _repo(tmp_path)
    run_dir = _run_dir(repo_root)
    worktree = _worktree(repo_root)
    _seed_journal(
        run_dir,
        (
            _launch_line(),
            *_outcome_pair(
                kind=dispatch_core.KIND_DISPATCH_FINALIZE,
                payload={"story_key": _STORY_KEY, "trigger": "harness-done", "ok": True},
                counter=1,
            ),
        ),
    )
    _seed_spec(repo_root, worktree, primary=_BLOCKED_SPEC_TEMPLATE.format(baseline="0" * 40))
    fs = FakeFs()
    publisher = FakePublisher()

    code = _run(repo_root, fs=fs, vcs=FakeVcs(head_sha=_MOVED), process=FakeProcess(alive=False), publisher=publisher)

    assert code == 0
    journal = fs.journal_text(run_dir)
    assert "MRS-DISP-046" in journal
    assert publisher.completions[0][1] == DispatchSessionVerdict.STOPPED_EXTERNALLY.value


def test_supervisor_fails_when_the_completion_entry_cannot_be_journaled(
    tmp_path: Path, clock: _FakeClock, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_root = _repo(tmp_path)
    _seed_journal(_run_dir(repo_root), (_launch_line(),))
    fs = FakeFs(fail_append_after=1)

    code = _run(
        repo_root,
        fs=fs,
        vcs=FakeVcs(head_sha=_BASELINE, changed=()),
        process=FakeProcess(alive=False),
        publisher=FakePublisher(),
    )

    assert code == 1
    assert "cannot journal completion" in capsys.readouterr().err


def test_supervisor_preserves_the_worktree_patch_on_a_failed_run(tmp_path: Path, clock: _FakeClock) -> None:
    repo_root = _repo(tmp_path)
    run_dir = _run_dir(repo_root)
    worktree = _worktree(repo_root)
    _seed_journal(
        run_dir,
        (
            _launch_line(),
            *_outcome_pair(
                kind=dispatch_core.KIND_DISPATCH_VERIFICATION,
                payload={"verdict": "refused", "ok": False},
                counter=1,
            ),
        ),
    )
    _seed_spec(repo_root, worktree, primary=_READY_SPEC_TEXT)
    fs = FakeFs()

    code = _run(
        repo_root,
        fs=fs,
        vcs=FakeVcs(head_sha=_MOVED, patch="diff --git a/x b/x\n+work\n"),
        process=FakeProcess(alive=False),
        publisher=FakePublisher(),
    )

    assert code == 0
    assert any(path.suffix == ".patch" for path in fs.files)
    assert dispatch_core.KIND_DISPATCH_PRESERVE in fs.journal_text(run_dir)


def test_supervisor_skips_publishing_when_no_handle_was_issued(tmp_path: Path, clock: _FakeClock) -> None:
    repo_root = _repo(tmp_path)
    _seed_journal(_run_dir(repo_root), (_launch_line(),))
    publisher = FakePublisher(handle=None)

    code = _run(
        repo_root,
        fs=FakeFs(),
        vcs=FakeVcs(head_sha=_BASELINE, changed=()),
        process=FakeProcess(alive=False),
        publisher=publisher,
    )

    assert code == 0
    assert publisher.completions == []


def test_supervisor_survives_an_initial_fetch_failure(tmp_path: Path, clock: _FakeClock) -> None:
    repo_root = _repo(tmp_path)
    _seed_journal(_run_dir(repo_root), (_launch_line(),))
    publisher = FakePublisher()

    code = _run(
        repo_root,
        fs=FakeFs(),
        vcs=FakeVcs(head_sha=_BASELINE, changed=(), fetch_raises=True),
        process=FakeProcess(alive=False),
        publisher=publisher,
    )

    # Exit 0 alone would also hold for a supervisor that gave up before
    # judging anything; the completion is what proves the swallowed fetch
    # failure cost the run nothing -- same verdict as the fetching twin,
    # `test_supervisor_journals_a_failed_run_to_completion`.
    assert code == 0
    assert publisher.completions and publisher.completions[0][1] == DispatchSessionVerdict.FAILED.value


def test_supervisor_exits_completed_once_the_story_is_merged_on_main(tmp_path: Path, clock: _FakeClock) -> None:
    repo_root = _repo(tmp_path)
    _seed_journal(_run_dir(repo_root), (_launch_line(),))
    _ledger_path(repo_root).write_text("development_status:\n  51-11-a-real-story: done\n", encoding="utf-8")
    publisher = FakePublisher()

    code = _run(
        repo_root,
        fs=FakeFs(),
        vcs=FakeVcs(head_sha=_MOVED, subjects=("Merge pyforge-marshal/51-11 into main",)),
        process=FakeProcess(alive=False),
        publisher=publisher,
    )

    assert code == 0
    assert publisher.completions[0][1] == DispatchSessionVerdict.COMPLETED.value


# -- Story 72.1 (CAP-280): the tick loop judges a merge from `origin/main` ---------------------------


def _seed_verified_run(repo_root: Path) -> tuple[Path, Path]:
    """A run whose session ended and whose verification journaled ``verified``: the land trigger's
    precondition. Returns ``(run_dir, worktree)``."""
    run_dir = _run_dir(repo_root)
    worktree = _worktree(repo_root)
    _seed_journal(
        run_dir,
        (
            _launch_line(),
            *_outcome_pair(
                kind=dispatch_core.KIND_DISPATCH_VERIFICATION,
                payload={"verdict": "verified", "ok": True},
                counter=1,
            ),
        ),
    )
    (run_dir / "session.log").write_text("implementation done\n", encoding="utf-8")
    _seed_spec(repo_root, worktree, primary=_READY_SPEC_TEXT)
    return run_dir, worktree


def _spy(monkeypatch: pytest.MonkeyPatch, name: str) -> list[tuple[dict, object]]:
    """Record every ``(kwargs, result)`` of ``supervisor_main.<name>``, calling through."""
    real = getattr(supervisor_main, name)
    calls: list[tuple[dict, object]] = []

    def _wrapper(**kwargs):
        result = real(**kwargs)
        calls.append((kwargs, result))
        return result

    monkeypatch.setattr(supervisor_main, name, _wrapper)
    return calls


def _record_land_or_block(monkeypatch: pytest.MonkeyPatch) -> list[object]:
    """Record every call of ``supervisor_main._land_or_journal_block`` (positional or keyword), calling through."""
    real = supervisor_main._land_or_journal_block
    calls: list[object] = []

    def _wrapper(*args, **kwargs):
        calls.append((args, kwargs))
        return real(*args, **kwargs)

    monkeypatch.setattr(supervisor_main, "_land_or_journal_block", _wrapper)
    return calls


def _log_landings_into(monkeypatch: pytest.MonkeyPatch, vcs: FakeVcs) -> None:
    """Put each land attempt into ``vcs.calls``, so a test can order it against the merge reads."""
    inner = supervisor_main.execute_dispatch_land

    def _logged(**kwargs):
        vcs.calls.append(("land",))
        return inner(**kwargs)

    monkeypatch.setattr(supervisor_main, "execute_dispatch_land", _logged)


def test_supervisor_does_not_land_a_story_merged_on_origin_main_while_local_main_lags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    repo_root = _repo(tmp_path)
    _seed_verified_run(repo_root)
    land_calls = _patch_landing(monkeypatch)
    blocks = _record_land_or_block(monkeypatch)
    retries = _spy(monkeypatch, "should_retry_stuck_land")
    exits = _spy(monkeypatch, "supervisor_should_exit")
    publisher = FakePublisher()

    code = _run(
        repo_root,
        fs=FakeFs(),
        vcs=_merge_vcs(on_origin=True, on_local=False),
        process=FakeProcess(alive=False),
        publisher=publisher,
    )

    assert code == 0
    assert land_calls == []
    assert blocks == []  # AC: `_land_or_journal_block` is never called (review 1: asserted directly)
    # The stuck-land retry reads the story as merged and never counts a tick.
    assert retries and all(kwargs["story_merged_on_main"] is True for kwargs, _ in retries)
    assert all(kwargs["stuck_land_ticks"] == 0 for kwargs, _ in retries)
    # The exit decision sees the merge.
    assert exits
    exit_kwargs, exit_result = exits[-1]
    assert exit_kwargs["story_merged_on_main"] is True
    assert exit_result is True
    assert publisher.completions[0][1] == DispatchSessionVerdict.COMPLETED.value


def test_supervisor_lands_a_verified_story_that_only_local_main_shows_merged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    """The reverse fixture: a merge local `main` carries and `origin/main` lacks is no merge, so the
    land trigger fires -- the twin of the lagging-local-`main` test, and its mutation proof."""
    repo_root = _repo(tmp_path)
    _seed_verified_run(repo_root)
    land_calls = _patch_landing(monkeypatch)
    blocks = _record_land_or_block(monkeypatch)

    code = _run(
        repo_root,
        fs=FakeFs(),
        vcs=_merge_vcs(on_origin=False, on_local=True),
        process=FakeProcess(alive=False),
        publisher=FakePublisher(),
    )

    assert code == 0
    assert len(land_calls) == 1
    assert blocks  # the same recorder sees the land-or-block step here, so its silence above is meaningful


def _seed_live_branch_land_run(repo_root: Path) -> None:
    """The first land site: verification ``verified`` while a marshal-initiated stop keeps the run ``LIVE``."""
    run_dir, _worktree_path = _seed_verified_run(repo_root)
    (run_dir / "session.log").write_text("budget-stop reached; idle-defer\n", encoding="utf-8")


def _seed_terminal_branch_land_run(repo_root: Path) -> None:
    """The second land site: the session ended unverified, so finalize verifies, then the terminal branch lands."""
    run_dir = _run_dir(repo_root)
    worktree = _worktree(repo_root)
    _seed_journal(run_dir, (_launch_line(),))
    (run_dir / "session.log").write_text("implementation done\n", encoding="utf-8")
    _seed_spec(repo_root, worktree, primary=_READY_SPEC_TEXT)


@pytest.mark.parametrize(
    "seed",
    [_seed_live_branch_land_run, _seed_terminal_branch_land_run],
    ids=["live-branch-land-site", "terminal-branch-land-site"],
)
def test_supervisor_fetches_origin_main_between_its_own_land_and_the_regather(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _FakeClock, seed
) -> None:
    repo_root = _repo(tmp_path)
    seed(repo_root)
    _patch_verification(monkeypatch, _clean_envelope)
    land_calls = _patch_landing(monkeypatch)
    vcs = FakeVcs(head_sha=_MOVED)
    _log_landings_into(monkeypatch, vcs)

    code = _run(repo_root, fs=FakeFs(), vcs=vcs, process=FakeProcess(alive=False), publisher=FakePublisher())

    assert code == 0
    assert len(land_calls) == 1
    after_land = vcs.calls[vcs.calls.index(("land",)) + 1 :]
    first_read = next(index for index, call in enumerate(after_land) if call[0] == "commit_subjects")
    assert ("fetch", "origin", "main") in after_land[:first_read]
    assert after_land[first_read] == ("commit_subjects", ORIGIN_MAIN)


def test_supervisor_tolerates_a_failed_fetch_after_its_own_land(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    repo_root = _repo(tmp_path)
    _seed_terminal_branch_land_run(repo_root)
    _patch_verification(monkeypatch, _clean_envelope)
    land_calls = _patch_landing(monkeypatch)
    publisher = FakePublisher()

    code = _run(
        repo_root,
        fs=FakeFs(),
        vcs=FakeVcs(head_sha=_MOVED, fetch_raises=True),
        process=FakeProcess(alive=False),
        publisher=publisher,
    )

    assert code == 0
    assert len(land_calls) == 1
    assert publisher.completions[0][1] == DispatchSessionVerdict.COMPLETED.value


def test_supervisor_continues_without_landing_or_exiting_while_origin_main_is_unreadable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _FakeClock, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_root = _repo(tmp_path)
    _seed_verified_run(repo_root)
    land_calls = _patch_landing(monkeypatch)
    publisher = FakePublisher()
    # `origin/main` is unreadable on the first tick and carries the merge on the second; local `main`
    # never does -- an unreadable `origin/main` is neither merged nor a reason to read local `main`.
    vcs = _merge_vcs(on_origin=True, on_local=False, unreadable_refs={ORIGIN_MAIN: 1})

    code = _run(repo_root, fs=FakeFs(), vcs=vcs, process=FakeProcess(alive=False), publisher=publisher)

    assert code == 0
    assert "git fact gather failed" in capsys.readouterr().err
    # One skipped tick (the loop slept once and carried on), nothing landed, and the run completed only
    # once `origin/main` read again.
    assert clock.sleeps == [supervisor_main._TICK_SECONDS]
    assert land_calls == []
    assert len(publisher.completions) == 1
    assert publisher.completions[0][1] == DispatchSessionVerdict.COMPLETED.value


# ==========================================================================
# main()
# ==========================================================================


def test_main_threads_every_supervisor_positional_and_ignores_the_log_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict = {}

    def _fake_run(**kwargs) -> int:
        captured.update(kwargs)
        return 0

    monkeypatch.setattr(supervisor_main, "run_dispatch_supervisor", _fake_run)
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)

    code = supervisor_main.main(
        [
            str(repo_root),
            _SLUG,
            _RUN_ID,
            str(_SESSION_PID),
            str(worktree),
            _STORY_KEY,
            _BASELINE,
            _TEMPLATE,
            str(tmp_path / "supervisor.log"),
        ]
    )

    assert code == 0
    # The whole forwarded set, by name: a test that checks four of the eight
    # passes over a dropped one, which is the failure it exists to catch.
    assert captured == {
        "repo_root": repo_root,
        "slug": _SLUG,
        "run_id": _RUN_ID,
        "session_pid": _SESSION_PID,
        "worktree": worktree,
        "story_key": _STORY_KEY,
        "baseline_head_sha": _BASELINE,
        "merge_subject_template": _TEMPLATE,
    }
    # The ninth positional is deliberately absent from that set:
    # `run_dispatch_supervisor` takes no `log_path`. `cli/dispatch.py`'s
    # `_spawn_dispatch_supervisor` sends the supervisor log twice -- on argv, and
    # as `spawn_detached(log_path=...)`, which is what actually redirects the
    # child's output -- so argparse must accept the positional while the
    # supervisor itself has nothing to do with it. Forwarding it would be a
    # production change with no behaviour behind it.
    assert "log_path" not in captured


def test_main_refuses_a_missing_positional(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(supervisor_main, "run_dispatch_supervisor", lambda **_kwargs: 0)

    with pytest.raises(SystemExit) as excinfo:
        supervisor_main.main(["only-one-argument"])

    # A bare `raises(SystemExit)` would also pass on a clean `SystemExit(0)`,
    # i.e. on a `main()` that quietly ran the supervisor with defaults. The
    # refusal this pins is argparse's usage error.
    assert excinfo.value.code == 2


# ==========================================================================
# The landing's check wait keeps the run alive (Story 80.1, CAP-284)
# ==========================================================================
#
# The portal marks a published run FAILED `heartbeat_lost` once its heartbeat is older than the
# station time limit (300 s by default). The landing can now wait 45 minutes for CI, and the tick
# loop writes its heartbeat only after the landing returns -- so the wait ticks the heartbeat itself.


def _heartbeat_entries(fs: FakeFs) -> list[dict]:
    return [
        entry
        for entry in (json.loads(line) for line in fs.journal_text(_run_dir_of(fs)).splitlines() if line)
        if entry.get("payload", {}).get("heartbeat") is True
    ]


def _run_dir_of(fs: FakeFs) -> Path:
    return next(path.parent for path in fs.files if path.name == "journal.jsonl")


def test_supervisor_heartbeats_the_run_through_the_landing_wait(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    """Each tick of the landing's wait writes the loop's own heartbeat observation AND calls the run
    publisher's heartbeat -- two ticks here, plus the loop's one after the landing returns."""
    repo_root = _repo(tmp_path)
    run_dir = _run_dir(repo_root)
    worktree = _worktree(repo_root)
    _seed_journal(
        run_dir,
        (
            _launch_line(),
            *_outcome_pair(
                kind=dispatch_core.KIND_DISPATCH_VERIFICATION,
                payload={"verdict": "verified", "ok": True},
                counter=1,
            ),
        ),
    )
    (run_dir / "session.log").write_text("budget-stop reached; idle-defer\n", encoding="utf-8")
    _seed_spec(repo_root, worktree, primary=_READY_SPEC_TEXT)
    land_calls = _patch_landing(monkeypatch, wait_ticks=2)
    fs = FakeFs()
    publisher = FakePublisher()

    code = _run(
        repo_root,
        fs=fs,
        vcs=FakeVcs(head_sha=_MOVED),
        process=FakeProcess(alive=False),
        publisher=publisher,
    )

    assert code == 0
    assert len(land_calls) == 1
    assert publisher.heartbeats == ["handle-1"] * 3
    beats = _heartbeat_entries(fs)
    assert len(beats) == 3
    assert all(beat["payload"]["current_head_sha"] == _MOVED for beat in beats)
    ids = [json.dumps(json.loads(line)["id"], sort_keys=True) for line in fs.journal_text(run_dir).splitlines() if line]
    assert len(ids) == len(set(ids))  # the ticks and the landing's own entries never reuse a journal id


def test_supervisor_heartbeats_the_run_through_the_landing_wait_on_the_terminal_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    """The tick loop's SECOND landing call site (a finished harness session: finalize verifies, the
    verdict is terminal, then it lands) hands the landing the same wait heartbeat -- two wait ticks
    write two heartbeat observations and call the publisher heartbeat twice. No loop heartbeat
    follows: the verdict is terminal, so the run completes instead."""
    repo_root = _repo(tmp_path)
    run_dir = _run_dir(repo_root)
    worktree = _worktree(repo_root)
    _seed_journal(run_dir, (_launch_line(),))
    (run_dir / "session.log").write_text("implementation done\n", encoding="utf-8")
    _seed_spec(repo_root, worktree, primary=_READY_SPEC_TEXT)
    _patch_verification(monkeypatch, _clean_envelope)
    land_calls = _patch_landing(monkeypatch, wait_ticks=2)
    branch = dispatch_core.dispatch_worktree_branch(_SLUG, _STORY_KEY)
    vcs = FakeVcs(branches=frozenset({branch}), head_sha=_MOVED)
    fs = FakeFs()
    publisher = FakePublisher()

    code = _run(repo_root, fs=fs, vcs=vcs, process=FakeProcess(alive=False), publisher=publisher)

    assert code == 0
    assert len(land_calls) == 1
    assert publisher.heartbeats == ["handle-1"] * 2
    beats = _heartbeat_entries(fs)
    assert len(beats) == 2
    assert all(beat["payload"]["session_alive"] is False for beat in beats)
    assert all(beat["payload"]["current_head_sha"] == _MOVED for beat in beats)
    assert '"verdict": "landed"' in fs.journal_text(run_dir)
    assert publisher.completions


def test_supervisor_without_a_publish_handle_still_journals_the_wait_heartbeat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    repo_root = _repo(tmp_path)
    run_dir = _run_dir(repo_root)
    worktree = _worktree(repo_root)
    _seed_journal(
        run_dir,
        (
            _launch_line(),
            *_outcome_pair(
                kind=dispatch_core.KIND_DISPATCH_VERIFICATION,
                payload={"verdict": "verified", "ok": True},
                counter=1,
            ),
        ),
    )
    (run_dir / "session.log").write_text("budget-stop reached; idle-defer\n", encoding="utf-8")
    _seed_spec(repo_root, worktree, primary=_READY_SPEC_TEXT)
    _patch_landing(monkeypatch, wait_ticks=2)
    fs = FakeFs()
    publisher = FakePublisher(handle=None)

    code = _run(repo_root, fs=fs, vcs=FakeVcs(head_sha=_MOVED), process=FakeProcess(alive=False), publisher=publisher)

    assert code == 0
    assert publisher.heartbeats == []
    assert len(_heartbeat_entries(fs)) == 3


def test_journal_heartbeat_returns_the_next_counter_and_survives_a_journal_failure(tmp_path: Path) -> None:
    """A heartbeat is liveness evidence, never a reason to stop: a refused journal write is swallowed
    and the counter still advances (the next entry must not reuse the id)."""
    run_dir = _run_dir(_repo(tmp_path))
    kwargs = dict(
        run_dir=run_dir,
        run_id=_RUN_ID,
        writer_id="dispatch-supervisor-1",
        counter=7,
        session_alive=True,
        git_facts=_git_facts(),
    )
    ok_fs = FakeFs()
    assert supervisor_main._journal_heartbeat(fs=ok_fs, **kwargs) == 8
    assert len(ok_fs.appended) == 1
    failing_fs = FakeFs(append_fails_for=frozenset({"journal.jsonl"}))
    assert supervisor_main._journal_heartbeat(fs=failing_fs, **kwargs) == 8
    assert failing_fs.appended == []


# ==========================================================================
# Story 73.1 (CAP-281): a follow-up review run is judged by its own branch
# ==========================================================================

_FOLLOWUP_DW_ID = "DW-FRR-51-11"
#: ``origin/main``'s tip the run's launch INTENT recorded -- the story's first merge is at or before it.
_LAUNCH_TIP = "1a2b3c4d5e6f708192a3b4c5d6e7f8091a2b3c4d"
_TIP_RANGE = f"{_LAUNCH_TIP}..{ORIGIN_MAIN}"
_BASELINE_RANGE = f"{_BASELINE}..{ORIGIN_MAIN}"
_FOLLOWUP = FollowupReview(dw_id=_FOLLOWUP_DW_ID, launch_origin_main_sha=_LAUNCH_TIP)
_DONE_SPEC_TEXT = "---\nstatus: done\nfollowup_review_recommended: false\n---\n\n## Intent\n\nReviewed.\n"


def _followup_launch_line(
    dw_id: str | None = _FOLLOWUP_DW_ID, *, run_id: str = _RUN_ID, tip: str | None = _LAUNCH_TIP
) -> str:
    """The launch INTENT ``dispatch_once`` journals for a follow-up review run (the marker beside the usual facts)."""
    return _line(
        kind=dispatch_core.KIND_DISPATCH_LAUNCH,
        phase=Phase.INTENT,
        payload={
            "story_key": _STORY_KEY,
            **FollowupReview(dw_id=dw_id, launch_origin_main_sha=tip).to_intent_payload(),
        },
        counter=0,
        run_id=run_id,
    )


def _first_landing_vcs(*, own_merge: bool = False, **kwargs: object) -> FakeVcs:
    """The reused pre-merge worktree (attempt 1's G1): ``origin/main`` carries the story's FIRST merge, and so
    does ``<baseline>..origin/main``, because the surviving worktree's baseline predates that merge. Only
    ``<launch tip>..origin/main`` is free of it -- and holds the run's own merge when ``own_merge``. The run's
    branch is never reported merged by ancestry."""
    branch = dispatch_core.dispatch_worktree_branch(_SLUG, _STORY_KEY)
    return FakeVcs(
        branches=frozenset({branch}),
        subjects_by_ref={
            ORIGIN_MAIN: (_PR_MERGE_SUBJECT,),
            _BASELINE_RANGE: (_PR_MERGE_SUBJECT,),
            _TIP_RANGE: (_PR_MERGE_SUBJECT,) if own_merge else (),
        },
        merged_into_refs=frozenset(),
        spec_at_ref=_SPEC_DONE,
        **kwargs,  # type: ignore[arg-type]
    )


def _gather_facts_spy(monkeypatch: pytest.MonkeyPatch) -> list[DispatchGitFacts]:
    """Every ``DispatchGitFacts`` ``gather_dispatch_git_facts`` returns during a run, calling through."""
    real = supervisor_main.gather_dispatch_git_facts
    facts: list[DispatchGitFacts] = []

    def _wrapper(*args, **kwargs):
        result = real(*args, **kwargs)
        facts.append(result)
        return result

    monkeypatch.setattr(supervisor_main, "gather_dispatch_git_facts", _wrapper)
    return facts


# -- the marker, read back off the launch INTENT --------------------------------------------------


def _folded(tmp_path: Path, lines: tuple[str, ...]):
    run_dir = _run_dir(_repo(tmp_path))
    path = _seed_journal(run_dir, lines)
    return supervisor_main._fold_dispatch_journal(FakeFs(), run_dir, path.read_text(encoding="utf-8"))


def test_followup_review_is_read_off_the_launch_intent(tmp_path: Path) -> None:
    folded = _folded(tmp_path, (_followup_launch_line(),))

    assert supervisor_main._followup_review_from_launch(folded, _RUN_ID) == _FOLLOWUP


def test_followup_review_carries_the_launch_tip_the_intent_recorded(tmp_path: Path) -> None:
    folded = _folded(tmp_path, (_followup_launch_line(tip="f" * 40),))

    marker = supervisor_main._followup_review_from_launch(folded, _RUN_ID)

    assert marker is not None
    assert marker.launch_origin_main_sha == "f" * 40


def test_followup_review_without_a_row_is_still_a_marker(tmp_path: Path) -> None:
    folded = _folded(tmp_path, (_followup_launch_line(None),))

    assert supervisor_main._followup_review_from_launch(folded, _RUN_ID) == FollowupReview(
        dw_id=None, launch_origin_main_sha=_LAUNCH_TIP
    )


def test_a_launch_without_the_marker_is_a_normal_run(tmp_path: Path) -> None:
    folded = _folded(tmp_path, (_launch_line(),))

    assert supervisor_main._followup_review_from_launch(folded, _RUN_ID) is None


def test_another_runs_marker_is_not_this_runs(tmp_path: Path) -> None:
    folded = _folded(tmp_path, (_followup_launch_line(run_id="another-run"), _launch_line()))

    assert supervisor_main._followup_review_from_launch(folded, _RUN_ID) is None


# -- gather_dispatch_git_facts: the launch-tip scope -------------------------------------------------


def _gather_followup(
    repo_root: Path, worktree: Path, vcs: FakeVcs, *, followup_review: FollowupReview | None
) -> DispatchGitFacts:
    return supervisor_main.gather_dispatch_git_facts(
        vcs,
        fs=FakeFs(),
        repo_root=repo_root,
        worktree=worktree,
        story_key=_STORY_KEY,
        project_slug=_SLUG,
        baseline_head_sha=_BASELINE,
        merge_subject_template=_TEMPLATE,
        followup_review=followup_review,
    )


def _commit_subject_reads(vcs: FakeVcs) -> list[tuple[str, ...]]:
    return [call for call in vcs.calls if call[0] == "commit_subjects"]


def test_gather_git_facts_for_a_follow_up_ignores_the_stories_first_merge(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    _seed_spec(repo_root, worktree, primary=_DONE_SPEC_TEXT)
    vcs = _first_landing_vcs(head_sha=_MOVED)

    facts = _gather_followup(repo_root, worktree, vcs, followup_review=_FOLLOWUP)

    assert facts.story_merged_on_main is False
    # Scoped to the launch tip: neither the whole ref nor the (stale) baseline range is ever asked for.
    assert _commit_subject_reads(vcs) == [("commit_subjects", _TIP_RANGE)]


def test_gather_git_facts_for_a_follow_up_counts_its_own_merge(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    _seed_spec(repo_root, worktree, primary=_DONE_SPEC_TEXT)

    facts = _gather_followup(
        repo_root, worktree, _first_landing_vcs(own_merge=True, head_sha=_MOVED), followup_review=_FOLLOWUP
    )

    assert facts.story_merged_on_main is True


def test_gather_git_facts_for_a_follow_up_with_no_recorded_tip_counts_no_merge(tmp_path: Path) -> None:
    """An INTENT that recorded no tip cannot scope the read, so nothing is countable (never the whole ref)."""
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    _seed_spec(repo_root, worktree, primary=_DONE_SPEC_TEXT)
    vcs = _first_landing_vcs(head_sha=_MOVED)

    facts = _gather_followup(repo_root, worktree, vcs, followup_review=FollowupReview(dw_id=_FOLLOWUP_DW_ID))

    assert facts.story_merged_on_main is False
    assert _commit_subject_reads(vcs) == []


def test_gather_git_facts_for_a_normal_run_reads_origin_main_whole(tmp_path: Path) -> None:
    """The same repository, no marker: the story's first merge is the evidence, and no range is asked for."""
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    _seed_spec(repo_root, worktree, primary=_DONE_SPEC_TEXT)
    vcs = _first_landing_vcs(head_sha=_MOVED)

    facts = _gather_followup(repo_root, worktree, vcs, followup_review=None)

    assert facts.story_merged_on_main is True
    assert _commit_subject_reads(vcs) == [("commit_subjects", ORIGIN_MAIN)]


def test_gather_git_facts_defaults_to_a_normal_run(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    _seed_spec(repo_root, worktree, primary=_DONE_SPEC_TEXT)
    vcs = _first_landing_vcs(head_sha=_MOVED)

    assert _gather(repo_root, worktree, vcs).story_merged_on_main is True
    assert _commit_subject_reads(vcs) == [("commit_subjects", ORIGIN_MAIN)]


# -- gather_dispatch_git_facts against real git: attempt 1's G1 reproduction ---------------------------


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def test_a_follow_up_in_the_stories_surviving_pre_merge_worktree_is_scoped_by_the_launch_tip_against_real_git(
    tmp_path: Path,
) -> None:
    """The story landed once, its dispatch worktree survived at the PRE-merge tip, and a follow-up review run
    was launched into it. Its ``baseline_head_sha`` is not a descendant of the first merge, so a baseline scope
    would count that merge and read the run COMPLETED on its first tick. The launch tip does not."""
    remote, clone = tmp_path / "remote.git", tmp_path / "clone"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True)
    subprocess.run(["git", "clone", "-q", str(remote), str(clone)], check=True, capture_output=True)
    _git(clone, "config", "user.email", "t@example.com")
    _git(clone, "config", "user.name", "T")
    (clone / "README.md").write_text("base\n", encoding="utf-8")
    _git(clone, "add", "-A")
    _git(clone, "commit", "-qm", "base")
    _git(clone, "push", "-q", "origin", "main")
    # The templated merge subject corroborates through the station's own ledger (Story 35.1).
    ledger = clone / "_bmad-output" / "projects" / _SLUG / "planning-artifacts" / "sprint-status-ledger.yaml"
    ledger.parent.mkdir(parents=True)
    ledger.write_text("development_status:\n  51-11-halt: done\n", encoding="utf-8")

    branch = dispatch_core.dispatch_worktree_branch(_SLUG, _STORY_KEY)
    worktree = dispatch_core.dispatch_worktree_path(clone, _SLUG, _STORY_KEY)
    worktree.parent.mkdir(parents=True, exist_ok=True)
    _git(clone, "worktree", "add", "-q", "-b", branch, str(worktree), "main")
    pre_merge_baseline = _git(worktree, "rev-parse", "HEAD")

    # The story's FIRST landing reaches origin/main; the surviving worktree stays behind it.
    first_merge = _TEMPLATE.format(slug=_SLUG, key=_STORY_KEY)
    _git(clone, "commit", "--allow-empty", "-qm", first_merge)
    _git(clone, "push", "-q", "origin", "main")
    launch_tip = _git(clone, "rev-parse", ORIGIN_MAIN)
    marker = FollowupReview(dw_id=_FOLLOWUP_DW_ID, launch_origin_main_sha=launch_tip)
    vcs = GitVcs()

    def facts(followup_review: FollowupReview | None) -> DispatchGitFacts:
        return supervisor_main.gather_dispatch_git_facts(
            vcs,
            fs=LocalFs(),
            repo_root=clone,
            worktree=worktree,
            story_key=_STORY_KEY,
            project_slug=_SLUG,
            baseline_head_sha=pre_merge_baseline,
            merge_subject_template=_TEMPLATE,
            followup_review=followup_review,
        )

    def verdict(followup_review: FollowupReview | None) -> DispatchSessionVerdict:
        """The completion judgment of a run whose session is still alive."""
        return judge_dispatch_completion(DispatchCompletionInput(session_alive=True, git=facts(followup_review)))

    # The premise: the reused worktree's baseline range still holds the first merge, and a normal run reads it.
    assert first_merge in _git(clone, "log", "--format=%s", f"{pre_merge_baseline}..{ORIGIN_MAIN}")
    assert facts(None).story_merged_on_main is True
    assert verdict(None) is DispatchSessionVerdict.COMPLETED
    # The follow-up is not fooled by it ...
    assert facts(marker).story_merged_on_main is False
    assert verdict(marker) is DispatchSessionVerdict.LIVE
    # ... and still sees its own merge, which reaches origin/main after the launch tip.
    (worktree / "review.md").write_text("reviewed\n", encoding="utf-8")
    _git(worktree, "add", "-A")
    _git(worktree, "commit", "-qm", "review: patch")
    _git(clone, "merge", "--no-ff", "-q", branch, "-m", first_merge)
    _git(clone, "push", "-q", "origin", "main")
    own_merge = facts(marker)
    assert own_merge.story_merged_on_main is True
    assert own_merge.branch_merged is True
    assert verdict(marker) is DispatchSessionVerdict.COMPLETED


# -- _spec_land_block_reason: a follow-up's spec-only diff is its record -------------------------------


def _followup_block_reason(
    repo_root: Path, worktree: Path, git: DispatchGitFacts, *, followup_review: FollowupReview | None
):
    return supervisor_main._spec_land_block_reason(
        fs=FakeFs(),
        repo_root=repo_root,
        slug=_SLUG,
        story_key=_STORY_KEY,
        worktree=worktree,
        git_facts=git,
        followup_review=followup_review,
    )


def test_spec_land_block_reason_lets_a_follow_up_review_land_a_spec_only_diff(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    relative = _seed_spec(repo_root, worktree, primary=_DONE_SPEC_TEXT)
    spec_only = _git_facts(changed=(relative,))

    assert _followup_block_reason(repo_root, worktree, spec_only, followup_review=_FOLLOWUP) is None
    # The same diff on a normal run is still narration (Story 51.4).
    assert (
        _followup_block_reason(repo_root, worktree, spec_only, followup_review=None)
        == "harness produced no changes beyond the tracked spec"
    )


def test_spec_land_block_reason_still_blocks_a_follow_up_whose_spec_reads_blocked(tmp_path: Path) -> None:
    repo_root = _repo(tmp_path)
    worktree = _worktree(repo_root)
    relative = _seed_spec(repo_root, worktree, primary=_BLOCKED_SPEC_TEMPLATE.format(baseline=_BASELINE))

    reason = _followup_block_reason(repo_root, worktree, _git_facts(changed=(relative,)), followup_review=_FOLLOWUP)

    assert reason == "an intent gap the harness could not close"


# -- the tick loop ----------------------------------------------------------------------------------


def test_a_follow_up_run_stays_live_while_only_the_stories_first_merge_is_on_origin_main(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    """The reused-worktree fixture: the story's first merge is on ``origin/main`` and in the (stale) baseline
    range, the run's own branch has not merged, and the first tick is LIVE -- a heartbeat and a sleep, no
    completion. Removing the launch-tip scope fails this (``test_without_the_launch_tip_scope_...`` below)."""
    repo_root = _repo(tmp_path)
    run_dir = _run_dir(repo_root)
    worktree = _worktree(repo_root)
    _seed_journal(run_dir, (_followup_launch_line(),))
    _seed_spec(repo_root, worktree, primary=_DONE_SPEC_TEXT)
    facts = _gather_facts_spy(monkeypatch)
    exits = _spy(monkeypatch, "supervisor_should_exit")
    publisher = FakePublisher()
    vcs = _first_landing_vcs(head_sha=_BASELINE)

    code = _run(repo_root, fs=FakeFs(), vcs=vcs, process=FakeProcess(alive=[True, False]), publisher=publisher)

    assert code == 0
    assert facts[0].story_merged_on_main is False
    # The first tick is LIVE: a heartbeat and a sleep, and no exit was allowed before the session died.
    assert publisher.heartbeats == ["handle-1"]
    assert clock.sleeps == [supervisor_main._TICK_SECONDS]
    # The run's own branch never merged and it did no work: it ends FAILED, never COMPLETED.
    assert [status for _handle, status, _result in publisher.completions] == [DispatchSessionVerdict.FAILED.value]
    assert all(kwargs["story_merged_on_main"] is False for kwargs, _ in exits)
    assert _commit_subject_reads(vcs)
    assert all(read == ("commit_subjects", _TIP_RANGE) for read in _commit_subject_reads(vcs))


@pytest.mark.parametrize(
    "scope",
    [
        pytest.param(lambda ref, *, followup_review: ref, id="scope-removed"),
        pytest.param(lambda ref, *, followup_review: f"{_BASELINE}..{ref}", id="scope-replaced-by-the-baseline"),
    ],
)
def test_without_the_launch_tip_scope_the_reused_worktree_fixture_reads_completed_on_its_first_tick(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _FakeClock, scope
) -> None:
    """Mutation proof for the launch-tip scope: with ``merge_subject_ref`` answering the whole ref, or the run's
    baseline range, the SAME fixture as the LIVE test above reads the story's first merge as the run's own --
    COMPLETED on the first tick, no heartbeat -- so that test fails under either mutation."""
    repo_root = _repo(tmp_path)
    run_dir = _run_dir(repo_root)
    worktree = _worktree(repo_root)
    _seed_journal(run_dir, (_followup_launch_line(),))
    _seed_spec(repo_root, worktree, primary=_DONE_SPEC_TEXT)
    monkeypatch.setattr(supervisor_main, "merge_subject_ref", scope)
    publisher = FakePublisher()

    code = _run(
        repo_root,
        fs=FakeFs(),
        vcs=_first_landing_vcs(head_sha=_BASELINE),
        process=FakeProcess(alive=[True, False]),
        publisher=publisher,
    )

    assert code == 0
    assert publisher.heartbeats == []
    assert [status for _handle, status, _result in publisher.completions] == [DispatchSessionVerdict.COMPLETED.value]


def test_a_follow_up_run_completes_once_its_own_merge_reaches_origin_main(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    repo_root = _repo(tmp_path)
    run_dir = _run_dir(repo_root)
    worktree = _worktree(repo_root)
    _seed_journal(run_dir, (_followup_launch_line(),))
    _seed_spec(repo_root, worktree, primary=_DONE_SPEC_TEXT)
    facts = _gather_facts_spy(monkeypatch)
    publisher = FakePublisher()

    code = _run(
        repo_root,
        fs=FakeFs(),
        vcs=_first_landing_vcs(own_merge=True, head_sha=_MOVED),
        process=FakeProcess(alive=False),
        publisher=publisher,
    )

    assert code == 0
    assert facts[0].story_merged_on_main is True
    assert [status for _handle, status, _result in publisher.completions] == [DispatchSessionVerdict.COMPLETED.value]


def test_the_same_run_without_the_marker_reads_completed_on_the_stories_first_merge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    """A normal run is judged exactly as today: on this repository its first tick reads COMPLETED."""
    repo_root = _repo(tmp_path)
    run_dir = _run_dir(repo_root)
    worktree = _worktree(repo_root)
    _seed_journal(run_dir, (_launch_line(),))
    _seed_spec(repo_root, worktree, primary=_DONE_SPEC_TEXT)
    publisher = FakePublisher()
    vcs = _first_landing_vcs(head_sha=_MOVED)

    code = _run(repo_root, fs=FakeFs(), vcs=vcs, process=FakeProcess(alive=[True, False]), publisher=publisher)

    assert code == 0
    assert publisher.heartbeats == []
    assert [status for _handle, status, _result in publisher.completions] == [DispatchSessionVerdict.COMPLETED.value]
    assert _commit_subject_reads(vcs) == [("commit_subjects", ORIGIN_MAIN)]


def _seed_spec_only_run(repo_root: Path, launch_line: str) -> str:
    """A run whose session ended (``implementation done``) having changed only its own tracked spec."""
    run_dir = _run_dir(repo_root)
    worktree = _worktree(repo_root)
    _seed_journal(run_dir, (launch_line,))
    (run_dir / "session.log").write_text("implementation done\n", encoding="utf-8")
    return _seed_spec(repo_root, worktree, primary=_DONE_SPEC_TEXT)


def test_a_follow_up_run_whose_only_change_is_its_own_spec_lands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    repo_root = _repo(tmp_path)
    relative = _seed_spec_only_run(repo_root, _followup_launch_line())
    _patch_verification(monkeypatch, _clean_envelope)
    land_calls = _patch_landing(monkeypatch)
    fs = FakeFs()
    publisher = FakePublisher()
    vcs = _first_landing_vcs(head_sha=_MOVED, changed=(relative,))

    code = _run(repo_root, fs=fs, vcs=vcs, process=FakeProcess(alive=False), publisher=publisher)

    assert code == 0
    assert len(land_calls) == 1
    # The landing is told it is a follow-up, and which row it serves.
    assert land_calls[0]["followup_review"] == _FOLLOWUP
    journal = fs.journal_text(_run_dir(repo_root))
    assert dispatch_core.KIND_DISPATCH_BLOCKED not in journal
    assert '"verdict": "landed"' in journal
    assert [status for _handle, status, _result in publisher.completions] == [DispatchSessionVerdict.COMPLETED.value]


def test_a_normal_run_whose_only_change_is_its_own_spec_still_never_lands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    """The twin of the follow-up test above, and its regression guard: Story 51.4's rule is untouched."""
    repo_root = _repo(tmp_path)
    relative = _seed_spec_only_run(repo_root, _launch_line())
    _patch_verification(monkeypatch, _clean_envelope)
    land_calls = _patch_landing(monkeypatch)
    fs = FakeFs()
    publisher = FakePublisher()
    vcs = FakeVcs(
        branches=frozenset({dispatch_core.dispatch_worktree_branch(_SLUG, _STORY_KEY)}),
        head_sha=_MOVED,
        changed=(relative,),
    )

    code = _run(repo_root, fs=fs, vcs=vcs, process=FakeProcess(alive=False), publisher=publisher)

    assert code == 0
    assert land_calls == []
    assert dispatch_core.KIND_DISPATCH_BLOCKED in fs.journal_text(_run_dir(repo_root))
    assert [status for _handle, status, _result in publisher.completions] == [DispatchSessionVerdict.FAILED.value]


def test_a_normal_run_passes_the_landing_no_follow_up_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    repo_root = _repo(tmp_path)
    run_dir = _run_dir(repo_root)
    worktree = _worktree(repo_root)
    _seed_journal(run_dir, (_launch_line(),))
    (run_dir / "session.log").write_text("implementation done\n", encoding="utf-8")
    _seed_spec(repo_root, worktree, primary=_READY_SPEC_TEXT)
    _patch_verification(monkeypatch, _clean_envelope)
    land_calls = _patch_landing(monkeypatch)
    branch = dispatch_core.dispatch_worktree_branch(_SLUG, _STORY_KEY)
    vcs = FakeVcs(branches=frozenset({branch}), head_sha=_MOVED)

    code = _run(repo_root, fs=FakeFs(), vcs=vcs, process=FakeProcess(alive=False), publisher=FakePublisher())

    assert code == 0
    assert len(land_calls) == 1
    assert "followup_review" not in land_calls[0]
    assert _commit_subject_reads(vcs)
    assert all(call == ("commit_subjects", ORIGIN_MAIN) for call in _commit_subject_reads(vcs))


def _spy_terminal_verdicts(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, object]]:
    """The keyword arguments of every ``resolve_terminal_session_verdict`` call the loop makes, calling through."""
    real = supervisor_main.resolve_terminal_session_verdict
    calls: list[dict[str, object]] = []

    def _wrapper(**kwargs):
        calls.append(kwargs)
        return real(**kwargs)

    monkeypatch.setattr(supervisor_main, "resolve_terminal_session_verdict", _wrapper)
    return calls


def test_every_terminal_verdict_read_of_a_follow_up_run_takes_no_narration_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    repo_root = _repo(tmp_path)
    relative = _seed_spec_only_run(repo_root, _followup_launch_line())
    _patch_verification(monkeypatch, _clean_envelope)
    _patch_landing(monkeypatch)
    verdict_reads = _spy_terminal_verdicts(monkeypatch)

    _run(
        repo_root,
        fs=FakeFs(),
        vcs=_first_landing_vcs(head_sha=_MOVED, changed=(relative,)),
        process=FakeProcess(alive=False),
        publisher=FakePublisher(),
    )

    assert len(verdict_reads) >= 3  # the loop head, the post-finalize re-read and the post-land re-read
    assert all(read["spec_relative_path"] is None for read in verdict_reads)


def test_every_terminal_verdict_read_of_a_normal_run_still_takes_the_spec_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    repo_root = _repo(tmp_path)
    relative = _seed_spec_only_run(repo_root, _launch_line())
    _patch_verification(monkeypatch, _clean_envelope)
    _patch_landing(monkeypatch)
    verdict_reads = _spy_terminal_verdicts(monkeypatch)
    branch = dispatch_core.dispatch_worktree_branch(_SLUG, _STORY_KEY)

    _run(
        repo_root,
        fs=FakeFs(),
        vcs=FakeVcs(branches=frozenset({branch}), head_sha=_MOVED, changed=(relative,)),
        process=FakeProcess(alive=False),
        publisher=FakePublisher(),
    )

    assert verdict_reads
    assert all(read["spec_relative_path"] == relative for read in verdict_reads)


def test_a_failed_follow_up_run_with_a_spec_only_diff_preserves_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _FakeClock
) -> None:
    """A follow-up's spec-only diff is progress, so a verification the run then fails still preserves it."""
    repo_root = _repo(tmp_path)
    relative = _seed_spec_only_run(repo_root, _followup_launch_line())
    _patch_verification(monkeypatch, _refused_envelope)
    land_calls = _patch_landing(monkeypatch)
    fs = FakeFs()
    publisher = FakePublisher()

    code = _run(
        repo_root,
        fs=fs,
        vcs=_first_landing_vcs(head_sha=_MOVED, changed=(relative,), patch="diff --git a/spec b/spec\n"),
        process=FakeProcess(alive=False),
        publisher=publisher,
    )

    assert code == 0
    assert land_calls == []
    assert [status for _handle, status, _result in publisher.completions] == [DispatchSessionVerdict.FAILED.value]
    assert dispatch_core.KIND_DISPATCH_PRESERVE in fs.journal_text(_run_dir(repo_root))


# -- both land sites hand a follow-up run to the landing, and re-gather with its marker (BH-6 / VG-1 / VG-2)


def _seed_followup_live_branch_land_run(repo_root: Path) -> None:
    """The first land site: verification ``verified`` while a marshal-initiated stop keeps the run ``LIVE``."""
    run_dir = _run_dir(repo_root)
    worktree = _worktree(repo_root)
    _seed_journal(
        run_dir,
        (
            _followup_launch_line(),
            *_outcome_pair(
                kind=dispatch_core.KIND_DISPATCH_VERIFICATION,
                payload={"verdict": "verified", "ok": True},
                counter=1,
            ),
        ),
    )
    (run_dir / "session.log").write_text("budget-stop reached; idle-defer\n", encoding="utf-8")
    _seed_spec(repo_root, worktree, primary=_DONE_SPEC_TEXT)


def _seed_followup_terminal_branch_land_run(repo_root: Path) -> None:
    """The second land site: the session ended unverified, so finalize verifies, then the terminal branch lands."""
    run_dir = _run_dir(repo_root)
    worktree = _worktree(repo_root)
    _seed_journal(run_dir, (_followup_launch_line(),))
    (run_dir / "session.log").write_text("implementation done\n", encoding="utf-8")
    _seed_spec(repo_root, worktree, primary=_DONE_SPEC_TEXT)


@pytest.mark.parametrize(
    ("seed", "verdict"),
    [
        pytest.param(_seed_followup_live_branch_land_run, DispatchLandingVerdict.LANDED, id="live-branch-landed"),
        pytest.param(
            _seed_followup_terminal_branch_land_run, DispatchLandingVerdict.LANDED, id="terminal-branch-landed"
        ),
        pytest.param(
            _seed_followup_terminal_branch_land_run, DispatchLandingVerdict.REFUSED, id="terminal-branch-refused"
        ),
    ],
)
def test_each_land_site_hands_a_follow_up_run_to_the_landing_and_regathers_with_its_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _FakeClock, seed, verdict: DispatchLandingVerdict
) -> None:
    repo_root = _repo(tmp_path)
    seed(repo_root)
    _patch_verification(monkeypatch, _clean_envelope)
    land_calls = _patch_landing(monkeypatch, verdict=verdict)
    blocks = _record_land_or_block(monkeypatch)
    vcs = _first_landing_vcs(head_sha=_MOVED)
    _log_landings_into(monkeypatch, vcs)

    code = _run(repo_root, fs=FakeFs(), vcs=vcs, process=FakeProcess(alive=False), publisher=FakePublisher())

    assert code == 0
    # The site's own call into `_land_or_journal_block` carries the marker, and so does the landing it makes.
    assert blocks
    assert all(kwargs["followup_review"] == _FOLLOWUP for _args, kwargs in blocks)
    assert land_calls
    assert all(call["followup_review"] == _FOLLOWUP for call in land_calls)
    # The re-gather right after the landing is scoped to the launch tip too, never the whole ref.
    reads = [call for call in vcs.calls if call[0] in {"land", "commit_subjects"}]
    after_land = reads[reads.index(("land",)) + 1 :]
    assert after_land
    assert after_land[0] == ("commit_subjects", _TIP_RANGE)
    assert ("commit_subjects", ORIGIN_MAIN) not in reads


def test_a_follow_up_runs_blocked_halt_regathers_with_the_launch_tip_scope(tmp_path: Path, clock: _FakeClock) -> None:
    """The twin of ``test_supervisor_commits_and_promotes_a_blocked_halt`` for a follow-up run on a story whose
    first merge is already on ``origin/main``: the re-gather after the committed halt keeps the launch-tip
    scope, so the completion INTENT never records the story's first merge as this run's."""
    repo_root = _repo(tmp_path)
    run_dir = _run_dir(repo_root)
    worktree = _worktree(repo_root)
    _seed_journal(
        run_dir,
        (
            _followup_launch_line(),
            *_outcome_pair(
                kind=dispatch_core.KIND_DISPATCH_FINALIZE,
                payload={"story_key": _STORY_KEY, "trigger": "harness-done", "ok": True},
                counter=1,
            ),
        ),
    )
    _seed_spec(
        repo_root,
        worktree,
        primary=_DONE_SPEC_TEXT,
        worktree_text=_BLOCKED_SPEC_TEMPLATE.format(baseline=_BASELINE),
    )
    vcs = _first_landing_vcs(head_sha=_MOVED)
    fs = FakeFs()
    publisher = FakePublisher()

    code = _run(repo_root, fs=fs, vcs=vcs, process=FakeProcess(alive=False), publisher=publisher)

    assert code == 0
    reads = _commit_subject_reads(vcs)
    assert reads and all(read == ("commit_subjects", _TIP_RANGE) for read in reads)
    entries = [json.loads(line) for line in fs.journal_text(run_dir).splitlines() if line]
    [completion_intent] = [
        e for e in entries if e["kind"] == dispatch_core.KIND_DISPATCH_COMPLETION and e["phase"] == Phase.INTENT.value
    ]
    assert completion_intent["payload"]["verdict"] == DispatchSessionVerdict.BLOCKED.value
    assert completion_intent["payload"]["story_merged_on_main"] is False


# --------------------------------------------------------------------------
# Story 85.2 — verify-fix turn coverage on this module's floor
# --------------------------------------------------------------------------


def _platform_config(repo_root: Path) -> Path:
    config = repo_root / "src/platform/config"
    config.mkdir(parents=True, exist_ok=True)
    return config


def _seed_verify_fix_flag(repo_root: Path, *, on: bool) -> None:
    from pyforge.testing_kit.flags import flagd_tree

    from pyforge.marshal.core.dispatch_verify_fix import VERIFY_FIX_LOOP_FLAG_KEY

    flagd_tree(_platform_config(repo_root), {VERIFY_FIX_LOOP_FLAG_KEY: "on" if on else "off"})


class _HarnessResolutionStub:
    spec = None


def _refused_verify_envelope(tail: str = "E501 line too long\n"):
    command = "pixi run --frozen -e pyforge-marshal pyforge-marshal-test"
    return build_envelope(
        command="dispatch verify",
        verdict="gate-failed",
        data={
            "slug": _SLUG,
            "commands": [{"command": command, "returncode": 1, "stdout": tail, "stderr": ""}],
        },
        findings=(
            Finding(code="MRS-GATE-001", severity=Severity.ERROR, message=f"verify command {command!r} exited 1"),
        ),
    )


def test_verify_fix_turn_reads_failed_commands_from_a_sidecar(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = _repo(tmp_path)
    _seed_verify_fix_flag(repo_root, on=True)
    worktree = _worktree(repo_root)
    _seed_spec(repo_root, worktree, primary=_READY_SPEC_TEXT)
    monkeypatch.setattr(
        supervisor_main,
        "evaluate_dispatch_verification",
        lambda **_k: _refused_verify_envelope("x" * 9000),
    )
    calls: list[str] = []

    def _launch(*_a, **_k):
        calls.append("launch")
        raise supervisor_main.BuildHarnessError("stop")

    monkeypatch.setattr(supervisor_main.BmadBuildHarness, "binary_present", lambda *_a, **_k: _HarnessResolutionStub())
    monkeypatch.setattr(supervisor_main.BmadBuildHarness, "dispatch_verify_fix", _launch)
    fs = FakeFs()
    branch = dispatch_core.dispatch_worktree_branch(_SLUG, _STORY_KEY)

    _finalize(fs, FakeVcs(branches=frozenset({branch}), head_sha=_MOVED), repo_root, worktree)

    assert calls == ["launch"]


def test_verify_fix_turn_reverify_green_and_pre_verify_commit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from pyforge.marshal.dispatch_verify import ProcessWaitResult

    repo_root = _repo(tmp_path)
    _seed_verify_fix_flag(repo_root, on=True)
    worktree = _worktree(repo_root)
    _seed_spec(repo_root, worktree, primary=_READY_SPEC_TEXT)
    branch = dispatch_core.dispatch_worktree_branch(_SLUG, _STORY_KEY)
    vcs = FakeVcs(dirty=True, changed_vs_head=("fix.py",), branches=frozenset({branch}), head_sha=_MOVED)
    n = {"v": 0}

    def _evaluate(**_k):
        n["v"] += 1
        return _refused_verify_envelope() if n["v"] == 1 else _clean_envelope()

    monkeypatch.setattr(supervisor_main, "evaluate_dispatch_verification", _evaluate)
    monkeypatch.setattr(supervisor_main.BmadBuildHarness, "binary_present", lambda *_a, **_k: _HarnessResolutionStub())
    monkeypatch.setattr(
        supervisor_main.BmadBuildHarness,
        "dispatch_verify_fix",
        lambda *_a, **_k: type("L", (), {"pid": 88011})(),
    )
    monkeypatch.setattr(
        supervisor_main,
        "wait_for_process",
        lambda *_a, **_k: ProcessWaitResult(exited=True, returncode=0),
    )
    fs = FakeFs()

    _counter, ok = _finalize(fs, vcs, repo_root, worktree)

    assert ok is True
    assert vcs.commits


def test_verify_fix_turn_resume_waits_on_a_journaled_pid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from pyforge.marshal.core.journal import VERIFY_FAILED_COMMANDS_FIELD
    from pyforge.marshal.dispatch_verify import ProcessWaitResult

    repo_root = _repo(tmp_path)
    _seed_verify_fix_flag(repo_root, on=True)
    worktree = _worktree(repo_root)
    _seed_spec(repo_root, worktree, primary=_READY_SPEC_TEXT)
    command = "pixi run --frozen -e pyforge-marshal pyforge-marshal-test"
    ver = _outcome_pair(
        kind=dispatch_core.KIND_DISPATCH_VERIFICATION,
        payload={
            "verdict": "refused",
            "ok": False,
            "failed_gate": "MRS-GATE-001",
            "failed_message": f"verify command {command!r} exited 1",
            "scope_violation_advisories": [],
            VERIFY_FAILED_COMMANDS_FIELD: [{"command": command, "exit_code": 1, "output_tail": "fail\n"}],
        },
        counter=1,
    )
    fix_intent = build_entry(
        id=JournalEntryId("dispatch-supervisor-1", 10),
        ts="2026-10-03T10:00:00.000Z",
        run_id=_RUN_ID,
        kind=dispatch_core.KIND_DISPATCH_VERIFY_FIX,
        phase=Phase.INTENT,
        payload={
            "launch_mode": "fix_only",
            "wall_clock_budget_s": 600.0,
            "budget_started_monotonic": 1000.0,
        },
    )
    fix_obs = build_entry(
        id=JournalEntryId("dispatch-supervisor-1", 11),
        ts="2026-10-03T10:00:01.000Z",
        run_id=_RUN_ID,
        kind=dispatch_core.KIND_DISPATCH_VERIFY_FIX,
        phase=Phase.OBSERVATION,
        payload={"session_pid": 88012, "ok": True, "fix_intent_id": str(fix_intent.id)},
    )
    waits: list[float] = []
    monkeypatch.setattr(
        supervisor_main,
        "wait_for_process",
        lambda _p, _pid, *, timeout_s, on_poll=None: (
            waits.append(timeout_s),
            ProcessWaitResult(exited=True, returncode=1),
        )[1],
    )
    monkeypatch.setattr(supervisor_main.time, "monotonic", lambda: 1150.0)
    monkeypatch.setattr(
        supervisor_main.BmadBuildHarness,
        "dispatch_verify_fix",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no second launch")),
    )
    fs = FakeFs()
    branch = dispatch_core.dispatch_worktree_branch(_SLUG, _STORY_KEY)

    _finalize(
        fs,
        FakeVcs(branches=frozenset({branch}), head_sha=_MOVED),
        repo_root,
        worktree,
        journal_lines=(*ver, prepare_for_write(fix_intent).line, prepare_for_write(fix_obs).line),
    )

    assert waits and waits[0] == 450.0


def test_verify_fix_turn_in_flight_helper(tmp_path: Path) -> None:
    fs = FakeFs()
    run_dir = _run_dir(_repo(tmp_path))
    intent = build_entry(
        id=JournalEntryId("dispatch-supervisor-1", 1),
        ts="2026-10-03T10:00:00.000Z",
        run_id=_RUN_ID,
        kind=dispatch_core.KIND_DISPATCH_VERIFY_FIX,
        phase=Phase.INTENT,
        payload={"launch_mode": "fix_only"},
    )
    _seed_journal(run_dir, (_launch_line(), prepare_for_write(intent).line))
    folded = supervisor_main._fold_dispatch_journal(fs, run_dir, fs.journal_text(run_dir))

    assert supervisor_main.verify_fix_turn_in_flight(folded, _RUN_ID) is True
