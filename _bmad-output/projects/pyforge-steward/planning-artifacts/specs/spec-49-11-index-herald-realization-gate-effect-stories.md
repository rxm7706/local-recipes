---
title: '49.11: Index — herald realization-gate effect stories'
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

**Problem:** three herald capabilities are `done` and not in effect — the live backend (`herald-live-demo.yml` is `disabled_manually` with 100 of 100 runs failed, last run 2026-08-24, and its store is `runner.temp`), the deck-QA gate (called by nothing), and the pptx pipeline (has never rendered a station deck) **When** herald lands their effect stories, or re-scopes them as a *hosting* decision deferred unti…

**Approach:** this row flips `done`

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-49-11-index-herald-realization-gate-effect-stories.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.
- Do not flip ledger key `49-11-index-herald-realization-gate-effect-stories` off `blocked` (operator confirmation required).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| three herald capabilities are `done` and not in effect — the live backend (`herald-live-demo.yml` is `disabled_manually` with 100 of 100 runs failed, last run… | herald lands their effect stories, or re-scopes them as a *hosting* decision deferred until the Foundry gives Herald a… | this row flips `done` | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | steward records only the dependency: the perimeter is a Foundry capability, so herald's hosting branch is gated on steward's chart work, not on this row | n/a |

</intent-contract>

## Binding

Parent Spec capability: `named on the story in epics.md`.
Surface: this file only (the index row). Herald's own artifacts are **named, never edited** by steward
Ledger key: `49-11-index-herald-realization-gate-effect-stories`.
Ledger status at mint (unchanged): `blocked`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-49-11-index-herald-realization-gate-effect-stories.md`.

## Epic excerpt

**Type:** index • **Effort:** S • **Deps:** S-49.2; cross-station: herald's effect epic (ledger `blocked` until it closes) • **FR/AD:** fleet readiness 2026-09-09 § 2.3 C6 / C11
**Surface:** this file only (the index row). Herald's own artifacts are **named, never edited** by steward
**Given** three herald capabilities are `done` and not in effect — the live backend (`herald-live-demo.yml` is `disabled_manually` with 100 of 100 runs failed, last run 2026-08-24, and its store is `runner.temp`), the deck-QA gate (called by nothing), and the pptx pipeline (has never rendered a station deck) **When** herald lands their effect stories, or re-scopes them as a *hosting* decision deferred until the Foundry gives Herald a perimeter (steward's `deploy perimeter` cannot target an arbitrary ASGI callable today, `deploy.py:484`) **Then** this row flips `done`
**And** steward records only the dependency: the perimeter is a Foundry capability, so herald's hosting branch is gated on steward's chart work, not on this row

