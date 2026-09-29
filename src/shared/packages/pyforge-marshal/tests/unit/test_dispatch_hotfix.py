"""Unit tests for dispatch hotfix modules (2026-09-01)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.marshal.core import dispatch as dispatch_core
from pyforge.marshal.core import dispatch_re_preflight as re_preflight
from pyforge.marshal.core import harness_session
from pyforge.marshal.core.dispatch_completion import DispatchGitFacts
from pyforge.marshal.core.dispatch_retry import (
    DispatchBlockKind,
    classify_dispatch_block,
    exclude_harness_profiles_after_transient_failure,
    prune_blocked_stories_merged_on_main,
)
from pyforge.marshal.core.dispatch_supervisor_state import (
    should_retry_stuck_land,
    should_terminalize_verify_refusal,
    supervisor_should_exit,
)
from pyforge.marshal.core.gate import widen_effective_surface_with_paths
from pyforge.marshal.core.harness_session import (
    HarnessSessionOutcome,
    classify_session_log,
)


def test_classify_session_log_quota() -> None:
    log = "Error: monthly spend limit reached for this workspace"
    assert classify_session_log(log) is HarnessSessionOutcome.QUOTA_EXCEEDED


# Real fixture: pyforge-herald-20260918T132400673Z-194af3a0/session.log
# (Story 50.2, spec-pyforge-marshal CAP-245). `classify_session_log`
# returned `unknown` for this exact text until the Cursor markers landed,
# so the drain refused story 23.1 as terminal until a human re-dispatched it.
_CURSOR_USAGE_WALL_LOG = (
    "ActionRequiredError: Increase limits for faster responses "
    "You're out of usage. Switch to Auto, or ask your admin to increase "
    "your limit to continue."
)


def test_classify_session_log_quota_cursor_usage_wall() -> None:
    assert classify_session_log(_CURSOR_USAGE_WALL_LOG) is HarnessSessionOutcome.QUOTA_EXCEEDED


def test_transient_block_on_cursor_usage_wall_with_no_git_progress() -> None:
    kind = classify_dispatch_block(
        session_log=_CURSOR_USAGE_WALL_LOG,
        failed_gate=None,
        changed_path_count=0,
    )
    assert kind is DispatchBlockKind.TRANSIENT


def test_exclude_harness_after_cursor_usage_wall() -> None:
    preference = ("cursor", "claude", "copilot")
    result = exclude_harness_profiles_after_transient_failure(preference, _CURSOR_USAGE_WALL_LOG)
    assert result == ("claude", "copilot")


def test_classify_session_log_reterminalizes_without_cursor_markers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mutation test: removing the Cursor markers reproduces the original
    Story 50.2 defect (the fixture goes back to ``unknown``)."""
    monkeypatch.setattr(
        harness_session,
        "_QUOTA_MARKERS",
        harness_session._QUOTA_MARKERS_BY_HARNESS["claude"],
    )
    assert classify_session_log(_CURSOR_USAGE_WALL_LOG) is HarnessSessionOutcome.UNKNOWN


def test_classify_session_log_auth() -> None:
    log = "cursor: not logged in — run cursor auth login"
    assert classify_session_log(log) is HarnessSessionOutcome.AUTH_FAILURE


def test_classify_session_log_harness_model_mismatch() -> None:
    log = "Cannot use this model: haiku. Available models: auto, gpt-5.3-codex"
    assert classify_session_log(log) is HarnessSessionOutcome.HARNESS_MISCONFIG


def test_transient_block_on_model_mismatch() -> None:
    kind = classify_dispatch_block(
        session_log="Cannot use this model: haiku",
        failed_gate=None,
        changed_path_count=0,
    )
    assert kind is DispatchBlockKind.TRANSIENT


def test_transient_block_on_quota_with_no_git_progress() -> None:
    kind = classify_dispatch_block(
        session_log="monthly spend limit exceeded",
        failed_gate=None,
        changed_path_count=0,
    )
    assert kind is DispatchBlockKind.TRANSIENT


def test_terminal_block_on_scope_gate() -> None:
    kind = classify_dispatch_block(
        session_log="",
        failed_gate="MRS-GATE-007",
        changed_path_count=3,
    )
    assert kind is DispatchBlockKind.TERMINAL


def test_transient_block_on_verify_gate() -> None:
    kind = classify_dispatch_block(
        session_log="tests failed",
        failed_gate="MRS-GATE-001",
        changed_path_count=5,
    )
    assert kind is DispatchBlockKind.TRANSIENT


def test_terminal_block_on_pre_existing_gate() -> None:
    kind = classify_dispatch_block(
        session_log="",
        failed_gate="MRS-GATE-014",
        changed_path_count=3,
    )
    assert kind is DispatchBlockKind.TERMINAL


def test_exclude_harness_after_quota_failure() -> None:
    preference = ("claude", "cursor", "copilot")
    result = exclude_harness_profiles_after_transient_failure(preference, "monthly spend limit hit")
    assert result == ("cursor", "copilot")


def test_exclude_harness_keeps_preference_on_success_log() -> None:
    preference = ("claude", "cursor")
    result = exclude_harness_profiles_after_transient_failure(preference, "story complete, all tests green")
    assert result == preference


def test_prune_blocked_stories_merged_on_main() -> None:
    blocked = {
        "28-7-done": "verify failed",
        "28-8-stuck": "verify failed",
    }
    pruned = prune_blocked_stories_merged_on_main(
        blocked,
        merged_story_keys=frozenset({"28-7-done"}),
    )
    assert pruned == {"28-8-stuck": "verify failed"}


def test_should_retry_stuck_land_after_threshold() -> None:
    assert should_retry_stuck_land(
        verification_verdict="verified",
        story_merged_on_main=False,
        landing_journaled=False,
        stuck_land_ticks=5,
    )


def test_should_not_retry_stuck_land_when_merged() -> None:
    assert not should_retry_stuck_land(
        verification_verdict="verified",
        story_merged_on_main=True,
        landing_journaled=False,
        stuck_land_ticks=10,
    )


def test_supervisor_should_exit_on_completed() -> None:
    assert supervisor_should_exit(
        completion_verdict="completed",
        story_merged_on_main=False,
    )


def test_supervisor_should_exit_when_merged() -> None:
    assert supervisor_should_exit(
        completion_verdict="live",
        story_merged_on_main=True,
    )


def test_widen_effective_surface_with_paths() -> None:
    surface = ("src/**",)
    widened = widen_effective_surface_with_paths(surface, ("src/foo/bar.py", "docs/readme.md"))
    assert "src/foo/bar.py" in widened
    assert "docs/readme.md" in widened
    assert "src/**" in widened


def _git_facts(*, baseline: str = "aaa", current: str = "bbb") -> DispatchGitFacts:
    return DispatchGitFacts(
        baseline_head_sha=baseline,
        current_head_sha=current,
        changed_paths=(),
        branch_merged=False,
        story_merged_on_main=False,
    )


def test_terminalize_verify_refusal_when_dead_session_and_refused() -> None:
    assert should_terminalize_verify_refusal(
        session_alive=False,
        verification_verdict="refused",
        git=_git_facts(),
    )


def test_no_terminalize_while_session_alive() -> None:
    assert not should_terminalize_verify_refusal(
        session_alive=True,
        verification_verdict="refused",
        git=_git_facts(),
    )


def test_no_terminalize_when_verify_still_pending() -> None:
    assert not should_terminalize_verify_refusal(
        session_alive=False,
        verification_verdict=None,
        git=_git_facts(),
    )


def test_no_terminalize_when_verify_passed() -> None:
    assert not should_terminalize_verify_refusal(
        session_alive=False,
        verification_verdict="verified",
        git=_git_facts(),
    )


def test_no_terminalize_without_git_progress() -> None:
    assert not should_terminalize_verify_refusal(
        session_alive=False,
        verification_verdict="refused",
        git=_git_facts(baseline="same", current="same"),
    )


def test_spec_fingerprint_missing_when_no_spec(tmp_path: Path) -> None:
    slug = "pyforge-marshal"
    (tmp_path / "_bmad-output" / "projects" / slug / "planning-artifacts" / "specs").mkdir(parents=True)
    assert re_preflight.spec_fingerprint(tmp_path, slug, "22-7-fleet") == "spec:missing"


def test_spec_fingerprint_changes_when_spec_lands(tmp_path: Path) -> None:
    slug = "pyforge-marshal"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True)
    before = re_preflight.spec_fingerprint(tmp_path, slug, "22-7-fleet")
    (specs / "spec-22-7-fleet.md").write_text("---\ndifficulty: medium\n---\n")
    after = re_preflight.spec_fingerprint(tmp_path, slug, "22-7-fleet")
    assert before == "spec:missing"
    assert after.startswith("spec:spec-22-7-fleet.md:")


def test_reconcile_clears_missing_spec_block_when_spec_appears(tmp_path: Path) -> None:
    slug = "pyforge-marshal"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True)
    detail = f"MRS-DISP-005: no tracked spec found for story '22.7' under {specs!r}"
    prior = re_preflight.RefusePredicate(
        gate="MRS-DISP-005",
        spec_fingerprint="spec:missing",
        verify_fingerprint=re_preflight.verify_commands_fingerprint(()),
    )
    (specs / "spec-22-7-fleet.md").write_text("---\ndifficulty: medium\n---\n")
    kept, results = re_preflight.reconcile_station_re_preflight(
        repo_root=tmp_path,
        slug=slug,
        blocked={"22-7-fleet": detail},
        verify_commands=(),
        prior_predicates={"22-7-fleet": prior},
    )
    assert kept == {}
    assert len(results) == 1
    assert results[0].decision is re_preflight.RePreflightDecision.CLEARED


def test_reconcile_rate_limits_when_spec_becomes_unreadable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing→unreadable must not clear MRS-DISP-005 — refuse still applies."""
    slug = "pyforge-marshal"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True)
    detail = "MRS-DISP-005: no tracked spec found for story '22.7'"
    prior = re_preflight.RefusePredicate(
        gate="MRS-DISP-005",
        spec_fingerprint="spec:missing",
        verify_fingerprint=re_preflight.verify_commands_fingerprint(()),
    )
    spec_path = specs / "spec-22-7-fleet.md"
    spec_path.write_text("---\ndifficulty: medium\n---\n")

    def _fingerprint(repo_root: Path, slug_arg: str, story: str) -> str:
        try:
            spec_path.stat()
        except OSError:
            return "spec:unreadable"
        return "spec:unreadable"

    monkeypatch.setattr(re_preflight, "spec_fingerprint", _fingerprint)
    kept, results = re_preflight.reconcile_station_re_preflight(
        repo_root=tmp_path,
        slug=slug,
        blocked={"22-7-fleet": detail},
        verify_commands=(),
        prior_predicates={"22-7-fleet": prior},
    )
    assert "22-7-fleet" in kept
    assert results[0].decision is re_preflight.RePreflightDecision.RATE_LIMITED


def test_reconcile_rate_limits_unreadable_spec_predicate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    slug = "pyforge-marshal"
    dispatch_core.planning_specs_dir(tmp_path, slug).mkdir(parents=True)
    detail = "MRS-DISP-005: no tracked spec found for story '22.7'"
    prior = re_preflight.RefusePredicate(
        gate="MRS-DISP-005",
        spec_fingerprint="spec:unreadable",
        verify_fingerprint=re_preflight.verify_commands_fingerprint(()),
    )
    monkeypatch.setattr(
        re_preflight,
        "spec_fingerprint",
        lambda *args, **kwargs: "spec:unreadable",
    )
    kept, results = re_preflight.reconcile_station_re_preflight(
        repo_root=tmp_path,
        slug=slug,
        blocked={"22-7-fleet": detail},
        verify_commands=(),
        prior_predicates={"22-7-fleet": prior},
    )
    assert "22-7-fleet" in kept
    assert results[0].decision is re_preflight.RePreflightDecision.RATE_LIMITED


def test_refuse_still_applies_treats_unreadable_like_missing() -> None:
    predicate = re_preflight.RefusePredicate(
        gate="MRS-DISP-005",
        spec_fingerprint="spec:unreadable",
        verify_fingerprint=re_preflight.verify_commands_fingerprint(()),
    )
    assert re_preflight.refuse_still_applies(predicate=predicate, gate="MRS-DISP-005")


def test_reconcile_rate_limits_unchanged_missing_spec_predicate(tmp_path: Path) -> None:
    slug = "pyforge-marshal"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True)
    detail = "MRS-DISP-005: no tracked spec found for story '22.7'"
    prior = re_preflight.compute_refuse_predicate(
        repo_root=tmp_path,
        slug=slug,
        story="22-7-fleet",
        gate="MRS-DISP-005",
        verify_commands=(),
    )
    kept, results = re_preflight.reconcile_station_re_preflight(
        repo_root=tmp_path,
        slug=slug,
        blocked={"22-7-fleet": detail},
        verify_commands=(),
        prior_predicates={"22-7-fleet": prior},
    )
    assert "22-7-fleet" in kept
    assert results[0].decision is re_preflight.RePreflightDecision.RATE_LIMITED


def test_reconcile_rate_limits_verify_refuse_when_only_spec_changes(
    tmp_path: Path,
) -> None:
    slug = "pyforge-marshal"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True)
    detail = "MRS-GATE-001: verify failed"
    verify_cmds = ("pytest -q",)
    prior = re_preflight.compute_refuse_predicate(
        repo_root=tmp_path,
        slug=slug,
        story="22-7-fleet",
        gate="MRS-GATE-001",
        verify_commands=verify_cmds,
    )
    (specs / "spec-22-7-fleet.md").write_text("---\ndifficulty: medium\n---\n")
    kept, results = re_preflight.reconcile_station_re_preflight(
        repo_root=tmp_path,
        slug=slug,
        blocked={"22-7-fleet": detail},
        verify_commands=verify_cmds,
        prior_predicates={"22-7-fleet": prior},
    )
    assert "22-7-fleet" in kept
    assert results[0].decision is re_preflight.RePreflightDecision.RATE_LIMITED


def test_reconcile_clears_verify_refuse_when_verify_config_changes(
    tmp_path: Path,
) -> None:
    slug = "pyforge-marshal"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True)
    detail = "MRS-GATE-001: verify failed"
    prior = re_preflight.compute_refuse_predicate(
        repo_root=tmp_path,
        slug=slug,
        story="22-7-fleet",
        gate="MRS-GATE-001",
        verify_commands=("pytest -q",),
    )
    kept, results = re_preflight.reconcile_station_re_preflight(
        repo_root=tmp_path,
        slug=slug,
        blocked={"22-7-fleet": detail},
        verify_commands=("ruff check .",),
        prior_predicates={"22-7-fleet": prior},
    )
    assert kept == {}
    assert results[0].decision is re_preflight.RePreflightDecision.CLEARED


def test_verify_rerun_needed_only_when_verify_fingerprint_changes() -> None:
    prior = re_preflight.RefusePredicate(
        gate="MRS-GATE-001",
        spec_fingerprint="spec:missing",
        verify_fingerprint=re_preflight.verify_commands_fingerprint(("pytest -q",)),
    )
    same_verify = re_preflight.RefusePredicate(
        gate="MRS-GATE-001",
        spec_fingerprint="spec:spec-22-7-fleet.md:1:10",
        verify_fingerprint=re_preflight.verify_commands_fingerprint(("pytest -q",)),
    )
    changed_verify = re_preflight.RefusePredicate(
        gate="MRS-GATE-001",
        spec_fingerprint="spec:spec-22-7-fleet.md:1:10",
        verify_fingerprint=re_preflight.verify_commands_fingerprint(("ruff check .",)),
    )
    assert not re_preflight.verify_rerun_needed(prior=prior, current=same_verify)
    assert re_preflight.verify_rerun_needed(prior=prior, current=changed_verify)


def test_expected_story_spec_glob_names_the_tracked_specs_path(tmp_path: Path) -> None:
    slug = "pyforge-marshal"
    glob = dispatch_core.expected_story_spec_glob(tmp_path, slug, "22.7")
    assert glob is not None
    assert glob.endswith("/planning-artifacts/specs/spec-22-7-*.md")


def test_gather_fleet_missing_spec_escalations_reads_latest_campaign(
    tmp_path: Path,
) -> None:
    """Story 28.19: MRS-DISP-005 campaign blocks surface with expected spec glob."""
    from pyforge.marshal.adapters.fs_local import LocalFs
    from pyforge.marshal.cli.dispatch import (
        FleetCycleReport,
        _journal_fleet_cycle,
        gather_fleet_missing_spec_escalations,
    )
    from pyforge.marshal.core import dispatch_fleet
    from pyforge.marshal.core.dispatch_fleet import StationCycleStatus

    slug = "pyforge-marshal"
    (tmp_path / "_bmad-output" / "projects" / slug).mkdir(parents=True)
    dispatch_core.planning_specs_dir(tmp_path, slug).mkdir(parents=True)
    run_dir = dispatch_fleet.fleet_run_dir(tmp_path, "camp-28-19")
    run_dir.mkdir(parents=True)
    detail = (
        "MRS-DISP-005: no tracked spec found for story '22.7' "
        f"under {dispatch_core.planning_specs_dir(tmp_path, slug)!r}"
    )
    report = FleetCycleReport(
        results=(
            dispatch_fleet.StationCycleResult(
                slug=slug,
                status=StationCycleStatus.REFUSED,
                remaining=1,
                story="22.7",
                detail=detail,
            ),
        ),
        findings=(),
        data={"mode": "drain_to_zero"},
    )
    fs = LocalFs()
    _journal_fleet_cycle(fs, run_dir, "camp-28-19", report, [])

    class _Harness:
        def ledger_story_statuses(self, path: Path) -> tuple[tuple[str, str], ...]:
            return (("22-7-fleet", "backlog"),)

    class _Vcs:
        """Story 51.9: simulates a clean, unmoved local `main` so this test
        keeps exercising the local `HarnessPort` read it always has --
        `tmp_path` isn't a real git repo, so this must never fall through
        to the new `origin/main` read path."""

        def has_uncommitted_changes(self, worktree_path: Path) -> bool:
            return False

        def worktree_head_sha(self, worktree_path: Path) -> str:
            return "same-sha"

        def resolve_ref(self, repo_root: Path, ref: str) -> str:
            return "same-sha"

    escalations = gather_fleet_missing_spec_escalations(
        fs=fs,
        harness=_Harness(),
        vcs=_Vcs(),
        repo_root=tmp_path,
    )
    assert slug in escalations
    assert escalations[slug].story == "22.7"
    assert escalations[slug].expected_spec_glob.endswith("spec-22-7-*.md")
