---
title: '63.4: `steward session check` — one verdict for the session preconditions, run from every entry point'
type: 'feature'
created: '2026-09-18'
status: 'ready'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** a session begins on any harness, local or cloud

**Approach:** it reports, as findings not prose: pixi present and `pyforge-guild` materialised at the frozen lock; `bmad-method` at the pinned version (reuse doctor's drift verdict, do not re-implement); the token kit — `headroom` on PATH, this harness's caveman skill installed, the three context layers not `layer-off` (reuse `marshal seed check`); `gh auth status` and `gh api rate_limit` (an unauthenticated s…

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-63-4-steward-session-check-one-verdict-for-the-session-preconditions-run-from-every-entry-point.md` (CHAIN-STANDARD §5).
- This file is the tracked dispatch target for `marshal factory dispatch` / `resolve_story_spec_path`.

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| a session begins on any harness, local or cloud | `pyforge steward session check` runs | it reports, as findings not prose: pixi present and `pyforge-guild` materialised at the frozen lock; `bmad-method` at the pinned version (reuse doctor's drift verdict, do not re-implement); the token… | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | the four entry points call this one command and nothing else for preconditions (vocabulary-one-name-one-job: one mechanism, many surfaces); a cloud clone with no feed can land a ledger flip by follow… | n/a |

</intent-contract>

## Binding

Parent Spec capability: `named on the story in epics.md`.
Surface: `src/shared/packages/pyforge-steward/src/pyforge/steward/` (new `session` duty, `pyforge steward session check`, exit domain `0` ok / `1` findings / `70` crash), `.claude/hooks/session-start.sh`, `.cursor/environment.json` (`start`), `.github/workflows/copilot-setup-steps.yml`, the Marshal dispatch preamble (`pyforge-marshal` calls the steward CLI, never imports it), station tests.
Ledger key: `63-4-steward-session-check-one-verdict-for-the-session-preconditions-run-from-every-entry-point`.
Ledger status at mint (unchanged): `backlog`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-63-4-steward-session-check-one-verdict-for-the-session-preconditions-run-from-every-entry-point.md`.

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** S-63.1, S-63.3 • **FR/AD:** spec-pyforge-steward CAP-5; AD-8 (`DutyResult` is frozen evidence; duties never `sys.exit`)
**Surface:** `src/shared/packages/pyforge-steward/src/pyforge/steward/` (new `session` duty, `pyforge steward session check`, exit domain `0` ok / `1` findings / `70` crash), `.claude/hooks/session-start.sh`, `.cursor/environment.json` (`start`), `.github/workflows/copilot-setup-steps.yml`, the Marshal dispatch preamble (`pyforge-marshal` calls the steward CLI, never imports it), station tests.
**Given** a session begins on any harness, local or cloud
**When** `pyforge steward session check` runs
**Then** it reports, as findings not prose: pixi present and `pyforge-guild` materialised at the frozen lock; `bmad-method` at the pinned version (reuse doctor's drift verdict, do not re-implement); the token kit — `headroom` on PATH, this harness's caveman skill installed, the three context layers not `layer-off` (reuse `marshal seed check`); `gh auth status` and `gh api rate_limit` (an unauthenticated session is a finding, because drift probes fail open); the codegraph index present (absent in every fresh clone); **the Tier-3 feed present for the project in hand — and when absent, the one sanctioned remedy: seed it by copying the tracked twin (`cp planning-artifacts/sprint-status-ledger.yaml implementation-artifacts/sprint-status.yaml`; verified 2026-09-16 in a fresh clone: `sprint-ledger-sync` then reports `unchanged`, tree clean)**; scribe recall reachability (absent by design in `pyforge-guild` — reported, not failed)
**And** the four entry points call this one command and nothing else for preconditions (vocabulary-one-name-one-job: one mechanism, many surfaces); a cloud clone with no feed can land a ledger flip by following the printed remedy
**Status:** backlog

