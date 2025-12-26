# Migration Guide: meta.yaml to recipe.yaml

Complete guide for converting conda recipes from legacy meta.yaml format to modern recipe.yaml (v1) format.

## Overview

| Feature | meta.yaml | recipe.yaml |
|---------|-----------|-------------|
| Templating | `{{ var }}` (Jinja2) | `${{ var }}` |
| Selectors | `# [linux]` comments | `if/then/else` blocks |
| Variables | `{% set var = ... %}` | `context:` section |
| Tests | `test:` (singular) | `tests:` (list) |
| Validation | None | YAML schema |

## Quick Reference

### Variables

```yaml
# meta.yaml
{% set name = "my-package" %}
{% set version = "1.2.3" %}

package:
  name: {{ name }}
  version: {{ version }}
```

```yaml
# recipe.yaml
context:
  name: my-package
  version: "1.2.3"

package:
  name: ${{ name }}
  version: ${{ version }}
```

### Platform Selectors

```yaml
# meta.yaml
requirements:
  build:
    - gcc       # [linux]
    - clang     # [osx]
    - vs2019    # [win]
```

```yaml
# recipe.yaml
requirements:
  build:
    - if: linux
      then: gcc
    - if: osx
      then: clang
    - if: win
      then: vs2019
```

### Skip Conditions

```yaml
# meta.yaml
build:
  skip: true  # [py<39]
  skip: true  # [win]
```

```yaml
# recipe.yaml
build:
  skip:
    - py < 39
    - win
```

### Tests Section

```yaml
# meta.yaml
test:
  imports:
    - mypackage
  commands:
    - pip check
  requires:
    - pip
```

```yaml
# recipe.yaml
tests:
  - python:
      imports:
        - mypackage
      pip_check: true
  - script:
      - mycommand --version
```

## Automated Conversion

### Using rattler-build

```bash
rattler-build generate-recipe convert meta.yaml > recipe.yaml
```

### Using conda-recipe-manager

```bash
pip install conda-recipe-manager
conda-recipe-manager convert meta.yaml > recipe.yaml
```

### Using feedrattler (Full Feedstock)

```bash
pixi exec feedrattler my-package-feedstock your-github-username
```

## Manual Conversion Steps

### Step 1: Add Schema Header

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/prefix-dev/recipe-format/main/schema.json
schema_version: 1
```

### Step 2: Convert Variables

**Before:**
```yaml
{% set name = "my-package" %}
{% set version = "1.2.3" %}
{% set sha256 = "abc123..." %}
```

**After:**
```yaml
context:
  name: my-package
  version: "1.2.3"
  sha256: abc123...
```

### Step 3: Convert Jinja Expressions

| meta.yaml | recipe.yaml |
|-----------|-------------|
| `{{ name }}` | `${{ name }}` |
| `{{ name\|lower }}` | `${{ name \| lower }}` |
| `{{ compiler('c') }}` | `${{ compiler("c") }}` |
| `{{ pin_subpackage('pkg', max_pin='x.x') }}` | `${{ pin_subpackage("pkg", upper_bound="x.x") }}` |

### Step 4: Convert Selectors

**Before (inline selectors):**
```yaml
requirements:
  build:
    - {{ compiler('c') }}       # [unix]
    - {{ compiler('m2w64_c') }} # [win]
  host:
    - python
    - numpy                     # [not win]
```

**After (if/then blocks):**
```yaml
requirements:
  build:
    - if: unix
      then: ${{ compiler("c") }}
    - if: win
      then: ${{ compiler("m2w64_c") }}
  host:
    - python
    - if: not win
      then: numpy
```

### Step 5: Convert Build Section

**Before:**
```yaml
build:
  number: 0
  skip: true  # [py<39]
  script: {{ PYTHON }} -m pip install . -vv
  entry_points:
    - mycli = mypackage.cli:main
```

**After:**
```yaml
build:
  number: 0
  skip:
    - py < 39
  script: ${{ PYTHON }} -m pip install . -vv
  python:
    entry_points:
      - mycli = mypackage.cli:main
```

### Step 6: Convert Test Section

**Before:**
```yaml
test:
  imports:
    - mypackage
    - mypackage.submodule
  commands:
    - pip check
    - mycli --version
    - mycli --help
  requires:
    - pip
    - pytest
  source_files:
    - tests/
```

**After:**
```yaml
tests:
  - python:
      imports:
        - mypackage
        - mypackage.submodule
      pip_check: true

  - script:
      - mycli --version
      - mycli --help

  - script:
      - pytest tests/ -v
    requirements:
      run:
        - pytest
    files:
      source:
        - tests/
```

### Step 7: Convert About Section

**Before:**
```yaml
about:
  home: https://github.com/org/pkg
  license: MIT
  license_family: MIT
  license_file: LICENSE
  summary: Short description
  doc_url: https://docs.example.com
  dev_url: https://github.com/org/pkg
```

**After:**
```yaml
about:
  homepage: https://github.com/org/pkg
  license: MIT
  license_file: LICENSE
  summary: Short description
  documentation: https://docs.example.com
  repository: https://github.com/org/pkg
```

### Step 8: Convert run_exports

**Before:**
```yaml
build:
  run_exports:
    - {{ pin_subpackage(name, max_pin='x.x') }}

  # OR with strength
  run_exports:
    strong:
      - {{ pin_subpackage(name, max_pin='x.x') }}
    weak:
      - openssl
```

**After:**
```yaml
build:
  run_exports:
    - ${{ pin_subpackage(name, upper_bound="x.x") }}

  # OR with strength
  run_exports:
    strong:
      - ${{ pin_subpackage(name, upper_bound="x.x") }}
    weak:
      - openssl
```

### Step 9: Convert ignore_run_exports

**Before:**
```yaml
build:
  ignore_run_exports:
    - libfoo
  ignore_run_exports_from:
    - {{ compiler('cuda') }}
```

**After:**
```yaml
requirements:
  ignore_run_exports:
    by_name:
      - libfoo
    from_package:
      - ${{ compiler("cuda") }}
```

### Step 10: Convert Multi-Output

**Before:**
```yaml
outputs:
  - name: libfoo
    script: build-lib.sh
    build:
      run_exports:
        - {{ pin_subpackage('libfoo', max_pin='x.x') }}
    requirements:
      build:
        - {{ compiler('c') }}
    test:
      commands:
        - test -f $PREFIX/lib/libfoo.so
```

**After:**
```yaml
outputs:
  - package:
      name: libfoo
    build:
      script: build-lib.sh
      run_exports:
        - ${{ pin_subpackage("libfoo", upper_bound="x.x") }}
    requirements:
      build:
        - ${{ compiler("c") }}
    tests:
      - script:
          - test -f $PREFIX/lib/libfoo${{ shlib_ext }}
```

## Complex Conversions

### Jinja Conditionals

**Before:**
```yaml
{% if cuda_compiler_version != "None" %}
requirements:
  build:
    - {{ compiler('cuda') }}
{% endif %}
```

**After:**
```yaml
requirements:
  build:
    - if: cuda_compiler_version != "None"
      then: ${{ compiler("cuda") }}
```

### Dynamic Skip Lists

**Before:**
```yaml
{% set tests_to_skip = "_not_a_test" %}
{% set tests_to_skip = tests_to_skip + " or test_network" %}
{% set tests_to_skip = tests_to_skip + " or test_slow" %}  # [aarch64]

test:
  commands:
    - pytest -k "not ({{ tests_to_skip }})"
```

**After:**
```yaml
context:
  base_skip: "_not_a_test or test_network"
  skip_slow: ${{ " or test_slow" if aarch64 else "" }}
  tests_to_skip: ${{ base_skip }}${{ skip_slow }}

tests:
  - script:
      - pytest -k "not (${{ tests_to_skip }})"
```

### Build Number Variants

**Before:**
```yaml
{% set build_number = 0 %}

build:
  number: {{ build_number + 200 }}  # [cuda_compiler_version != "None"]
  number: {{ build_number }}         # [cuda_compiler_version == "None"]
```

**After:**
```yaml
context:
  build_number: 0
  cuda_offset: ${{ 200 if cuda_compiler_version != "None" else 0 }}

build:
  number: ${{ build_number + cuda_offset }}
```

### Cross-Compilation

**Before:**
```yaml
requirements:
  build:
    - {{ compiler('c') }}
    - python                                     # [build_platform != target_platform]
    - cross-python_{{ target_platform }}         # [build_platform != target_platform]
```

**After:**
```yaml
requirements:
  build:
    - ${{ compiler("c") }}
    - if: build_platform != target_platform
      then:
        - python
        - cross-python_${{ target_platform }}
```

## Field Name Changes

| meta.yaml | recipe.yaml |
|-----------|-------------|
| `home:` | `homepage:` |
| `doc_url:` | `documentation:` |
| `dev_url:` | `repository:` |
| `license_family:` | (removed) |
| `max_pin:` | `upper_bound:` |
| `min_pin:` | `lower_bound:` |
| `folder:` | `target_directory:` |
| `git_url:` | `git:` |
| `git_rev:` | `rev:` or `tag:` |
| `source_files:` | `files: source:` |
| `test:` | `tests:` |

## Validation

### Validate Converted Recipe

```bash
# Check YAML syntax
python -c "import yaml; yaml.safe_load(open('recipe.yaml'))"

# Render recipe
rattler-build build -r recipe.yaml --render-only

# Full lint
conda-smithy recipe-lint .
```

### Common Conversion Errors

| Error | Cause | Fix |
|-------|-------|-----|
| Invalid YAML | Missing quotes around version | `version: "1.0"` not `version: 1.0` |
| Unknown field | Field name changed | Check field name mapping |
| Invalid selector | Wrong syntax | Use `if/then` not `# [selector]` |
| Schema error | Missing `schema_version: 1` | Add at top of file |

## Testing Both Formats

During migration, test both formats work:

```bash
# Test legacy
conda-build recipes/my-package-legacy -c conda-forge

# Test modern
rattler-build build -r recipes/my-package/recipe.yaml -c conda-forge

# Compare outputs
diff <(conda-render recipes/my-package-legacy) \
     <(rattler-build build -r recipes/my-package/recipe.yaml --render-only)
```

## Feedstock Migration

### Full Feedstock Conversion

1. **Fork the feedstock**
2. **Create branch**: `git checkout -b migrate-to-v1`
3. **Convert recipe**: Use automated tools + manual review
4. **Update conda-forge.yml**:
   ```yaml
   conda_build_tool: rattler-build
   ```
5. **Rerender**: `conda-smithy rerender`
6. **Test locally**: `python build-locally.py`
7. **Submit PR**

### Partial Migration (Hybrid)

Not recommended. Choose one format per feedstock.

## Resources

- [Recipe Format Schema](https://github.com/prefix-dev/recipe-format)
- [rattler-build Migration Docs](https://rattler-build.prefix.dev/latest/converting_from_conda_build/)
- [conda-forge v1 Announcement](https://conda-forge.org/blog/2025/02/27/conda-forge-v1-recipe-support/)
