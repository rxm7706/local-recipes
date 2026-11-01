---
title: "45.4: The ci-pause relay keeps steward's reason"
type: 'fix'
created: '2026-11-01'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/research/egm-audit-2026-11-01.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-45-1-doctor-names-every-ci-surface-that-drifted-stuck-or-outlived-its-review-date.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-45-3-the-fleet-picture-meta-test-names-every-probe-main-calls.md
  - docs/dreams/pyforge-doctor.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/ci_pause_drift.py
  - src/shared/packages/pyforge-doctor/tests/unit/test_sources_ci_pause_drift.py
  - src/shared/packages/pyforge-core/src/pyforge/core/dispatch.py
  - scripts/fleet_picture.py
  - tests/scripts/test_fleet_picture_ci_pauses.py
  - .claude/skills/conda-forge-expert/tests/meta/test_fleet_picture_main_attention.py
---

<intent-contract>

## Intent

**Problem:** CAP-89 promises that a CI surface steward reports as drifted, stuck or past its review date reaches the
operator in `fleet-picture`'s ATTENTION block with its owner and steward's reason. At `03a7aff5d9` the reason is lost:

- `_findings_for_row` (`src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/ci_pause_drift.py:136-178`)
  appends steward's `detail` last, after the switch and the owner, and only to a `drift` finding. The `overdue`
  finding never carries it, though `row_drift_and_overdue.json` has one; a `stuck` finding would drop one too.
- `fleet-picture` cuts each ATTENTION message at 110 characters (`scripts/fleet_picture.py:1310`), so a drift row's
  reason falls past the cut (`row_drift.json`: 69 characters precede a 63-character detail).
- No test asserts the detail on any fixture.
- DOC-M-D4's code residue: `ci_pause_drift_findings`' outer timeout (`scripts/fleet_picture.py:528-529`, 120 s)
  equals the source's inner dispatch bound (`_DISPATCH_TIMEOUT`, `ci_pause_drift.py:22`, 120 s), so a hung steward
  kills the probe first and the operator reads `could not check CI pauses` instead of the named
  `ci-pause-unobserved` WARN. And the refusal test's exit-127 case
  (`src/shared/packages/pyforge-doctor/tests/unit/test_sources_ci_pause_drift.py:134`) says a missing steward:
  `pyforge.core.dispatch` exits 2 (`EXIT_USAGE`) when it finds no steward distribution and 127 (`EXIT_NOT_FOUND`)
  when the mapped console script fails to launch.

These are the EGM audit's accepted findings DOC-M-Z3 and DOC-D-C5 (cluster DOC-CL-4), with DOC-M-D4's code residue,
recorded in `_bmad-output/projects/pyforge-doctor/planning-artifacts/research/egm-audit-2026-11-01.md`.

**Approach:**
1. In `_findings_for_row`, read a non-empty string `detail` once and put it on every finding the row yields:
   `drift`, `stuck` and `overdue`. The reason goes right after the surface and the rule, before the switch and the
   owner: `CI surface '<id>' drifted: <detail> (switch '<switch>', owner <owner>)`; the stuck and overdue messages
   take the same place for it and keep their own fields (`last_green_run`; `review_by` and the days overdue) after
   it. A row with no `detail` reads exactly as today. Steward sends no `detail` on `stuck` rows (the Spec's open
   question), so that branch is latent until steward does.
2. In `scripts/fleet_picture.py`, raise `ci_pause_drift_findings`' default `timeout` above the inner 120 s bound
   (150 s is enough), so the source's own `ci-pause-unobserved` WARN arrives before the probe gives up.
3. In the unit tests, assert the detail on every fixture that carries one, check that the reason sits inside the
   110-character cut, and correct the exit-127 and exit-2 refusal cases' stderr lines to what dispatch means by them.
4. Record the change on the chain: a decision on the station Spec's memlog that amends CAP-89's success, then the
   surface reconcile and scoped stamps.

### Living CAP citations

- **`spec-pyforge-doctor` CAP-89** (a CI surface that drifted, stuck or outlived its review date is a Doctor finding
  where the operator already looks): the intent already says each finding names "steward's `detail` when the row
  carries one"; the code honours it on one rule of three, after the cut. A fix, no new CAP.
- **No flag.** `type: fix` (`spec-feature-flag-governance` Q1).
- **Origin.** `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-11-01 (the EGM fleet audit) entry; the
  operator's acceptance of every audit recommendation, 2026-11-01 (memlog decision at line 875).

## Acceptance Criteria

- **AC1 — The reason on every rule.** On recorded fixtures, each `ci-pause-drift`, `ci-pause-stuck` and
  `ci-pause-overdue` finding whose row carries a non-empty `detail` names it right after the surface and the rule,
  before the switch and the owner; a finding whose row has no `detail` (or an empty or non-string one) is unchanged
  from today. A synthetic `stuck` row carrying a `detail` shows it.
- **AC2 — Inside the cut.** On every fixture whose row carries a `detail` (`row_drift.json`,
  `partial_with_drift.json`, both findings of `row_drift_and_overdue.json`, `row_unregistered_drift.json`), the
  detail starts within the message's first 50 characters; on `row_drift.json` the whole detail sits inside the first
  110 characters, the length `fleet-picture` keeps.
- **AC3 — Tests assert it.** `src/shared/packages/pyforge-doctor/tests/unit/test_sources_ci_pause_drift.py` asserts
  the detail on each fixture named in AC2 and the AC1 synthetic `stuck` row.
- **AC4 — A hung steward is named.** `ci_pause_drift_findings`' default `timeout` in `scripts/fleet_picture.py` is
  above `_DISPATCH_TIMEOUT`, and a test in `tests/scripts/test_fleet_picture_ci_pauses.py` asserts that order, so a
  timeout yields the `ci-pause-unobserved` watch line and not `could not check CI pauses`.
- **AC5 — The exit codes say what they mean.** The refusal test's exit-127 case names a console script that failed
  to launch, and its exit-2 case names dispatch finding no steward distribution; both still yield one
  `ci-pause-unobserved` WARN and no OK.
- **AC6 — Mutation.** Each change below fails a named test; restore each:
  - the detail dropped from the `drift` branch;
  - the detail dropped from the `overdue` branch;
  - the detail moved back after the owner (AC2 fails);
  - the outer timeout set back to 120 s (AC4 fails).
- **AC7 — Unchanged.** Every finding stays a WARN, the dispatcher exits 0 on every fixture, the OK row and the
  `ci-pause-unobserved` / `ci-pause-partial` findings keep their shape, the source has no `scripts/detectors.py` row
  and no `doctor check` membership. The Story 45.3 meta-test
  (`.claude/skills/conda-forge-expert/tests/meta/test_fleet_picture_main_attention.py`) and
  `tests/scripts/test_fleet_picture_ci_pauses.py` pass.
- **AC8 — The chain.** One `(decision)` line on
  `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md`, appended with
  `_bmad/scripts/memlog.py`, amends CAP-89's success for the DOC-CL-1 re-derive: the ATTENTION line names the row,
  its reason and its owner; steward's partial report is read from stdout (steward 103.7) with stderr as the older
  fallback; the source has no `scripts/detectors.py` row and never runs in `detectors-ci` (CAP-91's clause,
  mirrored). The per-finding events are already on that memlog (DOC-M-Z3 at line 878, DOC-D-C5 at line 899,
  DOC-M-D4 at line 885). `SPEC.md` is not hand-edited.
- **AC9 — Surface reconciled.** Each governed path this story changes is named in a reconcile event on every Spec
  `spec-surface-check` names for it (`spec-pyforge-doctor`; `spec-pyforge-core`, which co-governs station `src/`; the
  Specs that govern `scripts/fleet_picture.py`), then stamped scoped, one `--spec` each, from a clean tree after
  `git add`.

## Boundaries & Constraints

**Always:**
- Keep Story 45.1's HARD boundaries: the source reads `ci status --json` through `pyforge.core.dispatch` and
  `cli_bridge` and nothing else of steward's (no `pyforge.steward` import, no `gh`, no read of
  `docs/governance/ci-surfaces.yaml`, no copy of steward's verdict rules); every finding is a WARN (AD-2).
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Never change steward's report, schema or registry: a `detail` on `stuck` rows is steward's change, on steward's
  chain.
- Never widen `fleet-picture`'s 110-character cut to make the reason fit; the message order carries it.
- Never hand-edit `SPEC.md`; never stamp a Spec this story's diff does not touch.

## I/O & Edge-Case Matrix

| Row | Finding message (start) |
|---|---|
| `drift` with `detail` | `CI surface 'drift-live' drifted: live switch PAUSE_DRIFT_LIVE is true but registry declares live (switch …, owner …)` |
| `drift` past `review_by`, with `detail` | the drift message as above, and `CI surface '…' past review date: registry/live mismatch (switch …, owner …, review_by …, N day(s) overdue)` |
| `stuck` without `detail` | unchanged from today |
| `stuck` with `detail` (synthetic) | `CI surface '…' stuck: <detail> (switch …, owner …, last_green_run …)` |
| any row without `detail` | unchanged from today |
| steward hangs past 120 s | one `ci-pause-unobserved` WARN (timeout), shown as a watch line |

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-doctor` CAP-89 (Story 45.1, the ci-pause-drift source and its `fleet-picture`
  probe). No CAP is minted, and `SPEC.md` changes only through the DOC-CL-1 re-derive.

Parent: spec-pyforge-doctor CAP-89

- Audit findings carried: DOC-M-Z3, DOC-D-C5 (cluster DOC-CL-4) and DOC-M-D4's code residue; residue file
  `_bmad-output/projects/pyforge-doctor/planning-artifacts/research/egm-audit-2026-11-01.md`.
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-11-01 (the EGM fleet audit) entry.
- Epic: Epic 45 (`done`; this story reopens it through the roll-up, Story 41.5). The audit's cluster drafted it as
  Story 56.1 under a new Epic 56; it is keyed into its done epic instead (operator rule 2026-10-04: a fix story goes
  into its done epic), so no Epic 56 is minted.
- Ledger key: `45-4-the-ci-pause-relay-keeps-steward-s-reason`.
- Deps: none.
- Surface: `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/ci_pause_drift.py`,
  `src/shared/packages/pyforge-doctor/tests/unit/test_sources_ci_pause_drift.py`, `scripts/fleet_picture.py`,
  `tests/scripts/test_fleet_picture_ci_pauses.py`; `marshal-policy.toml` `[epic_surfaces]."45"` already covers each.
- Build mode: in-PR (built in the EGM audit landing PR, branch `egm-audit-2026-11`).
- Minted 2026-11-01 by marshal Story 113.7's landing.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor python -m pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_ci_pause_drift.py -q` — expected: pass (AC1–AC3, AC5).
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-live-test` — expected: pass (the test file is `live_tree`-marked, so this half runs it).
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_fleet_picture_ci_pauses.py .claude/skills/conda-forge-expert/tests/meta/test_fleet_picture_main_attention.py -q -p no:cacheprovider` — expected: pass (AC4, AC7).

**Run before the push (not dispatch gates):**
- The four mutations of AC6 — expected: each fails its named test. Restore each.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog events and the scoped stamps (AC9).
- `pixi run -e pyforge-guild detectors-ci` — expected: exit 0.
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0.

## Auto Run Result

Status: in-review (implemented 2026-11-01 in the EGM audit landing worktree, branch `egm-audit-2026-11`; not
committed, not stamped — the session owner commits, reconciles co-governors and stamps).

**What changed**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/ci_pause_drift.py`: `_findings_for_row` reads the
  row's `detail` once through a new `_reason()` helper (`": <detail>"` for a non-empty string, `""` otherwise) and
  puts it right after the surface and the rule on all three branches: `drifted{reason} (switch …, owner …)`,
  `stuck{reason} (switch …, owner …, last_green_run …)`, `past review date{reason} (switch …, owner …, review_by …,
  N day(s) overdue)`. A row with no detail, or an empty or non-string one, reads exactly as before.
- `scripts/fleet_picture.py`: `ci_pause_drift_findings`' default `timeout` 120 -> 150 s (above `_DISPATCH_TIMEOUT`,
  120 s), with a docstring naming why. The 110-character ATTENTION cut is unchanged.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_ci_pause_drift.py`: refusal cases now read exit 127 =
  `executable not found: 'steward' …` (console script failed to launch) and exit 2 = `station 'steward' is not
  installed in this environment; …` (dispatch found no steward distribution), with ids; new tests:
  `test_the_rows_detail_follows_the_rule_before_switch_and_owner` (5 cases: `row_drift.json`,
  `partial_with_drift.json`, both findings of `row_drift_and_overdue.json`, `row_unregistered_drift.json`; detail
  starts < 50, follows `": "`, precedes `(switch ` and `, owner `), `test_row_drift_keeps_its_whole_reason_inside_the_cut`
  (whole detail in `message[:110]`, exact message), `test_drift_past_review_by_names_the_reason_on_both_findings`,
  `test_a_stuck_row_with_a_detail_names_it` (synthetic stuck row), `test_a_row_without_a_string_detail_reads_as_before`
  (absent / `""` / null / int / list), `test_recorded_rows_without_a_detail_are_unchanged` (overdue, stuck).
- `tests/scripts/test_fleet_picture_ci_pauses.py`: `test_probe_timeout_outlasts_the_sources_dispatch_bound` (captures
  the `timeout` the probe passes to `subprocess.run` and asserts it exceeds `_DISPATCH_TIMEOUT`, read from the
  source file by `ast`, no `pyforge.doctor` import in that lane) and `test_main_names_a_hung_steward_as_unobserved`
  (the source's timeout WARN reaches ATTENTION as `ci-pause-unobserved: …`, never `could not check CI pauses`).
- Chain: `spec-pyforge-doctor/.memlog.md` gains one `(event)` surface reconcile naming the four paths and one
  `(decision)` amending CAP-89's success (AC8). `SPEC.md` not edited.

**Commands (exit codes)**
- `pixi run --frozen -e pyforge-doctor python -m pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_ci_pause_drift.py -q -p no:cacheprovider` — 0 (51 passed).
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_fleet_picture_ci_pauses.py .claude/skills/conda-forge-expert/tests/meta/test_fleet_picture_main_attention.py -q -p no:cacheprovider` — 0 (11 passed).
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — 0 (unit+meta 1213 passed, all segments green).
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-live-test` — 0 (2699 passed; 4 passed).
- `ruff check` / `ruff format --check` (pyforge-guild's ruff, the doctor package's `[tool.ruff]`) on the two doctor
  files — 0 / 0. `scripts/` and `tests/scripts/` sit under no repo ruff config or lint lane; no new finding on the
  changed lines.
- `mypy --cache-dir .mypy_cache/pyforge-guild -p pyforge.doctor` (the lint-types doctor slice, from the package
  dir, `-e pyforge-guild`) — 0 (no issues in 50 source files).
- `grep -n "ci.pause.drift\|ci_pause" scripts/detectors.py` — 1 (no row; AC7).

**AC6 mutations (each applied, run, restored)**
- detail dropped from the `drift` branch — exit 1: `test_the_rows_detail_follows_the_rule_before_switch_and_owner`
  [drift, partial-drift, drift-and-overdue:drift, unregistered-drift], `test_row_drift_keeps_its_whole_reason_inside_the_cut`,
  `test_drift_past_review_by_names_the_reason_on_both_findings`.
- detail dropped from the `overdue` branch — exit 1: `…before_switch_and_owner[drift-and-overdue:overdue]`,
  `test_drift_past_review_by_names_the_reason_on_both_findings`.
- detail moved back after the owner (drift branch) — exit 1: `…before_switch_and_owner` [4 drift cases],
  `test_row_drift_keeps_its_whole_reason_inside_the_cut`, `test_drift_past_review_by_names_the_reason_on_both_findings`.
- outer timeout set back to 120 s — exit 1: `test_probe_timeout_outlasts_the_sources_dispatch_bound`.
- (extra) detail dropped from the `stuck` branch — exit 1: `test_a_stuck_row_with_a_detail_names_it`.

**Left for the session owner (not run here, by the task's rules):** AC9's co-governor reconciles
(`spec-pyforge-core`, and the Specs `spec-surface-check` names for `scripts/fleet_picture.py` and
`tests/scripts/test_fleet_picture_ci_pauses.py`), the scoped stamps after `git add`, `lint-types` in full,
`spec-surface-check`, `detectors-ci` and the full `pr-preflight`.

## Spec Change Log

- 2026-11-01: minted `backlog` (in-PR) from the EGM audit's cluster DOC-CL-4 (findings DOC-M-Z3, DOC-D-C5; DOC-M-D4's
  code residue) at the operator's acceptance of every recommendation, 2026-11-01; marshal Story 113.7's landing.
- 2026-11-01: `in-progress` -> `in-review` — implemented as the Auto Run Result records; AC1–AC8 met in the
  worktree; AC9's stamps and co-governor reconciles left to the session owner.
- 2026-11-01: `in-review` -> `done` — independent review passed (Review Triage Log); AC9's stamps stay the session
  owner's.

## Review Triage Log

- 2026-11-01 — reviewer: independent session (did not write this code; judged the diff against this spec, not the
  Auto Run Result). **Verdict: pass.**
  - Read: `git diff HEAD` of `ci_pause_drift.py`, `test_sources_ci_pause_drift.py`, `scripts/fleet_picture.py`,
    `tests/scripts/test_fleet_picture_ci_pauses.py` and the two `spec-pyforge-doctor/.memlog.md` lines; the dispatch
    exit codes in `src/shared/packages/pyforge-core/src/pyforge/core/dispatch.py` (`EXIT_USAGE` 2 on a
    `DispatchError`, whose not-installed text the exit-2 case now quotes; `EXIT_NOT_FOUND` 127 on a `ProcessError`,
    `executable not found: …` in `pyforge/core/process.py`); the fixtures carrying `detail` (exactly the four AC2
    names); `scripts/detectors.py` (no ci-pause row, AC7); the one caller of `ci_pause_drift_findings`
    (`fleet_picture.main`, its 110-character cut unchanged).
  - AC1–AC5, AC7, AC8 hold in code and tests: the reason sits right after the rule on all three branches, a
    non-string or empty `detail` reads as before (5 cases), the synthetic stuck row names it, the default timeout is
    150 s against `_DISPATCH_TIMEOUT` 120.0, the memlog decision amends CAP-89 as AC8 words it.
  - Commands (exit codes read from `$?`): `pytest …/test_sources_ci_pause_drift.py` 0 (51 passed);
    `pytest tests/scripts/test_fleet_picture_ci_pauses.py …/test_fleet_picture_main_attention.py` (pyforge-guild) 0
    (11 passed); `pyforge-doctor-test` 0 (1213 passed); `pyforge-doctor-live-test` 0 (2728 + 4 passed);
    `python scripts/lint_types.py ruff-format` 0 and `mypy` 0; `lint_types.py ruff` 1 for pyforge-doctor, but only
    on `test_sources_pages_liveness.py` (Story 48.3's file), none on this story's files; `spec-surface-check` 0.
  - AC6 mutations, each on a scratch mirror of the package and `scripts/` (`PYTHONPATH` to the mirror's `src`),
    restored each time: detail dropped from `drift` → 6 failed (`…before_switch_and_owner` ×4,
    `…whole_reason_inside_the_cut`, `…names_the_reason_on_both_findings`); from `overdue` → 2 failed
    (`…[drift-and-overdue:overdue]`, `…on_both_findings`); moved after the owner → the same 6; outer timeout 120 →
    `test_probe_timeout_outlasts_the_sources_dispatch_bound`; (extra) dropped from `stuck` →
    `test_a_stuck_row_with_a_detail_names_it`.
  - Failures: none.
  - Left to the session owner (this workflow reserves them; not judged here): AC9's `spec-pyforge-core`
    co-governor reconcile and the scoped stamps after `git add`; `detectors-ci` and the full `pr-preflight`.
