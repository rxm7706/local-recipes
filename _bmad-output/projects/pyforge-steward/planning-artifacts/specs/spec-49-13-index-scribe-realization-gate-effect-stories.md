---
title: '49.13: Index — scribe realization-gate effect stories'
type: 'docs'
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
- Do not flip ledger key `49-13-index-scribe-realization-gate-effect-stories` off `blocked` (operator confirmation required). The operator flipped it to `done` on 2026-10-10 (below).

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
Ledger status at mint: `blocked`. Flipped `blocked` → `done` 2026-10-10 by the operator's ruling, through the Tier-3 feed and `sprint-ledger-sync --project steward --allow-regression` (one run with the day's three `blocked` → `backlog` flips; this key's move to `done` is not a regression).
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-49-13-index-scribe-realization-gate-effect-stories.md`.

## Epic excerpt

**Type:** index • **Effort:** S • **Deps:** S-49.2; cross-station: scribe's effect epic (ledger `blocked` until it closes) • **FR/AD:** fleet readiness 2026-09-09 § 2.3 C6
**Surface:** this file only (the index row). Scribe's own artifacts are **named, never edited** by steward
**Given** scribe's scheduled compile is `done` and not in effect — the store was last written 2026-08-27 and the "nightly" schedule is a hand-installed crontab line, not a declared, reproducible surface **When** scribe lands the effect story (a declared schedule the estate can see and a recorded run) **Then** this row flips `done`
**And** steward records the placement question only: a scheduled compile that must survive the cutover is a Foundry-side surface, not a workstation crontab

## Outcome — 2026-10-10

**Status:** done. The operator ruled "lets look at each one of these and see if we can get them moving and complete them"
(spec-pyforge-steward memlog, 2026-10-10). The row's condition is met on `main` (`6d5e84cb6b`):

- Scribe Epic 8, "Scribe in effect — the compile runs on a schedule the estate owns", is `done` in scribe's ledger,
  with Stories 8.1–8.6 all `done`.
- The declared schedule is checked in: `src/shared/packages/pyforge-scribe/ops/systemd/pyforge-scribe-nightly-compile.timer`
  and its `.service.tmpl`, fired through `scripts/scribe_nightly_trigger.py` (Story 8.1, merged 2026-09-10 as
  `4134316780`).
- The recorded-run signal is `scribe-graph-freshness-check` (`scripts/scribe_graph_freshness_check.py`), an advisory
  runtime detector that reports a store older than the timer's own period.

The And-clause stands as recorded: the unit is a workstation surface, and a compile that must survive the cutover is a
Foundry-side surface. This row closes nothing on scribe's side; scribe's artifacts are named, never edited.
