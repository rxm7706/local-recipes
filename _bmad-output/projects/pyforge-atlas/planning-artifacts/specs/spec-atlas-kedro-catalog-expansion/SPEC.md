---
spec: atlas-kedro-catalog-expansion
status: shipped   # 2026-09-09 (operator, batch § 2.2 row atlas-B5), was `ready` and untouched since
                  # authoring: Epics 21, 22 and 23 are 100% `done` in `sprint-status-ledger.yaml`
                  # and CAP-1..CAP-8 are decomposed, landed and gated. The owner Dream deliberately
                  # HOLDS at `specified` — see § Dream holds at `specified`.
updated: "2026-09-09"
owner-station: pyforge-atlas
owner-dream: docs/dreams/atlas-kedro-catalog-expansion.md
surface:
  - src/shared/packages/pyforge-atlas/conf/base/catalog.yml
  - src/shared/packages/pyforge-atlas/conf/base/globals.yml
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/**
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/upstream_discovery/**
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/pypi_intelligence/**
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/core/**
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/**
  - .github/workflows/kedro-viz-publish.yml
  - pixi.toml
companions:
  - catalog-sources.md
  - identity-contract.md
  - verification-matrix.md
  - architecture-diagrams.md
  - operator-surfaces.md
  - vizro-canvas-parity.md
  - complete-export-contract.md
  - ../catalog-contract.md
  - ../spec-conda-forge-packaging-inventory-operations/SPEC.md
sources:
  - ../../../../../../docs/dreams/atlas-kedro-catalog-expansion.md
open_questions: []   # ANSWERED BY DELIVERY 2026-09-09 (readiness § C-4). (1) CDO-ENT-JFROG
                     # universe names — answered at Story 21.5 (`done`): `project_artifactory_names`
                     # ships the Tier-2 names-only projection and degrades to an empty frame
                     # carrying the names-only schema when the upstream columns are absent;
                     # telemetry columns stay inventory-side, as recommended. (2) The
                     # conda-forge.org/packages scrape — the recommended path was taken and nothing
                     # proved it insufficient: `core_feedstock_attribution` is a live catalog
                     # dataset and the feedstock-name join source, and `catalog-sources.md:40`
                     # already records the scrape as `deferred` with that rationale.
---

# SPEC — Atlas Kedro catalog expansion (self-contained + inventory-aligned)

## Why

Pyforge-atlas runs a declarative Kedro catalog, but Kedro still seeds from
`cf_atlas.db`, defaults stores to `.claude/data/conda-forge-expert/`, and
duplicates live-index fetches the inventory quartet performs for PyPI,
conda-forge, assurance lists, and identity. Operators proved the combined path
(legacy bootstrap + seven pipelines) on 2026-08-29; steady-state requires one
catalog-owned data plane the inventory quartet consumes via `--live-catalog`,
without Excel tabs or parallel HTTP clients for public verification. **Station:
pyforge-atlas** owns catalog, pipelines, and the extended `upstream_discovery`
identity join; the inventory quartet thins to ranking and enterprise overlays.

## Capabilities

- **CAP-1 — Kedro self-containment (Phases A–B).**
  - **intent:** A fresh clone runs the documented Kedro bootstrap on
    `PYFORGE_ATLAS_DATA_ROOT` without `CF_ATLAS_DB` or legacy `.claude/data/`
    on the Kedro path.
  - **success:** `pixi run pyforge-atlas-bootstrap` completes green; production
    dataset code has no default to `cf_atlas.db`; vdb/OSV/mapping stores live
    under `${paths.data_root}/stores/`; `parity-diff` and `bsl-metric-check`
    pass.
  - **verified:** a real `pixi run -e pyforge-atlas pyforge-atlas-bootstrap`
    (2026-09-11) completed 75/75 tasks in 201.8s with no `CF_ATLAS_DB`/legacy
    `.claude/data/` on the path, materializing real live Tier-0/1 data under
    `PYFORGE_ATLAS_DATA_ROOT` (`pypi_universe` 889,433 rows,
    `core_feedstock_attribution` 32,998 rows); `parity-diff` (71 tests) and
    `bsl-metric-check` (16 tests) both green. Credentialed-only nodes
    (Artifactory/JFrog) correctly degraded to empty per AD-13, not a failure —
    see CAP-8's verified line.

- **CAP-2 — Public index catalog completeness (Phase C, Tier 0–2).**
  - **intent:** Every live source the inventory verification matrix needs is
    declared in `catalog.yml`, fetched at the dataset layer, and materialized
    as Parquet the metrics runner reads directly.
  - **success:** `conda-forge-packaging-inventory-operations_metrics.py
    --live-catalog` produces matching `PyPI_Verified`, `CondaForge_Verified`,
    Basilisk/AOSS/Anaconda/cross-channel columns from Parquet alone; scale
    sanity gates fail loudly below order-of-magnitude floors (conda-forge ~30k+).
  - **verified:** the ~30k+ conda-forge scale floor is cleared for real by
    CAP-1's live bootstrap run (`core_feedstock_attribution` 32,998 rows, not
    a fixture); `kedro-catalog-check` (67 tests, incl.
    `tests/unit/catalog/test_scale_floors.py`'s below-floor-raises assertions)
    green; `--live-catalog` metrics-script behavior live in
    `scripts/tests/test_conda_forge_packaging_inventory_operations_metrics.py`
    (10 tests, incl. `test_live_catalog_formats_csv_md_and_queue_from_exports`).
    A live `--live-catalog` invocation against this run's own fresh exports
    was not independently re-run in this pass.

- **CAP-3 — Identity join in `upstream_discovery` (Phase D).**
  - **intent:** PURL Associator ingest, OpenTeams project 1 board ingest,
    feedstock/staged-PR/local-recipe overlays, and identity export Parquet
    replace parallel HTTP/GraphQL in `..._openteams_identity.py`.
  - **success:** Export rows match today's `GIST_SCHEMA` identity columns and
    `lookup_assoc` / `from_inventory` / `from_board_only` parity on a fixed
    fixture corpus; gist publish reads export + merges ranking from
    `priority.py` at publish time.
  - **verified:** `build_identity_packages_primary` (PURL Associator +
    OpenTeams board + feedstock/staged-PR/local-recipe overlays) and
    `build_identity_export_parquet` (docstring: "CAP-3 — GIST_SCHEMA-shaped
    export, Story 21.6") in `pipelines/upstream_discovery/nodes.py`; live in
    `tests/unit/pipelines/upstream_discovery/test_nodes.py` +
    `test_identity_parity_fixtures.py` (258 tests green, shared suite with
    `spec-upstream-discovery`'s CAP-2, 2026-09-11); CAP-1's live bootstrap run
    also materialized real `identity_packages_primary` output end-to-end.

- **CAP-4 — Quartet consumes Atlas exports (thin orchestration).**
  - **intent:** Inventory scripts stop owning public-index fetch and identity
    join; they orchestrate ranking, enterprise JFROG telemetry, dashboard
    canvases, and optional OpenTeams issue creation.
  - **success:** Metrics and identity scripts have no direct fetch to public
    verification endpoints when `--live-catalog` is set; Epic 17 constraint
    (purl-associator stays in quartet) is superseded in inventory spec with a
    dated memlog cross-reference.
  - **verified:** the quartet went further than this CAP's own ask — Story
    23.9 fully RETIRED the direct-fetch path (not merely made it optional):
    `conda-forge-packaging-inventory-operations_metrics.py`'s old flag now
    "exits 2 with a pointer to --live-catalog"; `--live-catalog` is the only
    live path, live in
    `scripts/tests/test_conda_forge_packaging_inventory_operations_metrics.py`
    (10 tests green).

- **CAP-5 — Bootstrap operator Vizro pages (optional follow-on, Story 21.9).**
  - **intent:** After bootstrap, operators inspect index health, identity
    export quality, and live-catalog verification coverage in the existing Vizro
    dashboard — BSL measures over catalog Parquet only.
  - **success:** Three new pages (`bootstrap-index-health`,
    `identity-export-snapshot`, `live-catalog-coverage`) render non-empty tables
    post-bootstrap; `dashboard-dryrun` includes them; no duplicate HTTP fetch in
    dashboard loaders.
  - **verified:** all three pages present in `dashboard/app.py`'s
    `PAGE_INVENTORY` with wired loaders (`build_bootstrap_index_health_model`,
    `build_identity_export_snapshot_model`, `build_live_catalog_coverage_model`);
    `pixi run -e local-recipes dashboard-dryrun` green (72 tests, 2026-09-11,
    same run as `spec-atlas-query-dashboards` CAP-7) covers the full page
    inventory including these three; whole-package no-inline-IO gate
    (`tests/unit/catalog/test_no_inline_io.py`, part of the 67-test
    `kedro-catalog-check`) covers the dashboard loaders structurally.

- **CAP-6 — Kedro-Viz publish stays in sync (optional follow-on, Story 21.10).**
  - **intent:** Static Kedro-Viz export republishes when catalog or dataset
    code changes, not only pipeline Python edits.
  - **success:** `kedro-viz-publish.yml` triggers on `catalog.yml`, `globals.yml`,
    and `datasets/**`; merged catalog-only PR updates `docs/dashboard/kedro-viz/`.
  - **verified:** `.github/workflows/kedro-viz-publish.yml`'s `on.push.paths`
    literally lists all three (plus `pipelines/**`, a superset); `docs/dashboard/kedro-viz/`
    exists and carries a real prior publish (`6a1ba53a134`, 2026-08-15, via
    `steward deploy dashboard`). By config inspection, not a live CI trigger
    test — the GH Actions billing outage active this session (2026-09-11)
    means the workflow cannot be fired to prove the catalog-only path
    specifically, as distinct from a pipeline-code-change path.

- **CAP-7 — Vizro parity with identity canvases (Epic 22 follow-on).**
  - **intent:** Vizro becomes a **parallel replacement** for the three Cursor
    Canvas identity views (catalog, ops, workbook) — same ranked data, browser
    operator surface; canvases stay until parity is proven.
  - **success:** Three Vizro pages (`identity-catalog`, `identity-ops`,
    `identity-workbook`) match canvas/gist aggregates on a shared fixture;
    ranked export feeds Vizro (quartet `identity_ranked_export` until Epic 23.5,
    then `identity_complete_export.parquet` from Atlas); parity gate in
    `dashboard-dryrun`; canvas deprecation deferred to Story 22.6.
  - **verified:** all three pages' parity against the canvas/gist aggregates on
    a shared fixture live in
    `tests/integration/dashboard/test_identity_parity.py`
    (`test_identity_catalog_matches_write_canvas_on_shared_fixture`,
    `test_identity_ops_pane_totals_match_write_ops_canvas_on_shared_fixture`,
    `test_identity_workbook_both_sides_degrade_honestly_on_same_fixture`) +
    per-page tests (`test_identity_catalog_page.py`, `test_identity_ops_page.py`,
    `test_identity_workbook_page.py`); 24 tests green (2026-09-11); part of the
    same `dashboard-dryrun` 72-test gate cited on CAP-5/6 above.
  - **explicitly deferred within CAP-7:** enterprise JFROG workbook parity until
    Epic 23.2 enterprise Parquet exists (19.4 shell OK); gist generator replacement
    until CAP-8d (Epic 23.6); full UX port; canvas writer removal before 22.5 gate.

- **CAP-8 — Complete inventory export, zero deferred (Epic 23 closure).**
  - **intent:** Close the dream with **no data slices left in `scripts/`** —
    Tier 3 OS indexes, enterprise JFROG telemetry, priority assignment,
    `Packaging_Candidate_Status`, deliverable A, and gist/dashboard aggregates
    all materialize as Kedro Parquet under `PYFORGE_ATLAS_DATA_ROOT`; one canonical
    `identity_complete_export.parquet` supersedes quartet merge passes.
  - **success:** Enterprise builds `enterprise_jfrog_consumption.parquet` per
    `complete-export-contract.md`; bootstrap produces complete export; parity vs
    frozen inventory corpus; BSL gist markdown matches today's gist files; Epic 22
    reads complete export only; `--live-catalog` / `--gist-only` are thin actuators.
  - **verified:** the CAP-1 live bootstrap run (2026-09-11) DOES produce both
    named Parquets end-to-end — `identity_complete_export` and
    `enterprise_jfrog_consumption` both build cleanly (node
    `build_identity_complete_export`, 75/75 tasks) — but **both are 0 rows**,
    confirming (not contradicting) this Spec's own recorded "Dream holds at
    `specified`" gap: the schema/pipeline machinery is real and green, but
    Story 25.2's attended, credentialed Artifactory run — the thing that would
    put real rows in these two files — genuinely has not happened, exactly as
    already documented above. Everything NOT gated on that credential is
    green: contract-shape/thin-actuator/zero-ranked-export-reference tests in
    `tests/unit/pipelines/derived_artifacts/test_identity_complete_export.py`
    + `tests/integration/dashboard/test_zero_deferred_e2e_gate.py` (19 tests,
    incl. `test_dashboard_constant_points_at_complete_export`); gist-markdown
    parity in `tests/unit/test_dashboard_identity_gist.py` +
    `tests/integration/dashboard/test_identity_gist_markdown.py` (54 tests,
    incl. `test_bsl_dashboard_counts_match_legacy_on_fixture`).
  - **enterprise handoff:** Story 23.2 column contract is the build target for
    [[artifactory-download-intelligence]] live bring-up — see companion §1.
  - **workbook retirement (added 2026-08-30 course correction):** the inventory
    quartet no longer needs `docs/Analysis_Dataset-2026-08-12.xlsx` at any step —
    Story 23.8 lands the `inventory_universe` Parquet (the ~38k full-inventory row
    grain with the workbook's provenance labels) and makes `--analysis-xlsx`
    optional; Story 23.9 removes every workbook code path (`openpyxl` absent from
    `scripts/`); Story 23.7 gates both the bootstrap and the quartet on zero
    `.xlsx` reads. See companion §9.

## Constraints

- **AD-2:** fetch/parse/rate-limit/fallback in `pyforge.atlas.datasets.*`; nodes
  are `DataFrame → DataFrame`.
- **AD-13:** last-good Parquet + staleness marker; never silent SQLite fallback.
- **Phase D extends `upstream_discovery` only** — no 9th pipeline.
- **Tier 1 split:** SelfExplainML + Anaconda main/dist → `core` /
  `pypi_intelligence`; Basilisk packages + AOSS + about + curated orgs →
  `upstream_discovery`.
- **`PYFORGE_ATLAS_DATA_ROOT` default:** member
  `src/shared/packages/pyforge-atlas/data/`; env override documented.
- **Bootstrap entry:** pixi task `pyforge-atlas-bootstrap` (CLI subcommand optional
  later).
- **Associator:** `mappings-index.json` required; per-package shards on demand;
  full bundle opt-in air-gap seed ([prefix-dev/purl-associator](https://github.com/prefix-dev/purl-associator)
  Pages payload is canonical).
- **Parselmouth** remains the conda↔PyPI **name** map (`pypi_conda_mapping`);
  PURL Associator is **upstream identity** — distinct surfaces, both cataloged.
- **Enterprise JFROG telemetry** (`risk_level`, `platform_env_count`, …) stays
  inventory-only through Epic 21; Epic 23.2 moves it to
  `enterprise_jfrog_consumption.parquet` (Tier 2 names-only in 18.5 is the bridge).
- **Ranking (`P`/`Score`/`Work`)** stays in quartet through Epic 21; Epic 23.3
  ports rules to Kedro nodes. **`--create-issues`** optional — not required for
  CAP-8 data closure.
- **Legacy coexistence:** do not retire `bootstrap-data`, `cf_atlas.db`, or CFE
  atlas CLIs.
- **`kedro-catalog-check` stays green:** typed datasets only; AD-14 parity for
  additive signals.

## Non-goals

- Tier 3 bulk OS indexes in Epic 21 v1 — deferred to **Epic 23.1** (CAP-8).
- Excel workbook ingest or mirror — Kedro never reads the workbook and no catalog
  entry mirrors a sheet. (Clarified 2026-08-30: *retiring* the quartet's own
  workbook inputs IS in scope — Stories 23.8/23.9; the `10kClosed` sheet has no
  upstream and is reported as a delta, not seeded.)
- `universal_sbom` in the default bootstrap chain.
- OpenTeams issue creation inside Atlas.
- Retiring legacy atlas or conda-forge-expert tooling.
- Duplicating inventory ranking logic in Kedro nodes **during Epic 21** — Epic 23.3
  intentionally ports `priority.py` rules once.
- **Deprecating Cursor Canvas during Epic 21** — CAP-7 / Epic 22 targets parallel
  Vizro replacement after parity gate; canvas writers stay until Story 22.6.
- **Core Epic 21 (21.1–21.8) does not add Vizro pages** — CAP-5 / Story 21.9 is
  optional follow-on after 18.8 is green.

## Success signal

On a machine with no `CF_ATLAS_DB` on the Kedro path: `pixi run
pyforge-atlas-bootstrap` materializes Tier-0/1 indexes; inventory metrics with
`--live-catalog` matches live verification columns from Parquet; identity export
passes associator/board join parity; `parity-diff` / `bsl-metric-check` pass;
gist publish succeeds via export + priority merge without re-fetching public
indexes.

Optional follow-on (CAP-5/6): `dashboard-serve` shows bootstrap/identity/coverage
pages; Kedro-Viz CI republishes on catalog-only merges.

Epic 22 (CAP-7): Vizro pages reach parity with the three identity canvases;
ranking + enterprise columns + gist handoff + UX polish bridge via quartet until
Epic 23 — not because Vizro cannot, because Epic 21 scoped public data first.

Epic 23 (CAP-8): Dream fully closed — `identity_complete_export.parquet` +
`complete-export-contract.md`; no deferred data slices; enterprise builds §1
`enterprise_jfrog_consumption.parquet` to close JFROG workbook + ranking inputs.

## Assumptions

- Attended GitHub credentials exist for OpenTeams GraphQL and gist publish; CI
  uses fixtures and `--skip-gist`.
- CDO consumption universe **names** can be supplied from catalog Tier 2; full
  telemetry columns remain workbook/inventory-sourced until an enterprise spec
  moves them.
- Feedstock URLs derive from `core_feedstock_attribution` Parquet without a v1
  `conda-forge.org/packages` scrape.

## Dream holds at `specified` — 2026-09-09

This Spec is `shipped`; the owner Dream `docs/dreams/atlas-kedro-catalog-expansion.md` **does not
follow it to a terminal state** (batch § 2.2 row atlas-B5). It holds at `specified` until one
recorded run materializes BOTH `identity_complete_export.parquet` and
`enterprise_jfrog_consumption.parquet`. A declared Kedro dataset (`conf/base/catalog.yml:987-989`,
`:1301-1303`) is a contract, not data — moving both together would set the precedent that a data
Dream is `realized` before any data exists, the exact pathology the realization gate was written
for. Splitting Spec-status from Dream-status is the shape `spec-wagtail-corporate-brain` already
uses successfully.

**Effect story:** atlas **Story 25.2**, "Materialize CAP-8's canonical Parquets — one recorded
run", under the new **Epic 25** (batch § 2.3 C6). It is seeded `blocked` because it needs the
ATTENDED, credentialed Artifactory path that `spec-conda-forge-packaging-inventory-operations` also
waits on ("CAP-2 (17.2) code landed, live-execution verification deferred — attended, credentialed
run pending"). **Two Specs, one precondition**: they must not disagree about whether it has been
met. Recorded here as prose, deliberately NOT as a cross-project `Deps:` token. Closing 25.2 is
what moves the owner Dream to `realized`.
