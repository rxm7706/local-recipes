"""``marshal watch`` (Story 44.1) -- port the operator's marshal-run-watch
ritual into a real CLI verb.

Read-only: gathers the SAME ground truth ``bmad-loop status``/``list`` and
``marshal status`` already expose, diffs it against a local cache under
``.claude/data/marshal-run-watch/``, and recommends a next-check delay.
Never writes a sprint ledger, never calls resolve/resume/dispatch.

Tests inject every I/O port -- no live ``bmad-loop`` process or network.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from pyforge.core.errors import PyforgeError
from pyforge.core.process import PosixProcess, ProcessError, ProcessPort

from ..core.context import MarshalContext
from ..core.dispatch import DispatchJournalFacts
from ..core.dispatch_completion import DispatchSessionVerdict
from ..core.model import Finding, Severity, build_envelope
from ..core.verdict import compute_verdict, exit_code_for
from .config import _suppress_downstream_pipe_close, repo_root

_MRS_WATCH_001 = "MRS-WATCH-001"
_MRS_WATCH_002 = "MRS-WATCH-002"
_MRS_WATCH_003 = "MRS-WATCH-003"
_MRS_WATCH_004 = "MRS-WATCH-004"

_LIVE_STATUSES = frozenset({"running", "paused"})
_ACTIVE_PHASES = frozenset({"dev-running", "review-running"})
_DONE_PHASES = frozenset({"done", "completed", "landed"})
_TERMINAL_STATUSES = frozenset({"finished", "complete", "completed", "stopped"})
_STORY_HEADING = re.compile(r"^#{2,4}\s+Story\s+(\d+\.\d+)\b", re.MULTILINE)
_CACHE_RELPATH = (".claude", "data", "marshal-run-watch")
_WATCH_TIMEOUT_S = 90.0
#: The module ``_default_ports.marshal_home`` executes as ``python -m <this>``
#: to read a station's marshal home. It is the console script's own module
#: (``[project.scripts] marshal = "pyforge.marshal.cli.main:main"``) -- NOT the
#: package ``pyforge.marshal``, which has no ``__main__`` and so cannot be run.
#: Story 51.10 (spec-pyforge-marshal CAP-257): from 51.6's landing until
#: 2026-09-20 the probe named the package, every call raised ``ProcessError``,
#: the probe degraded to ``None`` and ``_gather_station``'s dispatch-run
#: detection never fired -- ``marshal watch --fleet`` read three live dispatch
#: sessions as idle stations. ``test_watch.py`` executes this exact module
#: against the real interpreter so the name can never silently rot again.
_MARSHAL_STATUS_MODULE = "pyforge.marshal.cli.main"


class LoopCliError(PyforgeError, RuntimeError):
    """``bmad-loop status``/``list`` failed -- never fabricate a delta.

    Story 52.1, SPEC-pyforge-core CAP-5: gains ``PyforgeError`` as an
    additional base -- ``RuntimeError`` stays in the MRO."""

    def __init__(self, command: str, reason: str) -> None:
        super().__init__(f"{command}: {reason}")
        self.command = command
        self.reason = reason


class ProbeError(PyforgeError, RuntimeError):
    """Best-effort git/gh probe failed -- finding, not a crash.

    Story 52.1, SPEC-pyforge-core CAP-5: gains ``PyforgeError`` as an
    additional base -- ``RuntimeError`` stays in the MRO."""

    def __init__(self, command: str, reason: str) -> None:
        super().__init__(f"{command}: {reason}")
        self.command = command
        self.reason = reason


@dataclass(frozen=True)
class WatchPorts:
    """Every external read ``marshal watch`` needs. Tests supply fixtures."""

    list_runs: Callable[[str], Mapping[str, Any]]
    run_status: Callable[[str, str], Mapping[str, Any]]
    marshal_home: Callable[[str], Mapping[str, Any] | None]
    loop_sha: Callable[[str], str | None]
    list_prs: Callable[[str], list[Mapping[str, Any]]]
    discover_projects: Callable[[], list[str]]
    load_queue: Callable[[str], list[str]] | None = None
    #: Story 51.6 (spec-pyforge-marshal CAP-254): the bmad-loop run's own
    #: last journal fact (``(slug, run_id) -> ts``), read from its
    #: ``journal.jsonl`` -- ``None`` when unset (existing callers) or when
    #: the journal can't be read, never fabricated.
    loop_last_fact: Callable[[str, str], datetime | None] | None = None
    #: The dispatch run's own last journal fact (``(slug, dispatch_run_id)
    #: -> ts``), via ``cli/dispatch.py``'s ``iter_dispatch_run_dirs`` /
    #: ``gather_dispatch_journal_facts`` -- same absent-is-``None`` contract.
    dispatch_last_fact: Callable[[str, str], datetime | None] | None = None


def seconds_to_next_half_hour(now: datetime) -> int:
    """Seconds until the next UTC ``:00``/``:30`` wall-clock boundary."""
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)
    if now.minute < 30:
        nxt = now.replace(minute=30, second=0, microsecond=0)
    else:
        nxt = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    return max(0, int((nxt - now).total_seconds()))


def recommend_delay(
    *,
    finished: bool,
    paused_or_escalated: bool,
    actively_progressing: bool,
    now: datetime,
    fleet: bool,
) -> tuple[int | None, str]:
    """Skill Step 5. Terminal station/pinned runs omit a delay; fleet never
    recommends stop."""
    boundary = seconds_to_next_half_hour(now)
    if finished and not fleet:
        return None, "run/dispatch is finished -- no next-check delay"
    if paused_or_escalated and not actively_progressing:
        delay = min(1800, boundary)
        return delay, (f"paused/escalated -- boundary-only delay {delay}s (next :00/:30 in {boundary}s UTC)")
    if actively_progressing:
        delay = min(300, boundary)
        return delay, (f"actively progressing -- min(300, boundary) = {delay}s (next :00/:30 in {boundary}s UTC)")
    delay = boundary
    return delay, (f"idle/paused fleet or non-active run -- boundary-only {delay}s (next :00/:30 in {boundary}s UTC)")


def add_watch_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Register ``watch`` on ``main.py``'s subparser tree -- sibling to
    ``status``/``check`` (Story 44.1 Code Map)."""
    parser = subparsers.add_parser(
        "watch",
        help=("Operator ritual as a CLI verb: ground-truth + delta + boundary-aware next-check delay (Story 44.1)."),
        description=(
            "Ports .claude/skills/marshal-run-watch into marshal watch. "
            "Pinned (--project + --run), station (--project), or fleet "
            "(--fleet). Read-only except the local marshal-run-watch cache."
        ),
    )
    parser.add_argument(
        "--project",
        default=None,
        metavar="SLUG",
        help="Project slug (pinned or station scope).",
    )
    parser.add_argument(
        "--run",
        default=None,
        metavar="RUN_ID",
        help="Pin a harness or dispatch run id (requires --project).",
    )
    parser.add_argument(
        "--fleet",
        action="store_true",
        help="Compact snapshot of every project under _bmad-output/projects/*/",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    parser.set_defaults(handler=run_watch)


def _cache_dir(root: Path) -> Path:
    return root.joinpath(*_CACHE_RELPATH)


def _read_cache(path: Path) -> Mapping[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError, TypeError, ValueError:
        return None
    return payload if isinstance(payload, Mapping) else None


def _write_cache(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _story_rows(status: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = status.get("stories")
    if not isinstance(raw, list):
        raw = status.get("tasks")
    rows: list[dict[str, Any]] = []
    if not isinstance(raw, list):
        return rows
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        key = item.get("key") or item.get("story_key") or item.get("story")
        if not isinstance(key, str) or not key:
            continue
        rows.append(
            {
                "key": key,
                "phase": str(item.get("phase") or item.get("status") or ""),
                "commit_sha": item.get("commit_sha") or item.get("commit") or None,
                "attempt": item.get("attempt") or item.get("attempt_number"),
                "tokens": item.get("tokens") or item.get("token_consumption"),
            }
        )
    return rows


def _overall_status(status: Mapping[str, Any], list_row: Mapping[str, Any] | None) -> str:
    if status.get("finished") is True:
        return "finished"
    for key in ("status", "run_status"):
        value = status.get(key)
        if isinstance(value, str) and value:
            return value
    if list_row and isinstance(list_row.get("status"), str):
        return str(list_row["status"])
    return "unknown"


def _list_row(listed: Mapping[str, Any], run_id: str) -> Mapping[str, Any] | None:
    runs = listed.get("runs")
    if not isinstance(runs, list):
        return None
    for row in runs:
        if isinstance(row, Mapping) and str(row.get("id") or row.get("run_id") or "") == run_id:
            return row
    return None


def _live_loop_row(listed: Mapping[str, Any]) -> Mapping[str, Any] | None:
    runs = listed.get("runs")
    if not isinstance(runs, list):
        return None
    live: list[Mapping[str, Any]] = []
    for row in runs:
        if isinstance(row, Mapping) and str(row.get("status") or "") in _LIVE_STATUSES:
            live.append(row)
    return live[-1] if live else None


def _newest_row(listed: Mapping[str, Any]) -> Mapping[str, Any] | None:
    runs = listed.get("runs")
    if not isinstance(runs, list) or not runs:
        return None
    last = runs[-1]
    return last if isinstance(last, Mapping) else None


def _is_active_rows(rows: Sequence[Mapping[str, Any]]) -> bool:
    return any(str(row.get("phase") or "") in _ACTIVE_PHASES for row in rows)


def _paused_or_escalated(status: Mapping[str, Any], overall: str) -> bool:
    stage = status.get("paused_stage")
    if stage in {"escalation", "paused"} or overall in {"paused", "escalated"}:
        return True
    return bool(status.get("paused_reason") or status.get("escalation_reason"))


def _dispatch_outranks_loop(*, loop_last_fact: datetime | None, dispatch_last_fact: datetime | None) -> bool:
    """Story 51.6 (spec-pyforge-marshal CAP-254) -- the ONE comparison
    ``_gather_station`` uses to pick its engine, kept pure and small on
    purpose so it can be mutation-tested directly: true only when the
    dispatch run's last journal fact is STRICTLY newer than the loop run's.
    Either side's fact being unknown never outranks -- an unreadable or
    absent journal keeps today's loop-wins default rather than guessing."""
    if loop_last_fact is None or dispatch_last_fact is None:
        return False
    return dispatch_last_fact > loop_last_fact


def _dispatch_journal_last_fact(facts: DispatchJournalFacts) -> datetime | None:
    """The dispatch run's own last known journal fact -- the latest of its
    launch time and its timing entry's recorded start/end. Never a
    directory ``mtime`` (this module's established precedent against it,
    see ``cli/status.py::_discover_harness_run_id_by_filesystem``)."""
    candidates: list[datetime] = []
    if facts.launched_at is not None:
        candidates.append(facts.launched_at)
    for raw in (facts.story_started_at, facts.story_ended_at):
        if isinstance(raw, str) and raw:
            try:
                candidates.append(datetime.fromisoformat(raw.replace("Z", "+00:00")))
            except ValueError:
                continue
    return max(candidates) if candidates else None


def _loop_journal_last_fact(text: str) -> datetime | None:
    """The latest epoch ``ts`` among a bmad-loop ``journal.jsonl``'s lines
    -- that file's own append-only shape (each line an object with a float
    ``ts``). A malformed line is skipped, never fatal -- including a
    non-finite ``ts`` (``NaN``/``Infinity`` parse fine as JSON floats but
    crash ``datetime.fromtimestamp``). Tracks the true maximum rather than
    the last-seen line, so an out-of-order journal still reports its real
    latest fact. An empty or entirely unparseable journal reports ``None``
    rather than a fabricated time."""
    max_ts: float | None = None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = entry.get("ts") if isinstance(entry, dict) else None
        if isinstance(ts, (int, float)) and not isinstance(ts, bool) and math.isfinite(ts):
            if max_ts is None or ts > max_ts:
                max_ts = float(ts)
    return datetime.fromtimestamp(max_ts, tz=timezone.utc) if max_ts is not None else None


def _filter_prs(rows: Sequence[Mapping[str, Any]], slug: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        head = str(row.get("headRefName") or "")
        if slug not in head:
            continue
        out.append(
            {
                "number": row.get("number"),
                "title": row.get("title"),
                "headRefName": head,
                "state": row.get("state"),
                "updatedAt": row.get("updatedAt"),
            }
        )
    return out


def _snapshot_loop(
    *,
    slug: str,
    run_id: str,
    status: Mapping[str, Any],
    listed: Mapping[str, Any],
    loop_sha: str | None,
    prs: list[Mapping[str, Any]],
    overall: str,
) -> dict[str, Any]:
    rows = _story_rows(status)
    return {
        "pattern": "bmad-loop",
        "slug": slug,
        "run_id": run_id,
        "status": overall,
        "paused_reason": status.get("paused_reason"),
        "escalation_reason": status.get("escalation_reason") or status.get("paused_reason"),
        "paused_stage": status.get("paused_stage"),
        "finished": bool(status.get("finished")),
        "stories": [{"key": r["key"], "phase": r["phase"], "commit_sha": r["commit_sha"]} for r in rows],
        "loop_sha": loop_sha,
        "prs": [{"number": p.get("number"), "state": p.get("state"), "updatedAt": p.get("updatedAt")} for p in prs],
        "list_status": (_list_row(listed, run_id) or {}).get("status"),
    }


def _dispatch_verdict_is_terminal(verdict: object) -> bool:
    """Story 51.13 (spec-pyforge-marshal CAP-260): a dispatch run is finished
    only when its completion verdict is a ``DispatchSessionVerdict`` member
    other than ``LIVE`` -- the supervisor's own vocabulary
    (``live | completed | failed | stopped_externally``). ``live``, absent,
    empty or unknown values are NOT terminal: the row keeps the home's own
    state. The pre-51.13 predicate treated anything outside an invented set
    (``{"", "None", "pending", "in-progress"}``) as terminal, so every live
    run read ``finished`` the moment CAP-257 made the probe return data."""
    if not isinstance(verdict, str):
        return False
    try:
        member = DispatchSessionVerdict(verdict)
    except ValueError:
        return False
    return member is not DispatchSessionVerdict.LIVE


def _snapshot_dispatch(
    slug: str, home: Mapping[str, Any], loop_sha: str | None, prs: list[Mapping[str, Any]]
) -> dict[str, Any]:
    run_id = home.get("dispatch_run_id")
    verdict = home.get("dispatch_completion_verdict")
    finished = _dispatch_verdict_is_terminal(verdict)
    return {
        "pattern": "bmad-build-auto",
        "slug": slug,
        "run_id": run_id,
        "status": "finished" if finished else str(home.get("state") or "unknown"),
        "paused_reason": home.get("escalation_reason"),
        "escalation_reason": home.get("escalation_reason"),
        "paused_stage": "escalation" if home.get("escalation_reason") else None,
        "finished": finished,
        "dispatch_completion_verdict": home.get("dispatch_completion_verdict"),
        "dispatch_verification_verdict": home.get("dispatch_verification_verdict"),
        "current_story": home.get("current_story"),
        "loop_sha": loop_sha,
        "prs": [{"number": p.get("number"), "state": p.get("state"), "updatedAt": p.get("updatedAt")} for p in prs],
    }


def _changed(prev: Mapping[str, Any] | None, curr: Mapping[str, Any]) -> bool:
    if prev is None:
        return True
    if curr.get("pattern") == "bmad-loop":
        if prev.get("stories") != curr.get("stories"):
            return True
    else:
        if prev.get("dispatch_completion_verdict") != curr.get("dispatch_completion_verdict"):
            return True
        if prev.get("dispatch_verification_verdict") != curr.get("dispatch_verification_verdict"):
            return True
    if prev.get("status") != curr.get("status"):
        return True
    if prev.get("paused_reason") != curr.get("paused_reason"):
        return True
    if prev.get("escalation_reason") != curr.get("escalation_reason"):
        return True
    if prev.get("loop_sha") != curr.get("loop_sha") and curr.get("loop_sha") is not None:
        return True
    if prev.get("prs") != curr.get("prs"):
        return True
    return False


def _delta_lines(prev: Mapping[str, Any] | None, curr: Mapping[str, Any]) -> list[str]:
    if prev is None:
        return ["first observation -- no prior cache"]
    lines: list[str] = []
    prev_stories = {r["key"]: r for r in prev.get("stories") or [] if isinstance(r, Mapping) and "key" in r}
    for row in curr.get("stories") or []:
        if not isinstance(row, Mapping):
            continue
        key = row.get("key")
        old = prev_stories.get(key) if isinstance(key, str) else None
        if old is None:
            lines.append(f"new story {key}: phase={row.get('phase')}")
            continue
        if old.get("phase") != row.get("phase") or old.get("commit_sha") != row.get("commit_sha"):
            lines.append(
                f"{key}: {old.get('phase')} -> {row.get('phase')} "
                f"(commit {old.get('commit_sha')} -> {row.get('commit_sha')})"
            )
    if prev.get("status") != curr.get("status"):
        lines.append(f"run status {prev.get('status')} -> {curr.get('status')}")
    if prev.get("paused_reason") != curr.get("paused_reason") and curr.get("paused_reason"):
        lines.append(f"new paused_reason: {curr.get('paused_reason')}")
    if prev.get("escalation_reason") != curr.get("escalation_reason") and curr.get("escalation_reason"):
        lines.append(f"new escalation_reason: {curr.get('escalation_reason')}")
    if prev.get("loop_sha") != curr.get("loop_sha") and curr.get("loop_sha"):
        lines.append(f"origin/loop SHA {prev.get('loop_sha')} -> {curr.get('loop_sha')}")
    if prev.get("prs") != curr.get("prs"):
        lines.append("PR list changed")
    if curr.get("pattern") == "bmad-build-auto":
        for field in ("dispatch_completion_verdict", "dispatch_verification_verdict"):
            if prev.get(field) != curr.get(field):
                lines.append(f"{field} {prev.get(field)} -> {curr.get(field)}")
    return lines or ["nothing changed"]


def _session_completions(curr: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]) -> list[str]:
    if curr.get("pattern") == "bmad-build-auto":
        verdict = curr.get("dispatch_completion_verdict")
        story = curr.get("current_story")
        # Story 51.13 (CAP-260): the same enum predicate as `_snapshot_dispatch`
        # -- a `live` verdict is not a completion.
        if _dispatch_verdict_is_terminal(verdict):
            return [f"{story or 'dispatch'} -- completion {verdict}"]
        return []
    return [f"{r['key']} -- {r['phase']}" for r in rows if str(r.get("phase") or "") in _DONE_PHASES]


def _currently_running(curr: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if curr.get("pattern") == "bmad-build-auto":
        return {
            "story": curr.get("current_story"),
            "phase": curr.get("status"),
            "verdict": curr.get("dispatch_completion_verdict"),
        }
    for row in rows:
        if str(row.get("phase") or "") in _ACTIVE_PHASES:
            return {
                "story": row.get("key"),
                "phase": row.get("phase"),
                "attempt": row.get("attempt"),
                "tokens": row.get("tokens"),
            }
    return {"story": None, "phase": None}


def _up_next(
    curr: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    queue: Sequence[str],
) -> list[str]:
    if curr.get("pattern") == "bmad-build-auto":
        return ["bmad-build-auto -- no further queue unless the operator names one"]
    done = {r["key"] for r in rows if str(r.get("phase") or "") in _DONE_PHASES}
    active = {r["key"] for r in rows if str(r.get("phase") or "") in _ACTIVE_PHASES}
    remaining = [key for key in queue if key not in done and key not in active]
    if remaining:
        return remaining
    from_status = [r["key"] for r in rows if r["key"] not in done and r["key"] not in active]
    return from_status


def _user_action(
    *,
    status: Mapping[str, Any],
    overall: str,
    stale_dispatch: str | None,
    home_state: str | None,
    stale_loop: str | None = None,
) -> str:
    parts: list[str] = []
    if status.get("paused_stage") == "escalation" or overall in {"paused", "escalated"}:
        reason = status.get("paused_reason") or status.get("escalation_reason") or overall
        parts.append(f"blocking: {reason}")
    if not parts:
        parts.append("None")
    if stale_dispatch:
        parts.append(
            f"stale unrelated dispatch record {stale_dispatch!r} was present and ignored "
            "(per-story detail is from bmad-loop status only)"
        )
    if stale_loop:
        parts.append(
            f"loop run {stale_loop!r} is paused/escalated but was outranked by a newer "
            "dispatch run -- operator attention still needed"
        )
    if home_state:
        parts.append(f"supervisor liveness (marshal status homes[0].state): {home_state}")
    return "; ".join(parts)


def _parse_queue(slug: str, root: Path) -> list[str]:
    planning = root / "_bmad-output" / "projects" / slug / "planning-artifacts"
    epics = planning / "epics.md"
    keys: list[str] = []
    if epics.is_file():
        keys = _STORY_HEADING.findall(epics.read_text(encoding="utf-8"))
    ledger = planning / "sprint-status-ledger.yaml"
    done: set[str] = set()
    if ledger.is_file():
        for line in ledger.read_text(encoding="utf-8").splitlines():
            match = re.match(r"^(\d+-\d+):\s*(\S+)", line.strip())
            if match and match.group(2) == "done":
                done.add(match.group(1).replace("-", ".", 1))
    return [key for key in keys if key not in done]


def _default_ports(process: ProcessPort, root: Path) -> WatchPorts:
    def _run_json(argv: list[str], cwd: Path, command: str) -> Mapping[str, Any]:
        try:
            result = process.run(argv, cwd=cwd, timeout_s=_WATCH_TIMEOUT_S)
        except ProcessError as exc:
            raise LoopCliError(command, str(exc)) from exc
        if getattr(result, "returncode", 0) not in (0, None):
            raise LoopCliError(command, f"exit {result.returncode}")
        try:
            payload = json.loads(result.stdout)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise LoopCliError(command, "stdout did not parse as JSON") from exc
        if not isinstance(payload, Mapping):
            raise LoopCliError(command, "JSON was not an object")
        return payload

    def list_runs(slug: str) -> Mapping[str, Any]:
        home = Path.home() / ".bmad-loops" / slug
        if not home.is_dir():
            return {"runs": []}
        return _run_json(
            ["pixi", "run", "-e", "pyforge-guild", "bmad-loop", "list", "--json"],
            home,
            "bmad-loop list --json",
        )

    def run_status(slug: str, run_id: str) -> Mapping[str, Any]:
        home = Path.home() / ".bmad-loops" / slug
        return _run_json(
            ["pixi", "run", "-e", "pyforge-guild", "bmad-loop", "status", run_id, "--json"],
            home if home.is_dir() else root,
            f"bmad-loop status {run_id} --json",
        )

    def marshal_home(slug: str) -> Mapping[str, Any] | None:
        try:
            result = process.run(
                [
                    sys.executable,
                    "-m",
                    _MARSHAL_STATUS_MODULE,
                    "status",
                    "--project",
                    slug,
                    "--format",
                    "json",
                ],
                cwd=root,
                timeout_s=_WATCH_TIMEOUT_S,
            )
        except ProcessError:
            return None
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError, TypeError, ValueError:
            return None
        homes = payload.get("data", {}).get("homes") if isinstance(payload, Mapping) else None
        if isinstance(homes, list) and homes and isinstance(homes[0], Mapping):
            return homes[0]
        return None

    def loop_sha(slug: str) -> str | None:
        try:
            process.run(["git", "fetch", "origin", "--quiet"], cwd=root, timeout_s=_WATCH_TIMEOUT_S)
            result = process.run(
                ["git", "rev-parse", f"origin/loop/{slug}"],
                cwd=root,
                timeout_s=_WATCH_TIMEOUT_S,
            )
        except ProcessError as exc:
            raise ProbeError("git rev-parse", str(exc)) from exc
        sha = (result.stdout or "").strip()
        if not sha:
            raise ProbeError("git rev-parse", "empty stdout")
        return sha

    def list_prs(slug: str) -> list[Mapping[str, Any]]:
        del slug
        try:
            result = process.run(
                [
                    "gh",
                    "pr",
                    "list",
                    "--repo",
                    "rxm7706/local-recipes",
                    "--state",
                    "all",
                    "--json",
                    "number,title,headRefName,state,updatedAt",
                    "--limit",
                    "30",
                ],
                cwd=root,
                timeout_s=_WATCH_TIMEOUT_S,
            )
        except ProcessError as exc:
            raise ProbeError("gh pr list", str(exc)) from exc
        try:
            payload = json.loads(result.stdout)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ProbeError("gh pr list", "stdout did not parse as JSON") from exc
        if not isinstance(payload, list):
            raise ProbeError("gh pr list", "JSON was not a list")
        return [row for row in payload if isinstance(row, Mapping)]

    def discover_projects() -> list[str]:
        projects = root / "_bmad-output" / "projects"
        if not projects.is_dir():
            return []
        return sorted(p.name for p in projects.iterdir() if p.is_dir())

    def load_queue(slug: str) -> list[str]:
        return _parse_queue(slug, root)

    def loop_last_fact(slug: str, run_id: str) -> datetime | None:
        # Story 51.6: bmad-loop's own journal, same home layout as
        # list_runs/run_status above (<home>/.bmad-loop/runs/<run_id>/).
        journal_path = Path.home() / ".bmad-loops" / slug / ".bmad-loop" / "runs" / run_id / "journal.jsonl"
        try:
            text = journal_path.read_text(encoding="utf-8")
        except OSError:
            return None
        return _loop_journal_last_fact(text)

    def dispatch_last_fact(slug: str, dispatch_id: str) -> datetime | None:
        # Story 51.6: reuse cli/dispatch.py's own run-dir/journal readers --
        # imported lazily, mirroring cli/status.py::_merge_dispatch_overlay's
        # identical local-import precedent for the same module.
        from ..adapters.fs_local import FsError, LocalFs
        from .dispatch import gather_dispatch_journal_facts, iter_dispatch_run_dirs

        run_dir = next(
            (p for p in iter_dispatch_run_dirs(root, slug) if p.name == dispatch_id),
            None,
        )
        if run_dir is None:
            return None
        try:
            facts = gather_dispatch_journal_facts(LocalFs(), run_dir, run_dir.name)
        except FsError:
            # Same fail-safe contract as loop_last_fact's `except OSError:
            # return None` above -- an unreadable journal (permission
            # denied, corrupt encoding) is never fatal to `marshal watch`.
            return None
        return _dispatch_journal_last_fact(facts)

    return WatchPorts(
        list_runs=list_runs,
        run_status=run_status,
        marshal_home=marshal_home,
        loop_sha=loop_sha,
        list_prs=list_prs,
        discover_projects=discover_projects,
        load_queue=load_queue,
        loop_last_fact=loop_last_fact,
        dispatch_last_fact=dispatch_last_fact,
    )


def _emit(args: argparse.Namespace, data: dict[str, Any], findings: list[Finding]) -> int:
    verdict_value = compute_verdict(findings)
    envelope = build_envelope(
        command="watch",
        verdict=verdict_value,
        data=data,
        data_version=1,
        findings=tuple(findings),
    )
    if args.format == "json":
        rendered = json.dumps(envelope.to_json_dict(), indent=2, sort_keys=True)
    else:
        rendered = _render_text(envelope.data, envelope.findings)
    try:
        print(rendered, flush=True)
    except OSError:
        _suppress_downstream_pipe_close()
    return exit_code_for(envelope.verdict)


def _render_text(data: Mapping[str, Any], findings: Sequence[Finding]) -> str:
    lines: list[str] = []
    if data.get("scope") == "fleet":
        lines.append(f"## Fleet Watch — {data.get('project_count')} projects")
        lines.append(f"*(checked {data.get('checked_at')})*")
        if data.get("quiet"):
            lines.append("")
            lines.append("nothing changed")
        else:
            lines.append("")
            lines.append("**Delta Since Last Update:**")
            for item in data.get("delta") or []:
                lines.append(f"- {item}")
            lines.append("")
            lines.append("**Per-Project Snapshot:**")
            for row in data.get("projects") or []:
                flag = " — ESCALATED" if row.get("escalated") else ""
                lines.append(
                    f"- {row.get('slug')} — {row.get('pattern')} — "
                    f"{row.get('run_id') or 'idle'} — {row.get('status')}{flag}"
                )
            lines.append("")
            lines.append(f"**User Action Required:** {data.get('user_action_required')}")
    elif data.get("quiet"):
        lines.append(f"## {data.get('slug')} — Run `{data.get('run_id')}` ({data.get('pattern')}) Status Report")
        lines.append(f"*(checked {data.get('checked_at')})*")
        lines.append("")
        lines.append("nothing changed")
    else:
        sections = data.get("sections") or {}
        lines.append(f"## {data.get('slug')} — Run `{data.get('run_id')}` ({data.get('pattern')}) Status Report")
        lines.append(f"*(checked {data.get('checked_at')})*")
        lines.append("")
        lines.append("**Session Completions:**")
        completions = sections.get("session_completions") or []
        if completions:
            for item in completions:
                lines.append(f"- {item}")
        else:
            lines.append("- (none)")
        lines.append("")
        lines.append("**Delta Since Last Update:**")
        for item in sections.get("delta") or []:
            lines.append(f"- {item}")
        lines.append("")
        running = sections.get("currently_running") or {}
        lines.append("**Currently Running:**")
        lines.append(
            f"- story={running.get('story')} phase={running.get('phase')} "
            f"attempt={running.get('attempt')} tokens={running.get('tokens')}"
        )
        lines.append("")
        lines.append("**Up Next & Full Queue:**")
        for item in sections.get("up_next") or []:
            lines.append(f"- {item}")
        lines.append("")
        lines.append(f"**User Action Required:** {sections.get('user_action_required')}")
    delay = data.get("delay_seconds")
    if delay is not None:
        lines.append("")
        lines.append(f"next-check delay: {delay}s -- {data.get('delay_reason')}")
    elif data.get("delay_reason"):
        lines.append("")
        lines.append(str(data.get("delay_reason")))
    if findings:
        lines.append("")
        lines.append("findings:")
        for finding in findings:
            lines.append(f"  {finding.code} [{finding.severity.value}] {finding.message}")
    return "\n".join(lines)


def _probe_sha_prs(ports: WatchPorts, slug: str, findings: list[Finding]) -> tuple[str | None, list[Mapping[str, Any]]]:
    sha: str | None = None
    prs: list[Mapping[str, Any]] = []
    try:
        sha = ports.loop_sha(slug)
    except ProbeError as exc:
        findings.append(
            Finding(
                code=_MRS_WATCH_003,
                severity=Severity.WARN,
                message=f"{exc.command} failed -- {exc.reason} -- SHA not fabricated",
            )
        )
    try:
        prs = ports.list_prs(slug)
    except ProbeError as exc:
        findings.append(
            Finding(
                code=_MRS_WATCH_004,
                severity=Severity.WARN,
                message=f"{exc.command} failed -- {exc.reason} -- PR list not fabricated",
            )
        )
    return sha, prs


def _gather_station(
    *,
    ports: WatchPorts,
    slug: str,
    run_id: str | None,
    findings: list[Finding],
) -> dict[str, Any] | None:
    try:
        listed = ports.list_runs(slug)
    except LoopCliError as exc:
        findings.append(
            Finding(
                code=_MRS_WATCH_001,
                severity=Severity.ERROR,
                message=f"{exc.command} failed -- {exc.reason} -- no delta fabricated",
            )
        )
        return None

    live = _live_loop_row(listed)
    home: Mapping[str, Any] | None = None
    try:
        home = ports.marshal_home(slug)
    except Exception:  # noqa: BLE001 -- marshal status is advisory for loop pattern
        home = None

    pattern: str
    resolved: str | None = run_id
    #: Story 51.6 (review followup): the winning engine's own last journal
    #: fact (ISO 8601 string in the return dict, ``None`` when unknown), and
    #: -- when dispatch outranks a loop row that was itself paused -- that
    #: loop run's id, so its escalation doesn't silently drop out of the
    #: fleet's escalated-first sort just because a newer dispatch run won.
    last_fact_at: datetime | None = None
    stale_loop_id: str | None = None
    if live is not None:
        loop_id = str(live.get("id") or live.get("run_id") or "")
        pattern = "bmad-loop"
        if resolved is None:
            resolved = loop_id
        # Story 51.6 (spec-pyforge-marshal CAP-254): an auto-detected live
        # loop row no longer wins unconditionally -- when this station also
        # has a dispatch run, the engine whose last journal fact is more
        # recent wins. A pinned ``run_id`` (``run_id is not None``) is the
        # operator watching THIS run on purpose; the comparison never
        # overrides a pin.
        raw_dispatch_id = home.get("dispatch_run_id") if home else None
        if run_id is None and isinstance(raw_dispatch_id, str) and raw_dispatch_id:
            loop_last = ports.loop_last_fact(slug, loop_id) if ports.loop_last_fact is not None else None
            dispatch_last = (
                ports.dispatch_last_fact(slug, raw_dispatch_id) if ports.dispatch_last_fact is not None else None
            )
            if _dispatch_outranks_loop(loop_last_fact=loop_last, dispatch_last_fact=dispatch_last):
                pattern = "bmad-build-auto"
                resolved = raw_dispatch_id
                last_fact_at = dispatch_last
                if str(live.get("status") or "") == "paused":
                    stale_loop_id = loop_id
            else:
                last_fact_at = loop_last
    elif resolved is not None:
        # Pinned run_id with no live row: still try bmad-loop status first.
        pattern = "bmad-loop"
    else:
        dispatch_id = home.get("dispatch_run_id") if home else None
        if isinstance(dispatch_id, str) and dispatch_id:
            pattern = "bmad-build-auto"
            resolved = dispatch_id
        else:
            findings.append(
                Finding(
                    code=_MRS_WATCH_002,
                    severity=Severity.ERROR,
                    message=f"no active run found for {slug!r}",
                )
            )
            return None

    if not resolved:
        findings.append(
            Finding(
                code=_MRS_WATCH_002,
                severity=Severity.ERROR,
                message=f"no active run found for {slug!r}",
            )
        )
        return None

    sha, prs = _probe_sha_prs(ports, slug, findings)
    prs = _filter_prs(prs, slug)

    if pattern == "bmad-loop":
        try:
            status = ports.run_status(slug, resolved)
        except LoopCliError as exc:
            findings.append(
                Finding(
                    code=_MRS_WATCH_001,
                    severity=Severity.ERROR,
                    message=f"{exc.command} failed -- {exc.reason} -- no delta fabricated",
                )
            )
            return None
        list_row = _list_row(listed, resolved) or live or _newest_row(listed)
        overall = _overall_status(status, list_row)
        snap = _snapshot_loop(
            slug=slug,
            run_id=resolved,
            status=status,
            listed=listed,
            loop_sha=sha,
            prs=prs,
            overall=overall,
        )
        rows = _story_rows(status)
        stale = None
        if home and home.get("dispatch_run_id") and home.get("dispatch_run_id") != resolved:
            stale = str(home.get("dispatch_run_id"))
        queue_fn = ports.load_queue
        queue = queue_fn(slug) if queue_fn is not None else []
        sections = {
            "session_completions": _session_completions(snap, rows),
            "delta": [],  # filled after cache compare
            "currently_running": _currently_running(snap, rows),
            "up_next": _up_next(snap, rows, queue),
            "user_action_required": _user_action(
                status=status,
                overall=overall,
                stale_dispatch=stale,
                home_state=str(home.get("state")) if home and home.get("state") else None,
            ),
        }
        return {
            "pattern": pattern,
            "slug": slug,
            "run_id": resolved,
            "snapshot": snap,
            "sections": sections,
            "rows": rows,
            "stale_dispatch_ignored": bool(stale),
            "stale_dispatch_run_id": stale,
            "stale_loop_ignored": False,
            "stale_loop_run_id": None,
            "actively_progressing": _is_active_rows(rows),
            "paused_or_escalated": _paused_or_escalated(status, overall),
            "finished": overall in _TERMINAL_STATUSES or bool(status.get("finished")),
            "last_fact_at": last_fact_at.isoformat() if last_fact_at is not None else None,
        }

    assert home is not None
    snap = _snapshot_dispatch(slug, home, sha, prs)
    rows = []
    status = {
        "paused_stage": snap.get("paused_stage"),
        "paused_reason": snap.get("escalation_reason"),
        "escalation_reason": snap.get("escalation_reason"),
        "finished": snap.get("finished"),
    }
    sections = {
        "session_completions": _session_completions(snap, rows),
        "delta": [],
        "currently_running": _currently_running(snap, rows),
        "up_next": _up_next(snap, rows, []),
        "user_action_required": _user_action(
            status=status,
            overall=str(snap.get("status")),
            stale_dispatch=None,
            home_state=str(home.get("state")) if home.get("state") else None,
            stale_loop=stale_loop_id,
        ),
    }
    active = str(home.get("state") or "") in {"running", "dev-running"} and not snap["finished"]
    return {
        "pattern": pattern,
        "slug": slug,
        "run_id": resolved,
        "snapshot": snap,
        "sections": sections,
        "rows": rows,
        "stale_dispatch_ignored": False,
        "stale_dispatch_run_id": None,
        "stale_loop_ignored": bool(stale_loop_id),
        "stale_loop_run_id": stale_loop_id,
        "actively_progressing": active,
        # Story 51.6 (review followup): OR in a loop row that was itself
        # paused and got outranked -- it must not vanish from the fleet's
        # escalated-first sort just because a newer dispatch run won.
        "paused_or_escalated": bool(home.get("escalation_reason")) or bool(stale_loop_id),
        "finished": bool(snap.get("finished")),
        "last_fact_at": last_fact_at.isoformat() if last_fact_at is not None else None,
    }


def run_watch(
    args: argparse.Namespace,
    *,
    context: MarshalContext | None = None,
    process: ProcessPort | None = None,
    ports: WatchPorts | None = None,
    now: datetime | None = None,
    cache_dir: Path | None = None,
    repo: Path | None = None,
) -> int:
    process = process if process is not None else PosixProcess()
    root = repo if repo is not None else repo_root()
    ports = ports if ports is not None else _default_ports(process, root)
    checked = now if now is not None else datetime.now(timezone.utc)
    if checked.tzinfo is None:
        checked = checked.replace(tzinfo=timezone.utc)
    cache_root = cache_dir if cache_dir is not None else _cache_dir(root)

    slug = getattr(args, "project", None)
    if context is not None and not slug:
        slug = context.slug
    fleet = bool(getattr(args, "fleet", False))
    run_id = getattr(args, "run", None)

    findings: list[Finding] = []
    data: dict[str, Any] = {
        "scope": "fleet" if fleet else ("pinned" if run_id else "station"),
        "checked_at": checked.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "writes_outside_cache": False,
    }

    if fleet and slug:
        findings.append(
            Finding(
                code=_MRS_WATCH_002,
                severity=Severity.ERROR,
                message="--fleet and --project are mutually exclusive",
            )
        )
        return _emit(args, data, findings)
    if not fleet and not slug:
        findings.append(
            Finding(
                code=_MRS_WATCH_002,
                severity=Severity.ERROR,
                message="need --project SLUG or --fleet",
            )
        )
        return _emit(args, data, findings)
    if run_id and not slug:
        findings.append(
            Finding(
                code=_MRS_WATCH_002,
                severity=Severity.ERROR,
                message="--run requires --project",
            )
        )
        return _emit(args, data, findings)

    if fleet:
        slugs = ports.discover_projects()
        projects: list[dict[str, Any]] = []
        fleet_snap: dict[str, Any] = {}
        any_active = False
        any_paused = False
        actions: list[str] = []
        for item in slugs:
            gathered = _gather_station(ports=ports, slug=item, run_id=None, findings=findings)
            if gathered is None:
                # Drop no-active-run errors for idle fleet members.
                findings[:] = [f for f in findings if not (f.code == _MRS_WATCH_002 and item in f.message)]
                projects.append(
                    {
                        "slug": item,
                        "pattern": None,
                        "run_id": None,
                        "status": "idle",
                        "escalated": False,
                    }
                )
                fleet_snap[item] = {
                    "pattern": None,
                    "run_id": None,
                    "status": "idle",
                    "current_story_or_phase": None,
                }
                continue
            snap = gathered["snapshot"]
            running = gathered["sections"]["currently_running"]
            escalated = bool(gathered["paused_or_escalated"])
            any_active = any_active or bool(gathered["actively_progressing"])
            any_paused = any_paused or escalated
            if escalated:
                actions.append(f"{item}: {gathered['sections']['user_action_required']}")
            projects.append(
                {
                    "slug": item,
                    "pattern": gathered["pattern"],
                    "run_id": gathered["run_id"],
                    "status": snap.get("status"),
                    "escalated": escalated,
                    "current_story_or_phase": running.get("phase") or running.get("story"),
                }
            )
            fleet_snap[item] = {
                "pattern": gathered["pattern"],
                "run_id": gathered["run_id"],
                "status": snap.get("status"),
                "current_story_or_phase": running.get("phase") or running.get("story"),
            }

        # Escalated/paused first, then slug.
        projects.sort(key=lambda row: (not row.get("escalated"), row.get("slug") or ""))

        cache_path = cache_root / "__fleet__.json"
        prior = _read_cache(cache_path)
        prior_projects = prior.get("projects") if isinstance(prior, Mapping) else None
        first = prior_projects is None
        changed = first or prior_projects != fleet_snap
        delta = ["first observation -- no prior cache"] if first else []
        if not first and changed:
            old = prior_projects or {}
            for key in sorted(set(old) | set(fleet_snap)):
                if old.get(key) != fleet_snap.get(key):
                    delta.append(f"{key}: {old.get(key)} -> {fleet_snap.get(key)}")
        if not first and not changed:
            delta = ["nothing changed"]

        _write_cache(
            cache_path,
            {
                "projects": fleet_snap,
                "last_report_at": data["checked_at"],
            },
        )
        delay, reason = recommend_delay(
            finished=False,
            paused_or_escalated=any_paused and not any_active,
            actively_progressing=any_active,
            now=checked,
            fleet=True,
        )
        data.update(
            {
                "project_count": len(slugs),
                "projects": projects,
                "delta": delta,
                "first_observation": first,
                "changed": changed,
                "quiet": (not first) and (not changed),
                "user_action_required": "; ".join(actions) if actions else "None",
                "delay_seconds": delay,
                "delay_reason": reason,
                "cache_path": str(cache_path),
            }
        )
        # Loop CLI errors on fleet still fail the command.
        return _emit(args, data, findings)

    gathered = _gather_station(ports=ports, slug=str(slug), run_id=run_id, findings=findings)
    if gathered is None:
        return _emit(args, data, findings)

    cache_path = cache_root / f"{gathered['slug']}__{gathered['run_id']}.json"
    prior = _read_cache(cache_path)
    prior_snap = prior.get("snapshot") if isinstance(prior, Mapping) else None
    if prior_snap is not None and not isinstance(prior_snap, Mapping):
        prior_snap = None
    first = prior_snap is None
    curr_snap = gathered["snapshot"]
    changed = _changed(prior_snap if isinstance(prior_snap, Mapping) else None, curr_snap)
    delta = _delta_lines(prior_snap if isinstance(prior_snap, Mapping) else None, curr_snap)
    gathered["sections"]["delta"] = delta
    quiet = (not first) and (not changed)

    _write_cache(
        cache_path,
        {
            "snapshot": curr_snap,
            "last_report_at": data["checked_at"],
        },
    )
    delay, reason = recommend_delay(
        finished=bool(gathered["finished"]),
        paused_or_escalated=bool(gathered["paused_or_escalated"]),
        actively_progressing=bool(gathered["actively_progressing"]),
        now=checked,
        fleet=False,
    )
    data.update(
        {
            "slug": gathered["slug"],
            "run_id": gathered["run_id"],
            "pattern": gathered["pattern"],
            "first_observation": first,
            "changed": changed,
            "quiet": quiet,
            "stale_dispatch_ignored": gathered["stale_dispatch_ignored"],
            "stale_dispatch_run_id": gathered["stale_dispatch_run_id"],
            "sections": gathered["sections"],
            "delay_seconds": delay,
            "delay_reason": reason,
            "cache_path": str(cache_path),
        }
    )
    return _emit(args, data, findings)
