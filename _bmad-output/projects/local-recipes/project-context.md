---
project_name: 'local-recipes'
user_name: 'rxm7706'
date: '2026-05-12'
sections_completed: ['default_conventions', 'tech_stack', 'recipe_format', 'compiler_stdlib', 'python_policy', 'dependency_resolution', 'mcp_lifecycle', 'sha256', 'build_test', 'anti_patterns', 'canonical_patterns', 'air_gapped', 'submission_workflow', 'repository_conventions', 'planner_constraints']
existing_patterns_found: 1392
status: 'complete'
rule_count: 63
optimized_for_llm: true
sync_sources: ['CLAUDE.md', '.claude/skills/conda-forge-expert/SKILL.md', '.claude/skills/conda-forge-expert/reference/', '.claude/skills/conda-forge-expert/guides/', '.claude/skills/conda-forge-expert/quickref/', '.claude/skills/conda-forge-expert/CHANGELOG.md', 'docs/enterprise-deployment.md']
last_synced_skill_version: 'conda-forge-expert v7.8.1'
maintenance_model: 'hand-edited rulebook; per-section (Sync: ...) tags name the upstream source. Re-verify volatile sections (Recipe Format, MCP Lifecycle, Anti-Patterns) on each CHANGELOG MINOR bump'
---

# Project Context for AI Agents

_Foundational rules every BMAD agent reads on spawn. This file is a **rulebook**, not a primer — full mechanics live in the cited upstream sources. Mirrors `CLAUDE.md` (repo-wide guidance) and the `conda-forge-expert` skill (conda-forge specifics)._

---

## Default Conventions

(Sync: `CLAUDE.md` § Project Overview; `pixi.toml`)

- Maintainer for new recipes: `rxm7706` (in `extra.recipe-maintainers`).
- Recipe format emitted by `generate_recipe_from_pypi`: v1 `recipe.yaml`.
- Default channel: `conda-forge`.
- Target platforms: `linux-64`, `linux-aarch64`, `osx-64`, `osx-arm64`, `win-64`.
- Build engine: pixi + rattler-build (NOT conda-build, except for legacy v0 maintenance during migration).

## Technology Stack

(Sync: `pixi.toml`; `.claude/tools/conda_forge_server.py`)

Versions live in `pixi.toml` — read it, do not duplicate version numbers in prose. Non-obvious:
- 8 pixi envs (`linux`, `osx`, `win`, `build`, `grayskull`, `conda-smithy`, `local-recipes`, `vuln-db`); `local-recipes` is the default (set via `# default-env:` directive at the top of `[environments]`).
- FastMCP server at `.claude/tools/conda_forge_server.py` exposes the recipe lifecycle as MCP tools; Claude Code auto-starts it at session boot.

## Recipe Format Rules

(Sync: `.claude/skills/conda-forge-expert/reference/recipe-yaml-reference.md`; `meta-yaml-reference.md`)

- v1 `recipe.yaml` with `schema_version: 1` and the rattler-build schema header on line 1 (`# yaml-language-server: $schema=https://raw.githubusercontent.com/prefix-dev/recipe-format/main/schema.json`).
- **Schema-validation header is mandatory on v1.** `generate_recipe_from_pypi` + `generate_npm_recipe_yaml` emit it; `tests/meta/test_recipe_yaml_schema_header.py` enforces it. *Skip rule*: the meta-test silently skips any file lacking a `schema_version:` line — so when hand-authoring, add `schema_version: 1` and the header together.
- v0 `meta.yaml` is migration source only. When you touch a v0 recipe, migrate it in the same PR: `migrate_to_v1` → `validate_recipe` → delete `meta.yaml` → commit.
- v1 substitution: `${{ name }}` / `${{ version }}`.
- License: valid SPDX identifier. `license_file` MUST be a list, even with one entry.

## Compiler & stdlib Rule

(Sync: `.claude/skills/conda-forge-expert/SKILL.md` § Critical Constraints; `reference/recipe-yaml-reference.md` § Requirements)

**Missing `stdlib("c")` when any `compiler(...)` is present = automatic conda-forge CI rejection (lint code STD-001).** Any recipe using `${{ compiler("c") }}`, `${{ compiler("cxx") }}`, or `${{ compiler("rust") }}` MUST include `${{ stdlib("c") }}` in `requirements.build`.

## Python Version Policy

(Sync: `.claude/skills/conda-forge-expert/reference/python-min-policy.md`)

- Floor tracks `conda-forge-pinning-feedstock`. Floor at file-sync time: `"3.10"` (3.9 dropped 2025-08). **Read the upstream pinning file before submitting** — the floor value in this file is a snapshot, not a contract.
- `noarch: python` recipes use the CFEP-25 triad with the **list-form test matrix**: `host: python ${{ python_min }}.*` / `run: python >=${{ python_min }}` / test `python_version: [${{ python_min }}.*, "*"]`. Single-string form is flagged **TEST-002**.
- Compiled Python: `python >=<current-floor>`; no `python_min` variable.
- Never downgrade below the current floor in a new submission.

## Dependency Resolution

(Sync: `.claude/skills/conda-forge-expert/reference/mcp-tools.md` § `get_conda_name`, `check_dependencies`)

- Resolve PyPI → conda names via `get_conda_name` MCP tool or `name_resolver.py`. Don't guess.
- Verify all deps with `check_dependencies` before submission.
- **Loosen-then-tighten**: when a pinned version is unavailable on conda-forge, loosen to the available version and add `# TODO(pin-tighten): <pkg> >=<target> when available on conda-forge`. Trigger to tighten: the next autotick PR for `<pkg>` (the bot opens one when upstream lands on conda-forge) — verify in the PR diff that `<target>` is now resolvable, then remove the TODO.

## Autonomous MCP Lifecycle

(Sync: `.claude/skills/conda-forge-expert/SKILL.md` § Primary Workflow: The Autonomous Loop — authoritative source for the full 10-step sequence)

The skill's autonomous loop runs 10 ordered steps from `generate_recipe_from_pypi` through `submit_pr`. SKILL.md is authoritative for the pipeline; the invariants below override the pipeline narrative when they conflict.

- **Step 8b (`prepare_submission_branch`) is the only human-gated checkpoint.** It pushes to your `<user>/staged-recipes` fork and returns `fork_branch_url` but does NOT open the PR. `submit_pr` is ungated and will proceed unprompted, so the gate is the human inspecting the branch URL in a browser between 8b and `submit_pr`. **Inspection checklist:** (a) `recipe.yaml` renders correctly post-jinja; (b) branch name matches `<recipe-name>-<version>`; (c) no `.claude/data/` or local caches leaked into the diff; (d) commit message matches `Add recipe for <name>`.
- **Force pushes default to `--force-with-lease`** — errors on divergent remote instead of overwriting silently. Pass `force=False` (CLI: `--no-force`) for plain push.
- **Build-failure loop has no hard cap.** If `analyze_build_failure` → `edit_recipe` → `trigger_build` cycles 3 times without progress, escalate to the user. Repeated identical failures indicate the diagnosis is wrong; new evidence is required, not another iteration.
- **MCP server precondition**: Claude Code auto-starts the FastMCP server at session boot. If MCP calls fail with "server not running," restart Claude Code rather than working around it.
- **Cross-platform build precondition**: the linux-64-green submission gate assumes a Linux host or Docker. On hosts that can't build linux-64 locally, defer to conda-forge CI by submitting on the strength of `validate_recipe` clean plus the local platform's build — note the deferral explicitly in the PR description.

Use `edit_recipe` with structured actions for routine version/SHA/maintainer changes. Hand-edit YAML only for changes the structured action set doesn't cover.

## SHA256 Verification

(Sync: `.claude/skills/conda-forge-expert/reference/recipe-yaml-reference.md`; `mcp-tools.md` § `edit_recipe`)

- SHA256 source of truth: PyPI JSON API (`https://pypi.org/pypi/<pkg>/<ver>/json` → `urls[].digests.sha256`) or `sha256sum` of the downloaded source tarball. **Never paste upstream's claimed hash without re-fetching.**
- Write SHA256 with `edit_recipe`; never hand-edit.

## Build & Test Rules

(Sync: `.claude/skills/conda-forge-expert/quickref/commands-cheatsheet.md` § Project Pixi Tasks; `build-locally.py`)

- Native linux-64 = full build + test via `rattler-build`.
- Cross-platform (osx-*, win-64, linux-aarch64) skips tests with `--no-test`; win-64 also passes `--allow-symlinks-on-windows`.
- Linux builds run inside Docker (`build-locally.py`); osx/win run directly on host.
- For local cross-platform on a Linux host: build linux-64 + linux-aarch64 only; rely on conda-forge CI for osx/win unless explicitly requested.
- **Fork-bootstrap precondition for submission**: `<your-user>/staged-recipes` fork must exist on GitHub and `gh auth status` must show a token with `repo` scope before step 8b. `prepare_submission_branch` does NOT create the fork.

## Anti-Patterns

(Sync: `.claude/skills/conda-forge-expert/scripts/recipe_optimizer.py` for lint codes; `SKILL.md` § Recipe Authoring Gotchas for G-codes)

Run `optimize_recipe` and fix what it flags — 17 lint codes spanning **DEP, PIN, ABT, SCRIPT, SEL, STD, TEST, MAINT, SEC, OPT** prefixes. **STD-001** (missing stdlib) is the most common auto-rejection trigger; **TEST-002** (single-string noarch:python test matrix) is the most common reviewer comment.

Project-specific gotchas the linter doesn't catch:
- `build.bat` bare `pnpm --version` / `npm --version` silently terminates the parent script. Prefix with `call`: `call pnpm --version`.
- Skill tests in `.claude/skills/conda-forge-expert/tests/` use real fixtures + `network` / `slow` markers — do not mock the network. Offline subset: `pixi run -e local-recipes test`.
- `submit_pr` without `dry_run=True` first — always dry-run; see § Submission Workflow.
- `tree-sitter-<lang>` PyPI sdists strip `parser.h` inconsistently — see SKILL.md Recipe Authoring Gotcha **G5**. Inspection: download the sdist (`pip download --no-deps --no-binary :all: <pkg>==<ver>`) then `tar tzf <pkg>-<ver>.tar.gz | grep tree_sitter/parser.h`. No skill-managed sdist cache exists.
- `get_build_summary` false negatives — see SKILL.md Recipe Authoring Gotcha **G6** (v7.7.1). Verify via `conda_build.log`, not summary text; log path resolution under § Repository Conventions.

## Canonical Patterns

(Sync: `.claude/skills/conda-forge-expert/SKILL.md` § Canonical Patterns; `.claude/skills/conda-forge-expert/templates/`)

The skill encodes canonical patterns for npm-ecosystem recipes, GitHub-only sources, v0→v1 migration, and upstream-bug patch shims — read SKILL.md and the matching template. Invariants enforced here:
- npm recipes: `license_file` is a list; no `__unix` / `__win` selectors.
- GitHub-only sources (no PyPI): `update_recipe_from_github` for autotick — always `dry_run=True` first.
- v0 → v1 migration: migrate in the same PR that touches the recipe (see § Recipe Format Rules).
- Upstream-bug patches: `recipes/<name>/patches/0001-<short-description>.patch`, referenced as a `patches:` list under `source:`.

## Air-Gapped / Enterprise

(Sync: `docs/enterprise-deployment.md` § JFrog Artifactory Integration; `CLAUDE.md` § "Project Documentation Reference"; `_bmad-output/projects/local-recipes/planning-artifacts/deployment-guide.md` § 2b)

- All workflows MUST function offline given upstream proxies/mirrors. The atlas pipeline (`bootstrap-data`, `atlas-phase`) is fully offline-tolerant: Phase F has an S3 parquet backend (`PHASE_F_SOURCE=auto|anaconda-api|s3-parquet`); Phase H has a cf-graph offline backend (`PHASE_H_SOURCE=pypi-json|cf-graph`).
- **Per-host redirects** (v7.8.1: full parity). Every external host the atlas + skill talks to is redirectable via a `<HOST>_BASE_URL` env var. Public default applies when unset; trailing slashes are auto-stripped.
  - Python + conda: `CONDA_FORGE_BASE_URL`, `PYPI_BASE_URL`, `PYPI_JSON_BASE_URL`, `S3_PARQUET_BASE_URL`, `ANACONDA_API_BASE_URL` (legacy alias `ANACONDA_API_BASE`).
  - Git forges: `GITHUB_BASE_URL`, `GITHUB_RAW_BASE_URL`, `GITHUB_API_BASE_URL` (covers REST + GraphQL; GHES set to `https://<ghes>/api`), `GITLAB_API_BASE_URL`, `CODEBERG_API_BASE_URL`.
  - Phase L registries: `NPM_BASE_URL` (also honors npm CLI's `npm_config_registry`), `CRAN_BASE_URL`, `CPAN_BASE_URL`, `LUAROCKS_BASE_URL`, `CRATES_BASE_URL`, `RUBYGEMS_BASE_URL`, `MAVEN_BASE_URL`, `NUGET_BASE_URL`.
  - Vulnerability scanning: `OSV_API_BASE_URL`, `OSV_VULNS_BUCKET_URL`.
- **Phase tunables** (operational, post-v7.8.x defaults): `PHASE_F_CONCURRENCY=3` (was 8), `PHASE_H_CONCURRENCY=3` (was 8) — both rate-limit safety; Phase L per-registry caps via `PHASE_L_CONCURRENCY_<SOURCE>` (defaults: crates=rubygems=1, cran=cpan=luarocks=maven=2, npm=nuget=4); `ATLAS_CFGRAPH_TTL_DAYS` (default 1.0; weekly-cron users should set to 7); `PHASE_K_GRAPHQL_DISABLED` + `PHASE_K_GRAPHQL_BATCH_SIZE` (recovery / tuning).
- Channel resolution via `.pixi/config.toml`; auth via env vars per `docs/enterprise-deployment.md`.
- **Cross-host credential leak** (UNRESOLVED). `_http.py`'s `make_request` injects the `X-JFrog-Art-Api` header on EVERY outbound request when `JFROG_API_KEY` is set, regardless of destination host. v7.8.x extracted `auth_headers_for(url)` but kept the same semantics — the leak is preserved across both urllib + `requests` paths. **Always unset `JFROG_API_KEY` before commands that hit non-JFrog hosts.** Commands known to hit external hosts: `submit_pr`, `prepare_submission_branch`, `update_cve_database`, `update_mapping_cache`, `generate_recipe_from_pypi`, `update_recipe_from_github`, any `atlas-phase` invocation in `auto` mode. Mitigation pattern: scope to a subshell — `( unset JFROG_API_KEY; <command> )` — or only export `JFROG_API_KEY` in shells exclusively touching JFrog-mirrored URLs. (Mirrored in `docs/enterprise-deployment.md` § Cross-host credential leak.)
- Local CVE database (`update_cve_database`) and PyPI mapping cache (`update_mapping_cache`) MUST be refreshable from internal sources. v7.8.1 added `OSV_VULNS_BUCKET_URL` so the ~4 GB OSV `all.zip` can be served from an internal mirror; download streams + resumes (Range request) so a dropped connection at 95% no longer restarts from byte 0.
- **Engineering rule book**: `.claude/skills/conda-forge-expert/reference/atlas-phase-engineering.md` (added v7.8.0) documents the 9 patterns governing phase authoring (per-host rate limits, GraphQL batching, Retry-After + jitter, per-registry concurrency, atomic writes, incremental commits + idempotent SQL, streaming tarfiles, page-level checkpoints, `<HOST>_BASE_URL` routing). Consult before any phase work.

## Submission Workflow

(Sync: `.claude/skills/conda-forge-expert/reference/mcp-tools.md` § `submit_pr`, `prepare_submission_branch`)

- Target: `conda-forge/staged-recipes` fork → upstream PR.
- **Submission-ready gate** (all four required): `validate_recipe` clean + `optimize_recipe` clean + `scan_for_vulnerabilities` clean + linux-64 build green.
- **Two-step submission flow**: `prepare_submission_branch` (or `pixi run -e local-recipes prepare-pr <recipe>`) pushes to fork without opening the PR. Inspect `fork_branch_url` per the checklist in § Autonomous MCP Lifecycle. Then `submit_pr(recipe_name, dry_run=True)` (verifies `gh auth`, fork, branch state) followed by `submit_pr()` to open the PR.
- Optional per-recipe `conda-forge.yml` override (newer glibc, additional CI matrix, retained Azure artifacts): see `.claude/skills/conda-forge-expert/reference/conda-forge-yml-reference.md` + templates under `.claude/skills/conda-forge-expert/templates/conda-forge-yml/{staged-recipes,feedstock}/`. **Don't commit an all-empty file** — it just adds noise to the PR diff.
- After merge → `<package>-feedstock` repo. Post-publish fixes → `conda-forge-repodata-patches-feedstock`, not feedstock rebuilds.

## Repository Conventions

(Sync: `CLAUDE.md` § "Project Documentation Reference"; `.claude/skills/conda-forge-expert/INDEX.md`)

- Recipes: `recipes/<package-name>/recipe.yaml` (canonical, v1). Upstream-bug patches: `recipes/<name>/patches/0001-*.patch`. `meta.yaml` is transient migration state only.
- **Three-place rule for new CI scripts**: (1) canonical implementation `.claude/skills/conda-forge-expert/scripts/<name>.py`; (2) thin CLI wrapper `.claude/scripts/conda-forge-expert/<name>.py`; (3) pixi task `[feature.local-recipes.tasks.<name>]` in `pixi.toml` + entry in the `SCRIPTS` list in `.claude/skills/conda-forge-expert/tests/meta/test_all_scripts_runnable.py`. Missing any one breaks the meta-test.
- Skill data (mutable, gitignored): `.claude/data/conda-forge-expert/` — `cf_atlas.db` (+ `-shm`/`-wal`), `cf_atlas_meta.json`, `cf-graph-countyfair.tar.gz` (cf-graph snapshot for Phase E/H/M), `vdb/`, `vdb-cache/`, `cve/`, `pypi_conda_map.json`. Directories created on demand: `cache/parquet/` (Phase F S3 backend), `inventory_cache/` (scan_project).
- Skill reference / guides (read-only): `.claude/skills/conda-forge-expert/{reference/,guides/,quickref/}`. `INDEX.md` is the task→tool navigator; `guides/atlas-operations.md` covers cron schedules / hard reset / air-gapped use.
- Build artifacts: outputs at `build_artifacts/<config>/<subdir>/<name>-<version>-*.conda`; diagnostic logs at `build_artifacts/<config>/bld/rattler-build_<name>_<id>/work/conda_build.log`. Resolve the latest log: `ls -t build_artifacts/*/bld/rattler-build_<name>_*/work/conda_build.log | head -1`.
- Pass extra args to pixi tasks after `--`: `pixi run -e local-recipes validate -- recipes/numpy`. Single-phase atlas refresh: `pixi run -e local-recipes atlas-phase <ID>` (B/B.5/C/D/E/F/G/H/J/K/L/M/N) — avoids the 30-45 min full rebuild.
- Project docs: `docs/`. BMAD multi-project artifacts: `_bmad-output/projects/<slug>/{planning-artifacts,implementation-artifacts}/`.

## Planner Constraints

(Sync: `.claude/skills/conda-forge-expert/SKILL.md` § Critical Constraints; `reference/recipe-yaml-reference.md`)

Rules that reshape **story scope** for `bmad-create-prd`, `bmad-create-epics-and-stories`, and `bmad-create-story` when planning conda-forge work:

- **`noarch: python` recipes have no per-platform test matrix** — a story that splits test coverage by OS for a noarch package is invalid. Either commit to per-platform builds (drop `noarch:`) or write a single test matrix.
- **The submission-ready gate is non-negotiable.** A story that targets "submit PR" cannot complete until `validate_recipe` + `optimize_recipe` + `scan_for_vulnerabilities` + linux-64 build are all green. Plan the four checks as explicit acceptance criteria, not implicit "tests pass."
- **Step 8b is a story boundary.** `prepare_submission_branch` is the natural "done for now" point for a recipe-authoring story; `submit_pr` belongs to a separate, human-authorized "publish recipe" story. Don't bundle them.
- **`python_min` floor moves.** When planning a story that pins a Python floor, reference the **current** `conda-forge-pinning-feedstock` value at implementation time, not the snapshot in this file.
- **Cross-platform stories require a named build host.** A story authoring a recipe that ships on `win-64` must name the build host (Windows host, Windows VM, or "rely on conda-forge CI") in the acceptance criteria — the local Linux host cannot validate win-64 binaries.

---

## Usage

- **BMAD agents**: read on spawn; cite specific sections rather than restating rules.
- **Humans**: keep this file in sync with the source files identified in each section's `(Sync: ...)` tag. The `CHANGELOG.md` TL;DR section is the canonical drift-detection source — re-verify the **volatile sections** (Recipe Format Rules, Autonomous MCP Lifecycle, Anti-Patterns) whenever the latest CHANGELOG **MINOR** version exceeds the `last_synced_skill_version` pinned in frontmatter. PATCH bumps do not require re-sync.

<!-- Sync sources: CLAUDE.md (repo-wide) + .claude/skills/conda-forge-expert/ (conda-forge specifics) + docs/enterprise-deployment.md (JFROG mirror). Hand-maintained — verify alignment when sources change. -->
