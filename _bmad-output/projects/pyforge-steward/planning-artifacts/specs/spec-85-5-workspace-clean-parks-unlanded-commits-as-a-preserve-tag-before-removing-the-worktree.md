---
title: "85.5: Workspace clean parks unlanded commits as a preserve tag before removing the worktree"
type: 'feature'
created: '2026-10-04'
status: 'blocked'
review_loop_iteration: 0
followup_review_recommended: false
flag:
  key: pyforge.steward.workspace_preserve_tag
  provider: openfeature-file
  default: {production: off, staging: off, dev: off}
  scope: global
  fallback: "workspace clean keeps today's behaviour: a .landed.txt note or a tarball, and an unmerged recorded branch is kept and reported"
  cleanup: 90 days after ON in every environment (Q4)
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/preserved-work-refs-2026-10-04-review.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-87-3-preserved-work-has-one-grammar-and-one-verb.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py
  - src/shared/packages/pyforge-core/src/pyforge/core/preserve_refs.py
  - src/shared/packages/pyforge-core/src/pyforge/core/flags.py
  - src/platform/config/flags.json
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `steward workspace clean` removes an unlanded scratch worktree after it archives the files into a host-local tarball (`workspace.py:866-945`). Since CAP-157, the recorded branch is kept when it is not on its source, so its commits survive only on that local branch. The tarball holds files, never history, and marshal:AD-81 asks for a `preserve/` tag. Low urgency: on 2026-10-04 `.steward/workspace-archive/` held 26 `.landed.txt` notes and no tarballs (review minor 8).

**Blocked:** this story needs `pyforge.core.preserve_refs`, which marshal Story 87.3 ships. Marshal's `Deps:` parser is station-local, so the gate is this ledger row, minted `blocked`. The operator flips it once marshal 87.3 is `done`.

**Approach:**
- **Tag first.** Behind `pyforge.steward.workspace_preserve_tag`, before removing a worktree whose commits are not on its source, `clean` writes an annotated `preserve/<slug>/<N.M>/workspace-<sha8>` tag through `pyforge.core.preserve_refs` (or `preserve/unbound/workspace-<sha8>` when the record names no story). It snapshots uncommitted and untracked files with no branch moved.
- **Then remove.** The local tag is enough to remove the worktree (marshal:AD-81 predicate (a)).
- **Push.** The tag is pushed through the core module's content gate, or reported as debt when it cannot be.
- **Failure.** A tag that cannot be written keeps the worktree, and the record is reported `branch_kept` with the reason.
- **Tarball.** The tarball keeps only git-ignored bytes and is reported as host-local; untracked files go into the snapshot.
- **Unchanged.** A worktree already on its source keeps its `.landed.txt` note.
- **Boundary.** Steward never imports `pyforge.marshal`.

Ledger key: `85-5-workspace-clean-parks-unlanded-commits-as-a-preserve-tag-before-removing-the-worktree`.
Type / Effort / Deps: feature / S / — (cross-project gate on marshal Story 87.3; minted `blocked`).

### Living CAP citations

- `spec-pyforge-steward` CAP-165 (FR-38) and CAP-157 as amended 2026-10-04 (review minor 8: CAP-157 owns branch deletion in clean); CAP-155. Flag `pyforge.steward.workspace_preserve_tag`, owner steward.

## Acceptance Criteria

- Given a recorded scratch worktree with commits not on its source, an uncommitted edit and an untracked file When `steward workspace clean` removes it with the flag on Then a local `preserve/<slug>/<N.M>/workspace-<sha8>` tag exists first, its tree holds the edit and the untracked file, the result names it, and no branch moved.
- Given no network, or a push the content gate refuses When `clean` runs Then the worktree is still removed on the local tag, and the result reports the tag as preserve debt.
- Given a tag that cannot be written (for example a read-only object store) When `clean` runs Then the worktree is kept and the record is reported `branch_kept` with the reason.
- Given a worktree whose commits are all on its source When `clean` runs Then the `.landed.txt` note path is unchanged and no tag is written.
- Given git-ignored files When the tarball is written Then it holds only those, and the result reports it as host-local.
- Given the flag off When `clean` runs Then today's behaviour holds; one test file runs both states.
- Given the station's source When the meta-tests run Then no module imports `pyforge.marshal`, and `test_no_station_assumes_local_recipes.py` stays green; removing the tag-before-remove rule fails a test (mutation).

## Boundaries & Constraints

**Always:** Tag before remove. Use the one grammar module. Real git and a bare remote in tests.

**Never:** Never import `pyforge.marshal`. Never delete an unmerged branch. Never keep a worktree only because a push failed.

</intent-contract>

## Binding

Parent: `spec-pyforge-steward` CAP-165 (FR-38), CAP-157 (amended 2026-10-04), CAP-155.
Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-04 (later) entry.
Research: drafts' Story 85.3, corrected by review B2 (a local tag suffices; push failure is debt) and minor 8.
Ledger key: `85-5-workspace-clean-parks-unlanded-commits-as-a-preserve-tag-before-removing-the-worktree`.
Ledger status at mint: `blocked` (cross-project gate: marshal Story 87.3 ships `pyforge.core.preserve_refs`; the operator flips it).
Deps: — (cross-project, see above).
Minted 2026-10-04 under the operator's ruling of the same day.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- The two-state flag test: `src/shared/packages/pyforge-steward/tests/unit/test_workspace_preserve_tag.py` — runs `pyforge.steward.workspace_preserve_tag` on and off.
- `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0.

## Spec Change Log

- No change yet.

## Review Triage Log

- No review has run yet.
