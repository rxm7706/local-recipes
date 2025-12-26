# meta.yaml Reference (Legacy Format)

Complete reference for the conda-build recipe format.

## Overview

The `meta.yaml` format is the legacy recipe format using:
- Jinja2 templating with `{{ }}` syntax
- Comment-based selectors `# [platform]`
- Section-based structure

While still widely used, new packages should prefer `recipe.yaml` (v1 format).

## Basic Structure

```yaml
{% set name = "my-package" %}
{% set version = "1.0.0" %}

package:
  name: {{ name|lower }}
  version: {{ version }}

source:
  url: https://example.com/{{ name }}-{{ version }}.tar.gz
  sha256: abc123...

build:
  number: 0
  script: {{ PYTHON }} -m pip install . -vv

requirements:
  host:
    - python
    - pip
  run:
    - python

test:
  imports:
    - mypackage

about:
  home: https://example.com
  license: MIT
  license_file: LICENSE
  summary: Package description

extra:
  recipe-maintainers:
    - username
```

## Jinja2 Variables

### Setting Variables

```yaml
{% set name = "my-package" %}
{% set version = "1.2.3" %}
{% set build_number = 0 %}

# From environment
{% set my_var = environ.get('MY_VAR', 'default') %}

# Computed
{% set major = version.split('.')[0] %}
```

### Using Variables

```yaml
package:
  name: {{ name|lower }}
  version: {{ version }}

source:
  url: https://pypi.org/packages/source/{{ name[0] }}/{{ name }}/{{ name }}-{{ version }}.tar.gz
```

### Jinja2 Filters

```yaml
{{ name|lower }}                   # Lowercase
{{ name|upper }}                   # Uppercase
{{ name|replace("-", "_") }}       # Replace
{{ version|default("1.0.0") }}     # Default value
```

## Package Section

```yaml
package:
  name: {{ name|lower }}
  version: {{ version }}
```

### Version Format
- Follows PEP 440 for Python packages
- No leading zeros in numeric parts
- Use `post` instead of `_` for post-releases

## Source Section

### URL Source

```yaml
source:
  url: https://pypi.org/packages/source/{{ name[0] }}/{{ name }}/{{ name }}-{{ version }}.tar.gz
  sha256: abc123def456...
```

### Multiple Sources

```yaml
source:
  - url: https://example.com/main.tar.gz
    sha256: abc123...
    folder: main

  - url: https://example.com/extra.tar.gz
    sha256: def456...
    folder: extra
```

### Git Source

```yaml
source:
  git_url: https://github.com/org/repo.git
  git_rev: v{{ version }}
  git_depth: 1                     # Shallow clone
```

### Patches

```yaml
source:
  url: https://example.com/source.tar.gz
  sha256: abc123...
  patches:
    - fix-build.patch
    - 0001-add-feature.patch
```

## Build Section

### Basic Build

```yaml
build:
  number: 0
  script: {{ PYTHON }} -m pip install . -vv --no-deps --no-build-isolation
```

### Multi-line Script

```yaml
build:
  script:
    - mkdir build
    - cd build
    - cmake ..
    - make -j${CPU_COUNT}
    - make install
```

### Platform-Specific Scripts

```yaml
build:
  script: build.sh   # [unix]
  script: bld.bat    # [win]
```

### Noarch

```yaml
build:
  noarch: python     # Pure Python
  # OR
  noarch: generic    # Architecture-independent
```

### Skip Conditions

```yaml
build:
  skip: true  # [win]
  skip: true  # [py<38]
  skip: true  # [linux and aarch64]
```

### Build String

```yaml
build:
  string: py{{ CONDA_PY }}h{{ PKG_HASH }}_{{ PKG_BUILDNUM }}
```

### Entry Points

```yaml
build:
  entry_points:
    - mycli = mypackage.cli:main
    - myserver = mypackage.server:run
```

### Run Exports

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

### Ignore Run Exports

```yaml
build:
  ignore_run_exports:
    - libfoo

  ignore_run_exports_from:
    - {{ compiler('cuda') }}
```

### Error Overlinking

```yaml
build:
  error_overlinking: true          # Default
  error_overdepending: true
```

### Missing DSO Whitelist

```yaml
build:
  missing_dso_whitelist:
    - "*/libcuda.so*"    # [linux]
    - "*/nvcuda.dll"     # [win]
```

## Requirements Section

### Basic Requirements

```yaml
requirements:
  build:
    # Build tools (run on build machine)
    - {{ compiler('c') }}
    - {{ compiler('cxx') }}
    - {{ stdlib('c') }}
    - cmake
    - ninja

  host:
    # Libraries (target platform)
    - python
    - numpy
    - zlib

  run:
    # Runtime dependencies
    - python
    - numpy

  run_constrained:
    # Optional/soft constraints
    - scipy >=1.0
```

### Selector Usage

```yaml
requirements:
  build:
    - {{ compiler('c') }}         # [unix]
    - {{ compiler('m2w64_c') }}   # [win]
  run:
    - __linux                     # [linux]
    - __osx                       # [osx]
    - __win                       # [win]
```

### Pin Expressions

```yaml
requirements:
  host:
    - python {{ python }}
    - numpy {{ numpy }}
  run:
    - python
    - {{ pin_compatible('numpy') }}
```

## Test Section

### Import Test

```yaml
test:
  imports:
    - mypackage
    - mypackage.submodule
```

### Command Test

```yaml
test:
  commands:
    - mycommand --version
    - mycommand --help
    - pip check
```

### Test Requirements

```yaml
test:
  requires:
    - pip
    - pytest
  commands:
    - pip check
    - pytest tests/
```

### Test Files

```yaml
test:
  source_files:
    - tests/
    - conftest.py
  files:
    - test_script.py
```

### Full Test Example

```yaml
test:
  imports:
    - mypackage
  commands:
    - pip check
    - mycommand --version
    - pytest tests/ -v
  requires:
    - pip
    - pytest
  source_files:
    - tests/
```

## Outputs Section (Multi-Output)

### Basic Multi-Output

```yaml
outputs:
  - name: libmypackage
    script: build-lib.sh
    build:
      run_exports:
        - {{ pin_subpackage('libmypackage', max_pin='x.x') }}
    requirements:
      build:
        - {{ compiler('c') }}
        - {{ stdlib('c') }}
    test:
      commands:
        - test -f $PREFIX/lib/libmypackage.so  # [linux]

  - name: mypackage
    script: build-python.sh
    requirements:
      build:
        - python
      host:
        - {{ pin_subpackage('libmypackage', exact=True) }}
        - python
        - pip
      run:
        - {{ pin_subpackage('libmypackage', exact=True) }}
        - python
    test:
      imports:
        - mypackage
```

### Shared Build

```yaml
build:
  number: 0

requirements:
  build:
    - {{ compiler('c') }}
    - {{ stdlib('c') }}
    - cmake

outputs:
  - name: libfoo
    files:
      - lib/libfoo*
      - include/foo/

  - name: foo-dev
    files:
      - lib/cmake/
      - lib/pkgconfig/
```

## About Section

```yaml
about:
  home: https://github.com/org/mypackage
  license: MIT
  license_family: MIT
  license_file: LICENSE
  summary: Short one-line description
  description: |
    Longer multi-line description
    of the package.
  doc_url: https://mypackage.readthedocs.io
  dev_url: https://github.com/org/mypackage
```

### License File

```yaml
about:
  license_file: LICENSE

  # Multiple files
  license_file:
    - LICENSE
    - NOTICE
    - licenses/
```

## Extra Section

```yaml
extra:
  recipe-maintainers:
    - github-username-1
    - github-username-2

  feedstock-name: mypackage
```

## Platform Selectors

### Basic Selectors

```yaml
- package          # [linux]
- package          # [osx]
- package          # [win]
- package          # [unix]    (linux or osx)
```

### Architecture Selectors

```yaml
- package          # [x86_64]
- package          # [aarch64]
- package          # [arm64]   (same as aarch64)
- package          # [ppc64le]
```

### Python Selectors

```yaml
skip: true         # [py<38]
skip: true         # [py>=312]
- package          # [py==310]
```

### Combined Selectors

```yaml
- package          # [linux and x86_64]
- package          # [osx and arm64]
- package          # [unix and not aarch64]
- package          # [win or (linux and x86_64)]
```

### Build Platform Selectors

```yaml
- cross-python_{{ target_platform }}  # [build_platform != target_platform]
```

## Compiler Macros

```yaml
requirements:
  build:
    - {{ compiler('c') }}
    - {{ compiler('cxx') }}
    - {{ compiler('fortran') }}
    - {{ compiler('rust') }}
    - {{ compiler('go') }}
    - {{ compiler('go-cgo') }}
    - {{ stdlib('c') }}            # Required for compiled packages
```

### Windows MinGW-w64

```yaml
requirements:
  build:
    - {{ compiler('m2w64_c') }}    # [win]
    - {{ stdlib('m2w64_c') }}      # [win]
    - m2-base                      # [win]
```

## Pin Functions

### pin_subpackage

```yaml
# Default (x.x.x.x.x.x)
{{ pin_subpackage('pkg') }}

# With max_pin
{{ pin_subpackage('pkg', max_pin='x.x') }}
{{ pin_subpackage('pkg', max_pin='x.x.x') }}

# Exact version
{{ pin_subpackage('pkg', exact=True) }}

# With min_pin
{{ pin_subpackage('pkg', min_pin='x.x', max_pin='x.x.x') }}
```

### pin_compatible

```yaml
# In requirements.run
{{ pin_compatible('numpy') }}
{{ pin_compatible('numpy', max_pin='x.x') }}
```

## CFEP-25 Compliance

For `noarch: python` packages:

```yaml
{% set python_min = "3.10" %}

build:
  noarch: python

requirements:
  host:
    - python {{ python_min }}
    - pip
  run:
    - python >={{ python_min }}

test:
  requires:
    - python {{ python_min }}
```

Override minimum:
```yaml
# conda_build_config.yaml
python_min:
  - "3.10"
```

## Complete Example

```yaml
{% set name = "example-package" %}
{% set version = "2.1.0" %}

package:
  name: {{ name|lower }}
  version: {{ version }}

source:
  url: https://pypi.org/packages/source/{{ name[0] }}/{{ name }}/{{ name }}-{{ version }}.tar.gz
  sha256: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef

build:
  number: 0
  noarch: python
  script: {{ PYTHON }} -m pip install . -vv --no-deps --no-build-isolation
  entry_points:
    - example-cli = example_package.cli:main

requirements:
  host:
    - python {{ python_min }}
    - pip
    - hatchling
  run:
    - python >={{ python_min }}
    - click >=8.0
    - rich >=12.0
  run_constrained:
    - optional-dep >=1.0

test:
  imports:
    - example_package
    - example_package.cli
  commands:
    - pip check
    - example-cli --version
    - example-cli --help
  requires:
    - pip

about:
  home: https://github.com/org/example-package
  license: MIT
  license_family: MIT
  license_file: LICENSE
  summary: An example Python package
  description: |
    This is an example package demonstrating
    the meta.yaml format for conda-forge.
  doc_url: https://example-package.readthedocs.io
  dev_url: https://github.com/org/example-package

extra:
  recipe-maintainers:
    - maintainer1
    - maintainer2
```

## References

- [conda-build Documentation](https://docs.conda.io/projects/conda-build/)
- [conda-forge Guidelines](https://conda-forge.org/docs/maintainer/guidelines/)
- [CFEP-25: python_min](https://github.com/conda-forge/cfep/blob/main/cfep-25.md)
