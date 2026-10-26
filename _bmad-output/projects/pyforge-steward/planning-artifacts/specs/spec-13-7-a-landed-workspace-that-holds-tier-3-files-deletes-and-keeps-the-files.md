---
title: '13.7: A landed workspace that holds Tier-3 files deletes, and keeps the files'
type: 'fix'
created: '2026-10-25'
status: 'ready-for-dev'
baseline_revision: 'fd06415e4d1e1e3446ad6463f9e1149630d3311a'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-13-5-workspace-clean-delete-removes-a-gone-or-landed-workspace-without-a-prompt-or-an-archive.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-13-6-a-workspace-started-from-another-branch-is-landed-once-its-branch-is-on-main.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py
  - src/shared/packages/pyforge-steward/tests/unit/test_workspace_clean_delete.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `steward workspace clean <slug> --delete` skips a landed workspace as `not-merged` while `status` reads it
`merged`. Line numbers are at `fd06415e4d`, in `src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py`.

- Observed 2026-10-25 on `chain-steward-retro-fixes` (Stories 71.14 and 99.8, #2318): tip `b89f2bb1e0` merged as
  `fd06415e4d`, tree clean, `status` printed `clean ahead=0 behind=1 merged`, `clean --delete` printed
  `skipped chain-steward-retro-fixes (not-merged)`.
- `status_of` (`:690`) and `_delete_eligibility`'s first landing check (`:1471`) both ask `_branch_landed`, and both
  answer yes. `_delete_eligibility` then asks CAP-157's proof, `_landed_note_body` (`:1473`), and reports every way it
  fails as `not-merged`.
- The proof refuses a real (not symlinked) git-ignored path under `_bmad-output/` (`:1296`-`:1299`). The worktree held
  `_bmad-output/projects/pyforge-steward/implementation-artifacts/runs/<run-id>/journal.jsonl`, which
  `marshal dispatch_land_finalize` wrote after the merge. A steward workspace has no `implementation-artifacts` backlink
  (`start_workspace` runs only `git worktree add`), so the journal made a real directory in the worktree instead of
  going to the main checkout's shared Tier-3 store.
- Not the cause, measured in a scratch repository: the worktree's `.pixi/envs/` (ignored, not under `_bmad-output/`)
  and its `origin/main` ref.

**Approach:**
- Split the proof's checks out of `_landed_note_body` into one helper that returns either why there is no proof or
  what the proof found: HEAD, the landing ref and its sha, the ignored listing, and the Tier-3 paths (real ignored
  entries under `_bmad-output/`). `_landed_note_body` keeps its answer: no note when any Tier-3 path exists.
- `_delete_eligibility` returns that helper's reason, so each refusal names its cause (`dirty`, a submodule, a
  per-worktree ref, an unreadable HEAD, a failed listing; `not-merged` only for a HEAD or branch on no landing ref).
  When the only thing in the way is Tier-3 files, it checks that each file (every non-directory entry under each
  Tier-3 path) can move to the same relative path in the main checkout: the main checkout is the parent of
  `git rev-parse --git-common-dir` when that directory is named `.git`, is not the worktree itself, and no file exists
  there at that path (`lexists`), and the destination does not resolve inside the worktree. Any failure is a skip
  reason naming the file.
- `_execute_delete` re-reads the Tier-3 files, re-checks the same conditions, moves each file (its directories created
  as needed), then removes the worktree and the branch as before. The deleted row gains `tier3_moved_to` (the main
  checkout) and the count of files moved; `format_clean` prints them.
- A fix under CAP-107 and CAP-157: no CAP, no amendment, no flag. CAP-157's proof for the `.landed.txt` note, the default
  `clean`, `--merged-only`, `status`, `ls`, `start_workspace` and marshal's landing step do not change.

Ledger key: `13-7-a-landed-workspace-that-holds-tier-3-files-deletes-and-keeps-the-files`. Type / Effort / Deps:
fix / S / S-13.6.

## Acceptance Criteria

- **AC1 — The landed workspace deletes, and the file is kept.** A scratch repository with a bare origin, a workspace
  off `origin/main` with one commit merged into `main` and pushed, and an ignored
  `_bmad-output/projects/demo/implementation-artifacts/runs/r1/journal.jsonl` in its worktree: `status` reads it
  merged; `clean <slug> --delete` reports it deleted with `tier3_moved_to` the main checkout and one file moved; the
  journal is at the same path in the main checkout with the same bytes; the worktree, the branch and the record are
  gone; no tarball, note or tag is written. The test fails at `fd06415e4d`.
- **AC2 — Nothing is overwritten.** The same workspace when the main checkout already has a file at that path: the
  workspace is skipped with a reason naming the path, the main checkout's file is unchanged, and the worktree, its
  file, the branch and the record stay.
- **AC3 — No main checkout, no move.** When the main checkout cannot be found (a common directory not named `.git`),
  the workspace is skipped with a reason naming the Tier-3 path, and nothing moves.
- **AC4 — Each refusal says why.** A landed workspace with a per-worktree ref is skipped with a reason that names
  per-worktree refs, not `not-merged`; the 13.5 cases keep their reasons (`not-merged` for a commit not on its source,
  `dirty`, `branch <b> not on <source>`).
- **AC5 — Nothing else moves.** The `.landed.txt` note is still refused for a worktree with Tier-3 files (the default
  `clean` archives it as before); the 13.1-13.6, 68.1, 69.1, 70.1 and 85.5 workspace tests pass;
  `pixi run --frozen -e pyforge-steward pyforge-steward-test` passes.

## Boundaries & Constraints

**Never:** overwrite or merge into a file that exists in the main checkout; delete a Tier-3 file; move anything for the
default `clean` or `--merged-only`; change `start_workspace`, marshal's landing step or CAP-157's note proof; add a flag.

</intent-contract>

## Binding

- Parent capabilities: `spec-pyforge-steward` CAP-107 and CAP-157. No CAP is minted or amended.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, 2026-10-25 (a landed workspace that holds a run journal
  never deletes).
- Epic 13 (done; reopened by this story under doctor Story 41.5's rule). Ledger key above. Deps: S-13.6.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_workspace_delete_tier3.py`
  — expected: pass; at `fd06415e4d`'s `workspace.py`, AC1 and AC4 fail.
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0, read from a file (with
  `TMPDIR` on the repository's filesystem).

## Spec Change Log

- 2026-10-25: drafted from the Dream entry of 2026-10-25, found while cleaning up #2318's landing workspace.
