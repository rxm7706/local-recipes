---
title: "96.1: `platform-ci-local` never runs a stage on a stale env"
type: 'fix'
created: '2026-10-11'
status: 'in-review'
baseline_revision: 'b4722aeba9e0f476c129d057c150fb0c4fd25294'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-89-1-a-killed-platform-ci-local-run-never-blocks-the-next-one.md
  - scripts/platform-ci-local.sh
  - src/shared/packages/pyforge-steward/tests/unit/test_platform_ci_local_concurrency.py
  - src/shared/packages/pyforge-steward/tests/unit/test_platform_ci_local_killed_holder.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** a `platform-ci-local` run uses the platform envs the checkout already has, even when `pixi.lock` has moved
past them. A verification can then fail, or pass, on an env the lock no longer describes. Line numbers below are at
`485d325d56`.

- **Which envs a run uses.** `run_platform_ci_local` points `CIT`, `DEV` and `WRD` at
  `$ROOT/.pixi/envs/platform-ci-test/bin`, `platform-dev/bin` and `pyforge-warden/bin` (:224-:226).
  - The `test` stage puts `CIT` and `DEV` first on `PATH` and runs every step from them (:276-:286).
  - `start_services` runs PostgreSQL and Redis from `DEV` (:258-:267), and so does the EXIT trap's `stop_services`
    (:208). The `test` and `container` stages start services (:383-:385).
  - The `promotion` stage puts `WRD` on `PATH` and runs `CIT/python` (:365-:375).
  - The `images` stage uses only the engine, `git` and `tar` (:290-:304).
- **When they are installed.** `ensure_envs` (:244-:250) loops over all three envs, whatever stages run. It installs an
  env only when its interpreter is missing: `[ -x "$ROOT/.pixi/envs/$e/bin/python" ] || pixi install --frozen -e "$e"
  9>&- >/dev/null` (:247). An env that exists is never checked against `pixi.lock`.
- **Why nothing else syncs them.** `pixi run -e pyforge-guild platform-ci-local` (the guild task, Story 63.6) makes
  pixi sync the `pyforge-guild` env before the task starts, and only that env. The script calls the other envs'
  binaries by path, never through `pixi run`, so pixi never checks them.
- **Who depends on it.** Marshal's cross-surface rule runs `pixi run -e pyforge-guild platform-ci-local -- --test` in
  the dispatch worktree whenever a story's diff touches `src/platform/` (MRS-GATE-015; `CROSS_SURFACE_VERIFY_COMMAND`
  in `pyforge-marshal`'s `core/gate.py`). A dispatch worktree that merges `main` while its story is in flight (a
  landing heal, a review iteration, a hand merge) keeps the envs it installed first.

**Evidence:**
- **Steward 91.1, 2026-10-11.**
  - The worktree `.worktrees/dispatch-pyforge-steward-91.1` created `platform-ci-test` at 18:53:50 (its
    `conda-meta/pixi_env_prefix`).
  - At 20:22 it merged `main` (`548b976af3`). That brought warden Story 16.1's merge `dae6101829`: `pixi.toml` gained
    `pyforge-warden = { path = "src/shared/packages/pyforge-warden" }` under `[feature.platform-ci-test.dependencies]`,
    and `pixi.lock` gained 76 lines.
  - The next `platform-ci-local -- --test` failed 15 tests in `src/platform/tests/test_warden_fleet_inventory.py` with
    "No module named 'pyforge.warden'".
  - A hand-run `pixi install --frozen -e platform-ci-test` installed `pyforge-warden-0.1.0-pyh4616a5c_0` into that env
    at 20:43:10 (its `conda-meta` record), and the tests passed.
  - The script's work dir is overwritten by each run, so the failing run's log is gone.
- **The cost, measured on `485d325d56`** (pixi 0.81.0, this host, warm package cache):
  - `pixi install --frozen -e <env>` on an env that is current: 0.20-0.29 s for each of `platform-ci-test`,
    `platform-dev` and `pyforge-warden` (five runs on `platform-ci-test`: 0.25-0.29 s).
  - The same call with `--manifest-path`, nested in `pixi run --frozen -e pyforge-guild` as the task runs it:
    0.28-0.33 s.
  - With the env's recorded lock hash made stale by hand: 0.24 s, and pixi rewrote the record to the lock's hash.
  - Into an empty prefix: `platform-ci-test` 2.03 s, `platform-dev` 1.28 s, `pyforge-warden` 0.37 s.
  - So a `--test` run pays about 0.5 s for its two installs when nothing changed.
- **What pixi records.** After each install pixi writes `.pixi/envs/<env>/conda-meta/pixi`, a JSON record whose
  `environment_lock_file_hash` identifies the env's section of `pixi.lock` it installed. A no-op install leaves that
  hash unchanged (it rewrites the file, so its mtime moves); a sync changes it. Measured as above.
- **What `--frozen` does.** `pixi install --help` (0.81.0):
  - `--frozen`: "Install the environment as defined in the lock file, doesn't update lock file if it isn't up-to-date
    with the manifest file". `--locked` is the flag that aborts on a lock behind `pixi.toml`.
  - So `--frozen` never re-solves and never writes `pixi.lock`. It fails only when it cannot install what the lock
    says: an env not in the lock (checked: "unknown environment", exit 1), a package it cannot fetch, a broken prefix.
  - CI's `test` job installs `platform-ci-test` the same way (`.github/actions/platform-test-setup`: `setup-pixi`,
    `frozen: true`).
- **The test seam.** Under `pixi run`, `PIXI_PROJECT_MANIFEST` names the checkout's `pixi.toml`, and pixi honours it
  from any working directory (checked: a `pixi install --frozen -e <env>` run from an empty directory with it set
  resolved that manifest). Story 63.7's tests copy the runner's environment, point `PIXI_PROJECT_ROOT` at a temporary
  stub root, and put no `pixi` stand-in on `PATH`. Today they never reach `pixi`, because every stub env has a
  `bin/python`. A fix that always ran the real `pixi install` without naming its manifest would sync the real
  checkout's envs from a unit test. With `--manifest-path` naming the stub root's absent `pixi.toml`, pixi exits 1
  ("unable to canonicalize") and touches nothing.

**Approach:** every run syncs each env its stages use, through pixi, before anything else starts.
- **Always install; pixi decides.** `ensure_envs` drops the `-x` guard. For each env the selected stages use, it runs
  `pixi install --frozen --manifest-path "$ROOT/pixi.toml" -e "$e"`. That is a no-op when the env matches `pixi.lock`
  and a sync when it does not. Pixi alone judges staleness, and the script computes no hash of its own (AD-1, and AD-5:
  provisioning shells out to `pixi install -e <name>`).
- **Only the envs the stages use,** in one fixed order, each once:

  | Stage | Envs |
  |---|---|
  | `test` | `platform-ci-test`, `platform-dev` |
  | `images` | none |
  | `container` | `platform-dev` (its services) |
  | `promotion` | `platform-ci-test` (`CIT/python`), `pyforge-warden` |

  A `--test` run, marshal's, syncs two envs; an `--images` run syncs none. Today every run ensures all three.
- **The run's own manifest.** `--manifest-path "$ROOT/pixi.toml"` makes the env that pixi syncs the env whose `bin/`
  the run then uses (`$ROOT/.pixi/envs/<env>`), whatever `PIXI_PROJECT_MANIFEST` the caller exported.
- **Where.** Where `ensure_envs` already runs: inside `run_platform_ci_local`, after `acquire_run_lock` and before
  `start_services` and any stage (:382). So every install happens under the machine-wide lock (Story 63.7), with fd 9
  closed (Story 89.1), before this run starts a service from those binaries. The engine check after it is unchanged.
- **Say what happened.** Before and after each install, the script reads `environment_lock_file_hash` from
  `.pixi/envs/<env>/conda-meta/pixi` (pixi's own record, read only).
  - No record before: `installed`. A different hash after: `synced`. The same hash: `current`. No hash after a
    successful install: `checked` (pixi's record changed shape; the install still ran).
  - It prints `env <name>: <state>` and appends `INFO\tenv\t<name>: <state>` to the run's `results.tsv`, so the summary
    shows it.
  - Each install's output goes to `$WORK/env-sync-<name>.log`.
- **Fail loudly; never fall back.** A non-zero `pixi install`, `pixi` missing from `PATH` (127) included, ends the run
  with exit 2, Story 63.7's "usage or environment" code. Stderr names the env and pixi's exit code and shows the last
  25 lines of its log. No later env is installed, no service starts and no stage runs. The run never goes on with the
  env it had.
- **Unchanged:**
  - the lock, its `.holder` record and its contention report; the reclaim and port refusal (Story 89.1);
  - the stage flags, the step names, the PASS and FAIL rows and the `RESULT` line;
  - exit codes 0 (pass) and 1 (a step failed), and exit 2's meaning (usage or environment);
  - the `PLATFORM_CI_LOCAL_*` overrides, `--help`'s text, marshal's command, `pixi.toml` and `pixi.lock`.

**Rejected:**
- **A staleness probe in the script,** comparing `conda-meta/pixi` with a hash of `pixi.lock`. The hash is pixi's
  internal format, so computing it here reimplements pixi (AD-1), and pixi's own check costs 0.2-0.3 s.
- **`--locked`.** It aborts when `pixi.lock` is behind `pixi.toml`. That drift is the lock gates' to catch, and CI's
  `test` job installs `platform-ci-test` frozen. A verification would start failing on a manifest edit no env
  reflects.
- **`pixi run -e <env>` around each step.** It would sync too, but it rewrites every step's command line and each step
  pays pixi's activation. The workflow's step lines stay as they are.
- **`$PIXI_EXE`.** It would bypass `PATH`, which is the seam the tests use. The script resolves `pixi` from `PATH`
  today.
- **An opt-out (`PLATFORM_CI_LOCAL_NO_SYNC`).** Nothing asks for one, and the tests use a stand-in.

Ledger key: `96-1-platform-ci-local-never-runs-a-stage-on-a-stale-env`.
Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-steward` CAP-152: `platform-ci-local` is a task a station shells to, reachable
  from `pyforge-guild` (Story 63.6), and it provisions the platform envs it uses (marshal's `CROSS_SURFACE_VERIFY_COMMAND`
  comment, Story 46.12). Stories 63.7 and 89.1 made overlapping and killed runs safe. This story makes the provisioning
  follow `pixi.lock`. It fixes the realization of shipped behaviour, so it mints no CAP and changes no `SPEC.md`.
- **Governance.** `scripts/platform-ci-local.sh` and both existing test files are on `spec-pyforge-steward`'s surface
  (`scripts/.spec-surface-baseline.json`); no other Spec governs them. The new test file sits in the same package tree.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag: it restores intended behaviour, and a
  flag would keep the bug reachable.
- **Origin.** `docs/dreams/pyforge-steward.md` Realization log, 2026-10-11 (platform-ci-local syncs a stale env). The
  operator's ask, verbatim: "Do this task here: Make platform-ci-local sync a stale env".

## Acceptance Criteria

Every criterion runs the real `scripts/platform-ci-local.sh` against Story 63.7's stub root under a temporary
`PIXI_PROJECT_ROOT`, with a `pixi` stand-in first on `PATH`. None needs the real `pixi`, PostgreSQL, Redis, Docker or
podman. The stub root has no `pixi.toml`.

**The `pixi` stand-in.** An executable `pixi` in the stub root's `bin/`. On each call it:
- appends one line to the stub log (`PLATFORM_CI_STUB_LOG`): its argv, and whether any link in `/proc/self/fd` points
  at the lock file, as the other stubs do;
- for `install`, also logs whether the run holds the lock at that moment: `flock -n "$PLATFORM_CI_LOCAL_LOCK" true`,
  run from the stand-in, fails while the run holds it;
- exits with a code the test chooses for each env;
- when the test asks, writes `<root>/.pixi/envs/<env>/conda-meta/pixi` with a new `environment_lock_file_hash` (a
  sync), or leaves it as it is (current).

- **AC1 — Every run syncs the envs its stages use, frozen, under the lock.**
  - **Given** the stub root, whose envs all have a `bin/python` (so the old guard installs nothing), **When** `--test`
    runs, **Then** the stand-in is called exactly twice: `install --frozen --manifest-path <root>/pixi.toml -e
    platform-ci-test`, then the same for `platform-dev`. It is never called for `pyforge-warden`.
  - Both calls come before the first service stub (`initdb`) and the first step stub in the stub log.
  - Each call happens while the run holds the lock (the `flock -n` probe fails), and the stand-in never has the lock
    file open.
  - **When** `--images` runs alone, **Then** the stand-in is never called.
  - A test reads the script: every `pixi` command in it, comments aside, is `pixi install --frozen --manifest-path
    "$ROOT/pixi.toml" -e …`. It fails on `pixi update`, `pixi add`, `pixi lock`, `pixi upgrade`, `pixi remove`,
    `pixi reinstall`, `--locked`, or a `pixi install` without `--frozen`.
- **AC2 — A stale env is synced before its stage runs, and the run says so.**
  - **Given** `platform-ci-test`'s `conda-meta/pixi` recording the hash `stale` and a stand-in that rewrites it to
    `fresh`, **When** `--test` runs, **Then** stdout has `env platform-ci-test: synced` before the first `== [test]`
    line, `results.tsv` and the summary carry `INFO env platform-ci-test: synced`, and the run prints `RESULT: PASS`
    and exits 0.
  - With a stand-in that leaves the record as it is, the line reads `env platform-ci-test: current`. With no record
    before the run, it reads `env platform-ci-test: installed`. With a record that has no hash after the install, it
    reads `env platform-ci-test: checked`.
  - Each env's install output is in `$WORK/env-sync-<name>.log`.
- **AC3 — A failed sync stops the run, loudly.**
  - **Given** a stand-in that prints a line and exits 1 for `platform-ci-test`, **When** `--test` runs, **Then** the run
    exits 2. Stderr names `platform-ci-test` and the exit code 1, and shows the stand-in's line.
  - No service stub and no step stub ran: the stub log has neither `initdb` nor a step's call.
  - The stand-in was not called for `platform-dev`, and stdout has no `RESULT: PASS`.
- **AC4 — Mutation.** Each of these fails a named test, and each is reverted; the spec's Auto Run Result records which:
  - restoring `[ -x "$ROOT/.pixi/envs/$e/bin/python" ] ||` before the install fails AC1 and AC2 (the stand-in is never
    called);
  - dropping `--frozen` fails AC1's argv check and its script check;
  - letting a failed install continue (`|| true`) fails AC3;
  - moving the sync after `start_services` fails AC1's order check.
- **AC5 — Stories 63.7 and 89.1 stay green.**
  - The six tests in `test_platform_ci_local_concurrency.py` and the tests in `test_platform_ci_local_killed_holder.py`
    pass.
  - Their only change: `_prepare_stub_root` writes a `pixi` stand-in that logs its call and exits 0 into the stub
    `bin/`, because every run now calls `pixi`. No test function, assertion, port, timeout or other stub changes.
    `test_no_child_holds_run_lock` then also covers the stand-in.
  - The stage flags, step names, PASS and FAIL rows, `RESULT` line, exit codes, `PLATFORM_CI_LOCAL_*` overrides, the
    7200 s default wait and marshal's command do not change.
- **AC6 — Green on the real tree.**
  - `pixi run --frozen -e pyforge-steward pyforge-steward-test` and `pixi run --frozen -e pyforge-guild lint-types`
    exit 0.
  - `pixi run -e pyforge-guild platform-ci-local -- --test` exits 0. It prints one `env` line each for
    `platform-ci-test` and `platform-dev`, and none for `pyforge-warden`. A second run straight after prints both as
    `current`.
- **AC7 — The surface is reconciled.** The `spec-pyforge-steward` memlog gets a surface-reconcile entry that names
  each changed governed path and this story. The Spec is stamped scoped (`--spec pyforge-steward/spec-pyforge-steward`),
  and so is any co-governor `spec-surface-check` names. `spec-surface-check` exits 0.

## Boundaries & Constraints

**Always:**
- Fix it in `scripts/platform-ci-local.sh`. Put the tests in the steward suite, beside Stories 63.7's and 89.1's, so
  the station's `verify_commands` runs them.
- Sync with `pixi install --frozen --manifest-path "$ROOT/pixi.toml" -e <env>`, under the run's lock, with fd 9 closed,
  before any service or stage starts.
- In the tests, put the `pixi` stand-in first on `PATH`, and keep the stub root free of a `pixi.toml`, so no test can
  reach the real checkout's envs.
- Reconcile every governed path the change touches on the memlogs of the Specs that govern it, then stamp those Specs
  scoped (AGENTS.md pre-PR item 5).

**Never:**
- Never run `pixi update`, `pixi add`, `pixi lock`, `pixi upgrade`, `pixi remove`, `pixi reinstall`, `--locked`, or a
  `pixi install` that may write `pixi.lock`.
- Never compute, write or edit pixi's records; the script only reads `conda-meta/pixi`.
- Never change `pixi.toml`, `pixi.lock`, marshal's verification command or its rule table.
- Never let a run go on after a failed sync, and never skip the sync for an env a selected stage uses.
- Never weaken or delete an existing test.

**Residual risk:**
- `conda-meta/pixi` is pixi's record, not a public contract. If its shape changes, every env reports `checked`; the
  sync itself is unaffected.
- `--frozen` installs what the lock says, so a `pixi.lock` behind `pixi.toml` still runs, as CI's `test` job does.
  The lock gates catch that drift.
- A real sync needs the package cache or the network. Offline with a cache miss, a run now exits 2 naming the env,
  where today it went on (and may have failed later) on the stale env.
- A sync can change an env that another process of the same checkout is using at that moment, such as a
  `pixi run -e platform-ci-test …` outside this script. Pixi serialises its own installs; the machine-wide lock
  serialises only `platform-ci-local` runs.
- Doctor's `platform-policy-suite` source (`pyforge.doctor.sources.platform_policy`) also runs `platform-ci-test`'s
  interpreter by path without syncing it. That is doctor's code and out of scope here; the `spec-pyforge-steward`
  memlog records it.

## I/O & Edge-Case Matrix

| Situation | Today (`485d325d56`) | After |
|---|---|---|
| an env the stages use matches `pixi.lock` | nothing runs | `pixi install --frozen` (about 0.25 s); `env <name>: current` |
| an env is older than `pixi.lock` (91.1) | stages run on the old env; tests fail with import errors | synced first; `env <name>: synced`; stages run on the synced env |
| an env is missing | installed silently | installed; `env <name>: installed` |
| `pixi install --frozen` fails (env not in the lock, offline cache miss, broken prefix, `pixi` not on `PATH`) | a missing env: the run goes on and its steps fail later; an existing env: never tried | exit 2 naming the env and pixi's exit code, with its log tail; no service, no stage |
| `pixi.lock` is behind `pixi.toml` | not checked | not checked: `--frozen` installs the lock as it is, as CI does |
| `--images` alone | ensures all three envs | syncs none |
| `--promotion` alone | ensures all three envs | syncs `platform-ci-test` and `pyforge-warden` |
| the caller's `PIXI_PROJECT_MANIFEST` names another checkout (Story 63.7's tests inherit the runner's) | a missing env would be installed into that checkout | the run's own `$ROOT/pixi.toml`; in a stub root with none, pixi exits 1 and the run exits 2 |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-152 (no station code assumes the `local-recipes` environment at
  runtime), realized for this script by Stories 63.6, 63.7 and 89.1. No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-11 (platform-ci-local syncs a stale env)
  entry.
- Epic: Epic 96 (new). Epics 63 and 89, which shipped the script's lock and its kill safety under CAP-152, are `done`,
  so the fix opens its own epic. `epic-96` and `epic-96-retrospective` are minted with it.
- Ledger key: `96-1-platform-ci-local-never-runs-a-stage-on-a-stale-env`.
- Ledger status at mint: `backlog`.
- Deps: none.
- Spec: the `spec-pyforge-steward` memlog records the ask verbatim, the evidence and design, and this mint.
- Surface: `marshal-policy.toml` `[epic_surfaces]."96"` (added with this mint) covers `scripts/platform-ci-local.sh`,
  steward's tests and every Spec memlog.
- Minted 2026-10-11 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding). It runs the new test module and Stories 63.7's and 89.1's.

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_platform_ci_local_env_sync.py src/shared/packages/pyforge-steward/tests/unit/test_platform_ci_local_concurrency.py src/shared/packages/pyforge-steward/tests/unit/test_platform_ci_local_killed_holder.py -q` — expected: exit 0 (AC1-AC3, AC5).
- The AC4 mutations, one at a time, re-running the new module each time — expected: each fails the named test. Revert each.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0 (AC6).
- `pixi run -e pyforge-guild platform-ci-local -- --test`, twice — expected: exit 0 both times; the first prints an `env` line for `platform-ci-test` and `platform-dev` and none for `pyforge-warden`, the second prints both `current` (AC6).
- The 91.1 case by hand: set `environment_lock_file_hash` in `.pixi/envs/platform-ci-test/conda-meta/pixi` to `0000000000000000`, then run `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: `env platform-ci-test: synced`, the hash back to the lock's, exit 0.
- `git diff origin/main...HEAD --stat` — expected: outside `_bmad-output/` and `scripts/.spec-surface-baseline.json`, only the script and the three steward test files.
- `python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entry and the scoped stamp (AC7).
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: no new finding against `main`.

## Spec Change Log

- 2026-10-11: minted from the operator's ask "Do this task here: Make platform-ci-local sync a stale env". `type: fix`,
  no flag, no CAP; bound to `spec-pyforge-steward` CAP-152 through Stories 63.6, 63.7 and 89.1.
