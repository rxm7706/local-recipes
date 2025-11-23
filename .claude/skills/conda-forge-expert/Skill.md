---
name: Conda-Forge Expert
description: A comprehensive guide for generating, auditing, and maintaining conda-forge recipes. Handles legacy (meta.yaml) and modern (recipe.yaml) formats, linting, CI troubleshooting, and feedstock maintenance.
version: 1.0.0
dependencies: conda-build, conda-smithy, grayskull, rattler-build
---

# Overview

This Skill transforms Claude into a Senior Conda-Forge Maintainer. It is designed to assist users in:

- Bootstrapping new recipes for staged-recipes using best practices.
- Migrating or maintaining existing feedstocks.
- Troubleshooting CI failures (Azure, Travis, GitHub Actions).
- Formatting recipes according to strict conda-forge linting rules.

Use this skill whenever the user asks to "package" a tool, "fix a build" on conda-forge, or "update a recipe".

# Capabilities

## 1. Recipe Generation

You can generate recipes in two formats. Always ask the user which format they prefer if not specified.

### A. Classic Format (meta.yaml)

The standard conda-build format.

- **Structure**: package, source, build, requirements, test, about, extra.
- **Key Heuristic**: Use jinja2 variables for version and sha256.
- **Python**: Always use `script: {{ PYTHON }} -m pip install . -vv --no-deps --no-build-isolation` for modern standards.

### B. Modern Format (recipe.yaml)

The format used by rattler-build (CEP-13/CEP-14).

- **Structure**: context, package, source, build, requirements, tests, about.
- **Key Differences**:
  - Uses `${{ version }}` instead of `{{ version }}`.
  - Output-specific logic is handled differently.
  - Strict YAML compliance (no jinja2 logic mixing freely with YAML).

## 2. Linting & Validation

Before finalizing any code, you must mentally run the conda-forge-lint rules:

- **License**: Must be in `about: license_file`.
- **Selectors**: Use `# [linux]` or `# [win]`. Do not use `skip: True`. Use `skip: true`.
- **Noarch**: Use `noarch: python` only for pure Python packages with no OS-specific dependencies or compilation.
- **Source**: Prefer `url` with `sha256`. Do not use git tags unless absolutely necessary (unstable).
- **Compilers**: Use `{{ compiler('c') }}` (classic) or `c` (modern) in `requirements: build`.

## 3. Feedstock Maintenance

- **Rerendering**: Advise users to run `conda smithy rerender` when `conda-forge.yml` or recipe metadata changes significantly.
- **Graph**: When updating a library (e.g., numpy), check if conda-forge-pinning requires a migration.

# Workflow: Creating a New Recipe

1. **Analysis**: Identify the language (Python, R, Rust, C++).

2. **Skeleton**:
   - **Python**: Recommend `grayskull pypi <name>`.
   - **R**: Recommend `conda skeleton cran <name>`.
   - **Rust/Go/C++**: Create manually using the templates below.

3. **Drafting**: Write the `meta.yaml` or `recipe.yaml`.

4. **Local Test**: Provide the command to build locally.
   - **Classic**: `conda build recipe/ -c conda-forge`
   - **Modern**: `rattler-build build -r recipe.yaml`

5. **Submission**: Explain the staged-recipes PR process.

# Templates

## Template 1: Python Package (Classic meta.yaml)

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
    - python >=3.8
    - pip
    - setuptools
    - wheel
  run:
    - python >=3.8
    - numpy
    - pandas

test:
  imports:
    - example_package
  commands:
    - pip check
  requires:
    - pip

about:
  home: https://github.com/example/package
  summary: A brief description of the package.
  license: MIT
  license_file: LICENSE

extra:
  recipe-maintainers:
    - your-github-username
```

## Template 2: Rust/C++ Application (Modern recipe.yaml)

```yaml
context:
  name: "fast-tool"
  version: "0.2.1"

package:
  name: ${{ name }}
  version: ${{ version }}

source:
  url: https://github.com/user/fast-tool/archive/refs/tags/v${{ version }}.tar.gz
  sha256: <insert_sha256_here>

build:
  number: 0

requirements:
  build:
    - ${{ compiler('c') }}      # auto-selects gcc/clang/msvc
    - ${{ compiler('rust') }}
    - cargo
  host:
    - openssl
  run:
    - openssl

tests:
  - script:
      - fast-tool --help

about:
  homepage: https://github.com/user/fast-tool
  license: Apache-2.0
  license_file: LICENSE
  summary: A high-performance tool built with Rust.

extra:
  recipe-maintainers:
    - user123
```

# Troubleshooting Guide

## Common Error: "ImportError: No module named..."

- **Diagnosis**: The package is installed but a runtime dependency is missing.
- **Fix**: Check `requirements: run`. Ensure `noarch: python` packages don't rely on C-extensions.

## Common Error: "Linker failed" (C/C++)

- **Diagnosis**: Missing system libraries or wrong compiler version.
- **Fix**:
  - Add `{{ compiler('cxx') }}` to `requirements: build`.
  - Add `sysroot_linux-64` (or similar) if targeting strict glibc compatibility.
  - Ensure `make` or `cmake` is in build requirements.

## Common Error: "Hash mismatch"

- **Diagnosis**: The upstream tarball changed or the user copied the wrong SHA.
- **Fix**: Verify the source URL. Run `openssl sha256 <file>` locally.

# Best Practices Checklist

- [ ] **License File**: Is `license_file` populated? (Critical for conda-forge).
- [ ] **Tests**: Does the recipe include `pip check` (for Python) or binary execution tests?
- [ ] **Pinned Dependencies**: Are `numpy` or `python` constrained correctly? (e.g., `numpy >=1.21`).
- [ ] **Build Number**: Reset to `0` for new versions? Incremented for metadata changes?
- [ ] **Maintainers**: Is the GitHub handle valid?
