---
id: SPEC-marshal-status-harness-run-id-poisoning
owner-dream: docs/dreams/marshal-status-harness-run-id-poisoning.md
companions: []
sources:
  - docs/dreams/marshal-status-harness-run-id-poisoning.md
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what to build, test, and validate. The source document is for traceability only.

# A spin-time poll timeout never permanently blinds marshal status to a healthy run

## Why

Reproduced live 2026-08-15: a spin-time poll timeout (`MRS-SPIN-004`) journals
`harness_run_id: null` permanently into a run's launch OUTCOME entry; `cli/status.py`'s only
fallback (`_resolve_harness_run_id_for_resume`) re-reads the same poisoned field and can never
recover, even though `.bmad-loop/runs/<id>/state.json` is real, readable, and correctly
updating for the run's entire life. A prior session (2026-08-13) logged this same symptom as
resolved after simply not observing it once — it was never actually fixed, and it blinded
`marshal status`/`fleet-picture`/`dashboard-gen`'s in-flight card to a healthy, ~40-minute-long
run.

## Capabilities

- **CAP-1 — harness_run_id recovers via filesystem discovery.**
  - **intent:** A status read for a run whose journal-poll timed out (`harness_run_id: null`)
    recovers the real bmad-loop run id via the same `.bmad-loop/runs/` filesystem discovery
    `cli/spin.py::_latest_run_dir` already performs, rather than permanently reporting
    `unknown`.
  - **success:** Given a run whose journal entry has `harness_run_id: null` but whose
    `.bmad-loop/runs/<id>/` directory exists and is readable, `marshal status` reports the
    run's real state (`running`/`idle`/`stopped`), not `unknown` — reproduced against the live
    2026-08-15 case (`pyforge-doctor` story 9.1's spin).

- **CAP-2 — `MRS-STATUS-002` keeps firing correctly for genuinely unrecoverable cases.**
  - **intent:** A run whose directory truly cannot be found or read still reports `unknown`
    with the `MRS-STATUS-002` finding — the fix narrows the failure mode, it does not remove
    the honest-degradation signal.
  - **success:** Given a run with no discoverable `.bmad-loop/runs/` directory at all (or an
    unreadable one), status still reports `unknown` and the finding still fires.

## Constraints

- **No live subprocess or network call per status read** (NFR-14's own "no live query per
  home" discipline) — the fallback stays a plain `Path.glob`, the same budget
  `_latest_run_dir` already operates within.
- **Must not weaken `MRS-STATUS-002`'s own honest-degradation contract** for the case it
  actually protects — CAP-2 exists specifically to hold this line while CAP-1 narrows the
  surface that trips it.

## Non-goals

- Not fixing the poll's own timeout window or retry behavior — this Spec is about the
  permanent-blindness consequence of a timeout, not about preventing timeouts from happening.
- Not a general audit of every other journal field with a similar single-write-no-repair shape
  — scoped to `harness_run_id` specifically. `bmad-loop-liveness-footgun` (`engine.pid`'s own
  two-field liveness misread) is a separate, already-captured sibling Dream, not this Spec's
  territory.

## Success signal

The live 2026-08-15 reproduction case (a spin-time poll timeout on `pyforge-doctor`'s story
9.1 run) resolves to a correct state on the next status read instead of staying `unknown` for
the run's entire life.
