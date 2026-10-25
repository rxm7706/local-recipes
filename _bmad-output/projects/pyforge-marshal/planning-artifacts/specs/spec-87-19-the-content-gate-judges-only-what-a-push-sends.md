---
title: "87.19: The content gate judges only what a push sends"
type: 'fix'
created: '2026-10-25'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-87-15-a-preserve-reaches-origin-only-through-the-content-gate.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-87-12-legacy-refs-are-promoted-and-attempt-preserve-leaves-the-protected-list.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-87-9-every-preserve-reader-sees-preserve-tags-and-origin.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/preserve-manifests/legacy-preserve-promote-2026-10-22.json
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml
  - docs/dreams/pyforge-marshal.md
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - docs/governance/preserve-purge-list.json
  - docs/how-to/purge-preserved-refs.md
  - src/shared/packages/pyforge-core/src/pyforge/core/preserve_refs.py
  - src/shared/packages/pyforge-core/src/pyforge/core/process.py
  - src/shared/packages/pyforge-core/tests/unit/test_preserve_refs.py
  - src/shared/packages/pyforge-core/tests/unit/test_process.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/preserve.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py
  - scripts/legacy_preserve_promote.py
  - scripts/worktree_sweep.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the content gate refuses almost every preserve that would reach `origin`, and it never reads a blob that
an earlier commit added. Line numbers are at `d287eceb0a`.

- **What it reads.** `run_content_gate` (`pyforge-core/src/pyforge/core/preserve_refs.py:578`) lists every blob in the
  tagged commit's tree (`git ls-tree -r`). It runs the size cap and the secret scan on each one, starting
  `git cat-file -s` and `git cat-file -p` per blob (`_blob_size`, `:571`; `_scan_blob_for_secrets`, `:557`).
- **What it should read.** Story 87.15's acceptance criteria refuse a preserve that *adds* a blob with a planted
  credential, or *adds* a file over the cap. A push sends only the objects `origin` does not already reach, so those
  are the objects that need judging.
- **The effect.** Run read-only on `origin/main`, the gate returns 13 findings. Three are slide decks under
  `presentations/` over the 5 MB cap. The other ten are synthetic `sk-ant-`, `ghp_` and private-key strings in test
  fixtures and in two steward story specs. All of it is already public. So any preserve built on today's `main` is
  refused. On 2026-10-25 the gate refused 25 of the 29 preserve and archive tags that exist only locally. Every
  refusal named a file that is on `origin/main` or in its history. Turning `pyforge.marshal.preserve_refs` on would
  push 4 and refuse the rest. Every dispatch, spin and sweep preserve would be refused the same way.
- **The gap.** A blob that an intermediate unpushed commit added and a later commit removed is never read, although
  the push sends it. Neither the annotated tag object being pushed nor the sent commit messages are read.
- **The cost.** Two processes per blob is about 80 s per tag on this repository: `preserve/unbound/hand-6069fa46`'s
  tree holds 25,104 blobs.
- **The seam.** `preserve_refs.py` runs every process through `pyforge.core.process.PosixProcess` (`:88`).
  `PosixProcess.run` (`process.py:165`) closes stdin (`stdin=subprocess.DEVNULL`) and decodes output as text with
  `errors="replace"`. So it cannot drive `git cat-file --batch`, which needs stdin and byte-exact output.
  spec-pyforge-core's process seam is the one sanctioned way to start a process, so a raw `subprocess` call in
  `preserve_refs.py` is not an option.
- **The remedy text.** `MRS-STATUS-016` (`pyforge-marshal/src/pyforge/marshal/cli/status.py:1311`) says "push each
  with `marshal preserve push`", a verb that refuses while the flag is off.
- **The operator's push path.** `push_reviewed_rows` (`scripts/legacy_preserve_promote.py:495`) counts every
  `pushed=True` against the per-run cap of 20. A tag already on `origin` comes back `pushed=True`, so a second run
  re-counts the first 20 and refuses rows 21 to 27 with `push-cap-run`. A `PreserveGitError` from one row stops the
  run.

**Approach:**
1. **The process seam.** `PosixProcess` gains a concrete-only sibling method that writes bytes to a child's stdin and
   returns its own bytes result type (returncode, stdout bytes, stderr). `run` and `ProcessResult` do not change:
   `ProcessResult`'s fields are `str` (`process.py:52-63`), and bytes from `run` would break `PosixProcess`'s match
   with `ProcessPort` under strict mypy. `ProcessPort` does not change either, since other stations' fakes implement
   it. This follows the `env=` precedent (`process.py:150-158`). Story 103.1's stdio probe also writes to a child's
   stdin: whichever story lands second reuses the first one's path instead of adding a second stdin seam.
2. **The sent set.** `run_content_gate` gains `remote` (default `ORIGIN_REMOTE`). It reads the remote once with
   `git ls-remote <remote> 'refs/heads/*' 'refs/tags/*'`, through `_git_via` with
   `timeout_s=REMOTE_PROBE_TIMEOUT_S`.
   - It judges the objects `git rev-list --objects --ignore-missing --stdin <commit>` names, with the listed shas fed
     on stdin as `^<sha>`. A listed sha missing locally is ignored, so the gate reads more objects, never fewer, and
     the process count does not grow with the number of listed refs.
   - `refs/pull/*` and every other namespace are never trusted as public. The owner cannot delete pull refs, and
     GitHub's receive-pack hides them, so a push sends their objects anyway.
3. **An unreadable remote** is a refusal with a new `ContentGateReason` (additive): a non-zero exit, a timeout or a
   `ProcessError`. It is never a pass, never an exception and never a fall back to the whole tree.
4. **One batched read.** One `git cat-file --batch-check` gives every sent object's type and size, and one
   `git cat-file --batch` reads the contents. That is a fixed number of processes per gate run, whatever the number of
   blobs. A blob already over the cap is refused without reading its contents.
5. **The rules.**
   - The secret scan (`_SECRET_PATTERNS`, unchanged) reads every sent blob, intermediate commits included. It also
     reads every sent commit object and, when the caller names the annotated tag being pushed, that tag object.
   - The size cap applies to every sent blob.
   - The purge rules hold. A commit that matches or descends from a purge-listed sha is refused. A purge-listed path is
     refused when the tip tree carries it (`git ls-tree -r`, as today) or any sent commit touched it:
     `git log --name-only --format= --no-renames --diff-merges=first-parent --ignore-missing --stdin <commit>`, fed
     the same `^<sha>` lines, gives the full path of everything a sent commit touched. The single path `rev-list`
     gives each object is not used for this.
   - A secret finding names the object's path (or "commit" / "tag") and its short sha, never the matched text.
6. **Callers.** `push_preserve_ref` passes its `remote` and the tag's refname through. Its caps, its one-refspec push
   and its `ls-remote` verification do not change. The other callers gain the fix with no change of their own:
   - `marshal preserve push`;
   - the dispatch and spin supervisors;
   - steward's `workspace.py:1195`;
   - `scripts/worktree_sweep.py`, including `write_and_push_archive_twin` (`:1099`), which runs on
     `--remote`/`--retire --execute` and is not flag-gated.
7. **The operator's push path.** `push_reviewed_rows` reads `origin` once. It skips, and does not count, a row whose
   twin `origin` already lists. If `origin` cannot be read, it treats nothing as listed: each row's gate then refuses
   with the unreadable-remote finding, and nothing is pushed or counted. A `PreserveGitError` on one row is recorded
   as that row's refusal, and the run goes on.
8. **The remedy.** `MRS-STATUS-016` names both push paths: `marshal preserve push` once `pyforge.marshal.preserve_refs`
   is on, and `scripts/legacy_preserve_promote.py --push-reviewed` for a reviewed legacy twin. Status reads no flag.
9. **The runbook.** `docs/how-to/purge-preserved-refs.md:21` describes the gate. It is updated to the sent set and the
   unreadable-remote refusal.

Ledger key: `87-19-the-content-gate-judges-only-what-a-push-sends`.
Type / Effort / Deps: fix / M / S-87.15.

### Living CAP citations

- `spec-pyforge-marshal` CAP-287 (FR-234; AD-81): nothing reaches `origin` past the content gate. This story makes
  the gate judge what Story 87.15's acceptance criteria already say, so no new CAP. It is a fix, so no flag
  (`spec-feature-flag-governance` Q1).
- `spec-pyforge-core` and `spec-pyforge-unifying-strategy` co-govern `preserve_refs.py` and `process.py` with
  `spec-pyforge-marshal`.

## Acceptance Criteria

All tests use real git with a bare remote.

- **AC1 — Public content passes.** `origin/main` carries a file over the cap and a synthetic `sk-ant-` string. A
  preserve commit on top of it adds one clean file. `run_content_gate` returns no finding, and `push_preserve_ref`
  pushes the tag; `ls-remote` lists it.
- **AC2 — The intermediate blob.** One unpushed commit adds a planted `sk-ant-` string and the next removes it. A
  preserve of the second commit is refused with a `secret-scan` finding naming the file's path, and the tag stays
  local.
- **AC3 — Pull refs are not public.** A blob carrying a planted credential is reachable on the bare remote only from
  `refs/pull/1/head`. A preserve that reaches it is refused with `secret-scan`.
- **AC4 — Tag and commit bodies.** A planted credential in the annotated tag's message, and one in a sent commit's
  message, are each refused with `secret-scan`.
- **AC5 — New content is still judged.**
  - A sent blob over the cap is refused with `size-cap`.
  - A sent blob with a planted credential is refused with `secret-scan`.
  - A commit that matches or descends from a purge-listed sha is refused with `purge-listed-sha`.
  - A tip-tree or sent-tree entry that carries a purge-listed path is refused with `purge-listed-path`.
  - Story 87.15's existing tests in `test_preserve_refs.py` pass unchanged.
- **AC6 — Unreadable remote.** When `git ls-remote` exits non-zero, times out or cannot start, the gate returns the new
  finding, raises nothing, and nothing is pushed.
- **AC7 — A fixed process count.** A test counts the processes one gate run starts. The count is the same for a commit
  that adds 3 blobs and one that adds 300, and for a remote listing 2 refs and one listing 200.
- **AC8 — The process seam.** `test_process.py` covers the new bytes path: stdin is delivered, stdout comes back
  byte-exact (including non-UTF-8 bytes), and the timeout and launch-failure contracts raise `ProcessError` only.
  `run` without the new input still closes stdin.
- **AC9 — The operator's push path.** In `tests/scripts/test_legacy_preserve_promote.py`, 25 reviewed rows, 3 already
  on `origin`, push 20 in one run and the remaining 2 in a second. A row whose push raises `PreserveGitError` is
  reported refused and the run continues.
- **AC10 — Remedy text.** `MRS-STATUS-016`'s message names `marshal preserve push` with the flag it needs, and
  `scripts/legacy_preserve_promote.py --push-reviewed`. A test in `tests/unit/test_status.py` asserts both. Today's
  tests there assert only the code.
- **AC11 — Mutation.** Each of these fails a named test:
  - judging the whole tree again instead of the sent set;
  - scanning only the tip tree's sent blobs;
  - trusting `refs/pull/*`;
  - treating an unreadable remote as a pass;
  - dropping the secret scan;
  - counting an already-pushed row in `push_reviewed_rows`.
- **AC12 — Live, read-only.** A scratch script, kept untracked, runs from the story worktree; tags and objects are
  shared through the common git dir. It calls `run_content_gate` on `origin/main` and on every preserve and archive
  tag that `ls-remote` does not list at run time (29 at `d287eceb0a`). It pushes nothing. It refuses none of them,
  where the old gate refused 25 of the tags and `origin/main` itself. The whole run takes under 120 s. `## Run
  results` records each tag's verdict and the total time.

## Boundaries & Constraints

**Always:**
- Real git with a bare remote in tests, and no GitHub call.
- One refspec per tag, never `--tags`.
- Start every process through `pyforge.core.process`.
- Read every verdict from its exit code.

**Ask First:** any change to the purge list or to `_SECRET_PATTERNS`.

**Never:**
- Push a tag, even in AC12.
- Turn on `pyforge.marshal.preserve_refs` in any environment.
- Delete or move a ref, or change a GitHub setting.
- Print a secret the scan matched.
- Change `ProcessPort`.
- Mark a row of the preserve manifest `reviewed`. That review is the operator's.

**Residual risk:**
- The gate trusts that what a listed branch or tag reaches is public, and does not read it again. A secret already
  on `origin` is the purge runbook's case, not the gate's.
- The secret scan has three patterns. Non-provider patterns are off in the repository settings, a separate operator
  step under Story 87.15.
- Paths the old gate blocked will start to push once this lands. `worktree_sweep --remote/--retire --execute` writes
  and pushes `archive/heads/*` twins, then deletes the remote branch. Steward's workspace preserve and the
  supervisors' preserves push only while their own flags are on.

## I/O & Edge-Case Matrix

| Scenario | Input | Expected |
|----------|-------|----------|
| preserve adds a clean file on top of `main` | tip tree carries public oversize and fixture files | pass, tag pushed |
| intermediate commit adds a secret, the tip removes it | unpushed two-commit chain | refused, `secret-scan`, path named |
| blob reachable on the remote only from `refs/pull/1/head` | preserve reaches it | read; refused if flagged |
| credential in the tag message | annotated tag object | refused, `secret-scan` |
| preserve adds a file over the cap | sent blob over 5 MB | refused, `size-cap`; contents not read |
| preserve descends from a purge-listed sha | purge list names an ancestor | refused, `purge-listed-sha` |
| `ls-remote` fails or times out | remote unreachable | refused, the new reason |
| listed sha missing locally | `ls-remote` lists an object not fetched | ignored; more objects read |
| preserve of a commit already on `origin` | sent set: the tag object only | pass |
| second `--push-reviewed` run | 20 rows already on `origin` | skipped, not counted |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-marshal` CAP-287 (FR-234; AD-81). No CAP is minted, and no `SPEC.md` text
  changes.
- Co-governors: `spec-pyforge-core` and `spec-pyforge-unifying-strategy` govern `preserve_refs.py`, `process.py` and
  their tests with `spec-pyforge-marshal`. Each memlog takes the surface reconcile when the code lands, with one scoped
  `--spec` stamp each.
- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-25 entry (the content gate refuses what
  origin already holds).
- Epic: Epic 87 (done). Operator rule 2026-10-04: a fix story joins its done epic. This backlog story reopens
  `epic-87` to `in-progress` through doctor Story 41.5's `epic_reopened_by_new_story`.
- Ledger key: `87-19-the-content-gate-judges-only-what-a-push-sends`; status at mint `backlog`.
- Deps: S-87.15.
- Surface: `marshal-policy.toml` `[epic_surfaces]."87"` already lists `preserve_refs.py`, `pyforge-core/tests/**`,
  the marshal package, `scripts/**`, `tests/scripts/**`, `docs/how-to/**` and the Spec memlogs. This mint adds
  `src/shared/packages/pyforge-core/src/pyforge/core/process.py`.
- After it lands (operator steps, not this story):
  - Mark the manifest rows `reviewed`, then run
    `pixi run -e pyforge-guild python scripts/legacy_preserve_promote.py --manifest-date 2026-10-22 --push-reviewed`
    twice. The per-run cap is 20, and the manifest has 27 promotion rows.
  - The two legacy sources, `archive/recover-scribe-1-3` and `archive/scribe-1-3-dangling-91d3571f`, are not
    manifest twins. Their twins `archive/tags/…` carry the same commits. They stay local, so the fleet check's archive
    count still lists them. `MRS-STATUS-016` counts only `preserve/*` and does not.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, with AC10's test (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-core pyforge-core-test` — expected: pass, with AC1–AC8's and AC11's tests.
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_legacy_preserve_promote.py tests/scripts/test_worktree_sweep.py -q` — expected: pass, with AC9's tests.
- `pixi run -e pyforge-guild pyforge-station-tests` — expected: pass (a `pyforge-core` change fires every station suite in CI).
- AC11's six mutations — expected: each fails its named test. Restore each.
- AC12's read-only script, from the story worktree — expected: exit 0, 0 refused, under 120 s.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0 (`pyforge-core` is mypy strict).
- `python3 scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries on `spec-pyforge-marshal`, `spec-pyforge-core` and `spec-pyforge-unifying-strategy` and the three scoped stamps.
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0.

## Run results

To be filled at landing: AC12's per-tag verdicts and total time, and each command above with its exit code.

## Spec Change Log

- 2026-10-25: minted from the Dream entry of 2026-10-25 (the content gate refuses what origin already holds) at the
  operator's ruling "start the option 2 chain here". `type: fix`, no flag, no CAP.
- 2026-10-25: chain review round 1 (independent reviewer, FAIL: 1 blocker, 8 should-fix, 9 nits); all applied. The
  process seam joins the surface; `refs/pull/*` is not trusted; the remote read has a timeout; tag and commit bodies
  are scanned; the promoter's second run and per-row errors are fixed; the third co-governor is named; AC12 runs from
  the story worktree; Effort S to M.
- 2026-10-25: chain review round 2 (same reviewer, PASS, 0 blockers, 4 nits); all applied. A sibling method with its
  own bytes result pins the process seam; the purge-path read is named; an unreadable `origin` in
  `push_reviewed_rows` is stated; Story 103.1's stdin path is shared, not duplicated.

## Review Triage Log

- **Round 1, 2026-10-25 (chain review of `49dbfac992`, independent reviewer): FAIL, 1 blocker, 8 should-fix, 9 nits;
  all applied.**
  - blocker B1: the batched read cannot run through `PosixProcess` (stdin closed, text decode) and the seam was
    outside the Surface. Fixed: a concrete-only bytes path on `PosixProcess` (Approach 1, AC8); `process.py` added to
    the Surface and to `[epic_surfaces]."87"`.
  - should-fix S1: `spec-pyforge-unifying-strategy` also governs `preserve_refs.py`. Named in Binding and Verification.
  - should-fix S2: `refs/pull/*` would have counted as public. Only `refs/heads/*` and `refs/tags/*` are excluded
    (Approach 2, AC3).
  - should-fix S3: `ls-remote` had no timeout. `_git_via` with `REMOTE_PROBE_TIMEOUT_S`; AC6 covers timeout and
    `ProcessError`.
  - should-fix S4: tag and commit bodies were sent unread. Scanned (Approach 5, AC4).
  - should-fix S5: a second `--push-reviewed` run re-counted pushed rows. Fixed in the promoter (Approach 7, AC9).
  - should-fix S6: AC12 ran in the primary checkout and named a count that drifts. It runs from the story worktree
    over the tags `ls-remote` does not list at run time; `## Run results` added.
  - should-fix S7: callers list incomplete. Steward's `workspace.py:1195` and `write_and_push_archive_twin` named;
    Residual risk records the sweep's new pushes; `pyforge-station-tests` added.
  - should-fix S8: the locally-present filter would cost a process per listed sha. `rev-list --ignore-missing --stdin`;
    AC7 also varies the number of listed refs.
  - nits: blob count 25,104; two of the ten secret hits are story specs; the 846-object figure moves with origin's refs
    and stays out of every AC; Epic 87's header lists 87.19 among the unflagged fixes; the runbook line joins the
    surface; purge paths are checked against tree entries; over-cap blobs are not read; the two legacy sources are
    named in the operator steps; a tip-tree-only mutation added.
- **Round 2, 2026-10-25 (re-review of `2a7f4507c3`, same reviewer): PASS, 0 blockers, 0 should-fix, 4 nits; all
  applied.** B1 and S1–S8 fixed; N1–N9 fixed, N6 partly (closed by nit 2). The reviewer confirmed live on git 2.53
  that `rev-list --stdin` takes `^<sha>` lines beside a commit argument and that `--ignore-missing` skips a missing
  `^<sha>` (exit 0; exit 128 without it), and that the branch-and-tag listing is the full listing minus `refs/pull/*`.
  - nit: a keyword-only bytes `input=` on `run` would break `ProcessResult`'s `str` fields under strict mypy. Fixed:
    a sibling method with its own bytes result.
  - nit: sent-tree entries give no full paths. Fixed: the `git log --name-only … --stdin` read named in Approach 5.
  - nit: an unreadable `origin` in `push_reviewed_rows` was unstated. Fixed in Approach 7.
  - nit: Story 103.1's stdio probe also writes to a child's stdin. Fixed: the second story to land reuses the first
    one's path (Approach 1).
