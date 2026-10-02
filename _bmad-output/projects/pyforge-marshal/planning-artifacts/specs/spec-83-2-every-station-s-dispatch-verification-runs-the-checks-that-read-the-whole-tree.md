---
title: '83.2: Every station's dispatch verification runs the checks that read the whole tree'
type: 'fix'
created: '2026-10-02'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `dispatch_verify._verify_commands_with_surface_guard` folds the derived commands (the surface guard, `lint-types`) into every station's dispatch verification, but neither pyforge-core's suite nor the deferred-work check is among them. On 2026-10-02 steward 83.2 landed uncited `verified:` lines and turned doctor's live-ledger test red on `main`, and marshal 82.4's new exception root failed pyforge-core's CAP-5 meta-test in CI; the station verification passed both.

**Approach:** Append `pixi run --frozen -e pyforge-core pyforge-core-test` and `pixi run --frozen -e pyforge-guild deferred-work-check` in the same place `lint-types` was folded in, after the same dedupe rule, so every station's verification runs them. Both are seconds-long.

Ledger key: `83-2-every-station-s-dispatch-verification-runs-the-checks-that-read-the-whole-tree`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- Story 53.1 (CAP-261a, the derived verification guard). A defect of shipped behaviour, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a story whose change fails pyforge-core's suite When its dispatch verifies Then verification fails and the landing is refused
- Given a story whose change adds an uncited post-cutoff verified: line When its dispatch verifies Then verification fails
- Given a story that breaks neither When its dispatch verifies Then it lands as today
- Given either command removed from the guard When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Fix the defect where the shipped behaviour lives, and pin it with a test that fails without the fix.

**Never:** Do not edit any station's `verify_commands`. Do not make a WARN-only detector finding fail verification.

</intent-contract>

## Binding

Parent: Story 53.1 (CAP-261a, the derived verification guard).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-02 (night) entry.
Ledger key: `83-2-every-station-s-dispatch-verification-runs-the-checks-that-read-the-whole-tree`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-02 at the operator's request to chain the defects found landing Phase 2.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- No review has run yet.
