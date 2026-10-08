---
title: '62.2: Add, switch, and archive without a rewrite'
type: 'feature'
created: '2026-09-16'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - src/shared/packages/pyforge-steward/src/pyforge/steward/catalog.py
  - src/shared/packages/pyforge-steward/tests/unit/test_catalog.py
deferred: []
declared_low_risk: false
baseline_revision: 'ca4cc7f7d1'
---

<intent-contract>

## Intent

**Problem:** A new source or a dead source would fork the product.

**Approach:** Add is a new row starting off; archive keeps the id and forbids reuse. on / off / archived is a config flip.

## Boundaries & Constraints

**Always:**
- Add starts off.
- Archive keeps the id and forbids reuse.
- State is a config flip.

**Never:**
- Do not invent weights.
- Do not rewrite the product to add or retire a source.
- Do not flip any Epic 44 blocked key.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| add measure | new id | row starts off | n/a |
| archive | existing id | id retained; reuse refused | refuse |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/measures/measures.yaml` — git-tracked config (edit store); eight first-cut rows, all `on`; `archived_ids` tombstone list for ids removed from `measures`.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/measures.py` — `load_config`, `validate_add_rules` (new ids off), `refuse_reuse`, `MeasureDuty` (`check`|`list`).
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` — `measure` duty wired like `catalog` (Story 60.1 precedent); duty count 26.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-build-league-scorecard/measure-catalog.md` — companion prose; points at `measures.yaml` for authoritative state; heading no longer claims “all on”.
- `src/shared/packages/pyforge-steward/tests/unit/test_measures.py` — matrix + CLI smoke tests.

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-steward/measures/measures.yaml` — declare the eight first-cut measures with dimension, source, notes, and `state: on`.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/measures.py` — load and validate config; enforce add/archive rules without rewriting consumers (Story 62.3).
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` — expose `steward measure check|list [--json] [--measures-dir DIR]`.
- `spec-build-league-scorecard/measure-catalog.md` — document that state flips live in config.
- `tests/unit/test_measures.py` — cover I/O matrix rows and committed config load.

**Acceptance Criteria:**
- Given the tracked `measures.yaml`, when `steward measure check` runs, then validation passes for the first-cut catalog.
- Given a measure id not in the first cut, when its `state` is not `off`, then `steward measure check` reports a policy finding.
- Given an id listed in `archived_ids` or on a row with `state: archived`, when `refuse_reuse` is consulted for that id, then reuse is refused.
- Given `steward measure list`, when invoked on the default config, then all eight ids appear with dimension, source, and state.

## Spec Change Log

### 2026-10-08 — Review pass 1
- Trigger: planning completion for Story 62.2 implementation.
- Amended: Code Map, Tasks & Acceptance, Verification, baseline revision.
- Avoided: implementing consumer refuse paths (Story 62.3 scope).

## Review Triage Log

### 2026-10-08 — Review pass
- verdicts: 4 findings — high 0, medium 0, low 0, false 4, maybe-false 0
- findings:
  - `[false]` `[reject]` blind-hunter: no sync from config back into the markdown table State column — refuted: companion doc names yaml as authoritative; regenerating markdown is optional and Story 62.3+ consumers read yaml.
  - `[false]` `[reject]` blind-hunter: guards outcome category still blocked on the archived Dream — refuted: 62.2 surface is config only; guards update is a later consumer story.
  - `[false]` `[reject]` intent-alignment: archive scenario lacks CLI verb — refuted: archive is a config flip (`state: archived`) plus optional `archived_ids` tombstone; epics do not require a dedicated archive subcommand in v1.
  - `[false]` `[reject]` verification-gap: matrix “add measure” row not tested via CLI add — refuted: `validate_add_rules` and `load_config` unit tests cover add-off and reuse refusal; no add verb is in scope.

## Binding

Parent Spec capability: `spec-build-league-scorecard CAP-2`.
Surface: a config the catalog and later consumers read..
Ledger key: `62-2-add-switch-and-archive-without-a-rewrite`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-62-2-add-switch-and-archive-without-a-rewrite.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).
- `python scripts/spec_surface_reconcile.py` — expected: exit 0 after memlog surface reconcile on owning/co-governor Specs.

## Auto Run Result

**Summary of implemented change:** Shipped git-tracked `measures/measures.yaml` plus `steward measure check|list` so Build League measure state is a config flip (`on` / `off` / `archived`) with add-starting-off and archived-id reuse refusal enforced in `measures.py`.

**Files changed:**
- `src/shared/packages/pyforge-steward/measures/measures.yaml` — eight first-cut measures declared.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/measures.py` — config loader, policy validation, duty.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` — `measure` duty registration.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-build-league-scorecard/measure-catalog.md` — authoritative config pointer; heading fix.
- `src/shared/packages/pyforge-steward/tests/unit/test_measures.py` — matrix coverage.
- `tests/unit/test_cli.py`, `tests/unit/test_restore_duty.py` — duty count 26.

**Review findings breakdown:** Patched 0; deferred 0; rejected 4 (see Review Triage Log).

**Follow-up review recommendation:** `false`.

**Verification performed:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — 2066 passed, 5 skipped.
- `python scripts/spec_surface_reconcile.py` — exit 0 after memlog reconcile entries.

**Residual risks:** Story 62.3 still owes consumer refuse paths; markdown table State column may drift from yaml until a render verb exists or operators edit both deliberately.
