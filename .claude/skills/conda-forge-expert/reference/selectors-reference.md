# Platform Selectors Reference

Comprehensive guide for conditional logic in conda recipes.

## Overview

Selectors allow recipes to adapt based on:
- **Operating System**: Linux, macOS, Windows
- **Architecture**: x86_64, ARM64, PowerPC
- **Python Version**: py>=39, py<312
- **Build Configuration**: CUDA, MPI variants

## Format Comparison

| Feature | recipe.yaml (v1) | meta.yaml (legacy) |
|---------|------------------|---------------------|
| Syntax | `if/then/else` blocks | `# [selector]` comments |
| Validation | YAML-validated | Comment-based (no validation) |
| Nesting | Full YAML nesting | Limited |
| Boolean ops | `and`, `or`, `not` | `and`, `or`, `not` |

## recipe.yaml Selectors (v1 Format)

### Basic Syntax

```yaml
requirements:
  build:
    - if: unix
      then: make
    - if: win
      then: m2-make
```

### With else clause

```yaml
build:
  script:
    - if: unix
      then: bash ${{ RECIPE_DIR }}/build.sh
      else: call %RECIPE_DIR%\bld.bat
```

### Multiple items in then/else

```yaml
requirements:
  build:
    - if: unix
      then:
        - ${{ compiler("c") }}
        - ${{ stdlib("c") }}
        - make
    - if: win
      then:
        - ${{ compiler("m2w64_c") }}
        - ${{ stdlib("m2w64_c") }}
        - m2-make
```

### Nested conditions

```yaml
requirements:
  run:
    - if: linux
      then:
        - if: x86_64
          then: intel-openmp
          else: llvm-openmp
    - if: osx
      then: llvm-openmp
```

### Skip conditions

```yaml
build:
  skip:
    - win                          # Skip on Windows
    - py < 39                      # Skip Python < 3.9
    - linux and aarch64            # Skip Linux ARM64
    - osx and x86_64               # Skip macOS Intel
```

## meta.yaml Selectors (Legacy Format)

### Basic Syntax

```yaml
requirements:
  build:
    - make          # [unix]
    - m2-make       # [win]
```

### Boolean Operators

```yaml
requirements:
  build:
    - package                      # [linux]
    - package                      # [linux or osx]
    - package                      # [unix and x86_64]
    - package                      # [not win]
    - package                      # [linux and not aarch64]
```

### Complex Expressions

```yaml
build:
  skip: true  # [win or (linux and aarch64)]
  skip: true  # [py<38 or py>=313]
```

### Multi-line with selectors

```yaml
source:
  url: https://example.com/source-{{ version }}.tar.gz  # [unix]
  url: https://example.com/source-{{ version }}.zip     # [win]
  sha256: abc123...  # [unix]
  sha256: def456...  # [win]
```

## Platform Variables

### Operating System

| Variable | True on | Description |
|----------|---------|-------------|
| `linux` | Linux | Any Linux distribution |
| `osx` | macOS | Any macOS version |
| `win` | Windows | Any Windows version |
| `unix` | Linux, macOS | Unix-like systems |

### Architecture

| Variable | True on | Description |
|----------|---------|-------------|
| `x86` | 32-bit x86 | Legacy 32-bit Intel |
| `x86_64` | 64-bit x86 | Intel/AMD 64-bit |
| `aarch64` | 64-bit ARM | ARM64 (Linux) |
| `arm64` | 64-bit ARM | ARM64 (alias for aarch64) |
| `ppc64le` | PowerPC 64 LE | IBM POWER systems |
| `s390x` | IBM Z | IBM mainframe |

### Python Version

| Selector | Meaning |
|----------|---------|
| `py==39` | Python 3.9 exactly |
| `py>=39` | Python 3.9 or newer |
| `py<312` | Python before 3.12 |
| `py>=310,<312` | Python 3.10 or 3.11 |

### Build vs Target Platform

| Variable | Description |
|----------|-------------|
| `build_platform` | Platform where build runs |
| `target_platform` | Platform for output package |

```yaml
# Cross-compilation support
requirements:
  build:
    - if: build_platform != target_platform
      then:
        - python
        - cross-python_${{ target_platform }}
```

Legacy format:
```yaml
requirements:
  build:
    - python                                     # [build_platform != target_platform]
    - cross-python_{{ target_platform }}         # [build_platform != target_platform]
```

## Common Patterns

### Platform-specific dependencies

```yaml
# recipe.yaml
requirements:
  run:
    - if: linux
      then: __linux
    - if: osx
      then: __osx >=10.13
    - if: win
      then: __win

# meta.yaml
requirements:
  run:
    - __linux               # [linux]
    - __osx >=10.13         # [osx]
    - __win                 # [win]
```

### Windows MinGW-w64

```yaml
# recipe.yaml
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
        - m2-base

# meta.yaml
requirements:
  build:
    - {{ compiler('c') }}         # [unix]
    - {{ stdlib('c') }}           # [unix]
    - {{ compiler('m2w64_c') }}   # [win]
    - {{ stdlib('m2w64_c') }}     # [win]
    - m2-base                     # [win]
```

### Architecture-specific optimizations

```yaml
# recipe.yaml
requirements:
  run:
    - if: x86_64
      then: intel-openmp
    - if: aarch64 or arm64
      then: llvm-openmp

# meta.yaml
requirements:
  run:
    - intel-openmp    # [x86_64]
    - llvm-openmp     # [aarch64 or arm64]
```

### CUDA builds

```yaml
# recipe.yaml
build:
  skip:
    - cuda_compiler_version == "None"

requirements:
  build:
    - ${{ compiler("cuda") }}
  run:
    - __cuda >=${{ cuda_compiler_version_min }}

# meta.yaml
build:
  skip: true  # [cuda_compiler_version == "None"]

requirements:
  build:
    - {{ compiler('cuda') }}
  run:
    - __cuda >={{ cuda_compiler_version_min }}
```

### Platform-specific tests

```yaml
# recipe.yaml
tests:
  - script:
      - if: unix
        then: test -f $PREFIX/lib/libmylib${{ shlib_ext }}
      - if: win
        then: if not exist %LIBRARY_BIN%\mylib.dll exit 1

# meta.yaml
test:
  commands:
    - test -f $PREFIX/lib/libmylib${SHLIB_EXT}      # [unix]
    - if not exist %LIBRARY_BIN%\mylib.dll exit 1   # [win]
```

### Skip architectures

```yaml
# recipe.yaml
build:
  skip:
    - ppc64le                    # No PowerPC support
    - s390x                      # No IBM Z support
    - osx and x86_64             # macOS Intel deprecated

# meta.yaml
build:
  skip: true  # [ppc64le or s390x]
  skip: true  # [osx and x86_64]
```

### Python version constraints

```yaml
# recipe.yaml
build:
  skip:
    - py < 39                    # Requires Python 3.9+
    - py >= 313                  # Not yet compatible with 3.13

# meta.yaml
build:
  skip: true  # [py<39]
  skip: true  # [py>=313]
```

## Context Variables (recipe.yaml only)

Use platform detection in context for computed values:

```yaml
context:
  name: mypackage
  version: "1.0.0"

  # Platform-specific extensions
  shlib_ext: ${{ ".dylib" if osx else ".so" if linux else ".dll" }}
  exec_ext: ${{ "" if unix else ".exe" }}

  # Library prefix
  lib_prefix: ${{ "" if win else "lib" }}

package:
  name: ${{ name }}
  version: ${{ version }}

tests:
  - package_contents:
      lib:
        - ${{ lib_prefix }}mylib${{ shlib_ext }}
```

## Script Selection

### recipe.yaml

```yaml
build:
  script:
    - if: unix
      then: bash ${{ RECIPE_DIR }}/build.sh
    - if: win
      then: call %RECIPE_DIR%\bld.bat
```

### meta.yaml

Two approaches:

**Inline selection:**
```yaml
build:
  script: build.sh   # [unix]
  script: bld.bat    # [win]
```

**Separate scripts (preferred):**
```yaml
build:
  script: run_build.sh   # [unix]
  script: run_build.bat  # [win]
```

Or use automatic detection (files in recipe folder):
- `build.sh` - Used on Unix
- `bld.bat` - Used on Windows

## Environment Variables in Selectors

### recipe.yaml

```yaml
context:
  use_openmp: ${{ env.get("USE_OPENMP", "1") == "1" }}

build:
  script:
    - if: use_openmp and unix
      then: export CFLAGS="$CFLAGS -fopenmp"
```

### meta.yaml

```yaml
{% set use_openmp = environ.get('USE_OPENMP', '1') == '1' %}

build:
  script_env:
    - USE_OPENMP={{ use_openmp }}
```

## Variant-Based Selectors

### CUDA variant

```yaml
# recipe.yaml
build:
  skip:
    - cuda_compiler_version == "None"
  string: cuda${{ cuda_compiler_version | replace(".", "") }}_h${{ hash }}_${{ number }}

# meta.yaml
build:
  skip: true  # [cuda_compiler_version == "None"]
  string: cuda{{ cuda_compiler_version | replace(".", "") }}_h{{ PKG_HASH }}_{{ PKG_BUILDNUM }}
```

### MPI variant

```yaml
# recipe.yaml
build:
  skip:
    - mpi == "nompi"

requirements:
  host:
    - if: mpi != "nompi"
      then: ${{ mpi }}

# meta.yaml
build:
  skip: true  # [mpi == "nompi"]

requirements:
  host:
    - {{ mpi }}  # [mpi != "nompi"]
```

## Debugging Selectors

### Render to check evaluation

```bash
# rattler-build
rattler-build build -r recipe.yaml --render-only --target-platform linux-64
rattler-build build -r recipe.yaml --render-only --target-platform win-64

# conda-build
conda-render recipes/mypackage --variants "{'target_platform': 'linux-64'}"
```

### Common mistakes

1. **Incorrect operator precedence**
   ```yaml
   # Wrong - ambiguous
   skip: true  # [linux and x86_64 or osx]

   # Correct - explicit grouping
   skip: true  # [(linux and x86_64) or osx]
   ```

2. **Missing quotes in recipe.yaml**
   ```yaml
   # Wrong
   skip:
     - cuda_compiler_version == None

   # Correct
   skip:
     - cuda_compiler_version == "None"
   ```

3. **Using py37 instead of py==37**
   ```yaml
   # Old syntax (deprecated)
   skip: true  # [py37]

   # New syntax
   skip: true  # [py==37]
   ```

## Best Practices

1. **Prefer unix over listing linux and osx separately**
   ```yaml
   # Good
   - package  # [unix]

   # Verbose
   - package  # [linux or osx]
   ```

2. **Use explicit platform markers for runtime**
   ```yaml
   run:
     - __linux   # [linux]
     - __osx     # [osx]
     - __win     # [win]
   ```

3. **Group platform logic in recipe.yaml**
   ```yaml
   # Cleaner - grouped by platform
   requirements:
     build:
       - if: unix
         then:
           - ${{ compiler("c") }}
           - make
       - if: win
         then:
           - ${{ compiler("m2w64_c") }}
           - m2-make
   ```

4. **Document complex conditions**
   ```yaml
   build:
     # Skip on Windows ARM64 - not yet supported by upstream
     skip:
       - win and aarch64
   ```

## References

- [rattler-build Selectors](https://rattler-build.prefix.dev/latest/selectors/)
- [conda-build Selectors](https://docs.conda.io/projects/conda-build/en/latest/resources/define-metadata.html#preprocessing-selectors)
- [conda-forge Platform Support](https://conda-forge.org/docs/maintainer/knowledge_base/#platform-support)
