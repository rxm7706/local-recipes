---
title: A dead supervisor and a dead engine report identically — and only one of them needs help
type: dream
owner: marshal
status: archived
archived-reason: folded-into-station-dream
---

> **Consolidated into [[pyforge-marshal]]** on 2026-09-16 (one-chain-per-station CAP-8 pilot; folded from `fleet-status-supervisor-fallback`).

# A dead supervisor and a dead engine report identically — and only one of them needs help

## The Dream

`marshal status`'s fleet view (Story 5.1, FR-36/AD-5) exists so "what is
running?" is one question, not five. Its state derivation
(`core/status.py::derive_home_state`) treats supervisor liveness as an
override above everything else — its own docstring is explicit: "Supervisor
liveness overrides every other derived state... `supervisor_alive is False`
and `not finished` together are the ONLY unsupervised trigger." In code, the
very first branch:

```python
if not finished and supervisor_alive is False:
    return "unsupervised"
```

...returns before the function has looked at whether the harness itself has
any actively-running task (`"running"` via a non-terminal `TaskPhaseSnapshot`).
`supervisor_alive` is a real OS-level `process.is_alive(supervisor_pid)` probe
(`cli/status.py`) — but it only probes the *supervisor sidecar* Marshal itself
spawns, never the underlying `bmad-loop` engine process the sidecar watches.
When the sidecar is gone but the engine is not, the row still reads
`unsupervised`.

That gap is not hypothetical. On 2026-08-11, 5 live stations (marshal, doctor,
mason, steward, herald) were resumed via a bare `bmad-loop resume <run_id>`
instead of `marshal factory resume <slug>`. The bare path never spawns a
fresh supervisor sidecar, so `supervisor_alive` stayed `False` for the rest
of each run's life. Every subsequent `fleet-picture` run (the
`scripts/fleet_picture.py` wrapper around `marshal status --format json`)
reported all 5 as `UNSUPERVISED — needs re-spin` — even though each station
was independently confirmed fully alive and working: its `bmad-loop resume`
process present in `ps`, its tmux session live, and its own `state.json`
reading `stopped: false`. The report gave no way to tell "the engine actually
died too, re-spin it" from "the sidecar never attached, but the work is
fine" apart from that manual three-way cross-check — an operator (or another
AI session reading the fleet report) had to do it by hand, and did, three
separate landing-pass reports in that one session.

The immediate trigger is being closed operationally — the standing practice
is now "always resume via `marshal factory resume`, never bare `bmad-loop
resume`" — so this exact reproduction path should recur less. But the
underlying blind spot is bigger than its trigger: a supervisor sidecar can go
missing for any number of reasons independent of the engine's own health — a
sidecar crash, `marshal factory spin --foreground`'s own escape hatch that
never spawns one at all, a sidecar process that is killed and never
restarted, or (per the docstring itself) a `supervisor_pid` that is simply
never recovered. Every one of those hits the same first branch and collapses
to the same word, `"unsupervised"`, whether or not there is anything actually
wrong.

`derive_home_state`'s own AD-5 promise is that every row is derived from
journals and run state, never hand-assembled or silently guessed at — and
Story 5.1's own acceptance criterion already says "a home with a dead
supervisor is shown as unsupervised, not as healthy." That promise is half
kept: a dead supervisor is never shown as healthy, but a *healthy engine
behind a dead supervisor* is never shown as healthy either. The fleet view is
supposed to be the one question that replaces five; today, for this one
case, it silently reintroduces exactly those five.

## What it looks like when real

- When `supervisor_alive is False`, the fleet view has a second, independent
  signal to consult before it settles on `"unsupervised"` — something that
  answers "is the engine itself still doing anything?", not just "did its
  sidecar attach." What that signal is (an engine-process liveness probe, the
  run's own tmux session, freshness of `state.json`/journal activity, or some
  combination) is a design decision for the Spec and its downstream story,
  not settled here.
- The two failure shapes read differently in the report itself, so an
  operator — or an automated `fleet-picture` consumer — never again has to
  run the `ps` / `tmux ls` / `state.json` cross-check by hand to tell them
  apart.
- A run whose supervisor is gone AND whose engine is demonstrably gone too
  still reads as needing attention — this Dream narrows a false positive, it
  never softens a real one.
- The fix stays inside the spirit of AD-5: whatever the fallback checks, it
  is itself derived from journals/process state, never a hand-maintained
  flag or an operator override.

## Constraints

- This is a narrow gap-fill, not a redesign of the state model. The
  `FLEET_STATES` five-value vocabulary, and the rule that a dead supervisor
  is never reported as healthy, both stay intact.
- No implementation detail is prescribed here — not which process to probe,
  not whether tmux or `state.json` freshness is the right signal, not how
  the extra check is surfaced in the row. That is exactly what the Spec (and
  the story that decomposes it) is for.

## Realization log

- **2026-08-11** — Captured after a live reproduction the same day: 5
  stations resumed via bare `bmad-loop resume` reported `UNSUPERVISED —
  needs re-spin` for the rest of their run's life despite being
  independently verified alive and working, requiring the same manual
  cross-check (`ps`, `tmux ls`, `state.json`) three separate times in one
  session before the pattern was recognized and the operational fix
  (`marshal factory resume`, never bare `bmad-loop resume`) was adopted
  going forward. Queued as a Dream rather than patched by hand —
  `core/status.py`, `cli/status.py`, and `scripts/fleet_picture.py` were
  deliberately left untouched pending the Spec/story chain.
- **2026-08-14** — Realized — FR-181 (PRD, PR #435), Story 5.8 shipped (`d9f7691c97`), ledger-done. Status flipped by the 2026-08-14 dream-backlog chain audit.
