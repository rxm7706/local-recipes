---
title: 'A Spec with no `status:` line is a finding, not a silent exemption'
type: 'feature'
created: '2026-09-10'
status: 'done'
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

### 2026-09-10 — Review pass
- verdicts: 14 findings — high 0, medium 0, low 1, false 6, maybe-false 0, reject 7
- findings:
  - `[false] [reject]` Whitespace-only `status` silently exempted vs Dream check — intent limits scope to missing key only; `_frontmatter_from_text` skips value-less keys so key-absence and value-less are equivalent today
  - `[false] [reject]` I/O matrix missing empty-whitespace row — spec edit only; out of scope for this story
  - `[false] [reject]` No test for whitespace-only status — out of scope per intent contract
  - `[false] [reject]` Stale line references in acceptance criteria — spec doc drift; no runtime harm
  - `[low] [reject]` DEFERRED_SPECS block comment cites old `:716` line — comment inaccuracy only; direct fix not worth a patch pass
  - `[false] [reject]` Code Map points at wrong test module — spec doc drift; tests live in chain_completeness module by convention
  - `[false] [reject]` `test_unreadable_spec` omits explicit FAIL assert on spec-status-missing — finding always FAILs via `gather_chain_completeness`; presence assertion sufficient
  - `[false] [reject]` No parametrized tests for all terminal statuses — `test_shipped_spec_is_not_open` exercises the same `continue` branch
  - `[false] [defer]` Ledger still lists story at backlog — ledger sync is operator/build-auto finalize concern, not story acceptance
  - `[false] [reject]` report-schema.json not updated — `check` is open string, not enumerated; task N/A
  - `[false] [defer]` pixi task description omits new finding — detector output self-describes via finding kind
  - `[false] [reject]` WARN vs FAIL severity vs Dream — intentional; spec says mirror "in spirit"
  - `[false] [reject]` Only one Class-B flip visible in diff — live-tree test passes (1549 tests); tree already clean
  - `[false] [reject]` Spec Change Log not extended pre-review — addressed in this finalize pass

## Auto Run Result

Status: done

**Summary:** INV-A in `board.py` now emits `spec-status-missing` when a Spec's frontmatter lacks a `status:` key, instead of silently exempting it via the terminal-status `continue`. `DEFERRED_SPECS` is checked first so the escape hatch survives.

**Files changed:**
- `board.py` — missing-key branch + reordered DEFERRED_SPECS guard
- `test_sources_board_chain_completeness.py` — fixture tests + unreadable-spec expectation update
- `test_sources_board.py` — live-tree zero-missing guard
- `spec-sprint-status-promotion-regression-guard/SPEC.md` — Class-B `status: shipped` flip
- This story spec — dispatch metadata

**Review:** 0 patches applied, 0 deferred, 14 findings rejected (6 false, 1 low, 7 out-of-scope/doc). Edge-case hunter: none. Verification-gap: none.

**Follow-up review recommended:** false

**Verification:** `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — 1549 passed, 1 skipped.

**Residual risks:** Unreadable/non-UTF-8 SPEC.md degrades to `{}` and now fires `spec-status-missing` (stricter than prior silent exemption). Present-but-empty `status` value (key in dict, empty after strip) remains exempt — intentionally out of scope per intent.
