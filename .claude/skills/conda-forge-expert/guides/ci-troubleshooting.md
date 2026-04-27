# CI Troubleshooting Guide

Comprehensive guide for diagnosing and fixing conda-forge CI build failures.

## Systematic Debug Protocol

*From `debugging-and-error-recovery` + `shipping-and-launch`. Apply this before diving into specific error sections below.*

### Six-Step Triage

**Stop-the-Line Rule**: If the build behaves unexpectedly, stop. Do not add workarounds. Understand the root cause first.

| Step | Action | For conda-forge builds |
|------|--------|----------------------|
| **1. Reproduce** | Confirm the failure is deterministic | `python build-locally.py linux-64` — does it fail locally? |
| **2. Localize** | Narrow to the failing component | Is it a lint/solve/compile/test/packaging error? Read the log section headers. |
| **3. Reduce** | Find the minimal failing case | Comment out test sections; remove optional deps; try `--render-only` first. |
| **4. Fix Root Cause** | Address the actual problem | Don't mask errors (`2>/dev/null`, `|| true`). Fix the real failure. |
| **5. Guard** | Prevent regression | Add the fix to the recipe, not as a build-phase workaround. |
| **6. Verify** | Confirm fix, not just absence of error | `get_build_summary()` → all platforms green; `analyze_build_failure` reports no issues. |

### Failure Category Quick-Lookup

| Category | Typical Pattern | Likely Fix |
|----------|----------------|-----------|
| `MISSING_DEPENDENCY` | `PackagesNotFoundError` | `check_dependencies()` → add missing dep or loosen pin |
| `HASH_MISMATCH` | `SHA256 mismatch` | Recalculate with `curl -sL \| sha256sum` |
| `COMPILER_ERROR` | `error: unknown type` | Missing header, wrong C standard, or stdlib not declared |
| `STDLIB_MISSING` | `missing stdlib` | Add `${{ stdlib("c") }}` alongside every `compiler()` |
| `LINKER_ERROR` | `undefined reference` | Add library to `host:` requirements |
| `TEST_FAILURE` | `ModuleNotFoundError` | Missing `run:` dep; check `pip_check` output |
| `NETWORK_BLOCKED` | `curl/git during build` | Network is isolated in CI; fetch at source, not build time |
| `BUILD_TOOLS` | `meson: command not found` | Add `meson`, `ninja`, or `autotools` to `build:` requirements |
| `ENV_ISOLATION` | `command not found` | Tool missing from `build:` requirements (not on PATH in sysroot) |
| `RESOURCE` | `MemoryError`, `Errno 28` | Reduce `-j` parallelism; clean intermediate files |
| `BAT_SILENT_EXIT` | win-64 only: `× No license files were copied` (or other "this never ran") despite seemingly clean log; script halts after `pnpm`/`npm`/`yarn` line | `.cmd` shim invoked from `.bat` without `call` — see Windows § "Silent build.bat Termination" |

### Max Iteration Rule

**Stop after 5 fix-rebuild cycles** without a green build. At that point:
1. Call `analyze_build_failure` with the full error log
2. Check if a similar package on conda-forge solves the same problem (`gh search repos`)
3. Ask in `#help-c-cpp` or `#help-python` on the conda-forge Zulip (`conda-forge.zulipchat.com`) before continuing

### Pre-Submit Quality Gate

Before opening any PR to staged-recipes, verify all of these:

| Gate | Check | Tool |
|------|-------|------|
| Correctness | License file present, SHA256 correct, version matches | `validate_recipe()` |
| Security | No CVEs in deps, no git URLs for releases | `scan_for_vulnerabilities()` |
| Build | All target platforms pass locally | `get_build_summary()` all green |
| Standards | `stdlib()` present with compilers, no format mixing, `python_min ≥ 3.10` | `optimize_recipe()` — no STD-001/STD-002/SEL-002 |
| Submission | `gh auth` ok, fork exists, branch clean | `submit_pr(dry_run=True)` |

---

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

### CI Platform Assignment

conda-forge defaults to **Azure Pipelines** for builds. As of **March 8, 2026** GitHub Actions is also available as an opt-in build provider for `linux_64` (requires conda-smithy ≥ 3.57.1 and a `provider:` entry in `conda-forge.yml`). Windows and macOS builds remain on Azure. GitHub Actions still handles rerendering and automerge for every feedstock.

| Platform | Default CI Provider | Build limit | Notes |
|----------|---------------------|------------|-------|
| Linux x86_64 | Azure Pipelines (or GitHub Actions, opt-in) | 6 hours | GA opt-in via `provider: { linux_64: github_actions }` |
| Linux aarch64, ppc64le | Azure Pipelines (emulated) or Cirun (native) | 6 hours | |
| macOS x86_64, arm64 | Azure Pipelines | 6 hours | |
| Windows x86_64 | Azure Pipelines | 6 hours | |
| Windows ARM64 | Azure Pipelines | 6 hours | Python 3.14 cross-builds |
| Rerendering / automerge | GitHub Actions | N/A | Always |

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

#### Silent `build.bat` Termination After Calling a `.cmd` Shim (pnpm/npm/yarn)

**Symptom:** `build.bat` prints output up to a `pnpm`/`npm`/`yarn` invocation, then **silently terminates with no error**. Rattler-build proceeds to packaging and may fail later with a misleading error like `× No license files were copied` (because subsequent build steps that generate THIRDPARTY-* files never ran).

**Example log:**
```
=== Build environment ===
v24.14.1          ← node --version (node.exe)
10.33.2           ← pnpm --version (pnpm.cmd)
[script ends with exit 0; rattler-build moves to "Packaging new files"]
Error: × No license files were copied
```

**Root cause:** When a `.bat` invokes a `.cmd` shim (like `pnpm.cmd`, `npm.cmd`, `yarn.cmd`) **without `call`**, cmd.exe **transfers control** to the shim instead of recursing. When the shim returns, the parent `.bat` terminates rather than continuing to the next line. This is a long-standing cmd.exe footgun, not a rattler-build bug.

**Wrong:**
```bat
node --version || exit /b 1
pnpm --version || exit /b 1   :: pnpm is pnpm.cmd → terminates the script here
cargo --version || exit /b 1  :: never runs
```

**Right:**
```bat
node --version
if errorlevel 1 exit /b 1
call pnpm --version
if errorlevel 1 exit /b 1
cargo --version
if errorlevel 1 exit /b 1
```

**Rule:** In `build.bat`, prefix **every** invocation of a CLI that ships as a `.cmd`/`.bat` wrapper with `call`. Common offenders on conda-forge win-64:
- `pnpm` (pnpm.cmd)
- `npm` (npm.cmd)
- `yarn` (yarn.cmd)
- `npx` (npx.cmd)
- Any third-party CLI installed via npm

`call` is harmless on real `.exe` binaries (`node.exe`, `cargo.exe`, `rustc.exe`, etc.), so when in doubt, add it.

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
# conda-forge.yml — request a newer Linux base image
os_version:
  linux_64: alma8    # glibc 2.28
  # alma9            # glibc 2.34 (current recommended)
  # cos7             # glibc 2.17 (default, most compatible)

# conda_build_config.yaml — match c_stdlib_version to your os_version
c_stdlib_version:
  - "2.17"      # cos7 (default)
  - "2.28"      # alma8
  - "2.34"      # alma9
```

**Available OS versions** (Apr 2026): `cos7` (default), `alma8`, `alma9`, `ubi8`, `alma10`, `rocky10`

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

- [Zulip](https://conda-forge.zulipchat.com/) — primary real-time channel (replaces Gitter)
- [Discourse](https://conda.discourse.group/) — read-only archive since Oct 2025; do not post new threads
- [conda-forge Blog](https://conda-forge.org/news/) — announcements and migration notices
- [Status Dashboard](https://conda-forge.org/status/) — active migrations, infrastructure incidents
