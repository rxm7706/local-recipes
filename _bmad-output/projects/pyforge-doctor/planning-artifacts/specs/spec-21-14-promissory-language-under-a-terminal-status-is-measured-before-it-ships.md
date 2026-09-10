---
title: 'Promissory language under a terminal status is measured before it ships'
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

**Problem:** A document can declare a terminal status (`realized`/`shipped`) while its own body still reads as promissory, forward-looking narrative -- exactly the shape the herald Dream and `spec-pyforge-herald` both exhibit for a mid-build station, and which no count- or vocabulary-based signal (Stories 21.2/21.12/21.13) can catch. A loose narrative-language signal that cries wolf is worse than none: it gets muted by operators and never looked at again.

**Approach:** In the same new source module as Story 21.12 (`spec-status-body-consistency`, CAP-3), implement a bounded forward-looking-language pattern measured against the whole live tier before it ever joins `detectors`. The bar is dual: it must fire on the herald pair AND stay quiet everywhere else in the live tier. If it cannot clear both, the honest outcome is to ship it measured-and-rejected -- record the measured precision number in this Spec's own memlog rather than widen the threshold until the signal looks clean. Either way (accepted or rejected), the measured precision at ship time is recorded.

## Boundaries & Constraints

**Always:**
- The signal is measured against the FULL live tier before any decision to ship it.
- It must fire on the herald Dream/Spec pair specifically (the motivating case).
- It must stay quiet on every other live document (no false positives tolerated).
- The measured precision number is recorded in this Spec's own memlog regardless of outcome.

**Never:**
- Never widen the threshold after measurement just to make the signal look clean -- a rejected signal ships measured-and-rejected, not silently loosened.
- Never join `detectors` (Story 21.16's registration) if the dual bar isn't cleared.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Herald pair (the motivating case) | Herald Dream + `spec-pyforge-herald` both describe a mid-build station under `realized`/`shipped` | Signal fires | n/a |
| Quiet elsewhere | Every other live-tier document with a terminal status | Signal stays quiet -- no finding | n/a |
| Dual bar not cleared | Measurement shows either a herald-pair miss or a false positive elsewhere | Ship measured-and-rejected; record precision in this Spec's memlog; does not join `detectors` | n/a |
| Dual bar cleared | Fires on herald pair, quiet elsewhere | Ship as a real signal; record precision; eligible for Story 21.16's registration | n/a |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/` -- the same new source module as Story 21.12.
- `src/shared/packages/pyforge-doctor/tests/unit/` -- new unit tests, including the herald-pair fixture.
- This Spec's own `.memlog.md` -- carries the measured precision number regardless of accept/reject outcome.

## Tasks & Acceptance

**Execution:**
- `feature` -- implement a bounded forward-looking-language pattern in the shared source module.
- `feature` -- measure it against the whole live tier (every document with a terminal status).
- `feature` -- record the measured precision in this Spec's memlog.
- `feature` -- if the dual bar (fires on herald pair, quiet elsewhere) is not cleared, ship measured-and-rejected -- do not widen the threshold to force a pass.

**Acceptance Criteria:**
- Given the herald Dream and `spec-pyforge-herald` both describe a mid-build station under `realized`/`shipped`, which no count- or vocabulary-based signal can catch, and that a loose narrative signal that cries wolf gets muted -- and a muted detector is worse than none -- when a bounded forward-looking-language pattern is measured over the whole live tier, then it must both fire on the herald pair and stay quiet elsewhere before it joins `detectors`.
- If it cannot do both, the honest outcome is to ship it measured-and-rejected with the precision number recorded in the Spec's memlog rather than to widen the threshold until it looks clean.
- Either way, the signal's measured precision at ship time is recorded beside it.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: full suite green

## Spec Change Log

- 2026-09-10: added the missing `## Verification` -> `**Commands:**` section before dispatch. Its absence makes `core.gate.check_spec_binding` (marshal Story 2.7, MRS-GATE-010) unconditionally refuse dispatch verification for any spec authored this way -- confirmed live against `spec-21-13`'s own dispatch run, and again against `spec-21-14`'s.

## Review Triage Log
