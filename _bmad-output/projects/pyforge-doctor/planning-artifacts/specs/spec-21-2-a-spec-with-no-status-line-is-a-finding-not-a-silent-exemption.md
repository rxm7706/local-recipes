---
title: 'A Spec with no `status:` line is a finding, not a silent exemption'
type: 'feature'
created: '2026-09-10'
status: 'in-progress'
baseline_revision: '0c75d60935d60a30448aee10f62079411ad98348'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `board.py:715` reads `status = str(_frontmatter_from_text(spec_text).get("status",
"")).strip()` and `:716` `continue`s when it is not in `OPEN_SPEC_STATUSES`. A **missing**
`status:` key fails that membership test identically to a declared-terminal one, and
silently exempts the Spec from every finding — **8 fleet-wide, 4 of them doctor's
own**. One of those, `spec-pixi-candidate-currency`, has 5 of 5 declared CAPs
uncovered by any epic or FR while `chain-completeness` reports `ok`.

**Approach:** Separate "no `status:` key present" from "status present and terminal."
A missing key produces a new `spec-status-missing` finding naming the Spec with the
remedy "add a `status:` line, or add the slug to `DEFERRED_SPECS` with the reason."
Every declared-but-terminal status (`shipped`/`archived`/`absorbed`/`superseded`/
`extension-point`) stays exempt exactly as today. No status is guessed or inferred —
treating absence as `draft` would red two effectively-shipped station flagships
(`spec-pyforge-marshal`, `spec-pyforge-mason`) for a bookkeeping omission. The branch
mirrors the Dream-side check that already exists (`chain.py:993`, `Dream {slug!r} has
no status: in frontmatter`).

## Boundaries & Constraints

**Always:**
- Absence of the `status:` key is detected and handled **separately** from a
  declared-but-not-open status — the two must not collapse into the same branch.
- Every declared-but-terminal status (`shipped`, `archived`, `absorbed`,
  `superseded`, `extension-point`) stays exempt exactly as it is today — this story
  changes the missing-key path only.
- The new finding names the Spec and states the remedy: "add a `status:` line, or add
  the slug to `DEFERRED_SPECS` with the reason."
- The branch mirrors the existing Dream-side check at `chain.py:993` in spirit
  (same class of finding: a frontmatter field silently absent rather than
  meaningfully declared).

**Never:**
- Never guess or infer an implied status for a Spec missing `status:` (e.g. never
  treat absence as `draft`) — this would produce false findings against Specs like
  `spec-pyforge-marshal` and `spec-pyforge-mason` for a bookkeeping omission rather
  than a real gap.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Spec with no `status:` key | `_frontmatter_from_text(spec_text).get("status", "")` returns `""` | `spec-status-missing` finding naming the Spec, with the two-option remedy | n/a |
| Spec with a declared terminal status | `status: shipped` (or archived/absorbed/superseded/extension-point) | Stays exempt exactly as today — no finding | n/a |
| Spec with a declared open status | `status: draft/ready/in-progress` | Normal open-Spec handling, unchanged | n/a |
| `spec-pixi-candidate-currency` today | Missing `status:`, 5/5 CAPs uncovered, `chain-completeness` reports `ok` | Now fires `spec-status-missing`; live tree count is measured at ship time (0 after this pass's own Class-B flips) | n/a |
| Fixture with a status-less `SPEC.md` | Planted fixture, no `status:` frontmatter key | Fires `spec-status-missing` | n/a |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/board.py` — a new branch before `:716` separating missing-key from declared-terminal handling.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_board.py` — new fixture/test for a status-less `SPEC.md`.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/data/report-schema.json` — if the check name is enumerated there, add `spec-status-missing`.

## Tasks & Acceptance

**Execution:**
- `feature` — add a branch in `board.py` before `:716` that distinguishes "no `status:` key" from "status present but not open."
- `feature` — emit a `spec-status-missing` finding for the missing-key case, naming the Spec and the two-option remedy.
- `docs`/`feature` — enumerate `spec-status-missing` in `report-schema.json` if check names are enumerated there.
- `feature` — add a fixture carrying a status-less `SPEC.md` and a test proving it fires while today's (post-Class-B-flip) tree reports zero.

**Acceptance Criteria:**
- Given `board.py:715-716`'s membership test against `OPEN_SPEC_STATUSES`, when the absence of the `status:` key is separated from a declared-terminal status, then a `spec-status-missing` finding names the Spec with the remedy "add a `status:` line, or add the slug to `DEFERRED_SPECS` with the reason."
- Every declared-but-terminal status (`shipped`/`archived`/`absorbed`/`superseded`/`extension-point`) stays exempt exactly as today.
- No implied status is guessed for a Spec missing `status:` — absence is never treated as `draft`.
- The branch mirrors the Dream-side check that already exists at `chain.py:993` ("Dream {slug!r} has no status: in frontmatter").
- A fixture carrying a status-less `SPEC.md` fires the new finding, while today's tree — after the Class-B flips of this same pass — reports zero.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: full suite green

## Spec Change Log

- 2026-09-10: added the missing `## Verification` -> `**Commands:**` section before dispatch. Its absence makes `core.gate.check_spec_binding` (marshal Story 2.7, MRS-GATE-010) unconditionally refuse dispatch verification for any spec authored this way -- confirmed live against `spec-21-13`'s own dispatch run, and again against `spec-21-14`'s.

## Review Triage Log
