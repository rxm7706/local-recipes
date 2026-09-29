---
title: '64.2: PyForge publishes its Frame conformance profile'
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

**Problem:** §7 requires every implementation to publish a profile and PyForge has none

**Approach:** the profile states all ten §7 items for the in-repo reader (reads Markdown, writes none, resolves no composition, `visibility` is declared intent, `specification: draft-mcandrew-frame-spec-00`) and declares under §9 that no trust configuration exists yet

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-64-2-pyforge-publishes-its-frame-conformance-profile.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| §7 requires every implementation to publish a profile and PyForge has none | this story lands | the profile states all ten §7 items for the in-repo reader (reads Markdown, writes none, resolves no composition, `visibility` is declared intent, `specification: draft-mcandrew-frame-spec-00`) and d… | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | upstream `validate_frame.py --check-profile` at the pinned SHA accepts it via `frame-upstream-check` | n/a |

</intent-contract>

## Binding

Parent Spec capability: `named on the story in epics.md`.
Surface: `docs/foundry/frames/conformance-profile.yaml`, `docs/foundry/frames/README.md` § Conformance profile.
Ledger key: `64-2-pyforge-publishes-its-frame-conformance-profile`.
Ledger status at mint (unchanged): `done`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-64-2-pyforge-publishes-its-frame-conformance-profile.md`.

## Epic excerpt

**Type:** docs • **Effort:** S • **Deps:** S-64.1 • **FR/AD:** spec-pyforge-steward CAP-6 (d); Constraint CAP-6
**Surface:** `docs/foundry/frames/conformance-profile.yaml`, `docs/foundry/frames/README.md` § Conformance profile.
**Given** §7 requires every implementation to publish a profile and PyForge has none
**When** this story lands
**Then** the profile states all ten §7 items for the in-repo reader (reads Markdown, writes none, resolves no composition, `visibility` is declared intent, `specification: draft-mcandrew-frame-spec-00`) and declares under §9 that no trust configuration exists yet
**And** upstream `validate_frame.py --check-profile` at the pinned SHA accepts it via `frame-upstream-check`
**Status:** backlog

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `7d4b6ed6ba` (2026-09-16, "steward: open CAP-5 (pyforge-guild env) and CAP-6 (Frame draft re-grounding); land 64.1+64.2"). Ledger row `64-2-pyforge-publishes-its-frame-conformance-profile: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`, `docs/dreams/intelligence-hub.md`, `docs/dreams/pyforge-steward.md`, `docs/foundry/frames/README.md`, `docs/foundry/frames/conformance-profile.yaml`, `docs/foundry/frames/pyforge.frame.md`, `docs/foundry/frames/stations/atlas.frame.md` (+11 more)
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
