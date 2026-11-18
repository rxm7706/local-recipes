---
sources:
  - environment.yaml
  - .scripts/run_win_build.bat
  - build-locally.py
  - test-recipes.py
  - scripts/ensure-local-recipes-env.sh
  - .claude/skills/conda-forge-expert/scripts/health_check.py
verified: 2026-11-17
---

# Getting started

Learning-oriented path to a working build environment for this repo. For
task-oriented commands after setup, see [`docs/how-to/`](../how-to/README.md).

## Requirements

- A supported OS (Windows, Linux, or macOS). The Pixi route works on all three (linux-64, osx-arm64 and win-64; there is no Intel macOS platform); the batch-script route below is Windows-only.
- Network access to conda-forge.
- On Windows, a shell that can run batch scripts and allow PowerShell execution for initial provisioning.

The build tools environment will be provisioned automatically by the Windows script using micromamba if it is not already present.

Packages pulled into the bootstrap environment (see `environment.yaml`):

- python 3.14, pixi, conda, conda-libmamba-solver, conda-build, conda-index,
  conda-forge-ci-setup, conda-forge-pinning, networkx, rattler-build-conda-compat.
  `environment.yaml` is exported from `pixi.toml` and carries the exact version floors.

## Prerequisites (Pixi route)

- [Pixi](https://pixi.sh) at or above the workspace's `requires-pixi` floor in `pixi.toml` (0.80.0 on 2026-11-17; the envs carry the same floor)
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

## Fast path on Windows

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

- A `win*` config delegates to `.scripts\run_win_build.bat`.
- A `linux*` config runs `.scripts/run_docker_build.sh`, so it needs Docker.
- An `osx*` config runs `.scripts/run_osx_build.sh` on macOS, and the Docker script on a Linux host.

## Installation (Pixi / clone)

```bash
# Clone the repository
git clone https://github.com/rxm7706/local-recipes.git
cd local-recipes

# Laptop SBOM — Guild stations, detectors, and build/grayskull tooling (fnd:CAP-12)
pixi install -e pyforge-foundry-full

# Recipe factory at scale (~10 GB) — rattler-build tasks, atlas bootstrap, full task surface
pixi install -e local-recipes

# Legacy meta.yaml-only sweeps (minimal; prefer recipe-build in local-recipes for recipe.yaml)
pixi install -e build

# Verify legacy build env tools (optional)
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

## Guild station development (optional)

Contributing to a PyForge Guild station (atlas, doctor, herald, marshal, mason, scribe, steward,
warden) instead of authoring recipes? After `pixi install -e pyforge-foundry-full`, run this
bootstrap sequence once (atlas-heavy steps need the `local-recipes` env installed too):

```bash
pixi run -e pyforge-guild detectors-ci        # the CI-safe detector subset; exit 0 is the merge bar
pixi run -e local-recipes health-check        # checks the git upstream remote, gh auth, Docker, MCP scripts, API reachability
pixi run -e local-recipes bootstrap-data      # one-time atlas refresh; 30-45 min cold, 5-10 min warm
pixi run -e local-recipes verify-env          # confirms the shell is in the local-recipes env and rattler-build answers
pixi run -e pyforge-guild bmad-groundtruth    # live factory facts as JSON
```

See [Pixi tasks](../how-to/pixi-tasks.md) for the full task surface, including `bmad-drift-check`
and the maintenance/infrastructure task set.

## Next steps

- [Recipe testing and builds](../how-to/recipe-testing-and-builds.md) — targeted builds, `test-recipes.py`, platform matrix
- [Pixi tasks](../how-to/pixi-tasks.md) — full `pixi.toml` task surface for recipe tooling and atlas
- [Developer guide (reference)](../reference/developer-guide.md) — configuration reference, recipe format examples

See [`docs/MAP.md`](../MAP.md) for the full documentation map.
