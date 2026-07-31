#!/usr/bin/env python3
"""Keep the local dashboard current while any bmad-loop run is in flight.

THE GAP THIS CLOSES
-------------------
`docs/dashboard/index.html` carries `<meta http-equiv="refresh" content="120">`,
so the page reloads itself every two minutes — but nothing REGENERATES
`data.js`, which is a static snapshot. The board therefore reloads the same
stale file forever and a running story never appears.

Observed 2026-07-31: doctor 1.5 had been running six minutes, `generate.py`
detected it correctly (`loop-home in-flight: 1.5`), and the board showed
nothing — because no one had re-run the generator. Auto-refresh without
auto-regen is a page that lies twice a minute.

WHAT IT DOES
------------
Regenerates `data.js` on an interval for as long as at least one loop run is
live, then EXITS. Self-terminating is the point: no orphan process outlives the
fleet, and `dashboard-watch` can be started next to a run and forgotten.

"Live" reuses the definition `loop_stall_check` established — a run whose
`state.json` says neither `finished`, `stopped` nor paused. A paused run is not
live: it is waiting for a human, and regenerating for it would spin forever.

INTERVAL
--------
Default 100 s, deliberately just under the page's 120 s meta-refresh, so each
reload picks up data at most one cycle old. Raising it above 120 s means some
reloads show the previous cycle; that is a display lag, not an error.

WORKING-TREE NOTE
-----------------
`docs/dashboard/data.js` is TRACKED, so watching leaves it modified. That is
expected and harmless — the file is fully regenerable from the feeds, and this
repo already treats its timestamp churn as discardable. Before committing
unrelated work:

    git checkout -- docs/dashboard/data.js

NOT A CI SUBSTITUTE
-------------------
The published GitHub Pages board can never show in-flight state: it is derived
from `~/.bmad-loops/` and `tmux`, neither of which exists on a runner. This is a
LOCAL-only view, the same Tier-3-invisible-to-CI asymmetry that has bitten this
board before.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "docs" / "dashboard" / "generate.py"
LOOP_ROOT = Path.home() / ".bmad-loops"
DEFAULT_INTERVAL = 100


def live_runs() -> list[tuple[str, str]]:
    """(station, run_id) for every run that is neither finished, stopped nor paused."""
    out: list[tuple[str, str]] = []
    if not LOOP_ROOT.is_dir():
        return out
    for home in sorted(p for p in LOOP_ROOT.iterdir() if (p / ".git").exists()):
        runs = sorted((home / ".bmad-loop" / "runs").glob("*/"),
                      key=lambda p: p.stat().st_mtime, reverse=True)
        if not runs:
            continue
        try:
            st = json.loads((runs[0] / "state.json").read_text())
        except Exception:
            continue
        if st.get("finished") or st.get("stopped") or st.get("paused_reason"):
            continue
        out.append((home.name.removeprefix("pyforge-"), runs[0].name))
    return out


def regenerate() -> bool:
    r = subprocess.run([sys.executable, str(GEN), "--source", "sprint-status"],
                       cwd=ROOT, capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        print(f"  regen FAILED (rc={r.returncode}): {r.stderr.strip()[:200]}")
        return False
    for line in r.stdout.splitlines():
        if "in-flight" in line or "clearing" in line:
            print(f"  {line.strip()}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--interval", type=int, default=DEFAULT_INTERVAL,
                    help=f"seconds between regenerations (default {DEFAULT_INTERVAL})")
    ap.add_argument("--once", action="store_true",
                    help="regenerate once and exit, regardless of live runs")
    args = ap.parse_args()

    if args.once:
        return 0 if regenerate() else 1

    runs = live_runs()
    if not runs:
        print("no live run — regenerating once so the board is current, then exiting")
        return 0 if regenerate() else 1

    print(f"watching {len(runs)} live run(s), regenerating every {args.interval}s:")
    for station, run in runs:
        print(f"  {station}: {run}")
    print("(exits by itself when the last run finishes)\n")

    cycles = 0
    try:
        while True:
            still = live_runs()
            if not still:
                print(f"\nno live run left after {cycles} cycle(s) — final regen, then exit")
                regenerate()
                return 0
            print(f"[{time.strftime('%H:%M:%S')}] cycle {cycles + 1} — "
                  f"{', '.join(s for s, _ in still)}")
            regenerate()
            cycles += 1
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\ninterrupted — the board holds the last regenerated state")
        return 0


if __name__ == "__main__":
    sys.exit(main())
