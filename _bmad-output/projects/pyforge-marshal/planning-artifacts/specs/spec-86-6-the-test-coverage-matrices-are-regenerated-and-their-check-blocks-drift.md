---
title: "86.6: The test-coverage matrices are regenerated and their check blocks drift"
type: 'fix'
created: '2026-10-03'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** CAP-5's Story Coverage Matrices are stale on all eight stations (`bmad_tea_playwright.py --all --check` exits 1 everywhere) and the check runs only on opt-in from the local-recipes env.

**Approach:** Regenerate all eight `test-architecture.md` matrices with tea-playwright-all, move the tea-playwright tasks to pyforge-guild, and register tea-playwright-check as a blocking repo-scope detector in detectors-ci.

Ledger key: `86-6-the-test-coverage-matrices-are-regenerated-and-their-check-blocks-drift`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- The capabilities that shipped each behaviour (see each row); a `fix`, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given the regenerated matrices When the check runs Then it exits 0 on all eight stations
- Given a new story without a matrix row When detectors-ci runs Then it reds
- Given pixi.toml When the guild env runs the tasks Then they resolve; environment.yaml regenerated in the same change
- Given this story lands When its deferred-work rows are read Then each of `DW-FU-19-4` is closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` it fixed

## Boundaries & Constraints

**Always:** Regenerate before wiring, so main never reds. Fix each defect where the shipped behaviour lives and pin it with a test that fails without the fix.

**Never:** Never hand-edit a generated matrix.

</intent-contract>

## Deferred-work rows this story closes (operator rulings 2026-10-03, deferral burn-down Phase 3)

- `DW-FU-19-4` — Regenerate all eight test-architecture.md files with tea-playwright-all, move the tea-playwright tasks from the local-recipes env to pyforge-guild, and register tea-playwright-check as a blocking repo-scope detector in detectors-ci.

## Binding

Parent: The capabilities that shipped each behaviour (see each row)
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-03 (Phase 3) entry.
Ledger key: `86-6-the-test-coverage-matrices-are-regenerated-and-their-check-blocks-drift`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 from the operator's Phase 3 rulings (rulings page `rulings` collection; "group them by module, as Phase 2 did").

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- No review has run yet.
