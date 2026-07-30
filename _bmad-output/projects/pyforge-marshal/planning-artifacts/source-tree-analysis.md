---
doc_type: source-tree-analysis
project_name: local-recipes
date: 2026-07-25
repository_type: monorepo
parts: 5
source_pin: 'conda-forge-expert v8.81.0'
---

# Source Tree Analysis

> **Re-grounded 2026-07-25** (source_pin → v8.79.1; full end-to-end re-verification of every path and count against the live checkout). **The headline is structural, not a version bump: the repo grew a fifth part — `src/`, the `pyforge` package family** (five hatchling dists sharing a PEP 420 implicit namespace: `pyforge-warden`, `pyforge-atlas`, `pyforge-herald`, `pyforge-scribe`, `pyforge-doctor`, plus the non-packaged `src/sentinel/knowledge/` and the generated `src/prototype/`). The prior revision did not mention `src/` at all. Also newly mapped: `presentations/` (14 decks), `docs/dreams/` (Tier 0), `docs/dashboard/` (the **Guildhall** console), `.bmad-loop/`, `conf/`, `helm/`, `archive/`, `_skf-learn/`, `.claude/memory/`, `.claude/hooks/`.
>
> **Re-verified UNCHANGED** (do not "fix" these): cf_atlas schema **v29**, **46 MCP tools**, gotchas **G1–G107**, **22 executable atlas phases** (23 cataloged — `reference/atlas-phases-overview.md` also carries a runner-less conceptual Phase I), CFE `reference/` 15 / `guides/` 9 / `quickref/` 2.
>
> **Corrected (previously wrong, not merely stale):** the top-level tree claimed a root `pyproject.toml`, a root `package.json`, an `output/` directory and a `build.pid` — **none exist**; `.gitignore` is **738 lines**, not ">13k"; `SDKs/` was described as a committed binary but is entirely untracked; the Counts table's atlas schema version, MCP-tool count, reference-doc count, skill-test count and pixi-env count all sat below live and are now re-measured; `docs/` no longer has any top-level `.md` (everything moved into `docs/reference/` + `archive/docs/`). See § *Counts* refresh notes.

This document is the **path map**: every architecturally-significant directory and entry-point file. Architecture docs (parts 1-5) reference paths in this tree; this tree exists once.

Gitignored runtime data is included where relevant (most under `.claude/data/`); it is created by build/runtime processes, not committed. Where a documented runtime path does **not** exist in this checkout it is marked *(absent locally)* rather than described as if populated.

---

## Top-level layout (annotated)

```
local-recipes/                               # pixi monorepo root, default-env=local-recipes
│
├── pixi.toml                                # 18 envs + 17 features + 152 tasks (106 in local-recipes); the 5 pyforge-* envs are workspace members
├── pixi.lock                                # locked deps (committed)
├── environment.yaml                         # exported conda-env mirror of the `build` env — MUST be regenerated whenever pixi.toml changes (ungated CI sync check)
├── conda-forge.yml                          # staged-recipes-style root config
├── conda_build_config.yaml                  # global build matrix overrides
├── pre-commit-config.yaml                   # pre-commit hook set (note: no leading dot)
│
├── CLAUDE.md                                # ★ entry point for Claude Code (repo-wide guidance)
├── AGENTS.md                                # ★ cross-tool entry point — the tier model lives here; CLAUDE.md/GEMINI.md/.cursor/.github are thin pointers to it
├── GEMINI.md                                # per-tool pointer (Gemini)
├── CHANGELOG.md                             # repo-level changelog (separate from skill CHANGELOG)
├── LICENSE / LICENSE.txt                    # BSD-3-Clause
├── README.md                                # human-facing intro
│
├── azure-pipelines.yml                      # primary CI: Azure DevOps
├── .azure-pipelines/                        # CI templates
├── .ci_support/                             # CI helper scripts
├── .scripts/                                # 5 build-step shell/bat helpers invoked by CI (build_steps.sh, run_docker_build.sh, run_osx_build.sh, run_win_build.bat, logging_utils.sh)
├── .github/                                 # 8 workflows + actions/ + issue templates + copilot-instructions.md
├── .appveyor.yml.notused                    # legacy AppVeyor (disabled)
├── build-locally.py                         # ★ Docker-based local-build harness (Linux builds run here)
├── test-recipes.py                          # inherited staged-recipes recipe-test driver
│
├── .env, .env.github, .secrets, .private     # local env / secret material (gitignored)
├── .gitignore                               # 738 lines — covers pixi/rattler/output dirs, Tier-3 artifacts, node_modules
├── .gitattributes                           # git LFS attrs etc.
├── .cursorrules / .cursor/                  # Cursor IDE rules (.cursor/rules/specs.mdc is the spec pointer)
├── .windsurfrules / .junie/                 # Windsurf + JetBrains AI rules (analogs to CLAUDE.md)
├── .idea/                                   # JetBrains IDE config (gitignored)
│
├── .claude/                                 # ★★ Parts 1 + 3 (skill + MCP server) + 93 skill dirs + memory/ + hooks/ + settings.json
├── _bmad/                                   # ★★ Part 4: BMAD installer (config layers + bmm/core/skf modules)
├── _bmad-output/                            # ★★ Part 4: BMAD per-project artifacts (14 projects + 2 gitignored symlinks)
├── .bmad-loop/                              # bmad-loop orchestrator: policy.toml (13.5 KB) + bmad_loop_hook.py + runs/ (gitignored)
│
├── src/                                     # ★★ Part 5: the `pyforge` package family (5 dists) + sentinel/ + prototype/
│
├── recipes/                                 # 1,664 recipe directories (OUTPUTS of the system, not part of it)
│
├── docs/                                    # ★ Tier 0 dreams/ + legacy Tier 1 specs/ + reference/ + intake/ + dashboard/ (no top-level .md)
├── presentations/                           # 14 deck dirs + README.md — one per Claude Design project; 6-artifact family each
├── scripts/                                 # 14 tracked repo-level helpers (bmad-switch, drift-check, spec-surface-check, deck-export, …)
├── tests/                                   # repo-level shell tests (still just test_load_env.sh)
├── conf/                                    # conf/base/knowledge.yml — config for the sentinel knowledge pipeline
├── helm/                                    # helm/lasuite-docs/values.yaml — La Suite Docs deployment values
├── archive/                                 # retired docs (archive/docs/: bmad-setup-plan.md + specs/gists/ 13 captured gists)
├── _skf-learn/                              # Skill-Forge (skf-*) learning corpus — 18 tracked .md + _data/ + _internal/
│
├── SDKs/                                    # macOS SDK files (MacOSX11.0.sdk + tarball) — untracked, cross-compile from Linux
├── build_artifacts/                         # rattler-build OUTPUT dir (gitignored) — .conda files + bld/ logs
│
└── .pixi/                                   # pixi env caches (gitignored)
```

**Reading guide:**
- `★` marks entry points an AI agent reads on first activation
- `★★` marks the five-part architecture roots
- Lines without annotations exist but are routine config/CI plumbing

**Verified absent** (claimed by the pre-2026-07-25 revision, confirmed non-existent): root `pyproject.toml`, root `package.json`, `output/`, `build.pid`, and every top-level `docs/*.md` — one of which was purged 2026-07-24 in secret-leak remediation and must not be re-cited anywhere.

---

## Part 1 + Part 3: `.claude/` subtree

```
.claude/
│
├── settings.json                            # ★ permissions + enabledPlugins + customInstructions + hooks; wires the bmad-loop hook on SessionStart / Stop / SessionEnd / PreCompact
├── settings.local.json                      # per-machine overrides
│
├── tools/                                   # ★★ Part 3: FastMCP server lives here
│   ├── conda_forge_server.py                # 2,266 LOC / 46 `@mcp.tool` (recipe-authoring + atlas-intelligence + project-scanning)
│   ├── gemini_server.py                     # auxiliary MCP server (Gemini integration)
│   ├── mcp_call.py                          # MCP helper utilities (used by scripts that bridge to MCP runtime)
│   └── __pycache__/                         # (runtime artifact)
│
├── hooks/                                   # post-tool-call.py — the single repo-level Claude Code hook script
│
├── memory/                                  # checked-in team-memory layer (5 tracked files)
│   ├── MEMORY.md / README.md                # index + contributor guide
│   └── feedback/ · project/ · reference/    # .gitkeep-seeded buckets (`pyforge.scribe` writes here — see Part 5)
│
├── docs/                                    # internal Claude-Code notes — currently just bmad-method-llms-full.txt (offline BMAD copy)
│
├── skills/                                  # 93 dirs = 89 real skills + 4 non-skill support dirs (cf-atlas-legacy, data, knowledge, shared — none has a SKILL.md)
│   │                                        # real split: 51 bmad-*, 16 skf-*, 21 engineering-practice, 1 conda-forge-expert
│   │
│   ├── conda-forge-expert/                  # ★★ Part 1 canonical source
│   │   ├── SKILL.md                         # ★ primary spine (3,887 lines): critical constraints, 10-step loop, gotchas G1–G107
│   │   ├── INDEX.md                         # task→tool navigator
│   │   ├── CHANGELOG.md                     # ★ release history (1,841 lines) with TL;DR (canonical drift-detection source; v8.79.1 current)
│   │   ├── MANIFEST.yaml                    # declares "standalone-portable" deployment (host-repo install.py target)
│   │   ├── install.py                       # bootstraps the skill into another host repo (writes wrappers, copies MCP)
│   │   │
│   │   ├── reference/                       # 15 deep-reference files
│   │   │   ├── recipe-yaml-reference.md          # v1 recipe.yaml schema deep-ref
│   │   │   ├── recipe-yaml-reference-full.md     # full generated v1 schema (gen_yml_reference.py)
│   │   │   ├── meta-yaml-reference.md            # v0 meta.yaml legacy ref
│   │   │   ├── mcp-tools.md                      # MCP tool inventory + signatures
│   │   │   ├── python-min-policy.md              # CFEP-25 + python_min triad rules
│   │   │   ├── conda-forge-yml-reference.md      # conda-forge.yml subset
│   │   │   ├── conda-forge-yml-reference-full.md # full generated conda-forge.yml schema
│   │   │   ├── pinning-reference.md              # global pin rules
│   │   │   ├── selectors-reference.md            # rattler-build selector syntax
│   │   │   ├── jinja-functions.md                # ${{ compiler() / stdlib() / pin_subpackage() / cdt() }}
│   │   │   ├── abi3-matrix-collapse.md           # abi3 / stable-ABI build-matrix collapse
│   │   │   ├── dependency-input-formats.md       # scan_project input matrix (~28 formats)
│   │   │   ├── atlas-phases-overview.md          # consolidated atlas intelligence: Part A persona catalog + Part B phase index (absorbed atlas-actionable-intelligence.md, 2026-07-02)
│   │   │   ├── atlas-phase-engineering.md        # engineering patterns (rate limits, GraphQL, atomic writes) + § 13 Phase P cost model (absorbed atlas-phase-p-cost-model.md)
│   │   │   └── conda-forge-ecosystem.md          # ecosystem overview (bot, smithy, repodata-patches)
│   │   │
│   │   ├── guides/                          # 9 workflow guides
│   │   │   ├── getting-started.md
│   │   │   ├── migration.md                      # v0 → v1 migration
│   │   │   ├── ci-troubleshooting.md
│   │   │   ├── cross-compilation.md
│   │   │   ├── feedstock-maintenance.md
│   │   │   ├── feedstock-platform-expansion.md   # dual-goal refresh + platform-widen workflow
│   │   │   ├── testing-recipes.md
│   │   │   ├── sdist-missing-license.md          # specific recipe failure mode
│   │   │   └── atlas-operations.md               # cron schedules, hard reset, air-gap
│   │   │
│   │   ├── quickref/                        # 2 quick-reference files
│   │   │   ├── commands-cheatsheet.md            # pixi tasks + raw CLIs
│   │   │   └── bot-commands.md                   # @conda-forge-admin slash commands
│   │   │
│   │   ├── scripts/                         # ★★ Tier 1: canonical Python implementations (66 .py / 41,410 LOC)
│   │   │   │
│   │   │   ├── # ── Recipe lifecycle (Part 1 core) ──
│   │   │   ├── recipe-generator.py               # 2,653 LOC — generate_recipe_from_pypi entrypoint (grayskull + post-processing)
│   │   │   ├── recipe_editor.py                  # edit_recipe structured-action engine
│   │   │   ├── recipe_optimizer.py               # 17 lint codes (STD/TEST/PIN/DEP/etc.) — optimize_recipe
│   │   │   ├── recipe_updater.py                 # update_recipe (version/SHA bumps)
│   │   │   ├── validate_recipe.py                # validate_recipe (rattler-build --render dry-run)
│   │   │   ├── local_builder.py                  # trigger_build wrapper (rattler-build + Docker)
│   │   │   ├── failure_analyzer.py               # analyze_build_failure
│   │   │   ├── submit_pr.py                      # prepare_submission_branch + submit_pr (split flow)
│   │   │   ├── github_updater.py                 # update_recipe_from_github (autotick for GitHub-only sources)
│   │   │   ├── github_version_checker.py         # check_github_version
│   │   │   ├── npm_updater.py                    # npm-ecosystem recipe handling
│   │   │   ├── feedstock-migrator.py             # migrate_to_v1 (feedrattler invocation)
│   │   │   ├── feedstock_context.py              # get_feedstock_context
│   │   │   ├── feedstock_enrich.py               # enrich_from_feedstock
│   │   │   ├── feedstock_lookup.py               # lookup_feedstock
│   │   │   ├── license-checker.py                # license_file validation
│   │   │   ├── dependency-checker.py             # check_dependencies (PyPI→conda resolution)
│   │   │   ├── name_resolver.py                  # PyPI→conda name resolution engine
│   │   │   ├── _cfy_template.py                  # shared conda-forge.yml pre-seed renderer (v8.61.0; emitted by every generator path)
│   │   │   │
│   │   │   ├── # ── cf_atlas pipeline (Part 2 core) ──
│   │   │   ├── conda_forge_atlas.py              # ★ orchestrator, 8,902 LOC: `PHASES` = 22 executable phases, `SCHEMA_VERSION = 29`, run_single_phase
│   │   │   ├── _cf_graph_versions.py             # Phase H cf-graph offline backend (v7.7.0)
│   │   │   ├── _parquet_cache.py                 # Phase F S3 parquet cache layer (v7.6.0)
│   │   │   ├── atlas_phase.py                    # single-phase CLI entrypoint
│   │   │   ├── bootstrap_data.py                 # full-pipeline orchestrator: mapping + CVE + vdb + cf_atlas + Phase N
│   │   │   ├── detail_cf_atlas.py                # query helpers: detail-cf-atlas CLI
│   │   │   ├── inventory_channel.py              # channel inventory cache
│   │   │   ├── cisa_kev_fetcher.py               # CISA KEV overlay loader (v8.5.3)
│   │   │   ├── epss_fetcher.py                   # FIRST.org EPSS daily-CSV overlay (v8.6.0)
│   │   │   ├── cwe_catalog_fetcher.py            # MITRE CWE Research-Concepts catalog (v8.6.0)
│   │   │   ├── gen_yml_reference.py              # generates the *-reference-full.md schema docs
│   │   │   │
│   │   │   ├── # ── Atlas-intelligence query CLIs (Part 2 read side) ──
│   │   │   ├── staleness_report.py               # staleness-report
│   │   │   ├── feedstock_health.py               # feedstock-health
│   │   │   ├── whodepends.py                     # whodepends
│   │   │   ├── behind_upstream.py                # behind-upstream
│   │   │   ├── version_downloads.py              # version-downloads (Phase F-based)
│   │   │   ├── release_cadence.py                # release-cadence (Phase L-based)
│   │   │   ├── find_alternative.py               # find-alternative
│   │   │   ├── adoption_stage.py                 # adoption-stage
│   │   │   ├── pypi_only_candidates.py           # pypi-only-candidates (Phase D side-table reader, v7.9.0+)
│   │   │   ├── pypi_intelligence.py              # pypi-intelligence (Phase O→S reader, v8.1.0)
│   │   │   ├── platform_breakdown.py             # platform-breakdown (Wave-3 CLI, v8.19.0)
│   │   │   ├── pyver_breakdown.py                # pyver-breakdown (Wave-3 CLI, v8.19.0)
│   │   │   ├── channel_split.py                  # channel-split (Wave-3 CLI, v8.19.0)
│   │   │   ├── my_feedstocks.py                  # my-feedstocks (maintainer-scoped atlas view)
│   │   │   ├── cve_watcher.py                    # cve-watcher
│   │   │   ├── cve_manager.py                    # CVE DB CRUD (update_cve_database)
│   │   │   ├── vulnerability_scanner.py          # scan_for_vulnerabilities
│   │   │   ├── health_check.py                   # run_system_health_check
│   │   │   ├── env_inspect.py                    # env_inspect (build-env introspection)
│   │   │   ├── pr_artifacts.py                   # download_pr_artifacts (Azure DevOps, v8.14.0)
│   │   │   ├── scan_project.py                   # 3,703 LOC — scan_project (~28 input formats)
│   │   │   ├── _sbom.py                          # SBOM parsing helpers (CycloneDX / SPDX / Syft)
│   │   │   │
│   │   │   ├── # ── purl / SBOM / futures suite (v8.73.0 cyclonedx-universe-inventory) ──
│   │   │   ├── export_purls.py                   # export-purls (pkg:conda + upstream purls out of the atlas)
│   │   │   ├── mapping_gap.py                    # mapping-gap (unmapped PyPI↔conda ranking)
│   │   │   ├── universe_sbom.py                  # universe-sbom (full PyPI + conda-forge CycloneDX BOM)
│   │   │   ├── inventory_match.py                # inventory-match (manifest/lock/SBOM intake → atlas match + vulns gate)
│   │   │   ├── add_handoff.py                    # add-handoff (packaging-handoff emitter)
│   │   │   ├── library_futures.py                # library-futures (2027–2030 tiering)
│   │   │   ├── recommend_2027.py                 # recommend-2027 (py314 + LTS/endoflife scoring)
│   │   │   │
│   │   │   ├── # ── Read-only seed-gap suggesters (v8.74–v8.76; CLI/pixi only, no MCP tool) ──
│   │   │   ├── lts_registry_gap.py               # lts-registry-gap (endoflife.date ↔ v_actionable_packages diff)
│   │   │   ├── cwe_seed_gap.py                   # cwe-seed-gap (keyword-classified `Other` CWEs)
│   │   │   ├── spdx_schema_gap.py                # spdx-schema-gap (vendored-vs-upstream SPDX enum diff)
│   │   │   ├── license_map_gap.py                # license-map-gap (unmapped PyPI licenses → _LICENSE_TO_SPDX)
│   │   │   │
│   │   │   ├── # ── Shared infrastructure ──
│   │   │   ├── _http.py                          # ★ 1,024 LOC — truststore + JFrog/GitHub/.netrc auth chain (every outbound request)
│   │   │   ├── mapping_manager.py                # update_mapping_cache (PyPI→conda map refresh)
│   │   │   └── test-skill.py                     # skill-internal smoke test runner
│   │   │
│   │   ├── templates/                       # 41 templates + README across 13 ecosystems (12 language + conda-forge-yml); 39 .yaml + 2 .yml
│   │   │   ├── README.md
│   │   │   ├── python/{noarch,compiled,maturin}-{recipe.yaml,meta.yaml}    # v1 + v0 variants
│   │   │   ├── rust/{library-recipe.yaml, cli-recipe.yaml, cli-meta.yaml}
│   │   │   ├── go/{pure,cgo}-{recipe.yaml,meta.yaml}
│   │   │   ├── c-cpp/{header-only,autotools,cmake,meson}-recipe.yaml + cmake-meta.yaml
│   │   │   ├── r/{cran,bioconductor}-recipe.yaml + cran-meta.yaml
│   │   │   ├── java/{maven,gradle}-recipe.yaml + maven-meta.yaml
│   │   │   ├── ruby/gem-{recipe.yaml,meta.yaml}
│   │   │   ├── dotnet/nuget-{recipe.yaml,meta.yaml}
│   │   │   ├── fortran/f90-{recipe.yaml,meta.yaml}
│   │   │   ├── multi-output/ · nodejs/ · perl/   # 5 / 3 / 2 files
│   │   │   └── conda-forge-yml/{staged-recipes,feedstock}/conda-forge.yml  # conda-forge.yml starters (v7.3.0)
│   │   │
│   │   ├── tests/                           # 100 .py (98 test_*.py) / 1,186 `def test_` / 22,318 LOC
│   │   │   ├── unit/                             # 85 modules — function-level
│   │   │   ├── integration/                      # 4 modules — cross-module + network-marked
│   │   │   ├── meta/                             # 9 modules — ★ enforces invariants: test_recipe_yaml_schema_header,
│   │   │   │                                     #   test_all_scripts_runnable, test_bmad_artifacts_in_sync, test_spec_surface_check
│   │   │   ├── data/                             # 2 JSON schemas used by the meta suite
│   │   │   └── fixtures/                         # 39 files
│   │   │       ├── recipes/                      # real recipe.yaml snippets
│   │   │       ├── manifest_samples/             # scan_project inputs (~28 formats)
│   │   │       ├── error_logs/                   # build-failure samples for failure_analyzer
│   │   │       └── mocked_responses/             # selective mocks (rare; suite mostly uses real fixtures)
│   │   │
│   │   ├── config/                          # skill config templates
│   │   │   ├── skill-config.yaml                 # ★ carries the authoritative skill version (8.79.1)
│   │   │   └── enterprise-config.yaml.template   # JFrog/air-gap config starter
│   │   │
│   │   ├── data/                            # curated skill data (3 files)
│   │   │   ├── lts-registry.yaml                 # hand-curated LTS/endoflife registry (suggested by lts-registry-gap)
│   │   │   ├── cwe_categories_seed.json          # CWE category seed map
│   │   │   └── spdx.schema.json                  # vendored SPDX license enum
│   │   │
│   │   ├── examples/                        # 5 example recipes + README (c-library, multi-output, python-compiled, python-simple, rust-cli)
│   │   │
│   │   ├── automation/                      # quarterly audit workflow
│   │   │   ├── quarterly-audit.prompt.md
│   │   │   ├── run-audit-local.sh
│   │   │   └── README.md
│   │   │
│   │   ├── mappings/                        # name-mapping (legacy single file)
│   │   │   └── pypi-conda.yaml
│   │   │
│   │   └── pypi_conda_mappings/             # name-mapping (current multi-file)
│   │       ├── custom.yaml                       # user-curated overrides
│   │       ├── different_names.json              # large auto-generated table
│   │       └── stats.json                        # mapping coverage stats
│   │
│   ├── # ── BMAD installer skills (51 bmad-* of the 93 dirs) ──
│   ├── bmad-agent-{analyst,architect,dev,pm,tech-writer,ux-designer}/    # 6 persona agents
│   ├── bmad-{prd,architecture,create-epics-and-stories,create-story,ux,spec}/  # planning chain (6.10: bmad-create-{prd,architecture} are deprecated wrappers)
│   ├── bmad-{advanced-elicitation,brainstorming,party-mode,forge-idea,...}/   # process skills
│   ├── bmad-{retrospective,code-review,review,review-adversarial-general,...}/ # review/retro skills
│   ├── bmad-{quick-dev,dev-story,dev-auto,document-project,...}/         # implementation skills
│   ├── bmad-{sprint-planning,sprint-status,correct-course}/              # sprint skills
│   ├── bmad-loop-{setup,resolve,sweep}/                                  # bmad-loop orchestrator skills (see .bmad-loop/)
│   │
│   ├── # ── Skill Forge skills (16 skf-*) ──
│   ├── skf-{setup,analyze-source,brief-skill,create-skill,quick-skill,test-skill,export-skill,...}/
│   │                                        # learning corpus for these lives at repo root in _skf-learn/
│   │
│   ├── # ── Non-skill support dirs (4; no SKILL.md — excluded from the 89 real skills) ──
│   ├── cf-atlas-legacy/ · data/ · knowledge/ · shared/
│   │
│   └── # ── Engineering practice skills (21) ──
│   │   ├── api-and-interface-design/        # cross-language API design patterns
│   │   ├── ci-cd-and-automation/
│   │   ├── code-review-and-quality/
│   │   ├── code-simplification/
│   │   ├── context-engineering/
│   │   ├── debugging-and-error-recovery/
│   │   ├── deprecation-and-migration/
│   │   ├── documentation-and-adrs/
│   │   ├── frontend-ui-engineering/
│   │   ├── git-workflow-and-versioning/
│   │   ├── idea-refine/
│   │   ├── incremental-implementation/
│   │   ├── performance-optimization/
│   │   ├── planning-and-task-breakdown/
│   │   ├── security-and-hardening/
│   │   ├── shipping-and-launch/
│   │   ├── source-driven-development/
│   │   ├── spec-driven-development/
│   │   ├── test-driven-development/
│   │   ├── using-agent-skills/
│   │   └── browser-testing-with-devtools/
│
├── scripts/                                 # ★★ Part 1 Tier 2: CLI wrapper layer
│   └── conda-forge-expert/                  # 60 entries = 57 thin .py subprocess wrappers + cross-build.sh + native-build.sh + README.md
│       ├── (most names mirror skill scripts/, plus prepare_pr.py which delegates to submit_pr.py --prepare-only)
│
└── data/                                    # ★★ Part 1 Tier 3 + Part 2 artifacts (gitignored)
    │                                        # ⚠ ABSENT in this checkout — the atlas has never been built here.
    │                                        #   The layout below is the DOCUMENTED shape (what bootstrap_data creates), not a live listing.
    └── conda-forge-expert/
        ├── cf_atlas.db                           # ★ Part 2 primary artifact (SQLite, schema v29; `packages` + `pypi_universe` + `pypi_intelligence` + cisa_kev/epss_scores/cwe_categories overlays + ~15 supporting tables)
        ├── cf_atlas.db-shm                       # SQLite shared memory (WAL mode)
        ├── cf_atlas.db-wal                       # SQLite write-ahead log
        ├── cf_atlas_meta.json                    # atlas run metadata
        ├── cf-graph-countyfair.tar.gz            # cf-graph offline snapshot (Phases E, H, M)
        ├── pypi_conda_map.json                   # PyPI→conda name cache (refreshed by update_mapping_cache)
        ├── vdb/                                  # AppThreat vulnerability DB (populated in vuln-db env)
        ├── vdb-cache/                            # vdb runtime cache
        ├── cve/                                  # CVE feed cache
        ├── cache/parquet/                        # (created on demand) Phase F S3 monthly parquet cache
        └── inventory_cache/                      # (created on demand) scan_project inventory cache
```

**Tier discipline:** every CLI in `.claude/scripts/conda-forge-expert/` is a thin (~10-30 line) subprocess wrapper that delegates to the canonical implementation in `.claude/skills/conda-forge-expert/scripts/`. New scripts touch three places (the wrapper + a pixi task + the meta-test `SCRIPTS` list); this discipline is enforced by `tests/meta/test_all_scripts_runnable.py`.

---

## Part 2: cf_atlas artifacts under `.claude/data/`

See `architecture-cf-atlas.md` for the full pipeline + schema. The data subtree above shows the artifacts at rest — *not built in this checkout*, so nothing below was read from a live DB; it is sourced from `conda_forge_atlas.py` itself.

**Key entry points:**
- **Orchestrator:** `.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py` — `PHASES` registry + `run_single_phase()` + `bootstrap_data()` chain
- **Phase count:** the `PHASES` list holds **22 executable phases** — B, B.5, B.6, C, C.5, D, O, P, Q, R, S, E, E.5, F, G, G', H, J, K, L, M, N. `reference/atlas-phases-overview.md` catalogs **23** because it also documents a runner-less conceptual *Phase I*. Correct phrasing anywhere in this doc set: **22 executable, 23 cataloged**. (`bmad-groundtruth` reports 23 for a different reason — its `phase_count()` regexes `def phase_` and mis-counts the per-row helper `phase_r_upsert_one`.)
- **Schema version:** `SCHEMA_VERSION = 29` (line 139); migrations in `init_schema()` (idempotent; runs on every open)
- **TTL-gated columns:** `*_fetched_at` per phase; gated by `progress_every = min(max(N, len // 40), 2500)` with 60s heartbeat
- **Checkpoint table:** `phase_state` (added v7.7.0)

**Note on the Kedro reimplementation:** `src/shared/packages/pyforge-atlas/` (Part 5) is a *parallel* Kedro/Dagster/Ibis→DuckDB reimplementation of this pipeline, not a replacement — `conda_forge_atlas.py` remains the live orchestrator behind the MCP tools and CLIs. See § *Part 5*.

---

## Part 4: BMAD subtree

```
_bmad/                                       # ★★ BMAD installer (regenerated by BMAD-METHOD)
│
├── config.toml                              # layer 1: installer team, regenerated
├── config.user.toml                         # layer 2: installer user, regenerated
├── _config/                                 # internal installer state
│
├── core/                                    # BMAD core module (config.yaml + module-help.csv)
│
├── bmm/                                     # BMAD module: planning + dev workflows
│   ├── config.yaml                          # module config (user_name, project_knowledge, planning_artifacts)
│   └── module-help.csv                      # module help index (workflow phases now live in skills/, not here)
│
├── skf/                                     # Skill Forge module: config.yaml + module.yaml + module-help.csv
│   ├── knowledge/ · shared/                 # module-scoped assets
│   └── skf-*/                               # per-skill module blocks mirroring .claude/skills/skf-*
│
├── custom/                                  # global overrides (NOT regenerated)
│   ├── config.toml                          # layer 3: global custom team
│   ├── config.user.toml                     # layer 4: global custom user (absent here — layer resolves empty)
│   ├── .active-project                      # active-project marker file (managed by scripts/bmad-switch)
│   └── bmad-agent-dev.toml, bmad-agent-pm.toml   # the 2 live per-skill overrides
│
└── scripts/                                 # config resolution helpers
    ├── resolve_config.py                    # six-layer config merge (key-based query)
    ├── resolve_customization.py             # per-skill workflow-block resolver
    └── memlog.py                            # spec memlog appender (paired with scripts/spec_surface_check.py)

_bmad-output/                                # ★★ BMAD per-project artifacts
│
├── PROJECTS.md                              # multi-project index ("what's hosted here")
│
├── planning-artifacts       -> projects/<active>/planning-artifacts        # ★ gitignored symlink
├── implementation-artifacts -> projects/<active>/implementation-artifacts  # ★ gitignored symlink
│                                            #   _bmad/bmm/config.yaml hard-codes planning_artifacts to the SYMLINK path,
│                                            #   so every write-skill resolves through it — marker and symlinks must agree.
│                                            #   Switch only via `scripts/bmad-switch <slug>` (re-points both, marker last).
│
└── projects/                                # 14 projects
    ├── deckcraft/ · presenton-pixi-image/ · unity-data-stack/ · wasm-analytics-stack/
    ├── pyforge-{atlas,doctor,genesis,herald,marshal,mason,scribe,steward,warden}/   # the Smith projects
    │   ├── planning-artifacts/              # Tier 2 — tracked (PRD, architecture, epics, specs/)
    │   └── implementation-artifacts/        # Tier 3 — gitignored; NOTHING here may be git-tracked
    │
    └── local-recipes/                       # ★ this project (55 tracked files)
        ├── project-context.md               # ★ foundational rules every BMAD agent reads
        ├── SYNC-RUNBOOK.md                  # ★ the reconcile procedure this document is produced by
        ├── planning-artifacts/              # ← THIS DOCUMENT SET LANDS HERE
        │   ├── PRD.md / epics.md / architecture*.md / project-overview.md / index.md / ...
        │   ├── source-tree-analysis.md      # ← THIS FILE
        │   ├── project-parts.json           # machine-readable part manifest — reconciled to 5 parts in this same
        │   │                                #   2026-07-25 pass; the fifth `part_id` is `pyforge-packages` (= § Part 5 below)
        │   ├── specs/                       # 8 tracked Spec dirs (spec-packaging-factory, spec-fleet-stewardship,
        │   │                                #   spec-regenerable-factory, spec-factory-console, spec-enterprise-airgap,
        │   │                                #   spec-modernist-identity, spec-multi-loop-isolation, spec-pyforge-marshal)
        │   ├── research/                    # 4 dated research reports (2026-07-16)
        │   ├── change-history/              # sprint-change proposals (9 files)
        │   └── validation-report-PRD.md / implementation-readiness-report.md / campaign-*.md
        └── implementation-artifacts/        # Tier 3 — gitignored (deferred-work.md, spec mirrors, retros/)
```

**Tier model** (never crossed — full statement in `AGENTS.md`):

| Tier | Location | Git |
|---|---|---|
| 0 — Dream | `docs/dreams/*.md` | tracked, permanent |
| 1 — Intake spec (LEGACY) | `docs/specs/*.md` | tracked, phasing out — author no new files here |
| 2 — Spec & planning | `_bmad-output/projects/<slug>/planning-artifacts/` | tracked, permanent |
| 3 — Execution output | `_bmad-output/projects/<slug>/implementation-artifacts/` | **gitignored / local-only** |

**Story specs are durable (tracked), NOT Tier-3** (convention since 2026-07-25): bmad-loop drafts a story spec into the run's gitignored `implementation-artifacts/`, and after the story merges it is promoted into the tracked `planning-artifacts/specs/` subdir. Motivating incident: pyforge-warden lost 13 of 31 story specs to worktree teardown before this convention existed (fully recovered 2026-07-25).

**Active-project resolution priority:**
1. `--project <slug>` CLI flag (per-call)
2. `BMAD_ACTIVE_PROJECT` env var
3. `_bmad/custom/.active-project` marker file (managed by `scripts/bmad-switch`)
4. Fallback: only layers 1-4 resolve (no project-scoped config)

---

## Part 5: `src/` — the `pyforge` package family (`part_id: pyforge-packages`)

**New in this revision.** The repo's fifth architectural part is `src/`: real, installable Python distributions (2,454 of 3,042 files tracked), as opposed to Parts 1–3 which are skill/wrapper/server code that runs in place. Each of the five dists under `src/shared/packages/` is a **hatchling** build with its own `pyproject.toml` **and** its own `[package]`-style `pixi.toml` (a pixi *workspace member* — no `[workspace]` table of its own; the root `pixi.toml` owns the 5 matching `pyforge-*` envs).

They share a **PEP 420 implicit namespace**: there is deliberately **no `src/pyforge/__init__.py` in any package** (verified: zero such files), which is what lets the five modules coexist under one `pyforge` namespace.

```
src/
│
├── shared/packages/                         # ★★ the five installable dists (the Smiths that have code)
│   │
│   ├── pyforge-warden/                      # module pyforge.warden · py≥3.12 · console script `warden`
│   │   ├── src/pyforge/warden/              # 16,597 LOC / 28 .py — the multi-axis dependency compliance gate
│   │   │   ├── cli.py 1879 · engines.py 1880 · vuln.py 1244 · config.py 1031 · models.py 908
│   │   │   ├── waiver.py 873 · currency.py 869 · report.py 818 · license.py 797 · interfaces.py 557
│   │   │   ├── hygiene.py 550 · inventory.py 534 · actuator.py 494 · feeds.py 419 · discovery.py 244
│   │   │   ├── sbom.py 199 · verdict.py 140 · routing.py 96 · mapping.py 51
│   │   │   ├── extract/                     # ★ "the no-execution zone" — parse manifests, never execute them
│   │   │   │   └── _identity.py 688 · recipe_v1.py 658 · meta_v0.py 532 · lockfiles.py 318
│   │   │   │      · pixi.py 293 · pyproject.py 225 · environment_yml.py 208
│   │   │   ├── data/report-schema.json      # ★ 575 lines, title `ComplianceReport` — the one schema-validated output
│   │   │   ├── data/conda_pypi_map.json     # 1.5 MB / 59,292 lines
│   │   │   ├── data/lts-registry.yaml       # (own copy; the CFE skill carries a parallel one)
│   │   │   └── py.typed
│   │   ├── tests/                           # 29,752 LOC / 65 .py / 1,575 `def test_`
│   │   │   └── fixtures/                    # ⚠ 16 MB / 2,031 files — a 1,988-file recipe corpus
│   │   │                                    #   + 24 fixture projects + an offline osv-db
│   │   ├── scripts/                         # 5 .py / 1,287 LOC (maintenance helpers)
│   │   └── dist/ + dist-conda/              # build outputs
│   │
│   ├── pyforge-atlas/                       # module pyforge.atlas · py≥3.14 · console script `pyforge-atlas`
│   │   ├── src/pyforge/atlas/               # 14,461 LOC / 78 .py — Kedro/Dagster reimplementation of cf_atlas
│   │   │   ├── settings.py · pipeline_registry.py · hooks.py · __main__.py
│   │   │   ├── observability.py 478 · validation.py 359
│   │   │   ├── pipelines/                   # 7 Kedro pipelines: core, pypi_intelligence, vulnerability,
│   │   │   │                                #   vcs_health, universal_sbom, seed_gaps, derived_artifacts
│   │   │   ├── datasets/                    # 9 custom Kedro datasets (basilisk, incremental_parquet,
│   │   │   │                                #   migration_status, rate_limit, refresh, request_datasets,
│   │   │   │                                #   sbom_intake, vdb_boundary, …)
│   │   │   ├── orchestration/definitions.py # 735 LOC — Dagster definitions
│   │   │   ├── mcp/                         # ★ its OWN second FastMCP server (11 `@mcp.tool()` in mcp/server.py)
│   │   │   ├── semantic/                    # Ibis → DuckDB query layer
│   │   │   └── factory/ · a2a/ · dashboard/ (Vizro) · parity/ · rag/ · nl/ · publish/
│   │   ├── conf/base/                       # ★ contracts live OUTSIDE the wheel: catalog.yml (800 lines),
│   │   │                                    #   globals.yml, parameters.yml, dagster.yml
│   │   ├── tests/                           # 14,682 LOC / 110 .py / 772 `def test_`
│   │   ├── wasm/                            # wasm build assets
│   │   └── dist/ + dist-conda/
│   │                                        # Storage note: Parquet read by Ibis→DuckDB at query time —
│   │                                        # there is NO persisted .duckdb file (verified: 0 found).
│   │
│   ├── pyforge-herald/                      # module pyforge.herald · py≥3.12 · console script `herald`
│   │   ├── src/pyforge/herald/              # 1,277 LOC / 6 .py — tests 1,594 LOC / 5 .py / 112 `def test_`
│   │   │   ├── transport/mcp_transport.py 626 + transport/base.py 462   # ← the real code
│   │   │   └── cli.py 72                    # ⚠ deliberate stub: `herald deck` has ZERO registered subparsers
│   │
│   ├── pyforge-scribe/                      # module pyforge.scribe · py≥3.12 · console script `scribe`
│   │   ├── src/pyforge/scribe/              # 421 LOC / 4 .py — tests 323 LOC / 2 .py / 18 `def test_`
│   │   │   ├── capture.py 202               # real — writes into `.claude/memory/<type>/`
│   │   │   └── (`graph compile` and `recall` are explicit stubs)
│   │
│   └── pyforge-doctor/                      # module pyforge.doctor · py≥3.14 · console script `doctor`
│       └── src/pyforge/doctor/              # ⚠ SCAFFOLD ONLY — 304 LOC / 4 .py; tests 1,081 LOC / 6 .py / 62 `def test_`
│           ├── models.py 189 · verdict.py 44 · __init__.py (empty)
│           ├── __main__.py 71               # only --version / --help
│           └── data/report-schema.json      # 92 lines, title `DoctorReport`
│
├── sentinel/knowledge/                      # loose, NON-packaged Python (no pyproject.toml, no __init__.py anywhere)
│   ├── config.py · crews/compilation_crew.py · dagster/assets.py
│   ├── lasuite/client.py · lasuite/sync.py  # 5 .py / 346 LOC total
│   └── agents/compiler.md
│                                            # Imported as top-level `sentinel.knowledge` by 14 `wiki-*` pixi tasks
│                                            # and by pyforge-atlas tests. Config: conf/base/knowledge.yml; deploy: helm/lasuite-docs/.
│
└── prototype/packages/pyforge-atlas-kedro-viz/   # GENERATED, dependency-free kedro-viz mirror of the atlas DAG
    │                                        # setuptools (not hatchling); 283 files but only 14 .py / 915 LOC —
    │                                        # ~98% of the bulk is a checked-in static `build/` export. No tests.
    └── tools/regenerate_from_atlas.py       # ★ regenerate from here; never hand-maintain
```

**Verified defect — `src/sentinel/knowledge/` is largely inert.** `pixi.toml` wires 14 `wiki-*` tasks against 9 crew modules, but only `crews/compilation_crew.py` exists on disk; the other 8 (`linting_crew`, `qa_crew`, `ingestion_crew`, `cleaning_crew`, `search_crew`, `chat_crew`, `summarization_crew`, `review_crew`) are **missing**. `crews/` also has no `__init__.py`, and `compilation_crew.py` has no `__main__` guard — so even `wiki-compile`, the one task whose module exists, is a no-op. Recorded here as a finding, not fixed (out of scope for a doc reconcile).

**Cross-part relationships:**
- `pyforge.warden` is the compliance gate specified by `docs/specs/pyforge-warden.md` + `_bmad-output/projects/pyforge-warden/` (31/31 stories, merged 2026-07-25). Its `report-schema.json` is the contract; the `doctor` schema is the same shape at scaffold stage.
- `pyforge.atlas` parallels Part 2's `conda_forge_atlas.py` (see § *Part 2* note) and adds a **second** FastMCP server alongside Part 3's `.claude/tools/conda_forge_server.py`.
- `pyforge.scribe` writes into Part 1's `.claude/memory/` buckets.
- `pyforge.herald` renders Dreams into decks — output lands in `presentations/`.

---

## Repository support: `docs/` + `scripts/` + `presentations/`

`docs/` is now **five subdirectories and no top-level files** — the three reference docs moved into `docs/reference/`, and `bmad-setup-plan.md` retired to `archive/docs/`. All 83 files are tracked.

```
docs/                                        # 83 files, all tracked
│
├── dreams/                                  # ★ TIER 0 — 26 Dreams + README.md
│   ├── pyforge-charter.md                   # ★★ the binding identity document: Branding + The Lexicon
│   │                                        #   (PyForge in prose / `pyforge` in code; the eight Smiths;
│   │                                        #    "The Spec", capital-S — the five-field contract, and the
│   │                                        #    older synonym for it is retired; do not revive it;
│   │                                        #    the program console is the Guildhall)
│   ├── ecosystem-crew.md                    # the founding Dream (the persona crew)
│   ├── pyforge-{atlas,doctor,genesis,herald,marshal,mason,scribe,steward,warden}.md   # per-Smith Dreams
│   ├── packaging-factory.md · fleet-stewardship.md · regenerable-factory.md · factory-console.md
│   ├── enterprise-airgap.md · modernist-identity.md · agentic-sdlc-autonomy.md · agent-portability.md
│   ├── design-code-bridge.md · team-memory.md · upstream-discovery.md · sentinel.md
│   └── deckcraft.md · presenton-pixi-image.md · unity-data-stack.md · wasm-analytics-stack.md
│
├── specs/                                   # TIER 1 (LEGACY) — 19 in-flight specs; author no new files here
│   ├── # ── active packaging efforts ──
│   ├── langflow-conda-forge.md · db-gpt-conda-forge.md · flyte-conda-forge.md
│   ├── feedstock-refresh.md · trendshift-conda-forge.md
│   ├── # ── timeless workflows (parameterized, re-runnable) ──
│   ├── feedstock-platform-expansion.md · feedstock-failure-remediation.md · presentation-deck.md
│   ├── # ── tooling / adjacent ──
│   ├── bmad-loop-adoption.md · bmad-copilot-adapter-upstream.md · claude-team-memory.md
│   ├── conda-forge-tracker.md · copilot-bridge-vscode-extension.md · pyforge-warden.md
│   └── # ── shipped (historical record) ──
│       cfe-atlas-datapipeline-kedro-migration.md · cfe-shipped-releases.md
│       cyclonedx-universe-inventory.md · lts-registry-gap.md · seed-gap-suggesters.md
│
├── reference/                               # 6 files (was the docs/ top level)
│   ├── mcp-server-architecture.md           # FastMCP server + name-mapping subsystem
│   ├── enterprise-deployment.md             # air-gap + JFrog (incl. v7.6.0+ cross-host leak)
│   ├── developer-guide.md                   # local testing + recipe development
│   ├── library-llms-full.md                 # ★ LLM-facing catalog of every library/CLI in the pixi envs
│   │                                        #   (drift detector: `pixi run -e local-recipes llms-full-check`)
│   ├── pixi-config-jfrog.example.toml       # example .pixi/config.toml for JFrog air-gap
│   └── README.md
│
├── intake/                                  # 27 files — captured source material (agentic-sdlc/, gists/, sentinel/)
│
└── dashboard/                               # ★ the Guildhall — program console published to GitHub Pages
    ├── index.html · data.js · generate.py · README.md      # built by .github/workflows/dashboard.yml

scripts/                                     # 14 tracked entries (+ __pycache__)
├── bmad-switch                              # ★ active-project switcher — re-points BOTH symlinks, writes marker last
├── bmad_drift_check.py                      # ★ the detector this reconcile loop runs (--specs / --fix / --write-baseline)
├── spec_surface_check.py                    # ★ deterministic spec-surface coverage + drift checker (CFE v8.79.1)
├── spec_surface_allowlist.txt               #   its allowlist
├── .spec-surface-baseline.json              #   its baseline (462 KB, tracked)
├── bmad-loop-worktree                       # per-run git worktree helper for bmad-loop
├── deck_export.py                           # deck → Marp / PPTX export (backs the `deck-export` pixi task)
├── llms_full_check.py                       # staleness detector for docs/reference/library-llms-full.md
├── load-env.sh                              # parses pixi.toml default-env: directive
├── offline-build.sh                         # air-gap-aware build invocation
├── submit_pr.sh                             # shell wrapper around pixi submit-pr
├── sync-upstream-conda-forge.sh             # sync from conda-forge/staged-recipes upstream
├── sync_pypi_mappings.py                    # refresh pypi-conda mapping data
└── mirror-channels.py                       # internal mirror seeding (JFrog channel population)

presentations/                               # 14 deck dirs + README.md; 692 tracked files of 31,718 on disk
│                                            # (node_modules/ + dist/ dominate the untracked remainder)
├── agentic-sdlc/                            # Worked Example 1 of docs/specs/presentation-deck.md (45 slides)
├── pyforge-{atlas,doctor,genesis,herald,marshal,mason,scribe,steward,warden}/
├── deckcraft/ · presenton-pixi-image/ · unity-data-stack/ · wasm-analytics-stack/
└── <deck>/                                  # each mirrors a Claude Design project and carries the same
    ├── index.html · package.json · project/ # 6-artifact family: deck prototype, built React deck,
    ├── src/ · public/ · scripts/            # exec summary, infographic trio, marp sources, pptx exports
    └── dist/ · node_modules/                # (gitignored build output + deps)

.github/workflows/                           # 8 active workflows + scripts/{linter,linter_issue_comment}.py
├── staged-recipes-linter.yml                # ★ the ALWAYS-ON PR gate (maintenance label + environment.yaml sync)
├── dashboard.yml                            # ★ publishes docs/dashboard/ (the Guildhall) to GitHub Pages
├── test-{all,linux,macos,windows}.yml       # workflow_dispatch / workflow_call only
├── linter_issue_comment.yml                 # gated: only on "please rerun linter" / "/rerun-linter"
└── sync-pypi-mappings.yml                   # workflow_dispatch only (cron off pending a green run)
   # 5 inherited files deleted 2026-07-26 (PR #127) — upstream had deleted all five.
   # Inventory + provenance: docs/reference/github-workflows.md
```

---

## Output / build directories (gitignored)

```
build_artifacts/                             # rattler-build OUTPUT (final .conda files + per-build logs)
├── <config-hash>/
│   ├── <subdir>/                            # linux-64, linux-aarch64, osx-arm64, win-64, noarch
│   │   └── <name>-<version>-<build>.conda
│   └── bld/                                 # per-build working dir
│       └── rattler-build_<name>_<id>/
│           └── work/
│               └── conda_build.log          # ★ authoritative success/failure log (G6 — see project-context § Anti-Patterns)

SDKs/                                        # cross-compile SDKs — 30,811 files, ZERO tracked (local-only, not committed)
├── MacOSX11.0.sdk.tar.xz                    # macOS 11.0 SDK tarball
└── MacOSX11.0.sdk/                          # extracted SDK (used for cross-compile from Linux to osx-64)

.bmad-loop/runs/                             # per-run bmad-loop state (gitignored); policy.toml + hook are tracked

src/shared/packages/*/dist/ + dist-conda/    # per-package wheel/sdist + .conda build outputs (Part 5)
```

> **Removed 2026-07-25:** the prior revision documented a top-level `output/` (rattler-build working dir with `bld/`, `broken/`, per-platform staging, `src_cache/`, `rattler-build-log.txt`). **No such directory exists** — `build_artifacts/` is the only rattler-build output root. Likewise the SDKs comment "committed binary" was wrong: nothing under `SDKs/` is tracked.

---

## Recipe corpus (out of scope for rebuild)

```
recipes/                                     # 1,664 recipe directories (933 recipe.yaml + 1,024 meta.yaml; 300 dirs carry BOTH)
└── <package-name>/
    ├── recipe.yaml                          # v1 format (canonical); schema_version: 1
    ├── meta.yaml                            # v0 format (legacy, migration source only)
    ├── patches/                             # optional upstream-bug shims
    │   └── 0001-<short-description>.patch
    ├── LICENSE*                             # vendored license files (when license_file points here)
    ├── build.sh / bld.bat                   # legacy v0 build scripts (rare in v1 recipes)
    └── (other support files: extra_metadata.yaml, conda-forge.yml override, etc.)
```

The recipe corpus is the **output** of the system, not part of it. The rebuild target reconstructs the factory; recipes are re-authored using the rebuilt factory.

Counts here are **churny and never gated** — they move with every packaging session. Two measurement notes: `ls -1d recipes/*/` reports **1,664** while the drift detector's `iterdir()` reports **1,667** (it also counts hidden dirs); and the **300 dirs carrying both formats are deliberate**, not migration debris — a v0 feedstock keeps its `meta.yaml` until its v0→v1 switch completes. `recipes/**` is governed by the `spec-fleet-stewardship` Spec as coverage-only (`surface-drift: exempt`); per-recipe change control remains the 10-step loop plus gates.

---

## Entry points (start here when reading the codebase)

| For an agent doing… | Read first | Then |
|---|---|---|
| Any task (orientation) | `CLAUDE.md` | `_bmad-output/projects/local-recipes/project-context.md` |
| Authoring a recipe | `.claude/skills/conda-forge-expert/SKILL.md` | `INDEX.md` → 10-step loop |
| Atlas refresh / query | `.claude/skills/conda-forge-expert/guides/atlas-operations.md` | `scripts/conda_forge_atlas.py` PHASES registry |
| Adding a new MCP tool | `.claude/tools/conda_forge_server.py` | matching canonical script in `scripts/` |
| Adding a new CLI | `.claude/skills/conda-forge-expert/scripts/<new>.py` (canonical) | `.claude/scripts/conda-forge-expert/<new>.py` (wrapper) + `pixi.toml` task + meta-test SCRIPTS list |
| BMAD planning for a feature | `_bmad-output/PROJECTS.md` | `scripts/bmad-switch --current` → relevant skill |
| Air-gap / JFrog setup | `docs/reference/enterprise-deployment.md` | `.claude/skills/conda-forge-expert/scripts/_http.py` |
| CI failure debugging | `.claude/skills/conda-forge-expert/guides/ci-troubleshooting.md` | `build_artifacts/<config>/bld/rattler-build_<name>_<id>/work/conda_build.log` |
| Starting any new effort | `AGENTS.md` (tiers + Dream-first rule) | `docs/dreams/<slug>.md` → `bmad-spec` → `planning-artifacts/` |
| Naming / wording anything | `docs/dreams/pyforge-charter.md` § Branding + § The Lexicon | PyForge in prose, `pyforge` in code; the eight Smiths; The Spec; the Guildhall |
| Working on a `pyforge` dist | `src/shared/packages/<dist>/pyproject.toml` + its `pixi.toml` | `src/pyforge/<module>/` (PEP 420 — no namespace `__init__.py`) |
| Adding a library / dependency | `docs/reference/library-llms-full.md` | `pixi run -e local-recipes llms-full-check` |
| Reconciling these BMAD docs | `_bmad-output/projects/local-recipes/SYNC-RUNBOOK.md` | `pixi run -e local-recipes bmad-drift-check` + `scripts/spec_surface_check.py` |
| Publishing the program console | `docs/dashboard/generate.py` | `.github/workflows/dashboard.yml` → GitHub Pages |

---

## Critical files summary

These files are load-bearing — changing them affects the whole system, not just one part:

| File | Owner part | Why it's critical |
|---|---|---|
| `CLAUDE.md` | all | Repo-wide AI agent guidance + BMAD↔CFE integration rules |
| `AGENTS.md` | all | Cross-tool entry point; the tier model + Dream-first rule live here — the per-tool files are pointers |
| `docs/dreams/pyforge-charter.md` | all | Binding identity: branding, the Lexicon, the eight Smiths. Governs wording in every artifact |
| `pixi.toml` | all | Defines **18 envs / 17 features / 152 tasks**; the contract between human shell and tool surface. Changing it **requires** regenerating `environment.yaml` (ungated CI check) |
| `environment.yaml` | all | Exported mirror of the `build` env — the linter reds if it drifts from `pixi.toml`, and the `maintenance` label does NOT suppress that check |
| `.claude/skills/conda-forge-expert/SKILL.md` | Part 1 | Skill's primary spine (3,887 lines) — read by Claude Code on every conda-forge task |
| `.claude/skills/conda-forge-expert/CHANGELOG.md` | Part 1 | Canonical drift-detection source — every MINOR bump triggers a project-context re-sync; also the **CHANGELOG sentinel** for `spec_surface_check.py` (a governed edit that moves neither it nor the Spec memlog is a finding) |
| `.claude/skills/conda-forge-expert/config/skill-config.yaml` | Part 1 | Carries the authoritative skill version (8.79.1) that `source_pin` must match |
| `.claude/skills/conda-forge-expert/scripts/_http.py` | all (Parts 1+2+3) | Every outbound HTTP request routes through here. Contains the JFROG_API_KEY cross-host leak (mitigated via env-var hygiene; see deployment-guide.md) |
| `.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py` | Part 2 | 22-executable-phase pipeline orchestrator + schema migrations (`SCHEMA_VERSION = 29`) |
| `.claude/tools/conda_forge_server.py` | Part 3 | 46 MCP tools — auto-started at Claude Code session boot |
| `_bmad-output/projects/local-recipes/project-context.md` | Part 4 | Foundational rules every BMAD agent reads on spawn (CFE-version-pinned) |
| `_bmad/custom/.active-project` + the 2 `_bmad-output/` symlinks | Part 4 | Together they select the active project. `_bmad/bmm/config.yaml` hard-codes the **symlink** path, so a marker/symlink desync silently writes into the wrong project. Switch only via `scripts/bmad-switch` |
| `.claude/settings.json` | Part 4 | Wires the bmad-loop hook on SessionStart / Stop / SessionEnd / PreCompact |
| `.bmad-loop/policy.toml` | Part 4 | 13.5 KB orchestrator policy — gates, escalation, run layout |
| `scripts/spec_surface_check.py` + `.spec-surface-baseline.json` | all | Repo-wide Spec-coverage + surface-drift gate; every file must be classified by some Spec |
| `src/shared/packages/pyforge-warden/src/pyforge/warden/data/report-schema.json` | Part 5 | The one schema-validated `ComplianceReport` contract + CI exit-code gate |
| `src/shared/packages/pyforge-atlas/conf/base/catalog.yml` | Part 5 | 800-line Kedro catalog — the atlas reimplementation's contracts live outside the wheel |

---

## Counts (verified 2026-07-25)

Every row below was re-measured against the live checkout on 2026-07-25 — none is carried forward from a prior sync.

**Part 1 — conda-forge-expert skill**

| Asset | Count |
|---|---|
| CFE canonical scripts (Tier 1) | **66** `.py` / **41,410** LOC — largest: `conda_forge_atlas.py` 8,902, `scan_project.py` 3,703, `recipe-generator.py` 2,653, `_http.py` 1,024 |
| CFE CLI wrappers (Tier 2) | **60** entries = 57 `.py` + `cross-build.sh` + `native-build.sh` + `README.md` |
| Skill tests | **100** `.py` (98 `test_*.py`) / **1,186** `def test_` / **22,318** LOC — unit 85, meta 9, integration 4; fixtures 39 files, data 2 JSON schemas |
| Recipe templates | **41** + README across **13** ecosystems (12 language: c-cpp, dotnet, fortran, go, java, multi-output, nodejs, perl, python, r, ruby, rust + conda-forge-yml starter); 39 `.yaml` + 2 `.yml` |
| Skill reference docs | **15** |
| Skill guides | **9** |
| Skill quickrefs | **2** |
| Skill data / config / examples / automation | 3 / 2 / 6 / 3 |
| Name-mapping files | `pypi_conda_mappings/` 3 + legacy `mappings/` 1 |
| SKILL.md / CHANGELOG.md | 3,887 / 1,841 lines |
| Recipe-Authoring Gotchas | **G1–G107** |
| Skill version (source_pin) | **conda-forge-expert v8.80.0** |

**Part 2 — cf_atlas**

| Asset | Count |
|---|---|
| Atlas pipeline phases | **22 executable** (B, B.5, B.6, C, C.5, D, O, P, Q, R, S, E, E.5, F, G, G', H, J, K, L, M, N) — **23 cataloged** (`atlas-phases-overview.md` adds a runner-less conceptual Phase I) |
| Atlas schema version | **v29** (additive migrations only) |
| `.claude/data/conda-forge-expert/` | **absent in this checkout** — gitignored; the atlas has not been built here |

**Part 3 — MCP servers**

| Asset | Count |
|---|---|
| MCP tools (grep `@mcp.tool`, `.claude/tools/conda_forge_server.py`) | **46** (file is 2,266 LOC) |
| Second MCP server (Part 5) | `pyforge.atlas.mcp.server` — **11** `@mcp.tool()` |

**Part 4 — BMAD + agent surface**

| Asset | Count |
|---|---|
| `.claude/skills/` dirs | **93** = **89 real skills** + 4 non-skill support dirs (`cf-atlas-legacy`, `data`, `knowledge`, `shared` — none has a `SKILL.md`) |
| Real-skill split | **51** `bmad-*` · **16** `skf-*` · **21** engineering-practice · **1** `conda-forge-expert` |
| BMAD multi-projects | **14** (deckcraft, local-recipes, presenton-pixi-image, unity-data-stack, wasm-analytics-stack + 9 `pyforge-*`) |
| `planning-artifacts/` (local-recipes) | 55 tracked files; `specs/` 8 Spec dirs, `research/` 4, `change-history/` 9 |
| `.claude/memory/` | 5 tracked (MEMORY.md, README.md + 3 `.gitkeep` buckets) |
| `.claude/hooks/` | 1 (`post-tool-call.py`); `settings.json` wires SessionStart / Stop / SessionEnd / PreCompact |

**Part 5 — `src/` (`pyforge` family)** — new this revision

| Dist | module | py | script | src LOC / files | tests LOC / files / `def test_` |
|---|---|---|---|---|---|
| `pyforge-warden` | `pyforge.warden` | ≥3.12 | `warden` | 16,597 / 28 | 29,752 / 65 / **1,575** |
| `pyforge-atlas` | `pyforge.atlas` | ≥3.14 | `pyforge-atlas` | 14,461 / 78 | 14,682 / 110 / **772** |
| `pyforge-herald` | `pyforge.herald` | ≥3.12 | `herald` | 1,277 / 6 | 1,594 / 5 / **112** |
| `pyforge-scribe` | `pyforge.scribe` | ≥3.12 | `scribe` | 421 / 4 | 323 / 2 / **18** |
| `pyforge-doctor` | `pyforge.doctor` | ≥3.14 | `doctor` | 304 / 4 | 1,081 / 6 / **62** |
| **totals** | | | | **33,060 / 120** | **47,432 / 188 / 2,539** |

| Asset | Count |
|---|---|
| `src/` files | 3,042 on disk / **2,454 tracked** |
| Namespace `__init__.py` under `src/*/src/pyforge/` | **0** (PEP 420 implicit namespace — deliberate) |
| `src/sentinel/knowledge/` | 5 `.py` / 346 LOC, **non-packaged** (no `pyproject.toml`, no `__init__.py`); 8 of its 9 pixi-referenced crew modules are missing |
| `src/prototype/packages/pyforge-atlas-kedro-viz/` | 283 files but only 14 `.py` / 915 LOC — generated, no tests |
| `pyforge-warden/tests/fixtures/` | 16 MB / 2,031 files (1,988-file recipe corpus + 24 fixture projects + offline osv-db) |

**Repo-wide**

| Asset | Count |
|---|---|
| Recipes in `recipes/` | **1,664** dirs (**933** `recipe.yaml` + **1,024** `meta.yaml`; **300** carry both, deliberately) |
| Pixi envs | **15** (linux, osx, win, build, grayskull, conda-smithy, local-recipes, vuln-db, gcloud, bmad-ui + 5 `pyforge-*`) |
| Pixi features / tasks | **17** features · **152** tasks (106 in `local-recipes`, 10 atlas, 7 warden, 7 vuln-db, 4 each herald/scribe/doctor/grayskull, 2 bmad-ui, 1 each linux/osx/win/conda-smithy); no root-level tasks |
| `docs/` | **83** files, all tracked — dreams 27 (**26 Dreams** + README), specs **19**, reference **6**, intake 27, dashboard 4; **no top-level `.md`** |
| `presentations/` | **14** deck dirs + README.md — 692 tracked of 31,718 on disk |
| `scripts/` | **14** tracked entries |
| `.github/workflows/` | **8** active + `scripts/{linter,linter_issue_comment}.py` (was 12 + 1 disabled before the 2026-07-26 audit, PR #127) |
| `_skf-learn/` · `archive/` · `.scripts/` · `tests/` · `conf/` · `helm/` | 18 · 15 · 5 · 1 · 1 · 1 tracked files |
| `SDKs/` | 30,811 files, **0 tracked** |
| `.gitignore` | **738** lines |

**Refresh notes (2026-07-25 vs. prior 2026-06-20 / 2026-07-06 syncs):**
- **Structural: a fifth part.** `src/` (the `pyforge` family) did not exist in the prior revision's map at all. Also newly mapped: `presentations/`, `docs/dreams/`, `docs/dashboard/` (the Guildhall), `docs/intake/`, `.bmad-loop/`, `.claude/memory/`, `.claude/hooks/`, `conf/`, `helm/`, `archive/`, `_skf-learn/`, `.scripts/`, `AGENTS.md`, `GEMINI.md`.
- **Corrections (previously *wrong*, not just stale):** root `pyproject.toml`, root `package.json`, `output/` and `build.pid` were all documented but do **not** exist; `.gitignore` is 738 lines, not ">13k"; `SDKs/` was called a "committed binary" but is entirely untracked; `docs/` top-level `.md` files no longer exist (moved to `docs/reference/`, retired to `archive/docs/`); the Counts table's schema version, MCP-tool count, reference-doc count and pixi-env count were all below live.
- **Growth:** recipes 1,602 → 1,664 (`recipe.yaml` 718 → 933 as v0→v1 migration advances); CFE scripts 54 → 66; wrappers 46 → 60; skill tests 82 files → 100 files / 1,186 `def test_`; skills 65 dirs → 93; pixi envs 9 → 15, tasks ~80 → 152; BMAD projects 3 → 14; `docs/specs/` 12 → 19 (now **legacy** — Tier 2 `planning-artifacts/specs/` holds the 8 active Specs).
- **Re-verified UNCHANGED:** cf_atlas schema **v29**; **46 MCP tools**; **22 executable / 23 cataloged** atlas phases; gotchas **G1–G107**; `reference/` 15, `guides/` 9, `quickref/` 2; templates 41 across 13 ecosystems.
- **Sibling artifact in agreement:** `planning-artifacts/project-parts.json` was reconciled in the same 2026-07-25 pass — it now declares **5** parts (`conda-forge-expert`, `cf-atlas`, `mcp-server`, `bmad-infra`, **`pyforge-packages`**) at `source_pin` v8.79.1, matching this document's frontmatter and § *Part 5*. It entered this pass declaring 4 parts at v8.79.0.
- **Verified defect recorded, not fixed:** `src/sentinel/knowledge/` — 14 `wiki-*` pixi tasks reference 9 crew modules, 8 of which do not exist; `crews/` has no `__init__.py`; the one existing module has no `__main__` guard, so even `wiki-compile` is a no-op.
- Earlier per-sync refresh notes (2026-06-20 through 2026-07-06) recorded incremental skill-version spans with no source-tree structural change; they have been collapsed into this entry, since several of their counts were superseded or were wrong at the time.
