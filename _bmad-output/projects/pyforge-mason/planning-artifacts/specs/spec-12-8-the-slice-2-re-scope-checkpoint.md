---
title: The slice-2 re-scope checkpoint
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
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/slice-map.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-6-4-the-re-scope-gate-measured-cost-recorded-decision.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** After slice 2 completes (Story 12.7), nothing yet records its measured cost or
a go/adjust/stop decision for slices 3-4, slice 5's opportunistic porting, or the end-cutover
decomposition trigger. Story 6.4's own re-scope note already recommends this exact repeat
"before slice 3's brief specifically, since slice 3 is even larger (12.3x) than slice 2."

**Approach:** Record a second dated re-scope note in `campaign-state.yaml` — slice 2's
measured cost, the go/adjust/stop decision for slices 3-4, slice 5's opportunistic-porting
status, and the end-cutover decomposition trigger — following Story 6.4's own note-writing
discipline. No slice-3 brief and no endgame stories land before this checkpoint.

## Acceptance Criteria

- **Given** the completed slice 2 **Then** a second dated re-scope note in campaign state
  records slice 2's measured cost and the go/adjust/stop decision for slices 3–4, slice 5's
  opportunistic porting, and the end-cutover decomposition trigger — no slice-3 brief and no
  endgame stories before this lands (the 6.4 note's own recommendation before the 12.3x
  slice).

## Boundaries & Constraints

**Always:**
- Write artifacts under `_bmad-output/projects/pyforge-mason/planning-artifacts/` literally.
  `BMAD_ACTIVE_PROJECT=pyforge-mason` only — never `scripts/bmad-switch`. Ledger key
  `12-8-the-slice-2-re-scope-checkpoint`.
- Block until Story 12.7 (`slice-2-recipe-lifecycle` at `status: compiled`/`equivalence:
  green`, or an honestly-recorded non-green) is done — this story's sole Dep.
- Follow Story 6.4's own note-writing discipline exactly: base the cost accounting on
  evidence actually gathered (12.7's real commit history, dual-maintenance burden, any new
  cross-slice gaps found), record a structured `decision` field (go/adjust/stop) alongside a
  dated prose `note` — avoiding 6.4's own review-caught pitfall of recording the verdict only
  in prose — and state whether slice 5's opportunistic porting needs any explicit action yet.
- Decide/record slices 3-4's own go/adjust/stop and the end-cutover decomposition trigger,
  updating Story 6.4's own "high-level end-cutover plan" with whatever changed since slice 1
  (e.g. `campaign.callers` population plan; SPEC.md Open Question 4's deprecation posture;
  Open Question 5's Rule-2-retro-landing-surface precedent, now that Story 12.7 should have
  set it).

**Block If:** The evidence is genuinely ambiguous, or the risk of recording the wrong
decision is asymmetric enough to need human sign-off — HALT `blocked`, per Story 6.4's own
precedent, rather than picking a verdict to avoid halting.

**Never:**
- Never edit `.claude/skills/conda-forge-expert/**`, `.claude/scripts/conda-forge-expert/**`,
  or `.claude/tools/conda_forge_server.py` (CFE surface) — mason consults CFE, never edits it
  (mason-cfe-surface-check gate).
- Never write slice 3's brief as part of this story, regardless of the decision recorded —
  matches Story 6.4's own "never write a second slice's brief" boundary, one slice number
  further on.
- Never touch `cfe_rebuild_guard_check.py`'s clause logic (including the clause (d) Story
  12.4 adds) — this story only writes campaign-state.yaml's re-scope note, same as Story
  6.4's own boundary.
- Never touch `epics.md` or `sprint-status-ledger.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Evidence supports a decision | Slice 2's real cost data (Story 12.7) | Second dated re-scope note recorded, `decision` field set | — |
| Evidence ambiguous | Conflicting signals | HALT `blocked`, evidence + question stated | — |
| Decision recorded | — | Slice 3/4's `next_action` text updated to match, same as Story 6.4 did for slice 2 | Must not leave stale `next_action` text (Story 6.4's own review-caught bug) |
| No slice-3 brief exists yet | — | Verified: `slices[2].brief_path` still `null` after this story | Test/verification step, not just a promise |

</intent-contract>

## Code Map

- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml`
  — add a second dated re-scope note (structured similarly to the existing
  `campaign.re_scope_gate` block — a new key such as `campaign.re_scope_gate_2`, or an
  appended dated entry within the existing note, whichever keeps the file most resumable per
  CAP-4's "fresh session reads one file" design intent); update slice 3/4's `next_action` text
  to match whatever is decided, mirroring how Story 6.4 updated slice 2's and its own
  `campaign.next_story` field.
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/slice-map.md`
  — read-only source for slice 3 (37/35/22) and slice 4 (2/2/2) sizes, already exact per
  Story 6.4's own re-verification.
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/SPEC.md`
  — read-only; Open Questions 4 (deprecation posture) and 5 (Rule-2 retro landing surface)
  should be referenced/updated if Stories 12.6/12.7 resolved either in practice.
