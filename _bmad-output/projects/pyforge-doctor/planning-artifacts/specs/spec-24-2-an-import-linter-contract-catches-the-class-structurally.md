---
title: '24.2: An import-linter contract catches the class structurally'
type: 'feature'
created: '2026-09-16'
status: 'in-review'
baseline_revision: '42f4b5e9b53118f59e1c9e64f18164db4eaab77a'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The defect Story 24.1 removes survived because nothing asked whether a station package evaluates that station's CI gate.

**Approach:** A contract forbids any pyforge.<station> module from importing or defining the gate evaluator. A meta-test fails on a planted reintroduction and passes on the moved layout. The docstring names Charter §5/§6 and this Spec.

## Boundaries & Constraints

**Always:**
- Planted pyforge.<station>.coverage_gate shim fails the contract.
- Moved layout passes.
- Docstring names Charter §5/§6 and this Spec.

**Never:**
- Do not leave the rule undocumented as an arbitrary layering check.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| planted shim | temp pyforge.<station>.coverage_gate | contract fails | fail |

</intent-contract>

## Binding

Parent Spec capability: `spec-coverage-gate-independence CAP-3`.
Surface: src/shared/packages/pyforge-marshal/pyproject.toml [tool.importlinter] and/or a fleet-level contract; marshal tests/meta/test_ad3_ad4_import_linter.py or a sibling; a fixture that fires..
Ledger key: `24-2-an-import-linter-contract-catches-the-class-structurally`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-24-2-an-import-linter-contract-catches-the-class-structurally.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).

