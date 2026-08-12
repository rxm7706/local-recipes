# Sprint Change Proposal — 2026-08-12

**Project:** pyforge-marshal
**Mode:** Batch (single, well-scoped addition; no iterative refinement needed)
**Scope classification:** Minor — direct implementation by a Developer agent (`bmad-quick-dev`) whenever prioritized.

## 1. Issue Summary

Story 5.9's review pass 2 (2026-08-12) discovered that `marshal land`'s own merges render a
GitHub-auto-generated subject indistinguishable from a human's plain PR merge, defeating
`core.promotion.marshal_native_merged_keys`'s otherwise-correct classification for every
`marshal land` landing. This was resolved *for 5.9's own scope* by relabeling its reported
completion path from `bmad-quick-dev` to the honest, coarser `not-loop-native` (see 5.9's Spec
Change Log, 2026-08-12). The root-cause fix — making `marshal land` render the same templated,
detectable subject `deploy land-story` already does — was explicitly deferred as a follow-up,
not a prerequisite, per the operator's own decision.

A Dream (`docs/dreams/marshal-land-detectable-merge-subject.md`) and Spec
(`_bmad-output/planning-artifacts/specs/spec-marshal-land-merge-subject/SPEC.md`) were produced
for that follow-up. This proposal sequences the Spec into a Story slot so it is not lost to the
backlog with no owning epic entry.

## 2. Impact Analysis

- **Epic impact:** Epic 5 (Fleet visibility) only — the new story serves that epic's own stated
  goal ("... be told, rather than left to discover, where the ledger and git disagree") by
  making one more Marshal-driven landing route classifiable.
- **Story impact:** One new story added (5.10). No existing story's acceptance criteria,
  dependencies, or status change. Story 5.9 is unaffected (already shipped its own resolution;
  5.10 is additive, not a correction to it).
- **Artifact conflicts:** `epics.md` only — story count (E5: 9→10), running total (125→126),
  and the file's own running footnote (extended, not rewritten). PRD.md carries no FR catalog to
  update (confirmed: FR-181/185/186, the three most recent prior additions, have no PRD.md
  entries either — this repo's convention is inline-in-epics.md only for small Dream/Spec-chain
  additions). No architecture or UX artifact impact.
- **Technical impact:** None yet — this proposal only sequences the story; implementation
  (`ForgePort.merge_pr` gaining an optional `subject` parameter, `adapters/forge_gh.py` passing
  `-t/--subject` to `gh pr merge`, `cli/land.py::run_land` computing it via
  `identity.render_merge_subject`) is Story 5.10's own future scope, per the Spec.

## 3. Recommended Approach

**Direct Adjustment** — add Story 5.10 within the existing Epic 5, no rollback or MVP-scope
review needed. Effort: **S**. Risk: low (`gh pr merge` already supports `-t/--subject` for every
merge strategy, confirmed via `gh pr merge --help` before the Spec was written — no unknown API
constraint). Timeline: backlog, unsequenced; not on any current critical path.

## 4. Detailed Change Proposal

**Artifact:** `_bmad-output/planning-artifacts/epics.md`

**Change 1 — new story, Epic 5** (after Story 5.9, before `## Epic 6`):

```
### Story 5.10: `marshal land` renders a detectable merge subject *(added 2026-08-12 — FR-187, backlog)*
[full As-a/I-want/So-that + Why now + Acceptance Criteria — see epics.md]
```

Sourced entirely from `spec-marshal-land-merge-subject/SPEC.md`'s CAP-1, constraints, and
non-goals; no scope invented beyond the Spec.

**Change 2 — epic index table:** E5 story count `9` → `10`; Total `125` → `126`.

**Change 3 — running footnote paragraph:** appended a sentence for Story 5.10, matching the
exact convention the 5.7/5.8/2.8+5.9 entries already established (FR number, source, deliberate
`sprint-status-ledger.yaml` exclusion pending next sync, running epic/total counts).

**Rationale (all three):** matches this file's own established, repeatedly-used convention for
sequencing a small Dream/Spec-chain addition without a full PRD/architecture pass — see the
identical pattern for Stories 5.8, 3.11-3.13, and 2.8/5.9 in the same footnote paragraph.

## 5. Implementation Handoff

**Minor scope** — routed to: Developer agent (`bmad-quick-dev`), whenever the operator
prioritizes Story 5.10. Deliverables already in place: the Story's Acceptance Criteria (in
`epics.md`) and the full technical contract (`spec-marshal-land-merge-subject/SPEC.md`) — a dev
session can implement directly against either, they agree by construction (the Story was
derived from the Spec, not authored independently).

**Success criteria:** `marshal_native_merged_keys`, given a real post-fix `marshal land` merge
subject, classifies it as native; `pyforge-marshal-test` green; no change to `marshal land`'s
existing gates or default strategy.
