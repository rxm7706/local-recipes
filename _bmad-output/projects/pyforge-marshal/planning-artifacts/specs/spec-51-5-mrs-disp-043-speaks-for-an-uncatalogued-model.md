---
title: '51.5: MRS-DISP-043 speaks for an uncatalogued model'
type: 'fix'
created: '2026-09-19'
status: 'in-progress'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
baseline_revision: '66463b49860151f0a7ff4d0756cf679be95fe3a0'
---

<intent-contract>

## Intent

**Problem:** the guard's condition (`model_provider is not None and model_provider != resolved_provider`) only fires when the model IS found under some OTHER provider, and `provider_declaring_model` returns `None` both for a foreign id and — by documented design — for `sonnet` / `opus` on claude

**Approach:** the predicate distinguishes "uncatalogued and not the chosen harness's own id" from "the harness's own default"

## Boundaries & Constraints

**Always:**
- a fixture tier map naming an id no provider declares raises MRS-DISP-043 before launch, `sonnet` on claude is byte-identical (no finding), and the cross-provider case is unchanged
- removing the uncatalogued branch silences the fixture (mutation test); no second gate

**Never:**
- Do not make the supervisor trust a session's self-report, perform the merge marshal only materialises, add a second gate or verdict owner, move a primary checkout that is not a clean `main`, or re-attribute landed history — the Epic 51/52 HARD boundaries in `epics.md` bind.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the named fixture | the real run/journal/PR named in the Given | the Then holds | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-253`.
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` (the guard at the `provider_declaring_model` / `resolved_provider` comparison), `.../core/model_cost.py::provider_declaring_model` (or a sibling predicate that knows the harness's own default/alias set), `.../core/findings.py` / `.../core/verdict.py` only if the finding text changes, tests.
Ledger key: `51-5-mrs-disp-043-speaks-for-an-uncatalogued-model`.
Minted 2026-09-19 from `epics.md` so `marshal factory dispatch` (51.x) or a hand-driven `bmad-build-auto` (52.x) can resolve `spec-51-5-mrs-disp-043-speaks-for-an-uncatalogued-model.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- The Then/And of Story 51.5 in `epics.md` hold on the named fixture; the mutation or byte-identical check named there is run, not inferred.
