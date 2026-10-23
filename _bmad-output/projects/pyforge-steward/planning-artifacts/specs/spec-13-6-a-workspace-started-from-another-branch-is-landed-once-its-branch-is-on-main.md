---
title: '13.6: A workspace started from another branch is landed once its branch is on main'
type: 'fix'
created: '2026-10-23'
status: 'in-progress'
baseline_revision: 'bdb49ec39f'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-13-5-workspace-clean-delete-removes-a-gone-or-landed-workspace-without-a-prompt-or-an-archive.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py
  - src/shared/packages/pyforge-steward/tests/unit/test_workspace_clean_delete.py
  - src/shared/packages/pyforge-steward/tests/unit/test_workspace_full_refs.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** a workspace started `--from` another branch is never judged landed, so `status` and `clean` refuse it
after its work is on `main`. Found while cleaning up Story 71.13's workspace, started `--from
claude/zealous-booth-19783d` (Story 71.12's branch). Its branch merged to `main` as `bdb49ec39f`, yet `status` read it
`unmerged ahead=18`, and `clean <slug> --delete` skipped it `not-merged`. The operator removed it by hand with
`git worktree remove`.

Read at `bdb49ec39f` in `src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py`:

- **Every landing check reads only the recorded source.** Each one asks `merge-base --is-ancestor <branch> <source>`:
  - `status_of`'s merged flag (`:687`);
  - `clean --merged-only` (`:1263`);
  - `--delete`'s eligibility (`:1168`, `:1179`) and its branch removal (`:1198`);
  - the preserve-tag check (`:1063`);
  - the archive's branch removal (`:1123`-`:1132`).
- **A stacked source stops moving.** A stacked workspace's source is a local branch. It never moves once the work
  lands, so the branch is never an ancestor of it.
- **CAP-157's landed proof needs a remote source.** `_landed_note_body` (`:989`-`:1000`) asks `_source_commit`
  (`:788`) for the source's commit, which answers only for a source under `refs/remotes/` (`:797`). A local source
  proves nothing.

**Measured at `bdb49ec39f`** in a scratch repository with a bare origin:
- Setup: a `base` workspace off `origin/main` with one commit; a `stacked` one `--from base` with another; `stacked`
  merged into `main` and pushed.
- `status` read `merged=False`; `clean --delete` skipped `stacked` as `not-merged`; `clean --merged-only` skipped it
  too.

**Approach:** one helper names a record's landing refs: its recorded source and, when that is not the trunk,
`origin/main` read as `refs/remotes/origin/main` (CAP-158).
- **Merge checks.** Every check passes when the branch is an ancestor of either ref. The source is asked first,
  with today's errors. A trunk git cannot resolve answers "not landed there" and never turns the source's answer
  into an error, so a repo-set member with no `origin/main` gets today's verdict.
- **The landed proof.** It takes the first landing ref that resolves under `refs/remotes/` and holds HEAD and the
  branch. The note names that ref and its sha, and adds the recorded source when the two differ.
- **`ahead`/`behind`** still read the recorded source.

### Living CAP citations

- **Shipped behaviour, amended.** `spec-pyforge-steward` CAP-157 is amended in place (memlog decision 2026-10-23).
  The amended text says a workspace's landing refs are its source and the trunk, and that a workspace started `--from`
  a local branch whose branch lands on `origin/main` reads merged, leaves a note, and is dropped by `--delete`.
  `SPEC.md` was re-rendered by a scratchpad script that asserts each anchor once; the operator approved that route in
  chat on 2026-10-23.
- **Unchanged.** CAP-106 (`status`), CAP-107 (`clean --merged-only`), CAP-108 (own worktrees only), CAP-155 (archive,
  never the environments), CAP-158 (full refs) and Story 13.5's `--delete` contract all stay as written. They now read
  "the source" through the landing refs.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag.
- **Deps.** S-13.5, which is `done`.
- **Epic.** Epic 13 is `done`. This backlog story reopens it (`epic-13` moves to `in-progress`), which
  `ledger-regression`'s `epic_reopened_by_new_story` admits when the new story arrives in the same change.

## Acceptance Criteria

In a scratch repository with a bare origin: a `base` workspace off `origin/main` with one commit, then a `stacked`
workspace `--from base` with another.

- **(1) `status` reads a landed stacked workspace merged.** Given `stacked` merged into `main` and pushed, `status`
  reports `source: base` and `merged: true`.
- **(2) `clean --delete` drops it.** Given the same, `clean stacked --delete`:
  - reports it under `deleted`, with nothing skipped;
  - removes its worktree, its local branch and its record, and leaves `base`'s record;
  - writes no archive, note or tag.
- **(3) `clean --merged-only` leaves a note.** Given the same, `clean stacked --merged-only`:
  - archives it as a `.landed.txt` note, not a tarball, and reports no `branch_kept`;
  - writes a note that reads `on source: origin/main at <sha>` and names the recorded source;
  - removes the worktree and deletes the branch.
- **(4) An unlanded stacked workspace is still refused.** Given `stacked` not merged anywhere:
  - `status` reports `merged: false`;
  - `clean stacked --delete` skips it `not-merged` and keeps its worktree and branch.
- **(5) The fix is what makes them pass.** (1)-(3) fail on `bdb49ec39f`, and (4) passes there.
- **(6) Nothing else moves.** The 13.1-13.5, 68.1, 69.1, 70.1 and 85.5 workspace tests pass unchanged, and
  `pixi run --frozen -e pyforge-steward pyforge-steward-test` is green.

## Boundaries & Constraints

**Always:**
- Change only `src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py` and its unit tests under
  `src/shared/packages/pyforge-steward/tests/unit/`.
- Read the trunk by its full ref (`refs/remotes/origin/main`, CAP-158).
- Keep every other condition of CAP-157's proof: a clean tree, no hidden index entry, no gitlink, no per-worktree
  ref, and no Tier-3 work.

**Never:**
- Never let the trunk check raise where the source check would not have raised.
- Never judge a branch landed on a local ref named like the trunk.
- Never change `ahead`/`behind`, the bookkeeping format, the exit codes or the CLI flags.
- Never hand-edit `sprint-status-ledger.yaml`, and never edit `SPEC.md` except by the approved render script.

**At landing:** `workspace.py` and the new test are in `spec-pyforge-steward`'s surface; `spec-surface-check` names
any co-governor. Append the reconcile to each Spec it names, then one scoped stamp each. Promote the story to `done`
before the merge.

## I/O & Edge-Case Matrix

| Workspace | Today (`bdb49ec39f`) | After |
|---|---|---|
| started from `origin/main`, branch on main | landed | unchanged |
| started `--from` a local branch, branch on main | `unmerged`; `--delete` and `--merged-only` skip; the default `clean` tars it and keeps the branch | landed: note, branch deleted, `--delete` drops it |
| started `--from` a local branch, branch only on that source | merged; `--delete` refuses (no remote proof); the default `clean` tars it | unchanged |
| started `--from` a local branch, branch on neither | `not-merged` | unchanged |
| repository with no `origin/main` (repo-set member) | verdict from its source | unchanged (the trunk answers "not landed there") |
| source branch since deleted, branch on main | error row (source unresolvable) | landed (the trunk proves it) |

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-23 (a stacked workspace never reads
  landed) entry.
- Epic: Epic 13 (`spec-scratch-worktree-lifecycle`, absorbed into `spec-pyforge-steward`). It was `done`; this story
  reopens it to `in-progress`.
- Ledger key: `13-6-a-workspace-started-from-another-branch-is-landed-once-its-branch-is-on-main`.
- Ledger status at mint: `backlog`.
- Deps: S-13.5 (`done`).
- Spec: `spec-pyforge-steward/.memlog.md` records the decision; `SPEC.md`'s CAP-157 is re-rendered.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass.
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0, read from a file (with
  `TMPDIR` on the repository's filesystem when `/tmp` is tmpfs).

**Manual checks (not a dispatch gate):**
- `src/shared/packages/pyforge-steward/tests/unit/test_workspace_stacked_landing.py` against `workspace.py` at
  `bdb49ec39f`: expected (1)-(3) red, (4) green.

## Spec Change Log

- No change yet.
