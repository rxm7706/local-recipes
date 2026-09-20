---
title: '53.4: Guards as a library without a second verdict'
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

**Problem:** Source-Grounding exists only at scribe recall AD-8 and Outcome is absent **When** this story lands **Then** a Spec can name which paper Guard categories it lacks

**Approach:** a Spec can name which paper Guard categories it lacks

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-53-4-guards-as-a-library-without-a-second-verdict.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Source-Grounding exists only at scribe recall AD-8 and Outcome is absent **When** this story lands **Then** a Spec can name which paper Guard categories it lac… | this story lands **Then** a Spec can name which paper Guard categories it lacks | a Spec can name which paper Guard categories it lacks | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | Warden stays the sole PR verdict and doctor stays advisory — no Guard mints a second verdict | n/a |
| And-clause from epics.md | when the story lands | Source-Grounding is the first category added to the library | n/a |

</intent-contract>

## Binding

Parent Spec capability: `named on the story in epics.md`.
Surface: named on the story in epics.md
Ledger key: `53-4-guards-as-a-library-without-a-second-verdict`.
Ledger status at mint (unchanged): `done`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-53-4-guards-as-a-library-without-a-second-verdict.md`.

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** 53.1 • **FR/AD:** spec-intelligence-hub
CAP-4 (B7)
**Given** Source-Grounding exists only at scribe recall AD-8 and Outcome is
absent **When** this story lands **Then** a Spec can name which paper Guard
categories it lacks
**And** Warden stays the sole PR verdict and doctor stays advisory — no Guard
mints a second verdict
**And** Source-Grounding is the first category added to the library
**Status:** done

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `5ce83b3686` (2026-09-13, "Merge pull request #1335 from rxm7706/steward-53-4-guards"). Ledger row `53-4-guards-as-a-library-without-a-second-verdict: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `.claude/skills/pyforge-steward/0.1.0/pyforge-steward/SKILL.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`, `docs/foundry/guards/README.md`, `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py`, `src/shared/packages/pyforge-steward/src/pyforge/steward/guards.py`, `src/shared/packages/pyforge-steward/tests/unit/test_cli.py`, `src/shared/packages/pyforge-steward/tests/unit/test_guards.py`, `src/shared/packages/pyforge-steward/tests/unit/test_restore_duty.py`, `src/shared/packages/pyforge-steward/tests/unit/test_track.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
