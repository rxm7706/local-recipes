---
sources:
  - test-recipes.py
  - build-locally.py
  - .ci_support/build_all.py
  - .scripts/run_win_build.bat
  - .claude/scripts/conda-forge-expert/native-build.sh
  - scripts/platform-ci-local.sh
  - .github/workflows/platform-ci.yml
  - .github/workflows/pyforge-station-tests.yml
verified: 2026-11-21
---

# Recipe testing and builds

Task-oriented instructions for building and testing individual recipes locally.

For first-time environment setup, see [Getting started](../tutorials/getting-started.md).

> **Install:** everyday PyForge work uses `pixi install -e pyforge-foundry-full` (laptop SBOM). Recipe builds need the factory env too: `pixi install -e local-recipes` (~10 GB). See [Getting started](../tutorials/getting-started.md).
>
> **Everyday rattler-build route:** prefer `pixi run -e local-recipes recipe-build recipes/<name>` (native, fast, host platform only). The smaller `build` env carries both conda-build and rattler-build (0.76.1 in the lock on 2026-11-17) and is what `test-recipes.py` runs in; `local-recipes` adds the recipe-factory tasks. Never mix `meta.yaml` and `recipe.yaml` recipes in one build run: `.ci_support/build_all.py` rejects it.

> **Mason-backed route** (mason Story 16.2): same native rattler-build,
> invoked through the `mason` CLI's `recipe build` verb instead of the bare `local-recipes`
> task. `mason` still wraps `conda-forge-expert` by subprocess underneath (it adds no recipe
> judgment of its own); this is one real estate caller wired to prove the `pyforge-mason`
> `recipe` verb family is exercised in CI, not just built.
>
> ```bash
> pixi run -e pyforge-mason mason recipe build recipes/<name>
> ```
>
> CI wiring: `.github/workflows/pyforge-station-tests.yml`'s `mason-live-test` job runs
> `pixi run -e pyforge-mason pyforge-mason-recipe-build-smoke` after the live-tree half of mason's
> suite (steward Story 124.2 moved it there from `mason-test`).

## Building a single recipe (targeted workflow)

- For `recipe.yaml` (Rattler Build):
  1. Create/activate a tooling env that includes the pins/variants you intend to use. If you already ran the Windows script from [Getting started](../tutorials/getting-started.md), you have compatibility shims available in that environment. Otherwise, for a standalone env:

  ```
  conda create -n rb -c conda-forge python=3.12 rattler-build rattler-build-conda-compat conda-forge-pinning conda conda-build conda-libmamba-solver -y
  conda activate rb
  ```

  2. Build the recipe (example for win-64):

  ```
  rattler-build build recipes\py-key-value --target-platform win-64 -c conda-forge --variant-config .ci_support\win64.yaml
  ```

- For `meta.yaml` (conda-build):

  ```
  conda-build recipes\<recipe-name>
  ```

  You may also let `.ci_support\build_all.py` compute the build order and dependencies for multiple conda-build recipes.

## How tests work here

- Rattler Build (`recipe.yaml`): tests are defined in the top-level `tests:` list.
  - Example: `recipes\py-key-value\recipe.yaml` includes Python import checks and optional script checks.
- conda-build (`meta.yaml`): tests are under `test:` with `imports`, `commands`, `requires`, etc.
- Tests run automatically during the build step. If a build completes successfully, these functional smoke tests have already executed.

Running just tests on an existing artifact:

- conda-build:

  ```
  conda-build --test <path-to-artifact.tar.bz2 or .conda>
  ```

- Rattler Build: re-run `rattler-build build` for that recipe (standalone test invocation differs by version; the common local workflow is to rebuild).

## Direct recipe testing (`test-recipes.py`)

For testing individual recipes without the full CI workflow (which removes recipes in main), use `test-recipes.py`:

```bash
# Install with pixi (the build env carries both rattler-build and conda-build)
pixi install -e build

# Check available build tools and platforms
pixi run -e build python test-recipes.py --check

# Test a specific recipe
pixi run -e build python test-recipes.py --recipe pandas

# Test on all available platforms
pixi run -e build python test-recipes.py --recipe pandas --all

# Test random recipes (dry-run)
pixi run -e build python test-recipes.py --random 5 --dry-run
```

### Command line options

| Option | Description | Example |
|--------|-------------|---------|
| `--recipe NAME [NAME ...]` | Build one or more named recipes | `--recipe pandas` |
| `--random N` | Build N random recipes | `--random 10` |
| `--list` | List discovered recipes (no build) | `--list` |
| `--all` | Build on all available platforms | `--all` |
| `--platform PLAT [PLAT ...]` | Target platforms (`win-64`, `linux-64`, `osx-64`, `osx-arm64`); default is the host | `--platform win-64` |
| `--type TYPE` | Only `meta.yaml` or only `recipe.yaml` recipes | `--type recipe.yaml` |
| `--dry-run` | Show what would be built | `--dry-run` |
| `--check` | Check tool availability | `--check` |
| `--filter PATTERN` | Filter recipes by pattern | `--filter "py*"` |
| `--stop-on-error` | Stop at first failure | `--stop-on-error` |

### Examples

```bash
# Check available build tools
pixi run -e build python test-recipes.py --check

# Build 5 random recipe.yaml recipes
pixi run -e build python test-recipes.py --random 5 --type recipe.yaml

# Build pandas on every platform this host can reach
pixi run -e build python test-recipes.py --recipe pandas --all

# Dry-run 100 random recipes on all platforms
pixi run -e build python test-recipes.py --random 100 --all --dry-run

# Build all recipes matching pattern
pixi run -e build python test-recipes.py --filter "aws-*" --platform linux-64
```

### Platform support

| Platform | Build Method |
|----------|--------------|
| win-64 | Native (Windows host) |
| linux-64 | WSL or Docker |
| osx-64 | Native (macOS Intel) |
| osx-arm64 | Native (macOS Apple Silicon) |

:::note
macOS builds require a Mac, and `test-recipes.py` warns when `OSX_SDK_DIR` is unset. Linux builds from Windows prefer WSL for `recipe.yaml` (rattler-build) and Docker for `meta.yaml` (conda-build).
:::

### Platform build methods

| Platform | Build Method | Requirements |
|----------|--------------|--------------|
| **win-64** | Native | Windows + pixi/conda |
| **linux-64** | WSL (preferred) | WSL2 with pixi installed |
| **linux-64** | Docker (fallback) | Docker Desktop |
| **osx-64** | Native only | macOS Intel hardware |
| **osx-arm64** | Native only | macOS Apple Silicon |

### WSL setup for Linux builds

```bash
# Install pixi in WSL
wsl bash -c "curl -fsSL https://pixi.sh/install.sh | bash"

# Install the local-recipes environment in WSL (the recipe-factory tasks live here)
wsl bash -c "cd /mnt/c/path/to/local-recipes && ~/.pixi/bin/pixi install -e pyforge-foundry-full && ~/.pixi/bin/pixi install -e local-recipes"

# Verify rattler-build works
wsl bash -c "cd /mnt/c/path/to/local-recipes && ~/.pixi/bin/pixi run -e local-recipes rattler-build --version"
```

`conda-build` has compatibility issues when the project is on a Windows filesystem accessed via WSL. For `meta.yaml` recipes on Linux, use Docker instead.

## Platform CI locally (zero Actions minutes)

`pixi run -e pyforge-guild platform-ci-local` replays `.github/workflows/platform-ci.yml`
on your machine: the `checks` and `test` jobs step for step (`manage.py check`, Ruff, mypy,
the policy suite, sqlmigrate extraction, then the full pytest suite), the three image builds, the
`container` job's runtime smokes against the built image, and `golden-path-promotion`
plus the deploy-side verifier. It starts its own PostgreSQL 17 (+pgvector) and Redis 7
from the `platform-dev` env on 15432/16379 and tears them down on exit.

```bash
pixi run -e pyforge-guild platform-ci-local                         # all four stages, docker
pixi run -e pyforge-guild platform-ci-local -- --test               # only the checks and test jobs
pixi run -e pyforge-guild platform-ci-local -- --images --container --engine podman
```

Run it before pushing any `src/platform`, Containerfile or `pixi.toml` change: Platform CI
triggers on those paths and builds three images per run. The four stage flags are `--test`,
`--images`, `--container` and `--promotion`; with none, all four run. Docker or podman must
be on the host. Images are built from a git-exported context (`git ls-files`, minus
`recipes/`), because a raw `docker build .` from a developer checkout walks the whole
`.pixi/` tree. Logs land under `${TMPDIR:-/tmp}/platform-ci-local/`.

## Environment variables

Commonly used variables (some set by our scripts):

- `CONFIG` — Platform/variant key, e.g., `win64`. Used by `build-locally.py` and to select `.ci_support\<CONFIG>.yaml`.
- `CONDA_BLD_PATH` — Artifact workspace directory (defaults to `C:\bld` on Windows if unset in the script).
- `MINIFORGE_HOME` — Location of the base conda environment. `.scripts\run_win_build.bat` defaults it to `%USERPROFILE%\Miniforge3`; `build-locally.py` sets it to `miniforge3` beside the script when unset.
- `CI` — May be set to `azure` in CI environments; used for certain logging/behavior in scripts.
- `UPLOAD_PACKAGES`, `IS_PR_BUILD` — Set by `build-locally.py` on every run (`False` and `True`).
- `BUILD_WITH_CONDA_DEBUG`, `BUILD_OUTPUT_ID` — Set by `build-locally.py` under `--debug` (and `--output-id`).
- `CONDA_FORGE_DOCKER_RUN_ARGS` — Set by `build-locally.py` on a macOS host with a Linux config, to move the rattler cache to a writable location.
- `OSX_SDK_DIR` — macOS SDK location; `build-locally.py` defaults it to `SDKs` beside the script.
- `MACOSX_DEPLOYMENT_TARGET`, `MACOSX_SDK_VERSION` — Read from each recipe's `conda_build_config.yaml` by `.ci_support\build_all.py`, which writes the highest value it finds into the variant config.
- `DEFAULT_LINUX_VERSION` — Set to `cos7` by `.ci_support\build_all.py` when a recipe asks for the CentOS 7 sysroot.

## Useful scripts and entry points

- `build-locally.py` — Cross-platform entry; chooses Windows/Linux/macOS backend based on host OS and `CONFIG`/`--filter`. It refuses to run from `main`; the pixi wrapper is `pixi run -e local-recipes recipe-build-docker <config>`.
- `test-recipes.py` — Builds named, filtered or random recipes on the platforms the host can reach.
- `.scripts\run_win_build.bat` — Windows provision + build runner.
- `.ci_support\build_all.py` — Orchestrates builds; determines if the repo contains `meta.yaml` or `recipe.yaml` recipes (mixing is rejected), constructs dependency graphs (conda-build), and shells out to Rattler Build as needed.

## Best practices (testing)

1. **Local first** — Use `test-recipes.py` before pushing
2. **Dry-run** — Always preview with `--dry-run`
3. **Incremental** — Test one recipe at a time
4. **All platforms** — Use `--all` before submitting to conda-forge
