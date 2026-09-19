---
title: '52.1: The six accumulated violations are cleared'
type: 'fix'
created: '2026-09-19'
status: 'ready'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `test_exception_root_sole_ownership` fails for the three exception files and `test_no_second_subprocess_implementation` for the three subprocess files (2026-09-19)

**Approach:** each is brought under the extracted primitive

## Boundaries & Constraints

**Always:**
- `pixi run --frozen -e pyforge-core pyforge-core-test` → 0 failed, and `pyforge-marshal-test`, `pyforge-warden-test` and the testing-kit suite stay green
- the CAP-5 widening test passes for every re-parented class

**Never:**
- Do not make the supervisor trust a session's self-report, perform the merge marshal only materialises, add a second gate or verdict owner, move a primary checkout that is not a clean `main`, or re-attribute landed history — the Epic 51/52 HARD boundaries in `epics.md` bind.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the named fixture | the real run/journal/PR named in the Given | the Then holds | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-core CAP-9`.
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/oidc_pkce.py`, `.../cli/watch.py`, `src/shared/packages/pyforge-warden/src/pyforge/warden/tea_advisory.py` (exception root — re-parent to the core root, no `except` clause widens); `.../marshal/cli/login.py`, `.../marshal/cli/refresh.py`, `src/shared/packages/pyforge-testing-kit/src/pyforge/testing_kit/branch_diff_guard.py` (route through the core subprocess guard); tests.
Ledger key: `52-1-the-six-accumulated-violations-are-cleared`.
Minted 2026-09-19 from `epics.md` so `marshal factory dispatch` (51.x) or a hand-driven `bmad-build-auto` (52.x) can resolve `spec-52-1-the-six-accumulated-violations-are-cleared.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- The Then/And of Story 52.1 in `epics.md` hold on the named fixture; the mutation or byte-identical check named there is run, not inferred.
