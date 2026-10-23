---
title: '13.6: A workspace started from another branch is landed once its branch is on main'
type: 'fix'
created: '2026-10-23'
status: 'in-review'
baseline_revision: 'bdb49ec39f'
review_loop_iteration: 2
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
- **By commit, never by name** *(reviews 1 and 2)*. An `origin/<b>` or `refs/remotes/<r>/<b>` source and the trunk
  are compared by the commit their remote-tracking ref names. `_source_commit` looks the full refname up exactly with
  `show-ref --verify`. Passed by name, a missing `refs/remotes/origin/main` let git read a local
  `refs/heads/refs/remotes/origin/main` and prove an unlanded branch merged. When both refs exist, `rev-parse` only
  reported ambiguity, so a real landing read as unresolvable.
- **HEAD too** *(review 1)*. `--merged-only` and the preserve-tag check also require the worktree's HEAD to be
  landed, so commits on a detached HEAD past a landed branch are skipped or parked, never left on no ref. A HEAD
  git cannot read (unborn, a broken gitdir) names no commit to lose, so the branch's verdict stands, as before.
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
- **(5) A deleted source and a missing trunk.** Given `stacked` landed and `base`'s worktree and branch then
  removed, `clean stacked --delete` drops it, while `status` still reports the row unreachable. Given `stacked` not
  landed and `refs/remotes/origin/main` removed, `status` reports `merged: false` with no error, and `--delete`
  skips it `not-merged`.
- **(6) A shadow, a detached HEAD, and the other paths** *(review 1)*.
  - **Shadow.** With `refs/remotes/origin/main` deleted and a local `refs/heads/refs/remotes/origin/main` at the
    unlanded `stacked` tip:
    - `status` reports `merged: false`;
    - `--merged-only` and `--delete` skip it as `not-merged`;
    - the default `clean` writes a tarball and keeps the branch.
    For a workspace started from `origin/main`, the same shadow is an error row, never a landing.
  - **Detached HEAD.** `stacked` landed, with its worktree on a detached HEAD carrying one more commit:
    - `--merged-only` skips it as `not-merged`;
    - with the preserve flag on, the default `clean` parks that commit as a preserve tag.
  - **Gone worktree.** A landed `stacked` branch whose worktree is gone is dropped by `--delete`. One on neither ref
    is refused with `branch stacked not on base or origin/main`.
  - **Remote non-trunk source.** A workspace started from `origin/base` that landed on `main` leaves a note naming
    `origin/main` and `recorded source: origin/base`.
  - **Unresolvable source.** A source git cannot resolve, with a commit not on `main`, still archives a tarball and
    keeps the branch.
  - **Review 2.** These cases are pinned:
    - a short-name shadow (`refs/heads/origin/main`) and a pruned `origin/base` shadowed by
      `refs/heads/refs/remotes/origin/base` are never landings;
    - neither is a source recorded as the full ref `refs/remotes/origin/main` with its remote ref gone;
    - a trunk shadowed while present still proves a landing;
    - `--merged-only` cleans a landed branch whose worktree is gone;
    - an unborn HEAD leaves the branch verdict as before.
- **(7) The fix is what makes them pass.** (1)-(3) and (5)'s deleted-source case fail on `bdb49ec39f`; (4) and (5)'s
  missing-trunk case pass there.
- **(8) Nothing else moves.** The 13.1-13.5, 68.1, 69.1, 70.1 and 85.5 workspace tests pass, and
  `pixi run --frozen -e pyforge-steward pyforge-steward-test` is green. One of them changes its setup and keeps its
  meaning: `test_a_worktree_whose_source_git_cannot_resolve_still_archives` also removes `refs/remotes/origin/main`.
  Its worktree sits on the trunk, so with the trunk in place git can prove it landed, and the note is the right answer
  (CAP-157's success clause now says "unless the trunk proves the worktree landed").

## Boundaries & Constraints

**Always:**
- Change only `src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py` and its unit tests under
  `src/shared/packages/pyforge-steward/tests/unit/`.
- Read the trunk by its full ref (`refs/remotes/origin/main`, CAP-158).
- Keep every other condition of CAP-157's proof: a clean tree, no hidden index entry, no gitlink, no per-worktree
  ref, and no Tier-3 work.

**Never:**
- Never let the trunk check raise where the source check would not have raised.
- Never judge a branch landed on a local ref named like the trunk, or like an `origin/<b>` source.
- Never remove a worktree under `--merged-only`, or skip its preserve tag, while its HEAD holds commits on neither
  landing ref.
- Never change `ahead`/`behind`, the bookkeeping format, the exit codes or the CLI flags.
- Never hand-edit `sprint-status-ledger.yaml`, and never edit `SPEC.md` except by the approved render script.

**At landing:** `workspace.py` and the new test are in `spec-pyforge-steward`'s surface; `spec-surface-check` names
any co-governor. Append the reconcile to each Spec it names, then one scoped stamp each. Promote the story to `done`
before the merge.

## I/O & Edge-Case Matrix

| Workspace | Today (`bdb49ec39f`) | After |
|---|---|---|
| started from `origin/main`, branch on main | landed | unchanged |
| source git cannot resolve, worktree on main | tarball (no proof) | note (the trunk proves it) |
| source git cannot resolve, no trunk either | tarball (no proof) | unchanged |
| local `refs/heads/refs/remotes/origin/main` shadows a missing trunk | `origin/main`-sourced: read as landed | never a landing (an error row for an `origin/main` source) |
| HEAD git cannot read (unborn, broken gitdir), branch landed | `--merged-only` cleans it | unchanged |
| both `refs/remotes/origin/main` and a local `refs/heads/refs/remotes/origin/main` | landed by the remote ref | unchanged (looked up exactly) |
| source recorded as `refs/remotes/origin/main`, remote ref gone, local ref of that full name | read as landed | never a landing |
| detached HEAD with commits past a landed branch | trunk-sourced: `--merged-only` removed it, no preserve tag | skipped `not-merged`; parked as a preserve tag when the flag is on |
| started `--from` a local branch, branch on main | `unmerged`; `--delete` and `--merged-only` skip; the default `clean` tars it and keeps the branch | landed: note, branch deleted, `--delete` drops it |
| started `--from` a local branch, branch only on that source | merged; `--delete` refuses (no remote proof); the default `clean` tars it | unchanged |
| started `--from` a local branch, branch on neither | `not-merged` | unchanged |
| repository with no `origin/main` (repo-set member) | verdict from its source | unchanged (the trunk answers "not landed there") |
| source branch since deleted, branch on main | `status` and `clean` report an error row (source unresolvable) | `clean` judges it landed (the trunk proves it); `status` still reports the row unreachable, since `ahead`/`behind` need the source |

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

- 2026-10-23, after review 1: the Approach gains "by commit, never by name" and "HEAD too"; AC (6) is new; the
  matrix gains the shadow and detached-HEAD rows; the Never clause covers both; CAP-157's text says "the first that
  holds both".
- 2026-10-23, during implementation: an unresolvable source no longer forces a tarball when the trunk proves the
  worktree landed (AC (7), the matrix, CAP-157's success clause); the deleted-source case is AC (5). `status` of a
  record whose source is gone still reports the row unreachable.

## Review Triage Log

### 2026-10-23 — Review pass 1 (FAIL: one must-fix, four should-fix, four nits)

1. **must-fix, fixed.** The trunk, passed to `merge-base` by name, fell through to a local
   `refs/heads/refs/remotes/origin/main` when the remote ref was missing. The reviewer reproduced this with steward's
   own `start refs/remotes/origin/main`: `status` read the branch merged, `--merged-only` tarred the worktree and
   deleted the branch, and the commit was left on no ref. The same hole was already there for `origin/main`-sourced
   records. `_rev_merged_into` now compares any `origin/<b>` target by the commit `_source_commit` reads under
   `refs/remotes/`. The new shadow tests pin `status`, `--merged-only`, `--delete` and the default `clean`'s proof.
2. **should-fix, fixed.** A detached HEAD with commits past a landed branch was removed by `--merged-only` with no
   preserve tag. `_worktree_head_landed` now joins the branch in both checks.
3. **should-fix, fixed.** CAP-157's text said "the first landing ref that resolves". The code takes the first one
   that resolves and holds HEAD and the branch, so the text was re-rendered to match, and a remote non-trunk source
   test pins it.
4. **should-fix, fixed.** Story 13.6's And clause in `epics.md` (one old test adjusted; four landed tests red at the
   baseline).
5. **should-fix, fixed** except one. New tests pin:
   - the note's `recorded source:` line;
   - `--delete`'s gone-worktree path;
   - the proof's remote-only rule for the trunk.
   A preserve check that goes source-only parks more than it needs (an extra tag, the host-local tarball, the tag
   pushed through the content gate). It loses no data, so it is not pinned.
6. **nit, fixed.** The `_landed_note_text` docstring and `--delete`'s gone-worktree refusal.
7. **nit, fixed.** An unresolvable source with a commit not on `main` still archives a tarball.
8. **nit, fixed.** The PRD's 2026-10-23 bullet names FR-38's preserve rule.
9. **nit, recorded.** A stale trunk proves more only if `main` is force-pushed backwards, which the protected-refs
   rulesets forbid here. This is pre-existing.

### 2026-10-23 — Review pass 2 (FAIL: three should-fix, three nits; every round-1 must-fix and should-fix resolved)

1. **should-fix, fixed.** A source recorded as the full ref `refs/remotes/origin/main` was still passed by name. When
   its remote ref was missing, a local branch of that full name proved an unlanded commit merged, and `--merged-only`
   deleted the branch. This was pre-existing. `_rev_merged_into` now reads `refs/remotes/` targets by commit too.
2. **should-fix, fixed.** With both the remote-tracking ref and a local ref of the same full name present,
   `rev-parse --symbolic-full-name` printed only "ambiguous" and exited 0, so a real landing read as unresolvable.
   `_source_commit` now looks the full refname up exactly (`show-ref --verify --hash`).
3. **should-fix, fixed.** The non-trunk `origin/<b>` shadow is pinned. The mutant `into == _DEFAULT_FROM` now fails.
4. **nit, fixed.** A HEAD git cannot read now leaves the branch's verdict as before, where it used to block a landed
   workspace. An unborn HEAD is pinned.
5. **nit, fixed.** A short-name shadow (`refs/heads/origin/main`) and `--merged-only` on a gone worktree whose branch
   landed are pinned. The mutants m3 and mH now fail, as do mG and a proof that reads the trunk by name.
6. **nit, fixed.** The source-only preserve check is worded as "parks more than it needs", not "only writes an
   extra tag".

