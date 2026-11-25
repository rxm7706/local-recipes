---
title: '133.3: The platform suite''s test stage runs without a container engine, on a UTF-8 database'
type: 'fix'
created: '2026-11-25'
status: 'done'
story: 133-3-the-platform-suite-s-test-stage-runs-without-a-container-engine-on-a-utf-8-database
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'scripts/platform-ci-local.sh'
  - 'tests/scripts/test_platform_ci_local_host.py'
  - 'src/platform/tests/test_redis_cache_eviction_broker_survival.py'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `DW-steward-review-2026-11-24-3` records three things met on a macOS laptop. (1) `scripts/platform-ci-local.sh:376` exits 2 when its container engine is not on `PATH`, before the stage switch, so `--test` fails on a host with no engine though that stage calls the engine only in cleanup. (2) `:385` runs `initdb` with no encoding, so under a `C` locale the throwaway cluster is `SQL_ASCII` and two policy tests error on a Unicode escape. (3) With both worked around, one test failed: `tests/test_redis_cache_eviction_broker_survival.py::test_broker_survives_cache_eviction_when_split`, a Redis `maxmemory` error not traced to a cause and not checked against main.

**Approach:** Reproduce each first on the unchanged tree and record how in the Spec Change Log, one line per defect. Then check the engine only for the stages that call it (images, container, promotion), and let the test stage's cleanup skip the engine when it is absent; pass `-E UTF8 --locale=C` to `initdb`; run the Redis test on the file as it is on main and either fix its cause where it lies in this surface or record it as not a defect of this tree. A defect the tree does not reproduce is recorded here as not a defect.

**Lead's rulings (2026-11-25), which this spec follows:** the per-defect record is written in the Spec Change Log below. The `platform-ci-local` task description in `pixi.toml` and its generated row in `docs/how-to/pixi-tasks.md` still say the engine is needed on the host without qualification; the session lead updates the description and regenerates the page, and neither file is in this story's surface. Recommended sentence, replacing "Docker or podman on the host." in the `platform-ci-local` description: "Docker or podman on the host for the images, container and promotion stages; --test needs none." The full `--test` stage (AC3) is run by the session lead after the implementation pass, and AC3 is proven by that run. The deferred-work row is closed by the session lead, naming each outcome recorded here.

Ledger key: `133-3-the-platform-suite-s-test-stage-runs-without-a-container-engine-on-a-utf-8-database`.

### Living CAP citations

- spec-pyforge-steward CAP-175 (realized, no text change); no AD moves.

## Boundaries & Constraints

**Always:**
- Reproduce before fixing, each defect on its own.
- A stage that builds or runs an image still refuses, exit 2, naming the engine, when the engine is absent.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never weaken or skip the Redis test to make the stage green; a cause outside this surface is named and reported.
- Never change what the script runs in CI's own job order.
- Never fix a defect that did not reproduce.
- Never edit `pixi.toml` or `docs/how-to/pixi-tasks.md` from this story; the session lead owns the task description and its generated page.

## Acceptance Criteria

**Given** `DW-steward-review-2026-11-24-3` reports that the script exits 2 when its container engine is not on `PATH` even for `--test`, that `initdb` runs with no encoding so a `C` locale gives an `SQL_ASCII` cluster and two policy tests error, and that one Redis eviction test failed with a `maxmemory` error not traced to a cause
**When** each is first reproduced on the unchanged tree, and then the engine is checked only for the stages that call it, `initdb` is given UTF-8 and a fixed locale, and the Redis test is traced on a clean main
**Then** `--test` with no engine on `PATH` and `LC_ALL=C` passes its prerequisite check and builds a UTF-8 cluster, a stage that uses the engine still exits 2 naming it, and the Redis test passes or its cause is fixed where it lies in this surface
**And** a defect the tree does not reproduce is recorded on this spec as not a defect, and the session lead closes the row naming each outcome

- **AC1 — Defects 1 and 2 are held by tests.** `tests/scripts/test_platform_ci_local_host.py` fails by name when the test stage's prerequisite check asks for the engine, when a stage that uses the engine stops asking for it, and when the `initdb` line carries no UTF-8 encoding. Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_platform_ci_local_host.py -q
  ```

- **AC2 — Defect 2: `initdb` names its encoding.** Expected: exit 0 (a line matches).

  ```bash
  grep -n -E "initdb.* -E UTF8" scripts/platform-ci-local.sh
  ```

- **AC3 — Defects 1, 2 and 3: the stage runs under a `C` locale.** Run by the session lead after the implementation pass, on a host with no container engine on `PATH` where one is to hand; this criterion is proven by that run, not by the implementation pass, and the lead records the host and the exit code in the Spec Change Log. Expected: exit 0.

  ```bash
  LC_ALL=C pixi run --frozen -e pyforge-guild platform-ci-local -- --test
  ```

- **AC4 — The script still parses.** Expected: exit 0.

  ```bash
  bash -n scripts/platform-ci-local.sh
  ```

- **AC5 — Steward's tests of the script pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pyforge-steward-test
  ```

- **AC6 — Not a defect is written down.** For each of the three defects, the Spec Change Log names either the command that showed it on the unchanged tree, or the command that showed the tree does not reproduce it and the words "not a defect". A defect recorded as not a defect has no AC above to meet. Expected: exit 0.

  ```bash
  grep -c -E "defect [1-3]: (reproduced|not a defect)" _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-133-3-the-platform-suite-s-test-stage-runs-without-a-container-engine-on-a-utf-8-database.md
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-175 (realized, no text change); no AD moves.
- Dream: `docs/dreams/pyforge-steward.md`, the 2026-11-25 entry (the review's lower-severity defects are reproduced, then fixed or closed); operator ruling of 2026-11-25.
- Epic: Epic 133, minted with this story.
- Ledger key: `133-3-the-platform-suite-s-test-stage-runs-without-a-container-engine-on-a-utf-8-database`.
- Deferred-work row: `DW-steward-review-2026-11-24-3`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."133"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry and the operator's ruling of the same date. Not implemented.
- 2026-11-25: defect 1: reproduced and fixed - `pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_platform_ci_local_host.py -q` against the unchanged script exited 1 (3 failed, 5 passed): `--test` with `PLATFORM_CI_LOCAL_ENGINE` set to a name no host has exited 2, "<engine> is not on PATH", from the last line of `ensure_envs`, which ran for every stage. Now `ensure_envs` asks for the engine only when images, container or promotion is among the stages, and `stop_services` skips the engine's `rm` when it is absent; held by `test_the_test_stage_does_not_ask_for_the_container_engine` and `test_a_stage_that_uses_the_engine_still_refuses_without_it` (five stage sets, each exit 2 naming the engine before any service starts).
- 2026-11-25: defect 2: reproduced and fixed - `LC_ALL=C initdb -D <dir> -U postgres --auth=trust` (PostgreSQL 17.11, the unchanged arguments) built `encoding=SQL_ASCII collate=C ctype=C`, and `pytest tests/policy` on that cluster ended 96 passed, 2 errors (`UntranslatableCharacter: unsupported Unicode escape sequence` in `test_sqlmigrate_extraction.py::test_live_first_party_tree_is_covered` and `test_liquibase_ddl_governance.py::test_app_role_create_alter_drop_refused_by_postgresql`). The `initdb` line now carries `-E UTF8 --locale=C`; on that cluster `tests/policy` passes in full; held by `test_initdb_builds_a_utf8_cluster_under_a_c_locale` and `test_the_initdb_line_names_its_encoding`, both red before the change.
- 2026-11-25: defect 3: reproduced and fixed - `pytest tests/test_redis_cache_eviction_broker_survival.py` on the file as it is on main (`git diff main` on it empty) raised `redis.exceptions.OutOfMemoryError` at the tail loop's first SET, every run, on osx-arm64 with redis-server 8.10.2 (libc allocator); the reviewer reproduced it independently, 3 of 3 runs. Cause: an empty server already uses about 0.9 MB of the test's own `CACHE_MAXMEMORY = "1mb"`, so the first 50 kB SET is refused with nothing to evict; the cause is the test's limit, not the product. The limit is now `"4mb"`, the value the shared-instance test already uses; no assertion is weakened or removed, and the fill still requires a real eviction. Not checked on linux-64.
- 2026-11-25: hosts. Every reproduction above ran on a macOS laptop (osx-arm64) with no docker or podman on `PATH`, the PostgreSQL and redis-server binaries from the `platform-dev` environment, on a throwaway cluster. AC1, AC2, AC4 and AC5 exit 0 on that host. AC3, the full `LC_ALL=C ... platform-ci-local -- --test` stage, was not run in the implementation pass: the session lead runs it after this pass and AC3 is proven by that run. One thing that run should watch: the local cluster is now `C`-collated on every host, where CI's `postgres:17` service is `en_US.utf8`; `-E UTF8` alone also closes defect 2 and leaves UTF-8 hosts as they were, should a collation-sensitive test turn up.
- 2026-11-25: the story is implemented and in review. Left to the session lead under the rulings above: the AC3 run, the `pixi.toml` task description and its generated page, and closing `DW-steward-review-2026-11-24-3`.
- 2026-11-25: closed. PR #2385 merged as 080f89c4df (`Merge pyforge-steward/133-1 into main`) after its 51 CI checks passed and the full local `pr-preflight` exited 0 on 48 lanes; an independent reviewer read the diff against this spec before the merge, its findings were applied and re-reviewed.
