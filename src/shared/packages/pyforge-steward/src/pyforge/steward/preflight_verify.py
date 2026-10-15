"""``steward preflight verify-deferred`` -- the catch-up for what pushes left to CI (Story 103.6, CAP-159).

A touched-scope ``pr-preflight`` (``PYFORGE_PREFLIGHT_SCOPE=touched``, or the flag
``pyforge.steward.preflight_ci_arbitrates`` on) runs only the lanes its diff touches and journals every other lane
as deferred in ``.steward/preflight-runs.jsonl``; a push under ``PYFORGE_PREFLIGHT_SKIP=1`` runs none and leaves a
line in ``.steward/preflight-skips.log``. This duty lists both since a date, then runs the full preflight on HEAD:
the "verify everything at the end" step.

It reaches pixi by subprocess (AD-1) and returns a ``DutyResult``; ``main()`` owns the exit code (AD-8).

EXIT  0 the full preflight is green · 1 it is red · 2 usage (a bad ``--since``, refused by argparse) ·
      3 it could not run (its exit 2, or no ``pixi`` on ``PATH``) · 130 interrupted
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, TextIO

from . import preflight
from .interfaces import DutyResult

SKIPS_RELATIVE = Path(".steward") / "preflight-skips.log"
EXIT_CANNOT_RUN = 3
EXIT_INTERRUPTED = 130
PREFLIGHT_ARGV: tuple[str, ...] = ("pixi", "run", "--frozen", "-e", "pyforge-guild", "pr-preflight")
# The hook unsets these before it runs the preflight (scripts/pre_push_preflight.sh); so does this duty.
GIT_HOOK_VARIABLES = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_PREFIX",
    "GIT_COMMON_DIR",
    "GIT_OBJECT_DIRECTORY",
)
# A branch delete pushes no commits, so there is nothing it left unverified.
NOTHING_PUSHED = "branch delete: nothing to preflight"

Runner = Callable[[Sequence[str], Path, Mapping[str, str]], int]


@dataclass(frozen=True)
class Owed:
    """One run or push whose lanes were never run locally."""

    when: str
    where: str  # the branch a run was on, or the refs a push named
    head: str
    lanes: str  # the deferred ``task@environment`` lanes, or ``every lane``
    why: str

    def line(self) -> str:
        return f"{self.when}  {self.where}  {self.head}  {self.lanes}  ({self.why})"


def _default_runner(argv: Sequence[str], cwd: Path, env: Mapping[str, str]) -> int:
    return subprocess.run(list(argv), cwd=cwd, env=dict(env), check=False).returncode  # noqa: S603


@dataclass
class VerifyDeps:
    """What the duty reads and runs; tests inject their own."""

    root: Path
    runner: Runner = _default_runner
    out: TextIO | None = None
    err: TextIO | None = None
    environ: Mapping[str, str] | None = None
    head: Callable[[Path], tuple[str, str]] = field(default=preflight._git_head)  # noqa: SLF001 -- one head reader


def _day(stamp: str) -> date | None:
    try:
        moment = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC).date()


def deferred_runs(path: Path, since: date | None) -> tuple[list[Owed], list[str]]:
    """Every journaled run record on or after ``since`` (UTC) whose ``deferred`` list is not empty.

    A record without ``deferred`` -- every record before Story 103.6, and every ``full`` run -- deferred nothing.
    """
    owed: list[Owed] = []
    warnings: list[str] = []
    if not path.is_file():
        return owed, warnings
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            record: Any = json.loads(raw)
        except json.JSONDecodeError:
            warnings.append(f"verify-deferred: warning: {path.name} line {number} is not JSON; skipped")
            continue
        if not isinstance(record, dict) or "run_id" not in record or "lanes" not in record:
            continue
        entries = record.get("deferred")
        if not isinstance(entries, list) or not entries:
            continue
        started = str(record.get("started_at", ""))
        day = _day(started)
        if day is None:
            warnings.append(f"verify-deferred: warning: {path.name} line {number} has no readable started_at; skipped")
            continue
        if since is not None and day < since:
            continue
        lanes = [
            preflight.lane_label(str(entry.get("lane", "?")), str(entry.get("environment", "?")))
            for entry in entries
            if isinstance(entry, dict)
        ]
        reasons = sorted({str(entry.get("reason", "")) for entry in entries if isinstance(entry, dict)})
        owed.append(
            Owed(
                when=started,
                where=str(record.get("branch", "unknown")),
                head=str(record.get("head_sha", "unknown"))[:10],
                lanes=", ".join(lanes),
                why=f"{len(lanes)} deferred, {'; '.join(reasons)}; the run was {record.get('verdict', 'unknown')}",
            )
        )
    return owed, warnings


def skipped_pushes(path: Path, since: date | None) -> tuple[list[Owed], list[str]]:
    """Every skip-log line on or after ``since`` (UTC): ``time<TAB>refs<TAB>shas<TAB>reason``, but branch deletes."""
    owed: list[Owed] = []
    warnings: list[str] = []
    if not path.is_file():
        return owed, warnings
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        fields = raw.split("\t")
        if len(fields) < 4:  # noqa: PLR2004 -- the hook writes four fields
            warnings.append(
                f"verify-deferred: warning: {path.name} line {number} has {len(fields)} fields, not 4; skipped"
            )
            continue
        stamp, refs, shas, reason = fields[0], fields[1], fields[2], "\t".join(fields[3:])
        if reason == NOTHING_PUSHED:
            continue
        day = _day(stamp)
        if day is None:
            warnings.append(f"verify-deferred: warning: {path.name} line {number} has no readable time; skipped")
            continue
        if since is not None and day < since:
            continue
        owed.append(Owed(when=stamp, where=refs, head=shas, lanes="every lane", why=f"skipped: {reason}"))
    return owed, warnings


def full_preflight_env(base: Mapping[str, str]) -> dict[str, str]:
    """The hook's environment for the preflight, with the scope forced to ``full``."""
    env = {name: value for name, value in base.items() if name not in GIT_HOOK_VARIABLES}
    env[preflight.SCOPE_ENV] = preflight.SCOPE_FULL
    return env


def verify_deferred(deps: VerifyDeps, *, since: date | None) -> DutyResult:
    """List what was left to CI since ``since``, then run the full preflight on HEAD."""
    out = deps.out or sys.stdout
    err = deps.err or sys.stderr
    runs, run_warnings = deferred_runs(deps.root / preflight.JOURNAL_RELATIVE, since)
    skips, skip_warnings = skipped_pushes(deps.root / SKIPS_RELATIVE, since)
    for warning in [*run_warnings, *skip_warnings]:
        print(warning, file=err)
    window = f"since {since.isoformat()}" if since is not None else "in the journals"
    print(
        f"verify-deferred: {len(runs)} run(s) deferred lanes to CI and {len(skips)} push(es) skipped the preflight {window}",
        file=out,
    )
    for owed in sorted([*runs, *skips], key=lambda item: item.when):
        print(f"  {owed.line()}", file=out)
    sha, branch = deps.head(deps.root)
    print(
        f"verify-deferred: running the full preflight on {branch}@{sha[:10]}: "
        f"{preflight.SCOPE_ENV}={preflight.SCOPE_FULL} {shlex.join(PREFLIGHT_ARGV)}",
        file=out,
        flush=True,
    )
    details: dict[str, Any] = {"runs_deferred": len(runs), "pushes_skipped": len(skips), "head": sha}
    try:
        code = deps.runner(PREFLIGHT_ARGV, deps.root, full_preflight_env(deps.environ or os.environ))
    except FileNotFoundError:
        details["exit_code"] = EXIT_CANNOT_RUN
        return DutyResult(
            ok=False,
            summary="verify-deferred: pixi is not on PATH, so the full preflight could not run",
            details=details,
        )
    details["preflight_exit"] = code
    if code == preflight.EXIT_OK:
        return DutyResult(
            ok=True, summary=f"verify-deferred: the full preflight on {sha[:10]} is green", details=details
        )
    if code == preflight.EXIT_CONFIG:
        details["exit_code"] = EXIT_CANNOT_RUN
        return DutyResult(
            ok=False,
            summary=f"verify-deferred: the full preflight could not run (exit {code})",
            details=details,
        )
    if code == preflight.EXIT_INTERRUPT:
        details["exit_code"] = EXIT_INTERRUPTED
        return DutyResult(ok=False, summary="verify-deferred: the full preflight was interrupted", details=details)
    return DutyResult(
        ok=False,
        summary=f"verify-deferred: the full preflight on {sha[:10]} is red (exit {code})",
        details=details,
    )


class PreflightDuty:
    """``steward preflight`` -- one verb, ``verify-deferred``."""

    name = "preflight"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        verb = getattr(ns, "preflight_verb", None)
        if verb != "verify-deferred":
            return DutyResult(ok=False, summary="preflight: need verify-deferred")
        deps: VerifyDeps | None = getattr(ns, "_preflight_deps", None)
        if deps is None:
            from .bootstrap import repo_root

            deps = VerifyDeps(root=repo_root())
        return verify_deferred(deps, since=getattr(ns, "since", None))
