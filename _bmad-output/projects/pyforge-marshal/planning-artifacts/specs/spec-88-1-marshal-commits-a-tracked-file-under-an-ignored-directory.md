---
title: "88.1: Marshal commits a tracked file under an ignored directory"
type: 'fix'
created: '2026-10-10'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/vcs_git.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/commit.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/vcs.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/worktree_checkpoint.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/chain_regen.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_vcs_git.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** every commit marshal makes in a story worktree goes through one port method,
`VcsPort.commit_paths` (`adapters/vcs_git.py`). It stages each named path with `git add -- <path>`. Git refuses that
for a file that is **tracked** but lives inside a directory a `.gitignore` pattern excludes, so a session that edits
such a file loses its whole commit. Line numbers below are at `9c0d3c1f45`, with git 2.43.0.

- **The refusal.** For a tracked file under an ignored directory, `git add -- <path>` prints "The following paths are
  ignored by one of your .gitignore files: <dir> … Use -f if you really want to add them" and exits 1. It does this
  whether the change is in the worktree or already staged, and for a modification or a deletion. It even stages the
  change before it exits 1. `git add -u -- <path>` stages the same change and exits 0. A file-level ignore of a
  tracked file (`pixi.lock`, `.gitignore:719`) is not refused; the trap is the ignored **directory**. Reproduce it in
  a scratch repo: commit `.c/r/f`, then write `.c/` to `.gitignore` and change `.c/r/f`. `git add -- .c/r/f` exits 1
  and `git add -u -- .c/r/f` exits 0.
- **Where it raises.** `commit_paths` (:1130) reads `git status --porcelain -z` once for Story 83.16's facts
  (:1158-:1176), skips a named path whose deletion is already staged (:1179-:1180), and runs
  `git add -- <path>` per path (:1181). A non-zero exit raises `VcsCommandError("git add -- <path> failed: …")`
  (:1182-:1183), and nothing is committed.
- **Who calls it.** The supervisor's finalize (`dispatch_supervisor/__main__.py`, about :1749-:1757, Story 28.24),
  its pre-verify WIP commit (:225, which the fix turn's commit also uses at :1580) and Story 51.11's blocked-halt commit (:938), Story 34.2's idle checkpoint
  (`core/worktree_checkpoint.py` :63, which turns the error into `skipped_reason` and saves nothing),
  `dispatch_verify.py` (:551), `dispatch_land.py` (:701, :767, :836, :1234), `cli/land.py` (:1336) and
  `commit_paths_onto_remote_tip` (:1889). A fix in `commit_paths` reaches all of them.
- **Which files are at risk.** `git ls-files -ci --exclude-standard` lists 24 tracked files under ignored
  directories: 12 under `.cursor/` (`.gitignore:693` is `.cursor/`; `.cursor/rules/*.mdc` are tracked on purpose,
  per the comment at `.gitignore:691-692`), 10 under `recipes/.idea/` (`.gitignore:198`), `.junie/guidelines.md`
  and `.pixi/config.toml`.

**Evidence** (Tier-3 run journal,
`_bmad-output/projects/pyforge-doctor/implementation-artifacts/dispatch-runs/pyforge-doctor-20261010T145603286Z-16048b81/journal.jsonl`):
doctor Story 37.1 edited `.cursor/rules/specs.mdc`. Its `dispatch-finalize` OUTCOME (15:12:23Z, trigger
`commitable-dirty`) records `committed: false`, `failed_step: commit` and `failed_message: "git add --
.cursor/rules/specs.mdc failed: The following paths are ignored by one of your .gitignore files: .cursor …"`. The
run then ended `stopped_externally` (`external-operator-stop`) with the whole story uncommitted in its worktree. The
operator committed it by hand, and it is PR #2081.

**Other `git add --` calls (audit).**
- **Shares the defect: `merge_ref_resolving`** (`adapters/vcs_git.py` :1583, Story 59.1's landing heal). It stages
  each resolved conflicted path with `git add -- <rel>`. A conflicted tracked path under an ignored directory is
  refused the same way (exit 1); `git add -u -- <rel>` exits 0. The heal's resolvable paths today are memlogs, ledgers
  and the spec-surface baseline, none under an ignored directory, so this is latent.
- **Shares the defect: `stage_index_paths(update=False)`** (:1964-:1987, `marshal planning … --stage`, Story 21.4).
  It runs `git add -- <paths>` for paths that exist, so a tracked one under an ignored directory is refused. It
  returns 0 on any git failure and never raises, so the failure is silent. Latent too: it stages regenerated planning
  paths.
- **Does not share it: `core/chain_regen.py` `stage_hook`** (:978-:1010). It only classifies paths. Missing
  (deleted) paths go to the stager with `update=True` (`git add -u --`), and existing paths go through
  `stage_index_paths(update=False)`, so it is fixed with that function.
- **Not staging calls:** every other `"add"` in `adapters/vcs_git.py` (:566, :573, :1326, :1722, :1869) is
  `git worktree add`.

**Approach:** stage by what the index already knows, in one place.
- **One staging rule.** A named path the index tracks (`git ls-files` lists it, including an intent-to-add entry) is
  staged with `git add -u -- <path>`. A path the index does not track is staged with `git add -- <path>`, so git's
  ignore rules still refuse an untracked path under an ignored directory. The index is read once per call, with the
  paths taken literally. One private helper in `adapters/vcs_git.py` applies the rule, and `commit_paths`,
  `merge_ref_resolving` and `stage_index_paths(update=False)` all call it.
- **`commit_paths` keeps its contract.** It stages exactly the named paths and never runs `git add -A`. The Story
  83.16 status read, the staged-deletion skip and the rename-source pathspec (`:(top,literal)<old>`) are unchanged. A
  refused path still raises `VcsCommandError` naming the path and git's message.
- **`merge_ref_resolving`.** Every conflicted path is in the index, so the helper stages it with `-u`.
- **`stage_index_paths(update=False)`.** It applies the same split and keeps its contract: it returns the number of
  path arguments accepted, returns 0 on a git failure, and never raises.
- **Docs.** The docstrings that say "one `git add -- <path>` per entry" (`ports/commit.py`, `ports/vcs.py`, the
  `adapters/vcs_git.py` module docstring and `commit_paths`) are restated as the rule above, still never `-A`.

Ledger key: `88-1-marshal-commits-a-tracked-file-under-an-ignored-directory`.
Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-marshal` CAP-4 (FR-30): Story 4.1's commit port and AD-29 ("a promotion
  commit contains only promotion paths"), which this fix keeps. The finalize that failed is Story 28.24
  (`spec-marshal-drain-self-resolution` CAP-7). The idle checkpoint is Story 34.2, the landing heal is Story 59.1
  (`spec-pyforge-marshal` CAP-269), and the rename and staged-deletion handling is Story 83.16. This story fixes the
  realization of shipped behaviour, so it needs no new CAP and no SPEC.md change.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag: it restores intended behaviour, and a
  flag would keep the bug reachable.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, 2026-10-10 (ignored-directory commit). Operator
  ruling 2026-10-10, verbatim: "Mint both (Recommended)".

## Acceptance Criteria

Every test below builds a real temporary git repo (the existing `vcs`/`repo` fixtures in
`tests/unit/test_vcs_git.py`): it commits `.c/r/f` (and `.c/r/g` where needed), then commits `.c/` to `.gitignore`.
Each test first asserts the precondition that a plain `git add -- .c/r/f` exits non-zero in that repo, so the fixture
cannot silently stop reproducing the refusal.

- **AC1 — A modified tracked file under an ignored directory commits.** **Given** `.c/r/f` changed in the worktree
  and not staged **When** `commit_paths(repo, (Path(".c/r/f"),), message)` runs **Then** it returns the new `HEAD`, and
  `git show HEAD:.c/r/f` holds the new content.
- **AC2 — Already staged, too.** **Given** the same change already staged (the state a refused `git add --` leaves
  behind) **When** `commit_paths` runs **Then** it commits as in AC1.
- **AC3 — A deleted tracked file under an ignored directory commits.** **Given** `.c/r/g` removed from the worktree
  and not staged **When** `commit_paths` names it **Then** the commit records its deletion, and
  `git ls-files .c/r/g` prints nothing.
- **AC4 — An untracked file under an ignored directory is still refused.**
  - **Given** a new, untracked `.c/r/new`, **When** `commit_paths` names it, **Then** it raises `VcsCommandError`,
    and the message names `.c/r/new`.
  - `HEAD` is unchanged and `.c/r/new` is not in the index afterwards: marshal never passes `-f`/`--force` to
    `git add`.
- **AC5 — Mixed calls, and Story 83.16 unchanged.**
  - **Given** one call naming the AC1 file, a new untracked file outside any ignored directory and a tracked file
    outside it, **When** `commit_paths` runs, **Then** one commit holds all three.
  - Every existing `commit_paths` test in `tests/unit/test_vcs_git.py` (rename in both forms, a spaced or awkward
    original, renames-off config, an absolute path, a staged deletion, an unnamed rename) passes unchanged.
- **AC6 — The finalize and checkpoint paths commit it.** **Given** a worktree whose only change is a tracked
  `.cursor/rules/x.mdc` with `.cursor/` ignored (the doctor 37.1 shape) **When** `commit_worktree_checkpoint` runs,
  and separately the supervisor's finalize commit step runs over the same tree (the shape of the existing
  `test_the_finalize_path_commits_a_rename_under_an_operators_renames_off_config`), **Then** the checkpoint returns
  `committed: True`, and the finalize commits with no `failed_step: commit`.
- **AC7 — The landing heal stages a conflicted file under an ignored directory.** **Given** a merge in which a tracked
  `.c/r/f` conflicts and `resolutions` holds its content **When** `merge_ref_resolving` runs **Then** the merge
  commits, and `HEAD:.c/r/f` holds the resolution.
- **AC8 — `stage_index_paths` follows the same rule.** **Given** the AC1 change **When**
  `stage_index_paths(repo, [".c/r/f"])` runs **Then** it returns 1 and the change is staged. **Given** an untracked
  `.c/r/new` **When** it is staged the same way **Then** it returns 0, nothing raises, and `.c/r/new` stays out of the
  index.
- **AC9 — Mutation.**
  - Restoring a plain `git add -- <path>` for tracked paths fails AC1, AC6 and AC7.
  - Adding `-f` to the staging call fails AC4.
  - Dropping the staged-deletion skip fails Story 83.16's staged-deletion test.

## Boundaries & Constraints

**Always:**
- Stage exactly the named paths, one decision per path, from one index read. Make it one helper, reused by
  `commit_paths`, `merge_ref_resolving` and `stage_index_paths`, never copied.
- Read paths literally, as Story 83.16 does, so a space, a glob character or a leading `:` in a path never becomes a
  pathspec.
- Reconcile every governed path the change touches on the memlogs of the Specs that govern it, then stamp those Specs
  scoped. `adapters/vcs_git.py` and the ports are governed by `spec-pyforge-marshal` and `spec-pyforge-core`, plus
  any co-governor `spec-surface-check` names (AGENTS.md pre-PR item 5).

**Never:**
- Never `git add -f`/`--force`, and never `git add -A`, `git add .` or `git commit -a`.
- Never edit `.gitignore` to work around the refusal, and never untrack the `.cursor/` rules.
- Never change which paths finalize, the checkpoint or the landing pass to `commit_paths`. Story 83.19/83.24's CFE
  partition (`non_retro_commit_paths`) is unchanged.
- Never swallow a refusal in `commit_paths`: an untracked ignored path still raises. The checkpoint keeps its own
  `skipped_reason` behaviour.

**Residual risk:** a session that creates a NEW file under an ignored directory still has it refused at finalize.
That is intended: git's own ignore rule decides, and marshal never forces a path git was told to ignore.

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-10 (ignored-directory commit) entry.
- Epic: Epic 88 (a new fix epic. The capabilities that shipped this behaviour are in Epics 4, 28, 59 and 83, all
  `done`, and the defect spans more than one of them).
- Ledger key: `88-1-marshal-commits-a-tracked-file-under-an-ignored-directory`.
- Ledger status at mint: `backlog`.
- Deps: none.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- Repro: in a scratch repo, commit `.c/r/f`, write `.c/` to `.gitignore`, change `.c/r/f`; `git add -- .c/r/f` exits 1 and `git add -u -- .c/r/f` exits 0 (git 2.43.0).
- Mutation: restore the plain `git add -- <path>` for tracked paths and re-run the station suite; AC1, AC6 and AC7 fail. Restore it.
- `grep -n '"-f"\|--force' src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/vcs_git.py` prints no line that stages with `git add`.
- `pixi run --frozen -e pyforge-guild spec-surface-check`: exit 0 after the memlog reconciles and scoped stamps.
- On the next dispatch whose session edits a `.cursor/rules/*.mdc` file, the run's `journal.jsonl` shows a `dispatch-finalize` OUTCOME with `committed: true`.
