# FastMCP Server Architecture for Conda-Forge Recipes

**Integration Model:** BMAD Method + Claude Code
**Primary Server:** `.claude/tools/conda_forge_server.py` — `FastMCP("conda-forge-expert")`
**Goal:** Autonomous, air-gapped-compatible recipe generation, maintenance, and intelligence.

This document describes the MCP **tool layer** that the `conda-forge-expert` skill exposes to
Claude. The skill remains the authoritative playbook (Operating Principles, the recipe
lifecycle loop, gotchas, Build-Failure Protocol — see `.claude/skills/conda-forge-expert/SKILL.md`);
the FastMCP server wraps the skill's `scripts/` as deterministic, JSON-returning tools. The
server *is* the skill's tool surface, not a replacement for it.

---

## 1. Overview

The repository is an AI-assisted, semi-autonomous packaging factory for `conda-forge` recipes.
Claude interacts with it through a **FastMCP server** that exposes **46 tools** (verified against
`@mcp.tool()` in `conda_forge_server.py`) across three layers:

| Layer | Count | What |
|---|---|---|
| **Recipe authoring** | 23 | generate → validate → edit → scan → optimize → build → debug → submit |
| **Atlas intelligence** | 21 | read-side queries over the `cf_atlas.db` data layer (offline-safe) |
| **Project / env scanning** | 2 | `scan_project`, `env_inspect` |

Each tool thin-wraps a script under `.claude/skills/conda-forge-expert/scripts/`. This aligns
with the **BMAD Method** — agents use robust, deterministic tools to accomplish user stories.

> **Enterprise / Air-Gap Constraint:** all MCP tools support operation inside strict air-gapped
> environments. Enterprise routing (JFrog Artifactory mirrors, internal channels) is
> **runtime-driven** via `_http.py` (truststore + JFrog/GitHub/.netrc auth chain) and pixi
> channel config — env vars only, never committed config. See `docs/enterprise-deployment.md`.

## 2. Autonomous Recipe Lifecycle

BMAD agents follow this closed-loop sequence with the recipe-authoring tools:

1. **Generate** — `generate_recipe_from_pypi(package_name="<pkg>")` scaffolds an initial `v1` `recipe.yaml`.
2. **Validate** — `validate_recipe(recipe_path="<path>")` checks schema, license, and runs `rattler-build lint`.
3. **Edit & Refine** — `edit_recipe()` for structured modifications (maintainers, SHA256, version bounds).
4. **Security Scan** — `scan_for_vulnerabilities()` against OSV.dev; resolve findings.
5. **Optimize** — `optimize_recipe()` applies conda-forge best practices (e.g. CFEP-25 `python_min`, `stdlib`).
6. **Build** — `trigger_build(recipe="recipes/<pkg>", config="linux64")` starts the local async build
   (native rattler-build; `config` auto-detects from the host if omitted — stems are `linux64` /
   `linux_aarch64` / `osx64` / `osxarm64` / `win64`, no hyphen; `mode="docker"` for CI fidelity).
7. **Monitor** — poll `get_build_summary()` until the build completes.
8. **Debug (if failed)** — pass the error log to `analyze_build_failure()`, apply the fix via `edit_recipe`, rebuild.
8b. **Stage for review (optional)** — `prepare_submission_branch(recipe_name)` pushes the recipe to a
    branch on your staged-recipes fork and returns `fork_branch_url` to inspect **before** the PR.
9. **Submit PR** — `submit_pr(recipe_name, dry_run=True)` first (verifies gh auth + fork), then `submit_pr(recipe_name)`.

---

## 3. MCP Tool Surface (46 tools)

Full, purpose-indexed inventory: `.claude/skills/conda-forge-expert/reference/mcp-tools.md`.
The atlas layer's per-signal catalog: `.../reference/atlas-phases-overview.md`. Highlights below.

### 3.1 Recipe authoring (23)

| Group | Tools |
|---|---|
| Generate | `generate_recipe_from_pypi` (+ the skill's CRAN/CPAN/LuaRocks/npm generators via CLI) |
| Validate / optimize | `validate_recipe`, `check_dependencies`, `optimize_recipe`, `scan_for_vulnerabilities`, `update_cve_database`, `run_system_health_check` |
| Edit | `edit_recipe` (structured; preferred over raw edits), `update_recipe`, `migrate_to_v1` |
| Feedstock reuse | `lookup_feedstock`, `enrich_from_feedstock`, `get_feedstock_context` |
| Name mapping | `get_conda_name`, `update_mapping_cache` |
| Build / debug | `trigger_build`, `get_build_summary`, `analyze_build_failure`, `download_pr_artifacts` |
| Autotick / update | `update_recipe_from_github`, `check_github_version` |
| Submit | `prepare_submission_branch`, `submit_pr` |

### 3.2 Atlas intelligence (21, read-side, offline)

Wrap the `cf_atlas.db` data layer (`.claude/data/conda-forge-expert/cf_atlas.db` — 16 schema
versions, pipeline phases B–N), all offline-safe. Portfolio/triage: `my_feedstocks`,
`staleness_report`, `feedstock_health`, `platform_breakdown`, `pyver_breakdown`, `channel_split`.
Dependency + lag: `whodepends`, `behind_upstream`, `release_cadence`, `adoption_stage`,
`find_alternative`. Security: `cve_watcher`. Downloads: `version_downloads`. CycloneDX
universe-inventory: `export_purls`, `universe_sbom`, `inventory_match`, `recommend_2027`,
`pypi_intelligence`, `pypi_only_candidates`, `package_health`. Escape hatch: `query_atlas`
(guarded SELECT).

### 3.3 Project / env scanning (2)

- `scan_project` — vuln + license + atlas scan of a project dir, container image, SBOM, live env, or K8s manifest (Helm/Kustomize/Argo/Flux).
- `env_inspect` — multi-mode pixi/conda env inspector (audit / freshness / security / bus_factor / licenses / sbom / diff).

---

## 4. PyPI ↔ Conda Name-Mapping Subsystem

Required because PyPI and conda-forge often use different names (e.g. `docker` → `docker-py`).
Resolved cache-first, then a repodata fallback, all offline-safe.

### Layout — tracked source vs runtime cache

```text
.claude/skills/conda-forge-expert/pypi_conda_mappings/   # TRACKED (source overrides)
├── custom.yaml             # user-defined overrides
├── different_names.json    # packages where PyPI ≠ conda names
└── stats.json              # sync metadata & TTL tracking

.claude/data/conda-forge-expert/                         # GITIGNORED (runtime cache)
├── pypi_conda_map.json     # resolver Tier-1 cache (7-day TTL) ← what name_resolver.py reads
└── repodata/…              # resolver Tier-2 repodata fallback
```

`name_resolver.py` reads `MAPPING_CACHE_FILE = .claude/data/conda-forge-expert/pypi_conda_map.json`
(Tier 1), falling back to `repodata/` (Tier 2). `mapping_manager.py` builds that cache primarily
from grayskull's bundled PyPI→conda mapping table plus the remote `mappings/pypi/name_mapping.*`,
with a 7-day TTL (`MAPPING_TTL_DAYS = 7`).

### Automation

Refreshed by the GitHub Actions workflow `.github/workflows/sync-pypi-mappings.yml` (weekly or on
`custom.yaml` change). Manual refresh:

```bash
pixi run -e local-recipes update-mapping-cache
```

`get_conda_name(pypi_name="<pkg>")` resolves cache-first through this subsystem during generation.

---

## 5. Related surface — pyforge-atlas (Kedro-native MCP)

A **separate, in-development** MCP server — `FastMCP("pyforge-atlas-atlas")` at
`src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/server.py` — exposes the *migrated*
cf_atlas pipeline as pipeline-trigger + dataset-read tools (`run_*_pipeline`, `read_atlas_dataset`,
`list_atlas_pipelines`, `list_atlas_datasets`, `query_vizro_ai`). It is the target of the
`cfe-atlas-datapipeline-kedro-migration` effort (BMAD project `pyforge-atlas`) and is **distinct
from** the atlas-intelligence tools in `conda_forge_server.py` — the two coexist today. This
document covers the `conda-forge-expert` server only.
