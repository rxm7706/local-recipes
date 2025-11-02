# local-recipes

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
- Optional/Present but not primary: `pixi.toml`/`pixi.lock` (no explicit integration in scripts) — see TODO.

## Requirements
- A supported OS (Windows, Linux, or macOS). Windows is the fastest path here.
- Network access to conda-forge.
- On Windows, a shell that can run batch scripts and allow PowerShell execution for initial provisioning.

The build tools environment will be provisioned automatically by the Windows script using micromamba if it is not already present.

Packages pulled into the bootstrap environment (see `environment.yaml`):
- python 3.12.*, conda ≥ 25.9, conda-libmamba-solver, conda-build, conda-index,
  conda-forge-ci-setup, conda-forge-pinning, networkx 2.4.*, rattler-build-conda-compat.

## Quick start

### Fast path on Windows (recommended)
1) Open "Developer Command Prompt for VS" or a PowerShell/cmd with script execution allowed.
2) From the repo root, select a variant (optional):
```
SET CONFIG=win64
```
3) Run the Windows build runner:
```
CALL .scripts\run_win_build.bat
```
What it does:
- Provisions a Miniforge environment into `%MINIFORGE_HOME%` (defaults to `%USERPROFILE%\Miniforge3`) using micromamba.
- Activates it, sets strict channel priority and libmamba solver.
- Runs `run_conda_forge_build_setup` to configure conda-forge settings.
- Removes recipes also present in the `main` branch (so you only build the changed/new local recipes).
- Builds all recipes found in `recipes\` via `.ci_support\build_all.py`.
- Indexes `%CONDA_BLD_PATH%` for local artifact resolution.

Artifacts will be placed under `%CONDA_BLD_PATH%` (default `C:\bld`).

### Cross-platform builds
Use the dispatcher to select the correct backend for your platform:
```
python build-locally.py win64
# or interactively filter/select
python build-locally.py --filter win*
```
- On Windows, this delegates to `.scripts\run_win_build.bat`.
- On Linux/macOS, it invokes the corresponding `.scripts/run_docker_build.sh` or `.scripts/run_osx_build.sh` (if present from conda-smithy).

## Building a single recipe (targeted workflow)

- For `recipe.yaml` (Rattler Build):
  1) Create/activate a tooling env that includes the pins/variants you intend to use. If you already ran the Windows script above, you have compatibility shims available in that environment. Otherwise, for a standalone env:
  ```
  conda create -n rb -c conda-forge python=3.12 rattler-build-conda-compat conda-forge-pinning conda conda-build conda-libmamba-solver -y
  conda activate rb
  ```
  2) Build the recipe (example for win-64):
  ```
  rattler-build build recipes\py-key-value --target-platform win-64 -c conda-forge --variant-config .ci_support\win64.yaml
  ```

- For `meta.yaml` (conda-build):
  ```
  conda-build recipes\<recipe-name>
  ```
  You may also let `.ci_support\build_all.py` compute the build order and dependencies for multiple conda-build recipes.

## How tests work here
- Rattler Build (`recipe.yaml`): tests are defined under `recipe: tests:` blocks.
  - Example: `recipes\py-key-value\recipe.yaml` includes Python import checks and optional script checks.
- conda-build (`meta.yaml`): tests are under `test:` with `imports`, `commands`, `requires`, etc.
- Tests run automatically during the build step. If a build completes successfully, these functional smoke tests have already executed.

Running just tests on an existing artifact:
- conda-build:
  ```
  conda-build --test <path-to-artifact.tar.bz2 or .conda>
  ```
- Rattler Build: re-run `rattler-build build` for that recipe (standalone test invocation differs by version; the common local workflow is to rebuild).

## Useful scripts and entry points
- `build-locally.py` — Cross-platform entry; chooses Windows/Linux/macOS backend based on host OS and `CONFIG`/`--filter`.
- `.scripts\run_win_build.bat` — Windows provision + build runner.
- `.ci_support\build_all.py` — Orchestrates builds; determines if the repo contains `meta.yaml` or `recipe.yaml` recipes (mixing is rejected), constructs dependency graphs (conda-build), and shells out to Rattler Build as needed.

## Environment variables
Commonly used variables (some set by our scripts):
- `CONFIG` — Platform/variant key, e.g., `win64`. Used by `build-locally.py` and to select `.ci_support\<CONFIG>.yaml`.
- `CONDA_BLD_PATH` — Artifact workspace directory (defaults to `C:\bld` on Windows if unset in the script).
- `MINIFORGE_HOME` — Location of the base conda environment; defaults to `%USERPROFILE%\Miniforge3`.
- `CI` — May be set to `azure` in CI environments; used for certain logging/behavior in scripts.
- `UPLOAD_PACKAGES`, `IS_PR_BUILD`, `BUILD_WITH_CONDA_DEBUG`, `BUILD_OUTPUT_ID` — Build flags the tooling may honor (set inside `build-locally.py` when debug mode is used).
- `CONDA_FORGE_DOCKER_RUN_ARGS` — Used on macOS host with Linux docker backend to adjust cache location.
- `OSX_SDK_DIR`, `MACOSX_DEPLOYMENT_TARGET`, `MACOSX_SDK_VERSION` — Used by the macOS backend when appropriate.
- `DEFAULT_LINUX_VERSION` — May be set to `cos7` when CentOS 7 sysroots are detected.

## Project structure (selected)
```
local-recipes/
├─ LICENSE, LICENSE.txt
├─ README.md                      # This file
├─ environment.yaml               # Bootstrap environment for build tooling
├─ conda_build_config.yaml        # Global pinning and variants
├─ .ci_support/
│  ├─ build_all.py               # Build orchestration (mode detection, graph, variants)
│  └─ <platform>.yaml            # Variant configs, e.g., win64.yaml
├─ .scripts/
│  └─ run_win_build.bat          # Windows provisioning/build runner
├─ build-locally.py               # Cross-platform dispatcher
├─ recipes/
│  ├─ <recipe>/recipe.yaml       # Rattler Build format (modern)
│  └─ <recipe>/meta.yaml         # conda-build format (legacy)
├─ setup.cfg                      # flake8 / Python style config
├─ conda-forge.yml, azure-pipelines.yml  # CI config (if used)
├─ pixi.toml, pixi.lock           # Present; not wired into scripts (see TODO)
```

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
- Document how (or if) `pixi.toml`/`pixi.lock` are intended to be used in this workspace. Currently, the provided scripts do not reference Pixi.
- Add short contributor guidelines for adding new recipes and expected review checklist.
- If CI is enabled for this repo, add a section describing how CI picks up and builds recipes (e.g., Azure Pipelines config in `azure-pipelines.yml`).
- Add examples for Linux/macOS runners if/when `.scripts/run_docker_build.sh` and `.scripts/run_osx_build.sh` are present in this repo.
