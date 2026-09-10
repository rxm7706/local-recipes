---
title: 'A status comment that contradicts its own ledger is a finding'
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

**Problem:** A frontmatter status line can carry a trailing comment naming an epic or story key whose claim contradicts that key's own live ledger row -- found live on `docs/dreams/bmad-method-version-drift.md`, which reads `status: realized   # ... -> Epic 14 backlog` while `epic-14` actually reads `done` in the tracked ledger. This is the cheapest and most mechanical of this Spec's signals -- a pure string-vs-ledger reconciliation, no narrative judgment involved.

**Approach:** In the same new source module as Story 21.12 (`spec-status-body-consistency`, CAP-4), reconcile a frontmatter status comment naming an epic or story key against that key's live row in the tracked ledger. A comment naming no key is ignored rather than guessed at. A key absent from every ledger is reported as unresolvable, never silently read as agreement.

## Boundaries & Constraints

**Always:**
- A status comment naming an epic/story key is reconciled against that key's live ledger row.
- A contradiction is a WARN finding naming both the comment and the ledger row.
- A key absent from every ledger is reported as unresolvable, not as silent agreement.

**Never:**
- Never guess at a key when the comment names none -- an unparseable/keyless comment is ignored, not treated as a match or a miss.
- Never treat "key not found in any ledger" as agreement -- that is its own distinct unresolvable outcome.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Live contradiction (the motivating case) | `bmad-method-version-drift.md` reads `status: realized # ... -> Epic 14 backlog` while `epic-14` reads `done` in the tracked ledger | WARN finding naming both the comment and the ledger row | n/a |
| No key named | Status comment carries no parseable epic/story key | Ignored -- no finding | n/a |
| Key absent from every ledger | Comment names a key that exists in no tracked ledger | Reported as unresolvable, not as agreement | n/a |
| Comment agrees with ledger | Comment's claim matches the live ledger row | No finding | n/a |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/` -- the same new source module as Story 21.12.
- `src/shared/packages/pyforge-doctor/tests/unit/` -- new unit tests, including the `bmad-method-version-drift.md` live fixture.

## Tasks & Acceptance

**Execution:**
- `feature` -- parse a frontmatter status line's trailing comment for an epic/story key reference.
- `feature` -- reconcile the named key against every tracked project's `sprint-status-ledger.yaml`.
- `feature` -- emit a WARN finding naming both the comment and the live ledger row on contradiction.
- `feature` -- handle "no key named" (ignore) and "key absent from every ledger" (unresolvable) as distinct, non-agreement outcomes.
- `feature` -- add tests covering the live contradiction case, the no-key case, the unresolvable-key case, and the agreement case.

**Acceptance Criteria:**
- Given the `status: realized   # ... -> Epic 14 backlog` shape found live on `docs/dreams/bmad-method-version-drift.md` while `epic-14` reads `done` in the tracked ledger -- the cheapest and most mechanical of this Spec's signals -- when a frontmatter status comment naming an epic or story key is reconciled against that key's live ledger row, then the contradiction is a warn naming both the comment and the ledger row.
- A comment naming no key is ignored rather than guessed at.
- A key absent from every ledger is reported as unresolvable, not as agreement.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: full suite green

## Spec Change Log

- 2026-09-10: added the missing `## Verification` -> `**Commands:**` section before dispatch. Its absence makes `core.gate.check_spec_binding` (marshal Story 2.7, MRS-GATE-010) unconditionally refuse dispatch verification for any spec authored this way -- confirmed live against `spec-21-13`'s own dispatch run, and again against `spec-21-14`'s.

## Review Triage Log
