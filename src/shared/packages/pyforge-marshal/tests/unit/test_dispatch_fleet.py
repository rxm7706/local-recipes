"""Unit tests for Story 22.7 — fleet-wide drain as a marshal-orchestrated mode.

Two layers:

* the pure planning core (``core/dispatch_fleet.py``) — campaign modes,
  ledger-derived backlogs, order overrides, the per-cycle queue decision;
* the driver (``cli/dispatch.py::execute_fleet_cycle`` / ``run_fleet_drain``)
  replaying every row of the story spec's I/O & Edge-Case Matrix, i.e. the
  2026-08-22/23 eight-station campaign's outcomes without session discipline.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import pytest
from pyforge.core.process import ProcessResult

from pyforge.marshal.adapters.fs_local import FsError
from pyforge.marshal.adapters.harness_bmadloop import HarnessError
from pyforge.marshal.adapters.vcs_git import VcsCommandError
from pyforge.marshal.cli.dispatch import (
    execute_fleet_cycle,
    run_fleet_drain,
)
from pyforge.marshal.core import dispatch as dispatch_core
from pyforge.marshal.core import dispatch_fleet
from pyforge.marshal.core.dispatch_fleet import (
    ALREADY_LANDED_ADVANCE_PREFIX,
    HARNESS_DONE_ADVANCE_CODE,
    FleetBlockClass,
    FleetCampaignMode,
    InvalidCampaignModeError,
    ParsedStoryDeps,
    StationCycleStatus,
    StationQueueOutcome,
    apply_order_override,
    classify_fleet_block,
    dependency_ordered_backlog,
    explicit_story_backlog,
    has_review_verify_cycle_evidence,
    is_advance_reason,
    is_already_landed_self_refusal,
    is_finalize_pending,
    parse_campaign_mode,
    parse_epics_dependencies,
    plan_station_queue,
    station_backlog,
)
from pyforge.marshal.core.identity import StoryKey
from pyforge.marshal.core.journal import (
    JournalEntryId,
    Phase,
    build_entry,
    prepare_for_write,
)
from pyforge.marshal.core.model import Severity
from pyforge.marshal.core.verdict import EXIT_OK
from pyforge.marshal.ports.build_harness import (
    DispatchLaunchResult,
    HarnessCandidateSkip,
    HarnessResolution,
)
from pyforge.marshal.ports.fs import AdvisoryLock

# --------------------------------------------------------------------------
# Pure planning core
# --------------------------------------------------------------------------


def test_missing_campaign_mode_is_refused_never_defaulted() -> None:
    with pytest.raises(InvalidCampaignModeError) as excinfo:
        parse_campaign_mode(None)
    assert "drain_to_zero" in str(excinfo.value)
    with pytest.raises(InvalidCampaignModeError):
        parse_campaign_mode("   ")


def test_unknown_campaign_mode_names_the_invalid_value() -> None:
    with pytest.raises(InvalidCampaignModeError) as excinfo:
        parse_campaign_mode("drain_everything")
    assert "drain_everything" in str(excinfo.value)


@pytest.mark.parametrize("raw", dispatch_fleet.CAMPAIGN_MODES)
def test_every_named_mode_parses(raw: str) -> None:
    assert parse_campaign_mode(raw).value == raw


def test_station_backlog_drops_done_and_malformed_keys() -> None:
    statuses = (
        ("1-1-shipped", "done"),
        ("2-1-queued", "backlog"),
        ("not-a-story-key", "backlog"),
        ("10-1-later", "review"),
        ("3-1-ready", "in-progress"),
        ("4-6-held", "blocked"),
    )
    assert station_backlog(statuses) == ("2-1-queued", "3-1-ready")


def test_station_backlog_orders_by_story_key_not_lexicographically() -> None:
    # The interim runner's plain sorted() put "10-1-…" ahead of "2-1-…".
    statuses = (("10-1-later", "backlog"), ("2-1-earlier", "backlog"))
    assert station_backlog(statuses) == ("2-1-earlier", "10-1-later")


def test_order_override_wins_then_remaining_keys_follow() -> None:
    backlog = ("2-1-a", "3-1-b", "4-1-c")
    assert apply_order_override(backlog, ["4-1-c", "9-9-absent"]) == (
        "4-1-c",
        "2-1-a",
        "3-1-b",
    )


def test_empty_backlog_plans_as_drained() -> None:
    plan = plan_station_queue(slug="pyforge-mason", backlog=(), mode=FleetCampaignMode.DRAIN_TO_ZERO)
    assert plan.outcome is StationQueueOutcome.DRAINED
    assert plan.next_story is None


def test_leave_one_stops_at_the_configured_tail() -> None:
    plan = plan_station_queue(
        slug="pyforge-mason",
        backlog=("2-1-a",),
        mode=FleetCampaignMode.LEAVE_ONE,
        leave_remaining=1,
    )
    assert plan.outcome is StationQueueOutcome.LEFT_REMAINING
    assert plan.next_story is None
    deeper = plan_station_queue(
        slug="pyforge-mason",
        backlog=("2-1-a", "2-2-b"),
        mode=FleetCampaignMode.LEAVE_ONE,
        leave_remaining=1,
    )
    assert deeper.outcome is StationQueueOutcome.DISPATCH
    assert deeper.next_story == "2-1-a"


def test_classify_fleet_block_environment_when_no_progress_or_verify_evidence() -> None:
    assert classify_fleet_block(changed_path_count=0, has_review_verify_evidence=False) is FleetBlockClass.ENVIRONMENT
    assert classify_fleet_block(changed_path_count=2, has_review_verify_evidence=False) is FleetBlockClass.STORY
    assert (
        classify_fleet_block(
            changed_path_count=0,
            has_review_verify_evidence=has_review_verify_cycle_evidence(
                verification_verdict="failed",
                verification_failed_gate=None,
                completion_stop_reason=None,
            ),
        )
        is FleetBlockClass.STORY
    )


def test_skip_on_blocked_skips_environment_blocks_only() -> None:
    plan = plan_station_queue(
        slug="pyforge-steward",
        backlog=("12-7-live-ocp", "12-8-github-projects"),
        mode=FleetCampaignMode.SKIP_ON_BLOCKED,
        blocked={"12-7-live-ocp": "needs a live OCP cluster"},
        block_classes={"12-7-live-ocp": FleetBlockClass.ENVIRONMENT},
    )
    assert plan.outcome is StationQueueOutcome.DISPATCH
    assert plan.next_story == "12-8-github-projects"
    assert plan.skipped == (("12-7-live-ocp", "needs a live OCP cluster"),)
    # The blocked story is never removed from the backlog.
    assert "12-7-live-ocp" in plan.backlog


def test_skip_on_blocked_stops_at_story_classified_blocks() -> None:
    plan = plan_station_queue(
        slug="pyforge-marshal",
        backlog=("34-3-crashed", "34-4-next"),
        mode=FleetCampaignMode.SKIP_ON_BLOCKED,
        blocked={"34-3-crashed": "verify failed"},
        block_classes={"34-3-crashed": FleetBlockClass.STORY},
    )
    assert plan.outcome is StationQueueOutcome.BLOCKED
    assert plan.blocked_story == "34-3-crashed"


def test_retry_environment_blocks_skips_under_drain_to_zero() -> None:
    plan = plan_station_queue(
        slug="pyforge-marshal",
        backlog=("34-3-crashed", "34-4-next"),
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        blocked={"34-3-crashed": "session died before progress"},
        block_classes={"34-3-crashed": FleetBlockClass.ENVIRONMENT},
        retry_environment_blocks=True,
    )
    assert plan.outcome is StationQueueOutcome.DISPATCH
    assert plan.next_story == "34-4-next"


def test_other_modes_stop_at_a_blocked_story_and_never_force_past_it() -> None:
    plan = plan_station_queue(
        slug="pyforge-steward",
        backlog=("12-7-live-ocp", "12-8-github-projects"),
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        blocked={"12-7-live-ocp": "needs a live OCP cluster"},
        block_classes={"12-7-live-ocp": FleetBlockClass.STORY},
    )
    assert plan.outcome is StationQueueOutcome.BLOCKED
    assert plan.blocked_story == "12-7-live-ocp"
    assert plan.next_story is None


def test_harness_done_040_is_skipped_under_drain_to_zero() -> None:
    """Harness-done CAP-4 (040) must not halt drain_to_zero on a ledger-stale head."""
    plan = plan_station_queue(
        slug="pyforge-steward",
        backlog=("43-4-landed-head", "43-5-next"),
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        blocked={"43-4-landed-head": ("MRS-DISP-040: awaiting-operator (skipped-unverified)")},
    )
    assert plan.outcome is StationQueueOutcome.DISPATCH
    assert plan.next_story == "43-5-next"
    assert plan.skipped[0][0] == "43-4-landed-head"
    assert "43-4-landed-head" in plan.backlog


def test_a_declared_skip_is_honored_under_every_mode() -> None:
    """The 2026-08-22/23 campaign ran ``mode: drain_to_zero`` WITH seven
    hand-authored steward ``skip_policies``. An operator's explicit "don't
    try this one" is not the same fact as derived HALT evidence: it is
    honored under every mode, or that campaign could not be replayed in the
    mode it actually ran."""
    for mode in FleetCampaignMode:
        plan = plan_station_queue(
            slug="pyforge-steward",
            backlog=("12-7-live-ocp", "12-8-github-projects"),
            mode=mode,
            leave_remaining=0,
            declared_skips={"12-7-live-ocp": "Live OCP/CRC."},
        )
        assert plan.outcome is StationQueueOutcome.DISPATCH, mode
        assert plan.next_story == "12-8-github-projects", mode
        assert plan.skipped == (("12-7-live-ocp", "Live OCP/CRC."),), mode
        # Never removed from the backlog, never auto-retried.
        assert "12-7-live-ocp" in plan.backlog


def test_a_declared_skip_never_masks_a_derived_block_on_a_later_story() -> None:
    plan = plan_station_queue(
        slug="pyforge-steward",
        backlog=("12-7-live-ocp", "12-8-github-projects"),
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        declared_skips={"12-7-live-ocp": "Live OCP/CRC."},
        blocked={"12-8-github-projects": "its last dispatch ended 'failed'"},
    )
    assert plan.outcome is StationQueueOutcome.BLOCKED
    assert plan.blocked_story == "12-8-github-projects"
    assert plan.skipped == (("12-7-live-ocp", "Live OCP/CRC."),)


def test_every_declared_skip_consumed_reports_all_skipped() -> None:
    plan = plan_station_queue(
        slug="pyforge-steward",
        backlog=("27-1-liquibase", "27-2-preupgrade"),
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        declared_skips={
            "27-1-liquibase": "Operator Liquibase >=5.0.4 feedstock.",
            "27-2-preupgrade": "Deps 27-1.",
        },
    )
    assert plan.outcome is StationQueueOutcome.ALL_SKIPPED
    assert plan.next_story is None
    assert len(plan.skipped) == 2


def test_fleet_station_slugs_are_derived_not_declared() -> None:
    slugs = dispatch_fleet.fleet_station_slugs(
        ("pyforge-atlas", "local-recipes", "pyforge-zzz-new-station", "deckcraft")
    )
    assert slugs == ("pyforge-atlas", "pyforge-zzz-new-station")


# --------------------------------------------------------------------------
# Story 22.11 — station-scoped drain + an explicit story sequence (CAP-10):
# the pure planning core
# --------------------------------------------------------------------------


def test_parse_story_sequence_splits_and_trims_dropping_blanks() -> None:
    assert dispatch_fleet.parse_story_sequence("22-11-a, 22-12-b ,,22-13-c") == (
        "22-11-a",
        "22-12-b",
        "22-13-c",
    )
    assert dispatch_fleet.parse_story_sequence("") == ()
    assert dispatch_fleet.parse_story_sequence(",  ,") == ()


def test_unresolved_story_sequence_keys_accepts_short_or_full_form() -> None:
    backlog = ("6-1-first-story", "6-2-second-story")
    # A caller may type either the bare feed key or the full tracked-ledger
    # slug -- both must resolve against the SAME normalized identity.
    assert dispatch_fleet.unresolved_story_sequence_keys(["6.1", "6-2-second-story"], backlog) == ()


def test_unresolved_story_sequence_keys_names_unknown_and_done_keys() -> None:
    # `backlog` already excludes `done` keys (station_backlog's job) -- a
    # caller-supplied key absent from it is either unknown or already done;
    # unresolved_story_sequence_keys doesn't need to distinguish the two.
    backlog = ("6-1-first-story",)
    assert dispatch_fleet.unresolved_story_sequence_keys(["6.1", "6.2", "not-a-key"], backlog) == ("6.2", "not-a-key")


def test_unresolved_story_sequence_keys_empty_when_every_key_is_eligible() -> None:
    backlog = ("6-1-a", "6-2-b", "6-3-c")
    assert dispatch_fleet.unresolved_story_sequence_keys(["6.3", "6.1"], backlog) == ()


def test_explicit_story_backlog_is_the_callers_own_order_not_the_ledgers() -> None:
    statuses = (
        ("6-1-a", "backlog"),
        ("6-2-b", "backlog"),
        ("6-3-c", "backlog"),
    )
    # The caller's own order (3, then 1) wins outright -- unlike
    # apply_order_override, the untouched tail (6-2-b) is NEVER appended.
    assert dispatch_fleet.explicit_story_backlog(statuses, ["6.3", "6.1"]) == (
        "6.3",
        "6.1",
    )


def test_explicit_story_backlog_drops_a_key_once_it_lands() -> None:
    statuses = (("6-1-a", "done"), ("6-2-b", "backlog"))
    assert dispatch_fleet.explicit_story_backlog(statuses, ["6.1", "6.2"]) == ("6.2",)


def test_explicit_story_backlog_skips_malformed_entries() -> None:
    statuses = (("6-1-a", "backlog"),)
    assert dispatch_fleet.explicit_story_backlog(statuses, ["not-a-key", "6.1"]) == ("6.1",)


# --------------------------------------------------------------------------
# Driver fakes
# --------------------------------------------------------------------------

_STATIONS = ("pyforge-marshal", "pyforge-doctor")


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "drain@test"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "config", "user.name", "drain"], cwd=path, check=True, capture_output=True)


class FakeFs:
    """Writes through to the real tree so run dirs stay discoverable."""

    def __init__(self, *, lock_unavailable: bool = False) -> None:
        self.files: dict[Path, str] = {}
        self.lock_unavailable = lock_unavailable
        self.locks_acquired: list[Path] = []
        self.locks_released: list[Path] = []

    def acquire_advisory_lock(self, path: Path, *, timeout_s: float) -> AdvisoryLock:
        if self.lock_unavailable:
            raise FsError(f"timed out after {timeout_s}s waiting for {path}")
        self.locks_acquired.append(path)
        return AdvisoryLock(path=path.with_suffix(path.suffix + ".lock"), handle=None)

    def release_advisory_lock(self, lock: AdvisoryLock) -> None:
        self.locks_released.append(lock.path)

    def is_dir(self, path: Path) -> bool:
        return path.is_dir()

    def ensure_dir(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)

    def create_dir_exclusive(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)

    def append_line(self, path: Path, line: str, *, fsync: bool) -> None:
        # LocalFs.append_line writes the line PLUS a trailing newline -- one
        # physical line per call. Mirroring that matters: without it every
        # journal entry concatenates onto one line and `fold` recovers
        # nothing, silently turning an in-flight run into "no run at all".
        assert "\n" not in line
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        self.files[path] = self.files.get(path, "") + line + "\n"

    def write_text_atomic(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self.files[path] = content

    def read_text(self, path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return None


class FakeVcs:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.head_sha = "baseline1234"
        self.progressed_worktrees: set[str] = set()
        self.merged_branches: set[str] = set()
        # Story 51.9 (re-mint of 51.3): default to "clean main" so every
        # pre-existing test in this file keeps reading the local
        # `HarnessPort` ledger unchanged; a test can flip `dirty=True`,
        # move `main_ref` away from `head_sha`, or stock
        # `remote_ledger_texts` to exercise the new `origin/main` fallback.
        self.dirty = False
        self.main_ref = self.head_sha
        self.remote_ledger_texts: dict[str, str] = {}
        # Review pass 2026-09-19 (VG1): record `fetch` calls so tests can
        # assert the local `origin/main` cache is refreshed before the
        # remote-read fallback trusts it.
        self.fetched: list[tuple[str, str]] = []

    def repo_common_root(self, _cwd: Path) -> Path:
        return self.repo_root

    def branch_exists(self, _repo_root: Path, _branch: str) -> bool:
        return False

    def worktree_path_for_branch(self, _repo_root: Path, _branch: str) -> Path | None:
        return None

    def add_worktree(self, repo_root: Path, home: Path, branch: str, *, base: str) -> None:
        home.mkdir(parents=True, exist_ok=True)

    def worktree_head_sha(self, worktree_path: Path) -> str:
        if str(worktree_path) in self.progressed_worktrees:
            return "progress9999"
        return self.head_sha

    def changed_files(self, repo_root: Path, worktree_path: Path, *, base: str):
        return ("src/changed.py",) if str(worktree_path) in self.progressed_worktrees else ()

    def is_branch_merged(self, repo_root: Path, branch: str, *, into: str) -> bool:
        return branch in self.merged_branches

    def commit_subjects(self, repo_root: Path, ref: str):
        return ()

    # Story 51.9 (re-mint of 51.3): the "is the primary safely a clean,
    # unmoved local `main`" gate + the `origin/main` ledger-text fallback.
    def has_uncommitted_changes(self, worktree_path: Path) -> bool:
        return self.dirty

    def resolve_ref(self, repo_root: Path, ref: str) -> str:
        return self.main_ref

    def file_text_at_ref(self, repo_root: Path, ref: str, path: str) -> str | None:
        return self.remote_ledger_texts.get(path)

    def fetch(self, repo_root: Path, remote: str, ref: str) -> None:
        self.fetched.append((remote, ref))


class FakeBuildHarness:
    def __init__(self, *, present: bool = True) -> None:
        self.present = present
        self.dispatched: list[tuple[str, str]] = []

    def binary_present(self, preference=(), repo_root=None) -> HarnessResolution:
        if not self.present:
            return HarnessResolution(
                profile=None,
                skipped=tuple(
                    HarnessCandidateSkip(profile=name, reason=f"binary {name!r} not found on PATH")
                    for name in preference
                ),
            )
        chosen = next(iter(preference), "claude")
        return HarnessResolution(profile=chosen, binary_path=f"/usr/bin/{chosen}")

    def dispatch(self, worktree: Path, **kwargs) -> DispatchLaunchResult:
        self.dispatched.append((kwargs["project_slug"], kwargs["story_key"]))
        resolution = kwargs.get("resolution")
        return DispatchLaunchResult(
            pid=7070,
            command=("cursor", "agent"),
            model=kwargs.get("model"),
            budget_env=dict(kwargs.get("budget_env") or {}),
            profile=resolution.profile if resolution is not None else None,
        )


class FakeProcess:
    def __init__(
        self,
        *,
        alive: bool = True,
        alive_pids: frozenset[int] | None = None,
        session_check_returncode: int = 0,
    ) -> None:
        self.alive = alive
        # Story 50.1: per-pid liveness. ``None`` keeps the flat ``alive``
        # behaviour every pre-existing fixture relies on byte-identical --
        # Part A is the first probe that needs a live supervisor pid
        # alongside a dead session pid in the SAME run.
        self.alive_pids = alive_pids
        self.spawned: list[list[str]] = []
        # Story 63.4: dispatch_once shells `steward session check --json`
        # right after repo_root resolves. Default 0 ("ok") keeps every
        # pre-existing fixture behaviour byte-identical -- no unexpected
        # MRS-DISP-049 finding unless a test opts in.
        self.session_check_returncode = session_check_returncode
        self.run_calls: list[list[str]] = []

    def is_alive(self, pid: int) -> bool:
        if self.alive_pids is None:
            return self.alive
        return pid in self.alive_pids

    def spawn_detached(self, argv, *, cwd: Path, log_path: Path) -> int:
        self.spawned.append(list(argv))
        return 7071

    def run(self, argv, *, cwd: Path, timeout_s: float | None = None) -> ProcessResult:
        self.run_calls.append(list(argv))
        return ProcessResult(returncode=self.session_check_returncode, stdout="", stderr="")


class FakeHarness:
    """``HarnessPort.ledger_story_statuses`` over an in-memory fleet ledger."""

    def __init__(self, ledgers: dict[str, tuple[tuple[str, str], ...]]) -> None:
        self.ledgers = ledgers
        # Story 22.11: which stations' ledgers were actually READ -- the
        # "provably untouched" assertion needs this, not just "not
        # dispatched" (a station could be read and still skipped).
        self.read_slugs: list[str] = []

    def ledger_story_statuses(self, path: Path) -> tuple[tuple[str, str], ...]:
        slug = path.parent.parent.name
        self.read_slugs.append(slug)
        if slug not in self.ledgers:
            raise HarnessError(f"cannot read ledger: no such file {path}")
        return self.ledgers[slug]


def _seed_fleet(tmp_path: Path, *, stories: dict[str, list[str]]) -> None:
    """Create each station's project dir and a tracked spec per story key."""
    for slug, keys in stories.items():
        (tmp_path / "_bmad-output" / "projects" / slug).mkdir(parents=True, exist_ok=True)
        specs = dispatch_core.planning_specs_dir(tmp_path, slug)
        specs.mkdir(parents=True, exist_ok=True)
        for key in keys:
            (specs / f"spec-{key}.md").write_text(
                '---\ndifficulty: medium\nsurface: ["src/%s/**"]\n---\n' % slug,
                encoding="utf-8",
            )


def _seed_live_dispatch_journal(
    tmp_path: Path,
    *,
    slug: str,
    run_id: str,
    story_key: str,
    session_pid: int = 42,
    baseline_head_sha: str = "aaa111",
) -> Path:
    """Seed a per-story dispatch journal.

    ``baseline_head_sha`` decides what CAP-2's own facts will say once the
    session process is gone: leave it different from ``FakeVcs.head_sha``
    (the default) and the run reads as LIVE-by-git-progress; pass the SAME
    sha and a dead session reads as FAILED -- the HALTed story this story's
    ``skip_on_blocked`` matrix row is about.
    """
    run_dir = dispatch_core.dispatch_run_dir(tmp_path, slug, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    intent = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 0),
            ts="2026-08-23T00:00:00.000Z",
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
    outcome = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 1),
            ts="2026-08-23T00:00:01.000Z",
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_LAUNCH,
            phase=Phase.OUTCOME,
            intent_id=JournalEntryId("w", 0),
            payload={"session_pid": session_pid},
        )
    ).line
    (run_dir / "journal.jsonl").write_text(intent + "\n" + outcome + "\n", encoding="utf-8")
    return run_dir


_CYCLE_POLICY_SERIAL: dict[str, object] = {"dispatch": {"max_parallel": 1}}
_CYCLE_POLICY_REAL = object()


def _cycle(
    tmp_path: Path,
    *,
    mode: FleetCampaignMode,
    ledgers: dict[str, tuple[tuple[str, str], ...]],
    vcs: FakeVcs | None = None,
    process: FakeProcess | None = None,
    build_harness: FakeBuildHarness | None = None,
    leave_remaining: int = 1,
    campaign_blocked: dict[str, dict[str, str]] | None = None,
    harness: FakeHarness | None = None,
    station: str | None = None,
    explicit_stories: tuple[str, ...] | None = None,
    policy_flags: dict[str, object] | None | object = _CYCLE_POLICY_REAL,
    retry_environment_blocks: bool = False,
):
    """Fleet-cycle helper.

    Default: force ``dispatch.max_parallel = 1`` so tests stay serial even
    when the tracked ``marshal-policy.toml`` enables waves (Story 33.8).
    Pass ``policy_flags=None`` to compose from the live project policy only.

    Also monkeypatches ``dispatch_once`` to point a real scope triangle at
    each dispatched slug before calling through, so existing fleet-cycle
    tests keep passing under Story 33.9's dispatch-boundary scope guard
    without needing their own marker/symlink fixtures.
    """
    import os

    from scope_triangle import point_scope_triangle

    from pyforge.marshal.cli import dispatch as dispatch_cli

    resolved_policy: dict[str, object] | None
    if policy_flags is _CYCLE_POLICY_REAL:
        resolved_policy = _CYCLE_POLICY_SERIAL
    else:
        resolved_policy = policy_flags  # type: ignore[assignment]

    real_dispatch_once = dispatch_cli.dispatch_once

    def _scoped_dispatch_once(*, slug: str, story: str, **kwargs):
        point_scope_triangle(tmp_path, slug)
        os.environ["BMAD_ACTIVE_PROJECT"] = slug
        return real_dispatch_once(slug=slug, story=story, **kwargs)

    dispatch_cli.dispatch_once = _scoped_dispatch_once
    try:
        return execute_fleet_cycle(
            repo_root=tmp_path,
            mode=mode,
            leave_remaining=leave_remaining,
            campaign_blocked=campaign_blocked if campaign_blocked is not None else {},
            fs=FakeFs(),
            vcs=vcs if vcs is not None else FakeVcs(tmp_path),
            build_harness=build_harness if build_harness is not None else FakeBuildHarness(),
            process=process if process is not None else FakeProcess(alive=False),
            harness=harness if harness is not None else FakeHarness(ledgers),
            station=station,
            explicit_stories=explicit_stories,
            policy_flags=resolved_policy,
            retry_environment_blocks=retry_environment_blocks,
        )
    finally:
        dispatch_cli.dispatch_once = real_dispatch_once


def _status_by_station(report) -> dict[str, StationCycleStatus]:
    return {result.slug: result.status for result in report.results}


# --------------------------------------------------------------------------
# I/O & Edge-Case Matrix
# --------------------------------------------------------------------------


def test_drained_station_is_reported_and_never_dispatched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": ["22-7-fleet"], "pyforge-doctor": []})
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers={
            "pyforge-marshal": (("22-7-fleet", "backlog"),),
            "pyforge-doctor": (("1-1-shipped", "done"),),
        },
        build_harness=harness,
    )
    statuses = _status_by_station(report)
    assert statuses["pyforge-doctor"] is StationCycleStatus.DRAINED
    assert statuses["pyforge-marshal"] is StationCycleStatus.DISPATCHED
    assert harness.dispatched == [("pyforge-marshal", "22.7")]


def test_every_station_drained_completes_the_campaign_with_no_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={slug: [] for slug in _STATIONS})
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers={slug: (("1-1-shipped", "done"),) for slug in _STATIONS},
        build_harness=harness,
    )
    assert report.complete is True
    assert harness.dispatched == []
    assert all(s is StationCycleStatus.DRAINED for s in _status_by_station(report).values())


def test_two_ready_stations_dispatch_in_the_same_cycle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_git_repo(tmp_path)
    _seed_fleet(
        tmp_path,
        stories={"pyforge-marshal": ["22-7-fleet"], "pyforge-doctor": ["14-1-canary"]},
    )
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers={
            "pyforge-marshal": (("22-7-fleet", "backlog"),),
            "pyforge-doctor": (("14-1-canary", "backlog"),),
        },
        build_harness=harness,
    )
    assert sorted(harness.dispatched) == [
        ("pyforge-doctor", "14.1"),
        ("pyforge-marshal", "22.7"),
    ]
    assert report.data["dispatched"] == ["pyforge-doctor", "pyforge-marshal"]
    # Both launches are detached; nothing in this path consults or mutates
    # FR-184's in-loop max_parallel clamp.
    assert report.complete is False


def test_every_station_busy_refuses_every_dispatch_naming_the_in_flight_story(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_git_repo(tmp_path)
    _seed_fleet(
        tmp_path,
        stories={"pyforge-marshal": ["22-7-fleet"], "pyforge-doctor": ["14-1-canary"]},
    )
    for slug in _STATIONS:
        _seed_live_dispatch_journal(tmp_path, slug=slug, run_id="run-live", story_key="9.9")
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers={
            "pyforge-marshal": (("22-7-fleet", "backlog"),),
            "pyforge-doctor": (("14-1-canary", "backlog"),),
        },
        process=FakeProcess(alive=True),
        build_harness=harness,
    )
    assert harness.dispatched == []
    assert all(s is StationCycleStatus.IN_FLIGHT for s in _status_by_station(report).values())
    relays = [f for f in report.findings if f.code == "MRS-DRAIN-006"]
    assert len(relays) == len(_STATIONS)
    for finding in relays:
        assert finding.severity is Severity.WARN
        assert "MRS-DISP-021" in finding.message
        assert "9.9" in finding.message
    # A busy fleet is the normal state of a healthy campaign, never terminal.
    assert report.complete is False


def test_zombie_redispatch_of_the_same_story_is_refused_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": ["22-7-fleet"]})
    _seed_live_dispatch_journal(tmp_path, slug="pyforge-marshal", run_id="run-live", story_key="22.7")
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers={"pyforge-marshal": (("22-7-fleet", "backlog"),)},
        process=FakeProcess(alive=True),
        build_harness=harness,
    )
    assert harness.dispatched == []
    relay = next(f for f in report.findings if f.code == "MRS-DRAIN-006")
    assert "MRS-DISP-011" in relay.message
    assert _status_by_station(report)["pyforge-marshal"] is StationCycleStatus.IN_FLIGHT


def test_queued_story_without_a_tracked_spec_is_refused_naming_mrs_disp_005(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_git_repo(tmp_path)
    # Project dir exists, but no spec file is written for the queued story.
    (tmp_path / "_bmad-output" / "projects" / "pyforge-marshal").mkdir(parents=True)
    dispatch_core.planning_specs_dir(tmp_path, "pyforge-marshal").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers={"pyforge-marshal": (("22-7-fleet", "backlog"),)},
        build_harness=harness,
    )
    assert harness.dispatched == []
    assert any(f.code == "MRS-DISP-005" for f in report.findings)
    assert _status_by_station(report)["pyforge-marshal"] is StationCycleStatus.REFUSED
    # No spec was drafted on the station's behalf.
    assert list(dispatch_core.planning_specs_dir(tmp_path, "pyforge-marshal").iterdir()) == []


def test_a_non_liveness_refusal_is_not_retried_in_the_next_cycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "_bmad-output" / "projects" / "pyforge-marshal").mkdir(parents=True)
    dispatch_core.planning_specs_dir(tmp_path, "pyforge-marshal").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    campaign_blocked: dict[str, dict[str, str]] = {}
    ledgers = {"pyforge-marshal": (("22-7-fleet", "backlog"),)}
    _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers=ledgers,
        campaign_blocked=campaign_blocked,
    )
    assert "22-7-fleet" in campaign_blocked["pyforge-marshal"]
    harness = FakeBuildHarness()
    second = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers=ledgers,
        campaign_blocked=campaign_blocked,
        build_harness=harness,
    )
    assert harness.dispatched == []
    assert _status_by_station(second)["pyforge-marshal"] is StationCycleStatus.BLOCKED
    assert any(f.code == "MRS-DRAIN-005" for f in second.findings)
    assert second.complete is True


def test_missing_spec_refuse_re_preflights_when_spec_lands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Story 28.18: a refused MRS-DISP-005 head dispatches once spec appears."""
    _init_git_repo(tmp_path)
    (tmp_path / "_bmad-output" / "projects" / "pyforge-marshal").mkdir(parents=True)
    specs = dispatch_core.planning_specs_dir(tmp_path, "pyforge-marshal")
    specs.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    ledgers = {"pyforge-marshal": (("22-7-fleet", "backlog"),)}
    args = _drain_args(once=True)
    _run_drain(tmp_path, args, ledgers=ledgers)
    run_id = next(dispatch_fleet.fleet_runs_dir(tmp_path).iterdir()).name

    (specs / "spec-22-7-fleet.md").write_text(
        '---\ndifficulty: medium\nsurface: ["src/**"]\n---\n',
        encoding="utf-8",
    )
    harness = FakeBuildHarness()
    capsys.readouterr()
    _run_drain(
        tmp_path,
        _drain_args(once=True, campaign=run_id),
        ledgers=ledgers,
        build_harness=harness,
    )
    out = capsys.readouterr().out
    assert harness.dispatched == [("pyforge-marshal", "22.7")]
    assert "MRS-DRAIN-017" not in out


def test_unchanged_refuse_predicate_is_rate_limited_across_campaign_cycles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Story 28.18: identical refuse predicate journals rate-limited skip."""
    _init_git_repo(tmp_path)
    (tmp_path / "_bmad-output" / "projects" / "pyforge-marshal").mkdir(parents=True)
    dispatch_core.planning_specs_dir(tmp_path, "pyforge-marshal").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    ledgers = {"pyforge-marshal": (("22-7-fleet", "backlog"),)}
    _run_drain(tmp_path, _drain_args(once=True), ledgers=ledgers)
    run_id = next(dispatch_fleet.fleet_runs_dir(tmp_path).iterdir()).name

    harness = FakeBuildHarness()
    capsys.readouterr()
    _run_drain(
        tmp_path,
        _drain_args(once=True, campaign=run_id),
        ledgers=ledgers,
        build_harness=harness,
    )
    out = capsys.readouterr().out
    assert harness.dispatched == []
    assert "MRS-DRAIN-017" in out
    assert "MRS-DRAIN-005" in out


def test_skip_on_blocked_moves_to_the_next_story_and_reports_the_skip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-steward": ["12-7-live-ocp", "12-8-projects"]})
    (tmp_path / "_bmad-output" / "projects" / "pyforge-marshal" / "planning-artifacts").mkdir(parents=True)
    (
        tmp_path
        / "_bmad-output"
        / "projects"
        / "pyforge-marshal"
        / "planning-artifacts"
        / dispatch_fleet.QUEUE_CONFIG_FILENAME
    ).write_text(
        "skip_policies:\n  - station: steward\n    story: 12-7-live-ocp\n    reason: Requires a live OCP cluster.\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.SKIP_ON_BLOCKED,
        ledgers={
            "pyforge-steward": (("12-7-live-ocp", "backlog"), ("12-8-projects", "backlog")),
            "pyforge-marshal": (),
        },
        build_harness=harness,
    )
    assert harness.dispatched == [("pyforge-steward", "12.8")]
    skip = next(f for f in report.findings if f.code == "MRS-DRAIN-004")
    assert "12-7-live-ocp" in skip.message
    assert "Requires a live OCP cluster." in skip.message
    steward = next(r for r in report.results if r.slug == "pyforge-steward")
    # The blocked story stays in the backlog and is never auto-retried.
    assert steward.remaining == 2
    assert steward.skipped == (("12-7-live-ocp", "Requires a live OCP cluster."),)


def test_a_halted_story_blocks_its_station_under_drain_to_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": ["22-7-fleet", "22-8-next"]})
    # A prior dispatch of 22.7 whose session is gone and whose branch never
    # merged: CAP-2's own facts judge that FAILED.
    _seed_live_dispatch_journal(
        tmp_path,
        slug="pyforge-marshal",
        run_id="run-halt",
        story_key="22.7",
        baseline_head_sha="baseline1234",
    )
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers={"pyforge-marshal": (("22-7-fleet", "backlog"), ("22-8-next", "backlog"))},
        process=FakeProcess(alive=False),
        build_harness=harness,
    )
    assert harness.dispatched == []
    blocked = next(f for f in report.findings if f.code == "MRS-DRAIN-005")
    assert "22-7-fleet" in blocked.message
    assert "skip_on_blocked" in blocked.message
    assert _status_by_station(report)["pyforge-marshal"] is StationCycleStatus.BLOCKED


def _seed_failed_dispatch_with_verify(
    tmp_path: Path,
    *,
    slug: str,
    run_id: str,
    story_key: str,
    failed_gate: str = "MRS-GATE-007",
) -> Path:
    """Seed a dead session with verify-cycle evidence (Story 34.3 story block)."""
    run_dir = dispatch_core.dispatch_run_dir(tmp_path, slug, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    wt = str(tmp_path / ".worktrees" / f"dispatch-{slug}")
    intent = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 0),
            ts="2026-09-10T00:00:00.000Z",
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_LAUNCH,
            phase=Phase.INTENT,
            payload={
                "story_key": story_key,
                "worktree_path": wt,
                "baseline_head_sha": "aaa111",
            },
        )
    ).line
    launch_outcome = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 1),
            ts="2026-09-10T00:00:01.000Z",
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_LAUNCH,
            phase=Phase.OUTCOME,
            intent_id=JournalEntryId("w", 0),
            payload={"session_pid": 42},
        )
    ).line
    verify_intent = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 2),
            ts="2026-09-10T00:04:59.000Z",
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_VERIFICATION,
            phase=Phase.INTENT,
            payload={},
        )
    ).line
    verify_outcome = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 3),
            ts="2026-09-10T00:05:00.000Z",
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_VERIFICATION,
            phase=Phase.OUTCOME,
            intent_id=JournalEntryId("w", 2),
            payload={"verdict": "failed", "failed_gate": failed_gate},
        )
    ).line
    completion_intent = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 4),
            ts="2026-09-10T00:05:59.000Z",
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_COMPLETION,
            phase=Phase.INTENT,
            payload={"verdict": "failed"},
        )
    ).line
    completion_outcome = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 5),
            ts="2026-09-10T00:06:00.000Z",
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_COMPLETION,
            phase=Phase.OUTCOME,
            intent_id=JournalEntryId("w", 4),
            payload={"verdict": "failed", "ok": True},
        )
    ).line
    (run_dir / "journal.jsonl").write_text(
        intent
        + "\n"
        + launch_outcome
        + "\n"
        + verify_intent
        + "\n"
        + verify_outcome
        + "\n"
        + completion_intent
        + "\n"
        + completion_outcome
        + "\n",
        encoding="utf-8",
    )
    return run_dir


def test_crashed_before_progress_is_environment_and_skips_under_skip_on_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": ["34-3-crashed", "34-4-next"]})
    _seed_live_dispatch_journal(
        tmp_path,
        slug="pyforge-marshal",
        run_id="run-crash",
        story_key="34.3",
        baseline_head_sha="baseline1234",
    )
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    _cycle(
        tmp_path,
        mode=FleetCampaignMode.SKIP_ON_BLOCKED,
        ledgers={"pyforge-marshal": (("34-3-crashed", "backlog"), ("34-4-next", "backlog"))},
        process=FakeProcess(alive=False),
        build_harness=harness,
    )
    assert harness.dispatched == [("pyforge-marshal", "34.4")]


def test_verify_failure_is_story_block_and_not_skipped_under_skip_on_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": ["34-3-failed", "34-4-next"]})
    wt = tmp_path / ".worktrees" / "dispatch-pyforge-marshal"
    wt.mkdir(parents=True)
    vcs = FakeVcs(tmp_path)
    vcs.progressed_worktrees.add(str(wt))
    _seed_failed_dispatch_with_verify(
        tmp_path,
        slug="pyforge-marshal",
        run_id="run-verify-fail",
        story_key="34.3",
    )
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.SKIP_ON_BLOCKED,
        ledgers={"pyforge-marshal": (("34-3-failed", "backlog"), ("34-4-next", "backlog"))},
        vcs=vcs,
        process=FakeProcess(alive=False),
        build_harness=harness,
    )
    assert harness.dispatched == []
    assert _status_by_station(report)["pyforge-marshal"] is StationCycleStatus.BLOCKED
    blocked = next(f for f in report.findings if f.code == "MRS-DRAIN-005")
    assert "story" in blocked.message


def _seed_escalation_pause_dispatch(
    tmp_path: Path,
    *,
    slug: str,
    run_id: str,
    story_key: str,
) -> Path:
    run_dir = dispatch_core.dispatch_run_dir(tmp_path, slug, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    wt = str(tmp_path / ".worktrees" / f"dispatch-{slug}")
    intent = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 0),
            ts="2026-09-10T00:00:00.000Z",
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_LAUNCH,
            phase=Phase.INTENT,
            payload={
                "story_key": story_key,
                "worktree_path": wt,
                "baseline_head_sha": "baseline1234",
            },
        )
    ).line
    launch_outcome = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 1),
            ts="2026-09-10T00:00:01.000Z",
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_LAUNCH,
            phase=Phase.OUTCOME,
            intent_id=JournalEntryId("w", 0),
            payload={"session_pid": 42},
        )
    ).line
    completion_intent = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 2),
            ts="2026-09-10T00:02:00.000Z",
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_COMPLETION,
            phase=Phase.INTENT,
            payload={"verdict": "failed", "stop_reason": "escalation-paused"},
        )
    ).line
    completion_outcome = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 3),
            ts="2026-09-10T00:02:01.000Z",
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_COMPLETION,
            phase=Phase.OUTCOME,
            intent_id=JournalEntryId("w", 2),
            payload={
                "verdict": "failed",
                "stop_reason": "escalation-paused",
                "ok": True,
            },
        )
    ).line
    (run_dir / "journal.jsonl").write_text(
        intent + "\n" + launch_outcome + "\n" + completion_intent + "\n" + completion_outcome + "\n",
        encoding="utf-8",
    )
    return run_dir


def test_escalation_pause_is_story_block_and_not_skipped_under_skip_on_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": ["34-3-escalated", "34-4-next"]})
    _seed_escalation_pause_dispatch(
        tmp_path,
        slug="pyforge-marshal",
        run_id="run-escalation",
        story_key="34.3",
    )
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.SKIP_ON_BLOCKED,
        ledgers={"pyforge-marshal": (("34-3-escalated", "backlog"), ("34-4-next", "backlog"))},
        process=FakeProcess(alive=False),
        build_harness=harness,
    )
    assert harness.dispatched == []
    assert _status_by_station(report)["pyforge-marshal"] is StationCycleStatus.BLOCKED


def _seed_background_task_ceiling_dispatch(
    tmp_path: Path,
    *,
    slug: str,
    run_id: str,
    story_key: str,
) -> Path:
    """Terminated before verify, narration-only diff (Story 51.4, CAP-252 --
    the 51.3 incident): the harness hit its background-task ceiling
    mid-session. The supervisor's own tick loop (already threading
    ``spec_relative_path``) recorded the correct ``failed`` completion
    verdict directly -- no verify entries, mirroring
    ``_seed_escalation_pause_dispatch``'s shape."""
    run_dir = dispatch_core.dispatch_run_dir(tmp_path, slug, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    wt = str(tmp_path / ".worktrees" / f"dispatch-{slug}")
    intent = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 0),
            ts="2026-09-19T00:00:00.000Z",
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_LAUNCH,
            phase=Phase.INTENT,
            payload={
                "story_key": story_key,
                "worktree_path": wt,
                "baseline_head_sha": "aaa111",
            },
        )
    ).line
    launch_outcome = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 1),
            ts="2026-09-19T00:00:01.000Z",
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_LAUNCH,
            phase=Phase.OUTCOME,
            intent_id=JournalEntryId("w", 0),
            payload={"session_pid": 42},
        )
    ).line
    completion_intent = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 2),
            ts="2026-09-19T00:10:00.000Z",
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_COMPLETION,
            phase=Phase.INTENT,
            payload={"verdict": "failed"},
        )
    ).line
    completion_outcome = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 3),
            ts="2026-09-19T00:10:01.000Z",
            run_id=run_id,
            kind=dispatch_core.KIND_DISPATCH_COMPLETION,
            phase=Phase.OUTCOME,
            intent_id=JournalEntryId("w", 2),
            payload={"verdict": "failed", "ok": True},
        )
    ).line
    (run_dir / "journal.jsonl").write_text(
        intent + "\n" + launch_outcome + "\n" + completion_intent + "\n" + completion_outcome + "\n",
        encoding="utf-8",
    )
    (run_dir / "session.log").write_text(
        "resolving story...\nBackground tasks still running after 600s; terminating\n",
        encoding="utf-8",
    )
    return run_dir


class _NarrationOnlyVcs(FakeVcs):
    """A dead session's diff that collapses to just the tracked spec's own
    relative path -- narration, not work (Story 51.4, the 51.3 incident's
    shape). Real progress happened (the head sha moves), it just was not
    implementation."""

    def __init__(self, repo_root: Path, *, worktree: Path, spec_relative: str) -> None:
        super().__init__(repo_root)
        self._worktree = str(worktree)
        self._spec_relative = spec_relative
        self.progressed_worktrees.add(self._worktree)

    def changed_files(self, repo_root: Path, worktree_path: Path, *, base: str):
        if str(worktree_path) == self._worktree:
            return (self._spec_relative,)
        return ()


def test_a_deliberate_blocked_spec_status_blocks_its_station_naming_the_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Story 51.4 (CAP-252), the 27.3 incident: a session that reverted to
    baseline and left its tracked spec ``status: blocked`` must halt the
    station and name the blocking condition -- an empty diff is never
    silently promoted to ``done``."""
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": ["27-3-gap", "27-4-next"]})
    _seed_live_dispatch_journal(
        tmp_path,
        slug="pyforge-marshal",
        run_id="run-27-3",
        story_key="27.3",
        baseline_head_sha="baseline1234",
    )
    wt = tmp_path / ".worktrees" / "dispatch-pyforge-marshal"
    spec_path = dispatch_core.planning_specs_dir(tmp_path, "pyforge-marshal") / "spec-27-3-gap.md"
    relocated = dispatch_core.relocated_spec_path(spec_path, tmp_path, wt)
    relocated.parent.mkdir(parents=True, exist_ok=True)
    relocated.write_text(
        '---\nstatus: blocked\nblocking_condition: "an intent gap was found; reverted to baseline"\n---\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.SKIP_ON_BLOCKED,
        ledgers={"pyforge-marshal": (("27-3-gap", "backlog"), ("27-4-next", "backlog"))},
        process=FakeProcess(alive=False),
        build_harness=harness,
    )
    assert harness.dispatched == []
    assert _status_by_station(report)["pyforge-marshal"] is StationCycleStatus.BLOCKED
    blocked = next(f for f in report.findings if f.code == "MRS-DRAIN-005")
    assert "status: blocked" in blocked.message
    assert "intent gap" in blocked.message


def test_a_narration_only_diff_after_a_harness_ceiling_is_transient_not_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Story 51.4 (CAP-252), the 51.3 incident: a session that hit the
    harness's background-task ceiling before verify, leaving only the
    tracked spec's own frontmatter changed, must classify TRANSIENT --
    re-dispatchable -- never a terminal station block."""
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": ["51-3-ceiling", "51-4-next"]})
    _seed_background_task_ceiling_dispatch(
        tmp_path,
        slug="pyforge-marshal",
        run_id="run-51-3",
        story_key="51.3",
    )
    wt = tmp_path / ".worktrees" / "dispatch-pyforge-marshal"
    spec_path = dispatch_core.planning_specs_dir(tmp_path, "pyforge-marshal") / "spec-51-3-ceiling.md"
    relocated = dispatch_core.relocated_spec_path(spec_path, tmp_path, wt)
    relocated.parent.mkdir(parents=True, exist_ok=True)
    relocated.write_text("---\nstatus: in-progress\n---\n", encoding="utf-8")
    spec_relative = str(relocated.resolve().relative_to(wt.resolve()))
    vcs = _NarrationOnlyVcs(tmp_path, worktree=wt, spec_relative=spec_relative)
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.SKIP_ON_BLOCKED,
        ledgers={"pyforge-marshal": (("51-3-ceiling", "backlog"), ("51-4-next", "backlog"))},
        vcs=vcs,
        process=FakeProcess(alive=False),
        build_harness=harness,
    )
    assert harness.dispatched == [("pyforge-marshal", "51.3")]
    assert _status_by_station(report)["pyforge-marshal"] is not StationCycleStatus.BLOCKED


def test_retry_environment_blocks_cli_wiring_moves_past_crash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": ["34-3-crashed", "34-4-next"]})
    _seed_live_dispatch_journal(
        tmp_path,
        slug="pyforge-marshal",
        run_id="run-crash",
        story_key="34.3",
        baseline_head_sha="baseline1234",
    )
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    code = _run_drain(
        tmp_path,
        _drain_args(once=True, retry_environment_blocks=True),
        ledgers={"pyforge-marshal": (("34-3-crashed", "backlog"), ("34-4-next", "backlog"))},
        build_harness=harness,
        process=FakeProcess(alive=False),
    )
    assert code == EXIT_OK
    assert harness.dispatched == [("pyforge-marshal", "34.4")]


def test_retry_environment_blocks_moves_past_crash_under_drain_to_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": ["34-3-crashed", "34-4-next"]})
    _seed_live_dispatch_journal(
        tmp_path,
        slug="pyforge-marshal",
        run_id="run-crash",
        story_key="34.3",
        baseline_head_sha="baseline1234",
    )
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers={"pyforge-marshal": (("34-3-crashed", "backlog"), ("34-4-next", "backlog"))},
        process=FakeProcess(alive=False),
        build_harness=harness,
        retry_environment_blocks=True,
    )
    assert harness.dispatched == [("pyforge-marshal", "34.4")]
    skip = next(f for f in report.findings if f.code == "MRS-DRAIN-004")
    assert "environment-classified block" in skip.message


def test_a_halted_story_is_skipped_under_skip_on_blocked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": ["22-7-fleet", "22-8-next"]})
    _seed_live_dispatch_journal(
        tmp_path,
        slug="pyforge-marshal",
        run_id="run-halt",
        story_key="22.7",
        baseline_head_sha="baseline1234",
    )
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    _cycle(
        tmp_path,
        mode=FleetCampaignMode.SKIP_ON_BLOCKED,
        ledgers={"pyforge-marshal": (("22-7-fleet", "backlog"), ("22-8-next", "backlog"))},
        process=FakeProcess(alive=False),
        build_harness=harness,
    )
    assert harness.dispatched == [("pyforge-marshal", "22.8")]


def test_overlapping_declared_surfaces_advise_loudly_but_never_block(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_git_repo(tmp_path)
    for slug, key in (("pyforge-marshal", "22-7-fleet"), ("pyforge-doctor", "14-1-canary")):
        (tmp_path / "_bmad-output" / "projects" / slug).mkdir(parents=True, exist_ok=True)
        specs = dispatch_core.planning_specs_dir(tmp_path, slug)
        specs.mkdir(parents=True, exist_ok=True)
        (specs / f"spec-{key}.md").write_text(
            '---\ndifficulty: medium\nsurface: ["src/shared/**"]\n---\n', encoding="utf-8"
        )
    _seed_live_dispatch_journal(tmp_path, slug="pyforge-doctor", run_id="run-live", story_key="14.1")
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers={
            "pyforge-marshal": (("22-7-fleet", "backlog"),),
            "pyforge-doctor": (("14-1-canary", "in-progress"),),
        },
        process=FakeProcess(alive=True),
        build_harness=harness,
    )
    assert ("pyforge-marshal", "22.7") in harness.dispatched
    advisory = next(f for f in report.findings if f.code == "MRS-DISP-022")
    assert advisory.severity is Severity.WARN
    assert "LOUD ADVISORY" in advisory.message


def test_merge_through_finalize_chains_the_stations_next_story(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The chain step: the ledger advancing (CAP-4's scoped
    ``sprint-ledger-sync``) plus the freed station slot is what hands the
    station its next story on the following cycle -- no second landing path."""
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": ["22-7-fleet", "22-8-next"]})
    monkeypatch.chdir(tmp_path)
    vcs = FakeVcs(tmp_path)
    process = FakeProcess(alive=True)
    harness = FakeBuildHarness()
    ledgers: dict[str, tuple[tuple[str, str], ...]] = {
        "pyforge-marshal": (("22-7-fleet", "backlog"), ("22-8-next", "backlog"))
    }
    first = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers=ledgers,
        vcs=vcs,
        process=process,
        build_harness=harness,
    )
    assert harness.dispatched == [("pyforge-marshal", "22.7")]
    assert _status_by_station(first)["pyforge-marshal"] is StationCycleStatus.DISPATCHED

    # Same fleet, story still queued: the CAP-5 guard holds the slot.
    held = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers=ledgers,
        vcs=vcs,
        process=process,
        build_harness=harness,
    )
    assert harness.dispatched == [("pyforge-marshal", "22.7")]
    assert _status_by_station(held)["pyforge-marshal"] is StationCycleStatus.IN_FLIGHT

    # Merge-through-finalize: the branch merges and the scoped ledger sync
    # advances the key. The next cycle chains 22.8 with no operator step.
    vcs.merged_branches.add(dispatch_core.dispatch_worktree_branch("pyforge-marshal", "22.7"))
    process.alive = False
    ledgers["pyforge-marshal"] = (("22-7-fleet", "done"), ("22-8-next", "backlog"))
    chained = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers=ledgers,
        vcs=vcs,
        process=process,
        build_harness=harness,
    )
    assert harness.dispatched[-1] == ("pyforge-marshal", "22.8")
    assert _status_by_station(chained)["pyforge-marshal"] is StationCycleStatus.DISPATCHED


def test_unreadable_station_ledger_is_reported_never_read_as_drained(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": [], "pyforge-doctor": []})
    monkeypatch.chdir(tmp_path)
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers={"pyforge-marshal": (("1-1-shipped", "done"),)},
    )
    statuses = _status_by_station(report)
    assert statuses["pyforge-doctor"] is StationCycleStatus.LEDGER_UNREADABLE
    assert statuses["pyforge-marshal"] is StationCycleStatus.DRAINED
    unreadable = next(f for f in report.findings if f.code == "MRS-DRAIN-003")
    assert "pyforge-doctor" in unreadable.message
    assert "never assumed empty" in unreadable.message


def test_order_overrides_decide_which_story_a_station_gets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": ["22-7-fleet", "22-8-next"]})
    (tmp_path / "_bmad-output" / "projects" / "pyforge-marshal" / "planning-artifacts").mkdir(
        parents=True, exist_ok=True
    )
    dispatch_fleet.queue_config_path(tmp_path).write_text(
        "order_overrides:\n  marshal:\n    - 22-8-next\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers={"pyforge-marshal": (("22-7-fleet", "backlog"), ("22-8-next", "backlog"))},
        build_harness=harness,
    )
    assert harness.dispatched == [("pyforge-marshal", "22.8")]


def test_malformed_queue_override_file_is_reported_not_silently_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": []})
    (tmp_path / "_bmad-output" / "projects" / "pyforge-marshal" / "planning-artifacts").mkdir(
        parents=True, exist_ok=True
    )
    dispatch_fleet.queue_config_path(tmp_path).write_text("order_overrides: [unbalanced\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers={"pyforge-marshal": (("1-1-shipped", "done"),)},
    )
    assert any(f.code == "MRS-DRAIN-008" for f in report.findings)


# --------------------------------------------------------------------------
# The command surface
# --------------------------------------------------------------------------


def _drain_args(**overrides) -> argparse.Namespace:
    base = {
        "mode": "drain_to_zero",
        "leave_remaining": 1,
        "once": False,
        "max_cycles": 0,
        "tick_seconds": 60,
        "campaign": None,
        "format": "json",
        "max_in_flight": 1,
        "retry_environment_blocks": False,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


def _run_drain(tmp_path: Path, args: argparse.Namespace, **kwargs) -> int:
    import os

    from scope_triangle import point_scope_triangle

    from pyforge.marshal.cli import dispatch as dispatch_cli

    real_dispatch_once = dispatch_cli.dispatch_once

    def _scoped_dispatch_once(*, slug: str, story: str, **kwargs):
        point_scope_triangle(tmp_path, slug)
        os.environ["BMAD_ACTIVE_PROJECT"] = slug
        return real_dispatch_once(slug=slug, story=story, **kwargs)

    dispatch_cli.dispatch_once = _scoped_dispatch_once
    try:
        return run_fleet_drain(
            args,
            fs=kwargs.get("fs") or FakeFs(),
            vcs=kwargs.get("vcs") or FakeVcs(tmp_path),
            build_harness=kwargs.get("build_harness") or FakeBuildHarness(),
            process=kwargs.get("process") or FakeProcess(alive=False),
            harness=kwargs.get("harness") or FakeHarness(kwargs["ledgers"]),
        )
    finally:
        dispatch_cli.dispatch_once = real_dispatch_once


def test_drain_refuses_a_missing_mode_loudly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": []})
    monkeypatch.chdir(tmp_path)
    code = _run_drain(tmp_path, _drain_args(mode=None), ledgers={"pyforge-marshal": ()})
    out = capsys.readouterr().out
    assert code != EXIT_OK
    assert "MRS-DRAIN-001" in out
    assert "drain_to_zero" in out


def test_drain_refuses_an_unknown_mode_naming_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": []})
    monkeypatch.chdir(tmp_path)
    code = _run_drain(tmp_path, _drain_args(mode="drain_everything"), ledgers={"pyforge-marshal": ()})
    out = capsys.readouterr().out
    assert code != EXIT_OK
    assert "drain_everything" in out


def test_drain_on_a_fully_drained_fleet_exits_clean_without_a_supervisor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={slug: [] for slug in _STATIONS})
    monkeypatch.chdir(tmp_path)
    process = FakeProcess(alive=False)
    harness = FakeBuildHarness()
    code = _run_drain(
        tmp_path,
        _drain_args(),
        ledgers={slug: (("1-1-shipped", "done"),) for slug in _STATIONS},
        process=process,
        build_harness=harness,
    )
    assert code == EXIT_OK
    assert harness.dispatched == []
    assert process.spawned == []


def test_drain_spawns_a_detached_campaign_supervisor_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": ["22-7-fleet"]})
    monkeypatch.chdir(tmp_path)
    process = FakeProcess(alive=False)
    _run_drain(
        tmp_path,
        _drain_args(),
        ledgers={"pyforge-marshal": (("22-7-fleet", "backlog"),)},
        process=process,
    )
    # One detached per-story dispatch supervisor plus the campaign
    # supervisor -- the latter is the fleet supervisor MODULE, never a
    # foreground loop inside the command itself.
    campaign = [argv for argv in process.spawned if "pyforge.marshal.dispatch_fleet_supervisor" in argv]
    assert len(campaign) == 1
    assert "drain_to_zero" in campaign[0]


def test_drain_once_runs_a_single_cycle_and_spawns_no_campaign_supervisor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": ["22-7-fleet"]})
    monkeypatch.chdir(tmp_path)
    process = FakeProcess(alive=False)
    _run_drain(
        tmp_path,
        _drain_args(once=True),
        ledgers={"pyforge-marshal": (("22-7-fleet", "backlog"),)},
        process=process,
    )
    assert [argv for argv in process.spawned if "pyforge.marshal.dispatch_fleet_supervisor" in argv] == []


def test_drain_journals_its_cycle_in_repo_under_pyforge_marshal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": ["22-7-fleet"]})
    monkeypatch.chdir(tmp_path)
    _run_drain(
        tmp_path,
        _drain_args(once=True),
        ledgers={"pyforge-marshal": (("22-7-fleet", "backlog"),)},
    )
    runs = dispatch_fleet.fleet_runs_dir(tmp_path)
    journals = list(runs.glob("*/journal.jsonl"))
    assert len(journals) == 1
    body = journals[0].read_text(encoding="utf-8")
    assert dispatch_fleet.KIND_FLEET_CYCLE in body
    assert "pyforge-marshal" in body
    # Campaign state never lands in a session-local .cursor/ tree.
    assert not (tmp_path / ".cursor").exists()


def test_a_refused_station_is_remembered_across_supervised_cycles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Campaign state survives the process: each supervised cycle is its own
    subprocess, so "this station is blocked" must come back from the campaign
    journal, not from a driver's memory."""
    _init_git_repo(tmp_path)
    (tmp_path / "_bmad-output" / "projects" / "pyforge-marshal").mkdir(parents=True)
    dispatch_core.planning_specs_dir(tmp_path, "pyforge-marshal").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    ledgers = {"pyforge-marshal": (("22-7-fleet", "backlog"),)}
    args = _drain_args(once=True)
    _run_drain(tmp_path, args, ledgers=ledgers)
    run_id = next(dispatch_fleet.fleet_runs_dir(tmp_path).iterdir()).name

    harness = FakeBuildHarness()
    capsys.readouterr()
    _run_drain(
        tmp_path,
        _drain_args(once=True, campaign=run_id),
        ledgers=ledgers,
        build_harness=harness,
    )
    out = capsys.readouterr().out
    assert harness.dispatched == []
    # Reported by name, never silently retried.
    assert "MRS-DRAIN-005" in out
    assert "MRS-DISP-005" in out
    assert '"status": "blocked"' in out


def test_campaign_supervisor_reads_completion_from_the_cycle_envelope() -> None:
    from pyforge.marshal.dispatch_fleet_supervisor.__main__ import (
        build_cycle_argv,
        cycle_reported_complete,
    )

    argv = build_cycle_argv(mode="leave_one", leave_remaining=2, run_id="camp-1")
    assert argv[-5:] == ["--campaign", "camp-1", "--once", "--format", "json"]
    assert "--loop" not in argv  # the supervisor waits; the command never does
    assert cycle_reported_complete('{"data": {"complete": true}}') is True
    assert cycle_reported_complete('{"data": {"complete": false}}') is False
    # Unreadable output is never read as "complete" -- that would silently
    # abandon a live campaign.
    assert cycle_reported_complete("not json at all") is False
    assert cycle_reported_complete("") is False


# --------------------------------------------------------------------------
# The acceptance oracle: the eight-station 2026-08-22/23 campaign, replayed
#
# `fleet-drain-playbook.md` is this story's acceptance oracle, and the
# campaign it validated is on disk in the superseded interim runner
# (`.cursor/pyforge-fleet-drain/queues.yaml`): eight stations, `mode:
# drain_to_zero`, six already drained, marshal + steward carrying ordered
# backlogs under `order_overrides`, and steward carrying hand-authored
# `skip_policies` (12-7 needs a live OCP cluster). The fixture below replays
# that exact shape through `marshal factory drain` and asserts the hand
# ritual's own outcomes -- skip, parallel, chain, drained -- fall out of the
# machinery with no operator holding session discipline.
# --------------------------------------------------------------------------

#: The live fleet, derived the same way `list_station_slugs` derives it.
_EIGHT_STATIONS = (
    "pyforge-atlas",
    "pyforge-doctor",
    "pyforge-herald",
    "pyforge-marshal",
    "pyforge-mason",
    "pyforge-scribe",
    "pyforge-steward",
    "pyforge-warden",
)
_ALREADY_DRAINED = tuple(slug for slug in _EIGHT_STATIONS if slug not in {"pyforge-marshal", "pyforge-steward"})


def _campaign_fixture(tmp_path: Path) -> dict[str, tuple[tuple[str, str], ...]]:
    """Seed the eight-station fleet in its 2026-08-22/23 starting state."""
    _init_git_repo(tmp_path)
    _seed_fleet(
        tmp_path,
        stories={
            **{slug: [] for slug in _ALREADY_DRAINED},
            # marshal's real override head, then the key that follows it.
            "pyforge-marshal": ["22-7-fleet-wide-drain", "22-8-profile-driven-harness"],
            "pyforge-steward": [
                "12-7-live-ocp",
                "12-8-github-projects",
                "12-9-story-ledger",
            ],
        },
    )
    (tmp_path / "_bmad-output" / "projects" / "pyforge-marshal" / "planning-artifacts").mkdir(
        parents=True, exist_ok=True
    )
    dispatch_fleet.queue_config_path(tmp_path).write_text(
        # The in-repo analog of queues.yaml's two hand-edited blocks. The
        # `stations:` block it also carried is deliberately absent: that was
        # a regenerated copy of state the tracked ledgers already hold.
        "order_overrides:\n"
        "  marshal:\n"
        "    - 22-8-profile-driven-harness\n"
        "    - 22-7-fleet-wide-drain\n"
        "skip_policies:\n"
        "  - station: steward\n"
        "    story: 12-7-live-ocp\n"
        "    reason: Live OCP/CRC.\n",
        encoding="utf-8",
    )
    return {
        **{slug: (("1-1-shipped", "done"),) for slug in _ALREADY_DRAINED},
        "pyforge-marshal": (
            ("22-7-fleet-wide-drain", "backlog"),
            ("22-8-profile-driven-harness", "backlog"),
        ),
        "pyforge-steward": (
            ("12-7-live-ocp", "backlog"),
            ("12-8-github-projects", "backlog"),
            ("12-9-story-ledger", "backlog"),
        ),
    }


def test_eight_station_campaign_replays_without_session_discipline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledgers = _campaign_fixture(tmp_path)
    monkeypatch.chdir(tmp_path)
    vcs = FakeVcs(tmp_path)
    process = FakeProcess(alive=True)
    harness = FakeBuildHarness()

    def cycle():
        return _cycle(
            tmp_path,
            mode=FleetCampaignMode.DRAIN_TO_ZERO,
            ledgers=ledgers,
            vcs=vcs,
            process=process,
            build_harness=harness,
        )

    # --- Cycle 1: parallel launch across the two non-drained stations ------
    first = cycle()
    statuses = _status_by_station(first)
    assert len(statuses) == len(_EIGHT_STATIONS)
    for slug in _ALREADY_DRAINED:
        assert statuses[slug] is StationCycleStatus.DRAINED
    assert statuses["pyforge-marshal"] is StationCycleStatus.DISPATCHED
    assert statuses["pyforge-steward"] is StationCycleStatus.DISPATCHED
    # The order override decides marshal's story; the declared skip policy
    # carries steward past 12-7 to 12-8 -- under drain_to_zero, the mode the
    # campaign actually ran.
    assert sorted(harness.dispatched) == [
        ("pyforge-marshal", "22.8"),
        ("pyforge-steward", "12.8"),
    ]
    skip = next(f for f in first.findings if f.code == "MRS-DRAIN-004")
    assert "12-7-live-ocp" in skip.message and "Live OCP/CRC." in skip.message
    assert "declared skip policy" in skip.message
    # A campaign with work in flight is never reported complete.
    assert first.complete is False
    assert first.data["dispatched"] == ["pyforge-marshal", "pyforge-steward"]

    # --- Cycle 2: one story in flight per station, nothing redispatched ----
    held = cycle()
    held_statuses = _status_by_station(held)
    assert held_statuses["pyforge-marshal"] is StationCycleStatus.IN_FLIGHT
    assert held_statuses["pyforge-steward"] is StationCycleStatus.IN_FLIGHT
    assert len(harness.dispatched) == 2
    relays = {f.message for f in held.findings if f.code == "MRS-DRAIN-006"}
    assert any("MRS-DISP-011" in m for m in relays)
    assert held.complete is False

    # --- Cycle 3: merge-through-finalize chains each station's next story --
    # CAP-4's composition (CI-green merge + scoped `sprint-ledger-sync
    # --project <station>` + spec promotion) is what advances these two
    # facts; the fleet mode adds no landing path of its own.
    vcs.merged_branches.add(dispatch_core.dispatch_worktree_branch("pyforge-marshal", "22.8"))
    vcs.merged_branches.add(dispatch_core.dispatch_worktree_branch("pyforge-steward", "12.8"))
    process.alive = False
    ledgers["pyforge-marshal"] = (
        ("22-7-fleet-wide-drain", "backlog"),
        ("22-8-profile-driven-harness", "done"),
    )
    ledgers["pyforge-steward"] = (
        ("12-7-live-ocp", "backlog"),
        ("12-8-github-projects", "done"),
        ("12-9-story-ledger", "backlog"),
    )
    chained = cycle()
    assert sorted(harness.dispatched[2:]) == [
        ("pyforge-marshal", "22.7"),
        ("pyforge-steward", "12.9"),
    ]
    chained_statuses = _status_by_station(chained)
    assert chained_statuses["pyforge-marshal"] is StationCycleStatus.DISPATCHED
    assert chained_statuses["pyforge-steward"] is StationCycleStatus.DISPATCHED

    # --- Exit criteria: every station drained (or wholly skipped) ---------
    vcs.merged_branches.add(dispatch_core.dispatch_worktree_branch("pyforge-marshal", "22.7"))
    vcs.merged_branches.add(dispatch_core.dispatch_worktree_branch("pyforge-steward", "12.9"))
    ledgers["pyforge-marshal"] = (
        ("22-7-fleet-wide-drain", "done"),
        ("22-8-profile-driven-harness", "done"),
    )
    ledgers["pyforge-steward"] = (
        ("12-7-live-ocp", "backlog"),
        ("12-8-github-projects", "done"),
        ("12-9-story-ledger", "done"),
    )
    final = cycle()
    final_statuses = _status_by_station(final)
    assert final_statuses["pyforge-marshal"] is StationCycleStatus.DRAINED
    # steward's only remaining key is the one the operator declared skipped:
    # it stays in the backlog, is never auto-retried, and is never forced.
    assert final_statuses["pyforge-steward"] is StationCycleStatus.ALL_SKIPPED
    steward = next(r for r in final.results if r.slug == "pyforge-steward")
    assert steward.remaining == 1
    assert steward.skipped == (("12-7-live-ocp", "Live OCP/CRC."),)
    assert len(harness.dispatched) == 4
    assert final.complete is True


def test_eight_station_campaign_halts_one_station_without_stopping_the_rest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A HALT mid-drain is per-station, reported by name, and never forced:
    the other seven stations keep working (playbook incident table)."""
    ledgers = _campaign_fixture(tmp_path)
    # marshal's override head already HALTed: its session is gone and its
    # branch never merged, so CAP-2's own facts judge that run `failed`.
    _seed_live_dispatch_journal(
        tmp_path,
        slug="pyforge-marshal",
        run_id="run-halt",
        story_key="22.8",
        baseline_head_sha="baseline1234",
    )
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers=ledgers,
        process=FakeProcess(alive=False),
        build_harness=harness,
    )
    statuses = _status_by_station(report)
    assert statuses["pyforge-marshal"] is StationCycleStatus.BLOCKED
    # Steward is untouched by marshal's HALT and lands its next story.
    assert statuses["pyforge-steward"] is StationCycleStatus.DISPATCHED
    assert harness.dispatched == [("pyforge-steward", "12.8")]
    blocked = next(f for f in report.findings if f.code == "MRS-DRAIN-005")
    assert "pyforge-marshal" in blocked.message
    assert "22-8-profile-driven-harness" in blocked.message
    assert "never auto-retried" in blocked.message

    # Same fleet under skip_on_blocked: marshal steps past the HALTed story
    # to its next one -- the steward-12-7 remedy from the incident table,
    # applied to derived HALT evidence.
    skipping = FakeBuildHarness()
    _cycle(
        tmp_path,
        mode=FleetCampaignMode.SKIP_ON_BLOCKED,
        ledgers=ledgers,
        process=FakeProcess(alive=False),
        build_harness=skipping,
    )
    assert ("pyforge-marshal", "22.7") in skipping.dispatched


def test_the_replayed_campaign_keeps_its_state_in_repo_never_in_cursor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The Spec's named subsumption target: campaign/queue state lives
    in-repo under `pyforge-marshal`, never session-local `.cursor/`."""
    ledgers = _campaign_fixture(tmp_path)
    monkeypatch.chdir(tmp_path)
    code = _run_drain(tmp_path, _drain_args(once=True), ledgers=ledgers)
    assert code == EXIT_OK
    runs = dispatch_fleet.fleet_runs_dir(tmp_path)
    assert runs.is_relative_to(tmp_path / "_bmad-output" / "projects" / "pyforge-marshal")
    journal = next(iter(runs.glob("*/journal.jsonl")))
    body = journal.read_text(encoding="utf-8")
    for slug in _EIGHT_STATIONS:
        assert slug in body
    assert not (tmp_path / ".cursor").exists()


# --------------------------------------------------------------------------
# Review findings (2026-08-27 adversarial pass) — regression pins
# --------------------------------------------------------------------------


def test_campaign_state_survives_an_over_threshold_cycle_payload(
    tmp_path: Path,
) -> None:
    """AD-30 sidecars on the READ side.

    A cycle payload carries one row per station plus every skip reason and
    refusal detail, so a real eight-station campaign crosses
    ``SIDECAR_THRESHOLD_BYTES`` within a few cycles — at which point
    ``prepare_for_write`` moves the payload to ``blobs/`` and leaves a
    ``{"sidecar_ref": …}`` pointer. Folding without resolving those pointers
    quarantines exactly the entries the blocked map is read from, so the
    station would be retried on every tick forever and the campaign could
    never report itself complete.
    """
    from pyforge.marshal.cli.dispatch import (
        FleetCycleReport,
        _campaign_blocked_from_journal,
        _journal_fleet_cycle,
    )
    from pyforge.marshal.core.journal import SIDECAR_THRESHOLD_BYTES

    fs = FakeFs()
    run_dir = tmp_path / "campaign"
    run_dir.mkdir()
    detail = "MRS-DISP-005: no tracked spec found for story " + ("x" * 400)
    results = tuple(
        dispatch_fleet.StationCycleResult(
            slug=f"pyforge-station-{n}",
            status=StationCycleStatus.REFUSED,
            remaining=3,
            story=f"{n}-1-a-story-key-of-realistic-length",
            detail=detail,
        )
        for n in range(12)
    )
    report = FleetCycleReport(results=results, findings=(), data={"mode": "drain_to_zero"})
    _journal_fleet_cycle(fs, run_dir, "camp-1", report, [])

    # Precondition: this payload really did take the sidecar route.
    body = (run_dir / "journal.jsonl").read_text(encoding="utf-8")
    assert '"sidecar_ref"' in body
    assert (run_dir / "blobs").is_dir()
    blob = next(iter((run_dir / "blobs").iterdir()))
    assert len(blob.read_text(encoding="utf-8").encode("utf-8")) > SIDECAR_THRESHOLD_BYTES

    recovered, _predicates = _campaign_blocked_from_journal(fs, run_dir, "camp-1")
    assert len(recovered) == 12
    assert recovered["pyforge-station-0"]["0-1-a-story-key-of-realistic-length"] == detail


def test_exactly_one_drain_cycle_runs_at_a_time_fleet_wide(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The interim runner's singleton-coordinator convention, made structural:
    two concurrent drains must never both see a station's slot free."""
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": ["22-7-fleet"]})
    monkeypatch.chdir(tmp_path)
    process = FakeProcess(alive=False)
    harness = FakeBuildHarness()
    code = _run_drain(
        tmp_path,
        _drain_args(),
        ledgers={"pyforge-marshal": (("22-7-fleet", "backlog"),)},
        fs=FakeFs(lock_unavailable=True),
        process=process,
        build_harness=harness,
    )
    out = capsys.readouterr().out
    assert code != EXIT_OK
    assert "MRS-DRAIN-010" in out
    # Nothing dispatched, and no second campaign supervisor left behind.
    assert harness.dispatched == []
    assert process.spawned == []


def test_the_cycle_lock_is_released_even_on_the_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": []})
    monkeypatch.chdir(tmp_path)
    fs = FakeFs()
    _run_drain(
        tmp_path,
        _drain_args(once=True),
        ledgers={"pyforge-marshal": (("1-1-shipped", "done"),)},
        fs=fs,
    )
    assert fs.locks_acquired == [dispatch_fleet.fleet_cycle_lock_path(tmp_path)]
    assert len(fs.locks_released) == 1
    # Fleet-wide, never per-campaign: two different campaigns racing on one
    # station is precisely the case this lock exists to prevent.
    assert "campaign" not in fs.locks_acquired[0].parent.name


def test_one_stations_raising_dispatch_never_starves_the_rest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The station loop is alphabetical: an unguarded raise would silently
    starve every station after it, on every supervised tick, forever — and
    journal no cycle at all."""
    from pyforge.marshal.cli import dispatch as dispatch_cli

    _init_git_repo(tmp_path)
    _seed_fleet(
        tmp_path,
        stories={"pyforge-doctor": ["14-1-canary"], "pyforge-marshal": ["22-7-fleet"]},
    )
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    real_dispatch_once = dispatch_cli.dispatch_once

    def exploding(*, slug: str, story: str, **kwargs):
        import os

        from scope_triangle import point_scope_triangle

        if slug == "pyforge-doctor":  # sorts BEFORE pyforge-marshal
            raise VcsCommandError("worktree vanished under a live session")
        point_scope_triangle(tmp_path, slug)
        os.environ["BMAD_ACTIVE_PROJECT"] = slug
        return real_dispatch_once(slug=slug, story=story, **kwargs)

    monkeypatch.setattr(dispatch_cli, "dispatch_once", exploding)
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers={
            "pyforge-doctor": (("14-1-canary", "backlog"),),
            "pyforge-marshal": (("22-7-fleet", "backlog"),),
        },
        build_harness=harness,
    )
    statuses = _status_by_station(report)
    assert statuses["pyforge-doctor"] is StationCycleStatus.REFUSED
    assert statuses["pyforge-marshal"] is StationCycleStatus.DISPATCHED
    assert harness.dispatched == [("pyforge-marshal", "22.7")]
    crash = next(f for f in report.findings if f.code == "MRS-DRAIN-011")
    assert "pyforge-doctor" in crash.message
    assert "VcsCommandError" in crash.message


def test_an_empty_fleet_is_reported_never_read_as_drained(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`campaign_complete(())` is vacuously True — without a finding this is
    a clean 'campaign complete' from a repo with no projects tree at all."""
    _init_git_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    report = _cycle(tmp_path, mode=FleetCampaignMode.DRAIN_TO_ZERO, ledgers={})
    assert report.results == ()
    empty = next(f for f in report.findings if f.code == "MRS-DRAIN-012")
    assert empty.severity is Severity.ERROR
    assert "never treated as a drained one" in empty.message


def test_complete_is_reported_alongside_what_it_does_not_cover(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`complete` is the supervisor's stop signal ("nothing more this
    campaign can do"), NOT "everything drained" — a station whose ledger will
    not read is terminal with its real backlog unattended, so it is named."""
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": [], "pyforge-doctor": []})
    monkeypatch.chdir(tmp_path)
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers={"pyforge-marshal": (("1-1-shipped", "done"),)},
    )
    assert report.complete is True
    unresolved = report.data["unresolved"]
    assert unresolved == [{"station": "pyforge-doctor", "status": "ledger-unreadable", "remaining": 0}]
    assert any(f.code == "MRS-DRAIN-003" for f in report.findings)


def test_a_path_shaped_campaign_id_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--campaign` names a directory under the campaign runs tree."""
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": []})
    monkeypatch.chdir(tmp_path)
    code = _run_drain(
        tmp_path,
        _drain_args(campaign="../../escaped"),
        ledgers={"pyforge-marshal": ()},
    )
    assert code != EXIT_OK
    assert "MRS-DRAIN-001" in capsys.readouterr().out
    assert not (tmp_path.parent / "escaped").exists()


def test_a_negative_cycle_ceiling_is_refused_not_clamped_to_unbounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`max(0, -1)` is 0, and 0 means UNBOUNDED here — the opposite ask."""
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": []})
    monkeypatch.chdir(tmp_path)
    code = _run_drain(tmp_path, _drain_args(max_cycles=-1), ledgers={"pyforge-marshal": ()})
    assert code != EXIT_OK
    out = capsys.readouterr().out
    assert "MRS-DRAIN-001" in out and "--max-cycles" in out


def test_order_override_deduplicates_a_repeated_key() -> None:
    """The override file is hand-maintained; a repeated key would otherwise
    put the same story in the backlog twice."""
    backlog = ("2-1-a", "3-1-b")
    assert apply_order_override(backlog, ["3-1-b", "3-1-b", "2-1-a"]) == (
        "3-1-b",
        "2-1-a",
    )


def test_campaign_supervisor_stops_re_running_an_unrunnable_cycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`ProcessPort.run` never raises on a non-zero exit and an unreadable
    cycle reads as "not complete" — with the default unbounded --max-cycles
    that makes a permanently broken command an immortal 60s spinner."""
    from pyforge.marshal.dispatch_fleet_supervisor import __main__ as sup

    monkeypatch.setattr(sup.time, "sleep", lambda _s: None)

    class ExplodingProcess:
        def __init__(self) -> None:
            self.calls = 0

        def run(self, argv, *, cwd):
            self.calls += 1
            return type("R", (), {"stdout": "Traceback (most recent call last): ...", "stderr": "boom"})()

    process = ExplodingProcess()
    code = sup.run_fleet_campaign_supervisor(
        repo_root=Path("/tmp"),
        run_id="camp-1",
        mode="drain_to_zero",
        leave_remaining=1,
        max_cycles=0,  # unbounded
        tick_seconds=1,
        process=process,
    )
    assert code == 1
    assert process.calls == sup._MAX_CONSECUTIVE_UNREADABLE_CYCLES


def test_campaign_supervisor_distinguishes_unreadable_from_not_complete() -> None:
    from pyforge.marshal.dispatch_fleet_supervisor.__main__ import cycle_completion

    assert cycle_completion('{"data": {"complete": true}}') is True
    assert cycle_completion('{"data": {"complete": false}}') is False
    # "don't know" is its own answer, never conflated with "still working".
    assert cycle_completion("not json at all") is None
    assert cycle_completion('{"data": {}}') is None
    assert cycle_completion("") is None


# --------------------------------------------------------------------------
# Story 22.11 — station-scoped drain (`drain --station`) and an explicit
# story sequence (`dispatch --stories`), FR-193 CAP-10
# --------------------------------------------------------------------------


def test_station_scope_reads_only_that_stations_ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The AC's own wording: "every other station's backlog is provably
    untouched by the same invocation" -- not merely "not dispatched", its
    ledger must never even be READ."""
    _init_git_repo(tmp_path)
    _seed_fleet(
        tmp_path,
        stories={"pyforge-marshal": ["22-11-fleet"], "pyforge-doctor": ["14-1-canary"]},
    )
    monkeypatch.chdir(tmp_path)
    harness = FakeHarness(
        {
            "pyforge-marshal": (("22-11-fleet", "backlog"),),
            "pyforge-doctor": (("14-1-canary", "backlog"),),
        }
    )
    build_harness = FakeBuildHarness()
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers={},
        harness=harness,
        build_harness=build_harness,
        station="pyforge-marshal",
    )
    assert harness.read_slugs == ["pyforge-marshal"]
    assert build_harness.dispatched == [("pyforge-marshal", "22.11")]
    assert [r.slug for r in report.results] == ["pyforge-marshal"]


def test_station_scope_accepts_the_bare_name_too(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": ["22-11-fleet"]})
    monkeypatch.chdir(tmp_path)
    harness = FakeHarness({"pyforge-marshal": (("22-11-fleet", "backlog"),)})
    build_harness = FakeBuildHarness()
    _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers={},
        harness=harness,
        build_harness=build_harness,
        station="marshal",
    )
    assert harness.read_slugs == ["pyforge-marshal"]
    assert build_harness.dispatched == [("pyforge-marshal", "22.11")]


def test_unknown_station_is_refused_naming_the_live_ones(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": ["22-11-fleet"]})
    monkeypatch.chdir(tmp_path)
    harness = FakeHarness({"pyforge-marshal": (("22-11-fleet", "backlog"),)})
    build_harness = FakeBuildHarness()
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers={},
        harness=harness,
        build_harness=build_harness,
        station="pyforge-nonexistent",
    )
    assert harness.read_slugs == []
    assert build_harness.dispatched == []
    assert report.results == ()
    refusal = next(f for f in report.findings if f.code == "MRS-DRAIN-013")
    assert "pyforge-nonexistent" in refusal.message
    assert "pyforge-marshal" in refusal.message


def test_execute_fleet_cycle_rejects_explicit_stories_without_station(
    tmp_path: Path,
) -> None:
    """Review finding (Story 22.11 patch pass): ``explicit_stories`` is only
    meaningful scoped to one station -- without a guard, a future caller
    passing it alone would silently apply the sequence fleet-wide."""
    with pytest.raises(ValueError, match="explicit_stories requires station"):
        _cycle(
            tmp_path,
            mode=FleetCampaignMode.DRAIN_TO_ZERO,
            ledgers={},
            explicit_stories=("22-11-a",),
        )


def test_run_fleet_drain_station_flag_scopes_the_campaign(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_git_repo(tmp_path)
    _seed_fleet(
        tmp_path,
        stories={"pyforge-marshal": ["22-11-fleet"], "pyforge-doctor": ["14-1-canary"]},
    )
    monkeypatch.chdir(tmp_path)
    harness = FakeHarness(
        {
            "pyforge-marshal": (("22-11-fleet", "backlog"),),
            "pyforge-doctor": (("14-1-canary", "backlog"),),
        }
    )
    build_harness = FakeBuildHarness()
    process = FakeProcess(alive=False)
    code = _run_drain(
        tmp_path,
        _drain_args(station="pyforge-marshal"),
        ledgers={},
        harness=harness,
        build_harness=build_harness,
        process=process,
    )
    assert code == EXIT_OK
    assert harness.read_slugs == ["pyforge-marshal"]
    assert build_harness.dispatched == [("pyforge-marshal", "22.11")]
    # The campaign supervisor's own re-invocation must carry --station too,
    # or the next supervised tick would silently widen back to fleet-wide.
    campaign_argv = next(argv for argv in process.spawned if "pyforge.marshal.dispatch_fleet_supervisor" in argv)
    assert "pyforge-marshal" in campaign_argv


def test_stories_without_station_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": ["22-11-fleet"]})
    monkeypatch.chdir(tmp_path)
    build_harness = FakeBuildHarness()
    process = FakeProcess(alive=False)
    code = _run_drain(
        tmp_path,
        _drain_args(stories="22-11-fleet"),
        ledgers={"pyforge-marshal": (("22-11-fleet", "backlog"),)},
        build_harness=build_harness,
        process=process,
    )
    assert code != EXIT_OK
    assert build_harness.dispatched == []
    assert process.spawned == []


def test_stories_naming_an_unknown_key_refuses_before_any_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": ["22-11-fleet", "22-12-next"]})
    monkeypatch.chdir(tmp_path)
    build_harness = FakeBuildHarness()
    process = FakeProcess(alive=False)
    code = _run_drain(
        tmp_path,
        _drain_args(station="pyforge-marshal", stories="22-11-fleet,99-9-nonexistent"),
        ledgers={"pyforge-marshal": (("22-11-fleet", "backlog"), ("22-12-next", "backlog"))},
        build_harness=build_harness,
        process=process,
    )
    assert code != EXIT_OK
    assert build_harness.dispatched == []
    assert process.spawned == []
    # No campaign run directory was even created for this refusal.
    runs = dispatch_fleet.fleet_runs_dir(tmp_path)
    assert not runs.is_dir() or list(runs.iterdir()) == []


def test_stories_naming_an_already_done_key_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": ["22-12-next"]})
    monkeypatch.chdir(tmp_path)
    build_harness = FakeBuildHarness()
    code = _run_drain(
        tmp_path,
        _drain_args(station="pyforge-marshal", stories="22-11-fleet,22-12-next"),
        ledgers={"pyforge-marshal": (("22-11-fleet", "done"), ("22-12-next", "backlog"))},
        build_harness=build_harness,
    )
    out = capsys.readouterr().out
    assert code != EXIT_OK
    assert build_harness.dispatched == []
    assert "MRS-DISP-032" in out
    assert "22-11-fleet" in out


def test_stories_sequence_dispatches_in_the_given_order_not_ledger_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": ["22-11-fleet", "22-12-next"]})
    monkeypatch.chdir(tmp_path)
    build_harness = FakeBuildHarness()
    process = FakeProcess(alive=False)
    code = _run_drain(
        tmp_path,
        _drain_args(station="pyforge-marshal", stories="22-12-next,22-11-fleet"),
        ledgers={"pyforge-marshal": (("22-11-fleet", "backlog"), ("22-12-next", "backlog"))},
        build_harness=build_harness,
        process=process,
    )
    assert code == EXIT_OK
    # 22.12 first, even though the ledger's own order is 22.11 then 22.12.
    assert build_harness.dispatched == [("pyforge-marshal", "22.12")]


def test_explicit_sequence_chains_through_both_keys_in_order_across_cycles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mirrors test_merge_through_finalize_chains_the_stations_next_story,
    but with an explicit, REVERSED sequence proving order is the caller's,
    never the ledger's."""
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": ["22-11-fleet", "22-12-next"]})
    monkeypatch.chdir(tmp_path)
    vcs = FakeVcs(tmp_path)
    process = FakeProcess(alive=True)
    build_harness = FakeBuildHarness()
    ledgers: dict[str, tuple[tuple[str, str], ...]] = {
        "pyforge-marshal": (("22-11-fleet", "backlog"), ("22-12-next", "backlog"))
    }
    sequence = ("22-12-next", "22-11-fleet")

    def cycle():
        return _cycle(
            tmp_path,
            mode=FleetCampaignMode.DRAIN_TO_ZERO,
            ledgers=ledgers,
            vcs=vcs,
            process=process,
            build_harness=build_harness,
            station="pyforge-marshal",
            explicit_stories=sequence,
        )

    first = cycle()
    assert build_harness.dispatched == [("pyforge-marshal", "22.12")]
    assert _status_by_station(first)["pyforge-marshal"] is StationCycleStatus.DISPATCHED

    # In flight: the CAP-5 guard holds the slot, no redispatch.
    held = cycle()
    assert build_harness.dispatched == [("pyforge-marshal", "22.12")]
    assert _status_by_station(held)["pyforge-marshal"] is StationCycleStatus.IN_FLIGHT

    # 22.12 lands; the next cycle chains to 22.11 -- the SEQUENCE's next
    # entry, not the ledger's own ascending order.
    vcs.merged_branches.add(dispatch_core.dispatch_worktree_branch("pyforge-marshal", "22.12"))
    process.alive = False
    ledgers["pyforge-marshal"] = (("22-11-fleet", "backlog"), ("22-12-next", "done"))
    chained = cycle()
    assert build_harness.dispatched[-1] == ("pyforge-marshal", "22.11")
    assert _status_by_station(chained)["pyforge-marshal"] is StationCycleStatus.DISPATCHED

    # Both keys done: the campaign completes.
    vcs.merged_branches.add(dispatch_core.dispatch_worktree_branch("pyforge-marshal", "22.11"))
    ledgers["pyforge-marshal"] = (("22-11-fleet", "done"), ("22-12-next", "done"))
    final = cycle()
    assert _status_by_station(final)["pyforge-marshal"] is StationCycleStatus.DRAINED
    assert final.complete is True


def test_dispatch_supervisor_re_invocation_carries_station_and_stories() -> None:
    """`build_cycle_argv` -- the command a supervised tick re-runs -- must
    keep BOTH flags across every tick, or a station-scoped/sequenced
    campaign silently widens back to fleet-wide on its very first re-tick."""
    from pyforge.marshal.dispatch_fleet_supervisor.__main__ import build_cycle_argv

    argv = build_cycle_argv(
        mode="drain_to_zero",
        leave_remaining=0,
        run_id="camp-1",
        station="pyforge-scribe",
        stories="22-11-a,22-12-b",
    )
    assert "--station" in argv
    assert argv[argv.index("--station") + 1] == "pyforge-scribe"
    assert "--stories" in argv
    assert argv[argv.index("--stories") + 1] == "22-11-a,22-12-b"

    harness_argv = build_cycle_argv(
        mode="drain_to_zero",
        leave_remaining=0,
        run_id="camp-h",
        harness="cursor,claude",
    )
    assert "--harness" in harness_argv
    assert harness_argv[harness_argv.index("--harness") + 1] == "cursor,claude"

    # Omitted when unset -- an ordinary fleet-wide drain's argv is untouched.
    plain = build_cycle_argv(mode="drain_to_zero", leave_remaining=1, run_id="camp-2")
    assert "--station" not in plain
    assert "--stories" not in plain
    assert "--harness" not in plain
    assert "--max-in-flight" not in plain

    parallel_argv = build_cycle_argv(
        mode="drain_to_zero",
        leave_remaining=0,
        run_id="camp-3",
        max_in_flight=2,
    )
    assert "--max-in-flight" in parallel_argv
    assert parallel_argv[parallel_argv.index("--max-in-flight") + 1] == "2"


def test_unknown_station_with_stories_refuses_as_unknown_station_not_unreadable_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review finding (Story 22.11 patch pass): station liveness must be
    checked BEFORE the ledger read in the ``--stories`` pre-validation path,
    or a simple ``--station`` typo surfaces as a confusing MRS-DRAIN-015
    ("ledger unreadable") instead of the actionable MRS-DRAIN-013."""
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": ["22-11-fleet"]})
    monkeypatch.chdir(tmp_path)
    build_harness = FakeBuildHarness()
    process = FakeProcess(alive=False)
    code = _run_drain(
        tmp_path,
        _drain_args(station="pyforge-nonexistent", stories="22-11-fleet"),
        ledgers={"pyforge-marshal": (("22-11-fleet", "backlog"),)},
        build_harness=build_harness,
        process=process,
    )
    assert code != EXIT_OK
    assert build_harness.dispatched == []
    assert process.spawned == []
    runs = dispatch_fleet.fleet_runs_dir(tmp_path)
    assert not runs.is_dir() or list(runs.iterdir()) == []


def test_stories_with_known_station_unreadable_ledger_refuses_mrs_drain_015(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """MRS-DRAIN-015 -- distinct from the unknown-station MRS-DRAIN-013 case
    above -- fires when the station IS live but its tracked ledger cannot be
    read for some other reason (``FakeHarness`` raises ``HarnessError`` for
    any station absent from its ``ledgers`` map)."""
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": ["22-11-fleet"]})
    monkeypatch.chdir(tmp_path)
    harness = FakeHarness({})  # pyforge-marshal is live but has no ledger entry
    build_harness = FakeBuildHarness()
    process = FakeProcess(alive=False)
    code = _run_drain(
        tmp_path,
        _drain_args(station="pyforge-marshal", stories="22-11-fleet"),
        ledgers={},
        harness=harness,
        build_harness=build_harness,
        process=process,
    )
    out = capsys.readouterr().out
    assert code != EXIT_OK
    assert build_harness.dispatched == []
    assert process.spawned == []
    assert "MRS-DRAIN-015" in out


def test_stories_supervisor_reinvocation_via_run_fleet_drain_carries_stories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verification-gap finding: the earlier ``build_cycle_argv`` test only
    checks the pure function in isolation, and the pre-existing
    ``test_run_fleet_drain_station_flag_scopes_the_campaign`` only asserts
    on ``station`` (``stories`` stays ``None`` there). This drives the REAL
    ``run_fleet_drain`` -> ``_spawn_campaign_supervisor`` call path with
    BOTH set and asserts the spawned supervisor subprocess's argv actually
    carries the raw ``--stories`` value -- as a plain trailing positional
    (``_spawn_campaign_supervisor`` invokes the DETACHED supervisor module
    itself, whose own CLI is positional; ``--station``/``--stories`` flags
    only appear later, inside ``build_cycle_argv``'s re-invocation of
    ``factory drain``, which this unit test never runs). Without this,
    ``stories=explicit_stories`` could be silently dropped or misassigned
    on the call into ``_spawn_campaign_supervisor`` with no test catching
    it."""
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": ["22-11-fleet", "22-12-next"]})
    monkeypatch.chdir(tmp_path)
    build_harness = FakeBuildHarness()
    process = FakeProcess(alive=False)
    code = _run_drain(
        tmp_path,
        _drain_args(station="pyforge-marshal", stories="22-12-next,22-11-fleet"),
        ledgers={"pyforge-marshal": (("22-11-fleet", "backlog"), ("22-12-next", "backlog"))},
        build_harness=build_harness,
        process=process,
    )
    assert code == EXIT_OK
    campaign_argv = next(argv for argv in process.spawned if "pyforge.marshal.dispatch_fleet_supervisor" in argv)
    assert "pyforge-marshal" in campaign_argv
    assert "22-12-next,22-11-fleet" in campaign_argv


def test_stale_campaign_id_with_stories_still_validates_unresolved_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Review finding (Story 22.11 patch pass): a ``--campaign`` id that
    never actually ran (no run directory on disk) must not be trusted as a
    genuine resume -- otherwise an operator hand-typing an unused campaign
    id together with ``--stories`` could bypass the unknown/already-done-key
    pre-launch refusal AC3 promises unconditionally."""
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": ["22-12-next"]})
    monkeypatch.chdir(tmp_path)
    build_harness = FakeBuildHarness()
    code = _run_drain(
        tmp_path,
        _drain_args(
            station="pyforge-marshal",
            stories="99-9-nonexistent",
            campaign="never-ran-before",
        ),
        ledgers={"pyforge-marshal": (("22-12-next", "backlog"),)},
        build_harness=build_harness,
    )
    out = capsys.readouterr().out
    assert code != EXIT_OK
    assert build_harness.dispatched == []
    assert "MRS-DISP-032" in out
    assert "99-9-nonexistent" in out


# --------------------------------------------------------------------------
# Story 28.12 — dependency-derived dispatch ordering (CAP-14)
# --------------------------------------------------------------------------


_ATLAS_CROSS_EPIC_EPICS = """
### Story 22.1: Earlier epic story
**Type:** feature • **Effort:** M • **Deps:** —

### Story 23.9: Quartet workbook retirement
**Type:** feature • **Effort:** L • **Deps:** S-23.4, S-23.5, S-23.6, S-23.8, S-22.1
"""


def test_cross_epic_dependency_orders_prerequisite_first() -> None:
    deps = parse_epics_dependencies(_ATLAS_CROSS_EPIC_EPICS)
    backlog = (
        "23-9-quartet-workbook-retirement",
        "22-1-dashboard-provenance",
    )
    ordered = dependency_ordered_backlog(backlog, deps_by_story=deps)
    assert ordered.index("22-1-dashboard-provenance") < ordered.index("23-9-quartet-workbook-retirement")


def test_independent_stories_keep_ledger_order_tie_break() -> None:
    deps = parse_epics_dependencies(
        "### Story 2.1: A\n**Type:** feature • **Deps:** —\n\n### Story 10.1: B\n**Type:** feature • **Deps:** —\n"
    )
    backlog = ("10-1-later", "2-1-earlier")
    ordered = dependency_ordered_backlog(backlog, deps_by_story=deps)
    assert ordered == ("10-1-later", "2-1-earlier")


def test_station_backlog_uses_dependency_order_when_epics_loaded() -> None:
    deps = parse_epics_dependencies(_ATLAS_CROSS_EPIC_EPICS)
    statuses = (
        ("23-9-quartet-workbook-retirement", "backlog"),
        ("22-1-dashboard-provenance", "backlog"),
    )
    ordered = station_backlog(statuses, deps_by_story=deps)
    assert ordered == (
        "22-1-dashboard-provenance",
        "23-9-quartet-workbook-retirement",
    )


def test_explicit_stories_override_is_unchanged_by_dependency_ordering() -> None:
    deps = parse_epics_dependencies(_ATLAS_CROSS_EPIC_EPICS)
    statuses = (
        ("23-9-quartet-workbook-retirement", "backlog"),
        ("22-1-dashboard-provenance", "backlog"),
    )
    explicit = ("23-9-quartet-workbook-retirement", "22-1-dashboard-provenance")
    ordered = explicit_story_backlog(statuses, explicit)
    assert ordered == explicit
    # Caller override path never consults deps — station_backlog with override
    # also unchanged.
    assert station_backlog(
        statuses,
        order_override=("23-9-quartet-workbook-retirement",),
        deps_by_story=deps,
    ) == ("23-9-quartet-workbook-retirement", "22-1-dashboard-provenance")


@pytest.mark.parametrize("backlog", [(), ("28-12-only",)])
def test_dependency_ordering_never_crashes_on_small_backlogs(
    backlog: tuple[str, ...],
) -> None:
    deps = {
        StoryKey(28, 12): ParsedStoryDeps(story_keys=(StoryKey(28, 11),)),
    }
    assert dependency_ordered_backlog(backlog, deps_by_story=deps) == backlog
    statuses = tuple((key, "backlog") for key in backlog)
    assert station_backlog(statuses, deps_by_story=deps) == backlog


def _seed_done_worktree_spec(repo: Path, slug: str, story: str) -> Path:
    from pyforge.marshal.core.identity import normalize, render_feed_key

    specs = dispatch_core.planning_specs_dir(repo, slug)
    spec = specs / f"spec-{story}.md"
    spec.write_text(
        f'---\nstatus: ready-for-dev\ndifficulty: medium\nsurface: ["src/{slug}/**"]\n---\n',
        encoding="utf-8",
    )
    feed = render_feed_key(normalize(story))
    worktree = dispatch_core.dispatch_worktree_path(repo, slug, feed)
    dest = worktree / spec.relative_to(repo)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        f'---\nstatus: done\nfollowup_review_recommended: false\ndifficulty: medium\nsurface: ["src/{slug}/**"]\n---\n',
        encoding="utf-8",
    )
    return worktree


def test_harness_done_dirty_pr_does_not_relaunch_on_drain(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """41.2-shaped: DIRTY PR + done worktree spec → 0 additional launches."""
    from pyforge.marshal.cli import dispatch as dispatch_cli
    from pyforge.marshal.core.dispatch_landing import DispatchLandingVerdict

    _init_git_repo(tmp_path)
    slug = "pyforge-steward"
    story = "41-2-query-plane"
    _seed_fleet(tmp_path, stories={slug: [story]})
    _seed_done_worktree_spec(tmp_path, slug, story)
    monkeypatch.chdir(tmp_path)
    pr_url = "https://github.com/rxm7706/local-recipes/pull/1017"
    monkeypatch.setattr(
        dispatch_cli,
        "_attempt_harness_done_cap4",
        lambda **_kwargs: (DispatchLandingVerdict.REFUSED, pr_url, None),
    )
    harness = FakeBuildHarness()
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers={slug: ((story, "backlog"),)},
        build_harness=harness,
        station=slug,
    )
    assert harness.dispatched == []
    assert _status_by_station(report)[slug] is StationCycleStatus.REFUSED
    assert any(f.code == "MRS-DISP-040" for f in report.findings)
    assert any("1017" in f.message for f in report.findings)


def test_harness_done_040_advances_to_next_backlog_same_cycle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """040 on a harness-done head must dispatch the next implementable story."""
    from pyforge.marshal.cli import dispatch as dispatch_cli
    from pyforge.marshal.core.dispatch_landing import DispatchLandingVerdict

    _init_git_repo(tmp_path)
    slug = "pyforge-steward"
    done_head = "43-4-query-plane"
    next_story = "43-5-next-implementable"
    _seed_fleet(tmp_path, stories={slug: [done_head, next_story]})
    _seed_done_worktree_spec(tmp_path, slug, done_head)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        dispatch_cli,
        "_attempt_harness_done_cap4",
        lambda **_kwargs: (
            DispatchLandingVerdict.REFUSED,
            "https://github.com/rxm7706/local-recipes/pull/1033",
            None,
        ),
    )
    harness = FakeBuildHarness()
    campaign_blocked: dict[str, dict[str, str]] = {}
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers={
            slug: (
                (done_head, "backlog"),
                (next_story, "backlog"),
                ("43-6-held", "blocked"),
            )
        },
        build_harness=harness,
        station=slug,
        campaign_blocked=campaign_blocked,
    )
    assert harness.dispatched == [(slug, "43.5")]
    assert _status_by_station(report)[slug] is StationCycleStatus.DISPATCHED
    assert report.complete is False
    assert done_head in campaign_blocked[slug]
    assert any(f.code == "MRS-DISP-040" for f in report.findings)
    assert any(f.code == "MRS-DRAIN-004" for f in report.findings)


def test_harness_done_040_second_cycle_does_not_block_the_station(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A journaled 040 must not become MRS-DRAIN-005 / campaign-complete."""
    _init_git_repo(tmp_path)
    slug = "pyforge-steward"
    next_story = "43-5-next-implementable"
    _seed_fleet(tmp_path, stories={slug: [next_story]})
    monkeypatch.chdir(tmp_path)
    campaign_blocked = {slug: {"43-4-landed-head": "MRS-DISP-040: awaiting-operator (skipped-unverified)"}}
    harness = FakeBuildHarness()
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers={
            slug: (
                ("43-4-landed-head", "backlog"),
                (next_story, "backlog"),
                ("43-6-held", "blocked"),
            )
        },
        build_harness=harness,
        station=slug,
        campaign_blocked=campaign_blocked,
    )
    assert harness.dispatched == [(slug, "43.5")]
    assert _status_by_station(report)[slug] is StationCycleStatus.DISPATCHED
    assert report.complete is False
    assert not any(f.code == "MRS-DRAIN-005" for f in report.findings)


def test_harness_done_no_pr_does_not_relaunch_on_drain(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """13.2-shaped: commits and no PR → 0 launches, worktree named."""
    _init_git_repo(tmp_path)
    slug = "pyforge-mason"
    story = "13-2-recipe-refresh"
    _seed_fleet(tmp_path, stories={slug: [story]})
    worktree = _seed_done_worktree_spec(tmp_path, slug, story)
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers={slug: ((story, "backlog"),)},
        build_harness=harness,
        station=slug,
    )
    assert harness.dispatched == []
    assert _status_by_station(report)[slug] is StationCycleStatus.REFUSED
    assert any(f.code == "MRS-DISP-040" for f in report.findings)
    assert any(str(worktree) in f.message for f in report.findings)


def test_execute_fleet_cycle_forms_two_member_wave_with_dispatch_max_parallel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Story 33.8: dispatch.max_parallel=2 + disjoint probe specs → one wave,
    two ``dispatch_once`` launches, dispatch-wave journal."""
    from pyforge.marshal.cli import dispatch as dispatch_cli
    from pyforge.marshal.cli.dispatch import DispatchAttempt

    slug = "pyforge-marshal"
    story_a = "33-8"
    story_b = "33-9"
    _init_git_repo(tmp_path)
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True, exist_ok=True)
    (specs / "spec-33-8-wave-probe-a.md").write_text(
        '---\nstatus: backlog\nsurface: ["scripts/bmad_loop_baseline_drift_check.py"]\n---\n',
        encoding="utf-8",
    )
    (specs / "spec-33-9-wave-probe-b.md").write_text(
        '---\nstatus: backlog\nsurface: ["scripts/missing_preserve_check.py"]\n---\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    launches: list[str] = []

    def recording_dispatch_once(*, story: str, **kwargs):
        launches.append(story)
        return DispatchAttempt(
            data={"session_pid": 7070, "story": story},
            findings=(),
        )

    monkeypatch.setattr(dispatch_cli, "dispatch_once", recording_dispatch_once)

    harness = FakeBuildHarness()
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers={slug: ((story_a, "backlog"), (story_b, "backlog"))},
        build_harness=harness,
        station=slug,
        policy_flags={"dispatch": {"max_parallel": 2}},
    )
    assert sorted(launches) == sorted([story_a, story_b])
    assert _status_by_station(report)[slug] is StationCycleStatus.DISPATCHED

    waves_root = dispatch_core.dispatch_runs_dir(tmp_path, slug) / "waves"
    assert waves_root.is_dir()
    wave_dirs = [p for p in waves_root.iterdir() if p.is_dir()]
    assert len(wave_dirs) == 1
    journal = (wave_dirs[0] / "journal.jsonl").read_text(encoding="utf-8")
    assert dispatch_core.KIND_DISPATCH_WAVE in journal
    assert story_a in journal and story_b in journal


# --------------------------------------------------------------------------
# Story 50.1 (CAP-244) -- a landing never re-dispatches the story it landed
# --------------------------------------------------------------------------


@pytest.mark.parametrize("story_on_backlog", [True, False])
@pytest.mark.parametrize("landing_complete", [True, False])
@pytest.mark.parametrize("completion_journaled", [True, False])
@pytest.mark.parametrize("supervisor_alive", [True, False])
def test_is_finalize_pending_matrix(
    supervisor_alive: bool,
    completion_journaled: bool,
    landing_complete: bool,
    story_on_backlog: bool,
) -> None:
    """Every cell of Part A's own I/O matrix, exhaustively."""
    expected = story_on_backlog and (landing_complete or (supervisor_alive and not completion_journaled))
    assert (
        is_finalize_pending(
            supervisor_alive=supervisor_alive,
            completion_journaled=completion_journaled,
            landing_complete=landing_complete,
            story_on_backlog=story_on_backlog,
        )
        is expected
    )


def test_is_finalize_pending_is_self_limiting_once_the_ledger_promotes() -> None:
    """A promoted story ends the condition no matter how alive the run looks."""
    assert (
        is_finalize_pending(
            supervisor_alive=True,
            completion_journaled=False,
            landing_complete=True,
            story_on_backlog=False,
        )
        is False
    )


@pytest.mark.parametrize(
    ("session_log", "expected"),
    [
        ("the branch is already merged into main", True),
        ("work already landed; nothing to do", True),
        ("land verdict: already_landed", True),
        ("HALT: status done, follow-up not recommended", True),
        ("merged as https://github.com/rxm7706/local-recipes/pull/1467", True),
        ("this PR #1467 was merged upstream", True),
        ("ALREADY MERGED (uppercase still counts)", True),
        # A PR reference with no "merged" on that line is not evidence.
        ("opened https://github.com/rxm7706/local-recipes/pull/1467\nstill open", False),
        ("#1467 is the tracking issue", False),
        ("quota exceeded; the session aborted", False),
        ("", False),
        (None, False),
    ],
)
def test_is_already_landed_self_refusal_evidence(session_log: str | None, expected: bool) -> None:
    assert is_already_landed_self_refusal(changed_path_count=0, session_log=session_log) is expected


@pytest.mark.parametrize("changed_path_count", [1, 7])
def test_is_already_landed_self_refusal_needs_zero_changed_paths(
    changed_path_count: int,
) -> None:
    """Merged wording alone never advances a session that changed files."""
    assert (
        is_already_landed_self_refusal(
            changed_path_count=changed_path_count,
            session_log="the branch is already merged into main",
        )
        is False
    )


def test_is_advance_reason_covers_both_families() -> None:
    assert is_advance_reason(f"{HARNESS_DONE_ADVANCE_CODE}: awaiting-operator")
    assert is_advance_reason(f"{ALREADY_LANDED_ADVANCE_PREFIX}: run 'x' refused itself")
    assert not is_advance_reason("the last dispatch of '23.6' (run 'r') ended 'failed' by git and process facts")
    assert not is_advance_reason("")


def test_already_landed_reason_skips_under_every_mode() -> None:
    """Part B's one widened test at ``plan_station_queue``'s skip branch."""
    for mode in FleetCampaignMode:
        plan = plan_station_queue(
            slug="pyforge-herald",
            backlog=("23-6-landed", "23-7-next"),
            mode=mode,
            leave_remaining=0,
            blocked={"23-6-landed": f"{ALREADY_LANDED_ADVANCE_PREFIX}: already landed"},
        )
        assert plan.outcome is StationQueueOutcome.DISPATCH, mode
        assert plan.next_story == "23-7-next", mode
        assert plan.skipped[0][0] == "23-6-landed", mode


def _seed_finalize_pending_journal(
    tmp_path: Path,
    *,
    slug: str,
    run_id: str,
    story_key: str,
    session_pid: int = 42,
    supervisor_pid: int | None = 99,
    landing_verdict: str | None = None,
    completion_verdict: str | None = None,
    baseline_head_sha: str = "baseline1234",
) -> Path:
    """Seed the 2026-09-18 window: session exited, finalize still running.

    ``baseline_head_sha`` defaults to ``FakeVcs.head_sha`` so a dead session
    reads FAILED by CAP-2's own facts -- the shape that blocked the station
    before Part A. ``landing_verdict='landed'`` instead makes
    ``resolve_dispatch_session_verdict`` say COMPLETED, which is the shape
    that RE-DISPATCHED the story. Part A must read both as in flight.
    """
    run_dir = dispatch_core.dispatch_run_dir(tmp_path, slug, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    launch_outcome_payload: dict[str, object] = {"session_pid": session_pid}
    if supervisor_pid is not None:
        launch_outcome_payload["supervisor_pid"] = supervisor_pid
    lines = [
        prepare_for_write(
            build_entry(
                id=JournalEntryId("w", 0),
                ts="2026-09-18T16:19:45.000Z",
                run_id=run_id,
                kind=dispatch_core.KIND_DISPATCH_LAUNCH,
                phase=Phase.INTENT,
                payload={
                    "story_key": story_key,
                    "worktree_path": str(tmp_path / ".worktrees" / f"dispatch-{slug}"),
                    "baseline_head_sha": baseline_head_sha,
                },
            )
        ).line,
        prepare_for_write(
            build_entry(
                id=JournalEntryId("w", 1),
                ts="2026-09-18T16:19:46.000Z",
                run_id=run_id,
                kind=dispatch_core.KIND_DISPATCH_LAUNCH,
                phase=Phase.OUTCOME,
                intent_id=JournalEntryId("w", 0),
                payload=launch_outcome_payload,
            )
        ).line,
    ]
    if landing_verdict is not None:
        lines.append(
            prepare_for_write(
                build_entry(
                    id=JournalEntryId("w", 2),
                    ts="2026-09-18T16:20:45.000Z",
                    run_id=run_id,
                    kind=dispatch_core.KIND_DISPATCH_LAND,
                    phase=Phase.INTENT,
                    payload={},
                )
            ).line
        )
        lines.append(
            prepare_for_write(
                build_entry(
                    id=JournalEntryId("w", 3),
                    ts="2026-09-18T16:20:46.000Z",
                    run_id=run_id,
                    kind=dispatch_core.KIND_DISPATCH_LAND,
                    phase=Phase.OUTCOME,
                    intent_id=JournalEntryId("w", 2),
                    payload={"ok": True, "verdict": landing_verdict},
                )
            ).line
        )
    if completion_verdict is not None:
        lines.append(
            prepare_for_write(
                build_entry(
                    id=JournalEntryId("w", 4),
                    ts="2026-09-18T16:21:45.000Z",
                    run_id=run_id,
                    kind=dispatch_core.KIND_DISPATCH_COMPLETION,
                    phase=Phase.INTENT,
                    payload={},
                )
            ).line
        )
        lines.append(
            prepare_for_write(
                build_entry(
                    id=JournalEntryId("w", 5),
                    ts="2026-09-18T16:21:46.000Z",
                    run_id=run_id,
                    kind=dispatch_core.KIND_DISPATCH_COMPLETION,
                    phase=Phase.OUTCOME,
                    intent_id=JournalEntryId("w", 4),
                    payload={"ok": True, "verdict": completion_verdict},
                )
            ).line
        )
    (run_dir / "journal.jsonl").write_text("".join(line + "\n" for line in lines), encoding="utf-8")
    return run_dir


_ALREADY_LANDED_LOG = (
    "resolving story 23.6...\n"
    "the spec's work is already merged as "
    "https://github.com/rxm7706/local-recipes/pull/1466\n"
    "HALT: nothing to implement\n"
)


def _seed_already_landed_self_refusal(
    tmp_path: Path,
    *,
    slug: str,
    run_id: str,
    story_key: str,
    session_log: str = _ALREADY_LANDED_LOG,
) -> Path:
    """A dead session with zero git progress that refused itself as merged."""
    run_dir = _seed_live_dispatch_journal(
        tmp_path,
        slug=slug,
        run_id=run_id,
        story_key=story_key,
        baseline_head_sha="baseline1234",
    )
    (run_dir / "session.log").write_text(session_log, encoding="utf-8")
    return run_dir


def test_landed_but_unpromoted_head_reports_in_flight_not_re_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC1: dispatch-land 'landed' + ledger still backlog → in-flight."""
    _init_git_repo(tmp_path)
    slug = "pyforge-herald"
    head = "23-6-landing-fallout"
    nxt = "23-7-next-implementable"
    _seed_fleet(tmp_path, stories={slug: [head, nxt]})
    _seed_finalize_pending_journal(
        tmp_path,
        slug=slug,
        run_id=f"{slug}-20260918T161945000Z-82ce96c8",
        story_key="23.6",
        supervisor_pid=None,
        landing_verdict="landed",
    )
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers={slug: ((head, "backlog"), (nxt, "backlog"))},
        process=FakeProcess(alive=False),
        build_harness=harness,
        station=slug,
    )
    assert harness.dispatched == []
    assert _status_by_station(report)[slug] is StationCycleStatus.IN_FLIGHT
    assert report.complete is False
    waiting = next(f for f in report.findings if f.code == "MRS-DRAIN-006")
    assert head in waiting.message
    assert not any(f.code == "MRS-DRAIN-005" for f in report.findings)


def test_live_supervisor_without_completion_reports_in_flight_not_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC2: live supervisor + dead session + no completion + no git progress."""
    _init_git_repo(tmp_path)
    slug = "pyforge-herald"
    head = "23-6-landing-fallout"
    nxt = "23-7-next-implementable"
    _seed_fleet(tmp_path, stories={slug: [head, nxt]})
    _seed_finalize_pending_journal(
        tmp_path,
        slug=slug,
        run_id=f"{slug}-20260918T161945000Z-82ce96c8",
        story_key="23.6",
        session_pid=42,
        supervisor_pid=99,
    )
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers={slug: ((head, "backlog"), (nxt, "backlog"))},
        process=FakeProcess(alive_pids=frozenset({99})),
        build_harness=harness,
        station=slug,
    )
    assert harness.dispatched == []
    assert _status_by_station(report)[slug] is StationCycleStatus.IN_FLIGHT
    assert report.complete is False
    assert not any(f.code == "MRS-DRAIN-005" for f in report.findings)


def test_a_dead_supervisor_without_completion_still_blocks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Part A cannot wedge a station: clause (a) requires a LIVE supervisor."""
    _init_git_repo(tmp_path)
    slug = "pyforge-herald"
    head = "23-6-landing-fallout"
    _seed_fleet(tmp_path, stories={slug: [head]})
    _seed_finalize_pending_journal(
        tmp_path,
        slug=slug,
        run_id=f"{slug}-20260918T161945000Z-82ce96c8",
        story_key="23.6",
        supervisor_pid=99,
    )
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers={slug: ((head, "backlog"),)},
        process=FakeProcess(alive_pids=frozenset()),
        build_harness=harness,
        station=slug,
    )
    assert harness.dispatched == []
    assert _status_by_station(report)[slug] is StationCycleStatus.BLOCKED


def test_a_still_live_session_is_not_finalize_pending(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Part A never pre-empts CAP-2's own liveness path.

    A session still running is plain in-flight: ``MRS-DISP-011`` relayed
    through ``MRS-DRAIN-006`` is the already-correct report, and clause (a)
    is about the window AFTER the session exits.
    """
    _init_git_repo(tmp_path)
    slug = "pyforge-herald"
    head = "23-6-landing-fallout"
    _seed_fleet(tmp_path, stories={slug: [head]})
    _seed_finalize_pending_journal(
        tmp_path,
        slug=slug,
        run_id=f"{slug}-20260918T161945000Z-82ce96c8",
        story_key="23.6",
        session_pid=42,
        supervisor_pid=99,
    )
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers={slug: ((head, "backlog"),)},
        process=FakeProcess(alive_pids=frozenset({42, 99})),
        build_harness=harness,
        station=slug,
    )
    assert harness.dispatched == []
    relays = {f.message for f in report.findings if f.code == "MRS-DRAIN-006"}
    assert any("MRS-DISP-011" in message for message in relays)
    assert not any("finalizing" in message for message in relays)


def test_once_the_ledger_promotes_the_next_story_dispatches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """AC3: promotion ends finalize-pending on the very next cycle."""
    _init_git_repo(tmp_path)
    slug = "pyforge-herald"
    head = "23-6-landing-fallout"
    nxt = "23-7-next-implementable"
    _seed_fleet(tmp_path, stories={slug: [head, nxt]})
    _seed_finalize_pending_journal(
        tmp_path,
        slug=slug,
        run_id=f"{slug}-20260918T161945000Z-82ce96c8",
        story_key="23.6",
        supervisor_pid=99,
        landing_verdict="landed",
    )
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers={slug: ((head, "done"), (nxt, "backlog"))},
        process=FakeProcess(alive_pids=frozenset({99})),
        build_harness=harness,
        station=slug,
    )
    assert harness.dispatched == [(slug, "23.7")]
    assert _status_by_station(report)[slug] is StationCycleStatus.DISPATCHED
    assert report.complete is False


def test_sibling_promoted_ledger_is_read_when_primary_sits_behind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Story 51.9 (re-mint of 51.3): `_promote_sprint_ledger`'s own CAP-5
    isolation never touches the primary checkout, so a sibling station's
    finalize can promote `head` on `origin/main` while THIS campaign's
    primary checkout stays dirty (or otherwise unverified as a clean local
    `main`) and is never fast-forwarded by this fixture. The very next
    cycle must read the promoted status from `origin/main` -- never the
    stale local ledger twin -- and chain straight to the next ready story
    (replays the herald 2026-09-18 sequence's own outcome via the new
    read-side fallback instead of a local ledger write)."""
    _init_git_repo(tmp_path)
    slug = "pyforge-herald"
    head = "23-6-landing-fallout"
    nxt = "23-7-next-implementable"
    _seed_fleet(tmp_path, stories={slug: [head, nxt]})
    _seed_finalize_pending_journal(
        tmp_path,
        slug=slug,
        run_id=f"{slug}-20260918T161945000Z-82ce96c8",
        story_key="23.6",
        supervisor_pid=99,
        landing_verdict="landed",
    )
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    vcs = FakeVcs(tmp_path)
    # The primary checkout is dirty -- never fast-forwarded or otherwise
    # mutated by this fixture. `_station_ledger_statuses` must fall back
    # to reading `origin/main` directly instead of refusing or blocking.
    vcs.dirty = True
    ledger_rel = f"_bmad-output/projects/{slug}/planning-artifacts/sprint-status-ledger.yaml"
    vcs.remote_ledger_texts[ledger_rel] = f"development_status:\n  {head}: done\n  {nxt}: backlog\n"
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        # The LOCAL on-disk twin is deliberately stale -- if the campaign
        # ever fell back to it, `head` would still read "backlog" and the
        # station would stay stuck rather than chaining to `nxt`.
        ledgers={slug: ((head, "backlog"), (nxt, "backlog"))},
        vcs=vcs,
        process=FakeProcess(alive_pids=frozenset({99})),
        build_harness=harness,
        station=slug,
    )
    assert harness.dispatched == [(slug, "23.7")]
    assert _status_by_station(report)[slug] is StationCycleStatus.DISPATCHED
    assert report.complete is False
    # VG1 (review pass 2026-09-19): the local cache of `origin/main` must be
    # refreshed before the remote-read fallback trusts it, or a stale cache
    # would silently defeat this very fallback.
    assert vcs.fetched == [("origin", "main")]


def test_clean_but_diverged_primary_still_reads_the_remote_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Group 4a (review pass 2026-09-19): a primary that is NOT dirty but
    has simply moved past (or never was) local `main`'s resolved tip must
    still hit the `origin/main` remote-read path -- `_primary_checkout_is_
    clean_main` gates on SHA-match too, not only on dirtiness."""
    _init_git_repo(tmp_path)
    slug = "pyforge-herald"
    head = "23-6-landing-fallout"
    nxt = "23-7-next-implementable"
    _seed_fleet(tmp_path, stories={slug: [head, nxt]})
    _seed_finalize_pending_journal(
        tmp_path,
        slug=slug,
        run_id=f"{slug}-20260918T161945000Z-82ce96c8",
        story_key="23.6",
        supervisor_pid=99,
        landing_verdict="landed",
    )
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    vcs = FakeVcs(tmp_path)
    # Clean checkout, but its resolved `main` tip has moved on -- never
    # fast-forwarded or otherwise mutated by this fixture.
    vcs.dirty = False
    vcs.main_ref = "diverged-tip-9999"
    ledger_rel = f"_bmad-output/projects/{slug}/planning-artifacts/sprint-status-ledger.yaml"
    vcs.remote_ledger_texts[ledger_rel] = f"development_status:\n  {head}: done\n  {nxt}: backlog\n"
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        # The LOCAL on-disk twin is deliberately stale, same as the dirty
        # case -- divergence alone must be enough to distrust it.
        ledgers={slug: ((head, "backlog"), (nxt, "backlog"))},
        vcs=vcs,
        process=FakeProcess(alive_pids=frozenset({99})),
        build_harness=harness,
        station=slug,
    )
    assert harness.dispatched == [(slug, "23.7")]
    assert _status_by_station(report)[slug] is StationCycleStatus.DISPATCHED
    assert vcs.fetched == [("origin", "main")]


def test_remote_read_failure_falls_back_to_the_local_ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Group 4b (review pass 2026-09-19): when the remote read itself fails
    (here, `file_text_at_ref` raises `VcsCommandError`), the fallback must
    still resolve -- to the existing local `HarnessPort` read -- rather than
    propagating the error or reporting no status at all."""
    _init_git_repo(tmp_path)
    slug = "pyforge-herald"
    head = "23-6-landing-fallout"
    nxt = "23-7-next-implementable"
    _seed_fleet(tmp_path, stories={slug: [head, nxt]})
    _seed_finalize_pending_journal(
        tmp_path,
        slug=slug,
        run_id=f"{slug}-20260918T161945000Z-82ce96c8",
        story_key="23.6",
        supervisor_pid=99,
        landing_verdict="landed",
    )
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    vcs = FakeVcs(tmp_path)
    vcs.dirty = True

    def _raise_on_read(repo_root: Path, ref: str, path: str) -> str | None:
        raise VcsCommandError("origin/main ref temporarily unavailable")

    vcs.file_text_at_ref = _raise_on_read  # type: ignore[method-assign]
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        # The LOCAL ledger already reflects the promotion here -- since the
        # remote read fails, this is what must be trusted instead.
        ledgers={slug: ((head, "done"), (nxt, "backlog"))},
        vcs=vcs,
        process=FakeProcess(alive_pids=frozenset({99})),
        build_harness=harness,
        station=slug,
    )
    assert harness.dispatched == [(slug, "23.7")]
    assert _status_by_station(report)[slug] is StationCycleStatus.DISPATCHED
    assert vcs.fetched == [("origin", "main")]


def test_herald_2026_09_18_three_cycle_replay_ends_with_the_next_story(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC4: the campaign ends with the NEXT story dispatched, never the same
    story blocked (``fleet-drain-runs/…151925342Z-82ce96c8``)."""
    _init_git_repo(tmp_path)
    slug = "pyforge-herald"
    head = "23-6-landing-fallout"
    nxt = "23-7-next-implementable"
    run_id = f"{slug}-20260918T161945000Z-82ce96c8"
    _seed_fleet(tmp_path, stories={slug: [head, nxt]})
    monkeypatch.chdir(tmp_path)
    process = FakeProcess(alive_pids=frozenset({99}))
    harness = FakeBuildHarness()
    findings_by_cycle: list[list[str]] = []

    def _run(ledger: tuple[tuple[str, str], ...]):
        report = _cycle(
            tmp_path,
            mode=FleetCampaignMode.DRAIN_TO_ZERO,
            ledgers={slug: ledger},
            process=process,
            build_harness=harness,
            station=slug,
        )
        findings_by_cycle.append([f.code for f in report.findings])
        return report

    backlog_ledger = ((head, "backlog"), (nxt, "backlog"))

    # 16:19:45Z -- session exited, supervisor still landing.
    _seed_finalize_pending_journal(tmp_path, slug=slug, run_id=run_id, story_key="23.6", supervisor_pid=99)
    first = _run(backlog_ledger)
    assert _status_by_station(first)[slug] is StationCycleStatus.IN_FLIGHT

    # 16:20:47Z -- the cycle that used to RE-DISPATCH: land journaled,
    # ledger not yet promoted.
    _seed_finalize_pending_journal(
        tmp_path,
        slug=slug,
        run_id=run_id,
        story_key="23.6",
        supervisor_pid=99,
        landing_verdict="landed",
    )
    second = _run(backlog_ledger)
    assert _status_by_station(second)[slug] is StationCycleStatus.IN_FLIGHT

    # 16:21:47Z -- the cycle that used to BLOCK. Finalize has promoted.
    third = _run(((head, "done"), (nxt, "backlog")))
    assert _status_by_station(third)[slug] is StationCycleStatus.DISPATCHED
    assert third.complete is False

    assert harness.dispatched == [(slug, "23.7")]
    assert all("MRS-DRAIN-005" not in codes for codes in findings_by_cycle)


def test_already_landed_self_refusal_advances_to_the_next_story(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Part B: the re-dispatched session's self-refusal advances, never blocks."""
    _init_git_repo(tmp_path)
    slug = "pyforge-herald"
    head = "23-6-landing-fallout"
    nxt = "23-7-next-implementable"
    _seed_fleet(tmp_path, stories={slug: [head, nxt]})
    _seed_already_landed_self_refusal(tmp_path, slug=slug, run_id="run-already-landed", story_key="23.6")
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers={slug: ((head, "backlog"), (nxt, "backlog"))},
        process=FakeProcess(alive=False),
        build_harness=harness,
        station=slug,
    )
    assert harness.dispatched == [(slug, "23.7")]
    assert _status_by_station(report)[slug] is StationCycleStatus.DISPATCHED
    assert report.complete is False
    assert not any(f.code == "MRS-DRAIN-005" for f in report.findings)
    skip = next(f for f in report.findings if f.code == "MRS-DRAIN-004")
    assert "already landed" in skip.message
    assert head in skip.message


def test_a_failed_dispatch_without_merged_evidence_still_blocks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC5a: a genuine failure with zero changed paths blocks exactly as today."""
    _init_git_repo(tmp_path)
    slug = "pyforge-herald"
    head = "23-6-landing-fallout"
    nxt = "23-7-next-implementable"
    _seed_fleet(tmp_path, stories={slug: [head, nxt]})
    _seed_already_landed_self_refusal(
        tmp_path,
        slug=slug,
        run_id="run-genuine-failure",
        story_key="23.6",
        session_log="starting story 23.6...\nthe harness crashed mid-implement\n",
    )
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers={slug: ((head, "backlog"), (nxt, "backlog"))},
        process=FakeProcess(alive=False),
        build_harness=harness,
        station=slug,
    )
    assert harness.dispatched == []
    assert _status_by_station(report)[slug] is StationCycleStatus.BLOCKED
    assert any(f.code == "MRS-DRAIN-005" for f in report.findings)


def test_mutation_stubbing_already_landed_false_re_blocks_the_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC5b: remove the advance classification and the fixture re-blocks."""
    _init_git_repo(tmp_path)
    slug = "pyforge-herald"
    head = "23-6-landing-fallout"
    nxt = "23-7-next-implementable"
    _seed_fleet(tmp_path, stories={slug: [head, nxt]})
    _seed_already_landed_self_refusal(tmp_path, slug=slug, run_id="run-already-landed", story_key="23.6")
    monkeypatch.setattr(dispatch_fleet, "is_already_landed_self_refusal", lambda **_kwargs: False)
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    report = _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers={slug: ((head, "backlog"), (nxt, "backlog"))},
        process=FakeProcess(alive=False),
        build_harness=harness,
        station=slug,
    )
    assert harness.dispatched == []
    assert _status_by_station(report)[slug] is StationCycleStatus.BLOCKED
    assert any(f.code == "MRS-DRAIN-005" for f in report.findings)
