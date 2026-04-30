# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Behavioral Guidelines (Andrej Karpathy Skills)

These guidelines bias toward caution over speed. For trivial tasks, use judgment.

### 1. Think Before Coding
**Don't assume. Don't hide confusion. Surface tradeoffs.**
Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First
**Minimum code that solves the problem. Nothing speculative.**
- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.
Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes
**Touch only what you must. Clean up only your own mess.**
When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.
The test: Every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution
**Define success criteria. Loop until verified.**
Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

## Project Overview

This repository is an **AI-assisted, semi-autonomous packaging factory** for conda-forge recipes. It mirrors the workflow of `conda-forge/staged-recipes` but is supercharged with a suite of custom tools that enable Claude to handle nearly the entire recipe lifecycle, from generation and security scanning to building, debugging, and maintenance.

**Critical Rule**: Do not mix `meta.yaml` and `recipe.yaml` formats in the same build run. The tooling will reject mixed-mode runs.

## AI-Assisted Workflow & Custom Tooling

This repository's core strength is its suite of custom tools, which are natively exposed to Claude via a FastMCP server (`.claude/tools/conda_forge_server.py`). This enables a powerful, autonomous workflow.

### Autonomous Recipe Lifecycle Loop

When creating or updating a recipe, follow this closed-loop sequence:

1. **Generate** — `generate_recipe_from_pypi` to create initial recipe files.
2. **Validate** — `validate_recipe` to check schema, license, checksums (also runs `rattler-build lint`).
3. **Edit & Refine** — `edit_recipe` for structured changes (maintainers, SHA256, version).
4. **Security Scan** — `scan_for_vulnerabilities` against OSV.dev; resolve any findings.
5. **Optimize** — `optimize_recipe` for conda-forge best practices.
6. **Build** — `trigger_build` to start the local build asynchronously.
7. **Monitor** — poll `get_build_summary` until complete.
8. **Debug (if failed)** — `analyze_build_failure` on the error log → `edit_recipe` fix → return to step 6.
9. **Submit PR** — call `submit_pr(recipe_name, dry_run=True)` first to verify prerequisites (gh auth, fork), then `submit_pr(recipe_name)` to push and open the PR.

### Core Capabilities

| Tool | Description | Example Usage |
|---|---|---|
| `generate_recipe_from_pypi` | Creates a new recipe from a PyPI package. | `generate_recipe_from_pypi(package_name="numpy")` |
| `edit_recipe` | Programmatically modifies a recipe file using structured actions. **This is the preferred method for all edits.** | `edit_recipe('recipes/numpy/recipe.yaml', [{"action": "update", "path": "context.version", "value": "2.0.0"}])` |
| `check_dependencies` | Verifies that all dependencies exist on conda-forge or a custom channel. Uses batch repodata.json fetching (fast, air-gapped-friendly). Supports JFrog Artifactory via `channel` param + auth env vars (`JFROG_API_KEY`, etc.). | `check_dependencies(recipe_path="recipes/numpy")` |
| `validate_recipe` | Lints a recipe for correctness against conda-forge standards; also runs `rattler-build lint` as an extra pass when available. | `validate_recipe(recipe_path="recipes/numpy")` |
| `optimize_recipe` | Lints a recipe for quality, maintainability, and best practices. Check codes: DEP-001 (dev dep in run), DEP-002 (noarch Python upper bound), PIN-001 (exact pin), ABT-001 (missing license_file), SCRIPT-001/002 (build.sh anti-patterns), SEL-001/002 (redundant selectors, CFEP-25 python_min). | `optimize_recipe(recipe_path="recipes/numpy")` |

### Build, Test, and Debug Workflow

This system features a "closed-loop" build process, allowing Claude to trigger, monitor, and debug builds autonomously.

| Tool | Description | Example Usage |
|---|---|---|
| `trigger_build` | Starts a local build asynchronously. | `trigger_build(config="linux-64")` |
| `get_build_summary` | Polls for the result of the build, returning a JSON report. | `get_build_summary()` |
| `analyze_build_failure` | Takes the error log from a failed build and suggests a structured fix. | `analyze_build_failure(error_log=summary['error_log'])` |

### Security and Maintenance Workflow

These tools enable proactive maintenance and security management.

| Tool | Description | Example Usage |
|---|---|---|
| `update_recipe` | **"Autotick" Bot (PyPI).** Checks for new upstream versions on PyPI and automatically updates the recipe. | `update_recipe(recipe_path="recipes/numpy/recipe.yaml")` |
| `update_recipe_from_github` | **"Autotick" Bot (GitHub).** Fetches the latest GitHub release and updates the recipe. Use for packages not on PyPI. Always `dry_run=True` first. | `update_recipe_from_github(recipe_path="recipes/apple-fm-sdk", dry_run=True)` |
| `check_github_version` | Read-only GitHub version check — returns the latest tag without modifying the recipe. | `check_github_version(recipe_path="recipes/apple-fm-sdk")` |
| `scan_for_vulnerabilities` | Scans a recipe's dependencies against OSV.dev (API primary, local database offline fallback). | `scan_for_vulnerabilities(recipe_path="recipes/numpy")` |
| `update_cve_database` | Updates the local CVE database from `osv.dev`. | `update_cve_database(force=True)` |
| `update_mapping_cache` | Updates the local PyPI-to-Conda name mapping cache from Grayskull. Run when `get_conda_name` misses a package. | `update_mapping_cache(force=True)` |
| `migrate_to_v1` | **meta.yaml → recipe.yaml.** Converts a v0 recipe to v1 format using `feedrattler`. meta.yaml is preserved; review and remove it manually after validation. | `migrate_to_v1(recipe_path="recipes/numpy")` |
| `submit_pr` | Pushes recipe to your staged-recipes fork and opens a PR to conda-forge. Always `dry_run=True` first. | `submit_pr(recipe_name="numpy", dry_run=True)` |
| `get_conda_name` | Resolves a PyPI package name to its conda-forge equivalent. | `get_conda_name(pypi_name="python-dateutil")` |
| `run_system_health_check` | Performs a full diagnostic on the development environment. | `run_system_health_check()` |

## Manual CLI Commands

While Claude can run most of the workflow autonomously via MCP tools, you can also use these commands to manually manage the environment.

### Core Build Commands
```bash
# Build for a specific platform (runs inside Docker on Linux)
python build-locally.py linux-64

# Build with platform filter (runs all matching configs, e.g. all linux variants)
python build-locally.py --filter 'linux*'
python build-locally.py --filter 'osx*'

# Lint a recipe
pixi run -e conda-smithy lint recipes/<name>
```

### Maintenance and CI Commands
```bash
# Run a full diagnostic on the environment
pixi run -e local-recipes health-check

# Sync your fork with the upstream conda-forge/staged-recipes
pixi run -e local-recipes sync-upstream

# Submit a finished recipe to conda-forge (also available as submit_pr MCP tool)
pixi run -e local-recipes submit-pr <recipe-name>

# Manually update the local CVE and name mapping databases
pixi run -e local-recipes update-cve-db
pixi run -e local-recipes update-mapping-cache

# Manually run the PyPI "autotick" bot on a recipe
pixi run -e local-recipes autotick recipes/<name>/recipe.yaml

# Convert a meta.yaml recipe to recipe.yaml using feedrattler
feedrattler recipes/<name>
```

## Recipe Formats

### Modern Format (recipe.yaml) - Recommended
Uses `schema_version: 1` with `${{ }}` context substitution and `if/then/else` conditionals.
```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/prefix-dev/recipe-format/main/schema.json
schema_version: 1
context:
  name: my-package
  version: "1.0.0"
package:
  name: ${{ name }}
  version: ${{ version }}
```

### Legacy Format (meta.yaml)
Uses Jinja2 `{{ }}` syntax with `# [selector]` comments.
```yaml
{% set name = "my-package" %}
{% set version = "1.0.0" %}
package:
  name: {{ name|lower }}
  version: {{ version }}
```

## Python Version Policy (`python_min`)

### Current conda-forge floor: `3.10`
Python 3.9 was dropped from the conda-forge build matrix in **August 2025**. The current matrix is `3.10, 3.11, 3.12, 3.13, 3.14`.

### Rules for setting `python_min`

1. **New `noarch: python` recipes (recipe.yaml v1)** — always use the CFEP-25 triad:
   ```yaml
   context:
     python_min: "3.10"        # global floor; increase if upstream requires it
   requirements:
     host:
       - python ${{ python_min }}.*
     run:
       - python >=${{ python_min }}
   tests:
     - python:
         imports: [mypackage]
         pip_check: true
         python_version: ${{ python_min }}.*
   ```

2. **New `noarch: python` recipes (meta.yaml v0)** — use:
   ```yaml
   {% set python_min = "3.10" %}
   requirements:
     host:
       - python {{ python_min }}
     run:
       - python >={{ python_min }}
   test:
     requires:
       - python {{ python_min }}
   ```

3. **When to use a value higher than `3.10`** — only when the upstream `python_requires` metadata explicitly requires a higher version. Always verify before setting `python_min` above the global floor.

4. **Never downgrade below `3.10`** — packages targeting Python 3.9 or 3.8 cannot be accepted into conda-forge as new recipes and will fail CI. Exception: existing feedstocks with a freeze on specific Python ranges (these require special handling and are not submittable to staged-recipes).

5. **Compiled packages** — use `python >=3.10` (no python_min variable; the build matrix handles versioning via the global pin).

6. **When reviewing existing recipes with `python_min: '3.9'`** — run `optimize_recipe` (SEL-002 will flag it) and update to `'3.10'` unless the upstream package's own `python_requires` is `>=3.9,<3.10` (i.e., genuinely 3.9-only).

## ⚠️ Critical Build Requirement: `stdlib`

**ALL** recipes that use a compiler (`c`, `cxx`, `rust`, etc.) **MUST** also include a matching `stdlib` dependency. Failure to do so will result in automatic rejection by conda-forge CI.

**Correct Usage (`recipe.yaml`):**
```yaml
requirements:
  build:
    - ${{ compiler("c") }}
    - ${{ stdlib("c") }}      # REQUIRED!
```

**Correct Usage (`meta.yaml`):**
```yaml
requirements:
  build:
    - {{ compiler('c') }}
    - {{ stdlib('c') }}      # REQUIRED!
```

## Conda-Forge Ecosystem Reference

The submission-to-feedstock workflow spans two GitHub orgs: **conda-forge** (the "Forge" — review, build infrastructure, automation) and **prefix-dev** (the modern Rust-based "Tooling" — pixi, rattler-build). This reference maps the repos and docs you'll touch when working on a recipe in this project.

### Local Tooling (this project's stack)

| Repo / Tool | Purpose | Docs |
|-------------|---------|------|
| [`prefix-dev/pixi`](https://github.com/prefix-dev/pixi) | Manages this project's `pixi.toml` env; installs `rattler-build` and other build tools without a separate conda/mamba install | https://pixi.sh/latest/ |
| [`prefix-dev/rattler-build`](https://github.com/prefix-dev/rattler-build) | Build engine for v1 `recipe.yaml` recipes — replaces `conda-build` and is significantly faster | https://rattler-build.prefix.dev/latest/ |
| [`conda/rattler`](https://github.com/conda/rattler) | Underlying Rust library that provides core conda logic for both pixi and rattler-build | https://docs.rs/rattler |
| [`conda-forge/rattler-build-conda-compat`](https://github.com/conda-forge/rattler-build-conda-compat) | Shim that lets rattler-build interoperate with `conda-smithy` linting and feedstock workflows | (README in repo) |
| [`conda-forge/miniforge`](https://github.com/conda-forge/miniforge) | Community installer used to bootstrap build environments inside CI | https://conda-forge.org/miniforge/ |
| [`conda/grayskull`](https://github.com/conda/grayskull) | Recipe generator from PyPI/CRAN metadata — used by `generate_recipe_from_pypi` and the autotick bot | (README in repo) |
| [`conda/conda-build`](https://github.com/conda/conda-build) | Legacy Python-based build engine; still required for v0 `meta.yaml` feedstocks that haven't migrated to v1 | https://docs.conda.io/projects/conda-build/ |
| [`mamba-org/mamba`](https://github.com/mamba-org/mamba) | Fast C++ conda solver; pixi and CI flows use `micromamba` for fast env setup | https://mamba.readthedocs.io/ |
| [`prefix-dev/setup-pixi`](https://github.com/prefix-dev/setup-pixi) | GitHub Action that installs pixi in CI; standard for next-gen feedstock workflows | (README in repo) |
| [`prefix-dev/pixi-build-backends`](https://github.com/prefix-dev/pixi-build-backends) | Collection of pixi build backends (`pixi-build-cmake`, `pixi-build-python`, `pixi-build-rust`, `pixi-build-rattler-build`) — the rattler-build crate referenced under Documentation is one entry in this repo | (README in repo) |
| [`prefix-dev/pixi-pack`](https://github.com/prefix-dev/pixi-pack) | Bundle a pixi env into a portable archive; relevant for the air-gapped flow in `docs/enterprise-deployment.md` | (README in repo) |

### Conda-Forge Submission Pipeline

| Repo | Role |
|------|------|
| [`conda-forge/staged-recipes`](https://github.com/conda-forge/staged-recipes) | Entry point for new recipes. Holds them until they're merged and converted into a feedstock. Ships `pixi.toml` + `build-locally.py` so contributors can build with the same toolchain CI uses. [Docs](https://conda-forge.org/docs/maintainer/adding_pkgs/) |
| [`conda-forge/conda-smithy`](https://github.com/conda-forge/conda-smithy) | Lints recipes (`conda-smithy recipe-lint`), rerenders feedstock CI configs, registers feedstocks with CI providers. Supports both `meta.yaml` and v1 `recipe.yaml`. [Docs](https://conda-forge.org/docs/maintainer/infrastructure/#conda-smithy) |
| [`conda-forge/conda-forge-pinning-feedstock`](https://github.com/conda-forge/conda-forge-pinning-feedstock) | Source of truth for global pins (Python 3.10–3.14, NumPy 2, GCC 14, Clang 19, CUDA 12.9, OpenSSL 3.5, Boost 1.88, …). Both conda-build and rattler-build resolve these. [Docs](https://conda-forge.org/docs/maintainer/pinning_deps/) |
| [`conda-forge/conda-forge.github.io`](https://github.com/conda-forge/conda-forge.github.io) | Source for the conda-forge documentation site itself |
| [`conda-forge/cdt-builds`](https://github.com/conda-forge/cdt-builds) | Core Dependency Tree (CDT) recipes for Linux system libraries (X11, glibc, mesa-libGL); cited as build-only deps in feedstocks linking against system packages |
| [`conda-forge/conda-forge-ci-setup-feedstock`](https://github.com/conda-forge/conda-forge-ci-setup-feedstock) | Helper conda package installed in build envs that configures channels, fetches pinning, and sets CI-specific paths |

### Automation, Bots & Backend

| Repo | Role |
|------|------|
| [`conda-forge/admin-requests`](https://github.com/conda-forge/admin-requests) | Cron jobs and admin scripts that turn merged staged-recipes PRs into standalone feedstock repos and handle ad-hoc admin tasks (mark-broken, transfer ownership, etc.) |
| [`regro/cf-scripts`](https://github.com/regro/cf-scripts) | Codebase for the **autotick bot** (`regro-cf-autotick-bot`) — monitors upstream releases, opens version-bump PRs against feedstocks |
| [`regro/cf-graph-countyfair`](https://github.com/regro/cf-graph-countyfair) | Dependency graph the autotick bot uses to plan migrations across the ecosystem |
| [`conda-forge/conda-forge-metadata`](https://github.com/conda-forge/conda-forge-metadata) | Python package providing API access to conda-forge metadata (PyPI↔conda mappings, feedstock metadata) — used by bots and the local `mapping_manager.py` |
| [`conda-forge/webservices`](https://github.com/conda-forge/webservices) | Backend that handles `@conda-forge-admin` PR commands (rerender, restart ci, lint, add user, …) and Heroku-hosted automation |
| [`conda-forge/feedstock-tokens`](https://github.com/conda-forge/feedstock-tokens) | Manages per-feedstock CI upload tokens |
| [`conda-forge/feedstock-outputs`](https://github.com/conda-forge/feedstock-outputs) | Registry mapping each feedstock to the package outputs it publishes; prevents two feedstocks from claiming the same output name |
| [`conda-forge/conda-forge-repodata-patches-feedstock`](https://github.com/conda-forge/conda-forge-repodata-patches-feedstock) | Post-publish fix mechanism — yanks, dep-pin tweaks, and metadata corrections applied to published packages without rebuilding |
| [`regro/conda-forge-feedstock-check-solvable`](https://github.com/regro/conda-forge-feedstock-check-solvable) | Tool used by webservices/CI to confirm a feedstock's dep tree is satisfiable before merging migration PRs |
| [`conda-forge/conda-forge-feedstock-ops`](https://github.com/conda-forge/conda-forge-feedstock-ops) | Shared Python toolkit for feedstock automation (rerendering, version updates, lint, solvability); imported by webservices, conda-smithy, and the autotick bot |
| [`regro/regro-cf-autotick-bot-action`](https://github.com/regro/regro-cf-autotick-bot-action) | GitHub Action wrapper that runs autotick-bot logic inside a feedstock's own CI workflow |
| [`prefix-dev/parselmouth`](https://github.com/prefix-dev/parselmouth) | PyPI ↔ conda-forge name-mapping data service; powers `mapping_manager.py` in this project's skill (`pypi_mapping_source: parselmouth` in `skill-config.yaml`) |

### Post-Submission

| Pattern | What It Is |
|---------|-----------|
| `<package>-feedstock` | The standalone repo created automatically when a staged-recipes PR is merged. All future updates, builds, and releases happen here — `staged-recipes` is no longer involved for that package. New v1 feedstocks are configured to use rattler-build as the default build tool in CI. |
| `repodata-patches` | When a published package needs a small fix (yank a bad build, tighten an upper bound, correct metadata), file a PR to `conda-forge-repodata-patches-feedstock` to amend the published metadata in-place — no rebuild required |

### Documentation & Knowledge Bases

| Source | Use For |
|--------|---------|
| [conda-forge Maintainer Docs](https://conda-forge.org/docs/maintainer/) | Authoritative reference for recipe authoring, pinning, infrastructure, and CI |
| [conda-forge News](https://conda-forge.org/news/) | Migration announcements, infrastructure changes, policy updates |
| [conda-forge Status Dashboard](https://conda-forge.org/status/) | Currently active migrations |
| [conda-forge Knowledge Base](https://conda-forge.org/docs/maintainer/knowledge_base/) | Common patterns: NumPy, BLAS/LAPACK, multi-output, CUDA, MPI |
| [v1 Recipe Support Announcement](https://conda-forge.org/blog/2025/02/27/conda-forge-v1-recipe-support/) | Why and how conda-forge adopted rattler-build / `recipe.yaml` |
| [Rattler-Build on Conda-Forge](https://prefix.dev/blog/rattler_build_in_conda_forge) | Practical walkthrough for migrating recipes to v1 |
| [CFEPs](https://github.com/conda-forge/cfep) | Conda-Forge Enhancement Proposals — accepted policy decisions (e.g., CFEP-25 `python_min`, CFEP-26 naming) |
| [Recipe Format Schema](https://github.com/prefix-dev/recipe-format) | JSON schema for `recipe.yaml` — referenced via `# yaml-language-server: $schema=...` at the top of v1 recipes |
| [Publishing to conda-forge (Rattler-Build docs)](https://rattler-build.prefix.dev/latest/publishing/) | End-to-end publishing walkthrough using the Rust toolchain |
| [pixi-build-rattler-build](https://github.com/prefix-dev/pixi-build-backends/tree/main/crates/pixi-build-rattler-build) | Configure pixi to call rattler-build as a build backend in `pixi.toml` |
| [conda-forge Blog](https://conda-forge.org/blog/) | Long-form posts (deep-dives, retrospectives); distinct from News (terse announcements) |
| [conda-forge User Docs](https://conda-forge.org/docs/user/) | End-user channel docs (install, configure); distinct from Maintainer Docs |
| [conda-forge Governance](https://conda-forge.org/docs/orga/) | Org structure, decision-making, code of conduct, CFEP process |
| [conda-forge/by-the-numbers](https://github.com/conda-forge/by-the-numbers) | Source for the conda-forge ecosystem-level statistics dashboard (package counts, build times, contributor data) |

### Community Channels

| Channel | Status |
|---------|--------|
| [Zulip](https://conda-forge.zulipchat.com/) | **Primary** real-time channel for help, troubleshooting, announcements |
| [conda-forge News](https://conda-forge.org/news/) | Posted announcements (also surfaced in Zulip) |
| [Discourse](https://conda.discourse.group/) | **Read-only** since Oct 15, 2025 — search archive only |
| Gitter | Decommissioned; replaced by Zulip |

### Channel Storefronts

| Storefront | Use For |
|------------|---------|
| [Anaconda.org/conda-forge](https://anaconda.org/conda-forge) | Original front-end; package search, build status badges, owner info |
| [prefix.dev/channels/conda-forge](https://prefix.dev/channels/conda-forge) | Modern front-end; faster search, cleaner UI |

## BMAD Method Documentation

The BMAD Method is an AI-driven software development framework used in this project.

- **Local copy** (offline): `.claude/docs/bmad-method-llms-full.txt`
- **Live source**: https://docs.bmad-method.org/llms-full.txt

Fetch the live source for the latest version, or reference the local copy with `@.claude/docs/bmad-method-llms-full.txt` when working offline.

## Project Documentation Reference

For extended architectural context, please reference the centralized `docs/` folder:
- **`docs/mcp-server-architecture.md`** — FastMCP server integration and PyPI name mapping subsystem.
- **`docs/enterprise-deployment.md`** — Air-gapped environments and JFrog Artifactory integration.
- **`docs/developer-guide.md`** — Local testing and general recipe development guidelines.
- **`docs/copilot-to-api.md`** — Five ways to drive a GitHub Copilot subscription as a local model backend (`copilot-api`, `litellm`, `copilot-openai-api`, `copilot-api-proxy`, `c2p`); decision tree, auth flows, configuration reference.
- **`docs/specs/copilot-bridge-vscode-extension.md`** — BMAD-consumable tech-spec for a sideload-only VS Code extension that wraps the bridge pattern. Run via `bmad-quick-dev`.