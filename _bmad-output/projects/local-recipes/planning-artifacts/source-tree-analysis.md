---
doc_type: source-tree-analysis
project_name: local-recipes
date: 2026-05-12
repository_type: monorepo
parts: 4
source_pin: 'conda-forge-expert v7.7'
---

# Source Tree Analysis

This document is the **path map**: every architecturally-significant directory and entry-point file. Architecture docs (parts 1-4) reference paths in this tree; this tree exists once.

Gitignored runtime data is included where relevant (most under `.claude/data/`); it is created by build/runtime processes, not committed.

---

## Top-level layout (annotated)

```
local-recipes/                               # pixi monorepo root, default-env=local-recipes
│
├── pixi.toml                                # 8 envs + ~30 tasks + 9 features (python/build/linux/osx/win/grayskull/conda-smithy/shellcheck/local-recipes/vuln-db)
├── pixi.lock                                # locked deps (gitignored mostly; lockfile is committed)
├── pyproject.toml                           # Python package metadata
├── package.json                             # Node.js metadata (for npm-ecosystem recipes' tooling)
├── conda-forge.yml                          # staged-recipes-style root config
├── conda_build_config.yaml                  # global build matrix overrides
├── environment.yaml                         # legacy conda-env file (predates pixi)
│
├── CLAUDE.md                                # ★ entry point for AI agents (repo-wide guidance)
├── CHANGELOG.md                             # repo-level changelog (separate from skill CHANGELOG)
├── LICENSE / LICENSE.txt                    # BSD-3-Clause
├── README.md                                # human-facing intro
│
├── azure-pipelines.yml                      # primary CI: Azure DevOps
├── .azure-pipelines/                        # CI templates
├── .ci_support/                             # CI helper scripts
├── .github/                                 # GitHub workflows + issue templates
├── .appveyor.yml.notused                    # legacy AppVeyor (disabled)
├── build-locally.py                         # ★ Docker-based local-build harness (Linux builds run here)
├── build.pid                                # pidfile from an active build (gitignored)
│
├── .env, .env.github                        # local env files (gitignored)
├── .gitignore                               # >13k lines — extensive, covers pixi/rattler/output dirs
├── .gitattributes                           # git LFS attrs etc.
├── .cursorrules                             # Cursor IDE rules (analog to CLAUDE.md)
├── .junie/                                  # JetBrains AI rules (analog to CLAUDE.md)
├── .idea/                                   # JetBrains IDE config (gitignored)
│
├── .claude/                                 # ★★ Parts 1 + 3 live here (skill + MCP server) + 65 skills + data state
├── _bmad/                                   # ★★ Part 4: BMAD installer (config layers + workflow phases)
├── _bmad-output/                            # ★★ Part 4: BMAD per-project artifacts
│
├── recipes/                                 # 1,415 recipe directories (OUTPUTS of the system, not part of it)
├── wagtail/                                 # one-off recipe at top-level (single recipe.yaml; not under recipes/)
│
├── docs/                                    # human-facing docs (architecture, deployment, dev guide, specs)
├── scripts/                                 # repo-level helper scripts (bmad-switch, load-env, sync, mirror)
├── tests/                                   # repo-level shell tests (currently just test_load_env.sh)
│
├── SDKs/                                    # macOS SDK files (MacOSX11.0.sdk + tarball) — for cross-compile from Linux
├── build_artifacts/                         # rattler-build OUTPUT dir (gitignored) — .conda files + bld/ logs
├── output/                                  # rattler-build working dir (gitignored) — bld/, src_cache/, per-platform
│
└── .pixi/                                   # pixi env caches (gitignored)
```

**Reading guide:**
- `★` marks entry points an AI agent reads on first activation
- `★★` marks the four-part architecture roots
- Lines without annotations exist but are routine config/CI plumbing

---

## Part 1 + Part 3: `.claude/` subtree

```
.claude/
│
├── tools/                                   # ★★ Part 3: FastMCP server lives here
│   ├── conda_forge_server.py                # 35 MCP tools (recipe-authoring + atlas-intelligence + project-scanning)
│   ├── gemini_server.py                     # auxiliary MCP server (Gemini integration)
│   ├── mcp_call.py                          # MCP helper utilities (used by scripts that bridge to MCP runtime)
│   └── __pycache__/                         # (runtime artifact)
│
├── docs/                                    # internal Claude-Code-specific notes (rare, not the same as repo /docs)
│
├── skills/                                  # 65 skills total (mix of BMAD-installer + repo-specific + auxiliary)
│   │
│   ├── conda-forge-expert/                  # ★★ Part 1 canonical source
│   │   ├── SKILL.md                         # ★ primary spine: critical constraints, 10-step loop, gotchas G1-G6
│   │   ├── INDEX.md                         # task→tool navigator
│   │   ├── CHANGELOG.md                     # ★ release history with TL;DR (canonical drift-detection source)
│   │   ├── MANIFEST.yaml                    # declares "standalone-portable" deployment (host-repo install.py target)
│   │   ├── install.py                       # bootstraps the skill into another host repo (writes wrappers, copies MCP)
│   │   │
│   │   ├── reference/                       # 11 deep-reference files
│   │   │   ├── recipe-yaml-reference.md          # v1 recipe.yaml schema deep-ref
│   │   │   ├── meta-yaml-reference.md            # v0 meta.yaml legacy ref
│   │   │   ├── mcp-tools.md                      # MCP tool inventory + signatures
│   │   │   ├── python-min-policy.md              # CFEP-25 + python_min triad rules
│   │   │   ├── conda-forge-yml-reference.md      # conda-forge.yml subset
│   │   │   ├── pinning-reference.md              # global pin rules
│   │   │   ├── selectors-reference.md            # rattler-build selector syntax
│   │   │   ├── jinja-functions.md                # ${{ compiler() / stdlib() / pin_subpackage() / cdt() }}
│   │   │   ├── dependency-input-formats.md       # scan_project input matrix (~28 formats)
│   │   │   ├── actionable-intelligence-catalog.md  # persona-mapped atlas signal index
│   │   │   └── conda-forge-ecosystem.md          # ecosystem overview (bot, smithy, repodata-patches)
│   │   │
│   │   ├── guides/                          # 8 workflow guides
│   │   │   ├── getting-started.md
│   │   │   ├── migration.md                      # v0 → v1 migration
│   │   │   ├── ci-troubleshooting.md
│   │   │   ├── cross-compilation.md
│   │   │   ├── feedstock-maintenance.md
│   │   │   ├── testing-recipes.md
│   │   │   ├── sdist-missing-license.md          # specific recipe failure mode
│   │   │   └── atlas-operations.md               # cron schedules, hard reset, air-gap
│   │   │
│   │   ├── quickref/                        # 2 quick-reference files
│   │   │   ├── commands-cheatsheet.md            # pixi tasks + raw CLIs
│   │   │   └── bot-commands.md                   # @conda-forge-admin slash commands
│   │   │
│   │   ├── scripts/                         # ★★ Tier 1: canonical Python implementations (42 modules)
│   │   │   │
│   │   │   ├── # ── Recipe lifecycle (Part 1 core) ──
│   │   │   ├── recipe-generator.py               # generate_recipe_from_pypi entrypoint (grayskull + post-processing)
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
│   │   │   │
│   │   │   ├── # ── cf_atlas pipeline (Part 2 core) ──
│   │   │   ├── conda_forge_atlas.py              # ★ orchestrator: 15 phases B→N, PHASES registry, run_single_phase
│   │   │   ├── _cf_graph_versions.py             # Phase H cf-graph offline backend (v7.7.0)
│   │   │   ├── _parquet_cache.py                 # Phase F S3 parquet cache layer (v7.6.0)
│   │   │   ├── atlas_phase.py                    # single-phase CLI entrypoint
│   │   │   ├── bootstrap_data.py                 # full-pipeline orchestrator: mapping + CVE + vdb + cf_atlas + Phase N
│   │   │   ├── detail_cf_atlas.py                # query helpers: detail-cf-atlas CLI
│   │   │   ├── inventory_channel.py              # channel inventory cache
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
│   │   │   ├── cve_watcher.py                    # cve-watcher
│   │   │   ├── cve_manager.py                    # CVE DB CRUD (update_cve_database)
│   │   │   ├── vulnerability_scanner.py          # scan_for_vulnerabilities
│   │   │   ├── health_check.py                   # run_system_health_check
│   │   │   ├── scan_project.py                   # scan_project (~28 input formats)
│   │   │   ├── _sbom.py                          # SBOM parsing helpers (CycloneDX / SPDX / Syft)
│   │   │   │
│   │   │   ├── # ── Shared infrastructure ──
│   │   │   ├── _http.py                          # ★ truststore + JFrog/GitHub/.netrc auth chain (every outbound request)
│   │   │   ├── mapping_manager.py                # update_mapping_cache (PyPI→conda map refresh)
│   │   │   └── test-skill.py                     # skill-internal smoke test runner
│   │   │
│   │   ├── templates/                       # 30 recipe templates across 11 ecosystems
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
│   │   │   └── conda-forge-yml/{staged-recipes,feedstock}/conda-forge.yml  # conda-forge.yml starters (v7.3.0)
│   │   │
│   │   ├── tests/                           # 41 test files (unit + integration + meta)
│   │   │   ├── unit/                             # function-level
│   │   │   ├── integration/                      # cross-module + network-marked
│   │   │   ├── meta/                             # ★ enforces invariants: test_recipe_yaml_schema_header, test_all_scripts_runnable
│   │   │   └── fixtures/
│   │   │       ├── recipes/                      # real recipe.yaml snippets
│   │   │       ├── manifest_samples/             # scan_project inputs (~28 formats)
│   │   │       ├── error_logs/                   # build-failure samples for failure_analyzer
│   │   │       └── mocked_responses/             # selective mocks (rare; suite mostly uses real fixtures)
│   │   │
│   │   ├── config/                          # skill config templates
│   │   │   ├── skill-config.yaml
│   │   │   └── enterprise-config.yaml.template   # JFrog/air-gap config starter
│   │   │
│   │   ├── examples/                        # 5 example recipes (c-library, multi-output, python-compiled, python-simple, rust-cli)
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
│   ├── # ── BMAD installer skills (64 of the 65 total) ──
│   ├── bmad-agent-{analyst,architect,dev,pm,tech-writer,ux-designer}/    # 6 persona agents
│   ├── bmad-create-{prd,architecture,epics-and-stories,story,ux-design}/  # 5 planning skills
│   ├── bmad-{advanced-elicitation,brainstorming,party-mode,...}/         # ~25 process skills
│   ├── bmad-{retrospective,code-review,review-adversarial-general,...}/  # review/retro skills
│   ├── bmad-{quick-dev,dev-story,document-project,...}/                  # implementation skills
│   ├── bmad-{sprint-planning,sprint-status,correct-course}/              # sprint skills
│   │
│   └── # ── Engineering practice skills (~15) ──
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
│   └── conda-forge-expert/                  # 34 thin subprocess wrappers (delegate to skill scripts/)
│       ├── (most names mirror skill scripts/, plus prepare_pr.py which delegates to submit_pr.py --prepare-only)
│
└── data/                                    # ★★ Part 1 Tier 3 + Part 2 artifacts (gitignored)
    └── conda-forge-expert/
        ├── cf_atlas.db                           # ★ Part 2 primary artifact (SQLite, 19 schema versions)
        ├── cf_atlas.db-shm                       # SQLite shared memory (WAL mode)
        ├── cf_atlas.db-wal                       # SQLite write-ahead log
        ├── cf_atlas_meta.json                    # atlas run metadata
        ├── cf-graph-countyfair.tar.gz            # cf-graph offline snapshot (Phase E/H/M)
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

See `architecture-cf-atlas.md` (next batch) for the full pipeline + schema. The data subtree above shows the artifacts at rest.

**Key entry points:**
- **Orchestrator:** `.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py` — `PHASES` registry + `run_single_phase()` + `bootstrap_data()` chain
- **Schema migrations:** in the same file, function `init_schema()` (idempotent; runs on every open)
- **TTL-gated columns:** `*_fetched_at` per phase; gated by `progress_every = min(max(N, len // 40), 2500)` with 60s heartbeat
- **Checkpoint table:** `phase_state` (added v7.7.0)

---

## Part 4: BMAD subtree

```
_bmad/                                       # ★★ BMAD installer (regenerated by BMAD-METHOD)
│
├── config.toml                              # layer 1: installer team, regenerated
├── config.user.toml                         # layer 2: installer user, regenerated
├── _config/                                 # internal installer state
│
├── core/                                    # BMAD core mechanics (workflows, runtime helpers)
│
├── bmm/                                     # BMAD module: planning + dev workflows
│   ├── config.yaml                          # module config (user_name, project_knowledge, planning_artifacts)
│   ├── 1-analysis/                          # phase 1: discovery
│   │   └── research/
│   ├── 2-plan-workflows/                    # phase 2: PRD + architecture
│   ├── 3-solutioning/                       # phase 3: epic + story breakdown
│   └── 4-implementation/                    # phase 4: dev + retro
│
├── custom/                                  # global overrides (NOT regenerated)
│   ├── config.toml                          # layer 3: global custom team
│   ├── config.user.toml                     # layer 4: global custom user (if present)
│   ├── .active-project                      # active-project marker file (managed by scripts/bmad-switch)
│   └── (per-skill .toml overrides — e.g. bmad-create-prd.toml)
│
└── scripts/                                 # config resolution helpers
    ├── resolve_config.py                    # six-layer config merge (key-based query)
    └── resolve_customization.py             # per-skill workflow-block resolver

_bmad-output/                                # ★★ BMAD per-project artifacts
│
├── PROJECTS.md                              # multi-project index ("what's hosted here")
│
└── projects/
    ├── deckcraft/                           # sibling project (gitignored content)
    │   ├── planning-artifacts/
    │   └── implementation-artifacts/
    │
    ├── local-recipes/                       # ★ this project
    │   ├── project-context.md               # ★ foundational rules every BMAD agent reads
    │   ├── planning-artifacts/              # ← THIS DOCUMENT SET LANDS HERE
    │   └── implementation-artifacts/
    │       ├── deferred-work.md             # cross-spec deferred items (cursor-sdk, atlas-phase-f, etc.)
    │       ├── spec-cursor-sdk-local-recipe.md
    │       ├── spec-atlas-phase-f-s3-air-gap.md
    │       └── review-diff.patch
    │
    └── presenton-pixi-image/                # sibling project (gitignored content)
        ├── planning-artifacts/
        └── implementation-artifacts/
```

**Active-project resolution priority:**
1. `--project <slug>` CLI flag (per-call)
2. `BMAD_ACTIVE_PROJECT` env var
3. `_bmad/custom/.active-project` marker file (managed by `scripts/bmad-switch`)
4. Fallback: only layers 1-4 resolve (no project-scoped config)

---

## Repository support: `docs/` + `scripts/`

```
docs/                                        # human-facing documentation
├── mcp-server-architecture.md               # FastMCP server + name-mapping subsystem
├── enterprise-deployment.md                 # air-gap + JFrog (incl. v7.6.0+ cross-host leak)
├── developer-guide.md                       # local testing + recipe development
├── copilot-to-api.md                        # 5 ways to drive Copilot subscription as local model
├── bmad-setup-plan.md                       # BMAD installation rationale
├── pixi-config-jfrog.example.toml           # example .pixi/config.toml for JFrog air-gap
│
└── specs/                                   # BMAD-consumable feature specs
    ├── atlas-phase-f-s3-backend.md          # 14 stories, 4 waves (wave 0+1 shipped in v7.6.0)
    ├── conda-forge-tracker.md               # 13 stories, channel-aware migration
    ├── copilot-bridge-vscode-extension.md   # sideload-only VS Code extension
    ├── db-gpt-conda-forge.md                # 13-story DB-GPT packaging plan (lyric-* + cocoindex-class)
    └── claude-team-memory.md                # team-memory subsystem (status: see file)

scripts/                                     # repo-level helper scripts
├── bmad-switch                              # ★ active-project switcher (--current / --list / <slug>)
├── load-env.sh                              # parses pixi.toml default-env: directive
├── offline-build.sh                         # air-gap-aware build invocation
├── submit_pr.sh                             # shell wrapper around pixi submit-pr
├── sync-upstream-conda-forge.sh             # sync from conda-forge/staged-recipes upstream
├── sync_pypi_mappings.py                    # refresh pypi-conda mapping data
└── mirror-channels.py                       # internal mirror seeding (JFrog channel population)
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

output/                                      # rattler-build WORKING dir
├── bld/                                     # build scratch
├── broken/                                  # quarantined artifacts
├── linux-64/, linux-aarch64/, osx-64/, osx-arm64/, noarch/, win-64/  # per-platform staging
├── src_cache/                               # source tarball cache
├── test/                                    # test scratch
└── rattler-build-log.txt                    # most-recent run log

SDKs/                                        # cross-compile SDKs
├── MacOSX11.0.sdk.tar.xz                    # macOS 11.0 SDK tarball (committed binary)
└── MacOSX11.0.sdk/                          # extracted SDK (used for cross-compile from Linux to osx-64)
```

---

## Recipe corpus (out of scope for rebuild)

```
recipes/                                     # 1,415 recipe directories
└── <package-name>/
    ├── recipe.yaml                          # v1 format (canonical); schema_version: 1
    ├── meta.yaml                            # v0 format (legacy, migration source only)
    ├── patches/                             # optional upstream-bug shims
    │   └── 0001-<short-description>.patch
    ├── LICENSE*                             # vendored license files (when license_file points here)
    ├── build.sh / bld.bat                   # legacy v0 build scripts (rare in v1 recipes)
    └── (other support files: extra_metadata.yaml, conda-forge.yml override, etc.)

wagtail/                                     # one-off recipe at top-level (NOT under recipes/)
└── recipe.yaml                              # appears to be a personal workspace recipe
```

The recipe corpus is the **output** of the system, not part of it. The rebuild target reconstructs the factory; recipes are re-authored using the rebuilt factory.

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
| Air-gap / JFrog setup | `docs/enterprise-deployment.md` | `.claude/skills/conda-forge-expert/scripts/_http.py` |
| CI failure debugging | `.claude/skills/conda-forge-expert/guides/ci-troubleshooting.md` | `build_artifacts/<config>/bld/rattler-build_<name>_<id>/work/conda_build.log` |

---

## Critical files summary

These files are load-bearing — changing them affects the whole system, not just one part:

| File | Owner part | Why it's critical |
|---|---|---|
| `CLAUDE.md` | all | Repo-wide AI agent guidance + BMAD↔CFE integration rules |
| `pixi.toml` | all | Defines 8 envs and ~30 tasks; the contract between human shell and tool surface |
| `.claude/skills/conda-forge-expert/SKILL.md` | Part 1 | Skill's primary spine — read by Claude Code on every conda-forge task |
| `.claude/skills/conda-forge-expert/CHANGELOG.md` | Part 1 | Canonical drift-detection source — every MINOR bump triggers a project-context re-sync |
| `.claude/skills/conda-forge-expert/scripts/_http.py` | all (Parts 1+2+3) | Every outbound HTTP request routes through here. Contains the JFROG_API_KEY cross-host leak (mitigated via env-var hygiene; see deployment-guide.md) |
| `.claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py` | Part 2 | 15-phase pipeline orchestrator + schema migrations |
| `.claude/tools/conda_forge_server.py` | Part 3 | 35 MCP tools — auto-started at Claude Code session boot |
| `_bmad-output/projects/local-recipes/project-context.md` | Part 4 | Foundational rules every BMAD agent reads on spawn (v7.7-pinned) |
| `_bmad/custom/.active-project` | Part 4 | Determines which project's `.bmad-config.toml` overlays apply |

---

## Counts (verified 2026-05-12)

| Asset | Count |
|---|---|
| Recipes in `recipes/` | 1,415 (NOT ~440 as estimated in project-overview Batch 1) |
| One-off recipe at top-level | 1 (`wagtail/`) |
| CFE canonical scripts | 42 (Tier 1) |
| CFE CLI wrappers | 34 (Tier 2; some scripts are internal-only and don't have wrappers) |
| MCP tools (verified by grep `@mcp.tool`) | 35 |
| Recipe templates | 30 across 11 ecosystems + 2 conda-forge.yml starters |
| Skill tests | 41 (unit + integration + meta) |
| Installed skills total | 65 (BMAD installer + repo-specific + engineering-practice) |
| Skill reference docs | 11 |
| Skill guides | 8 |
| Skill quickrefs | 2 |
| Pixi envs | 8 |
| Pixi features | 9 (`python`, `build`, `linux`, `osx`, `win`, `grayskull`, `conda-smithy`, `shellcheck`, `local-recipes`, `vuln-db`) |
| Docs (top-level) | 5 + 1 example .toml + 1 BMAD setup plan |
| Spec files | 5 in `docs/specs/` |
| BMAD multi-projects | 3 (deckcraft, local-recipes, presenton-pixi-image) |
| Atlas pipeline phases | 17 phase IDs (B, B.5, B.6, C, C.5, D, E, E.5, F, G, G', H, J, K, L, M, N) |
| Atlas schema versions | 19 (additive migrations only) |

**Drift fixes applied to this doc set vs. project-overview.md (Batch 1):**
- Recipe count: 1,415 actual vs. 440 estimated → I will correct project-overview.md after the doc set lands.
- CFE script count: 42 actual vs. ~30 estimated → noted in this doc; will correct in architecture-conda-forge-expert.md.
- MCP tool count: 35 actual vs. "30+" estimated → noted; will use 35 in architecture-mcp-server.md.
- 5 specs in `docs/specs/` (not 4 as listed in project-overview) → claude-team-memory.md was missed.
