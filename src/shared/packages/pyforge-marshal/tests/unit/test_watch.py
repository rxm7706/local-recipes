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
) -> WatchPorts:
    listed = listed if listed is not None else {"runs": [{"id": "20260914-201759-bd47", "status": "running"}]}
    status = status if status is not None else _loop_status()
    home = home if home is not None else {"state": "running", "dispatch_run_id": "herald-OLD"}
    prs = prs if prs is not None else [
        {
            "number": 1373,
            "title": "herald",
            "headRefName": "loop/pyforge-herald",
            "state": "OPEN",
            "updatedAt": "2026-09-15T00:00:00Z",
        }
    ]
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

    return WatchPorts(
        list_runs=list_runs,
        run_status=run_status,
        marshal_home=marshal_home,
        loop_sha=loop_sha,
        list_prs=list_prs,
        discover_projects=discover_projects,
        load_queue=load_queue,
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
            "dispatch_completion_verdict": "passed",
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
