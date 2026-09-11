# Getting started

Learning-oriented path to a working build environment for this repo. For
task-oriented commands after setup, see [`docs/how-to/`](../how-to/).

## Requirements

- A supported OS (Windows, Linux, or macOS). Windows is the fastest path here.
- Network access to conda-forge.
- On Windows, a shell that can run batch scripts and allow PowerShell execution for initial provisioning.

The build tools environment will be provisioned automatically by the Windows script using micromamba if it is not already present.

Packages pulled into the bootstrap environment (see `environment.yaml`):

- python 3.12.*, conda ≥ 25.9, conda-libmamba-solver, conda-build, conda-index,
  conda-forge-ci-setup, conda-forge-pinning, networkx 2.4.*, rattler-build-conda-compat.

## Prerequisites (Pixi route)

- [Pixi](https://pixi.sh) >= 0.72.2 (the workspace's `requires-pixi` floor; pixi 0.73+ is pinned in-env)
- Or: Conda/Mamba with conda-build and rattler-build
- For Linux builds on Windows: WSL2 with Ubuntu or Docker Desktop

> **Which env builds recipes?** `rattler-build` (the v1 / `recipe.yaml` engine) lives in
> the **`local-recipes`** env, not the minimal `build` env — the `build` env carries only
> `conda-build` for legacy `meta.yaml`. For everyday recipe builds prefer the purpose-built
> pixi tasks over `test-recipes.py`:
>
> ```bash
> pixi run -e local-recipes recipe-build recipes/<name>          # native rattler-build (fast, no Docker)
> pixi run -e local-recipes recipe-build-docker linux64          # full conda-forge CI fidelity (alma9)
> pixi run -e local-recipes recipe-build-cross recipes/<name> osx-arm64   # cross-platform .conda artifact
> ```
>
> `test-recipes.py` (see [Recipe testing and builds](../how-to/recipe-testing-and-builds.md)) remains available for batch/random sweeps and for `meta.yaml`
> builds via the `build` env. See also the authoritative `conda-forge-expert` skill
> (`.claude/skills/conda-forge-expert/`) whose recipe lifecycle loop drives these tasks.

## Fast path on Windows (recommended)

1. Open "Developer Command Prompt for VS" or a PowerShell/cmd with script execution allowed.
2. From the repo root, select a variant (optional):

```
SET CONFIG=win64
```

3. Run the Windows build runner:

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

## Cross-platform builds

Use the dispatcher to select the correct backend for your platform:

```
python build-locally.py win64
# or interactively filter/select
python build-locally.py --filter win*
```

- On Windows, this delegates to `.scripts\run_win_build.bat`.
- On Linux/macOS, it invokes the corresponding `.scripts/run_docker_build.sh` or `.scripts/run_osx_build.sh` (if present from conda-smithy).

## Installation (Pixi / clone)

```bash
# Clone the repository
git clone https://github.com/rxm7706/local-recipes.git
cd local-recipes

# Install the build environment with Pixi
pixi install -e build

# Verify tools are available
pixi run -e build python test-recipes.py --check
```

## Your first build

```bash
# Build a specific recipe on your current platform
pixi run -e build python test-recipes.py --recipe <package-name>

# Dry-run to see what would be built
pixi run -e build python test-recipes.py --recipe <package-name> --dry-run

# Build on all available platforms
pixi run -e build python test-recipes.py --recipe <package-name> --all
```

## Next steps

- [Recipe testing and builds](../how-to/recipe-testing-and-builds.md) — targeted builds, `test-recipes.py`, platform matrix
- [Pixi tasks](../how-to/pixi-tasks.md) — full `pixi.toml` task surface for recipe tooling and atlas
- [Developer guide (reference)](../reference/developer-guide.md) — configuration reference, recipe format examples

See [`docs/MAP.md`](../MAP.md) for the full documentation map.
