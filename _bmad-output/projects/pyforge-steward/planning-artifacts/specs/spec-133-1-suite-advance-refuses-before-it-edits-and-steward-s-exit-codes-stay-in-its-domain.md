---
title: '133.1: Suite advance refuses before it edits, and steward''s exit codes stay in its domain'
type: 'fix'
created: '2026-11-25'
status: 'in-review'
story: 133-1-suite-advance-refuses-before-it-edits-and-steward-s-exit-codes-stay-in-its-domain
spec: spec-pyforge-steward
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/suite_advance.py'
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/guards.py'
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py'
  - 'src/shared/packages/pyforge-steward/tests/unit/test_suite_advance.py'
  - 'src/shared/packages/pyforge-steward/tests/unit/test_guards.py'
  - 'src/shared/packages/pyforge-steward/tests/unit/test_cli.py'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `DW-steward-review-2026-11-24-1` reports four defects in steward's own duties, none re-traced by the session lead. (1) `steward suite advance` without `--dry-run` rewrites the recipe and builds, then its default publish step always returns not ok, so it leaves an edited checkout and opens no PR (`suite_advance.py:117-246,397-405`). (2) `keys exec` relays its child's raw exit code, so a child that exits 3 or 70 reads as steward's refusal or crash (`keys.py:1309-1310`). (3) `steward guards lacking --spec <missing file>` exits 70 on a user-input error (`guards.py:199-217`). (4) `main()` returns any integer a duty raises as `SystemExit` (`cli.py:2020-2026`).

**Approach:** Reproduce each defect first with a test that fails on the unchanged tree, and record the failing test's name in the Spec Change Log. Then: refuse the advance before its autotick when no publish path is configured, naming what is missing; project a `SystemExit` integer raised inside a duty that falls outside steward's documented domain to the internal-error code, naming the original code; catch `OSError` and `ValueError` in the guards duty and return a failed duty. A defect the tree does not reproduce, or that is the documented contract, is recorded here as not a defect and its source is left alone.

**Ruling (session lead, 2026-11-25): defect 2 is not a defect.** `keys exec` passing its child's exit code through is the documented contract: `spec-pyforge-steward/contract.md` § Exit codes ("`steward keys exec` passes its child's (both *not derived*: the code is the child's, not a constant)"), the steward `SKILL.md` ("`steward deploy nic` and `steward keys exec` pass their child's own non-zero exit through"), and `tests/unit/test_keys_ghe_credentials.py::test_exec_returns_the_childs_exit_code`, which pins a child exiting 3 returning 3. `keys.py` is unchanged, no clamp is added, and the `details["exit_code"]` path of `main()` stays as it is, since that is how the two documented pass-throughs (`keys exec`, `deploy nic`) reach it.

Ledger key: `133-1-suite-advance-refuses-before-it-edits-and-steward-s-exit-codes-stay-in-its-domain`.

### Living CAP citations

- spec-pyforge-steward CAP-22, CAP-1 and CAP-55 (realized, no text change); no AD moves.

## Boundaries & Constraints

**Always:**
- Reproduce before fixing: one failing test per defect, written first, kept as the regression test.
- Keep `main()` the only place that returns a process exit code; a duty requests a code, it never exits.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never change the advance's `--dry-run` path or make it publish; `anaconda upload` stays the operator's step.
- Never add an exit code to steward's documented domain, and never move Spec text; a fix that needs either stops and is reported.
- Never fix a defect that did not reproduce.
- Never clamp or rewrite the child exit code `keys exec` or `deploy nic` passes through; pass-through is the documented contract (ruling above).

## Acceptance Criteria

**Given** `DW-steward-review-2026-11-24-1` reports that `suite advance` without `--dry-run` rewrites the recipe and builds before a publish step that always returns not ok, that `keys exec` relays its child's raw exit code, that `guards lacking --spec <missing file>` exits 70, and that `main()` returns any integer a duty raises as `SystemExit`
**When** defects 1, 3 and 4 are each first reproduced by a test that fails on the unchanged tree, defect 2 is found to be the documented contract, and then the advance refuses before its autotick when no publish path is configured, a `SystemExit` integer raised inside a duty outside the documented domain is projected into it, and the guards duty reports an unreadable `--spec` as a failed duty
**Then** a refused advance leaves the recipe byte-identical and says what is missing, `guards lacking --spec` on a missing file exits 1 naming the path, and a `SystemExit` raised inside a duty never returns a code outside the documented domain
**And** `keys exec` still passes its child's exit code through, recorded on this spec as not a defect with the contract text and the test that pin it
**And** a defect the tree does not reproduce is recorded on this spec as not a defect and no source changes for it, and the row closes naming each outcome

- **AC1 — Defect 1: an advance with no publish path refuses before it edits.** The tests hold the recipe byte-identical after the refusal. Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_suite_advance.py -q
  ```

- **AC2 — Defect 2 is not a defect: `keys exec` still passes its child's exit code through.** Retired as a clamp by the lead's ruling of 2026-11-25; the criterion now holds the documented pass-through. The test runs a child that exits 3 and expects 3. Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pytest "src/shared/packages/pyforge-steward/tests/unit/test_keys_ghe_credentials.py::test_exec_returns_the_childs_exit_code" -q
  ```

- **AC3 — Defect 3: a missing `--spec` is a failed duty, not a crash.** Expected: exit 1, the path named on the output, no traceback.

  ```bash
  pixi run --frozen -e pyforge-steward pyforge steward guards lacking --spec /nonexistent/SPEC.md
  ```

- **AC4 — Defect 3, held by a test.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_guards.py -q
  ```

- **AC5 — Defect 4: a `SystemExit` raised inside a duty never returns a code outside the documented domain.** The tests raise `SystemExit` with 99, 4, 255 and -1 from inside a duty and expect 70 with the raised code named on stderr; the parser's own 0 and 2 keep their codes. A code a duty requests in `details["exit_code"]` is out of this criterion (the documented pass-throughs use it). Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_cli.py -q
  ```

- **AC6 — Steward's package half passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pyforge-steward-test
  ```

- **AC7 — Steward's live-tree half passes** (it holds the public contract's exit-code list against the code). Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pyforge-steward-live-test
  ```

- **AC8 — Not a defect is written down.** For each of the four defects, the Spec Change Log names either the test that failed on the unchanged tree, or the evidence that it is not a defect (the tree does not reproduce it, or the behaviour is the documented contract) and the words "not a defect". A defect recorded as not a defect has no AC above to meet. Expected: exit 0.

  ```bash
  grep -c -E "defect [1-4]: (reproduced|not a defect)" _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-133-1-suite-advance-refuses-before-it-edits-and-steward-s-exit-codes-stay-in-its-domain.md
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-22, CAP-1 and CAP-55 (realized, no text change); no AD moves.
- Dream: `docs/dreams/pyforge-steward.md`, the 2026-11-25 entry (the review's lower-severity defects are reproduced, then fixed or closed); operator ruling of 2026-11-25.
- Epic: Epic 133, minted with this story.
- Ledger key: `133-1-suite-advance-refuses-before-it-edits-and-steward-s-exit-codes-stay-in-its-domain`.
- Deferred-work row: `DW-steward-review-2026-11-24-1`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."133"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry and the operator's ruling of the same date. Not implemented.
- 2026-11-25: defect 1: reproduced and fixed - `tests/unit/test_suite_advance.py::test_a_live_advance_with_no_publish_path_refuses_before_it_edits` failed on the unchanged tree (the autotick ran and rewrote the recipe before the default publish stage answered not ok). `run_advance` now refuses after resolve, before the autotick, when the run is live and no publish hook is injected; the recipe stays byte-identical, the exit stays 1, and `--dry-run` is unchanged (`test_a_dry_run_with_no_publish_path_still_walks_the_whole_chain`).
- 2026-11-25: defect 2: not a defect - `keys exec` passing its child's exit code through is the documented contract: `spec-pyforge-steward/contract.md` § Exit codes, the steward `SKILL.md` § exit codes, and `tests/unit/test_keys_ghe_credentials.py::test_exec_returns_the_childs_exit_code` (a child exiting 3 returns 3) all state it. Lead's ruling of 2026-11-25; `keys.py` unchanged, no test file added, AC2 rewritten to hold the pass-through, and the surface no longer lists `keys.py` or `tests/unit/test_keys_exec_exit_code.py`.
- 2026-11-25: defect 3: reproduced and fixed - `tests/unit/test_guards.py::test_lacking_with_a_missing_spec_exits_1_not_70` failed on the unchanged tree (`FileNotFoundError` escaped the duty and `main()` returned 70), with `test_lacking_with_a_missing_spec_is_a_failed_duty_naming_the_path`, `test_lacking_with_a_spec_that_is_not_utf8_is_a_failed_duty` and `test_source_ground_with_a_missing_text_file_is_a_failed_duty_naming_the_path`. `GuardsDuty.run` catches `OSError` and `ValueError` on both reads (`lacking --spec`, `source-ground --text`) and returns a failed duty naming the path.
- 2026-11-25: defect 4: reproduced and fixed - `tests/unit/test_cli.py::test_a_system_exit_raised_inside_a_duty_never_returns_its_own_code` failed on the unchanged tree for 99, 4, 255 and -1 (`main()` returned the raised integer). `main()` now returns 70 and names the raised code on stderr when a `SystemExit` integer is outside the six documented codes; no exit code is added. Narrowed by the lead's ruling: the claim covers a raised `SystemExit` only, not a code a duty requests in `details["exit_code"]`.
- 2026-11-25: the story is implemented and in review. Owed outside this spec, reported to the lead: the row `DW-steward-review-2026-11-24-1` closes naming these four outcomes, and Story 133.1's sentences in `epics.md` and the Dream take the narrowed wording.
