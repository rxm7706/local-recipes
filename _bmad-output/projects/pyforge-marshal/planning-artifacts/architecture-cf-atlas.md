---
doc_type: architecture
part_id: cf-atlas
display_name: cf_atlas data pipeline
project_type_id: data
date: 2026-07-25
source_pin: 'conda-forge-expert v8.80.0'
---

# Architecture: cf_atlas (Part 2)

> **Re-verified 2026-07-25** (source_pin → **v8.79.1**; reconciler pass per SYNC-RUNBOOK). **The hand-rolled pipeline did not move** since the last pass — no new phase, no schema bump, no view added. This pass corrects numbers, not design.
>
> **⚠ READ FIRST — `.claude/data/` DOES NOT EXIST IN THIS CHECKOUT.** The atlas has never been built here. **Every fact in this document is derived from DDL and Python source, not from a live database.** Row counts, `phases_run`, build recency, TTL-eligibility counts, and the timing table are **UNVERIFIABLE HERE** and are marked as such inline. Do not treat any of them as observed.
>
> **Corrected in this pass** (carried forward unchecked, all re-read from source): `SCHEMA_VERSION` **28 → 29** (the At-a-Glance table and the schema heading had drifted *behind* the body text, which already said v29); views **4 → 5**; orchestrator LOC ~4,300 → **8,902**; MCP tools ~42 → **46**; `_http.py` resolvers 14 → **19**; **every line number in the phase table was wrong** (`conda_forge_atlas.py` has grown ~2× since they were recorded) — all 22 re-read; the public-CLI roster; the "~800k conda-forge packages" figure (that is the **PyPI** universe, not conda-forge).
>
> **New framing, the important one:** the pipeline has **22 executable phases and 23 cataloged** — see § *The 22 Executable Phases (and why you will see "23")*. The `23` you will encounter in `bmad-groundtruth` output is a **detector artifact**, and there is a separate, legitimate 23rd *conceptual* phase. Both are explained there; neither is a 23rd runner.
>
> **Also new since the last pass:** a full **Kedro/Dagster/DuckDB parallel reimplementation** now exists in-repo at `src/shared/packages/pyforge-atlas/` (189 `.py` / 29,288 LOC). It is **explicitly not a replacement** — see § *The Kedro reimplementation (parallel, not a replacement)*.
>
> **Re-verified unchanged:** the 22-entry `PHASES` registry and its order; 21 tables; TTL gating (F/G/H/K) and its `_TTL_GATED` predicates; checkpointing on B/D/N; both air-gap backends; the `current_repodata.json` rationale; SQLite + WAL.


`cf_atlas` is the **offline-tolerant package-intelligence layer** for the system. It builds and maintains `cf_atlas.db` (SQLite, schema v29) — an inventory of every conda-forge package with metadata, dependencies, version skew, vulnerability surface, downloads, and staleness signals, plus a separate `pypi_universe` side table holding the PyPI directory (~800k projects) for the admin-persona "what's on PyPI but not on conda-forge" candidate-list query, plus a `pypi_intelligence` enrichment side table (v8.1.0+), `pypi_universe_serial_snapshots` (v8.1.0+), the Phase P/F+ download tables `pypi_downloads_daily` / `package_platform_downloads` / `package_python_downloads` / `package_channel_downloads` (v8.15.0/v8.18.0/v8.19.0), a `cisa_kev` overlay table (v8.5.3+), and `epss_scores` + `cwe_categories` overlay tables (v8.6.0+). The atlas is what makes Part 1's `scan_for_vulnerabilities` / `behind-upstream` / `feedstock-health` / `whodepends` queries fast and offline.

Part 2's scripts live inside Part 1's `scripts/` directory by design — the pipeline is the skill's data layer, not a separate codebase. This document focuses on **what** the pipeline does and **why** its structure looks the way it does; Part 1's architecture covers the script-level tier discipline.

---

## Mission

> **Build and maintain an offline-queryable graph of conda-forge package state, refreshable in single-phase chunks, tolerant to firewalls, network failures, and mid-run interrupts.**

Operationalized:
- One SQLite file (`cf_atlas.db`) is the answer to every question.
- 22 executable pipeline phases run in dependency order; each is independently re-runnable via `atlas-phase <ID>`.
- TTL-gated columns mean stale-row re-fetch is cheap; full rebuild is expensive but rare.
- Two air-gap backends (S3 parquet for Phase F, cf-graph offline for Phase H) close the last hard external-host dependencies.

---

## At a Glance

| Field | Value |
|---|---|
| Primary artifact | `.claude/data/conda-forge-expert/cf_atlas.db` (SQLite, WAL mode via `PRAGMA journal_mode = WAL` at `conda_forge_atlas.py:765`) — **absent in this checkout** |
| Path resolution | `_get_data_dir()` (`:142`) → `DATA_DIR` (`:147`), `DB_PATH` (`:148`), `META_PATH` = `cf_atlas_meta.json` (`:149`), `EXPORT_PATH` = `cf_atlas_export.json` (`:150`); connection via `open_db()` (`:761`) |
| Schema version | **29** (additive migrations only; idempotent on every open) |
| Schema constant | `SCHEMA_VERSION = 29` — **sole declaration** at `conda_forge_atlas.py:139`; consumed at `:1212`, `:8655`, `:8776`; re-exported through `atlas_phase.py:99` |
| Tables | **21** (packages + 20 supporting/side) — incl. `pypi_universe`, `pypi_intelligence`, `pypi_universe_serial_snapshots`, `pypi_downloads_daily`, `package_platform_downloads`, `package_python_downloads`, `package_channel_downloads`, `cisa_kev`, `epss_scores`, `cwe_categories` (v7.9.0/v8.1.0/v8.15.0/v8.18.0/v8.19.0/v8.5.3/v8.6.0) |
| Views | **5** (was recorded as 4): `v_actionable_packages` (`:376`), `v_pypi_candidates` (`:585`), `v_pypi_intelligence_valid` (`:615`), `v_packages_enriched` (`:634`), `v_current_version_vulns` (`:744`) |
| Pipeline phases | **22 executable, 23 cataloged** — executable set is B, B.5, B.6, C, C.5, D, O, P, Q, R, **S**, E, E.5, F, G, G', H, J, K, L, M, N (Phases O–S added in v8.1.0 as the PyPI intelligence layer). See § *The 22 Executable Phases (and why you will see "23")* |
| TTL-gated phases | 4 (F, G, H, K) — re-fetch only stale rows |
| Checkpoint-aware phases | B, D, N (via `phase_state` table) |
| Air-gap backends | Phase F: S3 parquet; Phase H: cf-graph offline |
| Public CLIs | 2 orchestration (`bootstrap-data`, `atlas-phase`) + **25 read-side CLIs** per SKILL.md § *Daily-use CLIs*. ⚠ **Conflicting live number** — see § *The Public CLIs* |
| MCP exposure | **46** `@mcp.tool` registrations in `conda_forge_server.py`, of which **21 are atlas-intelligence** (+2 project-scanning that also read the DB). Not every CLI has one — 6 are CLI/pixi-only |
| Pixi envs used | `local-recipes` (primary), `vuln-db` (Phase G/G' require AppThreat vdb importable) — of **15** envs defined in `pixi.toml` |
| Lines of orchestrator code | **8,902** (`conda_forge_atlas.py`) — driver `bootstrap_data.py` 1,094; single-phase runner `atlas_phase.py` 112 |
| Approximate package count tracked | ⚠ **UNVERIFIABLE HERE** (no built DB). The prior "~800k conda-forge packages" was **wrong regardless**: ~800k is the size of the **PyPI directory** held in the `pypi_universe` side table; the conda-forge working set in `packages` is roughly an order of magnitude smaller. Cited row counts elsewhere in this doc come from historical run logs quoted in the CHANGELOG, not from this checkout |

---

## Pipeline Architecture

```
                                  ┌─────────────────────────────┐
                                  │   bootstrap-data (full run) │
                                  │   atlas-phase <ID> (single) │
                                  └──────────────┬──────────────┘
                                                 │
                                  ┌──────────────▼──────────────┐
                                  │ conda_forge_atlas.py        │
                                  │  PHASES registry            │
                                  │  init_schema() — idempotent │
                                  │  run_single_phase()         │
                                  └──────────────┬──────────────┘
                                                 │ ordered execution
       ┌─────────────────────────────────────────┴─────────────────────────────────────────┐
       │                                                                                   │
       ▼                                                                                   ▼
  ┌─────────┐  ┌──────┐  ┌──────┐  ┌───┐  ┌─────┐  ┌───┐  ┌───┐  ┌─────┐  ┌───┐
  │   B     │→│ B.5  │→│ B.6  │→│ C │→│ C.5 │→│ D │→│ E │→│ E.5 │→│ F │
  │ enum    │  │ feed │  │ yank │  │par│  │ src │  │py │  │enr│  │ arc │  │dl │
  │ packages│  │stock │  │ ed   │  │sel│  │ url │  │pi │  │ich │  │hive │  │   │
  └─────────┘  └──────┘  └──────┘  └───┘  └─────┘  └───┘  └───┘  └─────┘  └─┬─┘
                                                                              │
                            ┌─────────────────────────────────────────────────┘
                            ▼
                     ┌─────┐  ┌─────┐  ┌───┐  ┌───┐  ┌───┐  ┌───┐  ┌───┐  ┌───┐
                     │  G  │→│ G'  │→│ H │→│ J │→│ K │→│ L │→│ M │→│ N │
                     │ vdb │  │ per │  │pyp│  │dep│  │vcs│  │ext│  │fee│  │gh │
                     │summ │  │ver  │  │ver│  │grf│  │ver│  │reg│  │ds │  │   │
                     └──┬──┘  └──┬──┘  └─┬─┘  └─┬─┘  └─┬─┘  └─┬─┘  └─┬─┘  └─┬─┘
                        │        │       │      │      │      │      │      │
                        └────────┴───────┴──────┼──────┴──────┴──────┴──────┘
                                                ▼
                                     ┌──────────────────────┐
                                     │  cf_atlas.db (v29)   │
                                     │   packages           │
                                     │   + 20 supporting/   │
                                     │     side tables      │
                                     │   + 5 views          │
                                     └──────────┬───────────┘
                                                │
                  ┌──────────────────────────────┼───────────────────────────────────┐
                  ▼                              ▼                                   ▼
            25 read-side CLIs            Part 3 (MCP)                       Part 1 (skill)
            (detail-cf-atlas,            46 tools total, of                recipe-lifecycle
             staleness-report,           which 21 are atlas                consumes atlas
             behind-upstream,            reads (+2 project-                for validation +
             feedstock-health, etc.)     scanning) — NOT 1:1               intelligence
```

*The `atlas-phase` and `bootstrap-data` orchestration CLIs are write-side and sit above the DB, not below it — they are excluded from the 25.*

---

## The 22 Executable Phases (and why you will see "23")

**22 executable phases, 23 cataloged.** Both numbers are correct about different things, and a third number — also 23 — is a measurement bug. Because "23 phases" appears in tooling output, in the previous banner on this document, and in the phases reference, the distinction is documented here rather than silently resolved to one figure.

**1. 22 — the executable pipeline.** The `PHASES` registry at `conda_forge_atlas.py:8679` is the single source of truth for `cmd_build`, the `atlas-phase` CLI, and `get_phase()` / `run_single_phase()`. It has **exactly 22 entries**, in this order:

`B` · `B.5` · `B.6` · `C` · `C.5` · `D` · `O` · `P` · `Q` · `R` · `S` · `E` · `E.5` · `F` · `G` · `G'` · `H` · `J` · `K` · `L` · `M` · `N`

If it is not in that registry, `atlas-phase <ID>` cannot run it. **22 is the operationally meaningful number.**

**2. 23 — the catalog, which includes a phase with no runner.** `reference/atlas-phases-overview.md:916` documents a 23rd phase, **Phase I — per-version download history (side-table)**. Phase I is real as a *concept* and as *data*: its table `package_version_downloads` is declared in `SCHEMA_DDL` at `conda_forge_atlas.py:312` with a DDL comment explicitly naming it ("Phase I: per-version download history … written by Phase F as a side effect"). But it has **no runner function and no `PHASES` entry** — it is a byproduct of Phases F/H, consumed downstream by Phase G′, `version-downloads`, and `release-cadence`. You cannot `atlas-phase I`. Counting it gives 23 *cataloged* phases.

**3. 23 — the detector artifact. Do not propagate this one.** `bmad-groundtruth` / `scripts/bmad_drift_check.py`'s `phase_count()` derives its number by regexing `def phase_` over `conda_forge_atlas.py`. That matches **23** definitions, because it also picks up **`phase_r_upsert_one`** (`:8198`) — which is not a phase at all. It is the single per-row upsert path for per-project JSON enrichment, called both by Phase R's bulk loop (`:8436`) and by the `add-handoff` CLI (`add_handoff.py:120`), deliberately shared so the two writers cannot diverge. The detector's 23 and the catalog's 23 are numerically equal **by coincidence** and are not the same claim.

**Guidance:** say "22 executable phases" in any operational context (runbooks, CLI docs, capacity planning); say "22 executable, 23 cataloged" when reconciling against the phases reference; and treat a bare `phase_count == 23` from the drift detector as a known over-count, not as evidence of a new phase. Fixing `phase_count()` to read the `PHASES` registry instead of regexing `def phase_` would remove the ambiguity at the source — a genuine open item.

---

## The Phase Table

> The ASCII pipeline diagram above does not depict the v8.1.0 PyPI intelligence phases (**O**, **P**, **Q**, **R**, **S**) — they slot in between Phase D and Phase E and write to the `pypi_intelligence` side table joined on `pypi_name`. The phase table below is authoritative for the full set.

Phases run in dependency order. Each phase populates specific columns on the `packages` table or writes to a supporting table. Function names below match `conda_forge_atlas.py`.

> **All line numbers re-read live 2026-07-25.** Every line number previously in this table was wrong — `conda_forge_atlas.py` roughly doubled (to 8,902 LOC) since they were recorded, and the definitions moved by thousands of lines. Note that **source order ≠ pipeline order**: e.g. `phase_g_prime_per_version_vulns` is defined at `:6808`, well after Phase N at `:6525`.

| Phase | Function (line) | What it does | TTL? | Checkpoint? | External hosts |
|---|---|---|---|---|---|
| **B** | `phase_b_conda_enumeration` (1408) | Enumerate every conda-forge package from `current_repodata.json` (deliberately not py-rattler sharded — see "Why current_repodata.json") | — | ✓ | conda.anaconda.org (or `CONDA_FORGE_BASE_URL`) |
| **B.5** | `phase_b5_feedstock_outputs` (1593) | Map conda-forge outputs to source feedstocks | — | — | parselmouth cdn |
| **B.6** | `phase_b6_yanked_detection` (1665) | Detect packages removed from current_repodata since last run | — | — | (uses Phase B's output) |
| **C** | `phase_c_parselmouth_join` (1744) | Join PyPI names via parselmouth mapping | — | — | parselmouth cdn |
| **C.5** | `phase_c5_source_url_match` (1802) | Match recipes to PyPI projects via source URL parsing | — | — | (DB-internal) |
| **D** | `phase_d_pypi_enumeration` (1947) | Two-tier write strategy (migration v20 onward): **always-on lean path** updates `pypi_last_serial` on conda-linked rows + discovers name-coincidence matches; **TTL-gated universe upsert** (default 7d via `PHASE_D_UNIVERSE_TTL_DAYS`) refreshes the `pypi_universe` side table with the ~800k-project PyPI directory. Legacy v19 `INSERT INTO packages ... 'pypi_only'` branch removed entirely. Env: `PHASE_D_DISABLED`, `PHASE_D_UNIVERSE_DISABLED`, `PHASE_D_UNIVERSE_TTL_DAYS`. | (universe TTL) | ✓ | pypi.org index (`PYPI_BASE_URL`) |
| **O** | `phase_o_serial_snapshots` (7051) | **v8.1.0 PyPI intelligence layer.** Daily serial-snapshot deltas + `activity_band` classification (hot / warm / cold / silent) into `pypi_universe_serial_snapshots` (90-day rolling history). No HTTP — operates entirely off Phase D's `pypi_last_serial`. Default-on under maintainer + admin profiles; disabled under consumer (air-gap). Env: `PHASE_O_DISABLED`, `HOT_THRESHOLD`, `WARM_THRESHOLD`, `SNAPSHOT_RETAIN_DAYS`. | — | — | (DB-internal) |
| **P** | `phase_p_pypi_downloads` (7352) | **v8.1.0 PyPI intelligence layer.** Opt-in BigQuery `pypi.file_downloads` ingest for 30/90-day download counts. Admin profile only (cost-bearing). Requires `google-cloud-bigquery` + `GOOGLE_APPLICATION_CREDENTIALS`. Writes to `pypi_intelligence.dl_last_30d` + `.dl_last_90d`. | — | — | bigquery.googleapis.com |
| **Q** | `phase_q_cross_channel` (7847) | **v8.1.0 PyPI intelligence layer.** Cross-channel `in_<channel>` BOOLs from bulk `current_repodata.json` fetches against `repo.prefix.dev/<channel>/noarch/` for bioconda / pytorch / nvidia / robostack-staging. PEP 503 name canonicalization on both sides. Per-channel `<CHANNEL>_BASE_URL` env override for JFrog mirroring. Default-on under maintainer + admin profiles. | — | — | per-channel `<CHANNEL>_BASE_URL` |
| **R** | `phase_r_pypi_json_enrich` (8330) | **v8.1.0 PyPI intelligence layer.** Per-project `pypi.org/pypi/<name>/json` enrichment bounded to the top-N candidate slice (`CANDIDATE_LIMIT=5000` default). Extracts license, requires_python, classifiers, repo_url, packaging_shape classifier (`_classify_packaging_shape`). Admin profile only. Concurrency cap `PHASE_R_CONCURRENCY=3`; TTL 7 d. | ✓ | — | pypi.org JSON (`PYPI_JSON_BASE_URL`) |
| **S** | `phase_s_computed_scores` (8546) | **v8.1.0 PyPI intelligence layer.** Computes `conda_forge_readiness` (0-100 composite, 6-component weighted) + `recommended_template` (full template path) on the rows enriched by Phase R. No HTTP — pure SQL + Python. Default-on whenever Phase R has run. | — | — | (DB-internal) |
| **E** | `phase_e_enrichment` (2188) | Download cf-graph tarball + extract feedstock-level metadata. Cache TTL via `ATLAS_CFGRAPH_TTL_DAYS` (default 1.0). Atomic-write cache; streams tar from disk (saves ~150 MB peak RAM). Incremental commits every 200 enriched rows. | ✓ (cache TTL) | — | github.com (`GITHUB_BASE_URL`) |
| **E.5** | `phase_e5_archived_feedstocks` (2504) | Identify archived feedstocks via GitHub GraphQL pagination. Page-level `save_phase_checkpoint(cursor=…)` so progress is observable mid-run. Incremental commits every 500 applied rows. | — | ✓ (page-level) | api.github.com (`GITHUB_API_BASE_URL`) |
| **F** | `phase_f_downloads` (3560) | Per-conda-package total downloads (3 backends: API / S3 parquet / auto). Default `PHASE_F_CONCURRENCY=3` (was 8 pre-v7.8.0). Retry-After honored on 429/503 (60s cap) + ±25% jitter. | ✓ | — | api.anaconda.org (`ANACONDA_API_BASE_URL`) OR AWS S3 (`S3_PARQUET_BASE_URL`) |
| **G** | `phase_g_vdb_summary` (3771) | AppThreat vdb scan summary per package — **requires `vuln-db` pixi env**. **v8.5.3 (DW13):** loads `cisa_kev` CVE IDs once via `_load_kev_cves(conn)` and ORs the result with vdb's per-CVE `kev` flag so `vuln_kev_affecting_current` reflects the live CISA catalogue (vdb's aqua source default-ignores `kevc/`). **v8.6.0:** also loads `_load_epss_scores(conn)` + `_load_cwe_categories(conn)` maps; per-row math runs through the shared `_aggregate_v8_6_0_overlays(affecting, epss_map, cwe_map)` pure function and writes `vuln_max_epss_score` + `vuln_max_epss_percentile` + `vuln_cwe_top` + `vuln_cwe_categories_json`. Phase prints "KEV overlay active: N / EPSS overlay active: M / CWE overlay active: K CVE-and-CWE IDs loaded" or per-source hints when any table is empty. | ✓ | — | (local vdb/ DB + cisa_kev + epss_scores + cwe_categories tables) |
| **G'** | `phase_g_prime_per_version_vulns` (6808) | Per-version CVE scoring — writes `package_version_vulns` — **requires `vuln-db`**. **v8.5.3 (DW13):** same KEV overlay as Phase G. **v8.5.3 (DW12):** ends with `_phase_g_sync_current_rollup` pure-SQL tail step that re-derives `packages.vuln_*_affecting_current` from `package_version_vulns` at the row's CURRENT `latest_conda_version` — closes the rollup-staleness drift surfaced by the 2026-05-23 channel-wide CVE audit. **v8.6.0:** same EPSS + CWE overlay via the shared `_aggregate_v8_6_0_overlays`; rollup-sync tail step extended to propagate the 4 new v8.6.0 columns (`vuln_max_epss_score`, `vuln_max_epss_percentile`, `vuln_cwe_top`, `vuln_cwe_categories_json`) with **COALESCE-to-existing** semantics — review-finding fix that prevents Phase G' from clobbering Phase G's direct writes to NULL whenever Phase G' runs with a stale `epss_map`. Idempotent + commits inside the same transaction as the per-version writes. | (row-absence) | — | (local vdb/ DB + cisa_kev + epss_scores + cwe_categories tables) |
| **H** | `phase_h_pypi_versions` (4517) | PyPI current-version skew detection (2 backends: pypi-json / cf-graph offline). Default `PHASE_H_CONCURRENCY=3` (was 8 pre-v7.8.1). Retry-After + ±25% jitter on the pypi-json path. **v7.9.0:** eligible-rows selector now applies the canonical persona-filter triplet `conda_name IS NOT NULL AND latest_status='active' AND COALESCE(feedstock_archived,0)=0` (matches F/G/G'/K/L/N); cold-run denominator drops from ~672k to ~12k (56× cut). **v8.0.0:** selector reads `FROM v_actionable_packages` (canonical view); eligible-rows gate becomes serial-aware (3-condition OR: never-fetched / `pypi_last_serial != pypi_version_serial_at_fetch` / 30 d safety re-check). Phase H stamps `pypi_version_serial_at_fetch` on successful fetch (column added at migration v20 → v21). Warm-daily wall-clock drops ~5 min → ~30 s. Stats split into `eligible_never_fetched / eligible_serial_moved / eligible_safety_recheck`. | ✓ | — | pypi.org JSON (`PYPI_JSON_BASE_URL`) OR github.com (cf-graph) |
| **J** | `phase_j_dependency_graph` (6067) | Build the dependency graph in the `dependencies` table. **Monolithic transaction by design** — `DELETE FROM dependencies` at txn start gives consumers atomic full-snapshot semantics. **v7.9.0:** pre-pass builds `inactive_feedstocks` skip-set from `packages` (`feedstock_archived=1 OR latest_status='inactive'`); cf-graph tarball iteration skips matching basenames. New `skipped_inactive_feedstocks` stat in return dict. | — | — | (DB-internal + cf-graph) |
| **K** | `phase_k_vcs_versions` (5039) | GitHub via **batched GraphQL** (~100 repos/POST; was REST fanout pre-v7.8.0). GitLab + Codeberg still REST. Writes `upstream_versions`. `PHASE_K_GRAPHQL_DISABLED=1` reverts to REST. `PHASE_K_GRAPHQL_BATCH_SIZE` tunes batch size. | ✓ | — | api.github.com (`GITHUB_API_BASE_URL`, covers GraphQL too), gitlab.com (`GITLAB_API_BASE_URL`), codeberg.org (`CODEBERG_API_BASE_URL`) |
| **L** | `phase_l_extra_registries` (5841) | Extra registry lookups (npm / CRAN / CPAN / LuaRocks / crates / RubyGems / Maven / NuGet). **Per-registry concurrency caps**: npm=nuget=4, cran=cpan=luarocks=maven=2, crates=rubygems=1. Sequential across registries. Override via `PHASE_L_CONCURRENCY_<SOURCE>`. Writes `upstream_versions`. | (per-source) | — | per-registry `<HOST>_BASE_URL` envs (NPM/CRAN/CPAN/LUAROCKS/CRATES/RUBYGEMS/MAVEN/NUGET) |
| **M** | `phase_m_feedstock_health` (6263) | Compute feedstock health metrics from cf-graph + cached state. Incremental commits every 500 rows. **v7.9.0:** `rows_to_process` SELECT now applies the canonical persona-filter triplet at the write site (matches F/G/G'/K/L/N); no behavior change for `feedstock-health` read paths, but bot-status columns no longer get written on archived/inactive rows that read paths filter out anyway. | — | — | (uses Phase E's tarball) |
| **N** | `phase_n_github_live` (6525) | Live GitHub queries (default-branch CI status, open issues/PRs, pushed_at) — batched per-feedstock via `gh api graphql`. Rate-limit detection on stderr; 30s/60s backoff + ±25% jitter on hits (more patient than F/H since secondary windows are minutes). | (per-feedstock) | ✓ | api.github.com (`GITHUB_API_BASE_URL`) |

**Why `B` not `A`**: phase A is reserved for future use; the pipeline started at B and the letters have stuck.

**Why two phases F/H have backends**: external-host dependencies needed fallback paths. Phase F's `api.anaconda.org` was the last hard non-JFrog-proxyable external host before v7.6.0 added the S3 parquet backend; Phase H's per-package pypi.org fan-out was the slowest leg of `--fresh` until v7.7.0 added the cf-graph offline backend.

**`_http.py` public surface** (expanded in v7.8.0 + v7.8.1):

- **URL resolvers — 19** (re-counted live 2026-07-25; the header said 14 while the list itself named 17, so both halves were wrong). Every external host is redirectable via a `<HOST>_BASE_URL` env var; public default applies when unset; trailing slashes stripped. Functions: `resolve_conda_forge_urls`, `resolve_pypi_simple_urls`, `resolve_pypi_json_urls`, `resolve_github_urls`, `resolve_github_raw_urls`, `resolve_github_api_urls`, `resolve_gitlab_api_urls`, `resolve_codeberg_api_urls`, `resolve_npm_urls`, `resolve_cran_urls`, `resolve_cpan_urls`, `resolve_luarocks_urls`, `resolve_crates_urls`, `resolve_rubygems_urls`, `resolve_maven_urls`, `resolve_nuget_urls`, `resolve_s3_parquet_urls`, **`resolve_endoflife_urls`** (added for the LTS/EOL horizon signals), **`resolve_anaconda_channel_urls`** (the Phase Q cross-channel probe).
- **21 `<HOST>_BASE_URL` env vars** back those resolvers — more vars than resolvers because `resolve_anaconda_channel_urls` is parameterized per channel: `BIOCONDA_`, `CODEBERG_API_`, `CONDA_FORGE_`, `CPAN_`, `CRAN_`, `CRATES_`, `ENDOFLIFE_`, `GITHUB_API_`, `GITHUB_`, `GITHUB_RAW_`, `GITLAB_API_`, `LUAROCKS_`, `MAVEN_`, `NPM_`, `NUGET_`, `PYPI_`, `PYPI_JSON_`, `PYTORCH_`, `ROBOSTACK_STAGING_`, `RUBYGEMS_`, `S3_PARQUET_`.
- **Auth chain** — `auth_headers_for(url)` extracted from `make_request` so `requests`-based callers (recipe-generator, npm_updater) share the same JFROG / .netrc / GitHub-token chain that urllib callers got for free. `make_request` delegates to it; caller-supplied headers still win via `setdefault`.
- **Atomic file writes** — `atomic_writer(path, mode)` context manager + `atomic_write_bytes(path, data)` + `atomic_write_text(path, text)`. Writes to `.tmp` sibling, fsyncs, `os.replace` into place. Used by `cve_manager`, `mapping_manager`, `inventory_channel`, and the cf-graph cache write in Phase E.
- **Streaming Range-resumable download** — `fetch_to_file_resumable(target, urls, *, chunk_size, ...)`. Handles 206 (append), 200-to-Range (restart), 416 (stale `.part` discard). Atomic-renames on success. Used by `cve_manager` to stream the ~4 GB OSV `all.zip` in 4 MB chunks; dropped connection at 95% resumes from current byte position. RAM drops from ~4 GB to ~4 MB during indexing.

**Engineering rule book**: `.claude/skills/conda-forge-expert/reference/atlas-phase-engineering.md` (added in v7.8.0) documents the 9 founding patterns that govern phase authoring and refactoring: per-host secondary rate limits vs primary quotas, GraphQL batching vs REST fanout, `Retry-After` parsing + hard cap + jitter, per-registry concurrency caps, atomic file writes, incremental commits + idempotent SQL, streaming tarfiles from disk, page-level checkpoints, and the `<HOST>_BASE_URL` enterprise routing convention. Two sections have been appended since:

- **§ 13** — the Phase P cost model + operator playbook (absorbed from `atlas-phase-p-cost-model.md`, 2026-07-02).
- **§ 14** — added by the v8.79.0 retro, harvested from the Kedro reimplementation: **(14.1)** make a phase's network fetch an **injected callable defaulting to OFFLINE** — no HTTP/DB/process-client import in the phase body, and the default *refuses* rather than reaching for a public endpoint, so the phase's unit/dry-run gate is genuinely offline and the live client is one documented injection point; **(14.2)** propagate the source `StalenessMarker` forward through **every** derivation hop so a derived card never reads "fresh" over a skipped or last-good source — the "degrade toward stale/indeterminate, never a false fresh" discipline the live atlas already applies to the Phase G KEV overlay, now stated as a rule.

Consult before adding a phase or touching HTTP fanout / batch writes / cache IO in an existing one.

---

## Schema (cf_atlas.db, version 29)

**21 tables + 5 views**, all declared in the `SCHEMA_DDL` constant (verified 2026-07-25 by counting `CREATE TABLE IF NOT EXISTS` / `CREATE VIEW IF NOT EXISTS` in `conda_forge_atlas.py`; one further `CREATE TABLE IF NOT EXISTS pypi_universe` at `:990` is inside the v19→v20 migration string, not a 22nd table). The `packages` table is primary (conda-actionable working set); the rest are supporting. `pypi_universe` (added v7.9.0) is the **directory** of every PyPI project — separated from `packages` so the working set stays conda-actionable and the universe upsert can TTL on its own cadence (default 7 d via `PHASE_D_UNIVERSE_TTL_DAYS`).

**The five views** (`CREATE VIEW IF NOT EXISTS`, in DDL order):

| View | Line | Role |
|---|---|---|
| `v_actionable_packages` | `:376` | ★ the canonical persona-filter view — every phase selector and read CLI should enter through it |
| `v_pypi_candidates` | `:585` | PyPI-side candidate slice feeding Phases R/S and `pypi-intelligence` |
| `v_pypi_intelligence_valid` | `:615` | ORPHAN_RULE validity filter over `pypi_intelligence` (policed by `tests/meta/test_pypi_intelligence_scope.py`) |
| `v_packages_enriched` | `:634` | the flattened export projection (`EXPORT_PATH` JSON dump) |
| `v_current_version_vulns` | `:744` | ★ query-time-correct per-**current**-version vuln source; structurally immune to the rollup-staleness class the `packages.vuln_*_affecting_current` columns suffer from |

*(Both starred views are load-bearing: new code should prefer `v_current_version_vulns` over the rollup columns, and every new `SELECT ... FROM packages WHERE ...` must either read `v_actionable_packages` or carry a `# scope:` justification — enforced by `tests/meta/test_actionable_scope.py`.)*

**v8.15.0 → v8.19.0 additions (the Phase P/F+ download-intelligence band, migration ladder v25 → v26 → v27 → v28 en route to the current v29):**

- **v25 → v26 (v8.15.0, Phase P incremental refactor):** new `pypi_downloads_daily` side table holds per-day per-package BigQuery download counts so `pypi_intelligence.downloads_30d/90d` are recomputed from local SQL aggregation (no single-shot 90-day query). Cost-cap + dry-run preflight env vars added; no consumer-surface change.
- **v26 → v27 (v8.18.0, Phase F+ Wave 2 richer metrics):** five new `packages` columns (rolling 30/90-day downloads, 90-day trend slope, lifetime totals) plus per-platform + per-Python breakdown tables `package_platform_downloads` + `package_python_downloads`, all computed in one extended parquet sweep (zero new network). Migration writes a `phase_f_force_refresh_pending` sentinel.
- **v27 → v28 (v8.19.0, Phase F+ Wave 3 CLI surface):** new `package_channel_downloads` side table + `packages.python_min` (declared `python_min` parsed from `raw_meta_yaml` during Phase E). Surfaces the `platform-breakdown` / `pyver-breakdown` (with `--policy-check`) / `channel-split` operator CLIs + MCP tools. Migration writes BOTH force-refresh meta sentinels under `BEGIN IMMEDIATE`.

**v8.6.0 additions (migration ladder v23 → v24 → v25, a round-trip cleanup):**

- New `epss_scores` side table (5 columns: cve_id PK + epss_score REAL + epss_percentile REAL + snapshot_date TEXT + fetched_at INTEGER). Populated by `epss_fetcher.py` from FIRST.org's daily EPSS CSV at `https://epss.empiricalsecurity.com/epss_scores-current.csv.gz` (Cyentia rebranded to Empirical Security — the original v8.6.0 spec URL `epss.cyentia.com` was stale; corrected pre-Wave-A by verify-don't-assume verification). `percentile` normalized from FIRST's 0.0-1.0 to stored 0.0-100.0 at upsert to match CISA's published convention. Live verification 2026-05-24: 334,683 EPSS rows ingested in 5.1 s; 4,378 high-EPSS (≥0.7) actively-exploited CVEs (Citrix CVE-2023-23752, HTTP/2 Rapid Reset CVE-2023-44487, Jenkins CVE-2024-23897, Drupal CVE-2018-7600).
- New `cwe_categories` side table (4 columns: cwe_id PK [`CWE-NNN` form] + name TEXT + category TEXT + fetched_at INTEGER). Populated by `cwe_catalog_fetcher.py` from MITRE's Research Concepts view at `https://cwe.mitre.org/data/csv/1000.csv.zip` (the original v8.6.0 spec said `2000.csv.zip` Architectural Concepts; corrected pre-Wave-B by verify-don't-assume verification). Joined with the committed `data/cwe_categories_seed.json` 67-entry mapping that assigns one of 7 cf_atlas categories (RCE / DoS / Info-Disclosure / Auth-Bypass / Memory-Safety / Traversal / Injection); unmapped CWEs default to 'Other'. BOM-tolerant via `utf-8-sig` decode (Wave B review-finding); CWE-ID double-prefix guard handles future format drift defensively. Live verification 2026-05-24: 944 CWEs ingested in 1.03 s; 67 seeded + 877 → 'Other'.
- 4 new `packages` columns surviving v25 cleanup: `vuln_max_epss_score REAL`, `vuln_max_epss_percentile REAL`, `vuln_cwe_top TEXT`, `vuln_cwe_categories_json TEXT`. Written by Phase G + Phase G' overlay loops; propagated by `_phase_g_sync_current_rollup` (extended from v8.5.3's DW12 tail step) with **COALESCE-to-existing** semantics on the new EPSS/CWE columns — a review-finding fix that prevents Phase G' clobbering Phase G's direct writes to NULL whenever Phase G' runs with a stale `epss_map`.
- 3 new `package_version_vulns` columns surviving v25 cleanup: `vuln_max_epss_score REAL`, `vuln_max_epss_percentile REAL`, `vuln_cwe_top TEXT`. (Wave A also provisioned `vuln_total_active`; dropped in v25.)
- New `_load_epss_scores(conn) -> dict[str, tuple[float, float]]` + `_load_cwe_categories(conn) -> dict[str, str]` helpers symmetric to v8.5.3's `_load_kev_cves(conn) -> set[str]`. All three graceful-degrade to empty mapping on missing or empty table.
- New shared `_aggregate_v8_6_0_overlays(affecting, epss_map, cwe_map)` pure function consumed by both Phase G + Phase G' overlay loops. Tie-break for `cwe_top` is first-encountered (matches Python `max` stability); covered in isolation by `tests/unit/test_phase_g_overlay_v8_6_0.py` across 13 scenarios without mocking vdb.
- **Withdrawn-filter scope DROPPED** at Wave B verification time: `appthreat-vulnerability-db/lib/osv.py:91` and `gha.py:184-185` both skip withdrawn records at ingest, so a filter on Phase G/G' would be dead code (`vuln_total_active` would always equal `vuln_total`; `vuln_withdrawn_count` would always be 0 channel-wide). Columns provisioned in Wave A; dropped in Wave D's v25 cleanup.
- **Phase T (blint hardening) + Phase U (EPSS overlay phase) — CANCELLED 2026-05-23 pre-implementation** at Wave C verification. Phase T low-signal in conda-forge's hermetic compile environment (~0 hardening variance across ~32k packages; ~150 GB download cost in admin top-N mode); the actionable response to a non-hardened binary would be "file upstream issue and wait for compiler-flag patch" — not a triage signal. Phase U was redundant with Wave B's `_phase_g_sync_current_rollup` extension — the parent spec conflated "rerun max-EPSS computation" with "re-fetch vdb data" (equivalent today without a per-package CVE list). A genuine standalone Phase U would require a new `package_cves` table (filed as DW19, separate spec). Pipeline phase count preserved at 22 (B-N + O/P/Q/R/S); no new phase IDs in v8.6.0. Full rationale at `_bmad-output/projects/local-recipes/implementation-artifacts/deferred-work.md` § "Wave C cancellation".
- Migration ladder v23 → v24 → v25 is idempotent and self-healing on every `init_schema` open: v24 adds the 3 side tables (`epss_scores`, `cwe_categories`, `package_hardening`) + 6 packages columns + 3 `package_version_vulns` columns via `CREATE TABLE IF NOT EXISTS` + `pragma_table_info`-guarded `ALTER TABLE ADD COLUMN`; v25 cleanup drops `package_hardening` (+ 2 indexes) + `packages.{vuln_total_active, vuln_withdrawn_count}` + `package_version_vulns.vuln_total_active` via SQLite ≥3.35 native `ALTER TABLE … DROP COLUMN` (verified: pixi env ships SQLite 3.53.1) — guarded by `pragma_table_info` column-presence + `sqlite_master` table-presence checks; `schema_version` meta-row is the single source of truth.

**v8.5.3 additions (migration v22 → v23):**

- New `cisa_kev` side table (13 columns + 3 indexes; cve_id PK so re-fetches are pure UPSERT). Populated by `cisa_kev_fetcher.py` from the CISA Known Exploited Vulnerabilities JSON feed at `https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json` (~2 MB / ~1,602 CVEs / 0.74 s end-to-end). Joined per-CVE by Phase G + G' overlay loops via the new `_load_kev_cves(conn) -> set[str]` helper. Free-text `knownRansomwareCampaignUse` mapped to tri-state INTEGER (Known→1, Unknown→0, other→NULL). Live verification 2026-05-23: 1,602 CVEs loaded; 323 (~20%) flagged with known ransomware-campaign use; 1 actionable conda-forge feedstock surfaced channel-wide (`salt-2016.3.0`, 3 KEV CVEs).
- New `v_current_version_vulns` VIEW (DW12 fix): query-time-correct JOIN of `package_version_vulns` to `packages.latest_conda_version`. Eliminates the rollup-staleness drift class that `packages.vuln_*_affecting_current` columns suffer from when Phase B advances `latest_conda_version` between Phase G runs. New code should prefer the view; the rollup columns are retained for backward-compat and synced by Phase G''s new `_phase_g_sync_current_rollup` pure-SQL tail step.
- Migration v22 → v23 is idempotent and self-healing on next `init_schema` (CREATE TABLE / VIEW IF NOT EXISTS; no ALTER TABLE needed).
- **v8.6.0 forward-flag — ✅ SHIPPED 2026-05-24** (commits e4ba891cd2 + e22c531ac2 + 592b18089a). The as-shipped surface differs from the v8.5.3-era forecast in two ways: (1) the schema journey is v23 → v24 → v25 (round-trip cleanup) instead of net-additive v24, because Wave C (Phase T blint + Phase U EPSS overlay phase) was cancelled pre-implementation and the columns provisioned for it were dropped; (2) the withdrawn-filter columns (`vuln_total_active`, `vuln_withdrawn_count`) are also dropped in v25 — verification showed vdb pre-filters at ingest, making the filter dead code. See § "v8.6.0 additions (migration ladder v23 → v24 → v25, a round-trip cleanup)" above for the as-shipped surface.

**v8.0.0 additions (migration v20 → v21):**

- `v_actionable_packages` VIEW encodes the canonical persona-filter
  triplet `conda_name IS NOT NULL AND COALESCE(latest_status,'active')='active' AND COALESCE(feedstock_archived,0)=0`.
  Seven phase selectors (F / G / G' / H / K / L / N) refactored to
  `FROM v_actionable_packages`. New `tests/meta/test_actionable_scope.py`
  asserts every `SELECT ... FROM packages WHERE ...` either reads the
  view or carries a `# scope:` justification comment within 3 lines
  above — preventing the drift the v7.9.0 audit had to fix by hand.
- `packages.pypi_version_serial_at_fetch INTEGER` + index
  (`idx_pypi_serial_at_fetch`) enable Phase H's serial-aware
  eligible-rows gate. Phase H stamps this column on every successful
  fetch from the row's current `pypi_last_serial`; the gate fires when
  the serial moves, when the row was never fetched, or past the 30 d
  safety re-check window.
- `vuln_total` column **kept** (Wave C drop deferred — see retro at
  `implementation-artifacts/retro-conda-forge-expert-v8.0-2026-05-13.md`
  and the corrected `retro-atlas-pypi-universe-split-2026-05-13.md`;
  4 consumers were identified post-spec).

Migration from v20 → v21 is idempotent and self-healing on next
`init_schema` (column-add guarded by `pragma_table_info`; view created
via `CREATE VIEW IF NOT EXISTS` in SCHEMA_DDL).

```sql
-- ───── PRIMARY ─────────────────────────────────────────────────────────────────
CREATE TABLE packages (
    conda_name             TEXT,                  -- conda-forge package name (often != pypi)
    pypi_name              TEXT,                  -- mapped PyPI name (via Phase C parselmouth)
    feedstock_name         TEXT,                  -- feedstock repo name (often == conda_name)
    feedstock_archived     INTEGER,
    archived_at            INTEGER,
    relationship           TEXT NOT NULL,         -- 'has_pypi' | 'no_pypi' | 'pypi_only' | 'orphan'
    match_source           TEXT NOT NULL,         -- 'parselmouth' | 'source_url' | 'manual' | ...
    match_confidence       TEXT NOT NULL,         -- 'high' | 'medium' | 'low'
    conda_subdirs          TEXT,
    conda_noarch           INTEGER,
    latest_conda_version   TEXT,
    latest_conda_upload    INTEGER,
    latest_status          TEXT,                  -- 'active' | 'yanked' | ...
    conda_summary          TEXT,
    conda_license          TEXT,
    conda_license_family   TEXT,
    conda_homepage         TEXT,
    conda_dev_url          TEXT,
    conda_doc_url          TEXT,
    conda_repo_url         TEXT,
    conda_keywords         TEXT,
    recipe_format          TEXT,                  -- 'v0' | 'v1'
    conda_source_registry  TEXT,
    npm_name               TEXT,                  -- ecosystem cross-refs
    cran_name              TEXT,
    cpan_name              TEXT,
    luarocks_name          TEXT,
    maven_coord            TEXT,                  -- GAV coord (v6.x added)
    pypi_last_serial       INTEGER,
    -- ── Phase F (downloads) ──
    total_downloads          INTEGER,
    latest_version_downloads INTEGER,
    downloads_fetched_at     INTEGER,             -- TTL gate
    downloads_fetch_attempts INTEGER,
    downloads_last_error     TEXT,
    downloads_source         TEXT,                -- 'anaconda-api' | 's3-parquet' | 'merged' (v7.6+)
    -- ── Phase G (vdb summary) ──
    vuln_total                       INTEGER,
    vuln_critical_affecting_current  INTEGER,
    vuln_high_affecting_current      INTEGER,
    vuln_kev_affecting_current       INTEGER,
    vdb_scanned_at                   INTEGER,     -- TTL gate
    vdb_last_error                   TEXT,
    -- ── Phase H (pypi version skew) ──
    pypi_current_version             TEXT,
    pypi_current_version_yanked      INTEGER,    -- PEP 592 (cf-graph backend leaves NULL)
    pypi_version_fetched_at          INTEGER,    -- TTL gate
    pypi_version_last_error          TEXT,
    pypi_version_source              TEXT,        -- 'pypi-json' | 'cf-graph' (v7.7+)
    -- ── Phase K (VCS version) ──
    github_current_version           TEXT,
    github_version_fetched_at        INTEGER,    -- TTL gate
    github_version_last_error        TEXT,
    -- ── Phase N (GitHub live) ──
    bot_open_pr_count                INTEGER,
    bot_last_pr_state                TEXT,
    bot_last_pr_version              TEXT,
    bot_version_errors_count         INTEGER,
    feedstock_bad                    INTEGER,
    bot_status_fetched_at            INTEGER,
    gh_default_branch_status         TEXT,
    gh_open_issues_count             INTEGER,
    gh_open_prs_count                INTEGER,
    gh_pushed_at                     INTEGER,
    gh_status_fetched_at             INTEGER,
    gh_status_last_error             TEXT,
    notes                  TEXT
);

-- Indexes on packages: relationship, match_source, pypi_name, conda_name, feedstock_name, license

-- ───── SUPPORTING ──────────────────────────────────────────────────────────────
CREATE TABLE maintainers (...);
CREATE TABLE package_maintainers (...);
CREATE TABLE meta (...);                    -- schema_version, last_full_run, etc.

CREATE TABLE phase_state (                  -- v7.7+ checkpoint table
    phase_name               TEXT PRIMARY KEY,
    run_started_at           INTEGER,
    last_completed_cursor    TEXT,           -- e.g. feedstock_name for Phase N
    items_completed          INTEGER,
    items_total              INTEGER,
    run_completed_at         INTEGER,        -- non-NULL iff run finished cleanly
    status                   TEXT,            -- 'in_progress' | 'completed' | 'failed'
    last_error               TEXT
);

CREATE TABLE dependencies (                 -- Phase J output
    source_conda_name        TEXT,
    target_conda_name        TEXT,
    dependency_type          TEXT,           -- 'run' | 'host' | 'build' | 'test'
    ...
);

CREATE TABLE vuln_history (                 -- Phase G' snapshots over time
    conda_name               TEXT,
    snapshot_at              INTEGER,
    ...
);

CREATE TABLE package_version_downloads (    -- Phase F per-version (anaconda-api + s3-parquet)
    conda_name               TEXT,
    version                  TEXT,
    total_downloads          INTEGER,
    upload_unix              INTEGER,
    file_count               INTEGER,
    fetched_at               INTEGER,
    source                   TEXT,            -- 'anaconda-api' | 's3-parquet'
    PRIMARY KEY (conda_name, version)
);

CREATE TABLE upstream_versions (            -- Phase H + Phase K + Phase L (multi-source)
    conda_name               TEXT,
    source                   TEXT,            -- 'pypi-json' | 'cf-graph' | 'github' | 'cran' | ...
    version                  TEXT,
    fetched_at               INTEGER,
    ...
);

CREATE TABLE upstream_versions_history (...);  -- audit trail of upstream_versions writes

CREATE TABLE package_version_vulns (        -- Phase G' per-version CVE scoring
    conda_name               TEXT,
    version                  TEXT,
    vuln_critical_affecting_version  INTEGER,
    ...
);

CREATE TABLE pypi_universe (                -- Phase D side table (v7.9.0, migration v19 → v20)
    pypi_name   TEXT PRIMARY KEY,           -- ~800k rows, the full PyPI directory
    last_serial INTEGER,                    -- monotonic per-project serial from Simple API
    fetched_at  INTEGER                     -- TTL-gate target (PHASE_D_UNIVERSE_TTL_DAYS)
);
-- Separated from `packages` so working-set queries (Phase F/G/G'/H/K/L/N + every read
-- CLI) stop seeing the ~660k PyPI-only rows. Read by `pypi-only-candidates` CLI via
-- LEFT JOIN to `packages.pypi_name`. v19→v20 migration self-heals in `init_schema`:
-- moves existing `relationship='pypi_only'` rows from `packages` to `pypi_universe`
-- via INSERT OR IGNORE + DELETE in one transaction (idempotent on re-runs).
```

**Schema migrations**: idempotent on every connection open via `init_schema()`. Migrations are **predominantly additive** — new columns / tables; the only DROP is the v24 → v25 cleanup of Wave-A-provisioned-but-cancelled columns (native `ALTER TABLE … DROP COLUMN`, guarded). History (chronological): schema started at v1 and runs to the current **v29**; major additions tracked in CHANGELOG entries v6.0 → v8.19.0 (Phase F+ Wave 3).

> **Corrected 2026-07-25 — a mass search-and-replace defect, not mere staleness.** An earlier reconciliation pass rewrote the *current* schema version into the **historical** per-release headings of this section, so `v8.0.0`, `v8.5.3`, `v8.6.0`, and the `pypi_universe` DDL comment all carried the current version while their own bodies described migrations `v20 → v21`, `v22 → v23`, and `v23 → v24 → v25`. The headings have been restored to match the ladders their bodies document, and reworded to say **"migration vN → vM"** rather than "schema vN" so a historical label can never again be mistaken for — or mechanically rewritten into — a current-version claim. Only the At-a-Glance table, this paragraph, and the intro now carry the current **v29**. When re-grounding this document, bump *current-version* statements only; per-release headings are history and must not move.

---

## TTL Gating (cheap stale-row refresh)

Four phases (F, G, H, K) use **per-row `*_fetched_at` timestamps** as TTL gates. The phase only re-fetches rows where:
- `*_fetched_at IS NULL` (never fetched), OR
- `*_fetched_at < (now - TTL)` (stale)

Default TTLs: F=7d, G=7d, H=24h, K=24h (configurable). Phase eligibility predicates (from `atlas_phase.py:_TTL_GATED`):

| Phase | Column | Scope predicate |
|---|---|---|
| F | `downloads_fetched_at` | `conda_name IS NOT NULL` |
| G | `vdb_scanned_at` | `conda_name IS NOT NULL` |
| G' | (row absence in `package_version_vulns`) | — |
| H | `pypi_version_fetched_at` | `pypi_name IS NOT NULL` |
| K | `github_version_fetched_at` | `conda_name IS NOT NULL` |
| L | (per-registry source) | — |

`atlas-phase F --reset-ttl` NULLs the column **scoped to the predicate** (not bare `UPDATE packages SET col = NULL` — that would touch every row including ones the phase wouldn't pick up). Verified by `tests/unit/test_atlas_phase_reset_ttl.py` (4 cases).

---

## Checkpointing (`phase_state` table)

Long-running phases write `phase_state` rows with cursor + items_completed + items_total + status. Three phases write checkpoints:
- **B** — alphabetically-sorted conda_name cursor, every 1k rows
- **D** — alphabetically-sorted PyPI project cursor, every 5k rows
- **N** — alphabetically-sorted feedstock_name cursor, every batch (~50 items)

On resume, the phase reads `phase_state.last_completed_cursor` and skips items ≤ cursor. `status='completed'` markers prevent false resume on the next clean run.

**Progress cadence** (v7.7.0): `progress_every = min(max(N, len // 40), 2500)`. Plus a 60-second wall-clock heartbeat that prints "still alive" if no progress fired in the last minute — closes the "Phase H hangs" UX bug where 770k-row runs went silent for 5-11 minutes between progress lines.

---

## Air-Gap Backends

### Phase F (Downloads)

Three modes via `PHASE_F_SOURCE` env var (default `auto`):

| Mode | Backend | Data path |
|---|---|---|
| `anaconda-api` | `api.anaconda.org/package/conda-forge/<name>/files` | Direct API (needs `api.anaconda.org` reachable or `ANACONDA_API_BASE` override) |
| `s3-parquet` | `s3://anaconda-package-data/conda/monthly/<YYYY>/<YYYY-MM>.parquet` over HTTPS | Pyarrow reads parquet from AWS S3 (separate from `*.anaconda.org`); `S3_PARQUET_BASE_URL` override supported |
| `auto` (default) | probe `api.anaconda.org` once, fall through to S3 on URLError/timeout/HTTP≥500 | Mid-run >25%-failure-after-1000-rows trigger also flips |

Cache: `.claude/data/conda-forge-expert/cache/parquet/<YYYY-MM>.parquet` (~13MB/month, ~1.4GB for full 9+ years). Current-month always re-fetched; older months cached indefinitely. Optional `PHASE_F_S3_MONTHS=24` caps trailing months.

**Numeric caveat**: API and S3 totals do NOT agree (verified 2026-05-10: `requests` 1.50× higher on S3, `django` 0.56×). Consumers (`staleness_report`, `package_health`, etc.) must surface `downloads_source` to be honest about which backend produced the number.

### Phase H (PyPI Version Skew)

Two modes via `PHASE_H_SOURCE` env var (default `pypi-json`):

| Mode | Backend | Cost | Caveat |
|---|---|---|---|
| `pypi-json` | Per-package pypi.org JSON API | ~25-30 min for 25k rows | Real-time + yanked status (PEP 592) |
| `cf-graph` | Local cf-graph tarball scan (`.claude/data/conda-forge-expert/cf-graph-countyfair.tar.gz`) | ~30 seconds for 770k rows | No yanked status; lags pypi.org by hours-to-days |
| (auto via `bootstrap-data --phase-h-source auto`) | `--fresh` → cf-graph (fast cold-start), else pypi-json | — | — |

`pypi_version_source` column on `packages` discriminates which backend wrote the row.

---

## The Public CLIs

All have a Tier 2 wrapper in `.claude/scripts/conda-forge-expert/` and a pixi task in `pixi.toml` (106 tasks under `[feature.local-recipes.tasks.*]`). All are offline-safe (read-only against the DB except `bootstrap-data` and `atlas-phase`).

> **⚠ CONFLICTING LIVE NUMBERS — reported, not resolved.** There is no single authority for "how many read CLIs does the atlas have."
> - **SKILL.md § *Daily-use CLIs (all offline; all support `--json`)*** enumerates **25**: `detail-cf-atlas`, `staleness-report`, `feedstock-health`, `whodepends`, `behind-upstream`, `cve-watcher`, `version-downloads`, `release-cadence`, `find-alternative`, `adoption-stage`, `platform-breakdown`, `pyver-breakdown`, `channel-split`, `scan-project`, `export-purls`, `mapping-gap`, `universe-sbom`, `inventory-match`, `add-handoff`, `library-futures`, `recommend-2027`, `lts-registry-gap`, `cwe-seed-gap`, `spdx-schema-gap`, `license-map-gap`.
> - **`src/shared/packages/pyforge-atlas/src/pyforge/atlas/semantic/__init__.py:4`** states "the metric / business logic of the **28 read CLIs**" and calls the full 28-CLI metric surface its D2 completion target.
>
> The 3-CLI delta is a boundary judgment, not necessarily an error on either side — candidates for the extra three are `query-atlas` / `package-health` (MCP-tool composites without their own standalone entry point) and `health-check` (system-level, not package-level). **This doc uses 25** because SKILL.md is the operating contract, and flags the reimplementation's 28 rather than silently overriding it. Reconciling the two — or declaring one authoritative — is an open item.

### Orchestration (2)

| CLI | Pixi task | Purpose |
|---|---|---|
| `bootstrap-data` | `pixi run -e local-recipes bootstrap-data` | Full data refresh: mapping cache + CVE DB + vdb + cf_atlas (B-N) + optional Phase N. `--fresh` for hard reset; `--status` for state; `--resume`; `--no-vdb` / `--no-cf-atlas` to skip heavy steps. Per-step timeouts via `BOOTSTRAP_<STEP>_TIMEOUT` env vars. |
| `atlas-phase` | `pixi run -e local-recipes atlas-phase <ID>` | Single-phase invocation against the existing DB. `--reset-ttl` for TTL-gated phases (F, G, H, K). `--list` enumerates phases. **Avoids the 30-45 min full rebuild.** |

### Atlas-intelligence query CLIs

*(The table below is the founding 20 read surfaces, three of which — `query-atlas`, `package-health`, `health-check` — are MCP-tool composites or system-level rather than members of SKILL.md's 25. The 11 added since are listed beneath it.)*

| CLI | Reads from | Use case |
|---|---|---|
| `staleness-report` | `packages` (Phase H + Phase F + Phase N) | "Which feedstocks are behind upstream and not actively maintained?" |
| `feedstock-health` | `packages` (Phase M + Phase N) | "What's the health summary of feedstock X?" |
| `whodepends` | `dependencies` (Phase J) | "Which feedstocks depend on package X?" (reverse dep graph) |
| `behind-upstream` | `upstream_versions` + `packages.latest_conda_version` (Phase H + Phase K) | "Which packages have new upstream releases not yet on conda-forge?" |
| `version-downloads` | `package_version_downloads` (Phase F) | "Download trend for package X across versions" |
| `release-cadence` | `upstream_versions_history` (Phase L) | "How often does upstream X release?" |
| `find-alternative` | `packages` (Phase B + Phase D + Phase E) | "What conda-forge packages are similar to X?" |
| `adoption-stage` | `packages` (Phase B + Phase F) | "Is package X mature / popular / abandoned?" |
| `cve-watcher` | `package_version_vulns` (Phase G') + vdb/ | "What new CVEs landed in packages I maintain?" |
| `detail-cf-atlas` | `packages` (all phases) | "Show me everything about package X" |
| `query-atlas` | `packages` (all phases) | Generic SQL-ish query interface |
| `package-health` | `packages` + `feedstock-health` join | "Holistic health score for package X" |
| `scan-project` | `packages` + `inventory_cache/` | "Scan this manifest / SBOM / container for conda-forge intelligence" |
| `my-feedstocks` | `package_maintainers` + GitHub user | "What feedstocks does user X maintain?" |
| `pypi-only-candidates` | `pypi_universe LEFT JOIN packages` (Phase D, v7.9.0+) | "Which PyPI projects have no conda-forge equivalent yet?" (admin candidate-list, ordered by `last_serial DESC`; flags `--limit N --min-serial M --json`) |
| `pypi-intelligence` | `pypi_intelligence` + `v_pypi_candidates` (Phases O/P/Q/R/S, v8.1.0+) | "What's the conda-forge readiness, activity band, cross-channel presence, and download trend for PyPI project X?" |
| `platform-breakdown` | `package_platform_downloads` (Phase F+, v8.19.0+) | "ARM / Windows / EOL-Python download share for package X (or channel-wide)" |
| `pyver-breakdown` | `package_python_downloads` + `packages.python_min` (Phase F+, v8.19.0+) | "Per-Python download distribution; `--policy-check` flags python_min bump-safe candidates from real download data" |
| `channel-split` | `package_channel_downloads` (Phase F+, v8.19.0+) | "Defaults-channel vs conda-forge download split — surfaces migration opportunities" |
| `health-check` | various | System-level pipeline health |

### Added since (11 — the purl/BOM/gap-matcher/2027-scoring + seed-gap suites)

| CLI | Reads from | Use case | MCP tool? |
|---|---|---|---|
| `export-purls` | `packages` + `pypi_universe` | The six purl + mapping artifacts (conda / versioned / pypi-universe purls, conda↔pypi TSV, recipe exceptions, upstream TSV); regenerate after every atlas rebuild | ✅ `export_purls` |
| `universe-sbom` | `packages` + `pypi_universe` (+ vulns) | Full-universe CycloneDX 1.6 / SPDX BOM; a mapped pair is ONE conda component; 14-day freshness gate | ✅ `universe_sbom` |
| `inventory-match` | user inventory ⋈ `packages` | Gap / version-lag buckets (ADD / ADD-NONPYPI / UPDATE-FEEDSTOCK / UPDATE-PIN / CURRENT / UNKNOWN) + freshness percentile + CI policy gate (rc 2) | ✅ `inventory_match` |
| `recommend-2027` | S5→S7 composite | The single 2027–2030 scorecard; annotated BOM with 5 `cfe:*` properties; overrides shown-never-silent | ✅ `recommend_2027` |
| `mapping-gap` | `packages` ⋈ `pypi_universe` | Classify + recover conda↔PyPI mapping gaps offline (inverse-G10); DRY-RUN by default | ❌ CLI/pixi-only |
| `add-handoff` | ADD bucket + bounded Phase-R enrichment | ADD-bucket packaging worklist (readiness, template, fail-closed license blockers). Writes via the shared `phase_r_upsert_one` | ❌ CLI/pixi-only |
| `library-futures` | `packages` + LTS/EOL signals | 2027–2030 survival composite per package: `futures_score` + keep / watch / plan-migration / replace tier, py314 + endoflife horizons | ❌ CLI/pixi-only |
| `lts-registry-gap` | endoflife.date ⋈ `v_actionable_packages` | Propose `data/lts-registry.yaml` entries (exact / likely tiers) | ❌ CLI/pixi-only |
| `cwe-seed-gap` | `cwe_categories` | Propose `data/cwe_categories_seed.json` entries by keyword-classifying CWEs bucketed `Other` | ❌ CLI/pixi-only |
| `spdx-schema-gap` | vendored SPDX enum vs upstream | Propose `data/spdx.schema.json` enum additions, ranked by real package license usage | ❌ CLI/pixi-only |
| `license-map-gap` | `pypi_intelligence.license_raw` | Propose `_LICENSE_TO_SPDX` entries from raw PyPI license strings that normalize to nothing | ❌ CLI/pixi-only |

All four seed-gap suggesters are **read-only by design**: they propose, git review disposes. The curated maps (`lts-registry.yaml`, `cwe_categories_seed.json`, `spdx.schema.json`, `_LICENSE_TO_SPDX`) stay hand-owned — `conda_forge_atlas.py` is never written by them.

---

## MCP Exposure

**Not** every query CLI has an MCP-tool counterpart — that long-standing claim is false (corrected 2026-07-25). `.claude/tools/conda_forge_server.py` (Part 3) registers **46** `@mcp.tool` functions, split **21 recipe-authoring / 21 atlas-intelligence / 2 project-scanning / 2 infrastructure**. Of the atlas read surface:

- **7 CLIs have no MCP tool at all** — `mapping-gap`, `add-handoff`, `library-futures`, and the four seed-gap suggesters (`lts-registry-gap`, `cwe-seed-gap`, `spdx-schema-gap`, `license-map-gap`). They are CLI/pixi-only.
- **MCP-only tools (no public CLI)**: `update_cve_database`, `update_mapping_cache`, `lookup_feedstock`, `get_feedstock_context`, `enrich_from_feedstock`, `check_dependencies`, `check_github_version`, `get_conda_name`.

The MCP server is the wire format; the canonical implementation is Part 1's `scripts/`. It does not talk to `cf_atlas.db` itself — it shells out. Full surface split: Part 3.

---

## The Kedro reimplementation (parallel, NOT a replacement)

Since the last pass a second, complete implementation of the atlas exists in-repo at **`src/shared/packages/pyforge-atlas/`** (189 `.py` / 29,288 LOC incl. tests), delivered by BMAD project `pyforge-atlas`. **This section exists so nobody reads it as a successor.** The v8.79.0 CHANGELOG states the boundary explicitly: *"it is a parallel reimplementation, not a replacement of `conda_forge_atlas.py` … authored no conda recipes and changed no operational guidance."* Everything above this section describes the live, hand-rolled pipeline, which remains the operational one.

Shape of the reimplementation:

| Aspect | Legacy (`conda_forge_atlas.py`) | Kedro reimplementation |
|---|---|---|
| Unit of work | 22 phases in a `PHASES` registry | **7 modular pipelines** — `core`, `pypi_intelligence`, `vulnerability`, `vcs_health`, `universal_sbom`, `seed_gaps`, `derived_artifacts` |
| Orchestration | `bootstrap_data.py` + `atlas_phase.py` | Dagster glue in `orchestration/definitions.py` — `KedroProjectTranslator`, `SCHEDULED_JOBS`, 3 bootstrap profiles, per-op `NODE_TIMEOUTS`. AD-1/AD-6 make it the **only** module permitted to import `dagster` / `kedro_dagster` |
| Storage | one SQLite file, WAL | **Parquet** under `data/<layer>/<dataset>/`, read by **Ibis → DuckDB at query time** (AD-4, "Ibis → DuckDB ONLY"). **No persisted `.duckdb` file exists** — verified; the engine is a query-time construct, not an artifact |
| Data-access contract | inline in phase bodies | **`conf/base/catalog.yml` (800 lines)** — every source and persisted output declared there; nodes contain no IO, enforced by a `no-inline-IO` meta-test |
| Credentials | `_http.py` global auth chain | **per-dataset only.** The catalog header states the legacy `_http.py` JFrog leak is **"FIXED, not ported"**: no global credential injection exists, a JFrog key may attach only to a dataset whose endpoint resolves to an Artifactory host, and no shipped entry carries the key |
| MCP surface | shares Part 3's 46-tool server | its **own second FastMCP server** at `pyforge/atlas/mcp/server.py` with **11** `@mcp.tool()` registrations |
| Verification | pytest + meta-tests | additionally a `parity/` package (`legacy_surface.py`, `frame_diff.py`, `evidence.py`) + frozen per-node JSON parity fixtures — the contract binding the reimplementation to the legacy pipeline |

`src/prototype/packages/pyforge-atlas-kedro-viz/` is a generated, dependency-free stub mirror driving `pixi run kedro-viz-proto`.

Two things worth carrying forward into the legacy pipeline regardless of the reimplementation's fate: the **per-dataset credential model** (the direct fix for the still-unresolved `JFROG_API_KEY` cross-host leak) and the **catalog-declared, no-inline-IO** discipline (already partly captured as `atlas-phase-engineering.md` § 14.1).

> **⚠ Spec self-contradiction — flagged, not resolved.** `docs/specs/cfe-atlas-datapipeline-kedro-migration.md` disagrees with itself: its frontmatter says `status: shipped` / `shipped_ref: "conda-forge-expert v8.79.0"` / `spec_updated: 2026-07-18`, and the v8.79.0 CHANGELOG entry says Waves 0 + A–H all landed (PRs #96–#102) — while the § 1 Execution table body still reads *"Waves 0 + A–D SHIPPED … **Remaining: Waves E–H (epics 6–9)**."* The frontmatter and CHANGELOG are the newer statements and agree with each other; the table body is a stale mid-effort snapshot. This document treats the migration as shipped, but the spec body should be reconciled by its owner rather than by a downstream architecture doc.

---

## Pipeline Run Modes

### Full bootstrap (`bootstrap-data`)

```bash
pixi run -e local-recipes bootstrap-data --fresh
```

What runs:
1. `update_mapping_cache` (Tier 1: `mapping_manager.py`) — refresh `pypi_conda_map.json`
2. `update_cve_database` (Tier 1: `cve_manager.py`) — refresh `cve/` feed cache
3. vdb refresh (if not `--no-vdb`) — requires `vuln-db` pixi env
4. `conda_forge_atlas.py` phase B → N — full pipeline, may take 30-45 min on cold cache
5. Phase N (`--gh --maintainer <user>`) — optional live GitHub data (rate-limited; secondary throttle risk on burst fanout, see `project_phase_k_secondary_rate_limit.md` auto-memory)

`--fresh` invokes a hard reset on `.claude/data/conda-forge-expert/` with a 5-second confirmation countdown (skip with `--yes`). `--reset-cache` also wipes `cache/parquet/` (immutable historical data; ~30 min to refetch).

Default cf_atlas step timeout: 7,200s (2h) — sized for cold `--fresh` worst-case. Override with `BOOTSTRAP_CF_ATLAS_TIMEOUT` env var.

### Single-phase (`atlas-phase <ID>`)

```bash
pixi run -e local-recipes atlas-phase F                # re-run Phase F only
pixi run -e local-recipes atlas-phase H --reset-ttl    # NULL fetched_at then re-run
pixi run -e local-recipes atlas-phase --list           # enumerate phases
```

Use when: a phase shipped a fix and you want to re-process; a phase failed mid-run; downstream consumers need fresher data than the full pipeline cadence.

### Status check

```bash
pixi run -e local-recipes bootstrap-data --status
```

Prints:
- `phase_state` checkpoint table (per-phase status + items_completed + cursor + last run time)
- TTL-gated phase eligibility summary (stale row counts per phase)
- `*_last_error` row counts per phase

Useful before deciding whether to run `--fresh` (rare) vs `atlas-phase X` (common).

---

## Why `current_repodata.json` (Phase B's deliberate non-py-rattler choice)

Phase B enumerates packages by fetching `<channel>/<subdir>/current_repodata.json` directly rather than using py-rattler's sharded repodata protocol. Rationale (from `project_cf_atlas_rattler_502.md` auto-memory):

- py-rattler's sharded protocol issued 502 errors against `conda.anaconda.org` during a 2026-Q1 run (~15% of shards 502'd).
- `current_repodata.json` is one HTTP request per subdir (5 subdirs × ~30MB each) — fast, predictable, JFrog-proxyable, and has zero shard-fanout failure modes.
- The skill's `_http.py` layer routes this through the same JFrog auth chain as every other request.

Trade-off: `current_repodata.json` excludes outdated package versions (it's the "current" view, not the full archive). Phase B.6 ("yanked detection") tracks delta-from-last-run to capture removals.

---

## Data Refresh Patterns

| Frequency | Command | Why |
|---|---|---|
| **Daily** (cron) | `atlas-phase N` | Phase N's GitHub live data (PR counts, default-branch CI) goes stale fastest |
| **Weekly** (cron) | `atlas-phase F, atlas-phase G, atlas-phase H, atlas-phase K` | TTL-gated phases; weekly matches their TTL settings |
| **Monthly** (cron) | `bootstrap-data --resume` | Full pipeline; resume-friendly via TTL gates |
| **Quarterly** | `bootstrap-data --fresh` | Hard reset; rarely needed; takes 30-45 min |
| **On demand** | `atlas-phase <ID>` | After a CHANGELOG bump that touches the phase |

Cron schedules + sample crontab entries: `guides/atlas-operations.md`.

---

## Performance Characteristics

> **⚠ UNVERIFIABLE IN THIS CHECKOUT.** `.claude/data/` does not exist here, so no run of this pipeline can be observed and no `phase_state` / TTL-eligibility figure can be checked. Every number in the table below is a **historical measurement** carried from 2026-Q1/Q2 production runs (and the parenthetical row counts, e.g. Phase H's "770k rows" and Phase K's "8,893 fetches", are from those same logs). They are retained as sizing guidance, not asserted as current fact. Re-measure before relying on them for capacity or timeout decisions.

| Phase | Cold-start time (`--fresh`) | Warm-run time (TTL gates active) | Note |
|---|---|---|---|
| B | ~5 min | ~5 min | Fixed cost (5 subdirs × current_repodata.json) |
| B.5/B.6/C/C.5 | ~1 min each | <30s each | Mostly DB-internal joins |
| D | ~3-5 min | ~30s | TTL-aware on rerun |
| E/E.5 | ~30s | ~30s | After Phase E downloads cf-graph tarball (~5 min one-time) |
| F (api) | ~25 min | ~3-5 min | API path — per-row fetch |
| F (s3-parquet) | ~5-10 min cold (S3 download) | <30s warm (parquet cache hit) | S3 path — bulk read |
| G | ~10 min | ~3 min | Requires `vuln-db` env |
| G' | ~15-20 min | ~5 min | Per-version CVE scoring |
| H (pypi-json) | ~25-30 min (770k rows) | ~3-5 min | Per-row pypi.org fetch |
| H (cf-graph) | ~30 sec | ~30 sec | Bulk local file scan |
| J | ~5 min | ~5 min | Dependency graph build |
| K | ~30 min (8,893 fetches) | ~5 min | GitHub/GitLab/Codeberg per-feedstock; secondary rate-limit risk on burst fanout |
| L | ~10 min | ~3 min | Per-registry probes |
| M | ~2 min | ~2 min | DB-internal + cf-graph |
| N | ~15 min (rate-limited) | ~3 min | GitHub GraphQL batched |
| **Total cold** | **~3-4 hours uncapped** | — | With auto-mode F/H backends, can drop to ~1.5 hr on `--fresh` |
| **Total warm** | — | **~30-45 min** | Mostly TTL gates short-circuit |

(Timings approximate, from 2026-Q1/Q2 production runs.)

---

## Failure Modes & Mitigations

| Failure | Where | Mitigation |
|---|---|---|
| `api.anaconda.org` unreachable (firewall) | Phase F | `PHASE_F_SOURCE=s3-parquet` or `auto` (default falls through) |
| pypi.org fan-out hangs `--fresh` | Phase H | `PHASE_H_SOURCE=cf-graph` (auto on `--fresh`) |
| GitHub secondary rate-limit on burst fanout | Phase K, Phase N | **Corrected 2026-07-25 — backoff now exists** (this row previously said "no built-in backoff", contradicting the phase table two sections above). Phase K has `_phase_k_backoff_seconds(attempt, cap=60.0)` (`conda_forge_atlas.py:4640`) plus GraphQL batching (~100 repos/POST) instead of REST fanout; Phase N does stderr rate-limit detection with 30s/60s backoff + ±25% jitter. Concurrency is additionally capped at 3 across F/H/K (down from 8) against the empirically-observed ~10 req/s secondary threshold documented at `:1334`. Cron with `--reset-ttl` per-day still helps spread load. |
| Phase K regex captures multi-URL `dev_url` strings | Phase K | v7.7.2 fix: regex char-class excludes `\s , ( ) < > " '` |
| Mid-run interrupt | B, D, N (checkpointed) | Resume via `bootstrap-data --resume`; checkpoint cursor preserved in `phase_state` |
| Mid-run interrupt | F, G, H, K, L (TTL-gated) | Next run only re-fetches rows where `*_fetched_at IS NULL` |
| Phase G/G' import error | All vdb-dependent | Must run in `vuln-db` pixi env, NOT `local-recipes` |
| Schema migration failed | Schema bump | `init_schema()` is idempotent; safe to retry |
| `current_repodata.json` 502 from py-rattler | (avoided by design) | Phase B uses direct fetch, not py-rattler sharded |

---

## Integration Points (recap)

See `integration-architecture.md` for full cross-part contracts. Summary:

- **← Part 1 (skill)**: cf_atlas is implemented inside Part 1's `scripts/`. The `conda-forge-expert` skill exposes the atlas as MCP tools and CLIs.
- **→ Part 3 (MCP server)**: **21 of the 46** tools in `conda_forge_server.py` are atlas-intelligence reads (plus 2 project-scanning tools that also read the DB). Seven read CLIs have **no** MCP counterpart — see § MCP Exposure.
- **⟂ pyforge-atlas (parallel)**: the Kedro/Dagster reimplementation ships its own separate 11-tool FastMCP server and does not consume Part 3.
- **→ vuln-db env**: Phase G + G' require `pixi run -e vuln-db ...` because they import AppThreat vdb's Python library.
- **→ Enterprise layer**: all outbound HTTP from atlas phases routes through `_http.py` (truststore + JFrog/GitHub/.netrc auth). Per-host env-var overrides (`CONDA_FORGE_BASE_URL`, `PYPI_BASE_URL`, `ANACONDA_API_BASE`, `S3_PARQUET_BASE_URL`, `GITHUB_API_BASE_URL`) supported across all phases.

---

## Rebuild checklist for Part 2

1. **Prerequisites**: Part 1 must exist (cf_atlas lives inside Part 1's `scripts/`).
2. **Schema bootstrap**: implement `init_schema()` with all 21 tables + **5** views + indexes. Start at SCHEMA_VERSION=1; add migrations additively as the build progresses (current head: **v29**).
3. **Phase B first** (every other phase depends on Phase B's `packages` rows). Use `current_repodata.json` direct fetch via `_http.py`, NOT py-rattler.
4. **Phase D second** (PyPI enumeration; Phase C/C.5 link Phase B and Phase D).
5. **Phase E** (cf-graph tarball download — one-time ~5 min) — must exist before E.5, M (which read the tarball).
6. **Phases F, G, G', H, K, L, M, N**: in any order. Each is independently re-runnable. Implement TTL gates from the start, not as a retrofit.
7. **Phase J** (dependency graph): after Phase D (PyPI deps) and Phase E (recipe deps from cf-graph).
8. **CLI wrappers** in Tier 2: 2 orchestration entries (`bootstrap-data`, `atlas-phase`) + the read-side CLIs (25 per SKILL.md; see the conflict note in § The Public CLIs).
9. **MCP tool wrappers** in Part 3: **not** one per CLI — 21 atlas tools + the MCP-only tools listed above, with 7 read CLIs deliberately CLI/pixi-only.
10. **Tests**: per-phase unit tests with fixtures; meta-tests for schema migration idempotency, TTL gate scoping (`test_atlas_phase_reset_ttl.py`), checkpoint resumability, plus the two scope gates (`tests/meta/test_actionable_scope.py`, `tests/meta/test_pypi_intelligence_scope.py`) that keep selectors reading the views.
11. **Documentation**: `guides/atlas-operations.md` for cron schedules + hard reset + air-gap; `reference/atlas-phases-overview.md` — the **single consolidated** reference (Part A persona-mapped signal catalog + Part B phase-indexed companion). *The separate `reference/atlas-actionable-intelligence.md` cited here previously was absorbed into it on 2026-07-02 and no longer exists.*
12. **Decide the phase-count contract up front**: make the registry the only source (have any `phase_count`-style detector read `PHASES`, not a `def phase_` regex) and give conceptual side-table stages like Phase I an explicit non-runner marker, so "22 vs 23" never has to be re-litigated.

Rebuild order matters: Phase B is foundational. Without Phase B's `packages` rows, every other phase short-circuits cleanly (the pipeline doesn't crash, but produces no useful data).
