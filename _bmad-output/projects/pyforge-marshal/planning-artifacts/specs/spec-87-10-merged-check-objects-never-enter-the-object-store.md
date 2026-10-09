---
title: "87.10: Merged-check objects never enter the object store"
type: 'fix'
created: '2026-10-04'
status: 'in-progress'
baseline_revision: '3cd4a1e205e47bcdd521e7372117594ad2110424'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/preserved-work-refs-2026-10-04.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/preserved-work-refs-2026-10-04-review.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/vcs_git.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Every `is_branch_merged` call builds a synthetic "marshal teardown merged-check (not a real commit)" commit with `git commit-tree` in the repository's own object store (`adapters/vcs_git.py:490-512`). The merge-tree preview does the same (`:1347-1375`). The dispatch supervisor calls the merged check every tick. On 2026-10-04, 19,412 of the 20,135 dangling commits were these objects, created at 700–2,500 a day. That pushes the loose-object count past `gc.auto`'s threshold and slows `fsck` to 30–46 s. 149 of the 682 `rescue/dangling-*` tags preserve such objects, and the unpushed-work detector would now print a minting remedy for about 16,000 more.

**Approach:** Answer the same questions without writing a commit object into the repository. Any one of these is acceptable, as long as the behaviour criteria below hold:
- compute the patch-id from `git diff <merge-base> <tree> | git patch-id --stable`, with no commit object;
- write the synthetic commit into a temporary object directory reached through `GIT_ALTERNATE_OBJECT_DIRECTORIES` / `GIT_OBJECT_DIRECTORY`;
- pin `GIT_AUTHOR_DATE` / `GIT_COMMITTER_DATE`, so repeated checks reuse one object per (tree, merge-base).

The review (M2.2) prefers the first two because they leave no object at all. Land this beside Story 87.2.

Ledger key: `87-10-merged-check-objects-never-enter-the-object-store`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- AD-47 (the patch-id evidence the merged check computes) and `spec-pyforge-marshal` CAP-287 / AD-81 (nothing mints unreviewed preserves of scratch). A defect of shipped behaviour, so it is a `fix` with no flag. The operator ruled on 2026-10-04 that 87.10 ships unflagged.

## Acceptance Criteria

- Given an unmerged branch, a squash-equivalent branch and an ancestor branch When `is_branch_merged` runs on each Then its verdict is unchanged from today's for each, and `git count-objects -v` (loose and packed counts) is identical before and after.
- Given the merge-tree preview path When it runs Then the same holds: same answer, no new object.
- Given a temporary object directory, if the implementation uses one When the call returns, or raises Then the directory is removed.
- Given the change reverted When the tests run Then the object-count test fails (mutation).

## Boundaries & Constraints

**Always:** Same verdicts. Real git repositories in tests. Keep the change behind the VCS port (AD-4).

**Never:** Never write a commit, tree or blob into the repository's store to answer a read-only question. Never change what counts as merged.

</intent-contract>

## Binding

Parent: AD-47; `spec-pyforge-marshal` CAP-287 / AD-81.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-04 (preserved-work refs) entry.
Research: drafts' Story 87.10; review M2 (land with 87.2; simpler forms allowed).
Ledger key: `87-10-merged-check-objects-never-enter-the-object-store`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-04 under the operator's ruling of the same day.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- The object-count tests: `src/shared/packages/pyforge-marshal/tests/unit/test_vcs_git_merged_check_objects.py` (new) beside `tests/unit/test_vcs_git*.py`.

## Spec Change Log

- No change yet.

## Review Triage Log

- No review has run yet.
