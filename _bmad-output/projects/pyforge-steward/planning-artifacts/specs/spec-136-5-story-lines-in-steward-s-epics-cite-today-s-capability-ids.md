---
title: '136.5: Story lines in steward''s epics cite today''s capability ids'
type: 'fix'
created: '2026-11-25'
status: 'ready-for-dev'
story: 136-5-story-lines-in-steward-s-epics-cite-today-s-capability-ids
spec: spec-pyforge-steward
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md'
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

**Problem:** `DW-steward-cutover-2026-11-10-9`. The 2026-11-10 design pass counted 383 Story `FR/AD` lines in steward's `epics.md` that cite a pre-fold or bare capability id or none: 133 bare, 149 qualified to an absorbed Spec, 101 with none.

**Approach:** Re-count first, with a script kept in the story's change log. Re-key each line that cites an absorbed Spec's id by the provenance headings of `SPEC.md` (`CAP-n ... <- spec-<absorbed> CAP-m`), the map `test_cap_citations.py` holds; qualify a bare `CAP-n` only where the Story's own text or its Epic heading fixes which Spec it meant. A line with no capability, and a bare id that cannot be resolved from the page, is left as it is and counted: a guessed arrow is worse than none (trace, never count). Only the citation token moves on a line; no Story text, status, key or heading changes.

Ledger key: `136-5-story-lines-in-steward-s-epics-cite-today-s-capability-ids`.

### Living CAP citations

- spec-pyforge-steward CAP-179 (the ids the station cites are the Spec's; realized, no text change); CHAIN-STANDARD section 2 (a citation names a defined capability); no AD moves.

## Boundaries & Constraints

**Always:**
- Reproduce what the row reports on the unchanged tree before changing it, and record the reproduction in the Spec Change Log.
- Append the surface reconcile to the memlog of each Spec that governs a moved file before the scoped stamps.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never guess an arrow: an id the page does not resolve stays as it is.
- Never renumber or reword a Story.
- Never add a flag, a capability or an architecture decision; a fix that would need one stops and is reported.

## Acceptance Criteria

**Given** `DW-steward-cutover-2026-11-10-9` reports 383 Story FR/AD lines in steward's `epics.md` that cite an absorbed Spec's capability id, a bare id or none
**When** each line citing an absorbed Spec is re-keyed through the Spec's provenance headings, and each bare id the page resolves is qualified
**Then** no Story FR/AD line cites an absorbed steward Spec's capability as a live id, every re-keyed id is a capability `spec-pyforge-steward` defines, and the lines left unresolved are counted by kind in the story's change log
**And** no Story key, heading, status or acceptance line changes, `chain-completeness-check`, `story-status-check` and `ledger-regression-check` pass, and the row reads resolved, naming any remainder as a new row if one is left

- **AC1 — The chain detectors hold.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild chain-completeness-check
  ```

- **AC2 — Story statuses are untouched.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild story-status-check
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-179 (the ids the station cites are the Spec's; realized, no text change); CHAIN-STANDARD section 2 (a citation names a defined capability); no AD moves.
- Dream: `docs/dreams/pyforge-steward.md`, the 2026-11-25 entry (the rows a lapsed blocker held close); operator ruling of 2026-11-25: "All 22 rows".
- Epic: Epic 136, minted with this story.
- Ledger key: `136-5-story-lines-in-steward-s-epics-cite-today-s-capability-ids`.
- Deferred-work row: `DW-steward-cutover-2026-11-10-9`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."136"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry (the rows a lapsed blocker held close) and the operator's ruling of the same date. Not implemented.
