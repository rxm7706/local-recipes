---
title: '13.6: A workspace started from another branch is landed once its branch is on main'
type: 'fix'
created: '2026-10-23'
status: 'done'
baseline_revision: 'bdb49ec39f'
review_loop_iteration: 14
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-13-5-workspace-clean-delete-removes-a-gone-or-landed-workspace-without-a-prompt-or-an-archive.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py
  - src/shared/packages/pyforge-steward/tests/unit/test_workspace_clean_delete.py
  - src/shared/packages/pyforge-steward/tests/unit/test_workspace_full_refs.py
deferred:
  - summary: >-
      A workspace directory deleted by hand whose recorded HEAD is detached at commits no ref holds loses them when
      its own record is cleaned (the default clean writes .missing.txt and unregisters it), as at the baseline.
    evidence: |-
      Out of Story 13.6's scope by the operator's ruling of 2026-10-23, after six review rounds found the protection
      for this case leaking. Since review 8 every clean unregisters only its own worktree, so a kept sibling is no
      longer pruned by another clean; the record's own clean still drops its commits. A fix story (ref-contains
      check, keep or preserve-tag the recorded HEAD) is proposed.
    location: >-
      src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py
    severity: medium
  - summary: >-
      A present worktree whose branch is landed loses a commit only its refs/worktree/* or refs/bisect/* ref holds
      when clean --merged-only removes it, as at the baseline (CAP-157's proof refuses the note, but the tarball keeps
      files, not history).
    evidence: |-
      Found at Story 13.6's eighth review (pre-existing: the baseline does the same to a source-landed worktree); out
      of 13.6's scope by the operator's ruling of 2026-10-23, beside DW-steward-13-6.
    location: >-
      src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py
    severity: low
  - summary: >-
      clean --delete of a present, locked worktree whose branch is landed reports an error row (git refuses to
      remove a locked worktree) rather than a named locked refusal, so a fleet --delete exits non-zero; the baseline
      does the same for a source-landed one, and the trunk now makes stacked workspaces reach it.
    evidence: |-
      Found at Story 13.6's final review (round 10). Not a loss: the worktree, its branch and its record stay.
      Deferred by the operator's ruling of 2026-10-23 (land 13.6 once no must-fix regression remains).
    location: >-
      src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py
    severity: low
  - summary: >-
      Story 13.6's final verification left four non-must-fix items: clean --merged-only refuses (not-merged) a
      present workspace git no longer lists when its HEAD cannot be read (non-UTF-8 repository path, or a directory
      the user cannot enter) where the baseline archived it or gave an error row, so one CLI case exits 0 instead of 1;
      the broadened per-record catch and the OSError guard in _worktree_head_landed have no pin of their own (a
      --delete sweep over a workspace the user cannot enter would pin the catch); status still raises PermissionError
      for such a directory, as at the baseline; and DW-steward-13-6 does not name the non-UTF-8 default-clean case.
    evidence: |-
      Round 14 verification (PASS, no must-fix against bdb49ec39f): a refusal keeps the record and loses nothing.
      Fault injection over 3,628 sweeps found no lost commit, branch or record.
    location: >-
      src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py
    severity: low
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
  `show-ref --verify`: `origin/<b>` always, any configured remote that prefixes the source up to a `/`, and
  `remotes/...` (reviews 3 to 5). Passed by name, a missing `refs/remotes/origin/main` let git read a local
  `refs/heads/refs/remotes/origin/main` and prove an unlanded branch merged. When both refs exist, `rev-parse` only
  reported ambiguity, so a real landing read as unresolvable.
- **HEAD too** *(review 1)*. `--merged-only` and the preserve-tag check also require the worktree's HEAD to be
  landed, so commits on a detached HEAD past a landed branch are skipped or parked, never left on no ref. HEAD is
  read as the repository records it (`worktree list --porcelain`), so a broken `.git` link still names its commit; an
  unborn HEAD (forty zeros with a branch line) names none; any other HEAD git cannot read, and a listing git cannot
  give, count as not landed (reviews 3 and 4).
- **Out of scope: a directory deleted by hand** *(operator ruling, 2026-10-23, after review 6; refined at
  review 7)*. Rounds 3-5 added protection for it, and each review found it still leaking: a bare `worktree prune`
  from any other clean dropped its record, and a HEAD another ref held was kept forever. That protection is gone.
  The trunk still must never lose what the baseline kept, so a gone directory lands on its source as before, and
  lands on the trunk only when the HEAD git still records for it is landed too (`_gone_branch_landed`). Otherwise it
  gets the baseline's answer, including the source's error. It also must hold no `refs/worktree/*` or
  `refs/bisect/*` ref, which unregistering would delete (review 8). Every clean unregisters only its own worktree
  (`worktree remove --force`), and a locked registration stays (review 9). The rest of the loss is the deferred
  items above.
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
  - **Review 3.** These cases are pinned:
    - a broken `.git` link still names a detached HEAD, so `--merged-only` skips;
    - a detached HEAD past a landed branch whose source is gone is kept;
    - a local full-ref source (`refs/heads/base`) proves nothing;
    - an `upstream/main` landing still proves it;
    - a workspace named like its remote source is never compared with itself;
    - a short-name `origin/base` shadow is never a landing;
    - a revision source is read as `refs/remotes/<b>~N`, as at the baseline.
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
- Never remove a present worktree under `--merged-only`, or skip its preserve tag when the flag is on, while its HEAD
  holds commits no ref keeps. Two cases are out of this story's scope, both as at the baseline:
  - the default `clean` with the preserve flag off still tars and removes a present worktree (CAP-155);
  - a directory deleted by hand lands through the trunk only when the HEAD git records for it is landed and it holds no
    per-worktree ref; otherwise it gets the baseline's verdict. Its own clean still loses a detached commit, as at
    the baseline (`DW-steward-13-6`). Every clean unregisters only its own worktree, never a sibling (review 8).
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
| unborn HEAD, branch landed | `--merged-only` cleans it | unchanged |
| broken `.git` link, detached HEAD past a landed branch | `--merged-only` removes it; the commit is left on no ref | skipped `not-merged` (HEAD read from the root) |
| source on another remote (`upstream/main`), landed | landed | unchanged |
| slug and branch `upstream/main` started from `upstream/main`, unlanded | read as merged (compared with itself); `--merged-only` deletes the branch | not merged |
| revision source (`origin/main~0`) | read as `refs/remotes/origin/main~0` | unchanged (a local ref named `origin/main` never stands in) |
| directory deleted by hand, stacked branch landed only on the trunk, recorded HEAD detached past it | kept (`not-merged`; `--delete`: `branch <b> not on <source>`) | kept (`--delete` names both refs) |
| repository without an `origin` remote, a local branch `origin/main` at an unlanded tip | read as landed (by name) | never a landing (`origin/<b>` is always remote-tracking) |
| a remote named with a slash (`team/fork/main`), landed | landed | unchanged (a configured remote prefixes it) |
| a local branch `upstream/feat` where `upstream` is a remote with no such remote-tracking ref | a verdict (read by name) | an error row: indistinguishable from a pruned remote ref behind a local shadow, so it fails safe |
| directory deleted by hand, recorded HEAD detached past a landed branch | pruned or dropped; the commit is left on no ref | unchanged (out of scope; a separate fix story) |
| directory deleted by hand, HEAD at its own unmerged branch's tip | `.missing.txt`, branch kept, record dropped; `--delete` refuses `branch <b> not on <source>` | unchanged, except the refusal names `<source> or origin/main` |
| directory deleted by hand, source git cannot resolve, branch not on main (or recorded HEAD past it) | `--delete`: an error row | unchanged |
| local source `originals` (starts like the remote `origin`) | local | unchanged |
| HEAD file git cannot read (zeros with no branch line), or no worktree listing | read as unborn or not checked | not landed |
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

### 2026-10-23 — Review pass 3 (FAIL: three should-fix, three nits; round 2 resolved)

1. **should-fix, fixed.** Round 2's "an unreadable HEAD defers to the branch" lost a detached HEAD's commit when the
   worktree's `.git` link was broken. That was the baseline's behaviour, so round 2 had reopened it. HEAD is now read
   from the root (`worktree list --porcelain -z`); forty zeros means unborn, and anything else unreadable is not
   landed. The same read covers a directory deleted by hand, which was pre-existing.
2. **should-fix, fixed.** The round-2 exact lookup accepted only `origin/` and `refs/remotes/`, so `upstream/main`
   stopped proving landings. `_remote_tracking_name` now maps `<remote>/<b>` for every configured remote. This also
   closes a pre-existing loss: a workspace slugged like its remote source was compared with itself.
3. **should-fix, fixed.** Mutants mE, mG4 and mN now fail, each against its own test.
4. **nit, fixed.** A revision source (`origin/main~N`) is no refname, so it is read as recorded, as at the baseline,
   with no error row.
5. **nit, fixed.** The `refs/remotes/` guard is pinned, by mN.
6. **nit, fixed.** CAP-157's `--symbolic-full-name` clause and the spine bullet.

### 2026-10-23 — Review pass 4 (FAIL: one must-fix, two should-fix, three nits; round 3 resolved)

1. **must-fix, fixed.** This was a regression of round 3. `origin/<b>` counted as remote-tracking only when
   `git remote` listed `origin`. In a repository without that remote, a local branch `origin/main` proved an unlanded
   commit landed. `origin/<b>` is now always remote-tracking.
2. **should-fix, fixed.** The default `clean` pruned, and `--delete` dropped, a directory deleted by hand whose
   recorded HEAD was not landed. This was pre-existing. Both modes now keep the record and name the reason.
3. **should-fix, fixed.** Remote names containing `/` (`team/fork`) now resolve to the longest configured remote that
   prefixes the source. `remotes/...` maps under `refs/`.
4. **nit, recorded.** A local branch whose first segment equals a remote name, with no remote-tracking ref of that
   name, now gives an error row where the baseline gave a verdict. That fails safe, and the matrix row says so.
5. **nit, fixed.** A HEAD file git cannot read lists as forty zeros with no branch line. That no longer counts as
   unborn.
6. **nit, fixed.** A failed worktree listing counts as not landed. Mutant mR5 now fails.

### 2026-10-23 — Review pass 5 (FAIL: one must-fix, three should-fix, three nits; round 4 resolved)

1. **must-fix, fixed.** This was a regression of round 4. `--delete` asked about a deleted directory's recorded HEAD
   before its branch. That changed Story 13.5's refusal text, and it turned a git failure into a refusal, so a fleet
   run exited 0 instead of 1. The branch decides first again. Only a landed branch, which `--delete` removes, also
   needs its recorded HEAD landed.
2. **should-fix, fixed.** The default `clean` kept forever a deleted directory whose HEAD sat on its own unmerged
   branch, which `clean` keeps anyway. `_recorded_head_at_risk` now keeps the record only when the HEAD is neither
   landed nor on that branch.
3. **should-fix, fixed.** The Never clause and the Dream claimed "every `clean` mode". They are now scoped to what
   the code does. The default `clean` with the preserve flag off still tars and removes a present worktree, which is
   pre-existing and out of scope.
4. **should-fix, fixed.** The `remotes/` spelling is pinned by a workspace slugged like its `remotes/origin/main`
   source, so mutant mT2 now fails.
5. **nit, corrected.** Round 4's triage said mR5 fails. It does not: the fallback for a directory git does not list
   is unpinned, and archiving such a directory loses nothing.
6. **nit, fixed.** The `/` in the remote-prefix match is pinned by a local source named `originals`, so mT11 now
   fails.
7. **nit, fixed.** "Longest configured remote" was the wrong wording: any matching remote gives the same refname.

### 2026-10-23 — Review pass 6 (FAIL: no must-fix, three should-fix, two nits) and the operator's scope ruling

Every should-fix sat in the protection rounds 3-5 added for a directory deleted by hand:
- a bare `worktree prune` from any other clean dropped a kept record;
- a HEAD another branch or a tag held was kept forever;
- five legs were unpinned.

The baseline loses those commits in every case, so the protection was not converging. The operator ruled in chat to
scope back:
- The deleted-directory paths return to the baseline. `_recorded_head_at_risk` is removed, and so are the archive's
  early return and `--delete`'s recorded-HEAD checks for a missing directory.
- The two tests for that protection are dropped; the baseline-shape tests stay.
- The Never clause, the Approach and the matrix now scope it out.
- The loss is proposed as its own steward fix story.

Kept: the trunk as a landing ref, the exact remote-tracking lookup, and the HEAD check for a present worktree.
Nit 4 (matrix "longest remote prefix") is fixed. Nit 5 (the deleted-directory error row) no longer applies.

### 2026-10-23 — Review pass 7 (FAIL: two must-fix, three nits)

1. **must-fix, fixed.** The scope-back judged a deleted directory by its branch alone. Landed through the trunk, a
   stacked workspace whose recorded HEAD sat past its branch was pruned, where the baseline kept it because the
   branch was not on the workspace's local source. `_gone_branch_landed` now lands such a directory on the trunk
   only when its recorded HEAD is landed too; otherwise it gives the baseline's answer, including the source's error.
   `--merged-only`, `--delete`'s eligibility and its branch removal (now decided before the prune) all use it.
2. **must-fix, fixed.** Since round 3, a target that is not remote-tracking was passed as written, so `origin/main~0`
   lost its `refs/remotes/` prefix and a local `origin/main` could land a branch. It goes through `_source_ref`
   again, as at the baseline.
3. **nit, fixed.** The matrix rows for a deleted directory now say the refusal names both refs.
4. **nit, fixed.** The deferred loss is now recorded in this spec's `deferred:` list.
5. **nit, fixed.** Three test docstrings were stale.

### 2026-10-23 — Review pass 8 (FAIL: three must-fix, two should-fix, three nits)

1. **must-fix, fixed.** Every clean path ran a bare `git worktree prune`, which drops every registration whose
   directory is missing. So the clean of a newly trunk-landed workspace could prune a sibling deleted by hand, and its
   detached commit with it, where the baseline never cleaned that workspace. `_unregister_worktree` (`worktree remove
   --force --force <path>`) now drops this record's registration only, at all three sites. Pinned for
   `--merged-only` and `--delete`.
2. **must-fix, fixed.** Unregistering also deletes the worktree's `refs/worktree/*` and `refs/bisect/*`. A gone
   directory with such a ref no longer lands through the trunk (`_holds_per_worktree_refs`), the same rule CAP-157's
   proof applies to a present worktree.
3. **must-fix, fixed.** The `deferred:` entry had no location, so the deferred-work gate went red. It now names
   `workspace.py` and was ingested as `DW-steward-13-6`.
4. **should-fix, fixed.** Two gone-directory legs are pinned: a failed listing (mW6) and a garbage HEAD (mW4).
5. **should-fix, fixed.** A gone, unmerged directory with no trunk is refused, not reported as an error row (mW7).
6. **nit, recorded.** A present trunk-landed worktree with a per-worktree ref loses that commit under `--merged-only`.
   This is pre-existing: the baseline does the same to a source-landed one. It joins the deferred story's scope.
7. **nit, fixed.** Stale wording in the Never clause, the `_worktree_head_landed` docstring and the revision-source
   descriptions. CAP-157 and the Dream now name per-worktree refs.
8. **nit, accepted.** A landed T4 case is unpinned; a refusal there keeps the baseline's verdict.

### 2026-10-23 — Review pass 9 (FAIL: two must-fix, three should-fix, four nits); the operator chose "fix, final review, land"

1. **must-fix, fixed.** `worktree remove --force --force` overrode `git worktree lock`, so a locked registration
   whose detached HEAD or per-worktree ref held a commit was unregistered, where `prune` always left it. The removal
   now uses one `--force`. Pinned for a hand-deleted locked registration under all three modes, and for the
   archive's move-aside fallback.
2. **must-fix, fixed.** The admin lookup and the per-worktree-ref listing decoded strictly, so a non-UTF-8 pointer
   or ref name crashed the sweep. Both now read bytes. The `.missing.txt`, landed-note and host-local writes, which
   crashed the same way before this story, now write those bytes back (`errors="surrogateescape"`).
3. **should-fix, fixed.** The garbage-HEAD test now writes an invalid symbolic ref, which lists as zeros with no
   branch line (mutant mW4).
4. **should-fix, fixed.** `refs/bisect/bad` and relative worktree pointers are pinned (mX5, mX7). A relative pointer
   now resolves against its admin directory.
5. **should-fix, fixed.** The move-aside site is pinned (mX11a).
6. **nit, accepted.** These mutants keep more than needed or are equivalent: mX9, mX10, mX12, mX3, mX8, mW4b, mW5b,
   mH, mV1, mW10 and mW14.
7. **nit, fixed.** Relative `gitdir` pointers are covered by item 4.
8. **nit, fixed.** Wording fixes:
   - the Approach now names per-worktree refs and the lock;
   - the present-worktree loss is a second deferral (`DW-steward-13-6-2`);
   - Story 13.6 in `epics.md` is qualified;
   - the test name is fixed;
   - the deferral is captured in team memory.
9. **nit, pre-existing.** `exp31` Q1 is `DW-steward-13-6-2`.

### 2026-10-23 — Review pass 10, the final regression-only review (FAIL: three must-fix)

The bar was a must-fix regression against `bdb49ec39f`. The reviewer compared 43 reproducers at HEAD and at the
baseline and found three crashes, all in code new in this story. Each is fixed and pinned:

1. **`_remote_names` read `git remote` strictly,** so a remote with a non-UTF-8 name crashed `status` and every clean
   mode. It now reads bytes.
2. **`_unregister_worktree` decoded `worktree remove` output,** which echoes a path git no longer lists. A non-UTF-8
   one crashed `--delete`. The output is no longer read.
3. **`_admin_dir` passed a damaged `gitdir` pointer containing a NUL to `realpath`,** which raised `ValueError`. Such
   a pointer is now skipped.

`show-ref`'s output is read as bytes as well, since its error message echoes the name.

Two items were deferred:
- the locked present worktree's `--delete` error row (third `deferred:` entry);
- the non-UTF-8 default-clean loss, which falls under `DW-steward-13-6`.

### 2026-10-23 — Review pass 11, verification of the round-10 fixes (FAIL: two must-fix)

The round-10 crashes are fixed. The reachability harness (48 reproducers at HEAD and at the baseline) is unchanged
from round 10 apart from them. Two more members of the same class turned up, and both are fixed and pinned:

1. **A non-UTF-8 common git directory crashed `_admin_dir`,** which ran `rev-parse --git-common-dir` through a strict
   decode. That path is absolute from a linked worktree or with a separated git dir. It is now read as bytes.
2. **A NUL in a hand-edited bookkeeping path raised `ValueError`** in `_unregister_worktree` and in `realpath`. Both
   now treat it as unregistered or unresolvable, which is fail-safe.

The new-code family (`_registered_head`, `_admin_dir`, `_holds_per_worktree_refs`, `_unregister_worktree`,
`_remote_names`, `_source_commit`) now reads git output as bytes, and handles the `ValueError` a path can raise,
everywhere.

### 2026-10-23 — Review pass 12, verification of the round-11 fixes (FAIL: two must-fix of the same class)

The reachability harness (51 reproducers) is unchanged apart from the round-11 cases. Two more strict-decode crashes
turned up in paths that now run where the baseline answered:
- `merge-base` echoing a non-UTF-8 source deleted after landing;
- `rev-parse HEAD` inside an unregistered worktree of a repository at a non-UTF-8 path.

The class is now closed at its root: the module's `_git_ok` decodes with `errors="surrogateescape"`, so no git output
raises, for any caller. `_worktree_head_landed` also guards `ValueError`. Both cases are pinned.

### 2026-10-23 — Review pass 13, verification of the round-12 fixes (FAIL: one must-fix)

The round-12 cases are fixed. Switching to surrogateescape changes no answer for UTF-8 input, and the harness (53
reproducers) shows no new loss.

**must-fix, fixed.** `_worktree_head_landed` caught `ValueError` but not `OSError`. A present, unregistered workspace
the user cannot enter therefore stopped `--merged-only`, where the baseline gave an error row and went on (CAP-155).

The fix has two parts:
- the guard catches both `ValueError` and `OSError`;
- the sweep loop now reports any `OSError` or `ValueError` from a record as an error row and keeps the record, as
  CAP-155 states.

Both are pinned by a two-record sweep.

### 2026-10-23 — Review pass 14, verification of the round-13 fix (PASS)

There is no must-fix regression against `bdb49ec39f`.
- The reachability harness (55 reproducers, HEAD and baseline) is unchanged apart from the round-13 cases.
- The loss scan shows only the accepted deferrals.
- Fault injection replaced every git call with an `OSError` or `ValueError`, across 3,628 sweeps. It lost no commit,
  branch or record, and the broadened catch changed no answer the narrow catch gave.

The verifier's "to defer" items are the fourth `deferred:` entry: the `--merged-only` refusal for an unreadable,
unregistered worktree, the pin strength, `status`'s `PermissionError`, and the `DW-steward-13-6` wording. By the
operator's ruling, Story 13.6 lands.

