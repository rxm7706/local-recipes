# FastMCP Server Architecture for Conda-Forge Recipes

**Integration Model:** BMAD Method (Brownfield) + Claude Code 
**Primary Server:** `.claude/tools/conda_forge_server.py`
**Goal:** Autonomous, air-gapped compatible recipe generation and maintenance.

This document details the AI integration architecture for `local-recipes`. It replaces the legacy `conda-forge-expert` skill model with a modern, tool-driven FastMCP architecture.

---

## 1. Overview

The repository acts as an AI-assisted, semi-autonomous packaging factory for `conda-forge` recipes. Instead of static text skills, Claude interacts with the repository via a **FastMCP Server**. This server exposes a suite of Python-based tools that handle the entire recipe lifecycle—from generation to submission.

This design aligns perfectly with the **BMAD Method**, allowing BMAD agents to use robust, deterministic tools to accomplish user stories (e.g., "Add requests-cache to conda-forge").

> **Enterprise / Air-Gap Constraint:** All MCP tools and workflows in this repository are designed to support operation within strict air-gapped environments. Tools must be capable of bootstrapping via internal JFrog Artifactory mirrors (`conda-forge-remote` and `internal-conda-local`) using configured `.pixi/config.toml` default channels, rather than relying on public internet access.

## 2. Autonomous Recipe Lifecycle

BMAD agents operating in this repository should follow this closed-loop sequence using the exposed MCP tools:

1. **Generate** — `generate_recipe_from_pypi(package_name="<pkg>")` to create initial `recipe.yaml` files.
2. **Validate** — `validate_recipe(recipe_path="<path>")` to check schema, license, and run `rattler-build lint`.
3. **Edit & Refine** — `edit_recipe()` for structured modifications (e.g., maintainers, SHA256, version bounds).
4. **Security Scan** — `scan_for_vulnerabilities()` against OSV.dev; resolve any findings.
5. **Optimize** — `optimize_recipe()` to apply conda-forge best practices (e.g., fixing `python_min` CFEP-25 violations).
6. **Build** — `trigger_build(config="linux-64")` to start the local asynchronous build.
7. **Monitor** — Poll `get_build_summary()` until the build completes.
8. **Debug (if failed)** — Pass the error log to `analyze_build_failure()`, apply the suggested fix via `edit_recipe`, and trigger the build again.
9. **Submit PR** — Call `submit_pr(recipe_name, dry_run=True)` first to verify gh auth and forks, then `submit_pr(recipe_name)` to push and open the PR.

---

## 3. Core MCP Capabilities

These tools are natively exposed by `.claude/tools/conda_forge_server.py`:

| Category | Tool | Description |
|---|---|---|
| **Generation** | `generate_recipe_from_pypi` | Scaffolds a new `v1` recipe from PyPI metadata. |
| **Validation** | `validate_recipe` | Lints recipe schema, license, and checksums. |
| | `check_dependencies` | Air-gapped friendly dependency verification against conda-forge or JFrog channels. |
| **Modification** | `edit_recipe` | Programmatic, structured editing of `recipe.yaml` (preferred over raw file edits). |
| | `optimize_recipe` | Enforces best practices (e.g., DEP-001, PIN-001, SEL-002). |
| **Execution** | `trigger_build` | Starts a local build (rattler-build via pixi). |
| | `get_build_summary` | Polls for build results. |
| | `analyze_build_failure` | Analyzes standard error patterns and suggests structural fixes. |

---

## 4. PyPI-Conda Name Mapping Subsystem

A critical part of the architecture is the name mapping subsystem, required because PyPI and conda-forge often use different package names (e.g., `docker` -> `docker-py`). 

### Design Philosophy

To maintain a lean repository and support air-gapped environments:
- Only essential files are tracked in git (`custom.yaml`, `different_names.json`, `stats.json`).
- Large indexes are cached locally with a 7-day TTL and are ignored via `.gitignore`.
- Data is aggregated from multiple sources, prioritizing user overrides.

### Directory Structure

```text
.claude/skills/conda-forge-expert/pypi_conda_mappings/
├── custom.yaml             # User-defined overrides (Highest Priority, TRACKED)
├── different_names.json    # Packages where names differ (TRACKED)
├── stats.json              # Sync metadata & TTL tracking (TRACKED)
├── unified.json            # All mappings (CACHE - gitignored)
├── by_pypi_name.json       # PyPI lookup index (CACHE - gitignored)
└── by_conda_name.json      # Conda lookup index (CACHE - gitignored)
```

### Automation

The mapping subsystem is updated via a GitHub Actions workflow (`.github/workflows/sync-pypi-mappings.yml`) which runs weekly or whenever `custom.yaml` is updated. 

Developers and BMAD agents can manually trigger an update using:
```bash
pixi run -e local-recipes update-mapping-cache
```
The MCP tool `get_conda_name(pypi_name="<pkg>")` hooks directly into this cached subsystem to instantly resolve PyPI names to their conda-forge equivalents during recipe generation.
