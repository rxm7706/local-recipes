---
doc_type: architecture
part_id: cf-atlas
display_name: cf_atlas data pipeline
project_type_id: data
date: 2026-05-12
source_pin: 'conda-forge-expert v7.7'
---

# Architecture: cf_atlas (Part 2)

`cf_atlas` is the **offline-tolerant package-intelligence layer** for the system. It builds and maintains `cf_atlas.db` (SQLite, schema v19) — an inventory of every conda-forge package with metadata, dependencies, version skew, vulnerability surface, downloads, and staleness signals. The atlas is what makes Part 1's `scan_for_vulnerabilities` / `behind-upstream` / `feedstock-health` / `whodepends` queries fast and offline.

Part 2's scripts live inside Part 1's `scripts/` directory by design — the pipeline is the skill's data layer, not a separate codebase. This document focuses on **what** the pipeline does and **why** its structure looks the way it does; Part 1's architecture covers the script-level tier discipline.

---

## Mission

> **Build and maintain an offline-queryable graph of conda-forge package state, refreshable in single-phase chunks, tolerant to firewalls, network failures, and mid-run interrupts.**

Operationalized:
- One SQLite file (`cf_atlas.db`) is the answer to every question.
- 17 pipeline phases run in dependency order; each phase is independently re-runnable via `atlas-phase <ID>`.
- TTL-gated columns mean stale-row re-fetch is cheap; full rebuild is expensive but rare.
- Two air-gap backends (S3 parquet for Phase F, cf-graph offline for Phase H) close the last hard external-host dependencies.

---

## At a Glance

| Field | Value |
|---|---|
| Primary artifact | `.claude/data/conda-forge-expert/cf_atlas.db` (SQLite, WAL mode) |
| Schema version | **19** (additive migrations only; idempotent on every open) |
| Schema constant | `SCHEMA_VERSION = 19` in `conda_forge_atlas.py:113` |
| Tables | 11 (packages + 10 supporting) |
| Pipeline phases | **17** (B, B.5, B.6, C, C.5, D, E, E.5, F, G, G', H, J, K, L, M, N) |
| TTL-gated phases | 4 (F, G, H, K) — re-fetch only stale rows |
| Checkpoint-aware phases | B, D, N (via `phase_state` table) |
| Air-gap backends | Phase F: S3 parquet; Phase H: cf-graph offline |
| Public CLIs | 17 (1 orchestrator + 1 single-phase + 15 query CLIs) |
| MCP exposure | All 17 CLIs have an MCP tool counterpart in `conda_forge_server.py` |
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
                                     │  cf_atlas.db (v19)   │
                                     │   packages           │
                                     │   + 10 supporting    │
                                     └──────────┬───────────┘
                                                │
                  ┌──────────────────────────────┼───────────────────────────────────┐
                  ▼                              ▼                                   ▼
            17 query CLIs                Part 3 (MCP)                       Part 1 (skill)
            (atlas-phase,                35 MCP tools                       recipe-lifecycle
             staleness-report,           expose every CLI                   consumes atlas
             behind-upstream,                                               for validation +
             feedstock-health, etc.)                                        intelligence
```

---

## The 17 Phases (verified against `conda_forge_atlas.py:PHASES` registry)

Phases run in dependency order. Each phase populates specific columns on the `packages` table or writes to a supporting table. Function names below match `conda_forge_atlas.py`.

| Phase | Function (line) | What it does | TTL? | Checkpoint? | External hosts |
|---|---|---|---|---|---|
| **B** | `phase_b_conda_enumeration` (611) | Enumerate every conda-forge package from `current_repodata.json` (deliberately not py-rattler sharded — see "Why current_repodata.json") | — | ✓ | conda.anaconda.org (or `CONDA_FORGE_BASE_URL`) |
| **B.5** | `phase_b5_feedstock_outputs` (775) | Map conda-forge outputs to source feedstocks | — | — | parselmouth cdn |
| **B.6** | `phase_b6_yanked_detection` (834) | Detect packages removed from current_repodata since last run | — | — | (uses Phase B's output) |
| **C** | `phase_c_parselmouth_join` (905) | Join PyPI names via parselmouth mapping | — | — | parselmouth cdn |
| **C.5** | `phase_c5_source_url_match` (954) | Match recipes to PyPI projects via source URL parsing | — | — | (DB-internal) |
| **D** | `phase_d_pypi_enumeration` (963) | Enumerate PyPI projects + upgrade-to-coincidence (pypi/conda matches) | — | ✓ | pypi.org index (or `PYPI_BASE_URL`) |
| **E** | `phase_e_enrichment` (1148) | Download cf-graph tarball + extract feedstock-level metadata | — | — | github.com (cf-graph-countyfair tarball) |
| **E.5** | `phase_e5_archived_feedstocks` (1395) | Identify archived feedstocks via cf-graph metadata | — | — | (uses Phase E's tarball) |
| **F** | `phase_f_downloads` (1950) | Per-conda-package total downloads (3 backends: API / S3 parquet / auto) | ✓ | — | api.anaconda.org OR AWS S3 |
| **G** | `phase_g_vdb_summary` (1994) | AppThreat vdb scan summary per package — **requires `vuln-db` pixi env** | ✓ | — | (local vdb/ DB) |
| **G'** | `phase_g_prime_per_version_vulns` (4029) | Per-version CVE scoring — writes `package_version_vulns` — **requires `vuln-db`** | (row-absence) | — | (local vdb/ DB) |
| **H** | `phase_h_pypi_versions` (2560) | PyPI current-version skew detection (2 backends: pypi-json / cf-graph offline) | ✓ | — | pypi.org JSON OR github.com (cf-graph) |
| **J** | `phase_j_dependency_graph` (3383) | Build the dependency graph in the `dependencies` table | — | — | (DB-internal + cf-graph) |
| **K** | `phase_k_vcs_versions` (2771) | GitHub/GitLab/Codeberg `releases/latest` lookup — writes `upstream_versions` | ✓ | — | api.github.com, gitlab.com, codeberg.org |
| **L** | `phase_l_extra_registries` (3191) | Extra registry lookups (CRAN, Maven, npm, RubyGems, etc.) — writes `upstream_versions` | (per-source) | — | various registries |
| **M** | `phase_m_feedstock_health` (3548) | Compute feedstock health metrics from cf-graph + cached state | — | — | (uses Phase E's tarball) |
| **N** | `phase_n_github_live` (3744) | Live GitHub queries (default-branch CI status, open issues/PRs, pushed_at) — batched per-feedstock | (per-feedstock) | ✓ | api.github.com (GraphQL) |

**Why `B` not `A`**: phase A is reserved for future use; the pipeline started at B and the letters have stuck.

**Why two phases F/H have backends**: external-host dependencies needed fallback paths. Phase F's `api.anaconda.org` was the last hard non-JFrog-proxyable external host before v7.6.0 added the S3 parquet backend; Phase H's per-package pypi.org fan-out was the slowest leg of `--fresh` until v7.7.0 added the cf-graph offline backend.

---

## Schema (cf_atlas.db, version 19)

11 tables. The `packages` table is primary; the rest are supporting.

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
```

**Schema migrations**: idempotent on every connection open via `init_schema()`. Migrations are **additive only** — new columns / tables; never DROP or rename. v19 history (chronological): schema started at v1; major additions tracked in CHANGELOG entries v6.0 → v7.7.

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

## The 17 Public CLIs

All have a Tier 2 wrapper in `.claude/scripts/conda-forge-expert/` and a pixi task in `pixi.toml`. All are offline-safe (read-only against the DB except `bootstrap-data` and `atlas-phase`).

### Orchestration (2)

| CLI | Pixi task | Purpose |
|---|---|---|
| `bootstrap-data` | `pixi run -e local-recipes bootstrap-data` | Full data refresh: mapping cache + CVE DB + vdb + cf_atlas (B-N) + optional Phase N. `--fresh` for hard reset; `--status` for state; `--resume`; `--no-vdb` / `--no-cf-atlas` to skip heavy steps. Per-step timeouts via `BOOTSTRAP_<STEP>_TIMEOUT` env vars. |
| `atlas-phase` | `pixi run -e local-recipes atlas-phase <ID>` | Single-phase invocation against the existing DB. `--reset-ttl` for TTL-gated phases (F, G, H, K). `--list` enumerates phases. **Avoids the 30-45 min full rebuild.** |

### Atlas-intelligence query CLIs (15)

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
| `health-check` | various | System-level pipeline health |

---

## MCP Exposure

All 17 CLIs have an MCP-tool counterpart in `.claude/tools/conda_forge_server.py` (Part 3). MCP-only tools (no public CLI): `update_cve_database`, `update_mapping_cache`, `lookup_feedstock`, `get_feedstock_context`, `enrich_from_feedstock`, `check_dependencies`, `check_github_version`, `get_conda_name`. The MCP server is the wire format; the canonical implementation is Part 1's `scripts/`.

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
- **→ Part 3 (MCP server)**: all 17 CLIs surface as MCP tools in `conda_forge_server.py`.
- **→ vuln-db env**: Phase G + G' require `pixi run -e vuln-db ...` because they import AppThreat vdb's Python library.
- **→ Enterprise layer**: all outbound HTTP from atlas phases routes through `_http.py` (truststore + JFrog/GitHub/.netrc auth). Per-host env-var overrides (`CONDA_FORGE_BASE_URL`, `PYPI_BASE_URL`, `ANACONDA_API_BASE`, `S3_PARQUET_BASE_URL`, `GITHUB_API_BASE_URL`) supported across all phases.

---

## Rebuild checklist for Part 2

1. **Prerequisites**: Part 1 must exist (cf_atlas lives inside Part 1's `scripts/`).
2. **Schema bootstrap**: implement `init_schema()` with all 11 tables + indexes. Start at SCHEMA_VERSION=1; add migrations additively as the build progresses.
3. **Phase B first** (every other phase depends on Phase B's `packages` rows). Use `current_repodata.json` direct fetch via `_http.py`, NOT py-rattler.
4. **Phase D second** (PyPI enumeration; Phase C/C.5 link Phase B and Phase D).
5. **Phase E** (cf-graph tarball download — one-time ~5 min) — must exist before E.5, M (which read the tarball).
6. **Phases F, G, G', H, K, L, M, N**: in any order. Each is independently re-runnable. Implement TTL gates from the start, not as a retrofit.
7. **Phase J** (dependency graph): after Phase D (PyPI deps) and Phase E (recipe deps from cf-graph).
8. **CLI wrappers** (17 in Tier 2): one per phase + 2 orchestration entries (`bootstrap-data`, `atlas-phase`) + 13 query CLIs.
9. **MCP tool wrappers** in Part 3: one per CLI + the MCP-only tools listed above.
10. **Tests**: per-phase unit tests with fixtures; meta-tests for schema migration idempotency, TTL gate scoping (`test_atlas_phase_reset_ttl.py`), checkpoint resumability.
11. **Documentation**: `guides/atlas-operations.md` for cron schedules + hard reset + air-gap; `reference/actionable-intelligence-catalog.md` for persona-mapped signal index.

Rebuild order matters: Phase B is foundational. Without Phase B's `packages` rows, every other phase short-circuits cleanly (the pipeline doesn't crash, but produces no useful data).
