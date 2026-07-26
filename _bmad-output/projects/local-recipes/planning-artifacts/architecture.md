---
doc_type: architecture
project_name: local-recipes
date: 2026-07-25
version: '1.1.0'
status: draft
source_pin: 'conda-forge-expert v8.79.1'
consolidates:
  - architecture-conda-forge-expert.md
  - architecture-cf-atlas.md
  - architecture-mcp-server.md
  - architecture-bmad-infra.md
  - integration-architecture.md
---

# Unified Architecture: `local-recipes`

> **Re-grounded 2026-07-25** (source_pin → v8.79.1). **The system grew a fifth part.** `src/shared/packages/` now hosts **`pyforge-packages`** — five hatchling-built distributions (`pyforge-warden`, `pyforge-atlas`, `pyforge-herald`, `pyforge-scribe`, `pyforge-doctor`) sharing one PEP 420 implicit `pyforge` namespace, each a pixi workspace member with its own lean `no-default-feature` env. Consequences woven through this doc: **19 pixi envs** (9 factory + 9 product, was 9), a **second MCP server** (pyforge-atlas' 11-tool FastMCP, additive to the legacy 46-tool one), **Parquet + Ibis→DuckDB** storage alongside SQLite, **spec-surface governance** (`scripts/spec_surface_check.py`), and five new ADRs (013–017). Also corrected — every one of these was **understated** here and is now raised to live: the view count on `cf_atlas.db` (now **21 tables + 5 views**; the missing one is `v_pypi_intelligence_valid`, which schema v29 landed), Part 1's inventory (**66 Tier-1 scripts / 57 Tier-2 wrappers / 100 test files / 15 reference files**), the BMAD installer version (**6.10.0**), the skill catalogue (**93 dirs / 89 real skills**), the project count (**14**), the recipe corpus (**1,664**), and the several stale `SCHEMA_VERSION` mentions (now **29** throughout). Re-verified **unchanged**: conda-forge-expert **v8.79.1**, cf_atlas schema **v29**, **46 legacy MCP tools**, gotchas **G1–G106**, **22 executable atlas phases** (23 cataloged), 41 templates / 13 ecosystems, and the `JFROG_API_KEY` cross-host leak in `_http.py` (still UNRESOLVED — ADR-010 stands).


This document is the **executive architecture** for the rebuild. It consolidates the four part-specific architecture docs plus the integration doc into one navigable artifact, and adds the fifth part (`pyforge-packages`), which has no part-specific doc of its own — its detail lives in the per-product `_bmad-output/projects/pyforge-*/planning-artifacts/` sets. Part-specific docs remain authoritative for fine-grained detail (~3,000 lines collectively); this doc is for orientation, decision rationale, and rebuild planning.

---

## 1. System Architecture Overview

```
                           ┌────────────────────────────────────────┐
                           │  User / Claude Code / BMAD agent       │
                           └──────────────────┬──────────────────────┘
                                              │
              ┌───────────────────────────────┴───────────────────────────────┐
              │                                                                │
              ▼ (BMAD-driven planning)                                          ▼ (direct conda-forge work)
   ┌─────────────────────┐                                          ┌────────────────────────┐
   │  Part 4: BMAD       │                                          │  Part 3: MCP Server    │
   │  - 93 skill dirs    │── Rule 1: invoke ────────────┐           │  - 46 tools            │
   │    (89 real skills) │                              │           │  - thin subprocess     │
   │  - 6-layer config   │                              │           │    wrappers            │
   │  - 14 projects      │                              │           │  - stdio; registered   │
   │  - active-project   │   ┌──────────────────────────▼───────────│    in ~/.claude.json   │
   │    marker + 2       │   │   Part 1: conda-forge-expert skill   └────────────────────────┘
   │    symlinks         │◀──│   - SKILL.md (10-step loop, 5 critical          │
   │  - bmad-loop        │   │     constraints, G1-G106 gotchas)                │
   │    (external        │   │   - 66 Tier 1 canonical scripts                 │
   │     harness)        │   │   - 57 Tier 2 CLI wrappers                      │
   └─────────────────────┘   │   - 41 templates / 13 ecosystems (12 language + conda-forge-yml)                │
              │              │   - 100 test files (unit + integration + meta)  │
              │ Rule 2:      │   - 15 reference + 9 guides + 2 quickrefs       │
              │ retro on     │   - MANIFEST.yaml + install.py (portable)       │
              │ closeout     │                                                  │
              ▼              └────────────────────────┬─────────────────────────┘
                                                      │ Tier 1 scripts host:
                                                      ▼
                                     ┌──────────────────────────────────────┐
                                     │  Part 2: cf_atlas data pipeline      │
                                     │  - 22 executable phases              │
                                     │    (B → N + O/P/Q/R/S; 23 cataloged) │
                                     │  - SQLite schema v29 (21 tables/5 views)│
                                     │  - TTL gates on F, G, H, K           │
                                     │  - phase_state checkpoint (B, D, N)  │
                                     │  - S3-parquet + cf-graph offline     │
                                     │    backends (Phase F + Phase H)      │
                                     │  - 17 query CLIs                     │
                                     └──────────────────┬───────────────────┘
                                                        │
              ┌─────────────────────────────────────────┤
              │ parallel reimplementation (NOT a        │
              │ replacement — legacy stays authoritative)│
              ▼                                          ▼
   ┌───────────────────────────────────────┐  ┌───────────────────────────────────────────────┐
   │  Part 5: pyforge-packages             │  │  Shared state: .claude/data/conda-forge-      │
   │  src/shared/packages/ — 5 dists,      │  │  expert/   ← ABSENT in this checkout          │
   │  one PEP 420 `pyforge` namespace      │  │  - cf_atlas.db (SQLite WAL)                   │
   │  ┌─ pyforge-warden  (gate engine)     │  │  - vdb/, vdb-cache/, cve/                     │
   │  ├─ pyforge-atlas   (Kedro/Dagster;   │  │  - cf-graph-countyfair.tar.gz                 │
   │  │    own 11-tool FastMCP server;     │  │  - cache/parquet/                             │
   │  │    Parquet + Ibis→DuckDB)          │  │  - pypi_conda_map.json                        │
   │  ├─ pyforge-herald  (MCP transport)   │  └───────────────────────────────────────────────┘
   │  ├─ pyforge-scribe  (docs CLI)        │                       │
   │  └─ pyforge-doctor  (DoctorReport)    │                       │
   │  6 lean `no-default-feature` envs     │                       │
   └───────────────────┬───────────────────┘                       │
                       └───────────────┬───────────────────────────┘
                                       ▼
                                ┌───────────────────────────────────────────────┐
                                │  Cross-cutting auth chain (_http.py, 1,024 LOC)│
                                │  - REQUESTS_CA_BUNDLE / SSL_CERT_FILE →        │
                                │    truststore.inject_into_ssl() → certifi      │
                                │  - JFROG_API_KEY → X-JFrog-Art-Api header     │
                                │    ★ leaks cross-host (mitigation: subshell)  │
                                │  - JFROG_USERNAME+PASSWORD → Basic             │
                                │  - ~/.netrc → Basic                            │
                                │  - GITHUB_TOKEN/GH_TOKEN → Bearer (github only)│
                                │  + 21 per-host *_BASE_URL overrides            │
                                │  ✗ Part 5 does NOT inherit this — pyforge-atlas│
                                │    uses per-dataset credentials (ADR-015)      │
                                └───────────────────────────────────────────────┘
```

---

## 2. Architectural Style

| Dimension | Style | Rationale |
|---|---|---|
| **Decomposition** | 5-part monorepo: 4 factory parts on shared infrastructure + 1 pixi workspace of independently-versioned product packages | Parts 1–4 share env, data dir, and auth chain; Part 5 deliberately shares only the pixi workspace and the `pyforge` namespace, so each product can be installed standalone |
| **Language** | Python throughout, but **not one floor**: factory + warden/herald/scribe on ≥3.12; pyforge-atlas + pyforge-doctor on ≥3.14 | conda-forge ecosystem is Python-native; env isolation (ADR-014) is what lets the floors diverge without a lockfile fight |
| **State management** | Parts 1–3: SQLite (WAL) + JSON caches + flat-file logs. Part 5 (atlas): Parquet files read by Ibis→DuckDB at query time — **no persisted `.duckdb`** | Single-file portability for the legacy store; columnar + zero-server analytics for the reimplementation |
| **API surface** | MCP (Model Context Protocol) — JSON-RPC over stdio. **Two servers**: the legacy 46-tool `conda_forge_server.py` and pyforge-atlas' 11-tool FastMCP | Standardized; Claude Code native. The two surfaces are additive and must not be conflated |
| **Build pattern** | rattler-build via pixi tasks (recipes); hatchling via pixi-build backend (Part 5 packages); Docker for Linux native builds | conda-forge canonical for recipes; hatchling keeps the products pip- and conda-installable; Docker prevents host-env pollution |
| **Concurrency** | Sequential subprocess; SQLite WAL allows concurrent reads; Dagster provides the execution plane for Part 5's atlas pipelines | Atlas phases serialize naturally; MCP tool calls block at server level |
| **Communication pattern** | Pull-based (subprocess invocations); Kedro catalog datasets for Part 5 | Predictable; no message-queue complexity; subprocess inherits env |
| **Deployment model** | Single-host + CI. **Exactly one thing deploys**: the Guildhall dashboard (`docs/dashboard/` → GitHub Pages). No Dockerfile, Helm chart, or k8s manifest outside test fixtures | No production server; everything else runs in the operator's pixi env |
| **Auth model** | Parts 1–4: env-var-driven chain in `_http.py`. Part 5 (atlas): per-dataset credentials in `conf/base/catalog.yml`, global injection deliberately not ported | The legacy chain's cross-host leak is a known defect; the reimplementation fixed rather than inherited it (ADR-015) |
| **Governance** | Spec-surface coverage + drift gate (`scripts/spec_surface_check.py`) over every tracked file | Every file is governed by a spec `surface:` glob or reason-tagged allowlist entry; never false-green (ADR-016) |
| **Versioning** | Skill (MANIFEST.yaml + CHANGELOG.md) + Schema (SCHEMA_VERSION) + per-package `pyproject.toml` version | Three surfaces: portability protocol, data migration, product semver |

---

## 3. The Five Parts (Consolidated)

Parts 1–4 are the **factory**: the machinery that turns upstream sources into conda-forge recipes and keeps the planning artifacts honest. Part 5 is the **product line**: five installable distributions the factory dogfoods on itself. The factory is a monolith by design; the products are deliberately decoupled from it (ADR-013/014/015).

### Part 1: conda-forge-expert skill

**Role**: encodes every conda-forge packaging decision so AI agents author conda-forge-acceptable recipes on first pass.

**Components**:
- **Documentation**: `SKILL.md` (3,887 lines, primary spine) + `INDEX.md` + `CHANGELOG.md` + 15 reference files + 9 guides + 2 quickrefs
- **Scripts (Tier 1 canonical)**: 66 Python modules in `.claude/skills/conda-forge-expert/scripts/`
- **CLI wrappers (Tier 2)**: 57 thin subprocess wrappers in `.claude/scripts/conda-forge-expert/`
- **Templates**: 41 recipe templates across 13 ecosystems (12 language: python, rust, go, c-cpp, r, java, ruby, dotnet, fortran, multi-output, nodejs, perl + conda-forge-yml config-template starter)
- **Tests**: 100 files in `tests/{unit,integration,meta}/` with real fixtures
- **Portability**: `MANIFEST.yaml` (`version: 7.0.0`, `type: standalone-portable`) + `install.py` for installing into other repos

**Key invariants**:
1. 10-step autonomous loop with one human gate at step 8b
2. 5 critical constraints (no-mix-formats, stdlib-required, python-floor, pypi-url-pattern, build.bat-call-prefix)
3. 106 Recipe Authoring Gotchas (G1-G106)
4. Three-place rule for new scripts (canonical + wrapper + pixi task + meta-test)

**Detail**: see [architecture-conda-forge-expert.md](./architecture-conda-forge-expert.md)

### Part 2: cf_atlas data pipeline

**Role**: builds and maintains an offline-queryable graph of conda-forge package state.

**Components**:
- **Orchestrator**: `conda_forge_atlas.py` with the `PHASES` registry
- **Phases**: **22 executable** ordered functions (B, B.5, B.6, C, C.5, D, O, P, Q, R, S, E, E.5, F, G, G', H, J, K, L, M, N) — v8.1.0 added O/P/Q/R/S for the PyPI intelligence layer. **23 cataloged**: `reference/atlas-phases-overview.md` also documents a runner-less conceptual "Phase I" (per-version download history side-table). `bmad-groundtruth` prints 23 for a different reason — its `phase_count()` regexes `def phase_` and catches the per-row helper `phase_r_upsert_one`. Never state a bare phase count of 23; always qualify it as executable-vs-cataloged
- **Schema**: 21 tables + **5 views**, `SCHEMA_VERSION = 29`, idempotent additive migrations
- **TTL gates**: 4 phases (F, G, H, K) with `*_fetched_at` timestamps
- **Checkpointing**: 3 phases (B, D, N) with `phase_state` cursor
- **Backends**: Phase F (S3 parquet / anaconda-api / auto) + Phase H (pypi-json / cf-graph)
- **CLIs**: 17 public (1 orchestrator + 1 single-phase + 15 query)

**Key invariants**:
1. All phases idempotent (re-run safe)
2. TTL gates scope UPDATE statements to phase eligibility predicates
3. Mid-run kill is cheap (checkpoint resume + TTL gates)
4. Phase F + Phase H tolerate firewall (no hard `*.anaconda.org` or `pypi.org` dep)

**Detail**: see [architecture-cf-atlas.md](./architecture-cf-atlas.md). Note Part 5's `pyforge-atlas` is a **parallel reimplementation** of this pipeline, not a replacement — see ADR-015.

### Part 3: FastMCP server

**Role**: exposes Parts 1+2 as 46 MCP tools for Claude Code / BMAD agents.

**Components**:
- **Server**: `conda_forge_server.py` (2,266 lines, FastMCP)
- **Auxiliary**: `gemini_server.py` (Gemini bridge), `mcp_call.py` (JSON-RPC shell client)
- **Tools**: **46** `@mcp.tool()` registrations — **21 recipe-authoring + 21 atlas-intelligence + 2 project-scanning** (`scan_project`, `env_inspect`) **+ 2 infra** (`run_system_health_check`, `update_mapping_cache`); **44 sync + 2 async** (`update_cve_database`, `trigger_build`)
- **Transport**: **stdio**. Registered in `~/.claude.json`, **not in-repo** — there is no `.mcp.json` and `.claude/settings.json` carries no `mcpServers` block
- **Helper**: `_run_script(script_path, args, input_text=None, timeout=120)` with 3-tier error handling; 600 s timeout for `update_cve_database`; runs `sys.executable` (the pixi env interpreter)
- **Out-of-band state**: `build_summary.json` + `build.pid` at repo root
- **Zero auth code**: the server itself contains none; every subprocess script imports `_http.py`

**Key invariants**:
1. Every tool is a thin subprocess wrapper over a Tier 1 script (no inline logic)
2. JSON-stdout contract — every wrapped script accepts `--json`
3. Subprocess for isolation + timeout + pixi-env consistency
4. Errors structured (`{"error": "..."}`), never raw Python exceptions

**Detail**: see [architecture-mcp-server.md](./architecture-mcp-server.md). Part 5's `pyforge-atlas` ships a **second, additive** MCP server (11 tools) — the two surfaces are separate.

### Part 4: BMAD infrastructure

**Role**: provides multi-project planning/dev/review/retro workflows.

**Components**:
- **Installer**: `_bmad/` with config.toml (layer 1), config.user.toml (layer 2), bmm/ module, core/, scripts/ — **BMAD-METHOD 6.10.0**
- **Custom overlays**: `_bmad/custom/` with layers 3-4 + per-skill .toml + active-project marker
- **Output**: `_bmad-output/projects/<slug>/` with planning + implementation artifacts per project — **14 projects**, **22 Specs**, **63 tracked per-story specs**
- **Switcher**: `scripts/bmad-switch`
- **Skills**: **93 dirs / 89 real skills** (51 `bmad-*`, 16 `skf-*`, 21 engineering-practice, 1 repo-specific)
- **External harness**: `bmad-loop` — a deterministic DEV → VERIFY → REVIEW → VERIFY → COMMIT cycle in fresh tmux sessions with worktree isolation and squash merges; `--frozen` verify commands mandatory. Loop homes moved 2026-07-25 to `~/.bmad-loops/<slug>` (`BMAD_LOOP_HOME_ROOT` overrides) because long paths panic pixi-build-python 0.8.3
- **Integration rules**: CLAUDE.md § BMAD↔CFE (Rule 1 invoke + Rule 2 retro)

**Key invariants**:
1. Six-layer TOML config merge in priority order
2. Active-project resolution has **two halves**: the `.active-project` marker resolved by `_bmad/scripts/resolve_config.py` (CLI flag > env var > marker > none) **and** two gitignored symlinks `_bmad-output/{planning,implementation}-artifacts -> projects/<slug>/…`. `_bmad/bmm/config.yaml` hard-codes `planning_artifacts` to the symlink path and that key does **not** compose with a project's `output_folder`, so **every write-skill resolves through the symlinks, not the marker**. Marker and symlinks disagreeing means a write-skill silently targets the wrong project
3. **Parallel agents address projects by physical path and never call `scripts/bmad-switch`** (HARD rule, 2026-07-25) — the marker+symlink pair is per-working-tree global state, i.e. a mutex nobody holds
4. Rule 1: BMAD agents touching conda-forge work MUST invoke the skill
5. Rule 2: Every conda-forge effort runs a `bmad-retrospective` at closeout

**Detail**: see [architecture-bmad-infra.md](./architecture-bmad-infra.md)

### Part 5: pyforge-packages

**Role**: the product line — five installable Python distributions the factory builds, gates, and dogfoods on itself. Root `src/shared/packages/`.

**Components**: five hatchling-built distributions sharing a **PEP 420 implicit namespace** (`pyforge`). No distribution ships `src/pyforge/__init__.py` — that absence is load-bearing: it is what lets `pyforge.atlas`, `.doctor`, `.herald`, `.scribe` and `.warden` coexist in one import root when installed independently. Each carries its own `[package]` `pixi.toml` (a pixi workspace member) and **no `[workspace]` table**. The root `pixi.toml` `[workspace]` sets `preview = ["pixi-build"]` and deliberately has **no `members` key** — a comment records that pixi through 0.72.2 has no such key; members are declared via path dependencies.

| dist | module | py | deps | extras | console script | src LOC/files | tests LOC/files/`def test_` | maturity |
|---|---|---|---|---|---|---|---|---|
| `pyforge-warden` | `pyforge.warden` | ≥3.12 | PyYAML, packaging, cyclonedx-python-lib, jsonschema, packageurl-python, license-expression | — | `warden` | 16,597 / 28 | 29,752 / 65 / 1,575 | production-grade, self-dogfooding |
| `pyforge-atlas` | `pyforge.atlas` | **≥3.14** | kedro≥1.5.0, kedro-datasets≥9.5.0 | `gate=[pyforge-warden]` | `pyforge-atlas` | 14,461 / 78 | 14,682 / 110 / 772 | production-grade |
| `pyforge-herald` | `pyforge.herald` | ≥3.12 | mcp≥1.28.1 | — | `herald` | 1,277 / 6 | 1,594 / 5 / 112 | real transport core, stub CLI |
| `pyforge-scribe` | `pyforge.scribe` | ≥3.12 | typer, pydantic | — | `scribe` | 421 / 4 | 323 / 2 / 18 | one working command, 2 stubs |
| `pyforge-doctor` | `pyforge.doctor` | **≥3.14** | jsonschema | `gate=[pyforge-warden]` (declared, not yet wired) | `doctor` | 304 / 4 | 1,081 / 6 / 62 | scaffold + frozen schema only |

**`pyforge-atlas` specifics** — a real Kedro project, not a script port:
- **7 modular pipelines**: `core`, `pypi_intelligence`, `vulnerability`, `vcs_health`, `universal_sbom`, `seed_gaps`, `derived_artifacts`
- **Dagster glue** in `orchestration/definitions.py` — the **only** module permitted to import `dagster` / `kedro_dagster` (AD-1 / AD-6)
- **Storage**: Parquet under `data/<layer>/<dataset>/`, read by **Ibis→DuckDB at query time** (AD-4, "Ibis → DuckDB ONLY"). There is **no persisted `.duckdb` file**
- **Contracts** in `conf/base/catalog.yml` (800 lines)
- **`parity/` package** (`frame_diff.py`, `evidence.py`, `legacy_surface.py`) plus frozen per-node JSON parity fixtures — the verification contract binding the reimplementation to the legacy pipeline
- **Own FastMCP server** at `pyforge/atlas/mcp/server.py` — **11 `@mcp.tool()`**: 7 `run_*_pipeline`, plus `read_atlas_dataset`, `list_atlas_pipelines`, `list_atlas_datasets`, `query_vizro_ai`

**Frozen report contracts**: `pyforge/warden/data/report-schema.json` (575 lines, `$id: urn:local-recipes:pyforge-warden:report-schema`, title `ComplianceReport`) and `pyforge/doctor/data/report-schema.json` (92 lines, `urn:local-recipes:pyforge-doctor:report-schema`, title `DoctorReport`). Each package's exit-code projection has a **single owner module**, `verdict.py`. Doctor's stated purpose is to consolidate `pyforge-warden` + cf_atlas signals into one schema-validated `DoctorReport` envelope — the cross-part contract pattern made explicit.

**Key invariants**:
1. No `src/pyforge/__init__.py` anywhere — the namespace is implicit (PEP 420) or the packages collide on install (ADR-013)
2. Every product env sets `no-default-feature = true`, which is what permits divergent Python floors (ADR-014)
3. Package edges are **extras-gated and one-directional**: atlas and doctor declare `gate = ["pyforge-warden"]`; nothing imports in reverse, so an external conda install of atlas/doctor is warden-optional. In-repo, warden is default-installed at feature level for atlas (AC-8) but is deliberately **not** a package run-dep
4. `pyforge-atlas` is a parallel reimplementation of Part 2, verified by `parity/` against frozen fixtures — the legacy pipeline stays authoritative (ADR-015)

**Detail**: no consolidated part-doc exists; see the per-product planning sets under `_bmad-output/projects/pyforge-{warden,atlas,herald,scribe,doctor}/planning-artifacts/`.

---

## 4. Cross-Cutting Concerns

### 4.1 Auth chain (`_http.py`)

Every outbound HTTP request from **Parts 1–3** routes through `.claude/skills/conda-forge-expert/scripts/_http.py` (1,024 LOC). Auth lives **entirely** here — the MCP server has zero auth code; every subprocess script imports `_http`. **Part 5 is outside this chain** (see § 4.7).

Two distinct chains, often conflated:

**SSL trust chain** — applied **once at process start** (`inject_ssl_truststore()`): `REQUESTS_CA_BUNDLE` / `SSL_CERT_FILE` → `truststore.inject_into_ssl()` → Python default (certifi).

**Auth chain** — per request (`auth_headers_for(url)`), **first match wins, branching on host**:

1. **`JFROG_API_KEY`** → `X-JFrog-Art-Api` header — **★ unconditional; applied to every host**
2. elif **`JFROG_USERNAME` + `JFROG_PASSWORD`** → `Authorization: Basic`
3. elif host is github.com / api.github.com → **`GITHUB_TOKEN` / `GH_TOKEN`** as **`Authorization: Bearer`**; falling back to `~/.netrc` Basic if neither is set
4. else (non-GitHub host) → **`~/.netrc`** (or `$NETRC`) → Basic
5. otherwise unauthenticated

`skip_auth=True` is the per-call-site opt-out for known-public endpoints — the documented stopgap "until a host allowlist lands".

> **Source defect (2026-07-25):** `_http.py`'s module-header docstring (lines 13–17) and `auth_headers_for`'s docstring (lines 190–193) **order the chain differently** (netrc-before-GitHub vs. GitHub-before-netrc). The implementation matches the *function* docstring; the module header is wrong and should be corrected at source.

**Per-host overrides** — **21 `<HOST>_BASE_URL` env vars**; every external host is redirectable as of v7.8.1:
- Conda + Python ecosystem: `CONDA_FORGE_BASE_URL`, `PYPI_BASE_URL`, `PYPI_JSON_BASE_URL`, `S3_PARQUET_BASE_URL`, `ANACONDA_API_BASE_URL` (legacy alias `ANACONDA_API_BASE`).
- Git forges: `GITHUB_BASE_URL`, `GITHUB_RAW_BASE_URL`, `GITHUB_API_BASE_URL` (covers REST + GraphQL — GHES set to `https://<ghes>/api`), `GITLAB_API_BASE_URL`, `CODEBERG_API_BASE_URL`.
- Phase L registries: `NPM_BASE_URL` (also honors npm CLI's `npm_config_registry`), `CRAN_BASE_URL`, `CPAN_BASE_URL`, `LUAROCKS_BASE_URL`, `CRATES_BASE_URL`, `RUBYGEMS_BASE_URL`, `MAVEN_BASE_URL`, `NUGET_BASE_URL`.
- Vulnerability scanning: `OSV_API_BASE_URL`, `OSV_VULNS_BUCKET_URL`.

Full table with use sites + JFrog mirror patterns in [deployment-guide.md § 2b](./deployment-guide.md).

**The JFROG_API_KEY cross-host leak** is the system's most consequential security constraint, and it is **still UNRESOLVED in `_http.py`** as of 2026-07-25. Mitigation patterns documented in 3 places (CLAUDE.md, project-context.md, deployment-guide.md). Architectural fix deferred to v2 ([Q-PRD-02 in PRD](./PRD.md)). Part 5's `pyforge-atlas` did not inherit the defect — see § 4.7 and ADR-015.

### 4.2 Pixi env contract

**18 envs** declared in `pixi.toml`, in **two families**. The isolation is itself an architectural contract: it is what lets `pyforge-atlas` and `pyforge-doctor` require Python ≥3.14 while warden/herald/scribe require ≥3.12 and the factory runs 3.12.

**Family 1 — 9 factory envs** (compose shared features; inherit the fat default `[dependencies]`):

| Env | Used by | Purpose |
|---|---|---|
| `local-recipes` (default) | Parts 1, 2, 3 | Primary operational env; exposes **111** tasks (its own 106 + grayskull's 4 + conda-smithy's 1) |
| `vuln-db` | Parts 1, 2 (vuln-specific only) | AppThreat vdb (Phase G/G', `scan_for_vulnerabilities`) |
| `grayskull` | Part 1 (`generate_recipe_from_pypi`) | PyPI→conda recipe scaffolding |
| `conda-smithy` | Part 1 (lint) | `conda-smithy recipe-lint` |
| `build` | Part 1 (cross-platform features) | rattler-build features |
| `gcloud` | Part 2 (Phase P) | gcloud-sdk for BigQuery PyPI download counts |
| `linux`, `osx`, `win` | Part 1 (per-platform builds) | Platform-specific configurations |

**Family 2 — 6 product envs**, every one `no-default-feature = true`:

| Env | Carries |
|---|---|
| `pyforge-warden` | built `pyforge-warden` + its conda run-deps + pytest |
| `pyforge-atlas` | built `pyforge-atlas` (Kedro/Dagster stack) — the env bmad-loop worktrees materialize |
| `pyforge-doctor` | built `pyforge-doctor` + jsonschema + pytest |
| `pyforge-scribe` | built `pyforge-scribe` + typer/pydantic + pytest |
| `pyforge-herald` | built `pyforge-herald` + mcp + pytest |
| `bmad-ui` | locally-built `bmad-dashboard` + `mybmad-dashboard` (consume-not-submit mirrors) |

**Why `vuln-db` separate**: AppThreat pulls ~500MB of CVE feeds; keeping the default env lean.

**Why `no-default-feature` on all six**: excluding the fat default `[dependencies]` (python 3.14 + pixi + conda + pip + uv) is what makes the product envs cheap enough for per-story loop worktrees, and what decouples their Python floors.

**Failure mode to respect**: a cross-env dependency union silently drops deps. It has broken `main` **twice** — PRs #113 and #115 each restored deps a manifest union had dropped. Treat env membership as a contract, not a convenience.

### 4.3 Shared data directory

`.claude/data/conda-forge-expert/` (gitignored) is the single source of mutable state for Parts 1–3:
- `cf_atlas.db` + WAL/SHM — Part 2 primary artifact
- `cf_atlas_meta.json` — atlas run metadata
- `cf-graph-countyfair.tar.gz` — cf-graph offline snapshot
- `pypi_conda_map.json` — PyPI→conda cache
- `vdb/`, `vdb-cache/` — AppThreat vulnerability DB
- `cve/` — CVE feed cache
- `cache/parquet/` — Phase F S3 parquet cache (on demand)
- `inventory_cache/` — scan_project cache (on demand)

Refreshable via `bootstrap-data --fresh` (full) or `atlas-phase <ID>` (single).

> **[UNVERIFIABLE IN THIS CHECKOUT]** `.claude/data/conda-forge-expert/` **does not exist here** — it is gitignored and the atlas has never been built in this working tree. Every row-count, DB-size, and cache-freshness claim about it in this doc-set is therefore an assertion carried forward from a machine that had built it, not something re-verified on 2026-07-25. Rebuild-planning consequence: treat the schema (code) as ground truth and the data volumes as estimates.

### 4.4 Permission gates (Claude Code)

`.claude/settings.json` (committed) declares the global allow/deny lists.
`.claude/settings.local.json` (gitignored) accumulates user-approved namespaced tools (e.g., `mcp__conda_forge_server__submit_pr`).

Default allow-list includes:
- `Bash(rattler-build *)`, `Bash(pixi run *)`, `Bash(gh *)`, `Bash(git push *)`, `Bash(curl *)`
- `WebFetch` for github.com, pypi.org, anaconda.org
- `Skill(conda-forge-expert)` for primary skill activation

Default deny: `Bash(git push --force *)` and variants (`-f`, etc.).

### 4.5 Versioning surfaces

| Surface | Source | Bump trigger |
|---|---|---|
| Skill release | `.claude/skills/conda-forge-expert/CHANGELOG.md` TL;DR | PATCH (fixes), MINOR (gotchas/sections), MAJOR (breaking) — currently **v8.79.1** |
| Skill portability | `.claude/skills/conda-forge-expert/MANIFEST.yaml: version` | Install protocol changes (currently v7.0.0) |
| cf_atlas schema | `SCHEMA_VERSION` in `conda_forge_atlas.py` (line 139) | Every additive migration (currently **v29**) |
| BMAD installer | `_bmad/bmm/config.yaml` header (currently **v6.10.0**) | `bmad-method` package upgrade |
| Part 5 packages | per-package `pyproject.toml: version` (5 independent surfaces) | Product semver, independent of the skill release line |
| Report schemas | `$id`-carrying `report-schema.json` per product | Frozen contracts — a change is a consumer-visible break |
| Project-context pin | `_bmad-output/projects/local-recipes/project-context.md:last_synced_skill_version` | Triggers re-sync when skill MINOR exceeds pin |

### 4.6 Spec-surface governance

`scripts/spec_surface_check.py` enforces two properties over `git ls-files`, and this is the strongest structural invariant in the repo:

- **coverage** — every tracked file matches ≥1 spec `surface:` glob (declared in `SPEC.md` frontmatter) **or** an entry in `scripts/spec_surface_allowlist.txt`, where every entry is reason-tagged and printed. No silent exemptions.
- **drift** — a governed file's content changed (vs. the committed baseline `scripts/.spec-surface-baseline.json`) while its spec's `.memlog.md` did **not** move. That is code drifting out from under its contract; reconcile by re-deriving the spec, then `--write-baseline`.

Specs are keyed **`<project>/<spec>`**, never the bare directory name: the same slug legitimately exists in two projects, and a bare-name key silently dropped one surface. The checker **exits non-zero on any finding** — the design rule is "never false-green".

Live (2026-07-25): **22 specs · 7,888 tracked files · 6,323 governed · 1,567 allowlisted** (43 allowlist entries, glob-expanded).

### 4.7 Where Part 5 deliberately does *not* connect

The most instructive thing about the fifth part is what it refuses to inherit:

- **Not the auth chain.** `pyforge-atlas`' `conf/base/catalog.yml` header states the legacy `_http.py` global credential injection is **"FIXED, not ported"** — no global injection exists; credentials attach per-dataset, only where the destination host requires them. This is the cleanest live example of a cross-part contract deliberately not inherited.
- **Not the shared data directory.** Part 5's atlas writes Parquet under its own `data/<layer>/<dataset>/`, not `.claude/data/conda-forge-expert/`.
- **Not the MCP server.** It ships its own, additive.
- **Not the default env.** Six `no-default-feature` envs, no dependency on the factory's fat default.

What it *does* share: the pixi workspace, the `pyforge` namespace, and the parity fixtures binding it to Part 2's behaviour.

---

## 5. Data Architecture

The system now has **two** data stores with different shapes: the legacy row-store (§ 5.1) and the reimplementation's columnar store (§ 5.4). They are not layered — they are parallel, and the legacy one is authoritative.

### 5.1 cf_atlas.db (primary data store)

21 tables + **5 views** (schema v29). *(This doc previously understated the view count by one — it was wrong from the moment schema v29 added `v_pypi_intelligence_valid`.)*

```
packages                       — 60+ columns; row per conda package
maintainers                    — feedstock maintainer registry
package_maintainers            — many-to-many join
meta                           — schema_version, last_full_run, etc.
phase_state                    — checkpoint cursors per phase (v7.7+)
dependencies                   — Phase J output (source → target deps)
vuln_history                   — Phase G' snapshots over time
package_version_downloads      — Phase F per-version downloads
package_platform_downloads     — Phase F+ per-platform downloads (v8.18.0)
package_python_downloads       — Phase F+ per-Python downloads (v8.18.0)
package_channel_downloads      — Phase F+ per-channel downloads (v8.19.0)
upstream_versions              — Phase H + K + L (multi-source)
upstream_versions_history      — audit trail of upstream_versions writes
package_version_vulns          — Phase G' per-version CVE scoring
pypi_universe                  — Phase D PyPI reference set (v7.9.0)
pypi_universe_serial_snapshots — Phase O serial deltas (v8.1.0)
pypi_intelligence              — Phase O/P/Q/R/S enrichment (v8.1.0)
pypi_downloads_daily           — Phase P incremental download counts (v8.15.0)
cisa_kev / cwe_categories / epss_scores — CVE-scoring reference feeds
# the 5 views (complete list, verified from CREATE VIEW statements):
#   v_actionable_packages, v_pypi_candidates, v_pypi_intelligence_valid,
#   v_packages_enriched, v_current_version_vulns
```

WAL mode for concurrent reads. Indexes on `packages.{relationship, match_source, pypi_name, conda_name, feedstock_name, license}` + per-table dimensions.

**Migration discipline**: additive only; `init_schema()` idempotent on every connection open.

**[UNVERIFIABLE IN THIS CHECKOUT]** the `.db` file itself is absent (§ 4.3). Table/view counts above come from the `CREATE TABLE` / `CREATE VIEW` statements in `conda_forge_atlas.py`, which *is* verifiable; row counts are not.

### 5.2 Out-of-band data files

| File | Location | Purpose |
|---|---|---|
| `build_summary.json` | Repo root | Build outcome (status, artifacts, log path) |
| `build.pid` | Repo root | Active build process ID |
| `cf-graph-countyfair.tar.gz` | `.claude/data/conda-forge-expert/` | cf-graph offline snapshot |
| `pypi_conda_map.json` | `.claude/data/conda-forge-expert/` | PyPI→conda name cache |

### 5.3 Data flow patterns

**Pattern 1: Recipe authoring**
```
generate_recipe_from_pypi → recipes/<pkg>/recipe.yaml (new)
                          → pypi_conda_map.json (read)
                          → grayskull (subprocess in grayskull env)
                          → templates/ (read)

edit_recipe → recipes/<pkg>/recipe.yaml (mutate)

validate_recipe → recipes/<pkg>/recipe.yaml (read)
                → rattler-build --render (subprocess)
                → JSON stdout

trigger_build → recipes/<pkg>/ (read)
              → build-locally.py / Docker (subprocess)
              → build_artifacts/<config>/ (write)
              → build_summary.json (write at end)
              → build.pid (write at start, clean at end)
```

**Pattern 2: Atlas refresh**
```
bootstrap-data → mapping_manager (pypi_conda_map.json write)
              → cve_manager (cve/ feed write)
              → vdb refresh (vdb/, vdb-cache/ write)
              → conda_forge_atlas.py:
                   Phase B → packages table (insert/update)
                   Phase B.5/B.6 → packages columns (update)
                   ...
                   Phase N → packages.gh_* columns (update)
              → phase_state table (cursor + status writes)
```

**Pattern 3: Atlas query**
```
staleness-report / behind-upstream / feedstock-health / etc.
   → cf_atlas.db read-only query
   → JSON stdout

(Via MCP server)
   @mcp.tool → subprocess to Tier 1 script → JSON parse → MCP runtime
```

### 5.4 pyforge-atlas store (Part 5, parallel)

The reimplementation does **not** write `cf_atlas.db`. Its shape:

```
conf/base/catalog.yml (800 lines)      — the dataset contracts; per-dataset credentials only
        │
        ▼
data/<layer>/<dataset>/*.parquet       — columnar, layered (Kedro convention)
        │
        ▼
Ibis expression  ──▶  DuckDB engine    — AD-4: "Ibis → DuckDB ONLY", at QUERY time
        │
        ▼
semantic/metrics.py                    — the single owned metric surface
```

Two properties that matter for a rebuild:

1. **There is no persisted `.duckdb` file.** DuckDB is an execution engine over Parquet, never a store. Anyone who "finds the missing database" has misread the design.
2. **Parity, not migration.** `parity/{frame_diff,evidence,legacy_surface}.py` plus frozen per-node JSON fixtures compare the reimplementation's frames against the legacy pipeline's outputs. The fixtures are the contract; the legacy store stays authoritative until parity says otherwise. See ADR-015.

---

## 6. Architecture Decision Records (ADRs)

Key technical decisions, captured in ADR-lite format. Each is a candidate for `bmad-architecture` decision-rationale expansion.

ADR-001…012 are **historical records and are preserved as written**; where a stated fact has since become false, the correction is called out inline as a dated **Correction (2026-07-25)** note rather than by rewriting the decision. ADR-013…017 are new, and all five come from the fifth part and its governance.

### ADR-001: rattler-build, not conda-build

- **Context**: conda-forge supports both v0 (conda-build, `meta.yaml`) and v1 (rattler-build, `recipe.yaml`); rattler-build is the future direction
- **Decision**: use rattler-build exclusively for new recipes; conda-build only for v0 migration source
- **Consequence**: all new recipes are v1; templates ship in both formats but v1 is canonical; migration is a one-time move per recipe

### ADR-002: Pixi as the sole env manager

- **Context**: previously the repo used conda environments; transition was already underway
- **Decision**: standardize on Pixi; no conda env, no venv, no manual env setup
- **Consequence**: 9 declared pixi envs; activation via pixi shell hooks; CI uses pixi too
- **Correction (2026-07-25)**: **18 envs**, not 9 — the six product envs of ADR-014 were added. The decision itself (pixi as sole env manager) held, and in fact hardened: pixi is now also the *build* backend for Part 5 via `preview = ["pixi-build"]`.

### ADR-003: SQLite (single file) for cf_atlas

- **Context**: atlas data is ~800k rows; could use Postgres, DuckDB, parquet, or SQLite
- **Decision**: SQLite WAL mode for atlas storage
- **Consequence**: single-file portability; no DB server; reads concurrent; writes serialize; fine for offline-tolerant model where atlas refresh is batch
- **Correction (2026-07-25)**: the "~800k rows" figure is **[UNVERIFIABLE]** here — `.claude/data/conda-forge-expert/` is absent from this checkout. Also, the rejected alternatives were not rejected forever: ADR-015's reimplementation chose exactly the **parquet + DuckDB** option this ADR passed over. ADR-003 remains correct *for Part 2*; it no longer describes the whole system.

### ADR-004: multi-phase atlas pipeline (not monolithic)

- **Context**: atlas refresh could be one monolithic script or split into stages
- **Decision**: named phases with explicit dependency order, independently re-runnable (founded as 17 phases B → N; grown to 22 with O/P/Q/R/S for the PyPI intelligence layer)
- **Consequence**: mid-run kill is cheap (TTL gates + checkpoint); operators can refresh single phase via `atlas-phase <ID>`; pipeline is auditable
- **Correction (2026-07-25)**: precise phrasing is **22 executable, 23 cataloged** (the 23rd is the runner-less conceptual "Phase I"). Never state a bare phase count of 23 — and note `bmad-groundtruth` reports 23 for an unrelated reason (its `def phase_` regex catches the helper `phase_r_upsert_one`). Part 5 re-expresses these 22 phases as **7 Kedro pipelines**, a regrouping, not a renumbering.

### ADR-005: `current_repodata.json` over py-rattler sharded

- **Context**: Phase B needs to enumerate conda-forge packages; py-rattler has a sharded protocol; or fetch `current_repodata.json` directly
- **Decision**: use direct `current_repodata.json` fetch (5 subdirs)
- **Consequence**: bypasses 502 errors py-rattler hit (2026-Q1); air-gappable; ~5 min one-time fetch; loses outdated package versions (Phase B.6 catches removals)

### ADR-006: MCP server via FastMCP, subprocess-wrapper pattern

- **Context**: expose Python scripts as MCP tools; could use direct import or subprocess
- **Decision**: FastMCP server with subprocess invocations to Tier 1 scripts
- **Consequence**: ~200-400ms overhead per call (acceptable for interactive use); process isolation; timeout enforcement; pixi env consistency via `_PYTHON = sys.executable`
- **Correction (2026-07-25)**: the pattern held so well it was adopted a second time — `pyforge-atlas` ships its **own** 11-tool FastMCP server. There are now **two MCP surfaces**, additive and non-overlapping; conflating them (e.g. quoting "57 tools") is an error. Transport for both is stdio; the legacy server is registered in `~/.claude.json`, not in-repo — there is no `.mcp.json` and `.claude/settings.json` has no `mcpServers` block.

### ADR-007: Three-tier script architecture (canonical + wrapper + data)

- **Context**: scripts could be inlined into MCP tools, or split
- **Decision**: Tier 1 (canonical Python) + Tier 2 (CLI wrappers) + Tier 3 (data state) with meta-test enforcing the three-place rule
- **Consequence**: clear separation of concerns; multiple call paths supported (pixi tasks, MCP tools, direct imports); discipline enforced by `test_all_scripts_runnable.py`

### ADR-008: BMAD↔CFE integration via CLAUDE.md prose rules

- **Context**: BMAD agents could call CFE via convention or enforcement
- **Decision**: codify in CLAUDE.md as Rule 1 (mandate invocation) + Rule 2 (mandate retro); no automated enforcement
- **Consequence**: relies on agents reading CLAUDE.md + project-context.md on spawn; reinforced by auto-memory entries; one-time per session; reviewer catches violations in PR review

### ADR-009: MINOR-version drift contract for project-context.md

- **Context**: project-context.md re-sync cadence vs. skill release cadence
- **Decision**: re-verify project-context.md on every skill CHANGELOG MINOR bump; PATCH bumps do not trigger re-sync
- **Consequence**: balanced overhead — major changes get re-sync, fixes don't churn the rulebook; frontmatter pin makes drift visible

### ADR-010: JFROG_API_KEY mitigation via env-var hygiene, not architectural fix

- **Context**: `_http.py` injects the header on every host when `JFROG_API_KEY` is set
- **Decision**: document subshell mitigation patterns in 3 places; architectural fix deferred to v2
- **Consequence**: operator discipline is the security boundary; rebuild includes this constraint as P0 documentation, not P0 code; ADR will be revisited in v2
- **Status (2026-07-25)**: **still unresolved in `_http.py`** — the deferral has now outlived several release lines, which is itself the finding. The interesting development is that Part 5 declined to inherit the defect: `pyforge-atlas`' catalog states the global injection is "FIXED, not ported", using per-dataset credentials instead (ADR-015). A working fix therefore already exists in-repo; porting it back into `_http.py` is the outstanding v2 item, not designing it.

### ADR-011: Standalone-portable skill via MANIFEST.yaml + install.py

- **Context**: skill could be repo-locked or portable
- **Decision**: `MANIFEST.yaml` declares "standalone-portable" type; `install.py` bootstraps into other repos
- **Consequence**: skill can be reused across repos; install.py keeps in sync with skill's directory layout; portability is testable (rebuild target benefits)

### ADR-012: BMAD multi-project pattern with active-project resolution

- **Context**: this repo hosts 3 BMAD projects (`local-recipes`, `deckcraft`, `presenton-pixi-image`); separate repos would duplicate BMAD installation
- **Decision**: single BMAD install, multi-project layout under `_bmad-output/projects/<slug>/`, active-project resolution (CLI > env > marker > none)
- **Consequence**: one skill catalog benefits all projects; per-project artifact privacy is convention not enforcement; `scripts/bmad-switch --current` is the sanity check
- **Correction (2026-07-25)**: two things in this ADR are now false. (1) **14 projects**, not 3 — the eight `pyforge-*` product projects plus `unity-data-stack` and `wasm-analytics-stack` joined the original three. (2) The stated resolution chain is **incomplete in a way that has caused a near-miss**: `_bmad/bmm/config.yaml` hard-codes `planning_artifacts` to `_bmad-output/planning-artifacts`, a gitignored **symlink**, and that key does *not* compose with a project's `output_folder` override. So the marker governs config resolution while the **symlinks govern where every write-skill actually writes**. On 2026-07-14 the two disagreed (symlinks on `pyforge-warden`, marker on `local-recipes`) and a routine doc re-sync would have overwritten another project's PRD/epics/architecture. `bmad-switch` was hardened to re-point symlinks atomically and write the marker last; `--current`/`--list` warn on desync. See ADR-017 for the parallel-agent consequence.

### ADR-013: PEP 420 implicit namespace for the five product packages

- **Context**: five distributions (`pyforge-{warden,atlas,herald,scribe,doctor}`) must be installable independently — from conda, from PyPI, or from the local pixi workspace — yet present as one coherent `pyforge.*` import root. The classic options are a single mega-package, `pkgutil`-style namespace shims, or PEP 420 implicit namespaces.
- **Decision**: PEP 420 implicit namespace. **No distribution ships `src/pyforge/__init__.py`.** Each is hatchling-built with its own `[package]` `pixi.toml` (a pixi workspace member) and no `[workspace]` table of its own.
- **Consequence**: `pyforge.atlas`, `.doctor`, `.herald`, `.scribe`, `.warden` coexist in one import root no matter which subset is installed. The cost is that the *absence* of a file is load-bearing — adding `src/pyforge/__init__.py` to any one distribution silently shadows the others' subpackages. A rebuild must treat that absence as a tested invariant, not an oversight. Related: the root `[workspace]` sets `preview = ["pixi-build"]` and deliberately has **no `members` key** — pixi through 0.72.2 has no such key, and members are declared via path dependencies (a comment in `pixi.toml` records this, answering a review suggestion that proposed otherwise).

### ADR-014: product-env isolation via `no-default-feature`

- **Context**: `pyforge-atlas` and `pyforge-doctor` require Python **≥3.14**; `pyforge-warden`, `-herald`, `-scribe` require **≥3.12**; the factory runs 3.12. One shared solve cannot satisfy all of these, and per-story `bmad-loop` worktrees must materialize an env cheaply enough to be worth isolating.
- **Decision**: give each product its own pixi env with `no-default-feature = true`, excluding the fat default `[dependencies]` (python 3.14 + pixi + conda + pip + uv). Six such envs (five products + `bmad-ui`), alongside the nine factory envs — **15 total**.
- **Consequence**: divergent Python floors coexist without a lockfile fight; loop worktrees materialize a lean env rather than the fat `local-recipes` one. The isolation is a *contract*, not a convenience: a cross-env dependency union silently drops deps, and has broken `main` **twice** (PRs #113 and #115 each restored dropped deps). Any tooling that "simplifies" the manifest by unioning features will reintroduce that failure.

### ADR-015: `pyforge-atlas` is a parallel reimplementation, not a replacement

- **Context**: Part 2's `conda_forge_atlas.py` works and is depended on by the whole factory, but is a single-file phase orchestrator over SQLite. A Kedro/Dagster/Parquet rebuild offers modularity and lineage — at the risk of a big-bang cutover against an unproven equivalent.
- **Decision**: build the new pipeline **alongside** the old one and bind them with a verification contract rather than cutting over. The v8.79.0 CHANGELOG states it explicitly: it "is a parallel reimplementation, not a replacement of `conda_forge_atlas.py`… authored no conda recipes and changed no operational guidance." Legacy stays authoritative.
- **Consequence**: (a) `parity/{frame_diff,evidence,legacy_surface}.py` plus frozen per-node JSON fixtures are the binding artifact — parity is the gate for any future cutover. (b) Two data stores coexist by design: SQLite (legacy, authoritative) and Parquet-read-by-Ibis→DuckDB (new; **no persisted `.duckdb`**, AD-4). (c) Dagster is quarantined to `orchestration/definitions.py`, the only module allowed to import `dagster`/`kedro_dagster` (AD-1/AD-6). (d) Most consequentially, the reimplementation **fixed rather than ported** the `_http.py` global credential injection — its `conf/base/catalog.yml` header says "FIXED, not ported", with per-dataset credentials only. A reimplementation is the cheapest place to shed an inherited defect, and this is the live example.

### ADR-016: spec-surface governance — every tracked file is governed or explicitly exempt

- **Context**: a spec-driven repo drifts in two directions: new files appear that no spec claims, and governed files change without their spec moving. Neither is visible in review.
- **Decision**: `scripts/spec_surface_check.py` enforces **coverage** (every tracked file matches a spec `surface:` glob or a reason-tagged entry in `scripts/spec_surface_allowlist.txt`) and **drift** (a governed file cannot change while its spec's `.memlog.md` stays still) against the committed baseline `scripts/.spec-surface-baseline.json`. Exit non-zero on any finding.
- **Consequence**: "never false-green" is the design rule — the checker fails rather than passes on ambiguity, and there are **no silent exemptions** (every allowlist entry carries a printed reason). Specs are keyed **`<project>/<spec>`**, never the bare directory name, because the same slug legitimately exists in two projects and a bare-name key silently dropped one surface — a bug worth recording, since it is the exact class of failure the checker exists to catch. Live: 22 specs · 7,888 tracked files · 6,323 governed · 1,567 allowlisted. Corollary for authors: adding a file to `planning-artifacts/` that no spec surface claims is a HARD `uncovered` finding, so new artifacts must land inside an existing governed surface.

### ADR-017: parallel agents address projects by physical path; `bmad-switch` is forbidden

- **Context**: the active-project switch is per-working-tree **global state** — a marker file plus two symlinks (ADR-012 correction). With one agent that is a convenience. With N agents in one tree it is a mutex nobody holds: agent A switches, agent B writes, and B's artifacts land in A's project.
- **Decision** (HARD rule, 2026-07-25): parallel agents **address projects by physical path** (`_bmad-output/projects/<slug>/…`) and **never call `scripts/bmad-switch`**. Interactive single-agent sessions may still switch, and must do so only via `bmad-switch` (never by hand-editing the marker), because it re-points the symlinks atomically and writes the marker last so a failed re-point cannot desync.
- **Consequence**: reading another project's artifacts never requires switching. The rule is prose-enforced (like ADR-008's Rules 1+2) — there is no lock — so it is stated in CLAUDE.md and in every parallel-agent brief. The 2026-07-14 near-miss (§ ADR-012 correction) is the evidence for why the weaker "just check `--current` first" convention was insufficient.

---

## 7. Quality Attributes

### 7.0 Deployment reality (the constraint under everything below)

**Exactly one thing deploys**: the **Guildhall** dashboard (`docs/dashboard/`) to GitHub Pages at https://rxm7706.github.io/local-recipes/ via `.github/workflows/dashboard.yml`, which regenerates `data.js` from git history at deploy time. There is **no production Dockerfile, no Helm chart** (`helm/lasuite-docs/values.yaml` is a values file with no chart and no apply step), and **no k8s manifests outside test fixtures**. As of 2026-07-26 (PR #127) there is **no feedstock-creation workflow at all** — the inherited `create_feedstocks.yml` was hard-gated to `github.repository == 'conda-forge/staged-recipes'` (a permanent no-op here) and has been deleted, following upstream, which moved it to `conda-forge/admin-requests` in 2025.

Everything else in this architecture is **operator-invoked local tooling**. Availability, performance and rollback targets below should be read in that light: there is no service to keep up.

**CI gates that every PR must satisfy** (the inherited staged-recipes linter, `.github/workflows/scripts/linter.py`, exits 1 on either):
1. **Any file changed outside `recipes/`** unless the PR carries the **`maintenance` label**.
2. **`environment.yaml` out of sync with `pixi.toml`** — an exact `.rstrip()` string comparison against `pixi project export conda-environment -e build`. This check is **ungated by the label**.

The workflow re-triggers on `labeled` / `unlabeled` for exactly this reason. Any change to Part 4 or Part 5 is by definition outside `recipes/` and therefore needs the label; any change to `pixi.toml` (which every Part 5 env change is) also needs the export regenerated and committed.

### 7.1 Availability

- **MCP servers**: the legacy server is auto-started by Claude Code at session boot; graceful tool-call failures (returns `{"error": "..."}` instead of crashing). Registration lives in `~/.claude.json`, so a fresh clone does **not** get the server — that is a rebuild gap, not a defect
- **Atlas pipeline**: TTL gates + checkpointing → mid-run kills don't lose work
- **Recipe lifecycle**: each step is independently re-runnable; loops cap at 3 cycles before escalation
- **Part 5 products**: CLIs, not services. Availability is "the env solves"; the failure mode is a dropped dependency (§ 4.2), not downtime

### 7.2 Performance

| Operation | Target | Current |
|---|---|---|
| Single MCP tool call (subprocess overhead) | ≤500 ms | ~200-400 ms |
| `validate_recipe` | ≤5 s | varies; typically <3 s |
| `optimize_recipe` (17 checks) | ≤2 s | typically <1 s |
| `atlas-phase F` warm (parquet cache hit) | ≤30 s | ~10-15 s |
| `atlas-phase H` cold (cf-graph) | ≤60 s | ~30 s |
| `bootstrap-data --fresh` (auto-mode) | ≤90 min | ~30-45 min |
| `pixi run validate -- recipes/<pkg>` | ≤5 s | typically <3 s |

**[UNVERIFIABLE IN THIS CHECKOUT]** every "Current" figure in this table depends on a built `.claude/data/conda-forge-expert/` (absent — § 4.3). They are carried forward unmeasured; re-measure before treating any of them as a regression baseline.

### 7.3 Reliability

- **Part 1**: 100 test files in `tests/{unit,integration,meta}/` on `pixi run test`
- **Part 5**: **2,539 `def test_` across 188 test files** (warden 1,575/65 · atlas 772/110 · herald 112/5 · doctor 62/6 · scribe 18/2) — the products carry far more test mass than the factory, and `pyforge-warden` gates itself (self-dogfooding)
- Meta-tests enforce structural invariants (`test_recipe_yaml_schema_header.py`, `test_all_scripts_runnable.py`, `test_bmad_artifacts_in_sync.py`)
- Schema migrations are additive and idempotent
- TTL gates prevent re-fetch of fresh data
- Build failure protocol caps loops at 3 iterations
- **Governance gate**: `spec_surface_check.py` exits non-zero on any coverage or drift finding (§ 4.6) — never false-green

### 7.4 Security

- **Permission gates**: Claude Code's `.claude/settings.json` allow/deny lists
- **No secrets in code**: env vars only (`JFROG_API_KEY`, `JFROG_USERNAME`/`JFROG_PASSWORD`, `GITHUB_TOKEN`/`GH_TOKEN`, `GEMINI_API_KEY`)
- **JFROG_API_KEY cross-host leak**: **still unresolved in `_http.py`**; mitigated only by subshell scoping (documented in 3 places). Part 5's atlas fixed it at the design level with per-dataset credentials (ADR-015) — the fix exists, the backport does not
- **GitHub `--force` push denied** in default permissions; `--force-with-lease` only
- **No outbound network without `_http.py`** — true for Parts 1–3. **Part 5 is a second, independent egress path** with its own credential model; a security review must cover both
- **Gate independence**: the doctrine "the hand that builds is never the gate that judges" is realized structurally — each product's exit-code projection lives in a single owner module (`verdict.py`), separate from the code that produces findings

### 7.5 Maintainability

- **Tier discipline**: meta-test enforces three-place rule for new scripts
- **Documentation cadence**: every BMAD effort runs a retro that updates SKILL.md / reference/ / guides / CHANGELOG
- **Schema migrations**: additive only; rerun-safe
- **Per-section sync tags**: project-context.md `(Sync: ...)` annotations point at upstream sources
- **Spec-surface coverage**: no tracked file is unowned; drift against a still `.memlog.md` is a finding (§ 4.6)
- **Deterministic harness**: `bmad-loop` runs DEV → VERIFY → REVIEW → VERIFY → COMMIT in fresh tmux sessions with worktree isolation, squash merges, and mandatory `--frozen` verify commands. The harness is deliberately **not a skill** — Skills are the unit of execution, the harness is the unit of governance

### 7.6 Portability

- **Skill**: `MANIFEST.yaml` declares standalone-portable; `install.py` bootstraps
- **Atlas (Part 2)**: SQLite single-file; relocatable
- **Products (Part 5)**: hatchling wheels with declared `requires-python` and extras — installable outside this repo entirely, which is the point of the one-directional `gate = ["pyforge-warden"]` edges (atlas/doctor stay warden-optional for an external consumer)
- **Air-gap**: all Part 1–3 workflows function offline given proxy/mirror infrastructure (21 `*_BASE_URL` overrides)
- **No host-specific assumptions**: Linux/macOS/Windows all supported for builds (cross-compile from Linux to osx via SDKs/)
- **Known path constraint**: long working-directory paths panic pixi-build-python 0.8.3, which is why loop homes moved to `~/.bmad-loops/<slug>` (`BMAD_LOOP_HOME_ROOT` overrides)

---

## 8. Risks & Mitigations

(Distilled from PRD § 10 and integration architecture)

| Risk | Mitigation in architecture |
|---|---|
| JFROG_API_KEY cross-host leak | Subshell scoping pattern; documented in 3 places; ADR-010. **Unmitigated in code** — a working per-dataset design exists in Part 5 and should be backported |
| Phase H "hangs" UX | 60s heartbeat + capped progress cadence (v7.7.0) |
| Phase K secondary rate-limit | Deferred work; cron with `--reset-ttl` spreads load |
| Schema drift on stale DBs | `init_schema()` idempotent on every connection open |
| MCP server crash from bad Tier 1 script | Subprocess isolation; `_run_script` catches exceptions |
| BMAD agent ignores integration rules | Auto-memory feedback entries reinforce; reviewer catches in PR |
| Recipe corpus growth (now **1,664**) | Out of scope for rebuild; atlas tracks growth automatically |
| **Cross-env dependency union drops deps** | Env membership is a contract (ADR-014); has broken `main` twice (PRs #113, #115). No automated detector — review manifest unions explicitly |
| **Namespace collision from a stray `src/pyforge/__init__.py`** | ADR-013: the file's absence is load-bearing; a rebuild must assert it, because the failure is silent shadowing, not an import error |
| **Marker/symlink desync sends a write-skill to the wrong project** | `bmad-switch` re-points symlinks atomically and writes the marker last; `--current`/`--list` warn. Parallel agents avoid the state entirely (ADR-017). Near-miss on 2026-07-14 |
| **Two MCP surfaces get conflated** | Documented as separate and additive (46 legacy + 11 atlas); never quote a combined tool count |
| **Parity fixtures rot while the legacy pipeline moves** | `parity/` fixtures are frozen and diffed per node; a legacy change that breaks parity is a finding, not a silent divergence (ADR-015) |
| **PR reds on the inherited linter** | Pre-empt at PR-open: `maintenance` label for any non-`recipes/` change, and regenerate `environment.yaml` whenever `pixi.toml` moves (§ 7.0) — the env-sync check is ungated by the label |
| **Long paths panic pixi-build-python 0.8.3** | Loop homes at `~/.bmad-loops/<slug>`; `BMAD_LOOP_HOME_ROOT` overrides |

---

## 9. Build Order (Dependency-Driven)

Rebuild MUST follow this order:

```
1. Bootstrap → pixi.toml + 9 FACTORY envs + Python 3.12 + pyproject.toml
   1a. [workspace] preview = ["pixi-build"], no `members` key (path deps only)
   1b. environment.yaml exported from the `build` env (CI gate — § 7.0)
                ↓
2. Part 4: BMAD installer → _bmad/ (6.10.0) + _bmad/scripts/ + 89 skills
   + scripts/bmad-switch + the marker AND the two planning/implementation symlinks
                ↓
3. Part 1: conda-forge-expert skill
   3a. _http.py (every other module imports it)
   3b. name_resolver.py + mapping_manager.py (helpers)
   3c. Recipe lifecycle scripts (recipe-generator, validate, edit, etc.)
   3d. SKILL.md + reference/ (15) + guides/ (9) + quickref/ (2) + INDEX.md
   3e. Templates (41 files / 13 ecosystems)
   3f. Tier 2 wrappers (57 files)
   3g. Pixi tasks (106 in the local-recipes feature; 111 visible in the env)
   3h. Meta-test (test_all_scripts_runnable.py)
                ↓
4. Part 2: cf_atlas (within Part 1's scripts/)
   4a. Schema (init_schema, 21 tables + 5 views, SCHEMA_VERSION=29)
   4b. Phase B (foundational; every other phase depends on it)
   4c. Phase D (PyPI enumeration; Phase C/C.5 join B and D)
   4d. Phase E + E.5 (cf-graph tarball; M depends on this)
   4e. Phases F, G, G', H, J, K, L, M, N, O, P, Q, R, S (any order)
   4f. CLI wrappers (17 entries) + pixi tasks
   4g. Per-phase tests + TTL-gate test + checkpoint test
                ↓
5. Part 3: MCP server
   5a. conda_forge_server.py with FastMCP("conda-forge-expert")
   5b. 46 @mcp.tool() registrations (44 sync + 2 async), stdio transport
   5c. _run_script helper (sys.executable; 120 s default, 600 s for update_cve_database)
   5d. Out-of-band state file paths
   5e. (Optional) gemini_server.py + mcp_call.py
   5f. Registration in ~/.claude.json — NOT in-repo; a fresh clone has no server
                ↓
6. Part 5: pyforge-packages  (depends on 1 for the workspace, on 2 only for parity fixtures)
   6a. src/shared/packages/<dist>/pyproject.toml + [package] pixi.toml per dist
       — and NO src/pyforge/__init__.py anywhere (ADR-013)
   6b. 6 product envs, every one no-default-feature = true (ADR-014)
   6c. pyforge-warden FIRST: it is the gate the others declare as an extra
       (frozen report-schema.json + verdict.py + 1,575 tests)
   6d. pyforge-atlas: 7 Kedro pipelines, catalog.yml contracts, Dagster confined
       to orchestration/definitions.py, parity/ + frozen fixtures, 11-tool MCP server
   6e. pyforge-herald / -scribe / -doctor (independent; doctor needs warden's schema
       shape as its consolidation target, not its code)
   6f. Regenerate + commit environment.yaml — every pixi.toml change trips the
       ungated CI sync check (§ 7.0)
                ↓
7. Governance: spec surfaces + baseline
   7a. SPEC.md `surface:` globs covering every tracked file
   7b. scripts/spec_surface_allowlist.txt (reason-tag every entry)
   7c. scripts/.spec-surface-baseline.json via --write-baseline
                ↓
8. Documentation + project-context.md
   8a. CLAUDE.md (repo-wide guidance + BMAD↔CFE integration rules + the CI-gate rule)
   8b. AGENTS.md + per-tool pointers (cross-tool entry point)
   8c. project-context.md (foundational rules; sync_sources + last_synced_skill_version pin)
   8d. docs/dreams/* (Tier 0 — 26 Dreams) then the Tier 2 Specs derived from them
   8e. docs/reference/* (mcp-server-architecture, enterprise-deployment, developer-guide,
       library-llms-full)
   8f. docs/specs/* — LEGACY Tier 1 (19 files, phasing out; author no new ones)
                ↓
9. Tests + meta-tests + spec_surface_check run clean
                ↓
10. CI pipelines (.github/workflows/* — 8 active; dashboard.yml is the only deploy,
    and no workflow creates feedstocks or publishes packages)
                ↓
11. Air-gap deployment validation (full atlas build + recipe submission with JFrog endpoints)
```

This is the **canonical build order**. Skipping or reordering risks integration breakage. Per `project-parts.json` `rebuild_dependencies.build_order` (which predates Part 5 and step 7 — treat this section as the current one).

**Why Part 5 comes after Part 2**: not for code (it imports nothing from the factory), but because its `parity/` fixtures are defined against the legacy pipeline's output. Build the thing being verified before the verifier.

---

## 10. Glossary

(See `PRD.md` Appendix A for the product glossary. The terms below are the **identity and governance vocabulary**, binding on every artifact in this repo — source: `docs/dreams/pyforge-charter.md` §§ Branding, The Lexicon.)

### 10.1 Branding law

**PyForge** is the brand, used in prose. **`pyforge`** lowercase is the *technical* form only — distributions, modules, slugs, paths, envs. Never brand-case a code identifier: it is `pyforge-warden` the dist and `pyforge.warden` the module, never "PyForge-Warden".

### 10.2 The seven Lexicon nouns

Each is a load-bearing separation of concerns; the chain reads forward as *authorization* and backward as *audit*.

| Noun | Unit of | Meaning here |
|---|---|---|
| **Charter** | legitimacy | Authorizes the workers. `docs/dreams/pyforge-charter.md` — mission, offices, doctrine, branding law. Changes by recorded amendment, never silent edit |
| **Spec** | contract | Governs the work. The five-field contract `## Why` / `## Capabilities` / `## Constraints` / `## Non-goals` / `## Success signal`, derived from an append-only `.memlog.md` and **re-rendered, never hand-patched**. The word **"kernel" is RETIRED** — do not use it for the Spec |
| **Guild** | body | The collective of agents and their shared conventions |
| **Smiths** | identity | The eight personas (= agents): **Herald · Marshal · Atlas · Warden · Mason · Doctor · Scribe · Steward**. Never "Forgemasters" |
| **Stations** | accountability | The offices a Smith is accountable for |
| **Skills** | execution | `.claude/skills/*` — the unit of *doing*. The deterministic harness (bmad-loop, sandbox/permission gates, CI verify gates) is the unit of *governance* and is deliberately **not a skill** |
| **Guildhall** | visibility | The program console — `docs/dashboard/`, deployed to GitHub Pages. The one deployed artifact |

**Mission lockup**: *Forging the Agentic SDLC — Humans Dream, Agents Deliver — Governed. Auditable. Production-ready.*

**Doctrine** (directly load-bearing for §§ 6–7): execution has **one owner** (Marshal); **the hand that builds is never the gate that judges** (realized structurally in the sole-owner `verdict.py` modules); Skills execute, the harness governs.

### 10.3 The tier model

| Tier | Location | Git | Count (2026-07-25) |
|---|---|---|---|
| **0 — Dream** | `docs/dreams/*.md` | tracked, permanent | 26 |
| **1 — Intake spec (LEGACY)** | `docs/specs/*.md` | tracked, phasing out | 19 |
| **2 — Spec & planning** | `_bmad-output/projects/<slug>/planning-artifacts/` | tracked, permanent — **the active contract** | 22 Specs |
| **3 — Execution output** | `_bmad-output/projects/<slug>/implementation-artifacts/` | **gitignored; nothing there may be tracked** | n/a |

- **Dream** (Tier 0) is the raw human aspiration and the mandatory starting point: no non-trivial effort begins without one, and BMAD produces the Spec *from* it.
- **Story specs are durable (tracked), NOT Tier-3** (convention since 2026-07-25). `bmad-loop` drafts one into the run's gitignored `implementation-artifacts/`; after the story merges it is **promoted into the tracked `planning-artifacts/specs/` subdir**. 63 such specs are tracked today. The motivating incident: pyforge-warden lost 13 of 31 story specs to worktree teardown before this convention existed.
- A tracked file under `implementation-artifacts/` is a HARD `tracked-impl-artifact` finding; a new uncovered file under `planning-artifacts/` is a HARD `uncovered` finding (§ 4.6).

### 10.4 Terms of art used in this document

- **Part** — one of the five top-level decompositions of § 3. Parts 1–4 are the factory; Part 5 is the product line.
- **Phase** — one atlas pipeline stage (Part 2). **22 executable, 23 cataloged.**
- **Tier 1 / Tier 2 / Tier 3 script** — canonical implementation / CLI wrapper / mutable data state (ADR-007). Unrelated to the Tier 0–3 *artifact* model above; the collision is historical, so always say which.
- **Gate** — an exit-code verdict produced by a `verdict.py`. Not a CI job.
- **Parity** — the frozen-fixture verification contract binding `pyforge-atlas` to `conda_forge_atlas.py` (ADR-015).

---

## 11. References

Authoritative sources:
- [PRD.md](./PRD.md) — product requirements
- [planning-artifacts/architecture-conda-forge-expert.md](./architecture-conda-forge-expert.md) — Part 1 detail
- [planning-artifacts/architecture-cf-atlas.md](./architecture-cf-atlas.md) — Part 2 detail
- [planning-artifacts/architecture-mcp-server.md](./architecture-mcp-server.md) — Part 3 detail
- [planning-artifacts/architecture-bmad-infra.md](./architecture-bmad-infra.md) — Part 4 detail
- **Part 5 has no consolidated part-doc** — see the per-product planning sets: `_bmad-output/projects/pyforge-{warden,atlas,herald,scribe,doctor}/planning-artifacts/`
- [planning-artifacts/integration-architecture.md](./integration-architecture.md) — contracts (now 5 parts)
- [planning-artifacts/specs/](./specs/) — the 8 local-recipes Tier-2 Specs (`spec-*/SPEC.md` + `.memlog.md`)
- [planning-artifacts/source-tree-analysis.md](./source-tree-analysis.md) — path map
- [planning-artifacts/development-guide.md](./development-guide.md) — local dev
- [planning-artifacts/deployment-guide.md](./deployment-guide.md) — enterprise

Identity + governance:
- [docs/dreams/pyforge-charter.md](../../../../docs/dreams/pyforge-charter.md) — Charter, Branding, the Lexicon (§ 10 is derived from this)
- [docs/dreams/](../../../../docs/dreams/) — Tier 0, 26 Dreams
- [scripts/spec_surface_check.py](../../../../scripts/spec_surface_check.py) — the governance detector (ADR-016)
- [AGENTS.md](../../../../AGENTS.md) — cross-tool entry point

Part 5 source of truth:
- [src/shared/packages/](../../../../src/shared/packages/) — the five distributions
- [pixi.toml](../../../../pixi.toml) — the 18 envs, the `[workspace]` preview flag, the path-dependency members

Existing repo docs:
- [CLAUDE.md](../../../../CLAUDE.md)
- [project-context.md](../project-context.md)
- [SYNC-RUNBOOK.md](../SYNC-RUNBOOK.md) — the detector→remedy procedure for keeping these artifacts honest
- [.claude/skills/conda-forge-expert/SKILL.md](../../../../.claude/skills/conda-forge-expert/SKILL.md)
- [.claude/skills/conda-forge-expert/CHANGELOG.md](../../../../.claude/skills/conda-forge-expert/CHANGELOG.md)
- [docs/reference/mcp-server-architecture.md](../../../../docs/reference/mcp-server-architecture.md)
- [docs/reference/enterprise-deployment.md](../../../../docs/reference/enterprise-deployment.md)
- [docs/reference/library-llms-full.md](../../../../docs/reference/library-llms-full.md)
