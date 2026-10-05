---
title: "86.2: local-recipes is genesis-adopted so the seed-adopt oracle goes green"
type: 'fix'
created: '2026-10-03'
status: 'done'
baseline_revision: '835894524e63ee69428972aeb5f28fa00d762edc'
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

**Problem:** The SC-02 slow oracle (seed adopt on this repo) plans 21 actions and stays red: 5 hybrid regions absent (AGENTS.md, CLAUDE.md, .gitignore, README.md, `_bmad-output/PROJECTS.md`), 12 first-claims of files that already exist, and the `{{ slug }}`/loop-home paths Story 70.1 fixes for `seed check`. The operator ruled on 2026-09-28 that this repo stays the oracle and is never exempted by name; on 2026-10-03 the operator ruled to bootstrap-adopt it.

**Approach:** After Story 70.1, make seed adopt render `{{ slug }}` and honour `required_in: loop-home` through 70.1's renderer, run the bootstrap `marshal seed adopt --apply` on local-recipes (managed-region markers plus `.marshal/seed-state.yml`), and put the oracle in a CI lane (NFR-M2).

Ledger key: `86-2-local-recipes-is-genesis-adopted-so-the-seed-adopt-oracle-goes-green`.
Type / Effort / Deps: fix / M / S-70.1.

### Living CAP citations

- The capabilities that shipped each behaviour (see each row); a `fix`, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given Story 70.1 has landed When the oracle runs on this repo Then it plans zero actions
- Given the adopt When AGENTS.md and CLAUDE.md are read Then the inserted managed regions leave the instruction-surface parity and governance-currency checks green
- Given the oracle When CI runs Then it runs in a named lane
- Given this story lands When its deferred-work rows are read Then each of `DW-FU-12-2` is closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` it fixed

## Boundaries & Constraints

**Always:** Review every inserted region against AGENTS.md § Instruction files before committing. Fix each defect where the shipped behaviour lives and pin it with a test that fails without the fix.

**Never:** Never widen the oracle's exclusion set (K-02). Never exempt this repo by name.

</intent-contract>

## Deferred-work rows this story closes (operator rulings 2026-10-03, deferral burn-down Phase 3)

- `DW-FU-12-2` — After Story 70.1, seed adopt renders {{ slug }} and honours required_in: loop-home through 70.1's renderer, the bootstrap `marshal seed adopt --apply` lands on local-recipes (markers in AGENTS.md, CLAUDE.md, .gitignore, README.md, PROJECTS.md plus .marshal/seed-state.yml), and the oracle joins a CI lane.

## Binding

Parent: The capabilities that shipped each behaviour (see each row)
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-03 (Phase 3) entry.
Ledger key: `86-2-local-recipes-is-genesis-adopted-so-the-seed-adopt-oracle-goes-green`.
Ledger status at mint: `backlog`.
Deps: S-70.1.
Minted 2026-10-03 from the operator's Phase 3 rulings (rulings page `rulings` collection; "group them by module, as Phase 2 did").

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- 2026-10-05: Implementation verified locally (`pyforge-marshal-test`, `pyforge-deps-test`, `lint-types`, `pyforge-marshal-test-local-recipes-seed-oracle`, `spec_surface_reconcile.py`). Genesis bootstrap landed; empty-plan oracle green.
