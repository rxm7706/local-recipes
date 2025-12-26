# Jinja Functions Reference

Comprehensive guide for templating functions in conda recipes.

## Syntax Comparison

| Feature | recipe.yaml (v1) | meta.yaml (legacy) |
|---------|------------------|---------------------|
| Variables | `${{ var }}` | `{{ var }}` |
| Set variable | `context:` section | `{% set var = value %}` |
| Conditionals | `if/then/else` YAML | `{% if %}...{% endif %}` |
| Comments | YAML comments `#` | `{# comment #}` |

## Built-in Variables

### Build Environment

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `PYTHON` | Python interpreter path | `/path/to/python` |
| `PREFIX` | Install prefix | `/path/to/prefix` |
| `SRC_DIR` | Source directory | `/path/to/src` |
| `RECIPE_DIR` | Recipe directory | `/path/to/recipe` |
| `BUILD_PREFIX` | Build environment prefix | `/path/to/build` |
| `CPU_COUNT` | Available CPU cores | `8` |

### Platform Detection

| Variable | Description |
|----------|-------------|
| `linux` | True on Linux |
| `osx` | True on macOS |
| `win` | True on Windows |
| `unix` | True on Linux/macOS |
| `x86_64` | True on 64-bit x86 |
| `aarch64` | True on ARM64 |

### Extension Variables

| Variable | Linux | macOS | Windows |
|----------|-------|-------|---------|
| `shlib_ext` | `.so` | `.dylib` | `.dll` |
| `executable_ext` | `` | `` | `.exe` |

## Context Section (recipe.yaml)

### Basic Variables

```yaml
context:
  name: my-package
  version: "1.2.3"
  python_min: "3.10"
  build_number: 0

package:
  name: ${{ name | lower }}
  version: ${{ version }}

build:
  number: ${{ build_number }}
```

### Computed Values

```yaml
context:
  version: "1.2.3"
  major_minor: ${{ version.split('.')[0:2] | join('.') }}
  first_letter: ${{ name[0] }}

source:
  url: https://pypi.org/packages/source/${{ first_letter }}/${{ name }}/${{ name }}-${{ version }}.tar.gz
```

### Platform-Conditional Context

```yaml
context:
  name: mylib
  lib_ext: ${{ ".dylib" if osx else ".so" if linux else ".dll" }}
  lib_prefix: ${{ "" if win else "lib" }}

tests:
  - package_contents:
      lib:
        - ${{ lib_prefix }}${{ name }}${{ lib_ext }}
```

## Jinja Set Statements (meta.yaml)

### Basic Variables

```yaml
{% set name = "my-package" %}
{% set version = "1.2.3" %}
{% set python_min = "3.10" %}

package:
  name: {{ name|lower }}
  version: {{ version }}
```

### From Environment

```yaml
{% set version = environ.get('PKG_VERSION', '1.0.0') %}
{% set build_number = environ.get('BUILD_NUMBER', 0)|int %}
```

### Computed Values

```yaml
{% set name = "my-package" %}
{% set version = "1.2.3" %}
{% set major = version.split('.')[0] %}
{% set minor = version.split('.')[1] %}

about:
  summary: Package version {{ major }}.{{ minor }}
```

### Conditional Variables

```yaml
{% set build_number = 0 %}
{% set cuda_build_offset = 200 %}

build:
  number: {{ build_number + cuda_build_offset }}  # [cuda_compiler_version != "None"]
  number: {{ build_number }}                       # [cuda_compiler_version == "None"]
```

## String Filters

### Common Filters

| Filter | Description | Example |
|--------|-------------|---------|
| `lower` | Lowercase | `${{ "ABC" \| lower }}` → `abc` |
| `upper` | Uppercase | `${{ "abc" \| upper }}` → `ABC` |
| `replace` | Replace chars | `${{ "a-b" \| replace("-", "_") }}` → `a_b` |
| `default` | Default value | `${{ var \| default("none") }}` |
| `trim` | Strip whitespace | `${{ " abc " \| trim }}` → `abc` |

### recipe.yaml Examples

```yaml
context:
  name: My-Package

package:
  name: ${{ name | lower | replace("-", "_") }}
  # Result: my_package
```

### meta.yaml Examples

```yaml
{% set name = "My-Package" %}

package:
  name: {{ name|lower|replace("-", "_") }}
  # Result: my_package
```

## Version Manipulation

### Splitting Versions

```yaml
# recipe.yaml
context:
  version: "1.2.3"
  major: ${{ version.split('.')[0] }}
  minor: ${{ version.split('.')[1] }}
  patch: ${{ version.split('.')[2] }}

# meta.yaml
{% set version = "1.2.3" %}
{% set major = version.split('.')[0] %}
{% set minor = version.split('.')[1] %}
```

### Version to Build String

```yaml
# recipe.yaml
build:
  string: py${{ python | version_to_buildstring }}h${{ hash }}_${{ number }}
  # Result: py312h1234abc_0

# meta.yaml
build:
  string: py{{ CONDA_PY }}h{{ PKG_HASH }}_{{ PKG_BUILDNUM }}
```

## Compiler Functions

### Basic Compilers

```yaml
# recipe.yaml
requirements:
  build:
    - ${{ compiler("c") }}       # C compiler
    - ${{ compiler("cxx") }}     # C++ compiler
    - ${{ compiler("fortran") }} # Fortran compiler
    - ${{ stdlib("c") }}         # C standard library

# meta.yaml
requirements:
  build:
    - {{ compiler('c') }}
    - {{ compiler('cxx') }}
    - {{ compiler('fortran') }}
    - {{ stdlib('c') }}
```

### Rust Compiler

```yaml
# recipe.yaml
requirements:
  build:
    - ${{ compiler("rust") }}

# meta.yaml
requirements:
  build:
    - {{ compiler('rust') }}
```

### Go Compilers

```yaml
# recipe.yaml
requirements:
  build:
    - ${{ compiler("go") }}      # Pure Go (no CGO)
    - ${{ compiler("go-cgo") }}  # Go with CGO support

# meta.yaml
requirements:
  build:
    - {{ compiler('go') }}
    - {{ compiler('go-cgo') }}
```

### CUDA Compiler

```yaml
# recipe.yaml
requirements:
  build:
    - ${{ compiler("cuda") }}

# meta.yaml
requirements:
  build:
    - {{ compiler('cuda') }}
```

### Windows MinGW-w64

```yaml
# recipe.yaml
requirements:
  build:
    - if: win
      then:
        - ${{ compiler("m2w64_c") }}
        - ${{ stdlib("m2w64_c") }}

# meta.yaml
requirements:
  build:
    - {{ compiler('m2w64_c') }}   # [win]
    - {{ stdlib('m2w64_c') }}     # [win]
```

## Pin Functions

### pin_subpackage

Pin to another output in the same recipe.

```yaml
# recipe.yaml
requirements:
  run:
    # Default (full version)
    - ${{ pin_subpackage("libfoo") }}

    # With upper bound
    - ${{ pin_subpackage("libfoo", upper_bound="x.x") }}
    - ${{ pin_subpackage("libfoo", upper_bound="x.x.x") }}

    # Exact match
    - ${{ pin_subpackage("libfoo", exact=true) }}

    # With lower bound
    - ${{ pin_subpackage("libfoo", lower_bound="x.x", upper_bound="x.x.x") }}

# meta.yaml
requirements:
  run:
    - {{ pin_subpackage('libfoo') }}
    - {{ pin_subpackage('libfoo', max_pin='x.x') }}
    - {{ pin_subpackage('libfoo', max_pin='x.x.x') }}
    - {{ pin_subpackage('libfoo', exact=True) }}
    - {{ pin_subpackage('libfoo', min_pin='x.x', max_pin='x.x.x') }}
```

### pin_compatible

Pin to a package from host requirements.

```yaml
# recipe.yaml
requirements:
  host:
    - numpy
  run:
    - ${{ pin_compatible("numpy") }}
    - ${{ pin_compatible("numpy", upper_bound="x.x") }}

# meta.yaml
requirements:
  host:
    - numpy
  run:
    - {{ pin_compatible('numpy') }}
    - {{ pin_compatible('numpy', max_pin='x.x') }}
```

### Pin Bound Syntax

| Pattern | Meaning | Example for 1.2.3 |
|---------|---------|-------------------|
| `x` | Major only | `>=1,<2` |
| `x.x` | Major.minor | `>=1.2,<1.3` |
| `x.x.x` | Full version | `>=1.2.3,<1.2.4` |
| `exact=true` | Exact match | `==1.2.3` |

## CDT Function

Core Development Toolkit packages (Linux only).

```yaml
# recipe.yaml
requirements:
  build:
    - if: linux
      then: ${{ cdt("mesa-libgl-devel") }}

# meta.yaml
requirements:
  build:
    - {{ cdt('mesa-libgl-devel') }}  # [linux]
```

## Environment Access

### recipe.yaml

```yaml
context:
  # Get environment variable
  my_var: ${{ env.get("MY_VAR") }}

  # With default
  my_var: ${{ env.get("MY_VAR", "default_value") }}

  # Boolean check
  enable_feature: ${{ env.get("ENABLE_FEATURE", "0") == "1" }}
```

### meta.yaml

```yaml
{% set my_var = environ.get('MY_VAR', 'default_value') %}
{% set enable_feature = environ.get('ENABLE_FEATURE', '0') == '1' %}

build:
  script_env:
    - MY_VAR={{ my_var }}
```

## Hash Function

Generate short hash for build string.

```yaml
# recipe.yaml
build:
  string: py${{ python | version_to_buildstring }}h${{ hash }}_${{ number }}

# meta.yaml
build:
  string: py{{ CONDA_PY }}h{{ PKG_HASH }}_{{ PKG_BUILDNUM }}
```

## Match Function

Version matching in conditionals.

```yaml
# recipe.yaml
requirements:
  run:
    - if: match(python, ">=3.10")
      then: tomli
```

## URL Helpers

### PyPI Source URL

```yaml
# recipe.yaml
context:
  name: requests
  version: "2.31.0"

source:
  url: https://pypi.org/packages/source/${{ name[0] }}/${{ name }}/${{ name }}-${{ version }}.tar.gz

# meta.yaml
{% set name = "requests" %}
{% set version = "2.31.0" %}

source:
  url: https://pypi.org/packages/source/{{ name[0] }}/{{ name }}/{{ name }}-{{ version }}.tar.gz
```

### GitHub Release URL

```yaml
# recipe.yaml
context:
  name: myproject
  version: "1.0.0"

source:
  url: https://github.com/org/${{ name }}/archive/refs/tags/v${{ version }}.tar.gz

# meta.yaml
source:
  url: https://github.com/org/{{ name }}/archive/refs/tags/v{{ version }}.tar.gz
```

## Conditional Blocks (meta.yaml only)

### If Statement

```yaml
{% if cuda_compiler_version != "None" %}
requirements:
  build:
    - {{ compiler('cuda') }}
{% endif %}
```

### If-Else

```yaml
{% if python_impl == "pypy" %}
  - pypy3
{% else %}
  - python
{% endif %}
```

### Loop

```yaml
{% set tests_to_skip = "_not_a_real_test" %}
{% for skip_test in ["test_network", "test_slow", "test_gpu"] %}
{% set tests_to_skip = tests_to_skip + " or " + skip_test %}
{% endfor %}

test:
  commands:
    - pytest -k "not ({{ tests_to_skip }})"
```

## Build Number Manipulation

### Variant Prioritization

```yaml
# meta.yaml
{% set build_number = 0 %}

build:
  # CUDA builds get higher priority
  number: {{ build_number + 200 }}  # [cuda_compiler_version != "None"]
  # MKL builds get medium priority
  number: {{ build_number + 100 }}  # [blas_impl == "mkl"]
  # Default
  number: {{ build_number }}

# recipe.yaml
context:
  build_number: 0
  cuda_offset: ${{ 200 if cuda_compiler_version != "None" else 0 }}
  blas_offset: ${{ 100 if blas_impl == "mkl" else 0 }}

build:
  number: ${{ build_number + cuda_offset + blas_offset }}
```

## Test Skip Patterns

### Dynamic Skip List (meta.yaml)

```yaml
{% set tests_to_skip = "_not_a_real_test" %}
{% set tests_to_skip = tests_to_skip + " or test_network" %}
{% set tests_to_skip = tests_to_skip + " or test_slow" %}  # [aarch64]
{% set tests_to_skip = tests_to_skip + " or test_gpu" %}   # [cuda_compiler_version == "None"]

test:
  commands:
    - pytest -k "not ({{ tests_to_skip }})" tests/
```

## Complete Examples

### Python Package (recipe.yaml)

```yaml
context:
  name: example-package
  version: "2.0.0"
  python_min: "3.10"

package:
  name: ${{ name | lower }}
  version: ${{ version }}

source:
  url: https://pypi.org/packages/source/${{ name[0] }}/${{ name }}/${{ name }}-${{ version }}.tar.gz
  sha256: abc123...

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
    - python >=${{ python_min }}

tests:
  - python:
      imports:
        - ${{ name | replace("-", "_") }}
      pip_check: true
```

### Python Package (meta.yaml)

```yaml
{% set name = "example-package" %}
{% set version = "2.0.0" %}

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
    - hatchling
  run:
    - python >={{ python_min }}

test:
  imports:
    - {{ name|replace("-", "_") }}
  commands:
    - pip check
  requires:
    - pip

about:
  home: https://github.com/org/{{ name }}
  license: MIT
  license_file: LICENSE
  summary: An example package

extra:
  recipe-maintainers:
    - maintainer
```

## References

- [rattler-build Variables](https://rattler-build.prefix.dev/latest/reference/jinja/)
- [conda-build Templates](https://docs.conda.io/projects/conda-build/en/latest/resources/define-metadata.html#templating-with-jinja)
- [Jinja2 Documentation](https://jinja.palletsprojects.com/)
