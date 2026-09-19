---
title: '52.2: The conformance suite is a PR gate'
type: 'infra'
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

**Problem:** no workflow invokes the `pyforge-core-test` task and the four sole-ownership meta-tests have never run in CI

**Approach:** the job exists and `pr-preflight` depends on it

## Boundaries & Constraints

**Always:**
- the lane is green on `main` at merge, and a fixture branch introducing a second `subprocess.run` implementation under `src/shared/packages/` reds it
- the job runs the pixi task — no hand-enumerated file list

**Never:**
- Do not make the supervisor trust a session's self-report, perform the merge marshal only materialises, add a second gate or verdict owner, move a primary checkout that is not a clean `main`, or re-attribute landed history — the Epic 51/52 HARD boundaries in `epics.md` bind.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the named fixture | the real run/journal/PR named in the Given | the Then holds | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-core CAP-8`.
Surface: `.github/workflows/pyforge-station-tests.yml` (a `core-test` job beside the eight station jobs, same shared-surface triggers, running `pixi run --frozen -e pyforge-core pyforge-core-test`), `pixi.toml` (`pr-preflight` depends on `pyforge-core-test`; `environment.yaml` regenerated), docs that list the lanes.
Ledger key: `52-2-the-conformance-suite-is-a-pr-gate`.
Minted 2026-09-19 from `epics.md` so `marshal factory dispatch` (51.x) or a hand-driven `bmad-build-auto` (52.x) can resolve `spec-52-2-the-conformance-suite-is-a-pr-gate.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- The Then/And of Story 52.2 in `epics.md` hold on the named fixture; the mutation or byte-identical check named there is run, not inferred.
