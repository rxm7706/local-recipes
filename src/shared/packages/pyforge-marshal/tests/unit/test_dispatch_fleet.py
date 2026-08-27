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

from pyforge.marshal.adapters.harness_bmadloop import HarnessError
from pyforge.marshal.cli.dispatch import (
    execute_fleet_cycle,
    run_fleet_drain,
)
from pyforge.marshal.core import dispatch as dispatch_core
from pyforge.marshal.core import dispatch_fleet
from pyforge.marshal.core.dispatch_fleet import (
    FleetCampaignMode,
    InvalidCampaignModeError,
    StationCycleStatus,
    StationQueueOutcome,
    apply_order_override,
    parse_campaign_mode,
    plan_station_queue,
    station_backlog,
)
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
    )
    assert station_backlog(statuses) == ("2-1-queued", "10-1-later")


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
    plan = plan_station_queue(
        slug="pyforge-mason", backlog=(), mode=FleetCampaignMode.DRAIN_TO_ZERO
    )
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


def test_skip_on_blocked_skips_to_the_next_story_and_reports_the_reason() -> None:
    plan = plan_station_queue(
        slug="pyforge-steward",
        backlog=("12-7-live-ocp", "12-8-github-projects"),
        mode=FleetCampaignMode.SKIP_ON_BLOCKED,
        blocked={"12-7-live-ocp": "needs a live OCP cluster"},
    )
    assert plan.outcome is StationQueueOutcome.DISPATCH
    assert plan.next_story == "12-8-github-projects"
    assert plan.skipped == (("12-7-live-ocp", "needs a live OCP cluster"),)
    # The blocked story is never removed from the backlog.
    assert "12-7-live-ocp" in plan.backlog


def test_other_modes_stop_at_a_blocked_story_and_never_force_past_it() -> None:
    plan = plan_station_queue(
        slug="pyforge-steward",
        backlog=("12-7-live-ocp", "12-8-github-projects"),
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        blocked={"12-7-live-ocp": "needs a live OCP cluster"},
    )
    assert plan.outcome is StationQueueOutcome.BLOCKED
    assert plan.blocked_story == "12-7-live-ocp"
    assert plan.next_story is None


def test_fleet_station_slugs_are_derived_not_declared() -> None:
    slugs = dispatch_fleet.fleet_station_slugs(
        ("pyforge-atlas", "local-recipes", "pyforge-zzz-new-station", "deckcraft")
    )
    assert slugs == ("pyforge-atlas", "pyforge-zzz-new-station")


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
    subprocess.run(
        ["git", "config", "user.name", "drain"], cwd=path, check=True, capture_output=True
    )


class FakeFs:
    """Writes through to the real tree so run dirs stay discoverable."""

    def __init__(self) -> None:
        self.files: dict[Path, str] = {}

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

    def repo_common_root(self, _cwd: Path) -> Path:
        return self.repo_root

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


class FakeBuildHarness:
    def __init__(self, *, present: bool = True) -> None:
        self.present = present
        self.dispatched: list[tuple[str, str]] = []

    def binary_present(self, preference=(), repo_root=None) -> HarnessResolution:
        if not self.present:
            return HarnessResolution(
                profile=None,
                skipped=tuple(
                    HarnessCandidateSkip(
                        profile=name, reason=f"binary {name!r} not found on PATH"
                    )
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
    def __init__(self, *, alive: bool = True) -> None:
        self.alive = alive
        self.spawned: list[list[str]] = []

    def is_alive(self, _pid: int) -> bool:
        return self.alive

    def spawn_detached(self, argv, *, cwd: Path, log_path: Path) -> int:
        self.spawned.append(list(argv))
        return 7071


class FakeHarness:
    """``HarnessPort.ledger_story_statuses`` over an in-memory fleet ledger."""

    def __init__(self, ledgers: dict[str, tuple[tuple[str, str], ...]]) -> None:
        self.ledgers = ledgers

    def ledger_story_statuses(self, path: Path) -> tuple[tuple[str, str], ...]:
        slug = path.parent.parent.name
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
):
    return execute_fleet_cycle(
        repo_root=tmp_path,
        mode=mode,
        leave_remaining=leave_remaining,
        campaign_blocked=campaign_blocked if campaign_blocked is not None else {},
        fs=FakeFs(),
        vcs=vcs if vcs is not None else FakeVcs(tmp_path),
        build_harness=build_harness if build_harness is not None else FakeBuildHarness(),
        process=process if process is not None else FakeProcess(alive=False),
        harness=FakeHarness(ledgers),
    )


def _status_by_station(report) -> dict[str, StationCycleStatus]:
    return {result.slug: result.status for result in report.results}


# --------------------------------------------------------------------------
# I/O & Edge-Case Matrix
# --------------------------------------------------------------------------


def test_drained_station_is_reported_and_never_dispatched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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


def test_two_ready_stations_dispatch_in_the_same_cycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
        _seed_live_dispatch_journal(
            tmp_path, slug=slug, run_id="run-live", story_key="9.9"
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
    _seed_live_dispatch_journal(
        tmp_path, slug="pyforge-marshal", run_id="run-live", story_key="22.7"
    )
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


def test_skip_on_blocked_moves_to_the_next_story_and_reports_the_skip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-steward": ["12-7-live-ocp", "12-8-projects"]})
    (
        tmp_path / "_bmad-output" / "projects" / "pyforge-marshal" / "planning-artifacts"
    ).mkdir(parents=True)
    (
        tmp_path
        / "_bmad-output"
        / "projects"
        / "pyforge-marshal"
        / "planning-artifacts"
        / dispatch_fleet.QUEUE_CONFIG_FILENAME
    ).write_text(
        "skip_policies:\n"
        "  - station: steward\n"
        "    story: 12-7-live-ocp\n"
        "    reason: Requires a live OCP cluster.\n",
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


def test_a_halted_story_blocks_its_station_under_drain_to_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
        ledgers={
            "pyforge-marshal": (("22-7-fleet", "backlog"), ("22-8-next", "backlog"))
        },
        process=FakeProcess(alive=False),
        build_harness=harness,
    )
    assert harness.dispatched == []
    blocked = next(f for f in report.findings if f.code == "MRS-DRAIN-005")
    assert "22-7-fleet" in blocked.message
    assert "skip_on_blocked" in blocked.message
    assert _status_by_station(report)["pyforge-marshal"] is StationCycleStatus.BLOCKED


def test_a_halted_story_is_skipped_under_skip_on_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
        ledgers={
            "pyforge-marshal": (("22-7-fleet", "backlog"), ("22-8-next", "backlog"))
        },
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
    _seed_live_dispatch_journal(
        tmp_path, slug="pyforge-doctor", run_id="run-live", story_key="14.1"
    )
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


def test_merge_through_finalize_chains_the_stations_next_story(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
    vcs.merged_branches.add(dispatch_core.dispatch_worktree_branch("22.7"))
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


def test_order_overrides_decide_which_story_a_station_gets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": ["22-7-fleet", "22-8-next"]})
    (
        tmp_path / "_bmad-output" / "projects" / "pyforge-marshal" / "planning-artifacts"
    ).mkdir(parents=True, exist_ok=True)
    dispatch_fleet.queue_config_path(tmp_path).write_text(
        "order_overrides:\n  marshal:\n    - 22-8-next\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    harness = FakeBuildHarness()
    _cycle(
        tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        ledgers={
            "pyforge-marshal": (("22-7-fleet", "backlog"), ("22-8-next", "backlog"))
        },
        build_harness=harness,
    )
    assert harness.dispatched == [("pyforge-marshal", "22.8")]


def test_malformed_queue_override_file_is_reported_not_silently_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_git_repo(tmp_path)
    _seed_fleet(tmp_path, stories={"pyforge-marshal": []})
    (
        tmp_path / "_bmad-output" / "projects" / "pyforge-marshal" / "planning-artifacts"
    ).mkdir(parents=True, exist_ok=True)
    dispatch_fleet.queue_config_path(tmp_path).write_text(
        "order_overrides: [unbalanced\n", encoding="utf-8"
    )
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
    }
    base.update(overrides)
    return argparse.Namespace(**base)


def _run_drain(tmp_path: Path, args: argparse.Namespace, **kwargs) -> int:
    return run_fleet_drain(
        args,
        fs=FakeFs(),
        vcs=kwargs.get("vcs") or FakeVcs(tmp_path),
        build_harness=kwargs.get("build_harness") or FakeBuildHarness(),
        process=kwargs.get("process") or FakeProcess(alive=False),
        harness=FakeHarness(kwargs["ledgers"]),
    )


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
    code = _run_drain(
        tmp_path, _drain_args(mode="drain_everything"), ledgers={"pyforge-marshal": ()}
    )
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
    campaign = [
        argv
        for argv in process.spawned
        if "pyforge.marshal.dispatch_fleet_supervisor" in argv
    ]
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
    assert [
        argv
        for argv in process.spawned
        if "pyforge.marshal.dispatch_fleet_supervisor" in argv
    ] == []


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
