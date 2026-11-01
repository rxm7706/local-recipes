---
title: "13.2: A TEA skip on a missing ref reaches the report"
type: 'fix'
created: '2026-11-01'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/.memlog.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-13-1-the-tea-advisory-diffs-from-the-remote-tracking-ref.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-11-2-tea-test-review-is-a-warden-advisory-finding.md
  - src/shared/packages/pyforge-warden/src/pyforge/warden/tea_advisory.py
deferred: []
---

<intent-contract>

## Intent

**Problem:** CAP-23's success line checks only the argv (`--base refs/remotes/origin/main`), not the effect. When that
ref does not exist, TEA's `tea-test-review` exits 2 (ENV_ERROR); `run_tea_test_review` records
`tea-test-review exited 2 -- verdict not trusted` as the result's `skipped_reason`, and then
`TeaAdvisoryScanPlugin._contribute` drops it at its `if not result.ran: return` (`src/shared/packages/pyforge-warden/src/pyforge/warden/tea_advisory.py`, about
:350-351 at `03a7aff5d9`). A report from a scan whose TEA run skipped therefore looks exactly like a report from a scan
with TEA never enabled. EGM audit 2026-11-01 finding WAR-M-Z6 (a Nit; the gap check narrowed it to CAP-23), accepted
by the operator on 2026-11-01; residue `_bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md`.

**Approach:** In `_contribute`, a result with `ran=False` and a `skipped_reason` from a run that started (the binary was
found: a non-0/1 exit, an unparsable or non-object verdict, or TEA's own skip) appends one advisory record to
`context["advisory_notes"]`: the tool id, `skipped: true` and the reason, with no score and no recommendation. The
`TeaAdvisoryResult` shape and the runner are unchanged. An absent binary keeps Story 9.3's omit-not-error, and
`TeaRosterMissingError` stays loud. Story 11.2's I/O matrix decided that runner errors leave no note
(`spec-11-2-tea-test-review-is-a-warden-advisory-finding.md`, the "Runner errors" row); this story supersedes that row
for an enabled run that started and skipped, through a memlog decision. Story 11.2 is done and is not edited.

Ledger key: `13-2-a-tea-skip-on-a-missing-ref-reaches-the-report`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-warden` CAP-23 — the TEA advisory reviews the diff from the remote-tracking ref. A `fix`, so no new
  CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- **AC1 — A skip reaches the report.** Given `WARDEN_OPTIONAL_SCANNERS=tea-test-review`, a suite:AD-9 roster with `tea`, and
  an injected runner that exits 2, When `warden scan` runs, Then the report's `advisory` carries exactly one
  `tea-test-review` record with `skipped: true` and the reason `tea-test-review exited 2 -- verdict not trusted`, and no
  score or recommendation.
- **AC2 — Not enabled stays silent.** Given TEA not in `WARDEN_OPTIONAL_SCANNERS`, When `warden scan` runs, Then the
  report carries no TEA record.
- **AC3 — Advisory only.** Given the AC1 run, When its status and exit code are compared with the same run with TEA
  disabled, Then they are equal; the record never reaches `plugin_findings`, a rung or the exit code.
- **AC4 — The other paths hold.** Given the binary absent from `PATH`, Then no record is written (Story 9.3); given a
  roster without `tea`, Then `TeaRosterMissingError` is still recorded as a `CONFIG_VALIDATION` error.
- **AC5 — The contract follows.** A memlog decision on `spec-pyforge-warden` records the superseded Story 11.2 row, and
  CAP-23's success line names the effect (a skip reaches the report) through a `bmad-spec` re-derive, never a hand edit.
- **AC6 — Green.** `pixi run --frozen -e pyforge-warden pyforge-warden-test` passes.

## Boundaries & Constraints

**Always:** keep the TEA advisory advisory: a record in `advisory`, never a finding, a rung or the exit code. Pin each
path with a test that fails without the change (mutation: restore the bare `return`, and AC1 goes red).

**Never:** change TEA's upstream default or its exit-code semantics; run the real agent-backed review in the suite;
hand-edit `SPEC.md`; edit Story 11.2's or Story 13.1's text.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| missing base ref | runner exits 2 | one skip record with the reason | fail-open; no exception |
| TEA reports nothing to review | JSON `skipped: true` | one skip record with TEA's reason | — |
| binary absent | roster has `tea`, no binary | no record (Story 9.3) | unchanged |
| roster lacks `tea` | — | `TeaRosterMissingError` | unchanged, loud |
| TEA not enabled | — | no record | — |

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-warden` CAP-23 — the TEA advisory reviews the diff from the remote-tracking ref; a
  fix, no new CAP.

Parent: CAP-23

- EGM audit finding carried: WAR-M-Z6 (accepted 2026-11-01; one memlog event on `spec-pyforge-warden/.memlog.md`);
  residue `_bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md`.
- Epic: Epic 13 — a fix story joins its done epic (operator rule 2026-10-04; doctor Story 41.5 lets the epic key roll up
  to `in-progress`).
- Ledger key: `13-2-a-tea-skip-on-a-missing-ref-reaches-the-report`.
- Ledger status at mint: `backlog`.
- Deps: —.
- Surface: `src/shared/packages/pyforge-warden/src/pyforge/warden/tea_advisory.py`, `src/shared/packages/pyforge-warden/tests/unit/test_tea_advisory.py`.
- Dream: `docs/dreams/pyforge-warden.md` § *Realization log*, the 2026-11-01 (the EGM fleet audit) entry.
- Minted 2026-11-01 by the EGM audit landing (marshal Story 113.7, spec-pyforge-marshal:CAP-302); mode in-PR: built in the audit's landing PR.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/unit/test_tea_advisory.py -q` — expected: pass, including the new skip,
  not-enabled and status-equality tests.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Auto Run Result

Status: done

Summary: built in the EGM audit landing worktree (`egm-audit-2026-11`), 2026-11-01, uncommitted for the session owner
to land. `TeaAdvisoryScanPlugin._contribute` no longer drops a started-then-skipped TEA run at its bare
`if not result.ran: return`: it appends one advisory record `{"tool": "tea-test-review", "skipped": true, "reason":
<skipped_reason>, "summary": "skipped: <skipped_reason>"}`, with no `score` and no `recommendation` key. The only skip
still omitted is the `shutil.which` miss (new module constant `_BINARY_ABSENT_REASON`, the same text as before;
Story 9.3). `TeaRosterMissingError` still propagates. `run_tea_test_review`, the runner seam and `TeaAdvisoryResult`
are unchanged.

### Dev notes

- **Files changed:** `src/shared/packages/pyforge-warden/src/pyforge/warden/tea_advisory.py` (the `_contribute`
  branch, `_BINARY_ABSENT_REASON`, and the docstrings that said a runner error "contributes nothing");
  `src/shared/packages/pyforge-warden/tests/unit/test_tea_advisory.py` (six new tests; the Story 11.2 plugin test
  `test_enabled_plugin_runner_error_never_propagates_and_adds_no_note` is renamed `..._adds_a_skip_record_only` and
  now expects the record, as the superseded row requires).
- **Which skips report.** "A run that started" is read as "the binary was found" (the Approach's own criterion):
  a non-0/1 exit, an unparsable, missing or non-object verdict, TEA's own `skipped`/`promptOnly`, and a runner that
  raises (a timeout, an engine error). Story 11.2's "Runner errors" row named exit 2/3, timeout and unparsable JSON
  together; all of them now report. Only the PATH miss stays silent.
- **AC1 reason text.** The runner is unchanged (Approach), so the record's `reason` is the result's `skipped_reason`
  verbatim: `tea-test-review run failed: RuntimeError: tea-test-review exited 2 -- verdict not trusted`. It carries
  the AC1 text as its suffix, and the tests assert `endswith`. Making it exactly the AC1 string would mean changing
  `run_tea_test_review`, which the Approach rules out.
- **Text format.** The record carries a `summary` so the unchanged `[advisory]` text renderer prints the skip
  (`score=unknown recommendation=unknown -- skipped: <reason>`). `report.py` and `report-schema.json` are untouched:
  `advisory` is an open array.
- **Tests (each fails without the change):** `test_enabled_plugin_exit_2_adds_exactly_one_skip_record`,
  `test_enabled_plugin_tea_own_skip_adds_a_skip_record_with_tea_reason`,
  `test_enabled_plugin_non_object_verdict_adds_a_skip_record`,
  `test_full_scan_with_a_missing_base_ref_reports_the_skip_and_keeps_the_verdict` (AC1 and AC3: rc and every report
  key except `advisory` equal the TEA-disabled run), `test_full_scan_with_tea_not_enabled_carries_no_tea_record`
  (AC2), `test_full_scan_with_the_binary_absent_writes_no_record` (AC4); the existing
  `test_full_scan_with_roster_missing_refuses_not_a_silent_pass` keeps AC4's loud path.
- **Mutations (run in place, file restored byte-identical with `cmp`):** restoring the bare `if not result.ran:
  return` reds 5 tests, including the AC1 plugin and end-to-end tests; dropping the PATH-miss exclusion reds 2
  (`test_full_scan_with_the_binary_absent_writes_no_record`, `test_enabled_plugin_absent_binary_contributes_nothing`).
- **AC5:** two `spec-pyforge-warden` memlog entries, a surface-reconcile event naming both files and a decision
  recording the superseded Story 11.2 row and the effect CAP-23's success line should name. The success line itself
  waits for the `bmad-spec` re-derive; `SPEC.md` is not hand-edited.
- **Commands and exit codes:**
  - `pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/unit/test_tea_advisory.py -q`
    exit 0 (35 passed).
  - `pixi run --frozen -e pyforge-warden pyforge-warden-test` exit 0 (2181 passed unit+meta; 265 passed others).
  - `.pixi/envs/pyforge-guild/bin/ruff check <both files>` exit 0; `ruff format --check <both files>` exit 0 (the
    `ruff` name in `pyforge-guild` is the `lint_types.py` task, which takes no paths).
  - `pixi run --frozen -e pyforge-guild python scripts/lint_types.py mypy` exit 0 (`pyforge-warden ok`).
  - `pixi run --frozen -e pyforge-guild lint-types` exit 1. The failures are not from this story: `ruff` and
    `ruff-format` red `pyforge-atlas` only, from another agent's uncommitted atlas files in this shared worktree;
    `pyforge-warden` and `django-warden` report `ok` on every verb.
  - `pixi run --frozen -e pyforge-warden pyforge-warden-coverage-gate` exit 0, but it reads committed
    `origin/main..HEAD` and saw no touched module. `tea_advisory.py` measures 91% in `.steward/coverage/warden-unit.json`
    (floor 80%).

## Spec Change Log

- 2026-11-01: minted `backlog` from the EGM fleet audit (marshal Story 113.7): finding WAR-M-Z6, accepted by the
  operator, narrowed by the gap check to CAP-23; mode in-PR.
- 2026-11-01: built (`in-progress` to `in-review`) in the audit's landing worktree; see Auto Run Result.

## Review Triage Log

- **Review 1 (2026-11-01, reviewer: independent session) — PASS.**
  - Checked: the diff of `tea_advisory.py` and `test_tea_advisory.py` against AC1-AC6 and the Boundaries; `test_tea_advisory.py` exit 0 (35 passed); `tea_advisory.py` unit coverage 91.2%.
  - Common evidence (one run for all eight stories, exit codes read from `$?`): `pixi run --frozen -e pyforge-warden pyforge-warden-test` exit 0 (2255 unit+meta, 265 other); the twelve touched warden unit/meta test files together exit 0 (290 passed, 0 skipped; opengrep 1.30.2 and osv-scanner present); `ruff check` and `ruff format --check` over every changed warden, django-warden and platform test file exit 0; `python scripts/lint_types.py ruff-format` exit 0 and `python scripts/lint_types.py mypy` exit 0 (`pyforge-warden ok`); `pixi run --frozen -e pyforge-guild lint-types` exit 1 only from `pyforge-doctor`'s I001 in `tests/unit/test_sources_pages_liveness.py`, another station's in-flight file (`pyforge-warden` and `django-warden` ruff legs ok); `pixi run -e pyforge-guild platform-ci-local -- --test` (private ports) exit 0, RESULT: PASS, 1377 passed / 14 skipped; touched warden modules' unit coverage all at or above 81%. Mutations ran on scratch copies only (warden via `PYTHONPATH`, django-warden via `pytest -o pythonpath=`), never on the worktree.
  - Mutation: HEAD's `tea_advisory.py` on a scratch copy turns 5 tests red, including `test_enabled_plugin_exit_2_adds_exactly_one_skip_record` and `test_full_scan_with_a_missing_base_ref_reports_the_skip_and_keeps_the_verdict` (AC1).
  - AC1 holds, with one recorded deviation: the record's `reason` is the result's `skipped_reason` verbatim, `tea-test-review run failed: RuntimeError: tea-test-review exited 2 -- verdict not trusted`, so the AC's quoted text is its suffix, and the tests assert `endswith`. The spec's Problem misdescribed what the runner records; the Approach keeps the runner and `TeaAdvisoryResult` unchanged, and the record carries no score or recommendation key.
  - AC2-AC4 hold: the end-to-end test compares every report key except `advisory`, and the exit code, with the TEA-disabled run; an absent binary writes no record; a roster without `tea` still records `CONFIG_VALIDATION`.
  - AC5: the memlog decision names the superseded Story 11.2 'Runner errors' row.
  - Carried forward, not held against the story: the CAP success-line change is recorded on `spec-pyforge-warden/.memlog.md`; `SPEC.md` is unchanged, as required, and the line waits for the session owner's `bmad-spec` re-derive.
  - Failures: none.
