---
title: 'A capability with no caller outside its own tests is a finding'
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

**Problem:** The 2026-09-09 pass found eighteen capabilities sharing one shape: a
`done` epic whose named success criterion has never actually been exercised. Three of
marshal's four were only visible by hand-grepping for call sites — nothing detects
this class mechanically today.

**Approach:** A new source module joins on `(spec-slug, CAP-N)` — the same pair
`board.py`'s own `_parse_declared_cap_ids` / `_cited_cap_ids_by_spec` already produce
for INV-A. It reaches code through the citing story's `Surface:` line in the owning
station's `epics.md`, and asks whether any symbol those surfaces define is referenced
outside its own module and outside tests. It must name
`risk-tiered-review-depth`'s `classify_review_tier` / `resolve_review_cycles` (zero
callers outside `core/gate.py` and `tests/unit/test_gate.py`) as a **live** finding —
proven against the real fleet before this story closes, not against a fixture that
constructs both sides from one synthetic value (the `sibling-dreams-drift` failure,
Story 21.3, is the cautionary precedent this story must not repeat). A capability
whose surfaces are documents rather than code modules reports "not applicable,
document surface" rather than a false "no callers." The reach is a bounded whole-word
textual scan, and the finding text says so. An unreadable `epics.md` or an absent
surface path degrades to a named finding, never to silence.

## Boundaries & Constraints

**Always:**
- The join key is `(spec-slug, CAP-N)`, reusing `board.py`'s existing
  `_parse_declared_cap_ids` / `_cited_cap_ids_by_spec` pair.
- Code reach is derived from the citing story's `Surface:` line in the owning
  station's `epics.md`.
- A capability is reported as having no caller only if no symbol its surfaces define
  is referenced outside its own module and outside tests.
- The `risk-tiered-review-depth` case (`classify_review_tier` / `resolve_review_cycles`,
  zero callers outside `core/gate.py` and `tests/unit/test_gate.py`) must be proven as
  a **live** finding against the real fleet before this story closes — not merely
  against a synthetic fixture.
- The reach is a bounded whole-word textual scan, and the finding text states this
  explicitly (it is not a full static-analysis call graph).
- An unreadable `epics.md` or an absent surface path degrades to a named finding,
  never silence.

**Never:**
- A capability whose declared surfaces are documents (not code modules) never
  produces a false "no callers" finding — it reports "not applicable, document
  surface" instead.
- The join and reach mechanism must not be validated only against a fixture that
  constructs both sides from one synthetic value — that is precisely the failure mode
  that made Story 16.1 (`sibling-dreams-drift`) structurally incapable of a live
  finding, per Story 21.3.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Live no-caller case | `risk-tiered-review-depth`'s `classify_review_tier`/`resolve_review_cycles`, zero callers outside `core/gate.py` and its own test | Live finding naming both symbols and their zero-caller status | n/a |
| Capability with real external callers | A CAP whose surface symbols are referenced outside their own module and outside tests | No finding | n/a |
| Document-surfaced capability | A CAP whose declared surfaces are documents, not code | Reports "not applicable, document surface" — never a false "no callers" | n/a |
| Unreadable `epics.md` | Owning station's `epics.md` cannot be read | Named finding | Fail-open, named, never silent |
| Absent surface path | A `Surface:` line names a path that does not exist | Named finding | Fail-open, named, never silent |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/` — new source module implementing the capability-effect check (CAP-1 of `spec-capability-effect-check`).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/board.py` — reused `_parse_declared_cap_ids` / `_cited_cap_ids_by_spec` for the `(spec-slug, CAP-N)` join.
- `src/shared/packages/pyforge-doctor/tests/unit/` — new unit tests.
- `src/shared/packages/pyforge-doctor/tests/fixtures/` — new fixtures.
- `src/shared/packages/pyforge-marshal/` (read-only reference) — the live `risk-tiered-review-depth` / `classify_review_tier` / `resolve_review_cycles` / `core/gate.py` case this story must prove against.

## Tasks & Acceptance

**Execution:**
- `feature` — implement the new source module: join on `(spec-slug, CAP-N)` via `board.py`'s existing parsers, resolve code reach from the citing story's `Surface:` line in `epics.md`, and scan for whole-word references outside the symbol's own module and outside tests.
- `feature` — handle the document-surfaced case explicitly ("not applicable, document surface").
- `feature` — handle unreadable `epics.md` and absent surface paths as named, non-silent findings.
- `feature` — add fixtures and unit tests, including a test proving the `risk-tiered-review-depth` case fires live against the real fleet (not only a synthetic fixture).

**Acceptance Criteria:**
- Given the 2026-09-09 pass found eighteen capabilities of one shape — a `done` epic whose named success criterion has never been exercised — and three of marshal's four were visible only by grepping for call sites, when the check joins on `(spec-slug, CAP-N)`, reaches code through the citing story's `Surface:` line in the owning station's `epics.md`, and asks whether any symbol those surfaces define is referenced outside its own module and outside tests, then it names `risk-tiered-review-depth`'s `classify_review_tier` / `resolve_review_cycles` (zero callers outside `core/gate.py` and `tests/unit/test_gate.py`) as a live finding — proven against the real fleet before this story closes, not against a fixture that constructs both sides from one synthetic value.
- A capability whose surfaces are documents rather than modules reports "not applicable, document surface" rather than a false "no callers."
- The reach is a bounded whole-word textual scan and says so in the finding text.
- An unreadable `epics.md` or an absent surface path degrades to a named finding, never to silence.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: full suite green

## Spec Change Log

- 2026-09-10: added the missing `## Verification` -> `**Commands:**` section before dispatch. Its absence makes `core.gate.check_spec_binding` (marshal Story 2.7, MRS-GATE-010) unconditionally refuse dispatch verification for any spec authored this way -- confirmed live against `spec-21-13`'s own dispatch run, and again against `spec-21-14`'s.

## Review Triage Log
