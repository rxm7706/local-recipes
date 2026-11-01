---
title: "34.14: A plain run on a fresh data root exits 0"
type: 'fix'
created: '2026-11-01'
status: 'backlog'
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
  fetch refused.
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
  `vulnerability_epss_raw`, `vulnerability_cwe_catalog_raw`).
- **AC3 — Network blocked keeps last-good.** A second run over the root AC2 filled, with every fetch refused, exits 0
  and every public store AC2 filled keeps its last-good file under its AD-13 `stale` marker.
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
  `src/shared/packages/pyforge-atlas/tests/integration/test_plain_run_fresh_root.py` (new).
- Minted 2026-11-01 by the EGM fleet audit (marshal Story 113.7); built later through `marshal factory dispatch`.
  That PR reconciles spec-surface on `spec-pyforge-atlas` and its co-governor `spec-pyforge-core`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-atlas pyforge-atlas-test` — expected: pass (the station's `verify_commands`; AC7).
- `pixi run --frozen -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests/unit/test_pipeline_inventory.py src/shared/packages/pyforge-atlas/tests/unit/orchestration/test_definitions_dryrun.py -q` — expected: pass (AC1, AC5).
- `pixi run --frozen -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests/integration/test_plain_run_fresh_root.py -q` — expected: pass (AC2, AC3).
- `pixi run --frozen -e pyforge-atlas kedro-catalog-check` — expected: pass.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Run before the push:** AC6's mutation (put `query_plane_cache` back into `__default__`) and the two named test files
fail; revert.

## Auto Run Result

Status: backlog (minted 2026-11-01 by the EGM fleet audit, marshal Story 113.7).

## Spec Change Log

- 2026-11-01: minted from the EGM audit's cluster ATL-K2 (ATL-M-D1, ATL-D-R2, ATL-D-C3), accepted by the operator on
  2026-11-01, as a fix under CAP-64 with no new CAP and no flag; it closes `DW-atlas-37-2-1`.

## Review Triage Log

- (none yet)
