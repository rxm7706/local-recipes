---
title: "101.1: The landing line lists every surface the CI master switch pauses"
type: 'fix'
created: '2026-10-14'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-100-1-a-landing-records-which-ci-surfaces-were-paused-when-it-merged.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-103-1-steward-ci-status-reports-the-master-switch-and-every-surface-it-pauses.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/landing_ci_pauses.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_landing_ci_pauses.py
  - src/shared/packages/pyforge-marshal/tests/meta/test_no_steward_internals_import.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/data/ci-status-schema.json
  - docs/governance/ci-surfaces.yaml
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** with the master switch `PAUSE_ALL_CI` on, every job that reads it is skipped, and a dispatch landing's
`ci_pauses_at_merge` will name the master but none of the surfaces it skipped. Story 100.1's Residual risk names this
as its own follow-up ("when steward adds the master's value, a follow-up story lists every surface under it"), and so
does the `spec-pyforge-marshal` memlog's 2026-10-14 decision on CAP-292's open question. Line numbers are at
`22e5c19c28`.

- **Marshal's rule.** `row_counts_as_paused_at_merge` (`core/landing_ci_pauses.py:28`) skips the synthetic
  `unregistered:` and `unregistered-workflow:` rows, lists every `paused-manually` row, skips `opt-in-off` and
  `retired`, and lists any other row whose `live_switch_value`, stripped and lower-cased, is `true`.
  `surfaces_from_envelope` (`:42`) sorts the ids. By CAP-292's design it reads no `verdict`, and it reads no master
  state.
- **Steward's answer.** Steward Story 103.1 gives `steward ci status --json` two things. Its key read `backlog` at
  `22e5c19c28`; it merged on 2026-10-14 as `a6cf663539`, while this chain was open:
  - one row, `master:PAUSE_ALL_CI`, with `declared_state` `live`, `live_switch_value` the variable's value, and
    `verdict` `drift` while it is `true`;
  - one optional boolean row property, `paused_by_master`. It is `true` when the master is `true` and the row is
    gated, whatever the row's verdict. Steward derives "gated" from the workflow files with the CI-surface gate's own
    parser: a `workflow` row when every job's `if:` reads the master, a `ci-job` row when its job's does, a `ci-step`
    row when its step's or its job's does. The master row, the `unregistered:` rows and every `value`, `retired` and
    `paused-manually` row carry `false`.

  A gated row that would otherwise read `live` reads `paused`, and `drift`, `stuck` and `overdue` keep their
  precedence. The verdict enum does not change. At `22e5c19c28` `data/ci-status-schema.json` had no
  `paused_by_master`; since `a6cf663539` it carries it as an optional boolean. Read at `a6cf663539`,
  `_row_gated_by_master` (`ci.py:493`) leaves out only `value` rows, `paused-manually` rows and a row whose workflow
  has no jobs, and `_apply_master_overlay` (`:539`) sets `paused_by_master` whatever the verdict but turns only a
  `live` verdict into `paused`. Its checked-in `tests/fixtures/ci_status_master_on.json` holds three gated `paused`
  rows, two ungated `live` workflow rows, a `value` row, a `paused-manually` row and the master row.
- **What 100.1 makes of it.** With 103.1 alone, the master row is declared `live` with the value `true`, so 100.1's
  rule lists `master:PAUSE_ALL_CI`. It lists no gated row, because each one's own switch is off. 103.1's own Residual
  risk names this gap as marshal's.
- **The opt-ins.** `docs/governance/ci-surfaces.yaml` declares seven `enable` rows, all `opt-in-off`: six `ci-job`
  rows and one `ci-step` row in `.github/workflows/platform-ci.yml`, in the jobs `build-platform-image`,
  `gke-portability-smoke`, `ocp-portability-smoke`, `air-gap-parity` and `golden-path-promotion`. Each of those jobs'
  `if:` reads `vars.PAUSE_ALL_CI`. So under 103.1 all seven carry `paused_by_master: true` while the master is on,
  whether or not their own opt-in is on. An opt-in that is off would not have run anyway, and its verdict stays
  `opt-in-off`. One that is on (`live_switch_value` `true`) reads `drift` (declared `opt-in-off`, enable switch
  `true`), and it is the master that stops it.

**Approach:**
- **The rule, extended (pure, in `core/landing_ci_pauses.py`).** A row is listed when 100.1's rule lists it, or when
  its `paused_by_master` is the JSON boolean `true` (`is True`) and it is not an opt-in that is off. An opt-in that is
  off is a row whose `declared_state` is `opt-in-off` and whose `live_switch_value`, stripped and lower-cased, is not
  `true`. The `unregistered:`, `unregistered-workflow:` and `retired` skips still run first. A missing or `false`
  `paused_by_master` adds nothing, and so does any value that is not a boolean, the string `"true"` included.
- **Nothing else moves.** Story 100.1 built all of these, and they stay as built: the adapter
  (`adapters/steward_cli.py`), the one read after the check wait, the `unknown` path, `envelope_is_valid`, the
  record's keys (`state`, `surfaces`, `fetched_at`), the PR-body line's format, the outcome and finalize copies and the
  flag `pyforge.marshal.landing_ci_pauses`. The master row stays listed, so the line says the master was on.
- **Steward's real payload.** A marshal test reads steward 103.1's checked-in
  `src/shared/packages/pyforge-steward/tests/fixtures/ci_status_master_on.json` as a file, never by import. Steward's
  own test keeps that file identical to what `run_status` prints, so the marshal rule is checked against the real
  envelope as well as hand-built rows.

**Rejected:**
- **Every `paused_by_master` row.** It names the seven opt-in surfaces while they are off, and they never run unless
  switched on.
- **`verdict == "paused"`.** A gated row that is also `stuck`, `overdue` or `drift` on its own state reads that verdict
  instead, which is CAP-292's reason not to read the verdict. An opt-in that is on reads `drift`.
- **Excluding opt-ins by `verdict == "opt-in-off"`.** A `stuck` opt-in that is off would then be listed. Declared state
  and switch value are what 100.1 already reads.
- **Marshal reads the master and the workflow files.** That makes marshal a second reader of the pause state, against
  CAP-292's constraint. Steward derives gating with the parser the `ci-surface-gates` detector uses.
- **A second key in the record for the master's surfaces.** The master row in `surfaces` already says the master was
  on, and the record stays the one object CAP-292 defines.

Ledger key: `101-1-the-landing-line-lists-every-surface-the-ci-master-switch-pauses`.
Type / Effort / Deps: fix / S / — (a cross-station gate on steward Story 103.1, held as this story's `blocked` ledger
row).

### Living CAP citations

- **`spec-pyforge-marshal` CAP-292** (FR-239; Story 100.1, done): a dispatch landing records which CI surfaces were
  paused when it merged. This story makes the record complete under the master switch, as the Spec's open question
  and the memlog's 2026-10-14 decision foresaw. It mints no CAP and changes no `SPEC.md` text.
- **`pyforge-steward:CAP-166`** (steward Story 99.3, with Story 103.1's master row and `paused_by_master`): the
  envelope this reads. Always cite it qualified; marshal has its own CAP-166.
- **AD-4:** the rule is a pure function in `core/`. **AD-8:** an unread envelope is still `unknown`, never `[]`.
  **AD-71:** the CI estate stays steward's, and marshal reads its CLI's JSON.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag of its own. With
  `pyforge.marshal.landing_ci_pauses` off, no steward call is made, exactly as today.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, the 2026-10-14 (the master switch's surfaces at merge)
  entry; Story 100.1's Residual risk; the operator's ask of 2026-10-14, "chain it here".

## Acceptance Criteria

- **AC1 — The master's surfaces are listed.** A unit test feeds `surfaces_from_envelope` an envelope with the master
  `true`, holding these rows:
  - the `master:PAUSE_ALL_CI` row (`declared_state` `live`, `live_switch_value` `"true"`, `verdict` `drift`,
    `paused_by_master` `false`);
  - with `paused_by_master` `true`: two rows declared `live` whose own switch is off, one with the verdict `paused`
    and one with `stuck`; a row declared `paused` whose switch is `"true"`, verdict `overdue`; a row declared `live`
    whose switch is `"true"`, verdict `drift`; and an opt-in declared `opt-in-off` whose switch is `"true"`, verdict
    `drift`.

  The list is every one of those ids, sorted, each once. A parametrized test of `row_counts_as_paused_at_merge` covers
  each row kind alone.
- **AC2 — Not listed.** In the same envelope none of these is listed: an opt-in declared `opt-in-off` whose switch is
  `"false"` or `null`, with `paused_by_master` `true` and verdict `opt-in-off`; a row declared `live` whose own switch
  is off, with `paused_by_master` `false`; a `retired` row with `paused_by_master` `true`; an `unregistered:PAUSE_FOO`
  row with `paused_by_master` `true`; a row declared `live` whose own switch is off and whose `paused_by_master` is the
  string `"true"`, `1` or `null`.
- **AC3 — No field, no change.** No envelope in today's `test_landing_ci_pauses.py` carries `paused_by_master`, and
  each one's record is unchanged. Every existing test in that file passes with no assertion weakened or deleted, the
  flag-off run of Story 100.1's AC7 included.
- **AC4 — The line and the record agree.** Through `execute_dispatch_land`, with the flag on and the steward fake
  returning AC1's envelope, the journal's `ci_pauses_at_merge.surfaces` holds AC1's ids. The body passed to
  `forge.update_pr` ends with one `CI paused at merge:` line naming the same ids in the same order.
- **AC5 — Steward's own payload.** A test reads
  `src/shared/packages/pyforge-steward/tests/fixtures/ci_status_master_on.json` (steward 103.1's AC6 fixture) as a
  file. `envelope_is_valid` is true. `surfaces_from_envelope` contains `master:PAUSE_ALL_CI` and every row whose
  `verdict` is `paused` and whose `paused_by_master` is `true`. It contains no row whose `paused_by_master` is `false`
  unless 100.1's rule alone lists it. The test fails, and never skips, when the file is absent.
- **AC6 — One reader.** `tests/meta/test_no_steward_internals_import.py` passes unedited: no module imports
  `pyforge.steward`, and no module but `adapters/steward_cli.py` invokes steward. No marshal module under `src/` names
  `PAUSE_ALL_CI` or `ci-surfaces.yaml`, or reads a workflow file.
- **AC7 — Mutation.** Each change below fails a named test, and the Auto Run Result records which:
  - ignoring `paused_by_master` (AC1);
  - listing an opt-in that is off (AC2);
  - accepting the string `"true"` for the field (AC2);
  - dropping an opt-in that is on (AC1);
  - listing a gated row by `verdict == "paused"` alone (AC1's `stuck` row).

## Boundaries & Constraints

**Always:**
- Read `paused_by_master` from steward's envelope through Story 100.1's adapter and its one read per landing, as
  100.1 reads every other field.
- Accept only the JSON boolean `true` for the field.
- Keep 100.1's record, its PR-body line and its `unknown` path unchanged for an envelope without the field.
- Reconcile every governed path on the memlogs of the Specs that govern it (`spec-pyforge-marshal`, and
  `spec-pyforge-core`, which co-governs station `src/`), then stamp scoped (AGENTS.md pre-PR item 5).

**Never:**
- Never import `pyforge.steward`. Never read `PAUSE_ALL_CI`, `gh`, the Actions API,
  `docs/governance/ci-surfaces.yaml` or a workflow file from marshal, and never decide in marshal which jobs read the
  master.
- Never refuse, delay or re-verdict a landing because of the master, and never wait on CI for it.
- Never add a key to `ci_pauses_at_merge` or change the PR-body line's format; never edit steward or its fixture.
- Never flip `pyforge.steward.ci_pause_control`, `pyforge.marshal.landing_ci_pauses` or `PAUSE_ALL_CI`.

**Residual risk:**
- Under the master the line names every gated surface, which can be most of the registry's 49 pause rows declared
  `live` or `paused`. It stays one line.
- With steward's flag `pyforge.steward.ci_pause_control` off (its default), every landing still records `unknown`, as
  under Story 100.1.
- A steward older than 103.1 sends no `paused_by_master` and no master row, so the record is 100.1's.

## I/O & Edge-Case Matrix

| Row, with the master `true` | `paused_by_master` | Listed |
|---|---|---|
| `master:PAUSE_ALL_CI`, declared `live`, value `"true"`, verdict `drift` | `false` | yes (100.1's rule) |
| declared `live`, own switch off, verdict `paused` | `true` | yes |
| declared `live`, own switch off, verdict `stuck` | `true` | yes |
| declared `paused`, own switch `"true"`, verdict `overdue` | `true` | yes (100.1's rule too) |
| declared `live`, own switch `"true"`, verdict `drift` | `true` | yes (100.1's rule too) |
| declared `opt-in-off`, switch `"true"`, verdict `drift` | `true` | yes |
| declared `opt-in-off`, switch `"false"` or `null`, verdict `opt-in-off` | `true` | no |
| declared `live`, own switch off, verdict `live` (no job, or not every job, reads the master) | `false` | no |
| `paused-manually` | `false` | yes (100.1's rule) |
| `retired` | `true` or `false` | no |
| `value` row (`PLATFORM_CI_REGISTRY`) | `false` | no |
| `unregistered:<NAME>` or `unregistered-workflow:<file>` | any | no |
| any row whose field is `"true"` (a string), `1` or `null` | not the boolean `true` | 100.1's rule only |
| an envelope with no `paused_by_master` (a steward before 103.1) | absent | 100.1's rule only |
| the master unset or `"false"` | `false` on every row | 100.1's rule only |
| steward unreadable | n/a | `unknown`, as under 100.1 |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-marshal` CAP-292 (FR-239), shipped by Story 100.1. No CAP is minted, and no
  `SPEC.md` text changes. Reads `pyforge-steward:CAP-166` as steward Story 103.1 extends it.
- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-14 (the master switch's surfaces at merge)
  entry.
- Epic: Epic 101 (new), minted with this story, because Epic 100 is `done`. `epic-101` and `epic-101-retrospective`
  are minted with it.
- Ledger key: `101-1-the-landing-line-lists-every-surface-the-ci-master-switch-pauses`.
- Ledger status at mint: `blocked`. It is a cross-station gate on steward Story 103.1
  (`103-1-steward-ci-status-reports-the-master-switch-and-every-surface-it-pauses`): the field and the fixture this
  story reads exist only from 103.1 on. Marshal's `Deps:` parser is station-local, so the gate is this ledger row,
  and the operator flips it to `backlog` once 103.1 is `done` on `main` (precedents: marshal 74.2, herald 38.1,
  doctor 42.1). 103.1 merged on 2026-10-14 (`a6cf663539`) while this chain was open, so the flip can follow this
  chain's merge.
- Deps: — (cross-station, see above).
- Surface: `marshal-policy.toml` `[epic_surfaces]."101"`, added with this mint.
- Minted 2026-10-14 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, with AC1–AC6's tests (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-marshal python -m pytest src/shared/packages/pyforge-marshal/tests/unit/test_landing_ci_pauses.py src/shared/packages/pyforge-marshal/tests/meta/test_no_steward_internals_import.py -q` — expected: pass.
- `git grep -n -e PAUSE_ALL_CI -e ci-surfaces.yaml -- src/shared/packages/pyforge-marshal/src` — expected: no match, exit 1 (AC6).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps.
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.
- The five mutations of AC7 — expected: each fails its named test. Restore each.
- `git diff origin/main...HEAD --stat` — expected: outside `_bmad-output/` and `scripts/.spec-surface-baseline.json`, only `core/landing_ci_pauses.py` and `tests/unit/test_landing_ci_pauses.py` under `pyforge-marshal`, and nothing under `pyforge-steward`.

## Spec Change Log

- 2026-10-14: minted from the Dream entry of 2026-10-14 (the master switch's surfaces at merge) at the operator's ask
  "chain it here", the follow-up that Story 100.1's Residual risk names. `type: fix`, no flag, no CAP. The key is
  minted `blocked` on steward Story 103.1.
- 2026-10-17 (implementation): the Verification list's `python3 scripts/spec_surface_reconcile.py` becomes
  `pixi run --frozen -e pyforge-guild python scripts/spec_surface_reconcile.py`. The host's `python3` is 3.12 and
  cannot parse the script (`except FileNotFoundError, NotADirectoryError:` is Python 3.14 syntax, PEP 758), so the
  bare form exits 1 with a `SyntaxError` before checking anything; the pixi form runs it on 3.14. No AC, boundary or
  surface changes. Two Verification items are not the builder's: `pr-preflight` is run by the orchestrator at
  landing, and with no commit yet `git diff origin/main...HEAD --stat` is read as `git diff --cached --stat
  origin/main`.
- 2026-10-17 (review fixes, on `d9b740ffdf`): the independent review passed with five nits (Review Triage Log), and
  all five are fixed in the same surface. One behaviour change, in `core/landing_ci_pauses.py`: a row whose `id` is
  not a non-empty string is skipped by `row_counts_as_paused_at_merge`, so `surfaces_from_envelope` no longer raises
  `KeyError` out of `ci_status_record` (documented "Never raises") and the landing. Steward's schema requires `id`,
  so a valid steward never sends such a row; the I/O matrix gains no row, since the record for every valid envelope
  is unchanged. The other four are tests. The review's observation outside this story, steward's
  `_row_gated_by_master` reading retirement from `kind`, is recorded in steward's deferred-work ledger as
  `DW-steward-101-1-2`, not the `DW-steward-101-1-1` the coordinator named: that id already belongs to steward's own
  Story 101.1 row (the master switch had no row, promoted to steward 103.1), and the ledger keys each row
  `DW-steward-<story>-<n>` by its source story, so the next free id under a "101.1" source is `-2`.

## Review Triage Log

- **2026-10-17, independent review of `d9b740ffdf` (scratchpad `r101/review.md`): PASS, no blocker or should-fix,
  five nits.** Each is fixed on the same branch (the review-fix pass), and each fix is pinned by a test and a
  mutation (Verification run, review fixes, below).
  1. *(nit)* The spec's rejected design (opt-ins left out by `verdict != "opt-in-off"`, the review's M9) passed every
     test. **Fix:** an unlisted row `gated.opt-in-off-stuck` (declared `opt-in-off`, switch `"false"`, verdict
     `stuck`, `paused_by_master` true); that mutation now fails 5 tests.
  2. *(nit)* The opt-in clause's strip and lower-case was untested (the review's M8 survived). **Fix:** a listed row
     `gated.opt-in-on-padded` (declared `opt-in-off`, switch `" TRUE "`, `paused_by_master` true); `== "true"` in the
     opt-in clause now fails 4 tests.
  3. *(nit)* AC6's second half (no marshal `src/` module names `PAUSE_ALL_CI` or `ci-surfaces.yaml`) had no standing
     test, only the Verification `git grep`. **Fix:** `test_101_1_ac6_no_marshal_src_module_names_the_master_switch_or_the_registry`
     scans `pyforge/marshal/**/*.py` (with a non-vacuity assert); `tests/meta/test_no_steward_internals_import.py`
     stays unedited. Naming either string in a src module fails it.
  4. *(nit)* `surfaces_from_envelope` indexed `row["id"]`, so an id-less row that counts as paused raised `KeyError`.
     **Fix:** the rule skips a row whose `id` is not a non-empty `str`;
     `test_101_1_a_row_without_a_string_id_is_skipped` (5 rows: no id, no id with the field, `""`, `None`, `7`) and
     `test_101_1_rows_without_an_id_never_raise_out_of_the_record` (through `StewardCli.ci_status_record`). Story
     100.1's `str(row.get("id", ""))` with no check fails 6 tests; a check without the non-empty test fails 2.
  5. *(nit)* Steward 103.7's `test_steward_cli_partial_envelope_on_stdout_is_a_read_carrying_partial` called
     `ci_status_record` with no `binary_path`, so outside `pixi run` it resolved no `pyforge` and failed. **Fix:**
     its four calls pass `binary_path="/bin/true"`, as the neighbouring tests do. HEAD's version fails under a bare
     python (exit 1); the fixed one passes (exit 0). Story 100.1's `test_steward_cli_unknown_paths` makes the same
     binary-less calls, but it passes either way (each asserts `unknown`), and the Epic keeps 100.1's tests unedited,
     so it is left as is.
  - *Observation outside this story (steward):* recorded as `DW-steward-101-1-2` (Spec Change Log, above).

## Implementation Result

Hand-built on branch `chain-marshal-101-1-master-switch-surfaces-2026-10-17`, from baseline `05fed5cb19`. The diff is
for an independent review against this spec, not against this summary.

- **`core/landing_ci_pauses.py`:** `row_counts_as_paused_at_merge` keeps the `unregistered:` /
  `unregistered-workflow:` and `retired` skips first, then lists a row whose `paused_by_master` `is True` unless it
  is declared `opt-in-off` with its own switch (stripped, lower-cased) not `true`; after that, Story 100.1's rule runs
  unchanged (`paused-manually` listed, `opt-in-off` skipped, otherwise the row's own switch). The module and function
  docstrings say why. `surfaces_from_envelope`, `envelope_is_valid`, the record, the PR-body line, the adapter and
  the flag are untouched.
- **`tests/unit/test_landing_ci_pauses.py`:** the existing tests are unedited (the module docstring and the one
  import line gain Story 101.1 and `StewardCiStatusOutcome`). New:
  - `test_101_1_row_rule_under_the_master_switch` (AC1/AC2, 18 cases): every AC1 row and every AC2 row alone, plus
    the matrix's `paused-manually`, ungated `retired`, `value` and `unregistered-workflow:` rows;
  - `test_101_1_ac1_master_surfaces_are_listed_sorted_once` and `test_101_1_ac2_unlisted_rows_stay_out_of_the_same_envelope`:
    one envelope holding AC1's six rows interleaved with AC2's eight;
  - `test_101_1_ac3_no_field_or_false_field_keeps_story_100_1_record`: `_sample_envelope()` carries no
    `paused_by_master`, and the same rows with `paused_by_master: false` (the master off) give the identical record;
  - `test_101_1_ac4_journal_record_and_pr_line_agree`: `execute_dispatch_land` with the flag on and
    `StewardCli.ci_status` faked to return AC1's envelope, so the real `ci_status_record` → `record_from_envelope`
    path builds the record; one steward read, the journal record is `{state: read, surfaces: AC1's ids, fetched_at}`,
    and the last `update_pr` body holds one `CI paused at merge:` line, ending with the same ids in the same order;
  - `test_101_1_ac5_steward_master_on_fixture`: reads
    `src/shared/packages/pyforge-steward/tests/fixtures/ci_status_master_on.json` as a file (`Path(__file__)`-anchored,
    `assert … is_file()`, so it fails, never skips); `envelope_is_valid`; the master row and the three gated
    `paused` rows listed; each `paused_by_master: false` row listed exactly when Story 100.1's rule alone (the row
    without the field) lists it; two non-vacuity asserts.
- **AC6:** `tests/meta/test_no_steward_internals_import.py` unedited and green; `git grep -n -e PAUSE_ALL_CI -e
  ci-surfaces.yaml -- src/shared/packages/pyforge-marshal/src` exits 1. The `.github/workflows` mentions under marshal's
  `src/` are three pre-existing docstrings and comments (`context_bootstrap.py`, `init.py`, `substrate.py`), no read.
- **AC7 — mutations (the Auto Run Result AC7 names).** Run against a scratch copy (`git archive HEAD` of the marshal
  package and the steward fixture, the two changed files copied in), the mutated line restored after each and checked
  with `filecmp` (byte-identical every time):
  - ignoring `paused_by_master` (`if False:`): 6 failed, among them `test_101_1_ac1_master_surfaces_are_listed_sorted_once`,
    `test_101_1_ac4_…`, `test_101_1_ac5_…` and the row cases `gated.live-paused`, `gated.live-stuck`, `gated.opt-in-on`;
  - listing an opt-in that is off (the opt-in clause dropped): 5 failed, among them
    `test_101_1_ac2_unlisted_rows_stay_out_of_the_same_envelope` and the row cases `gated.opt-in-off-false`,
    `gated.opt-in-off-null`;
  - accepting the string `"true"` (`str(field).strip().lower() == "true"`): 4 failed, among them
    `test_101_1_ac2_…` and the row case `field.string-true`;
  - dropping an opt-in that is on (`declared != "opt-in-off"` alone): 3 failed, among them `test_101_1_ac1_…` and the
    row case `gated.opt-in-on`;
  - listing a gated row by `verdict == "paused"` alone (in place of the field): 4 failed, among them `test_101_1_ac1_…`
    and the row case `gated.live-stuck`;
  - extra, not in AC7: `== True` in place of `is True` (accepts `1`): 4 failed, among them `test_101_1_ac2_…` and the
    row case `field.int-one`.
- **Not changed:** steward and its fixture, `adapters/steward_cli.py`, `dispatch_land.py`, the finalize and supervisor
  copies, the flag tree, `pixi.toml`, `pixi.lock`, `environment.yaml`, `.github/workflows/pyforge-station-tests.yml`.
  The new test's one read outside marshal's package (steward's fixture) is already on marshal's trigger list: the
  `changes` step's `'src/shared/packages/pyforge-*/tests/*'` pathspec and the `on.*.paths` glob
  `'src/shared/packages/pyforge-*/tests/**'`; steward's `test_station_tests_trigger_map.py` derives the read
  (`real_derivation()["marshal"]` names it, from `test_landing_ci_pauses.py`) and passes, so Story 98.1's guard needs
  no workflow edit.

## Verification run (2026-10-17)

At the branch's working tree (baseline `05fed5cb19` plus this change, every path staged); every exit code read
directly, never through a pipe.

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`: exit 0, 13193 passed, 20 skipped.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test`: exit 0, 130 passed, 3 skipped.
- `pixi run --frozen -e pyforge-marshal python -m pytest …/tests/unit/test_landing_ci_pauses.py
  …/tests/meta/test_no_steward_internals_import.py -q`: exit 0, 455 passed (the 23 new Story 101.1 cases among the
  file's 45).
- `COVERAGE_GATES_STATIONS=marshal pixi run --frozen -e pyforge-marshal python scripts/coverage_gates_ci.py --suites
  unit --paths-file <the staged paths>`: exit 0; `core/landing_ci_pauses.py` 91% against the 80% unit floor.
- `git grep -n -e PAUSE_ALL_CI -e ci-surfaces.yaml -- src/shared/packages/pyforge-marshal/src`: exit 1, no match (AC6).
- `pixi run --frozen -e pyforge-steward python -m pytest …/pyforge-steward/tests/meta/test_station_tests_trigger_map.py
  -q`: exit 0, 45 passed (Story 98.1's guard; the new steward-fixture read is derived and fires marshal's job).
- `pixi run --frozen -e pyforge-guild lint-types`: exit 0 (ruff, ruff format and mypy over every package,
  target-version, precommit-config).
- `pixi run --frozen -e pyforge-guild` `chain-completeness-check`, `dream-chain-check`, `dreams-hygiene-check`,
  `deferred-work-check`, `ledger-regression-check`, `story-status-check`, `flag-gate-check`,
  `chain-currency-sweep-check` (re-run after the memlog entries), `tea-playwright-check`, `llms-full-check`: each
  exit 0.
- `pixi run --frozen -e pyforge-guild python scripts/ci_surface_gates.py --check`: exit 0.
- `pixi run --frozen -e pyforge-guild detectors-ci`: exit 0 (after the scoped stamps).
- Spec surface: memlog entries on `spec-pyforge-marshal` and `spec-pyforge-core` (both under `pyforge-marshal`,
  the two Specs `spec-surface-check` named); `git add`; one scoped stamp each,
  `--write-baseline --spec pyforge-marshal/spec-pyforge-marshal` and
  `--write-baseline --spec pyforge-marshal/spec-pyforge-core` (each exit 0; the baseline moves only the two files'
  hashes and the two memlog hashes); `pixi run --frozen -e pyforge-guild spec-surface-check`: exit 0;
  `pixi run --frozen -e pyforge-guild python scripts/spec_surface_reconcile.py`: exit 0.
- `git diff --cached --stat origin/main`: outside `_bmad-output/` and `scripts/.spec-surface-baseline.json`, only
  `core/landing_ci_pauses.py` and `tests/unit/test_landing_ci_pauses.py` under `pyforge-marshal`; nothing under
  `pyforge-steward`.
- Not run here: `pr-preflight` (the orchestrator runs it at landing).

## Verification run (2026-10-17, review fixes)

On `d9b740ffdf` plus the review fixes (every path staged); every exit code read directly, never through a pipe.
`test_landing_ci_pauses.py` now holds 54 tests (32 for Story 101.1: the row-rule test has 20 cases, plus 5 id-less
rows, the record test and the AC6 scan).

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`: exit 0, 13202 passed, 20 skipped.
- The two focused files (`test_landing_ci_pauses.py`, `tests/meta/test_no_steward_internals_import.py`) under
  `pixi run --frozen -e pyforge-marshal python -m pytest -q`: exit 0, 464 passed; and under a bare python (the env's
  interpreter with `PIXI_ENVIRONMENT_NAME`, `CONDA_PREFIX` and `PIXI_PROJECT_ROOT` unset and no `pyforge` on `PATH`,
  `which pyforge` exit 1): exit 0, 464 passed.
- `COVERAGE_GATES_STATIONS=marshal pixi run --frozen -e pyforge-marshal python scripts/coverage_gates_ci.py --suites
  unit --paths-file <the staged paths>`: exit 0; `core/landing_ci_pauses.py` 91% against the 80% floor.
- `pixi run --frozen -e pyforge-guild lint-types`: exit 0.
- `deferred-work-check`, `story-status-check`, `chain-currency-sweep-check` (each `pixi run --frozen -e pyforge-guild`,
  re-run after the memlog entries): each exit 0. `detectors-ci`: exit 0.
- Mutations, on a scratch copy under a bare python, each restored and byte-compared (`filecmp`, identical every time):
  - nit 1, the rejected design (`paused_by_master is True and verdict != "opt-in-off"`): 5 failed, among them
    `test_101_1_ac2_unlisted_rows_stay_out_of_the_same_envelope` and the row case `gated.opt-in-off-stuck`;
  - nit 2, the opt-in clause's switch read without strip or lower-case (`live_switch_value == "true"`): 4 failed,
    among them `test_101_1_ac1_…` and the row case `gated.opt-in-on-padded`;
  - nit 3, `PAUSE_ALL_CI` in a comment of `core/journal.py`, and `docs/governance/ci-surfaces.yaml` in a comment of
    `core/landing_ci_pauses.py`: each failed `test_101_1_ac6_no_marshal_src_module_names_the_master_switch_or_the_registry`;
  - nit 4, Story 100.1's `str(row.get("id", ""))` with no check: 6 failed (the five
    `test_101_1_a_row_without_a_string_id_is_skipped` cases and `test_101_1_rows_without_an_id_never_raise_out_of_the_record`);
    the check without its non-empty test: 2 failed (the `""` case and the record test);
  - nit 5: HEAD's `test_steward_cli_partial_envelope_on_stdout_is_a_read_carrying_partial` under a bare python exit 1
    (1 failed); the fixed test exit 0 (1 passed);
  - AC7's five, re-run: 8, 7, 5, 5 and 6 failed, each failing its named test as before.
- Spec surface: memlog entries on `spec-pyforge-marshal` and `spec-pyforge-core` (the two Specs `spec-surface-check`
  named; steward's deferred-work ledger is not a governed path), `git add`, one scoped stamp each
  (`--write-baseline --spec pyforge-marshal/spec-pyforge-marshal`, `--write-baseline --spec pyforge-marshal/spec-pyforge-core`,
  each exit 0; the baseline moves only the two files' hashes and the two memlog hashes);
  `pixi run --frozen -e pyforge-guild python scripts/spec_surface_reconcile.py`: exit 0; `spec-surface-check`, last:
  exit 0.
