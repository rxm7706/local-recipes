"""Unit tests for Story 28.13 — sanctioned retry after operator-initiated stop."""

from __future__ import annotations

from pathlib import Path

from pyforge.marshal.adapters.vcs_git import VcsCommandError
from pyforge.marshal.cli.dispatch import (
    _policy_flags_from_harness_arg,
    _surface_worktree_wip_before_dispatch,
    gather_dispatch_journal_facts,
    resolve_dispatch_session_verdict,
    station_in_flight_conflict,
    station_story_blocked_evidence,
)
from pyforge.marshal.core import dispatch as dispatch_core
from pyforge.marshal.core.dispatch_completion import (
    DispatchGitFacts,
    DispatchSessionVerdict,
)
from pyforge.marshal.core.journal import JournalEntryId, Phase, build_entry, prepare_for_write
from pyforge.marshal.core.supervise import (
    count_unified_diff_lines,
    is_marshal_initiated_stop,
    resolve_terminal_session_verdict,
)


def _git_facts(**kwargs) -> DispatchGitFacts:
    defaults = dict(
        baseline_head_sha="aaa111",
        current_head_sha="bbb222",
        changed_paths=("src/foo.py",),
        branch_merged=False,
        story_merged_on_main=False,
    )
    defaults.update(kwargs)
    return DispatchGitFacts(**defaults)


def test_external_stop_classifies_as_stopped_externally() -> None:
    verdict = resolve_terminal_session_verdict(
        session_alive=False,
        git=_git_facts(),
        verification_verdict=None,
        session_log="process exited unexpectedly",
    )
    assert verdict is DispatchSessionVerdict.STOPPED_EXTERNALLY


def test_marshal_idle_defer_stop_stays_live_with_git_progress() -> None:
    verdict = resolve_terminal_session_verdict(
        session_alive=False,
        git=_git_facts(),
        verification_verdict=None,
        detach_reason="idle-deferred",
    )
    assert verdict is DispatchSessionVerdict.LIVE


def test_marshal_budget_stop_stays_live_with_git_progress() -> None:
    verdict = resolve_terminal_session_verdict(
        session_alive=False,
        git=_git_facts(),
        verification_verdict=None,
        detach_reason="budget-run-tokens-exceeded",
    )
    assert verdict is DispatchSessionVerdict.LIVE


def test_verify_refused_dead_session_still_failed() -> None:
    verdict = resolve_terminal_session_verdict(
        session_alive=False,
        git=_git_facts(),
        verification_verdict="refused",
    )
    assert verdict is DispatchSessionVerdict.FAILED


def test_live_session_unchanged() -> None:
    verdict = resolve_terminal_session_verdict(
        session_alive=True,
        git=_git_facts(changed_paths=()),
        verification_verdict=None,
    )
    assert verdict is DispatchSessionVerdict.LIVE


def test_is_marshal_initiated_stop_from_session_log() -> None:
    assert is_marshal_initiated_stop(session_log="supervisor idle-defer outcome")
    assert not is_marshal_initiated_stop(session_log="killed by operator")


def test_count_unified_diff_lines() -> None:
    patch = "--- a/foo\n+++ b/foo\n@@\n-old\n+new\n"
    assert count_unified_diff_lines(patch) == 2


def _seed_dispatch_journal_with_completion(
    tmp_path: Path,
    *,
    slug: str,
    run_id: str,
    story_key: str,
    completion_verdict: str,
    baseline_head_sha: str = "aaa111",
    session_pid: int = 42,
) -> Path:
    run_dir = dispatch_core.dispatch_run_dir(tmp_path, slug, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    intent = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 0),
            ts="2026-09-01T00:00:00.000Z",
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_LAUNCH,
            phase=Phase.INTENT,
            payload={
                "story_key": story_key,
                "worktree_path": str(tmp_path / ".worktrees" / f"dispatch-{slug}"),
                "baseline_head_sha": baseline_head_sha,
            },
        )
    ).line
    launch_outcome = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 1),
            ts="2026-09-01T00:00:01.000Z",
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_LAUNCH,
            phase=Phase.OUTCOME,
            intent_id=JournalEntryId("w", 0),
            payload={"session_pid": session_pid},
        )
    ).line
    completion_intent = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 2),
            ts="2026-09-01T00:01:00.000Z",
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_COMPLETION,
            phase=Phase.INTENT,
            payload={
                "verdict": completion_verdict,
                "stop_reason": "external-operator-stop",
            },
        )
    ).line
    completion_outcome = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 3),
            ts="2026-09-01T00:01:01.000Z",
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_COMPLETION,
            phase=Phase.OUTCOME,
            intent_id=JournalEntryId("w", 2),
            payload={"verdict": completion_verdict, "stop_reason": "external-operator-stop", "ok": True},
        )
    ).line
    (run_dir / "journal.jsonl").write_text(
        intent + "\n" + launch_outcome + "\n" + completion_intent + "\n" + completion_outcome + "\n",
        encoding="utf-8",
    )
    return run_dir


class FakeFs:
    def read_text(self, path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return None


class FakeVcs:
    def __init__(self, repo_root: Path, *, head_sha: str = "bbb222") -> None:
        self.repo_root = repo_root
        self.head_sha = head_sha

    def changed_files(self, repo_root: Path, worktree_path: Path, *, base: str):
        return ("src/changed.py",)

    def is_branch_merged(self, repo_root: Path, branch: str, *, into: str) -> bool:
        return False

    def commit_subjects(self, repo_root: Path, ref: str):
        return ()

    def worktree_head_sha(self, worktree_path: Path) -> str:
        return self.head_sha

    def worktree_unified_patch(self, worktree_path: Path, *, baseline_sha: str) -> str:
        return "--- a/x\n+++ b/x\n+line1\n-line0\n"

    def branch_exists(self, repo_root: Path, branch: str) -> bool:
        return False

    def worktree_path_for_branch(self, repo_root: Path, branch: str) -> Path | None:
        return None


class FakeProcess:
    def __init__(self, *, alive: bool = False) -> None:
        self.alive = alive

    def is_alive(self, _pid: int) -> bool:
        return self.alive


def test_externally_stopped_story_not_blocked_for_drain(tmp_path: Path) -> None:
    from pyforge.marshal.cli.dispatch import _compose_policy

    slug = "pyforge-marshal"
    _seed_dispatch_journal_with_completion(
        tmp_path,
        slug=slug,
        run_id="run-ext-stop",
        story_key="28.13",
        completion_verdict=DispatchSessionVerdict.STOPPED_EXTERNALLY.value,
    )
    blocked = station_story_blocked_evidence(
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        process=FakeProcess(alive=False),
        repo_root=tmp_path,
        slug=slug,
        story_key="28-13-sanctioned-retry",
        effective_policy=_compose_policy(slug),
    )
    assert blocked is None


def test_dead_dirty_worktree_does_not_refuse_redispatch_when_externally_stopped(
    tmp_path: Path,
) -> None:
    from pyforge.marshal.cli.dispatch import _compose_policy

    slug = "pyforge-marshal"
    run_dir = _seed_dispatch_journal_with_completion(
        tmp_path,
        slug=slug,
        run_id="run-ext-stop",
        story_key="28.13",
        completion_verdict=DispatchSessionVerdict.STOPPED_EXTERNALLY.value,
    )
    fs = FakeFs()
    journal = gather_dispatch_journal_facts(fs, run_dir, run_dir.name)
    verdict = resolve_dispatch_session_verdict(
        fs=fs,
        vcs=FakeVcs(tmp_path),
        process=FakeProcess(alive=False),
        repo_root=tmp_path,
        slug=slug,
        journal=journal,
        effective_policy=_compose_policy(slug),
        run_dir=run_dir,
    )
    assert verdict is DispatchSessionVerdict.STOPPED_EXTERNALLY
    conflict = station_in_flight_conflict(
        fs=fs,
        vcs=FakeVcs(tmp_path),
        process=FakeProcess(alive=False),
        repo_root=tmp_path,
        slug=slug,
        story_key="28.13",
        effective_policy=_compose_policy(slug),
    )
    assert conflict is None


def test_live_session_still_refuses_redispatch(tmp_path: Path) -> None:
    from pyforge.marshal.cli.dispatch import _compose_policy

    slug = "pyforge-marshal"
    run_dir = dispatch_core.dispatch_run_dir(tmp_path, slug, "run-live")
    run_dir.mkdir(parents=True, exist_ok=True)
    intent = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 0),
            ts="2026-09-01T00:00:00.000Z",
            run_id="run-live",
            kind=dispatch_core.KIND_DISPATCH_LAUNCH,
            phase=Phase.INTENT,
            payload={
                "story_key": "28.13",
                "worktree_path": str(tmp_path / "wt"),
                "baseline_head_sha": "aaa111",
            },
        )
    ).line
    outcome = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 1),
            ts="2026-09-01T00:00:01.000Z",
            run_id="run-live",
            kind=dispatch_core.KIND_DISPATCH_LAUNCH,
            phase=Phase.OUTCOME,
            intent_id=JournalEntryId("w", 0),
            payload={"session_pid": 99},
        )
    ).line
    (run_dir / "journal.jsonl").write_text(intent + "\n" + outcome + "\n", encoding="utf-8")

    conflict = station_in_flight_conflict(
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        process=FakeProcess(alive=True),
        repo_root=tmp_path,
        slug=slug,
        story_key="28.13",
        effective_policy=_compose_policy(slug),
    )
    assert conflict is not None
    assert conflict.code == "MRS-DISP-011"


def test_surface_worktree_wip_reports_file_and_line_counts(tmp_path: Path) -> None:
    wt = tmp_path / "wt"
    wt.mkdir()
    finding = _surface_worktree_wip_before_dispatch(
        vcs=FakeVcs(tmp_path),
        repo_root=tmp_path,
        worktree=wt,
        baseline_head_sha="aaa111",
    )
    assert finding is not None
    assert finding.code == "MRS-DISP-036"
    assert "1 changed file" in finding.message
    assert "2 diff line" in finding.message


class _EmptyChangedFilesVcs(FakeVcs):
    def changed_files(self, repo_root: Path, worktree_path: Path, *, base: str):
        return ()


class _ChangedFilesErrorVcs(FakeVcs):
    def changed_files(self, repo_root: Path, worktree_path: Path, *, base: str):
        raise VcsCommandError("git diff --name-only failed")


class _UnifiedPatchErrorVcs(FakeVcs):
    def worktree_unified_patch(self, worktree_path: Path, *, baseline_sha: str) -> str:
        raise VcsCommandError("git diff failed")


def test_surface_worktree_wip_returns_none_when_no_changed_files(tmp_path: Path) -> None:
    wt = tmp_path / "wt"
    wt.mkdir()
    assert (
        _surface_worktree_wip_before_dispatch(
            vcs=_EmptyChangedFilesVcs(tmp_path),
            repo_root=tmp_path,
            worktree=wt,
            baseline_head_sha="aaa111",
        )
        is None
    )


def test_surface_worktree_wip_returns_none_when_changed_files_errors(tmp_path: Path) -> None:
    wt = tmp_path / "wt"
    wt.mkdir()
    assert (
        _surface_worktree_wip_before_dispatch(
            vcs=_ChangedFilesErrorVcs(tmp_path),
            repo_root=tmp_path,
            worktree=wt,
            baseline_head_sha="aaa111",
        )
        is None
    )


def test_surface_worktree_wip_reports_unavailable_line_count_when_patch_errors(
    tmp_path: Path,
) -> None:
    wt = tmp_path / "wt"
    wt.mkdir()
    finding = _surface_worktree_wip_before_dispatch(
        vcs=_UnifiedPatchErrorVcs(tmp_path),
        repo_root=tmp_path,
        worktree=wt,
        baseline_head_sha="aaa111",
    )
    assert finding is not None
    assert "1 changed file" in finding.message
    assert "diff line count unavailable" in finding.message


def test_policy_flags_from_harness_arg_none_returns_empty() -> None:
    assert _policy_flags_from_harness_arg(None) == {}


def test_policy_flags_from_harness_arg_blank_returns_empty() -> None:
    assert _policy_flags_from_harness_arg("   ") == {}


def test_policy_flags_from_harness_arg_single_profile() -> None:
    assert _policy_flags_from_harness_arg("claude") == {"harness_preference": ("claude",)}


def test_policy_flags_from_harness_arg_multiple_profiles_trims_whitespace() -> None:
    assert _policy_flags_from_harness_arg("cursor, claude ,  gemini") == {
        "harness_preference": ("cursor", "claude", "gemini")
    }


def test_policy_flags_from_harness_arg_ignores_empty_segments() -> None:
    assert _policy_flags_from_harness_arg("claude,,gemini") == {"harness_preference": ("claude", "gemini")}


def test_epics_path_lands_under_planning_artifacts(tmp_path: Path) -> None:
    from pyforge.marshal.cli.dispatch import _epics_path

    path = _epics_path(tmp_path, "pyforge-marshal")
    assert path == (tmp_path / "_bmad-output" / "projects" / "pyforge-marshal" / "planning-artifacts" / "epics.md")


def test_load_station_deps_graph_returns_empty_when_epics_missing(tmp_path: Path) -> None:
    from pyforge.marshal.cli.dispatch import _load_station_deps_graph

    assert _load_station_deps_graph(tmp_path, "pyforge-marshal") == {}


def test_load_station_deps_graph_parses_real_epics_file(tmp_path: Path) -> None:
    from pyforge.marshal.cli.dispatch import _epics_path, _load_station_deps_graph
    from pyforge.marshal.core.identity import StoryKey

    epics = _epics_path(tmp_path, "pyforge-marshal")
    epics.parent.mkdir(parents=True)
    epics.write_text(
        "### Story 1.1: Foo\n**Deps:** —\n\n### Story 1.2: Bar\n**Deps:** S-1.1\n",
        encoding="utf-8",
    )
    graph = _load_station_deps_graph(tmp_path, "pyforge-marshal")
    assert graph.get("1.2") == (StoryKey(1, 1),)


def test_resolve_max_parallel_cli_override_wins() -> None:
    from pyforge.marshal.cli.dispatch import _compose_policy, resolve_max_parallel

    effective = _compose_policy("pyforge-marshal")
    assert resolve_max_parallel(effective, cli_override=3) == 3


def test_resolve_max_parallel_cli_override_floors_at_one() -> None:
    from pyforge.marshal.cli.dispatch import _compose_policy, resolve_max_parallel

    effective = _compose_policy("pyforge-marshal")
    assert resolve_max_parallel(effective, cli_override=0) == 1


def test_resolve_max_parallel_policy_flag_wins_over_default() -> None:
    from pyforge.marshal.cli.dispatch import _compose_policy, resolve_max_parallel

    effective = _compose_policy("pyforge-marshal", flags={"dispatch": {"max_parallel": 4}})
    assert resolve_max_parallel(effective) == 4


def test_resolve_max_parallel_defaults_from_effective_policy() -> None:
    from pyforge.marshal.cli.dispatch import _compose_policy, resolve_max_parallel

    effective = _compose_policy("pyforge-marshal")
    assert resolve_max_parallel(effective) == int(effective.dispatch.value["max_parallel"])
