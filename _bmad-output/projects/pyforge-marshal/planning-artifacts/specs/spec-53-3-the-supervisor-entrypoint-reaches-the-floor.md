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

## Review Triage Log

### 2026-09-20 — Review pass

Four review layers ran over the implementation diff: a blind hunter (18 findings), an edge-case
hunter (12), a verification-gap auditor (4) and an intent-alignment auditor (8). The
implementation subagent that produced the diff could not be re-engaged for the patch round — the
session was compacted between step 03 and step 04 — so every `patch` below was applied directly
in this session and re-verified against the story's own Verification commands. Findings appear in
layer order; duplicates across layers are recorded in full rather than merged, and cross-referenced.

- verdicts: 42 findings — high 6, medium 22, low 13, false 0, maybe-false 1

- findings:
  - `[medium]` `[bad_spec]` AC-1's evidence is vacuous: the gate it names never measured anything on this branch — `scripts/coverage_gates_ci.py` returns 0 on the empty-module path before `evaluate_coverage_payload` is called, so exit 0 proves only that no station `.py` changed. Restating the AC would mean editing this build's own intent-contract, which step 04 forbids; recorded here and stated plainly in AC-1's Auto Run Result entry instead, and the number is now re-measured by the new `tests/meta/` test rather than living only in prose.
  - `[medium]` `[patch]` The miss count was stale (27 claimed, 29 actual) and the enumeration omitted `775-776`, the `except FsError` arm of the second `fs.read_text` in `_promote_blocked_twin`; the 19 partial branches were not acknowledged at all even though the headline figure is branch coverage. Patched: `775-776` is now covered by a test that makes only the primary spec unreadable, and the Auto Run Result reports `623 / 20 / 172 / 18` with partial branches named.
  - `[high]` `[patch]` Line 1542 was misclassified as an unreachable `except` arm. `__main__.py:1541-1542` is `if landing_done:` / `verdict = COMPLETED` — ordinary success-path control flow. Patched: `test_supervisor_completes_when_another_writer_lands_during_finalize` drives a second journal writer that lands the story while the finalize entry is being written (the only reachable shape — the finalize sequence never lands, and `supervisor_should_finalize_harness_work` refuses once landing is complete), and asserts exit 0, no land call, and a COMPLETED publisher completion.
  - `[high]` `[patch]` `1538-1539` and `1618-1619` were called unreachable-by-fake, but `FakeVcs` already accepts head-SHA failure knobs. True: they need a scenario, not a production change. Patched with a journal-state-keyed fake (`_HeadShaFailsOnceJournaledVcs`) that refuses `worktree_head_sha` once the journal names a given entry kind — one test keyed on the finalize entry (covering `1538-1539` and `1700-1701`), one keyed on the land entry and bounded to a single refusal (covering `1618-1619`, asserting the land still happened exactly once and the session still completes). Keying on journal state rather than call count avoids pinning how many git reads the loop performs.
  - `[medium]` `[patch]` `main()` silently discards `log_path`, and `test_main_threads_every_positional_into_the_supervisor` asserted four of the arguments, so a test whose name promised "every positional" passed over a dropped one. Patched: the test is renamed `test_main_threads_every_supervisor_positional_and_ignores_the_log_path`, asserts the whole eight-key call dictionary and asserts `"log_path" not in captured`. The dropped argument is recorded as a finding and a `deferred:` entry rather than fixed, because "accepted for argv compatibility with the launcher" is a defensible reading and the Boundaries forbid an unproven production change.
  - `[medium]` `[patch]` `test_fold_dispatch_journal_reads_sidecars_through_the_fs_port` seeded no sidecar, so the read path its name advertises was never entered. Patched to seed a real offload record and to assert the fold over both offload shapes the writer can produce.
  - `[medium]` `[defer]` The `stuck_land_ticks` retry path is untested. Investigated rather than patched: the `or should_retry_stuck_land(...)` disjunct is inert by construction — its inputs are a subset of the first disjunct's conditions, and the counter is reset to 0 in the same tick immediately above — so it can never reach the `>= 5` it requires. A test that drove it would have to fake the reset away and would pin a fiction. Carried as a `deferred:` entry against `__main__.py:1564-1578`.
  - `[low]` `[patch]` `_FakeClock(mono_step=...)` was never constructed with a non-zero step, so every elapsed-time assertion was trivially zero and the idle arithmetic never crossed its threshold. Patched: a tick-loop test now drives a non-zero `mono_step` against the real, unpatched `should_checkpoint_on_idle` and asserts a single checkpoint entry.
  - `[medium]` `[patch]` The replacement floors test was weaker than the one it retired — `load_module_floors() == {}` also passes when the packaged TOML is missing. Patched: it now also asserts `default_thresholds_path().is_file()` and `thresholds_for("marshal").for_suite("unit") == 80.0`.
  - `[medium]` `[patch]` `spec-surface` emitted a `drift-presumed: warn` this diff caused and the record did not mention it: the memlog named one file short-form while the detector substring-matches the full `git ls-files` path. Patched: every path in both memlog entries is named in full repo-relative form. A second, independent cause of the same warn was found while verifying — a stray `.coverage` artifact captured by an auto-checkpoint commit — and removed with `git rm --cached`. The detector now exits 0 with zero `drift-presumed` lines.
  - `[low]` `[patch]` The reconcile was verified only with `scripts/spec_surface_reconcile.py`, not with the detector the merge gate reads, and `scripts/spec_surface_check.py` now exits 2 by design (the documented 2-inversion trap). Patched: Verification performed names `python -m pyforge.doctor.sources spec-surface` alongside the guard, records its zero-warn result, and notes the exit-2 behaviour so a future reader does not read it as a failure.
  - `[medium]` `[patch]` Nothing gated the number going forward, and "any future module that falls below 80% reds the gate" overstated the guarantee. Patched on both sides: the new `tests/meta/` coverage-floor test supplies the standing measurement, and Residual risks now states exactly what the gate covers (touched modules only) and what the package-wide evaluate is (operator reports, never a gate).
  - `[low]` `[patch]` The TOML comment documented the per-module-exception mechanism but not its new tripwire, so the next operator landing a dated exception would meet an unexplained unit-test failure. Patched: the comment names `test_the_live_file_holds_no_module_exception` and says that adding an entry reds it.
  - `[medium]` `[bad_spec]` The spec's Boundaries name `HarnessPort` and `ForgePort`; the entrypoint's actual injection points are `FsPort`, `VcsPort`, `ProcessPort` and `RunPublisherPort`. The suite fakes the real ports — correct against the code, divergent from the intent's naming. Recorded, not edited: correcting the clause means editing this build's spec. The Auto Run Result names the real seams so a reader wiring a new test uses the right ones.
  - `[low]` `[defer]` The "ports only" claim is achieved for the clock by replacing the module's `time` attribute, since the entrypoint has no `ClockPort`. Adding one is a production change to a signature the launcher calls. Recorded as a `deferred:` entry and disclosed in the Auto Run Result and the fixture docstring.
  - `[medium]` `[patch]` `warnings: []` and `deferred: []` contradicted a body that recorded three findings, one of them an explicit handoff with no ledger row anywhere. Patched: the frontmatter now carries ten `deferred:` entries, each with a real repository `location:`, including the CFE handoff and `DW-FU-53-2-4` — which Story 53.2 recorded as a candidate for its sibling and which this story neither addressed nor closed.
  - `[medium]` `[patch]` `baseline_revision` was rewritten by the run whose byte-identity claim it anchored, making the claim self-certifying. Patched: the claim now cites the pre-run `origin/main` SHA `326870e98` explicitly, with the empty `git diff` against that SHA as its evidence. `baseline_revision` itself is left where the harness put it — rewriting it would be a second self-certification.
  - `[low]` `[patch]` `test_main_refuses_a_missing_positional` used a bare `pytest.raises(SystemExit)`, which passes on exit 0. Patched to assert `excinfo.value.code == 2`, argparse's usage-error code.
  - `[low]` `[patch]` `FakeProcess` constructed with an empty liveness script (`alive=[]`) raised `IndexError` from inside the fake rather than a legible failure. Patched: the constructor refuses an empty script with `ValueError("FakeProcess(alive=[]) has no liveness to script")`.
  - `[low]` `[patch]` `mono_step` defaulted to 0.0 and no test passed another value, so `time.monotonic()` returned a constant. Same defect as the blind hunter's eighth finding; patched once, by the non-zero-step checkpoint test.
  - `[medium]` `[defer]` `FakeFs` falls through to the real checkout on an overlay miss, so a unit result can depend on working-tree state. True, and load-bearing today: the supervisor reads tracked repo files (the story spec, known story keys) that the fixtures deliberately do not stub, so closing it is a rewrite of the fixture layer rather than a review patch. Carried as a `deferred:` entry against the fixture.
  - `[medium]` `[patch]` `read_fails_for` was keyed by basename, so two paths sharing one basename could not be given different read outcomes — which is exactly why `__main__.py:775-776` was unreachable. Patched: `FakeFs.read_text` now matches a basename *or* a full posix path, and a new test makes only the primary story spec unreadable while the twin stays readable, covering the arm.
  - `[maybe-false]` `[reject]` "The fake clock patches attributes on the stdlib `time` module, so a future `time.perf_counter()` call raises AttributeError." The premise misdescribes the fixture: the suite does `monkeypatch.setattr(supervisor_main, "time", fake)` — it replaces the module *reference on the module under test*, mutating nothing global. The residual behaviour (an unknown attribute on the fake) fails loudly inside the test that introduced the call, which is the desired outcome for a clock seam, not a hazard.
  - `[low]` `[defer]` `supervisor_should_exit(...)` is inert — both arms `return 0` — so no added test can observe its regression. Correct, and a production change to fix; carried as a `deferred:` entry against `__main__.py:1861-1867`.
  - `[medium]` `[patch]` The ninth positional `log_path` is parsed then discarded. Same defect as the blind hunter's fifth finding; patched once, in the renamed `main()` test, and recorded as a `deferred:` entry together with the package docstring's argv, which is separately one positional short (it omits `<merge_subject_template>`).
  - `[medium]` `[patch]` The retired test also pinned that the packaged thresholds file resolves and parses through the default path, and `load_module_floors() == {}` does not. Same defect as the blind hunter's ninth finding; patched once.
  - `[high]` `[bad_spec]` AC-1's acceptance evidence comes from a different run than the cited gate, because `_evaluate` skips evaluate on this branch. Same defect as the blind hunter's first finding; recorded, not edited, and stated in AC-1.
  - `[medium]` `[bad_spec]` AC-2's second clause ("the gate's OK line names no dated exception") rests on output the cited command does not produce here: `evaluate_suite` is the sole producer of that line and never runs. Recorded in AC-2 as satisfied by construction rather than by observation.
  - `[medium]` `[bad_spec]` The Boundaries name ports the entrypoint does not accept. Same defect as the blind hunter's fourteenth finding; recorded, not edited.
  - `[low]` `[reject]` "Divergent doubles: the new file declares its own `FakeFs`/`FakeVcs` instead of reusing the siblings'." The siblings each declare their own local fakes — `test_dispatch_supervisor_blocked_halt.py` included — so the new file follows the established pattern, and the story's Approach says "the same fakes … already use" of the shape, not of shared objects. The half of this finding that was real, the weaker path-keyed injection, was patched under the basename-keying finding above.
  - `[high]` `[patch]` The restored 80% floor is measured by nothing that runs — not on this branch, and not on the change most likely to break it: `coverage_gates_ci.py` evaluates only touched source modules, so deleting or gutting the new unit file touches no `src/` path, skips evaluate, keeps every lane green, and lets the module drift back toward 35% while `test_the_live_file_holds_no_module_exception` still passes (it asserts the TOML's emptiness, not coverage). Patched: `tests/meta/test_dispatch_supervisor_main_coverage_floor.py` re-runs the suite in a subprocess under coverage and holds the measured percentage to the floor the gate itself would apply, so the number that justified deleting the exception is re-measured on every marshal change (0.71s).
  - `[medium]` `[patch]` `spec-surface-check` was not clean on the branch. Same defect as the blind hunter's tenth finding; patched, with a second cause (the stray `.coverage` artifact) found and removed during verification.
  - `[medium]` `[patch]` `test_supervisor_survives_an_initial_fetch_failure` asserted only `code == 0`, so it would keep passing if the supervisor stopped journaling or stopped gathering git facts after a failed fetch — it contributed coverage without pinning behaviour. Patched to assert the session's terminal verdict, not just the exit code.
  - `[low]` `[patch]` The unreachable line at `__main__.py:1558` was disclosed in prose with no deferred-work row named anywhere. Patched: it is now a `deferred:` entry with a real location, alongside the other production observations this story recorded and did not fix.
  - `[high]` `[bad_spec]` The AC's command measures a surface this branch does not touch; the intent's expectations live at gate stdout while the change lives in the module's coverage and in the thresholds file. The mismatch is inherited from the chain — `epics.md` Story 53.3 and the CAP-264 memlog Success line carry the same wording — so the correction belongs upstream, on the station Spec, not in this build's spec. Recorded, and stated in AC-1 and AC-2.
  - `[medium]` `[bad_spec]` Expectation surface versus change surface: what the diff changes is what makes the gate pass on some *future* branch that edits `__main__.py`, which is the only branch on which the AC's sentence can ever be observed. Recorded with the finding above.
  - `[high]` `[patch]` Nothing in the diff exercised the gate surface, so the measured percentage was regression-pinned nowhere. Patched by the new `tests/meta/` test, which is the closest a test-only branch can get to the AC's surface: it asserts the measured number against the floor the gate would apply, including a per-module exception if one is ever held again.
  - `[medium]` `[bad_spec]` Port vocabulary: `HarnessPort` / `ForgePort` exist in the package but are not parameters of this entrypoint. Recorded with the Boundaries findings above.
  - `[low]` `[reject]` "Some duplication of fixture code across four modules." Deliberate and conventional in this package: each `test_dispatch_supervisor_*.py` owns its doubles, which is what keeps one scenario's fake from constraining another's. Consolidating them is a refactor of four files, outside a test-only coverage story's scope, and would trade the duplication for coupling.
  - `[low]` `[reject]` "AC-3 is over-satisfied: the inverse pin covers the whole file, not just this module." Correct as an observation and intended as a design choice — a per-module absence assertion would silently pass if the exception were re-added under a different module name. The stronger pin is documented in the test docstring and in the TOML comment, and the mechanism it guards is deliberately retained. Nothing to change.
  - `[medium]` `[patch]` Reconcile surface: the `drift-presumed: warn`, and the Auto Run Result citing the reconcile helper rather than the detector the merge gate reads. Same defects as the blind hunter's tenth and eleventh findings; patched together — full repo-relative paths in both memlogs, and both surfaces named in Verification performed with their exit codes.
  - `[low]` `[patch]` `baseline_revision` moved from a real `origin/main` merge to the branch's own first checkpoint commit, so anything deriving "what this run changed" from it diffs from a branch commit. Same defect as the blind hunter's seventeenth finding; patched by citing the pre-run SHA for the byte-identity claim.

**Follow-up review recommended: yes.** Four `patch`-triaged findings entered at `high`
(the misclassified reachable line at 1542, the two reachable git-read arms, the unmeasured
restored floor, and the unpinned measurement), which meets the first-pass threshold on its own.
The specific unverified risk is the patch set itself, not the original implementation: five new
tick-loop scenarios and one new meta test were written in this session with no implementation
subagent available to re-engage, and two of them encode assumptions a second reviewer should
check — `_LandsDuringFinalizeFs` chooses a particular multi-writer journal interleaving to reach
`__main__.py:1542`, and `tests/meta/test_dispatch_supervisor_main_coverage_floor.py` is this
package's first subprocess-with-coverage test, verified locally in `-e pyforge-marshal` but never
yet run in CI, where the coverage plugin's environment differs.
