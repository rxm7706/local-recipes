---
doc_type: architecture
part_id: cf-atlas
display_name: cf_atlas data pipeline
project_type_id: data
date: 2026-06-20
source_pin: 'conda-forge-expert v8.42.1'
---

# Architecture: cf_atlas (Part 2)

`cf_atlas` is the **offline-tolerant package-intelligence layer** for the system. It builds and maintains `cf_atlas.db` (SQLite, schema v28) — an inventory of every conda-forge package with metadata, dependencies, version skew, vulnerability surface, downloads, and staleness signals, plus a separate `pypi_universe` side table holding the PyPI directory (~800k projects) for the admin-persona "what's on PyPI but not on conda-forge" candidate-list query, plus a `pypi_intelligence` enrichment side table (v8.1.0+), `pypi_universe_serial_snapshots` (v8.1.0+), the Phase P/F+ download tables `pypi_downloads_daily` / `package_platform_downloads` / `package_python_downloads` / `package_channel_downloads` (v8.15.0/v8.18.0/v8.19.0), a `cisa_kev` overlay table (v8.5.3+), and `epss_scores` + `cwe_categories` overlay tables (v8.6.0+). The atlas is what makes Part 1's `scan_for_vulnerabilities` / `behind-upstream` / `feedstock-health` / `whodepends` queries fast and offline.

Part 2's scripts live inside Part 1's `scripts/` directory by design — the pipeline is the skill's data layer, not a separate codebase. This document focuses on **what** the pipeline does and **why** its structure looks the way it does; Part 1's architecture covers the script-level tier discipline.

---

## Mission

> **Build and maintain an offline-queryable graph of conda-forge package state, refreshable in single-phase chunks, tolerant to firewalls, network failures, and mid-run interrupts.**

Operationalized:
- One SQLite file (`cf_atlas.db`) is the answer to every question.
- 22 pipeline phases run in dependency order; each phase is independently re-runnable via `atlas-phase <ID>`.
- TTL-gated columns mean stale-row re-fetch is cheap; full rebuild is expensive but rare.
- Two air-gap backends (S3 parquet for Phase F, cf-graph offline for Phase H) close the last hard external-host dependencies.

---

## At a Glance

| Field | Value |
|---|---|
| Primary artifact | `.claude/data/conda-forge-expert/cf_atlas.db` (SQLite, WAL mode) |
| Schema version | **28** (additive migrations only; idempotent on every open) |
| Schema constant | `SCHEMA_VERSION = 28` in `conda_forge_atlas.py:138` |
| Tables | **21** (packages + 20 supporting/side) — incl. `pypi_universe`, `pypi_intelligence`, `pypi_universe_serial_snapshots`, `pypi_downloads_daily`, `package_platform_downloads`, `package_python_downloads`, `package_channel_downloads`, `cisa_kev`, `epss_scores`, `cwe_categories` (v7.9.0/v8.1.0/v8.15.0/v8.18.0/v8.19.0/v8.5.3/v8.6.0) + 4 views |
| Pipeline phases | **22** (B, B.5, B.6, C, C.5, D, O, P, Q, R, S, E, E.5, F, G, G', H, J, K, L, M, N) — Phases O–S added in v8.1.0 as the PyPI intelligence layer |
| TTL-gated phases | 4 (F, G, H, K) — re-fetch only stale rows |
| Checkpoint-aware phases | B, D, N (via `phase_state` table) |
| Air-gap backends | Phase F: S3 parquet; Phase H: cf-graph offline |
| Public CLIs | 22 (1 orchestrator + 1 single-phase + 20 query CLIs — `pypi-only-candidates` added v7.9.0; `pypi-intelligence` added v8.1.0; `platform-breakdown` / `pyver-breakdown` / `channel-split` added v8.19.0) |
| MCP exposure | Every query CLI has an MCP tool counterpart in `conda_forge_server.py` (~42 atlas + recipe-authoring tools total) |
| Pixi envs used | `local-recipes` (primary), `vuln-db` (Phase G/G' require AppThreat vdb importable) |
| Lines of orchestrator code | ~4,300 (`conda_forge_atlas.py`) |
| Approximate package count tracked | ~800k conda-forge packages |

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
                                     │  cf_atlas.db (v28)   │
                                     │   packages           │
                                     │   + 20 supporting/   │
                                     │     side tables      │
                                     │   + 4 views          │
                                     └──────────┬───────────┘
                                                │
                  ┌──────────────────────────────┼───────────────────────────────────┐
                  ▼                              ▼                                   ▼
            20 query CLIs                Part 3 (MCP)                       Part 1 (skill)
            (atlas-phase,                ~42 MCP tools                      recipe-lifecycle
             staleness-report,           expose every CLI                   consumes atlas
             behind-upstream,                                               for validation +
             feedstock-health, etc.)                                        intelligence
```

---

## The 22 Phases (verified against `conda_forge_atlas.py:PHASES` registry — see also `.claude/skills/conda-forge-expert/reference/atlas-phases-overview.md` for the canonical per-phase reference)

> The ASCII pipeline diagram above does not depict the v8.1.0 PyPI intelligence phases (**O**, **P**, **Q**, **R**, **S**) — they slot in between Phase D and Phase E and write to the `pypi_intelligence` side table joined on `pypi_name`. The phase table below is authoritative for the full set.

Phases run in dependency order. Each phase populates specific columns on the `packages` table or writes to a supporting table. Function names below match `conda_forge_atlas.py`.

| Phase | Function (line) | What it does | TTL? | Checkpoint? | External hosts |
|---|---|---|---|---|---|
| **B** | `phase_b_conda_enumeration` (611) | Enumerate every conda-forge package from `current_repodata.json` (deliberately not py-rattler sharded — see "Why current_repodata.json") | — | ✓ | conda.anaconda.org (or `CONDA_FORGE_BASE_URL`) |
| **B.5** | `phase_b5_feedstock_outputs` (775) | Map conda-forge outputs to source feedstocks | — | — | parselmouth cdn |
| **B.6** | `phase_b6_yanked_detection` (834) | Detect packages removed from current_repodata since last run | — | — | (uses Phase B's output) |
| **C** | `phase_c_parselmouth_join` (905) | Join PyPI names via parselmouth mapping | — | — | parselmouth cdn |
| **C.5** | `phase_c5_source_url_match` (954) | Match recipes to PyPI projects via source URL parsing | — | — | (DB-internal) |
| **D** | `phase_d_pypi_enumeration` (1060) | Two-tier write strategy (schema v28+): **always-on lean path** updates `pypi_last_serial` on conda-linked rows + discovers name-coincidence matches; **TTL-gated universe upsert** (default 7d via `PHASE_D_UNIVERSE_TTL_DAYS`) refreshes the `pypi_universe` side table with the ~800k-project PyPI directory. Legacy v19 `INSERT INTO packages ... 'pypi_only'` branch removed entirely. Env: `PHASE_D_DISABLED`, `PHASE_D_UNIVERSE_DISABLED`, `PHASE_D_UNIVERSE_TTL_DAYS`. | (universe TTL) | ✓ | pypi.org index (`PYPI_BASE_URL`) |
| **O** | `phase_o_serial_snapshots` | **v8.1.0 PyPI intelligence layer.** Daily serial-snapshot deltas + `activity_band` classification (hot / warm / cold / silent) into `pypi_universe_serial_snapshots` (90-day rolling history). No HTTP — operates entirely off Phase D's `pypi_last_serial`. Default-on under maintainer + admin profiles; disabled under consumer (air-gap). Env: `PHASE_O_DISABLED`, `HOT_THRESHOLD`, `WARM_THRESHOLD`, `SNAPSHOT_RETAIN_DAYS`. | — | — | (DB-internal) |
| **P** | `phase_p_pypi_downloads` | **v8.1.0 PyPI intelligence layer.** Opt-in BigQuery `pypi.file_downloads` ingest for 30/90-day download counts. Admin profile only (cost-bearing). Requires `google-cloud-bigquery` + `GOOGLE_APPLICATION_CREDENTIALS`. Writes to `pypi_intelligence.dl_last_30d` + `.dl_last_90d`. | — | — | bigquery.googleapis.com |
| **Q** | `phase_q_cross_channel` | **v8.1.0 PyPI intelligence layer.** Cross-channel `in_<channel>` BOOLs from bulk `current_repodata.json` fetches against `repo.prefix.dev/<channel>/noarch/` for bioconda / pytorch / nvidia / robostack-staging. PEP 503 name canonicalization on both sides. Per-channel `<CHANNEL>_BASE_URL` env override for JFrog mirroring. Default-on under maintainer + admin profiles. | — | — | per-channel `<CHANNEL>_BASE_URL` |
| **R** | `phase_r_pypi_json_enrich` | **v8.1.0 PyPI intelligence layer.** Per-project `pypi.org/pypi/<name>/json` enrichment bounded to the top-N candidate slice (`CANDIDATE_LIMIT=5000` default). Extracts license, requires_python, classifiers, repo_url, packaging_shape classifier (`_classify_packaging_shape`). Admin profile only. Concurrency cap `PHASE_R_CONCURRENCY=3`; TTL 7 d. | ✓ | — | pypi.org JSON (`PYPI_JSON_BASE_URL`) |
| **S** | `phase_s_computed_scores` | **v8.1.0 PyPI intelligence layer.** Computes `conda_forge_readiness` (0-100 composite, 6-component weighted) + `recommended_template` (full template path) on the rows enriched by Phase R. No HTTP — pure SQL + Python. Default-on whenever Phase R has run. | — | — | (DB-internal) |
| **E** | `phase_e_enrichment` (1148) | Download cf-graph tarball + extract feedstock-level metadata. Cache TTL via `ATLAS_CFGRAPH_TTL_DAYS` (default 1.0). Atomic-write cache; streams tar from disk (saves ~150 MB peak RAM). Incremental commits every 200 enriched rows. | ✓ (cache TTL) | — | github.com (`GITHUB_BASE_URL`) |
| **E.5** | `phase_e5_archived_feedstocks` (1395) | Identify archived feedstocks via GitHub GraphQL pagination. Page-level `save_phase_checkpoint(cursor=…)` so progress is observable mid-run. Incremental commits every 500 applied rows. | — | ✓ (page-level) | api.github.com (`GITHUB_API_BASE_URL`) |
| **F** | `phase_f_downloads` (1950) | Per-conda-package total downloads (3 backends: API / S3 parquet / auto). Default `PHASE_F_CONCURRENCY=3` (was 8 pre-v7.8.0). Retry-After honored on 429/503 (60s cap) + ±25% jitter. | ✓ | — | api.anaconda.org (`ANACONDA_API_BASE_URL`) OR AWS S3 (`S3_PARQUET_BASE_URL`) |
| **G** | `phase_g_vdb_summary` (1994) | AppThreat vdb scan summary per package — **requires `vuln-db` pixi env**. **v8.5.3 (DW13):** loads `cisa_kev` CVE IDs once via `_load_kev_cves(conn)` and ORs the result with vdb's per-CVE `kev` flag so `vuln_kev_affecting_current` reflects the live CISA catalogue (vdb's aqua source default-ignores `kevc/`). **v8.6.0:** also loads `_load_epss_scores(conn)` + `_load_cwe_categories(conn)` maps; per-row math runs through the shared `_aggregate_v8_6_0_overlays(affecting, epss_map, cwe_map)` pure function and writes `vuln_max_epss_score` + `vuln_max_epss_percentile` + `vuln_cwe_top` + `vuln_cwe_categories_json`. Phase prints "KEV overlay active: N / EPSS overlay active: M / CWE overlay active: K CVE-and-CWE IDs loaded" or per-source hints when any table is empty. | ✓ | — | (local vdb/ DB + cisa_kev + epss_scores + cwe_categories tables) |
| **G'** | `phase_g_prime_per_version_vulns` (4029) | Per-version CVE scoring — writes `package_version_vulns` — **requires `vuln-db`**. **v8.5.3 (DW13):** same KEV overlay as Phase G. **v8.5.3 (DW12):** ends with `_phase_g_sync_current_rollup` pure-SQL tail step that re-derives `packages.vuln_*_affecting_current` from `package_version_vulns` at the row's CURRENT `latest_conda_version` — closes the rollup-staleness drift surfaced by the 2026-05-23 channel-wide CVE audit. **v8.6.0:** same EPSS + CWE overlay via the shared `_aggregate_v8_6_0_overlays`; rollup-sync tail step extended to propagate the 4 new v8.6.0 columns (`vuln_max_epss_score`, `vuln_max_epss_percentile`, `vuln_cwe_top`, `vuln_cwe_categories_json`) with **COALESCE-to-existing** semantics — review-finding fix that prevents Phase G' from clobbering Phase G's direct writes to NULL whenever Phase G' runs with a stale `epss_map`. Idempotent + commits inside the same transaction as the per-version writes. | (row-absence) | — | (local vdb/ DB + cisa_kev + epss_scores + cwe_categories tables) |
| **H** | `phase_h_pypi_versions` (2762) | PyPI current-version skew detection (2 backends: pypi-json / cf-graph offline). Default `PHASE_H_CONCURRENCY=3` (was 8 pre-v7.8.1). Retry-After + ±25% jitter on the pypi-json path. **v7.9.0:** eligible-rows selector now applies the canonical persona-filter triplet `conda_name IS NOT NULL AND latest_status='active' AND COALESCE(feedstock_archived,0)=0` (matches F/G/G'/K/L/N); cold-run denominator drops from ~672k to ~12k (56× cut). **v8.0.0:** selector reads `FROM v_actionable_packages` (canonical view); eligible-rows gate becomes serial-aware (3-condition OR: never-fetched / `pypi_last_serial != pypi_version_serial_at_fetch` / 30 d safety re-check). Phase H stamps `pypi_version_serial_at_fetch` on successful fetch (schema v28 column). Warm-daily wall-clock drops ~5 min → ~30 s. Stats split into `eligible_never_fetched / eligible_serial_moved / eligible_safety_recheck`. | ✓ | — | pypi.org JSON (`PYPI_JSON_BASE_URL`) OR github.com (cf-graph) |
| **J** | `phase_j_dependency_graph` (3976) | Build the dependency graph in the `dependencies` table. **Monolithic transaction by design** — `DELETE FROM dependencies` at txn start gives consumers atomic full-snapshot semantics. **v7.9.0:** pre-pass builds `inactive_feedstocks` skip-set from `packages` (`feedstock_archived=1 OR latest_status='inactive'`); cf-graph tarball iteration skips matching basenames. New `skipped_inactive_feedstocks` stat in return dict. | — | — | (DB-internal + cf-graph) |
| **K** | `phase_k_vcs_versions` (2771) | GitHub via **batched GraphQL** (~100 repos/POST; was REST fanout pre-v7.8.0). GitLab + Codeberg still REST. Writes `upstream_versions`. `PHASE_K_GRAPHQL_DISABLED=1` reverts to REST. `PHASE_K_GRAPHQL_BATCH_SIZE` tunes batch size. | ✓ | — | api.github.com (`GITHUB_API_BASE_URL`, covers GraphQL too), gitlab.com (`GITLAB_API_BASE_URL`), codeberg.org (`CODEBERG_API_BASE_URL`) |
| **L** | `phase_l_extra_registries` (3191) | Extra registry lookups (npm / CRAN / CPAN / LuaRocks / crates / RubyGems / Maven / NuGet). **Per-registry concurrency caps**: npm=nuget=4, cran=cpan=luarocks=maven=2, crates=rubygems=1. Sequential across registries. Override via `PHASE_L_CONCURRENCY_<SOURCE>`. Writes `upstream_versions`. | (per-source) | — | per-registry `<HOST>_BASE_URL` envs (NPM/CRAN/CPAN/LUAROCKS/CRATES/RUBYGEMS/MAVEN/NUGET) |
| **M** | `phase_m_feedstock_health` (4149) | Compute feedstock health metrics from cf-graph + cached state. Incremental commits every 500 rows. **v7.9.0:** `rows_to_process` SELECT now applies the canonical persona-filter triplet at the write site (matches F/G/G'/K/L/N); no behavior change for `feedstock-health` read paths, but bot-status columns no longer get written on archived/inactive rows that read paths filter out anyway. | — | — | (uses Phase E's tarball) |
| **N** | `phase_n_github_live` (3744) | Live GitHub queries (default-branch CI status, open issues/PRs, pushed_at) — batched per-feedstock via `gh api graphql`. Rate-limit detection on stderr; 30s/60s backoff + ±25% jitter on hits (more patient than F/H since secondary windows are minutes). | (per-feedstock) | ✓ | api.github.com (`GITHUB_API_BASE_URL`) |

**Why `B` not `A`**: phase A is reserved for future use; the pipeline started at B and the letters have stuck.

**Why two phases F/H have backends**: external-host dependencies needed fallback paths. Phase F's `api.anaconda.org` was the last hard non-JFrog-proxyable external host before v7.6.0 added the S3 parquet backend; Phase H's per-package pypi.org fan-out was the slowest leg of `--fresh` until v7.7.0 added the cf-graph offline backend.

**`_http.py` public surface** (expanded in v7.8.0 + v7.8.1):

- **URL resolvers** (14 total) — every external host is redirectable via a `<HOST>_BASE_URL` env var. Public default applies when unset; trailing slashes stripped. Functions: `resolve_conda_forge_urls`, `resolve_pypi_simple_urls`, `resolve_pypi_json_urls`, `resolve_github_urls`, `resolve_github_raw_urls`, `resolve_github_api_urls`, `resolve_gitlab_api_urls`, `resolve_codeberg_api_urls`, `resolve_npm_urls`, `resolve_cran_urls`, `resolve_cpan_urls`, `resolve_luarocks_urls`, `resolve_crates_urls`, `resolve_rubygems_urls`, `resolve_maven_urls`, `resolve_nuget_urls`, `resolve_s3_parquet_urls`.
- **Auth chain** — `auth_headers_for(url)` extracted from `make_request` so `requests`-based callers (recipe-generator, npm_updater) share the same JFROG / .netrc / GitHub-token chain that urllib callers got for free. `make_request` delegates to it; caller-supplied headers still win via `setdefault`.
- **Atomic file writes** — `atomic_writer(path, mode)` context manager + `atomic_write_bytes(path, data)` + `atomic_write_text(path, text)`. Writes to `.tmp` sibling, fsyncs, `os.replace` into place. Used by `cve_manager`, `mapping_manager`, `inventory_channel`, and the cf-graph cache write in Phase E.
- **Streaming Range-resumable download** — `fetch_to_file_resumable(target, urls, *, chunk_size, ...)`. Handles 206 (append), 200-to-Range (restart), 416 (stale `.part` discard). Atomic-renames on success. Used by `cve_manager` to stream the ~4 GB OSV `all.zip` in 4 MB chunks; dropped connection at 95% resumes from current byte position. RAM drops from ~4 GB to ~4 MB during indexing.

**Engineering rule book**: `.claude/skills/conda-forge-expert/reference/atlas-phase-engineering.md` (added in v7.8.0) documents the 9 patterns that govern phase authoring and refactoring: per-host secondary rate limits vs primary quotas, GraphQL batching vs REST fanout, `Retry-After` parsing + hard cap + jitter, per-registry concurrency caps, atomic file writes, incremental commits + idempotent SQL, streaming tarfiles from disk, page-level checkpoints, and the `<HOST>_BASE_URL` enterprise routing convention. Consult before adding a phase or touching HTTP fanout / batch writes / cache IO in an existing one.

---

## Schema (cf_atlas.db, version 28)

21 tables + 4 views. The `packages` table is primary (conda-actionable
working set); the rest are supporting. `pypi_universe` (added v7.9.0 /
schema v28) is the **directory** of every PyPI project — separated from
`packages` so the working set stays conda-actionable and the universe
upsert can TTL on its own cadence (default 7 d via
`PHASE_D_UNIVERSE_TTL_DAYS`).

**v8.15.0 → v8.19.0 additions (schema v28 → v26 → v27 → v28, the Phase P/F+ download-intelligence band):**

- **v25 → v26 (v8.15.0, Phase P incremental refactor):** new `pypi_downloads_daily` side table holds per-day per-package BigQuery download counts so `pypi_intelligence.downloads_30d/90d` are recomputed from local SQL aggregation (no single-shot 90-day query). Cost-cap + dry-run preflight env vars added; no consumer-surface change.
- **v26 → v27 (v8.18.0, Phase F+ Wave 2 richer metrics):** five new `packages` columns (rolling 30/90-day downloads, 90-day trend slope, lifetime totals) plus per-platform + per-Python breakdown tables `package_platform_downloads` + `package_python_downloads`, all computed in one extended parquet sweep (zero new network). Migration writes a `phase_f_force_refresh_pending` sentinel.
- **v27 → v28 (v8.19.0, Phase F+ Wave 3 CLI surface):** new `package_channel_downloads` side table + `packages.python_min` (declared `python_min` parsed from `raw_meta_yaml` during Phase E). Surfaces the `platform-breakdown` / `pyver-breakdown` (with `--policy-check`) / `channel-split` operator CLIs + MCP tools. Migration writes BOTH force-refresh meta sentinels under `BEGIN IMMEDIATE`.

**v8.6.0 additions (schema v28, via v24 → v25 cleanup):**

- New `epss_scores` side table (5 columns: cve_id PK + epss_score REAL + epss_percentile REAL + snapshot_date TEXT + fetched_at INTEGER). Populated by `epss_fetcher.py` from FIRST.org's daily EPSS CSV at `https://epss.empiricalsecurity.com/epss_scores-current.csv.gz` (Cyentia rebranded to Empirical Security — the original v8.6.0 spec URL `epss.cyentia.com` was stale; corrected pre-Wave-A by verify-don't-assume verification). `percentile` normalized from FIRST's 0.0-1.0 to stored 0.0-100.0 at upsert to match CISA's published convention. Live verification 2026-05-24: 334,683 EPSS rows ingested in 5.1 s; 4,378 high-EPSS (≥0.7) actively-exploited CVEs (Citrix CVE-2023-23752, HTTP/2 Rapid Reset CVE-2023-44487, Jenkins CVE-2024-23897, Drupal CVE-2018-7600).
- New `cwe_categories` side table (4 columns: cwe_id PK [`CWE-NNN` form] + name TEXT + category TEXT + fetched_at INTEGER). Populated by `cwe_catalog_fetcher.py` from MITRE's Research Concepts view at `https://cwe.mitre.org/data/csv/1000.csv.zip` (the original v8.6.0 spec said `2000.csv.zip` Architectural Concepts; corrected pre-Wave-B by verify-don't-assume verification). Joined with the committed `data/cwe_categories_seed.json` 67-entry mapping that assigns one of 7 cf_atlas categories (RCE / DoS / Info-Disclosure / Auth-Bypass / Memory-Safety / Traversal / Injection); unmapped CWEs default to 'Other'. BOM-tolerant via `utf-8-sig` decode (Wave B review-finding); CWE-ID double-prefix guard handles future format drift defensively. Live verification 2026-05-24: 944 CWEs ingested in 1.03 s; 67 seeded + 877 → 'Other'.
- 4 new `packages` columns surviving v25 cleanup: `vuln_max_epss_score REAL`, `vuln_max_epss_percentile REAL`, `vuln_cwe_top TEXT`, `vuln_cwe_categories_json TEXT`. Written by Phase G + Phase G' overlay loops; propagated by `_phase_g_sync_current_rollup` (extended from v8.5.3's DW12 tail step) with **COALESCE-to-existing** semantics on the new EPSS/CWE columns — a review-finding fix that prevents Phase G' clobbering Phase G's direct writes to NULL whenever Phase G' runs with a stale `epss_map`.
- 3 new `package_version_vulns` columns surviving v25 cleanup: `vuln_max_epss_score REAL`, `vuln_max_epss_percentile REAL`, `vuln_cwe_top TEXT`. (Wave A also provisioned `vuln_total_active`; dropped in v25.)
- New `_load_epss_scores(conn) -> dict[str, tuple[float, float]]` + `_load_cwe_categories(conn) -> dict[str, str]` helpers symmetric to v8.5.3's `_load_kev_cves(conn) -> set[str]`. All three graceful-degrade to empty mapping on missing or empty table.
- New shared `_aggregate_v8_6_0_overlays(affecting, epss_map, cwe_map)` pure function consumed by both Phase G + Phase G' overlay loops. Tie-break for `cwe_top` is first-encountered (matches Python `max` stability); covered in isolation by `tests/unit/test_phase_g_overlay_v8_6_0.py` across 13 scenarios without mocking vdb.
- **Withdrawn-filter scope DROPPED** at Wave B verification time: `appthreat-vulnerability-db/lib/osv.py:91` and `gha.py:184-185` both skip withdrawn records at ingest, so a filter on Phase G/G' would be dead code (`vuln_total_active` would always equal `vuln_total`; `vuln_withdrawn_count` would always be 0 channel-wide). Columns provisioned in Wave A; dropped in Wave D's v25 cleanup.
- **Phase T (blint hardening) + Phase U (EPSS overlay phase) — CANCELLED 2026-05-23 pre-implementation** at Wave C verification. Phase T low-signal in conda-forge's hermetic compile environment (~0 hardening variance across ~32k packages; ~150 GB download cost in admin top-N mode); the actionable response to a non-hardened binary would be "file upstream issue and wait for compiler-flag patch" — not a triage signal. Phase U was redundant with Wave B's `_phase_g_sync_current_rollup` extension — the parent spec conflated "rerun max-EPSS computation" with "re-fetch vdb data" (equivalent today without a per-package CVE list). A genuine standalone Phase U would require a new `package_cves` table (filed as DW19, separate spec). Pipeline phase count preserved at 22 (B-N + O/P/Q/R/S); no new phase IDs in v8.6.0. Full rationale at `_bmad-output/projects/local-recipes/implementation-artifacts/deferred-work.md` § "Wave C cancellation".
- Migration ladder v23 → v24 → v25 is idempotent and self-healing on every `init_schema` open: v24 adds the 3 side tables (`epss_scores`, `cwe_categories`, `package_hardening`) + 6 packages columns + 3 `package_version_vulns` columns via `CREATE TABLE IF NOT EXISTS` + `pragma_table_info`-guarded `ALTER TABLE ADD COLUMN`; v25 cleanup drops `package_hardening` (+ 2 indexes) + `packages.{vuln_total_active, vuln_withdrawn_count}` + `package_version_vulns.vuln_total_active` via SQLite ≥3.35 native `ALTER TABLE … DROP COLUMN` (verified: pixi env ships SQLite 3.53.1) — guarded by `pragma_table_info` column-presence + `sqlite_master` table-presence checks; `schema_version` meta-row is the single source of truth.

**v8.5.3 additions (schema v28):**

- New `cisa_kev` side table (13 columns + 3 indexes; cve_id PK so re-fetches are pure UPSERT). Populated by `cisa_kev_fetcher.py` from the CISA Known Exploited Vulnerabilities JSON feed at `https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json` (~2 MB / ~1,602 CVEs / 0.74 s end-to-end). Joined per-CVE by Phase G + G' overlay loops via the new `_load_kev_cves(conn) -> set[str]` helper. Free-text `knownRansomwareCampaignUse` mapped to tri-state INTEGER (Known→1, Unknown→0, other→NULL). Live verification 2026-05-23: 1,602 CVEs loaded; 323 (~20%) flagged with known ransomware-campaign use; 1 actionable conda-forge feedstock surfaced channel-wide (`salt-2016.3.0`, 3 KEV CVEs).
- New `v_current_version_vulns` VIEW (DW12 fix): query-time-correct JOIN of `package_version_vulns` to `packages.latest_conda_version`. Eliminates the rollup-staleness drift class that `packages.vuln_*_affecting_current` columns suffer from when Phase B advances `latest_conda_version` between Phase G runs. New code should prefer the view; the rollup columns are retained for backward-compat and synced by Phase G''s new `_phase_g_sync_current_rollup` pure-SQL tail step.
- Migration v22 → v23 is idempotent and self-healing on next `init_schema` (CREATE TABLE / VIEW IF NOT EXISTS; no ALTER TABLE needed).
- **v8.6.0 forward-flag — ✅ SHIPPED 2026-05-24** (commits e4ba891cd2 + e22c531ac2 + 592b18089a). The as-shipped surface differs from the v8.5.3-era forecast in two ways: (1) the schema journey is v23 → v24 → v25 (round-trip cleanup) instead of net-additive v24, because Wave C (Phase T blint + Phase U EPSS overlay phase) was cancelled pre-implementation and the columns provisioned for it were dropped; (2) the withdrawn-filter columns (`vuln_total_active`, `vuln_withdrawn_count`) are also dropped in v25 — verification showed vdb pre-filters at ingest, making the filter dead code. See § "v8.6.0 additions (schema v28, via v24 → v25 cleanup)" above for the as-shipped surface.

**v8.0.0 additions (schema v28):**

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

CREATE TABLE pypi_universe (                -- Phase D side table (v7.9.0 / schema v28)
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

**Schema migrations**: idempotent on every connection open via `init_schema()`. Migrations are **predominantly additive** — new columns / tables; the only DROP is the v24 → v25 cleanup of Wave-A-provisioned-but-cancelled columns (native `ALTER TABLE … DROP COLUMN`, guarded). History (chronological): schema started at v1 and runs to the current **v28**; major additions tracked in CHANGELOG entries v6.0 → v8.19.0 (Phase F+ Wave 3).

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

## The 22 Public CLIs

All have a Tier 2 wrapper in `.claude/scripts/conda-forge-expert/` and a pixi task in `pixi.toml`. All are offline-safe (read-only against the DB except `bootstrap-data` and `atlas-phase`).

### Orchestration (2)

| CLI | Pixi task | Purpose |
|---|---|---|
| `bootstrap-data` | `pixi run -e local-recipes bootstrap-data` | Full data refresh: mapping cache + CVE DB + vdb + cf_atlas (B-N) + optional Phase N. `--fresh` for hard reset; `--status` for state; `--resume`; `--no-vdb` / `--no-cf-atlas` to skip heavy steps. Per-step timeouts via `BOOTSTRAP_<STEP>_TIMEOUT` env vars. |
| `atlas-phase` | `pixi run -e local-recipes atlas-phase <ID>` | Single-phase invocation against the existing DB. `--reset-ttl` for TTL-gated phases (F, G, H, K). `--list` enumerates phases. **Avoids the 30-45 min full rebuild.** |

### Atlas-intelligence query CLIs (20)

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

---

## MCP Exposure

Every query CLI has an MCP-tool counterpart in `.claude/tools/conda_forge_server.py` (Part 3) — ~42 `@mcp.tool` tools across the atlas-intelligence + recipe-authoring + project-scanning surfaces. MCP-only tools (no public CLI): `update_cve_database`, `update_mapping_cache`, `lookup_feedstock`, `get_feedstock_context`, `enrich_from_feedstock`, `check_dependencies`, `check_github_version`, `get_conda_name`. The MCP server is the wire format; the canonical implementation is Part 1's `scripts/`.

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
| GitHub secondary rate-limit on burst fanout | Phase K, Phase N | Currently no built-in backoff; cron with `--reset-ttl` per-day spreads load. Tracked in deferred-work. |
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
- **→ Part 3 (MCP server)**: every query CLI surfaces as an MCP tool in `conda_forge_server.py` (~42 tools total).
- **→ vuln-db env**: Phase G + G' require `pixi run -e vuln-db ...` because they import AppThreat vdb's Python library.
- **→ Enterprise layer**: all outbound HTTP from atlas phases routes through `_http.py` (truststore + JFrog/GitHub/.netrc auth). Per-host env-var overrides (`CONDA_FORGE_BASE_URL`, `PYPI_BASE_URL`, `ANACONDA_API_BASE`, `S3_PARQUET_BASE_URL`, `GITHUB_API_BASE_URL`) supported across all phases.

---

## Rebuild checklist for Part 2

1. **Prerequisites**: Part 1 must exist (cf_atlas lives inside Part 1's `scripts/`).
2. **Schema bootstrap**: implement `init_schema()` with all 21 tables + 4 views + indexes. Start at SCHEMA_VERSION=1; add migrations additively as the build progresses (current head: v28).
3. **Phase B first** (every other phase depends on Phase B's `packages` rows). Use `current_repodata.json` direct fetch via `_http.py`, NOT py-rattler.
4. **Phase D second** (PyPI enumeration; Phase C/C.5 link Phase B and Phase D).
5. **Phase E** (cf-graph tarball download — one-time ~5 min) — must exist before E.5, M (which read the tarball).
6. **Phases F, G, G', H, K, L, M, N**: in any order. Each is independently re-runnable. Implement TTL gates from the start, not as a retrofit.
7. **Phase J** (dependency graph): after Phase D (PyPI deps) and Phase E (recipe deps from cf-graph).
8. **CLI wrappers** (22 in Tier 2): 2 orchestration entries (`bootstrap-data`, `atlas-phase`) + 20 query CLIs.
9. **MCP tool wrappers** in Part 3: one per CLI + the MCP-only tools listed above.
10. **Tests**: per-phase unit tests with fixtures; meta-tests for schema migration idempotency, TTL gate scoping (`test_atlas_phase_reset_ttl.py`), checkpoint resumability.
11. **Documentation**: `guides/atlas-operations.md` for cron schedules + hard reset + air-gap; `reference/atlas-actionable-intelligence.md` for persona-mapped signal index; `reference/atlas-phases-overview.md` for phase-indexed companion (data source + purpose + intelligence per stage).

Rebuild order matters: Phase B is foundational. Without Phase B's `packages` rows, every other phase short-circuits cleanly (the pipeline doesn't crash, but produces no useful data).
