---
title: '53.3: The supervisor entrypoint reaches the floor'
type: 'chore'
created: '2026-09-20'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: true
baseline_revision: 'd50aedbd22c5b8a531f25d90fca1532a3cae6ace'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/coverage_thresholds.toml
warnings: []
deferred:
  - summary: >-
      `supervisor_should_exit(...)` is inert at the supervisor's terminal return: both the
      True and the False arm return 0, so the predicate's result changes nothing and no test
      can observe it regressing.
    evidence: |-
      `if supervisor_should_exit(completion_verdict=..., story_merged_on_main=...,
      landing_verdict=...): return 0` is immediately followed by a bare `return 0`. The call
      still costs a journal fold and three keyword arguments. Either the False arm was meant
      to return a non-zero code (the supervisor stayed but the tick loop ended) or the call
      should go; both are production changes this story's Boundaries forbid.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py:1861-1867
    severity: low
  - summary: >-
      `verdict = DispatchSessionVerdict.FAILED` under `should_terminalize_verify_refusal` in
      the LIVE branch is unreachable dead defensive code, and therefore permanently
      uncoverable in the module whose floor this story restored.
    evidence: |-
      `should_terminalize_verify_refusal(...)` requires `not session_alive` and
      `verification_verdict == "refused"` and git progress. The only path yielding LIVE for a
      dead session is `resolve_terminal_session_verdict`'s marshal-initiated-stop branch
      (`core/supervise.py:718-720`), reached only after the refused-plus-progress case already
      returned FAILED at `supervise.py:714-717`. Deleting the line is a production change that
      buys coverage and nothing else.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py:1558
    severity: low
  - summary: >-
      The package docstring's documented entry-point argv is one positional short of what
      `main()` actually parses: it omits `<merge_subject_template>`.
    evidence: |-
      The docstring shows `python -m pyforge.marshal.dispatch_supervisor <repo_root> <slug>
      <run_id> <session_pid> <worktree_path> <story_key> <baseline_head_sha> <log_path>` —
      eight positionals. `main()` registers nine, with `merge_subject_template` between
      `baseline_head_sha` and `log_path`. Anyone launching the supervisor by hand from the
      docstring passes the log path where the merge subject template belongs.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__init__.py:9-13
    severity: medium
  - summary: >-
      `main()` parses a ninth positional `log_path` and never forwards it to
      `run_dispatch_supervisor(...)`, so a caller-supplied supervisor log destination is
      silently ignored.
    evidence: |-
      `parser.add_argument("log_path")` is parsed into `args.log_path`; the
      `run_dispatch_supervisor(...)` call that follows passes eight keywords and `log_path` is
      not among them. This run pinned the current behaviour rather than changing it —
      `test_main_threads_every_supervisor_positional_and_ignores_the_log_path` asserts the
      whole eight-key call and asserts `"log_path" not in captured` — because the story's
      Approach forbids a production change without a proven defect, and "the argument is
      accepted for argv compatibility with the launcher" is a defensible reading nothing in
      the module contradicts.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py:1880-1891
    severity: medium
  - summary: >-
      The touched-module coverage gate re-measures nothing on a branch that changes only
      tests, so a station's restored floor is defended by no lane that runs on the change most
      likely to break it.
    evidence: |-
      `_evaluate` derives its module list from changed `src/**/*.py` paths only and returns 0
      with `no touched source modules for pyforge-marshal unit; skipping evaluate` when that
      list is empty — verified on this branch, which prints exactly that. This story mitigates
      the single module it restored, by re-measuring it in
      `tests/meta/test_dispatch_supervisor_main_coverage_floor.py`, but the general hole stays:
      every other module's floor is still only checked when a branch happens to edit its
      source. A fleet-level fix (a periodic full-package evaluate, or a gate that also
      measures modules whose *tests* a branch touches) belongs to the gate's owning chain,
      `spec-pyforge-steward:CAP-153`, not to a marshal dispatch.
    location: scripts/coverage_gates_ci.py:230-246
    severity: medium
  - summary: >-
      The `should_retry_stuck_land(...)` disjunct in the LIVE branch's landing condition is
      inert by construction, so `stuck_land_ticks` can never reach the threshold it guards.
    evidence: |-
      The `or should_retry_stuck_land(...)` arm's inputs are a subset of the first disjunct's
      conditions, so whenever the retry predicate could be True the first disjunct is already
      True; and `stuck_land_ticks` is reset to 0 in the same tick, immediately above, whenever
      those conditions do not hold. The counter therefore never accumulates to the `>= 5`
      the predicate requires. No unit test can drive it without a production change; a
      test that pretended to would be pinning a fiction.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py:1564-1578
    severity: medium
  - summary: >-
      `FakeFs.read_text` falls through to the real checkout on an overlay miss, so a unit
      result can depend on the state of the working tree rather than on the fixture alone.
    evidence: |-
      The overlay is consulted first and an unseeded path reaches the real filesystem. That is
      load-bearing today — the supervisor reads tracked repo files (the story spec, known story
      keys) that the fixtures deliberately do not stub — so closing it means seeding those
      files in every scenario, which is a rewrite of the fixture layer rather than a review
      patch. Until then an edit to a tracked file the supervisor reads can change a unit
      result with no test edit.
    location: >-
      src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_supervisor_main_loop.py:101-110
    severity: medium
  - summary: >-
      The supervisor entrypoint has no `ClockPort`: its clock is faked by replacing the
      module's `time` attribute, the one seam in this suite that reaches past the ports
      contract the file advertises.
    evidence: |-
      `monkeypatch.setattr(supervisor_main, "time", fake)` swaps the whole stdlib module
      object for a `_FakeClock`. Every other collaborator is injected through `FsPort`,
      `VcsPort`, `ProcessPort` or `RunPublisherPort`. Adding a `ClockPort` parameter is a
      production change to a signature the launcher calls, so it belongs to a story of its
      own; the suite documents the deviation in the fixture's docstring meanwhile.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py:1442-1460
    severity: low
  - summary: >-
      `.claude/skills/conda-forge-expert/tests/unit/test_inventory_channel_auth_host_gate.py::test_malformed_base_url_does_not_crash_the_allowlist_scan`
      fails in any session running behind the headroom wire-compression proxy.
    evidence: |-
      `_fallback_configured_enterprise_hosts()` scans every `*_BASE_URL` environment variable
      and the test does not clear the ambient ones, so `ANTHROPIC_BASE_URL=http://127.0.0.1:9108`
      leaks `127.0.0.1` into the asserted set. It passes with that variable unset, and CI never
      sets it. The fix (clearing the environment in the test) belongs to the CFE skill's own
      chain under its Rule 1 / Rule 2 retro obligations, not to a marshal dispatch, which may
      not edit skill files under this story's Boundaries.
    location: >-
      .claude/skills/conda-forge-expert/tests/unit/test_inventory_channel_auth_host_gate.py
    severity: low
  - summary: >-
      `DW-FU-53-2-4` (dispatch finalize should promote the story spec from a tracked `done`
      copy) was recorded during Story 53.2 as a candidate for 53.3's sibling; this story
      neither addressed it nor re-recorded it, so it stays where 53.2 left it.
    evidence: |-
      The row is live in the marshal deferred-work ledger. It is out of scope here — 53.3's
      Approach is test-only and its Boundaries forbid the production change the promotion
      needs — but it is named here so the next session reading this story's deferred list sees
      it rather than inferring it was closed by Epic 53's completion.
    location: >-
      _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
    severity: low
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** As the operator who landed 53.2 behind a dated exception, I want `dispatch_supervisor/__main__.py` (623 statements, 388 uncovered, 35% on 2026-09-20; 36% on `main` before 53.2 touched 15 of its 1,895 lines) unit-covered to the 80% floor and the `[modules."pyforge.marshal.dispatch_supervisor.__main__"]` exception removed from `coverage_thresholds.toml`, So that Epic 53 closes with no named debt and the touched-module gate is whole again for marshal.

**Approach:** ports-driven unit tests of the supervisor's finalize / halt / land / completion sequences (the same fakes `test_dispatch_supervisor_*.py` already use), added until the gate reports ≥ 80%; then delete the exception entry. No production change unless a test proves a defect (which becomes its own finding).

Ledger key: `53-3-the-supervisor-entrypoint-reaches-the-floor`.
Ledger status (do not edit the ledger): `backlog`.

### Living CAP citations

- `spec-pyforge-marshal` CAP-264; the gate itself is `spec-pyforge-steward:CAP-153`.

## Acceptance Criteria

- Given the module sits at 35% behind a dated exception, When this story lands, Then `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` reports `pyforge.marshal.dispatch_supervisor.__main__` ≥ 80%.
- The `[modules."pyforge.marshal.dispatch_supervisor.__main__"]` entry is gone from `coverage_thresholds.toml` and the gate's OK line names no dated exception for marshal.
- `test_the_live_file_names_the_supervisor_exception_with_its_story` in `tests/unit/test_coverage_gate_module_floors.py` is retired with the entry (it pins the exception's presence, not its absence).

## Boundaries & Constraints

- Coverage comes from tests, never from excluding lines or lowering floors.
- The supervisor's process boundary is faked through its ports (`HarnessPort`, `VcsPort`, `ForgePort`); no live harness, no network.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary checkout's copy of this file).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass.

**Manual checks:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` — the module ≥ 80%, no exception named.

</intent-contract>

## Auto Run Result

**Summary:** Story 53.3 implemented in one pass and then hardened by the review pass. `dispatch_supervisor/__main__.py` goes from 35% (388 of 623 statements uncovered, behind the dated exception Story 53.2 opened) to **95% with branch coverage** — `623 statements / 20 missed / 172 branches / 18 partial branches`, measured over 101 ports-driven unit tests — and the `[modules."pyforge.marshal.dispatch_supervisor.__main__"]` entry is deleted from `coverage_thresholds.toml`, so marshal holds no per-module coverage exception at all. **No production code was changed:** `git diff 326870e985259412f799da04092a1f6299e357d4 -- src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py` is empty, against the `origin/main` commit this branch started from rather than against `baseline_revision` (which this run's own first checkpoint commit moved, and which therefore cannot certify the claim).

**Files changed this run:**
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_supervisor_main_loop.py` (**new**, 101 tests) — direct-call tests of the module's helpers (`_append_entry` incl. the sidecar offload above `SIDECAR_THRESHOLD_BYTES`, `_fold_dispatch_journal` over both sidecar offload shapes, `_maybe_fetch_origin_main`, `_commit_pre_verify_wip`, `_launch_story_started_ts`, `_journal_dispatch_timing` / `_preserve` / `_blocked` / `_finalize_attempt`, `_load_known_story_keys`, `gather_dispatch_git_facts` incl. the station-branch PR corroboration path, the six journal predicates, `_worktree_story_spec`, `_spec_land_block_reason`, `_blocked_halt_reason`, `_attempted_change_patch_paths`, `_commit_and_journal_blocked_halt`, `_promote_blocked_twin` incl. the unreadable-primary-spec arm, `_run_and_journal_dispatch_push` / `_verification` / `_landing`, `_land_or_journal_block`, `_session_awaits_verification`, `_run_supervisor_finalize_sequence`), 20 `run_dispatch_supervisor` tick-loop scenarios (heartbeat, verification, landing, blocked halt, stale-blocked advisory, finalize, preserve, timing, a concurrent journal writer landing the story mid-finalize, and git-read failures after finalize and after the live-branch land) and 2 `main()` argv tests. The process boundary is faked through the ports only — `FakeFs` / `FakeVcs` / `FakeProcess` / `FakePublisher` — plus a `_FakeClock` that replaces the module's `time` attribute (so `_TICK_SECONDS` never sleeps and a non-terminating loop raises instead of hanging); that clock is the suite's one documented deviation from the ports contract, carried as a deferred item because the entrypoint has no `ClockPort`. No live harness, no network, no subprocess.
- `src/shared/packages/pyforge-marshal/tests/meta/test_dispatch_supervisor_main_coverage_floor.py` (**new**, 1 test, 0.71s) — the review pass's one structural addition. It runs that unit file in a subprocess under `--cov=pyforge.marshal.dispatch_supervisor.__main__ --cov-branch --cov-report=json`, with `COV_CORE*` / `COVERAGE_PROCESS_START` stripped from the child environment and `COVERAGE_FILE` pointed at `tmp_path`, and asserts the measured `percent_covered` is at or above the floor the gate itself would apply — `load_module_floors()[module]` if an exception is ever held again, else `thresholds_for("marshal").for_suite("unit")`. It exists because deleting the exception left the restored floor measured by nothing that runs: `scripts/coverage_gates_ci.py` evaluates only the source modules a branch *touches*, and an edit that deletes or guts the unit file touches no `src/` path at all, so the module could drift back toward 35% with every lane green.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/coverage_thresholds.toml` — the `[modules."pyforge.marshal.dispatch_supervisor.__main__"]` block removed; the comment documenting the per-module-exception mechanism stays, records that none is held, and now names the test that reds when an entry is added back, so the next operator landing a dated exception under an operator ruling meets a pointer rather than an unexplained failure.
- `src/shared/packages/pyforge-marshal/tests/unit/test_coverage_gate_module_floors.py` — `test_the_live_file_names_the_supervisor_exception_with_its_story` retired (it pinned the entry's presence); `test_the_live_file_holds_no_module_exception` pins the absence in its place, and — after the review pass — also asserts `default_thresholds_path().is_file()` and `thresholds_for("marshal").for_suite("unit") == 80.0`, because `load_module_floors()` returns `{}` for a missing file too and the bare assertion would have passed if the packaged TOML disappeared. The five mechanism tests over the synthetic TOML are untouched.
- Surface reconcile: `.memlog.md` entries on `spec-pyforge-marshal` (the three test files) and its co-governor `spec-pyforge-core` (the thresholds file), every path named in the full repo-relative form `git ls-files` prints — the detector substring-matches that exact form, and a short-form name produced a `drift-presumed: warn` the review pass caught. **No baseline stamp** — `scripts/.spec-surface-baseline.json` is unchanged from `baseline_revision`. The implementation pass had stamped it scoped (`--write-baseline --spec`) and that was reverted: a producer that stamps its own baseline launders drift instead of reconciling it, which is why `scripts/spec_surface_reconcile.py` exposes no such flag. The memlog entries alone carry the reconcile.

**Acceptance criteria:**
- AC-1 — the module measures **95%** with branch coverage (`623 statements / 20 missed / 172 branches / 18 partial`), above the 80% floor. Stated precisely, because the AC's literal wording is not observable on this branch: `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` exits 0 but is *structurally silent* about the module — it derives its module list from changed `src/**/*.py` paths, this branch changes none, so `_evaluate` returns early with `coverage gate: no touched source modules for pyforge-marshal unit; skipping evaluate` and prints `pyforge-marshal unit floor: 80%` without reading a percentage. The only branch on which the gate can ever print this module's number is one that edits its source — which this story's Boundaries forbid. The number above therefore comes from a direct measurement of the same suite the gate would measure, and, as of this run, is re-measured on every marshal change by the new `tests/meta/` test rather than living only in this prose. The AC's command wording is recorded as a spec defect below, not edited.
- AC-2 — the entry is gone (`tomllib` parses the file to `{'defaults': {'unit': 80.0, 'integration': 70.0}}`, no `modules` table, and `load_module_floors() == {}` over the packaged path). The clause "the gate's OK line names no dated exception for marshal" is satisfied by construction and not by observation: `evaluate_suite` is the sole producer of that OK line and of its `under a dated exception` clause, and it never runs on a branch with no touched source modules. Also recorded as a spec defect below.
- AC-3 — `test_the_live_file_names_the_supervisor_exception_with_its_story` is retired with the entry. Over-satisfied deliberately: the replacement pins the absence for the whole file, so any future use of the retained per-module mechanism must also edit this test. That is beyond the AC's letter, is documented in the test's docstring and in the TOML comment, and is the behaviour a reviewer of a re-opened exception should meet.

**Verification performed** (every verdict read from `$?` or from a file, never through a pipe):
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — exit 0 (8498 passed, 1 skipped, 12 deselected).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — exit 0 (130 passed, 3 skipped). Note the environment: this task is defined in `pyforge-ci`, and `-e pyforge-marshal` refuses it.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` — exit 0, `no touched source modules for pyforge-marshal unit; skipping evaluate`, `pyforge-marshal unit floor: 80%`. Green, and — as recorded under AC-1 — silent about the module.
- Direct measurement, the number AC-1 asserts: `python -m pytest tests/unit/test_dispatch_supervisor_main_loop.py -q -p no:randomly --cov=pyforge.marshal.dispatch_supervisor.__main__ --cov-branch` in `-e pyforge-marshal` — 101 passed in 0.30s, `623 20 172 18 95%`.
- `pixi run --frozen -e pyforge-guild lint-types` — exit 0 (ruff, `ruff format --check`, mypy over the ten `pyforge-*` packages).
- `pixi run -e pyforge-guild pr-preflight` — exit 0 on the implementation pass (lint/format/mypy, `detectors-ci`, the CFE regression suite, `pyforge-core` + all 8 station suites, every station's touched-module coverage gate, site-check).
- `python scripts/spec_surface_reconcile.py` — exit 0, `OK: every tracked file governed or allowlisted; no drift`. Proved non-vacuous in both directions: with the `spec-pyforge-marshal` memlog entry reverted the guard exits 1 and names the changed and added test files; with the entry restored it exits 0.
- `pixi run --frozen -e pyforge-guild python -m pyforge.doctor.sources spec-surface` — exit 0, `spec-surface: ok -- every tracked file governed or allowlisted; no drift`, **zero** `drift-presumed` lines. This is the detector the merge gate actually reads, and it is a different surface from the reconcile guard above: during the review pass it reported a `drift-presumed: warn` (a memlog path named short-form, and separately a stray `.coverage` artifact captured by a checkpoint commit) that the reconcile guard did not. Note also that `python scripts/spec_surface_check.py` now exits **2** by design — it no longer computes the verdict — which is the documented 2-inversion trap, not a failure.

**Findings (recorded, not fixed — the story's Approach forbids a production change without a proven defect; each is carried as a `deferred:` entry above with a real repository location):**
- `dispatch_supervisor/__main__.py:1558` is unreachable dead defensive code, and therefore permanently uncoverable in the very module whose floor this story restored.
- `supervisor_should_exit(...)` at `__main__.py:1861-1867` is inert: both arms `return 0`.
- The `should_retry_stuck_land(...)` disjunct at `__main__.py:1564-1578` is inert by construction — its inputs are a subset of the first disjunct's conditions and `stuck_land_ticks` is reset in the same tick — so the counter never reaches the threshold it guards. The review pass flagged the retry path as untested; it is untestable without a production change, which is a stronger statement and is why no test pretends to drive it.
- `main()` parses a ninth positional `log_path` and never forwards it; the package docstring's documented argv is separately one positional short, omitting `<merge_subject_template>`. The suite now pins the current call exactly (`test_main_threads_every_supervisor_positional_and_ignores_the_log_path`) rather than asserting four of the arguments and passing over the dropped one.
- The touched-module coverage gate re-measures nothing on a test-only branch. Mitigated here for this one module by the new `tests/meta/` test; the general hole belongs to the gate's owning chain, `spec-pyforge-steward:CAP-153`.
- `FakeFs.read_text` falls through to the real checkout on an overlay miss — load-bearing today, since the supervisor reads tracked repo files the fixtures deliberately do not stub.
- The entrypoint has no `ClockPort`, so the fake clock is installed by replacing the module's `time` attribute.
- Unrelated to this story, surfaced by `pr-preflight` in this session: `.claude/skills/conda-forge-expert/tests/unit/test_inventory_channel_auth_host_gate.py::test_malformed_base_url_does_not_crash_the_allowlist_scan` fails in any session running behind the headroom wire-compression proxy, because `_fallback_configured_enterprise_hosts()` scans every `*_BASE_URL` environment variable and the test does not clear the ambient ones — `ANTHROPIC_BASE_URL=http://127.0.0.1:9108` leaks `127.0.0.1` into the asserted set. It passes with that variable unset, and CI (which never sets it) is unaffected. A fix belongs to the CFE skill's own chain (its Rule 1 / Rule 2 retro obligations), not to a marshal dispatch.
- `DW-FU-53-2-4`, recorded by Story 53.2 as a candidate for its sibling, is neither addressed nor closed here; it is re-named in the deferred list so the next session sees it.

**Residual risks:**
- **What is now gated, stated exactly.** Deleting the exception means a future branch that edits `dispatch_supervisor/__main__.py` is held to 80% by `coverage_gates_ci.py`. It does **not** mean "any module that falls below 80% reds the gate": the gate only measures modules a branch touches, and the package-wide evaluate (`pyforge-marshal-test-coverage`) is, by its own workflow's words, "reports for an operator, never a gate". The one standing protection for this module is the new `tests/meta/` test, which runs in the marshal suite on every marshal change.
- **The new meta test is the first of its kind in this package.** It spawns `pytest` with coverage as a subprocess, so it depends on the child environment being free of the parent's `COV_CORE*` hooks (handled explicitly) and on the coverage plugin being importable in whatever environment the marshal suite runs in. It passes here in `-e pyforge-marshal` in 0.71s; it has not yet run in CI.
- **The concurrent-writer scenario encodes an assumption.** `_LandsDuringFinalizeFs` injects a landing outcome into the journal while the finalize entry is being written, because that is the only way `__main__.py:1542` is reachable — the finalize sequence itself never lands, and the finalize predicate refuses once landing is complete. The scenario is faithful to the journal being multi-writer (which is why the module re-folds after finalize at `1523-1525`), but the exact interleaving is chosen by the test, not observed from a live run.
- The suite is pure-fake and clock-bounded (`_LoopGuard` raises after 12 sleeps), so it adds roughly a second to the marshal unit suite and cannot hang.
