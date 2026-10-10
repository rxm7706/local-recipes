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

## Host decision — 2026-10-10

**Status:** still `blocked`; this row flips `done` when herald Epic 19 closes.

The operator chose the local-host path for herald Story 19.2 (the one open story of herald Epic 19), verbatim "go with
option 1, local host": "Mint a small steward fix that adds `--asgi-application` to `deploy perimeter`. Then re-scope
herald 19.2 so its host and store are this machine's local stack: `pyforge-foundry-full-stack` with PostgreSQL 17. No
public endpoint, nothing outside the repo. Herald Epic 19 then closes, and 49.11 flips to done." (spec-pyforge-steward
memlog, 2026-10-10.)

- Steward's part is Story 86.1 (`86-1-deploy-perimeter-renders-the-asgi-application-it-is-given`, Epic 86). It adds
  `steward deploy perimeter --asgi-application <module:attr>` and closes herald's DW-13-6-1. The hardcoded
  `myproject.asgi:application` this row's Given cites as `deploy.py:484` sits at `deploy.py:539` on `6d5e84cb6b`.
- Herald's part, the re-scope of Story 19.2, is herald's chain. Steward names it and never edits it.
- The And-clause's dependency changes shape: herald's hosting branch now waits on Story 86.1 and herald's own 19.2, not
  on a Foundry perimeter or steward's chart work.
