---
title: "34.14: A plain run on a fresh data root exits 0"
type: 'fix'
created: '2026-11-01'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/live-sources.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/research/egm-audit-2026-11-01.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-37-2-the-pages-vizro-export-builds-the-public-atlas-data-first.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-34-12-a-vulnerability-feed-that-cannot-be-reached-keeps-its-last-good-copy.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-34-15-the-three-core-sources-keep-last-good-when-the-network-is-refused.md
  - src/shared/packages/pyforge-atlas/AGENTS.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipeline_registry.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/orchestration/definitions.py
  - src/shared/packages/pyforge-atlas/tests/conftest.py
deferred: []
---

<intent-contract>

## Intent

**Problem:** a plain `pyforge atlas run` (no `--pipelines`) on a fresh data root exits 1, while CAP-64's success
says the bootstrap plus `pyforge atlas run` exits 0 there, and no story AC owns that clause. Line numbers are at
`03a7aff5d9`.

- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipeline_registry.py` `register_pipelines()` (:17-35) sums
  every registered pipeline except `AFTER_RUN_PIPELINES` (`catalog_index`, :11) into `__default__`. So the plain run
  holds `query_plane_cache`, whose input `query_plane_estate_source` (`conf/base/catalog.yml`:1533) has no producer
  while Story 36.3 stays blocked (operator ruling 2026-10-18), and `universal_sbom`, whose intake load needs
  `--params sbom_intake_path` and has no degrade.
- Story 37.2's live run on a fresh scratch root, no credentials, stopped with `DatasetError:
  query_plane_estate_source: Failed while loading data` after 12 of 86 nodes, exit 1 at 5:25 (`DW-atlas-37-2-1`,
  2026-10-21). The `pyforge-atlas-bootstrap` task in `pixi.toml` and the Pages job already name their pipelines and
  leave both out; only the plain run takes the whole registry.
- The EGM audit of 2026-11-01 (`_bmad-output/projects/pyforge-atlas/planning-artifacts/research/egm-audit-2026-11-01.md`)
  accepted this as one code defect from three findings: **ATL-M-D1** (CAP-64's estate row cannot go green; Epic 34
  closed done with CAP-64 unmet), **ATL-D-R2** and **ATL-D-C3** (CAP-64's fresh-root and network-blocked run clauses
  own no story AC, and the first is false today). Their "no network call in the test lanes" part is refuted by the
  suite's socket guard (`tests/conftest.py`) and spec-34-12 AC9, so it is not carried here.

**Approach:**
- In `pipeline_registry.py`, add an excluded tuple beside `AFTER_RUN_PIPELINES` holding `query_plane_cache` and
  `universal_sbom`, the two the `pyforge-atlas-bootstrap` task leaves out, and keep both out of `__default__`. Each
  stays registered under its own name, so `pyforge atlas run --pipelines <name>` and the MCP trigger still reach it
  (and Story 42.2's kill switch still pops `universal_sbom` when it is off). A comment names Story 36.3 as the story
  that removes `query_plane_cache` from the tuple once the estate source has a producer.
- Read `orchestration/definitions.py` against the same exclusion: the `bootstrap_data` job is built from the
  translated `__default__` job, so it loses the two pipelines' ops; `NODE_TIMEOUTS` keeps their budgets, and
  `test_every_node_of_the_default_pipeline_has_its_own_timeout` compares the dict against every registered
  pipeline's nodes, not `__default__` alone.
- Prove the run, not only the registry: a run-level test drives `__default__` over a fresh data root with the public
  fetches served from recorded responses, under the socket guard, then runs again over the filled root with every
  fetch refused. (amended 2026-11-01: the second run, with every fetch refused, moved to Story 34.15 with AC3.)
- A `fix` under CAP-64: no CAP is minted and no flag is added (`spec-feature-flag-governance` Q1). It closes
  `DW-atlas-37-2-1`.

Ledger key: `34-14-a-plain-run-on-a-fresh-data-root-exits-0`. Type / Effort / Deps: fix / M / —.

## Acceptance Criteria

- **AC1 — The excluded tuple.** `pipeline_registry.py` declares a tuple beside `AFTER_RUN_PIPELINES` holding exactly
  `query_plane_cache` and `universal_sbom`; `register_pipelines()["__default__"]` holds no node of either, and both
  names stay in the registry (with `pyforge.atlas.manifest_inventory` on). A unit test in
  `src/shared/packages/pyforge-atlas/tests/unit/test_pipeline_inventory.py` pins the tuple against the
  `pyforge-atlas-bootstrap` task's pipeline list in `pixi.toml` (the same two left out, `catalog_index` aside).
- **AC2 — A plain run on a fresh root exits 0.** A run of `__default__` over an empty data root, with the public
  fetches served from recorded responses and the socket guard in `tests/conftest.py` active, exits 0; the test's
  assertion names `pypi_intelligence_scored` and the three vulnerability feeds (`vulnerability_cisa_kev_raw`,
  `vulnerability_epss_raw`, `vulnerability_cwe_catalog_raw`). (amended 2026-11-01: the run test lowers
  `verification_sets.core_packages_enumerated_floor` and `verification_sets.pypi_universe_floor` through runtime
  params, because fixture-scale recorded responses cannot meet the 30000-name floors; "plain run" here means
  `__default__` with no `--pipelines`, not the default parameters.)
- **AC3 — Network blocked keeps last-good.** A second run over the root AC2 filled, with every fetch refused, exits 0
  and every public store AC2 filled keeps its last-good file under its AD-13 `stale` marker. (amended 2026-11-01:
  moved to Story 34.15 by the session owner's ruling of 2026-11-01, because it needs an AD-13 last-good degrade on
  `FeedstockOutputsArchiveDataset`, `CondaRepodataDataset` and `PyPISimpleIndexDataset`, outside this story's
  Boundary; this story no longer carries it.)
- **AC4 — Still reachable.** `pyforge atlas run --pipelines query_plane_cache` and `--pipelines universal_sbom` resolve
  their pipelines as before (the estate source's absence still fails `query_plane_cache` on a fresh root: that is
  Story 36.3's, not this story's).
- **AC5 — The Dagster jobs.** The `bootstrap_data` job carries no op of either excluded pipeline;
  `NODE_TIMEOUTS` still holds every registered pipeline's nodes, and the timeout test reads every registered pipeline.
- **AC6 — Mutation.** AC1 and AC2 each fail when `query_plane_cache` is put back into `__default__`.
- **AC7 — Records.** `DW-atlas-37-2-1` reads closed with this story's evidence; `pixi run --frozen -e pyforge-atlas
  pyforge-atlas-test` passes.

## Boundaries & Constraints

**Always:**
- Keep both pipelines registered and reachable by name; change only what `__default__` sums.
- Keep the run-level test network-free (recorded responses, the socket guard; AD-11).

**Never:**
- Never produce `query_plane_estate_source` here or read platform tables (Story 36.3, blocked by operator ruling
  2026-10-18); never unregister a pipeline; never add a flag or a CAP; never change the `pyforge-atlas-bootstrap`
  task's pipeline list.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-atlas` CAP-64 (FR-72): the fresh-root and network-blocked run clauses of its
  success. No CAP is minted.

Parent: `spec-pyforge-atlas` CAP-64

- Audit findings carried: ATL-M-D1, ATL-D-R2, ATL-D-C3 (EGM audit 2026-11-01, cluster ATL-K2;
  `_bmad-output/projects/pyforge-atlas/planning-artifacts/research/egm-audit-2026-11-01.md`).
- Closes: `DW-atlas-37-2-1` (promoted to this story at mint; closes when it lands).
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, 2026-10-18 (atlas fills its own data).
- Epic 34 (done; reopened by this story under doctor Story 41.5's rule).
- Ledger key: `34-14-a-plain-run-on-a-fresh-data-root-exits-0`.
- Deps: —.
- Surface: `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipeline_registry.py`,
  `src/shared/packages/pyforge-atlas/src/pyforge/atlas/orchestration/definitions.py`,
  `src/shared/packages/pyforge-atlas/tests/unit/test_pipeline_inventory.py`,
  `src/shared/packages/pyforge-atlas/tests/unit/orchestration/test_definitions_dryrun.py`,
  `src/shared/packages/pyforge-atlas/tests/integration/test_plain_run_fresh_root.py` (new);
  (amended 2026-11-01) `src/shared/packages/pyforge-atlas/tests/unit/test_retrofit_flags.py`, whose manifest-inventory
  test asserted the `universal_sbom` nodes sit inside `__default__` and turns red with AC1.
- Minted 2026-11-01 by the EGM fleet audit (marshal Story 113.7); built later through `marshal factory dispatch`.
  That PR reconciles spec-surface on `spec-pyforge-atlas` and its co-governor `spec-pyforge-core`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-atlas pyforge-atlas-test` — expected: pass (the station's `verify_commands`; AC7).
- `pixi run --frozen -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests/unit/test_pipeline_inventory.py src/shared/packages/pyforge-atlas/tests/unit/orchestration/test_definitions_dryrun.py -q` — expected: pass (AC1, AC5).
- `pixi run --frozen -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests/integration/test_plain_run_fresh_root.py -q` — expected: pass (AC2, AC3). (amended 2026-11-01: AC3's run is Story 34.15's; the file holds both.)
- `pixi run --frozen -e pyforge-atlas kedro-catalog-check` — expected: pass.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Run before the push:** AC6's mutation (put `query_plane_cache` back into `__default__`) and the two named test files
fail; revert.

## Auto Run Result

Status: in-review (resumed 2026-11-01 in the landing worktree `egm-audit-2026-11` after the session owner's ruling
moved AC3 to Story 34.15; not committed). AC3 is that story's; every other AC is met here.

**What changed:**
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipeline_registry.py`: `NAMED_RUN_ONLY_PIPELINES =
  ("query_plane_cache", "universal_sbom")` beside `AFTER_RUN_PIPELINES`; `register_pipelines()` leaves both tuples out
  of `__default__`. Both stay registered (the kill switch still pops `universal_sbom` when off); the comment names
  Story 36.3 as the story that takes `query_plane_cache` out of the tuple. This is the preserved diff of the blocked
  pass, applied unchanged (AC1).
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/orchestration/definitions.py`: a comment on `bootstrap_data`
  says its DAG is the translated `__default__`, so it carries neither pipeline's ops. `NODE_TIMEOUTS` gains
  `report_catalog_index_health: 300`: read literally, AC5's "every registered pipeline's nodes" includes
  `catalog_index` (Story 37.10), whose one node never had a budget because it was never in `__default__`; the
  timeout test that now reads every registered pipeline went red on it (AC5).
- `src/shared/packages/pyforge-atlas/tests/unit/test_pipeline_inventory.py`:
  `test_a_plain_run_leaves_out_what_the_bootstrap_task_leaves_out` reads the `pyforge-atlas-bootstrap` task's
  `--pipelines` list from `pixi.toml` and pins the tuple to exactly what it leaves out (`catalog_index` aside), with
  each pipeline registered, holding nodes, and outside `__default__` (AC1, AC4).
- `src/shared/packages/pyforge-atlas/tests/unit/orchestration/test_definitions_dryrun.py`: the Story 34.8 timeout test
  is renamed `test_every_node_of_every_registered_pipeline_has_its_own_timeout` and reads every registered pipeline
  (the manifest-inventory switch pinned on); `test_the_bootstrap_job_carries_no_op_of_a_pipeline_a_run_must_name`
  is new (AC5).
- `src/shared/packages/pyforge-atlas/tests/unit/test_retrofit_flags.py`: switch ON, `universal_sbom` is registered
  and its nodes sit outside `__default__` (the amended Surface).
- `src/shared/packages/pyforge-atlas/tests/integration/test_plain_run_fresh_root.py` (new; shared with Story 34.15):
  a copied project with an all-`{}` credentials stub over an empty data root; `requests.Session.request` answers the
  feedstock-outputs zip, the seven `current_repodata.json`, the PyPI simple index and the three vulnerability feeds
  from recorded bodies and refuses everything else; `PosixProcess.run` refuses every subprocess; the socket guard
  stays on; `pyforge.atlas.live_public_sources` runs off and on. `test_a_plain_run_on_a_fresh_data_root_exits_0`
  runs `__default__` with the `verification_sets` floors lowered by runtime params (the AC2 amendment) and asserts
  `pypi_intelligence_scored` was written and each of `vulnerability_cisa_kev_raw`, `vulnerability_epss_raw` and
  `vulnerability_cwe_catalog_raw` kept rows with no marker (AC2). "Exits 0" is read in-process: `session.run()`
  returns without raising, which is what `kedro run` turns into exit 0.
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md`: `DW-atlas-37-2-1` reads
  `status: closed` with a `resolved:` line naming this story's change and test (AC7).
- Planning: the Tier-3 feed key `34-14-...` moved `backlog` -> `in-progress` and `sprint-ledger-sync` promoted it;
  without that, `tests/meta/test_planning_record.py::test_epics_per_story_status_matches_sprint_ledger` reds on the
  epics Status line this amendment set.
- AC4: both pipelines stay registered with nodes (the AC1 test and the retrofit test), and `kedro run --pipelines
  <name>` resolves `pipelines[name]`; neither named run was executed (on a fresh root `query_plane_cache` still
  fails on the estate source, Story 36.3's).

**Commands** (each from the worktree root; exit codes read from `$?`, never through a pipe):
- `pixi run --frozen -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests/unit/test_pipeline_inventory.py src/shared/packages/pyforge-atlas/tests/unit/orchestration/test_definitions_dryrun.py -q`: exit 0 (65 passed).
- `pixi run --frozen -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests/integration/test_plain_run_fresh_root.py -q`: exit 0 (4 passed; this story's test and Story 34.15's, each live off and on).
- `pixi run --frozen -e pyforge-atlas kedro-catalog-check`: exit 0 (71 passed).
- `TMPDIR=$HOME/.cache/pyforge-preflight-tmp pixi run --frozen -e pyforge-atlas pyforge-atlas-test`: exit 0
  (3316 passed, 17 skipped / 221 passed, 1 skipped / 103 passed) (AC7). The first run, before the feed key moved
  and before Story 34.15's `LAST_GOOD_TYPES` entry, failed 2: the epics-vs-ledger test and
  `test_vizro_static_boards.py::test_every_last_good_store_under_the_data_root_is_cached` (Story 34.15's).
- `pixi run --frozen -e pyforge-guild lint-types`: exit 0. The atlas mypy slice alone (`mypy --cache-dir
  .mypy_cache/pyforge-guild -p pyforge.atlas` from the package dir): exit 0, 150 files.
- Touched-module unit coverage from `.steward/coverage/atlas-unit.json`: `pipeline_registry.py` 100.0%,
  `orchestration/definitions.py` 90.4% (floor 80%).
- AC6 mutations, as a scratch pytest plugin (`-p atlas_mutant`, the tree never edited), over the AC1, AC5 and AC2
  files: `tuple-drops-query-plane-cache` (the tuple without `query_plane_cache`): exit 1, the AC1 test and all four
  integration cases fail, the run stopping on `query_plane_estate_source`; `sum-ignores-tuple` (the pre-34.14 sum):
  exit 1, the AC1 test, the AC5 bootstrap-job test and all four integration cases fail.
- `pixi run -e pyforge-guild sprint-ledger-sync -- --project atlas`: exit 0; `pixi run --frozen -e pyforge-guild
  story-status-check`: exit 0; `pixi run --frozen -e pyforge-guild deferred-work-check`: exit 0.

### Earlier pass: blocked (2026-11-01)

Status: blocked (2026-11-01, EGM audit fix pass). AC3 cannot be met without breaking the Boundary "change only
what `__default__` sums"; no code from this story is left in the tree.

**Blocking condition.** With every fetch refused, a plain run stops at its first node on three core datasets that
have no AD-13 degrade: `FeedstockOutputsArchiveDataset` (`core_feedstock_outputs_raw`), `CondaRepodataDataset`
(`core_repodata_raw`) and `PyPISimpleIndexDataset` (`pypi_simple_index_raw`), all in
`src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/core_sources.py`. Each raises
`DatasetError: ...: Failed to connect to the remote server` and keeps no last-good copy, whatever the data root
holds. Excluding `query_plane_cache` and `universal_sbom` from `__default__` does not touch them. Meeting AC3 means
giving those three datasets a last-good copy under the AD-13 `stale` marker (the Story 34.12
`VulnerabilityFeedDataset` pattern, with a `filepath` under the data root in `conf/base/catalog.yml`). That is a
change outside this story's Surface and outside what `__default__` sums. CAP-64's network-blocked clause is false for
these three today, and no story owns them.

**Measured** (exploration harness: a copy of the project in `tmp_path` with conf/base only, an all-`{}` credentials
stub, `PYFORGE_ATLAS_DATA_ROOT` on an empty dir, `requests.Session.request` and `PosixProcess.run` patched, under the
suite's socket guard; `__default__` with the registry change applied, 92 nodes):
- Every free input of `__default__` loaded with every fetch refused (`public_sources.live` OFF and ON): 31 inputs; only
  the three above raise.
- Fresh root, recorded responses for the feedstock-outputs zip, the seven conda-forge `current_repodata.json` subdirs,
  the PyPI simple index and the three vulnerability feeds, every other fetch refused: the run exits 0 in about 1 s,
  live OFF and ON. It needs `verification_sets.core_packages_enumerated_floor` and `pypi_universe_floor` lowered by
  runtime params: fixture-scale responses cannot meet the 30000-name floor (`HollowVerificationSetError` otherwise).
  AC2 is reachable.
- Second run over that root, every fetch refused: exit 1 at `core_feedstock_outputs_raw`, no node ran. The vulnerability
  stores still hold `last_good.parquet` and write no marker, because the run stopped before they loaded.
- The same second run with only the three core URLs still served: exits 0, and each of `vulnerability_cisa_kev_raw`,
  `vulnerability_epss_raw` and `vulnerability_cwe_catalog_raw` keeps `last_good.parquet` under `.staleness.json`. So
  the three core datasets are the whole gap.

**Other findings for the re-mint.**
- AC1's registry change also turns red two tests outside the Surface:
  `tests/unit/test_retrofit_flags.py::test_the_manifest_inventory_switch_unregisters_its_pipeline` asserts the
  `universal_sbom` nodes sit inside `__default__` when the switch is on, and
  `tests/unit/orchestration/test_definitions_dryrun.py::test_every_node_of_the_default_pipeline_has_its_own_timeout`
  reads `__default__` only, not every registered pipeline (AC5 already names the second).
- No `SCHEDULED_JOBS` row, Phase-P op or the dependency-history job names an op of either excluded pipeline, so the
  Dagster jobs other than `bootstrap_data` are untouched by AC1.
- The AC2 run test needs runtime-param floors, and should say so, so that its "plain run" is not read as the default
  parameters.

**To unblock (operator or session owner):** widen this story's Boundary and Surface to add an AD-13 last-good copy
to the three core datasets, or mint a sibling fix story under CAP-64 for them and make AC3 depend on it.

**Preserved work (not in the tree):** the registry diff and the exploration harness with its logs are in the
session scratchpad, `story-34-14/` beside `briefs/` (`pipeline_registry.diff`,
`exploration_harness_test_plain_run_fresh_root.py`, `probe_*.log`, `run_*.log`, `run2_*.log`).

Commands (each run from the worktree root; exit codes read from `$?`):
- `pixi run --frozen -e pyforge-atlas python <scratch>/list_pipes.py`: exit 0 (12 pipelines plus `__default__`,
  97 nodes; `query_plane_cache` 1 node, `universal_sbom` 4).
- `pixi run --frozen -e pyforge-atlas pytest <harness> -x -s -q` with `EXPLORE_PROBE=1`, `EXPLORE_LIVE=0|1`: exit 0
  both (the probe reports, it does not assert).
- The same, run mode, `EXPLORE_LIVE=0|1`: exit 0 both; first without floors, `HollowVerificationSetError`; with floors,
  the run completed.
- The same, two-run mode, `EXPLORE_LIVE=1`, `EXPLORE_KEEP_CORE=0|1`: exit 0 both; run 2 `DatasetError` at
  `core_feedstock_outputs_raw` (0), run 2 completed with the stale markers written (1).
- The station suite, ruff, mypy and the spec's Verification commands were not run: no change is left to verify.

## Spec Change Log

- 2026-11-01: minted from the EGM audit's cluster ATL-K2 (ATL-M-D1, ATL-D-R2, ATL-D-C3), accepted by the operator on
  2026-11-01, as a fix under CAP-64 with no new CAP and no flag; it closes `DW-atlas-37-2-1`.
- 2026-11-01 (amended): status `blocked` back to `in-progress` by the session owner's ruling of 2026-11-01. AC3 moves
  to the new sibling Story 34.15 under CAP-64 (FR-72), "the three core sources keep last-good when the network is
  refused" (`spec-34-15-the-three-core-sources-keep-last-good-when-the-network-is-refused.md`); AC2 states that its run test lowers the `verification_sets` floors through runtime params; the
  Surface adds `src/shared/packages/pyforge-atlas/tests/unit/test_retrofit_flags.py`, which the registry change
  breaks. No AC body was rewritten; each amendment is appended to its line.
- 2026-11-01: built; status `in-progress` -> `in-review` (Auto Run Result above). AC5's budget for
  `report_catalog_index_health` is recorded there.

## Review Triage Log

- 2026-11-01 (independent reviewer): **pass**; status `in-review` -> `done`. Judged against this spec's ACs and
  Boundaries, from `git diff HEAD` of `pipeline_registry.py`, `orchestration/definitions.py`,
  `test_pipeline_inventory.py`, `test_definitions_dryrun.py`, `test_retrofit_flags.py` and the new
  `tests/integration/test_plain_run_fresh_root.py` read in full; the Auto Run Result was not taken as evidence.
  - AC1: `NAMED_RUN_ONLY_PIPELINES = ("query_plane_cache", "universal_sbom")` beside `AFTER_RUN_PIPELINES`;
    `register_pipelines()` leaves both tuples out of `__default__`. `test_a_plain_run_leaves_out_what_the_bootstrap_task_leaves_out`
    parses the `pyforge-atlas-bootstrap` task's `--pipelines` list from `pixi.toml` and pins the tuple to what it
    leaves out (`catalog_index` aside), each still registered with nodes (switch on) and outside `__default__`. Met.
  - AC2: the integration test runs `__default__` over an empty root, live off and on, recorded bodies only, every
    other request and every subprocess refused, the socket guard on; floors lowered by runtime params as the
    amendment says; asserts `pypi_intelligence_scored` and the three vulnerability feeds. Met ("exits 0" read as
    `session.run()` returning, which is what `kedro run` turns into exit 0).
  - AC3: moved to Story 34.15 by the session owner's ruling; not judged here.
  - AC4: both pipelines stay registered with nodes (the AC1 test and the retrofit test); the named runs were not
    executed, which the AC does not require. Met.
  - AC5: `test_the_bootstrap_job_carries_no_op_of_a_pipeline_a_run_must_name` checks `bootstrap_data`'s ops; the
    timeout test now reads every registered pipeline; `report_catalog_index_health: 300` is the budget that reading
    requires (`catalog_index` is registered). Met.
  - AC6: reviewer's own in-memory mutations (a scratch `-p` pytest plugin; the tree was never edited): the tuple
    without `query_plane_cache` fails the AC1 test and all four integration cases (`query_plane_estate_source`
    FileNotFoundError), exit 1; an empty tuple also fails the AC5 bootstrap-job test, exit 1. Met.
  - AC7: `DW-atlas-37-2-1` reads `status: closed` with a `resolved:` line naming this story; `deferred-work-check`
    exit 0; `TMPDIR=$HOME/.cache/pyforge-preflight-tmp pixi run --frozen -e pyforge-atlas pyforge-atlas-test` exit 0
    (3316 passed, 17 skipped / 221 passed, 1 skipped / 103 passed). Met.
  - Boundaries: the `pyforge-atlas-bootstrap` task is unchanged (the `pixi.toml` diff in the tree is steward Story
    118.6's); nothing unregistered; no flag, no CAP; `query_plane_estate_source` not produced.
  - Commands, exit codes read from `$?`: the Verification pytest pair plus `test_retrofit_flags.py`,
    `test_vizro_static_boards.py` and the two core-source files: exit 0 (167 passed); the integration file: exit 0
    (4 passed); `kedro-catalog-check`: exit 0 (71 passed); package ruff over the touched files (`ruff check`,
    `ruff format --check`, from the package dir): exit 0 / exit 0; `pixi run --frozen -e pyforge-guild python
    scripts/lint_types.py ruff`: exit 0; `pixi run --frozen -e pyforge-guild lint-types`: exit 0 (atlas mypy ok);
    touched-module coverage `pipeline_registry.py` 100.0%, `orchestration/definitions.py` 90.4%.
  - Failures: none.
  - Observation, not this story's (untouched files, outside `lint_types.py`'s scope): a whole-package `ruff check .`
    from the package dir reports I001 in `tools/lasuite_bringup.py` and `tools/live_artifactory_transport.py`, and
    `ruff format --check .` would reformat `tools/lasuite_bringup.py` and `wasm/build.py`. The epics Status line and
    the ledger key still read `in-progress`; the session owner promotes them.
