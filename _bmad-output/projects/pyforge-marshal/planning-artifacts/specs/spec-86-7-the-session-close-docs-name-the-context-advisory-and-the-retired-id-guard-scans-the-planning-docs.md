---
title: "86.7: The session-close docs name the context advisory and the retired-id guard scans the planning docs"
type: 'fix'
created: '2026-10-03'
status: 'done'
baseline_revision: '9867aefc36fcc49864d6175e9aa4cd1409919794'
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

**Problem:** Two documentation gaps the operator ruled to fix: nothing documents running `marshal context advisory` at session close beside `scribe capture`; and the retired-BMAD-skill-id guard does not scan `architecture-bmad-infra.md` or `development-guide.md`, which carry bare retired ids (for example the `bmad-checkpoint-preview` rename-table row).

**Approach:** Name `marshal context advisory` beside `scribe capture` in AGENTS.md's session-close line and the pyforge-marshal station skill; add the two planning docs to SCAN_GLOB_FLOORS in `test_no_retired_bmad_skill_ids.py` and gloss their bare retired ids with an allow marker.

Ledger key: `86-7-the-session-close-docs-name-the-context-advisory-and-the-retired-id-guard-scans-the-planning-docs`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- The capabilities that shipped each behaviour (see each row); a `fix`, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given AGENTS.md When the scribe parity and governance-currency checks run Then they stay green
- Given the guard When it runs Then it scans both planning docs and passes
- Given this story lands When its deferred-work rows are read Then each of `DW-marshal-46-6`, `DW-FU-30-1-2` is closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` it fixed

## Boundaries & Constraints

**Always:** The guard lives under `.claude/skills/conda-forge-expert/`: invoke the conda-forge-expert skill first, and land its change as one `retro(cfe):` commit with a CHANGELOG entry and semver bump (AGENTS.md § Where things are). Fix each defect where the shipped behaviour lives and pin it with a test that fails without the fix.

**Never:** Never restate the session-close ritual in more than one place (point, don't copy).

</intent-contract>

## Deferred-work rows this story closes (operator rulings 2026-10-03, deferral burn-down Phase 3)

- `DW-marshal-46-6` — Name `marshal context advisory` beside `scribe capture` in AGENTS.md's session-close line (one line) and in the pyforge-marshal station skill; keep the scribe parity and governance-currency checks green.
- `DW-FU-30-1-2` — Add the two planning docs to SCAN_GLOB_FLOORS in test_no_retired_bmad_skill_ids.py and gloss the bare bmad-checkpoint-preview rename-table row (architecture-bmad-infra.md:577) with an allow marker.

## Binding

Parent: The capabilities that shipped each behaviour (see each row)
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-03 (Phase 3) entry.
Ledger key: `86-7-the-session-close-docs-name-the-context-advisory-and-the-retired-id-guard-scans-the-planning-docs`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 from the operator's Phase 3 rulings (rulings page `rulings` collection; "group them by module, as Phase 2 did").

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- 2026-10-05 build-auto pass: AC satisfied — session-close ritual names `marshal context advisory` beside `scribe capture`; guard scans both planning docs; DW-marshal-46-6 and DW-FU-30-1-2 closed in deferred-work-ledger with resolution and verified lines.

## Auto Run Result

Status: done
Verification: `pyforge-marshal-test` (after retro CFE commit), `pyforge-deps-test`, `lint-types`, `test_no_retired_bmad_skill_ids.py`, `test_instruction_surface_parity` session-close subset, `scripts/spec_surface_reconcile.py` — all green.
Surface reconcile memlogs: spec-pyforge-marshal, spec-pyforge-scribe, spec-conda-forge-expert-rebuild (paths named in each entry).
