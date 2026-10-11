---
title: '92.1: The unsplit-Redis eviction guard proves broker loss on every run'
type: 'fix'
created: '2026-10-11'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-49-5-cap-11-in-effect-the-eviction-test.md
  - src/platform/tests/test_redis_cache_eviction_broker_survival.py
  - scripts/platform-ci-local.sh
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the regression guard that keeps CAP-11's eviction test honest fails about one run in eight, on trees that
never touched Redis. Each failure refuses a platform-touching landing. Line numbers below are at `27af54f73b`.

- **What the guard is for.** Story 49.5 shipped two real-Redis tests in
  `src/platform/tests/test_redis_cache_eviction_broker_survival.py`. The split test
  (`test_broker_survives_cache_eviction_when_split`, :254-:268) fills `redis-cache` (1 MB, `allkeys-lru`) while
  `redis-broker` (32 MB, `noeviction`, AOF) holds a queued task, a stream entry and a pending (PEL) entry, and asserts
  all three survive. The guard (`test_unsplit_redis_loses_broker_state_under_cache_pressure`, :271-:303) runs the
  same pressure on one shared instance and asserts the broker loses something. Story 49.5's spec requires it: the
  split test "must FAIL if run against a single shared (non-split) Redis instance". Without the guard, the split test
  could pass because no broker key was ever at risk.
- **What the guard does.** It starts one `redis-server` at `SHARED_MAXMEMORY` (4 MB) with `allkeys-lru` (:280-:285),
  seeds the broker state (`_seed_broker_state`, :113-:141), runs `_fill_cache_to_eviction` once (:144-:175: 50 KB
  values until `evicted_keys` moves, then 50 more writes) and asserts `broker_lost` (:292-:301): the queue is shorter,
  the stream is shorter, the PEL is shorter, or the event is gone.
- **Why it flakes.** Redis's `allkeys-lru` is an approximation. It evicts the best candidate from a small random sample
  of keys (`maxmemory-samples`, default 5), and its LRU clock ticks once a second. The seed and the whole fill run
  inside about a second, so the two broker keys (the `DEFAULT_QUEUE` list and the stream) look no older than the fill
  keys. Measured once after one fill, 55 keys were resident and 52 had been evicted, so some runs leave both
  broker keys standing. Nothing is wrong with the split; the guard just did not apply enough pressure that run.

**Evidence:**
- **Warden 16.1.** Dispatch run `pyforge-warden-20261011T180723612Z-6ef4d113`, landing blob
  `dispatch-land-2621791-1.json`: MRS-GATE-015, `pixi run -e pyforge-guild platform-ci-local -- --test` exit 1,
  "1 failed, 1224 passed, 14 skipped", `FAILED
  tests/test_redis_cache_eviction_broker_survival.py::test_unsplit_redis_loses_broker_state_under_cache_pressure`,
  "AssertionError: unsplit redis must lose broker-side state under cache eviction; otherwise the split survival test
  would pass vacuously" at :298.
- **Herald 37.1.** Its `platform-ci-local -- --test` verification failed the same guard on 2026-10-11 (1 failed, 1206
  passed, as the session that ran it reported). The script's work dir is overwritten by each run, so that log is gone.
  The same trees passed on a re-run.
- **Measured on `27af54f73b`** (2026-10-11, platform-ci-test's python, platform-dev's `redis-server` 8.10.1): 8 of 60
  pytest runs of the guard's node id failed, each with the assertion above. In one process, the single fill lost broker
  state in 84 of 100 scenarios.
- **A prototype of the fix** (a scratch script, not committed) kept `allkeys-lru` and the 49.5 fill, then wrote full
  keyspace turnovers and re-read the broker after each. It lost broker state in 200 of 200 scenarios: 172 needed no
  extra round and 28 needed one. With no eviction pressure at all it lost nothing in 20 of 20.

**Approach:** the guard keeps applying cache pressure, a bounded number of times, until it sees the broker lose state.
- **Keep what 49.5 proves.** The shared instance stays at `allkeys-lru`, the cache's real policy, which is the unsafe
  composition CAP-11 names. `_fill_cache_to_eviction` still runs first and still asserts that eviction happened and
  memory stayed under the limit.
- **Add bounded turnover rounds, in the guard only.** After the fill, while the broker shows no loss and fewer than
  `_BROKER_LOSS_MAX_ROUNDS` (20) rounds have run: write one full turnover (`2 * maxmemory // _FILL_VALUE_BYTES` fresh
  `_FILL_VALUE_BYTES` keys, each key name unique to its round), then read `_broker_snapshot`. Stop at the first round
  that sees loss. A helper next to `_fill_cache_to_eviction` holds the loop; the split test never calls it.
- **Keep the assertion.** `broker_lost` keeps its four conditions and its message. When it fails, the message also
  names the rounds run and the instance's `evicted_keys`, so a red run says whether pressure was applied.
- **Why not `allkeys-random`,** the ruling's other option. It would change the composition under test from the cache's
  real policy to one no chart uses. One random pass is no more certain than one LRU pass; the certainty comes from
  turnover volume, which the rounds give under either policy.
- **Rejected:** a skip, an `xfail` or a rerun plugin, because the guard exists to stop the split test passing
  vacuously; raising `maxmemory-samples`, because it changes the server under test and is still a sample; asserting on
  `evicted_keys` alone, because that proves cache eviction, not broker loss.

Ledger key: `92-1-the-unsplit-redis-eviction-guard-proves-broker-loss-on-every-run`.
Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **`spec-pyforge-unifying-strategy` CAP-11** (Queue and cache cannot evict each other). Story 49.5 exercised its
  success clause, "Filling the cache to its eviction limit provably loses no queued task", with the split test, and
  proved that test is not vacuous with the guard. This story makes the guard reliable. It changes no behaviour CAP-11
  names, so it needs no new CAP and no `SPEC.md` change.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag, and this one changes only a test.
- **Origin.** `docs/dreams/pyforge-steward.md` Realization log, 2026-10-11 (eviction guard flake). Operator ruling
  2026-10-11, verbatim label "Mint steward fix story (Recommended)": "Steward fix story: make the regression guard
  deterministic (fill past maxmemory with enough keys and retry a bounded number of times until eviction is observed,
  or use the allkeys-random policy in that test). Mutation-check it, then dispatch it ahead of the next
  platform-touching landings."

## Acceptance Criteria

- **AC1 — The guard sees broker loss on every run.**
  - **Given** the shared instance at `SHARED_MAXMEMORY` with `allkeys-lru` and the seeded broker state, **When** the
    guard runs, **Then** it runs `_fill_cache_to_eviction` once, then turnover rounds (each `2 * maxmemory //
    _FILL_VALUE_BYTES` fresh keys under a round-unique name, then one `_broker_snapshot`), stopping at the first round
    that shows loss, and `broker_lost` holds.
  - The rounds are bounded by a module constant `_BROKER_LOSS_MAX_ROUNDS = 20`. The guard never loops without a bound.
  - When no round shows loss, the guard fails with the existing message plus the rounds run and `evicted_keys`.
- **AC2 — Twenty in a row.** The guard passes 20 of 20 consecutive runs of its node id, by the loop named under
  Verification, with no run skipped. The whole module passes 20 of 20 in the same loop over the file.
- **AC3 — Mutation: no pressure, no pass.** With the eviction pressure removed (the `_fill_cache_to_eviction` call and
  the turnover rounds both taken out of the guard, so it seeds and reads only), the guard fails with its own
  `AssertionError` on 5 of 5 runs. The change is reverted afterwards and the spec's Auto Run Result records the five
  failures.
- **AC4 — The split test it protects is unchanged and green.** `test_broker_survives_cache_eviction_when_split`,
  `_run_split_survival_scenario`, `_fill_cache_to_eviction`, `_seed_broker_state`, `_broker_snapshot`, `_start_redis`
  and the constants `CACHE_MAXMEMORY`, `BROKER_MAXMEMORY`, `SHARED_MAXMEMORY` and `_FILL_VALUE_BYTES` keep every
  line: the diff may add code beside them but changes none of their lines. The split test passes in every AC2 run.
- **AC5 — Never weakened.** The diff adds no `skip`, `skipif`, `xfail`, rerun marker, rerun plugin or `importorskip`.
  The existing "redis-server not on PATH" skip is unchanged. The guard's shared instance stays `allkeys-lru`. The four
  `broker_lost` conditions are unchanged.
- **AC6 — The platform suite is green.** `pixi run -e pyforge-guild platform-ci-local -- --test` exits 0, including
  its Ruff, Ruff format and mypy steps over `tests`.
- **AC7 — Only the test file moves.** `git diff origin/main...HEAD --stat` outside `_bmad-output/` and
  `scripts/.spec-surface-baseline.json` names only `src/platform/tests/test_redis_cache_eviction_broker_survival.py`.
  The chart, `src/platform/config/`, the platform's Redis settings, `scripts/platform-ci-local.sh` and `pixi.toml` do
  not change.
- **AC8 — The surface is reconciled.** The `spec-pyforge-unifying-strategy` memlog gets a surface-reconcile entry that
  names the test file and this story, the Spec is stamped scoped (`--spec
  pyforge-steward/spec-pyforge-unifying-strategy`), and `spec-surface-check` exits 0.

## Boundaries & Constraints

**Always:**
- Change only `src/platform/tests/test_redis_cache_eviction_broker_survival.py`, plus this story's memlog entry and
  scoped stamp.
- Use a real `redis-server` under real eviction pressure, as Story 49.5 requires. Never mock eviction.
- Keep the shared instance at `allkeys-lru`, the cache's real policy.
- Keep every bound explicit: a fixed round count and a fixed writes-per-round.

**Never:**
- Never weaken the guard: no skip, `xfail`, rerun, softened assertion or removed `broker_lost` condition.
- Never change the split test, its helpers, the module constants or the chart's Redis split and policies.
- Never change production Redis configuration, `src/platform/config/`, `scripts/platform-ci-local.sh` or `pixi.toml`.
- Never add a dependency: `pytest-repeat` and `pytest-rerunfailures` are not in `platform-ci-test`, and this story
  adds neither.

**Residual risk:**
- The rounds make a false red vanishingly unlikely, not impossible: each round writes 167 fresh keys into an instance
  that holds about 55, so it turns the keyspace over about three times. The prototype never needed more than one round
  in 200 scenarios, so 20 leaves a wide margin.
- `_broker_snapshot` reads the broker keys between rounds, which refreshes their LRU clock. The prototype measured the
  rounds converging anyway, because every key a round writes shares that second of the clock.
- Worst case, the guard writes 20 × 167 values of 50 KB (about 167 MB) to a local `redis-server`. That only
  happens if eviction stops reaching broker keys, which is the regression the guard exists to catch.

## I/O & Edge-Case Matrix

| Situation | Today (`27af54f73b`) | After |
|---|---|---|
| the 49.5 fill evicts a broker key | guard passes | passes, with no extra round |
| the fill leaves both broker keys standing (about 1 run in 8) | guard fails; the landing is refused (MRS-GATE-015) | turnover rounds until loss; passes |
| no eviction pressure at all (AC3 mutation) | guard fails | guard fails, every run |
| 20 rounds and still no broker loss | not possible today (one pass) | guard fails, naming the rounds and `evicted_keys` |
| split instances, cache under pressure | split test passes | unchanged |
| `redis-server` not on PATH | both tests skip | unchanged |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-unifying-strategy` CAP-11 (Queue and cache cannot evict each other), the CAP
  Story 49.5 bound. No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-11 (eviction guard flake) entry.
- Epic: Epic 92 (new). Epic 49, which shipped the guard, is `done`, so the fix opens its own epic. `epic-92` and
  `epic-92-retrospective` are minted with it.
- Ledger key: `92-1-the-unsplit-redis-eviction-guard-proves-broker-loss-on-every-run`.
- Ledger status at mint: `backlog`.
- Deps: none. The operator asked for it to be dispatched ahead of the next platform-touching landings.
- Spec: the `spec-pyforge-unifying-strategy` memlog records the ruling verbatim, the evidence and design, and this mint.
- Surface: `marshal-policy.toml` `[epic_surfaces]."92"` (added with this mint) covers `src/platform/tests/**`.
- Minted 2026-10-11 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding). It does not run `src/platform/tests`; the dispatch runs `platform-ci-local -- --test` as its cross-surface check (MRS-GATE-015) because the diff touches `src/platform/`.

**Run before the push (not dispatch gates):**
- The AC2 loop, from the repo root after `pixi install --frozen -e platform-ci-test` and `pixi install --frozen -e platform-dev` (it runs platform-ci-test's python with platform-dev's `redis-server` on `PATH`, as `platform-ci-local` does): `R="$PWD/.pixi/envs"; cd src/platform && for i in $(seq 1 20); do env -u PYTHONSAFEPATH PATH="$R/platform-ci-test/bin:$R/platform-dev/bin:$PATH" python -m pytest "tests/test_redis_cache_eviction_broker_survival.py::test_unsplit_redis_loses_broker_state_under_cache_pressure" -q -p no:cacheprovider || exit 1; done` — expected: exit 0, each of the 20 runs "1 passed". Then the same loop with the node id replaced by `tests/test_redis_cache_eviction_broker_survival.py` — expected: exit 0, each of the 20 runs "2 passed".
- The AC3 mutation: take the `_fill_cache_to_eviction` call and the turnover rounds out of the guard, run the node id 5 times — expected: 5 of 5 fail with the guard's `AssertionError`. Restore it.
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: exit 0 (AC6).
- `git diff origin/main...HEAD --stat` — expected: AC7's one code path.
- `python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entry and the scoped stamp (AC8).
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: no new finding against `main`.

## Spec Change Log

- 2026-10-11: minted from the operator's ruling "Mint steward fix story (Recommended)". `type: fix`, no flag, no CAP;
  bound to `spec-pyforge-unifying-strategy` CAP-11 through Story 49.5.

## Review Triage Log

- No review has run yet.
