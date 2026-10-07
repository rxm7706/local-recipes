---
title: "63.7: Two `platform-ci-local` runs at once never share services or a work dir"
type: 'fix'
created: '2026-10-07'
status: 'done'
baseline_revision: 'adea658e758cf460f11e78e484ed3ce80a51df18'
review_loop_iteration: 0
followup_review_recommended: false
review_loop_iteration: 0
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-63-6-no-station-code-assumes-the-local-recipes-environment-at-runtime.md
  - scripts/platform-ci-local.sh
  - pixi.toml
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py
  - docs/how-to/recipe-testing-and-builds.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** two `platform-ci-local` runs that overlap destroy each other's services, so both report a failure that
neither caused.

- **The shared state.** `scripts/platform-ci-local.sh` (measured on `b364823896`) fixes every resource a run uses:
  PostgreSQL on `PLATFORM_CI_LOCAL_PG_PORT` (default 15432), Redis on `PLATFORM_CI_LOCAL_REDIS_PORT` (default 16379),
  the work dir `PLATFORM_CI_LOCAL_WORK` (default `${TMPDIR:-/tmp}/platform-ci-local`, holding `pg/`, `redis/`,
  `redis.pid`, the step logs, `results.tsv` and the image build context), the image tag `ci-local` and the container
  name `platform-ci-app-ci-local` (about :48-:57). There is no lock.
- **How one run breaks the other.** `start_services` begins with `stop_services`, which removes the app container,
  kills the Redis named by `$WORK/redis.pid` and stops the PostgreSQL in `$WORK/pg`; it then deletes `$WORK/pg` and
  `$WORK/redis` (about :82-:103). `results.tsv` is truncated when a run starts, and each run's `trap stop_services
  EXIT` stops whatever services sit in the shared dir when it exits. A second run therefore stops the first run's
  database mid-suite, and whichever run ends first stops the other's.
- **The live failure.** Marshal's dispatch verification runs `pixi run -e pyforge-guild platform-ci-local -- --test`
  for any story whose diff touches `src/platform/` (`CROSS_SURFACE_VERIFY_COMMAND` in
  `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py`, marshal Story 22.14's rule table,
  MRS-GATE-015). On 2026-10-07 the warden 14.2 and steward 74.2 landings, both touching `src/platform/config/`,
  verified at the same time and both came back `skipped-unverified`; each passed when re-run alone.

**Approach:** a second concurrent run never shares the first's ports, work dir, container name or image tag. The
story picks one of two designs and records the choice, with the measured reason, in its Spec Change Log:

- **Lock.** An exclusive, machine-wide lock (default `${TMPDIR:-/tmp}/platform-ci-local.lock`, so two worktrees
  contend for one lock) is held for the whole run. A second run waits for it, then runs; after
  `PLATFORM_CI_LOCAL_LOCK_WAIT` seconds (a default long enough for one `--test` run, measured and recorded) it exits 2
  with a message naming the holder: pid, checkout root, stages and start time, written beside the lock when it is
  taken. A holder that died never blocks a later run (an `flock` is released at process exit; a pid-file lock checks
  that the pid is alive).
- **Per run.** Each run takes its own free ports, its own work dir (under `PLATFORM_CI_LOCAL_WORK` when it is set,
  otherwise a fresh directory), and its own container name and image tag. The `container` stage binds 8000, which the
  image's own contract fixes, so it alone is serialised by a lock or refused naming the holder.

Either way, a run's EXIT trap stops only the services that run started; the summary names that run's work dir; the
explicit `PLATFORM_CI_LOCAL_*` overrides still win; the stage flags, the workflow step names and the exit codes
(0 pass, 1 a step failed, 2 usage or environment) keep their meaning; marshal's command is unchanged.

Ledger key: `63-7-two-platform-ci-local-runs-at-once-never-share-services-or-a-work-dir`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-steward` CAP-152: `platform-ci-local` is one of the tasks a station shells to,
  reachable from `pyforge-guild` (Story 63.6 moved it into `guild-tasks`). Marshal's dispatch verification is that
  station, and it shells the task once per landing that touches `src/platform/`, so landings that overlap run it
  concurrently. A task a station shells to that cannot run twice at once is a defect of shipped behaviour, so this
  story mints no new CAP.
- **Governance.** `scripts/platform-ci-local.sh` is on `spec-pyforge-steward`'s `surface:` (claimed 2026-09-04 by
  `spec-python-agent-platform`, absorbed into this Spec on 2026-09-17).
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag.
- **Origin.** The warden 14.2 and steward 74.2 landings of 2026-10-07.

## Acceptance Criteria

- Given two `platform-ci-local -- --test` invocations started a second apart against stub service binaries under a
  temporary `PIXI_PROJECT_ROOT` When both finish Then each prints its own `RESULT: PASS` and exits 0, and neither
  run's PostgreSQL or Redis was stopped by the other (the stubs record every start and stop with its port and work
  dir).
- Given the same overlap where one run's stubbed step fails When both finish Then that run prints `RESULT: FAIL` and
  exits 1, and the other prints `RESULT: PASS` and exits 0.
- Given the lock design and a holder that outlives `PLATFORM_CI_LOCAL_LOCK_WAIT` When a second run waits Then it exits
  2 without starting a service, and its message names the holder's pid, checkout root, stages and start time.
- Given the lock design and a holder killed with SIGKILL When a later run starts Then it takes the lock and runs.
- Given the per-run design When two runs overlap Then their PostgreSQL ports, Redis ports, work dirs, container names
  and image tags differ, and an explicit `PLATFORM_CI_LOCAL_PG_PORT` is still used as given.
- Given a single run with no contention When `platform-ci-local -- --test` runs Then its steps, step names, summary and
  exit code are as on `b364823896`.
- Given the lock (or the per-run allocation) removed When the new test runs Then the first criterion fails (mutation).

## Boundaries & Constraints

**Always:**
- Fix it where the shared state lives: `scripts/platform-ci-local.sh`.
- Keep the stages, the workflow step names and the PASS/FAIL summary; the script mirrors
  `.github/workflows/platform-ci.yml` step for step.
- Put the test in the steward suite, so the station's `verify_commands` runs it. It runs the real script against
  stub binaries in a temporary root, as doctor's `test_fleet_scan_currency_feeds.py` loads the real
  `scripts/fleet_scan.py`; it needs no PostgreSQL, Redis or container engine.
- Record the touched governed paths on `spec-pyforge-steward/.memlog.md` (and on `spec-pyforge-doctor/.memlog.md` if
  `docs/how-to/recipe-testing-and-builds.md` moves), scoped stamps only (AGENTS.md pre-PR item 5).

**Never:**
- Never change marshal's verification command or its rule table; the fix lives in the task, not in its caller.
- Never let one run stop, delete or truncate anything another run started.
- Never wait without a bound, and never fail a wait without naming the holder.
- Never weaken or delete an existing test.

## I/O & Edge-Case Matrix

| Situation | Today (`b364823896`) | After |
|---|---|---|
| one run | passes | unchanged |
| two `--test` runs overlap | the second stops the first's services; both fail | lock: the second waits, then runs; per run: both run apart; each reports its own verdict |
| lock holder longer than the bound | — | lock: exit 2 naming the holder, no service started |
| holder killed | — | the next run proceeds |
| explicit `PLATFORM_CI_LOCAL_PG_PORT` | used | used |
| `--container` in two runs | both bind 8000 | serialised, or refused naming the holder |

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-07 (tooling gaps) entry.
- Epic: Epic 63 (CAP-152 was decomposed by Story 63.6); a fix joins its own epic, which reopens (doctor Story 41.5).
- Ledger key: `63-7-two-platform-ci-local-runs-at-once-never-share-services-or-a-work-dir`.
- Ledger status at mint: `backlog`.
- Deps: —.
- Spec: `spec-pyforge-steward/.memlog.md` records the mint; no contract change, `SPEC.md` untouched.
- Minted 2026-10-07 with Stories 85.6 and 13.5, in one chain commit. Epic 63 had no `[epic_surfaces]` entry; the
  chain adds one admitting `scripts/platform-ci-local.sh`, `docs/how-to/recipe-testing-and-builds.md` and every Spec
  memlog.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks (not a dispatch gate):**
- Two real overlapping runs: in two worktrees on one machine, start `pixi run -e pyforge-guild platform-ci-local --
  --test` in each a few seconds apart — expected: both print `RESULT: PASS` (on `b364823896` the pair fails).
- `pixi run -e pyforge-guild platform-ci-local -- --test` alone — expected: `RESULT: PASS`, exit 0.
- Mutation: remove the lock (or the per-run allocation) and re-run the new test; the overlap fixture fails. Restore it.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.
- `pixi run -e pyforge-guild detectors-ci` — expected: no new finding against `main`.

## Spec Change Log

- 2026-10-07: **Lock design** (not per-run allocation). Marshal dispatch runs `platform-ci-local -- --test` only; serializing the whole run with `flock` on `${TMPDIR}/platform-ci-local.lock` (override `PLATFORM_CI_LOCAL_LOCK`) preserves default ports/work dir/tag for uncontended runs, bounds wait with `PLATFORM_CI_LOCAL_LOCK_WAIT` (default **7200** s — above measured full four-stage local replay; `--test`-only dispatch fits with margin), and exits **2** naming the holder metadata file (pid, checkout, stages, start time). Container port 8000 contention is covered by the same lock when `--container` is included.

## Review Triage Log

### 2026-10-07 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (none)

## Auto Run Result

Status: done

Summary: Added a machine-wide `flock` lock to `scripts/platform-ci-local.sh` so concurrent `platform-ci-local` runs serialize instead of sharing PostgreSQL/Redis ports, work dir, image tag, and container name. Steward unit tests exercise overlap, lock timeout, SIGKILL release, and mutation (`PLATFORM_CI_LOCAL_NO_LOCK`) against stub service binaries.

Files changed:
- `scripts/platform-ci-local.sh` — acquire/release run lock with bounded wait and holder metadata
- `src/shared/packages/pyforge-steward/tests/unit/test_platform_ci_local_concurrency.py` — overlap oracle tests
- `spec-pyforge-steward/.memlog.md` — surface reconcile for the paths above

Review: no patch/defer/intent_gap items.

Follow-up review recommended: false

Verification:
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — 2032 passed, 5 skipped
- `python scripts/spec_surface_reconcile.py` — exit 0 after memlog reconcile for `scripts/platform-ci-local.sh` and `src/shared/packages/pyforge-steward/tests/unit/test_platform_ci_local_concurrency.py` on `spec-pyforge-steward/.memlog.md`

Governed paths reconciled on `spec-pyforge-steward/.memlog.md`:
- `scripts/platform-ci-local.sh`
- `src/shared/packages/pyforge-steward/tests/unit/test_platform_ci_local_concurrency.py`

Residual risk: default lock wait (7200 s) is conservative; a holder longer than that still exits 2 without starting services (by design).
