---
title: '49.9: Index — marshal realization-gate effect stories'
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

**Problem:** four marshal capabilities are `done` and not in effect — `adaptive-model-tiering` (fed on 2 of 8 stations; the floor-raise applies only on spin), `risk-tiered-review-depth` (zero callers outside `tests/unit/test_gate.py`; `core/gate.py:724,:768`), `marshal-parallel-dispatch-fanout` (`max_parallel = 1` everywhere, `cli/dispatch.py:902`; no live wave has run), and the two Epic-20 watchdogs plus Sto…

**Approach:** this row flips `done` and `capability-effect-check` stops reporting them

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-49-9-index-marshal-realization-gate-effect-stories.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| four marshal capabilities are `done` and not in effect — `adaptive-model-tiering` (fed on 2 of 8 stations; the floor-raise applies only on spin), `risk-tiered-… | marshal's Epic 33 lands their effect stories (the `bmad-correct-course` already scheduled there also carries token-econ… | this row flips `done` and `capability-effect-check` stops reporting them | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | steward's only action is this row plus the citation — the work, the surfaces and the retro are marshal's | n/a |

</intent-contract>

## Binding

Parent Spec capability: `named on the story in epics.md`.
Surface: this file only (the index row). Marshal's own `epics.md` / Specs are **named, never edited** by steward
Ledger key: `49-9-index-marshal-realization-gate-effect-stories`.
Ledger status at mint (unchanged): `done`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-49-9-index-marshal-realization-gate-effect-stories.md`.

## Epic excerpt

**Type:** index • **Effort:** S • **Deps:** S-49.2; cross-station: marshal Epic 33 (ledger `blocked` until that epic closes — never a foreign-station `Deps:` token) • **FR/AD:** fleet readiness 2026-09-09 § 2.3 C6
**Surface:** this file only (the index row). Marshal's own `epics.md` / Specs are **named, never edited** by steward
**Given** four marshal capabilities are `done` and not in effect — `adaptive-model-tiering` (fed on 2 of 8 stations; the floor-raise applies only on spin), `risk-tiered-review-depth` (zero callers outside `tests/unit/test_gate.py`; `core/gate.py:724,:768`), `marshal-parallel-dispatch-fanout` (`max_parallel = 1` everywhere, `cli/dispatch.py:902`; no live wave has run), and the two Epic-20 watchdogs plus Story 3.12's floor-raise, which observe `~/.bmad-loops` and have been dormant since 2026-08-22 **When** marshal's Epic 33 lands their effect stories (the `bmad-correct-course` already scheduled there also carries token-economy CAP-18 and the risk-tiered wiring story) **Then** this row flips `done` and `capability-effect-check` stops reporting them
**And** steward's only action is this row plus the citation — the work, the surfaces and the retro are marshal's
**Status:** done
**Outcome (2026-09-13):** marshal's own ledger confirms Stories 33.5 (risk-tiered-review-depth producer+caller), 33.6 (adaptive tiering fed on all eight stations), 33.7 (Epic-20 watchdogs observe the real plane), and 33.8 (first live fan-out wave) are all `done`. Citing marshal Epic 33 as closed for these four capabilities; ledger was never flipped after the work landed.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `49-9-index-marshal-realization-gate-effect-stories: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
