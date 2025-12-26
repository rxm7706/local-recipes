# Version Pinning Reference

Comprehensive guide for dependency version pinning in conda recipes.

## Overview

Version pinning ensures:
- **Reproducible builds**: Same dependencies across builds
- **ABI compatibility**: Correct library versions at runtime
- **Solver performance**: Constrained solution space

## Pinning Hierarchy

```
Global Pins (conda-forge-pinning)
    ↓
feedstock conda_build_config.yaml
    ↓
recipe conda_build_config.yaml
    ↓
inline requirements
```

Higher levels override lower levels.

## Pin Expression Syntax

### Basic Constraints

| Expression | Meaning |
|------------|---------|
| `>=1.0` | Version 1.0 or newer |
| `<2.0` | Version before 2.0 |
| `>=1.0,<2.0` | Between 1.0 and 2.0 |
| `==1.2.3` | Exactly 1.2.3 |
| `!=1.2.0` | Not version 1.2.0 |
| `1.0.*` | Any 1.0.x version |

### Combined Constraints

```yaml
requirements:
  run:
    - numpy >=1.20,<2.0
    - python >=3.10,<3.13
    - click >=8.0,<9
```

## conda_build_config.yaml

### Global Pins (Root Level)

```yaml
# conda_build_config.yaml (root of repo)
python:
  - "3.10"
  - "3.11"
  - "3.12"

numpy:
  - "1.26"
  - "2.0"

python_min:
  - "3.10"
```

### Recipe-Specific Override

```yaml
# recipes/mypackage/conda_build_config.yaml
python_min:
  - "3.11"  # Override global 3.10 minimum

numpy:
  - "2.0"   # Only build against numpy 2.0
```

### Pin Run As Build

Propagate build-time version to runtime:

```yaml
pin_run_as_build:
  python:
    min_pin: x.x
    max_pin: x.x
  numpy:
    min_pin: x.x
    max_pin: x.x
```

## Global Pinning (conda-forge-pinning)

conda-forge maintains global pins at:
https://github.com/conda-forge/conda-forge-pinning-feedstock

Key pins include:
- Python versions
- NumPy versions
- Compiler versions
- CUDA versions

### Checking Current Pins

```bash
# View pinning package
mamba search conda-forge-pinning -c conda-forge

# View specific pin
curl -s https://raw.githubusercontent.com/conda-forge/conda-forge-pinning-feedstock/main/recipe/conda_build_config.yaml | grep -A5 "^python:"
```

## pin_subpackage

Pin outputs within the same recipe.

### recipe.yaml Syntax

```yaml
requirements:
  run:
    # Default - pins to exact build
    - ${{ pin_subpackage("libmypackage") }}

    # Upper bound only
    - ${{ pin_subpackage("libmypackage", upper_bound="x.x") }}
    - ${{ pin_subpackage("libmypackage", upper_bound="x.x.x") }}
    - ${{ pin_subpackage("libmypackage", upper_bound="x") }}

    # Exact pin
    - ${{ pin_subpackage("libmypackage", exact=true) }}

    # Lower and upper bounds
    - ${{ pin_subpackage("libmypackage", lower_bound="x.x", upper_bound="x.x.x") }}
```

### meta.yaml Syntax

```yaml
requirements:
  run:
    - {{ pin_subpackage('libmypackage') }}
    - {{ pin_subpackage('libmypackage', max_pin='x.x') }}
    - {{ pin_subpackage('libmypackage', max_pin='x.x.x') }}
    - {{ pin_subpackage('libmypackage', exact=True) }}
    - {{ pin_subpackage('libmypackage', min_pin='x.x', max_pin='x.x.x') }}
```

### Bound Examples

For package version `1.2.3`:

| Bound | Result |
|-------|--------|
| `x` | `>=1,<2` |
| `x.x` | `>=1.2,<1.3` |
| `x.x.x` | `>=1.2.3,<1.2.4` |
| `exact=true` | `==1.2.3` |

## pin_compatible

Pin to a package from host requirements.

### recipe.yaml Syntax

```yaml
requirements:
  host:
    - numpy
  run:
    - ${{ pin_compatible("numpy") }}
    - ${{ pin_compatible("numpy", upper_bound="x.x") }}
    - ${{ pin_compatible("numpy", lower_bound="x.x", upper_bound="x.x.x") }}
```

### meta.yaml Syntax

```yaml
requirements:
  host:
    - numpy
  run:
    - {{ pin_compatible('numpy') }}
    - {{ pin_compatible('numpy', max_pin='x.x') }}
```

## run_exports

Automatically add runtime dependencies when package is used.

### Strong vs Weak

| Type | When applied |
|------|--------------|
| `strong` | Always propagated to run |
| `weak` | Propagated to run unless overridden |

### recipe.yaml

```yaml
build:
  run_exports:
    strong:
      - ${{ pin_subpackage(name, upper_bound="x.x") }}
    weak:
      - ${{ pin_subpackage(name, upper_bound="x") }}
```

Or in requirements section:

```yaml
requirements:
  run_exports:
    strong:
      - ${{ pin_subpackage(name, upper_bound="x.x") }}
```

### meta.yaml

```yaml
build:
  run_exports:
    - {{ pin_subpackage(name, max_pin='x.x') }}

  # OR with strength
  run_exports:
    strong:
      - {{ pin_subpackage(name, max_pin='x.x') }}
    weak:
      - {{ pin_subpackage(name, max_pin='x') }}
```

## Ignoring run_exports

Override automatic propagation.

### recipe.yaml

```yaml
requirements:
  ignore_run_exports:
    by_name:
      - libfoo           # Ignore this package's exports
      - libbar
    from_package:
      - ${{ compiler("cuda") }}  # Ignore all from CUDA
```

### meta.yaml

```yaml
build:
  ignore_run_exports:
    - libfoo
    - libbar

  ignore_run_exports_from:
    - {{ compiler('cuda') }}
```

## CFEP-25: python_min

Required for `noarch: python` packages.

### recipe.yaml

```yaml
context:
  python_min: "3.10"

build:
  noarch: python

requirements:
  host:
    - python ${{ python_min }}.*
    - pip
  run:
    - python >=${{ python_min }}
```

### meta.yaml

```yaml
build:
  noarch: python

requirements:
  host:
    - python {{ python_min }}
    - pip
  run:
    - python >={{ python_min }}
```

### Override python_min

```yaml
# recipes/mypackage/conda_build_config.yaml
python_min:
  - "3.11"  # Package requires Python 3.11+
```

## Common Pinning Patterns

### Multi-Output Library

```yaml
# recipe.yaml
outputs:
  - package:
      name: libmypackage
    build:
      run_exports:
        - ${{ pin_subpackage("libmypackage", upper_bound="x.x") }}

  - package:
      name: mypackage
    requirements:
      host:
        - ${{ pin_subpackage("libmypackage", exact=true) }}
      run:
        - ${{ pin_subpackage("libmypackage", exact=true) }}
```

```yaml
# meta.yaml
outputs:
  - name: libmypackage
    build:
      run_exports:
        - {{ pin_subpackage('libmypackage', max_pin='x.x') }}

  - name: mypackage
    requirements:
      host:
        - {{ pin_subpackage('libmypackage', exact=True) }}
      run:
        - {{ pin_subpackage('libmypackage', exact=True) }}
```

### NumPy ABI Compatibility

```yaml
# recipe.yaml
requirements:
  host:
    - python
    - numpy
  run:
    - python
    - ${{ pin_compatible("numpy") }}

# meta.yaml
requirements:
  host:
    - python
    - numpy
  run:
    - python
    - {{ pin_compatible('numpy') }}
```

### C/C++ Library ABI

```yaml
# recipe.yaml
build:
  run_exports:
    # Major version compatibility
    - ${{ pin_subpackage(name, upper_bound="x") }}

# meta.yaml
build:
  run_exports:
    - {{ pin_subpackage(name, max_pin='x') }}
```

### Strict Compatibility

```yaml
# recipe.yaml
build:
  run_exports:
    strong:
      - ${{ pin_subpackage(name, exact=true) }}

# meta.yaml
build:
  run_exports:
    strong:
      - {{ pin_subpackage(name, exact=True) }}
```

## run_constrained

Optional/soft dependencies with version constraints.

### recipe.yaml

```yaml
requirements:
  run_constrained:
    - scipy >=1.0           # If scipy installed, must be >=1.0
    - matplotlib >=3.0      # If matplotlib installed, must be >=3.0
```

### meta.yaml

```yaml
requirements:
  run_constrained:
    - scipy >=1.0
    - matplotlib >=3.0
```

## Variant Configuration

### Matrix Builds

```yaml
# conda_build_config.yaml
python:
  - "3.10"
  - "3.11"
  - "3.12"

numpy:
  - "1.26"
  - "2.0"

# Creates 6 variants: 3 python x 2 numpy
```

### Zip Keys

Build specific combinations only:

```yaml
# conda_build_config.yaml
python:
  - "3.10"
  - "3.11"
  - "3.12"

numpy:
  - "1.26"
  - "1.26"
  - "2.0"

zip_keys:
  - [python, numpy]

# Creates 3 variants: (3.10, 1.26), (3.11, 1.26), (3.12, 2.0)
```

### Excluding Combinations

```yaml
# conda_build_config.yaml
python:
  - "3.10"
  - "3.11"
  - "3.12"

# Skip Python 3.10 on Windows
skip:
  - python == "3.10"  # [win]
```

## Platform-Specific Pins

```yaml
# conda_build_config.yaml
# Different CUDA versions per platform
cuda_compiler_version:
  - "11.8"          # [linux]
  - "12.0"          # [linux]
  - "11.8"          # [win]

# macOS SDK
MACOSX_SDK_VERSION:
  - "11.0"          # [osx and arm64]
  - "10.15"         # [osx and x86_64]
```

## CI Support Files

Platform-specific configs in `.ci_support/`:

```
.ci_support/
├── linux_64_.yaml
├── linux_aarch64_.yaml
├── osx_64_.yaml
├── osx_arm64_.yaml
├── win_64_.yaml
└── linux_64_python3.10.yaml
```

### Example ci_support file

```yaml
# .ci_support/linux_64_python3.12.yaml
c_compiler:
  - gcc
c_compiler_version:
  - "12"
cxx_compiler:
  - gxx
cxx_compiler_version:
  - "12"
python:
  - "3.12"
target_platform:
  - linux-64
```

## Debugging Pins

### Render Recipe

```bash
# rattler-build
rattler-build build -r recipe.yaml --render-only

# conda-build
conda-render recipes/mypackage
```

### Check Solver

```bash
# Check dependencies
mamba repoquery depends mypackage

# Check what needs this package
mamba repoquery whoneeds mypackage

# Solve environment
mamba create -n test --dry-run mypackage
```

### View Package Metadata

```bash
# From conda-forge
curl -s "https://conda.anaconda.org/conda-forge/linux-64/mypackage-1.0.0-py312h123_0.conda" | tar -xO info/index.json | jq
```

## Best Practices

### 1. Use Global Pins When Possible

Let conda-forge-pinning handle common dependencies:
```yaml
requirements:
  host:
    - python      # Uses global python versions
    - numpy       # Uses global numpy versions
```

### 2. Pin Libraries by Major.Minor

```yaml
build:
  run_exports:
    - ${{ pin_subpackage(name, upper_bound="x.x") }}
```

### 3. Use exact=true for Co-Built Outputs

```yaml
outputs:
  - package:
      name: libfoo
  - package:
      name: foo
    requirements:
      run:
        - ${{ pin_subpackage("libfoo", exact=true) }}
```

### 4. Document Version Constraints

```yaml
requirements:
  run:
    # Requires numpy 2.0+ for new API
    - numpy >=2.0
    # Python 3.11+ for tomllib
    - python >=3.11
```

### 5. Test Pin Ranges

Before submission:
```bash
# Test with oldest supported version
mamba create -n test python=3.10 numpy=1.26 mypackage

# Test with newest
mamba create -n test python=3.12 numpy=2.0 mypackage
```

## Common Issues

### Pin Too Strict

```yaml
# Problem: exact pins break on updates
requirements:
  run:
    - numpy ==1.26.0

# Solution: use range
requirements:
  run:
    - numpy >=1.26,<2.0
```

### Pin Too Loose

```yaml
# Problem: ABI breaks on major versions
requirements:
  run:
    - libfoo

# Solution: add constraint
requirements:
  run:
    - libfoo >=1.0,<2.0
```

### Missing run_exports

```yaml
# Problem: downstream packages don't get runtime dep
build:
  # No run_exports

# Solution: add run_exports for libraries
build:
  run_exports:
    - ${{ pin_subpackage(name, upper_bound="x.x") }}
```

## References

- [conda-forge Pinning Policy](https://conda-forge.org/docs/maintainer/pinning_deps/)
- [conda-forge-pinning Feedstock](https://github.com/conda-forge/conda-forge-pinning-feedstock)
- [CFEP-25: python_min](https://github.com/conda-forge/cfep/blob/main/cfep-25.md)
- [rattler-build Pinning](https://rattler-build.prefix.dev/latest/reference/variants/)
