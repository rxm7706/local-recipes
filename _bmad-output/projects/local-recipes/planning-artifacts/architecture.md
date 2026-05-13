---
doc_type: architecture
project_name: local-recipes
date: 2026-05-12
version: '1.0.0'
status: draft
source_pin: 'conda-forge-expert v7.8.1'
consolidates:
  - architecture-conda-forge-expert.md
  - architecture-cf-atlas.md
  - architecture-mcp-server.md
  - architecture-bmad-infra.md
  - integration-architecture.md
---

# Unified Architecture: `local-recipes`

This document is the **executive architecture** for the rebuild. It consolidates the four part-specific architecture docs plus the integration doc into one navigable artifact. Part-specific docs remain authoritative for fine-grained detail (~3,000 lines collectively); this doc is for orientation, decision rationale, and rebuild planning.

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
   │  - 65 skills        │── Rule 1: invoke ────────────┐           │  - 35 tools            │
   │  - 6-layer config   │                              │           │  - thin subprocess     │
   │  - 3 projects       │                              │           │    wrappers            │
   │  - active-project   │   ┌──────────────────────────▼──────────────────────┐
   │    resolution       │   │   Part 1: conda-forge-expert skill              │
   │                     │◀──│   - SKILL.md (10-step loop, 5 critical          │
   │                     │   │     constraints, G1-G6 gotchas)                 │
   │                     │   │   - 42 Tier 1 canonical scripts                 │
   └─────────────────────┘   │   - 34 Tier 2 CLI wrappers                      │
              │              │   - 41 templates / 13 ecosystems (12 language + conda-forge-yml)                │
              │ Rule 2:      │   - 41 tests (unit + integration + meta)        │
              │ retro on     │   - 11 reference + 8 guides + 2 quickrefs       │
              │ closeout     │   - MANIFEST.yaml + install.py (portable)       │
              ▼              └────────────────────────┬─────────────────────────┘
                                                      │ Tier 1 scripts host:
                                                      ▼
                                     ┌──────────────────────────────────────┐
                                     │  Part 2: cf_atlas data pipeline      │
                                     │  - 17 phases (B → N) in PHASES       │
                                     │  - SQLite schema v19 (11 tables)     │
                                     │  - TTL gates on F, G, H, K           │
                                     │  - phase_state checkpoint (B, D, N)  │
                                     │  - S3-parquet + cf-graph offline     │
                                     │    backends (Phase F + Phase H)      │
                                     │  - 17 query CLIs                     │
                                     └──────────────────┬───────────────────┘
                                                        │
                                                        ▼
                                ┌───────────────────────────────────────────────┐
                                │  Shared state: .claude/data/conda-forge-      │
                                │  expert/                                       │
                                │  - cf_atlas.db (SQLite WAL)                    │
                                │  - vdb/, vdb-cache/, cve/                      │
                                │  - cf-graph-countyfair.tar.gz                  │
                                │  - cache/parquet/                              │
                                │  - pypi_conda_map.json                         │
                                └───────────────────────────────────────────────┘
                                                        │
                                                        ▼
                                ┌───────────────────────────────────────────────┐
                                │  Cross-cutting auth chain (_http.py):         │
                                │  - truststore (native CA)                      │
                                │  - JFROG_API_KEY → X-JFrog-Art-Api header     │
                                │    ★ leaks cross-host (mitigation: subshell)  │
                                │  - GITHUB_TOKEN → Authorization                │
                                │  - .netrc fallback                             │
                                │  + per-host *_BASE_URL overrides               │
                                └───────────────────────────────────────────────┘
```

---

## 2. Architectural Style

| Dimension | Style | Rationale |
|---|---|---|
| **Decomposition** | 4-part monorepo with shared infrastructure | Parts share env (pixi), data dir, and auth chain; separating into multiple repos would duplicate infrastructure |
| **Language** | Single-language (Python 3.12) | Reduces toolchain complexity; conda-forge ecosystem is Python-native |
| **State management** | SQLite (WAL mode) + JSON caches + flat-file logs | Single-file portability; no DB server; suitable for single-host operation |
| **API surface** | MCP (Model Context Protocol) — JSON-RPC over stdio | Standardized; Claude Code native; cross-language friendly if extended |
| **Build pattern** | rattler-build via pixi tasks; Docker for Linux native | conda-forge canonical; Docker prevents host-env pollution |
| **Concurrency** | Sequential subprocess; SQLite WAL allows concurrent reads | Atlas phases serialize naturally; MCP tool calls block at server level |
| **Communication pattern** | Pull-based (subprocess invocations) | Predictable; no message-queue complexity; subprocess inherits env |
| **Deployment model** | Single-host with optional CI; cron for scheduled atlas refresh | No production server; everything runs in the operator's pixi env |
| **Auth model** | Env-var-driven; truststore + JFrog + GitHub + .netrc chain | Per-host overrides via `*_BASE_URL` env vars; no auth daemon |
| **Versioning** | Skill (MANIFEST.yaml + CHANGELOG.md) + Schema (SCHEMA_VERSION constant) | Two surfaces: portability protocol + release semver |

---

## 3. The Four Parts (Consolidated)

### Part 1: conda-forge-expert skill

**Role**: encodes every conda-forge packaging decision so AI agents author conda-forge-acceptable recipes on first pass.

**Components**:
- **Documentation**: `SKILL.md` (914 lines, primary spine) + `INDEX.md` + `CHANGELOG.md` + 11 reference files + 8 guides + 2 quickrefs
- **Scripts (Tier 1 canonical)**: 42 Python modules in `.claude/skills/conda-forge-expert/scripts/`
- **CLI wrappers (Tier 2)**: 34 thin subprocess wrappers in `.claude/scripts/conda-forge-expert/`
- **Templates**: 41 recipe templates across 13 ecosystems (12 language: python, rust, go, c-cpp, r, java, ruby, dotnet, fortran, multi-output, nodejs, perl + conda-forge-yml config-template starter)
- **Tests**: 41 files in `tests/{unit,integration,meta}/` with real fixtures
- **Portability**: `MANIFEST.yaml` + `install.py` for installing into other repos

**Key invariants**:
1. 10-step autonomous loop with one human gate at step 8b
2. 5 critical constraints (no-mix-formats, stdlib-required, python-floor, pypi-url-pattern, build.bat-call-prefix)
3. 6 Recipe Authoring Gotchas (G1-G6)
4. Three-place rule for new scripts (canonical + wrapper + pixi task + meta-test)

**Detail**: see [architecture-conda-forge-expert.md](./architecture-conda-forge-expert.md)

### Part 2: cf_atlas data pipeline

**Role**: builds and maintains an offline-queryable graph of conda-forge package state.

**Components**:
- **Orchestrator**: `conda_forge_atlas.py` (~4,300 lines) with the PHASES registry
- **Phases**: 17 ordered functions (B, B.5, B.6, C, C.5, D, E, E.5, F, G, G', H, J, K, L, M, N)
- **Schema**: 11 tables, version 19, idempotent additive migrations
- **TTL gates**: 4 phases (F, G, H, K) with `*_fetched_at` timestamps
- **Checkpointing**: 3 phases (B, D, N) with `phase_state` cursor
- **Backends**: Phase F (S3 parquet / anaconda-api / auto) + Phase H (pypi-json / cf-graph)
- **CLIs**: 17 public (1 orchestrator + 1 single-phase + 15 query)

**Key invariants**:
1. All phases idempotent (re-run safe)
2. TTL gates scope UPDATE statements to phase eligibility predicates
3. Mid-run kill is cheap (checkpoint resume + TTL gates)
4. Phase F + Phase H tolerate firewall (no hard `*.anaconda.org` or `pypi.org` dep)

**Detail**: see [architecture-cf-atlas.md](./architecture-cf-atlas.md)

### Part 3: FastMCP server

**Role**: exposes Parts 1+2 as 35 MCP tools for Claude Code / BMAD agents.

**Components**:
- **Server**: `conda_forge_server.py` (1,199 lines, FastMCP)
- **Auxiliary**: `gemini_server.py` (Gemini bridge), `mcp_call.py` (JSON-RPC shell client)
- **Tools**: 35 `@mcp.tool()` registrations, 33 sync + 2 async
- **Helper**: `_run_script(script_path, args, input_text=None, timeout=120)` with 3-tier error handling
- **Out-of-band state**: `build_summary.json` + `build.pid` at repo root

**Key invariants**:
1. Every tool is a thin subprocess wrapper over a Tier 1 script (no inline logic)
2. JSON-stdout contract — every wrapped script accepts `--json`
3. Subprocess for isolation + timeout + pixi-env consistency
4. Errors structured (`{"error": "..."}`), never raw Python exceptions

**Detail**: see [architecture-mcp-server.md](./architecture-mcp-server.md)

### Part 4: BMAD infrastructure

**Role**: provides multi-project planning/dev/review/retro workflows.

**Components**:
- **Installer**: `_bmad/` with config.toml (layer 1), config.user.toml (layer 2), bmm/ module, core/, scripts/
- **Custom overlays**: `_bmad/custom/` with layers 3-4 + per-skill .toml + active-project marker
- **Output**: `_bmad-output/projects/<slug>/` with planning + implementation artifacts per project
- **Switcher**: `scripts/bmad-switch` (~80 lines Python)
- **Skills**: 65 installed (mix of BMAD-installer + repo-specific + engineering-practice)
- **Integration rules**: CLAUDE.md § BMAD↔CFE (Rule 1 invoke + Rule 2 retro)

**Key invariants**:
1. Six-layer TOML config merge in priority order
2. Active-project resolution: CLI flag > env var > marker file > none
3. Rule 1: BMAD agents touching conda-forge work MUST invoke the skill
4. Rule 2: Every conda-forge effort runs a `bmad-retrospective` at closeout

**Detail**: see [architecture-bmad-infra.md](./architecture-bmad-infra.md)

---

## 4. Cross-Cutting Concerns

### 4.1 Auth chain (`_http.py`)

Every outbound HTTP request from any Part routes through `.claude/skills/conda-forge-expert/scripts/_http.py`. The chain:

1. **truststore** (native OS CA store) — corporate CA / JFrog TLS
2. **`JFROG_API_KEY`** → `X-JFrog-Art-Api` header — **★ leaks cross-host**
3. **`GITHUB_TOKEN`** → `Authorization: token <...>` — scoped to github.com hosts
4. **.netrc** fallback for other authenticated hosts

**Per-host overrides** (used in air-gap / JFrog) — every external host is redirectable as of v7.8.1:
- Conda + Python ecosystem: `CONDA_FORGE_BASE_URL`, `PYPI_BASE_URL`, `PYPI_JSON_BASE_URL`, `S3_PARQUET_BASE_URL`, `ANACONDA_API_BASE_URL` (legacy alias `ANACONDA_API_BASE`).
- Git forges: `GITHUB_BASE_URL`, `GITHUB_RAW_BASE_URL`, `GITHUB_API_BASE_URL` (covers REST + GraphQL — GHES set to `https://<ghes>/api`), `GITLAB_API_BASE_URL`, `CODEBERG_API_BASE_URL`.
- Phase L registries: `NPM_BASE_URL` (also honors npm CLI's `npm_config_registry`), `CRAN_BASE_URL`, `CPAN_BASE_URL`, `LUAROCKS_BASE_URL`, `CRATES_BASE_URL`, `RUBYGEMS_BASE_URL`, `MAVEN_BASE_URL`, `NUGET_BASE_URL`.
- Vulnerability scanning: `OSV_API_BASE_URL`, `OSV_VULNS_BUCKET_URL`.

Full table with use sites + JFrog mirror patterns in [deployment-guide.md § 2b](./deployment-guide.md).

**The JFROG_API_KEY cross-host leak** is the system's most consequential security constraint. Mitigation patterns documented in 3 places (CLAUDE.md, project-context.md, deployment-guide.md). Architectural fix deferred to v2 ([Q-PRD-02 in PRD](./PRD.md)).

### 4.2 Pixi env contract

8 envs declared in `pixi.toml`:

| Env | Used by | Purpose |
|---|---|---|
| `local-recipes` (default) | Parts 1, 2, 3 | Primary operational env |
| `vuln-db` | Parts 1, 2 (vuln-specific only) | AppThreat vdb (Phase G/G', `scan_for_vulnerabilities`) |
| `grayskull` | Part 1 (`generate_recipe_from_pypi`) | PyPI→conda recipe scaffolding |
| `conda-smithy` | Part 1 (lint) | `conda-smithy recipe-lint` |
| `build` | Part 1 (cross-platform features) | rattler-build features |
| `linux`, `osx`, `win` | Part 1 (per-platform builds) | Platform-specific configurations |

**Why `vuln-db` separate**: AppThreat pulls ~500MB of CVE feeds; keeping default env lean.

### 4.3 Shared data directory

`.claude/data/conda-forge-expert/` (gitignored) is the single source of mutable state:
- `cf_atlas.db` + WAL/SHM — Part 2 primary artifact
- `cf_atlas_meta.json` — atlas run metadata
- `cf-graph-countyfair.tar.gz` — cf-graph offline snapshot
- `pypi_conda_map.json` — PyPI→conda cache
- `vdb/`, `vdb-cache/` — AppThreat vulnerability DB
- `cve/` — CVE feed cache
- `cache/parquet/` — Phase F S3 parquet cache (on demand)
- `inventory_cache/` — scan_project cache (on demand)

Refreshable via `bootstrap-data --fresh` (full) or `atlas-phase <ID>` (single).

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
| Skill release | `.claude/skills/conda-forge-expert/CHANGELOG.md` TL;DR | PATCH (fixes), MINOR (gotchas/sections), MAJOR (breaking) |
| Skill portability | `.claude/skills/conda-forge-expert/MANIFEST.yaml: version` | Install protocol changes (currently v7.0.0) |
| cf_atlas schema | `SCHEMA_VERSION` in `conda_forge_atlas.py:113` | Every additive migration (currently v19) |
| BMAD installer | `_bmad/bmm/config.yaml` header (currently v6.6.0) | `bmad-method` package upgrade |
| Project-context pin | `_bmad-output/projects/local-recipes/project-context.md:last_synced_skill_version` | Triggers re-sync when skill MINOR exceeds pin |

---

## 5. Data Architecture

### 5.1 cf_atlas.db (primary data store)

11 tables:

```
packages                       — 60+ columns; row per conda package
maintainers                    — feedstock maintainer registry
package_maintainers            — many-to-many join
meta                           — schema_version, last_full_run, etc.
phase_state                    — checkpoint cursors per phase (v7.7+)
dependencies                   — Phase J output (source → target deps)
vuln_history                   — Phase G' snapshots over time
package_version_downloads      — Phase F per-version downloads
upstream_versions              — Phase H + K + L (multi-source)
upstream_versions_history      — audit trail of upstream_versions writes
package_version_vulns          — Phase G' per-version CVE scoring
```

WAL mode for concurrent reads. Indexes on `packages.{relationship, match_source, pypi_name, conda_name, feedstock_name, license}` + per-table dimensions.

**Migration discipline**: additive only; `init_schema()` idempotent on every connection open.

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

---

## 6. Architecture Decision Records (ADRs)

Key technical decisions, captured in ADR-lite format. Each is a candidate for `bmad-create-architecture` decision-rationale expansion.

### ADR-001: rattler-build, not conda-build

- **Context**: conda-forge supports both v0 (conda-build, `meta.yaml`) and v1 (rattler-build, `recipe.yaml`); rattler-build is the future direction
- **Decision**: use rattler-build exclusively for new recipes; conda-build only for v0 migration source
- **Consequence**: all new recipes are v1; templates ship in both formats but v1 is canonical; migration is a one-time move per recipe

### ADR-002: Pixi as the sole env manager

- **Context**: previously the repo used conda environments; transition was already underway
- **Decision**: standardize on Pixi; no conda env, no venv, no manual env setup
- **Consequence**: 8 declared pixi envs; activation via pixi shell hooks; CI uses pixi too

### ADR-003: SQLite (single file) for cf_atlas

- **Context**: atlas data is ~800k rows; could use Postgres, DuckDB, parquet, or SQLite
- **Decision**: SQLite WAL mode for atlas storage
- **Consequence**: single-file portability; no DB server; reads concurrent; writes serialize; fine for offline-tolerant model where atlas refresh is batch

### ADR-004: 17-phase atlas pipeline (not monolithic)

- **Context**: atlas refresh could be one monolithic script or split into stages
- **Decision**: 17 named phases (B → N) with explicit dependency order, independently re-runnable
- **Consequence**: mid-run kill is cheap (TTL gates + checkpoint); operators can refresh single phase via `atlas-phase <ID>`; pipeline is auditable

### ADR-005: `current_repodata.json` over py-rattler sharded

- **Context**: Phase B needs to enumerate conda-forge packages; py-rattler has a sharded protocol; or fetch `current_repodata.json` directly
- **Decision**: use direct `current_repodata.json` fetch (5 subdirs)
- **Consequence**: bypasses 502 errors py-rattler hit (2026-Q1); air-gappable; ~5 min one-time fetch; loses outdated package versions (Phase B.6 catches removals)

### ADR-006: MCP server via FastMCP, subprocess-wrapper pattern

- **Context**: expose Python scripts as MCP tools; could use direct import or subprocess
- **Decision**: FastMCP server with subprocess invocations to Tier 1 scripts
- **Consequence**: ~200-400ms overhead per call (acceptable for interactive use); process isolation; timeout enforcement; pixi env consistency via `_PYTHON = sys.executable`

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

### ADR-011: Standalone-portable skill via MANIFEST.yaml + install.py

- **Context**: skill could be repo-locked or portable
- **Decision**: `MANIFEST.yaml` declares "standalone-portable" type; `install.py` bootstraps into other repos
- **Consequence**: skill can be reused across repos; install.py keeps in sync with skill's directory layout; portability is testable (rebuild target benefits)

### ADR-012: BMAD multi-project pattern with active-project resolution

- **Context**: this repo hosts 3 BMAD projects (`local-recipes`, `deckcraft`, `presenton-pixi-image`); separate repos would duplicate BMAD installation
- **Decision**: single BMAD install, multi-project layout under `_bmad-output/projects/<slug>/`, active-project resolution (CLI > env > marker > none)
- **Consequence**: one skill catalog benefits all projects; per-project artifact privacy is convention not enforcement; `scripts/bmad-switch --current` is the sanity check

---

## 7. Quality Attributes

### 7.1 Availability

- **MCP server**: auto-started by Claude Code at session boot; graceful tool-call failures (returns `{"error": "..."}` instead of crashing)
- **Atlas pipeline**: TTL gates + checkpointing → mid-run kills don't lose work
- **Recipe lifecycle**: each step is independently re-runnable; loops cap at 3 cycles before escalation

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

### 7.3 Reliability

- All 41 tests pass on `pixi run test`
- Meta-tests enforce structural invariants (`test_recipe_yaml_schema_header.py`, `test_all_scripts_runnable.py`)
- Schema migrations are additive and idempotent
- TTL gates prevent re-fetch of fresh data
- Build failure protocol caps loops at 3 iterations

### 7.4 Security

- **Permission gates**: Claude Code's `.claude/settings.json` allow/deny lists
- **No secrets in code**: env vars only (`JFROG_API_KEY`, `GITHUB_TOKEN`, `GEMINI_API_KEY`)
- **JFROG_API_KEY cross-host leak**: mitigated via subshell scoping (documented in 3 places); architectural fix in v2
- **GitHub `--force` push denied** in default permissions; `--force-with-lease` only
- **No outbound network without `_http.py`**: every Part routes through the same auth chain

### 7.5 Maintainability

- **Tier discipline**: meta-test enforces three-place rule for new scripts
- **Documentation cadence**: every BMAD effort runs a retro that updates SKILL.md / reference/ / guides / CHANGELOG
- **Schema migrations**: additive only; rerun-safe
- **Per-section sync tags**: project-context.md `(Sync: ...)` annotations point at upstream sources

### 7.6 Portability

- **Skill**: `MANIFEST.yaml` declares standalone-portable; `install.py` bootstraps
- **Atlas**: SQLite single-file; relocatable
- **Air-gap**: all workflows function offline given proxy/mirror infrastructure
- **No host-specific assumptions**: Linux/macOS/Windows all supported for builds (cross-compile from Linux to osx via SDKs/)

---

## 8. Risks & Mitigations

(Distilled from PRD § 10 and integration architecture)

| Risk | Mitigation in architecture |
|---|---|
| JFROG_API_KEY cross-host leak | Subshell scoping pattern; documented in 3 places; ADR-010 |
| Phase H "hangs" UX | 60s heartbeat + capped progress cadence (v7.7.0) |
| Phase K secondary rate-limit | Deferred work; cron with `--reset-ttl` spreads load |
| Schema drift on stale DBs | `init_schema()` idempotent on every connection open |
| MCP server crash from bad Tier 1 script | Subprocess isolation; `_run_script` catches exceptions |
| BMAD agent ignores integration rules | Auto-memory feedback entries reinforce; reviewer catches in PR |
| Recipe corpus growth (1,415 → ?) | Out of scope for rebuild; atlas tracks growth automatically |

---

## 9. Build Order (Dependency-Driven)

Rebuild MUST follow this order:

```
1. Bootstrap → pixi.toml + 8 envs + Python 3.12 + pyproject.toml
                ↓
2. Part 4: BMAD installer → _bmad/ + _bmad/scripts/ + 65 skills + scripts/bmad-switch
                ↓
3. Part 1: conda-forge-expert skill
   3a. _http.py (every other module imports it)
   3b. name_resolver.py + mapping_manager.py (helpers)
   3c. Recipe lifecycle scripts (recipe-generator, validate, edit, etc.)
   3d. SKILL.md + reference/ + guides/ + quickref/ + INDEX.md
   3e. Templates (41 files / 13 ecosystems)
   3f. Tier 2 wrappers (34 files)
   3g. Pixi tasks (~30 entries)
   3h. Meta-test (test_all_scripts_runnable.py)
                ↓
4. Part 2: cf_atlas (within Part 1's scripts/)
   4a. Schema (init_schema, 11 tables, SCHEMA_VERSION=19)
   4b. Phase B (foundational; every other phase depends on it)
   4c. Phase D (PyPI enumeration; Phase C/C.5 join B and D)
   4d. Phase E + E.5 (cf-graph tarball; M depends on this)
   4e. Phases F, G, G', H, J, K, L, M, N (any order)
   4f. CLI wrappers (17 entries) + pixi tasks
   4g. Per-phase tests + TTL-gate test + checkpoint test
                ↓
5. Part 3: MCP server
   5a. conda_forge_server.py with FastMCP("conda-forge-expert")
   5b. 35 @mcp.tool() registrations
   5c. _run_script helper
   5d. Out-of-band state file paths
   5e. (Optional) gemini_server.py + mcp_call.py
   5f. (Recommended) .mcp.json registration
                ↓
6. Documentation + project-context.md
   6a. CLAUDE.md (repo-wide guidance + BMAD↔CFE integration rules)
   6b. project-context.md (foundational rules; sync_sources + last_synced_skill_version pin)
   6c. docs/* (mcp-server-architecture, enterprise-deployment, developer-guide, copilot-to-api)
   6d. docs/specs/* (BMAD-consumable feature specs)
                ↓
7. Tests + meta-tests run clean
                ↓
8. CI pipelines (azure-pipelines.yml + .github/workflows/*)
                ↓
9. Air-gap deployment validation (full atlas build + recipe submission with JFrog endpoints)
```

This is the **canonical build order**. Skipping or reordering risks integration breakage. Per `project-parts.json` `rebuild_dependencies.build_order`.

---

## 10. Glossary

(See `PRD.md` Appendix A for full glossary.)

---

## 11. References

Authoritative sources:
- [PRD.md](./PRD.md) — product requirements
- [planning-artifacts/architecture-conda-forge-expert.md](./architecture-conda-forge-expert.md) — Part 1 detail
- [planning-artifacts/architecture-cf-atlas.md](./architecture-cf-atlas.md) — Part 2 detail
- [planning-artifacts/architecture-mcp-server.md](./architecture-mcp-server.md) — Part 3 detail
- [planning-artifacts/architecture-bmad-infra.md](./architecture-bmad-infra.md) — Part 4 detail
- [planning-artifacts/integration-architecture.md](./integration-architecture.md) — contracts
- [planning-artifacts/source-tree-analysis.md](./source-tree-analysis.md) — path map
- [planning-artifacts/development-guide.md](./development-guide.md) — local dev
- [planning-artifacts/deployment-guide.md](./deployment-guide.md) — enterprise

Existing repo docs:
- [CLAUDE.md](../../../../CLAUDE.md)
- [project-context.md](../project-context.md)
- [.claude/skills/conda-forge-expert/SKILL.md](../../../../.claude/skills/conda-forge-expert/SKILL.md)
- [.claude/skills/conda-forge-expert/CHANGELOG.md](../../../../.claude/skills/conda-forge-expert/CHANGELOG.md)
- [docs/mcp-server-architecture.md](../../../../docs/mcp-server-architecture.md)
- [docs/enterprise-deployment.md](../../../../docs/enterprise-deployment.md)
