# Cross-Compilation Guide

Complete guide for building packages that target different platforms.

## Overview

Cross-compilation builds packages for a **target platform** different from the **build platform**.

| Term | Description | Example |
|------|-------------|---------|
| Build platform | Where compilation runs | linux-64 |
| Host platform | Where package installs (same as target) | osx-arm64 |
| Target platform | Where package runs | osx-arm64 |

## When Cross-Compilation is Needed

- Building macOS ARM64 on Intel
- Building Windows from Linux
- Building Linux ARM from x86_64
- Any scenario where native builds aren't available

## Local cross-build for a downloadable artifact

When a staged-recipes PR needs a `.conda` for a platform the staged-recipes
Azure matrix doesn't build (typically `osx-arm64` and `linux-aarch64`), use
the `recipe-build-cross` pixi task. It produces a `.conda` you can ship to
a target-platform machine for hands-on verification before the feedstock's
post-merge CI publishes the official one.

```bash
# Cross-build to osx-arm64 from a linux-64 dev box
pixi run -e local-recipes recipe-build-cross recipes/<name> osx-arm64

# Output:
# build_artifacts/osxarm64/osx-arm64/<name>-<version>-<hash>.conda
```

Supported targets: `osx-arm64`, `osx-64`, `linux-aarch64`, `linux-64`, `win-64`.

What the wrapper does on top of plain `rattler-build build` — see
`.claude/scripts/conda-forge-expert/cross-build.sh` for the implementation:

1. Loads `.ci_support/<config>.yaml` + the `conda-forge-pinning` overlay so
   variant resolution matches upstream CI.
2. Sets `CONDA_OVERRIDE_OSX` / `CONDA_OVERRIDE_GLIBC` so the host
   virtual-package solve succeeds when the build host doesn't match.
3. **osx-* targets**: copies the recipe to a tempdir, injects
   `cctools_<arch>` + `ld64_<arch>` into `requirements.build` (provides the
   cross `<triple>-install_name_tool`), and appends a 6-line shim to
   `build.sh` that symlinks it to the plain name rattler-build's Mach-O
   relinker searches for. Source recipe is untouched.
4. **win-64 target**: overrides `build.script` to `bash ./build.sh` so
   rattler-build doesn't try to spawn `build.bat` under cmd.exe (absent on
   a unix host). The recipe's `build.sh` MUST handle
   `target_platform == "win-64"` itself — typically by writing to
   `${PREFIX}/Library/bin` with `.exe` suffixes. The wrapper does not
   auto-translate `build.bat`; if the recipe ships only `build.bat`, the
   wrapper errors with a clear message.
5. Passes `--test skip` — rattler-build can't execute foreign-arch
   binaries on the host. Verify on the target machine manually.

**Scope**: tuned for binary-repackage recipes (the staged-recipes pattern
for prebuilt CLI tools like `gh-copilot-cli`, `pixi`, `microsoft-edit`).
Compiled-source cross-builds need more wiring (sysroot, kernel-headers,
compiler shims) that this wrapper doesn't set up — for those, build
natively or use the Docker entrypoint.

**Single-output only**: the cctools-injection regex matches a single
top-level `requirements.build:` block. Multi-output recipes should edit
their own build deps and use `rattler-build build` directly.

### win-64 cross-build recipe pattern

For the win-64 cross path to work, the recipe's `build.sh` must branch on
`${target_platform}`:

```bash
#!/bin/bash
set -euxo pipefail

if [[ "${target_platform}" == win-* ]]; then
  BIN_DIR="${PREFIX}/Library/bin"
  EXE=".exe"
else
  BIN_DIR="${PREFIX}/bin"
  EXE=""
fi

mkdir -p "${BIN_DIR}"
cp "./copilot${EXE}" "${BIN_DIR}/copilot${EXE}"
```

This same `build.sh` runs cleanly under both the native unix build and the
cross-to-win path. Keep `build.bat` for staged-recipes' native win-64 CI
runner — the cross path doesn't touch it.

## Basic Setup

### recipe.yaml

```yaml
requirements:
  build:
    - ${{ compiler("c") }}
    - ${{ stdlib("c") }}
    # Cross-compilation tools
    - if: build_platform != target_platform
      then:
        - python
        - cross-python_${{ target_platform }}
  host:
    - python
    - numpy
  run:
    - python
    - numpy
```

### meta.yaml

```yaml
requirements:
  build:
    - {{ compiler('c') }}
    - {{ stdlib('c') }}
    - python                                     # [build_platform != target_platform]
    - cross-python_{{ target_platform }}         # [build_platform != target_platform]
  host:
    - python
    - numpy
  run:
    - python
    - numpy
```

## Python Packages

### Pure Python (noarch)

No cross-compilation needed - use `noarch: python`:

```yaml
build:
  noarch: python
```

### Python with C Extensions

```yaml
requirements:
  build:
    - ${{ compiler("c") }}
    - ${{ stdlib("c") }}
    - if: build_platform != target_platform
      then:
        - python
        - cross-python_${{ target_platform }}
        - numpy                    # If building against NumPy C API
        - cython                   # If using Cython
  host:
    - python
    - pip
    - numpy
    - cython
  run:
    - python
    - ${{ pin_compatible("numpy") }}
```

### Python with Rust (maturin)

```yaml
requirements:
  build:
    - ${{ compiler("c") }}
    - ${{ stdlib("c") }}
    - ${{ compiler("rust") }}
    - cargo-bundle-licenses
    - if: build_platform != target_platform
      then:
        - python
        - cross-python_${{ target_platform }}
        - crossenv
        - maturin >=1.0,<2.0
  host:
    - python
    - pip
    - maturin >=1.0,<2.0
  run:
    - python
```

## CMake Projects

### Standard CMake Cross-Compilation

```yaml
requirements:
  build:
    - ${{ compiler("c") }}
    - ${{ compiler("cxx") }}
    - ${{ stdlib("c") }}
    - cmake
    - ninja
    - if: build_platform != target_platform
      then:
        - python
        - cross-python_${{ target_platform }}
  host:
    - python
    - zlib
```

### CMake Configuration

```yaml
build:
  script:
    # CMAKE_ARGS includes cross-compilation settings automatically
    - cmake -B build -G Ninja ${CMAKE_ARGS}
      -DCMAKE_BUILD_TYPE=Release
    - cmake --build build
    - cmake --install build --prefix ${{ PREFIX }}
```

The `CMAKE_ARGS` variable automatically includes:
- Cross-compilation toolchain
- Target platform settings
- Install prefix

### Finding Python in CMake

```yaml
build:
  script:
    - cmake -B build -G Ninja ${CMAKE_ARGS}
      -DPython_EXECUTABLE=${{ PYTHON }}
      -DPython3_EXECUTABLE=${{ PYTHON }}
```

## Autotools Projects

```yaml
requirements:
  build:
    - ${{ compiler("c") }}
    - ${{ stdlib("c") }}
    - make
    - autoconf
    - automake
    - libtool
    - if: build_platform != target_platform
      then:
        - gnuconfig

build:
  script:
    # Update config.guess/config.sub for cross-compilation
    - if: build_platform != target_platform
      then:
        - cp $BUILD_PREFIX/share/gnuconfig/config.* .
    - ./configure --prefix=${{ PREFIX }} --host=${{ HOST }}
    - make -j${{ CPU_COUNT }}
    - make install
```

## Go Projects

### Pure Go (No CGO)

No cross-compilation setup needed - Go handles it:

```yaml
requirements:
  build:
    - ${{ compiler("go") }}

build:
  script:
    # GOOS and GOARCH set automatically
    - go build -o ${{ PREFIX }}/bin/myapp
```

### Go with CGO

```yaml
requirements:
  build:
    - ${{ compiler("c") }}
    - ${{ stdlib("c") }}
    - ${{ compiler("go-cgo") }}
  host:
    - zlib

build:
  script:
    - CGO_ENABLED=1 go build -o ${{ PREFIX }}/bin/myapp
```

## Rust Projects

Cross-compilation is automatic with the Rust compiler:

```yaml
requirements:
  build:
    - ${{ compiler("c") }}
    - ${{ stdlib("c") }}
    - ${{ compiler("rust") }}
    - cargo-bundle-licenses

build:
  script:
    - cargo build --release --locked
    - cargo install --root ${{ PREFIX }} --path .
```

## Platform-Specific Considerations

### macOS ARM64 from Intel

Common scenario: Building `osx-arm64` on `osx-64`.

```yaml
requirements:
  build:
    - ${{ compiler("c") }}
    - ${{ stdlib("c") }}
    - if: build_platform != target_platform
      then:
        - python
        - cross-python_${{ target_platform }}

# May need SDK version
# conda_build_config.yaml
MACOSX_SDK_VERSION:
  - "11.0"
```

### Linux ARM64 from x86_64

```yaml
requirements:
  build:
    - ${{ compiler("c") }}
    - ${{ stdlib("c") }}
    - if: build_platform != target_platform
      then:
        - python
        - cross-python_${{ target_platform }}
```

### Windows Cross-Compilation

Windows cross-compilation is limited. Most Windows builds require native Windows builders.

## Testing Cross-Compiled Packages

### Emulated Tests

Tests can run under emulation (slow):

```yaml
tests:
  - script:
      - python -c "import mypackage"
```

### Skip Tests on Cross-Build

```yaml
tests:
  - script:
      - if: build_platform == target_platform
        then:
          - pytest tests/
```

### Test Only on Native

```yaml
# Only run full tests on native builds
tests:
  - python:
      imports:
        - mypackage
  - script:
      - if: build_platform == target_platform
        then:
          - pytest tests/ -v
    requirements:
      run:
        - pytest
```

## Troubleshooting

### "Cannot find Python.h"

```yaml
requirements:
  build:
    - if: build_platform != target_platform
      then:
        - python
        - cross-python_${{ target_platform }}
```

### "Wrong architecture" at Runtime

Ensure host dependencies are for target platform:

```yaml
requirements:
  build:
    # Build tools run on build platform
    - cmake
    - ninja
  host:
    # Libraries link against target platform
    - zlib  # Will be target platform version
```

### CMake Can't Find Libraries

Use `CMAKE_ARGS` which sets up cross-compilation paths:

```yaml
build:
  script:
    - cmake ${CMAKE_ARGS} ...  # Don't quote CMAKE_ARGS
```

### Autotools Wrong Target

Update config files:

```yaml
requirements:
  build:
    - gnuconfig  # [build_platform != target_platform]

build:
  script:
    - cp $BUILD_PREFIX/share/gnuconfig/config.* .  # [build_platform != target_platform]
    - ./configure --host=$HOST
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `build_platform` | Platform running build (e.g., `linux-64`) |
| `target_platform` | Platform for output (e.g., `osx-arm64`) |
| `BUILD_PREFIX` | Prefix for build tools |
| `PREFIX` | Prefix for target package |
| `HOST` | GNU triplet for target |
| `BUILD` | GNU triplet for build machine |
| `CMAKE_ARGS` | CMake cross-compilation args |

## CI Configuration

### Enable Cross-Compilation in conda-forge.yml

```yaml
# Build arm64 from x86_64
build_platform:
  osx_arm64: osx_64
  linux_aarch64: linux_64
  linux_ppc64le: linux_64
```

### Skip Native Build

```yaml
# Only cross-compile, don't build natively
skip_render:
  - osx_arm64_native
```

## Best Practices

1. **Test native first** - Ensure native builds work before cross-compiling
2. **Use CMAKE_ARGS** - Don't manually set cross-compilation flags
3. **Minimize build-time Python** - Only include if needed
4. **Check dependencies** - Ensure all deps support target platform
5. **Test on target** - Verify package works on actual target hardware

## Resources

- [conda-forge Cross-Compilation](https://conda-forge.org/docs/maintainer/knowledge_base/#cross-compilation)
- [CMake Cross-Compiling](https://cmake.org/cmake/help/latest/manual/cmake-toolchains.7.html)
- [conda-build Cross-Compilation](https://docs.conda.io/projects/conda-build/en/latest/resources/compiler-tools.html#cross-compiling)
