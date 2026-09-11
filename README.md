# local-recipes

[![Test All Platforms](https://github.com/rxm7706/local-recipes/actions/workflows/test-all.yml/badge.svg)](https://github.com/rxm7706/local-recipes/actions/workflows/test-all.yml)
[![Test Linux](https://github.com/rxm7706/local-recipes/actions/workflows/test-linux.yml/badge.svg)](https://github.com/rxm7706/local-recipes/actions/workflows/test-linux.yml)
[![Test Windows](https://github.com/rxm7706/local-recipes/actions/workflows/test-windows.yml/badge.svg)](https://github.com/rxm7706/local-recipes/actions/workflows/test-windows.yml)
[![Test macOS](https://github.com/rxm7706/local-recipes/actions/workflows/test-macos.yml/badge.svg)](https://github.com/rxm7706/local-recipes/actions/workflows/test-macos.yml)

A local conda-forge style staged-recipes workspace for building and testing Conda/Rattler Build recipes on your machine. This repo lets you:
- Author recipes in either legacy conda-build format (`meta.yaml`) or modern Rattler Build format (`recipe.yaml`).
- Bootstrap a minimal build environment and build all recipes locally with pinned variants.
- Run the lightweight tests embedded in each recipe as part of the build.

Note: Do not mix `meta.yaml` and `recipe.yaml` recipes in the same build run. The tooling will reject mixed-mode runs.

## Stack and tooling
- Language: Python (tooling and scripts)
- Package managers/build tools:
  - Conda + libmamba solver (`conda`, `conda-libmamba-solver`)
  - conda-build (for `meta.yaml` recipes)
  - Rattler Build with conda-compat shim (for `recipe.yaml` recipes)
  - conda-index (local channel indexing)
- CI/Orchestration helpers:
  - `.ci_support/build_all.py` (determines build mode, order, variants)
  - Platform scripts under `.scripts/` (Windows, Linux, macOS)
  - Cross-platform dispatcher: `build-locally.py`
- Global pinning/variants: `conda_build_config.yaml` and `.ci_support/<platform>.yaml`
- Bootstrap env spec: `environment.yaml`
- Primary task runner: `pixi.toml` / `pixi.lock` — see [Pixi tasks](docs/how-to/pixi-tasks.md) for the full list.

## Quick start

See [`docs/tutorials/getting-started.md`](docs/tutorials/getting-started.md) for requirements, Windows fast path, cross-platform dispatch, and your first build.

## Building and testing recipes

See [`docs/how-to/recipe-testing-and-builds.md`](docs/how-to/recipe-testing-and-builds.md) for targeted builds, `test-recipes.py`, and platform matrix.

## Project structure (selected)
```
local-recipes/
├─ LICENSE, LICENSE.txt
├─ README.md                       # This file
├─ CHANGELOG.md                    # Repo-level change log (Keep a Changelog format)
├─ CLAUDE.md                       # Claude Code project context
├─ environment.yaml                # Bootstrap environment for build tooling
├─ conda_build_config.yaml         # Global pinning and variants
├─ test-recipes.py                 # Direct recipe testing script
├─ .ci_support/
│  ├─ build_all.py                # Build orchestration (mode detection, graph, variants)
│  ├─ linux64.yaml                # Linux x86_64 variant config
│  ├─ linux_aarch64.yaml          # Linux ARM64 variant config
│  ├─ win64.yaml                  # Windows x64 variant config
│  ├─ osx64.yaml                  # macOS x86_64 variant config
│  └─ osxarm64.yaml               # macOS ARM64 variant config
├─ .github/workflows/
│  ├─ test-all.yml                # Orchestrates all platform builds
│  ├─ test-linux.yml              # Linux builds (Docker)
│  ├─ test-windows.yml            # Windows builds (native)
│  └─ test-macos.yml              # macOS builds (x86_64 + ARM64)
├─ .scripts/
│  └─ run_win_build.bat           # Windows provisioning/build runner
├─ scripts/
│  ├─ bmad-switch                 # Active-project switcher for the BMAD multi-project layout
│  └─ ...                         # Other repo-level helper scripts (sync-upstream-conda-forge, submit_pr, ...)
├─ build-locally.py                # Cross-platform dispatcher
├─ recipes/
│  ├─ <recipe>/recipe.yaml        # Rattler Build format (modern)
│  └─ <recipe>/meta.yaml          # conda-build format (legacy)
├─ docs/                           # Diátaxis docs layer (see docs/MAP.md)
│  ├─ tutorials/                   # Getting started
│  ├─ how-to/                      # Task-oriented guides
│  ├─ reference/                   # Config / CLI / schema reference
│  ├─ explanation/                 # Architecture rationale
│  └─ specs/                       # Legacy intake specs (phasing out)
├─ archive/
│  └─ docs/bmad-setup-plan.md      # BMAD installation + multi-project layout plan
├─ _bmad/                          # BMAD configuration (installer-managed + custom overrides)
├─ _bmad-output/                   # BMAD artifacts, organized by project (see PROJECTS.md)
│  ├─ PROJECTS.md                  # Multi-project index + add-a-project guide
│  └─ projects/<slug>/             # Per-project planning + implementation artifacts
├─ setup.cfg                       # flake8 / Python style config
├─ conda-forge.yml                 # conda-forge configuration
├─ pixi.toml                       # Pixi environment configuration
```

## BMAD multi-project layout (this repo hosts more than just conda recipes)

This repository's primary purpose is conda-forge recipe authoring, but it also hosts other projects driven by [BMAD Method](https://docs.bmad-method.org/) under a single shared installation. Each BMAD project has its own subtree at `_bmad-output/projects/<slug>/`. The full layout, config-resolution order, and "adding a new project" guide live in:

- **`_bmad-output/PROJECTS.md`** — project index and operational reference.
- **`archive/docs/bmad-setup-plan.md`** — installation history + multi-project setup plan (Phase 8).
- **`CLAUDE.md` § "Multi-Project Pattern"** — quick-reference for AI agents and human contributors.

Quick commands:

```bash
scripts/bmad-switch --list             # list known projects
scripts/bmad-switch --current          # print active project
scripts/bmad-switch <slug>             # set active project
```

**Active-project resolution priority** — see **`CLAUDE.md` § "Multi-Project Pattern"** for the complete resolution order, two-symlink mechanism, and parallel-agent guidance (`_bmad/scripts/resolve_config.py`).

## Style and linting
- Python: `setup.cfg` configures flake8 with `max-line-length = 88`. Mirror nearby code style when editing helper scripts.
- YAML: Follow existing patterns in recipes. For Rattler Build, include the schema header:
  ```
  # yaml-language-server: $schema=https://raw.githubusercontent.com/prefix-dev/recipe-format/main/schema.json
  ```

## Examples
- Verified minimal sanity check for a Rattler recipe file structure:
  ```python
  from pathlib import Path
  recipe = Path(r"recipes/py-key-value/recipe.yaml")
  text = recipe.read_text(encoding="utf-8")
  required = ["schema_version:", "build:", "outputs:", "tests:"]
  missing = [m for m in required if m not in text]
  assert not missing, f"Missing markers: {missing}"
  print("Sanity test passed")
  ```
  Run from repo root: save as `temp_test_recipe_yaml.py` and execute with `python temp_test_recipe_yaml.py`.

## GitHub Actions and Pixi tasks

- Recipe CI workflows: [`docs/how-to/github-actions-recipe-ci.md`](docs/how-to/github-actions-recipe-ci.md)
- Full pixi task surface: [`docs/how-to/pixi-tasks.md`](docs/how-to/pixi-tasks.md)
- Developer reference (formats, config): [`docs/reference/developer-guide.md`](docs/reference/developer-guide.md)
- AI tooling architecture: [`docs/explanation/mcp-server-architecture.md`](docs/explanation/mcp-server-architecture.md)
- Enterprise / air-gap: [`docs/explanation/enterprise-deployment.md`](docs/explanation/enterprise-deployment.md)

Documentation map: [`docs/MAP.md`](docs/MAP.md)

## Known limitations and tips
- Do not mix `meta.yaml` and `recipe.yaml` recipes in a single run.
- Use `noarch: python` only for pure-Python packages that do not need compiled artifacts and don’t have OS-conditional install logic.
- When using `pin_subpackage(...)`, prefer `exact=True` if outputs are co-versioned in a multi-output recipe.
- Prefer `run_constraints` for optional extras to keep the solver flexible.
- For Python packages, ensure tests include `pip_check: true` where feasible to catch metadata issues early.
- Some dependencies referenced by example recipes may not exist on conda-forge yet; these are typically commented with notes and links in the recipe files.

## License
This repository is licensed under the terms found in `LICENSE` (and/or `LICENSE.txt`). Refer to those files for details.

## TODOs
- Add short contributor guidelines for adding new recipes and expected review checklist.
- If CI is enabled for this repo, add a section describing how CI picks up and builds recipes (e.g., Azure Pipelines config in `azure-pipelines.yml`).
- Add examples for Linux/macOS runners using `.scripts/run_docker_build.sh` and `.scripts/run_osx_build.sh`.
