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

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `7d4b6ed6ba` (2026-09-16, "steward: open CAP-5 (pyforge-guild env) and CAP-6 (Frame draft re-grounding); land 64.1+64.2"). Ledger row `64-1-the-nine-frames-go-bare-type-frame-and-the-readme-pins-the-upstream-heads: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`, `docs/dreams/intelligence-hub.md`, `docs/dreams/pyforge-steward.md`, `docs/foundry/frames/README.md`, `docs/foundry/frames/conformance-profile.yaml`, `docs/foundry/frames/pyforge.frame.md`, `docs/foundry/frames/stations/atlas.frame.md` (+11 more)
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
