---
title: "83.15: Dispatch applies ruff's safe fixes before it verifies"
type: 'fix'
created: '2026-10-03'
status: 'done'
followup_review_recommended: false
baseline_revision: '0cb8a62ec7c19485cb0f55b9faf89b3b5302c6f6'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_ruff_format.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 83.9 runs `ruff format` on a story's changed Python files before verification, but not `ruff check --fix`. On 2026-10-03 three Cursor sessions (85.1 twice, 84.1) were refused at verification only on auto-fixable `ruff check` findings (an unused import, an unsorted import block), each costing a hand fix or a session.

**Approach:** Before verification, run `ruff check --fix` (safe fixes only, never `--unsafe-fixes`) on the same story-scoped files, with each package's own ruff config, then `ruff format`, and commit the result with the same journaled commit 83.9 makes. A finding ruff cannot fix safely still fails verification as today.

Ledger key: `83-15-dispatch-applies-ruff-s-safe-fixes-before-it-verifies`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- Story 83.9 (the pre-verification ruff format step). A defect of shipped behaviour, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a story whose changed file has an unused import and an unsorted import block When dispatch verifies it Then `ruff check --fix` removes both before `lint-types` runs, the fix is committed and journaled, and verification passes
- Given a finding ruff cannot fix safely When dispatch verifies Then verification still refuses on it
- Given files outside the story's changed set When the pre-verify fix runs Then they are untouched
- Given the `ruff check --fix` step removed When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Safe fixes only; story-scoped files only; each package's own config.

**Never:** Never pass `--unsafe-fixes`. Never touch a file the story did not change.

</intent-contract>

## Binding

Parent: Story 83.9 (pre-verify ruff format).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-03 (night, later) entry.
Ledger key: `83-15-dispatch-applies-ruff-s-safe-fixes-before-it-verifies`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 at the operator's request.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

### 2026-10-04 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (none)

## Auto Run Result

Status: done

**Summary:** Pre-verify dispatch now runs `ruff check --fix` (safe fixes only) on story-scoped pyforge package paths before `ruff format`, then commits when either step dirties those paths — same scope and journaling as Story 83.9.

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_ruff_format.py` — invoke `ruff check --fix` per package before format; updated commit message.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_ruff_format.py` — call-order assertions, disk-dirty VCS stub, live-ruff mutation oracle test.

**Review:** No findings from review layers (implementation matches intent-contract ACs).

**Follow-up review recommended:** false

**Verification performed:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — 11411 passed, 6 skipped.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — 130 passed, 3 skipped.
- `pixi run --frozen -e pyforge-guild lint-types` — exit 0.
- `python scripts/spec_surface_reconcile.py` — OK after memlog reconcile on `spec-pyforge-core` and `spec-pyforge-marshal`.

**Residual risks:** None identified; unfixable ruff violations still fail at derived `lint-types` as before.
