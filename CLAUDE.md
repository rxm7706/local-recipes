# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository is an **AI-assisted, semi-autonomous packaging factory** for conda-forge recipes. It mirrors the workflow of `conda-forge/staged-recipes` but is supercharged with a suite of custom tools that enable Claude to handle nearly the entire recipe lifecycle, from generation and security scanning to building, debugging, and maintenance.

**Critical Rule**: Do not mix `meta.yaml` and `recipe.yaml` formats in the same build run. The tooling will reject mixed-mode runs.

## AI-Assisted Workflow & Custom Tooling

This repository's core strength is its suite of custom tools, which are natively exposed to Claude via a FastMCP server (`.claude/tools/conda_forge_server.py`). This enables a powerful, autonomous workflow.

### Core Capabilities

| Tool | Description | Example Usage |
|---|---|---|
| `generate_recipe_from_pypi` | Creates a new recipe from a PyPI package. | `generate_recipe_from_pypi(package_name="numpy")` |
| `edit_recipe` | Programmatically modifies a recipe file using structured actions. **This is the preferred method for all edits.** | `edit_recipe('recipes/numpy/recipe.yaml', [{"action": "update", "path": "context.version", "value": "2.0.0"}])` |
| `check_dependencies` | Verifies that all dependencies exist on conda-forge. | `check_dependencies(recipe_path="recipes/numpy")` |
| `validate_recipe` | Lints a recipe for correctness against conda-forge standards. | `validate_recipe(recipe_path="recipes/numpy")` |
| `optimize_recipe` | Lints a recipe for quality, maintainability, and best practices. | `optimize_recipe(recipe_path="recipes/numpy")` |

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
| `update_recipe` | **Local "Autotick" Bot.** Checks for new upstream versions and automatically updates the recipe file. | `update_recipe(recipe_path="recipes/numpy/recipe.yaml")` |
| `scan_for_vulnerabilities` | Scans a recipe's dependencies against a local CVE database. | `scan_for_vulnerabilities(recipe_path="recipes/numpy")` |
| `update_cve_database` | Updates the local CVE database from `osv.dev`. | `update_cve_database(force=True)` |
| `get_conda_name` | Resolves a PyPI package name to its conda-forge equivalent. | `get_conda_name(pypi_name="python-dateutil")` |
| `run_system_health_check` | Performs a full diagnostic on the development environment. | `run_system_health_check()` |

## Manual CLI Commands

While Claude can run most of the workflow autonomously, you can also use these commands to manually manage the environment.

### Core Build Commands
```bash
# Build for a specific platform
python build-locally.py linux-64

# Lint a recipe
pixi run -e conda-smithy lint recipes/<name>
```

### Maintenance and CI Commands
```bash
# Run a full diagnostic on the environment
pixi run -e local-recipes health-check

# Sync your fork with the upstream conda-forge/staged-recipes
pixi run -e local-recipes sync-upstream

# Submit a finished recipe to conda-forge
pixi run -e local-recipes submit-pr <recipe-name>

# Manually update the local CVE and name mapping databases
pixi run -e local-recipes update-cve-db
pixi run -e local-recipes update-mapping-cache

# Manually run the "autotick" bot on a recipe
pixi run -e local-recipes autotick recipes/<name>/recipe.yaml
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

## References

- [conda-forge Documentation](https://conda-forge.org/docs/)
- [staged-recipes Repository](https://github.com/conda-forge/staged-recipes)
- [rattler-build Documentation](https://rattler.build/latest/)
- [pixi Documentation](https://pixi.sh/latest/)
