# Conda-Forge Expert Skills Documentation

[![Test All Platforms](https://github.com/rxm7706/local-recipes/actions/workflows/test-all.yml/badge.svg)](https://github.com/rxm7706/local-recipes/actions/workflows/test-all.yml)
[![Test Linux](https://github.com/rxm7706/local-recipes/actions/workflows/test-linux.yml/badge.svg)](https://github.com/rxm7706/local-recipes/actions/workflows/test-linux.yml)
[![Test Windows](https://github.com/rxm7706/local-recipes/actions/workflows/test-windows.yml/badge.svg)](https://github.com/rxm7706/local-recipes/actions/workflows/test-windows.yml)
[![Test macOS](https://github.com/rxm7706/local-recipes/actions/workflows/test-macos.yml/badge.svg)](https://github.com/rxm7706/local-recipes/actions/workflows/test-macos.yml)

> Comprehensive guide for building, testing, and maintaining conda-forge recipes locally and via CI/CD.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Local Testing](#local-testing)
4. [GitHub Actions Workflows](#github-actions-workflows)
5. [Recipe Formats](#recipe-formats)
6. [Platform Support](#platform-support)
7. [Configuration Reference](#configuration-reference)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)

---

## Overview

This repository provides a complete local development environment for conda-forge recipes, including:

- **Local Testing Script** (`test-recipes.py`) - Test recipes on Windows, Linux (via WSL/Docker), without submitting to conda-forge CI
- **GitHub Actions Workflows** - On-demand CI testing for all platforms (Linux, Windows, macOS)
- **Multi-format Support** - Both `meta.yaml` (conda-build) and `recipe.yaml` (rattler-build) formats
- **Configurable Builds** - Python versions, CUDA support, macOS SDK versions, Linux base images

### Architecture

```
local-recipes/
├── recipes/                    # Recipe directories
│   └── <package-name>/
│       ├── meta.yaml          # Legacy format (conda-build)
│       └── recipe.yaml        # Modern format (rattler-build)
├── .ci_support/               # Build variant configurations
│   ├── linux64.yaml
│   ├── win64.yaml
│   ├── osx64.yaml
│   └── osxarm64.yaml
├── .github/workflows/         # GitHub Actions workflows
│   ├── test-all.yml           # Orchestrates all platforms
│   ├── test-linux.yml         # Linux builds (Docker)
│   ├── test-windows.yml       # Windows builds (native)
│   └── test-macos.yml         # macOS builds (native)
├── test-recipes.py            # Local testing script
├── conda_build_config.yaml    # Global pinning configuration
└── pixi.toml                  # Pixi environment configuration
```

---

## Quick Start

### Prerequisites

- [Pixi](https://pixi.sh) >= 0.59.0 (recommended)
- Or: Conda/Mamba with conda-build and rattler-build
- For Linux builds on Windows: WSL2 with Ubuntu or Docker Desktop

### Installation

```bash
# Clone the repository
git clone https://github.com/rxm7706/local-recipes.git
cd local-recipes

# Install the build environment with Pixi
pixi install -e build

# Verify tools are available
pixi run -e build python test-recipes.py --check
```

### Your First Build

```bash
# Build a specific recipe on your current platform
pixi run -e build python test-recipes.py --recipe <package-name>

# Dry-run to see what would be built
pixi run -e build python test-recipes.py --recipe <package-name> --dry-run

# Build on all available platforms
pixi run -e build python test-recipes.py --recipe <package-name> --all
```

---

## Local Testing

### test-recipes.py Reference

The `test-recipes.py` script provides direct recipe testing without the CI workflow that removes recipes already in the main branch.

#### Command Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `--recipe NAME` | Build a specific recipe | `--recipe pandas` |
| `--random N` | Build N random recipes | `--random 10` |
| `--all` | Build on all available platforms | `--all` |
| `--platform PLAT` | Target specific platform | `--platform win-64` |
| `--type TYPE` | Filter by recipe type | `--type recipe.yaml` |
| `--dry-run` | Show what would be built | `--dry-run` |
| `--check` | Check tool availability | `--check` |
| `--filter PATTERN` | Filter recipes by pattern | `--filter "py*"` |
| `--stop-on-error` | Stop at first failure | `--stop-on-error` |

#### Examples

```bash
# Check available build tools
pixi run -e build python test-recipes.py --check

# Build 5 random recipe.yaml recipes
pixi run -e build python test-recipes.py --random 5 --type recipe.yaml

# Build pandas on Windows and Linux
pixi run -e build python test-recipes.py --recipe pandas --all

# Dry-run 100 random recipes on all platforms
pixi run -e build python test-recipes.py --random 100 --all --dry-run

# Build all recipes matching pattern
pixi run -e build python test-recipes.py --filter "aws-*" --platform linux-64
```

### Platform Build Methods

| Platform | Build Method | Requirements |
|----------|--------------|--------------|
| **win-64** | Native | Windows + pixi/conda |
| **linux-64** | WSL (preferred) | WSL2 with pixi installed |
| **linux-64** | Docker (fallback) | Docker Desktop |
| **osx-64** | Native only | macOS Intel hardware |
| **osx-arm64** | Native only | macOS Apple Silicon |

### WSL Setup for Linux Builds

```bash
# Install pixi in WSL
wsl bash -c "curl -fsSL https://pixi.sh/install.sh | bash"

# Install the build environment in WSL
wsl bash -c "cd /mnt/c/path/to/local-recipes && ~/.pixi/bin/pixi install -e build"

# Verify rattler-build works
wsl bash -c "cd /mnt/c/path/to/local-recipes && ~/.pixi/bin/pixi run -e build rattler-build --version"
```

**Note:** `conda-build` has compatibility issues when the project is on a Windows filesystem accessed via WSL. For `meta.yaml` recipes on Linux, use Docker instead.

---

## GitHub Actions Workflows

All workflows run **on-demand only** to preserve GitHub Actions quota. No automatic triggers on push/PR.

### Available Workflows

| Workflow | File | Description |
|----------|------|-------------|
| **Test All** | `test-all.yml` | Orchestrates builds on all platforms |
| **Test Linux** | `test-linux.yml` | Linux builds with Docker |
| **Test Windows** | `test-windows.yml` | Native Windows builds |
| **Test macOS** | `test-macos.yml` | Native macOS builds (x86_64 + ARM64) |

### Running Workflows

#### Via GitHub UI

1. Navigate to **Actions** tab
2. Select the workflow (e.g., "Test All Platforms")
3. Click **"Run workflow"** button
4. Configure options and click **"Run workflow"**

#### Via GitHub CLI

```bash
# Install GitHub CLI if needed
# https://cli.github.com/

# Test all platforms with specific recipes
gh workflow run test-all.yml -f recipes="pandas,numpy" -f platforms="all"

# Test Linux only with CUDA
gh workflow run test-linux.yml -f recipes="pytorch" -f cuda_version="12.6"

# Test macOS with custom deployment target
gh workflow run test-macos.yml -f recipes="scipy" -f osx_arm64_deployment_target="12.0"

# Test Windows with Python 3.11
gh workflow run test-windows.yml -f recipes="requests" -f python_version="3.11"

# Test all recipes (first 20) on Linux
gh workflow run test-linux.yml -f recipes="all" -f architecture="linux-64"
```

### Workflow Inputs Reference

#### test-all.yml

| Input | Options | Default | Description |
|-------|---------|---------|-------------|
| `recipes` | comma-separated or "all" | (auto-detect) | Recipes to build |
| `platforms` | all, linux, windows, macos, combinations | all | Platforms to build |
| `linux_version` | alma9, alma8, cos7 | alma9 | Linux base image |
| `macos_deployment_target` | default, 10.13-14.0 | default | macOS minimum version |
| `cuda_version` | (empty), 12.6, 12.0, 11.8 | (empty) | CUDA version |
| `python_version` | 3.10, 3.11, 3.12, 3.13 | 3.12 | Python version |

#### test-linux.yml

| Input | Options | Default | Description |
|-------|---------|---------|-------------|
| `recipes` | comma-separated or "all" | (auto-detect) | Recipes to build |
| `linux_version` | alma9, alma8, cos7 | alma9 | Linux base image |
| `architecture` | linux-64, linux-aarch64, both | linux-64 | Target architecture |
| `cuda_version` | (empty), 12.6, 12.0, 11.8 | (empty) | CUDA version |
| `python_version` | 3.10-3.13 | 3.12 | Python version |

#### test-windows.yml

| Input | Options | Default | Description |
|-------|---------|---------|-------------|
| `recipes` | comma-separated or "all" | (auto-detect) | Recipes to build |
| `python_version` | 3.10-3.13 | 3.12 | Python version |
| `vc_version` | 14 | 14 | Visual C++ version |

#### test-macos.yml

| Input | Options | Default | Description |
|-------|---------|---------|-------------|
| `recipes` | comma-separated or "all" | (auto-detect) | Recipes to build |
| `osx_64_deployment_target` | 10.13-14.0 | 10.13 | x86_64 minimum macOS |
| `osx_arm64_deployment_target` | 11.0-14.0 | 11.0 | ARM64 minimum macOS |
| `osx_64_sdk_version` | (empty) or version | (empty) | Custom SDK for x86_64 |
| `osx_arm64_sdk_version` | (empty) or version | (empty) | Custom SDK for ARM64 |
| `platforms` | both, osx-64, osx-arm64 | both | Target platform(s) |

### Build Artifacts

Successful builds upload packages as workflow artifacts:

- Retention: 7 days
- Location: Workflow run → Artifacts section
- Naming: `<platform>-<recipe-name>` (e.g., `linux-64-pandas`)

---

## Recipe Formats

### meta.yaml (conda-build)

The traditional conda-forge recipe format using Jinja2 templating.

```yaml
{% set name = "example" %}
{% set version = "1.0.0" %}

package:
  name: {{ name|lower }}
  version: {{ version }}

source:
  url: https://pypi.org/packages/source/{{ name[0] }}/{{ name }}/{{ name }}-{{ version }}.tar.gz
  sha256: abc123...

build:
  number: 0
  noarch: python
  script: {{ PYTHON }} -m pip install . -vv --no-deps --no-build-isolation

requirements:
  host:
    - python {{ python_min }}
    - pip
    - setuptools
  run:
    - python >={{ python_min }}

test:
  imports:
    - example
  commands:
    - pip check
  requires:
    - pip

about:
  home: https://github.com/example/example
  license: MIT
  license_family: MIT
  license_file: LICENSE
  summary: Example package
  dev_url: https://github.com/example/example

extra:
  recipe-maintainers:
    - your-github-username
```

### recipe.yaml (rattler-build)

The modern format with native YAML (no Jinja2).

```yaml
schema_version: 1

context:
  name: example
  version: "1.0.0"

package:
  name: ${{ name|lower }}
  version: ${{ version }}

source:
  url: https://pypi.org/packages/source/${{ name[0] }}/${{ name }}/${{ name }}-${{ version }}.tar.gz
  sha256: abc123...

build:
  number: 0
  noarch: python
  script:
    - python -m pip install . -vv --no-deps --no-build-isolation

requirements:
  host:
    - python ${{ python_min }}
    - pip
    - setuptools
  run:
    - python >=${{ python_min }}

tests:
  - python:
      imports:
        - example
      pip_check: true

about:
  homepage: https://github.com/example/example
  license: MIT
  license_file: LICENSE
  summary: Example package
  repository: https://github.com/example/example

extra:
  recipe-maintainers:
    - your-github-username
```

### Key Differences

| Feature | meta.yaml | recipe.yaml |
|---------|-----------|-------------|
| Templating | Jinja2 (`{{ }}`) | YAML native (`${{ }}`) |
| Build tool | conda-build | rattler-build |
| Test section | `test:` | `tests:` (list) |
| Selectors | `# [linux]` | `if: linux` |
| Speed | Slower | Faster |
| Format | Legacy | Modern (recommended) |

### Converting meta.yaml to recipe.yaml

Use the `conda-recipe-manager` tool:

```bash
# Install
pip install conda-recipe-manager

# Convert
conda-recipe-manager convert recipes/example/meta.yaml
```

---

## Platform Support

### Build Matrix

| Platform | Runner/Method | Docker Image | Architecture |
|----------|--------------|--------------|--------------|
| linux-64 | Docker | `quay.io/condaforge/linux-anvil-x86_64:alma9` | x86_64 |
| linux-aarch64 | Docker + QEMU | `quay.io/condaforge/linux-anvil-aarch64:alma9` | ARM64 |
| linux-64-cuda | Docker | `quay.io/condaforge/linux-anvil-cuda:12.6` | x86_64 + CUDA |
| win-64 | Native | N/A | x86_64 |
| osx-64 | Native | N/A | x86_64 (Intel) |
| osx-arm64 | Native | N/A | ARM64 (Apple Silicon) |

### Linux Base Images

| Image | glibc | Use Case |
|-------|-------|----------|
| `alma9` | 2.34 | Default, modern packages |
| `alma8` | 2.28 | Broader compatibility |
| `cos7` | 2.17 | Maximum compatibility, CUDA |

### macOS Deployment Targets

| Target | Minimum macOS | Notes |
|--------|---------------|-------|
| 10.13 | High Sierra | Default for x86_64 |
| 11.0 | Big Sur | Default for ARM64, minimum for Apple Silicon |
| 12.0 | Monterey | |
| 13.0 | Ventura | |
| 14.0 | Sonoma | |

### CUDA Support

CUDA builds are triggered when:
1. Recipe contains "cuda" in `meta.yaml` or `recipe.yaml`
2. `cuda_version` input is explicitly set

Available CUDA versions: 12.6, 12.0, 11.8

---

## Configuration Reference

### conda_build_config.yaml

Global pinning configuration derived from [conda-forge-pinning](https://github.com/conda-forge/conda-forge-pinning-feedstock).

Key settings:

```yaml
# Python versions
python:
  - 3.10.* *_cpython
  - 3.11.* *_cpython
  - 3.12.* *_cpython
  - 3.13.* *_cp313

python_min:
  - '3.10'  # CFEP-25 minimum

# Compilers
c_compiler_version:
  - 14          # [linux]
  - 19          # [osx]

# macOS targets
MACOSX_DEPLOYMENT_TARGET:
  - 11.0        # [osx and arm64]
  - 10.13       # [osx and x86_64]

# CUDA
cuda_compiler_version:
  - None
  - 12.6        # [linux or win64]
```

### .ci_support/*.yaml

Platform-specific variant configurations:

- `linux64.yaml` - Linux x86_64 settings
- `win64.yaml` - Windows x64 settings
- `osx64.yaml` - macOS x86_64 settings
- `osxarm64.yaml` - macOS ARM64 settings

### pixi.toml Environments

| Environment | Purpose | Features |
|-------------|---------|----------|
| `build` | Build recipes | conda-build, rattler-build |
| `linux` | Linux builds via Docker | Python only |
| `win` | Windows builds | Full build stack |
| `osx` | macOS builds | Full build stack |
| `grayskull` | Generate recipes from PyPI | grayskull |
| `conda-smithy` | Lint recipes | conda-smithy |
| `local-recipes` | Full development | All tools |

---

## Troubleshooting

### Common Issues

#### "rattler-build not found"

```bash
# Ensure you're in the build environment
pixi run -e build rattler-build --version

# Or activate manually
pixi shell -e build
rattler-build --version
```

#### WSL conda-build fails with path errors

This occurs when the project is on a Windows filesystem. Solutions:

1. **Use rattler-build** for `recipe.yaml` recipes (works with WSL)
2. **Use Docker** for `meta.yaml` recipes (more reliable)
3. **Clone to WSL filesystem**: `git clone ... ~/local-recipes`

#### "No recipes to build"

For manual workflow triggers, you must specify recipes:

```bash
gh workflow run test-linux.yml -f recipes="pandas"
```

#### Docker permission denied

```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in, then test
docker run hello-world
```

#### macOS SDK download fails

The workflow falls back to the system SDK. For specific SDK versions:

1. Download from [MacOSX-SDKs](https://github.com/phracker/MacOSX-SDKs)
2. Extract to `~/.sdk/` or specify via `CONDA_BUILD_SYSROOT`

### Build Failures

#### Dependency resolution fails

```bash
# Try with verbose output
conda-build recipe/ -c conda-forge --debug

# Check for conflicts
mamba repoquery depends <package>
```

#### Test phase fails

```bash
# Skip tests temporarily
conda-build recipe/ --no-test

# Run tests separately
conda-build recipe/ --test
```

#### Cross-compilation issues (macOS ARM64 on Intel)

```yaml
# In conda_build_config.yaml
build_platform:
  osx_arm64: osx_64  # Build ARM64 packages on Intel Mac
```

---

## Best Practices

### Recipe Development

1. **Use recipe.yaml** for new recipes (faster, cleaner syntax)
2. **Follow CFEP-25** - use `python_min` variable for Python bounds
3. **Pin dependencies** using conda-forge-pinning values
4. **Include tests** - at minimum `pip check` and imports
5. **Add maintainers** in `extra.recipe-maintainers`

### Testing Strategy

1. **Local first** - Use `test-recipes.py` before pushing
2. **Dry-run** - Always preview with `--dry-run`
3. **Incremental** - Test one recipe at a time
4. **All platforms** - Use `--all` before submitting to conda-forge

### CI/CD Usage

1. **On-demand only** - Workflows don't run automatically
2. **Specify recipes** - Don't use "all" in production
3. **Monitor quotas** - Check GitHub Actions usage
4. **Cache artifacts** - Download and reuse build artifacts

### Version Control

1. **Atomic commits** - One recipe change per commit
2. **Clear messages** - Describe what changed and why
3. **Skip CI** - Use `[skip ci]` for docs-only changes
4. **Branch per recipe** - Isolate work for PRs

---

## Additional Resources

- [conda-forge Documentation](https://conda-forge.org/docs/)
- [rattler-build Documentation](https://prefix-dev.github.io/rattler-build/)
- [conda-build Documentation](https://docs.conda.io/projects/conda-build/)
- [CFEP-25: Minimum Python Version](https://github.com/conda-forge/cfep/blob/main/cfep-25.md)
- [conda-forge-pinning](https://github.com/conda-forge/conda-forge-pinning-feedstock)

---

## Changelog

### 2025-12-24

- Initial documentation
- Added local testing script (`test-recipes.py`)
- Created GitHub Actions workflows for all platforms
- Added WSL support for Linux builds on Windows
- Configured on-demand-only CI to preserve quotas