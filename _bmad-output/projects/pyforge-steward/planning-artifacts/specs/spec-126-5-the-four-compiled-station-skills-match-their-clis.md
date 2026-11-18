---
title: '126.5: The four compiled station skills match their CLIs'
type: 'fix'
created: '2026-11-18'
status: 'ready-for-dev'
story: 126-5-the-four-compiled-station-skills-match-their-clis
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # tests, a gate's own module and the scripts a gate runs; a gated gate is a silent green (roster list)
surface:
  - '.claude/skills/pyforge-doctor/**'
  - '.claude/skills/pyforge-herald/**'
  - '.claude/skills/pyforge-marshal/**'
  - '.claude/skills/pyforge-steward/**'
  - 'docs/reference/skills-catalog.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The audit of 2026-11-17 found doctor's, herald's, marshal's and steward's compiled skills state optional flags as required and omit verbs and flags their CLIs have.

**Approach:** Each of the four is updated through `skf-update-skill` against the live CLI and the skills catalog is regenerated.

Ledger key: `126-5-the-four-compiled-station-skills-match-their-clis`.

### Living CAP citations

- spec-pyforge-steward CAP-175 and CAP-5 (realized, no text change); FR-49 ← CAP-175; no AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Close the deferred-work row this story names with the commit that resolves it.

**Never:**
- Never weaken an assertion that holds on Linux, hand-edit a compiled skill, a `SPEC.md`, a generated page or `sprint-status-ledger.yaml`.

## Acceptance Criteria

**Given** the audit of 2026-11-17 found doctor's, herald's, marshal's and steward's compiled skills state optional flags as required and omit verbs and flags their CLIs have
**When** each of the four is updated through `skf-update-skill` against the live CLI and the skills catalog is regenerated
**Then** each mismatch the audit listed is gone, no other skill directory changes, and the scribe instruction-surface parity test passes
**And** `DW-doctor-59-6-1` reads resolved in its ledger with the commit that closed it

- **AC1 — The story's own check passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-scribe pyforge-scribe-live-test && pixi run --frozen -e pyforge-guild docs-currency-check
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-175 and CAP-5 (realized, no text change); FR-49 ← CAP-175; no AD moves.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-11-18 entry; operator ruling of 2026-11-18: "THIS MACHINE WILL BE A FIRST CLASS DEVELOPMENT HOST -- JUST FIX ALL THE DEFERRED ROW ITEMS NOW.. AND NOT LEAVE ANYTHING FOR LATER", "JUST USE ctranslate2 and remove the other one", "we should continue to support manticore and antigravity", "we still want to do everything in this session as one PR".
- Epic: Epic 126, minted with this story.
- Ledger key: `126-5-the-four-compiled-station-skills-match-their-clis` (`backlog`).
- Surface: `marshal-policy.toml` `[epic_surfaces]."126"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-18: minted from the station Dream's 2026-11-18 entry and the operator's rulings of the same date.
