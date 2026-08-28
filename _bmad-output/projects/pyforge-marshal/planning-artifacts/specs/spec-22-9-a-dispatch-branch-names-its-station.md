---
title: A dispatch branch names its station
type: bug
created: '2026-08-27'
status: in-progress
updated: '2026-08-27'
baseline_revision: 8519bd3a835fad95a455b4b9e7eb198910693bb0
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-single-story-dispatch/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-22-7-fleet-wide-drain-is-a-marshal-orchestrated-mode.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `core/dispatch.py::dispatch_worktree_branch(story_key)` renders
`marshal/<story_key>` with no station slug — mason 12.1 landed on `marshal/12.1`. Worse
than naming: `cli/dispatch.py::_ensure_dispatch_worktree` resolves an existing worktree BY
BRANCH NAME, so two stations sharing a story key silently reuse each other's worktree. At
Story 22.7 fleet-drain scale (eight stations dispatching concurrently) a cross-station key
collision is inevitable.

**Approach:** derive station-scoped branch names (`dispatch/<slug>/<key>`) from one
function every consumer shares; resolve or explicitly refuse legacy `marshal/<key>`
branches; never a second derivation site.

## Acceptance Criteria

- Given a dispatch for station `<slug>` story `<key>`, when the worktree branch is derived, then it carries the station (`dispatch/<slug>/<key>`) and no two stations can collide on a shared story key.
- Given an in-flight or preserved branch under the legacy `marshal/<key>` name, when dispatch or landing resolves it, then it is still found (or the refusal names the legacy branch and the land-first remedy) — never silent reuse of another station's tree.
- Given the branch-name consumers (worktree lookup, in-flight conflict guard, landing classification, status overlay), when any derives the name, then all agree on the one derivation function — verified by a test that fails on a second derivation site.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-marshal/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-marshal` only — never `scripts/bmad-switch`. Ledger key `22-9-a-dispatch-branch-names-its-station`. One derivation function; consumers import it.

**Block If:** Story 22.7 has not landed (its in-flight session edits `cli/dispatch.py`; implementing first manufactures a merge conflict). A change would strand the three preserved legacy branches (`marshal/20.1`, `marshal/12.1`, `marshal/22.7`, pushed to origin 2026-08-27) without a documented resolution path.

**Never:** A second branch-name derivation site. Deleting or force-moving a preserved legacy branch. Touching the conda-forge-expert surface.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| New dispatch | `pyforge-atlas`, `20-2` | branch `dispatch/pyforge-atlas/20.2`; worktree resolved by that name | — |
| Cross-station same key | `pyforge-atlas 20-1` while `pyforge-doctor 20-1` exists | two distinct branches/worktrees; zero reuse | collision impossible by construction |
| Legacy branch present | `marshal/12.1` exists with WIP | resolved for its original station, or loud refusal naming land-first | never silent cross-station reuse |
| Landing | verified story on new-name branch | Epic 4 landing + marshal-native classification unchanged | — |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch.py:160` — `dispatch_worktree_branch(story_key)` gains the slug parameter; the ONE derivation site.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py:~156` — `_ensure_dispatch_worktree` passes the slug; `worktree_path_for_branch` lookup keeps legacy-name fallback for the three preserved branches.
- Grep for every other `dispatch_worktree_branch` / literal `marshal/` branch-string consumer (landing, status overlay `core/status.py`, conflict guard) and route through the one function.
- Tests: `tests/unit/test_dispatch.py` — collision case (two stations, same key), legacy-fallback case, single-derivation-site guard.
