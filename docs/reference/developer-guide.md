# Local-Recipes Developer Guide

[![Test All Platforms](https://github.com/rxm7706/local-recipes/actions/workflows/test-all.yml/badge.svg)](https://github.com/rxm7706/local-recipes/actions/workflows/test-all.yml)
[![Test Linux](https://github.com/rxm7706/local-recipes/actions/workflows/test-linux.yml/badge.svg)](https://github.com/rxm7706/local-recipes/actions/workflows/test-linux.yml)
[![Test Windows](https://github.com/rxm7706/local-recipes/actions/workflows/test-windows.yml/badge.svg)](https://github.com/rxm7706/local-recipes/actions/workflows/test-windows.yml)
[![Test macOS](https://github.com/rxm7706/local-recipes/actions/workflows/test-macos.yml/badge.svg)](https://github.com/rxm7706/local-recipes/actions/workflows/test-macos.yml)

> Configuration reference for conda-forge recipe development in this repo. For onboarding,
> operational how-tos, and CI dispatch, see the Diátaxis map at [`docs/MAP.md`](../MAP.md):
>
> - [Getting started](../tutorials/getting-started.md) — first working environment
> - [Recipe testing and builds](../how-to/recipe-testing-and-builds.md) — local builds and `test-recipes.py`
> - [GitHub Actions recipe CI](../how-to/github-actions-recipe-ci.md) — on-demand workflow dispatch
> - [Troubleshooting recipe builds](../how-to/troubleshooting-recipe-builds.md) — common failure fixes
> - [Pixi tasks](../how-to/pixi-tasks.md) — full `local-recipes` task surface

## Table of Contents

1. [Overview](#overview)
2. [Recipe Formats](#recipe-formats)
3. [Platform Support](#platform-support)
4. [Configuration Reference](#configuration-reference)
5. [Best Practices](#best-practices)

---

## Overview

This repository provides a complete local development environment for conda-forge recipes, including:

- **Local Testing Script** (`test-recipes.py`) — see [Recipe testing and builds](../how-to/recipe-testing-and-builds.md)
- **GitHub Actions Workflows** — see [GitHub Actions recipe CI](../how-to/github-actions-recipe-ci.md)
- **Multi-format Support** — Both `meta.yaml` (conda-build) and `recipe.yaml` (rattler-build) formats
- **Configurable Builds** — Python versions, CUDA support, macOS SDK versions, Linux base images

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
  version: "1.0.0"

package:
  # Literal distribution name — `context.name` and `${{ name | lower }}`
  # interpolation are no longer used (2026 grayskull / conda-forge convention).
  name: example
  version: ${{ version }}

source:
  # Path segments (first letter, distribution name, sdist filename stem) are
  # literal; only `${{ version }}` interpolates.
  url: https://pypi.org/packages/source/e/example/example-${{ version }}.tar.gz
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

---

## Platform Support

### Build Matrix

| Platform | Runner/Method | Docker Image | Architecture |
|----------|--------------|--------------|--------------|
| linux-64 | Docker | `quay.io/condaforge/linux-anvil-x86_64:alma9` | x86_64 |
| linux-aarch64 | Docker + QEMU | `quay.io/condaforge/linux-anvil-aarch64:alma9` | ARM64 |
| linux-64-cuda | Docker | `quay.io/condaforge/linux-anvil-cuda:12.9` | x86_64 + CUDA |
| win-64 | Native | N/A | x86_64 |
| osx-64 | Native | N/A | x86_64 (Intel) |
| osx-arm64 | Native | N/A | ARM64 (Apple Silicon) |

---

## Configuration Reference

### conda_build_config.yaml

Global pinning configuration derived from conda-forge-pinning.

Key settings:

```yaml
# Python versions (zip_keys: python, is_python_min; win-arm64 only supports 3.14+)
python:
  - 3.10.* *_cpython   # [not (win and arm64)]
  - 3.11.* *_cpython   # [not (win and arm64)]
  - 3.12.* *_cpython   # [not (win and arm64)]
  - 3.13.* *_cp313     # [not (win and arm64)]
  - 3.14.* *_cp314     # [win and arm64]

python_min:
  - '3.10'             # CFEP-25 minimum [not (win and arm64)]
  - '3.14'             # [win and arm64]

# Compilers
c_compiler_version:
  - 14          # [linux]
  - 19          # [osx]

# macOS targets — the explicit override is commented out in this repo; the
# conda-forge-pinning defaults apply unless you uncomment it.
#MACOSX_DEPLOYMENT_TARGET:      # [osx]

# CUDA (gated on CF_CUDA_ENABLED=True)
cuda_compiler_version:
  - None
  - 12.9        # [((linux and not ppc64le) or win64) and CF_CUDA_ENABLED]
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
| `build` | Minimal `meta.yaml` builds | python + build (`conda-build` only — **no** rattler-build) |
| `linux` | Linux builds via Docker | linux + python |
| `win` | Windows builds | win + python + build |
| `osx` | macOS builds | osx + python + build |
| `local-recipes` | **Default / full development** | python + build + grayskull + conda-smithy + local-recipes (incl. rattler-build, recipe-build tasks, data/ML/agent stack) |
| `grayskull` | Recipe generation only | python + grayskull (`pypi`, `cran` tasks) |
| `conda-smithy` | Recipe linting only | python + conda-smithy + shellcheck (`lint` task) |
| `vuln-db` | CVE DB / SBOM work | python + vuln-db (AppThreat multi-source; `vdb-refresh`, `build-cf-atlas`, `atlas-phase`) |
| `gcloud` | One-time GCP auth | python + gcloud-sdk (linux/macOS only) |
| `pyforge-warden` | Warden compliance gate | pyforge-warden member (`warden` CLI, `pyforge-warden-test`) |
| `pyforge-atlas` | Kedro atlas pipeline | pyforge-atlas member (kedro/kedro-dagster/kedro-viz; `kedro-test`, `dagster-dryrun`, `viz`) |
| `bmad-ui` | BMad Method UI dashboards | bmad-ui member (**linux-64 only**; `bmad-dashboard-install`, `mybmad`) |

> The full per-library breakdown of every environment lives in
> [`library-llms-full.md`](library-llms-full.md).

---

## Best Practices

### Recipe Development

1. **Use recipe.yaml** for new recipes (faster, cleaner syntax)
2. **Follow CFEP-25** - use `python_min` variable for Python bounds
3. **Pin dependencies** using conda-forge-pinning values
4. **Include tests** - at minimum `pip check` and imports
5. **Add maintainers** in `extra.recipe-maintainers`

For testing strategy and CI usage tips, see [Recipe testing and builds](../how-to/recipe-testing-and-builds.md).

### Version Control

1. **Atomic commits** - One recipe change per commit
2. **Clear messages** - Describe what changed and why
3. **Skip CI** - Use `[skip ci]` for docs-only changes
4. **Branch per recipe** - Isolate work for PRs
