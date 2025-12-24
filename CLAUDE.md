# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A local conda-forge style staged-recipes workspace for building and testing Conda/Rattler Build recipes. This repo mirrors the workflow of [conda-forge/staged-recipes](https://github.com/conda-forge/staged-recipes) for local development before submission.

**Critical Rule**: Do not mix `meta.yaml` and `recipe.yaml` formats in the same build run. The tooling will reject mixed-mode runs.

## Build Commands

### Cross-Platform Dispatcher (Primary)
```bash
python build-locally.py                 # Interactive platform selection
python build-locally.py win64           # Windows
python build-locally.py linux64         # Linux (requires Docker)
python build-locally.py osx64           # macOS
python build-locally.py --filter win*   # Filter by pattern
```

### Platform-Specific Scripts
```batch
REM Windows native (alternative to build-locally.py)
SET CONFIG=win64
CALL .scripts\run_win_build.bat
```

### Pixi Environments
```bash
pixi run -e win build-win              # Windows native
pixi run -e osx build-osx              # macOS native
pixi run -e linux build-linux          # Linux via Docker
pixi run -e conda-smithy lint          # Lint all recipes
pixi run -e grayskull pypi <pkg>       # Generate recipe from PyPI
pixi run -e grayskull cran <pkg>       # Generate recipe from CRAN
```

### Single Recipe Builds
```bash
# Rattler Build (recipe.yaml)
rattler-build build recipes/<name> --target-platform win-64 -c conda-forge --variant-config .ci_support/win64.yaml

# conda-build (meta.yaml)
conda-build recipes/<name>

# Test existing artifact
conda-build --test <artifact.tar.bz2>
```

### Linting (Mandatory Before Submission)
```bash
conda-smithy recipe-lint recipes/<name>
conda-smithy recipe-lint --conda-forge recipes/*
```

## Architecture

### Build Orchestration
- **`.ci_support/build_all.py`**: Detects recipe format, constructs dependency graphs via networkx, enforces topological build order. For `meta.yaml` uses conda-build; for `recipe.yaml` shells out to `rattler-build`.
- **`build-locally.py`**: Cross-platform dispatcher selecting Windows/Linux/macOS backends.
- **`.scripts/run_win_build.bat`**: Windows provisioning via micromamba, activates Miniforge, runs `run_conda_forge_build_setup`, removes recipes present in main branch, builds via `build_all.py`.

### Configuration Hierarchy
- **`conda_build_config.yaml`** (root): Global pinning and variants
- **`.ci_support/<platform>.yaml`**: Platform-specific variants (e.g., `win64.yaml`)
- **`recipes/<pkg>/conda_build_config.yaml`**: Recipe-specific overrides
- **`environment.yaml`**: Bootstrap environment for build tooling
- **`pixi.toml`**: Pixi workspace with multiple environments

### Recipe Location
All recipes in `recipes/` - each subfolder contains either `recipe.yaml` (modern Rattler Build) or `meta.yaml` (legacy conda-build).

## Recipe Formats

### Modern Format (recipe.yaml) - Recommended
Uses `schema_version: 1` with `${{ }}` context substitution and `if/then/else` conditionals:
```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/prefix-dev/recipe-format/main/schema.json
schema_version: 1

context:
  name: my-package
  version: "1.0.0"

package:
  name: ${{ name }}
  version: ${{ version }}

build:
  noarch: python
  script: ${{ PYTHON }} -m pip install . -vv --no-deps --no-build-isolation

requirements:
  host:
    - python ${{ python_min }}.*
    - pip
    - hatchling
  run:
    - python >=${{ python_min }}

tests:
  - python:
      imports:
        - my_package
      pip_check: true
```

### Legacy Format (meta.yaml)
Uses Jinja2 `{{ }}` syntax with `# [selector]` comments:
```yaml
{% set name = "my-package" %}
{% set version = "1.0.0" %}

package:
  name: {{ name|lower }}
  version: {{ version }}

build:
  noarch: python
  script: {{ PYTHON }} -m pip install . -vv --no-deps --no-build-isolation

requirements:
  host:
    - python {{ python_min }}
    - pip
  run:
    - python >={{ python_min }}

test:
  imports:
    - my_package
  commands:
    - pip check
  requires:
    - pip
```

## CFEP-25 Compliance (Required for noarch: python)

All `noarch: python` packages MUST use the `python_min` variable:
```yaml
# meta.yaml
requirements:
  host:
    - python {{ python_min }}
  run:
    - python >={{ python_min }}

# recipe.yaml
requirements:
  host:
    - python ${{ python_min }}.*
  run:
    - python >=${{ python_min }}
```

Override in recipe's `conda_build_config.yaml` if package requires newer minimum:
```yaml
python_min:
  - "3.10"
```

## Key Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `CONFIG` | Platform/variant key | `win64`, `linux64`, `osx64` |
| `CONDA_BLD_PATH` | Artifact output directory | `C:\bld` (Windows) |
| `MINIFORGE_HOME` | Base conda environment | `%USERPROFILE%\Miniforge3` |
| `CI` | CI environment indicator | `azure` in CI |

## Pre-Submission Checklist

Before submitting to conda-forge/staged-recipes:

1. **Lint locally (REQUIRED)**: `conda-smithy recipe-lint recipes/<name>`
2. **Build locally (REQUIRED)**: `python build-locally.py`
3. **License**: SPDX identifier with correct case (e.g., `Apache-2.0`, not `APACHE 2.0`)
4. **License file**: `license_file` points to actual file in source
5. **Source**: Use tarball URL with SHA256, not git repository URLs
6. **Dependencies**: All must exist in conda-forge already
7. **Tests**: Include import tests and `pip_check: true` for Python
8. **Comments removed**: No generic instruction comments

## Platform Selectors

### Modern Format (if/then/else)
```yaml
requirements:
  host:
    - if: unix
      then: openssl
    - if: win
      then: openssl-windows
```

### Legacy Format (comment selectors)
```yaml
requirements:
  host:
    - openssl  # [unix]
    - openssl-windows  # [win]
```

Common selectors: `linux`, `osx`, `win`, `unix` (linux+osx), `x86_64`, `aarch64`/`arm64`

## Compilers

```yaml
# meta.yaml
requirements:
  build:
    - {{ compiler('c') }}
    - {{ compiler('cxx') }}
    - {{ compiler('rust') }}

# recipe.yaml
requirements:
  build:
    - ${{ compiler('c') }}
    - ${{ compiler('cxx') }}
```

## Style Guidelines

- Python: flake8 with `max-line-length = 88` (see `setup.cfg`)
- YAML recipes: Include schema header for Rattler Build format
- Use `noarch: python` only for pure-Python packages without compiled extensions or OS-conditional install logic
- Prefer `pin_subpackage(..., exact=True)` for co-versioned multi-output recipes
- Use `run_constraints` for optional extras instead of hard dependencies

## Advanced Patterns (Learned from Real Feedstocks)

### Creating Patches for Source Fixes
When upstream code has bugs or needs modifications:

```bash
# 1. Clone and checkout the exact version
git clone <upstream-repo>
git checkout tags/<version>

# 2. Make your modifications to fix the issue

# 3. Generate the patch
git diff -p > fix-issue.patch

# 4. Move patch to recipe folder and add to meta.yaml/recipe.yaml
```

```yaml
# meta.yaml
source:
  url: https://pypi.io/packages/source/...
  sha256: <hash>
  patches:
    - fix-issue.patch
    - 0001-another-fix.patch

# recipe.yaml
source:
  url: https://pypi.io/packages/source/...
  sha256: <hash>
  patches:
    - fix-issue.patch
```

**Windows tip**: Check line endings in patch files. Use `dos2unix` or editor to ensure Unix-style line breaks.

### Test Skipping Patterns
For tests that fail in CI but pass locally (network, GPU, timing issues):

```yaml
# meta.yaml - Dynamic skip list with Jinja
{% set tests_to_skip = "_not_a_real_test" %}
{% set tests_to_skip = tests_to_skip + " or test_network_call" %}
{% set tests_to_skip = tests_to_skip + " or test_gpu_only" %}  # [cuda_compiler_version == "None"]
{% set tests_to_skip = tests_to_skip + " or test_slow" %}  # [aarch64]

test:
  commands:
    - pytest -k "not ({{ tests_to_skip }})" --ignore=tests/integration
```

Common test markers to exclude: `network`, `slow`, `gpu`, `db`, `clipboard`, `single_cpu`

### Build Number Manipulation for Package Preference
```yaml
# Base build number
{% set build_number = 0 %}

build:
  number: {{ build_number + 200 }}  # [cuda_compiler_version != "None"]
  number: {{ build_number + 100 }}  # [blas_impl == "mkl"]
  number: {{ build_number }}  # Default
```

Higher build numbers are preferred by the solver - use this for CUDA/MKL variants.

### Multi-Output Recipes
For packages producing multiple conda packages (e.g., library + Python bindings):

```yaml
# meta.yaml
outputs:
  - name: libmypackage
    script: build-lib.sh
    requirements:
      build:
        - {{ compiler('c') }}
      run_exports:
        - {{ pin_subpackage('libmypackage', max_pin='x.x') }}

  - name: py-mypackage
    script: build-python.sh
    requirements:
      host:
        - {{ pin_subpackage('libmypackage', exact=True) }}
        - python
      run:
        - {{ pin_subpackage('libmypackage', exact=True) }}
        - python
```

### Cross-Compilation Support
```yaml
requirements:
  build:
    - {{ compiler('c') }}
    - python                                     # [build_platform != target_platform]
    - cross-python_{{ target_platform }}         # [build_platform != target_platform]
  host:
    - python
    - pip
```

### Rust-Python Hybrid Packages (maturin/pyo3)
```yaml
requirements:
  build:
    - {{ compiler('c') }}
    - {{ stdlib('c') }}
    - {{ compiler('rust') }}
    - cargo-bundle-licenses  # For license compliance
  host:
    - python
    - maturin >=1,<2
    - pip

build:
  script:
    - cargo-bundle-licenses --format yaml --output THIRDPARTY.yml
    - {{ PYTHON }} -m pip install . -vv --no-deps --no-build-isolation

about:
  license_file:
    - LICENSE
    - THIRDPARTY.yml
```

### CUDA Builds
```yaml
build:
  skip: true  # [cuda_compiler_version == "None"]
  missing_dso_whitelist:
    - "*/nvcuda.dll"   # [win]
    - "*/libcuda.so*"  # [linux]

requirements:
  build:
    - {{ compiler('cuda') }}
  run:
    - __cuda >={{ cuda_compiler_version_min }}
```

### run_exports for ABI Compatibility
```yaml
# For libraries that other packages link against
build:
  run_exports:
    - {{ pin_subpackage('mylib', max_pin='x.x') }}  # Minor version compat
    - {{ pin_subpackage('mylib', max_pin='x') }}    # Major version only
```

### Ignoring Upstream run_exports
```yaml
# meta.yaml
build:
  ignore_run_exports:
    - libfoo  # Don't propagate libfoo's run_exports
  ignore_run_exports_from:
    - {{ compiler('cuda') }}  # Ignore all exports from CUDA

# recipe.yaml
requirements:
  ignore_run_exports:
    by_name:
      - libfoo
    from_package:
      - ${{ compiler('cuda') }}
```

## Troubleshooting

### Hash Mismatch
Verify source URL and regenerate: `curl -sL <url> | sha256sum`

**Common cause**: Fetching redirect page instead of actual file. Use `-L` flag with curl.

### Missing Dependencies
All dependencies must exist in conda-forge. Submit dependencies first via staged-recipes.

### Windows CMake/MSBuild Issues
MSBuild isn't properly configured in Azure Windows images. Use Ninja or JOM:
```yaml
requirements:
  build:
    - cmake
    - ninja  # or jom
```
Then in build script: `cmake -G"Ninja" ..`

### macOS SDK Issues
Override in `conda_build_config.yaml`:
```yaml
MACOSX_SDK_VERSION:
  - "11.0"
c_stdlib_version:
  - "11.0"
```

### Linux glibc Compatibility
Default: glibc 2.17 (CentOS 7). For newer features:
```yaml
c_stdlib_version:
  - "2.28"  # Requires alma8 images
```

### Exit Code 139 (Segfault in CI)
Linux Kernel 4.11+ vsyscall issue. Fix via grub config or use newer base images.

### OpenGL/libGL Import Errors
Add as Linux host dependency:
```yaml
requirements:
  host:
    - libgl-devel  # [linux]
```

### Qt Platform Plugin Errors
For headless CI testing:
```yaml
test:
  commands:
    - export QT_QPA_PLATFORM=offscreen && python -c "import mypackage"  # [linux]
```

### conda-verify Warnings
Safe to ignore - conda-forge doesn't enforce conda-verify validation.

### Python Version Selectors (py37, py38, etc.)
Use `py==<version>` syntax for Python 3.7+. Old `py37` format no longer works.

### Build Numbers Over 1000
Reset to 0 when updating versions. High numbers are legacy from compiler migrations.

### setuptools_scm Version Detection
Set environment variable if version detection fails:
```yaml
build:
  script_env:
    - SETUPTOOLS_SCM_PRETEND_VERSION={{ version }}
```

### Faster Local Debugging
Use `rattler-build` for faster builds with modern recipes:
```bash
rattler-build build recipes/<name> --render-only  # Check rendering first
rattler-build build recipes/<name> -c conda-forge
```

### CMake Can't Find Python
Match the FindPython module to your setup:
- `FindPython`: `-DPython_EXECUTABLE=${PYTHON}`
- `FindPython3`: `-DPython3_EXECUTABLE=${PYTHON}`

Always include `${CMAKE_ARGS}` (unquoted) for conda-forge optimizations.

## Bot Commands (for PRs in conda-forge)

| Command | Action |
|---------|--------|
| `@conda-forge-admin, please rerender` | Regenerate CI configuration |
| `@conda-forge-admin, please lint` | Run recipe linting |
| `@conda-forge-admin, please restart ci` | Restart failed CI jobs |

## Review Teams

Request review by mentioning in PR comments:
- Python: `@conda-forge/help-python`
- C/C++: `@conda-forge/help-c-cpp`
- Rust: `@conda-forge/help-rust`
- R: `@conda-forge/help-r`
- Node.js: `@conda-forge/help-nodejs`
- Other: `@conda-forge/staged-recipes`

## References

- [conda-forge Documentation](https://conda-forge.org/docs/)
- [staged-recipes Repository](https://github.com/conda-forge/staged-recipes)
- [rattler-build Documentation](https://rattler.build/latest/)
- [pixi Documentation](https://pixi.sh/latest/)
- [CFEP-25: python_min](https://github.com/conda-forge/cfep/blob/main/cfep-25.md)
- [recipe-format Schema](https://github.com/prefix-dev/recipe-format)