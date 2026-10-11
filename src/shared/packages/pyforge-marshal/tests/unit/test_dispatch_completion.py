"""Unit tests for dispatch completion judgment (Story 22.2)."""

from __future__ import annotations

import argparse
import ast
import inspect
import subprocess
from pathlib import Path

import pytest
from pyforge.core.process import ProcessResult

from pyforge.marshal.adapters.fs_local import FsError
from pyforge.marshal.adapters.vcs_git import VcsCommandError
from pyforge.marshal.cli.dispatch import live_dispatch_conflict, run_dispatch
from pyforge.marshal.core import dispatch as dispatch_core
from pyforge.marshal.core.dispatch_completion import (
    DispatchCompletionInput,
    DispatchGitFacts,
    DispatchSessionVerdict,
    has_git_progress,
    is_spec_only_narration,
    judge_dispatch_completion,
    merge_subject_ref,
    narration_spec_path,
    run_head_reached_ref,
    zombie_redispatch_evidence,
)
from pyforge.marshal.core.dispatch_harness_done import FollowupReview
from pyforge.marshal.core.status import FleetHomeFacts, build_fleet_row
from pyforge.marshal.core.verdict import EXIT_OK
from pyforge.marshal.ports.build_harness import DispatchLaunchResult, HarnessResolution


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "dispatch@test"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "dispatch"],
        cwd=path,
        check=True,
        capture_output=True,
    )


def test_judge_live_when_session_process_alive() -> None:
    git = DispatchGitFacts(
        baseline_head_sha="aaa",
        current_head_sha="aaa",
        changed_paths=(),
        branch_merged=False,
        story_merged_on_main=False,
    )
    verdict = judge_dispatch_completion(DispatchCompletionInput(session_alive=True, git=git))
    assert verdict == DispatchSessionVerdict.LIVE


def test_run_head_reached_ref_true_when_merge_base_equals_head() -> None:
    class _Vcs:
        def merge_base(self, _repo_root: Path, a: str, b: str) -> str:
            assert b == "refs/remotes/origin/main"
            return a

    assert run_head_reached_ref(_Vcs(), Path("/tmp"), "abc123", "refs/remotes/origin/main") is True


def test_run_head_reached_ref_false_when_head_is_ahead_of_main() -> None:
    class _Vcs:
        def merge_base(self, _repo_root: Path, a: str, b: str) -> str:
            return "older-than-head"

    assert run_head_reached_ref(_Vcs(), Path("/tmp"), "abc123", "refs/remotes/origin/main") is False


def test_run_head_reached_ref_fails_closed_on_vcs_error() -> None:
    class _Vcs:
        def merge_base(self, _repo_root: Path, a: str, b: str) -> str:
            raise VcsCommandError("cannot read")

    assert run_head_reached_ref(_Vcs(), Path("/tmp"), "abc123", "refs/remotes/origin/main") is False


def test_judge_completed_when_story_merged_on_main() -> None:
    git = DispatchGitFacts(
        baseline_head_sha="aaa",
        current_head_sha="bbb",
        changed_paths=("src/foo.py",),
        branch_merged=False,
        story_merged_on_main=True,
    )
    verdict = judge_dispatch_completion(DispatchCompletionInput(session_alive=False, git=git))
    assert verdict == DispatchSessionVerdict.COMPLETED


def test_zombie_trap_dead_process_with_git_progress_is_live() -> None:
    git = DispatchGitFacts(
        baseline_head_sha="aaa",
        current_head_sha="bbb",
        changed_paths=("src/foo.py",),
        branch_merged=False,
        story_merged_on_main=False,
    )
    verdict = judge_dispatch_completion(
        DispatchCompletionInput(
            session_alive=False,
            git=git,
            harness_reported_failure=True,
        )
    )
    assert verdict == DispatchSessionVerdict.LIVE


def test_resolve_verdict_completed_when_land_journal_succeeded() -> None:
    """Dead session + git progress must not block chain after CAP-4 land."""
    from types import SimpleNamespace

    from pyforge.marshal.cli.dispatch import resolve_dispatch_session_verdict

    journal = dispatch_core.DispatchJournalFacts(
        story_key="28.9",
        session_pid=999999,
        model=None,
        launched_at=None,
        worktree_path="/tmp/wt",
        baseline_head_sha="aaa",
        landing_verdict="landed",
    )

    class DeadProcess:
        def is_alive(self, _pid: int) -> bool:
            return False

    def process_start_time(self, _pid: int) -> float | None:
        return None

    effective = SimpleNamespace(merge_subject_template=SimpleNamespace(value="Merge {key} into main"))

    verdict = resolve_dispatch_session_verdict(
        fs=object(),
        vcs=object(),
        process=DeadProcess(),
        repo_root=Path("/tmp"),
        slug="pyforge-marshal",
        journal=journal,
        effective_policy=effective,
    )
    assert verdict == DispatchSessionVerdict.COMPLETED


def test_resolve_verdict_blocked_short_circuits_before_git_facts() -> None:
    """Story 51.11 (CAP-258): an already-committed ``blocked`` verdict must
    not be re-derived from fresh git facts -- doing so would re-introduce
    the exact bug this story fixes (stale facts reading
    ``stopped_externally``). ``fs``/``vcs``/``process`` are never touched
    when this short-circuit fires."""
    from pyforge.marshal.cli.dispatch import resolve_dispatch_session_verdict

    journal = dispatch_core.DispatchJournalFacts(
        story_key="51.11",
        session_pid=999999,
        model=None,
        launched_at=None,
        worktree_path="/tmp/wt",
        baseline_head_sha="aaa",
        completion_verdict="blocked",
    )

    class ExplodingProcess:
        def is_alive(self, _pid: int) -> bool:
            raise AssertionError("must not consult process facts")

    def process_start_time(self, _pid: int) -> float | None:
        return None

    from types import SimpleNamespace

    effective = SimpleNamespace(merge_subject_template=SimpleNamespace(value="Merge {key} into main"))

    verdict = resolve_dispatch_session_verdict(
        fs=object(),
        vcs=object(),
        process=ExplodingProcess(),
        repo_root=Path("/tmp"),
        slug="pyforge-marshal",
        journal=journal,
        effective_policy=effective,
    )
    assert verdict == DispatchSessionVerdict.BLOCKED


def test_zombie_redispatch_evidence_names_git_progress() -> None:
    git = DispatchGitFacts(
        baseline_head_sha="aaa111",
        current_head_sha="bbb222",
        changed_paths=("pkg/module.py",),
        branch_merged=False,
        story_merged_on_main=False,
    )
    evidence = zombie_redispatch_evidence(
        story_key="22-2-example",
        verdict=DispatchSessionVerdict.LIVE,
        git=git,
        session_alive=False,
        harness_reported_failure=True,
    )
    assert evidence is not None
    assert "git facts" in evidence
    assert "harness reported failure" in evidence


def test_build_fleet_row_surfaces_live_dispatch_by_completion_verdict() -> None:
    facts = FleetHomeFacts(
        slug="pyforge-marshal",
        branch="loop/pyforge-marshal",
        has_run=False,
        dispatch_story="22-2-example",
        dispatch_engine_alive=False,
        dispatch_completion_verdict="live",
        dispatch_elapsed_seconds=42.0,
        dispatch_run_id="pyforge-marshal-20260823T000000000Z-cafebabe",
    )
    row, finding = build_fleet_row(facts)
    assert finding is None
    assert row["state"] == "running"
    assert row["current_story"] == "22-2-example"
    assert row["dispatch_completion_verdict"] == "live"


def test_run_dispatch_has_no_foreground_busy_wait() -> None:
    import pyforge.marshal.cli.dispatch as dispatch_module

    source = Path(dispatch_module.__file__)
    tree = ast.parse(source.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "time":
                if node.func.attr == "sleep":
                    pytest.fail("run_dispatch must not call time.sleep (CAP-2 busy-wait trap)")
        if isinstance(node, ast.While):
            for child in ast.walk(node):
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                    if child.func.attr == "is_alive":
                        pytest.fail("run_dispatch must not busy-wait on is_alive (CAP-2 watchdog trap)")


class FakeFs:
    def __init__(self) -> None:
        self.dirs: set[Path] = set()
        self.files: dict[Path, str] = {}
        self.appended: list[tuple[Path, str, bool]] = []

    def is_dir(self, path: Path) -> bool:
        return path in self.dirs

    def ensure_dir(self, path: Path) -> None:
        self.dirs.add(path)

    def create_dir_exclusive(self, path: Path) -> None:
        self.dirs.add(path)

    def append_line(self, path: Path, line: str, *, fsync: bool) -> None:
        self.appended.append((path, line, fsync))
        self.files[path] = self.files.get(path, "") + line

    def write_text_atomic(self, path: Path, content: str) -> None:
        self.files[path] = content
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def read_text(self, path: Path) -> str | None:
        if path in self.files:
            return self.files[path]
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return None

    def read_symlink_target(self, path: Path) -> Path | None:
        if not path.is_symlink():
            return None
        return path.readlink()

    def repoint_symlink_atomic(self, path: Path, target: Path) -> None:
        if not path.is_symlink() and path.exists():
            raise FsError(f"{path} is a real file/directory, not a symlink -- refusing to replace it")
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_symlink() or path.exists():
            path.unlink()
        path.symlink_to(target)

    def exists(self, path: Path) -> bool:
        return path.exists()


class FakeVcs:
    def __init__(self, repo_root: Path, *, head_sha: str = "baseline1234") -> None:
        self.repo_root = repo_root
        self.head_sha = head_sha
        self.added: list[tuple[Path, Path, str, str]] = []

    def repo_common_root(self, _cwd: Path) -> Path:
        return self.repo_root

    def branch_exists(self, _repo_root: Path, _branch: str) -> bool:
        return False

    def worktree_path_for_branch(self, _repo_root: Path, _branch: str) -> Path | None:
        return None

    def add_worktree(self, repo_root: Path, home: Path, branch: str, *, base: str) -> None:
        self.added.append((repo_root, home, branch, base))
        home.mkdir(parents=True, exist_ok=True)

    def worktree_head_sha(self, _worktree: Path) -> str:
        return self.head_sha

    def changed_files(self, _repo_root: Path, _worktree_path: Path, *, base: str) -> tuple[str, ...]:
        return ()

    def worktree_unified_patch(self, _worktree_path: Path, *, baseline_sha: str) -> str:
        return ""


class FakeBuildHarness:
    def __init__(self, *, pid: int = 5151) -> None:
        self.pid = pid
        self.calls: list[dict[str, object]] = []

    def binary_present(self, preference=(), repo_root=None) -> HarnessResolution:
        chosen = next(iter(preference), "claude")
        return HarnessResolution(profile=chosen, binary_path=f"/usr/bin/{chosen}")

    def dispatch(self, worktree: Path, **kwargs) -> DispatchLaunchResult:
        self.calls.append({"worktree": worktree, **kwargs})
        return DispatchLaunchResult(
            pid=self.pid,
            command=("fake-harness",),
            model=kwargs.get("model"),
            budget_env=dict(kwargs.get("budget_env") or {}),
        )


class FakeProcess:
    def __init__(self, *, alive: bool = True, session_check_returncode: int = 0) -> None:
        self.alive = alive
        self.spawned: list[list[str]] = []
        # Story 63.4: dispatch_once shells `steward session check --json`
        # right after repo_root resolves. Default 0 ("ok") keeps every
        # pre-existing fixture behaviour byte-identical -- no unexpected
        # MRS-DISP-049 finding unless a test opts in.
        self.session_check_returncode = session_check_returncode
        self.run_calls: list[list[str]] = []

    def is_alive(self, _pid: int) -> bool:
        return self.alive

    def process_start_time(self, _pid: int) -> float | None:
        return None

    def spawn_detached(self, argv, *, cwd: Path, log_path: Path) -> int:
        self.spawned.append(list(argv))
        return 9001

    def run(self, argv, *, cwd: Path, timeout_s: float | None = None) -> ProcessResult:
        self.run_calls.append(list(argv))
        return ProcessResult(returncode=self.session_check_returncode, stdout="", stderr="")


def test_run_dispatch_spawns_completion_supervisor_without_waiting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_git_repo(tmp_path)
    slug = "pyforge-marshal"
    story = "22-2-completion-is-judged-from-git-and-process-facts-and-a-zombie-is-never-redispatched"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True)
    spec = specs / f"spec-{story}.md"
    from dispatch_spec_fixtures import BINDING_VERIFICATION_TAIL

    spec.write_text(f"---\ndifficulty: medium\n---\n# spec\n{BINDING_VERIFICATION_TAIL}", encoding="utf-8")

    fs = FakeFs()
    vcs = FakeVcs(tmp_path, head_sha="deadbeef0001")
    harness = FakeBuildHarness()
    process = FakeProcess()

    args = argparse.Namespace(slug=slug, story=story, format="json")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    # Story 64.1's worktree-side scope guard (`_seed_dispatch_worktree_scope`) calls
    # `verify_scope` against the dispatch worktree's own triangle before launch, and
    # refuses when it disagrees with `slug` -- this test's bare `_init_git_repo`
    # fixture leaves the worktree without one, and scope verification is not this
    # test's concern (it verifies completion-supervisor spawning). Patched at the
    # dispatch module's own imported binding, not the `scope` module's source, since
    # `from ..scope import verify_scope` binds a local name `dispatch.py` reads directly.
    import pyforge.marshal.cli.dispatch as dispatch_module

    monkeypatch.setattr(dispatch_module, "verify_scope", lambda *_a, **_k: None)
    code = run_dispatch(
        args,
        fs=fs,
        vcs=vcs,
        build_harness=harness,
        process=process,
    )
    assert code == EXIT_OK
    assert process.spawned
    assert "pyforge.marshal.dispatch_supervisor" in process.spawned[0]
    assert "deadbeef0001" in process.spawned[0]


def test_live_dispatch_conflict_refuses_marshal_initiated_zombie_redispatch(
    tmp_path: Path,
) -> None:
    """Story 28.13: marshal ladder stops stay LIVE; external SIGTERM stops do not."""
    from pyforge.marshal.cli.dispatch import _compose_policy, gather_dispatch_journal_facts
    from pyforge.marshal.core.journal import JournalEntryId, Phase, build_entry, prepare_for_write

    slug = "pyforge-marshal"
    story = "22-2-example-story"
    fs = FakeFs()
    run_dir = dispatch_core.dispatch_run_dir(tmp_path, slug, "run-1")
    run_dir.mkdir(parents=True, exist_ok=True)
    session_log = run_dir / "session.log"
    session_log.write_text("budget-stop: idle ceiling reached\n", encoding="utf-8")
    fs.files[session_log] = session_log.read_text(encoding="utf-8")
    journal_path = run_dir / "journal.jsonl"
    intent = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 0),
            ts="2026-08-23T00:00:00.000Z",
            run_id="run-1",
            kind=dispatch_core.KIND_DISPATCH_LAUNCH,
            phase=Phase.INTENT,
            payload={
                "story_key": "22.2",
                "worktree_path": "/tmp/wt",
                "baseline_head_sha": "aaa111",
            },
        )
    ).line
    outcome = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 1),
            ts="2026-08-23T00:00:01.000Z",
            run_id="run-1",
            kind=dispatch_core.KIND_DISPATCH_LAUNCH,
            phase=Phase.OUTCOME,
            intent_id=JournalEntryId("w", 0),
            payload={"session_pid": 42},
        )
    ).line
    journal_text = intent + "\n" + outcome + "\n"
    journal_path.write_text(journal_text, encoding="utf-8")
    fs.files[journal_path] = journal_text
    journal = gather_dispatch_journal_facts(fs, run_dir, "run-1")
    assert journal.story_key == "22.2"

    class ZombieVcs(FakeVcs):
        def changed_files(self, repo_root: Path, worktree_path: Path, *, base: str):
            return ("src/changed.py",)

        def is_branch_merged(self, repo_root: Path, branch: str, *, into: str, into_ref: str | None = None) -> bool:
            return False

        def commit_subjects(self, repo_root: Path, ref: str):
            return ()

        def worktree_head_sha(self, worktree_path: Path) -> str:
            return "bbb222"

    policy = _compose_policy(slug)
    evidence = live_dispatch_conflict(
        fs=fs,
        vcs=ZombieVcs(tmp_path),
        process=FakeProcess(alive=False),
        repo_root=tmp_path,
        slug=slug,
        story_key=story,
        effective_policy=policy,
        harness_reported_failure=True,
    )
    assert evidence is not None
    assert "git facts" in evidence


# --- a follow-up review run's two scopes (Story 73.1, CAP-281) ----------------

_LAUNCH_TIP = "0123456789abcdef0123456789abcdef01234567"
_MARKER = FollowupReview(dw_id="DW-FRR-51-2", launch_origin_main_sha=_LAUNCH_TIP)


def test_merge_subject_ref_is_the_whole_ref_for_a_normal_run() -> None:
    assert merge_subject_ref("refs/remotes/origin/main", followup_review=None) == "refs/remotes/origin/main"


def test_merge_subject_ref_is_the_range_since_the_launch_tip_for_a_follow_up() -> None:
    assert (
        merge_subject_ref("refs/remotes/origin/main", followup_review=_MARKER)
        == f"{_LAUNCH_TIP}..refs/remotes/origin/main"
    )


def test_merge_subject_ref_never_scopes_a_follow_up_to_anything_but_the_launch_tip() -> None:
    """The run's baseline has no parameter here at all: a reused pre-merge worktree makes it stale (G1)."""
    assert "baseline_head_sha" not in inspect.signature(merge_subject_ref).parameters
    other_tip = "f" * 40
    marker = FollowupReview(dw_id=None, launch_origin_main_sha=other_tip)
    assert merge_subject_ref("refs/remotes/origin/main", followup_review=marker).startswith(f"{other_tip}..")


def test_merge_subject_ref_reads_nothing_for_a_follow_up_whose_intent_recorded_no_tip() -> None:
    assert merge_subject_ref("refs/remotes/origin/main", followup_review=FollowupReview(dw_id="DW-FRR-51-2")) is None


_SPEC_REL = "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-51-2-x.md"


def test_narration_spec_path_keeps_the_path_for_a_normal_run_and_drops_it_for_a_follow_up() -> None:
    assert narration_spec_path(_SPEC_REL, followup_review=None) == _SPEC_REL
    assert narration_spec_path(_SPEC_REL, followup_review=_MARKER) is None
    assert narration_spec_path(None, followup_review=None) is None
    assert narration_spec_path(None, followup_review=_MARKER) is None


def _spec_only_facts() -> DispatchGitFacts:
    return DispatchGitFacts(
        baseline_head_sha="aaa",
        current_head_sha="bbb",
        changed_paths=(_SPEC_REL,),
        branch_merged=False,
        story_merged_on_main=False,
    )


def test_a_spec_only_diff_is_narration_for_a_normal_run_and_progress_for_a_follow_up() -> None:
    git = _spec_only_facts()
    normal = narration_spec_path(_SPEC_REL, followup_review=None)
    followup = narration_spec_path(_SPEC_REL, followup_review=_MARKER)
    assert is_spec_only_narration(git.changed_paths, normal) is True
    assert has_git_progress(git, spec_relative_path=normal) is False
    assert is_spec_only_narration(git.changed_paths, followup) is False
    assert has_git_progress(git, spec_relative_path=followup) is True
