---
title: '53.2: Company and eight station Frames pass in-repo preflight'
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

**Problem:** B11 says author now **When** this story lands **Then** one Company Frame and eight station Frames that `inherits` it exist in git

**Approach:** one Company Frame and eight station Frames that `inherits` it exist in git

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-53-2-company-and-eight-station-frames-pass-in-repo-preflight.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| B11 says author now **When** this story lands **Then** one Company Frame and eight station Frames that `inherits` it exist in git | this story lands **Then** one Company Frame and eight station Frames that `inherits` it exist in git | one Company Frame and eight station Frames that `inherits` it exist in git | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | each passes the in-repo four-field preflight and names its owner | n/a |
| And-clause from epics.md | when the story lands | no Community Frame or registry is required for success | n/a |

</intent-contract>

## Binding

Parent Spec capability: `named on the story in epics.md`.
Surface: Company + eight station `.frame.md` (git store); in-repo four-field
Ledger key: `53-2-company-and-eight-station-frames-pass-in-repo-preflight`.
Ledger status at mint (unchanged): `done`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-53-2-company-and-eight-station-frames-pass-in-repo-preflight.md`.

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** 53.1 • **FR/AD:** spec-intelligence-hub
CAP-2 (B9/B11; D4 later-caps)
**Note:** Relay — scribe owns Frame-store half as pointer, not as Lexicon owner.
First nine artifacts only. Community Frame and registry stay later-caps.
**Surface:** Company + eight station `.frame.md` (git store); in-repo four-field
preflight (`type`, `name`, `description`, `visibility` + owner). Do not bind
acceptance to upstream `tools/validate_frames.py`.
**Given** B11 says author now **When** this story lands **Then** one Company
Frame and eight station Frames that `inherits` it exist in git
**And** each passes the in-repo four-field preflight and names its owner
**And** no Community Frame or registry is required for success
**Status:** done
**Superseded by 53.6 (2026-09-14) — do not read the Surface/AC above as current.**
The "four-field preflight … + owner" shape was v0.2-era and is gone: `owner` was
never a Frame element in any version (the field is `maintainer`; see
`DW-VOCAB-2026-09-14-4`), and the preflight now requires **six** — `type`,
`identifier`, `name`, `description`, `visibility`, `maintainer` — keyed on
`identifier`, not `name`. Current shape: `docs/foundry/frames/README.md`.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `dea36a14b3` (2026-09-13, "Merge pull request #1333 from rxm7706/steward-53-2-frames"). Ledger row `53-2-company-and-eight-station-frames-pass-in-repo-preflight: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `.claude/skills/pyforge-scribe/0.1.0/pyforge-scribe/SKILL.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`, `docs/foundry/frames/README.md`, `docs/foundry/frames/pyforge.frame.md`, `docs/foundry/frames/stations/atlas.frame.md`, `docs/foundry/frames/stations/doctor.frame.md`, `docs/foundry/frames/stations/herald.frame.md`, `docs/foundry/frames/stations/marshal.frame.md`, `docs/foundry/frames/stations/mason.frame.md`, `docs/foundry/frames/stations/scribe.frame.md`, `docs/foundry/frames/stations/steward.frame.md` (+4 more)
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
