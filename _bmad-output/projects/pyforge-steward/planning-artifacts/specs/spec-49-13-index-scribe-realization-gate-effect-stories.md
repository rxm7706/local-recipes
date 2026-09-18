---
title: '49.13: Index — scribe realization-gate effect stories'
type: 'docs'
created: '2026-09-18'
status: 'blocked'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** scribe's scheduled compile is `done` and not in effect — the store was last written 2026-08-27 and the "nightly" schedule is a hand-installed crontab line, not a declared, reproducible surface **When** scribe lands the effect story (a declared schedule the estate can see and a recorded run) **Then** this row flips `done`

**Approach:** this row flips `done`

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-49-13-index-scribe-realization-gate-effect-stories.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.
- Do not flip ledger key `49-13-index-scribe-realization-gate-effect-stories` off `blocked` (operator confirmation required).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| scribe's scheduled compile is `done` and not in effect — the store was last written 2026-08-27 and the "nightly" schedule is a hand-installed crontab line, not… | scribe lands the effect story (a declared schedule the estate can see and a recorded run) **Then** this row flips `done` | this row flips `done` | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | steward records the placement question only: a scheduled compile that must survive the cutover is a Foundry-side surface, not a workstation crontab | n/a |

</intent-contract>

## Binding

Parent Spec capability: `named on the story in epics.md`.
Surface: this file only (the index row). Scribe's own artifacts are **named, never edited** by steward
Ledger key: `49-13-index-scribe-realization-gate-effect-stories`.
Ledger status at mint (unchanged): `blocked`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-49-13-index-scribe-realization-gate-effect-stories.md`.

## Epic excerpt

**Type:** index • **Effort:** S • **Deps:** S-49.2; cross-station: scribe's effect epic (ledger `blocked` until it closes) • **FR/AD:** fleet readiness 2026-09-09 § 2.3 C6
**Surface:** this file only (the index row). Scribe's own artifacts are **named, never edited** by steward
**Given** scribe's scheduled compile is `done` and not in effect — the store was last written 2026-08-27 and the "nightly" schedule is a hand-installed crontab line, not a declared, reproducible surface **When** scribe lands the effect story (a declared schedule the estate can see and a recorded run) **Then** this row flips `done`
**And** steward records the placement question only: a scheduled compile that must survive the cutover is a Foundry-side surface, not a workstation crontab

