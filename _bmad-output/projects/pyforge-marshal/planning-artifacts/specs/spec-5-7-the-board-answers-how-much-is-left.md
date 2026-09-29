---
title: '5.7: The board answers "how much is left"'
type: 'feature'
created: '2026-09-18'
status: 'done'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** As the operator, I want the console to show done/total/blocked per station and a PyForge roll-up, So that the first question anyone asks of a fleet is answerable without a CLI.

**Approach:** See Surface / Given-When-Then in epics.md.

Ledger key: `5-7-the-board-answers-how-much-is-left`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: feature / S / —.

### Living CAP citations

- Cited from epics.md: FR-179

## Acceptance Criteria

- Given the tracked `sprint-status-ledger.yaml` of each project When the board is generated Then `data.js` carries per-station `done`/`stories`/`blocked`/`epicsDone`/`epics` plus a PyForge roll-up, counted through the same `parse_sprint_status` the deploy already uses And `blocked` is counted separately — the board's own states (`done`/`active`/`pending`) cannot distinguish blocked from unstarted, and 6 blocked looked identical to 119 pending And an epic counts done only when every story in it is done, matching `scripts/fleet_picture.py` so the two can never disagree And no live field is published: run state, projection and ATTENTION derive from tmux and `~/.bmad-loops`, which CI cannot read — they stay in the local `fleet-picture` report And `dashboard-check` (which executes the board's own JS) passes ---

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the tracked `sprint-status-ledger.yaml` of each project | the board is generated | `data.js` carries per-station `done`/`stories`/`blocked`/`epicsDone`/`epics` plu | named finding / refuse |

</intent-contract>

## Source

Contract recovered from `epics.md` Story 5.7 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `9b3bee4e1f` (2026-08-09, "marshal 5.7: the board answers "how much is left""). Ledger row `5-7-the-board-answers-how-much-is-left: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/prds/prd-pyforge-marshal-2026-07-25/prd.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-dashboard-project-path-derivation/.memlog.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-factory-console/.memlog.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/.memlog.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-testing-charter/.memlog.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-sprint-status-auto-promote/.memlog.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-unified-container/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`, `docs/dashboard/data.js`, `docs/dashboard/generate.py` (+6 more)
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
