---
title: "86.5: The chain tooling sheds its retired and noisy paths"
type: 'fix'
created: '2026-10-03'
status: 'in-progress'
baseline_revision: 33a7af0cb5e1f58540ba1f14385991ee74582cdf
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

**Problem:** Three chain-tooling cleanups the operator ruled to fix: code-linkage verify counts prose words as missing cites (marshal: 42 of 87); the older `marshal chain regenerate` only records phases and `--apply` rewrites the ledger with the statuses it read, while `marshal planning chain-regenerate` supersedes it; and `scripts/fleet_scan.py`'s retired `_generate()` and its only readers are dead code.

**Approach:** Count only cites that name a story spec or Spec folder and name each missing one (non-blocking); retire `marshal chain regenerate` (keep the shared core/chain_regen functions and MRS-CHAIN codes); delete `_generate()` and its only-caller readers with their tests, with the spec-surface reconcile for the governed file.

Ledger key: `86-5-the-chain-tooling-sheds-its-retired-and-noisy-paths`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- The capabilities that shipped each behaviour (see each row); a `fix`, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given the live tree When code-linkage verify runs Then its missing count names only real specs/folders and it stays complete
- Given `marshal chain regenerate` When invoked Then it no longer exists, and `planning chain-regenerate` still works
- Given scripts/fleet_scan.py When imported by doctor and promote_sprint_status Then everything they use still exists
- Given this story lands When its deferred-work rows are read Then each of `DW-FU-21-2`, `DW-FU-21-2-2`, `DW-marshal-75-1-2` is closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` it fixed

## Boundaries & Constraints

**Always:** Grep every caller before deleting. Fix each defect where the shipped behaviour lives and pin it with a test that fails without the fix.

**Never:** Never delete a function a live caller uses.

</intent-contract>

## Deferred-work rows this story closes (operator rulings 2026-10-03, deferral burn-down Phase 3)

- `DW-FU-21-2` — verify_code_linkage counts only cites that name a story spec or a Spec folder, names each missing one in its detail, and stays non-blocking (status complete).
- `DW-FU-21-2-2` — Retire `marshal chain regenerate` (cli/chain.py and its parser registration and tests), keeping the shared core/chain_regen functions and MRS-CHAIN codes that planning chain-regenerate reuses.
- `DW-marshal-75-1-2` — Delete _generate() and its only-caller readers (scan_dreams, scan_specs, build_archived, scan_guild, scan_backlog) plus their tests from scripts/fleet_scan.py, with the spec-surface reconcile for that governed file.

## Binding

Parent: The capabilities that shipped each behaviour (see each row)
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-03 (Phase 3) entry.
Ledger key: `86-5-the-chain-tooling-sheds-its-retired-and-noisy-paths`.
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
