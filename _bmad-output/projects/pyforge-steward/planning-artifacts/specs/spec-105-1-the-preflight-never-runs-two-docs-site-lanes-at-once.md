---
title: '105.1: The preflight never runs two docs-site lanes at once'
type: 'fix'
created: '2026-10-15'
status: 'done'
baseline_revision: '38ec9a2d2530636edaa8c08d117fd520a534ae09'
flag-exempt: detector-or-gate   # a fix needs no flag (spec-feature-flag-governance Q1: flagging a fix keeps the bug reachable); and pr-preflight is a gate, so a flag-OFF run would report a silent green (Q2's gate exemption), the rule doctor 34.7 and 35.1 followed
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-88-1-the-preflight-runs-each-task-once-after-its-dependencies.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-103-5-the-preflight-keys-each-lane-by-its-task-and-its-environment.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-71-10-a-stopped-lane-is-journaled-cancelled-and-the-lane-that-stopped-the-run-red.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight_ci.py
  - pixi.toml
  - docs-site/scripts/pages.mts
  - docs-site/scripts/nav-check.mts
  - src/shared/packages/pyforge-herald/tests/meta/pages_astro.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `pr-preflight` runs the lanes it selects in a bounded pool, and two lanes that use one `docs-site/` tree
can run at the same time. Line numbers are at `38ec9a2d25`.

- **What shares the tree.**
  - `docs-site-install` is `npm ci` with `cwd = "docs-site"` (`pixi.toml:961`-`:964`). It deletes
    `docs-site/node_modules` and installs it again.
  - `pages-build` (`node docs-site/scripts/pages.mts build`, `:972`-`:975`) runs `npm run build` (`astro build`) in
    `docs-site/`. The build rewrites `docs-site/public/` from scratch (`docs-site/scripts/populate-public.mts:49`),
    writes `docs-site/build/site/` and Astro's caches under `node_modules/`. `pages-check` (`:977`-`:980`) reads
    `docs-site/build/site/`. `docs-site-validate-sidebar` (`:990`-`:993`) runs `nav-check.mts`, which imports the
    `yaml` package from `docs-site/node_modules`. `docs-site-build` (`:966`-`:970`) is the bare build.
  - `pyforge-herald-test` (`pytest src/shared/packages/pyforge-herald/tests -q`, `pixi.toml:3124`-`:3126`) runs
    herald's built-site tests. They call `astro_build` (`tests/meta/pages_astro.py:236`-`:267`), which runs
    `node docs-site/node_modules/astro/bin/astro.mjs build` with `cwd=DOCS_SITE`, so each build rewrites
    `docs-site/public/`. `test_one_generator.py` also reads `docs-site/public/` directly. The module reads
    `RENDER_READY` (whether `node_modules/astro` exists) when it is imported, and the tests skip without it.
    `pyforge-herald-coverage-gate` runs herald's unit suite, which includes `test_docs_site_nav.py`'s built-site
    test, and `pyforge-herald-test-coverage` runs the whole suite.
  - Herald Story 43.7 (#2240) made Astro the one Pages generator, so these tests now run wherever docs-site is
    installed.
- **Nothing orders them.**
  - Story 88.1 (`preflight.py:1171`-`:1175`) starts a lane only after its own dependencies finish `ok`. That orders
    `pages-build` after `docs-site-install`, but it does not order `pyforge-herald-test`, which depends on neither.
  - Story 71.3's mutex is one key per lane (`run_preflight` `:1040`, `_run_lane_in_pool` `:846`/`:867`), read from
    the lane's CI job `services:` (`preflight_ci.static_service_mutex_keys`, `preflight_ci.py:1548`). It serializes
    only lanes that share a service container. A lane cannot hold a second key.
- **Measured.** On 2026-10-15 the orchestrating session ran `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild
  pr-preflight` with both lanes selected. Two herald tests failed with `[UNRESOLVED_ENTRY] Cannot resolve entry module
  astro/entrypoints/prerender`, and the same suite run alone passed 2058. This story reproduced the race twice at
  `38ec9a2d25` through the runner's own selection (Verification, the proof driver):
  - `docs-site-install` (0.4-3.6 s) ran while `pyforge-herald-test` (0.4-73.0 s) was importing its modules.
  - Herald reported 2033 passed and 30 skipped; alone it reports 2058 passed and 5 skipped.
  - All 25 extra skips name the docs-site install as their reason (17 `needs_astro`'s "docs-site is not
    installed", 8 "pixi run -e site docs-site-install"): `npm ci` had removed `node_modules/astro` when
    `pages_astro` read `RENDER_READY`. The race either reds the built-site tests or silently skips them.
- **CI is unaffected.** Each job has its own runner and checkout.
- **A latent race in the lock map.** `_RunCoordinator.service_lock` (`:503`-`:508`) creates a lock with an unguarded
  check-then-set from pool threads, so two threads could each get a lock of their own for one key.

**Approach:** the lanes that install into, read from or build in `docs-site/` hold one mutex, `tree:docs-site`, beside
any service key.

- **One declared set.** `preflight.DOCS_SITE_TASKS` is a `frozenset` of task names, each with a one-line reason:
  `docs-site-install`, `docs-site-build`, `pages-build`, `pages-check`, `docs-site-validate-sidebar`,
  `pyforge-herald-test`, `pyforge-herald-coverage-gate` and `pyforge-herald-test-coverage`. It is keyed by task
  because the tree is the same in every environment.
- **Derived in a test, not at run time.** `tests/meta/test_preflight_docs_site_lanes.py` derives the set from five
  rules, and fails on a task the set misses or a name no rule derives:
  - the task runs in the tree (`cwd` under `docs-site/`, or npm or astro on a `docs-site/` path);
  - its `depends-on` closure reaches such a task;
  - it runs a `docs-site/` script whose import closure, relative imports followed, names an npm package;
  - it runs a `docs-site/` script whose import closure takes `node:child_process` and names npm, npx, pnpm or astro
    as a command (`pages.mts` runs `spawnSync('npm', ['run', 'build'])`). `pages-build` and `pages-check` match this
    rule on their own, so the set does not hang on their install dependency. *(Added by the review, 2026-10-15.)*
  - it runs herald's suite, while some herald test calls `astro_build`.

  The same test checks that steward's station-tests job fires on every docs-site file an import closure visits, and
  on herald's Astro helper. Those reads come through import resolution, which the AST-derived trigger map
  (Story 98.1) cannot see. *(Added by the review.)*

  Herald's tests are why a runtime derivation alone cannot work: `pyforge-herald-test`'s command names no docs-site
  path.
- **Keys per lane.** `lane_mutex_keys(lanes, service_keys)` returns each lane's keys as a sorted tuple: its service
  key, if it has one, and `tree:docs-site` when its task is in the set. `run_preflight` passes each lane its tuple.
- **Taking the keys.** `_run_lane_in_pool` takes every key in `sorted()` order and releases them in reverse in its
  `finally`. Every lane takes its keys in that one order, so no two lanes can each hold a key the other waits for.
  `_RunCoordinator.mutex_lock(key)` makes the one lock per key with `setdefault` under `mutex_guard`.
  `service_lock` / `service_locks` are renamed `mutex_lock` / `mutex_locks`.
- **The pool gives no slot to a lane that can only wait.** When a candidate's keys intersect the keys of an
  in-flight lane, the scheduler leaves it pending and offers it again when a lane finishes. The slot goes to a lane
  that can run.
  - A lane is only ever submitted after its dependencies finish, and it takes its keys inside its own thread, so no
    lane holds a key while it waits for a dependency. A candidate is deferred only while an in-flight lane holds its
    key, and in-flight lanes never wait on one another.
  - So neither the deferral nor the lock can deadlock against a pending dependency.
  - On a red stop, a deferred lane is a lane that never started: `cancelled`, exit 0, 0 s and no `cancelled_by`,
    as Story 71.10 states.
- **A docs-site lane that pending lanes wait on starts first** *(added by the review, should-fix 2)*.
  - Ready lanes start in `_run_order`: first a lane that holds a mutex and that pending lanes depend on, then
    declaration order.
  - So `docs-site-install` (`pages-build` waits on it) starts before `pyforge-herald-test` (nothing waits on it),
    then `pages-build`, then herald.
  - Herald's built-site tests therefore read this run's install. That is never a stale one after a
    `package-lock.json` change, and never none at all on a fresh worktree (measured under Verification run).
  - A lane that holds no mutex keeps its declared place, as before. So `test_preflight_lane_identity.py`'s `--jobs 1`
    stop test still runs `a`@inv before `a`@other.
  - `test_preflight_selection.py::test_run_preflight_with_no_base_ref_runs_every_lane` is restated. It asserts that
    lanes outside the docs-site set keep their declared order and that `docs-site-install` is the first docs-site
    lane, where it asserted that the whole serial order equals the declared order.
- **A red stop starts no lane** *(added by the review)*.
  - `_skip_lane_on_red_stop(coord)` is true for every lane once a red lane has stopped a run without `--keep-going`.
  - After the stop the pool drains what is running and the run ends, so no pending lane ever starts.
  - Story 88.1's exception (a lane that pending lanes depend on may still start) only started lanes whose dependents
    never run. With the deferral, the subprocess path spawned `docs-site-install` after a stop, and `register_proc`
    killed it at once.
  - That lane is now a never-started lane (Story 71.10).
  - `_run_lane_in_pool` loses its `pending` argument.
- **Two validators stay concurrent.** `docs-site-validate-links` and `docs-site-validate-sidebar-order` import only
  `node:fs` and `node:path`, read only `docs/`, and depend on nothing. The meta test pins that from their source.
  `docs-site-validate-sidebar` imports `yaml` from `node_modules`, so it is in the set. Its dependency on
  `docs-site-install` already orders it after `npm ci`; the set also keeps it apart from a herald build.
- **Steward's suite runs when what the new test reads changes** (Story 98.1's rule, CAP-159). The meta test reads
  `docs-site/scripts/` and, through their relative imports, `docs-site/src/lib/`, so `pyforge-station-tests.yml`'s
  `steward_paths` gains `docs-site/scripts` and `docs-site/src/lib`. The older `docs-site/src/lib/status.ts`
  entry, which `docs-site/src/lib` now covers, is dropped (review nit). Herald's tests are already on it
  (`src/shared/packages/pyforge-*/tests/*`), and `on.pull_request.paths` already lists `docs-site/**`.
  `test_station_tests_trigger_map.py::test_every_read_and_declared_glob_fires_its_job` failed without the edit,
  naming `docs-site/scripts/nav-check.mts`. *(Amended in implementation, 2026-10-15.)*
- **The TEA matrix is regenerated.** `bmad_tea_playwright.py --project pyforge-steward` rewrites
  `planning-artifacts/test-architecture.md` with story 105.1 and the two new test files.
  `tea-playwright-check`, in `detectors-ci` and `pyforge-doctor-scripts-test`, failed without it. The regeneration
  also lists the Pages one-PR's renamed tests: `test_deploy_*` became `test_pages_*`. *(Amended in implementation,
  2026-10-15.)*
- **Unchanged.** Selection (apart from steward's job paths above), the touched scope, suite reduction, the journal's
  keys, the exit codes, `pixi.toml`, the pre-push hook and `PYFORGE_PREFLIGHT_SKIP`.

**Rejected:**
- **A dependency edge from `pyforge-herald-test` to `docs-site-install` in `pixi.toml`.** Herald's suite would then
  need node and npm in its own environment and on every CI runner. It would also order only those two lanes, and leave
  herald's build beside `pages-build`.
- **Lock-only, with no scheduler deferral.** It is correct, but a deferred lane would hold a pool slot while it waits.
  With `--jobs 2`, two docs-site lanes declared first would leave an unrelated lane waiting behind both.
- **Deriving the set at run time from `pixi.toml`.** Herald's suite names no docs-site path in its command, so the
  derivation would need a second, declared list anyway.
- **A per-path mutex (`node_modules`, `public/`, `build/`).** Three keys for one tree. `npm ci` and an Astro build
  each touch two of the three, so every docs-site lane would hold most of them.
- **Needed-first for every lane** (the review's first suggestion). It would also reorder lanes that share nothing,
  for example `test_preflight_lane_identity.py`'s `--jobs 1` stop test, whose `a`@other would then run before
  `a`@inv. Only lanes that run one at a time need the order.

Ledger key: `105-1-the-preflight-never-runs-two-docs-site-lanes-at-once`.
Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-steward` CAP-159 (Stories 71.1-71.3, 71.10, 88.1, 103.5). Its intent says
  concurrent lanes share no mutable state, and that lanes sharing a CI service container never overlap. The
  `docs-site/` tree is mutable state two lanes share, so this story restores the intent as written. It mints no CAP
  and changes no `SPEC.md` text.
- **Governance.** `preflight.py` is on `spec-pyforge-steward`'s and `spec-pyforge-core`'s surfaces, and steward's
  tests are on `spec-pyforge-steward`'s (`scripts/.spec-surface-baseline.json`).
- **Flag.** None: under `spec-feature-flag-governance` Q1 a `fix` needs no flag. The spec also carries
  `flag-exempt: detector-or-gate`, because `pr-preflight` is a gate. The same holds if the story is ever re-typed.
- **Origin.** `docs/dreams/pyforge-steward.md`, Realization log, the 2026-10-15 entry (the preflight runs two
  docs-site lanes at once).

## Acceptance Criteria

Every criterion runs the real `run_preflight`, `_run_lane_in_pool` or module function over a fixture `pixi.toml`, with
an injected lane runner. None runs pixi. The meta criteria read the real `pixi.toml`, the `docs-site/scripts/` sources
and herald's tests.

- **AC1: two docs-site lanes never overlap.** Given `pyforge-herald-test`, `pages-check` → `pages-build` →
  `docs-site-install` and `docs-site-validate-sidebar` → `docs-site-install`, at `--jobs 8`:
  - no two of the five lanes overlap;
  - each lane starts only after its dependency ends;
  - every lane is journaled `ok`.
- **AC2: other lanes still overlap.** A docs-site lane and an unrelated lane overlap at `--jobs 4`. At `--jobs 2`,
  with two docs-site lanes declared before an unrelated one, the unrelated lane runs beside the first docs-site lane:
  the second docs-site lane waits pending, not in a slot.
- **AC3: both keys, no deadlock.** A lane whose CI job declares `services: postgres` and whose task is in the set gets
  `("services:postgres", "tree:docs-site")` from `lane_mutex_keys`. In a run with a docs-site-only lane, a
  postgres-only lane and an unrelated lane:
  - it overlaps neither the docs-site-only lane nor the postgres-only lane;
  - those two overlap each other;
  - the run exits 0.

  Two lanes given the two keys in opposite orders both finish, and they do not overlap.
- **AC4: the locks.**
  - A lane that raises still releases every lock it took.
  - Two threads asking for one key at once get one lock, and only one lock is stored. The test's lock map holds the
    check-to-store window open, so both the old unguarded check-then-set and an unguarded `setdefault` store two
    *(review nit)*.
- **AC5: the set is derived.** `test_preflight_docs_site_lanes.py` fails when a task in `pixi.toml` matches a rule and
  is missing from `DOCS_SITE_TASKS`, or when the set names a task no rule derives.
  - Its blindness guards: each rule finds the tasks it was written for (`pages-build` and `pages-check` match the
    spawn rule on their own), the import scan finds `nav-check.mts`'s `yaml`, and a herald test calls `astro_build`
    in `docs-site/`.
  - A planted `pages-preview = "node docs-site/scripts/pages.mts build"` with no `depends-on` is derived, and so is
    `pages-build` with its install dependency dropped *(review should-fix 1)*.
  - Steward's station-tests job fires on every docs-site file an import closure visits *(review)*.
  - The shipped `pr-preflight-lanes` holds at least six docs-site lanes, each given the docs-site key.
- **AC6: two validators stay concurrent.** `docs-site-validate-links` and `docs-site-validate-sidebar-order` import
  only `node:` builtins and depend on nothing, and neither is in the set.
- **AC7: mutation.** Each change below fails the named test (recorded under Verification run):
  - no docs-site key in `lane_mutex_keys` (AC1);
  - no scheduler deferral (AC2's `--jobs 2` test);
  - keys taken unsorted (AC3's opposite-order test);
  - no release in `finally` (AC4);
  - `pages-check` or `pyforge-herald-coverage-gate` dropped from the set, or `docs-site-validate-links` added (AC5).
  - Added by the review:
    - ready lanes started in declaration order only (AC11);
    - lanes that pending lanes depend on started after a stop (AC12);
    - the old unguarded check-then-set, or `setdefault` without the guard (AC4);
    - no spawn rule (AC5);
    - `docs-site/src/lib` dropped from `steward_paths` (AC5).
- **AC8: nothing else moves.** Every existing preflight test passes unchanged, with three exceptions:
  - in `test_preflight_lane_identity.py`, the lock seam's rename, its argument becoming a tuple, and
    `_run_lane_in_pool` losing `pending`;
  - the one restated order assertion in `test_preflight_selection.py` (see Approach).

  Selection, the journal's record keys and the exit codes are unchanged.
- **AC9: the proof.** Through the runner's own selection and pool, `pyforge-herald-test` runs with no docs-site lane
  beside it. It passes with the same counts it has alone (2058 passed, 5 skipped at `38ec9a2d25`), and the run exits 0.
- **AC11: the install runs first.** With `pyforge-herald-test` declared before `pages-check` → `pages-build` →
  `docs-site-install`, at `--jobs 1` and at `--jobs 8`, `docs-site-install` and then `pages-build` end before herald
  starts. With one slot, keyless lanes keep their declared order, while a docs-site lane that a pending lane waits on
  goes first *(review should-fix 2)*.
- **AC12: a red stop starts nothing.** Herald, holding the docs-site key, goes red while `docs-site-install` (which
  `pages-build` waits on) is deferred. The install never starts and is journaled `cancelled`, exit 0, 0 s, with no
  `cancelled_by`. Herald's own dependent is `cancelled_by` herald *(review nit)*.
- **AC13: no hang.** Every test in `test_preflight_docs_site_mutex.py` runs under
  `faulthandler.dump_traceback_later(120, exit=True)`. A spin or a deadlock writes every thread's stack to
  `<basetemp>/hang-guard-<test>.txt` and ends the process with exit 1 *(review nit)*.
- **AC10: green, and the surface reconciled.** These exit 0:
  - `pixi run --frozen -e pyforge-steward pyforge-steward-test`;
  - the steward coverage gate;
  - `pixi run --frozen -e pyforge-guild lint-types`;
  - `ci_surface_gates.py --check`;
  - the planning detectors.

  Each changed governed path gets a surface-reconcile entry on the memlog of every Spec that governs it. The scoped
  stamps are taken after the commit, from a clean tree.

## Boundaries & Constraints

**Always:**
- Keep the set declared once, in `preflight.py`, with a reason per task. The meta test derives it; nothing copies it.
- Take a lane's keys in one sorted order and release them in reverse, whatever the lane does.
- Keep every per-lane structure keyed by `(task, environment)` (Story 103.5). The set itself is keyed by task, because
  the tree is the same in every environment.

**Never:**
- Never change `pixi.toml`, the pre-push hook or the journal's record keys. The one workflow edit is steward's
  `steward_paths` in `pyforge-station-tests.yml` (Story 98.1's rule for what steward's tests read).
- Never serialize a lane outside the set.
- Never weaken an existing assertion.

**Residual risk:**
- **The docs-site lanes now run one after another.** On the reference host the Pages chain (install, build, check,
  sidebar) takes about 12 s alone and 23 s under a full-scope run's load. Herald's suite now starts about 9 s later,
  behind the install and the build. In every measured full-scope run steward's suite (718-808 s) stays the critical
  path.
- **Herald's suite and herald's coverage gate run one after the other** on a herald-touching branch (measured
  2026-10-15, review should-fix 3). On a committed herald diff, the gate runs herald's unit suite under coverage and
  the station lane is reduced to the tests the gate does not run.
  - Serialized (the shipped code), the docs-site group took 158.2 s: install 3.0, build 5.9, herald's reduced lane
    4.8 (5 tests), gate 142.1 (2053 passed, 5 skipped), check 1.6, sidebar 0.3.
  - With the gate taken out of the set (the old behaviour), the gate ran beside the install and the build and took
    103.8 s. It skipped 17 more tests (2036 passed, 22 skipped): the same race, in the gate.
  - The cost of serializing is the gate's 14 s start delay (install, build and herald's reduced lane). The rest of
    the 54 s difference is the 17 built-site tests that now run.
  - Before a commit, the gate's task (`--base origin/main --head HEAD`) sees no touched module and takes about 1 s,
    so a pre-commit full-scope run pays only the delay.
  - On a herald-only branch, `detectors-ci` (about 470 s) stays the critical path.
- **A herald-only diff does not select `docs-site-install`** (`pages.yml` does not fire). So herald's built-site
  tests run against whatever install the worktree has, and skip on a fresh one with none. CI's herald job never
  installs docs-site. A run whose diff fires `pages.yml` installs first (AC11).
- **A new task that writes `docs-site/` through a non-node script** (for example a Python script) with no install
  dependency matches no rule. A reviewer adds it to the set with its reason. The meta test's docstring names the
  rules, so the gap is visible. A node script that spawns npm or astro is caught by the spawn rule.
- `pyforge-herald-test-coverage` is not a preflight lane today; it is in the set because it runs the same tests.

## I/O & Edge-Case Matrix

| Situation | Today (`38ec9a2d25`) | After |
|---|---|---|
| `docs-site-install` and `pyforge-herald-test` both selected | start together; herald's built-site tests red or skip | one runs, then the other |
| `pages-build` and herald's Astro builds | both rewrite `docs-site/public/` at once | never at once |
| a docs-site lane and `lint-types` | concurrent | concurrent |
| a lane with `services: postgres` in the set | holds the service key only | holds both, in sorted order |
| two docs-site lanes ready, `--jobs 2`, one unrelated lane | the second docs-site lane would take a slot | it waits pending; the unrelated lane runs |
| red stop while a docs-site lane is deferred | (no deferral) | journaled as a never-started lane (Story 71.10) |
| red stop while a lane that pending lanes wait on is ready (`docs-site-install`) | started after the stop, killed at once by `register_proc`, `cancelled_by` the red lane | never started (Story 71.10); its dependents never start |
| fresh worktree (no `docs-site/node_modules`), herald and the Pages chain selected | herald first: 25 built-site tests skip (2033 passed, 30 skipped) | install first: herald 2058 passed, 5 skipped |
| a diff that changes `docs-site/package-lock.json` | herald could test against the old install | the install runs before herald |
| herald-touching committed branch: herald suite and herald gate | concurrent; the gate's built-site tests race the install (17 skip) | one after the other (about 14 s start delay) |
| `docs-site-validate-links`, `-sidebar-order` | concurrent | concurrent (builtins only, read `docs/`) |
| two threads ask for one key's lock at once | two locks possible (unguarded check-then-set) | one lock, one stored |
| a new node task runs `pages.mts build` with no `depends-on` | not derived (the meta test passed) | derived by the spawn rule: the meta test fails until it joins the set |
| CI | separate runners | unchanged |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-159 (concurrent lanes share no mutable state). No CAP is minted,
  and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-15 entry (the preflight runs two docs-site
  lanes at once).
- Epic: Epic 105 (new; Epics 71, 88, 90 and 104 are `done`, and Epic 103's theme is steward's reports).
- Ledger key: `105-1-the-preflight-never-runs-two-docs-site-lanes-at-once`.
- Ledger status at mint: `in-progress`.
- Deps: none.
- Spec: the `spec-pyforge-steward` memlog records the evidence, the design, the mint and the surface reconcile.
- Surface: `marshal-policy.toml` `[epic_surfaces]."105"` (added with the mint; widened in implementation for the
  station-tests workflow and the TEA matrix).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass. This is the station's
  `verify_commands` (MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `PYTEST_ADDOPTS= pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_preflight_docs_site_mutex.py src/shared/packages/pyforge-steward/tests/meta/test_preflight_docs_site_lanes.py src/shared/packages/pyforge-steward/tests/unit/test_preflight_lane_identity.py -q` — expected: exit 0 (AC1-AC6).
- `PYTEST_ADDOPTS= pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit -q -k preflight` — expected: exit 0 (AC8).
- The AC7 mutations, one at a time, each re-running its named test — expected: each fails it; the file is restored
  byte for byte.
- The proof driver (AC9): an untracked `docs-site/PREFLIGHT_PROBE.txt` makes `pages.yml` and the herald job fire.
  Then `pixi run --frozen -e pyforge-guild python docs_site_lanes_run.py <repo> <scratch pixi.toml>` runs
  `preflight.run_preflight(pixi_path=<scratch copy whose pr-preflight-lanes names only pyforge-herald-test,
  pages-check and docs-site-validate>, keep_going=True, scope="full")`. Expected: exit 0; in the journal no docs-site
  lane overlaps another; herald's log has 2058 passed and 5 skipped. Remove the probe after.
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run --frozen -e pyforge-guild pr-preflight -- --keep-going` — expected: no red
  `pyforge-herald-test`.
- `pixi run -e pyforge-steward pyforge-steward-coverage-gate`, `pixi run --frozen -e pyforge-guild lint-types`,
  `python scripts/ci_surface_gates.py --check` and the planning detectors — expected: exit 0.

## Verification run (2026-10-15)

Hand-implemented on branch `chain-preflight-docs-site-mutex-2026-10-15`, from baseline `38ec9a2d25`, uncommitted
(staged). The diff is for an independent review against this spec, not against this summary. Every verdict below
is read from its exit code.

- **The race, before the fix (the proof driver at `38ec9a2d25`).**
  - Two runs, journal `d89c06a0` and `20e53343`, both exited 0.
  - `docs-site-install` ran 0.4-3.6 s, beside `pyforge-herald-test` at 0.4-73.0 s.
  - Herald reported 2033 passed and 30 skipped. All 25 extra skips name the docs-site install as their reason.
  - Herald alone (`pixi run --frozen -e pyforge-herald pyforge-herald-test -rs`): 2058 passed, 5 skipped, exit 0.
- **AC9, after the fix (the same driver).**
  - Journal `554cc0b4`, exit 0.
  - `pyforge-herald-test` ran 0.5-137.1 s with 2058 passed and 5 skipped.
  - The docs-site lanes followed, one at a time: `docs-site-install` 137.1-140.1, `pages-build` 140.1-145.9,
    `pages-check` 145.9-147.5 and `docs-site-validate-sidebar` 147.5-147.8.
  - The two builtin-only validators ran beside herald, at 0.5-0.7 s.
- **Full-scope `pr-preflight`, first run** (`PYFORGE_PREFLIGHT_SCOPE=full pixi run --frozen -e pyforge-guild
  pr-preflight -- --keep-going`, with an untracked `docs-site/PREFLIGHT_PROBE.txt` so `pages.yml` and the herald job
  fire). Journal `74246451`, exit 1, 25 lanes.
  - `pyforge-herald-test` was `ok`, with 2058 passed and 5 skipped. The docs-site lanes started only after it ended
    (384.0 s) and finished at 407.3 s, well before `pyforge-steward-test` (718.7 s).
  - The two red lanes, `detectors-ci` and `pyforge-doctor-scripts-test`, were both `tea-playwright-check`: story 105.1
    was missing from steward's matrix. That led to the amendment: the matrix is regenerated.
- **Full-scope `pr-preflight`, final tree** (the same command and probe; the workflow edit makes it a shared-surface
  run, so every station job fires). Journal `fdb7f5eb`, **exit 0**, 28 lanes, all `ok`, 808.3 s.
  - `pyforge-herald-test`: 2058 passed, 5 skipped, 3.6-476.4 s. Then `docs-site-install` 476.4-483.2,
    `pages-build` 483.2-495.2, `pages-check` 495.2-498.3 and `docs-site-validate-sidebar` 498.3-498.9.
  - `pyforge-steward-test`: 2829 passed, 1 skipped (no suite reduction). `detectors-ci`, `lint-types`' five legs,
    both `mypy` lanes and every station suite were green.
  - Scribe's Postgres was up for the run (`scribe-pg-up`, then `scribe-pg-down`). The probe was removed after.
- **AC1-AC6:** `test_preflight_docs_site_mutex.py` (8), `test_preflight_docs_site_lanes.py` (6) and
  `test_preflight_lane_identity.py` passed, 29 in all. Every preflight unit test passed too: `-k preflight`, 350
  passed (AC8).
- **AC7:** each mutation failed its named test, and the file was restored byte for byte (`cmp`):
  - no docs-site key: `test_two_docs_site_lanes_never_overlap_and_dependencies_keep_their_order`;
  - no scheduler deferral: `test_the_pool_gives_the_slot_to_a_lane_that_can_run`;
  - keys taken unsorted: `test_two_lanes_given_their_keys_in_opposite_orders_take_them_in_one_order` (the two lanes
    deadlocked);
  - no release: `test_a_lane_releases_every_mutex_it_took_when_it_fails`;
  - `pages-check` dropped, `pyforge-herald-coverage-gate` dropped and `docs-site-validate-links` added: each failed
    `test_the_declared_set_is_exactly_the_derived_set`.
  - The one-lock-per-key test (`test_every_thread_gets_the_one_lock_of_a_key`) checks the property and does not
    catch the old unguarded check-then-set: that race window is too small to hit on demand.
- **AC10, the gates.**
  - The steward coverage gate (`COVERAGE_GATES_STATIONS=steward python scripts/coverage_gates_ci.py --paths-file
    <the staged paths> --suites unit`, because nothing is committed for `--base origin/main --head HEAD` to see):
    exit 0, 2828 passed and 2 skipped; `preflight.py` at 94%, against the 80% floor.
  - `pixi run --frozen -e pyforge-guild lint-types`: exit 0.
  - `python scripts/ci_surface_gates.py --check`: exit 0.
  - Each of these exited 0: `chain-completeness-check`, `dream-chain-check`, `dreams-hygiene-check`,
    `deferred-work-check`, `ledger-regression-check`, `story-status-check`, `chain-currency-sweep-check`,
    `ad-citation-check`, `flag-gate-check`, `spec-surface-check` (no drift, with the memlog reconciles staged) and
    `tea-playwright-check`.
- **Not done here.** No commit and no scoped stamp: the orchestrating session stamps `spec-pyforge-steward` and
  `spec-pyforge-core` from a clean tree after committing. The independent review is still to come.

## Verification run (2026-10-15, review fixes)

Run on `bf92dfc0d9` (the story commit `9ef2b206e4` with `origin/main` merged), with the review unit staged. Every
verdict is read from its exit code.

- **A fresh worktree (should-fix 2).** With `docs-site/node_modules` removed, I ran the proof driver
  (`scratchpad/docs_site_lanes_run.py`, the runner's own selection with an untracked `docs-site/` probe).
  - Before the reorder, at `bf92dfc0d9` (journal `64ff83c3`): herald ran first (0.4-70.5 s) and reported 2033 passed,
    30 skipped. The install followed at 70.5 s.
  - After the reorder (journal `e5db2d86`, exit 0): `docs-site-install` ran 0.5-3.4, `pages-build` 3.4-9.2 and
    herald 9.2-146.0, with 2058 passed and 5 skipped. The two builtin-only validators ran beside the install.
- **Herald's suite and gate, serialized (should-fix 3).** I ran `scratchpad/herald_gate_cost_run.py` with the gate
  as `--paths-file` (`pages_env.py`) and an untracked herald probe. Each run selected all eight lanes.
  - Serialized, journal `74820f3c`, exit 0: 158.2 s.
  - The gate out of the set, journal `f612c11a`, exit 0: 103.8 s, with 17 of the gate's tests skipped by the race.
  - The figures are in Residual risk.
- **A full-scope `pr-preflight`** (`PYFORGE_PREFLIGHT_SCOPE=full pixi run --frozen -e pyforge-guild pr-preflight --
  --keep-going`, with untracked `docs-site/` and herald probes and scribe's Postgres up). Journal `c340e80d`,
  **exit 0**, 29 lanes, all `ok`, 739.7 s.
  - The docs-site group ran in order: `docs-site-install` 3.3-20.1, `pages-build` 20.1-43.8, `pyforge-herald-test`
    43.8-424.9 (2058 passed, 5 skipped), then `pages-check` 424.9-427.6 and `docs-site-validate-sidebar` 427.6-428.2.
  - `pyforge-herald-coverage-gate` was selected and ran at 739.3-739.7. With no herald module in the committed diff,
    it had no herald module to measure. It started late because it also holds `services:postgres`, the
    coverage-gates job's service (Story 71.3), and `pyforge-steward-coverage-gate` held that key until 739.3 s.
  - `pyforge-steward-test`: 2834 passed, 1 skipped. `detectors-ci`, every station suite and both `mypy` lanes were
    green.
- **The story's three test files:** 34 passed (`test_preflight_docs_site_mutex.py` 11,
  `test_preflight_docs_site_lanes.py` 8, `test_preflight_lane_identity.py` 15). `-k preflight`: 361 passed.
- **The review mutations.** Each failed its named tests, and every file was restored byte for byte:
  - ready lanes in declaration order only failed AC11's two tests and the restated selection test;
  - lanes pending lanes depend on starting after a stop failed AC12's test;
  - an unguarded `setdefault`, and the old check-then-set, each failed AC4's lock test;
  - no spawn rule failed the rule guard and the planted test;
  - `docs-site/src/lib` dropped from `steward_paths` failed the coverage test.
  - Planting `pages-preview` in the real `pixi.toml` failed `test_the_declared_set_is_exactly_the_derived_set`, and
    `pixi.toml` was restored byte for byte.
  - The hang guard, set to 5 s against a scheduler mutated into a spin, ended the process with exit 1 after 5.6 s
    and wrote every thread's stack to its dump file.
- **Gates.**
  - The steward coverage gate (`--paths-file`, the branch's committed and staged paths): exit 0, 2833 passed,
    `preflight.py` at 94%.
  - `lint-types`, `ci_surface_gates.py --check` and `tea-playwright-check`: each exit 0.
  - Each of these exited 0: `chain-completeness-check`, `dream-chain-check`, `dreams-hygiene-check`,
    `deferred-work-check`, `ledger-regression-check`, `story-status-check`, `chain-currency-sweep-check`,
    `ad-citation-check`, `flag-gate-check` and `spec-surface-check` (no drift).
- **Not done here.** No commit and no stamp. Both probes were removed, and Postgres is down again.

## Review (2026-10-15)

The independent review of `9ef2b206e4` (merge `bf92dfc0d9`) returned **PASS**, with three should-fix findings and four
nits. The report is in the orchestrating session's scratch (`review-105-1.md`), with its probes and scenario driver.
Every finding is resolved on the same branch, as one staged unit.

- **1 (should-fix): the meta test missed spawned builds.**
  - **Finding:** no rule saw a docs-site script that spawns npm or astro. A new `node docs-site/scripts/pages.mts
    build` task with no `depends-on` passed the test. Dropping `pages-build`'s install dependency made the test
    demand that `pages-build` and `pages-check` leave the set.
  - **Resolution:** the spawn rule (Approach). The guard requires `pages-build` and `pages-check` to match it on their
    own, and `test_a_build_through_a_docs_site_script_is_seen_without_its_install_dependency` plants both changes.
    Planting `pages-preview` in the real `pixi.toml` now fails `test_the_declared_set_is_exactly_the_derived_set`.
- **2 (should-fix): run order.**
  - **Finding:** ready lanes were ordered by `lanes.index`, so `pyforge-herald-test` always ran before
    `docs-site-install`. On a fresh worktree, herald's 25 built-site tests still skipped silently, and a
    `package-lock.json` change was tested against a stale install.
  - **Resolution:** `_run_order` (Approach), narrowed to lanes that hold a mutex. AC11's tests cover it, and the
    fresh-worktree run below measures it.
- **3 (should-fix): the cost of serializing herald's suite and gate was not measured.**
  - **Resolution:** measured, and recorded in Residual risk, in the I/O matrix and in the steward memlog.
- **4 (nit): the lock test did not bite.**
  - **Resolution:** `_RacyLocks` holds the check-to-store window open. Both the old unguarded check-then-set and an
    unguarded `setdefault` now fail the test.
- **5 (nit): no hang guard.**
  - **Resolution:** an autouse fixture wraps every test in
    `faulthandler.dump_traceback_later(120, exit=True, file=<basetemp>/hang-guard-<test>.txt)`. With the scheduler
    mutated into a spin and the guard set to 5 s, the test process exited 1 after 5.6 s, and the dump held every
    thread's stack.
- **6 (nit): a redundant `steward_paths` entry, and an unenforced one.**
  - **Resolution:** `docs-site/src/lib/status.ts` is dropped. `test_steward_s_job_fires_on_every_docs_site_file_this_test_reads`
    now enforces `docs-site/src/lib`: dropping it fails the test.
- **7 (nit): after a red stop, a deferred lane that pending lanes wait on was still started, then killed.**
  - **Resolution:** a red stop starts no lane (Approach). AC12's test covers it.

## Spec Change Log

- 2026-10-15: minted from the Dream's 2026-10-15 entry, from the orchestrating session's brief. `type: fix`, no flag,
  no CAP. Bound to `spec-pyforge-steward` CAP-159.
- 2026-10-15 (implementation): steward's `steward_paths` in `pyforge-station-tests.yml` gains `docs-site/scripts`
  and `docs-site/src/lib`, because the new meta test reads them (Story 98.1's guard failed without the edit). The
  TEA matrix is regenerated (the first full preflight failed `tea-playwright-check` on story 105.1). No AC changed.
- 2026-10-15 (review): PASS with three should-fix findings and four nits, all resolved (§ Review). Added:
  - AC11-AC13;
  - the spawn rule and the `steward_paths` coverage test (AC5);
  - the lock-map test (AC4).

  AC8 notes the one restated order assertion. `docs-site/src/lib/status.ts` leaves `steward_paths`.
