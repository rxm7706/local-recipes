---
spec: fleet-status-supervisor-fallback
status: shipped
owner-dream: docs/dreams/fleet-status-supervisor-fallback.md
surface:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/status.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py
sources:
  - ../../../../../../docs/dreams/fleet-status-supervisor-fallback.md
open_questions:
  - "Which concrete fallback signal (a recorded engine/launch pid liveness probe, the run's own tmux session name, or state.json/journal mtime freshness, or some combination) answers 'is the engine still doing anything?' -- a story-level design decision, not resolved by the Dream."
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what
> to build, test, and validate. `docs/dreams/fleet-status-supervisor-fallback.md` is listed in
> `sources:` for narrative rationale this contract intentionally omits.

# Fleet status wants a fallback liveness check when the supervisor sidecar is gone

## Why

A pain to solve. `marshal status`'s fleet view (Story 5.1, FR-36/AD-5) exists so "what is
running?" is one question, not five. Its state derivation,
`core/status.py::derive_home_state`, treats supervisor liveness as an override above
everything else: `if not finished and supervisor_alive is False: return "unsupervised"` runs
before the function ever checks whether the harness itself has an actively-running task.
`supervisor_alive` (`cli/status.py`) is a real OS-level probe of the *supervisor sidecar*
Marshal spawns -- never of the underlying `bmad-loop` engine process the sidecar watches. When
the sidecar is gone but the engine is not, the row still reads `"unsupervised"`.

This is not hypothetical: on 2026-08-11, 5 live stations were resumed via bare `bmad-loop
resume` instead of `marshal factory resume`, which never spawns a fresh sidecar. Every
subsequent fleet report showed all 5 as needing a re-spin, although each was independently
confirmed alive and working (`ps`, `tmux ls`, `state.json`). The operator had to run that
three-way manual cross-check by hand three times in one session before the pattern was
recognized. The immediate trigger is closed operationally (always resume via `marshal factory
resume`), but the underlying blind spot is broader -- any sidecar death independent of engine
health (crash, `--foreground`'s escape hatch, a killed-and-restarted sidecar, a pid never
recovered) hits the same branch and reports the same word.

## Capabilities

- **CAP-1**
  - **intent:** When `supervisor_alive is False`, `derive_home_state`'s caller consults a
    second, independent liveness signal for the run's engine before settling on
    `"unsupervised"`, so a dead sidecar behind a demonstrably live engine is distinguishable
    from a run that actually needs a re-spin.
  - **success:** Reproducing the 2026-08-11 scenario (a run resumed with no supervisor
    sidecar, engine still active) no longer reports `"unsupervised"` on an active run; a run
    whose engine is also gone still does.
- **CAP-2**
  - **intent:** The two failure shapes (sidecar-dead-engine-alive vs. sidecar-dead-engine-dead)
    are distinguishable from the fleet report itself.
  - **success:** An operator or an automated `fleet-picture` consumer can tell the two cases
    apart by reading the report -- never by running `ps` / `tmux ls` / `state.json` by hand.

## Constraints

- **Always:** the `FLEET_STATES` five-value vocabulary is unchanged, and the existing rule
  that a dead supervisor is never reported as healthy stays intact -- this work narrows a
  false positive, it never softens a real one.
- **Always:** whatever the fallback checks is itself derived from journals/process state
  (AD-5's own promise) -- never a hand-maintained flag or an operator override.

## Non-goals

- **Not** a redesign of the state model or the `FLEET_STATES` vocabulary.
- **Not** a prescription of which process to probe, whether tmux or `state.json` freshness is
  the right signal, or how the extra check surfaces on the row -- left to the downstream
  story's design.
- **Not** an attempt to eliminate every possible cause of a dead supervisor sidecar -- only to
  stop conflating "sidecar dead, engine fine" with "actually needs attention" in the report.

## Success signal

Given a run whose supervisor sidecar is dead but whose engine is independently verifiable as
alive (the exact 2026-08-11 reproduction: `bmad-loop resume` process present, tmux session
live, `state.json` reading `stopped: false`), `marshal status` / `fleet-picture` no longer
reports that row as needing a re-spin -- and a run whose engine is also genuinely gone still
does.

## Open Questions

- "Which concrete fallback signal (a recorded engine/launch pid liveness probe, the run's own
  tmux session name, or state.json/journal mtime freshness, or some combination) answers 'is
  the engine still doing anything?' -- a story-level design decision, not resolved by the
  Dream."
