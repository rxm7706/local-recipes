---
title: "13.5: `workspace clean --delete` removes a gone or landed workspace without a prompt or an archive"
type: 'fix'
created: '2026-10-07'
status: 'done'
baseline_revision: '8ef4a6aa7950d8491852344209b60cdbc8765ac0'
review_loop_iteration: 0
followup_review_recommended: false
review_loop_iteration: 0
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-scratch-worktree-lifecycle/.memlog.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-13-1-workspace-verbs-over-git-worktree.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-68-1-a-workspace-archive-holds-the-work-not-the-environments-and-one-bad-record-never-stops-the-sweep.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-69-1-workspace-clean-keeps-a-note-not-a-tarball-for-a-worktree-already-on-its-source.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-70-1-steward-reads-the-workspace-source-and-branch-and-origin-main-by-their-full-refs.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py
  - docs/how-to/manage-worktrees-with-bmad.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `steward workspace clean` has no form a non-interactive caller can use to delete a workspace, and no
form at all that drops the record of a workspace that is already gone.

- **The dead rows.** Measured on 2026-10-07 (`b364823896`): 34 of the 38 rows in the primary checkout's
  `.steward/workspaces.yaml` name a worktree path and a branch that no longer exist; `scripts/worktree_sweep.py` and
  hand cleanup removed them. `steward workspace ls` reads only the bookkeeping (CAP-105), so it lists all 38 as open.
- **No verb removes them.** `clean <slug>` (no `--merged-only`) asks `archive workspace <slug>? [y/N]` only when stdin
  is a TTY (`_confirm_archive`, about :948); an agent's shell and the operator's `!` input are not, so the row is
  reported `declined` and kept. `clean --merged-only` runs `git merge-base --is-ancestor refs/heads/<branch> …` on a
  branch that no longer exists, which exits 128; CAP-155 then reports the row as `error: …`, keeps it and exits 1, so
  every fleet `clean --merged-only` now exits 1. Both reproduced against a temporary repository with one such record.
- **What removal leaves.** Where `clean` does remove a workspace, `_archive_worktree` (about :866) writes a
  `<slug>-<stamp>.landed.txt` note for a worktree git proves landed (CAP-157), a tarball for anything else (CAP-107,
  CAP-155), or a `.missing.txt` marker when the path is gone. The operator ruled on 2026-10-06 that an abandoned
  scratch workspace is deleted outright: no archive, no tarball, no preserve tag. Today the only way to drop a dead
  row is to hand-edit the gitignored bookkeeping file.

**Approach:** a new flag, `steward workspace clean [<slug>] --delete`, that never prompts and never archives.

- **What it deletes.** Per record:
  - worktree and branch both gone: the record is dropped;
  - worktree gone, branch on its source: the local branch is deleted and the record dropped;
  - worktree present and proven landed by CAP-157's proof (clean `status --porcelain` with untracked files shown and
    submodules not ignored; no skip-worktree or assume-unchanged entry; HEAD and the branch ancestors of the source;
    the source read as a remote-tracking ref; no gitlink or per-worktree ref; source and branch read by full ref,
    CAP-158): `git worktree remove`, the local branch deleted, the record dropped.
  - Nothing is written under `.steward/workspace-archive/`: no tarball, no `.landed.txt` note, no `.missing.txt`
    marker, and no tag.
- **What it refuses.** A worktree with a commit not on its source (`not-merged`), with an uncommitted edit, an
  untracked file or an index flag (`dirty`), or a gone worktree whose branch still exists off its source
  (`branch <b> not on <source>`): worktree, branch and record are all kept, and the row names the reason. A refusal
  is not an error (CAP-155's error rows stay for git failures).
- **Exit codes and output.** `clean <slug> --delete` that refuses exits 1 naming why; a fleet `clean --delete` exits
  0 unless a row errored, as today. Text output gains `deleted <slug>` lines; `--json` gains a `deleted` list beside
  `archived` and `skipped`.
- **Usage errors.** `--delete` with `--merged-only` (it already removes only proven-landed or gone workspaces), or
  with a repo-set feature slug, exits 2 naming why.
- **Unchanged.** `clean` and `clean --merged-only` without `--delete` behave exactly as today (archive-not-delete,
  the TTY prompt, the note, the tarball, CAP-155's kept error rows); `ls`, `status` and `start` are untouched.

Ledger key: `13-5-workspace-clean-delete-removes-a-gone-or-landed-workspace-without-a-prompt-or-an-archive`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-steward` CAP-107 (← spec-scratch-worktree-lifecycle CAP-4, `workspace clean`)
  and CAP-108 (← CAP-5, the bookkeeping record of the worktrees steward created). A record of a worktree that no
  longer exists, which no verb can remove, makes the bookkeeping and `ls` wrong; that is a defect of shipped
  behaviour, so this story mints no CAP.
- **Constraints kept.** CAP-155 (a record the sweep cannot decide is kept; git failures are error rows), CAP-157 (the
  landed proof, reused unchanged), CAP-158 (full refs). Archive-not-delete still governs every path but `--delete`,
  and `--delete` removes only what git proves landed or what is already gone, so no unlanded commit or file is lost.
- **Operator ruling.** 2026-10-06: an abandoned scratch workspace is deleted, not archived or preserved.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag.

## Acceptance Criteria

- Given no TTY on stdin and a record whose worktree and branch are gone When `steward workspace clean <slug> --delete`
  runs Then the record is gone from the bookkeeping, the command exits 0, and `.steward/workspace-archive/` gained no
  file.
- Given a clean worktree whose HEAD and branch are on `origin/main` When `clean <slug> --delete` runs Then the
  worktree directory, the local branch and the record are gone, no file was written to the archive dir, and no tag
  exists.
- Given a worktree with a commit not on its source When `clean <slug> --delete` runs Then worktree, branch and record
  are kept, and the command exits 1 naming `not-merged`.
- Given a worktree with an uncommitted edit, or an untracked file (also with `status.showUntrackedFiles=no`), or a
  skip-worktree entry When `clean <slug> --delete` runs Then all three are kept and the command exits 1 naming `dirty`.
- Given a gone worktree whose branch exists and is not on its source When `clean <slug> --delete` runs Then the branch
  and the record are kept and the command exits 1 naming the branch; when the branch is on its source, the branch and
  the record are removed.
- Given a fleet of all five cases When `clean --delete` runs Then the removable ones are reported `deleted`, the others
  `skipped` with their reasons, and the command exits 0; `--json` lists both.
- Given `clean --delete --merged-only`, or `clean <repo-set feature> --delete` When it runs Then it exits 2 naming
  why, and nothing changes.
- Given `clean` and `clean --merged-only` without `--delete` When they run over the same fixtures Then every result
  matches `b364823896`'s (the existing workspace tests stay green unchanged).
- Given the refusal of an unmerged or dirty worktree removed When the new tests run Then they fail (mutation).

## Boundaries & Constraints

**Always:**
- Reuse CAP-157's proof and CAP-158's full-ref reads; never write a second proof.
- Save the bookkeeping in the existing `finally` path, so an interrupt loses no record (CAP-155).
- Real git in the tests, with worktrees under a temporary root and a stdin that is not a TTY.
- Update the one sentence in `docs/how-to/manage-worktrees-with-bmad.md` that says steward's scratch worktrees are
  archived, to name `--delete`; record it on `spec-pyforge-doctor/.memlog.md` (that file's governing Spec) and the
  steward paths on `spec-pyforge-steward/.memlog.md` and `spec-pyforge-core/.memlog.md` (`workspace.py`'s
  co-governor), scoped stamps only (AGENTS.md pre-PR item 5).

**Never:**
- Never delete an unmerged branch, a dirty worktree, or anything git cannot prove landed.
- Never write a tarball, a note, a marker or a tag under `--delete`.
- Never change the default `clean`, `--merged-only`, `ls`, `status` or `start`.
- Never touch the unlanded-worktree path Story 85.5 owns (behind `pyforge.steward.workspace_preserve_tag`).
- Never weaken or delete an existing test.

## I/O & Edge-Case Matrix

| Record | `clean --delete` | Exit (slug form) |
|---|---|---|
| worktree and branch gone | record dropped | 0 |
| worktree gone, branch on source | branch deleted, record dropped | 0 |
| worktree gone, branch off source | kept: `branch <b> not on <source>` | 1 |
| clean worktree, HEAD and branch on source | worktree removed, branch deleted, record dropped | 0 |
| commit not on source | kept: `not-merged` | 1 |
| uncommitted edit, untracked file, index flag | kept: `dirty` | 1 |
| git fails reading the record | kept: `error: …` (CAP-155) | 1 |
| with `--merged-only`, or a repo-set feature | usage error, nothing changes | 2 |

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-07 (tooling gaps) entry.
- Epic: Epic 13 (it decomposes `spec-scratch-worktree-lifecycle`, CAP-107 and CAP-108 here); a fix joins its own epic,
  which reopens (doctor Story 41.5).
- Ledger key: `13-5-workspace-clean-delete-removes-a-gone-or-landed-workspace-without-a-prompt-or-an-archive`.
- Ledger status at mint: `backlog`.
- Deps: —.
- Spec: `spec-pyforge-steward/.memlog.md` records the mint; no contract change, `SPEC.md` untouched.
- Story 85.5 (`blocked`) changes how `clean` treats an unlanded worktree; this story refuses one and leaves that path
  alone.
- Minted 2026-10-07 with Stories 63.7 and 85.6, in one chain commit. Epic 13's `[epic_surfaces]` entry gains
  `docs/how-to/manage-worktrees-with-bmad.md` and every Spec memlog.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks (not a dispatch gate):**
- Operator, after landing (it changes the operator's own bookkeeping and removes any landed workspace, so a dispatched
  session never runs it): on the primary checkout, `pixi run -e pyforge-guild pyforge steward workspace clean
  --delete` — expected: the rows whose worktree and branch are gone are reported `deleted`, every open workspace is
  kept or deleted by its proof, exit 0; `pyforge steward workspace ls` then lists only open workspaces.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- Mutation: delete an unmerged worktree under `--delete` and re-run the new tests; they fail. Restore it.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Spec Change Log

- No change yet.

## Review Triage Log

### 2026-10-07 — Review pass
- verdicts: 3 findings — high 0, medium 0, low 0, false 2, maybe-false 1
- findings:
  - `[false]` `[reject]` Lazy `EXIT_USAGE` import in `WorkspaceDuty.run` risks circular import — verified: import runs only after `cli` finished loading `workspace`; no cycle at runtime.
  - `[false]` `[reject]` `--delete` fleet exit should fail on refusals — verified against spec: fleet exits 0 on refusals; slug-targeted form exits 1; tests assert both.
  - `[maybe-false]` `[reject]` Repo-set `--delete` usage error when slug is unknown — not exercised without monkeypatch; duty checks `slug in load_repo_sets()` before clean; rejected as unverified low harm.

## Auto Run Result

Status: done

Summary: Added `steward workspace clean [--delete]` to drop gone or CAP-157-proven-landed workspaces without TTY prompt, archive artifacts, or tags; refusals keep worktree/branch/record with named reasons.

Files changed:
- `src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py` — `_delete_eligibility`, `_execute_delete`, `clean_workspaces(delete=)`, `format_clean` `deleted` list, duty exit rules
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` — `--delete` flag
- `src/shared/packages/pyforge-steward/tests/unit/test_workspace_clean_delete.py` — Story 13.5 matrix + mutation guard
- `src/shared/packages/pyforge-steward/tests/unit/test_workspace_edges.py` — `format_clean` JSON includes `deleted`
- `docs/how-to/manage-worktrees-with-bmad.md` — document `--delete`
- Memlogs: `spec-pyforge-steward`, `spec-pyforge-core` (marshal project), `spec-pyforge-doctor`

Review: 0 patches applied; 3 findings rejected after verification.

Follow-up review recommended: false

Verification:
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — pass (2044 tests)
- `python scripts/spec_surface_reconcile.py` — exit 0

Residual risk: merged branch with Tier-3 ignored non-symlink work refuses with `not-merged` when landed proof fails (same safety posture as archive path).
