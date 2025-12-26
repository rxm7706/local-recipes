# Recipe Templates

Ready-to-use templates for conda-forge recipes across all supported languages.

## Template Structure

Each language folder contains:
- `recipe.yaml` - Modern v1 format (rattler-build)
- `meta.yaml` - Legacy format (conda-build)
- Language-specific build scripts when needed

## Available Templates

| Language | Templates | Use Case |
|----------|-----------|----------|
| **Python** | noarch, compiled, maturin | Pure Python, C extensions, Rust bindings |
| **Rust** | cli, library, pyo3 | CLI tools, libraries, Python bindings |
| **Go** | pure, cgo | Pure Go, CGO with C dependencies |
| **C/C++** | cmake, autotools, meson, header-only | Native libraries and tools |
| **Java** | maven, gradle | JVM applications |
| **.NET** | nuget, source | .NET Core/5+ applications |
| **Node.js** | npm, native | Pure JS and native addons |
| **R** | cran, bioconductor | R packages |
| **Fortran** | f90, f77 | Scientific computing |
| **Ruby** | gem | Ruby packages |
| **Perl** | cpan | Perl modules |
| **Multi-output** | lib-python, lib-cli | Split packages |

## Quick Start

1. Copy the appropriate template to your recipe folder
2. Replace placeholder values (marked with `REPLACE_`)
3. Update checksums and dependencies
4. Run linting: `conda-smithy recipe-lint recipes/mypackage`
5. Build locally: `python build-locally.py`

## Template Variables

Templates use these placeholder patterns:

| Placeholder | Replace With |
|-------------|--------------|
| `REPLACE_NAME` | Package name |
| `REPLACE_VERSION` | Package version |
| `REPLACE_SHA256` | Source checksum |
| `REPLACE_LICENSE` | SPDX license identifier |
| `REPLACE_HOMEPAGE` | Project homepage URL |
| `REPLACE_MAINTAINER` | Your GitHub username |

## Choosing Between Formats

### Use recipe.yaml (v1) when:
- Starting new packages
- Using rattler-build
- Need cleaner YAML syntax
- Complex conditional logic

### Use meta.yaml when:
- Existing feedstock uses it
- Need conda-build specific features
- Migrating gradually

## Common Customizations

### Adding patches
```yaml
source:
  url: ...
  patches:
    - fix-build.patch
```

### Platform-specific dependencies
```yaml
# recipe.yaml
requirements:
  run:
    - if: linux
      then: libgl

# meta.yaml
requirements:
  run:
    - libgl  # [linux]
```

### Skip platforms
```yaml
# recipe.yaml
build:
  skip:
    - win
    - py < 39

# meta.yaml
build:
  skip: true  # [win]
  skip: true  # [py<39]
```

## Testing Templates

All templates include basic tests. Enhance with:

```yaml
# recipe.yaml
tests:
  - python:
      imports:
        - mypackage
      pip_check: true
  - script:
      - pytest tests/ -v
    requirements:
      run:
        - pytest

# meta.yaml
test:
  imports:
    - mypackage
  commands:
    - pip check
    - pytest tests/ -v
  requires:
    - pip
    - pytest
```
