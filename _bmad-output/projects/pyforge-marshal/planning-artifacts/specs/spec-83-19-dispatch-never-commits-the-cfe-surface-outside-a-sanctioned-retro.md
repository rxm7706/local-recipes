---
title: "83.19: Dispatch never commits the CFE surface outside a sanctioned retro"
type: 'fix'
created: '2026-10-03'
status: 'in-review'
baseline_revision: '325ca80bfb'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/worktree_checkpoint.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_ruff_format.py
  - src/shared/packages/pyforge-testing-kit/src/pyforge/testing_kit/branch_diff_guard.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Doctor Story 41.1's session edited `.claude/skills/conda-forge-expert/tests/meta/test_spec_surface_check.py`, and the supervisor's auto-checkpoints committed it as `wip: 41.1 (auto-checkpoint)` (59bb1effb3, 121e11b963). Every station's "CFE not replaced" meta-test runs `branch_diff_guard.unsanctioned_commits`, which refuses any branch commit that touches the conda-forge-expert surface unless its subject starts `retro:` / `retro(<scope>):` and the CFE `CHANGELOG.md` moves in the same commit. A `wip:` checkpoint can never satisfy that, so any dispatched story that touches the CFE surface can only land after a history rewrite. The supervisor's own finalize and ruff-format commits have the same problem, and a session's own commit can carry CFE paths too.

**Approach:** Dispatch's own commits (auto-checkpoint, ruff format, finalize, spec-surface reconcile) leave the CFE surface out, using the guards' own pathspec and CHANGELOG path (one owner, shared with `branch_diff_guard`). At finalize, CFE-surface changes are committed once, in a commit whose subject starts `retro(cfe):`, and only when the CFE `CHANGELOG.md` is among them; otherwise verification refuses, naming the Rule 2 requirement. Verification also runs `unsanctioned_commits` over `origin/main..HEAD` and refuses, naming each offending commit, before anything is pushed.

Ledger key: `83-19-dispatch-never-commits-the-cfe-surface-outside-a-sanctioned-retro`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- the dispatch commit path (Stories 34.2, 28.24, 83.9). A defect of shipped behaviour, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a session that edits a file under the CFE surface When the supervisor auto-checkpoints, ruff-formats or finalizes Then none of those commits contains a CFE-surface path
- Given the CFE edit plus a CFE `CHANGELOG.md` entry When the supervisor finalizes Then the CFE paths land in exactly one commit whose subject starts `retro(cfe):`, and `unsanctioned_commits` over the branch is empty
- Given a CFE edit with no CFE `CHANGELOG.md` change When dispatch verifies Then it refuses, naming the Rule 2 requirement, and nothing is pushed
- Given a branch that already carries a commit touching the CFE surface outside a sanctioned retro When dispatch verifies Then it refuses naming that commit
- Given a story that touches no CFE path When dispatch runs Then its commits are unchanged
- Given the exclusion or the verification check removed When its new tests run Then they fail (mutation)

## Boundaries & Constraints

**Always:** Read the CFE pathspec and CHANGELOG path from one owner shared with `branch_diff_guard`; test with a real git repository.

**Never:** Never rewrite a branch's history. Never weaken `unsanctioned_commits` or the station guards. Never touch the CFE surface in this story.

</intent-contract>

## Binding

Parent: Story 34.2 (worktree auto-checkpoints) and Story 28.24 (the supervisor finalize).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-03 (night, last) entry.
Ledger key: `83-19-dispatch-never-commits-the-cfe-surface-outside-a-sanctioned-retro`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 at the operator's request ("yes chain both fixes").

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- 2026-10-04: Implementation review against AC — checkpoint/finalize/ruff paths exclude CFE; verify runs `commit_pending_cfe_retro` then `unsanctioned_commits` (`MRS-GATE-020`). Unit fixtures in `test_dispatch_cfe_commit.py`. Verification: `pyforge-marshal-test`, `pyforge-deps-test`, `lint-types`, `spec_surface_reconcile.py` green.
- 2026-10-04 (landing review, rework): dispatch verification refused on `pyforge-marshal-coverage-gate` (`dispatch_verify.py` 76.1% unit, `core/dispatch_verification.py` 78.0%, floor 80%) and code review found two more defects. Dispositions:
  - **Runtime dependency on the testing kit — fixed.** `pyforge-marshal` declared `pyforge-testing-kit` as a runtime dependency (`pyproject.toml`, `pixi.toml`, `pixi.lock`) to import its CFE constants and `branch_diff_guard.unsanctioned_commits` from `src/`. All three are back to `origin/main`'s bytes, and no marshal `src/` module imports `pyforge.testing_kit`. This also clears the chain-currency trap (DW-marshal-86-8-1): marshal's `pyproject.toml` no longer moves, so `fleet_scan` does not re-date marshal's code stage.
  - **One owner — option (b), a pinned mirror; option (a) rejected.** The testing kit already depends on `pyforge-core`, so moving the constants into core was mechanically possible. It is still the wrong home. `spec-pyforge-core` admits only measured, named primitives ("No new primitive earns a place on one caller"), retires every copy in the story that extracts one ("Retire the copy in the story that extracts it"), and puts the kit out of scope ("Not `pyforge-testing-kit`"). The CFE path is A's recipe-factory layout, not a kernel primitive, and an extraction would have meant a new core CAP plus rewriting the four stations' guard tests in this story. Instead the surface's owner is `pyforge.testing_kit.cfe_surface`, beside `branch_diff_guard`, and marshal keeps a runtime mirror (`core/dispatch_cfe_commit.py`). `test_dispatch_cfe_commit.py` imports the kit at test time, which is already a test dependency in the `pyforge-marshal` environment through its meta-tests. It asserts the mirror's constants and `RETRO_SUBJECT` equal the kit's and `branch_diff_guard._RETRO_SUBJECT`, path classification agrees, and marshal's branch check returns exactly `branch_diff_guard.unsanctioned_commits`'s verdict over nine real-git scenarios.
  - **Coverage — root cause fixed, not padded.** At runtime, `findings_for_unsanctioned_cfe_commits` called the kit's `unsanctioned_commits`, whose `_require_ref` calls `pytest.skip` when `refs/remotes/origin/main` is missing. Every `evaluate_dispatch_verification` unit test on a non-git fixture was therefore silently SKIPPED (42 of 74 in `test_dispatch_verification.py`), leaving lines 638-835 uncovered. In production, a missing base would have raised pytest's `Skipped` (a `BaseException`) through the supervisor. `dispatch_verify.check_unsanctioned_cfe_commits` now reads `git log --no-merges --full-diff --name-only <base>..HEAD` and `git diff --name-only HEAD` over the surface through the injected `ProcessPort`. A failed read refuses with `MRS-GATE-009` and never reads clean. The unit fakes read the new `git diff` as clean, as they already did `git log` (Story 83.17). Result: `dispatch_verify.py` 93%, and the coverage gate passes for all nine touched modules.
  - **Gap found in review — fixed.** `dispatch_supervisor._commit_pre_verify_wip` (Story 85.2, the verify-fix loop's "marshal: pre-verify WIP checkpoint") committed every dirty path, CFE included. A CFE-touching story in a fix turn would then have looped on the retriable `MRS-GATE-020`. It now leaves the surface out, and a leftover CFE-only tree is not a refusal, because the re-verification commits it as `retro(cfe):` or refuses on Rule 2.
  - **Simplified.** `core/dispatch_ruff_format.py` and `core/dispatch_verification.py` are back to main. The ruff commit stages only `src/shared/packages/pyforge-*/**.py` paths, so its added filter could never remove anything: an equivalent mutant. AC1's ruff leg is now pinned by a real-git test in which the formatter also rewrites a CFE file. The second `CFE_COMMIT_GATE_CODE` was an unused duplicate. The blocked-halt patch filter stays: an `*attempted-change*.patch` can land inside the CFE tree, and a test covers that.
  - **Testing kit.** `cfe_surface.py` is trimmed to the surface definition (the unused `partition_paths`, `CFE_UNSANCTIONED_PATHSPEC` and `RULE2_RETRO_SUBJECT_HINT` are gone). `test_branch_diff_guard.py` adds a test that `unsanctioned_commits` reads both halves under a tuple pathspec. A pre-existing failure in the kit suite was red on main since 2026-09-30: `test_flags.py::test_flagd_tree_has_the_platform_trees_shape` broke when Story 76.2 added a `metadata` clock block to every platform flag. It is fixed by comparing the evaluation shape: core checks the clock only when a tree is composed with overlays, and a `flagd_tree` never is. It went unseen because no CI lane runs the kit's own suite; that is flagged as a separate task.
  - **Mutation (scratch copies of `src/`, never this worktree): 17/17 killed.** The 17 mutants: the checkpoint, finalize, pre-verify WIP and blocked-halt exclusions, plus the blocked-halt patch filter and the pre-verify leftover check; the ruff commit staging all dirt; the Rule-2 CHANGELOG check; the verify retro commit; the verify branch check; the retro-subject and CHANGELOG halves of the branch rule; its dirty-path half; `--no-merges`; fail-open on a git error; and two drifts of the mirrored surface.

## Auto Run Result

Status: in-review
Blocking condition: —
