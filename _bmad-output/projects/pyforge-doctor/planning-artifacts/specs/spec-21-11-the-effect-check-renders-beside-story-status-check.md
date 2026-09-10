---
title: 'The effect check renders beside `story-status-check`'
type: 'feature'
created: '2026-09-10'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** An operator reading "story 33.4 landed" today learns "and nothing calls
it" only three weeks later, in a manual readiness pass. The capability-effect check
(Stories 21.9/21.10) exists as a module but is not registered — it does not join the
`detectors` set and its findings do not reach the doctor report or fleet-picture.

**Approach:** Register the new source (from Story 21.9) and wire it into the
`detectors` set, `sources/__init__.py`, `report-schema.json`, and `pixi.toml`, the
same wiring shape every other source follows. One `detectors` run then answers both
"did the story land" and "is the capability reached" on adjacent lines. The two
checks stay **separate modules with separate check names** — this is explicitly not a
re-implementation of `story-status-check`. The meta-tests must still pass: the
verdict stays sole-owned by `verdict.exit_code_for`
(`tests/meta/test_verdict_sole_ownership.py`) and the new source imports no station
package it judges (`tests/meta/test_source_independence.py`).

## Boundaries & Constraints

**Always:**
- The capability-effect source is registered in `sources/__init__.py`'s `REGISTRY`,
  dispatched via `sources/__main__.py`, enumerated in `report-schema.json`, and joins
  `detectors` in `pixi.toml`.
- Its findings reach both the doctor report and the fleet-picture ATTENTION block.
- The check remains a **separate module with a separate check name** from
  `story-status-check` — not a re-implementation or merge of the two.
- `tests/meta/test_verdict_sole_ownership.py` continues to pass — the verdict stays
  sole-owned by `verdict.exit_code_for`.
- `tests/meta/test_source_independence.py` continues to pass — the new source imports
  no station package it judges.

**Never:**
- Never merge the capability-effect check into `story-status-check`'s own module or
  check name.
- Never let the new source's registration weaken or bypass either meta-test.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Full `detectors` run | Operator runs `pixi run -e local-recipes detectors` | Both "did the story land" (`story-status-check`) and "is the capability reached" (the new check) answer on adjacent lines | n/a |
| Finding surfaces | The new source emits a finding (e.g. the `risk-tiered-review-depth` case) | Appears in the doctor report and the fleet-picture ATTENTION block | n/a |
| Meta-test: verdict ownership | Full suite run after registration | `test_verdict_sole_ownership.py` passes — `verdict.exit_code_for` remains sole owner | n/a |
| Meta-test: source independence | Full suite run after registration | `test_source_independence.py` passes — new source imports no judged station package | n/a |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py` — new `SourceRegistration` entry for the Story 21.9 module.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/data/report-schema.json` — enum entry for the new check.
- `pixi.toml` — `detectors` membership + a standalone task for the new check.
- `src/shared/packages/pyforge-doctor/tests/unit/` — dispatch/registry test updates.
- `src/shared/packages/pyforge-doctor/tests/meta/` — `test_verdict_sole_ownership.py`, `test_source_independence.py` (verify continued pass, no edits expected unless dynamically derived).

## Tasks & Acceptance

**Execution:**
- `feature` — register the Story 21.9/21.10 source module in `sources/__init__.py`'s `REGISTRY` and `sources/__main__.py`'s `DISPATCH`.
- `feature` — enumerate the new check in `report-schema.json`.
- `feature` — add the new check to `pixi.toml`'s `detectors` membership plus a standalone task.
- `feature` — wire the finding into the fleet-picture ATTENTION block, mirroring existing source precedent.
- `feature` — confirm `test_verdict_sole_ownership.py` and `test_source_independence.py` both pass with the new source registered.

**Acceptance Criteria:**
- Given an operator reading "story 33.4 landed" today learns "and nothing calls it" three weeks later in a readiness pass, when the source is registered and joins the `detectors` set, then one `detectors` run answers both questions on adjacent lines — did the story land, is the capability reached.
- The finding reaches the doctor report and the fleet-picture ATTENTION block.
- The two checks stay separate modules with separate check names (this is not a re-implementation of `story-status-check`).
- The meta-tests still pass: the verdict stays sole-owned by `verdict.exit_code_for` (`tests/meta/test_verdict_sole_ownership.py`) and the new source imports no station package it judges (`tests/meta/test_source_independence.py`).

## Spec Change Log

## Review Triage Log
