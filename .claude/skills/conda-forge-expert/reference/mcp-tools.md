# MCP Tools Reference

The conda-forge-expert skill exposes 18 tools via a FastMCP server at `.claude/tools/conda_forge_server.py`. Full schemas (parameters, defaults, return types) are surfaced at tool-call time; this file is a navigable index by purpose.

## Core Capabilities

| Tool | Purpose |
|---|---|
| `generate_recipe_from_pypi` | Create a new recipe from a PyPI package. |
| `edit_recipe` | Programmatically modify a recipe file using structured actions. **Preferred method for all edits.** |
| `check_dependencies` | Verify dependencies exist on conda-forge or a custom channel. Uses batch repodata.json fetching (fast, air-gapped-friendly). Supports JFrog Artifactory via `channel` param + auth env vars (`JFROG_API_KEY`, etc.). |
| `validate_recipe` | Lint a recipe against conda-forge standards; also runs `rattler-build lint` when available. |
| `optimize_recipe` | Lint for quality and best practices. Check codes: DEP-001 (dev dep in run), DEP-002 (noarch Python upper bound), PIN-001 (exact pin), ABT-001 (missing license_file), SCRIPT-001/002 (build.sh anti-patterns), SEL-001/002 (redundant selectors, CFEP-25 python_min). |

## Build, Test, and Debug

| Tool | Purpose |
|---|---|
| `trigger_build` | Start a local build asynchronously. |
| `get_build_summary` | Poll for the build result; returns a JSON report. |
| `analyze_build_failure` | Take an error log from a failed build and suggest a structured fix. |

## Security and Maintenance

| Tool | Purpose |
|---|---|
| `update_recipe` | **"Autotick" Bot (PyPI).** Check for new upstream PyPI versions and update the recipe. |
| `update_recipe_from_github` | **"Autotick" Bot (GitHub).** Fetch the latest GitHub release and update. Use for packages not on PyPI. Always `dry_run=True` first. |
| `check_github_version` | Read-only GitHub version check — returns the latest tag without modifying the recipe. |
| `scan_for_vulnerabilities` | Scan a recipe's dependencies against OSV.dev (API primary, local DB offline fallback). |
| `update_cve_database` | Update the local CVE database from `osv.dev`. |
| `update_mapping_cache` | Update the local PyPI-to-Conda name-mapping cache from Grayskull. Run when `get_conda_name` misses a package. |
| `migrate_to_v1` | **meta.yaml → recipe.yaml** via `feedrattler`. meta.yaml is preserved; review and remove it manually after validation. |
| `submit_pr` | Push the recipe to your staged-recipes fork and open a PR to conda-forge. Always `dry_run=True` first. |
| `get_conda_name` | Resolve a PyPI package name to its conda-forge equivalent. |
| `run_system_health_check` | Full diagnostic on the development environment. |

## Special notes (not surfaced in tool docstrings)

- **`submit_pr` and `update_recipe_from_github`** — always run `dry_run=True` first to verify prerequisites (gh auth, fork presence, branch state).
- **`migrate_to_v1`** — preserves the original `meta.yaml`. Validate the converted `recipe.yaml` first, then remove `meta.yaml` manually. Never leave both files in the same recipe directory at build time.
- **`check_dependencies` JFrog support** — for air-gapped or corporate environments, pass `channel="https://your-jfrog-host/conda-forge"` plus the `JFROG_API_KEY` env var (or `JFROG_USERNAME` + `JFROG_PASSWORD`). See `docs/enterprise-deployment.md`.
- **`update_cve_database`** — runs offline-friendly (downloads OSV.dev's full database to `~/.cache/conda-forge-skill/`); use during initial setup or to refresh CVE feed. Not needed before each scan if the database is recent.

## See also

- **Lifecycle integration** — The 9-step Autonomous Loop (Generate → Validate → Edit → Security Scan → Optimize → Check Deps → Trigger Build → Monitor → Submit PR) in `SKILL.md` § "Primary Workflow: The Autonomous Loop" specifies success criteria and pre-conditions for each tool.
- **Server source** — `.claude/tools/conda_forge_server.py` (FastMCP) for canonical signatures and implementation.
