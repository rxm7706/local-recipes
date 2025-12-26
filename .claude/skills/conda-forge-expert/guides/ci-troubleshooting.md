# CI Troubleshooting Guide

Comprehensive guide for diagnosing and fixing conda-forge CI build failures.

## Quick Diagnosis

### Check Build Status

```bash
# View recent CI runs
gh run list --repo conda-forge/my-package-feedstock

# View specific run
gh run view <run-id> --log

# Watch running build
gh run watch
```

### Common Status Indicators

| Status | Meaning | Action |
|--------|---------|--------|
| 🔴 Failed | Build or test error | Check logs |
| 🟡 Pending | Waiting for resources | Wait or re-trigger |
| 🟢 Success | All platforms passed | Ready to merge |
| ⚪ Skipped | Platform not built | Check skip conditions |

## Build Failures

### Dependency Not Found

**Error:**
```
PackagesNotFoundError: The following packages are not available:
  - my-dependency
```

**Causes:**
1. Package doesn't exist on conda-forge
2. Typo in package name
3. Package only on PyPI, not conda

**Solutions:**
```yaml
# 1. Check package exists
mamba search -c conda-forge my-dependency

# 2. Check correct name (PyPI vs conda)
# PyPI: my-package → conda: my_package or my-package

# 3. Submit dependency to conda-forge first
```

### Hash Mismatch

**Error:**
```
SHA256 mismatch:
  Expected: abc123...
  Got: def456...
```

**Causes:**
1. Source file changed upstream
2. Wrong URL (redirect page)
3. Copy/paste error

**Solutions:**
```bash
# Recalculate hash
curl -sL "https://actual-url/file.tar.gz" | sha256sum

# Use -L to follow redirects
curl -sL -o /dev/null -w "%{url_effective}" "https://short-url"
```

### Compiler Errors

**Error:**
```
error: unknown type name 'uint64_t'
error: 'for' loop initial declarations are only allowed in C99 mode
```

**Solutions:**
```yaml
# Add C standard
build:
  script_env:
    - CFLAGS=-std=c99

# Or in CMakeLists.txt
set(CMAKE_C_STANDARD 99)
```

### Missing stdlib

**Error:**
```
Error: Package has compiler but missing stdlib
```

**Solution:**
```yaml
# recipe.yaml
requirements:
  build:
    - ${{ compiler("c") }}
    - ${{ stdlib("c") }}      # ADD THIS

# meta.yaml
requirements:
  build:
    - {{ compiler('c') }}
    - {{ stdlib('c') }}       # ADD THIS
```

### Linker Errors

**Error:**
```
undefined reference to `function_name'
ld: library not found for -lmylib
```

**Solutions:**
```yaml
# Add missing library to host
requirements:
  host:
    - libmylib

# Or add pkg-config
requirements:
  build:
    - pkg-config
```

## Platform-Specific Issues

### Windows

#### CMake/MSBuild Issues

**Error:**
```
MSBuild.exe not found
error MSB4019: The imported project was not found
```

**Solution:**
```yaml
# Use Ninja instead of MSBuild
requirements:
  build:
    - cmake
    - ninja      # NOT msbuild

# In build script
cmake -G "Ninja" ..
```

#### Path Issues

**Error:**
```
The filename or extension is too long
```

**Solution:**
```yaml
# Use shorter paths
build:
  script_env:
    - CONDA_BLD_PATH=C:\bld
```

#### Line Ending Issues

**Error:**
```
/bin/bash^M: bad interpreter
```

**Solution:**
```bash
# Convert to Unix line endings
dos2unix build.sh
```

### macOS

#### SDK Version Issues

**Error:**
```
error: 'TARGET_OS_OSX' is not defined
SDK does not support deployment target
```

**Solution:**
```yaml
# conda_build_config.yaml
MACOSX_SDK_VERSION:
  - "11.0"      # [osx and arm64]
  - "10.15"     # [osx and x86_64]

c_stdlib_version:
  - "11.0"      # [osx and arm64]
  - "10.15"     # [osx and x86_64]
```

#### Code Signing

**Error:**
```
error: the signature was invalid
codesign failed
```

**Solution:**
```yaml
# Disable signing for local builds
build:
  script_env:
    - CODESIGN_IDENTITY=-
```

### Linux

#### glibc Version

**Error:**
```
version `GLIBC_2.28' not found
```

**Solution:**
```yaml
# Use newer base image
# conda_build_config.yaml
c_stdlib_version:
  - "2.17"      # Default (cos7)
  - "2.28"      # For newer glibc (alma8)
```

#### Missing Libraries

**Error:**
```
libGL.so.1: cannot open shared object file
```

**Solution:**
```yaml
requirements:
  host:
    - libgl-devel    # [linux]
    - xorg-libx11    # [linux]
```

#### Segfault (Exit Code 139)

**Error:**
```
Exit code: 139 (segmentation fault)
```

**Causes:**
- vsyscall emulation issue in old kernels
- Memory corruption

**Solutions:**
```yaml
# Skip problematic tests
tests:
  - script:
      - if: not (linux and aarch64)
        then: pytest tests/

# Or use newer base image
```

## Test Failures

### Import Errors

**Error:**
```
ModuleNotFoundError: No module named 'mypackage'
```

**Solutions:**
```yaml
# 1. Check package installed correctly
tests:
  - script:
      - python -c "import sys; print(sys.path)"
      - pip list | grep mypackage

# 2. Check entry point name matches
build:
  python:
    entry_points:
      - mycommand = mypackage.cli:main  # Check module path
```

### pip check Failures

**Error:**
```
mypackage 1.0.0 requires missing-dep, which is not installed
```

**Solutions:**
```yaml
# Add missing runtime dependency
requirements:
  run:
    - missing-dep

# Or if optional, remove pip_check
tests:
  - python:
      imports:
        - mypackage
      pip_check: false  # Disable if deps are optional
```

### Test Timeouts

**Error:**
```
Test timed out after 600 seconds
```

**Solutions:**
```yaml
# Skip slow tests
tests:
  - script:
      - pytest -k "not slow" tests/

# Or increase timeout in conda-forge.yml
test:
  timeout: 7200  # 2 hours
```

### Network-Dependent Tests

**Error:**
```
ConnectionError: Failed to establish connection
requests.exceptions.ConnectionError
```

**Solution:**
```yaml
# Skip network tests in CI
tests:
  - script:
      - pytest -k "not network" tests/
      # OR
      - pytest -m "not network" tests/
```

## Resource Issues

### Out of Memory

**Error:**
```
MemoryError
Killed (signal 9)
```

**Solutions:**
```yaml
# Reduce parallelism
build:
  script:
    - make -j2  # Instead of -j$CPU_COUNT

# Or request more resources in conda-forge.yml
build:
  memory: 8GB
```

### Disk Space

**Error:**
```
No space left on device
OSError: [Errno 28]
```

**Solutions:**
```yaml
# Clean up during build
build:
  script:
    - make
    - rm -rf build/temp  # Clean intermediate files
    - make install
```

## CI Configuration Issues

### Rerender Needed

**Error:**
```
Recipe needs rerendering
CI files out of date
```

**Solution:**
```bash
# Locally
conda-smithy rerender

# Or via bot
# Comment on PR:
@conda-forge-admin, please rerender
```

### Azure Pipelines

**Error:**
```
No hosted parallelism has been purchased or granted
```

**Solution:**
Wait for conda-forge's shared pool, or use GitHub Actions.

### GitHub Actions

**Error:**
```
Resource not accessible by integration
```

**Solution:**
Check feedstock permissions and re-authenticate.

## Bot Commands

### Restart Failed CI

```
@conda-forge-admin, please restart ci
```

### Rerender

```
@conda-forge-admin, please rerender
```

### Re-run Linter

```
@conda-forge-admin, please lint
```

### Close Bad Bot PR

```
@conda-forge-admin, please close
```

## Debugging Strategies

### Reproduce Locally

```bash
# Using docker (Linux builds)
python build-locally.py linux64

# Native build
rattler-build build -r recipe.yaml -c conda-forge

# With debug output
rattler-build build -r recipe.yaml -c conda-forge -vvv
```

### Inspect Build Environment

```yaml
# Add debug commands to script
build:
  script:
    - echo "PATH=$PATH"
    - echo "PREFIX=$PREFIX"
    - which python
    - python --version
    - env | sort
    - ls -la $SRC_DIR
    # ... actual build commands
```

### Check Rendered Recipe

```bash
# See final recipe after variable substitution
rattler-build build -r recipe.yaml --render-only

# For meta.yaml
conda-render recipes/mypackage
```

### Compare with Working Feedstock

```bash
# Find similar package
gh search repos "feedstock similar-package" --owner conda-forge

# Clone and compare
git clone https://github.com/conda-forge/similar-package-feedstock
diff -r my-recipe similar-package-feedstock/recipe
```

## Preventive Measures

### Pre-Submit Checklist

1. ✅ Lint locally: `conda-smithy recipe-lint`
2. ✅ Build locally: `python build-locally.py`
3. ✅ Test all platforms if possible
4. ✅ Check dependencies exist on conda-forge
5. ✅ Verify hashes are correct

### CI Configuration Best Practices

```yaml
# conda-forge.yml
bot:
  automerge: true
  inspection: hint-all

build:
  error_overlinking: true

test:
  timeout: 3600

azure:
  store_build_artifacts: true  # For debugging
```

## Getting Help

### Request Review

```
@conda-forge/help-python ready for review
@conda-forge/help-c-cpp ready for review
@conda-forge/help-rust ready for review
```

### Open Issue

For infrastructure problems:
https://github.com/conda-forge/conda-forge.github.io/issues

### Community

- [Gitter](https://gitter.im/conda-forge/conda-forge.github.io)
- [Discourse](https://conda.discourse.group/)
