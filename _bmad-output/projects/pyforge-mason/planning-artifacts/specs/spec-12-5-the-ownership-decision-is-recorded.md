---
title: The ownership decision is recorded
type: chore
created: '2026-08-27'
status: ready
updated: '2026-08-27'
baseline_revision: cc8b3b2b1c09d6e56a5aebf752e25f507c846571
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** SPEC.md's Open Question 1 — "Is this genuinely Mason's to own, or
cross-station? ... Needs an operator decision before any slice beyond the first" — predates
any slice beyond slice 1 and is one of the four pre-conditions gating slice 2's brief
(Story 12.6's Deps).

**Approach:** Obtain the operator's decision and record it, dated, in both SPEC.md's § Open
Questions (item 1) and `campaign-state.yaml`; slice 3's brief authorship follows whatever is
recorded.

## Acceptance Criteria

- **Given** SPEC.md's Open Question 1 (mason owns the whole rebuild vs per-slice station
  ownership — atlas arguably owns the Slice-3 tier) predates any slice beyond the first
  **Then** the operator's decision is recorded dated in SPEC.md § Open Questions and mirrored
  into campaign-state.yaml, and slice 3's brief authorship follows it — until recorded,
  slice-2 briefing stays gated (12.6's Deps).

## Boundaries & Constraints

**Always:**
- Write artifacts under `_bmad-output/projects/pyforge-mason/planning-artifacts/` literally.
  `BMAD_ACTIVE_PROJECT=pyforge-mason` only — never `scripts/bmad-switch`. Ledger key
  `12-5-the-ownership-decision-is-recorded`.
- This is a decision-RECORDING story, not a decision-INVENTING one — obtain the operator's
  actual answer, then record it dated in both SPEC.md § Open Questions and
  `campaign-state.yaml` so both stay in sync.

**Block If:** The operator has not actually answered Open Question 1 when this story runs —
HALT with the question stated plainly (per Story 6.4's own "genuinely ambiguous → halt, do
not pick a verdict" discipline) rather than silently assuming mason owns everything.

**Never:**
- Never edit `.claude/skills/conda-forge-expert/**`, `.claude/scripts/conda-forge-expert/**`,
  or `.claude/tools/conda_forge_server.py` (CFE surface) — mason consults CFE, never edits it
  (mason-cfe-surface-check gate).
- Never touch Mason's own PRD, ARCHITECTURE-SPINE, or Epic 5 as part of recording this
  decision — SPEC.md's own Constraints already forbid rebuild stories from reaching into
  Mason's contracts; this story records who owns the rebuild campaign, not a Mason-architecture
  change.
- Never let this story alone unblock Story 12.6 — 12.6's Deps also name 12.2/12.3/12.4; this
  story closes only pre-condition (d).
- Never touch `epics.md` or `sprint-status-ledger.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Operator answers "mason owns the whole rebuild" | — | SPEC.md OQ-1 gets a dated resolution note; campaign-state.yaml mirrors it | — |
| Operator answers "per-slice station ownership" (atlas owns slice 3) | — | Same, but records slice 3's brief author as atlas, not mason | Slice 3 briefing is out of this epic's scope regardless (gated by Story 12.8) |
| No operator answer available | — | HALT, question restated, no fabricated decision | — |

</intent-contract>

## Code Map

- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/SPEC.md`
  — § "Open Questions", item 1 (around lines 164-169) — add a dated resolution note beneath
  it, in the same style this repo uses to annotate a resolved open question in place (e.g.
  Story 5.4's own recheck-spec resolution-record pattern per CLAUDE.md's Tier-3 promotion
  convention).
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml`
  — mirror the decision; likely a new field near `campaign:` (e.g. alongside
  `re_scope_gate`) rather than overloading an existing one — naming it is this story's own
  job, since no such field exists yet.
- No code files — this is a planning-artifact-only story (chore, Effort XS).
