---
title: '23.4: Empty the intake inbox per its own README'
type: 'fix'
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

**Problem:** Intake dumps have no per-file disposition and several already have a specified or pitched Dream.

**Approach:** Route each folder per docs/intake/README.md and gists/INDEX.md. Nothing a specified/realized/archived Dream already absorbed remains in intake. No gist dump gains Dream YAML.

## Boundaries & Constraints

**Always:**
- Intake holds nothing a specified/realized/archived Dream already absorbed.

**Never:**
- Do not add Dream YAML to a gist dump.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| absorbed dump | folder already owned by a specified Dream | gone from intake | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-docs-shelf-alignment CAP-4`.
Surface: docs/intake/, archive/docs/intake/, owning Dream companions..
Ledger key: `23-4-empty-the-intake-inbox-per-its-own-readme`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-23-4-empty-the-intake-inbox-per-its-own-readme.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).

