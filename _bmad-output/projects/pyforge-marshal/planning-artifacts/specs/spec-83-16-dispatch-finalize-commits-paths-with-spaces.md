---
title: "83.16: Dispatch finalize commits paths with spaces"
type: 'fix'
created: '2026-10-03'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/vcs_git.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** On 2026-10-03 herald Story 35.1's supervisor could not commit the session's work: `vcs.changed_files` reads `git status --porcelain` line by line, and porcelain v1 wraps a path that contains spaces in double quotes, so the finalize ran `git add -- "\"presentations/pyforge-atlas/project/PyForge Atlas - Infographic Deck.dc.html\""`, git refused the pathspec, and the run stopped with every change uncommitted (`stopped_externally`). The operator committed it by hand. Every path under `presentations/*/project/` has spaces.

**Approach:** Read status with `-z` (NUL-terminated, never quoted; a rename's two paths are separate fields) and parse that, so every consumer of `changed_files` gets the literal path.

Ledger key: `83-16-dispatch-finalize-commits-paths-with-spaces`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- the dispatch finalize (Story 28.24) and the scope check that reads `changed_files`. A defect of shipped behaviour, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given an untracked and a modified file whose paths contain spaces (and one with a non-ASCII character) When `changed_files` runs Then each comes back as its literal path, with no surrounding quotes
- Given such a file in a session's worktree When the supervisor finalizes Then it commits the file and the run does not stop
- Given a rename of a spaced path When `changed_files` runs Then only the new path is returned
- Given the `-z` parsing removed When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Use git's NUL-terminated output; test with a real git repository in `tmp_path`.

**Never:** Never unquote porcelain text by hand.

</intent-contract>

## Binding

Parent: Story 28.24 (the supervisor finalize).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-03 (night, latest) entry.
Ledger key: `83-16-dispatch-finalize-commits-paths-with-spaces`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 at the operator's request.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- 2026-10-04 build: ready for an independent review. `GitVcs.changed_files` reads `git diff --name-status -z` and `git status --porcelain -z` and parses the NUL-separated fields (`_name_status_z_paths`, `_porcelain_z_paths`); the `core.quotePath=false` pin it replaces is gone. Mutation checks (scratch copy): reverting `vcs_git.py` to `origin/main` fails 18 of the new tests, the finalize test with git's own `pathspec '"presentations/..."' did not match any files`; dropping `-z` from the status call alone fails 20, from the diff call alone 14; keeping a rename's original path fails 3; keeping a committed rename's source fails 3.

### 2026-10-04 — Landing review (independent reviewer) — SEND BACK, fixed
- `medium` **A rename's source deletion stayed uncommitted while the finalize journaled ok.** `changed_files` reports a rename by its new path only, and `commit_paths` (`adapters/vcs_git.py`, about 892-930 before the fix) ran `git add -- <new>` then `git commit -- <new>`. The old path's deletion stayed behind: staged after a `git mv`, unstaged in the intent-to-add form. `_run_supervisor_finalize_sequence` (`dispatch_supervisor/__main__.py`, about 1451-1458) still journaled ok. The reviewer's probe (`probe_tests/test_probe_rename_finalize.py`) showed the leftover `D  docs/old name.md`. **Fixed** in `commit_paths` (about 937-1010): before staging, it reads `git -c status.renames=true status --porcelain -z --untracked-files=no`. The pin means an operator's `status.renames`/`diff.renames=false` cannot hide the pair. `_commit_status_facts` (about 273) returns the original path of every rename whose new path is named: `R` in either column, never `C`, and never an original that is itself named. That path goes into the commit pathspec only, as `:(top,literal)<old>`, and never to `git add`. The same read finds named paths whose deletion is already staged (`D `). Those are committed without `git add`, which refuses them (`pathspec 'gone file.md' did not match any files`): the same mechanism, found while fixing, since a session's `git rm` failed the finalize. All three other committing callers go through `commit_paths`, so the fix covers them too: `_commit_pre_verify_wip` (`__main__.py` about 190), `_commit_and_journal_blocked_halt` (about 815) and `commit_worktree_checkpoint` (`core/worktree_checkpoint.py`). Tests drive the finalize in both forms, the pre-verify commit and the checkpoint.
- `low` Mutant M9 (`status[0] in "RC"`, which checks only the index column) survived. The `_porcelain_z_paths` parser test now has a ` R moved to.md\0moved from.md\0` worktree-column record. The parser moved into `_porcelain_z_records` (about 237), and a rename or copy cut short of its original now refuses (`rename-cut`, `worktree-rename-empty-original`).
- `low` `ports/vcs.py` `changed_files` docstring: paths come back literally from `-z` output and are never quoted, and a rename or copy reports only its destination. The `commit_paths` docstring in `ports/commit.py` now names its one widening: a named rename destination brings its original's deletion.
- Optional (M10, dropping `-M`, survived): a new test sets `diff.renames=false` and checks that a committed rename still reports only its new path. There is no `-c diff.renames=true` pin, because `-M` on the command line already forces rename detection.
- Mutants (scratch copy, restored): M9, M10, and seven against the fix. Those seven are: no `status.renames` pin; the original also passed to `git add`; a copy counted as a rename; no skip for staged deletions; a named original not deduplicated; no originals in the pathspec; originals taken from unnamed renames. All 9 were killed. Reverting `vcs_git.py` to the pre-fix commit fails 11 of the new tests.
- New tests: `test_vcs_git.py`: `test_commit_paths_commits_a_spaced_renames_source_deletion[git-mv|intent-to-add]`, `test_commit_paths_pairs_a_rename_under_an_operators_renames_off_config`, `test_commit_paths_commits_a_staged_deletion_without_re_adding_it`, `test_commit_paths_leaves_an_unnamed_rename_alone`, `test_worktree_checkpoint_commits_a_spaced_renames_source_deletion`, `test_commit_status_facts_names_rename_originals_and_staged_deletions_of_named_paths_only`, `test_changed_files_a_committed_rename_reports_only_the_new_path_under_an_operators_renames_off`, and the extended `test_porcelain_z_paths_drops_the_original_path_of_a_rename_or_copy` / `test_porcelain_z_paths_refuses_a_malformed_record`. `test_dispatch_supervisor_main_loop.py`: `test_finalize_sequence_commits_a_spaced_renames_source_deletion_against_real_git[git-mv|intent-to-add]` and `test_commit_pre_verify_wip_commits_a_spaced_renames_source_deletion_against_real_git`.
- 2026-10-04, delta review of the send-back fix (independent reviewer): verdict LAND; no HIGH or MEDIUM. The rename MEDIUM and both earlier LOWs are fixed. Two new LOWs, both fixed by the operator session before the push:
  - LOW-1: under `status.renames=false` / `diff.renames=false`, `changed_files` names both sides of a `git mv` (`A new`, `D old`) while `commit_paths`' pinned read sees one `R new\0old` record. The named original then went to `git add` and failed (fail-closed, never a false ok). `_commit_status_facts` now treats a named rename original as a staged deletion. Test: `test_the_finalize_path_commits_a_rename_under_an_operators_renames_off_config`, driven `changed_files` → `commit_paths` the way the finalize does; removing the rule fails it.
  - LOW-2: two parts of the fix had no test. N9: a rename original reaches `git commit --` as a literal pathspec (`:(top,literal)`); test `test_commit_paths_names_a_renames_awkward_original_literally` (a `:`-prefixed name and glob characters). N10: an absolute destination is made repo-relative; test `test_commit_paths_pairs_a_rename_named_by_an_absolute_path`. Each test fails with its mutant.
  - Information only: the named paths themselves still reach `git add` / `git commit` without literal magic, so a path that begins with `:` would fail. This predates 83.16; candidate follow-up: `--literal-pathspecs`.
