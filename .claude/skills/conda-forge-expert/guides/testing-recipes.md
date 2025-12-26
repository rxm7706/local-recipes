# Testing Recipes Guide

Complete guide for testing conda-forge recipes locally and in CI.

## Testing Hierarchy

```
1. Lint recipe        → Catch syntax/policy errors
2. Render recipe      → Verify variable substitution
3. Build package      → Compile and package
4. Run tests          → Verify functionality
5. Install test       → Check installation works
```

## Quick Test Commands

```bash
# Lint
conda-smithy recipe-lint recipes/my-package

# Render only (check variables)
rattler-build build -r recipe.yaml --render-only

# Full build
rattler-build build -r recipe.yaml -c conda-forge

# Build with debug output
rattler-build build -r recipe.yaml -c conda-forge -vvv
```

## Linting

### Why Lint?

Linting catches:
- Missing required fields
- Policy violations
- Common mistakes
- Best practice issues

### Running Linter

```bash
# Single recipe
conda-smithy recipe-lint recipes/my-package

# Multiple recipes
conda-smithy recipe-lint recipes/*

# Pedantic mode (more warnings)
conda-smithy recipe-lint --pedantic recipes/my-package
```

### Common Lint Errors

| Error | Solution |
|-------|----------|
| `missing license_file` | Add `license_file: LICENSE` |
| `missing maintainers` | Add `recipe-maintainers` in extra |
| `should be noarch` | Add `noarch: python` or justify arch-specific |
| `uses deprecated URL` | Use `pypi.org` not `pypi.io` |
| `missing stdlib` | Add `${{ stdlib("c") }}` with compilers |

## Local Building

### Using rattler-build

```bash
# Basic build
rattler-build build -r recipes/my-package/recipe.yaml -c conda-forge

# Specify target platform
rattler-build build -r recipe.yaml --target-platform linux-64 -c conda-forge
rattler-build build -r recipe.yaml --target-platform osx-arm64 -c conda-forge

# Keep build directory for debugging
rattler-build build -r recipe.yaml --keep-build -c conda-forge

# Render only (no actual build)
rattler-build build -r recipe.yaml --render-only
```

### Using conda-build

```bash
# Basic build
conda-build recipes/my-package -c conda-forge

# With variants
conda-build recipes/my-package -c conda-forge --variants "{'python': '3.12'}"

# Test existing package
conda-build --test /path/to/package.conda

# Keep work directory
conda-build recipes/my-package --keep-old-work
```

### Using build-locally.py

```bash
# Interactive platform selection
python build-locally.py

# Specific platform
python build-locally.py linux64
python build-locally.py win64
python build-locally.py osx64
python build-locally.py osxarm64

# Filter recipes
python build-locally.py --filter "my-*"
```

## Writing Tests

### Python Package Tests (recipe.yaml)

```yaml
tests:
  # Import test
  - python:
      imports:
        - mypackage
        - mypackage.submodule
        - mypackage.utils
      pip_check: true

  # CLI test
  - script:
      - mycommand --version
      - mycommand --help

  # Full test suite
  - script:
      - pytest tests/ -v --tb=short
    requirements:
      run:
        - pytest
        - pytest-cov
    files:
      source:
        - tests/
        - conftest.py
```

### Python Package Tests (meta.yaml)

```yaml
test:
  imports:
    - mypackage
    - mypackage.submodule

  commands:
    - pip check
    - mycommand --version
    - mycommand --help
    - pytest tests/ -v --tb=short

  requires:
    - pip
    - pytest
    - pytest-cov

  source_files:
    - tests/
    - conftest.py
```

### Library Tests (recipe.yaml)

```yaml
tests:
  # Check files exist
  - package_contents:
      lib:
        - libmylib${{ shlib_ext }}
      include:
        - mylib/*.h
      bin:
        - mytool${{ executable_ext }}

  # Run test program
  - script:
      - mytool --version
      - if: unix
        then: test -f $PREFIX/lib/libmylib${{ shlib_ext }}
      - if: win
        then: if not exist %LIBRARY_BIN%\mylib.dll exit 1
```

### Library Tests (meta.yaml)

```yaml
test:
  commands:
    - mytool --version
    - test -f $PREFIX/lib/libmylib${SHLIB_EXT}           # [unix]
    - if not exist %LIBRARY_BIN%\mylib.dll exit 1        # [win]
    - test -f $PREFIX/include/mylib/header.h             # [unix]
```

## Test Strategies

### Minimal Tests (Required)

Every package needs at minimum:

```yaml
# Python
tests:
  - python:
      imports:
        - mypackage
      pip_check: true

# Library
tests:
  - package_contents:
      lib:
        - libmylib${{ shlib_ext }}
```

### Comprehensive Tests

```yaml
tests:
  # 1. Import test
  - python:
      imports:
        - mypackage
        - mypackage.core
        - mypackage.utils
      pip_check: true

  # 2. CLI test
  - script:
      - mypackage --version
      - mypackage --help

  # 3. Unit tests
  - script:
      - pytest tests/unit -v
    requirements:
      run:
        - pytest
    files:
      source:
        - tests/unit/

  # 4. Downstream test
  - downstream:
      - dependent-package
```

### Skip Problematic Tests

```yaml
tests:
  - script:
      # Skip network tests
      - pytest -k "not network" tests/
      # Skip slow tests
      - pytest -m "not slow" tests/
      # Skip GPU tests
      - pytest --ignore=tests/gpu/ tests/
    requirements:
      run:
        - pytest
```

### Platform-Specific Tests

```yaml
# recipe.yaml
tests:
  - script:
      - if: unix
        then:
          - test -f $PREFIX/lib/libfoo.so
          - ldd $PREFIX/lib/libfoo.so
      - if: osx
        then:
          - otool -L $PREFIX/lib/libfoo.dylib
      - if: win
        then:
          - if exist %LIBRARY_BIN%\foo.dll echo OK
```

## Testing Variants

### Test Multiple Python Versions

```bash
# Build for specific Python
rattler-build build -r recipe.yaml -c conda-forge \
  --variant-config <(echo "python: ['3.10']")

rattler-build build -r recipe.yaml -c conda-forge \
  --variant-config <(echo "python: ['3.12']")
```

### Test with conda_build_config.yaml

```yaml
# conda_build_config.yaml for testing
python:
  - "3.10"
  - "3.12"

numpy:
  - "1.26"
  - "2.0"
```

## Debugging Failed Tests

### Inspect Build Environment

```yaml
tests:
  - script:
      # Debug output
      - echo "PREFIX=$PREFIX"
      - echo "PATH=$PATH"
      - which python
      - python --version
      - pip list
      - ls -la $PREFIX/lib/     # [unix]
      # Actual test
      - python -c "import mypackage"
```

### Keep Test Environment

```bash
# conda-build: keep environment
conda-build recipes/my-package --keep-old-work

# Check test env
ls /path/to/conda-bld/my-package_*/work
```

### Interactive Debugging

```bash
# Create test environment manually
mamba create -n test-env -c conda-forge -c local my-package pytest
mamba activate test-env

# Debug interactively
python -c "import mypackage; print(mypackage.__file__)"
pytest tests/ -v --pdb  # Drop into debugger on failure
```

## CI Testing

### View CI Logs

```bash
# GitHub Actions
gh run view --log

# Specific job
gh run view <run-id> --job=<job-id> --log
```

### Restart Failed Tests

```
@conda-forge-admin, please restart ci
```

### Test Configuration

```yaml
# conda-forge.yml
test:
  timeout: 3600  # Increase timeout

azure:
  store_build_artifacts: true  # Save for debugging
```

## Test Best Practices

### 1. Test What Matters

```yaml
# Good: Tests actual functionality
tests:
  - python:
      imports:
        - mypackage
      pip_check: true
  - script:
      - python -c "from mypackage import main_function; main_function()"

# Bad: Tests nothing useful
tests:
  - script:
      - echo "test passed"
```

### 2. Include pip_check

```yaml
tests:
  - python:
      imports:
        - mypackage
      pip_check: true  # Verify all dependencies resolved
```

### 3. Test CLI Tools

```yaml
tests:
  - script:
      - mytool --version  # Verify executable runs
      - mytool --help     # Verify help works
```

### 4. Don't Over-Test

```yaml
# Good: Quick import test
tests:
  - python:
      imports:
        - mypackage

# Excessive: Full test suite in CI
# (Better to run in upstream CI)
tests:
  - script:
      - pytest tests/ -v --cov --cov-report=xml
```

### 5. Handle Test Data

```yaml
tests:
  - script:
      - pytest tests/
    files:
      source:
        - tests/
        - data/test_data.json   # Include test data
```

## Test Matrix

### Testing Checklist

| Test Type | Priority | Example |
|-----------|----------|---------|
| Import | Required | `imports: [mypackage]` |
| pip_check | Required | `pip_check: true` |
| CLI --version | High | `mytool --version` |
| CLI --help | High | `mytool --help` |
| File existence | Medium | `test -f $PREFIX/lib/...` |
| Unit tests | Optional | `pytest tests/unit/` |
| Integration | Optional | `pytest tests/integration/` |

## Resources

- [conda-build Testing](https://docs.conda.io/projects/conda-build/en/latest/resources/define-metadata.html#test-section)
- [rattler-build Tests](https://rattler-build.prefix.dev/latest/reference/recipe_schema/#tests)
- [pytest Documentation](https://docs.pytest.org/)
