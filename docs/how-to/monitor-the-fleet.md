---
sources:
  - scripts/fleet_picture.py
  - scripts/fleet-poll-hourly.sh
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/main.py
  - .claude/memory/reference/fleet-landing-pass-liveness.md
  - pixi.toml
verified: 2026-09-20
---

# How to Monitor the Fleet

The PyForge ecosystem consists of 8 autonomous stations (e.g. `pyforge-steward`, `pyforge-marshal`, `pyforge-mason`). Operating the platform requires constant visibility into the state of each station, the active sprint ledgers, and any pending or blocked tasks.

This guide explains how to use the fleet monitoring tools to gain situational awareness.

## Generate a Fleet Picture

The most comprehensive way to monitor the fleet is by generating the Fleet Picture. It reads each station's **tracked** `_bmad-output/projects/<slug>/planning-artifacts/sprint-status-ledger.yaml` (the twin of the gitignored Tier-3 feed — never the feed itself, and never an ad-hoc regex over commit subjects) and aggregates every station into one report: done / in-progress / projected / blocked counts, plus an `ATTENTION` block naming anything that needs a human (an escalation, a dead run, idle-with-backlog, an open PR). Running stations are detected live from `marshal status --format json`.

```bash
pixi run -e pyforge-guild fleet-picture
```

`fleet-picture` is read-only and never gates — it always exits 0. Paste its stdout verbatim when reporting; do not reformat it. Throttle it to roughly hourly; it is a report, not a poll.

## Runtime state of the running loops

For what is actually running right now — one row per loop home with its runtime state (idle / running / paused-on-escalation / stopped / UNSUPERVISED), the current story, elapsed time and budget — use Marshal:

```bash
pixi run -e pyforge-guild marshal status                      # whole fleet
pixi run -e pyforge-guild marshal status --project <slug>     # one station
pixi run -e pyforge-guild marshal watch --fleet               # ground-truth + delta + next-check delay
```

`marshal status` derives everything from run journals and state, never from a hand-maintained file. `UNSUPERVISED` means no Marshal supervisor sidecar, not that the engine is dead — before re-spinning, confirm liveness with `bmad-loop status <run_id> --json` and `bmad-loop list --json` in the loop home (`.claude/memory/reference/fleet-landing-pass-liveness.md`).

## Automated Hourly Polling

For continuous background monitoring on an operator's workstation, `scripts/fleet-poll-hourly.sh` runs a poll at :30 past each hour:

```bash
./scripts/fleet-poll-hourly.sh
```

Each tick fetches and rebases the primary checkout and every loop home under `~/.bmad-loops/pyforge-*/` onto `origin/main`, pushes their branches, then writes an `AGENT_LOOP_TICK_fleet-poll` line to `.cursor/fleet-poll.log` whose prompt asks the attached Cursor agent to run the full `fleet-picture`, `pyforge marshal status --format json`, and summarise the delta since the last poll. It is a workstation loop that wakes an agent — not a cron job for a deployment server, and it does not itself detect stalled runs; the `loop-stall-check` and `baseline-drift-check` watchdogs (`pixi run -e pyforge-guild detectors -- --scope runtime`) do that.
