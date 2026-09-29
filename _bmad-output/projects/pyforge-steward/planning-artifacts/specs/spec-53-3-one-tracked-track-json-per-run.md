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

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `aedec54f4f` (2026-09-13, "Merge pull request #1334 from rxm7706/steward-53-3-track"). Ledger row `53-3-one-tracked-track-json-per-run: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `.claude/skills/pyforge-marshal/0.1.0/pyforge-marshal/SKILL.md`, `.claude/skills/pyforge-steward/0.1.0/pyforge-steward/SKILL.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`, `docs/foundry/tracks/FIELDS.md`, `docs/foundry/tracks/example-track.json`, `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py`, `src/shared/packages/pyforge-steward/src/pyforge/steward/data/track.schema.json`, `src/shared/packages/pyforge-steward/src/pyforge/steward/track.py`, `src/shared/packages/pyforge-steward/tests/fixtures/track-run-sparse/journal.jsonl`, `src/shared/packages/pyforge-steward/tests/fixtures/track-run/gate-record.json`, `src/shared/packages/pyforge-steward/tests/fixtures/track-run/journal.jsonl` (+4 more)
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
