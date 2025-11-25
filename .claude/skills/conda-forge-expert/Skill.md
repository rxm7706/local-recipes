---
name: Conda-Forge Expert
description: A comprehensive guide for generating, auditing, and maintaining conda-forge recipes. Handles legacy (meta.yaml) and modern (recipe.yaml) formats, linting, CI troubleshooting, and feedstock maintenance.
version: 2.3.0
dependencies: conda-build, conda-smithy, grayskull, rattler-build, pixi
---

# Overview

This Skill transforms Claude into a Senior Conda-Forge Maintainer with knowledge derived from analyzing 1,247+ real-world recipes and 10,000+ merged staged-recipes PRs. It assists users in:

- Bootstrapping new recipes for staged-recipes using best practices
- Migrating or maintaining existing feedstocks
- Troubleshooting CI failures (Azure Pipelines, GitHub Actions)
- Formatting recipes according to strict conda-forge linting rules
- Building and testing recipes locally before submission
- Understanding conda-forge infrastructure and automation
- Using modern tools like rattler-build and pixi

**IMPORTANT**: Always run `build-locally.py` to test recipes before submission. This is a mandatory step in the workflow.

Use this skill whenever the user asks to "package" a tool, "fix a build" on conda-forge, or "update a recipe".

# Modern Build Tools

## rattler-build

A fast, standalone Conda package builder written in Rust. No Python or conda-build dependency required.

### Installation

```bash
# Via pixi (recommended)
pixi global install rattler-build

# Via conda/mamba
micromamba install rattler-build -c conda-forge

# Via Homebrew
brew install rattler-build

# Via Arch Linux
pacman -S rattler-build
```

### Key Commands

```bash
# Build a package
rattler-build build -r recipe.yaml

# Build with specific channel
rattler-build build -r recipe.yaml -c conda-forge

# Build for specific platform
rattler-build build -r recipe.yaml --target-platform linux-64

# Test an existing package
rattler-build test --package-file my-package.conda

# Generate recipe from PyPI
rattler-build generate-recipe pypi numpy

# Generate recipe from CRAN
rattler-build generate-recipe cran ggplot2

# Render recipe without building
rattler-build build -r recipe.yaml --render-only

# Publish to prefix.dev
rattler-build publish --to prefix.dev my-package.conda

# Publish to anaconda.org
rattler-build publish --to anaconda.org my-package.conda
```

### System Dependencies

- **macOS**: `install_name_tool` for library path rewriting
- **Linux**: `patchelf` for runtime path modifications
- **All**: `git` for repository checkouts

## pixi

A cross-platform package manager and workflow tool built on the conda ecosystem.

### Installation

```bash
# macOS/Linux
curl -fsSL https://pixi.sh/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm -useb https://pixi.sh/install.ps1 | iex"

# Homebrew
brew install pixi

# Arch Linux
pacman -S pixi
```

### Key Commands

```bash
# Initialize a project
pixi init

# Add dependencies
pixi add numpy pandas

# Add PyPI dependency
pixi add --pypi requests

# Run a task
pixi run test

# Enter environment shell
pixi shell

# Install global tool
pixi global install cowpy

# Lock dependencies
pixi lock
```

### pixi.toml Configuration

```toml
[project]
name = "my-project"
version = "0.1.0"
channels = ["conda-forge"]
platforms = ["linux-64", "osx-arm64", "win-64"]

[dependencies]
python = ">=3.9"
numpy = "*"

[pypi-dependencies]
requests = "*"

[tasks]
test = "pytest -v"
lint = "ruff check ."
build = "rattler-build build -r recipe.yaml"

[feature.test.dependencies]
pytest = "*"

[environments]
test = ["test"]
```

### pixi-build-backends

Build packages directly from source with specialized backends:

```toml
[build-system]
# For Python projects
build-backend = { name = "pixi-build-python", version = "*" }
# For CMake projects
build-backend = { name = "pixi-build-cmake", version = "*" }
# For Rust projects
build-backend = { name = "pixi-build-rust", version = "*" }
# For recipe.yaml files
build-backend = { name = "pixi-build-rattler-build", version = "*" }

channels = ["https://prefix.dev/conda-forge"]
```

# Recipe Generation Tools

## Grayskull (Recommended for Python/R)

Generate recipes automatically from PyPI or CRAN:

```bash
# Python package from PyPI
grayskull pypi <package-name>

# From specific version
grayskull pypi <package-name>==1.2.3

# From GitHub repository
grayskull pypi https://github.com/user/repo

# From local archive
grayskull pypi ./package-1.0.0.tar.gz

# R package from CRAN
grayskull cran <package-name>

# Custom PyPI mirror
grayskull pypi --pypi-mirror-url https://pypi.example.com <package-name>
```

**Note**: Recipes from local archives are not portable as they depend on local file paths.

## Manual Creation

For Rust, Go, C/C++ packages, or when grayskull output needs significant modification, create manually using templates below.

# Recipe Formats

## Format Distribution (from 1,247 recipes analyzed)

- **meta.yaml** (Classic): 84.8% of recipes - Standard conda-build format
- **recipe.yaml** (Modern): 25.6% of recipes - rattler-build format with schema_version: 1

Always ask the user which format they prefer if not specified. Modern recipe.yaml is recommended for new packages.

## A. Classic Format (meta.yaml)

- Uses Jinja2 templating with `{{ }}` syntax
- Structure: package, source, build, requirements, test, about, extra
- Key: Use jinja2 variables for version and sha256

## B. Modern Format (recipe.yaml)

- Uses prefix-dev schema with `schema_version: 1`
- Context variables with `${{ }}` substitution syntax
- Structure: context, package, source, build, requirements, tests, about
- Strict YAML compliance (valid YAML without preprocessing)
- Uses if/then/else conditionals instead of `# [selector]` comments

### if/then/else Syntax (Modern Selectors)

Replace classic selectors with YAML conditionals:

```yaml
requirements:
  host:
    - if: unix
      then: unix-tool
    - if: win
      then: win-tool
    # Multiple items
    - if: linux
      then:
        - libfoo
        - libbar
    # Complex conditions
    - if: osx and arm64
      then: special-arm-lib
    - if: build_platform != target_platform
      then: cross-python_${{ target_platform }}
```

### Available Selector Variables

**Platform**: `unix`, `win`, `linux`, `osx`

**Architecture**: `x86`, `x86_64`, `aarch64`/`arm64`, `ppc64`, `ppc64le`, `s390x`

**Build Context**: `target_platform`, `build_platform`

### Conditional Operators

- Comparisons: `==`, `!=`
- Logical: `and`, `or`, `not`
- Version matching: `match(python, ">=3.8")`
- Grouping: `(osx and arm64) or (linux and aarch64)`

### Scalar Field Conditionals

For non-list fields, use Jinja:

```yaml
build:
  script: ${{ "build.sh" if unix else "build.bat" }}
```

### Variants Configuration

Create `variants.yaml` or `variant_config.yaml`:

```yaml
python:
  - "3.9"
  - "3.10"
  - "3.11"

numpy:
  - "1.24"
  - "1.26"

# Zip keys pair versions positionally (same length required)
zip_keys:
  - [python, numpy]

# Pin run dependencies based on build
pin_run_as_build:
  numpy:
    max_pin: 'x.x'
```

### Tests Section (Modern Format)

```yaml
tests:
  # Python import test
  - python:
      imports:
        - mypackage
        - mypackage.submodule
      pip_check: true
      python_version: ${{ python_min }}.*

  # Script test
  - script:
      - mycommand --help
      - mycommand --version
    requirements:
      run:
        - pytest

  # Package contents test
  - package_contents:
      lib:
        - mylib.so  # [unix]
        - mylib.dll  # [win]
      include:
        - mylib/*.h
      bin:
        - mytool

  # Downstream test
  - downstream:
      - dependent-package
```

### Advanced Build Options

```yaml
build:
  number: 0

  # Python-specific
  python:
    entry_points:
      - mycli = mypackage.cli:main
    skip_pyc_compilation: ["mypackage/templates/**"]

  # File inclusion control
  files:
    include:
      - include/**/*.h
    exclude:
      - include/**/private.h

  # Dynamic linking
  dynamic_linking:
    rpaths:
      - lib/
    missing_dso_allowlist:
      - "*/libcuda.so*"
    overlinking_behavior: error
    overdepending_behavior: ignore

  # Variant control
  variant:
    use_keys:
      - python
    ignore_keys:
      - numpy
    down_prioritize_variant: 1
```

# Linting & Validation

## Mandatory Local Linting with conda-smithy

**CRITICAL**: You MUST always run `conda-smithy recipe-lint` before submission. This step is mandatory and catches common recipe errors before CI runs.

```bash
# Lint a single recipe (REQUIRED before submission)
conda-smithy recipe-lint recipes/my-package

# Lint all recipes in staged-recipes
conda-smithy recipe-lint --conda-forge recipes/*

# Skip specific lint checks (use sparingly)
# Configure in conda-forge.yml:
# linter:
#   skip:
#     - lint_noarch_selectors
```

### Installing conda-smithy

```bash
# Via conda/mamba (recommended)
conda install -c conda-forge conda-smithy

# Via pixi
pixi global install conda-smithy
```

### What conda-smithy recipe-lint Checks

1. **License validation**: Correct SPDX identifier and license_file present
2. **Maintainer format**: Valid GitHub usernames in recipe-maintainers
3. **Source integrity**: SHA256 checksums present, no git URLs for releases
4. **Selector syntax**: Correct platform selector format
5. **Recipe structure**: Required fields present and properly formatted
6. **CFEP compliance**: python_min usage for noarch packages

**IMPORTANT**: Run linting BEFORE `build-locally.py` to catch simple errors early.

## Critical Linting Rules

- **License**: Must specify `about: license_file`. Use SPDX identifiers (MIT, Apache-2.0, BSD-3-Clause).
- **License Case**: Ensure correct case sensitivity (e.g., "Apache-2.0" not "APACHE 2.0")
- **Selectors**: Use `# [linux]` or `# [win]`. Use `skip: true` (lowercase), not `skip: True`.
- **Source**: Prefer `url` with `sha256`. Never use git tags (unstable checksums).
- **Comments**: Remove all generic instruction comments before submission.

## Python Selector Syntax

Replace deprecated `py37` selectors with `py==37`. Legacy selectors `py27` and `py36` remain valid, but newer versions require the updated syntax.

## CFEP-25 Compliance (CRITICAL for noarch: python)

All `noarch: python` packages MUST use the `python_min` variable from global pinnings:

```yaml
requirements:
  host:
    - python {{ python_min }}
  run:
    - python >={{ python_min }}

test:
  requires:
    - python {{ python_min }}
```

Override in `recipe/conda_build_config.yaml` if package requires newer minimum:

```yaml
python_min:
  - "3.10"
```

## Noarch Python Requirements

To qualify as `noarch: python`:
- No compiled extensions (C/C++/Rust)
- No post-link scripts
- No OS-specific build scripts
- No Python version-specific requirements beyond minimum
- No skips except Python versions

## Compilers

By platform:
- **Linux**: GCC (C/C++/Fortran)
- **macOS**: Clang (C/C++), GNU Fortran
- **Windows**: MSVC (C/C++), Flang (Fortran)

Syntax:
- Classic: `{{ compiler('c') }}`, `{{ compiler('cxx') }}`, `{{ compiler('rust') }}`
- Modern: `${{ compiler('c') }}`

# Mandatory Local Testing with build-locally.py

**CRITICAL**: You MUST always run `build-locally.py` to test recipes before submission. This step is non-negotiable and catches issues that linting alone cannot detect.

## Running build-locally.py

```bash
# Navigate to repository root
cd ~/staged-recipes  # or ~/my-feedstock

# Run the local build script
python build-locally.py

# Or specify a variant directly
python build-locally.py linux64
python build-locally.py osx64
python build-locally.py win64
python build-locally.py linux64_cuda118
```

## Requirements

- **Linux builds**: Requires Docker installed and running
- **macOS builds**: Prompts for SDK location (set `OSX_SDK_DIR` environment variable)
- **Windows builds**: Requires native Windows environment

## What build-locally.py Tests

1. **Dependency resolution**: Verifies all dependencies can be resolved
2. **Build scripts**: Runs actual build.sh/build.bat scripts
3. **Test commands**: Executes all tests defined in the recipe
4. **Package creation**: Creates the actual conda package
5. **Import checks**: Verifies Python imports and `pip check`

## Interpreting Results

- **Success**: Package builds and all tests pass - ready for PR
- **Dependency errors**: Missing packages in conda-forge - add them first
- **Build failures**: Fix build scripts or requirements
- **Test failures**: Fix tests or recipe configuration

## Always Run Before

- Submitting a new recipe to staged-recipes
- Creating a PR for feedstock updates
- After any recipe modifications
- After rerendering with conda-smithy

This step is **mandatory** and should never be skipped, even for "simple" changes.

# Requirements Structure

## Three-Tier System

```yaml
requirements:
  build:
    # Compilers, cmake, make (only during build, not packaged)
    - {{ compiler('c') }}
    - cmake
    - pkg-config
  host:
    # Libraries linked against, Python, build tools
    - python {{ python_min }}
    - pip
    - hatchling  # or setuptools, poetry-core, flit-core
    - numpy  # for ABI compatibility
  run:
    # Runtime dependencies (installed with package)
    - python >={{ python_min }}
    - numpy
    - pandas >=1.0
```

## Build Backend Preferences (ranked by usage)

1. **hatchling** (37%): Modern, fast default
2. **poetry-core** (18%): Poetry projects
3. **setuptools** (traditional): Legacy projects
4. **flit-core**: Minimal, lightweight
5. **meson-python**: Meson-based projects

## Dependency Pinning

### Global Pinning

Global pins are defined in `conda_build_config.yaml` within the `conda-forge-pinning` feedstock. Packages are automatically built against these versions.

### Overriding Pins

Make pinning stricter:
```yaml
requirements:
  run:
    - {{ pin_compatible('gmp', max_pin='x.x.x') }}
```

Remove pinning:
```yaml
build:
  ignore_run_exports:
    - libfoo
```

### run_exports

Automatically specifies ABI-compatible versions for dependent packages:

```yaml
build:
  run_exports:
    - {{ pin_subpackage('mylib', max_pin='x.x') }}
```

## Advanced Requirements Patterns

### run_constrained (Optional/Conditional Dependencies)

```yaml
requirements:
  run_constrained:
    - langsmith-pyo3 >=0.1.0,<0.2.0  # Optional accelerator
    - opentelemetry-sdk >=1.30.0    # Optional tracing
```

### Platform Selectors

Most common selectors:
- `# [win]` - Windows only
- `# [osx]` - macOS only
- `# [linux]` - Linux only
- `# [unix]` - Linux + macOS
- `# [not win]` - Not Windows
- `# [py>=39]` - Python 3.9+
- `# [build_platform != target_platform]` - Cross-compilation

```yaml
requirements:
  host:
    - python
    - libpython  # [win]
  run:
    - __cuda >={{ cuda_compiler_version_min }}  # [cuda_compiler_version != "None"]
```

### pin_compatible (Binary Packages)

```yaml
requirements:
  run:
    - {{ pin_compatible('numpy') }}  # Allows minor version updates
```

# Workflow: Creating a New Recipe

## 1. Analysis

Identify:
- Language (Python, R, Rust, C++, Go, Node.js/TypeScript)
- Build system (setuptools, hatchling, poetry, cargo, cmake, npm)
- Dependencies and their conda-forge availability
- License type
- For npm packages: Check if scoped (@scope/name) or unscoped

## 2. Generate Skeleton

```bash
# Python
grayskull pypi <package-name>

# R
grayskull cran <package-name>

# Node.js - check npm registry and create manually
curl -s https://registry.npmjs.org/<package-name> | jq '.["dist-tags"].latest'
curl -sL https://registry.npmjs.org/<package>/-/<package>-<version>.tgz | sha256sum

# Rust/Go/C++ - create manually
```

## 3. Review and Edit

- Verify all dependencies are in conda-forge
- Add missing test commands
- Ensure license_file is correct
- Apply CFEP-25 for noarch: python
- Remove all instructional comments

## 4. Lint Locally (MANDATORY)

**You MUST run `conda-smithy recipe-lint` before proceeding to build.** This catches common errors early.

```bash
# Install if needed
conda install -c conda-forge conda-smithy

# Lint your recipe (REQUIRED)
conda-smithy recipe-lint recipes/my-package

# Fix any errors before proceeding to step 5
```

**Do NOT proceed to build-locally.py until linting passes.**

## 5. Local Build & Test (MANDATORY)

**You MUST run `build-locally.py` before submitting any recipe.** This is a required step that validates your recipe actually builds and passes tests.

### For staged-recipes

```bash
cd ~/staged-recipes
python build-locally.py
# Select variant when prompted

# Or specify variant directly
python build-locally.py linux64
python build-locally.py osx64
python build-locally.py linux64_cuda118
```

**Requirements**: Docker for Linux builds. macOS prompts for SDK location.

### For feedstocks

```bash
cd ~/my-feedstock
python build-locally.py
```

### Alternative: Direct conda-build (for debugging only)

```bash
# Classic format
conda build recipe/ -c conda-forge

# Modern format
rattler-build build -r recipe.yaml

# Use mambabuild for faster debugging
conda mambabuild recipe/ -c conda-forge
```

**Note**: Even if using direct conda-build for debugging, you should still run `build-locally.py` before final submission to ensure CI compatibility.

## 6. Submission to staged-recipes

1. Fork conda-forge/staged-recipes
2. Create branch from main
3. Add recipe in `recipes/<package-name>/`
4. Push and create PR
5. Complete submission checklist (see below)
6. Request review from language-specific team
7. After merge, bot creates feedstock automatically (several times hourly)

# PR Submission Checklist

Before submitting, verify all items:

- [ ] **License correct**: SPDX identifier with correct case
- [ ] **License file included**: `license_file` points to actual file
- [ ] **Source is tarball**: Not a git repository URL
- [ ] **SHA256 verified**: From PyPI or generated locally
- [ ] **Dependencies in conda-forge**: All requirements available
- [ ] **Tests included**: Import tests and/or `pip check`
- [ ] **Comments removed**: No generic instruction comments
- [ ] **Recipe order correct**: Follows example structure
- [ ] **Linting passed (REQUIRED)**: Must have run `conda-smithy recipe-lint` successfully
- [ ] **Local build tested (REQUIRED)**: Must have run `python build-locally.py` successfully

**CRITICAL**: Both linting AND local build tests are mandatory. PRs should not be submitted until BOTH steps pass successfully:
1. First run: `conda-smithy recipe-lint recipes/my-package`
2. Then run: `python build-locally.py`

# Review Teams

Request review by commenting on your PR:

| Language | Team |
|----------|------|
| Python | `@conda-forge/help-python` |
| C/C++ | `@conda-forge/help-c-cpp` |
| R | `@conda-forge/help-r` |
| Go | `@conda-forge/help-go` |
| Java | `@conda-forge/help-java` |
| Julia | `@conda-forge/help-julia` |
| Node.js | `@conda-forge/help-nodejs` |
| Perl | `@conda-forge/help-perl` |
| Ruby | `@conda-forge/help-ruby` |
| Rust | `@conda-forge/help-rust` |
| Other | `@conda-forge/staged-recipes` |

**First-time contributors**: Use a bot command to ping review teams if you cannot mention them directly.

**Review timeline**: Variable (days to weeks) depending on team capacity. Ask on Zulip chat if your PR needs attention.

# Bot Commands & Automation

## @conda-forge-admin Commands

Use these in PR/issue comments:

| Command | Action |
|---------|--------|
| `@conda-forge-admin, please rerender` | Regenerate CI configuration |
| `@conda-forge-admin, please lint` | Run recipe linting |
| `@conda-forge-admin, please update team` | Sync maintainer team |
| `@conda-forge-admin, please restart ci` | Restart failed CI jobs |
| `@conda-forge-admin, please add user @username` | Add maintainer |
| `@conda-forge-admin, please update version` | Trigger version update |
| `@conda-forge-admin, please add noarch: python` | Convert to noarch |

## regro-cf-autotick-bot

Automatically:
- Monitors upstream version changes (PyPI, GitHub)
- Creates version update PRs
- Handles dependency migrations
- Updates build matrices for new Python versions

**Handling bot PRs**: You can commit directly to the bot's branch instead of creating new PRs. No approval needed—any maintainer can merge.

# conda-forge.yml Configuration

Key configuration options for feedstocks:

## Provider Configuration

```yaml
provider:
  linux_64: azure
  osx_64: azure
  win_64: azure
  linux_aarch64: default
  linux_ppc64le: default
```

## Build Tools

```yaml
conda_build_tool: mamba  # or conda, rattler-build
conda_install_tool: micromamba  # default
```

## OS Versions

```yaml
os_version:
  linux_64: alma9  # default; also cos7, alma8, ubi8
```

## Noarch Platforms

```yaml
noarch_platforms:
  - linux_64
  - win_64  # for multiple platforms
```

## Shell Script Linting

```yaml
shellcheck:
  enabled: true
```

## Azure-Specific

```yaml
azure:
  store_build_artifacts: true
  max_parallel: 4
```

## Upload Control

```yaml
upload_on_branch: main  # Restrict uploads to specific branch
```

## Skip Rendering

```yaml
skip_render:
  - .gitignore
  - LICENSE.txt
```

# Templates

## Template 1: Python Package (Classic meta.yaml)

CFEP-25 compliant template for `noarch: python` packages.

```yaml
{% set name = "example-package" %}
{% set version = "1.0.0" %}

package:
  name: {{ name|lower }}
  version: {{ version }}

source:
  url: https://pypi.io/packages/source/{{ name[0] }}/{{ name }}/{{ name }}-{{ version }}.tar.gz
  sha256: <insert_sha256_here>

build:
  number: 0
  noarch: python
  script: {{ PYTHON }} -m pip install . -vv --no-deps --no-build-isolation

requirements:
  host:
    - python {{ python_min }}
    - pip
    - hatchling
  run:
    - python >={{ python_min }}
    - numpy
    - pandas

test:
  imports:
    - example_package
  commands:
    - pip check
  requires:
    - pip
    - python {{ python_min }}

about:
  home: https://github.com/example/package
  summary: A brief description of the package.
  license: MIT
  license_file: LICENSE

extra:
  recipe-maintainers:
    - your-github-username
```

## Template 2: Python Package (Modern recipe.yaml)

Modern format with schema_version: 1 and CFEP-25 compliance.

```yaml
schema_version: 1

context:
  name: example-package
  version: "1.0.0"
  python_min: "3.9"

package:
  name: ${{ name|lower }}
  version: ${{ version }}

source:
  url: https://pypi.io/packages/source/${{ name[0] }}/${{ name }}/${{ name }}-${{ version }}.tar.gz
  sha256: <insert_sha256_here>

build:
  number: 0
  noarch: python
  script: ${{ PYTHON }} -m pip install . -vv --no-deps --no-build-isolation

requirements:
  host:
    - python ${{ python_min }}.*
    - pip
    - hatchling
  run:
    - python >=${{ python_min }},<4.0
    - numpy
    - pandas

tests:
  - python:
      imports:
        - example_package
      pip_check: true
      python_version: ${{ python_min }}.*

about:
  homepage: https://github.com/example/package
  summary: A brief description of the package.
  license: MIT
  license_file: LICENSE

extra:
  recipe-maintainers:
    - your-github-username
```

## Template 3: Python with C Extensions

For packages with compiled components (not noarch).

```yaml
{% set name = "fast-package" %}
{% set version = "2.0.0" %}

package:
  name: {{ name|lower }}
  version: {{ version }}

source:
  url: https://pypi.io/packages/source/{{ name[0] }}/{{ name }}/{{ name }}-{{ version }}.tar.gz
  sha256: <insert_sha256_here>

build:
  number: 0
  script: {{ PYTHON }} -m pip install . -vv --no-deps --no-build-isolation
  skip: true  # [py<39]

requirements:
  build:
    - {{ compiler('c') }}
    - {{ compiler('cxx') }}
  host:
    - python
    - pip
    - setuptools
    - cython
    - numpy
  run:
    - python
    - {{ pin_compatible('numpy') }}

test:
  imports:
    - fast_package
  commands:
    - pip check
  requires:
    - pip

about:
  home: https://github.com/example/fast-package
  summary: A high-performance package with C extensions.
  license: BSD-3-Clause
  license_file: LICENSE

extra:
  recipe-maintainers:
    - your-github-username
```

## Template 4: Rust/C++ Application (Modern recipe.yaml)

```yaml
schema_version: 1

context:
  name: fast-tool
  version: "0.2.1"

package:
  name: ${{ name }}
  version: ${{ version }}

source:
  url: https://github.com/user/${{ name }}/archive/refs/tags/v${{ version }}.tar.gz
  sha256: <insert_sha256_here>

build:
  number: 0

requirements:
  build:
    - ${{ compiler('c') }}
    - ${{ compiler('rust') }}
    - cargo
  host:
    - openssl
  run:
    - openssl

tests:
  - script:
      - ${{ name }} --help
      - ${{ name }} --version

about:
  homepage: https://github.com/user/${{ name }}
  license: Apache-2.0
  license_file: LICENSE
  summary: A high-performance tool built with Rust.

extra:
  recipe-maintainers:
    - user123
```

## Template 5: Multi-Output Recipe

For packages that produce multiple conda packages.

```yaml
{% set name = "multi-package" %}
{% set version = "1.0.0" %}

package:
  name: {{ name }}
  version: {{ version }}

source:
  url: https://github.com/user/{{ name }}/archive/v{{ version }}.tar.gz
  sha256: <insert_sha256_here>

build:
  number: 0

outputs:
  - name: {{ name }}-core
    script: build-core.sh  # [unix]
    script: build-core.bat  # [win]
    requirements:
      build:
        - {{ compiler('c') }}
      host:
        - python
      run:
        - python

  - name: {{ name }}-extras
    requirements:
      run:
        - {{ pin_subpackage(name + '-core', exact=True) }}
        - pandas
        - matplotlib

about:
  home: https://github.com/user/{{ name }}
  license: MIT
  license_file: LICENSE
  summary: Multi-output package example.

extra:
  recipe-maintainers:
    - your-github-username
```

## Template 6: Node.js/npm Package (Classic meta.yaml)

For Node.js packages from the npm registry. Includes handling for scoped packages (@scope/package-name).

```yaml
{% set name = "my-cli-tool" %}
{% set npm_name = "@scope/my-cli-tool" %}
{% set version = "1.0.0" %}

package:
  name: {{ name }}
  version: {{ version }}

source:
  # For scoped packages, npm uses: @scope/package/-/package-version.tgz
  url: https://registry.npmjs.org/{{ npm_name }}/-/{{ name }}-{{ version }}.tgz
  sha256: <insert_sha256_here>

build:
  number: 0

requirements:
  host:
    - nodejs
  run:
    - nodejs

test:
  commands:
    - {{ name }} --help
    - test -f $PREFIX/bin/{{ name }}  # [not win]
    - if not exist %PREFIX%\bin\{{ name }} exit 1  # [win]

about:
  home: https://github.com/user/my-cli-tool
  license: MIT
  license_file: LICENSE
  summary: A Node.js CLI tool.

extra:
  recipe-maintainers:
    - your-github-username
```

### Node.js Build Scripts

**build.sh** (Unix):
```bash
#!/bin/bash
set -ex

# Set npm prefix to install globally into the conda environment
export npm_config_prefix="${PREFIX}"

# Use a non-existent config file to avoid user-level npm config
export NPM_CONFIG_USERCONFIG=/tmp/nonexistentrc

# Pack the source (we're already in the extracted tarball)
npm pack

# Install globally with dependencies
# For scoped packages (@scope/name), npm pack creates: scope-name-VERSION.tgz
npm install -g scope-${PKG_NAME}-${PKG_VERSION}.tgz
```

**bld.bat** (Windows):
```batch
@echo on

:: Set npm prefix to install globally into the conda environment
call npm config set prefix "%PREFIX%"
if errorlevel 1 exit 1

:: Pack the source
call npm pack
if errorlevel 1 exit 1

:: Install globally with dependencies
:: For scoped packages (@scope/name), npm pack creates: scope-name-VERSION.tgz
call npm install --userconfig nonexistentrc -g scope-%PKG_NAME%-%PKG_VERSION%.tgz
if errorlevel 1 exit 1
```

### Node.js Package Notes

1. **Scoped packages**: npm registry URLs use `@scope/package/-/package-version.tgz` (note: only the package name after `/` in the path)
2. **npm pack naming**: Creates `scope-package-version.tgz` (scope without @, hyphens instead of slashes)
3. **Dependencies**: npm install -g automatically installs all dependencies into `$PREFIX/lib/node_modules`
4. **Binary linking**: npm automatically creates symlinks in `$PREFIX/bin` for packages with `bin` entries
5. **Getting sha256**: `curl -sL <tarball-url> | sha256sum`
6. **Unscoped packages**: For packages without a scope, use `${PKG_NAME}-${PKG_VERSION}.tgz` directly

### Simple Copy Method (for packages without CLI)

For Node.js libraries that don't need CLI binaries or dependencies bundled at runtime:

**build.sh**:
```bash
#!/bin/bash
set -ex

mkdir -p "${PREFIX}/lib/node_modules/@scope/package-name"
cp -r . "${PREFIX}/lib/node_modules/@scope/package-name/"
```

## Template 7: Node.js/npm Package (Modern recipe.yaml)

Modern format with schema_version: 1 for rattler-build. Uses if/then/else conditionals.

**IMPORTANT**: rattler-build uses `build.bat` (not `bld.bat`) for Windows builds. Using `bld.bat` will trigger a linting warning.

### Recommended: Inline Scripts (Most Reliable)

Inline scripts are recommended for simple Node.js packages as they are more reliable with rattler-build. External script files may not be copied to the work directory correctly.

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/prefix-dev/recipe-format/main/schema.json
schema_version: 1

context:
  name: my-cli-tool
  npm_name: "@scope/my-cli-tool"
  npm_scope: scope
  version: "1.0.0"

package:
  name: ${{ name }}
  version: ${{ version }}

source:
  url: https://registry.npmjs.org/${{ npm_name }}/-/${{ name }}-${{ version }}.tgz
  sha256: <insert_sha256_here>

build:
  number: 0
  script:
    - if: unix
      then:
        - export npm_config_prefix="${PREFIX}"
        - export NPM_CONFIG_USERCONFIG=/tmp/nonexistentrc
        - npm pack
        - npm install -g ${{ npm_scope }}-${PKG_NAME}-${PKG_VERSION}.tgz
    - if: win
      then:
        - npm config set prefix "%PREFIX%"
        - npm pack
        - npm install --userconfig nonexistentrc -g ${{ npm_scope }}-%PKG_NAME%-%PKG_VERSION%.tgz

requirements:
  host:
    - nodejs
  run:
    - nodejs

tests:
  - script:
      - ${{ name }} --help
  - script:
      - if: unix
        then: test -f $PREFIX/bin/${{ name }}
      - if: win
        then: if not exist %PREFIX%\bin\${{ name }} exit 1

about:
  summary: A Node.js CLI tool.
  homepage: https://github.com/user/my-cli-tool
  license: MIT
  license_file: LICENSE

extra:
  recipe-maintainers:
    - your-github-username
```

### Alternative: External Build Scripts

If you prefer external script files for complex builds, use `build.sh` and `build.bat` (not `bld.bat`):

```yaml
build:
  number: 0
  script:
    - if: unix
      then: bash build.sh
    - if: win
      then: cmd /c build.bat
```

**build.sh** (Unix):
```bash
#!/bin/bash
set -ex

export npm_config_prefix="${PREFIX}"
export NPM_CONFIG_USERCONFIG=/tmp/nonexistentrc

npm pack
# For scoped packages: scope-name-VERSION.tgz
npm install -g ${npm_scope}-${PKG_NAME}-${PKG_VERSION}.tgz
```

**build.bat** (Windows):
```batch
@echo on

call npm config set prefix "%PREFIX%"
if errorlevel 1 exit 1

call npm pack
if errorlevel 1 exit 1

call npm install --userconfig nonexistentrc -g %npm_scope%-%PKG_NAME%-%PKG_VERSION%.tgz
if errorlevel 1 exit 1
```

### Key Differences: meta.yaml vs recipe.yaml for Node.js

| Feature | meta.yaml (Classic) | recipe.yaml (Modern) |
|---------|---------------------|----------------------|
| **Variables** | `{% set name = "pkg" %}` | `context: name: pkg` |
| **Substitution** | `{{ name }}` | `${{ name }}` |
| **Platform tests** | `# [not win]` / `# [win]` | `if: unix` / `if: win` |
| **Build script** | `script: build.sh` | `script: - if: unix then: bash build.sh` |
| **Test section** | `test: commands:` | `tests: - script:` |
| **Build tool** | conda-build | rattler-build |

# Feedstock Maintenance

## Version Updates

The `regro-cf-autotick-bot` monitors PyPI/GitHub for new versions and creates PRs automatically.

**Manual updates**:

1. Fork the feedstock (never branch directly)
2. Sync fork with upstream
3. Update version and sha256 in recipe
4. Reset build number to 0
5. Push to fork and create PR

## Build Number Conventions

- **Version changes**: Reset to `0`
- **Metadata-only changes**: Increment by `1`
- **Build numbers over 1000**: Relics from compiler migrations. Reset to `0` when updating version.

## Rerendering

Run when configuration changes:

```bash
# Local
conda smithy rerender -c auto

# Or via web service (in PR comment)
@conda-forge-admin, please rerender
```

**Triggers**:
- Platform/skip changes
- `yum_requirements.txt` or `conda-forge.yml` modified
- Build matrix updates (Python versions)
- conda-forge pinning updates

## Forking Strategy

Always fork feedstocks to avoid:
- Wasteful CI duplication
- Premature package publication (branches auto-publish)

# Infrastructure & Build Pipeline

## Build Workflow

1. CI builds packages and uploads to `cf-staging` channel
2. CI sends API call with feedstock token to webservices
3. Webservices validates: token, package integrity, feedstock authorization
4. Valid packages move to `cf-post-staging` for final verification
5. Approved packages copy to `conda-forge` channel
6. CDN replication (~15 minutes typical)

## CI Providers

| Provider | Platforms | Max Duration |
|----------|-----------|--------------|
| Azure Pipelines | Windows, macOS, Linux (native + emulated ARM/PPC) | 6 hours |
| GitHub Actions | Administrative tasks, automerge | N/A |
| Cirun | GPU, custom architectures | Varies |

## Package Validation

- New package names require manual registration via admin-requests (prevents typosquatting)
- Feedstocks receive unique tokens for authentication
- Glob patterns supported for dynamic package names (e.g., `libllvm*`)

# CI Troubleshooting

## Azure Pipelines Issues

### Timeout

- Split long-running tests
- Use `pytest -x` to fail fast
- Skip slow tests in CI with markers
- Set `idle_timeout_minutes` in conda-forge.yml for packages with minimal output

### Missing Dependencies

- Ensure all deps are in conda-forge
- Check `yum_requirements.txt` for system libs on Linux

## GitHub Actions Issues

### Permission Denied

- Check file permissions in source archive
- Verify build scripts are executable

### Resource Limits

- Reduce parallelism
- Split into multiple outputs

## Platform-Specific Issues

### Windows CMake/MSBuild

MSBuild.exe isn't properly configured in Azure Windows images. Use alternatives:

```yaml
requirements:
  build:
    - cmake
    - ninja  # or jom
```

Then in build script:
```bash
cmake -G"Ninja" ..
# or
cmake -G"NMake Makefiles JOM" ..
```

### Windows Linking Errors

Windows requires import libraries (`.lib`) for DLLs. Conventions:
- MSVC: `{name}.dll` + `{name}.lib`
- MinGW: `lib{name}.dll` + `lib{name}.dll.a`

Don't mix conventions.

### macOS SDK Issues

Default target: macOS 10.13. Override in `conda_build_config.yaml`:

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

### Missing DSOs (Dynamic Shared Objects)

For CI machines without GPUs:

```yaml
build:
  missing_dso_whitelist:
    - "*/nvcuda.dll"  # [win]
    - "*/libcuda.so*"  # [linux]
```

### libGL.so.1 Import Error

Add as Linux host dependency:

```yaml
requirements:
  host:
    - libgl-devel  # [linux]
```

### Qt Platform Plugin Error

For headless CI testing:

```yaml
test:
  commands:
    - export QT_QPA_PLATFORM=offscreen && python -c "import mypackage"  # [linux]
```

Or set in meta.yaml script environment.

# Common Errors & Solutions

## "ImportError: No module named..."

**Diagnosis**: Runtime dependency missing.
**Fix**: Check `requirements: run`. Ensure `noarch: python` packages don't rely on C-extensions.

## "Linker failed" (C/C++)

**Diagnosis**: Missing libraries or wrong compiler.
**Fix**:
- Add `{{ compiler('cxx') }}` to build requirements
- Add `sysroot_linux-64` for glibc compatibility
- Ensure `make` or `cmake` in build requirements

## "Hash mismatch"

**Diagnosis**: Upstream tarball changed or wrong SHA.
**Fix**: Verify source URL. Generate hash: `openssl sha256 <file>` or `curl -sL <url> | sha256sum`

## "CMake can't find Python"

**Diagnosis**: Wrong FindPython module.
**Fix**: Match module to setup:
- `FindPython`: `-DPython_EXECUTABLE=${PYTHON}`
- `FindPython3`: `-DPython3_EXECUTABLE=${PYTHON}`

Always include `${CMAKE_ARGS}` for conda-forge optimizations.

## "Package not found in conda-forge"

**Diagnosis**: Dependency not yet in conda-forge.
**Fix**:
1. Submit dependency to staged-recipes first
2. Wait for feedstock creation
3. Then submit your package

## Cross-Compilation Failures

**Diagnosis**: Build vs target platform mismatch.
**Fix**: Add cross-compilation support:

```yaml
requirements:
  build:
    - {{ compiler('c') }}
    - cross-python_{{ target_platform }}  # [build_platform != target_platform]
```

## conda-verify Import Error

**Safe to ignore**: conda-forge doesn't use conda-verify for validation despite the warning message.

## Build Failed - Retrigger

For infrastructure issues (not recipe errors):
```bash
git commit --amend --no-edit
git push -f
```

# Common Mistakes to Avoid

1. **Missing dependencies**: Verify all required packages exist in conda-forge before submission
2. **Incorrect hashes**: Double-check SHA256 values against official sources
3. **Platform issues**: Test across platforms or explicitly exclude unsupported ones
4. **Incomplete testing**: Include basic import tests to verify installation success
5. **Generic comments left**: Remove all instruction comments from example recipes
6. **Wrong license case**: Use exact SPDX identifiers (Apache-2.0, not APACHE 2.0)
7. **Git URLs for source**: Use tarballs, not repository URLs
8. **Branching feedstocks**: Always fork instead of branch to avoid auto-publishing
9. **Forgetting to rerender**: Run after any conda-forge.yml or platform changes
10. **Hardcoded versions**: Use jinja2/context variables for version and sha256

# Best Practices Checklist

## Recipe Quality
- [ ] **License File**: Is `license_file` populated with correct path?
- [ ] **License SPDX**: Using correct SPDX identifier with proper case?
- [ ] **CFEP-25 Compliance**: For `noarch: python`, uses `python_min` variable?
- [ ] **Tests**: Includes `pip check` (Python) or binary execution tests?
- [ ] **Dependencies**: All available in conda-forge?
- [ ] **Build Number**: Reset to `0` for new versions?
- [ ] **Maintainers**: Valid GitHub handles with consent?

## Code Quality
- [ ] **No Hardcoded Versions**: Uses jinja2/context variables?
- [ ] **Correct Selectors**: Platform selectors are accurate?
- [ ] **Pin Compatible**: Binary packages use `{{ pin_compatible() }}`?
- [ ] **Source Hash**: SHA256 is correct and from official source?

## Submission
- [ ] **Linting Passed (REQUIRED)**: Tested with `conda-smithy recipe-lint`? This is mandatory!
- [ ] **Local Build (REQUIRED)**: Tested with `python build-locally.py`? This is mandatory!
- [ ] **Removed Comments**: Generic instruction comments removed?
- [ ] **Fork Strategy**: Using fork, not branch?

# Advanced Patterns

## CUDA Support

```yaml
build:
  skip: true  # [cuda_compiler_version not in ("None", cuda_compiler_version_min)]

requirements:
  build:
    - {{ compiler("cuda") }}  # [cuda_compiler_version != "None"]
  run:
    - __cuda >={{ cuda_compiler_version_min }}  # [cuda_compiler_version != "None"]
```

## Complex Test Skipping

```yaml
{% set tests_to_skip = "_not_a_test" %}
{% set tests_to_skip = tests_to_skip + " or test_windows_only" %}  # [not win]
{% set tests_to_skip = tests_to_skip + " or test_gpu" %}  # [cuda_compiler_version == "None"]

test:
  commands:
    - pytest -k "not ({{ tests_to_skip }})" --durations=50
```

## Multiple Sources

```yaml
source:
  - url: https://github.com/user/project/archive/v{{ version }}.tar.gz
    sha256: <main_sha256>
  - git_url: https://github.com/user/test-data.git
    git_rev: abc123
    folder: testing
```

## Patches

```yaml
source:
  url: https://pypi.io/packages/...
  sha256: <sha256>
  patches:
    - fix-windows.patch
    - 0001-update-deps.patch
```

## Platform Exclusion (Modern Format)

```yaml
build:
  skip:
    - win
    - osx and arm64
```

# Format Comparison: meta.yaml vs recipe.yaml

| Feature | meta.yaml (Classic) | recipe.yaml (Modern) |
|---------|---------------------|----------------------|
| **Syntax** | Jinja2 `{{ }}` | Context `${{ }}` |
| **Selectors** | `# [linux]` comments | `if/then/else` YAML |
| **Variables** | Top-level `{% set %}` | `context:` section |
| **Tests** | `test:` section | `tests:` list |
| **Compliance** | Requires preprocessing | Valid YAML directly |
| **Build tool** | conda-build | rattler-build |
| **Python imports** | `test: imports:` | `tests: - python: imports:` |

## Converting meta.yaml to recipe.yaml

Key transformations:

```yaml
# meta.yaml
{% set name = "pkg" %}
{% set version = "1.0" %}
requirements:
  host:
    - openssl  # [unix]
    - openssl-windows  # [win]

# recipe.yaml
context:
  name: pkg
  version: "1.0"
requirements:
  host:
    - if: unix
      then: openssl
    - if: win
      then: openssl-windows
```

# References

## conda-forge
- [conda-forge Documentation](https://conda-forge.org/docs/)
- [staged-recipes Repository](https://github.com/conda-forge/staged-recipes)
- [conda-smithy](https://github.com/conda-forge/conda-smithy)
- [Grayskull](https://github.com/conda/grayskull)
- [CFEP-25: python_min](https://github.com/conda-forge/cfep/blob/main/cfep-25.md)
- [conda-forge Status Dashboard](https://conda-forge.org/status)
- [Feedstock Outputs](https://conda-forge.org/feedstock-outputs)
- [Zulip Chat](https://conda-forge.zulipchat.com/)

## prefix-dev (Modern Tools)
- [rattler-build](https://github.com/prefix-dev/rattler-build)
- [rattler-build Documentation](https://rattler.build/latest/)
- [pixi](https://github.com/prefix-dev/pixi)
- [pixi Documentation](https://pixi.sh/latest/)
- [pixi-build-backends](https://github.com/prefix-dev/pixi-build-backends)
- [recipe-format Schema](https://github.com/prefix-dev/recipe-format)
- [prefix.dev](https://prefix.dev/) - Package discovery and publishing
