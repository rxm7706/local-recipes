---
title: '49.10: Index — atlas realization-gate effect stories'
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

**Problem:** `atlas-query-dashboards` shipped a second Lane-3 runtime at `pyforge/atlas/views/` (Epic 14, CAP-1..145, 4/4 `done`) that nothing reaches — no CLI verb, pixi task, ASGI mount or portal imports it, only `tests/unit/views/*` — and it reads the legacy SQLite store through a dynamic-import bridge whose own docstring declares the evasion of CAP-19's "no private DuckDB" ruling (`cli_bridge.py:11-17`) *…

**Approach:** this row flips `done`; the Unifying Dream's Kinships line has already been corrected here to say `retired 2026-09-09`

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-49-10-index-atlas-realization-gate-effect-stories.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| `atlas-query-dashboards` shipped a second Lane-3 runtime at `pyforge/atlas/views/` (Epic 14, CAP-1..145, 4/4 `done`) that nothing reaches — no CLI verb, pixi t… | atlas records the **retirement** (operator ruling C1: delete the package + tests, record the supersession on its Spec,… | this row flips `done`; the Unifying Dream's Kinships line has already been corrected here to say `retired 2026-09-09` | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | the live Lane-3 runtime is and remains the Vizro/BSL board (31 pages) | n/a |

</intent-contract>

## Binding

Parent Spec capability: `named on the story in epics.md`.
Surface: this file only (the index row). Atlas's own artifacts are **named, never edited** by steward
Ledger key: `49-10-index-atlas-realization-gate-effect-stories`.
Ledger status at mint (unchanged): `done`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-49-10-index-atlas-realization-gate-effect-stories.md`.

## Epic excerpt

**Type:** index • **Effort:** S • **Deps:** S-49.2; cross-station: atlas's effect epic (ledger `blocked` until it closes) • **FR/AD:** fleet readiness 2026-09-09 § 2.3 C1 / C6
**Surface:** this file only (the index row). Atlas's own artifacts are **named, never edited** by steward
**Given** `atlas-query-dashboards` shipped a second Lane-3 runtime at `pyforge/atlas/views/` (Epic 14, CAP-1..145, 4/4 `done`) that nothing reaches — no CLI verb, pixi task, ASGI mount or portal imports it, only `tests/unit/views/*` — and it reads the legacy SQLite store through a dynamic-import bridge whose own docstring declares the evasion of CAP-19's "no private DuckDB" ruling (`cli_bridge.py:11-17`) **When** atlas records the **retirement** (operator ruling C1: delete the package + tests, record the supersession on its Spec, keep the widget-registry idea only if a Vizro page wants it) **Then** this row flips `done`; the Unifying Dream's Kinships line has already been corrected here to say `retired 2026-09-09`
**And** the live Lane-3 runtime is and remains the Vizro/BSL board (31 pages)
**Status:** done
**Outcome (2026-09-13):** confirmed shipped 2026-09-10 via atlas Story 25.1 (PR #1114, `caeae255d05`) — `pyforge/atlas/views/`, its tests, and `cli_bridge.py` are all deleted (verified: zero repo-wide importers outside this Spec's own narrative text), `docs/dreams/atlas-query-dashboards.md` is `status: archived` with a Realization log entry, and `spec-atlas-query-dashboards/SPEC.md` marks CAP-1..CAP-4 `SUPERSEDED`. Ledger was never flipped after the work landed.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `49-10-index-atlas-realization-gate-effect-stories: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
