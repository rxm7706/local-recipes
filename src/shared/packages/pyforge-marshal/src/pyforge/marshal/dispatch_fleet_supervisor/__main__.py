"""Fleet-drain campaign supervisor entry point (Story 22.7, FR-193 CAP-7).

The ONE place a fleet drain waits. ``marshal factory drain`` runs exactly one
cycle in the operator's foreground and returns; this detached sidecar then
re-runs the SAME documented command -- ``marshal factory drain --once
--campaign <run_id>`` -- on a tick until the campaign reports itself
complete. That is what makes chaining structural rather than scripted: a
station whose story finished merge-through-finalize (CAP-4: CI-green merge,
scoped ``sprint-ledger-sync --project <station>``, spec promotion) has an
advanced tracked ledger and a free in-flight slot by the next tick, so that
cycle hands it its next story.

Two disciplines it inherits from the per-story dispatch supervisor:

* **No foreground busy-wait (CAP-2).** The operator's invocation never
  sleeps; only this detached process does. The ~600 s watchdog that killed
  the hand ritual's busy-waiting parent has nothing to kill here.
* **No control channel back into ``cli/`` (AD-9).** This module imports no
  ``pyforge.marshal.cli`` module. It drives the campaign the same way an
  operator would -- by running the published command as a subprocess through
  the ``ProcessPort`` seam -- and reads only that command's own JSON
  envelope. Campaign state it must not lose across ticks (which stations are
  blocked) lives in the campaign journal, not in this process's memory.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from pyforge.core.process import PosixProcess, ProcessError, ProcessPort

_DEFAULT_TICK_SECONDS = 60

#: How many CONSECUTIVE cycles may fail to produce a readable envelope
#: before this supervisor gives up. ``ProcessPort.run`` never raises on a
#: non-zero exit, and ``cycle_reported_complete`` reads anything it cannot
#: parse as "not complete" -- correct in isolation (never abandon a live
#: campaign on one unreadable tick) but, with the default unbounded
#: ``--max-cycles``, a cycle command that can NEVER succeed (a traceback, an
#: argparse usage error, an unresolvable repo root) would otherwise be
#: re-run every tick forever. Distinguishing "ran and reported not-complete"
#: from "blew up" is what makes the ceiling safe to apply.
_MAX_CONSECUTIVE_UNREADABLE_CYCLES = 5


def build_cycle_argv(
    *,
    mode: str,
    leave_remaining: int,
    run_id: str,
    station: str | None = None,
    stories: str | None = None,
    harness: str | None = None,
    max_in_flight: int | None = None,
) -> list[str]:
    """The documented one-cycle command this supervisor re-runs each tick.

    Story 22.11 (FR-193 CAP-10): ``station``/``stories`` are re-appended on
    EVERY tick when set -- a station-scoped or explicit-sequence campaign
    must stay scoped/sequenced for its whole lifetime, not just its first
    cycle, or a supervised re-tick would silently widen back to fleet-wide
    ledger order.
    """
    argv = [
        sys.executable,
        "-m",
        "pyforge.marshal.cli.main",
        "factory",
        "drain",
        "--mode",
        mode,
        "--leave-remaining",
        str(leave_remaining),
        "--campaign",
        run_id,
        "--once",
        "--format",
        "json",
    ]
    if station:
        argv += ["--station", station]
    if stories:
        argv += ["--stories", stories]
    if harness:
        argv += ["--harness", harness]
    if max_in_flight is not None:
        argv += ["--max-in-flight", str(max_in_flight)]
    return argv


def cycle_completion(stdout: str) -> bool | None:
    """``data.complete`` out of one cycle's JSON envelope, or ``None``.

    ``None`` means "this cycle produced no readable verdict" -- a traceback,
    an argparse usage error, an envelope without ``data.complete``. That is
    deliberately NOT the same answer as ``False`` ("ran fine, still work to
    do"): stopping on "don't know" would silently abandon a live campaign,
    while treating it as an ordinary tick forever is how an unrunnable
    command becomes an immortal 60 s spinner. The caller ticks again on
    ``None`` but counts it, and gives up after
    ``_MAX_CONSECUTIVE_UNREADABLE_CYCLES``.
    """
    try:
        envelope = json.loads(stdout)
    except ValueError, TypeError:
        return None
    if not isinstance(envelope, dict):
        return None
    data = envelope.get("data")
    if not isinstance(data, dict) or "complete" not in data:
        return None
    return data.get("complete") is True


def cycle_reported_complete(stdout: str) -> bool:
    """``True`` only when a cycle explicitly reported itself complete."""
    return cycle_completion(stdout) is True


def run_fleet_campaign_supervisor(
    *,
    repo_root: Path,
    run_id: str,
    mode: str,
    leave_remaining: int,
    max_cycles: int,
    tick_seconds: int,
    station: str | None = None,
    stories: str | None = None,
    harness: str | None = None,
    max_in_flight: int | None = None,
    process: ProcessPort | None = None,
) -> int:
    process = process if process is not None else PosixProcess()
    argv = build_cycle_argv(
        mode=mode,
        leave_remaining=leave_remaining,
        run_id=run_id,
        station=station,
        stories=stories,
        harness=harness,
        max_in_flight=max_in_flight,
    )
    tick = max(1, tick_seconds)
    cycles = 0
    unreadable_streak = 0
    while True:
        if max_cycles and cycles >= max_cycles:
            print(
                f"fleet campaign supervisor: reached the {max_cycles}-cycle ceiling for campaign {run_id!r}; stopping",
                file=sys.stderr,
            )
            return 0
        # The operator's own sleep budget lives here and nowhere else.
        time.sleep(tick)
        cycles += 1
        try:
            result = process.run(argv, cwd=repo_root)
        except ProcessError as exc:
            print(
                f"fleet campaign supervisor: cycle {cycles} could not run: {exc}",
                file=sys.stderr,
            )
            return 1
        # A non-zero exit is an ordinary reported cycle (e.g. a station whose
        # queued story has no tracked spec), never a reason to abandon the
        # campaign -- that station is journaled as refused and is not retried.
        print(result.stdout, flush=True)
        if result.stderr:
            print(result.stderr, file=sys.stderr, flush=True)
        completion = cycle_completion(result.stdout)
        if completion is None:
            unreadable_streak += 1
            if unreadable_streak >= _MAX_CONSECUTIVE_UNREADABLE_CYCLES:
                print(
                    f"fleet campaign supervisor: {unreadable_streak} "
                    f"consecutive cycles for campaign {run_id!r} produced no "
                    "readable verdict; stopping rather than re-running an "
                    "unrunnable command forever. Last stderr: "
                    f"{(result.stderr or '').strip()[-500:]!r}",
                    file=sys.stderr,
                )
                return 1
            continue
        unreadable_streak = 0
        if completion:
            print(
                f"fleet campaign supervisor: campaign {run_id!r} complete after {cycles} supervised cycle(s)",
                file=sys.stderr,
            )
            return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fleet-drain campaign supervisor (Story 22.7)")
    parser.add_argument("repo_root")
    parser.add_argument("run_id")
    parser.add_argument("mode")
    parser.add_argument("leave_remaining", type=int)
    parser.add_argument("max_cycles", type=int)
    parser.add_argument("tick_seconds", type=int, nargs="?", default=_DEFAULT_TICK_SECONDS)
    # Story 22.11 (FR-193 CAP-10): both optional, empty string means "unset"
    # -- `_spawn_campaign_supervisor` always supplies the full positional
    # list (empty strings for an unscoped/unsequenced campaign), so there is
    # no parsing ambiguity between these two trailing optional positionals.
    parser.add_argument("station", nargs="?", default="")
    parser.add_argument("stories", nargs="?", default="")
    parser.add_argument("harness", nargs="?", default="")
    parser.add_argument("max_in_flight", nargs="?", default="")
    args = parser.parse_args(argv)
    max_in_flight: int | None = None
    if args.max_in_flight:
        max_in_flight = int(args.max_in_flight)
    return run_fleet_campaign_supervisor(
        repo_root=Path(args.repo_root),
        run_id=args.run_id,
        mode=args.mode,
        leave_remaining=args.leave_remaining,
        max_cycles=args.max_cycles,
        tick_seconds=args.tick_seconds,
        station=args.station or None,
        stories=args.stories or None,
        harness=args.harness or None,
        max_in_flight=max_in_flight,
    )


if __name__ == "__main__":
    raise SystemExit(main())
