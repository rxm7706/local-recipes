---
name: conda-forge-expert
description: |
  Autonomous conda-forge packaging agent. Manages the entire recipe lifecycle,
  from generation, security scanning, and building to debugging, maintenance,
  and PR submission.

  USE THIS SKILL WHEN: creating or updating conda recipes, fixing conda-forge
  build failures, or performing any task related to conda packaging.
version: 5.4.0
allowed-tools: [conda_forge_server]
---

# Conda-Forge Autonomous Agent

> **Mission**: To autonomously manage the entire lifecycle of a conda-forge recipe, from creation to maintenance, with maximum efficiency and quality.

## Primary Workflow: The Autonomous Loop

My core operational loop is designed to be a fully autonomous, closed-loop system. When asked to create or update a recipe, I will follow these steps programmatically:

1.  **Generate Recipe**: Use `generate_recipe_from_pypi` to create the initial recipe files.
2.  **Initial Validation**: Use `validate_recipe` to check for basic correctness.
3.  **Edit & Refine**: Use the powerful `edit_recipe` tool to make structured changes, such as adding maintainers or calculating the SHA256 hash.
4.  **Security Scan**: Use `scan_for_vulnerabilities` to check all dependencies against OSV.dev (API primary, local CVE database as offline fallback). Report and resolve any findings.
5.  **Optimization**: Use `optimize_recipe` to lint for conda-forge best practices and apply quality improvements.
6.  **Trigger Build**: Use `trigger_build` to start the local build process asynchronously.
7.  **Monitor Build**: Periodically call `get_build_summary` to check the build status.
8.  **Analyze & Debug**:
    *   **If build fails**: Call `analyze_build_failure` on the error log to get a structured diagnosis. Use the diagnosis to construct a fix using `edit_recipe`, then return to Step 6.
    *   **If build succeeds**: Proceed to the next step.
9.  **Submit PR**: Call `submit_pr(recipe_name, dry_run=True)` first to verify all prerequisites (gh auth, fork presence). If OK, call `submit_pr(recipe_name)` to push and open the PR. The result contains `pr_url` on success.

## Core Tools Reference

My capabilities are powered by a suite of native MCP tools.

### Recipe Creation & Modification
| Tool | Description |
|---|---|
| `generate_recipe_from_pypi` | Creates a new recipe from a PyPI package. |
| `edit_recipe` | **Primary editing tool.** Safely modifies a recipe using structured actions (e.g., update version, add dependency, calculate hash). |
| `get_conda_name` | Resolves a PyPI package name to its correct conda-forge equivalent using a tiered, cache-first strategy. |

### Validation & Quality
| Tool | Description |
|---|---|
| `validate_recipe` | Lints for correctness (schema, license, etc.). |
| `check_dependencies` | Verifies that all dependencies exist on conda-forge (or a custom channel). Batch repodata.json fetching — fast, air-gapped-friendly, JFrog Artifactory-compatible. |
| `optimize_recipe` | Lints for quality and best practices. Check codes: DEP-001 (dev dep in run), DEP-002 (noarch Python upper bound), PIN-001 (exact pin), ABT-001 (missing license_file), SCRIPT-001/002 (build.sh), SEL-001/002 (selectors/CFEP-25). |

### Build & Debug
| Tool | Description |
|---|---|
| `trigger_build` | Starts a build asynchronously. |
| `get_build_summary` | Retrieves the result of a build (success/failure, artifacts, logs). |
| `analyze_build_failure` | Diagnoses the root cause of a build failure from an error log. |

### Security & Maintenance
| Tool | Description |
|---|---|
| `update_recipe` | **"Autotick" Bot (PyPI).** Checks for new upstream versions on PyPI and updates the recipe. |
| `update_recipe_from_github` | **"Autotick" Bot (GitHub).** Fetches latest GitHub release and updates the recipe (version + SHA256). Use for packages not on PyPI. Always `dry_run=True` first. |
| `check_github_version` | Read-only GitHub version check — returns latest tag without modifying the recipe. |
| `scan_for_vulnerabilities` | Scans dependencies against OSV.dev API (primary) with local CVE database as offline fallback. |
| `update_cve_database` | Updates the local CVE database from `osv.dev`. |
| `update_mapping_cache` | Updates the PyPI-to-Conda name mapping cache from Grayskull. |
| `run_system_health_check` | Performs a full diagnostic on the development environment. |
| `submit_pr` | **Completes the loop.** Pushes recipe to your staged-recipes fork and opens a PR to conda-forge. Use `dry_run=True` first. |

## Manual CLI Commands

While I can perform most actions autonomously, the following CLI commands are available for manual intervention and management.

| Command | Description |
|---|---|
| `pixi run -e local-recipes health-check` | Run a full diagnostic on the environment. |
| `pixi run -e local-recipes sync-upstream` | Sync your fork with `conda-forge/staged-recipes`. |
| `pixi run -e local-recipes submit-pr <name>` | Submit a finished recipe to conda-forge. |
| `pixi run -e local-recipes autotick <path>` | Manually run the "autotick" bot on a recipe. |
| `pixi run -e local-recipes update-cve-db` | Refresh the local vulnerability database. |
| `pixi run -e local-recipes update-mapping-cache`| Refresh the PyPI name mapping cache. |

## Version History

- **v5.4.0**: Documentation audit pass. Corrected `failure_analyzer.py` pattern count (30→33 patterns, 9→10 categories). Updated `check_dependencies` MCP tool to expose `--channel` and `--subdirs` parameters; added batch repodata.json / JFrog Artifactory / air-gapped environment docs. Updated `scan_for_vulnerabilities` description (OSV.dev API primary, local DB fallback). Updated `generate_recipe_from_pypi` docstring (grayskull only). Updated `optimize_recipe` docstring with full check-code table (DEP-001→SEL-002).
- **v5.3.0**: Added `github_updater.py` + `update_recipe_from_github` MCP tool — GitHub Releases autotick write path (mirrors `recipe_updater.py`). Auto-detects GitHub repo from recipe; updates `context.version`, resets `build.number`, recalculates SHA256. Pre-releases skipped by default. `check_github_version` clarified as read-only.
- **v5.2.0**: Added `check_github_version` MCP tool for GitHub-only packages (complements `update_recipe`). FastMCP 3.x Context injection on `trigger_build` and `update_cve_database` for progress logging. Fixed `recipe_optimizer.py` selector analysis to handle recipe.yaml v1 list-based `skip` conditions; added CFEP-25 `python_min` check (SEL-002). Fixed Pyright `reportPossiblyUnboundVariable` diagnostics.
- **v5.1.0**: Added `submit_pr` MCP tool, completing the full autonomous loop from generation to PR submission. Includes `dry_run` mode for safe prerequisite checks before writing to GitHub.
- **v5.0.0**: Major architectural overhaul. Implemented a full suite of autonomous tools, including a closed-loop build/debug system, a local "autotick" bot, vulnerability scanning, a programmatic recipe editor, and an intelligent failure analyzer. The skill is now a true autonomous agent.
- **v4.2.1**: Removed the `stdlib` local testing hack by implementing an automatic variant override.
- **v4.0.0**: Initial modular architecture.
