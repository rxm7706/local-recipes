---
title: '23.8: One command, idempotent, reported'
type: 'feature'
created: '2026-09-16'
status: 'ready'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Every stage exists as its own verb and an agent runs them from memory.

**Approach:** herald deck sync-all runs enumerate → pull moved etags → refresh → derive → push → prove → publish for every registered deck or one --slug. Per-deck report includes overwrote-local. Two consecutive runs: second is unchanged with zero writes. --dry-run prints without writing.

## Boundaries & Constraints

**Always:**
- Second consecutive run reports every deck unchanged.
- --dry-run writes nothing.

**Never:**
- Do not re-implement kernel verbs; call them.
- Do not treat facts.yaml as pullable.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| second run | no Design etag move | all unchanged; zero writes | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-design-sync-loop CAP-8 CAP-3`.
Surface: herald/cli.py deck sync-all --slug --dry-run; pixi deck-sync-all; run report; presentation-deck.md runbook..
Ledger key: `23-6-one-command-idempotent-reported`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-23-6-one-command-idempotent-reported.md`.
