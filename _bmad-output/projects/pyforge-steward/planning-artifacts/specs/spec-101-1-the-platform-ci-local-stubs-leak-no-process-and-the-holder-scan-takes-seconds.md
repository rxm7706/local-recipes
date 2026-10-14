---
title: "101.1: The `platform-ci-local` stubs leak no process, and the holder scan takes seconds"
type: 'fix'
created: '2026-10-14'
status: 'ready-for-dev'
baseline_revision: 'e0ad43f18c12c7c6e223c2f44b763c3e529db877'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-89-1-a-killed-platform-ci-local-run-never-blocks-the-next-one.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-96-1-platform-ci-local-never-runs-a-stage-on-a-stale-env.md
  - scripts/platform-ci-local.sh
  - src/shared/packages/pyforge-steward/tests/unit/test_platform_ci_local_concurrency.py
  - src/shared/packages/pyforge-steward/tests/unit/test_platform_ci_local_killed_holder.py
  - src/shared/packages/pyforge-steward/tests/unit/test_platform_ci_local_env_sync.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the `platform-ci-local` tests leave processes running after every run. Once enough have built up, a lock
wait spends minutes listing who holds the lock, and the tests that check that listing time out. Line numbers are at
`e0ad43f18c`.

- **The leak.** `_prepare_stub_root` (`test_platform_ci_local_concurrency.py`) writes one stub for `pg_ctl`,
  `redis-server` and the other service tools.
  - On `start`, the stub `pg_ctl` writes `$pgdata/postgres` as a bash script whose body is `sleep 999999` (:83-:86). It
    starts that script with `setsid "$pgdata/postgres" -D "$pgdata" &` and records `$!` in `postmaster.pid` (:88-:89).
  - The stub `redis-server` does the same with `$rdir/redis-server` and `--pidfile` (:112-:118).
  - `$!` is the wrapper bash, and bash runs `sleep` as its child. `stop_services` (`scripts/platform-ci-local.sh`
    :200-:226) proves the recorded pid is its service (`_is_our_postgres`, `_is_our_redis`), kills it and waits for it.
    The wrapper dies and the `sleep` is orphaned.
  - So every stubbed run that starts services leaks two processes. `test_platform_ci_local_killed_holder.py`'s
    `lock_holder.sh` (:265-:276) adds a third: it runs `sleep 999999` under a bash that the test SIGKILLs by pid (:302).
- **The scale.** On 2026-10-14 the host held 6,222 orphaned `sleep 999999` processes, reparented to `systemd --user`
  after about 23 hours of test runs. The operator cleared them.
- **The slow scan.** When a waiter's `flock -w` times out, `_report_lock_contention` (:83-:116) calls
  `_pids_holding_path` twice (:92, :98).
  - Without `fuser`, that function walks every `/proc/<pid>/fd/*` and forks a `readlink` per descriptor (:133-:142).
    `fuser` has been preferred since `07fa34a20d`, which landed in 99.7's dispatch on 2026-10-14 with no story; this
    story chains it.
  - At about 6,700 processes the walk ran past 120 s. `test_lock_wait_timeout_names_holder` and
    `test_lock_wait_names_live_holder_and_stale_record` then hit `_run_platform_ci_local`'s 120 s `subprocess` timeout,
    and their 2 s waiter spent minutes listing holders. That redded steward 99.7's verification and marshal's pre-push
    preflight.
- **The waiter names itself.** The waiter keeps fd 9, the lock file, open while it scans. It therefore lists its own
  pid, and the subshells and helpers of its scan pipeline, among the holders. A manual run at `e0ad43f18c`, with one
  outside holder, listed seven pids: the holder, the waiter, and five of the waiter's own helpers.

**Evidence, measured at `e0ad43f18c` on this host:**
- The two lock-wait tests passed in 33.33 s and 2.89 s (`--durations`). Afterwards three `sleep 999999` processes carried
  the tests' basetemp in their environment. None carried it in its cmdline, which is just `sleep 999999`. So a
  cmdline-scoped check cannot see this leak, and an environment-scoped one can.
- Holder scan, one process holding a lock, every variant fed the same lock file:

  | Variant | 550 processes (25,611 fds) | 6,549 processes |
  |---|---|---|
  | `/proc` walk, one `readlink` fork per fd (`e0ad43f18c`'s fallback) | 74.6 s | 110.6 s |
  | `fuser` | 0.40 s | 1.12 s |
  | `lsof -t -w` | 5.56 s | 6.12 s |
  | `/proc` walk with bash's `-ef` test (no fork per fd) | 0.48 s | 0.84 s |

  The 6,549-process run added 6,000 `sleep` processes that the benchmark started and killed itself, by pid. Every
  variant returned exactly the holder's pid. `lsof -b`, which avoids the blocking calls, failed on the lock file
  ("status error … Resource temporarily unavailable").

**Approach:**
- **The stubs exec.** Each stand-in's long-running body becomes `exec -a "$0 $*" sleep 999999`. The pid that `setsid`
  started, which the stub records, is then the `sleep` itself. Its cmdline keeps the stub's path and arguments
  (`…/pg/postgres -D …/pg 999999`, `…/redis/redis-server --port N 999999`), so `_is_our_postgres` and `_is_our_redis`
  still prove it, and the stop path's `kill` ends it.
- **The lock holder execs.** `lock_holder.sh` ends in `exec sleep 999999`, so the pid the test kills is the process
  that holds the lock.
- **Teardown stops what the test started.** `_kill_and_follow` kills its holder's process group after the follow run.
  After a SIGKILL to the shell alone, the group's slow `python` stand-in would otherwise outlive the test by up to 8 s.
- **A marker, scoped to the test.** Every process a test starts carries `PLATFORM_CI_STUB_MARKER=<tmp_path>` in its
  environment. This covers runs through `_run_platform_ci_local` and env-sync's `_run_script`, the `Popen`ed holders,
  and `lock_holder.sh`. Processes inherit the variable through `setsid`, `exec`, `env -u` and every stub.
  - `_marked_pids(root)` reads each `/proc/<pid>/environ` the user can read and returns the pids, other than its own,
    with exactly that NUL-separated entry.
  - An autouse fixture in the concurrency module, imported into the other two, waits up to 5 s after each test for
    the marked set to empty. If a marked process is left, the fixture SIGKILLs only those pids and fails the test,
    naming each one.
  - The named regression test `test_stub_start_stop_cycle_leaves_no_process` runs one `--test` cycle. It asserts that
    the stop path logged both stops and that nothing marked is left.
  - A zombie has an empty environ, so it never matches. Nothing matches by `pgrep`, a process name or `sleep 999999`.
- **The holder scan.** `_pids_holding_path` keeps `fuser` when it is on `PATH`. Otherwise it walks
  `/proc/[0-9]*/fd/*` once and keeps a descriptor when `[ "$fd" -ef "$target" ]` holds. That test is a bash builtin
  that compares device and inode, so the walk forks nothing per descriptor. Its output is the same as before: `sort
  -un`, one pid per line, sorted and unique.
  - `-ef` matches the file itself, the way `fuser` does. A descriptor on an unlinked earlier lock file no longer
    matches. Such a descriptor never blocks a `flock` on the current file, and the `fuser` path never listed it either.
- **The waiter reports cleanly.** When `flock -w` times out, the waiter closes fd 9 (`exec 9>&-`) before
  `_report_lock_contention`, so it never lists itself or its helpers. The report calls `_pids_holding_path` once,
  prints that list, and decides whether the `.holder` record is live from the same list.
- **Unchanged:** `PLATFORM_CI_LOCAL_LOCK_WAIT` and its 7200 s default, exit 2 on a timed-out wait, and the report's
  lines (`processes holding <lock>:`, `  pid=<n> cmdline=<…>`, `holder (from <meta>):`, `holder record stale (pid <n>
  not running):`). The lock, the reclaim, the port refusal, the env sync, the stage flags, the step names and the
  summary also stay as they are.

**Rejected:**
- **`lsof`.** The operator's brief asked for `fuser` or `lsof` when present. Measured here, `lsof -t` took 5.6-6.1 s,
  and the fork-free `/proc` walk it would replace took 0.5-0.8 s. So the fallback is the walk, and `fuser` meets the
  brief.
- **A single `find /proc/[0-9]*/fd -lname "$target"`.** It is one fork, but `-lname` matches the link text as a glob,
  so the target has to be glob-escaped, and the text is not the file: it differs across bind mounts and for unlinked
  files. `-ef` compares the file.
- **Killing by name in teardown** (`pkill -f 'sleep 999999'` and the like). That is host-wide, and the operator ruled
  it out.
- **A `trap 'kill $child' TERM` wrapper in the stubs.** It still leaks under SIGKILL. `exec` leaves one process to kill.
- **A test-only knob that picks the scan branch.** A test reaches the fallback by running the real function under a
  `PATH` without `fuser`.

Ledger key: `101-1-the-platform-ci-local-stubs-leak-no-process-and-the-holder-scan-takes-seconds`.
Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-steward` CAP-152: `platform-ci-local` is a task a station shells to, reachable
  from `pyforge-guild` (Story 63.6). Story 63.7 serialised its runs with a machine-wide lock and gave them a stub root
  to test against. Story 89.1 made a killed run unable to block the next, and made a timed-out wait name its holders.
  Story 96.1 synced its envs. This story fixes the leak in 63.7's stubs and the cost of 89.1's holder listing. It mints
  no CAP and changes no `SPEC.md`.
- **Governance.** `scripts/platform-ci-local.sh` and the three test files are on `spec-pyforge-steward`'s surface
  (`scripts/.spec-surface-baseline.json`). No other Spec governs them.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag. It restores intended behaviour, and a flag
  would keep the leak reachable.
- **Origin.** `docs/dreams/pyforge-steward.md` Realization log, 2026-10-14 (platform-ci-local stub leak). The operator
  approved, verbatim: "The operator approved this fix: the platform-ci-local test stubs leak processes, and the holder
  scan is slow."

## Acceptance Criteria

Every criterion runs the real `scripts/platform-ci-local.sh` or its real `_pids_holding_path` function. None needs
PostgreSQL, Redis, Docker or podman. No criterion counts, matches or signals a process outside its own marker or the pids
it started.

- **AC1 — The stubs record the process the stop path kills.**
  - **Given** Story 63.7's stub root, **When** a `--test` run starts its services, **Then** the pids in
    `postmaster.pid` and `redis.pid` belong to the long-running process itself (`/proc/<pid>/comm` is `sleep`). Their
    cmdlines still pass `_is_our_postgres` and `_is_our_redis`: the run's stderr has `stopping postgres (pid <n>)` and
    `stopping redis (pid <n>)` for those pids.
  - `lock_holder.sh` ends in `exec sleep 999999`.
- **AC2 — No test leaves a process behind.**
  - Every process a test in the three modules starts carries `PLATFORM_CI_STUB_MARKER=<tmp_path>`. This covers the
    script runs, the `Popen`ed holders and `lock_holder.sh`.
  - **Given** the autouse fixture, **When** any test in the three modules finishes, **Then** no process other than
    pytest's own carries the test's marker within 5 s. If one does, the fixture kills those pids, and only those, and
    fails the test naming each pid and its cmdline.
  - `test_stub_start_stop_cycle_leaves_no_process` runs one start/stop cycle. It asserts both stop lines and an empty
    marked set.
  - `_kill_and_follow` kills its holder's process group in teardown.
- **AC3 — The holder scan forks nothing per descriptor, and its contract holds.**
  - `test_pids_holding_path_lists_each_holder_once_sorted` holds a lock file open in two processes, one of them on two
    descriptors. It runs the script's own `_pids_holding_path`, extracted from `scripts/platform-ci-local.sh`, in two
    ways:
    - with `fuser`, `tr`, `sed` and `sort` on `PATH` (skipped where `fuser` is absent);
    - with only `sort` on `PATH`, so there is no `fuser` and no `readlink`.
  - Both print exactly the two pids, one per line, in numeric order, each once.
- **AC4 — The waiter names only the real holders.**
  - **Given** an outside process holding the lock and a dead `.holder` record, **When** the waiter times out, **Then**
    the `pid=` lines under `processes holding <lock>:` name exactly that process. The waiter, its subshells and its
    helpers are not listed. The stale record is still reported as stale.
  - The report calls `_pids_holding_path` once.
  - Every existing assertion in `test_lock_wait_timeout_names_holder` and
    `test_lock_wait_names_live_holder_and_stale_record` holds unchanged.
- **AC5 — The lock-wait tests are fast.** `test_lock_wait_timeout_names_holder` and
  `test_lock_wait_names_live_holder_and_stale_record` each pass in under 60 s (`pytest --durations=0`).
- **AC6 — Mutation.** Each of these fails a named test, and each is reverted. The Auto Run Result records which test
  fails:
  - dropping `exec -a "$0 $*"` from either stub fails `test_stub_start_stop_cycle_leaves_no_process` (and the fixture);
  - restoring the `readlink` walk as the fallback fails AC3's no-`fuser` run;
  - dropping the waiter's `exec 9>&-` fails AC4's exact-holder assertion.
- **AC7 — Nothing else moves.**
  - `PLATFORM_CI_LOCAL_LOCK_WAIT` and its 7200 s default, the exit codes, the contention report's lines, the stage
    flags, step names, summary and `--help` text do not change.
  - Every existing test in the three modules passes, with no assertion weakened or deleted.
- **AC8 — Green, and clean afterwards.**
  - `pixi run --frozen -e pyforge-steward pyforge-steward-test` exits 0, and so does
    `pixi run --frozen -e pyforge-guild lint-types`.
  - Before and after the three modules run, no process carries the run's basetemp in its environment or cmdline:
    0 before, 0 after.
- **AC9 — The surface is reconciled.**
  - The `spec-pyforge-steward` memlog gets a surface-reconcile entry that names each changed governed path and this
    story.
  - The Spec is stamped scoped (`--spec pyforge-steward/spec-pyforge-steward`), and so is any co-governor
    `spec-surface-check` names.
  - `spec-surface-check` exits 0.

## Boundaries & Constraints

**Always:**
- Fix the leak in the stubs and the teardowns, and fix the scan in `_pids_holding_path` and the contention report.
  Change nothing else in `scripts/platform-ci-local.sh`.
- Scope every process check to the test's own `PLATFORM_CI_STUB_MARKER` entry, and signal only the pids that check
  returns or pids the test started.
- Keep `_pids_holding_path`'s output: one pid per line, sorted and unique.
- Reconcile every governed path the change touches on the memlog of each Spec that governs it, then stamp those Specs
  scoped (AGENTS.md pre-PR item 5).

**Never:**
- Never `pkill`, `killall`, `pgrep` or kill by process name, and never count processes host-wide in a test or a tool.
- Never change `PLATFORM_CI_LOCAL_LOCK_WAIT`'s meaning or default, an exit code, or a report line.
- Never weaken or delete an existing test or assertion.
- Never touch `pixi.toml`, `pixi.lock`, marshal's verification command or any file outside the story's surface.

**Residual risk:**
- `fuser` also lists processes that hold the file as their cwd or through a mapping. A lock file is neither in
  practice, and `e0ad43f18c` already used `fuser` that way.
- The marker check reads only environments the user can read. A stub that cleared its environment (`env -i`) would
  escape it. None does, and the regression test fails if a stub stops carrying the marker.
- A test killed by pytest's own timeout, or by a crash, skips its fixture. The marker still names its leftovers, so the
  before and after counts in AC8 expose them.

## I/O & Edge-Case Matrix

| Situation | Today (`e0ad43f18c`) | After |
|---|---|---|
| a stubbed `--test` run starts and stops its services | 2 `sleep 999999` orphans | none; the recorded pid is the `sleep` |
| `lock_holder.sh` killed by pid | 1 orphan still holding the lock | none; the `sleep` is the pid |
| shell-only SIGKILL in `_kill_and_follow` | the group's slow `python` stand-in outlives the test (≤ 8 s) | the group is killed in teardown |
| a test leaves a marked process | unnoticed | the fixture kills it (scoped) and fails the test |
| waiter times out, `fuser` present | about 1 s per scan at 6,549 processes, twice | one scan |
| waiter times out, no `fuser` | 74.6-110.6 s per scan, twice | 0.5-0.8 s, once |
| the waiter's own pids in the report | listed | not listed |
| holder holds an unlinked earlier lock file | listed by the fallback, not by `fuser` | listed by neither (it cannot block the current file) |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-152 (no station code assumes the `local-recipes` environment at
  runtime), realized for this script by Stories 63.6, 63.7, 89.1 and 96.1. No CAP is minted, and no `SPEC.md` text
  changes.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-14 (platform-ci-local stub leak) entry.
- Epic: Epic 101 (new). Epics 63, 89 and 96, which shipped the script's lock, its kill safety and its env sync under
  CAP-152, are `done`, so the fix opens its own epic. `epic-101` and `epic-101-retrospective` are minted with it.
- Ledger key: `101-1-the-platform-ci-local-stubs-leak-no-process-and-the-holder-scan-takes-seconds`.
- Ledger status at mint: `backlog`.
- Deps: none.
- Spec: the `spec-pyforge-steward` memlog records the operator's approval, the evidence and design, and this mint.
- Surface: `marshal-policy.toml` `[epic_surfaces]."101"` (added with this mint) covers `scripts/platform-ci-local.sh`,
  steward's tests and every Spec memlog.
- Recorded with the mint, not implemented: `DW-steward-101-1-1` in steward's `deferred-work-ledger.md`
  (`steward ci status --json` has no row for the `PAUSE_ALL_CI` master switch).
- Minted 2026-10-14 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass. This is the station's
  `verify_commands` (MRS-GATE-010 binding), and it runs all three `platform-ci-local` modules.

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_platform_ci_local_concurrency.py src/shared/packages/pyforge-steward/tests/unit/test_platform_ci_local_killed_holder.py src/shared/packages/pyforge-steward/tests/unit/test_platform_ci_local_env_sync.py -q -p no:cacheprovider --durations=0 --basetemp="$BT"`, with `BT` a fresh directory — expected: exit 0, and the two lock-wait tests under 60 s each (AC1-AC5, AC7).
- The leak count, run before and after the previous command, with the same `BT` — expected: `0` both times (AC8):

  ```bash
  python3 - "$BT" <<'PY'
  import os, sys
  marker = sys.argv[1].encode()
  hits = 0
  for p in os.listdir("/proc"):
      if not p.isdigit() or int(p) == os.getpid():
          continue
      try:
          blob = open(f"/proc/{p}/environ", "rb").read() + open(f"/proc/{p}/cmdline", "rb").read()
      except OSError:
          continue
      hits += marker in blob
  print(hits)
  PY
  ```
- The AC6 mutations, one at a time, re-running the named test each time — expected: each fails the named test. Revert each.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0 (AC8).
- `git diff origin/main...HEAD --stat` — expected: outside `_bmad-output/`, `docs/dreams/pyforge-steward.md` and `scripts/.spec-surface-baseline.json`, only the script and the three steward test files.
- `python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entry and the scoped stamp (AC9).
- `pixi run --as-is -e pyforge-guild detectors-ci` — expected: no new finding against `main`.

## Spec Change Log

- 2026-10-14: minted from the operator's approval "the platform-ci-local test stubs leak processes, and the holder
  scan is slow". `type: fix`, no flag, no CAP. Bound to `spec-pyforge-steward` CAP-152 through Stories 63.7, 89.1 and
  96.1.
