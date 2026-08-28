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

## Implementation record — 2026-08-27

**Shape as built.** `core/dispatch.py` owns two derivations and one resolver:
`dispatch_worktree_branch(slug, story_key)` → `dispatch/<slug>/<key>` (slug is a required
positional, so an unmigrated consumer raises `TypeError` rather than rendering a
station-less name), `legacy_dispatch_worktree_branch(story_key)` → `marshal/<key>` (read,
never minted), and `resolve_dispatch_branch(vcs, repo_root, slug=…, story_key=…,
worktree=…)` — the single site where the legacy name is reconciled. Attribution of a legacy
branch is a git fact, not a guess: it is this station's only when git has it checked out AT
this station's dispatch worktree. Every branch-name consumer routes through the resolver —
`cli/dispatch.py::_ensure_dispatch_worktree`, `dispatch_supervisor::gather_dispatch_git_facts`
(which is also what the CAP-2 zombie refusal and the CAP-5 in-flight guard read), and
`dispatch_land::execute_dispatch_land`. `core/status.py`'s dispatch overlay derives no
branch name, so it needed no change.

**New finding codes:** `MRS-DISP-030` (ERROR) — an unattributable legacy branch refuses the
dispatch/landing, naming the branch and the land-first remedy; `MRS-DISP-031` (WARN) — this
run IS on an attributable legacy branch and proceeds from it, so the migration is visible
rather than silent.

**Verification.** `pixi run -e pyforge-marshal pyforge-marshal-test`: 6503 passed / 1
failed, the failure being the pre-existing `test_skf_domain_skill::
test_context_files_not_hand_edited` red that predates this story (it asserts on
`CLAUDE.md`/`AGENTS.md`, untouched here) and was already recorded on Story 22.7. Import-linter
`lint-imports`: 5 contracts kept, 0 broken (AD-4 core purity holds — `resolve_dispatch_branch`
takes a `VcsPort`, which is not a forbidden module). The single-derivation-site guard was
verified to genuinely fire by temporarily planting a second site. Live read-only run of
`resolve_dispatch_branch` against the real repo: the three in-flight legacy runs
(`marshal/22.9`, `marshal/12.2`, `marshal/20.2`) all resolve to their legacy branch, and a
different station on a live key (`pyforge-doctor 12.2`) is refused naming
`.worktrees/dispatch-pyforge-mason-12.2` — the exact silent-reuse defect, now loud.

**Correction to the Block If premise.** The three named preserved branches are not where the
spec says: `marshal/20.1`, `marshal/12.1` and `marshal/22.7` are absent from `origin`
(`git ls-remote --heads origin` carries no dotted `<prefix>/<n>.<n>` head at all) and absent
from `refs/heads/` here; `marshal/20.1` and `marshal/22.7` survive only as stale
remote-tracking refs into the station loop homes, their stories having landed via PRs #886
and #887, and `marshal/12.1` does not exist in any form. The legacy branches that DO exist
are the three in-flight dispatch-worktree branches above, and all three resolve — nothing is
stranded, and the `MRS-DISP-030` refusal is the documented resolution path for any that
reappear.
