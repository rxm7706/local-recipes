---
title: '94.1: No platform test leaves structlog configured differently'
type: 'fix'
created: '2026-10-11'
status: 'in-progress'
baseline_revision: 'b2a5463598d82f5468738ec6f8cc45bcb3aaa92e'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - src/platform/tests/test_oidc_identity.py
  - src/platform/conftest.py
  - src/platform/config/observability/logging.py
  - scripts/platform-ci-local.sh
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** one platform test reconfigures structlog and never puts it back. Every later test in the same pytest
process then logs through that test's print logger instead of the platform's logging pipeline. Line numbers below are
at `e4ab638bb6`.

- **The platform's configuration.** `src/platform/config/settings/base.py:406` calls `configure_structlog()`
  (`src/platform/config/observability/logging.py:57-:70`) once, when the settings load. It sets the standard-library
  logger factory and bound logger, `cache_logger_on_first_use=True`, and nine processors that end in
  `ProcessorFormatter.wrap_for_formatter`, so each event reaches the stdlib logging pipeline, where `caplog` and the
  JSON or console renderer see it.
- **The leak.** `tests/test_oidc_identity.py::test_sync_ignores_unmatched_groups_and_logs` (:77-:92) calls
  `structlog.configure(processors=[KeyValueRenderer()], wrapper_class=make_filtering_bound_logger(0),
  logger_factory=PrintLoggerFactory(), cache_logger_on_first_use=False)` (:80-:85) and never restores it. It asserts
  nothing about logs.
- **Why it matters.** `scripts/platform-ci-local.sh`'s test stage runs `python -m pytest` once over `src/platform`, in
  one process. After the OIDC test, a structlog logger used for the first time prints a key-value line to stdout. A
  test that reads the event from `caplog`, or asserts what the production renderer writes, sees nothing. Loggers that
  were used before the leak keep the platform's chain, because they cached it on first use, so the failures depend on
  test order.
- **The guard is missing.** `src/platform/conftest.py`, the suite's only conftest (there is no `tests/conftest.py`),
  isolates caches between tests (`_isolate_caches`, :23-:61) but nothing checks structlog. The next leak would again
  show up in whatever test runs after it.

**Evidence:**
- **Found by warden Story 16.1's fix pass** (2026-10-11): a new platform test asserting a `task_failed` event rendered
  by the production JSON renderer failed only in the full suite. Warden's test pins its own structlog configuration on
  its own branch as a workaround; this story does not depend on that branch.
- **Reproduced on `e4ab638bb6`** with a scratch probe test (outside the tree), platform-ci-test's python and a scratch
  PostgreSQL 17 and Redis. The probe prints `structlog.get_config()`, logs one event and reads `caplog`:

  | run | probe sees | probe's event | result |
  |---|---|---|---|
  | probe alone | `LoggerFactory`, `BoundLogger`, cache on, 9 processors ending in `wrap_for_formatter` | in `caplog` as a dict | 1 passed |
  | `tests/test_oidc_identity.py`, then the probe | `PrintLoggerFactory`, `BoundLoggerFilteringAtNotset`, cache off, one `KeyValueRenderer` | `k='v' event='probe_event'` on stdout, `caplog` empty | 1 failed, 18 passed |
  | the leaking test alone, then the probe | the same print-logger configuration | stdout | 1 failed, 1 passed |
  | the file with the leaking test deselected, then the probe | the platform's configuration | in `caplog` | 18 passed |

- **The test's own configure is order-dependent.** Run alone, the mapper's `authorization.unknown_group_claim` warning
  prints as key-value. Run after a test that already used the mapper's logger, it goes through the JSON renderer,
  because that logger cached the platform's chain on first use.
- **One structlog leaker in the suite.** A scratch survey plugin compared `structlog.get_config()` before and after
  every test of the full platform suite and put it back after any change: 1208 passed, 13 skipped, and only
  `test_sync_ignores_unmatched_groups_and_logs` changed it. No test depends on the leaked configuration.
- **Other logging state, not structlog.** Five tests replace the root logger's handlers by running `django.setup()`
  again, which re-applies `settings.LOGGING` through `dictConfig`:
  - `tests/test_cloudevents_redis_broker.py`: `test_execute_supervised_run_leaves_no_celery_result_key`,
    `test_consume_events_command_runs_one_pass_for_station` and `test_enumerate_dlq_returns_quarantined_and_empty`
    (each through `_ensure_django`, :1176-:1179), and `test_consume_events_binds_the_broker_through_the_ad10_guard`
    (through `mcp_host.app._real_station_apps` on reload);
  - `tests/test_herald_webhook_sidecar.py::test_mcp_host_sidecar_herald_dependency_missing_not_blamed_on_herald`.

  They leave structlog's configuration alone and re-apply the platform's own `LOGGING`; what they drop is pytest's
  session handlers (live logging and `--log-file`), which no platform lane passes. The two handler edits in
  `tests/test_herald_portal_without_herald.py` run in child processes. No other in-process `structlog.configure`,
  `dictConfig`, `basicConfig` or root-logger change exists under `src/platform` (grep and the survey agree).

**Approach:** the leaking test restores what it changed, and a session guard fails any test that does not.
- **Restore in the test module.** A yield fixture in `tests/test_oidc_identity.py` saves `structlog.get_config()`
  before the test, with its processors list copied (`structlog.testing.capture_logs` edits that list in place, so an
  uncopied snapshot would change with it), and calls `structlog.configure(**saved)` after the test, whether it passed
  or failed. `test_sync_ignores_unmatched_groups_and_logs` requests it. The test's own `structlog.configure()` call and
  its assertions stay as they are.
- **Guard in the platform conftest.** An autouse fixture in `src/platform/conftest.py`:
  - records structlog's configuration once per session, before the first test's body runs, after the settings have
    configured it;
  - after every test, compares the current configuration with that baseline: the five keys of
    `structlog.get_config()`, with the processors compared element by element;
  - on a difference, restores the baseline first, so one leak cannot spread to later tests, then fails that test at
    teardown with a message that names its node id and the keys that differ.
- **Rejected:** restoring with `configure_structlog()` (it builds new processor objects, so it is not the configuration
  the session started with, and loggers that cached the old chain keep it); deleting the test's `configure` call (it
  changes what the test does, and the ask is to stop the leak); `structlog.reset_defaults()` (structlog's defaults are
  not the platform's configuration); guarding the stdlib root logger as well (the five `django.setup()` re-runs above
  would fail, and they re-apply the platform's own `LOGGING`).

Ledger key: `94-1-no-platform-test-leaves-structlog-configured-differently`.
Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **`spec-pyforge-steward` CAP-87** (telemetry, absorbed from `spec-platform-fifteen-factors`; Story 16.3 built the
  platform's structlog configuration). The leak makes later tests log outside that configuration, so tests of it pass
  or fail by test order. This story restores and guards it. It changes no behaviour CAP-87 names, so it needs no new
  CAP and no `SPEC.md` change. The two files it changes are on `spec-pyforge-unifying-strategy`'s surface.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag, and this one changes only test harness
  code.
- **Origin.** `docs/dreams/pyforge-steward.md` Realization log, 2026-10-11 (structlog configuration leak). The
  operator's ask, verbatim: "Do this task here: Stop test_oidc_identity leaking structlog config".

## Acceptance Criteria

- **AC1 — The OIDC test puts structlog back.**
  - **Given** the suite's baseline configuration, **When** `test_sync_ignores_unmatched_groups_and_logs` runs, pass or
    fail, **Then** after it `structlog.get_config()` equals the configuration it started with (the same five values,
    the processors element by element).
  - The restoring fixture lives in `tests/test_oidc_identity.py`, saves `get_config()` with its processors list copied,
    and restores with `structlog.configure(**saved)` in its teardown.
  - The probe under Verification, run after `tests/test_oidc_identity.py`, passes: it sees the platform's
    configuration and its event reaches `caplog` as a dict.
- **AC2 — The guard fails a leak, names it, and stops it spreading.**
  - An autouse fixture in `src/platform/conftest.py` records the baseline once per session, before the first test's
    body, and checks it after every test.
  - A test that leaves structlog's configuration different fails at teardown. The failure names the test's node id and
    the keys of `get_config()` that differ.
  - Before failing, the guard restores the baseline, so the next test runs on the platform's configuration.
- **AC3 — Mutations.**
  - With the AC1 fixture removed from the OIDC test, `pytest tests/test_oidc_identity.py` exits 1 with an error at the
    teardown of `test_sync_ignores_unmatched_groups_and_logs`, and the message names it.
  - A temporary probe file under `src/platform/tests/` holding one test that calls `structlog.configure(...)` without
    restoring, and a second test that asserts `get_config()["logger_factory"]` is a `structlog.stdlib.LoggerFactory`,
    exits 1: the first test errors at teardown and names itself, and the second passes.
  - Both changes are reverted afterwards, and the spec's Auto Run Result records each outcome.
- **AC4 — The guard passes the suite as it stands.** With AC1 in place, the whole platform suite passes under the
  guard. The survey found the OIDC test the only one that changes structlog's configuration. The guard checks
  structlog's configuration only. The five tests that re-run `django.setup()` change the root logger's handlers, not
  structlog, and are out of scope; the guard neither checks nor fails them.
- **AC5 — Never weakened, nothing else moves.** The diff adds no `skip`, `skipif`, `xfail`, rerun marker or plugin.
  The OIDC test's assertions and its `structlog.configure()` call do not change. `git diff origin/main...HEAD --stat`
  outside `_bmad-output/` and `scripts/.spec-surface-baseline.json` names only `src/platform/tests/test_oidc_identity.py`
  and `src/platform/conftest.py`. `config/observability/logging.py`, the settings and every other test are unchanged.
- **AC6 — The platform suite is green.** `pixi run -e pyforge-guild platform-ci-local -- --test` exits 0, including its
  Ruff, Ruff format and mypy steps.
- **AC7 — The surface is reconciled.** The `spec-pyforge-unifying-strategy` memlog gets a surface-reconcile entry that
  names both files and this story, the Spec is stamped scoped (`--spec
  pyforge-steward/spec-pyforge-unifying-strategy`), and `spec-surface-check` exits 0.

## Boundaries & Constraints

**Always:**
- Change only `src/platform/tests/test_oidc_identity.py` and `src/platform/conftest.py`, plus this story's memlog entry
  and scoped stamp.
- Compare against the configuration the session started with, never against a rebuilt copy of it.
- Restore before failing, so one leak produces one failure.

**Never:**
- Never change the platform's logging configuration, its settings or `configure_structlog()`.
- Never change what the OIDC test asserts, and never skip, `xfail` or rerun a test.
- Never fail a test for the root logger's handlers; that is not this guard's job.
- Never add a dependency.

**Residual risk:**
- The guard catches a change to structlog's configuration, not to an individual logger. A test that binds a module
  logger to a private chain without calling `structlog.configure()` would pass it; none does today.
- Loggers that cached a leaked chain before the guard restored the baseline keep it. With `cache_logger_on_first_use`
  set to False by the only leaker today, none does; a future leaker that sets it to True would be reported by the
  guard, but loggers first used inside that test would keep its chain.
- The five `django.setup()` re-runs above keep replacing the root logger's handlers. Harmless today; they would matter
  only to a lane that passes `--log-file` or live logging.

## I/O & Edge-Case Matrix

| Situation | Today (`e4ab638bb6`) | After |
|---|---|---|
| the OIDC sync test runs, then a later test logs a new event | the event prints to stdout; `caplog` and the JSON renderer see nothing | the platform's pipeline; `caplog` sees it |
| the OIDC sync test fails part-way | configuration leaks | the fixture still restores it |
| a new test calls `structlog.configure()` and does not restore it | a later, unrelated test may fail | that test errors at teardown, naming itself; the baseline is restored |
| a test uses `structlog.testing.capture_logs()` | restored by structlog | unchanged; the guard sees no difference |
| a test re-runs `django.setup()` | root handlers replaced | unchanged; not guarded |
| the probe run after `tests/test_oidc_identity.py` | fails | passes |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-87 (telemetry), built by Story 16.3. No CAP is minted, and no
  `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-11 (structlog configuration leak) entry.
- Epic: Epic 94 (new). Epic 16, which built the configuration and the OIDC tests, is `done`, so the fix opens its own
  epic. `epic-94` and `epic-94-retrospective` are minted with it.
- Ledger key: `94-1-no-platform-test-leaves-structlog-configured-differently`.
- Ledger status at mint: `backlog`.
- Deps: none.
- Spec: the `spec-pyforge-steward` memlog records the ask verbatim, the evidence and design, and this mint; the
  `spec-pyforge-unifying-strategy` memlog records the incoming surface claim on its two files.
- Surface: `marshal-policy.toml` `[epic_surfaces]."94"` (added with this mint) covers `src/platform/tests/**` and
  `src/platform/conftest.py`.
- Minted 2026-10-11 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding). It does not run `src/platform/tests`; the dispatch runs `platform-ci-local -- --test` as its cross-surface check (MRS-GATE-015) because the diff touches `src/platform/`.

**Run before the push (not dispatch gates):**
- The AC1 probe. Write it to a temporary directory outside the tree, then run it after the OIDC module from `src/platform`, with platform-ci-test's python and a PostgreSQL and Redis reachable at `DATABASE_URL` and `REDIS_URL` (as `scripts/platform-ci-local.sh`'s `start_services` provides): `env -u PYTHONSAFEPATH python -m pytest -c pyproject.toml -p no:cacheprovider -q tests/test_oidc_identity.py "$PROBE_DIR/test_zz_structlog_probe.py"`. The probe's one test logs `structlog.get_logger("platformapp.probe").info("probe_event")` inside `caplog.at_level(logging.INFO, logger="platformapp.probe")` and asserts that `get_config()["logger_factory"]` is a `structlog.stdlib.LoggerFactory`, `wrapper_class` is `structlog.stdlib.BoundLogger`, `cache_logger_on_first_use` is True, the last processor is `structlog.stdlib.ProcessorFormatter.wrap_for_formatter`, and a dict record with `event == "probe_event"` is in `caplog.records`. Expected: exit 0 (on `e4ab638bb6` it exits 1).
- The AC3 mutations — expected: each exits 1 with the teardown error naming the leaking test, and the second probe test passes. Revert both.
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: exit 0 (AC4, AC6).
- `git diff origin/main...HEAD --stat` — expected: AC5's two code paths.
- `python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entry and the scoped stamp (AC7).
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: no new finding against `main`.

## Spec Change Log

- 2026-10-11: minted from the operator's ask "Do this task here: Stop test_oidc_identity leaking structlog config".
  `type: fix`, no flag, no CAP; bound to `spec-pyforge-steward` CAP-87 through Story 16.3.
