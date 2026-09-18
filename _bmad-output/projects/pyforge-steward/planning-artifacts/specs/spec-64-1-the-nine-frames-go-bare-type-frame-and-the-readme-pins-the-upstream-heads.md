---
title: '64.1: The nine Frames go bare `type: frame` and the README pins the upstream heads'
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

**Problem:** our Frames stamp `frame [0.3]`, a version no release has assigned

**Approach:** all nine read `type: frame`; `frame-preflight` is green; the README names the #28 and #29 SHAs we conform to

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-64-1-the-nine-frames-go-bare-type-frame-and-the-readme-pins-the-upstream-heads.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| our Frames stamp `frame [0.3]`, a version no release has assigned | this story lands | all nine read `type: frame`; `frame-preflight` is green; the README names the #28 and #29 SHAs we conform to | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | `pixi run -e pyforge-steward frame-upstream-check` clones frame-spec at the pinned SHA into a temp dir and reports 9/9 OK, exiting non-zero on any FAIL; it is opt-in and appears in no aggregate | n/a |

</intent-contract>

## Binding

Parent Spec capability: `named on the story in epics.md`.
Surface: `docs/foundry/frames/pyforge.frame.md`, `docs/foundry/frames/stations/*.frame.md`, `docs/foundry/frames/README.md` (Upstream pin block), `src/shared/packages/pyforge-steward/src/pyforge/steward/frames.py` docstring, `pixi.toml` `[feature.pyforge-steward.tasks.frame-upstream-check]`, deferred-work ledger accepted-risk entry.
Ledger key: `64-1-the-nine-frames-go-bare-type-frame-and-the-readme-pins-the-upstream-heads`.
Ledger status at mint (unchanged): `done`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-64-1-the-nine-frames-go-bare-type-frame-and-the-readme-pins-the-upstream-heads.md`.

## Epic excerpt

**Type:** docs • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-steward CAP-6 (a), (b), (c)
**Surface:** `docs/foundry/frames/pyforge.frame.md`, `docs/foundry/frames/stations/*.frame.md`, `docs/foundry/frames/README.md` (Upstream pin block), `src/shared/packages/pyforge-steward/src/pyforge/steward/frames.py` docstring, `pixi.toml` `[feature.pyforge-steward.tasks.frame-upstream-check]`, deferred-work ledger accepted-risk entry.
**Given** our Frames stamp `frame [0.3]`, a version no release has assigned
**When** this story lands
**Then** all nine read `type: frame`; `frame-preflight` is green; the README names the #28 and #29 SHAs we conform to
**And** `pixi run -e pyforge-steward frame-upstream-check` clones frame-spec at the pinned SHA into a temp dir and reports 9/9 OK, exiting non-zero on any FAIL; it is opt-in and appears in no aggregate
**Status:** backlog

