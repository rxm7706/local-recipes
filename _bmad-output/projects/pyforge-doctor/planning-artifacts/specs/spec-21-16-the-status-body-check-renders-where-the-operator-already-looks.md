---
title: 'The status/body check renders where the operator already looks'
type: 'feature'
created: '2026-09-10'
status: 'in-progress'
baseline_revision: '82626b1239a5c47dc8604676ae3066bced6c52e9'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The document tier drifts faster than any detector polices it, and a finding nobody sees is a finding nobody acts on. Stories 21.2/21.12–21.15 build `spec-status-body-consistency`'s signals inside a new source module, but until that module is registered and its findings actually surface in the doctor report and fleet-picture's own ATTENTION block, the whole Spec produces nothing an operator will ever see.

**Approach:** Register the new source module in `sources/__init__.py`, wire it into `report-schema.json`, add it to `pixi.toml`'s `detectors` membership + task, and surface its findings in both the doctor report and the fleet-picture ATTENTION block beside `dream-vocab` and Story 21.2's `spec-status-missing`. Each joining signal carries its own measured precision over the live tier (Story 21.14's own dual-bar discipline). A signal rejected under Story 21.14 does not join. Meta-tests (sole ownership, source independence, read-only) must still pass with the new source in place.

## Boundaries & Constraints

**Always:**
- The new source module is registered in `sources/__init__.py` and joins the `detectors` set.
- Findings surface in the doctor report AND the fleet-picture ATTENTION block, beside `dream-vocab` and `spec-status-missing`.
- Each joining signal's measured precision is carried alongside it.
- The existing meta-tests (sole ownership, source independence, read-only) still pass.

**Never:**
- A signal rejected under Story 21.14's dual-bar measurement does NOT join `detectors` -- this story registers only what already cleared that bar.
- Never weaken or bypass the sole-ownership/source-independence/read-only meta-tests to accommodate the new source.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Registration | New source module built by Stories 21.2/21.12-21.15 | Registered in `sources/__init__.py`, joins `detectors` in `pixi.toml` | n/a |
| Findings surface | The source fires a finding | Appears in the doctor report AND fleet-picture's ATTENTION block, beside `dream-vocab`/`spec-status-missing` | n/a |
| Rejected signal | A sub-signal was shipped measured-and-rejected under Story 21.14 | Does not join `detectors` | n/a |
| Meta-tests | Sole ownership, source independence, read-only checks | Still pass with the new source registered | n/a |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py` -- new source module's registration.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/report-schema.json` -- schema update for the new finding shape.
- `pixi.toml` -- `detectors` membership + task entry.
- `src/shared/packages/pyforge-doctor/tests/unit/` and `tests/meta/` -- registration + meta-test coverage.

## Tasks & Acceptance

**Execution:**
- `feature` -- register the new source module in `sources/__init__.py`.
- `feature` -- wire its finding shape into `report-schema.json`.
- `feature` -- add it to `pixi.toml`'s `detectors` membership + task.
- `feature` -- surface its findings in fleet-picture's ATTENTION block beside `dream-vocab`/`spec-status-missing`.
- `feature` -- carry each joining signal's measured precision alongside its findings.
- `feature` -- confirm sole-ownership, source-independence, and read-only meta-tests still pass.

**Acceptance Criteria:**
- Given the document tier drifts faster than any detector polices it, and a finding nobody sees is a finding nobody acts on, when the source is registered and joins the `detectors` set, then its findings appear in the doctor report and the fleet-picture ATTENTION block beside `dream-vocab` and Story 21.2's `spec-status-missing`.
- Each signal that joins carries its measured precision over the live tier.
- A signal rejected under Story 21.14 does not join.
- The meta-tests still pass -- verdict sole ownership, source independence, and read-only.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: full suite green

## Spec Change Log

- 2026-09-10: added the missing `## Verification` -> `**Commands:**` section before dispatch. Its absence makes `core.gate.check_spec_binding` (marshal Story 2.7, MRS-GATE-010) unconditionally refuse dispatch verification for any spec authored this way -- confirmed live against `spec-21-13`'s own dispatch run, and again against `spec-21-14`'s.

## Review Triage Log
