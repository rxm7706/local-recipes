---
title: Expand the Atlas Kedro catalog so live indexes match the packaging inventory
type: dream
owner: atlas
status: specified
---

# Expand the Atlas Kedro catalog — self-contained, inventory-aligned

## The Dream

[[pyforge-atlas]] already runs a declarative Kedro catalog — conda-forge backbone,
PyPI intelligence, vulnerability overlays, VCS health, discovery tracks. The
[[conda-forge-packaging-inventory-operations]] dream runs a **separate** quartet
(live-endpoint verification + priority + OpenTeams handoff). Both need the **same
live indexes** for verification (PyPI yes/no, conda-forge yes/no, cross-channel
presence, Basilisk catalog, AOSS lists, Anaconda defaults). Today those indexes
are duplicated, partially implemented, or only reachable through one toolchain.
**The Excel workbook is out of scope for this dream** — catalog entries are live
fetches with AD-13 last-good Parquet; inventory orchestration consumes those outputs.

The dream has **four closure tracks**:

1. **Catalog completeness (Epic 21)** — one catalog surface: every live source the inventory
   dream depends on is declared in `conf/base/catalog.yml`, fetched at the **dataset**
   layer (AD-2 — nodes stay pure), routed through `${globals:…}` override points
   (AD-13), and materialized as Parquet the BSL, dashboard, and inventory quarter
   can all read. No second HTTP client in scripts for **public index verification**.

2. **Kedro self-containment (Epic 21)** — pyforge-atlas can run its **own** bootstrap chain
   (external-refresh stores + seven pipelines) on a **dedicated data root**, without
   requiring a prior legacy `bootstrap-data` run or reading `cf_atlas.db` at
   dataset load time. Legacy `cf_atlas` and conda-forge-expert **keep working in
   parallel** — this dream does not retire them; it removes the *dependency* so
   Kedro is not a passenger on the legacy store.

3. **Identity pipeline in Atlas (Epic 21 Phase D)** — re-implement the inventory quartet's PURL
   Associator join, OpenTeams project 1 board ingest, and identity gist publish
   as catalog sources + derived nodes in **`upstream_discovery`** (extended, not a
   9th pipeline). Inventory scripts become thin orchestrators over Parquet exports,
   not parallel HTTP/GraphQL clients.

4. **Complete export + zero deferred (Epic 23 / CAP-8)** — Tier 3 OS indexes, enterprise
   JFROG telemetry, priority assignment, deliverable A, and gist/dashboard aggregates
   all land as Kedro Parquet; **`identity_complete_export.parquet`** is the single
   canonical surface. See `complete-export-contract.md` — enterprise builds
   **`enterprise_jfrog_consumption.parquet`** (§1) to close the dream.

The 2026-08-29 admin bootstrap proved the **combined** path works (legacy store +
seven Kedro pipelines). Steady-state for Kedro is: catalog-owned fetch, one env-var
block, one atlas data root — with optional SQLite seed only as a documented
migration bridge, not the only path.

## From training wheels to self-contained (Kedro only)

Today’s Kedro coupling (documented after the bootstrap session):

| Training wheel | What it does today | Steady-state replacement |
|----------------|-------------------|-------------------------|
| `cf_atlas.db` seeds | `pypi_json_raw`, GitHub/VCS/registry datasets read SQLite at `load()` when live fetch is off | Upstream Parquet from prior pipeline outputs, or live fetch in the dataset |
| `globals.yml` defaults | `vdb_store`, `osv_offline_store`, `pypi_conda_map` default to `.claude/data/conda-forge-expert/…` | `${paths.data_root}/stores/…` under `PYFORGE_ATLAS_DATA_ROOT` |
| Legacy bootstrap prerequisite | Operators run `bootstrap-data` before Kedro chain | Kedro bootstrap runs B5 external-refresh + pipelines on its own data root |

Legacy `bootstrap-data`, `cf_atlas.db`, and conda-forge-expert atlas CLIs **remain
valid** — they are out of scope for this dream.

## The unified Kedro data plane

One atlas root — env-var overridable, gitignored, never committed:

```
${PYFORGE_ATLAS_DATA_ROOT}/     # default: forge-data/atlas/ or member data/
├── raw/                        # Kedro catalog layers (HTTP → Parquet)
├── primary/
├── derived/
├── stores/
│   ├── vdb/                    # VDBStoreDataset (B5 external-refresh)
│   ├── osv/                    # OSVOfflineStoreDataset
│   └── pypi_conda_map.json     # mapping cache
└── seeds/                      # air-gap fallbacks only (small, tracked where needed)
```

Sibling `data.locks/` (run-admission) stays **outside** the data tree (AD-23 /
DW-AD23-3).

Legacy `.claude/data/conda-forge-expert/` may still exist on the same machine for
recipe work — Kedro simply does not *require* it.

## Phased journey (for `bmad-spec` decomposition)

### Phase A — Relocate defaults (mechanical)

- Point `conf/base/globals.yml` `paths.vdb_store`, `osv_offline_store`,
  `pypi_conda_map` at `${paths.data_root}/stores/…`, not `.claude/data/…`.
- Document one operator env block; add a Kedro bootstrap entrypoint (pixi task or
  `pyforge-atlas bootstrap`) that runs B5 external-refresh + pipeline chain in
  dependency order.

### Phase B — Replace SQLite seeds (core)

For each `seed_*_from_cf_atlas()` / `_cf_atlas_db_path()` call site, pick one:

- **Upstream Parquet** — read a catalog dataset another pipeline already wrote.
- **Live fetch** — dataset-owned HTTP (KEV/EPSS/CWE pattern).
- **Credentialed opt-in** — GitHub GraphQL, BigQuery Phase P (`PYPI_JSON_LIVE_FANOUT`, etc.).
- **External-refresh** — vdb, OSV, mapping (already cataloged).

Degrade per AD-13 (last-good + staleness marker), never silent fallback to SQLite.
Add a catalog gate: production dataset code must not default to
`.claude/data/conda-forge-expert/cf_atlas.db`.

### Phase C — Catalog expansion (Tier 1–3 below)

Fill fetch gaps so inventory verification and factory channels use **live catalog
outputs only** (no spreadsheet tabs as index sources).

### Phase D — Identity join in `upstream_discovery` (PURL Associator + OpenTeams + gist)

- **Source datasets:** `purl_associator_mappings_raw` (prefix-dev
  `mappings-index.json` + optional full bundle / per-package shards; AD-13
  last-good); `openteams_project_1_board_raw` (credentialed GitHub GraphQL —
  full project 1, **not** the OSS-milestone slice; same query shape as today's
  `fetch_project_issues`).
- **Derived node(s):** join inventory universe (`CDO-ENT-JFROG` ∪ `CDO-ENT-CONDA`
  from catalog Parquet) with associator index (`lookup_assoc` PEP 503 keys +
  `-`/`.`/`_` alias fallbacks); fallback to inventory-derived PURLs when
  unmapped (`PyPI_PURL` + `git_purl(Source_Repository_URL)`); board-only extras
  for packaging issues not in inventory. Output columns match today's
  `GIST_SCHEMA` / identity tab contract (`identity_source`, `associator_key`,
  `associator_status`, `primary_purl`, `primary_type`, `alternative_purls`,
  `cpes`, `conda_purl`, `source_repository_url`, `OpenTeams_Issue_URL`, …).
- **Overlay inputs (read Parquet or small tracked seeds):** feedstock-outputs map,
  staged-recipes PR map, `recipes/` local build overlay — same semantics as
  `attach_packaging_urls` / `overlay_live_local`.
- **Export target:** `identity_gist_publish` — credentialed dataset or post-pipeline
  actuator editing the pinned secret gist in place (`OPENTEAMS_IDENTITY_GIST_ID`;
  never committed): `mgmt-wf-python-modernization-identity.md` +
  `mgmt-wf-python-modernization-dashboards.md`. Ranking columns (`P`, `Score`,
  `Work`) are merged at publish time from the inventory priority pass — the join
  logic lives in Atlas; the ranking rules stay in `priority.py` until a later dream
  moves them.

## What it looks like when real

- **Cross-channel presence is complete for the factory's channels**, not just
  bioconda / pytorch / nvidia / robostack: **SelfExplainML** joins Phase Q-style
  bulk repodata (`in_selfexplainml` beside the existing four BOOLs).
- **Basilisk is two catalog entries, one override**: vuln advisories
  (`vulnerability_basilisk_*`, already shipped) **and** the **package catalog**
  (`GET /v1/packages`) — the dream's Basilisk tab and the HTML SPA are never
  the only source of truth.
- **Anaconda defaults are first-class**: `repo.anaconda.com/pkgs/main/channeldata.json`
  and the **Anaconda Distribution 2026.x** release list are cataloged beside
  conda-forge `core_channeldata_raw`.
- **Google AOSS free and premium** Python supported-package lists are catalog
  raw sources; premium ⊃ free; the **AOSS-Free Mason queue** (PyPI-yes,
  conda-forge-no, not in CDO consumption) derives from catalog Parquet, not a
  one-off script parse.
- **Discovery signals share the catalog**: maintainer feedstocks from
  [rxm7706/about](https://github.com/rxm7706/about), live curated-org sweeps,
  and Basilisk/AOSS frames land in **`upstream_discovery`** (or a sibling
  **`discovery`** pipeline) — not ad-hoc fetches inside
  `conda-forge-packaging-inventory-operations_metrics.py`.
- **Inventory quartet thins to orchestration**: priority / Score / Work assignment
  (`priority.py`) and enterprise-only consumption overlays (CDO JFROG fields)
  stay in the quartet for now. **Identity** (PURL Associator join, OpenTeams board
  ingest, gist publish, three dashboard canvases) **moves to Atlas Phase D**.
  **Live verification** (PyPI, conda-forge, Basilisk, AOSS, Anaconda,
  cross-channel, VCS URLs) **reads Kedro Parquet** via `--live-catalog`.
- **`kedro-catalog-check` and parity discipline stay green**: new entries get
  typed datasets (never bare `api.APIDataset` returning `Response` objects);
  new-signal datasets follow AD-14 (explicit parity scope for additive signals).
- **A fresh clone** runs the documented Kedro bootstrap, materializes Tier-1 +
  core pipeline outputs under `PYFORGE_ATLAS_DATA_ROOT`, and passes
  `parity-diff` / `bsl-metric-check` **without** `CF_ATLAS_DB` set.

## Sources to catalog (priority order)

### Tier 1 — explicit gaps from the 2026-08-29 bootstrap resume

| Source | Endpoint / pattern | Target pipeline | Notes |
|--------|-------------------|-----------------|-------|
| SelfExplainML channel | `conda.anaconda.org/SelfExplainML/.../repodata.json` | `pypi_intelligence` | Factory channel; extend `CrossChannelRepodataDataset` |
| Anaconda main | `repo.anaconda.com/pkgs/main/channeldata.json` | `core` or `pypi_intelligence` | Same parser family as `core_channeldata_raw` |
| Basilisk package catalog | `GET {BASILISK_BASE_URL}/v1/packages` | `upstream_discovery` or new `discovery` | Distinct from `vulnerability_basilisk_*` |
| Google AOSS free | supported-packages doc (Python) | `discovery` | Git-tracked fallback seed for air-gap |
| Google AOSS premium | premium doc or Wayback snapshot | `discovery` | Set-diff vs free in node |
| Anaconda Distribution 2026.x | release-doc package list | `core` or `discovery` | Version the fetcher; brittle HTML |

Cross-channel **bioconda / pytorch / nvidia / robostack** already flows through
`pypi_cross_channel_repodata_raw` — Tier 1 here is **hardening** (subdir +
`repodata.json` fallback, tests, offline last-good), not a new source.

### Tier 0 — already cataloged; inventory-critical (harden + document)

These exist in `catalog.yml` today but must be **live-first** after Phase B and
named in the `--live-catalog` contract:

| Source | Catalog entry | Inventory use |
|--------|---------------|---------------|
| conda-forge channeldata | `core_channeldata_raw` | `CondaForge_Verified` (~tens of thousands of packages; tens = fetch bug) |
| PyPI simple index | `pypi_simple_index_raw` | `PyPI_Verified` |
| PyPI project JSON | `pypi_json_raw` | `PyPI_Verified`, `Source_Repository_URL` via `project_urls` |
| Parselmouth mapping | `pypi_conda_map_store` | CondaForge Yes when PyPI name ≠ conda name |
| conda-forge channeldata URLs | `core_*` derived | `dev_url` / git-like `home` for VCS derivation |
| PURL Associator index | `purl_associator_mappings_raw` | `primary_purl`, `alternative_purls`, `cpes`, `associator_*` |
| OpenTeams project 1 board | `openteams_project_1_board_raw` | `OpenTeams_Issue_URL`, board-only identity rows, P1–P3 preservation inputs |

### Tier 2 — inventory live-index alignment

| Source | Role |
|--------|------|
| `rxm7706/about` maintained feedstocks | Maintainer/co-maintainer universe (`CDO-ENT-CONDA` semantics live) |
| Curated org repo sweeps | Live org pages: Apache, Django, LF AI & Data, NumFOCUS, Jazzband, FINOS, PSF, PyPA, Trendshift, Google, Microsoft, Kedro, BMAD (+ configurable list in `curated_groups.json` as air-gap seed only) |
| Artifactory / CDO consumption | [[artifactory-download-intelligence]] live endpoint for JFROG universe names (enterprise fields stay in inventory scripts) |
| `conda-forge.org/packages` (optional) | Feedstock/metadata URL enrichment for identity handoff — catalog or documented inventory overlay |

### Tier 3 — bulk-index stretch (Epic 23.1; deferred from Epic 21 v1)

homebrew · nixpkgs · spack · debian · fedora bulk indexes — same dataset-owned
fan-out pattern as Phase Q. See `complete-export-contract.md` §3.3.

## Inventory verification matrix (`--live-catalog`)

Maps [[conda-forge-packaging-inventory-operations]] live checks to catalog outputs.
The metrics runner reads Parquet under `PYFORGE_ATLAS_DATA_ROOT`; no duplicate HTTP
clients for these signals.

| Inventory field / rule | Kedro source (dataset or derived Parquet) |
|------------------------|-------------------------------------------|
| `PyPI_Verified` | `pypi_simple_index_raw` + `pypi_json_raw` |
| `CondaForge_Verified` | `core_channeldata_raw` + `pypi_conda_mapping` (Parselmouth) |
| `Source_Repository_URL` | channeldata git-like URLs + PyPI JSON `project_urls` / VCS pipeline |
| Basilisk membership | Tier 1 `basilisk_packages_raw` |
| AOSS free / premium membership | Tier 1 AOSS datasets (premium ⊃ free) |
| Anaconda main / Dist membership | Tier 1 Anaconda datasets |
| Cross-channel BOOLs (factory) | `pypi_cross_channel_flags` (+ SelfExplainML Tier 1) |
| `identity_source` / `primary_purl` / `conda_purl` | Phase D `identity_packages_primary` (+ associator join) |
| `OpenTeams_Issue_URL` | `openteams_project_1_board_raw` joined in Phase D |
| `Conda-Forge_FeedStock_URL` / metadata / staged PR / local build | Phase D overlays (feedstock map, staged PRs, `recipes/`) |
| `Packaging_Candidate_Status` taxonomy | **Epic 23.4** derived node — not a catalog fetch in Epic 21 |
| `P1`–`P10`, Score, Work | **Epic 23.3** Kedro priority node → **23.5** complete export |

**Scale sanity gates** (fetch bugs, not soft passes): conda-forge channeldata row
count on the order of **~30k+**; Basilisk package catalog **non-zero** when API
healthy; PyPI simple index non-empty. Catalog tests or bootstrap smoke assert
order-of-magnitude floors per index.

## Stays in the inventory quartet until Epic 23 (then thin actuators only)

- Priority / Score / Work assignment (`priority.py`) — **Epic 23.3** ports to Kedro
- Three dashboard canvases — **Epic 22** Vizro parity; data from **23.5** complete export
- Deliverable A 14-column shape — **Epic 23.4** `inventory_verified_packages.parquet`
- Enterprise JFROG consumption evidence — **Epic 23.2** `enterprise_jfrog_consumption.parquet`
- **Excel workbook parse** — explicitly out of scope forever; not a catalog input

## Catalog export targets (not fetch sources)

| Target | Contract |
|--------|----------|
| Identity gist | Edit pinned secret gist in place; markdown from BSL (Epic 23.6) over **23.5** complete export |
| Identity tab CSV/Parquet | **`identity_complete_export.parquet`** — full GIST_SCHEMA + handoff |
| Enterprise handoff | **`enterprise_jfrog_consumption.parquet`** — see `complete-export-contract.md` §1 |
| Deliverable A | **`inventory_verified_packages.parquet`** — 14 columns (Epic 23.4) |

## SQLite seeds to replace (explicit checklist for spec)

Dataset modules that must lose `_cf_atlas_db_path()` / `seed_*_from_cf_atlas`
defaults for Kedro self-containment:

- `pypi_json_raw` / `PyPIJsonFanOutDataset`
- `pypi_simple_index_raw` / `PyPISimpleIndexDataset` (if seeded)
- `GitHubRequestDataset` / `vcs_github_api_raw`
- GitLab, Codeberg, registry upstream seeds (`vcs_sources.py`)
- Parselmouth mapping (`ParselmouthMappingDataset` / `pypi_conda_map_store`)

Each entry in `catalog.yml` documents: **live fetch** | **upstream Parquet** |
**external-refresh** | **tracked seed** | **credentialed opt-in**.

## Architecture constraints (non-negotiable)

- **Dataset-owned IO** — fetch, parse, rate-limit, and fallback live in
  `pyforge.atlas.datasets.*`; nodes are `DataFrame → DataFrame` (A2 law).
- **One override point per host** — new channels use `{CHANNEL}_BASE_URL` env
  normalization; Basilisk reuses `BASILISK_BASE_URL` for both packages and vulns.
- **Bootstrap seed is transitional** — post-2026-08-29 SQLite seeding is a
  documented migration bridge only; steady-state catalog entries fetch or read
  upstream Parquet. When live fetch is opt-in (GitHub GraphQL, BigQuery Phase P),
  catalog metadata says so.
- **One Kedro data root** — `PYFORGE_ATLAS_DATA_ROOT` owns Parquet **and** external
  stores (vdb, OSV, mapping); no hardcoded `.claude/data/` defaults in shipped
  catalog paths after Phase A.
- **Legacy coexistence** — `bootstrap-data` and `cf_atlas.db` are **not** in scope
  for removal; this dream only removes Kedro's *requirement* on them.
- **Do not fold inventory ranking during Epic 21** — Epic **23.3** ports `priority.py` rules.
- **Do not duplicate enterprise consumption fields during Epic 21** — Epic **23.2** owns
  `enterprise_jfrog_consumption.parquet`; Tier 2 (21.5) supplies universe **names** only as bridge.
- **Index scale gates** — each public index catalog entry documents an expected
  order-of-magnitude row count; sub-threshold loads fail smoke tests loudly.

## Non-goals

- Replacing the inventory-operations quartet with Kedro nodes in one PR.
- Re-implementing OpenTeams **issue creation** (`--create-issues`) inside Atlas —
  board ingest yes; gh issue create + project add stays inventory until asked.
- Retiring legacy `cf_atlas`, `bootstrap-data`, or conda-forge-expert atlas CLIs.
- Running `universal_sbom` in the default bootstrap chain (entry-scoped; requires
  `sbom_intake_path`).
- Ingesting or mirroring the inventory **Excel workbook** as a catalog source.

## Spec-ready resolutions (2026-08-29)

Decisions locked before `bmad-spec` (`spec-atlas-kedro-catalog-expansion`):

| # | Question | Resolution |
|---|----------|------------|
| 1 | Spec shape | **One spec** + companions (tier matrix, identity contract, verification matrix, diagrams) |
| 2 | Phase D placement | **Extend `upstream_discovery`** — identity join + gist export nodes land there (not a 9th pipeline) |
| 3 | Tier 3 bulk indexes | **Epic 21 v1 non-goal** → **Epic 23.1** (CAP-8 closure) |
| 4 | Discovery vs pypi_intelligence for Tier 1 | **Split:** factory/cross-channel + assurance lists → extend `pypi_intelligence` / `core`; Basilisk/AOSS/about/curated → `upstream_discovery` |
| 5 | SelfExplainML subdirs | **Both** `noarch` and `linux-64` |
| 6 | AOSS premium | **Live doc** primary; Wayback snapshot as AD-13 last-good / air-gap seed |
| 7 | Anaconda Dist 2026.x | **Mechanical HTML extractor** + tracked seed fallback + scale gate |
| 8 | Quartet `--live-catalog` | **Direct Parquet reads** — no compatibility JSON shim |
| 9 | `PYFORGE_ATLAS_DATA_ROOT` default | Member **`src/shared/packages/pyforge-atlas/data/`**; env override documented |
| 10 | Kedro bootstrap surface | **Pixi task** `pyforge-atlas-bootstrap` (+ documented env block; CLI subcommand optional later) |
| 11 | Associator bundle depth | **`mappings-index.json` required**; per-package shards fetched on demand for `alternative_purls` / `cpes`; full `mappings.json` as opt-in air-gap seed |
| 12 | Gist publish | **Atlas export Parquet** + thin inventory wrapper (`--gist-only` reads export, merges ranking from `priority.py`, calls `gh gist edit`) |
| 13 | Epic 17 supersession | **`spec-conda-forge-packaging-inventory-operations` § Constraints** (purl-associator stays in quartet) **superseded** — associator join + board ingest + gist actuator fold into Atlas per this spec |
| 14 | Operator Vizro (optional 21.9) | Three BSL pages: `bootstrap-index-health`, `identity-export-snapshot`, `live-catalog-coverage` |
| 15 | Kedro-Viz CI (optional 21.10) | Extend `kedro-viz-publish.yml` paths: `catalog.yml`, `globals.yml`, `datasets/**` |
| 16 | Vizro canvas parity (Epic 22 / CAP-7) | Parallel replacement for three `.canvas.tsx` views — ranking/enterprise/gist/UX bridge until Epic 23 |
| 17 | Complete export (Epic 23 / CAP-8) | `identity_complete_export.parquet` + `enterprise_jfrog_consumption.parquet`; zero deferred data slices |

## Epic 22 — Vizro parity with identity canvases (CAP-7)

Vizro **can** become the parallel browser replacement for the three Cursor Canvas
identity views. Epic 21 scoped the **data plane** first; Epic 22 scopes **operator
UI parity**.

**North star:** `identity-catalog`, `identity-ops`, `identity-workbook` Vizro
pages match catalog / ops / workbook canvases; canvases stay on `both` until
Story 22.5 parity gate, then optional deprecation (22.6).

**Deferred (explicit, not blockers):**

| Slice | Deferred content |
|-------|------------------|
| Ranking feed | Quartet writes `identity_ranked_export.parquet` after `priority.py` (22.1) — not Kedro |
| Enterprise workbook | JFROG telemetry Parquet for `identity-workbook` (22.4 shell without it) |
| Gist handoff | CAP-7d — gist markdown from BSL instead of dual logic in dashboards script |
| UX port | Search/filter/four-pane fidelity after numeric parity (22.2–22.3) |
| Canvas removal | 22.6 only after 22.5 green |

Spec companion: `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/vizro-canvas-parity.md`.

## Epic 23 — Complete export, zero deferred (CAP-8)

Closes the dream with **no data slices left in `scripts/`**.

**North star:** one canonical Parquet:

```
${PYFORGE_ATLAS_DATA_ROOT}/derived/identity_complete_export.parquet
```

**Enterprise build target** (what Artifactory / CDO must supply — Story 23.2):

```
${PYFORGE_ATLAS_DATA_ROOT}/derived/enterprise_jfrog_consumption.parquet
```

Required columns: `core_python_package_name`, `platform_env_count`,
`internal_app_count`, `artifactory_downloads`, `artifactory_version_count`,
`risk_level`, `vuln_status`, `internal_component_count`, `internal_lob_count`
(+ audit-only `packaging_tier`, never used for P). Full contract:
`complete-export-contract.md` §1.

| Story | Closes |
|-------|--------|
| 23.1 | Tier 3 OS bulk indexes |
| 23.2 | **Enterprise JFROG telemetry Parquet** |
| 23.3 | Priority rules in Kedro (`inventory_priority_assignments`) |
| 23.4 | Deliverable A + `Packaging_Candidate_Status` |
| 23.5 | **`identity_complete_export.parquet`** (supersedes quartet ranked export) |
| 23.6 | BSL gist/dashboard aggregates (CAP-8d) |
| 23.7 | E2E zero-deferred gate — quartet data logic retired |

Epic 22 steady state: Vizro reads **23.5** complete export (22.1 quartet bridge until then).

Spec companion: `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/complete-export-contract.md`.

## Open questions (remaining for `bmad-spec` only if implementation surprises)

1. **CDO-ENT-JFROG live fetch** — does Tier 2 `artifactory_downloads` supply universe **names** only, with telemetry columns still inventory-only? (Recommended: yes.)
2. **`conda-forge.org/packages` scrape** — v1 catalog dataset vs Phase D overlay reading `core_feedstock_attribution` only? (Recommended: derive from existing feedstock Parquet first; scrape optional stretch.)

## Kinships

[[pyforge-atlas]] · [[conda-forge-packaging-inventory-operations]] ·
[[upstream-discovery]] · [[artifactory-download-intelligence]] ·
[[packaging-factory]] · [[enterprise-airgap]] · [[developer-machine-bootstrap]]

**Planning bindings:** Story B5 (external-refresh stores), `catalog-contract.md`
(86 datasets / TTLs), 2026-08-29 bootstrap session (reference combined run).

## Success signal

**Epic 21 (data plane):** `pixi run -e pyforge-atlas pyforge-atlas --pipeline __default__`
(or documented Kedro bootstrap) materializes Tier-0/1 live indexes; inventory
`conda-forge-packaging-inventory-operations_metrics.py --live-catalog` produces
matching verification columns from Parquet alone. Phase D identity export passes
associator/board join parity. No `CF_ATLAS_DB` on the Kedro path;
`parity-diff` / `bsl-metric-check` pass.

**Epic 23 (dream fully closed):** additionally `enterprise_jfrog_consumption.parquet`
and `identity_complete_export.parquet` exist; priority + candidate status + gist
markdown parity on frozen fixture; Epic 22 Vizro reads complete export only;
quartet scripts are thin actuators (gist edit, optional `--create-issues`) with
no verification/ranking merge logic. Excel workbook never required.

## Realization log

- **2026-08-29** — Seeded (`78ccbe4468`, the atlas bootstrap-chain fix) and specified the same day:
  `spec-atlas-kedro-catalog-expansion` under pyforge-atlas (status `ready`) with the Epics 21–23
  planning chain (`9a0cb475f9`).

- **2026-09-09** — Fleet readiness pass (operator batch § 2.2, row atlas-B5). The Spec moves
  `ready` → **`shipped`**: Epics 21, 22 and 23 are 100% `done`, CAP-1..CAP-8 are decomposed,
  landed and gated, and both declared open questions were answered by delivery (Story 21.5's
  `project_artifactory_names` names-only projection; `core_feedstock_attribution` proving
  sufficient so the conda-forge.org/packages scrape stays deferred). **This Dream deliberately
  HOLDS at `specified`.** CAP-8's closure claim is that `identity_complete_export.parquet` and
  `enterprise_jfrog_consumption.parquet` are the canonical surface — and the catalog *declares*
  both (`conf/base/catalog.yml:987-989`, `:1301-1303`), which is a contract, not data. Atlas
  Story 25.2 ("Materialize CAP-8's canonical Parquets — one recorded run", ledger `blocked`)
  is the unblock; it needs the attended, credentialed Artifactory path that
  [[conda-forge-packaging-inventory-operations]] also waits on. This Dream moves to `realized`
  in the same commit that records that run. Splitting Spec-status from Dream-status is the shape
  [[wagtail-corporate-brain]] already uses; moving both together would set the precedent that a
  data Dream is `realized` before any data exists.
