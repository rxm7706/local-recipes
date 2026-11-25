---
title: '121.1: Teardown compares tips, a bad environment is a usage error, and a required check is read on every page'
type: 'fix'
created: '2026-11-25'
status: 'done'
story: 121-1-teardown-compares-tips-a-bad-environment-is-a-usage-error-and-a-required-check-is-read-on-every-page
spec: spec-pyforge-marshal
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/teardown_preserve.py'
  - 'src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/main.py'
  - 'src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/forge_gh.py'
  - 'src/shared/packages/pyforge-marshal/tests/unit/test_teardown_preserve.py'
  - 'src/shared/packages/pyforge-marshal/tests/unit/test_init_teardown_preserve.py'
  - 'src/shared/packages/pyforge-marshal/tests/unit/test_cli.py'
  - 'src/shared/packages/pyforge-marshal/tests/unit/test_forge_gh.py'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-marshal.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Row `DW-marshal-review-2026-11-24-1` carries three defects. (1) `scan_teardown_unpreserved`'s branch loop in `core/teardown_preserve.py` skips the home branch whenever `remote_branch_exists` is true, without checking that anything holds the local tip, and a `resolve_ref` error is read as nothing to preserve, so `teardown --force` can remove a branch holding unpushed commits (traced, not run). (2) `cli/main.py`'s `main()` catches no `FlagConfigError`, so `PYFORGE_ENVIRONMENT=bogus marshal status` exits 1 under a traceback, and 1 is the UNEVALUABLE rung. (3) `GhForge.check_run_status` in `adapters/forge_gh.py` reads one page of check runs, so a failed required check past the first 30 reads as not yet concluded; its sibling `check_runs()` pages.

**Approach:** Reproduce each defect with a failing test first. Then: (1) run the commit-level preserve check on every branch, the home branch included, and report a tip that cannot be resolved as an unpreserved item so the teardown refuses. The check reads local refs only and fails closed: a tip is safe only when a local remote-tracking ref, `origin/main` ancestry or a preserve tag holds it; origin is not asked live, and the `MRS-TEARDOWN-006` message names the remedy (`git fetch origin`, or `--force --abandon <branch>`); (2) catch `FlagConfigError` in `main()` as usage (one stderr line, `EXIT_USAGE`) and add a last-resort handler that returns the ERROR rung through `exit_code_for`; (3) build `check_run_status` on the paged read `check_runs()` uses. A defect the tree does not reproduce is recorded in this spec's change log as not a defect, and its code is left alone.

Ledger key: `121-1-teardown-compares-tips-a-bad-environment-is-a-usage-error-and-a-required-check-is-read-on-every-page`.

### Living CAP citations

- spec-pyforge-marshal CAP-287, CAP-304 and CAP-210 (realized, no text change); no AD moves; a fix, no new CAP.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag: it restores the fail-closed teardown scan, the frozen exit domain and the full required-check read.
- **Origin.** `DW-marshal-review-2026-11-24-1` (written by doctor Story 61.1 from the review of main `7da08791f3`).

## Boundaries & Constraints

**Always:**
- Write the failing test before the fix, one per defect, and record what each showed.
- Read every verdict from its exit code, never through a pipe.
- Keep the newest-run-wins rule of `check_run_status` and its `None` for a check that has no run.
- Name the remedy in the `MRS-TEARDOWN-006` refusal: `git fetch origin`, or `--force --abandon <branch>`.

**Never:**
- Never add an exit code, a flag, or a row to `contract.md`.
- Never construct an exit code outside `core/verdict.py`'s projection.
- Never let a home branch with a tip a local remote-tracking ref holds refuse a teardown.
- Never read a same-named branch on origin as proof: a tip no local remote-tracking ref, `origin/main` ancestry or preserve tag holds refuses, even when origin holds it, until a `git fetch origin`.
- Never change code for a defect the tree does not reproduce.

## Acceptance Criteria

**Given** the preserve scan skips the home branch whenever a branch of the same name is on origin, without comparing tips, and reads a `resolve_ref` error as nothing to preserve; `main()` catches no `FlagConfigError`, so `PYFORGE_ENVIRONMENT=bogus marshal status` exits 1, the UNEVALUABLE rung, under a traceback; and `check_run_status` reads one page of check runs, so a required check past the first 30 reads as not yet concluded
**When** each defect is first reproduced by a failing test, then the scan runs its commit-level check on every branch and reports a tip it cannot resolve as unpreserved work, `main()` returns the usage code with one stderr line for a `FlagConfigError` and the ERROR rung for any other exception, and `check_run_status` reads every page through the call `check_runs()` already pages with
**Then** `teardown --force` refuses a home branch whose tip no local remote-tracking ref, `origin/main` ancestry or preserve tag holds, naming `git fetch origin` and `--force --abandon <branch>` as the remedy, and proceeds on a tip a local remote-tracking ref holds, a bad `PYFORGE_ENVIRONMENT` exits 2 with no traceback and no invocation exits outside the frozen domain, and a failed required check on a later page reads `failure`
**And** a defect the tree does not reproduce is recorded in the story spec as not a defect and its code is left alone, and marshal's suite passes

- **AC1 — Defect 1: the scan compares tips and refuses on a tip it cannot resolve.** The tests cover a home branch on origin with a local tip no local remote-tracking ref holds (reported, the message naming `git fetch origin` and `--force --abandon <branch>`), the same branch with a tip a local remote-tracking ref holds (not reported), a tip origin holds while no local remote-tracking ref does (refused until `git fetch origin`, then torn down), and a `resolve_ref` failure (reported). Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/unit/test_teardown_preserve.py src/shared/packages/pyforge-marshal/tests/unit/test_init_teardown_preserve.py -q
  ```

- **AC2 — Defect 2: a bad environment is a usage error.** The test drives `main()` with `PYFORGE_ENVIRONMENT=bogus` and asserts 2, and a handler that raises an unexpected exception returns the ERROR rung. Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/unit/test_cli.py -q
  ```

- **AC3 — Defect 2, on the installed command.** Expected: exit 2, with no `Traceback` on stderr.

  ```bash
  PYFORGE_ENVIRONMENT=bogus pixi run --frozen -e pyforge-guild marshal status
  ```

- **AC4 — Defect 3: a required check is read on every page.** The test serves a failed run of the named check on the second page and asserts `failure`. Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/unit/test_forge_gh.py -q
  ```

- **AC5 — The public contract did not move.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/meta/test_public_contract.py -q
  ```

- **AC6 — Marshal's suite passes, both halves.** Expected: exit 0 from each.

  ```bash
  pixi run --frozen -e pyforge-marshal pyforge-marshal-test
  pixi run --frozen -e pyforge-marshal pyforge-marshal-live-test
  ```

- **AC7 — A defect the tree does not reproduce is not a defect.** If the failing test for a defect cannot be made to fail on the unfixed tree, this spec's change log records it as not a defect with the command that showed it, its code is unchanged, and its criterion above is met by the test that pins the behaviour as found.

</intent-contract>

## Binding

- Capabilities: spec-pyforge-marshal CAP-287, CAP-304 and CAP-210 (realized, no text change); no AD moves.
- Dream: `docs/dreams/pyforge-marshal.md`, the 2026-11-25 entry (teardown, the front door and the required-check read fail closed) under *A stranger reads the chain*; operator ruling of 2026-11-25.
- Epic: Epic 121, minted with this story.
- Ledger key: `121-1-teardown-compares-tips-a-bad-environment-is-a-usage-error-and-a-required-check-is-read-on-every-page`.
- Deferred work: closes `DW-marshal-review-2026-11-24-1`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."121"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry and the operator ruling of the same date; `ready-for-dev`.
- 2026-11-25: lead ruling after review: the scan stays fail closed on local refs (a tip is safe only when a local remote-tracking ref, `origin/main` ancestry or a preserve tag holds it), the `MRS-TEARDOWN-006` message names the remedy, and the Never clause, the Then line and AC1 say "a tip a local remote-tracking ref holds" where they said origin's branch of that name.
- 2026-11-25: defect 1: reproduced and fixed - `pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/unit/test_teardown_preserve.py src/shared/packages/pyforge-marshal/tests/unit/test_init_teardown_preserve.py -q` exited 1 on the unchanged tree: `test_scan_reports_home_branch_on_origin_whose_local_tip_origin_does_not_hold` (the home branch was not reported), `test_scan_resolve_ref_failure_reports_branch_as_unpreserved` (no item for an unresolvable tip) and the real-git `test_teardown_force_refuses_home_branch_ahead_of_origin[on]` (`teardown --force` printed `removed: True` and deleted a branch one commit ahead of origin). The remedy wording was added the same way: those three and `test_teardown_force_refuses_until_a_fetch_when_no_local_remote_tracking_ref_holds_the_tip[on]` failed (4 failed, exit 1) until the message named `git fetch origin` and `--force --abandon <branch>`.
- 2026-11-25: defect 2: reproduced and fixed - `PYFORGE_ENVIRONMENT=bogus pixi run --frozen -e pyforge-guild marshal status` exited 1 under an `UnknownEnvironmentError` traceback on the unchanged tree, and `test_bad_pyforge_environment_is_a_usage_error_with_one_stderr_line` and `test_handler_raising_an_unexpected_exception_returns_the_error_rung` in `tests/unit/test_cli.py` failed against the unchanged `cli/main.py` (the exceptions left `main()`).
- 2026-11-25: defect 3: reproduced and fixed - `pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/unit/test_forge_gh.py -q` exited 1 on the unchanged tree: `test_check_run_status_reads_a_failed_required_check_on_a_later_page` read `None` for a failed run on page 2 of 101, and `test_check_run_status_raises_when_a_later_page_fails_never_a_partial_answer` did not raise.
- 2026-11-25: the story is implemented and in review; all three defects reproduced, none closed as not a defect (AC7 not exercised).
- 2026-11-25: closed. PR #2385 merged as 080f89c4df (`Merge pyforge-steward/133-1 into main`) after its 51 CI checks passed and the full local `pr-preflight` exited 0 on 48 lanes; an independent reviewer read the diff against this spec before the merge, its findings were applied and re-reviewed.
