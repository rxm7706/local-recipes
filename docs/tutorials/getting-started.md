---
sources:
  - environment.yaml
  - .scripts/run_win_build.bat
  - build-locally.py
  - test-recipes.py
  - scripts/ensure-local-recipes-env.sh
  - .claude/skills/conda-forge-expert/scripts/health_check.py
  - .claude/scripts/conda-forge-expert/native-build.sh
verified: 2026-11-18
---

# Getting started

Clone this repository, install its pixi environments, and build one recipe on your own machine. By the end you have a working build environment and know which environment each kind of work runs in.

## What You'll Learn

- Which pixi environment carries which build engine
- How to install the environments from a fresh clone
- How to build one recipe natively, and how to dry-run a build first
- How to build for another platform, including the Windows batch route
- How to bootstrap a checkout for Guild station development

:::note[Prerequisites]
- A supported OS: Windows, Linux or macOS. The pixi route works on linux-64, osx-arm64 and win-64; there is no Intel macOS platform.
- [Pixi](https://pixi.sh) at or above the workspace's `requires-pixi` floor in `pixi.toml` (0.80.0 on 2026-11-17; the envs carry the same floor). Or: Conda/Mamba with conda-build and rattler-build.
- Network access to conda-forge.
- For Linux builds on Windows: WSL2 with Ubuntu, or Docker Desktop.
- On Windows, for the batch-script route: a shell that can run batch scripts and allows PowerShell execution for initial provisioning.
:::

:::tip[Quick Path]
```bash
git clone https://github.com/rxm7706/local-recipes.git
cd local-recipes
pixi install -e local-recipes
pixi run -e local-recipes recipe-build recipes/<name>
```
:::

## Understanding the build environments

`rattler-build` (the v1 / `recipe.yaml` engine) lives in the `local-recipes` env, not the minimal `build` env. The `build` env carries only `conda-build`, for legacy `meta.yaml`.

| Environment | What it carries | Use it for |
| --- | --- | --- |
| `local-recipes` | The recipe factory (about 10 GB): rattler-build tasks, atlas bootstrap, the full task surface | Everyday `recipe.yaml` builds |
| `build` | `conda-build` only | Legacy `meta.yaml` sweeps with `test-recipes.py` |
| `pyforge-foundry-full` | Guild stations, detectors, and build/grayskull tooling (the laptop SBOM, fnd:CAP-12) | Station development on a laptop |
| `pyforge-guild` | The station session default | Detectors and Guild tasks |

The Windows batch route does not use pixi. It provisions its own build tools environment with micromamba if one is not already present, from `environment.yaml`: python 3.14, pixi, conda, conda-libmamba-solver, conda-build, conda-index, conda-forge-ci-setup, conda-forge-pinning, networkx and rattler-build-conda-compat. `environment.yaml` is exported from `pixi.toml` and carries the exact version floors.

## Installation

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

Install only the environments you need. A recipe author needs `local-recipes`; `build` is for `meta.yaml` recipes.

## Step 1: Build your first recipe

For everyday recipe builds, use the purpose-built pixi tasks:

```bash
pixi run -e local-recipes recipe-build recipes/<name>          # native rattler-build (fast, no Docker)
pixi run -e local-recipes recipe-build-docker linux64          # full conda-forge CI fidelity (alma9)
pixi run -e local-recipes recipe-build-cross recipes/<name> osx-arm64   # cross-platform .conda artifact
```

The native build writes its packages under `build_artifacts/<config>/` at the repository root.

`test-recipes.py` remains available for batch and random sweeps, and for `meta.yaml` builds through the `build` env:

```bash
# Build a specific recipe on your current platform
pixi run -e build python test-recipes.py --recipe <package-name>

# Dry-run to see what would be built
pixi run -e build python test-recipes.py --recipe <package-name> --dry-run

# Build on all available platforms
pixi run -e build python test-recipes.py --recipe <package-name> --all
```

[Recipe testing and builds](../how-to/recipe-testing-and-builds.md) covers targeted builds and the platform matrix.

:::caution
Never mix `meta.yaml` and `recipe.yaml` recipes in one build run; the tooling rejects it.
:::

## Step 2: Build for another platform

The dispatcher selects the backend for the config you name:

```
python build-locally.py win64
# or interactively filter/select
python build-locally.py --filter win*
```

- A `win*` config delegates to `.scripts\run_win_build.bat`.
- A `linux*` config runs `.scripts/run_docker_build.sh`, so it needs Docker.
- An `osx*` config runs `.scripts/run_osx_build.sh` on macOS, and the Docker script on a Linux host.

On Windows you can also run the batch runner directly. Open "Developer Command Prompt for VS", or a PowerShell or cmd with script execution allowed, and from the repo root select a variant (optional) and run it:

```
SET CONFIG=win64
CALL .scripts\run_win_build.bat
```

The runner does six things:

1. Provisions a Miniforge environment into `%MINIFORGE_HOME%` (defaults to `%USERPROFILE%\Miniforge3`) using micromamba.
2. Activates it, and sets strict channel priority and the libmamba solver.
3. Runs `run_conda_forge_build_setup` to configure conda-forge settings.
4. Removes recipes also present in the `main` branch, so only the changed and new local recipes build.
5. Builds all recipes found in `recipes\` through `.ci_support\build_all.py`.
6. Indexes `%CONDA_BLD_PATH%` for local artifact resolution.

Artifacts land under `%CONDA_BLD_PATH%` (default `C:\bld`).

## Step 3: Set up Guild station development (optional)

Skip this step if you only author recipes. To contribute to a PyForge Guild station (atlas, doctor, herald, marshal, mason, scribe, steward, warden), run this bootstrap sequence once after `pixi install -e pyforge-foundry-full`. The atlas-heavy steps need the `local-recipes` env installed too.

```bash
pixi run -e pyforge-guild detectors-ci        # the CI-safe detector subset; exit 0 is the merge bar
pixi run -e local-recipes health-check        # checks the git upstream remote, gh auth, Docker, MCP scripts, API reachability
pixi run -e local-recipes bootstrap-data      # one-time atlas refresh; 30-45 min cold, 5-10 min warm
pixi run -e local-recipes verify-env          # confirms the shell is in the local-recipes env and rattler-build answers
pixi run -e pyforge-guild bmad-groundtruth    # live factory facts as JSON
```

## What You've Accomplished

You have a clone with its pixi environments installed, and one recipe built on your machine.

```
local-recipes/
├── recipes/<name>/              # the recipe you built
├── build_artifacts/<config>/    # packages from the native build
├── .pixi/envs/                  # the environments you installed
└── ...
```

## Quick Reference

| Command | Environment | Purpose |
| --- | --- | --- |
| `recipe-build recipes/<name>` | `local-recipes` | Native rattler-build for the host platform |
| `recipe-build-docker <config>` | `local-recipes` | Docker build with conda-forge CI fidelity |
| `recipe-build-cross recipes/<name> <target>` | `local-recipes` | Cross-platform `.conda` artifact |
| `python test-recipes.py --check` | `build` | Check available build tools and platforms |
| `python test-recipes.py --recipe <name>` | `build` | Build one recipe; add `--dry-run` or `--all` |
| `python build-locally.py <config>` | none (plain Python) | Dispatch to the Windows, Docker or macOS build script |
| `detectors-ci` | `pyforge-guild` | The CI-safe detector subset |

[Pixi tasks](../how-to/pixi-tasks.md) lists the full task surface, including `bmad-drift-check` and the maintenance and infrastructure tasks.

## Common Questions

### Which env builds recipes?

`local-recipes`. It carries `rattler-build`; the `build` env carries only `conda-build` for legacy `meta.yaml`.

### Do I need Docker?

Only for a `linux*` config through `build-locally.py` or `recipe-build-docker`, and for an `osx*` config on a Linux host. The native `recipe-build` task needs none.

### Where is the configuration reference?

In the [Developer guide](../reference/developer-guide.md), with recipe format examples.

## Getting Help

- [Troubleshooting recipe builds](../how-to/troubleshooting-recipe-builds.md) for a build that fails.
- The `conda-forge-expert` skill (`.claude/skills/conda-forge-expert/`), whose recipe lifecycle loop drives the build tasks and is the authority on recipe work.
- [The documentation map](../MAP.md) for every other page.

:::tip[Key Takeaways]
- Build `recipe.yaml` recipes with `recipe-build` in the `local-recipes` env.
- Keep the `build` env for legacy `meta.yaml` and `test-recipes.py` sweeps.
- Station work starts from `pyforge-foundry-full` and runs its tasks with `-e pyforge-guild`.
:::
