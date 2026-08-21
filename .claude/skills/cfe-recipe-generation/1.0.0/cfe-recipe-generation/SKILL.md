---
name: cfe-recipe-generation
description: >
  Generates conda-forge recipe.yaml/meta.yaml files from PyPI, CRAN, CPAN, LuaRocks, npm, GitHub,
  and template sources, resolves a PyPI package name to its conda-forge equivalent, and checks/updates
  an existing recipe against the latest upstream GitHub release. Use when authoring or refreshing a
  conda-forge recipe's source/version/name fields.
---

# cfe-recipe-generation

## Overview

Packages conda-forge/local-recipes' Slice 1 "Recipe Generation" scripts (`recipe-generator.py`,
`name_resolver.py`, `github_updater.py` -- 3,148 lines total) as a standalone, source-cited skill.
Source: local path `.claude/skills/conda-forge-expert/` @ commit `c440227` (source_ref: `local`).
Forge tier: **Quick** (source-reading extraction, T1-low confidence throughout -- no AST tool
available at compile time). 62 exports documented (19 public entry points, 43 internal helpers).

## Quick Start

Three independent CLIs, one per script -- no shared entry point.

**Generate a recipe from PyPI** [SRC:scripts/recipe-generator.py:L2338-2346]:
```bash
python recipe-generator.py pypi requests
python recipe-generator.py pypi numpy==1.26.0
python recipe-generator.py template python-noarch --name mypackage --version 1.0.0
python recipe-generator.py github owner/repo --version v1.0.0
python recipe-generator.py cran ggplot2
python recipe-generator.py cpan Moose
python recipe-generator.py luarocks lua-cjson
python recipe-generator.py npm bmad-method
```
Writes `recipes/<conda-name>/recipe.yaml` (v1, default) or `meta.yaml` (`--format legacy`).

**Resolve a PyPI name to its conda-forge name** [SRC:scripts/name_resolver.py:L163-183]:
```bash
python name_resolver.py requests
# {"success": true, "pypi_name": "requests", "conda_name": "requests", ...}
```

**Update a recipe against the latest GitHub release** [SRC:scripts/github_updater.py:L269-303]:
```bash
python github_updater.py recipes/mypackage --dry-run
python github_updater.py recipes/mypackage --repo owner/repo --pre
```
Auto-detects the GitHub repo from the recipe's `source.url` / `about.homepage` when `--repo` is
omitted. Set `GITHUB_TOKEN` or `GH_TOKEN` to avoid the 60 req/h unauthenticated API rate limit.

## Common Workflows

**New PyPI package, sdist available:**
`fetch_pypi_info(name, version)` [SRC:scripts/recipe-generator.py:L714] `→ generate_recipe_yaml(info, output_dir)` [SRC:scripts/recipe-generator.py:L995]

**New PyPI package, maturin/PyO3 (Rust extension) wheel:**
`fetch_pypi_info(...)` detects `_is_maturin_pyo3()` [SRC:scripts/recipe-generator.py:L488] `→ _generate_maturin_recipe_yaml(info, output_dir)` [SRC:scripts/recipe-generator.py:L1129]

**npm CLI package:**
`fetch_npm_info(package_name, version, source="npm")` [SRC:scripts/recipe-generator.py:L1755] `→ generate_npm_recipe_yaml(info, output_dir, prepare_fix=..., test_mode="script")` [SRC:scripts/recipe-generator.py:L2040]

**Name resolution before any recipe edit (PyPI → conda-forge name may differ):**
`resolve_name(pypi_name)` [SRC:scripts/name_resolver.py:L112] tries local cache → `conda_forge_metadata` API → repodata fallback, in that order.

**Refresh an existing recipe's version:**
`update_recipe(recipe_path, github_repo=None, dry_run=False, allow_prerelease=False)` [SRC:scripts/github_updater.py:L131] -- parses the recipe, resolves the GitHub repo, compares latest release against the pinned version via `_is_newer()` [SRC:scripts/github_updater.py:L119].

## Key API Summary

| Function | Purpose | Key params |
|---|---|---|
| `fetch_pypi_info` | Fetch + normalize PyPI metadata into `PackageInfo` | `package_name`, `version` |
| `generate_recipe_yaml` | Write a v1 `recipe.yaml` for a PyPI/GitHub source | `info: PackageInfo`, `output_dir` |
| `generate_meta_yaml` | Write a legacy v0 `meta.yaml` | `info: PackageInfo`, `output_dir` |
| `_generate_maturin_recipe_yaml` | v1 recipe for a maturin/PyO3 compiled wheel | `info`, `output_dir` |
| `copy_template` | Seed a recipe from a template (`python-noarch`, etc.) | `template_name`, `output_dir`, `**replacements` |
| `fetch_npm_info` | Fetch + normalize npm registry metadata | `package_name`, `version`, `source` |
| `generate_npm_recipe_yaml` | Write a v1 npm recipe (per-platform inline build) | `info: NpmPackageInfo`, `output_dir` |
| `determine_build_backend` | Infer PEP 517 build backend from `requires_dist` | `requires_dist: list[str]` |
| `_render_cfe_block` | Emit the local-only `#### CFE metadata AND comments` footer | `info`, `conda_name`, `noarch_kind` |
| `normalize_name` (name_resolver) | Lowercase + hyphen-normalize a PyPI name | `name: str` |
| `resolve_name` (name_resolver) | PyPI name → conda-forge name, 3-tier fallback | `pypi_name: str` |
| `update_recipe` (github_updater) | Check/update a recipe against the latest GitHub release | `recipe_path`, `github_repo`, `dry_run`, `allow_prerelease` |

All 12 rows: [SRC:scripts/recipe-generator.py] / [SRC:scripts/name_resolver.py] / [SRC:scripts/github_updater.py] per the line numbers in Common Workflows and Full API Reference.

## Key Types

**`PackageInfo`** [SRC:scripts/recipe-generator.py:L82-107] -- the canonical result of `fetch_pypi_info`:
`name`, `version`, `summary`, `homepage`, `repository`, `license`, `license_file`, `source_url`,
`sha256`, `dependencies: list[str]`, `python_requires` (default `>=3.10`), `build_backend`
(default `setuptools`), `import_name` (actual top-level import, from sdist inspection),
`has_abi3: bool`, `sys_platform_deps: dict[str, list[str]]` (win/linux/osx-conditional deps, G91-adjacent),
`build_system_requires: list[str]` (conda-mapped `[build-system].requires`, G91).

**`NpmPackageInfo`** [SRC:scripts/recipe-generator.py:L1408-1443] -- the npm-path equivalent:
`raw_name` (e.g. `@openai/codex`), `conda_name` (e.g. `codex`), `version`, `tarball_url`,
`tarball_filename`, `bin_entries: dict`, `node_major` (default `20`), `is_scoped: bool`,
`is_github_source: bool`, `has_native_build: bool` (gates the maturin-style compiled path).

## Architecture at a Glance

- **PyPI path** (`recipe-generator.py pypi`): `fetch_pypi_info` → sdist inspection (import name,
  abi3, build-system requires, entry points) → `generate_recipe_yaml` / `_generate_maturin_recipe_yaml`
  / `generate_meta_yaml` (legacy).
- **npm path** (`recipe-generator.py npm`): `fetch_npm_info` → tarball hash + LICENSE detection →
  `generate_npm_recipe_yaml` (per-platform inline `build.script:`, no `noarch: generic`).
- **CRAN / CPAN / LuaRocks paths**: thin wrappers over `rattler-build generate-recipe` (`_run_rattler_generate`
  [SRC:scripts/recipe-generator.py:L2259]) plus a preflight validation pass (`_run_preflight_validation`
  [SRC:scripts/recipe-generator.py:L2220]).
- **Name resolution** (`name_resolver.py`): local mapping-cache JSON → `conda_forge_metadata` API →
  `current_repodata.json` fallback, first hit wins.
- **GitHub refresh** (`github_updater.py`): recipe-context parse → GitHub repo auto-detect from
  `source.url`/`about.homepage` → latest-release compare → in-place version/sha256 rewrite.
- **CFE-block emission contract** (`_render_cfe_block` [SRC:scripts/recipe-generator.py:L941-989]):
  every v1 generation path appends a local-only `#### CFE metadata AND comments` footer (identity,
  decision fields, `cfe-local-build-status: not-attempted` from birth) -- stripped before any push
  upstream (skill gotcha G62, outside this slice's scope). The v0 `meta.yaml` path deliberately omits it.

## CLI

```bash
python recipe-generator.py {pypi|template|github|cran|cpan|luarocks|npm} ...   # see Quick Start
python name_resolver.py <pypi-package-name>
python github_updater.py <recipe-path-or-dir> [--repo owner/repo] [--dry-run] [--pre]
```
Every CLI prints a JSON result to stdout and sets its exit code from `result["success"]`
(`github_updater.py`: `0` = success/already-current, `1` = error).

## Scripts & Assets

| Script | Purpose | Lines |
|---|---|---|
| `scripts/recipe-generator.py` | Generate conda-forge recipes from PyPI/CRAN/CPAN/LuaRocks/npm/GitHub/template sources | 2,651 |
| `scripts/name_resolver.py` | Resolve a PyPI name to its conda-forge equivalent | 186 |
| `scripts/github_updater.py` | Update a recipe against the latest GitHub release | 311 |

Copied byte-identical from source (content-preserved, per skf-create-skill's own script-bundling
contract) -- no assets detected (`assets_intent: none`).

<!-- [MANUAL:additional-notes] -->
<!-- Add custom notes here. This section is preserved during skill updates. -->
<!-- [/MANUAL:additional-notes] -->

## Full API Reference

See `references/recipe-generator.md`, `references/name-resolver.md`, `references/github-updater.md`
for the complete 62-entry export inventory (19 public, 43 internal helpers) with full signatures,
source lines, and provenance citations. See `references/knowledge-gotchas.md` for the four
recipe-generation-specific gotchas this skill must preserve (G54, G91, G94's third sub-item, G98)
and the four bundled reference docs (`recipe-yaml-reference.md`, `meta-yaml-reference.md`,
`jinja-functions.md`, `getting-started.md`).

<!-- [MANUAL:api-notes] -->
<!-- Add custom API notes here. This section is preserved during skill updates. -->
<!-- [/MANUAL:api-notes] -->
