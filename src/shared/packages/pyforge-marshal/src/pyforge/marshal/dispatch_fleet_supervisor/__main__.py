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


def build_cycle_argv(
    *,
    mode: str,
    leave_remaining: int,
    run_id: str,
) -> list[str]:
    """The documented one-cycle command this supervisor re-runs each tick."""
    return [
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


def cycle_reported_complete(stdout: str) -> bool:
    """Read ``data.complete`` out of one cycle's JSON envelope.

    Unparseable output is NOT read as "complete": an unreadable cycle means
    the supervisor does not know, and stopping on "don't know" would silently
    abandon a live campaign. It ticks again instead (``--max-cycles`` remains
    the ceiling).
    """
    try:
        envelope = json.loads(stdout)
    except (ValueError, TypeError):
        return False
    if not isinstance(envelope, dict):
        return False
    data = envelope.get("data")
    if not isinstance(data, dict):
        return False
    return data.get("complete") is True


def run_fleet_campaign_supervisor(
    *,
    repo_root: Path,
    run_id: str,
    mode: str,
    leave_remaining: int,
    max_cycles: int,
    tick_seconds: int,
    process: ProcessPort | None = None,
) -> int:
    process = process if process is not None else PosixProcess()
    argv = build_cycle_argv(mode=mode, leave_remaining=leave_remaining, run_id=run_id)
    tick = max(1, tick_seconds)
    cycles = 0
    while True:
        if max_cycles and cycles >= max_cycles:
            print(
                f"fleet campaign supervisor: reached the {max_cycles}-cycle "
                f"ceiling for campaign {run_id!r}; stopping",
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
        if cycle_reported_complete(result.stdout):
            print(
                f"fleet campaign supervisor: campaign {run_id!r} complete "
                f"after {cycles} supervised cycle(s)",
                file=sys.stderr,
            )
            return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fleet-drain campaign supervisor (Story 22.7)"
    )
    parser.add_argument("repo_root")
    parser.add_argument("run_id")
    parser.add_argument("mode")
    parser.add_argument("leave_remaining", type=int)
    parser.add_argument("max_cycles", type=int)
    parser.add_argument("tick_seconds", type=int, nargs="?", default=_DEFAULT_TICK_SECONDS)
    args = parser.parse_args(argv)
    return run_fleet_campaign_supervisor(
        repo_root=Path(args.repo_root),
        run_id=args.run_id,
        mode=args.mode,
        leave_remaining=args.leave_remaining,
        max_cycles=args.max_cycles,
        tick_seconds=args.tick_seconds,
    )


if __name__ == "__main__":
    raise SystemExit(main())
