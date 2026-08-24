---
name: fleet-landing-pass-liveness
description: "Fleet landing-pass STEP 2 — the one supported command to answer \"is this run's engine alive?\" (FR-195 CAP-2; Story 24.2)."
metadata:
  type: reference
---

PyForge fleet landing passes call `pixi run -e local-recipes fleet-picture` first,
then **STEP 2 — verify engine liveness** for every station fleet-picture labels
RUNNING (or whenever a single action needs a cheap confirm). The supported answer
is one documented command — never hand-parse `engine.pid`, never `ps -p $(cat
engine.pid)`, and never a bare `grep 'bmad-loop run'` (that misses `resume` and
`resolve`, the 2026-08-14 mason incident).

## Primary check (always use this first)

From the station's loop home (`~/.bmad-loops/<slug>/`):

```bash
cd ~/.bmad-loops/<slug>
bmad-loop status <run_id> --json
bmad-loop list --json
```

Read the matching entry in `list --json`'s `runs[]`: `status` of `running` means
**alive**, `stopped` means **dead**, `unknown` means **unknown** (do not coerce).
`status --json` alone is run-state metadata; liveness comes from `list --json`
(bmad-loop 0.9+; Story 24.1 documents the same split in
`HarnessPort.engine_liveness`).

Marshal code may call the same contract via `HarnessPort.engine_liveness(project,
run_id)` — on-demand only, not wired into fleet sweep (NFR-14).

## Mason 2026-08-14 scenario (resume argv)

Mason's original `bmad-loop run` died; its supervisor auto-resumed as
`bmad-loop resume <run-id>`. A bare `grep 'bmad-loop run'` found nothing and
misread the station as dead. The primary check above still answers **alive**
because `list --json` keys off upstream's pid-reuse-safe probe, not argv text.
Do not fall back to hand-parsed `engine.pid` or a run-only grep.

## Optional corroboration only (never primary)

If cheap process corroboration is still useful after the primary check, match
**all three** engine argv forms:

```bash
ps -eo pid,cmd | grep -E '[b]mad-loop (run|resume|resolve)'
```

A hit here is corroboration, not the liveness verdict. An empty grep with
`list --json` still showing `running` means trust `list --json`. An empty grep
with `stopped`/`unknown` means dead/unverifiable — do not `cat engine.pid`.

Supervisor journal tail (`journal.jsonl` for `supervisor-heartbeat` /
`stage-push`) and `tmux ls` remain progress/stall diagnostics (`loop_stall_check`,
Story 5.8's sidecar fallback) — not substitutes for engine liveness.

## Never prescribe as the liveness answer

- `cat engine.pid` / `ps -p $(cat engine.pid)` — two-token identity breaks `ps -p`
- bare `grep 'bmad-loop run'` — misses `resume` and `resolve --resume`
- inferring liveness from `marshal status` / fleet-picture RUNNING alone

Related: [[bmad-loop-escalation-and-landing-traps]] (trap 5 — bare resume vs
`marshal factory resume`; CAP-3 in Story 24.3 covers UNSUPERVISED double-check).
