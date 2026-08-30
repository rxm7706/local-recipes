---
spec: atlas-kedro-catalog-expansion
status: ready
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
open_questions:
  - "CDO-ENT-JFROG universe names via artifactory_downloads live fetch — confirm attended credential path before Story 21.5 lands telemetry-as-names-only contract."
  - "conda-forge.org/packages scrape — defer unless core_feedstock_attribution Parquet proves insufficient in 18.6 parity review."
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

- **CAP-2 — Public index catalog completeness (Phase C, Tier 0–2).**
  - **intent:** Every live source the inventory verification matrix needs is
    declared in `catalog.yml`, fetched at the dataset layer, and materialized
    as Parquet the metrics runner reads directly.
  - **success:** `conda-forge-packaging-inventory-operations_metrics.py
    --live-catalog` produces matching `PyPI_Verified`, `CondaForge_Verified`,
    Basilisk/AOSS/Anaconda/cross-channel columns from Parquet alone; scale
    sanity gates fail loudly below order-of-magnitude floors (conda-forge ~30k+).

- **CAP-3 — Identity join in `upstream_discovery` (Phase D).**
  - **intent:** PURL Associator ingest, OpenTeams project 1 board ingest,
    feedstock/staged-PR/local-recipe overlays, and identity export Parquet
    replace parallel HTTP/GraphQL in `..._openteams_identity.py`.
  - **success:** Export rows match today's `GIST_SCHEMA` identity columns and
    `lookup_assoc` / `from_inventory` / `from_board_only` parity on a fixed
    fixture corpus; gist publish reads export + merges ranking from
    `priority.py` at publish time.

- **CAP-4 — Quartet consumes Atlas exports (thin orchestration).**
  - **intent:** Inventory scripts stop owning public-index fetch and identity
    join; they orchestrate ranking, enterprise JFROG telemetry, dashboard
    canvases, and optional OpenTeams issue creation.
  - **success:** Metrics and identity scripts have no direct fetch to public
    verification endpoints when `--live-catalog` is set; Epic 17 constraint
    (purl-associator stays in quartet) is superseded in inventory spec with a
    dated memlog cross-reference.

- **CAP-5 — Bootstrap operator Vizro pages (optional follow-on, Story 21.9).**
  - **intent:** After bootstrap, operators inspect index health, identity
    export quality, and live-catalog verification coverage in the existing Vizro
    dashboard — BSL measures over catalog Parquet only.
  - **success:** Three new pages (`bootstrap-index-health`,
    `identity-export-snapshot`, `live-catalog-coverage`) render non-empty tables
    post-bootstrap; `dashboard-dryrun` includes them; no duplicate HTTP fetch in
    dashboard loaders.

- **CAP-6 — Kedro-Viz publish stays in sync (optional follow-on, Story 21.10).**
  - **intent:** Static Kedro-Viz export republishes when catalog or dataset
    code changes, not only pipeline Python edits.
  - **success:** `kedro-viz-publish.yml` triggers on `catalog.yml`, `globals.yml`,
    and `datasets/**`; merged catalog-only PR updates `docs/dashboard/kedro-viz/`.

- **CAP-7 — Vizro parity with identity canvases (Epic 22 follow-on).**
  - **intent:** Vizro becomes a **parallel replacement** for the three Cursor
    Canvas identity views (catalog, ops, workbook) — same ranked data, browser
    operator surface; canvases stay until parity is proven.
  - **success:** Three Vizro pages (`identity-catalog`, `identity-ops`,
    `identity-workbook`) match canvas/gist aggregates on a shared fixture;
    ranked export feeds Vizro (quartet `identity_ranked_export` until Epic 23.5,
    then `identity_complete_export.parquet` from Atlas); parity gate in
    `dashboard-dryrun`; canvas deprecation deferred to Story 22.6.
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
