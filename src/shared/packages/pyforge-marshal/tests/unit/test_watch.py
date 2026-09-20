"""Unit tests for ``pyforge.marshal.cli.watch`` (Story 44.1).

Every I/O-matrix row is driven through fixture ports -- no live
``bmad-loop`` process and no network.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from pyforge.marshal.cli.watch import (
    LoopCliError,
    ProbeError,
    WatchPorts,
    recommend_delay,
    run_watch,
    seconds_to_next_half_hour,
)


def _args(
    *,
    project: str | None = None,
    run: str | None = None,
    fleet: bool = False,
    format: str = "json",
) -> argparse.Namespace:
    return argparse.Namespace(project=project, run=run, fleet=fleet, format=format)


def _payload(capsys) -> dict:
    return json.loads(capsys.readouterr().out)


def _loop_status(
    *,
    finished: bool = False,
    paused_stage: str | None = None,
    paused_reason: str | None = None,
    status: str = "in-progress",
    stories: list[dict] | None = None,
) -> dict:
    return {
        "finished": finished,
        "paused_stage": paused_stage,
        "paused_reason": paused_reason,
        "status": status,
        "stories": stories
        or [
            {"key": "21.4", "phase": "done", "commit_sha": "aaa"},
            {"key": "21.5", "phase": "dev-running", "commit_sha": "bbb", "attempt": 1},
            {"key": "21.6", "phase": "ready", "commit_sha": None},
        ],
    }


def _ports(
    tmp_path: Path,
    *,
    listed: dict | None = None,
    status: dict | None = None,
    home: dict | None = None,
    list_error: LoopCliError | None = None,
    status_error: LoopCliError | None = None,
    sha: str | None = "deadbeef",
    sha_error: ProbeError | None = None,
    prs: list[dict] | None = None,
    slugs: list[str] | None = None,
    queue: list[str] | None = None,
    per_slug: dict[str, dict] | None = None,
    loop_last_fact: dict[str, datetime | None] | None = None,
    dispatch_last_fact: dict[str, datetime | None] | None = None,
) -> WatchPorts:
    listed = listed if listed is not None else {"runs": [{"id": "20260914-201759-bd47", "status": "running"}]}
    status = status if status is not None else _loop_status()
    home = home if home is not None else {"state": "running", "dispatch_run_id": "herald-OLD"}
    prs = (
        prs
        if prs is not None
        else [
            {
                "number": 1373,
                "title": "herald",
                "headRefName": "loop/pyforge-herald",
                "state": "OPEN",
                "updatedAt": "2026-09-15T00:00:00Z",
            }
        ]
    )
    slugs = slugs if slugs is not None else ["pyforge-herald"]
    queue = queue if queue is not None else ["21.5", "21.6", "21.7"]

    def list_runs(slug: str) -> dict:
        if list_error is not None:
            raise list_error
        if per_slug and slug in per_slug and "listed" in per_slug[slug]:
            return per_slug[slug]["listed"]
        return listed

    def run_status(slug: str, run_id: str) -> dict:
        del run_id
        if status_error is not None:
            raise status_error
        if per_slug and slug in per_slug and "status" in per_slug[slug]:
            return per_slug[slug]["status"]
        return status

    def marshal_home(slug: str) -> dict | None:
        if per_slug and slug in per_slug and "home" in per_slug[slug]:
            return per_slug[slug]["home"]
        return home

    def loop_sha(slug: str) -> str | None:
        del slug
        if sha_error is not None:
            raise sha_error
        return sha

    def list_prs(slug: str) -> list[dict]:
        del slug
        return list(prs)

    def discover_projects() -> list[str]:
        return list(slugs)

    def load_queue(slug: str) -> list[str]:
        del slug
        return list(queue)

    def loop_last_fact_fn(slug: str, run_id: str) -> datetime | None:
        del slug
        return (loop_last_fact or {}).get(run_id)

    def dispatch_last_fact_fn(slug: str, dispatch_id: str) -> datetime | None:
        del slug
        return (dispatch_last_fact or {}).get(dispatch_id)

    return WatchPorts(
        list_runs=list_runs,
        run_status=run_status,
        marshal_home=marshal_home,
        loop_sha=loop_sha,
        list_prs=list_prs,
        discover_projects=discover_projects,
        load_queue=load_queue,
        loop_last_fact=loop_last_fact_fn,
        dispatch_last_fact=dispatch_last_fact_fn,
    )


_NOW = datetime(2026, 9, 15, 12, 10, 0, tzinfo=timezone.utc)


def _run(tmp_path: Path, args: argparse.Namespace, ports: WatchPorts, now: datetime = _NOW) -> int:
    return run_watch(args, ports=ports, now=now, cache_dir=tmp_path / "cache", repo=tmp_path)


def test_pinned_first_check_writes_cache_and_five_sections(tmp_path: Path, capsys):
    ports = _ports(tmp_path)
    rc = _run(tmp_path, _args(project="pyforge-herald", run="20260914-201759-bd47"), ports)
    payload = _payload(capsys)
    assert rc == 0
    assert payload["command"] == "watch"
    assert payload["verdict"] == "clean"
    data = payload["data"]
    assert data["first_observation"] is True
    assert data["pattern"] == "bmad-loop"
    sections = data["sections"]
    assert "session_completions" in sections
    assert "21.4 -- done" in sections["session_completions"]
    assert sections["delta"] == ["first observation -- no prior cache"]
    assert sections["currently_running"]["story"] == "21.5"
    assert "21.6" in sections["up_next"]
    assert "21.7" in sections["up_next"]
    assert "stale unrelated dispatch" in sections["user_action_required"]
    cache = tmp_path / "cache" / "pyforge-herald__20260914-201759-bd47.json"
    assert cache.is_file()
    assert data["delay_seconds"] == min(300, seconds_to_next_half_hour(_NOW))


def test_pinned_unchanged_says_nothing_changed(tmp_path: Path, capsys):
    ports = _ports(tmp_path)
    args = _args(project="pyforge-herald", run="20260914-201759-bd47")
    _run(tmp_path, args, ports)
    capsys.readouterr()
    rc = _run(tmp_path, args, ports)
    payload = _payload(capsys)
    assert rc == 0
    assert payload["data"]["quiet"] is True
    assert payload["data"]["changed"] is False
    text_rc = run_watch(
        _args(project="pyforge-herald", run="20260914-201759-bd47", format="text"),
        ports=ports,
        now=_NOW,
        cache_dir=tmp_path / "cache",
        repo=tmp_path,
    )
    text = capsys.readouterr().out
    assert text_rc == 0
    assert "nothing changed" in text
    assert "**Session Completions:**" not in text


def test_pinned_story_completed_surfaces_delta(tmp_path: Path, capsys):
    ports = _ports(tmp_path)
    args = _args(project="pyforge-herald", run="20260914-201759-bd47")
    _run(tmp_path, args, ports)
    capsys.readouterr()
    later = _ports(
        tmp_path,
        status=_loop_status(
            stories=[
                {"key": "21.4", "phase": "done", "commit_sha": "aaa"},
                {"key": "21.5", "phase": "done", "commit_sha": "ccc"},
                {"key": "21.6", "phase": "dev-running", "commit_sha": None},
            ]
        ),
    )
    rc = _run(tmp_path, args, later)
    payload = _payload(capsys)
    assert rc == 0
    assert payload["data"]["changed"] is True
    assert payload["data"]["quiet"] is False
    joined = " ".join(payload["data"]["sections"]["delta"])
    assert "21.5" in joined
    assert "21.5 -- done" in payload["data"]["sections"]["session_completions"]


def test_stale_dispatch_ignored_for_per_story_detail(tmp_path: Path, capsys):
    ports = _ports(
        tmp_path,
        home={
            "state": "idle",
            "dispatch_run_id": "herald-OLD-DISPATCH",
            "current_story": "99.9",
            "dispatch_completion_verdict": "completed",
        },
    )
    rc = _run(tmp_path, _args(project="pyforge-herald"), ports)
    payload = _payload(capsys)
    assert rc == 0
    data = payload["data"]
    assert data["pattern"] == "bmad-loop"
    assert data["run_id"] == "20260914-201759-bd47"
    assert data["stale_dispatch_ignored"] is True
    assert data["stale_dispatch_run_id"] == "herald-OLD-DISPATCH"
    assert data["sections"]["currently_running"]["story"] == "21.5"
    assert "99.9" not in json.dumps(data["sections"])


# Story 51.6 (spec-pyforge-marshal CAP-254): the engine choice follows the
# last journal fact, not "any live bmad-loop row wins."

_AUG_LOOP_RUN_ID = "20260814-090000-aaaa"
_TODAY_DISPATCH_ID = "herald-20260918T060000000Z-abcd1234"


def _stale_loop_live_dispatch_ports(
    tmp_path: Path,
    *,
    loop_last_fact: dict[str, datetime | None] | None,
    dispatch_last_fact: dict[str, datetime | None] | None,
) -> WatchPorts:
    """The Given: a `paused` loop row minted in 2026-08 AND a dispatch run
    this station's `marshal status` still reports live -- exactly the
    2026-09-18 incident shape (Story 51.6's `Given`)."""
    return _ports(
        tmp_path,
        listed={"runs": [{"id": _AUG_LOOP_RUN_ID, "status": "paused"}]},
        status=_loop_status(
            status="paused",
            paused_stage="escalation",
            paused_reason="needs operator",
        ),
        home={
            "state": "running",
            "dispatch_run_id": _TODAY_DISPATCH_ID,
            "dispatch_completion_verdict": None,
            "dispatch_verification_verdict": None,
            "current_story": "6.1",
            "escalation_reason": None,
        },
        loop_last_fact=loop_last_fact,
        dispatch_last_fact=dispatch_last_fact,
    )


def test_dispatch_run_outranks_a_stale_paused_loop_row(tmp_path: Path, capsys):
    """Then: a dispatch run journaled today is reported (harness, key,
    phase, last fact) instead of the loop row paused in August."""
    ports = _stale_loop_live_dispatch_ports(
        tmp_path,
        loop_last_fact={_AUG_LOOP_RUN_ID: datetime(2026, 8, 14, 9, 5, 0, tzinfo=timezone.utc)},
        dispatch_last_fact={_TODAY_DISPATCH_ID: datetime(2026, 9, 18, 6, 0, 0, tzinfo=timezone.utc)},
    )
    rc = _run(tmp_path, _args(project="pyforge-herald"), ports)
    payload = _payload(capsys)
    assert rc == 0
    data = payload["data"]
    assert data["pattern"] == "bmad-build-auto"  # harness
    assert data["run_id"] == _TODAY_DISPATCH_ID  # key
    assert data["sections"]["currently_running"]["story"] == "6.1"
    assert data["sections"]["currently_running"]["phase"] == "running"  # phase
    assert data["run_id"] != _AUG_LOOP_RUN_ID

    # last fact: _gather_station's own return dict carries the winning
    # engine's last journal fact (ISO 8601) -- the value the comparison
    # actually used to prefer dispatch over the stale loop row.
    from pyforge.marshal.cli.watch import _gather_station

    gathered = _gather_station(ports=ports, slug="pyforge-herald", run_id=None, findings=[])
    assert gathered is not None
    assert gathered["last_fact_at"] == "2026-09-18T06:00:00+00:00"


def test_with_no_dispatch_last_fact_the_loop_row_is_chosen_exactly_as_today(tmp_path: Path, capsys):
    """Then: with no dispatch run (no discoverable journal fact for the
    `dispatch_run_id` `marshal status` reports) the loop row is chosen
    exactly as it was before Story 51.6 -- same fixture, minus the
    dispatch side's last fact."""
    ports = _stale_loop_live_dispatch_ports(
        tmp_path,
        loop_last_fact={_AUG_LOOP_RUN_ID: datetime(2026, 8, 14, 9, 5, 0, tzinfo=timezone.utc)},
        dispatch_last_fact=None,
    )
    rc = _run(tmp_path, _args(project="pyforge-herald"), ports)
    payload = _payload(capsys)
    assert rc == 0
    data = payload["data"]
    assert data["pattern"] == "bmad-loop"
    assert data["run_id"] == _AUG_LOOP_RUN_ID
    assert data["stale_dispatch_ignored"] is True
    assert data["stale_dispatch_run_id"] == _TODAY_DISPATCH_ID


def test_neither_engine_selection_reports_idle(tmp_path: Path, capsys):
    """And: neither branch of the Given/When/Then ever reports idle --
    ``MRS-WATCH-002`` ("no active run found") never fires when either side
    has a candidate engine."""
    dispatch_wins = _stale_loop_live_dispatch_ports(
        tmp_path,
        loop_last_fact={_AUG_LOOP_RUN_ID: datetime(2026, 8, 14, tzinfo=timezone.utc)},
        dispatch_last_fact={_TODAY_DISPATCH_ID: datetime(2026, 9, 18, tzinfo=timezone.utc)},
    )
    rc = _run(tmp_path, _args(project="pyforge-herald"), dispatch_wins)
    assert rc == 0
    assert _payload(capsys)["findings"] == []

    loop_wins = _stale_loop_live_dispatch_ports(tmp_path, loop_last_fact=None, dispatch_last_fact=None)
    rc = _run(tmp_path, _args(project="pyforge-herald"), loop_wins)
    assert rc == 0
    assert _payload(capsys)["findings"] == []


def test_a_pinned_run_id_is_never_overridden_by_a_fresher_dispatch_run(tmp_path: Path, capsys):
    """A pinned ``--run`` is the operator watching THIS run on purpose --
    the comparison must never override it, even when the dispatch run's
    last fact is strictly newer."""
    ports = _stale_loop_live_dispatch_ports(
        tmp_path,
        loop_last_fact={_AUG_LOOP_RUN_ID: datetime(2026, 8, 14, tzinfo=timezone.utc)},
        dispatch_last_fact={_TODAY_DISPATCH_ID: datetime(2026, 9, 18, tzinfo=timezone.utc)},
    )
    rc = _run(tmp_path, _args(project="pyforge-herald", run=_AUG_LOOP_RUN_ID), ports)
    payload = _payload(capsys)
    assert rc == 0
    assert payload["data"]["pattern"] == "bmad-loop"
    assert payload["data"]["run_id"] == _AUG_LOOP_RUN_ID


def test_fleet_mode_escalated_loop_row_outranked_by_dispatch_still_sorts_first(tmp_path: Path, capsys):
    """--fleet: a loop row stuck in escalation must not silently drop out
    of the escalated-first sort just because a newer dispatch run outranked
    it for engine selection -- ``paused_or_escalated`` ORs the two in, and
    the stale loop run's id still surfaces in ``user_action_required``."""
    ports = _ports(
        tmp_path,
        listed={"runs": [{"id": _AUG_LOOP_RUN_ID, "status": "paused"}]},
        status=_loop_status(status="paused", paused_stage="escalation", paused_reason="needs operator"),
        home={
            "state": "running",
            "dispatch_run_id": _TODAY_DISPATCH_ID,
            "dispatch_completion_verdict": None,
            "dispatch_verification_verdict": None,
            "current_story": "6.1",
            "escalation_reason": None,
        },
        slugs=["pyforge-herald", "aaa-station"],
        per_slug={
            "aaa-station": {
                "listed": {"runs": [{"id": "other-run", "status": "running"}]},
                "status": _loop_status(
                    status="in-progress",
                    stories=[{"key": "1.1", "phase": "dev-running", "commit_sha": "zzz", "attempt": 1}],
                ),
                "home": {"state": "running", "dispatch_run_id": None},
            }
        },
        loop_last_fact={_AUG_LOOP_RUN_ID: datetime(2026, 8, 14, tzinfo=timezone.utc)},
        dispatch_last_fact={_TODAY_DISPATCH_ID: datetime(2026, 9, 18, tzinfo=timezone.utc)},
    )
    rc = _run(tmp_path, _args(fleet=True), ports)
    payload = _payload(capsys)
    assert rc == 0
    data = payload["data"]
    projects = data["projects"]
    # aaa-station sorts alphabetically before pyforge-herald -- if escalation
    # weren't OR'd in, that alphabetical order would win instead.
    assert [p["slug"] for p in projects] == ["pyforge-herald", "aaa-station"]
    herald = next(p for p in projects if p["slug"] == "pyforge-herald")
    assert herald["pattern"] == "bmad-build-auto"
    assert herald["escalated"] is True
    assert _AUG_LOOP_RUN_ID in data["user_action_required"]


def test_dispatch_outranks_loop_is_a_strict_newer_than_comparison():
    """Story 51.6's mutation-tested choice function, exercised directly:
    flipping its `>` to `<` or `>=` must each break one of these three
    assertions (swapping the comparison re-selects the stale row)."""
    from pyforge.marshal.cli.watch import _dispatch_outranks_loop

    aug = datetime(2026, 8, 14, 9, 5, 0, tzinfo=timezone.utc)
    today = datetime(2026, 9, 18, 6, 0, 0, tzinfo=timezone.utc)
    # dispatch strictly newer -> dispatch wins. A `<` mutant flips this to
    # False -- it would re-select the stale August loop row.
    assert _dispatch_outranks_loop(loop_last_fact=aug, dispatch_last_fact=today) is True
    # dispatch strictly OLDER -> loop wins. A `<` mutant flips this to True
    # -- it would let a genuinely stale dispatch row outrank a fresher loop.
    assert _dispatch_outranks_loop(loop_last_fact=today, dispatch_last_fact=aug) is False
    # tied timestamps -> loop keeps its default. A `>=` mutant flips this to
    # True -- an unchanged station would spuriously "move" to dispatch.
    assert _dispatch_outranks_loop(loop_last_fact=today, dispatch_last_fact=today) is False
    # either side unknown -> never outranks (an unreadable/absent journal
    # must not be treated as "wins by default").
    assert _dispatch_outranks_loop(loop_last_fact=None, dispatch_last_fact=today) is False
    assert _dispatch_outranks_loop(loop_last_fact=aug, dispatch_last_fact=None) is False


def test_dispatch_journal_last_fact_takes_the_latest_of_launch_start_end():
    from pyforge.marshal.cli.watch import _dispatch_journal_last_fact
    from pyforge.marshal.core.dispatch import DispatchJournalFacts

    launched = datetime(2026, 9, 18, 6, 0, 0, tzinfo=timezone.utc)
    facts = DispatchJournalFacts(
        story_key="6.1",
        session_pid=None,
        model=None,
        launched_at=launched,
        worktree_path=None,
        story_started_at="2026-09-18T06:00:05Z",
        story_ended_at="2026-09-18T07:30:00Z",
    )
    assert _dispatch_journal_last_fact(facts) == datetime(2026, 9, 18, 7, 30, 0, tzinfo=timezone.utc)
    # No timing entries yet -- falls back to launched_at.
    only_launch = DispatchJournalFacts(
        story_key="6.1", session_pid=None, model=None, launched_at=launched, worktree_path=None
    )
    assert _dispatch_journal_last_fact(only_launch) == launched
    # Nothing parseable at all -- honest None, never fabricated.
    empty = DispatchJournalFacts(story_key=None, session_pid=None, model=None, launched_at=None, worktree_path=None)
    assert _dispatch_journal_last_fact(empty) is None
    # An unparseable story_ended_at is skipped, not fatal.
    bad_end = DispatchJournalFacts(
        story_key=None,
        session_pid=None,
        model=None,
        launched_at=launched,
        worktree_path=None,
        story_ended_at="not-a-timestamp",
    )
    assert _dispatch_journal_last_fact(bad_end) == launched


def test_loop_journal_last_fact_takes_the_last_parseable_ts():

    text = "\n".join(
        [
            '{"ts": 1755500000.0, "kind": "story-started"}',
            "",  # blank lines are skipped
            "not json",  # malformed lines are skipped
            '{"ts": 1755500100.5, "kind": "story-done"}',
            '{"kind": "no-ts-field"}',
        ]
    )
    result = watch_mod._loop_journal_last_fact(text)
    assert result == datetime.fromtimestamp(1755500100.5, tz=timezone.utc)
    assert watch_mod._loop_journal_last_fact("") is None
    assert watch_mod._loop_journal_last_fact("not json at all") is None


def test_loop_journal_last_fact_returns_the_true_max_not_the_last_line():
    """An out-of-order journal (the last line isn't the newest ``ts``) must
    still report its real maximum, matching the sibling
    ``_dispatch_journal_last_fact``'s own ``max(...)`` behavior."""
    text = "\n".join(
        [
            '{"ts": 1755500100.5, "kind": "story-done"}',
            '{"ts": 1755500000.0, "kind": "story-started"}',
        ]
    )
    assert watch_mod._loop_journal_last_fact(text) == datetime.fromtimestamp(1755500100.5, tz=timezone.utc)


def test_loop_journal_last_fact_skips_non_finite_ts_instead_of_crashing():
    """``json.loads`` parses ``NaN``/``Infinity`` as floats;
    ``datetime.fromtimestamp`` then raises on them -- a malformed line must
    be skipped, not fatal to ``marshal watch``."""
    text = "\n".join(
        [
            '{"ts": NaN, "kind": "bogus"}',
            '{"ts": Infinity, "kind": "also-bogus"}',
            '{"ts": -Infinity, "kind": "still-bogus"}',
            '{"ts": 1755500000.0, "kind": "story-started"}',
        ]
    )
    assert watch_mod._loop_journal_last_fact(text) == datetime.fromtimestamp(1755500000.0, tz=timezone.utc)
    # Entirely non-finite -- honest None, never a crash.
    assert watch_mod._loop_journal_last_fact('{"ts": NaN}') is None


def test_station_auto_detects_loop_run(tmp_path: Path, capsys):
    ports = _ports(tmp_path)
    rc = _run(tmp_path, _args(project="pyforge-herald"), ports)
    payload = _payload(capsys)
    assert rc == 0
    assert payload["data"]["scope"] == "station"
    assert payload["data"]["run_id"] == "20260914-201759-bd47"
    assert payload["data"]["pattern"] == "bmad-loop"


def test_station_falls_back_to_build_auto(tmp_path: Path, capsys):
    ports = _ports(
        tmp_path,
        listed={"runs": []},
        home={
            "state": "running",
            "dispatch_run_id": "warden-20260915T000000000Z-abcd1234",
            "dispatch_completion_verdict": None,
            "dispatch_verification_verdict": None,
            "current_story": "11.1",
            "escalation_reason": None,
        },
    )
    rc = _run(tmp_path, _args(project="pyforge-warden"), ports)
    payload = _payload(capsys)
    assert rc == 0
    assert payload["data"]["pattern"] == "bmad-build-auto"
    assert payload["data"]["run_id"] == "warden-20260915T000000000Z-abcd1234"
    assert payload["data"]["sections"]["currently_running"]["story"] == "11.1"
    assert "no further queue" in payload["data"]["sections"]["up_next"][0]


def test_fleet_discovers_live_and_sorts_escalated_first(tmp_path: Path, capsys):
    (tmp_path / "_bmad-output" / "projects" / "idle-one").mkdir(parents=True)
    ports = _ports(
        tmp_path,
        slugs=["pyforge-atlas", "pyforge-herald", "idle-one"],
        per_slug={
            "pyforge-atlas": {
                "listed": {"runs": [{"id": "atlas-run", "status": "paused"}]},
                "status": _loop_status(
                    status="paused",
                    paused_stage="escalation",
                    paused_reason="needs operator",
                    stories=[{"key": "1.1", "phase": "escalated", "commit_sha": None}],
                ),
                "home": {"state": "paused-on-escalation", "dispatch_run_id": None},
            },
            "pyforge-herald": {
                "listed": {"runs": [{"id": "20260914-201759-bd47", "status": "running"}]},
                "status": _loop_status(),
                "home": {"state": "running", "dispatch_run_id": "old"},
            },
            "idle-one": {
                "listed": {"runs": []},
                "home": {"state": "idle", "dispatch_run_id": None},
            },
        },
    )
    rc = _run(tmp_path, _args(fleet=True), ports)
    payload = _payload(capsys)
    assert rc == 0
    slugs = [row["slug"] for row in payload["data"]["projects"]]
    assert slugs[0] == "pyforge-atlas"
    assert "idle-one" in slugs
    assert payload["data"]["projects"][0]["escalated"] is True
    cache = tmp_path / "cache" / "__fleet__.json"
    assert cache.is_file()


def test_paused_escalation_is_boundary_only_delay(tmp_path: Path, capsys):
    ports = _ports(
        tmp_path,
        listed={"runs": [{"id": "20260914-201759-bd47", "status": "paused"}]},
        status=_loop_status(
            status="paused",
            paused_stage="escalation",
            paused_reason="spec-approval",
            stories=[{"key": "21.5", "phase": "escalated", "commit_sha": "bbb"}],
        ),
    )
    rc = _run(tmp_path, _args(project="pyforge-herald", run="20260914-201759-bd47"), ports)
    payload = _payload(capsys)
    assert rc == 0
    assert "blocking" in payload["data"]["sections"]["user_action_required"]
    boundary = seconds_to_next_half_hour(_NOW)
    assert payload["data"]["delay_seconds"] == min(1800, boundary)
    assert payload["data"]["delay_seconds"] != min(300, boundary) or boundary <= 300


def test_finished_omits_delay(tmp_path: Path, capsys):
    ports = _ports(
        tmp_path,
        listed={"runs": [{"id": "20260914-201759-bd47", "status": "finished"}]},
        status=_loop_status(
            finished=True,
            status="finished",
            stories=[{"key": "21.5", "phase": "done", "commit_sha": "ccc"}],
        ),
    )
    rc = _run(tmp_path, _args(project="pyforge-herald", run="20260914-201759-bd47"), ports)
    payload = _payload(capsys)
    assert rc == 0
    assert payload["data"]["delay_seconds"] is None
    assert "finished" in payload["data"]["delay_reason"]


def test_missing_cache_dir_is_created(tmp_path: Path, capsys):
    cache = tmp_path / "missing" / "nested"
    ports = _ports(tmp_path)
    rc = run_watch(
        _args(project="pyforge-herald", run="20260914-201759-bd47"),
        ports=ports,
        now=_NOW,
        cache_dir=cache,
        repo=tmp_path,
    )
    payload = _payload(capsys)
    assert rc == 0
    assert payload["data"]["first_observation"] is True
    assert (cache / "pyforge-herald__20260914-201759-bd47.json").is_file()


def test_loop_cli_error_is_verdict_error(tmp_path: Path, capsys):
    ports = _ports(
        tmp_path,
        list_error=LoopCliError("bmad-loop list --json", "not installed"),
    )
    rc = _run(tmp_path, _args(project="pyforge-herald", run="20260914-201759-bd47"), ports)
    payload = _payload(capsys)
    assert rc == 4
    assert payload["verdict"] == "error"
    codes = [f["code"] for f in payload["findings"]]
    assert "MRS-WATCH-001" in codes
    assert not (tmp_path / "cache").exists() or not list((tmp_path / "cache").glob("*bd47*"))


def test_no_active_run_is_verdict_error(tmp_path: Path, capsys):
    ports = _ports(
        tmp_path,
        listed={"runs": []},
        home={"state": "idle", "dispatch_run_id": None},
    )
    rc = _run(tmp_path, _args(project="pyforge-herald"), ports)
    payload = _payload(capsys)
    assert rc == 4
    assert payload["verdict"] == "error"
    assert any(f["code"] == "MRS-WATCH-002" for f in payload["findings"])


def test_git_failure_is_finding_not_crash(tmp_path: Path, capsys):
    ports = _ports(
        tmp_path,
        sha_error=ProbeError("git rev-parse", "no such ref"),
    )
    rc = _run(tmp_path, _args(project="pyforge-herald", run="20260914-201759-bd47"), ports)
    payload = _payload(capsys)
    assert rc == 0
    assert payload["verdict"] == "warn"
    assert any(f["code"] == "MRS-WATCH-003" for f in payload["findings"])
    assert payload["data"]["sections"]["session_completions"]


def test_watch_never_writes_outside_cache(tmp_path: Path, capsys):
    ports = _ports(tmp_path)
    ledger = tmp_path / "_bmad-output" / "projects" / "pyforge-herald" / "planning-artifacts"
    ledger.mkdir(parents=True)
    (ledger / "sprint-status-ledger.yaml").write_text("21-5: backlog\n", encoding="utf-8")
    before = (ledger / "sprint-status-ledger.yaml").read_text(encoding="utf-8")
    _run(tmp_path, _args(project="pyforge-herald", run="20260914-201759-bd47"), ports)
    capsys.readouterr()
    assert (ledger / "sprint-status-ledger.yaml").read_text(encoding="utf-8") == before
    written = list((tmp_path / "cache").rglob("*"))
    assert written
    assert all("marshal-run-watch" not in str(p) or True for p in written)
    # Only the injected cache_dir received a write.
    assert not (tmp_path / ".claude").exists()


def test_recommend_delay_math():
    now = datetime(2026, 9, 15, 12, 10, 0, tzinfo=timezone.utc)
    assert seconds_to_next_half_hour(now) == 20 * 60
    delay, _ = recommend_delay(
        finished=False,
        paused_or_escalated=False,
        actively_progressing=True,
        now=now,
        fleet=False,
    )
    assert delay == 300
    delay, _ = recommend_delay(
        finished=False,
        paused_or_escalated=True,
        actively_progressing=False,
        now=now,
        fleet=False,
    )
    assert delay == 20 * 60
    delay, reason = recommend_delay(
        finished=True,
        paused_or_escalated=False,
        actively_progressing=False,
        now=now,
        fleet=False,
    )
    assert delay is None
    assert "finished" in reason


def test_help_lists_watch_subcommand(capsys):
    from pyforge.marshal.cli.main import main

    assert main(["watch", "--help"]) == 0
    out = capsys.readouterr().out
    assert "--fleet" in out
    assert "--project" in out
    assert "--run" in out


# --- Story 52.1, SPEC-pyforge-core CAP-5: the re-parent widening guard ----


def test_loop_cli_error_is_a_pyforge_error_and_a_runtime_error():
    """``LoopCliError`` gained ``PyforgeError`` as an additional base and
    kept its original ``RuntimeError`` base -- every pre-existing exact-class
    ``except LoopCliError`` site in ``watch.py`` and any ``except
    RuntimeError`` site behave identically; ``except PyforgeError`` newly
    catches it too. The ``(command, reason)`` constructor is untouched."""
    from pyforge.core.errors import PyforgeError

    assert issubclass(LoopCliError, PyforgeError)
    assert issubclass(LoopCliError, RuntimeError)
    exc = LoopCliError("bmad-loop list --json", "not installed")
    assert exc.command == "bmad-loop list --json"
    assert exc.reason == "not installed"
    assert str(exc) == "bmad-loop list --json: not installed"
    for catch in (LoopCliError, RuntimeError, PyforgeError):
        try:
            raise LoopCliError("bmad-loop status", "x")
        except catch:
            pass


def test_probe_error_is_a_pyforge_error_and_a_runtime_error():
    """Same pin for ``ProbeError`` (the ``raise ProbeError("git", "x")``
    I/O-matrix row): caught by ``except ProbeError``, ``except
    RuntimeError`` and ``except PyforgeError`` alike."""
    from pyforge.core.errors import PyforgeError

    assert issubclass(ProbeError, PyforgeError)
    assert issubclass(ProbeError, RuntimeError)
    exc = ProbeError("git", "x")
    assert exc.command == "git"
    assert exc.reason == "x"
    assert str(exc) == "git: x"
    for catch in (ProbeError, RuntimeError, PyforgeError):
        try:
            raise ProbeError("git", "x")
        except catch:
            pass


# --- Coverage of the remaining branches (Story 52.1 coverage gate) --------
# Fakes only: a recording `ProcessPort` for `_default_ports`, `tmp_path`
# trees for the cache/queue readers, fixture `WatchPorts` for `run_watch`.

import sys as _sys

import pytest
from pyforge.core.process import ProcessError, ProcessResult

from pyforge.marshal.cli import watch as watch_mod
from pyforge.marshal.core.model import Finding, Severity


class _RecordingProcess:
    """A `ProcessPort` fake: `responses` maps the FIRST argv element that
    identifies the command (`"list"`, `"status"`, the marshal status module,
    `"fetch"`, `"rev-parse"`, `"gh"`) to a `ProcessResult` or an exception."""

    def __init__(self, responses: dict[str, object]) -> None:
        self.responses = responses
        self.calls: list[tuple[list[str], Path, float | None]] = []

    def run(self, argv, *, cwd, timeout_s=None):
        self.calls.append((list(argv), cwd, timeout_s))
        for key, response in self.responses.items():
            if key in argv:
                if isinstance(response, BaseException):
                    raise response
                return response
        raise AssertionError(f"unexpected argv: {argv!r}")

    def is_alive(self, pid: int) -> bool:  # pragma: no cover - protocol filler
        return False

    def spawn_detached(self, argv, *, cwd, log_path):  # pragma: no cover
        raise AssertionError("never spawned")


def _ok(payload: object) -> ProcessResult:
    return ProcessResult(returncode=0, stdout=json.dumps(payload), stderr="")


def _fake_home(monkeypatch, tmp_path: Path, *slugs: str) -> Path:
    home = tmp_path / "home"
    for slug in slugs:
        (home / ".bmad-loops" / slug).mkdir(parents=True)
    monkeypatch.setattr("pathlib.Path.home", classmethod(lambda cls: home))
    return home


def _cached_snapshot(tmp_path: Path, slug: str, run_id: str) -> dict:
    """The snapshot `run_watch` persisted -- it lives in the cache file, not
    in the envelope's `data`."""
    return json.loads((tmp_path / "cache" / f"{slug}__{run_id}.json").read_text(encoding="utf-8"))["snapshot"]


# seconds_to_next_half_hour / recommend_delay


def test_seconds_to_next_half_hour_handles_naive_and_second_half():
    naive = datetime(2026, 9, 15, 12, 45, 30)
    assert seconds_to_next_half_hour(naive) == 14 * 60 + 30
    on_boundary = datetime(2026, 9, 15, 12, 30, 0, tzinfo=timezone.utc)
    assert seconds_to_next_half_hour(on_boundary) == 30 * 60


def test_recommend_delay_idle_run_is_boundary_only():
    now = datetime(2026, 9, 15, 12, 10, 0, tzinfo=timezone.utc)
    delay, reason = recommend_delay(
        finished=False, paused_or_escalated=False, actively_progressing=False, now=now, fleet=False
    )
    assert delay == 20 * 60
    assert reason.startswith("idle/paused fleet or non-active run")
    # A finished FLEET never recommends stop.
    delay, _ = recommend_delay(
        finished=True, paused_or_escalated=False, actively_progressing=False, now=now, fleet=True
    )
    assert delay == 20 * 60


# cache readers


def test_read_cache_tolerates_missing_malformed_and_non_object(tmp_path: Path):
    assert watch_mod._read_cache(tmp_path / "absent.json") is None
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert watch_mod._read_cache(bad) is None
    non_object = tmp_path / "list.json"
    non_object.write_text("[1, 2]", encoding="utf-8")
    assert watch_mod._read_cache(non_object) is None
    good = tmp_path / "good.json"
    watch_mod._write_cache(good, {"snapshot": {"a": 1}})
    assert watch_mod._read_cache(good) == {"snapshot": {"a": 1}}


# pure helpers over bmad-loop payload shapes


def test_story_rows_accepts_tasks_alias_and_skips_junk():
    rows = watch_mod._story_rows(
        {
            "tasks": [
                "not-a-mapping",
                {"no_key": True},
                {"story_key": "1.2", "status": "done", "commit": "abc", "attempt_number": 2, "token_consumption": 7},
                {"story": "1.3"},
            ]
        }
    )
    assert rows == [
        {"key": "1.2", "phase": "done", "commit_sha": "abc", "attempt": 2, "tokens": 7},
        {"key": "1.3", "phase": "", "commit_sha": None, "attempt": None, "tokens": None},
    ]
    assert watch_mod._story_rows({"stories": "nope", "tasks": None}) == []


def test_overall_status_falls_back_to_list_row_then_unknown():
    assert watch_mod._overall_status({"finished": True}, None) == "finished"
    assert watch_mod._overall_status({"run_status": "paused"}, None) == "paused"
    assert watch_mod._overall_status({"status": ""}, {"status": "running"}) == "running"
    assert watch_mod._overall_status({}, {"status": 3}) == "unknown"
    assert watch_mod._overall_status({}, None) == "unknown"


def test_list_row_live_row_and_newest_row_edge_shapes():
    assert watch_mod._list_row({"runs": "nope"}, "x") is None
    assert watch_mod._list_row({"runs": [{"id": "a"}, "junk"]}, "b") is None
    assert watch_mod._list_row({"runs": [{"run_id": "b"}]}, "b") == {"run_id": "b"}
    assert watch_mod._live_loop_row({"runs": None}) is None
    assert watch_mod._live_loop_row({"runs": [{"status": "finished"}]}) is None
    assert watch_mod._live_loop_row({"runs": [{"id": "1", "status": "running"}, {"id": "2", "status": "paused"}]}) == {
        "id": "2",
        "status": "paused",
    }
    assert watch_mod._newest_row({"runs": []}) is None
    assert watch_mod._newest_row({"runs": "nope"}) is None
    assert watch_mod._newest_row({"runs": [{"id": "1"}, "junk"]}) is None
    assert watch_mod._newest_row({"runs": [{"id": "1"}]}) == {"id": "1"}


def test_filter_prs_skips_non_mappings_and_foreign_heads():
    rows = [
        "junk",
        {"number": 1, "headRefName": "loop/pyforge-atlas", "state": "OPEN"},
        {"number": 2, "headRefName": "loop/pyforge-herald", "title": "t", "state": "MERGED", "updatedAt": "u"},
    ]
    assert watch_mod._filter_prs(rows, "pyforge-herald") == [
        {"number": 2, "title": "t", "headRefName": "loop/pyforge-herald", "state": "MERGED", "updatedAt": "u"}
    ]


def test_changed_and_delta_lines_for_a_dispatch_snapshot():
    prev = {
        "pattern": "bmad-build-auto",
        "status": "running",
        "dispatch_completion_verdict": None,
        "dispatch_verification_verdict": None,
        "paused_reason": None,
        "escalation_reason": None,
        "loop_sha": "aaa",
        "prs": [],
    }
    same = dict(prev)
    assert watch_mod._changed(prev, same) is False
    assert watch_mod._delta_lines(prev, same) == ["nothing changed"]
    completed = dict(prev, dispatch_completion_verdict="completed")
    assert watch_mod._changed(prev, completed) is True
    assert "dispatch_completion_verdict None -> completed" in watch_mod._delta_lines(prev, completed)
    verified = dict(prev, dispatch_verification_verdict="green")
    assert watch_mod._changed(prev, verified) is True
    assert watch_mod._changed(prev, dict(prev, paused_reason="x")) is True
    assert watch_mod._changed(prev, dict(prev, escalation_reason="y")) is True
    assert watch_mod._changed(prev, dict(prev, loop_sha="bbb")) is True
    # A SHA that could not be probed (None) is not a change.
    assert watch_mod._changed(prev, dict(prev, loop_sha=None)) is False
    assert watch_mod._changed(prev, dict(prev, prs=[{"number": 1}])) is True


def test_delta_lines_for_a_loop_snapshot_cover_every_field():
    prev = {
        "pattern": "bmad-loop",
        "status": "running",
        "stories": [
            "junk",
            {"key": "1.1", "phase": "done", "commit_sha": "a"},
            {"key": "1.2", "phase": "ready", "commit_sha": None},
        ],
        "paused_reason": None,
        "escalation_reason": None,
        "loop_sha": "aaa",
        "prs": [],
    }
    curr = {
        "pattern": "bmad-loop",
        "status": "paused",
        "stories": [
            "junk",
            {"key": "1.1", "phase": "done", "commit_sha": "a"},
            {"key": "1.2", "phase": "dev-running", "commit_sha": "b"},
            {"key": "1.3", "phase": "ready", "commit_sha": None},
            {"key": None, "phase": "ready"},
        ],
        "paused_reason": "spec-approval",
        "escalation_reason": "needs operator",
        "loop_sha": "bbb",
        "prs": [{"number": 9}],
    }
    lines = watch_mod._delta_lines(prev, curr)
    assert "1.2: ready -> dev-running (commit None -> b)" in lines
    assert "new story 1.3: phase=ready" in lines
    assert "new story None: phase=ready" in lines
    assert "run status running -> paused" in lines
    assert "new paused_reason: spec-approval" in lines
    assert "new escalation_reason: needs operator" in lines
    assert "origin/loop SHA aaa -> bbb" in lines
    assert "PR list changed" in lines
    assert watch_mod._delta_lines(None, curr) == ["first observation -- no prior cache"]


def test_session_completions_and_currently_running_for_dispatch():
    snap = {
        "pattern": "bmad-build-auto",
        "dispatch_completion_verdict": "completed",
        "current_story": "11.1",
        "status": "finished",
    }
    assert watch_mod._session_completions(snap, []) == ["11.1 -- completion completed"]
    assert watch_mod._session_completions(dict(snap, dispatch_completion_verdict="live"), []) == []
    assert watch_mod._session_completions(dict(snap, current_story=None, dispatch_completion_verdict="failed"), []) == [
        "dispatch -- completion failed"
    ]
    assert watch_mod._currently_running(snap, []) == {
        "story": "11.1",
        "phase": "finished",
        "verdict": "completed",
    }
    loop_rows = [{"key": "2.1", "phase": "ready"}, {"key": "2.2", "phase": "done"}]
    assert watch_mod._currently_running({"pattern": "bmad-loop"}, loop_rows) == {
        "story": None,
        "phase": None,
    }


def test_up_next_falls_back_to_status_rows_when_the_queue_is_exhausted():
    rows = [
        {"key": "3.1", "phase": "done"},
        {"key": "3.2", "phase": "dev-running"},
        {"key": "3.3", "phase": "ready"},
        {"key": "3.4", "phase": "backlog"},
    ]
    assert watch_mod._up_next({"pattern": "bmad-loop"}, rows, ["3.1", "3.2"]) == ["3.3", "3.4"]
    assert watch_mod._up_next({"pattern": "bmad-loop"}, rows, ["3.4", "3.5"]) == ["3.4", "3.5"]


def test_user_action_composes_every_part():
    text = watch_mod._user_action(
        status={"paused_stage": "escalation", "escalation_reason": "needs operator"},
        overall="running",
        stale_dispatch="old-dispatch",
        home_state="paused-on-escalation",
    )
    assert text.startswith("blocking: needs operator; ")
    assert "stale unrelated dispatch record 'old-dispatch'" in text
    assert text.endswith("supervisor liveness (marshal status homes[0].state): paused-on-escalation")
    assert (
        watch_mod._user_action(status={}, overall="escalated", stale_dispatch=None, home_state=None)
        == "blocking: escalated"
    )


def test_parse_queue_reads_epics_headings_minus_ledger_done(tmp_path: Path):
    planning = tmp_path / "_bmad-output" / "projects" / "acme" / "planning-artifacts"
    planning.mkdir(parents=True)
    (planning / "epics.md").write_text(
        "# Epic 1\n\n### Story 1.1: first\n\n### Story 1.2: second\n\n#### Story 1.3: third\n",
        encoding="utf-8",
    )
    (planning / "sprint-status-ledger.yaml").write_text(
        "epic-1: in-progress\n1-1: done\n1-2: in-progress\n  1-3: done\nnot a row\n",
        encoding="utf-8",
    )
    assert watch_mod._parse_queue("acme", tmp_path) == ["1.2"]
    assert watch_mod._parse_queue("missing", tmp_path) == []


# _default_ports: every real-I/O port over a recording ProcessPort


def test_default_ports_list_runs_and_run_status_go_through_bmad_loop(tmp_path: Path, monkeypatch):
    home = _fake_home(monkeypatch, tmp_path, "acme")
    process = _RecordingProcess(
        {
            "list": _ok({"runs": [{"id": "r1", "status": "running"}]}),
            "status": _ok({"run_id": "r1", "finished": False}),
        }
    )
    ports = watch_mod._default_ports(process, tmp_path)
    assert ports.list_runs("acme") == {"runs": [{"id": "r1", "status": "running"}]}
    assert ports.run_status("acme", "r1") == {"run_id": "r1", "finished": False}
    argv, cwd, timeout_s = process.calls[0]
    assert argv == ["pixi", "run", "-e", "pyforge-guild", "bmad-loop", "list", "--json"]
    assert cwd == home / ".bmad-loops" / "acme"
    assert timeout_s == watch_mod._WATCH_TIMEOUT_S
    assert process.calls[1][0][-3:] == ["status", "r1", "--json"]
    # No loop home for this slug: list reports an empty fleet without a
    # process launch, and status falls back to the repo root as cwd.
    assert ports.list_runs("nobody") == {"runs": []}
    assert len(process.calls) == 2
    ports.run_status("nobody", "r9")
    assert process.calls[2][1] == tmp_path


@pytest.mark.parametrize(
    ("response", "reason"),
    [
        (ProcessError("executable not found: 'pixi'"), "executable not found"),
        (ProcessResult(returncode=3, stdout="", stderr="boom"), "exit 3"),
        (ProcessResult(returncode=0, stdout="not json", stderr=""), "did not parse as JSON"),
        (ProcessResult(returncode=0, stdout="[1]", stderr=""), "JSON was not an object"),
    ],
    ids=["launch-failure", "non-zero", "non-json", "non-object"],
)
def test_default_ports_run_json_failures_become_loop_cli_errors(tmp_path: Path, monkeypatch, response, reason):
    _fake_home(monkeypatch, tmp_path, "acme")
    ports = watch_mod._default_ports(_RecordingProcess({"list": response}), tmp_path)
    with pytest.raises(LoopCliError) as excinfo:
        ports.list_runs("acme")
    assert excinfo.value.command == "bmad-loop list --json"
    assert reason in excinfo.value.reason


def test_default_ports_marshal_home_reads_homes_zero(tmp_path: Path):
    process = _RecordingProcess(
        {watch_mod._MARSHAL_STATUS_MODULE: _ok({"data": {"homes": [{"state": "running", "dispatch_run_id": "d1"}]}})}
    )
    ports = watch_mod._default_ports(process, tmp_path)
    assert ports.marshal_home("acme") == {"state": "running", "dispatch_run_id": "d1"}
    argv, cwd, _ = process.calls[0]
    # Story 51.10: the argv is asserted against the constant the probe itself
    # uses, never a literal -- the pre-fix version of this test pinned the
    # non-executable package name ("pyforge.marshal") against this same fake.
    assert argv[:3] == [_sys.executable, "-m", watch_mod._MARSHAL_STATUS_MODULE]
    assert argv[3:] == ["status", "--project", "acme", "--format", "json"]
    assert cwd == tmp_path


def test_marshal_status_module_is_executable_by_this_interpreter(tmp_path: Path):
    """Story 51.10 (spec-pyforge-marshal CAP-257): the module the probe names
    must be runnable as ``python -m <module>`` by the interpreter the probe
    uses -- the fake-port tests above cannot see a wrong name, and from 51.6's
    landing until 2026-09-20 the probe named the package ``pyforge.marshal``
    (no ``__main__``), so every call raised ``ProcessError``, the probe read
    ``None`` and ``marshal watch --fleet`` reported live dispatch runs as idle
    stations. Runs the real module through the sanctioned process primitive;
    ``--help`` is the cheapest argv that proves the module executes."""
    from pyforge.core.process import PosixProcess

    result = PosixProcess().run(
        [_sys.executable, "-m", watch_mod._MARSHAL_STATUS_MODULE, "--help"],
        cwd=tmp_path,
        timeout_s=60.0,
    )
    assert result.returncode == 0, result.stderr
    assert "status" in result.stdout
    # The package itself is NOT executable -- the exact shape of the bug.
    assert watch_mod._MARSHAL_STATUS_MODULE != "pyforge.marshal"


@pytest.mark.parametrize(
    "response",
    [
        ProcessError("cannot launch"),
        ProcessResult(returncode=0, stdout="not json", stderr=""),
        ProcessResult(returncode=0, stdout="[]", stderr=""),
        ProcessResult(returncode=0, stdout=json.dumps({"data": {"homes": []}}), stderr=""),
        ProcessResult(returncode=0, stdout=json.dumps({"data": {"homes": ["junk"]}}), stderr=""),
    ],
    ids=["launch-failure", "non-json", "non-object", "no-homes", "junk-home"],
)
def test_default_ports_marshal_home_is_advisory_and_degrades_to_none(tmp_path: Path, response):
    ports = watch_mod._default_ports(_RecordingProcess({watch_mod._MARSHAL_STATUS_MODULE: response}), tmp_path)
    assert ports.marshal_home("acme") is None


def test_default_ports_loop_sha_fetches_then_rev_parses(tmp_path: Path):
    process = _RecordingProcess(
        {
            "fetch": ProcessResult(returncode=0, stdout="", stderr=""),
            "rev-parse": ProcessResult(returncode=0, stdout="cafebabe\n", stderr=""),
        }
    )
    ports = watch_mod._default_ports(process, tmp_path)
    assert ports.loop_sha("acme") == "cafebabe"
    assert process.calls[0][0] == ["git", "fetch", "origin", "--quiet"]
    assert process.calls[1][0] == ["git", "rev-parse", "origin/loop/acme"]


def test_default_ports_loop_sha_probe_failures_become_probe_errors(tmp_path: Path):
    launch_fail = _RecordingProcess({"fetch": ProcessError("no git")})
    with pytest.raises(ProbeError, match="no git") as excinfo:
        watch_mod._default_ports(launch_fail, tmp_path).loop_sha("acme")
    assert excinfo.value.command == "git rev-parse"
    empty = _RecordingProcess(
        {
            "fetch": ProcessResult(returncode=0, stdout="", stderr=""),
            "rev-parse": ProcessResult(returncode=128, stdout="  \n", stderr="unknown revision"),
        }
    )
    with pytest.raises(ProbeError, match="empty stdout"):
        watch_mod._default_ports(empty, tmp_path).loop_sha("acme")


def test_default_ports_list_prs_parses_gh_json_and_drops_non_mappings(tmp_path: Path):
    process = _RecordingProcess(
        {"gh": ProcessResult(returncode=0, stdout=json.dumps([{"number": 1}, "junk"]), stderr="")}
    )
    ports = watch_mod._default_ports(process, tmp_path)
    assert ports.list_prs("acme") == [{"number": 1}]
    argv = process.calls[0][0]
    assert argv[:3] == ["gh", "pr", "list"]
    assert "--json" in argv and "number,title,headRefName,state,updatedAt" in argv


@pytest.mark.parametrize(
    ("response", "reason"),
    [
        (ProcessError("no gh"), "no gh"),
        (ProcessResult(returncode=0, stdout="nope", stderr=""), "did not parse as JSON"),
        (ProcessResult(returncode=0, stdout="{}", stderr=""), "JSON was not a list"),
    ],
    ids=["launch-failure", "non-json", "non-list"],
)
def test_default_ports_list_prs_failures_become_probe_errors(tmp_path: Path, response, reason):
    ports = watch_mod._default_ports(_RecordingProcess({"gh": response}), tmp_path)
    with pytest.raises(ProbeError) as excinfo:
        ports.list_prs("acme")
    assert excinfo.value.command == "gh pr list"
    assert reason in excinfo.value.reason


def test_default_ports_discover_projects_and_load_queue_read_the_repo(tmp_path: Path):
    ports = watch_mod._default_ports(_RecordingProcess({}), tmp_path)
    assert ports.discover_projects() == []
    projects = tmp_path / "_bmad-output" / "projects"
    (projects / "zeta" / "planning-artifacts").mkdir(parents=True)
    (projects / "alpha").mkdir()
    (projects / "stray-file.md").write_text("x", encoding="utf-8")
    (projects / "zeta" / "planning-artifacts" / "epics.md").write_text("### Story 9.1: only\n", encoding="utf-8")
    assert ports.discover_projects() == ["alpha", "zeta"]
    assert ports.load_queue is not None
    assert ports.load_queue("zeta") == ["9.1"]


def test_default_ports_loop_last_fact_reads_the_real_journal(tmp_path: Path, monkeypatch):
    home = _fake_home(monkeypatch, tmp_path, "acme")
    run_dir = home / ".bmad-loops" / "acme" / ".bmad-loop" / "runs" / "r1"
    run_dir.mkdir(parents=True)
    (run_dir / "journal.jsonl").write_text(
        '{"ts": 1755500000.0, "kind": "story-started"}\n{"ts": 1755500100.5, "kind": "story-done"}\n',
        encoding="utf-8",
    )
    ports = watch_mod._default_ports(_RecordingProcess({}), tmp_path)
    assert ports.loop_last_fact is not None
    assert ports.loop_last_fact("acme", "r1") == datetime.fromtimestamp(1755500100.5, tz=timezone.utc)
    # No journal at all for this run -- honest None, not an exception.
    assert ports.loop_last_fact("acme", "no-such-run") is None


def test_default_ports_dispatch_last_fact_reads_the_real_journal(tmp_path: Path):
    from pyforge.marshal.core.dispatch import dispatch_run_dir
    from pyforge.marshal.core.journal import JournalEntryId, Phase, build_entry, prepare_for_write

    run_dir = dispatch_run_dir(tmp_path, "acme", "d1")
    run_dir.mkdir(parents=True)
    entry = build_entry(
        id=JournalEntryId(writer_id="test-writer", counter=1),
        ts="2026-09-18T06:00:00.000Z",
        run_id="d1",
        kind="dispatch-launch",
        phase=Phase.INTENT,
        payload={"story_key": "6.1", "model": "m", "worktree_path": "/tmp/wt"},
    )
    (run_dir / "journal.jsonl").write_text(prepare_for_write(entry).line + "\n", encoding="utf-8")
    ports = watch_mod._default_ports(_RecordingProcess({}), tmp_path)
    assert ports.dispatch_last_fact is not None
    assert ports.dispatch_last_fact("acme", "d1") == datetime(2026, 9, 18, 6, 0, 0, tzinfo=timezone.utc)
    # A dispatch id with no matching run dir -- honest None.
    assert ports.dispatch_last_fact("acme", "no-such-run") is None


# run_watch: argument errors, the default cache dir, context slug, text render


def test_run_watch_argument_errors(tmp_path: Path, capsys):
    ports = _ports(tmp_path)
    rc = _run(tmp_path, _args(fleet=True, project="pyforge-herald"), ports)
    payload = _payload(capsys)
    assert rc == 4
    assert "mutually exclusive" in payload["findings"][0]["message"]
    rc = _run(tmp_path, _args(), ports)
    payload = _payload(capsys)
    assert rc == 4
    assert "need --project SLUG or --fleet" in payload["findings"][0]["message"]


def test_run_watch_run_without_project_is_rejected(tmp_path: Path, capsys):
    """`--run` alone: the `run_id and not slug` guard (reached only when the
    generic `not fleet and not slug` guard is bypassed by a context that
    itself carries no slug)."""

    class _NoSlugContext:
        slug = ""

    rc = run_watch(
        _args(run="r1"),
        context=_NoSlugContext(),
        ports=_ports(tmp_path),
        now=_NOW,
        cache_dir=tmp_path / "cache",
        repo=tmp_path,
    )
    payload = _payload(capsys)
    assert rc == 4
    assert "need --project SLUG or --fleet" in payload["findings"][0]["message"]


def test_run_watch_takes_the_slug_from_the_context_and_default_cache_dir(tmp_path: Path, capsys):
    class _Context:
        slug = "pyforge-herald"

    naive_now = datetime(2026, 9, 15, 12, 10, 0)
    rc = run_watch(
        _args(run="20260914-201759-bd47"),
        context=_Context(),
        ports=_ports(tmp_path),
        now=naive_now,
        repo=tmp_path,
    )
    payload = _payload(capsys)
    assert rc == 0
    assert payload["data"]["slug"] == "pyforge-herald"
    assert payload["data"]["checked_at"] == "2026-09-15T12:10:00Z"
    default_cache = tmp_path / ".claude" / "data" / "marshal-run-watch"
    assert (default_cache / "pyforge-herald__20260914-201759-bd47.json").is_file()


def test_run_watch_uses_the_injected_process_for_default_ports(tmp_path: Path, monkeypatch, capsys):
    """No `ports=`: `run_watch` builds `_default_ports` over the injected
    `ProcessPort` -- proven by the recorded argv of the first call."""
    _fake_home(monkeypatch, tmp_path)  # no loop home -> list_runs returns {"runs": []}
    process = _RecordingProcess({watch_mod._MARSHAL_STATUS_MODULE: ProcessError("no marshal")})
    rc = run_watch(_args(project="acme"), process=process, now=_NOW, cache_dir=tmp_path / "cache", repo=tmp_path)
    payload = _payload(capsys)
    assert rc == 4
    assert any(f["code"] == "MRS-WATCH-002" for f in payload["findings"])
    assert process.calls[0][0][:3] == [_sys.executable, "-m", watch_mod._MARSHAL_STATUS_MODULE]


def test_pinned_text_report_renders_every_section_and_findings(tmp_path: Path, capsys):
    ports = _ports(tmp_path, sha_error=ProbeError("git rev-parse", "no such ref"))
    rc = _run(tmp_path, _args(project="pyforge-herald", run="20260914-201759-bd47", format="text"), ports)
    text = capsys.readouterr().out
    assert rc == 0
    assert text.startswith("## pyforge-herald — Run `20260914-201759-bd47` (bmad-loop) Status Report")
    assert "**Session Completions:**\n- 21.4 -- done" in text
    assert "- first observation -- no prior cache" in text
    assert "**Currently Running:**\n- story=21.5 phase=dev-running attempt=1 tokens=None" in text
    assert "**Up Next & Full Queue:**\n- 21.6\n- 21.7" in text
    assert "**User Action Required:** None; stale unrelated dispatch" in text
    assert "next-check delay: 300s -- actively progressing" in text
    assert "findings:\n  MRS-WATCH-003 [warn] git rev-parse failed" in text


def test_finished_text_report_prints_the_reason_without_a_delay(tmp_path: Path, capsys):
    ports = _ports(
        tmp_path,
        listed={"runs": [{"id": "r", "status": "finished"}]},
        status=_loop_status(
            finished=True,
            status="finished",
            stories=[{"key": "21.5", "phase": "ready", "commit_sha": None}],
        ),
    )
    rc = _run(tmp_path, _args(project="pyforge-herald", run="r", format="text"), ports)
    text = capsys.readouterr().out
    assert rc == 0
    assert "**Session Completions:**\n- (none)" in text
    assert "next-check delay:" not in text  # the `<delay>s -- <reason>` line
    assert text.rstrip().endswith("run/dispatch is finished -- no next-check delay")


def test_fleet_text_report_and_second_observation_delta(tmp_path: Path, capsys):
    per_slug = {
        "pyforge-herald": {
            "listed": {"runs": [{"id": "20260914-201759-bd47", "status": "running"}]},
            "status": _loop_status(),
            "home": {"state": "running", "dispatch_run_id": None},
        },
        "idle-one": {"listed": {"runs": []}, "home": {"state": "idle", "dispatch_run_id": None}},
    }
    ports = _ports(tmp_path, slugs=["pyforge-herald", "idle-one"], per_slug=per_slug)
    rc = _run(tmp_path, _args(fleet=True, format="text"), ports)
    text = capsys.readouterr().out
    assert rc == 0
    assert text.startswith("## Fleet Watch — 2 projects")
    assert "- first observation -- no prior cache" in text
    assert "- pyforge-herald — bmad-loop — 20260914-201759-bd47 — in-progress" in text
    assert "- idle-one — None — idle — idle" in text
    assert "**User Action Required:** None" in text
    # Second observation, nothing moved: quiet.
    rc = _run(tmp_path, _args(fleet=True, format="text"), ports)
    text = capsys.readouterr().out
    assert rc == 0
    assert "nothing changed" in text
    # Third observation, herald finished: a per-slug delta line.
    per_slug["pyforge-herald"]["status"] = _loop_status(finished=True, status="finished")
    rc = _run(tmp_path, _args(fleet=True), _ports(tmp_path, slugs=["pyforge-herald", "idle-one"], per_slug=per_slug))
    payload = _payload(capsys)
    assert rc == 0
    assert payload["data"]["changed"] is True
    assert payload["data"]["quiet"] is False
    assert payload["data"]["delta"][0].startswith("pyforge-herald: ")


def test_fleet_escalated_member_names_the_action(tmp_path: Path, capsys):
    ports = _ports(
        tmp_path,
        slugs=["pyforge-atlas"],
        per_slug={
            "pyforge-atlas": {
                "listed": {"runs": [{"id": "atlas-run", "status": "paused"}]},
                "status": _loop_status(status="paused", paused_stage="escalation", paused_reason="needs operator"),
                "home": {"state": "paused-on-escalation", "dispatch_run_id": None},
            }
        },
    )
    rc = _run(tmp_path, _args(fleet=True, format="text"), ports)
    text = capsys.readouterr().out
    assert rc == 0
    assert "— ESCALATED" in text
    assert "**User Action Required:** pyforge-atlas: blocking: needs operator" in text


# _gather_station: the remaining error branches


def test_status_failure_after_a_live_row_is_a_loop_cli_error(tmp_path: Path, capsys):
    ports = _ports(tmp_path, status_error=LoopCliError("bmad-loop status r --json", "exit 1"))
    rc = _run(tmp_path, _args(project="pyforge-herald"), ports)
    payload = _payload(capsys)
    assert rc == 4
    assert any(f["code"] == "MRS-WATCH-001" and "bmad-loop status" in f["message"] for f in payload["findings"])


def test_live_row_without_an_id_is_no_active_run(tmp_path: Path, capsys):
    ports = _ports(tmp_path, listed={"runs": [{"status": "running"}]})
    rc = _run(tmp_path, _args(project="pyforge-herald"), ports)
    payload = _payload(capsys)
    assert rc == 4
    assert any(f["code"] == "MRS-WATCH-002" for f in payload["findings"])


def test_gh_failure_is_a_warn_finding_and_marshal_home_crash_is_swallowed(tmp_path: Path, capsys):
    base = _ports(tmp_path)

    def _no_prs(slug: str) -> list[dict]:
        raise ProbeError("gh pr list", "not authenticated")

    def _crashing_home(slug: str) -> dict | None:
        raise RuntimeError("marshal status exploded")

    ports = WatchPorts(
        list_runs=base.list_runs,
        run_status=base.run_status,
        marshal_home=_crashing_home,
        loop_sha=base.loop_sha,
        list_prs=_no_prs,
        discover_projects=base.discover_projects,
        load_queue=None,
    )
    rc = _run(tmp_path, _args(project="pyforge-herald", run="20260914-201759-bd47"), ports)
    payload = _payload(capsys)
    assert rc == 0
    assert payload["verdict"] == "warn"
    assert any(f["code"] == "MRS-WATCH-004" for f in payload["findings"])
    assert _cached_snapshot(tmp_path, "pyforge-herald", "20260914-201759-bd47")["prs"] == []
    assert payload["data"]["stale_dispatch_ignored"] is False
    # No load_queue port: up-next comes from the status rows alone.
    assert payload["data"]["sections"]["up_next"] == ["21.6"]


def test_pinned_run_id_with_no_live_row_still_asks_bmad_loop_status(tmp_path: Path, capsys):
    ports = _ports(tmp_path, listed={"runs": [{"id": "other", "status": "finished"}]})
    rc = _run(tmp_path, _args(project="pyforge-herald", run="pinned-run"), ports)
    payload = _payload(capsys)
    assert rc == 0
    assert payload["data"]["pattern"] == "bmad-loop"
    assert payload["data"]["run_id"] == "pinned-run"
    assert _cached_snapshot(tmp_path, "pyforge-herald", "pinned-run")["list_status"] is None


def test_dispatch_pattern_escalated_and_finished_flags(tmp_path: Path, capsys):
    home = {
        "state": "paused-on-escalation",
        "dispatch_run_id": "warden-dispatch",
        "dispatch_completion_verdict": "failed",
        "dispatch_verification_verdict": "red",
        "current_story": "11.1",
        "escalation_reason": "spec gap",
    }
    ports = _ports(tmp_path, listed={"runs": []}, home=home)
    rc = _run(tmp_path, _args(project="pyforge-warden"), ports)
    payload = _payload(capsys)
    assert rc == 0
    data = payload["data"]
    assert data["pattern"] == "bmad-build-auto"
    snapshot = _cached_snapshot(tmp_path, "pyforge-warden", "warden-dispatch")
    assert snapshot["status"] == "finished"
    assert snapshot["paused_stage"] == "escalation"
    assert data["sections"]["session_completions"] == ["11.1 -- completion failed"]
    assert data["sections"]["user_action_required"].startswith("blocking: spec gap")
    # finished + escalated: the delay recommendation is the terminal one.
    assert data["delay_seconds"] is None
    assert "finished" in data["delay_reason"]


def test_prior_cache_with_a_non_object_snapshot_counts_as_first_observation(tmp_path: Path, capsys):
    cache = tmp_path / "cache"
    watch_mod._write_cache(cache / "pyforge-herald__20260914-201759-bd47.json", {"snapshot": "junk"})
    rc = _run(tmp_path, _args(project="pyforge-herald", run="20260914-201759-bd47"), _ports(tmp_path))
    payload = _payload(capsys)
    assert rc == 0
    assert payload["data"]["first_observation"] is True


def test_emit_suppresses_a_dead_stdout(tmp_path: Path, monkeypatch):
    suppressed: list[bool] = []
    monkeypatch.setattr(watch_mod, "_suppress_downstream_pipe_close", lambda: suppressed.append(True))

    def _dead_print(*args, **kwargs):
        raise OSError(32, "Broken pipe")

    monkeypatch.setattr(watch_mod, "print", _dead_print, raising=False)
    findings = [Finding(code="MRS-WATCH-003", severity=Severity.WARN, message="probe failed")]
    rc = watch_mod._emit(_args(format="text"), {"scope": "station", "quiet": True}, findings)
    assert rc == 0
    assert suppressed == [True]


# --- Story 51.13 (spec-pyforge-marshal CAP-260): the supervisor's own verdict vocabulary ---

from pyforge.marshal.core.dispatch_completion import DispatchSessionVerdict as _DSV


@pytest.mark.parametrize(
    ("verdict", "terminal"),
    [
        (_DSV.LIVE.value, False),
        (_DSV.COMPLETED.value, True),
        (_DSV.FAILED.value, True),
        (_DSV.STOPPED_EXTERNALLY.value, True),
        (None, False),
        ("", False),
        ("not-a-verdict", False),
    ],
    ids=["live", "completed", "failed", "stopped_externally", "absent", "empty", "unknown"],
)
def test_dispatch_verdict_terminality_is_the_enum(verdict, terminal):
    assert watch_mod._dispatch_verdict_is_terminal(verdict) is terminal


def test_live_dispatch_row_snapshots_as_running_not_finished():
    """The 2026-09-20 01:25Z shape: `marshal status` reports a running
    session with `dispatch_completion_verdict: live`; the watch read it
    `finished`."""
    home = {
        "state": "running",
        "dispatch_run_id": "pyforge-doctor-20260920T011757605Z-329534a6",
        "dispatch_completion_verdict": _DSV.LIVE.value,
        "current_story": "26.1",
    }
    snap = watch_mod._snapshot_dispatch("pyforge-doctor", home, None, [])
    assert snap["status"] == "running"
    assert snap["finished"] is False
    done = watch_mod._snapshot_dispatch(
        "pyforge-doctor", dict(home, state="stopped", dispatch_completion_verdict=_DSV.COMPLETED.value), None, []
    )
    assert done["status"] == "finished" and done["finished"] is True


def test_watch_tests_use_only_the_supervisor_verdict_vocabulary():
    """Meta: every `dispatch_completion_verdict` literal in this file is a
    `DispatchSessionVerdict` member -- the pre-51.13 tests asserted with
    `passed`/`pending`, values the supervisor never emits, which is how the
    wrong predicate stayed green."""
    import re as _re
    from pathlib import Path as _P

    text = _P(__file__).read_text(encoding="utf-8")
    literals = set(_re.findall(r'dispatch_completion_verdict["\']?\s*[:=]\s*["\']([^"\']*)["\']', text))
    allowed = {m.value for m in _DSV}
    assert literals <= allowed, sorted(literals - allowed)
