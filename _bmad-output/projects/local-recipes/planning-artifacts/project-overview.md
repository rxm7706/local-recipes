---
doc_type: project-overview
project_name: local-recipes
date: 2026-05-12
repository_type: monorepo
parts: 4
source_pin: 'conda-forge-expert v8.1.0'
---

# Project Overview: local-recipes

**A semi-autonomous conda-forge packaging factory with an offline-tolerant package-intelligence layer, MCP tool surface, and BMAD multi-project planning infrastructure — all in a single pixi monorepo.**

---

## At a Glance

| Field | Value |
|---|---|
| Repository type | Monorepo (4 logical parts) |
| Primary language | Python 3.12 |
| Build engine | Pixi + rattler-build (NOT conda-build, except for legacy v0 maintenance) |
| Target platforms | linux-64, linux-aarch64, osx-64, osx-arm64, win-64 |
| Default pixi env | `local-recipes` (declared via `# default-env:` directive in `pixi.toml`) |
| Total pixi envs | 8 (`linux`, `osx`, `win`, `build`, `grayskull`, `conda-smithy`, `local-recipes`, `vuln-db`) |
| Default channel | conda-forge |
| License | BSD-3-Clause (LICENSE.txt) |
| Maintainer of new recipes | `rxm7706` (in `extra.recipe-maintainers`) |
| Recipe corpus | 1,415 v1 `recipe.yaml` files under `recipes/` + 1 at `wagtail/` (NOT part of the rebuild target) |
| Source pin (for this doc set) | conda-forge-expert skill v8.1.0 |

---

## Executive Summary

`local-recipes` is **not a conda recipe project** — it's the **infrastructure that produces** conda-forge recipes, plus the offline intelligence and air-gap-tolerant tooling to maintain them at scale. A new contributor inheriting this repository would receive four conceptually-separable systems wrapped into one pixi monorepo:

1. **conda-forge-expert** — a Claude Code skill that encodes the full conda-forge packaging lifecycle (generate → validate → build → submit). 10-step autonomous loop with one human-gated checkpoint at step 8b. Versions, schemas, and policies are pinned in code so the skill produces conda-forge-acceptable recipes on first authoring.
2. **cf_atlas** — a 22-phase offline package-intelligence pipeline (`bootstrap-data`, `atlas-phase`) that builds and maintains a SQLite database (`cf_atlas.db`, schema v22) inventorying ~33k conda-actionable + ~806k PyPI directory packages with metadata, version skew, vulnerability surface, dependency graphs, staleness signals, and (v8.1.0+) per-PyPI-project enrichment scores. Air-gap-tolerant via S3-parquet (Phase F) and cf-graph (Phase H) offline backends. Three side tables: `packages` (working set, ~33k conda-actionable), `pypi_universe` (reference data, ~806k PyPI directory), `pypi_intelligence` (35-column enrichment side table joined on `pypi_name`, populated by the v8.1.0 Phase O/P/Q/R/S chain).
3. **FastMCP server** — `.claude/tools/conda_forge_server.py` exposing 35 MCP tools that surface the skill's lifecycle, the atlas's intelligence, and project-scanning capabilities to Claude Code's MCP runtime. Auto-started at session boot.
4. **BMAD infrastructure** — the BMAD-METHOD installer (`_bmad/`) plus a multi-project planning layout (`_bmad-output/projects/<slug>/`) with six-layer config merge, 65 installed skills, and `scripts/bmad-switch` for active-project resolution. Drives planning + dev + review + retro workflows for any project hosted in this repo.

These four parts share a single pixi monorepo, a single skill data directory (`.claude/data/conda-forge-expert/`), and a single enterprise-deployment layer (`_http.py` + `*_BASE_URL` env-var resolution + JFrog integration).

### What this repository is NOT

- It is **not** a fork of conda-forge/staged-recipes that you `git pull` from. It mirrors the staged-recipes workflow but adds custom tooling and the four parts above.
- The ~440 recipes in `recipes/` are **outputs** of the system, not part of the system. Rebuilding the architecture rebuilds the **factory**; the recipes are re-authored using the rebuilt factory.
- It is not a CI-only system — most workflows are interactive (Claude Code) with CI as a verification backstop.

---

## Repository Structure: Monorepo with Four Parts

```
local-recipes/                                  # pixi monorepo root
├── pixi.toml                                   # 8 envs, ~30 tasks, build features per platform
├── pyproject.toml                              # Python package metadata
├── pixi.lock                                   # locked deps
├── CLAUDE.md                                   # repo-wide AI agent guidance
├── conda-forge.yml                             # staged-recipes-style root config
├── conda_build_config.yaml                     # global build matrix overrides
├── build-locally.py                            # Docker-based local build harness
├── azure-pipelines.yml                         # CI pipeline (Azure DevOps)
├── .azure-pipelines/                           # CI templates
├── .ci_support/                                # CI scripts (linting, validation)
├── .github/                                    # GitHub workflows + issue templates
│
├── .claude/                                    # Part 1 (skill) + Part 3 (MCP server) live here
│   ├── skills/conda-forge-expert/              # Part 1: 9-step lifecycle skill
│   │   ├── SKILL.md                            # primary spine, critical constraints
│   │   ├── INDEX.md                            # task→tool navigator
│   │   ├── CHANGELOG.md                        # release history (drift-detection source)
│   │   ├── reference/                          # 11 deep-reference files
│   │   ├── guides/                             # 8 workflow guides
│   │   ├── quickref/                           # 2 quick-reference files
│   │   ├── scripts/                            # canonical Python implementations (~30)
│   │   ├── templates/                          # recipe + conda-forge.yml starter templates
│   │   └── tests/                              # pytest suite (unit + integration + meta)
│   ├── skills/                                 # 65 skills total (incl. BMAD installer skills)
│   ├── scripts/conda-forge-expert/             # CLI wrapper layer (~30 thin subprocess wrappers)
│   ├── tools/                                  # Part 3: FastMCP server lives here
│   │   ├── conda_forge_server.py               # 35 MCP tools across 3 surfaces
│   │   ├── gemini_server.py                    # auxiliary MCP server
│   │   └── mcp_call.py                         # MCP helper utilities
│   └── data/conda-forge-expert/                # mutable runtime state (gitignored)
│       ├── cf_atlas.db                         # Part 2's primary artifact (SQLite, 19 schema versions)
│       ├── cf_atlas_meta.json                  # atlas run metadata
│       ├── cf-graph-countyfair.tar.gz          # cf-graph offline snapshot (Phase E/H/M)
│       ├── pypi_conda_map.json                 # PyPI→conda name mapping cache
│       ├── vdb/, vdb-cache/                    # AppThreat vulnerability DB
│       └── cve/                                # CVE feed cache
│
├── _bmad/                                      # Part 4: BMAD installer
│   ├── config.toml, config.user.toml           # layers 1-2 (installer-team / installer-user)
│   ├── custom/                                 # layers 3-4 (global overrides) + active-project marker
│   ├── bmm/                                    # BMAD module config
│   ├── core/                                   # BMAD core
│   └── scripts/                                # resolve_config.py, resolve_customization.py
├── _bmad-output/                               # BMAD output root
│   ├── PROJECTS.md                             # multi-project index
│   └── projects/<slug>/                        # per-project planning + implementation artifacts
│       ├── deckcraft/
│       ├── local-recipes/                      # this project's planning lives here
│       └── presenton-pixi-image/
│
├── recipes/                                    # OUTPUT artifacts (1,415 v1 recipe.yaml + patches)
│   └── <package-name>/
│       ├── recipe.yaml                         # v1 format, schema_version: 1
│       ├── patches/                            # optional upstream-bug shims
│       └── (license files, scripts)
│
├── docs/                                       # repo-wide human-facing docs
│   ├── mcp-server-architecture.md
│   ├── enterprise-deployment.md
│   ├── developer-guide.md
│   ├── copilot-to-api.md
│   └── specs/                                  # feature specs ready for bmad-quick-dev
│
├── scripts/                                    # repo-wide helper scripts
│   └── bmad-switch                             # active-project switcher
│
├── build_artifacts/                            # rattler-build output (gitignored)
└── output/                                     # ad-hoc recipe-generator output
```

---

## Four-Part Architecture

The system decomposes into four parts that share infrastructure but solve distinct problems. Each has its own architecture document; this overview names them and their boundaries.

### Part 1: conda-forge-expert (the skill)

**Project type:** library + CLI surface
**Root:** `.claude/skills/conda-forge-expert/` (canonical source) + `.claude/scripts/conda-forge-expert/` (CLI wrappers)
**Pixi envs used:** `local-recipes`, `grayskull`, `conda-smithy`, `vuln-db`
**Purpose:** Encode every conda-forge packaging decision so an AI agent (Claude Code) can author, validate, build, and submit recipes that pass conda-forge review on first land.

The skill is a **3-tier architecture**:
- **Tier 1 (canonical implementation):** `.claude/skills/conda-forge-expert/scripts/*.py` — single source of truth for behavior. 42 modules.
- **Tier 2 (CLI wrapper layer):** `.claude/scripts/conda-forge-expert/*.py` — thin subprocess wrappers that pixi tasks invoke. 34 wrappers (some Tier 1 modules are internal-only).
- **Tier 3 (data state):** `.claude/data/conda-forge-expert/` — mutable runtime artifacts (cf_atlas.db, vdb/, cve/, mapping caches).

Plus a **documentation layer** (`SKILL.md`, `reference/`, `guides/`, `quickref/`, `INDEX.md`) that the agent reads on activation, and a **template layer** (`templates/`) for recipe scaffolding.

Authoritative spine: the 10-step autonomous loop in `SKILL.md` (generate → validate → edit → scan → optimize → trigger_build → get_build_summary → analyze_build_failure → **prepare_submission_branch** (human checkpoint) → submit_pr).

See: `architecture-conda-forge-expert.md`

### Part 2: cf_atlas (the data pipeline)

**Project type:** data pipeline + CLI surface
**Root:** `.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py` (the orchestrator) + `.claude/data/conda-forge-expert/cf_atlas.db` (the artifact)
**Pixi envs used:** `local-recipes` (primary), `vuln-db` (for Phase G / G' that need AppThreat vdb)
**Purpose:** Build and maintain an offline SQLite database of conda-forge package intelligence (versions, downloads, dependency graphs, vulnerability surface, staleness signals) so the skill and the MCP server can answer "what's going on with package X?" without network access.

22 ordered phases (no A; reserved) — B → N for the core pipeline; O / P / Q / R / S added in v8.1.0 for the PyPI intelligence layer:
- **B/B.5/B.6** — package + version + variant discovery from `current_repodata.json`
- **C/C.5** — feedstock + maintainer extraction
- **D** — recipe-content scraping from cf-graph
- **E/E.5** — cf-graph tarball download + version-PR metadata
- **F** — anaconda.org downloads (S3 parquet backend or anaconda.org API)
- **G/G'** — vulnerability database summary + per-version CVE scoring
- **H** — PyPI version skew (pypi-json or cf-graph offline backend)
- **J** — homepage/repository URL extraction
- **K** — VCS release lookup (GitHub/GitLab/Codeberg `releases/latest`)
- **L** — release cadence calculation
- **M** — license enrichment
- **N** — additional batch enrichment (checkpoint-aware)

19 schema versions (additive migrations). TTL-gated phases (F/G/H/K) only re-fetch stale rows. `phase_state` checkpoint table makes interrupts cheap.

18 atlas CLIs: `bootstrap-data` (full run), `atlas-phase <ID>` (single phase), plus 16 read-side query CLIs (`staleness-report`, `feedstock-health`, `whodepends`, `behind-upstream`, `cve-watcher`, `version-downloads`, `release-cadence`, `find-alternative`, `adoption-stage`, `scan-project`, `pypi-only-candidates`, `pypi-intelligence` (v8.1.0+), `detail-cf-atlas`, …).

See: `architecture-cf-atlas.md`

### Part 3: FastMCP server (the API surface)

**Project type:** backend service
**Root:** `.claude/tools/conda_forge_server.py`
**Pixi envs used:** depends on tool — most run in `local-recipes`
**Purpose:** Expose Part 1 (recipe lifecycle) + Part 2 (atlas intelligence) + project-scanning capabilities as MCP tools that Claude Code can invoke directly. Auto-started by Claude Code at session boot.

35 tools (verified by `grep -c @mcp.tool conda_forge_server.py`) across three surfaces:
- **Recipe-authoring surface** (~15 tools): `generate_recipe_from_pypi`, `validate_recipe`, `edit_recipe`, `optimize_recipe`, `scan_for_vulnerabilities`, `trigger_build`, `get_build_summary`, `analyze_build_failure`, `prepare_submission_branch`, `submit_pr`, `migrate_to_v1`, `update_recipe_from_github`, etc.
- **Atlas-intelligence surface** (~12 tools): `query_atlas`, `package_health`, `staleness_report`, `cve_watcher`, `behind_upstream`, `feedstock_health`, `whodepends`, `release_cadence`, `version_downloads`, `find_alternative`, `adoption_stage`, `my_feedstocks`, etc.
- **Project-scanning surface** (~5 tools): `scan_project` (~28 input formats — manifests, lock files, SBOMs, container images, GitOps CRs with auto git-clone, K8s manifests, OCI archives, OCI registry probes).

Each MCP tool is a thin wrapper around a Tier-1 canonical script from Part 1.

See: `architecture-mcp-server.md`

### Part 4: BMAD infrastructure

**Project type:** infra
**Root:** `_bmad/` (installer) + `_bmad-output/` (artifacts) + `scripts/bmad-switch`
**Pixi envs used:** any (BMAD skills run via Claude Code, not pixi)
**Purpose:** Provide BMAD-METHOD's planning + dev + review + retro workflows for multiple projects hosted in this repo. The "multi-project" pattern lets the repo's primary use (conda-forge packaging) coexist with sibling projects (`deckcraft`, `presenton-pixi-image`, etc.).

Core mechanisms:
- **Six-layer config merge** (highest priority last): installer team → installer user → custom team → custom user → project team → project user. Resolved by `_bmad/scripts/resolve_config.py`.
- **Active-project resolution** by priority: `--project <slug>` flag → `BMAD_ACTIVE_PROJECT` env var → `_bmad/custom/.active-project` marker file → fallback to global config only.
- **65 installed skills** (BMAD-METHOD v6.6.0): planning chain, dev, review variants, retros, party-mode, plus repo-specific skills (`conda-forge-expert`, etc.).
- **BMAD ↔ conda-forge-expert integration rules** (codified in CLAUDE.md): every BMAD agent touching conda-forge work must invoke the `conda-forge-expert` skill; every closeout runs a retro that updates the skill files.

See: `architecture-bmad-infra.md`

---

## Cross-Cutting Concerns

These touch all four parts:

### Enterprise / air-gap layer

- `.claude/skills/conda-forge-expert/scripts/_http.py` — runtime HTTP helper: truststore + JFrog/GitHub/.netrc auth chain. Used by every Part 1, 2, 3 outbound request.
- Per-host env-var overrides: `CONDA_FORGE_BASE_URL`, `S3_PARQUET_BASE_URL`, `PYPI_BASE_URL`, `ANACONDA_API_BASE`, etc.
- `JFROG_API_KEY` — Critical security constraint: when set, leaks to every host. See `deployment-guide.md` § Cross-host credential leak.
- Phase F S3 parquet backend (closes `api.anaconda.org` dependency for atlas).
- Phase H cf-graph backend (closes pypi.org dependency for atlas).

### Vulnerability scanning

- `vuln-db` pixi env (separate from `local-recipes` to keep the default env lean).
- AppThreat vulnerability database (NVD + GHSA + OSV + npm + custom sources).
- Atlas Phases G / G' depend on `vuln-db` env (vdb library importable).
- `pixi run -e vuln-db update-cve-db` refreshes the CVE feed.

### Data sharing

All four parts read/write through `.claude/data/conda-forge-expert/` — single source of mutable state. Gitignored. Refreshable via `bootstrap-data` (full) or `atlas-phase <ID>` (single-phase).

---

## Generated Documentation

This file is one of 10 produced by the planning-artifacts pass on 2026-05-12:

1. **[Project Overview](./project-overview.md)** — this file
2. **[Source Tree Analysis](./source-tree-analysis.md)** — annotated directory tree, critical folders, entry points
3. **[Architecture: conda-forge-expert](./architecture-conda-forge-expert.md)** — Part 1 _(To be generated)_
4. **[Architecture: cf_atlas](./architecture-cf-atlas.md)** — Part 2 _(To be generated)_
5. **[Architecture: MCP server](./architecture-mcp-server.md)** — Part 3 _(To be generated)_
6. **[Architecture: BMAD infrastructure](./architecture-bmad-infra.md)** — Part 4 _(To be generated)_
7. **[Integration Architecture](./integration-architecture.md)** — how the 4 parts integrate _(To be generated)_
8. **[Development Guide](./development-guide.md)** — local setup, build, test, debug _(To be generated)_
9. **[Deployment Guide](./deployment-guide.md)** — enterprise, air-gap, JFrog _(To be generated)_
10. **[Master Index](./index.md)** — primary navigator _(To be generated)_

Plus structured metadata: **[project-parts.json](./project-parts.json)** — machine-readable part inventory and integration points.

---

## Existing Documentation (Inputs to These Documents)

This document set synthesizes the following existing sources. To rebuild faithfully, an agent should treat these as authoritative for the items they cover and supplement with this set's overlays:

- `CLAUDE.md` — repo-wide AI agent guidance, BMAD↔CFE integration rules, skill index
- `_bmad-output/projects/local-recipes/project-context.md` — foundational rules every BMAD agent reads on spawn (v8.1.0-pinned)
- `.claude/skills/conda-forge-expert/SKILL.md` — primary skill spine
- `.claude/skills/conda-forge-expert/INDEX.md` — task→tool navigator
- `.claude/skills/conda-forge-expert/CHANGELOG.md` — release history with TL;DR
- `.claude/skills/conda-forge-expert/reference/*.md` — 11 deep-reference files
- `.claude/skills/conda-forge-expert/guides/*.md` — 8 workflow guides
- `.claude/skills/conda-forge-expert/quickref/*.md` — 2 quick-reference files
- `docs/mcp-server-architecture.md` — MCP server + name-mapping subsystem
- `docs/enterprise-deployment.md` — air-gap + JFrog + JFROG_API_KEY cross-host leak
- `docs/developer-guide.md` — local testing + recipe development
- `docs/copilot-to-api.md` — Copilot subscription as local model backend
- `docs/specs/*.md` — 5 feature specs (db-gpt, conda-forge-tracker, copilot-bridge, atlas-phase-f-s3-backend, claude-team-memory)
- `_bmad-output/projects/local-recipes/implementation-artifacts/{spec-*.md, deferred-work.md}` — prior planning artifacts

---

## Getting Started (orient an agent rebuilding this from scratch)

If you are an AI agent or human tasked with rebuilding the **architecture and features** of this repository:

1. **Read this overview** plus `index.md` (when generated).
2. **Read the four architecture documents in this order**: `architecture-bmad-infra.md` (foundation) → `architecture-conda-forge-expert.md` (skill) → `architecture-cf-atlas.md` (data) → `architecture-mcp-server.md` (API surface). Each part depends on the prior in the build sequence.
3. **Read `integration-architecture.md`** to understand cross-part contracts.
4. **Read `development-guide.md`** for local setup, then `deployment-guide.md` for enterprise / air-gap requirements.
5. **Cross-check against `project-context.md`** — that file is the foundational invariants, this doc set is the structural map.
6. **Plan with BMAD**: once oriented, `bmad-create-epics-and-stories` against this doc set to produce an implementable work-breakdown. Probably 10-15 epics, 100-150+ stories.

The ~440 recipes in `recipes/` are out of scope for the rebuild — they're authored using the rebuilt factory, not part of it.
