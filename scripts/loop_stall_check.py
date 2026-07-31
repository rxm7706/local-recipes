#!/usr/bin/env python3
"""Watchdog: find a bmad-loop run that has stopped making progress.

THE BLIND SPOT
--------------
`bmad-loop status` reports the last phase it *wrote*, not whether anything is
still happening. A session blocked on an interactive dialog therefore reads
`dev-running` indefinitely, and three things that should catch it do not:

  * the supervisor's stall ladder (`dev_stall_grace_s`, `dev_stall_nudges`)
    never fires;
  * the dialog is **not written to the session log** — it renders only in the
    multiplexer pane, so the log simply stops growing; and
  * nothing else polls.

Live cost 2026-07-31: scribe story 1.3 sat **74 minutes** on the CLAUDE.md
external-import dialog — seven times its 600 s grace — while five sibling
stations wrote to their logs every second. The only signal available was log
mtime going cold. Earlier the same class cost ~1 h on the folder-trust dialog
(warden 6.3).

This watchdog turns that signal into a check. It is deliberately about
*progress*, not about any particular dialog: it catches the folder-trust prompt,
the external-import prompt, a wedged model call, a hung nested CLI (herald's
`claude -p` that outlived its own `timeout 90`), and whatever prompt ships next.

HOW IT DECIDES
--------------
For each loop home, take the most recent run directory. A run is a candidate
only if it is genuinely live: its `state.json` says it is neither `finished`,
`stopped` nor paused. For a live run, compare *now* against the newest mtime
among its session logs and its journal.

  quiet <  threshold          -> working
  quiet >= threshold          -> STALLED, reported

A finished, stopped or paused run is never reported: a paused run is *supposed*
to sit still, and reporting it would train the check away.

Threshold defaults to 15 minutes. That is above the longest legitimate quiet
period observed across the 2026-07-30/31 six-station run (a single dev pass
thinking between tool calls, ~4 min) and well below the 74-minute incident.

EXIT
    0  no live run is stalled
    1  at least one live run has gone quiet past the threshold
"""
from __future__ import annotations

# Registry declaration — see scripts/detectors.py. `runtime`: reads host state (gitignored Tier-3 sprint feeds / tmux / ~/.bmad-loops), so CI cannot run it.
DETECTOR = {"scope": "runtime"}

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

LOOP_ROOT = Path.home() / ".bmad-loops"
DEFAULT_MIN = 15


def newest_activity(run: Path) -> float:
    """Newest mtime across a run's logs + journal. 0.0 if it has produced nothing."""
    times = [p.stat().st_mtime for p in run.glob("logs/*") if p.is_file()]
    journal = run / "journal.jsonl"
    if journal.is_file():
        times.append(journal.stat().st_mtime)
    return max(times, default=0.0)


def live_state(run: Path) -> tuple[bool, str]:
    """(is_live, why_not). A run must be neither finished, stopped nor paused."""
    try:
        st = json.loads((run / "state.json").read_text())
    except Exception:
        return False, "unreadable state.json"
    if st.get("finished"):
        return False, "finished"
    if st.get("stopped"):
        return False, "stopped"
    if st.get("paused_reason"):
        return False, f"paused ({st.get('paused_stage') or 'escalation'})"
    return True, ""


def tmux_sessions() -> set[str]:
    try:
        r = subprocess.run(["tmux", "ls", "-F", "#{session_name}"],
                           capture_output=True, text=True, timeout=10)
        return set(r.stdout.split()) if r.returncode == 0 else set()
    except Exception:
        return set()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--minutes", type=int, default=DEFAULT_MIN,
                    help=f"quiet period that counts as stalled (default {DEFAULT_MIN})")
    ap.add_argument("--verbose", action="store_true", help="show every run considered")
    args = ap.parse_args()

    if not LOOP_ROOT.is_dir():
        print(f"no loop homes at {LOOP_ROOT} — nothing to watch")
        return 0

    now, live_panes, stalled, checked = time.time(), tmux_sessions(), [], 0

    for home in sorted(p for p in LOOP_ROOT.iterdir() if (p / ".git").exists()):
        runs = sorted((home / ".bmad-loop" / "runs").glob("*/"),
                      key=lambda p: p.stat().st_mtime, reverse=True)
        if not runs:
            continue
        run = runs[0]
        ok, why = live_state(run)
        if not ok:
            if args.verbose:
                print(f"  skip     {home.name:22s} {run.name}  ({why})")
            continue
        checked += 1
        last = newest_activity(run)
        quiet_min = (now - last) / 60 if last else float("inf")
        pane = f"bmad-loop-{run.name}"
        attached = pane in live_panes
        if quiet_min >= args.minutes:
            stalled.append((home.name, run.name, quiet_min, attached))
        elif args.verbose:
            print(f"  working  {home.name:22s} {run.name}  quiet {quiet_min:.1f}m")

    print(f"loop-stall — {checked} live run(s) checked, threshold {args.minutes}m\n")
    if stalled:
        for name, run, quiet, attached in stalled:
            q = "never produced output" if quiet == float("inf") else f"silent for {quiet:.0f} min"
            print(f"  ✗ [stalled] {name}: run {run} claims to be running but has been {q}.")
            if attached:
                print(f"      Its pane is alive — inspect it: tmux attach -t bmad-loop-{run}")
                print(f"      An interactive dialog does NOT reach the log; only the pane shows it.")
            else:
                print(f"      No tmux pane named bmad-loop-{run} — the engine is gone; the run")
                print(f"      state is stale and will read `dev-running` forever. Resume or stop it.")
        print(f"\n{len(stalled)} run(s) stalled. `bmad-loop status` will NOT show this.")
        return 1

    print("OK: every live run is making progress.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
