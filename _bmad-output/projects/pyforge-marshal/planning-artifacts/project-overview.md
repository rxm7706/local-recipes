---
doc_type: project-overview
project_name: local-recipes
date: 2026-07-25
repository_type: monorepo
parts: 5
source_pin: 'conda-forge-expert v8.80.0'
---

# Project Overview: local-recipes

> **Re-grounded 2026-07-25** (source_pin → v8.79.1; reconciler loop per SYNC-RUNBOOK).
> **What actually changed since the last pass:**
> - **A fifth part.** `src/shared/packages/` is now a first-class part — five hatchling-built distributions (`pyforge-warden`, `pyforge-atlas`, `pyforge-herald`, `pyforge-scribe`, `pyforge-doctor`) sharing the PEP 420 implicit `pyforge` namespace. The repo is a **5-part monorepo**, not 4.
> - **Pixi doubled.** 18 environments / 17 features — 9 factory envs plus 8 `no-default-feature` product envs. The `local-recipes` feature alone declares **106** tasks.
> - **BMAD infra grew.** BMAD-METHOD **6.10.0** (+ a separately-managed SKF module v2.0.1); `.claude/skills/` holds **93 dirs = 89 real skills + 4 non-skill support dirs**; **14** BMAD projects; **22** Specs plus **63** tracked per-story specs; execution is driven by the external `bmad-loop` orchestrator.
> - **Tier model formalised.** Dream (Tier 0) → legacy intake spec (Tier 1, phasing out) → **the Spec & planning artifacts (Tier 2 — the active contract)** → execution output (Tier 3, gitignored). Story specs are durable and tracked, *not* Tier 3.
> - **A second MCP server.** `pyforge-atlas` ships its own FastMCP server (11 tools), separate from and additive to the legacy 46-tool server.
> - **Corrections landed here:** the doc's own source pin was self-contradictory (body said v8.41.0), it claimed both "1,602 recipes" and "~440 recipes" in the same file, and its repo tree listed a root `pyproject.toml`, an `output/` directory, and four `docs/` files that are not where it said (one of which no longer exists at all).
>
> **Re-verified as UNCHANGED — do not "fix" these:** cf_atlas schema **v29**, **46 MCP tools** on the legacy server, **22 executable atlas phases** (23 cataloged — see below), gotchas **G1–G107** contiguous.


**A semi-autonomous conda-forge packaging factory with an offline-tolerant package-intelligence layer, MCP tool surface, a PyForge namespace-package family, and BMAD multi-project planning infrastructure — all in a single pixi monorepo.**

---

## At a Glance

| Field | Value |
|---|---|
| Repository type | Monorepo (5 logical parts) |
| Primary language | Python 3.12 (two PyForge distributions require ≥3.14) |
| Build engine | Pixi + rattler-build (NOT conda-build, except for legacy v0 maintenance); hatchling for the PyForge distributions |
| Target platforms | linux-64, linux-aarch64, osx-64, osx-arm64, win-64 |
| Default pixi env | `local-recipes` (declared via `# default-env:` directive in `pixi.toml`) |
| Total pixi envs | 19 pixi envs across 17 features — **9 factory** (`linux`, `osx`, `win`, `build`, `grayskull`, `conda-smithy`, `local-recipes`, `vuln-db`, `gcloud`) + **6 product** (`pyforge-warden`, `pyforge-atlas`, `pyforge-doctor`, `pyforge-scribe`, `pyforge-herald`, `bmad-ui`, all `no-default-feature = true`) |
| Default channel | conda-forge |
| License | BSD-3-Clause (LICENSE.txt) |
| Maintainer of new recipes | `rxm7706` (in `extra.recipe-maintainers`) |
| Recipe corpus | 1,664 recipe dirs under `recipes/` — 933 v1 `recipe.yaml` + 1,024 v0 `meta.yaml`, with **300 dirs carrying both** (deliberate: a v0 feedstock keeps `meta.yaml` until it completes its v0→v1 switch). Churny by design; never gated by the drift detector. |
| Source pin (for this doc set) | conda-forge-expert skill v8.79.1 |

> **Skill-version caveat (live defect, not a doc error):** v8.79.1 is the canonical stamp in
> `.claude/skills/conda-forge-expert/config/skill-config.yaml`. `SKILL.md`'s frontmatter and
> `MANIFEST.yaml` both still say `version: 7.0.0` — a stale layout-era value. Do not propagate 7.0.0.

---

## Executive Summary

`local-recipes` is **not a conda recipe project** — it's the **infrastructure that produces** conda-forge recipes, plus the offline intelligence and air-gap-tolerant tooling to maintain them at scale. A new contributor inheriting this repository would receive five conceptually-separable systems wrapped into one pixi monorepo:

1. **conda-forge-expert** — a Claude Code skill that encodes the full conda-forge packaging lifecycle (generate → validate → build → submit). Its spine is 9 numbered steps plus 3 lettered sub-steps (1b, 7a/7b, 8b) = **12 gated stages**; CLAUDE.md refers to this as "the 10-step loop". One human-gated checkpoint at step 8b. Versions, schemas, and policies are pinned in code so the skill produces conda-forge-acceptable recipes on first authoring.
2. **cf_atlas** — a **22-executable-phase** offline package-intelligence pipeline (`bootstrap-data`, `atlas-phase`) that builds and maintains a SQLite database (`cf_atlas.db`, schema v29) inventorying conda-actionable packages plus the PyPI directory with metadata, version skew, vulnerability surface, dependency graphs, staleness signals, per-PyPI-project enrichment scores, and CISA-KEV / EPSS / CWE overlays on the vulnerability columns. Air-gap-tolerant via S3-parquet (Phase F) and cf-graph (Phase H) offline backends. Three side tables: `packages` (working set), `pypi_universe` (reference data), `pypi_intelligence` (enrichment, joined on `pypi_name`), plus the KEV/EPSS/CWE overlay tables and 5 SQL views.
3. **FastMCP server** — `.claude/tools/conda_forge_server.py` (2,266 LOC) exposing **46 MCP tools** that surface the skill's lifecycle, the atlas's intelligence, project scanning, and infra checks to Claude Code's MCP runtime. Transport is **stdio**; registered in `~/.claude.json`, **not** in-repo (there is no `.mcp.json`). Auto-started at session boot.
4. **BMAD infrastructure** — the BMAD-METHOD **6.10.0** installer (`_bmad/`, plus a separately-managed SKF module v2.0.1) and a multi-project planning layout (`_bmad-output/projects/<slug>/`) with a six-layer config merge, **89 real skills** across 93 directories, `scripts/bmad-switch` for active-project resolution, the `bmad-loop` orchestrator, and the governance detectors in `scripts/`. Drives planning + dev + review + retro for **14** projects hosted in this repo.
5. **PyForge namespace packages** — `src/shared/packages/`: five hatchling-built distributions sharing a PEP 420 **implicit** `pyforge` namespace. These are real shipped software (warden and atlas are production-grade with ~2,350 test functions between them), not scaffolding, and they are versioned, tested, and conda-packaged in-tree.

These five parts share a single pixi monorepo, a single skill data directory (`.claude/data/conda-forge-expert/`), and a single enterprise-deployment layer (`_http.py` + `*_BASE_URL` env-var resolution + JFrog integration).

### The "23 phases" trap

`cf_atlas` has **22 executable phases** in its `PHASES` registry: B, B.5, B.6, C, C.5, D, O, P, Q, R, S, E, E.5, F, G, G', H, J, K, L, M, N. Two adjacent numbers are *not* the executable count and must never be substituted for it:

- **`bmad-groundtruth` prints "23 phases"** because `phase_count()` regexes `def phase_` and also matches `phase_r_upsert_one`, a per-row upsert helper that is not a phase.
- **`reference/atlas-phases-overview.md` catalogs 23** because it documents a conceptual **Phase I** (per-version download-history side table) that has **no runner and no `PHASES` entry**.

Correct phrasing everywhere: **22 executable phases, 23 cataloged.** Never write a bare "23 phases".

### What this repository is NOT

- It is **not** a fork of conda-forge/staged-recipes that you `git pull` from. It mirrors the staged-recipes workflow but adds custom tooling and the five parts above.
- The **1,664 recipe directories** in `recipes/` are **outputs** of the system, not part of the system. Rebuilding the architecture rebuilds the **factory**; the recipes are re-authored using the rebuilt factory.
- It is not a CI-only system — most workflows are interactive (Claude Code) with CI as a verification backstop.
- `pyforge-atlas` (Part 5) is **not a replacement** for `cf_atlas` (Part 2). It is a Kedro/Dagster/DuckDB **parallel reimplementation**; the skill CHANGELOG v8.79.0 entry says so explicitly. Both exist.

---

## Repository Structure: Monorepo with Five Parts

```
local-recipes/                                  # pixi monorepo root  (NOTE: no pyproject.toml at root)
├── pixi.toml                                   # 18 envs / 17 features; local-recipes feature alone = 106 tasks
│                                               #   [workspace] exists but deliberately has NO `members` key
├── pixi.lock                                   # locked deps
├── environment.yaml                            # exported from pixi.toml; an UNGATED CI sync check compares them
├── AGENTS.md                                   # cross-tool entry point (thin per-tool pointers)
├── CLAUDE.md                                   # repo-wide AI agent guidance
├── GEMINI.md                                   # per-tool pointer
├── README.md, CHANGELOG.md, LICENSE, LICENSE.txt
├── conda-forge.yml                             # staged-recipes-style root config
├── conda_build_config.yaml                     # global build matrix overrides
├── build-locally.py                            # Docker-based local build harness
├── test-recipes.py                             # recipe test harness
├── azure-pipelines.yml                         # CI pipeline (Azure DevOps)
├── pre-commit-config.yaml
├── .azure-pipelines/  .ci_support/  .github/   # CI templates, CI scripts, workflows + issue templates
├── .cursor/  .idea/  .junie/  .scripts/        # per-tool config (AGENTS.md fans out to these)
│
├── .claude/                                    # Part 1 (skill) + Part 3 (MCP server) live here
│   ├── skills/conda-forge-expert/              # Part 1
│   │   ├── SKILL.md                            # 3,887 lines; 6 Operating Principles, 12 Critical Constraints, G1–G107
│   │   ├── INDEX.md                            # task→tool navigator
│   │   ├── CHANGELOG.md                        # release history (drift-detection source)
│   │   ├── config/                             # 2 files — skill-config.yaml is the CANONICAL version stamp
│   │   ├── reference/                          # 15 deep-reference files
│   │   ├── guides/                             # 9 workflow guides
│   │   ├── quickref/                           # 2 quick-reference files
│   │   ├── scripts/                            # 66 canonical Python implementations, 41,410 LOC
│   │   ├── templates/                          # 42 recipe/conda-forge.yml scaffolding template files
│   │   ├── data/  examples/  automation/       # 3 / 6 / 3 files
│   │   └── tests/                              # 100 .py (98 test_*.py), 1,186 test fns, 22,318 LOC
│   │                                           #   unit 85 / meta 9 / integration 4 + 39 fixture files
│   ├── skills/                                 # 93 dirs = 89 real skills + 4 support dirs
│   │                                           #   (51 bmad-*, 16 skf-*, 21 engineering-practice, 1 repo-specific)
│   ├── scripts/conda-forge-expert/             # CLI wrapper layer — 60 entries
│   ├── tools/                                  # Part 3: FastMCP server lives here
│   │   ├── conda_forge_server.py               # 46 MCP tools, 2,266 LOC, stdio transport
│   │   ├── gemini_server.py                    # auxiliary MCP server
│   │   └── mcp_call.py                         # MCP helper utilities
│   └── data/conda-forge-expert/                # mutable runtime state (gitignored; ABSENT in a fresh clone)
│       ├── cf_atlas.db                         # Part 2's primary artifact (SQLite, schema v29)
│       ├── cf_atlas_meta.json                  # atlas run metadata
│       ├── cf-graph-countyfair.tar.gz          # cf-graph offline snapshot (Phase E/H/M)
│       ├── pypi_conda_map.json                 # PyPI→conda name mapping cache
│       ├── vdb/, vdb-cache/                    # AppThreat vulnerability DB
│       └── cve/                                # CVE feed cache
│
├── _bmad/                                      # Part 4: BMAD installer (BMAD-METHOD 6.10.0)
│   ├── config.toml, config.user.toml           # layers 1-2 (installer-team / installer-user)
│   ├── custom/                                 # layers 3-4 (global overrides) + .active-project marker
│   ├── _config/manifest.yaml                   # BMAD 6.10.0 stamp
│   ├── _config/skf-manifest.yaml               # SKF module v2.0.1 (separately managed)
│   ├── bmm/  core/  skf/                       # module configs
│   └── scripts/                                # resolve_config.py, resolve_customization.py
├── _bmad-output/                               # BMAD output root
│   ├── PROJECTS.md                             # multi-project index
│   ├── planning-artifacts -> projects/<slug>/planning-artifacts          # gitignored symlink
│   ├── implementation-artifacts -> projects/<slug>/implementation-artifacts  # gitignored symlink
│   └── projects/                               # 14 projects: deckcraft, local-recipes,
│                                               #   presenton-pixi-image, pyforge-atlas, pyforge-doctor,
│                                               #   pyforge-genesis, pyforge-herald, pyforge-marshal,
│                                               #   pyforge-mason, pyforge-scribe, pyforge-steward,
│                                               #   pyforge-warden, unity-data-stack, wasm-analytics-stack
├── .bmad-loop/                                 # bmad-loop orchestrator config (policy.toml + hook)
├── _skf-learn/                                 # SKF learning corpus
│
├── src/                                        # Part 5 + adjacent unpackaged source
│   ├── shared/packages/                        # Part 5: five PyForge distributions (PEP 420 `pyforge` ns)
│   │   ├── pyforge-warden/                     #   compliance gate — production-grade, self-dogfooding
│   │   ├── pyforge-atlas/                      #   Kedro/Dagster/DuckDB atlas reimplementation
│   │   ├── pyforge-herald/                     #   real transport core, stub CLI
│   │   ├── pyforge-scribe/                     #   one working command + 2 stubs
│   │   └── pyforge-doctor/                     #   scaffold + frozen schema only
│   ├── sentinel/knowledge/                     # loose NON-packaged Python (5 .py / 346 LOC);
│   │                                           #   imported as top-level `sentinel.knowledge` by 14 wiki-* tasks
│   └── prototype/packages/pyforge-atlas-kedro-viz/  # GENERATED kedro-viz mirror — never hand-maintained
│
├── recipes/                                    # OUTPUT artifacts: 1,664 dirs
│   └── <package-name>/                         #   933 recipe.yaml + 1,024 meta.yaml (300 dirs carry both)
│       ├── recipe.yaml                         # v1 format, schema_version: 1
│       ├── meta.yaml                           # v0 format — retained until the feedstock finishes v0→v1
│       ├── patches/                            # optional upstream-bug shims
│       └── (license files, scripts)
│
├── docs/                                       # repo-wide human-facing docs
│   ├── dreams/                                 # Tier 0 — 26 Dreams + README (27 files)
│   ├── specs/                                  # Tier 1 LEGACY intake specs — 19 files, phasing out
│   ├── reference/                              # 6 entries: mcp-server-architecture.md,
│   │                                           #   enterprise-deployment.md, developer-guide.md,
│   │                                           #   library-llms-full.md, pixi-config-jfrog.example.toml, README.md
│   ├── intake/                                 # 27 files
│   └── dashboard/                              # 4 files — the Guildhall console
│                                               #   (index.html, data.js, generate.py; published by
│                                               #    .github/workflows/dashboard.yml, regenerated at deploy time)
│
├── presentations/                              # 14 deck dirs + README.md
├── scripts/                                    # repo-wide helper scripts + governance detectors
│   ├── bmad_drift_check.py                     # THIS sync loop's detector
│   ├── spec_surface_check.py                   # every tracked file must be spec-governed or allowlisted
│   ├── llms_full_check.py                      # library catalog staleness
│   ├── bmad-switch                             # active-project switcher (marker + BOTH symlinks)
│   ├── bmad-loop-worktree                      # loop worktree helper
│   └── deck_export.py                          # deck export
│
├── tests/                                      # repo-level tests
├── conf/  helm/  SDKs/  archive/               # config, charts, SDK material, retired content
└── build_artifacts/                            # rattler-build output (gitignored)
```

---

## Five-Part Architecture

The system decomposes into five parts that share infrastructure but solve distinct problems. Parts 1–4 each have their own architecture document; this overview names them and their boundaries.

### Part 1: conda-forge-expert (the skill)

**Project type:** library + CLI surface
**Root:** `.claude/skills/conda-forge-expert/` (canonical source) + `.claude/scripts/conda-forge-expert/` (CLI wrappers)
**Pixi envs used:** `local-recipes`, `grayskull`, `conda-smithy`, `vuln-db`, `gcloud`
**Purpose:** Encode every conda-forge packaging decision so an AI agent (Claude Code) can author, validate, build, and submit recipes that pass conda-forge review on first land.

The skill is a **3-tier architecture**:
- **Tier 1 (canonical implementation):** `.claude/skills/conda-forge-expert/scripts/*.py` — single source of truth for behavior. 66 modules, 41,410 LOC.
- **Tier 2 (CLI wrapper layer):** `.claude/scripts/conda-forge-expert/*` — thin subprocess wrappers that pixi tasks invoke. 60 entries (some Tier 1 modules are internal-only).
- **Tier 3 (data state):** `.claude/data/conda-forge-expert/` — mutable runtime artifacts (cf_atlas.db, vdb/, cve/, mapping caches). Gitignored, and **absent from a fresh clone**.

Plus a **documentation layer** (`SKILL.md`, `reference/`, `guides/`, `quickref/`, `INDEX.md`) that the agent reads on activation, and a **template layer** (`templates/`) for recipe scaffolding.

Authoritative spine: the lifecycle in `SKILL.md` — 9 numbered steps plus 3 lettered sub-steps (1b, 7a/7b, 8b), 12 gated stages in all, referred to in CLAUDE.md as "the 10-step loop": generate → validate → edit → scan → optimize → trigger_build → get_build_summary → analyze_build_failure → **prepare_submission_branch** (human checkpoint) → submit_pr.

See: `architecture-conda-forge-expert.md`

### Part 2: cf_atlas (the data pipeline)

**Project type:** data pipeline + CLI surface
**Root:** `.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py` (the orchestrator) + `.claude/data/conda-forge-expert/cf_atlas.db` (the artifact)
**Pixi envs used:** `local-recipes` (primary), `vuln-db` (for Phase G / G' that need AppThreat vdb)
**Purpose:** Build and maintain an offline SQLite database of conda-forge package intelligence (versions, downloads, dependency graphs, vulnerability surface, staleness signals) so the skill and the MCP server can answer "what's going on with package X?" without network access.

22 executable phases (no A; reserved) — B → N for the core pipeline; O / P / Q / R / S added in v8.1.0 for the PyPI intelligence layer:
- **B/B.5/B.6** — package + version + variant discovery from `current_repodata.json`
- **C/C.5** — feedstock + maintainer extraction
- **D** — recipe-content scraping from cf-graph
- **O/P/Q/R/S** — PyPI intelligence: activity band → downloads (opt-in BigQuery) → cross-channel flags → per-project enrichment → computed readiness + recommended template
- **E/E.5** — cf-graph tarball download + version-PR metadata
- **F** — anaconda.org downloads (S3 parquet backend or anaconda.org API)
- **G/G'** — vulnerability database summary + per-version CVE scoring (+ KEV / EPSS / CWE overlays)
- **H** — PyPI version skew (pypi-json or cf-graph offline backend)
- **J** — homepage/repository URL extraction
- **K** — VCS release lookup (GitHub/GitLab/Codeberg `releases/latest`)
- **L** — release cadence calculation
- **M** — license enrichment
- **N** — additional batch enrichment (checkpoint-aware)

Schema **v29** (`SCHEMA_VERSION = 29`, `conda_forge_atlas.py:139`). Migrations are additive `ALTER TABLE` / create-if-absent steps keyed on column presence rather than numbered migration files, so a discrete *migration count* is not enumerable from the source and is deliberately not asserted here. <!-- UNVERIFIED 2026-07-25: the earlier "28 schema versions" figure could not be reproduced from the source; only the version NUMBER (29) is verifiable. -->

TTL-gated phases (F/G/H/K) only re-fetch stale rows. The `phase_state` checkpoint table makes interrupts cheap. Five SQL views: `v_actionable_packages`, `v_pypi_candidates`, `v_pypi_intelligence_valid`, `v_packages_enriched`, `v_current_version_vulns`.

**25 read-side atlas CLIs** (SKILL.md § Daily-use CLIs), on top of `bootstrap-data` (full run) and `atlas-phase <ID>` (single phase). All read-side CLIs are offline-safe. Seven have **no MCP tool** and are CLI/pixi-only: `library-futures`, `add-handoff`, `lts-registry-gap`, `cwe-seed-gap`, `spdx-schema-gap`, `license-map-gap`, and `mapping-gap`.

> **Row counts are unverifiable in a fresh checkout.** `.claude/data/conda-forge-expert/` is gitignored and does not exist here, so no live table cardinality is asserted in this document.

See: `architecture-cf-atlas.md`

### Part 3: FastMCP server (the API surface)

**Project type:** backend service
**Root:** `.claude/tools/conda_forge_server.py` (2,266 LOC)
**Pixi envs used:** depends on tool — most run in `local-recipes`
**Purpose:** Expose Part 1 (recipe lifecycle) + Part 2 (atlas intelligence) + project-scanning + infra capabilities as MCP tools that Claude Code can invoke directly. Auto-started by Claude Code at session boot over **stdio**; registered in `~/.claude.json` (user-level) — there is deliberately **no `.mcp.json`** in the repo.

**46 tools** (verified by `grep -c '@mcp.tool'`), 44 sync + 2 async (`update_cve_database`, `trigger_build`), partitioned across four surfaces:

- **Recipe-authoring (21):** `validate_recipe`, `check_dependencies`, `generate_recipe_from_pypi`, `update_cve_database`, `scan_for_vulnerabilities`, `trigger_build`, `get_build_summary`, `lookup_feedstock`, `enrich_from_feedstock`, `get_feedstock_context`, `edit_recipe`, `get_conda_name`, `analyze_build_failure`, `optimize_recipe`, `update_recipe`, `prepare_submission_branch`, `submit_pr`, `update_recipe_from_github`, `check_github_version`, `migrate_to_v1`, `download_pr_artifacts`.
- **Atlas-intelligence (21):** `query_atlas`, `package_health`, `staleness_report`, `cve_watcher`, `behind_upstream`, `feedstock_health`, `whodepends`, `release_cadence`, `version_downloads`, `find_alternative`, `adoption_stage`, `pypi_only_candidates`, `pypi_intelligence`, `platform_breakdown`, `pyver_breakdown`, `channel_split`, `my_feedstocks`, `export_purls`, `universe_sbom`, `inventory_match`, `recommend_2027`.
- **Project-scanning (2):** `scan_project` (broad manifest / lock-file / SBOM / container-input matrix — the canonical answer to "what does `scan_project` accept?" is `reference/dependency-input-formats.md`), `env_inspect`.
- **Infra (2):** `run_system_health_check`, `update_mapping_cache`.

21 + 21 + 2 + 2 = 46. Each MCP tool is a thin wrapper around a Tier-1 canonical script from Part 1.

**This is no longer the repo's only MCP server** — `pyforge-atlas` (Part 5) ships an independent FastMCP server with 11 tools of its own.

See: `architecture-mcp-server.md`

### Part 4: BMAD infrastructure

**Project type:** infra
**Root:** `_bmad/` (installer) + `_bmad-output/` (artifacts) + `scripts/` (switcher, orchestration helpers, governance detectors) + `.bmad-loop/`
**Pixi envs used:** any (BMAD skills run via Claude Code, not pixi); `bmad-ui` for the dashboards
**Purpose:** Provide BMAD-METHOD's planning + dev + review + retro workflows for the **14** projects hosted in this repo, so the repo's primary use (conda-forge packaging) coexists with sibling efforts.

Core mechanisms:

- **BMAD-METHOD 6.10.0** (`_bmad/bmm/config.yaml`, `_bmad/core/config.yaml`, `_bmad/_config/manifest.yaml`), with a separately-managed **SKF module v2.0.1** layered on (`_bmad/_config/skf-manifest.yaml`).
- **89 real skills across 93 directories** in `.claude/skills/`: 51 `bmad-*`, 16 `skf-*`, 21 engineering-practice, 1 repo-specific (`conda-forge-expert`). The other 4 directories (`cf-atlas-legacy`, `data`, `knowledge`, `shared`) have no `SKILL.md` — they are support content, not skills.
- **Six-layer config merge** (highest priority last): installer team → installer user → custom team → custom user → project team → project user. Resolved by `_bmad/scripts/resolve_config.py`.
- **Active-project resolution** by priority: `--project <slug>` flag → `BMAD_ACTIVE_PROJECT` env var → `_bmad/custom/.active-project` marker → fallback to global config only.
- **The marker is only half the switch.** Two gitignored symlinks — `_bmad-output/planning-artifacts` and `_bmad-output/implementation-artifacts`, each pointing into `projects/<slug>/` — are the other half, because `_bmad/bmm/config.yaml` hard-codes `planning_artifacts: {project-root}/_bmad-output/planning-artifacts` and that key does **not** compose with a project's `output_folder` override. Marker and symlinks must always agree. **HARD rule (2026-07-25): parallel agents address projects by physical path and never call `scripts/bmad-switch`** — it mutates per-working-tree global state that no agent holds a lock on.
- **`bmad-loop`** — an external deterministic orchestrator (`bmad-loop >=0.9.0`) configured by `.bmad-loop/policy.toml` + `bmad_loop_hook.py`. Loop homes moved on 2026-07-25 to a short root, `~/.bmad-loops/<slug>` (override `BMAD_LOOP_HOME_ROOT`), because long paths panic pixi-build-python 0.8.3. Branches: `loop/<slug>`, `bmad-loop/<run-id>/<X-Y>-<slug>`, `attempt-preserve/*`.
- **Governance detectors** in `scripts/`: `bmad_drift_check.py` (this sync loop), `spec_surface_check.py` (every tracked file must be governed by a spec `surface:` glob or explicitly allowlisted; specs are keyed `<project>/<spec>` — a bare-name key once silently dropped a surface; live: 22 specs / 7,888 tracked files / 6,323 governed / 1,567 allowlisted), `llms_full_check.py`, plus `bmad-switch`, `bmad-loop-worktree`, `deck_export.py`.
- **BMAD ↔ conda-forge-expert integration rules** (codified in CLAUDE.md): every BMAD agent touching conda-forge work must invoke the `conda-forge-expert` skill; every closeout runs a retro that updates the skill files.

**Known broken:** the `bmad-preflight` pixi task (`pixi.toml:190`) runs `bash scripts/ensure-bmad-preflight.sh`, and that script does not exist anywhere in the repo. Verified 2026-07-25 — the task cannot succeed.

See: `architecture-bmad-infra.md`

### Part 5: PyForge namespace packages

**Project type:** library
**Root:** `src/shared/packages/`
**Pixi envs used:** `pyforge-warden`, `pyforge-atlas`, `pyforge-doctor`, `pyforge-scribe`, `pyforge-herald` (all `no-default-feature = true`)
**Purpose:** Ship the PyForge Smiths as real, independently-installable Python distributions rather than as in-repo scripts.

Five hatchling-built distributions share a **PEP 420 implicit namespace**, `pyforge`. There is deliberately **no `src/pyforge/__init__.py`** in any of them (verified absent in all five), which is exactly what lets `pyforge.atlas`, `pyforge.doctor`, `pyforge.herald`, `pyforge.scribe` and `pyforge.warden` coexist. Each package carries its own `[package]` `pixi.toml` (a pixi workspace member) and no `[workspace]` table.

| dist | module | py | deps | extras | console script | src LOC / files | tests LOC / files / `def test_` | maturity |
|---|---|---|---|---|---|---|---|---|
| `pyforge-warden` 0.1.0 | `pyforge.warden` | ≥3.12 | PyYAML, packaging, cyclonedx-python-lib, jsonschema, packageurl-python, license-expression | — | `warden` | 16,597 / 28 | 29,752 / 65 (54 `test_*.py`) / **1,575** | production-grade, self-dogfooding |
| `pyforge-atlas` 0.1.0 | `pyforge.atlas` | **≥3.14** | kedro≥1.5.0, kedro-datasets≥9.5.0 | `gate = [pyforge-warden]` | `pyforge-atlas` | 14,461 / 78 | 14,682 / 110 (78 `test_*.py`) / **772** | production-grade |
| `pyforge-herald` 0.1.0 | `pyforge.herald` | ≥3.12 | mcp≥1.28.1 | — | `herald` | 1,277 / 6 | 1,594 / 5 / **112** | real transport core, stub CLI |
| `pyforge-scribe` 0.1.0 | `pyforge.scribe` | ≥3.12 | typer≥0.27.0, pydantic≥2.13.4 | — | `scribe` | 421 / 4 | 323 / 2 / **18** | one working command (`capture`), 2 stubs |
| `pyforge-doctor` 0.1.0 | `pyforge.doctor` | **≥3.14** | jsonschema | `gate = [pyforge-warden]` (declared, not yet wired) | `doctor` | 304 / 4 | 1,081 / 6 / **62** | scaffold + frozen schema only |

Test splits: warden — unit 1,283 / conformance 244 / meta 45 / root 3. atlas — 772 across 26 directories. doctor — unit 45 / meta 17.

**Frozen contracts shipped inside the wheels:**
- `pyforge/warden/data/report-schema.json` — 575 lines, `$id: urn:local-recipes:pyforge-warden:report-schema`, title `ComplianceReport`.
- `pyforge/doctor/data/report-schema.json` — 92 lines, `urn:local-recipes:pyforge-doctor:report-schema`, title `DoctorReport`.
- warden also ships `conda_pypi_map.json` (1.5 MB / 59,292 lines) and `lts-registry.yaml`.

**Invariants:**
- Each package's exit-code projection has a **single owner module**, `verdict.py`.
- Cross-package edges are **one-directional and extras-gated** (atlas→warden, doctor→warden via the `gate` extra). Nothing imports in reverse.
- Built artifacts (`dist/`, `dist-conda/`) exist for warden and atlas.

**pyforge-atlas specifics:** a Kedro/Dagster/DuckDB **parallel reimplementation of cf_atlas, not a replacement** (CHANGELOG v8.79.0 states this explicitly). 7 Kedro pipelines — `core`, `pypi_intelligence`, `vulnerability`, `vcs_health`, `universal_sbom`, `seed_gaps`, `derived_artifacts`; Dagster glue in `orchestration/definitions.py`; Parquet storage read by Ibis→DuckDB at query time (**no persisted `.duckdb` file**); contracts in `conf/base/catalog.yml` (800 lines). It ships its own second FastMCP server, `pyforge/atlas/mcp/server.py`, with 11 tools.

**Adjacent source under `src/` that is *not* Part 5:**
- `src/sentinel/knowledge/` — loose, non-packaged Python (no `pyproject.toml`, no `__init__.py`), 5 `.py` / 346 LOC, imported as top-level `sentinel.knowledge` by 14 `wiki-*` pixi tasks and by pyforge-atlas tests.
- `src/prototype/packages/pyforge-atlas-kedro-viz/` — a **generated**, dependency-free kedro-viz mirror of the atlas DAG (setuptools, 14 `.py` / 915 LOC; ~98% of its bulk is a checked-in static `build/` export). Regenerated by `tools/regenerate_from_atlas.py`; **never hand-maintained.**

<!-- No dedicated architecture-pyforge-packages.md exists yet; Part 5 is documented here and in project-parts.json. Creating one is a planning decision, not a sync action. -->

---

## The Tier Model (how work enters this repo)

| Tier | Location | Purpose | Git |
|---|---|---|---|
| **0 — Dream** | `docs/dreams/*.md` (26 Dreams + README) | The raw human aspiration; BMAD turns it into the Spec | tracked, permanent |
| **1 — Intake spec (LEGACY)** | `docs/specs/*.md` (19 files) | Former hand-authored spec tier; **author no new files here** | tracked, phasing out |
| **2 — Spec & planning (BMAD)** | `_bmad-output/projects/<slug>/planning-artifacts/` | **The active contract.** `bmad-spec` output + PRD, architecture, epics + stories, gate reports | tracked, permanent |
| **3 — Execution output** | `_bmad-output/projects/<slug>/implementation-artifacts/` | story files, sprint YAMLs, test outputs, retros | **gitignored — nothing there may be git-tracked** |

**The Spec is a five-field contract**, headings exactly: `## Why`, `## Capabilities`, `## Constraints`, `## Non-goals`, `## Success signal` (plus optional `## Assumptions`, `## Open Questions`). It is **derived from an append-only `.memlog.md`, never hand-patched.** Live: **22 Specs** across the 14 projects, of which `local-recipes` owns **8** — `spec-enterprise-airgap`, `spec-factory-console`, `spec-fleet-stewardship`, `spec-modernist-identity`, `spec-multi-loop-isolation`, `spec-packaging-factory`, `spec-pyforge-marshal`, `spec-regenerable-factory` — plus **63 tracked per-story specs** (pyforge-atlas 32, pyforge-warden 31).

**Story specs are durable and git-tracked, NOT Tier 3** (convention since 2026-07-25). bmad-loop drafts a story spec into the run's gitignored `implementation-artifacts/`; after the story merges it is promoted into the tracked `planning-artifacts/specs/` subdir and committed.

---

## Cross-Cutting Concerns

These touch all five parts:

### Enterprise / air-gap layer

- `.claude/skills/conda-forge-expert/scripts/_http.py` — runtime HTTP helper: truststore + JFrog/GitHub/.netrc auth chain. Used by every Part 1, 2, 3 outbound request.
- Per-host env-var overrides: `CONDA_FORGE_BASE_URL`, `S3_PARQUET_BASE_URL`, `PYPI_BASE_URL`, `ANACONDA_API_BASE`, etc.
- `JFROG_API_KEY` — critical security constraint: when set, it attaches to **every** outbound request regardless of host. See `deployment-guide.md` § Cross-host credential leak and `docs/reference/enterprise-deployment.md`.
- Phase F S3 parquet backend (closes the `api.anaconda.org` dependency for atlas).
- Phase H cf-graph backend (closes the pypi.org dependency for atlas).

### Vulnerability scanning

- `vuln-db` pixi env (separate from `local-recipes` to keep the default env lean).
- AppThreat vulnerability database (NVD + GHSA + OSV + npm + custom sources).
- Atlas Phases G / G' depend on the `vuln-db` env (vdb library importable).
- `pixi run -e vuln-db update-cve-db` refreshes the CVE feed.
- Part 5's `pyforge-warden` is an independent, schema-validated compliance gate over Python/Conda/Pixi manifests — complementary to, not a replacement for, the atlas vulnerability columns.

### Data sharing

Parts 1–3 read/write through `.claude/data/conda-forge-expert/` — a single source of mutable state, gitignored, refreshable via `bootstrap-data` (full) or `atlas-phase <ID>` (single phase). Part 5 does **not** use it: `pyforge-atlas` persists Parquet and reads it through Ibis→DuckDB at query time.

### Visibility

The **Guildhall** program console is `docs/dashboard/{index.html,data.js,generate.py}`, published to GitHub Pages by `.github/workflows/dashboard.yml`. The workflow regenerates `data.js` from git history at deploy time and deliberately does not commit it back.

### CI gates on every PR

The inherited staged-recipes linter reds two ways that must be pre-empted at PR open/update:
1. **Any change outside `recipes/`** → add the `maintenance` label.
2. **`pixi.toml` changed** → regenerate and commit `environment.yaml` (`pixi project export conda-environment -e build > environment.yaml`). This sync check is **ungated** — the `maintenance` label does not suppress it.

Recipe-only PRs need neither.

---

## Identity and naming

Source of truth: `docs/dreams/pyforge-charter.md` § Branding, § The Lexicon.

- **PyForge** is the brand in prose; **`pyforge`** lowercase is the technical form only (distributions, modules, slugs, paths, envs, branches, CLIs). Never brand-case a code identifier.
- The eight personas are **Smiths**: Herald · Marshal · Atlas · Warden · Mason · Doctor · Scribe · Steward.
- **The Spec** (capital S) is the five-field contract; the **Guildhall** is the program console.
- Mission lockup: *Forging the Agentic SDLC — Humans Dream, Agents Deliver — Governed. Auditable. Production-ready.*
- Seven Lexicon nouns: Charter (legitimacy) → Spec (contract) → Guild (body) → Smiths (identity) → Stations (accountability) → Skills (execution) → Guildhall (visibility).

---

## Generated Documentation

The tracked living doc set for this project is **12 documents**, all present on disk:

1. **[Master Index](./index.md)** — primary navigator
2. **[Architecture](./architecture.md)** — the spine
3. **[Architecture: conda-forge-expert](./architecture-conda-forge-expert.md)** — Part 1
4. **[Architecture: cf_atlas](./architecture-cf-atlas.md)** — Part 2
5. **[Architecture: MCP server](./architecture-mcp-server.md)** — Part 3
6. **[Architecture: BMAD infrastructure](./architecture-bmad-infra.md)** — Part 4
7. **[Integration Architecture](./integration-architecture.md)** — how the parts integrate
8. **[Development Guide](./development-guide.md)** — local setup, build, test, debug
9. **[Deployment Guide](./deployment-guide.md)** — enterprise, air-gap, JFrog
10. **[Source Tree Analysis](./source-tree-analysis.md)** — annotated directory tree, critical folders, entry points
11. **[Project Overview](./project-overview.md)** — this file
12. **[project-parts.json](./project-parts.json)** — machine-readable part inventory and integration points

Part 5 does not yet have a dedicated architecture document; it is covered here and in `project-parts.json`.

---

## Existing Documentation (Inputs to These Documents)

This document set synthesizes the following existing sources. To rebuild faithfully, an agent should treat these as authoritative for the items they cover and supplement with this set's overlays:

- `AGENTS.md` — the cross-tool entry point; the tier convention lives here
- `CLAUDE.md` — repo-wide AI agent guidance, BMAD↔CFE integration rules, skill index
- `_bmad-output/projects/local-recipes/project-context.md` — foundational rules every BMAD agent reads on spawn
- `_bmad-output/projects/local-recipes/SYNC-RUNBOOK.md` — the reconciliation procedure this document is produced by
- `_bmad-output/PROJECTS.md` — multi-project index
- `.claude/skills/conda-forge-expert/SKILL.md` — primary skill spine
- `.claude/skills/conda-forge-expert/INDEX.md` — task→tool navigator
- `.claude/skills/conda-forge-expert/CHANGELOG.md` — release history with TL;DR
- `.claude/skills/conda-forge-expert/reference/*.md` — 15 deep-reference files
- `.claude/skills/conda-forge-expert/guides/*.md` — 9 workflow guides
- `.claude/skills/conda-forge-expert/quickref/*.md` — 2 quick-reference files
- `docs/dreams/*.md` — Tier 0; `pyforge-charter.md` is the identity source of truth
- `docs/reference/mcp-server-architecture.md` — MCP server + name-mapping subsystem
- `docs/reference/enterprise-deployment.md` — air-gap + JFrog + JFROG_API_KEY cross-host leak
- `docs/reference/developer-guide.md` — local testing + recipe development
- `docs/reference/library-llms-full.md` — LLM-facing catalog of every library/CLI in the pixi envs
- `docs/specs/*.md` — 19 legacy Tier-1 intake specs; indexed in CLAUDE.md, statuses via `bmad-drift-check --specs`
- `_bmad-output/projects/<slug>/planning-artifacts/specs/spec-*/SPEC.md` — the 22 live Specs

> **Removed 2026-07-25:** this list previously cited a `docs/`-level Copilot-bridge note that was **purged from the repository** during secret-leak remediation on 2026-07-24; it is intentionally not named or linked here, and must not be re-added. The list also cited `docs/developer-guide.md`, `docs/mcp-server-architecture.md` and `docs/enterprise-deployment.md` at the `docs/` top level; all three live under `docs/reference/`.

---

## Getting Started (orient an agent rebuilding this from scratch)

If you are an AI agent or human tasked with rebuilding the **architecture and features** of this repository:

1. **Read this overview** plus `index.md`.
2. **Read the four architecture documents in this order**: `architecture-bmad-infra.md` (foundation) → `architecture-conda-forge-expert.md` (skill) → `architecture-cf-atlas.md` (data) → `architecture-mcp-server.md` (API surface). Each part depends on the prior in the build sequence. Part 5 (`pyforge-packages`) comes last — see `project-parts.json` § `rebuild_dependencies`.
3. **Read `integration-architecture.md`** to understand cross-part contracts.
4. **Read `development-guide.md`** for local setup, then `deployment-guide.md` for enterprise / air-gap requirements.
5. **Cross-check against `project-context.md`** — that file holds the foundational invariants; this doc set is the structural map.
6. **Plan the Dream-first way.** Work does **not** start at epics any more. Write a Dream in `docs/dreams/<slug>.md`, then run **`bmad-spec`** to produce the Spec into `_bmad-output/projects/<slug>/planning-artifacts/` (small scope), or the full planning chain — `bmad-prd` → `bmad-architecture` → `bmad-create-epics-and-stories` — for a large one. Keep the Spec's status current (`draft → ready → in-progress → shipped`) regardless of who did the work.
7. **Address projects by physical path.** Do not call `scripts/bmad-switch` from a parallel agent — it is per-working-tree global state with no lock.

The 1,664 recipe directories in `recipes/` are out of scope for the rebuild — they are authored *using* the rebuilt factory, not part of it.
