# recipe.yaml Reference (v1 Format)

Complete reference for the modern rattler-build recipe format.

## Overview

The `recipe.yaml` format (v1) is the modern recipe format for conda-forge, introduced with rattler-build. It uses:
- `schema_version: 1` declaration
- `${{ }}` variable substitution (instead of Jinja2 `{{ }}`)
- `if/then/else` conditionals (instead of `# [selector]` comments)
- Valid YAML syntax throughout

## Basic Structure

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/prefix-dev/recipe-format/main/schema.json
schema_version: 1

context:
  # Variables for use throughout the recipe

package:
  # Package name and version

source:
  # Source code location(s)

build:
  # Build configuration

requirements:
  # Dependencies

tests:
  # Test definitions

about:
  # Metadata

extra:
  # Additional data (maintainers, etc.)
```

## Context Section

Define variables for use throughout the recipe.

```yaml
context:
  name: my-package
  version: "1.2.3"
  python_min: "3.10"

  # Computed values
  major_minor: ${{ version.split('.')[0:2] | join('.') }}

  # Platform-specific
  lib_ext: ${{ ".dylib" if osx else ".so" if linux else ".dll" }}
```

### Using Context Variables

```yaml
package:
  name: ${{ name | lower }}
  version: ${{ version }}

source:
  url: https://example.com/${{ name }}-${{ version }}.tar.gz
```

## Package Section

```yaml
package:
  name: ${{ name | lower }}        # Package name (lowercase recommended)
  version: ${{ version }}          # Package version
```

### Naming Rules
- Lowercase letters, numbers, hyphens, underscores
- Must start with a letter
- No spaces or special characters

## Source Section

### Single URL Source

```yaml
source:
  url: https://pypi.org/packages/source/m/my-package/my-package-1.0.0.tar.gz
  sha256: abc123...
```

### Multiple Sources

```yaml
source:
  - url: https://example.com/main-1.0.0.tar.gz
    sha256: abc123...
    target_directory: main

  - url: https://example.com/extra-1.0.0.tar.gz
    sha256: def456...
    target_directory: extra
```

### Git Source

```yaml
source:
  git: https://github.com/org/repo.git
  tag: v${{ version }}
  # OR
  branch: main
  # OR
  rev: abc123def456

  depth: 1                         # Shallow clone
```

### Local Source

```yaml
source:
  path: ../my-local-source
  use_gitignore: true              # Respect .gitignore
```

### Source Options

```yaml
source:
  url: https://example.com/source.tar.gz
  sha256: abc123...

  # Extraction
  target_directory: src            # Extract to subdirectory

  # Patches
  patches:
    - fix-build.patch
    - 0001-add-feature.patch

  # File operations
  file_name: custom-name.tar.gz    # Rename downloaded file
```

### Checksum Types

```yaml
source:
  url: https://example.com/source.tar.gz
  sha256: abc123...                # Preferred
  # OR
  sha1: abc123...
  # OR
  md5: abc123...                   # Least preferred
```

## Build Section

### Basic Build

```yaml
build:
  number: 0
  script:
    - ${{ PYTHON }} -m pip install . -vv --no-deps --no-build-isolation
```

### Platform-Specific Scripts

```yaml
build:
  script:
    - if: unix
      then: bash ${{ RECIPE_DIR }}/build.sh
    - if: win
      then: call %RECIPE_DIR%\bld.bat
```

### Noarch Packages

```yaml
build:
  noarch: python                   # Pure Python
  # OR
  noarch: generic                  # Architecture-independent
```

### Skip Conditions

```yaml
build:
  skip:
    - win                          # Skip on Windows
    - py < 39                      # Skip Python < 3.9
    - linux and aarch64            # Skip Linux ARM64
```

### Build String

```yaml
build:
  string: py${{ python | version_to_buildstring }}h${{ hash }}_${{ number }}
```

### Python Entry Points

```yaml
build:
  python:
    entry_points:
      - mycli = mypackage.cli:main
      - myserver = mypackage.server:run
```

### Skip PyC Compilation

```yaml
build:
  python:
    skip_pyc_compilation:
      - "mypackage/templates/**"
      - "mypackage/data/**"
```

### Files Include/Exclude

```yaml
build:
  files:
    include:
      - bin/*
      - lib/*.so
      - include/**/*.h
    exclude:
      - lib/*.a                    # Exclude static libraries
      - include/**/private.h
```

### Dynamic Linking

```yaml
build:
  dynamic_linking:
    rpaths:
      - lib/
      - $ORIGIN/../lib/

    missing_dso_allowlist:
      - "*/libcuda.so*"            # CUDA libraries
      - "*/nvcuda.dll"             # Windows CUDA

    overlinking_behavior: error    # error, warn, ignore
    overdepending_behavior: ignore
```

### Run Exports

```yaml
build:
  run_exports:
    strong:
      - ${{ pin_subpackage(name, upper_bound="x.x") }}
    weak:
      - ${{ pin_subpackage(name, upper_bound="x") }}
```

### Variant Control

```yaml
build:
  variant:
    use_keys:
      - python
      - numpy
    ignore_keys:
      - build_platform
    down_prioritize_variant: 1     # Lower priority in solver
```

## Requirements Section

### Basic Requirements

```yaml
requirements:
  build:
    # Build tools (run on build machine)
    - ${{ compiler("c") }}
    - ${{ stdlib("c") }}
    - cmake
    - ninja

  host:
    # Libraries linked against (target platform)
    - python
    - numpy
    - zlib

  run:
    # Runtime dependencies
    - python
    - numpy

  run_constrained:
    # Optional constraints
    - scipy >=1.0
```

### Conditional Dependencies

```yaml
requirements:
  build:
    - if: unix
      then:
        - ${{ compiler("c") }}
        - ${{ stdlib("c") }}
    - if: win
      then:
        - ${{ compiler("m2w64_c") }}
        - ${{ stdlib("m2w64_c") }}

  run:
    - if: linux
      then: __linux
    - if: osx
      then: __osx
    - if: win
      then: __win
```

### Pin Functions

```yaml
requirements:
  host:
    - ${{ pin_subpackage("libfoo", exact=true) }}
    - ${{ pin_compatible("numpy", upper_bound="x.x") }}

  run:
    - ${{ pin_subpackage("libfoo", upper_bound="x.x.x") }}
```

### Run Exports (in requirements)

```yaml
requirements:
  run_exports:
    strong:
      - ${{ pin_subpackage(name, upper_bound="x.x") }}
    weak:
      - openssl
    noarch:
      - python-dateutil
```

### Ignore Run Exports

```yaml
requirements:
  ignore_run_exports:
    by_name:
      - libfoo                     # Ignore specific package
    from_package:
      - ${{ compiler("cuda") }}    # Ignore all from CUDA
```

## Tests Section

Tests is a **list** of test definitions.

### Python Import Test

```yaml
tests:
  - python:
      imports:
        - mypackage
        - mypackage.submodule
      pip_check: true
      python_version: ${{ python_min }}.*
```

### Script Test

```yaml
tests:
  - script:
      - mycommand --version
      - mycommand --help
      - pytest tests/ -v
    requirements:
      run:
        - pytest
        - if: win
          then: m2-grep
    files:
      source:
        - tests/
```

### Package Contents Test

```yaml
tests:
  - package_contents:
      lib:
        - mylib${{ shlib_ext }}
      include:
        - mylib/*.h
      bin:
        - mytool${{ executable_ext }}
      site_packages:
        - mypackage/__init__.py
```

### Downstream Test

```yaml
tests:
  - downstream:
      - dependent-package
```

### Multiple Tests

```yaml
tests:
  - python:
      imports:
        - mypackage
      pip_check: true

  - script:
      - mypackage --version

  - package_contents:
      bin:
        - mypackage
```

## Outputs Section (Multi-Output)

### Basic Multi-Output

```yaml
outputs:
  - package:
      name: libmypackage
    build:
      script: build-lib.sh
    requirements:
      build:
        - ${{ compiler("c") }}
        - ${{ stdlib("c") }}
      run_exports:
        - ${{ pin_subpackage("libmypackage", upper_bound="x.x") }}
    tests:
      - script:
          - test -f $PREFIX/lib/libmypackage${{ shlib_ext }}

  - package:
      name: mypackage
    build:
      script: build-python.sh
    requirements:
      host:
        - ${{ pin_subpackage("libmypackage", exact=true) }}
        - python
        - pip
      run:
        - ${{ pin_subpackage("libmypackage", exact=true) }}
        - python
    tests:
      - python:
          imports:
            - mypackage
```

### Cache Section (Shared Build)

```yaml
cache:
  requirements:
    build:
      - ${{ compiler("c") }}
      - ${{ stdlib("c") }}
      - cmake
    host:
      - zlib
  build:
    script:
      - cmake -B build .
      - cmake --build build
      - cmake --install build --prefix ${{ PREFIX }}

outputs:
  - package:
      name: libmypackage
    build:
      files:
        include:
          - lib/libmypackage*
          - include/mypackage/

  - package:
      name: mypackage-dev
    build:
      files:
        include:
          - lib/cmake/
          - lib/pkgconfig/
```

## About Section

```yaml
about:
  homepage: https://github.com/org/mypackage
  license: MIT
  license_file: LICENSE
  license_family: MIT              # Optional: MIT, BSD, Apache, GPL, etc.

  summary: Short one-line description
  description: |
    Longer multi-line description
    of the package.

  documentation: https://mypackage.readthedocs.io
  repository: https://github.com/org/mypackage

  # Optional identifiers
  identifiers:
    - doi:10.1234/example
```

### License File Options

```yaml
about:
  license_file: LICENSE            # Single file

  # OR multiple files
  license_file:
    - LICENSE
    - NOTICE
    - THIRDPARTY.yml               # Bundled licenses
```

## Extra Section

```yaml
extra:
  recipe-maintainers:
    - github-username-1
    - github-username-2

  feedstock-name: mypackage        # If different from package name

  # Custom data (not processed)
  custom:
    key: value
```

## Built-in Variables

### Platform Variables

| Variable | Description |
|----------|-------------|
| `linux` | True on Linux |
| `osx` | True on macOS |
| `win` | True on Windows |
| `unix` | True on Linux or macOS |

### Architecture Variables

| Variable | Description |
|----------|-------------|
| `x86` | 32-bit x86 |
| `x86_64` | 64-bit x86 |
| `aarch64` / `arm64` | 64-bit ARM |
| `ppc64le` | PowerPC 64-bit LE |
| `s390x` | IBM Z |

### Build Variables

| Variable | Description |
|----------|-------------|
| `build_platform` | Platform of build machine |
| `target_platform` | Platform of target |
| `PYTHON` | Python interpreter path |
| `PREFIX` | Install prefix |
| `SRC_DIR` | Source directory |
| `RECIPE_DIR` | Recipe directory |

### Extension Variables

| Variable | Description |
|----------|-------------|
| `shlib_ext` | Shared library extension (.so, .dylib, .dll) |
| `executable_ext` | Executable extension ("", .exe) |

## Filter Functions

### String Filters

```yaml
${{ name | lower }}                # Lowercase
${{ name | upper }}                # Uppercase
${{ version | replace(".", "_") }} # Replace characters
${{ name | default("unknown") }}   # Default value
```

### Version Filters

```yaml
${{ python | version_to_buildstring }}  # "312" for Python 3.12
${{ version.split('.')[0] }}            # Major version
```

### Hash Filter

```yaml
${{ hash }}                        # Short hash of variant
```

## Jinja Functions

### Compiler Functions

```yaml
${{ compiler("c") }}               # C compiler
${{ compiler("cxx") }}             # C++ compiler
${{ compiler("fortran") }}         # Fortran compiler
${{ compiler("rust") }}            # Rust compiler
${{ compiler("go") }}              # Go compiler (no CGO)
${{ compiler("go-cgo") }}          # Go compiler with CGO
${{ compiler("m2w64_c") }}         # MinGW-w64 C (Windows)
```

### Standard Library

```yaml
${{ stdlib("c") }}                 # C standard library
${{ stdlib("m2w64_c") }}           # MinGW-w64 stdlib (Windows)
```

### Pin Functions

```yaml
# Pin to current version
${{ pin_subpackage("pkg") }}

# Pin with bounds
${{ pin_subpackage("pkg", upper_bound="x.x.x") }}
${{ pin_subpackage("pkg", lower_bound="x.x", upper_bound="x.x.x") }}

# Exact pin
${{ pin_subpackage("pkg", exact=true) }}

# Compatible pin
${{ pin_compatible("pkg", upper_bound="x.x") }}
```

### CDT Function

```yaml
${{ cdt("mesa-libgl-devel") }}     # Core Development Toolkit package
```

### Environment Access

```yaml
${{ env.get("MY_VAR") }}           # Get env var (empty if not set)
${{ env.get("MY_VAR", "default") }} # With default
```

### Match Function

```yaml
${{ match(python, ">=3.9") }}      # Version matching
```

## Complete Example

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/prefix-dev/recipe-format/main/schema.json
schema_version: 1

context:
  name: example-package
  version: "2.1.0"
  python_min: "3.10"
  python_max: "3.13"

package:
  name: ${{ name | lower }}
  version: ${{ version }}

source:
  url: https://pypi.org/packages/source/${{ name[0] }}/${{ name }}/${{ name }}-${{ version }}.tar.gz
  sha256: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef

build:
  number: 0
  noarch: python
  script: ${{ PYTHON }} -m pip install . -vv --no-deps --no-build-isolation
  python:
    entry_points:
      - example-cli = example_package.cli:main

requirements:
  host:
    - python ${{ python_min }}.*
    - pip
    - hatchling
  run:
    - python >=${{ python_min }},<${{ python_max }}
    - click >=8.0
    - rich >=12.0
  run_constrained:
    - optional-dep >=1.0

tests:
  - python:
      imports:
        - example_package
        - example_package.cli
      pip_check: true
  - script:
      - example-cli --version
      - example-cli --help

about:
  homepage: https://github.com/org/example-package
  license: MIT
  license_file: LICENSE
  summary: An example Python package
  description: |
    This is an example package demonstrating
    the recipe.yaml format for conda-forge.
  documentation: https://example-package.readthedocs.io

extra:
  recipe-maintainers:
    - maintainer1
    - maintainer2
```

## References

- [rattler-build Documentation](https://rattler-build.prefix.dev/latest/)
- [Recipe Format Schema](https://github.com/prefix-dev/recipe-format)
- [conda-forge v1 Announcement](https://conda-forge.org/blog/2025/02/27/conda-forge-v1-recipe-support/)
