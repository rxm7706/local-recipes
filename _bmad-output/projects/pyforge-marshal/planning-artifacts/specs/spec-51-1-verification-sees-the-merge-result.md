---
title: '51.1: Verification sees the merge result'
type: 'fix'
created: '2026-09-19'
status: 'ready'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** on 2026-09-18 marshal 50.4's review pass rewired doctor's `sources/marshal.py` / `sources/ledger.py` 42 min after doctor 27.5 had rewired the same files past 50.4's baseline — the branch suite was green, land was refused, the operator hand-composed `1a5895317f`, and the part git *would* have auto-merged called `bare_merge.py` with 2 args against the new 3-arg signature

**Approach:** the branch baseline is behind `origin/main` on any file the branch touches, land materialises `git merge-tree --write-tree origin/main <head>`, runs the station's own `verify_commands` against that tree, and refuses with a named finding when it is red — while a conflict-free green merge lands with no operator action

## Boundaries & Constraints

**Always:**
- the 50.4/27.5 fixture refuses with the runtime `TypeError` named in the finding, a fixture with a clean merge lands, and a branch whose baseline already equals `origin/main` verifies exactly once (byte-identical to today)
- removing the merged-tree run lets the 50.4/27.5 fixture land green (mutation test); marshal never performs the merge and no new gate or verdict owner appears

**Never:**
- Do not make the supervisor trust a session's self-report, perform the merge marshal only materialises, add a second gate or verdict owner, move a primary checkout that is not a clean `main`, or re-attribute landed history — the Epic 51/52 HARD boundaries in `epics.md` bind.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the named fixture | the real run/journal/PR named in the Given | the Then holds | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-249`.
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py` (the hook before `forge.merge_pr`; the MRS-DISP-038 branch), `.../dispatch_verify.py::evaluate_dispatch_verification` (a merged-tree checkout is another `worktree` path), `.../ports/vcs.py` + `.../adapters/vcs_git.py` (a `--write-tree` sibling of `merge_tree_conflict_paths` that materialises the tree), `.../core/dispatch_landing.py` (pure eligibility), `.../dispatch_supervisor/__main__.py` (`_run_and_journal_landing`, only if a new journal kind is needed), tests.
Ledger key: `51-1-verification-sees-the-merge-result`.
Minted 2026-09-19 from `epics.md` so `marshal factory dispatch` (51.x) or a hand-driven `bmad-build-auto` (52.x) can resolve `spec-51-1-verification-sees-the-merge-result.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- The Then/And of Story 51.1 in `epics.md` hold on the named fixture; the mutation or byte-identical check named there is run, not inferred.
