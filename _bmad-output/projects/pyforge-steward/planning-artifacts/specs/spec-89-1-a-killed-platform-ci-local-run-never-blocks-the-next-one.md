---
title: "89.1: A killed `platform-ci-local` run never blocks the next one"
type: 'fix'
created: '2026-10-10'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-63-7-two-platform-ci-local-runs-at-once-never-share-services-or-a-work-dir.md
  - scripts/platform-ci-local.sh
  - src/shared/packages/pyforge-steward/tests/unit/test_platform_ci_local_concurrency.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** a killed `platform-ci-local` run leaves its lock held. The next run waits the full bound (7200 s) for a
dead owner, then exits 2. Line numbers below are at `8ad2d18d69`.

- **How the lock is held.** `acquire_run_lock` (:57-:81) opens the lock file on fd 9 (`exec 9>"$lock_file"`, :63),
  takes `flock -w "$wait_sec" 9` (:64; `PLATFORM_CI_LOCAL_LOCK_WAIT`, default 7200 s, :61) and writes `pid`,
  `checkout`, `stages` and `started` to `<lock>.holder` (:74-:79). Bash does not mark fd 9 close-on-exec, so every
  command the script starts inherits it.
- **Who else holds it.** `start_services` (:117-:132) starts PostgreSQL with `pg_ctl ... start` (:122) and Redis with
  `redis-server --daemonize yes --pidfile "$WORK/redis.pid"` (:129-:130). Both inherit fd 9, and both detach into a
  session of their own. On the live run of 2026-10-10 (shell pid 2823842, started 13:24 -05:00), `ps` showed the
  postmaster and redis-server each with a session id equal to its pid, reparented away from the run, and
  `/proc/<pid>/fd/9` of each pointed at `/tmp/platform-ci-local.lock`. So a signal to the run's process group never
  reaches them, and while they live the `flock` stays held.
- **What the trap covers.** `trap stop_services EXIT` (:139) stops the services when the shell exits normally, and on
  SIGTERM (bash runs the EXIT trap then). It cannot run on SIGKILL, and a trap cut short (a SIGKILL inside a
  terminator's grace window) leaves the services up.
- **What the next run does.** It blocks in `flock -w` for the whole bound, then prints "lock held longer than
  ${wait_sec}s" and the `.holder` record, which names the dead pid as the holder (:64-:72).
- **What it would do with the lock.** `start_services` begins with `stop_services` (:119), which stops the
  PostgreSQL in `$WORK/pg` through `pg_ctl` and kills the pid in `$WORK/redis.pid` (:136-:137). Every default run
  shares one work dir, so that call would reach a dead run's services. But it checks nothing first: the pid in
  `redis.pid`, or the one `pg_ctl` reads from `postmaster.pid`, may by then belong to another process. And anything
  outside the work dir is invisible to it: a dead run's PostgreSQL under another `PLATFORM_CI_LOCAL_WORK`, or any
  other listener on 15432, makes `pg_ctl start` fail with its output thrown away (:122-:123). `pg_isready`, `psql` and
  the suite then talk to that other server.

**Evidence:**
- **The kill.** Dispatch run `pyforge-steward-20261010T154144466Z-88c00f58` (steward 87.3): verification was refused
  on `pixi run -e pyforge-guild platform-ci-local -- --test` (MRS-GATE-015), and the verify-fix turn ran. At
  16:19:55Z the supervisor's `terminate_process_group` signalled the fix session (journal: `signalled_term: true`,
  `signalled_kill: false`, `returncode: 143`). The outcome was `MRS-DISP-059` after 900.18 s
  (`verify_fix_wall_clock_minutes`, default 15).
- **What it left.** The run inside that turn had started at 11:05:24 -05:00. After the kill, `.lock.holder` still
  read `pid=2564298`, `checkout=.worktrees/dispatch-pyforge-steward-87.3`, `stages=test`. `fuser -v
  /tmp/platform-ci-local.lock` listed postgres 2564337-2564343 and redis-server 2564352, and no live run.
- **The cost.** The re-verification, started about 11:22 -05:00, waited 7200 s and exited 2 with
  "platform-ci-local: lock held longer than 7200s — not starting services". Only TERMing the orphaned postmaster and
  redis-server released the lock.
- **Reproduced without Docker** at `8ad2d18d69`, with Story 63.7's stub root and a `redis-server` stand-in that
  detaches (`setsid sleep`). After `killpg(SIGKILL)` of the run, the stand-in still had the lock open. The next run,
  with `PLATFORM_CI_LOCAL_LOCK_WAIT=3`, exited 2 after 3.0 s and named the dead pid as the holder.
- **Closing the fd alone is not the fix.** With `9>&-` on that one call, the next run took the lock in 0.1 s and
  passed. But the dead run's stand-in was still running beside it.
- **Why Story 63.7's tests missed it.** `test_sigkilled_holder_does_not_block_next_run` kills the run's process group,
  and its stubs exit at once. No stub outlives the run in a session of its own, the way the postmaster and a
  daemonized redis-server do.

**The trigger is marshal; the defect is here.** Marshal's `terminate_process_group` (SIGTERM to the session's group,
SIGKILL after 5 s) is how this run died. Any kill does the same: a harness tool timeout, an operator's `kill -9`, the
OOM killer. The lock and the services belong to `scripts/platform-ci-local.sh`, so the fix lives there. Marshal's
verification command, its kill path and its gate do not change.

**Approach:** the lock lives exactly as long as the run's own shell, and the next run clears what a dead run provably
left.
- **Only the shell holds the lock.** Every command the script starts runs with the lock's descriptor closed:
  PostgreSQL, Redis, each step, the container engine and the helpers.
  - Bash allows a one-line form: run the body after `acquire_run_lock` as one function call with `9>&-`, and exit
    from inside it. Bash keeps its own close-on-exec copy of fd 9 for the call, so the shell keeps the lock and no
    child inherits it. Exiting inside the call matters: the EXIT trap then runs with fd 9 still closed, while a body
    that returns first hands fd 9 back to the trap's `pg_ctl` and engine calls. Both behaviours were checked in a
    scratch harness on 2026-10-10 (bash 5.2).
  - The lock is never handed to a wrapper process such as `flock(1)` in command mode. A wrapper killed alone would
    free the lock while the run is still alive.
  - So a SIGKILL to the group or to the shell alone frees the lock at once.
- **The next run reclaims what a dead run provably left in the work dir.** Holding the lock proves no other run is
  live, so services whose pid files sit in the run's own work dir were left by a dead run. The `stop_services` call
  at the top of `start_services` stays the reclaim, with three changes:
  - **an identity check before any signal:** PostgreSQL is stopped through `pg_ctl -D "$WORK/pg" stop -m fast` only
    when `postmaster.pid` names a live pid whose `/proc/<pid>/cmdline` is postgres on `-D "$WORK/pg"`. Redis is
    stopped only when `$WORK/redis.pid` names a live pid whose command line is `redis-server`. A pid that is dead, or
    that now belongs to another process, is never signalled, and its stale pid file is removed;
  - **a log line for each stop,** naming the service and its pid, so a reclaim is visible in the run's output;
  - **a bounded wait** until each stopped pid has exited, before the run starts its own.
- **It refuses what it cannot prove.** After the reclaim, and before starting its own services, the run checks that
  its PostgreSQL and Redis ports are free. A port still taken, by a dead run's service under another work dir or by
  anything else, is a refusal: exit 2, no service started, nothing signalled. Stderr names the port, the listening
  pid and its command line.
- **A contended wait names the live holder.** When `flock -w` times out, the message lists the processes that hold
  the lock file open now, each with its pid and command line. The `.holder` record is shown as the holder only when
  its pid is alive and among them. Otherwise it is shown marked `stale (pid N not running)`.
- **Unchanged:**
  - the normal-exit and SIGTERM path: `trap stop_services EXIT` still stops the run's own services;
  - the `.holder` record's four lines (`pid`, `checkout`, `stages`, `started`);
  - the overrides `PLATFORM_CI_LOCAL_LOCK`, `_LOCK_WAIT` (default 7200), `_NO_LOCK`, `_PG_PORT`, `_REDIS_PORT`,
    `_WORK`, `_TAG` and `_ENGINE`;
  - the stage flags, the workflow step names, the summary, and the exit codes (0 pass, 1 a step failed, 2 usage or
    environment);
  - marshal's command.

**Why this shape, per the steward spine:**
- **AD-1 (wrap, never reimplement).** The `flock` stays the one liveness oracle; no second pid-file liveness scheme
  appears. Services are stopped through what owns them, `pg_ctl stop` and the pid file `redis-server` wrote, never by
  `pkill` on a name or a kill by port. The reclaim is the script's own `stop_services`, made safe, not a second
  cleanup path.
- **Story 63.7's boundary still holds.** "Never let one run stop, delete or truncate anything another run started."
  The lock proves no other run is live, and a reclaim stays inside the run's own work dir, behind an identity check on
  every pid.
- **Exit 2 keeps its 63.7 meaning (usage or environment).** A port held by a process the run cannot prove is a dead
  run's is an environment problem, and the run refuses it by name.
- **Rejected: refuse every leftover, naming the pids.** Every marshal verify-fix cap would leave the next dispatch
  verification refused until someone killed pids by hand. That is the 2026-10-10 failure again, with a shorter wait.
- **Rejected: kill whatever holds the ports or the lock.** It would stop an unrelated PostgreSQL or Redis on
  15432 or 16379, or a live run's services, which Story 63.7 forbids.

Ledger key: `89-1-a-killed-platform-ci-local-run-never-blocks-the-next-one`.
Type / Effort / Deps: fix / M / none.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-steward` CAP-152: `platform-ci-local` is a task a station shells to,
  reachable from `pyforge-guild` (Story 63.6). Story 63.7 made overlapping runs serialise on this lock, and its epics
  block promised that "a holder that died never blocks a later run". This story fixes the realization of shipped
  behaviour, so it mints no CAP and changes no `SPEC.md`.
- **Governance.** `scripts/platform-ci-local.sh` is on `spec-pyforge-steward`'s `surface:`.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag: it restores intended behaviour, and a
  flag would keep the bug reachable.
- **Origin.** `docs/dreams/pyforge-steward.md` Realization log, 2026-10-10 (platform-ci-local lock outlives its run).
  Operator ruling 2026-10-10, verbatim: "yes mint the platform-ci-local lock fix story".

## Acceptance Criteria

Every criterion runs the real `scripts/platform-ci-local.sh` against stubs under a temporary `PIXI_PROJECT_ROOT`, as
Story 63.7's tests do. None needs PostgreSQL, Redis, Docker or podman.

**The stand-ins.** The service stand-ins replace `pg_ctl ... start` and `redis-server`. Each one:
- detaches into its own session (`setsid`) and keeps running;
- writes the pid file the real tool writes (the first line of `<work>/pg/postmaster.pid`, or `<work>/redis.pid`);
- has a command line naming its data dir or port.

The `pg_ctl ... stop` stub reads `postmaster.pid` and stops that pid. Every stub (service, step, engine) appends to
the stub log whether any link in `/proc/self/fd` points at the lock file.

- **AC1 — No child of the run holds the lock.**
  - **Given** the stand-ins above **When** `--test` runs to completion **Then** no stub and no stand-in ever had the
    lock file open.
  - While the run is in a step, the only process with the lock file open is the run's shell.
- **AC2 — A killed run never blocks the next one.** Both runs share one work dir, as every default run does.
  - **Given** a run with its stand-ins up, killed in one of three ways: (a) SIGKILL to its process group, (b) SIGKILL
    to its shell alone during a slow step, (c) SIGTERM to its process group.
  - **When** a second run starts with `PLATFORM_CI_LOCAL_LOCK_WAIT=5` **Then** it takes the lock without waiting out
    the bound, prints `RESULT: PASS` and exits 0.
  - In (a) and (b) the second run first stops the dead run's stand-ins, and the stub log names each stop with the
    dead pid. In (c) the dead run's EXIT trap has already stopped them, and the second run finds nothing to stop.
  - After the second run ends, no stand-in from either run is alive.
- **AC3 — Never reuse, never guess.**
  - **Given** a listener with no pid file in the run's work dir, on the run's PostgreSQL port and then on its Redis
    port: a Python socket bound to a free port, which the test passes as `PLATFORM_CI_LOCAL_PG_PORT` or `_REDIS_PORT`.
  - **When** a run takes the lock **Then** it starts no service and exits 2. The listener is still alive, and stderr
    names the port, the listener's pid and its command line.
  - **Given** pid files in the work dir (`postmaster.pid`, then `redis.pid`) naming a live pid whose command line is
    not the expected service (a reused pid, stood in for by a plain `sleep`) **When** a run takes the lock **Then**
    that process is never signalled and is still alive when the run ends.
- **AC4 — The wait names the live holder.**
  - **Given** the lock held by a live stand-in that opens and `flock`s the lock file, and a `.holder` record naming a
    dead pid.
  - **When** a run's wait passes `PLATFORM_CI_LOCAL_LOCK_WAIT` **Then** it exits 2 without starting a service.
    Stderr names the stand-in's pid and command line as the holder, and shows the record marked stale with the dead
    pid.
  - With a live recorded holder (Story 63.7's `test_lock_wait_timeout_names_holder`) the record is shown as the
    holder, as today.
- **AC5 — A normal run still cleans up.** **Given** one uncontended run that passes and one whose step fails **When**
  each ends **Then** its EXIT trap has stopped its own stand-ins (the stub log shows it), and none is alive. The exits
  are 0 and 1, and a following run finds nothing to reclaim.
- **AC6 — Story 63.7 stays green.**
  - The six tests in `test_platform_ci_local_concurrency.py` pass.
  - Their only changes:
    - the shared helper and the SIGKILL test pass free ports (`PLATFORM_CI_LOCAL_PG_PORT`, `_REDIS_PORT`), so a real
      `platform-ci-local` run on the same machine never changes their verdict (one held 15432 and 16379 while this
      story was minted);
    - the `pg_ctl ... start` and `redis-server` stubs write the pid files the real tools write, so the identity check
      has something to check. The real `pg_ctl stop` does nothing without a `postmaster.pid` either.
  - No assertion is weakened or removed. The no-lock mutation test
    (`test_without_lock_overlapping_runs_do_not_both_pass`) still sees one run stop the other's services.
  - The stage flags, step names, summary lines, exit codes 0 / 1 / 2, the `PLATFORM_CI_LOCAL_*` overrides, the 7200 s
    default wait and marshal's command do not change.
- **AC7 — Mutation.**
  - Letting the services inherit the lock's descriptor again fails AC1 and AC2 (a): the next run waits out its bound
    and exits 2, as at `8ad2d18d69`.
  - Letting the steps inherit it fails AC1 and AC2 (b).
  - Dropping the reclaim fails AC2's "no stand-in alive".
  - Dropping the identity check fails AC3's reused-pid case.
  - Dropping the port check fails AC3's listener case.
  - Dropping the liveness check fails AC4.

## Boundaries & Constraints

**Always:**
- Fix it in `scripts/platform-ci-local.sh`. Put the tests in the steward suite, beside Story 63.7's, so the station's
  `verify_commands` runs them.
- Keep the lock one machine-wide `flock`, held by the run's own shell for the whole run.
- Check a pid's identity in `/proc/<pid>/cmdline` before signalling it, and stop PostgreSQL through `pg_ctl`.
- In the tests, kill only processes the test started, and reap every stand-in at teardown, pass or fail.
- Reconcile every governed path the change touches on the memlogs of the Specs that govern it, then stamp those Specs
  scoped: `spec-pyforge-steward` and any co-governor `spec-surface-check` names (AGENTS.md pre-PR item 5).

**Never:**
- Never change marshal's verification command, its rule table, `terminate_process_group` or the verify-fix budget.
- Never signal, stop or reuse a process the run cannot prove a dead run started. Never kill by port or by name.
- Never hold the lock in a separate wrapper process.
- Never wait without a bound, and never fail a wait without naming the live holder.
- Never weaken or delete an existing test.

**Residual risk:**
- When only the shell is SIGKILLed (AC2 (b)), its running step is orphaned. It keeps running against the dead run's
  services until the next run's reclaim stops them, and its log output is lost. The dead run has no verdict left to
  protect.
- A dead run whose work dir is gone (a cleaned `/tmp`), or that ran under another `PLATFORM_CI_LOCAL_WORK` on the
  same ports, leaves no pid files where the next run looks. Services it left are found only by the port check, which
  refuses them by name, and the operator stops them. Every default run, marshal's included, shares one work dir, so
  this needs an override or a cleaned `/tmp`.
- The pid checks read `/proc`, so the script stays Linux-only, as `flock` and `ss` already make it.

## I/O & Edge-Case Matrix

| Situation | Today (`8ad2d18d69`) | After |
|---|---|---|
| run ends normally, or its group gets SIGTERM | the trap stops its services; the lock is freed | unchanged |
| run's group gets SIGKILL | the services keep fd 9; the next run waits 7200 s and exits 2, naming the dead pid | the lock is freed at once; the next run stops the dead run's services, then runs |
| run's shell alone gets SIGKILL | the services and the running step keep fd 9 | the lock is freed at once; the next run stops the dead run's services, then runs |
| a port is held by a process with no pid file in the work dir | `pg_ctl start` fails unseen; the suite talks to that server | exit 2 naming the port, pid and command line; nothing signalled |
| a pid in the work dir's pid files now belongs to another process | `stop_services` signals it unchecked (`kill` on `redis.pid`, `pg_ctl stop` on `postmaster.pid`) | never signalled; the stale pid file is removed |
| the lock is held by a live run | waits, then exit 2 printing the record | unchanged, plus the live holder's pid and command line; a stale record is marked stale |

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-10 (platform-ci-local lock outlives its
  run) entry.
- Epic: Epic 89 (a new fix epic, because Epic 63, which shipped Story 63.7 under CAP-152, is `done`).
- Ledger key: `89-1-a-killed-platform-ci-local-run-never-blocks-the-next-one`.
- Ledger status at mint: `backlog`.
- Deps: none.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- A real kill:
  - Start `pixi run -e pyforge-guild platform-ci-local -- --test`. Once `services:` is printed, `kill -9` its process
    group.
  - Start it again with `PLATFORM_CI_LOCAL_LOCK_WAIT=60`. Expected: it takes the lock at once, logs stopping the
    first run's postmaster and redis-server by pid, and prints `RESULT: PASS`.
  - While it runs, `fuser -v /tmp/platform-ci-local.lock` lists only its shell.
- `pixi run -e pyforge-guild platform-ci-local -- --test` alone — expected: `RESULT: PASS`, exit 0, and no postgres
  or redis-server from it left running.
- Mutation: let the services inherit fd 9 again and re-run the new test module; AC1 and AC2 fail. Restore it.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconciles and scoped
  stamps.
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: no new finding against `main`.
