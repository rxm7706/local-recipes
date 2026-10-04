---
title: "70.2: Seed check honours recorded skips, and every verb records directory entries"
type: 'fix'
created: '2026-10-04'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-70-1-seed-check-judges-the-paths-the-manifest-means-never-its-placeholders.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-86-1-seed-honours-recorded-skips-refuses-shared-manifest-paths-and-pins-directory-entries.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/check.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/adopt.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/update.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/init.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/skips.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/fs.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/apply/run.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/seed.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 70.1 (#1831) was built and reviewed on 2026-10-04. The build recorded three findings outside its surface (its Review Triage Log), and the review added two lows. `DW-marshal-86-1` tracks the directory half. Line numbers below are from main at `afaa41af48`.

- **Skips:** `seed/verbs/check.py::run_check` never reads `state.skips`. So when an operator has recorded a skip for an artifact (Story 86.1 made `adopt` and `update` honour it on every run, `verbs/skips.py::with_recorded_skips`, :261), check still reports the absent artifact as HARD `artifact-missing`, with the remedy "run `marshal seed adopt`", and adopt would skip it. The absent branch is at check.py:458-470.
- **Test helper:** `tests/unit/test_seed_verbs_update.py::_shipped_entries_for_slug` (:1591) renders `{{ slug }}` with its own `str.replace` (:1599). It should call `model.manifest.render_slug_paths`, the one renderer `init` and `check` use.
- **Directories (`DW-marshal-86-1`):** a directory entry (a manifest path ending in `/`, `ManifestEntry.is_directory`, defined as create-if-missing by Story 86.1's `DIRECTORY_BEHAVIOR`) cannot be applied or recorded:
  - The post-apply record reads the target as a file: `verbs/adopt.py::_managed_artifact_after_apply` (:1010, `target.read_text` at :1074, also used by `init`, `verbs/init.py:404`), and `verbs/update.py`'s own copy (:1045, `_read_materialized_text` at :1087). A directory that a commit really created therefore raises `IsADirectoryError`, and `seed init` against the full packaged manifest cannot write state.
  - The commit dispatchers look for staged file bytes at the target (`_staged_bytes_for`, adopt.py:678 and update.py:704), and `seed/fs.py` has no guarded directory-creation primitive. So an absent directory entry is never created. This is adopt's documented known limitation (2), at adopt.py:176.
  - `seed/apply/run.py`'s rollback removes a created target only `if target.is_file()` (:248-249), so a directory created by an apply that then rolls back is left behind (`DW-10-3-3`).
- **Review L2:** `cli/seed.py::run_check` (around :489-508) reports a slug that `render_slug_paths` refuses as a `UsageError` (exit 2), whatever its source. That is right for an explicit `--project`. But a bad `BMAD_ACTIVE_PROJECT` or a bad `_bmad/custom/.active-project` marker is ambient: the operator did not pass it, so the check should not fail on it.
- **Review L4:** `cli/seed.py::_target_in_loop_home` (:225) has no test for a symlinked target path, or for a branch whose name only begins like a loop branch (such as `loopback-fix`).

**Approach:**
- Check reads `state.skips` from the state it already reads. An absent entry whose path a recorded skip matches yields no `artifact-missing`, and the report names it as skipped (INFO, never `failing`). Use the one matcher `apply_skips` uses. If `check.py`'s leaf import contract forbids importing `verbs.skips`, move that pure matcher to a module both may import, and move the contract's pin with it.
- `_shipped_entries_for_slug` calls `render_slug_paths`.
- Add a never-write-guarded directory-creation primitive and an empty-directory removal primitive to `seed/fs.py` (P-01: never `os` or `shutil` on a target path).
- Give the three commit dispatchers (adopt, init, update) a directory branch that creates an absent directory entry through the new primitive.
- In both post-apply record builders, record a directory entry without reading it as a file. Choose the record shape within `seed/state/schema.json`, and if the schema must change, follow its own migration rule.
- The apply runner removes, on rollback, a directory that this apply created, once what the run wrote beneath it has been restored. `DW-10-3-3`'s wider residue (parent directories that `atomic_write_bytes` creates, and a file replaced by a directory) stays open. Add a progress note to that row citing this story.
- In `cli/seed.py`, a slug from the environment or the marker that `render_slug_paths` refuses leaves the templated entries unjudged, each with INFO `slug-unresolved` naming the refused slug and its source. An explicit `--project` keeps the `UsageError`.
- Pin `_target_in_loop_home` with a symlinked target and a near-miss branch name.

Ledger key: `70-2-seed-check-honours-recorded-skips-and-every-verb-records-directory-entries`.
Type / Effort / Deps: fix / M / S-70.1.

### Living CAP citations

- `spec-pyforge-marshal` CAP-279 (FR-225, Story 70.1), with Story 86.1 (recorded skips and directory entries) and Story 10.3 (the transactional apply). This is a defect of shipped behaviour, so it mints no new CAP. Under `spec-feature-flag-governance` Q1, a `fix` needs no flag.

## Acceptance Criteria

- Given a state that records a skip matching an absent manifest entry's path When `marshal seed check` runs Then there is no `artifact-missing` for it, an INFO finding names the skip, and `failing` is unaffected. Removing the skip read fails the test (mutation).
- Given a skip pattern that `adopt` honours When `check` judges the same absent entry Then the two verbs agree, because one matcher decides both
- Given `_shipped_entries_for_slug` When the update tests run Then it renders through `render_slug_paths`, with no `str.replace` of `{{ slug }}` left in that file
- Given an absent directory entry in the plan When `seed adopt`, `seed init` or `seed update` applies Then the directory is created through `seed/fs.py`'s guarded primitive and the state records the entry with no `IsADirectoryError`. `seed init --slug demo` against the full packaged manifest writes state, and `seed check --project demo` then reports no directory entry as missing.
- Given a directory entry under a never-write subtree When it would be created Then the guard refuses, as a file write is refused
- Given an apply that creates a directory and then fails a later action When it rolls back Then the directory it created, and everything it wrote beneath it, is gone
- Given `BMAD_ACTIVE_PROJECT` or the target's marker naming a slug that `render_slug_paths` refuses When `seed check` runs with no `--project` Then it exits on its ordinary verdict, with INFO `slug-unresolved` for each templated entry naming the slug and its source; the same slug passed as `--project` still exits 2
- Given a target reached through a symlink to a `loop/<slug>` worktree When `_target_in_loop_home` reads it Then it returns `True`. Given a worktree on `loopback-fix` Then it returns `False`. Dropping the path resolution, or matching `loop` without its slash, fails a test (mutation).
- Given this story lands When `DW-marshal-86-1` is read Then it is closed with a `resolution:` naming Story 70.2 and a `verified:` line citing the `path:line` it fixed

## Boundaries & Constraints

**Always:**
- Keep one skip matcher, one `{{ slug }}` renderer and one never-write guard.
- Every new write or removal goes through `seed/fs.py`.
- A new `FindingType` gets its row in `src/shared/packages/pyforge-marshal/docs/finding-remedy-reference.md`, which `tests/meta/test_finding_remedy_reference_sync.py` requires.

**Never:**
- Never exempt this repository by name: it stays SC-02's oracle (Story 12.2).
- Never let a recorded skip hide a present artifact's drift. This story covers absent entries only.
- Never relax the explicit `--project` refusal.
- Never close `DW-10-3-3` here. Only its created-directory case is fixed.

</intent-contract>

## Binding

- Parent: Story 70.1 (#1831), its build findings and its review (L2, L4), with `DW-marshal-86-1`.
- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-04 (seed skips and directories) entry.
- Epic: Epic 70, which reopens. The sync rolls `epic-70` from `done` to `in-progress` while this story is open, and back to `done` when it lands. The operator ruled on 2026-10-04 that a fix goes into its own epic and reopens it, never a new epic, and doctor Story 41.5 lets `ledger-regression` accept the reopen.
- Policy: Epic 70 gains an `[epic_surfaces]` entry in this chain: the default surface plus the station deferred-work ledger (this story closes `DW-marshal-86-1` and notes `DW-10-3-3`) and every Spec memlog.
- Ledger key: `70-2-seed-check-honours-recorded-skips-and-every-verb-records-directory-entries`.
- Ledger status at mint: `backlog`.
- Deps: S-70.1 (done).
- Minted 2026-10-04 at the operator's request.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- On the primary checkout, `pixi run --frozen -e pyforge-guild marshal seed check --json` — expected: `result.failing: false` and exit 0, as after Story 70.1.
- `pixi run --frozen -e pyforge-guild deferred-work-check` — expected: exit 0 with `DW-marshal-86-1` closed.

## Review Triage Log

- No review has run yet.
