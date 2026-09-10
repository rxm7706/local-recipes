---
title: 'The effect check renders beside `story-status-check`'
type: 'feature'
created: '2026-09-10'
status: 'done'
baseline_revision: 'b2f99e866acf5ea45b4a90a8edd57b1fb1d03dbd'
review_loop_iteration: 0
followup_review_recommended: true
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

### 2026-09-10 — Review pass
- verdicts: 12 findings — high 0, medium 2, low 1, false 2, reject 1, defer 6
- findings:
  - `[false]` `[reject]` Spec Change Log / Auto Run Result empty mid-review — workflow artifact filled at finalize, not a code defect.
  - `[medium]` `[patch]` `_DOCTOR_SOURCE_TASKS` count-only tests allow dropping `capability-effect` silently — added `test_doctor_source_tasks_include_capability_effect_beside_story_status` pinning name, task, and ordering after `story-status`.
  - `[medium]` `[patch]` Fleet-picture ATTENTION wiring for capability-effect untested at `main()` — added `test_main_attention_watches_capability_effect_findings` plus helper meta-test stub update.
  - `[low]` `[patch]` New CFE meta test missing from `skf-manifest.yaml` — added `test_fleet_picture_capability_effect.py` beside sibling fleet-picture meta tests.
  - `[false]` `[reject]` Meta-tests pass not evidenced — ran `test_verdict_sole_ownership.py`, `test_source_independence.py`, and dispatch tests (200 passed).
  - `[maybe-false]` `[defer]` `scripts/.spec-surface-baseline.json` not stamped for new meta test — cross-spec drift includes 21.10 paths; scoped `--write-baseline --spec pyforge-doctor/spec-21-11-…` belongs at PR land after memlog reconcile.
  - `[maybe-false]` `[defer]` Story 21.10 live-fleet integration test still open — pre-existing follow-up, not introduced by 21.11 wiring.
  - `[low]` `[defer]` `_run_doctor_sources` docstring still says "ten ported sources" — pre-existing stale comment, not caused by this story's tuple append.
  - `[maybe-false]` `[defer]` `_DOCTOR_SOURCE_TASKS` ↔ `pixi.toml` task cross-check (DW-FU-6-9-3) — repo-wide known gap, unchanged.
  - `[maybe-false]` `[defer]` Edge-case hunter returned no findings — no action.
  - `[maybe-false]` `[defer]` Intent-alignment surface-gap notes (REGISTRY/schema pre-21.11, doctor-report E2E) — satisfied by prior stories or out of 21.11 scope; wiring AC met.

## Auto Run Result

Status: done

Summary: Wired the existing `capability-effect` source (Stories 21.9/21.10 module) into operational surfaces beside `story-status-check`: `DISPATCH`, `_DOCTOR_SOURCE_TASKS`, standalone `capability-effect-check` pixi task, and fleet-picture ATTENTION watch lines.

Files changed:
- `sources/__main__.py` — `capability-effect` DISPATCH entry
- `scripts/detectors.py` — `_DOCTOR_SOURCE_TASKS` pair immediately after `story-status`
- `pixi.toml` — `capability-effect-check` task
- `scripts/fleet_picture.py` — `capability_effect_findings()` + ATTENTION integration
- `tests/unit/test_sources_dispatch.py` — dispatch map entry
- `tests/scripts/test_detectors_doctor_sources.py` — ordering/name regression pin
- `tests/scripts/test_fleet_picture_baseline_drift_attention.py` — ATTENTION wiring test + stub
- `.claude/skills/conda-forge-expert/tests/meta/test_fleet_picture_capability_effect.py` — helper meta-test (new)
- `_bmad/_config/skf-manifest.yaml` — manifest entry for new meta test
- Comment-only updates in `sources/__init__.py`, `capability_effect.py`

Review: 3 patches applied (detectors ordering test, ATTENTION main test, skf-manifest); 6 deferred (spec-surface baseline cross-spec, live-fleet integration, stale docstring, DW-FU-6-9-3, edge-case empty, intent-alignment informational).

Follow-up review recommended: true — two medium wiring-regression patches on first pass; unverified risk is silent drop from `_DOCTOR_SOURCE_TASKS` or ATTENTION block if a future edit removes wiring without the new regression tests.

Verification:
- `pixi run -e pyforge-doctor pytest … test_sources_dispatch.py test_sources_capability_effect_verified.py test_verdict_sole_ownership.py test_source_independence.py` — 200 passed
- `pixi run -e pyforge-ci pyforge-doctor-scripts-test` — passed (297 tests)
- `pixi run -e local-recipes test-skill -- --meta -k fleet_picture_capability_effect` — 3 passed
- `pixi run -e local-recipes capability-effect-check` — exit 0, WARN findings emitted
- `pixi run -e local-recipes detectors -- --list` — shows `story-status` then `capability-effect` adjacent
