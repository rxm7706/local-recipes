---
title: 'Deferred-work intake refuses an entry that cites nothing checkable'
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

**Problem:** Epic 11 is 7/7 `done` while the Spec's own companion measurement
document, `sweep-tooling-effectiveness-2026-09-08.md`, finds CAP-3 matching **0 of
1,410** entries, CAP-2 skipping **0** of 183 due entries, and CAP-6 finding 1
near-duplicate pair where a hand sweep found 4 defect classes. The binding constraint,
measured directly: **144 of 183** never-verified entries cite no extractable path at
all. Intake has no gate against this, so ungrounded entries keep entering the ledger
and the never-verified population keeps growing regardless of how well the
verification machinery itself works.

**Approach:** Intake refuses (or explicitly flags) a new entry that cites no
resolvable `location:`. A new entry with no checkable claim cannot enter a ledger
silently. An entry **already** in a ledger is never rewritten — the sweep stays
read-only, exactly as it is today. The refusal names the missing field and describes
what a resolvable one looks like. This is the companion measurement document's own
recommendation #1, and it is the reason CAP-2/CAP-3/CAP-6 are left as written rather
than rewritten to describe their own inertness — this story fixes the intake gap that
makes those CAPs' inertness inevitable, rather than patching the CAPs themselves.

## Boundaries & Constraints

**Always:**
- Intake refuses (or explicitly flags) any new entry that cites no resolvable
  `location:`.
- The refusal names the missing field and describes what a resolvable one looks like.
- The never-verified population stops growing as a direct effect of this gate.

**Never:**
- An entry already present in a ledger is never rewritten by this story — the sweep
  and intake both stay read-only with respect to existing entries.
- CAP-2/CAP-3/CAP-6 of `spec-deferred-work-resolution-sweep` are not rewritten by this
  story — this story addresses the intake gap that produces their measured
  inertness, not the CAPs' own text.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| New entry with no resolvable `location:` | An entry citing no extractable path (the measured 144-of-183 shape) | Refused or explicitly flagged; refusal names the missing field and what a resolvable one looks like | n/a |
| New entry with a resolvable `location:` | An entry citing a real, extractable path | Enters the ledger normally | n/a |
| Existing ledger entry, regardless of location quality | An entry already present before this story | Never rewritten — read-only, as today | n/a |
| Measured effect | 144 of 183 never-verified entries cite no extractable path today | Never-verified population growth is halted for entries lacking a checkable claim | n/a |

</intent-contract>

## Code Map

- `deferred_work_intake.py` — the intake path this story gates.
- The doctor-side module backing deferred-work intake (under `src/shared/packages/pyforge-doctor/src/pyforge/doctor/`).
- `tests/unit/` — new tests for the refuse/flag behavior.

## Tasks & Acceptance

**Execution:**
- `feature` — add a check in `deferred_work_intake.py` (and its doctor-side module) that refuses or explicitly flags a new entry citing no resolvable `location:`.
- `feature` — the refusal/flag message names the missing field and describes what a resolvable `location:` looks like.
- `feature` — add unit tests covering: entry with no location (refused), entry with a resolvable location (accepted), and confirmation that existing ledger entries are never rewritten.

**Acceptance Criteria:**
- Given Epic 11 is 7/7 `done` while the companion measurement finds CAP-3 matching 0 of 1,410 entries, CAP-2 skipping 0 of 183 due entries, and CAP-6 finding 1 near-duplicate pair where a hand sweep found 4 — with 144 of 183 never-verified entries citing no extractable path — when intake refuses (or explicitly flags) an entry citing no resolvable `location:`, then a new entry with no checkable claim cannot enter a ledger silently.
- An entry already in a ledger is never rewritten (the sweep is read-only and stays so).
- The refusal names the missing field and what a resolvable one looks like.
- The never-verified population stops growing — the companion's own recommendation #1, and the reason CAP-2/CAP-3/CAP-6 are left as written rather than rewritten to describe their own inertness.

## Spec Change Log

## Review Triage Log
