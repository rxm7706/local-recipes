---
title: '53.3: One tracked track.json per run'
type: 'feature'
created: '2026-09-18'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** a run emits split gitignored evidence today **When** this story lands **Then** one structured Track record lists Guards, Gates, enumerated fields, and the stated retention

**Approach:** one structured Track record lists Guards, Gates, enumerated fields, and the stated retention

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-53-3-one-tracked-track-json-per-run.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| a run emits split gitignored evidence today **When** this story lands **Then** one structured Track record lists Guards, Gates, enumerated fields, and the stat… | this story lands | one structured Track record lists Guards, Gates, enumerated fields, and the stated retention | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | Guards/Gates are readable from the record, not inferred from policy TOML | n/a |

</intent-contract>

## Binding

Parent Spec capability: `named on the story in epics.md`.
Surface: one tracked `track.json` per bmad-loop / `marshal factory spin` run;
Ledger key: `53-3-one-tracked-track-json-per-run`.
Ledger status at mint (unchanged): `done`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-53-3-one-tracked-track-json-per-run.md`.

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** 53.1 • **FR/AD:** spec-intelligence-hub
CAP-3 (B8)
**Note:** Relay — marshal supplies Track field enumeration. Do not implement
marshal code in this steward story unless a one-line pointer is required.
**Surface:** one tracked `track.json` per bmad-loop / `marshal factory spin` run;
retention: Track indefinite, raw payload 90 days
**Given** a run emits split gitignored evidence today **When** this story lands
**Then** one structured Track record lists Guards, Gates, enumerated fields,
and the stated retention
**And** Guards/Gates are readable from the record, not inferred from policy TOML
**Status:** done

