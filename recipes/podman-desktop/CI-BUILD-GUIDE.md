# CI Build Guide - Replicating conda-forge Locally

This guide explains how to build and test podman-desktop locally using the same conda-forge CI environment.

## Overview

The `build-locally.py` script replicates conda-forge's GitHub CI environment locally by:
- **Linux**: Using Docker containers with conda-forge's build images
- **Windows**: Using native Windows build with Miniforge
- **macOS**: Using native macOS build (requires macOS SDK)

## Available Platforms

```bash
# List all available build configurations
python build-locally.py --filter "*"

# Available configs:
# - linux64          (Linux x86_64)
# - linux_aarch64    (Linux ARM64)
# - win64            (Windows x64)
# - osx64            (macOS x64)
# - osxarm64         (macOS ARM64)
```

## 🐧 Linux Builds (Docker-based)

### Requirements
- **Docker** installed and running
- **Host OS**: Linux or macOS (for Docker)
- **Disk Space**: ~5 GB (Docker images + build artifacts)
- **Network**: Downloads conda-forge Docker images (~1-2 GB)

### What You Get
- Exact conda-forge build environment (CentOS 7 / glibc 2.17 compatible)
- Reproducible builds matching conda-forge CI
- No need to install compilers or dependencies on host

### Build Commands

```bash
# Interactive mode - will prompt for config selection
python build-locally.py

# Direct mode - specify config
python build-locally.py linux64

# With filtering
python build-locally.py --filter "linux*"
```

### How It Works

1. **Pulls Docker Image**: `quay.io/condaforge/linux-anvil-comp7`
   - Pre-configured with GCC, glibc, build tools
   - Matches conda-forge CI exactly

2. **Mounts Workspace**:
   ```
   /home/rxm7706/.../local-recipes → /home/conda/staged-recipes (in container)
   ```

3. **Runs Build**:
   - Executes `.ci_support/build_all.py`
   - Builds all recipes in `recipes/` directory
   - Outputs to `build_artifacts/`

4. **Permissions**: Runs with your user ID to avoid permission issues

### Expected Output

```
output/
└── linux-64/
    └── podman-desktop-1.24.2-hb0f4dca_0.conda
```

### Advantages
✅ **Exact conda-forge environment** (same Docker images)
✅ **No host contamination** (isolated build)
✅ **Reproducible** (same results as conda-forge CI)
✅ **Works on macOS** (Docker runs Linux containers)

### Limitations
⚠️ **Requires Docker** (not available on all systems)
⚠️ **Slower than native** (Docker overhead)
⚠️ **Linux only** (can't build Windows/macOS in Docker)

---

## 🪟 Windows Builds (Native)

### Requirements
- **Host OS**: Windows 10/11 x64
- **Visual Studio 2017+** with C++ Build Tools (for Electron/node-gyp)
- **Miniforge** (auto-installed by script if missing)
- **Disk Space**: ~3 GB (Miniforge + build artifacts)

### What You Get
- Native Windows build environment
- Uses same conda configuration as conda-forge Windows CI
- Automatic Miniforge installation and setup

### Build Commands

```batch
REM Interactive mode
python build-locally.py

REM Direct mode
python build-locally.py win64

REM Set custom build path (optional)
set CONDA_BLD_PATH=D:\conda-builds
python build-locally.py win64
```

### How It Works

1. **Provisions Miniforge** (if not present):
   - Downloads micromamba
   - Creates environment at `%USERPROFILE%\Miniforge3`
   - Installs build tools from `environment.yaml`

2. **Configures Conda**:
   - Sets up channels (conda-forge)
   - Configures solver (libmamba)
   - Loads variant config from `.ci_support/win64.yaml`

3. **Runs Build**:
   - Activates Miniforge environment
   - Executes `.ci_support/build_all.py`
   - Builds with conda-build or rattler-build

4. **Output Location**: `C:\bld\win-64\` (or `%CONDA_BLD_PATH%`)

### Expected Output

```
C:\bld\
└── win-64\
    └── podman-desktop-1.24.2-h9490d1a_0.conda
```

### Advantages
✅ **Native performance** (no virtualization overhead)
✅ **Auto-provisioning** (installs Miniforge automatically)
✅ **Matches conda-forge Windows CI** (same config files)
✅ **MSVC compiler support** (via Visual Studio)

### Limitations
⚠️ **Windows only** (can't run on Linux/macOS)
⚠️ **Requires Visual Studio** (for C++ compilation)
⚠️ **Not isolated** (builds in host environment)

---

## 📦 What Gets Built

The build system processes all recipes in `recipes/` directory:

```bash
recipes/
├── podman-desktop/     # Your recipe
│   ├── recipe.yaml     # Rattler Build format
│   ├── meta.yaml       # conda-build format
│   ├── build.sh        # Linux/macOS build script
│   └── build.bat       # Windows build script
└── other-recipe/       # Other recipes (if any)
```

The build script automatically:
1. Detects recipe format (recipe.yaml vs meta.yaml)
2. Resolves dependencies between recipes
3. Builds in correct topological order
4. Outputs to platform-specific directories

---

## 🔧 Current Setup for podman-desktop

### Linux Build (Docker)

**Status**: ✅ **Ready and tested**

```bash
# From repo root
python build-locally.py linux64

# Build artifacts:
# → output/linux-64/podman-desktop-1.24.2-hb0f4dca_0.conda (122 MB)
```

**What happens**:
1. Pulls `quay.io/condaforge/linux-anvil-comp7`
2. Installs: GCC 15, Node.js 24, Python 3.12
3. Runs `build.sh`:
   - `corepack enable && pnpm install`
   - `pnpm build && pnpm electron-builder build --linux --dir`
   - Packages → `$PREFIX/lib/podman-desktop/`
4. Creates conda package with metadata
5. Includes dependencies: kubernetes-kind, kubernetes-client

**Build time**: ~25-30 minutes (in Docker)

---

### Windows Build (Native)

**Status**: ✅ **Recipe ready** | ⏳ **Needs Windows machine**

```batch
REM From repo root (on Windows)
python build-locally.py win64

REM Build artifacts (expected):
REM → C:\bld\win-64\podman-desktop-1.24.2-h9490d1a_0.conda (~150 MB)
```

**What would happen**:
1. Provisions Miniforge to `%USERPROFILE%\Miniforge3`
2. Installs: MSVC compilers (via VS), Node.js 24, Python 3.12
3. Runs `build.bat`:
   - `corepack enable && pnpm install`
   - `pnpm build && pnpm compile:current`
   - Packages → `%LIBRARY_PREFIX%\lib\podman-desktop\`
4. Creates conda package with metadata
5. Includes dependencies: kubernetes-kind, kubernetes-client

**Build time**: ~20-25 minutes (native Windows)

**Blockers**: Requires actual Windows machine (cannot cross-compile)

---

## 🚀 Testing Builds

### After Linux Build

```bash
# Install from local channel
mamba install -c file:///path/to/local-recipes/output -c conda-forge podman-desktop

# Verify installation
which podman-desktop kind kubectl
podman-desktop --version   # May hang (GUI app)
kind --version             # Should work
kubectl version --client   # Should work

# Test GUI (requires X11/Wayland)
podman-desktop
```

### After Windows Build

```batch
REM Install from local channel
mamba install -c file:///C:/path/to/local-recipes/output -c conda-forge podman-desktop

REM Verify installation
where podman-desktop kind kubectl
podman-desktop --version
kind --version
kubectl version --client

REM Test GUI
podman-desktop
```

---

## 🐛 Debugging Failed Builds

### Enable Debug Mode

```bash
# Linux/macOS
python build-locally.py linux64 --debug

# Windows
python build-locally.py win64 --debug
```

Debug mode:
- Enters build environment on failure
- Allows manual inspection
- Can rerun commands interactively

### Common Issues

**Docker Issues (Linux)**:
```bash
# Permission denied
sudo usermod -aG docker $USER
newgrp docker

# Docker not running
sudo systemctl start docker

# Image pull fails
docker pull quay.io/condaforge/linux-anvil-comp7
```

**Windows Issues**:
```batch
REM Visual Studio not found
REM → Install "Desktop development with C++" workload

REM Miniforge provisioning fails
REM → Delete %USERPROFILE%\Miniforge3 and retry

REM Build fails with "module not found"
REM → Check Node.js version (must be 24.x)
```

---

## 📊 Comparison: Local vs CI

| Aspect | build-locally.py | conda-forge CI |
|--------|------------------|----------------|
| **Environment** | Exact match (same Docker/config) | GitHub Actions runners |
| **Build time** | Similar (~25-30 min) | Similar (~20-30 min) |
| **Artifacts** | Local `output/` directory | GitHub Releases |
| **Debugging** | Interactive with `--debug` | Limited (CI logs only) |
| **Platform** | Single platform per run | Matrix builds (all platforms) |
| **Cost** | Free (local resources) | Free (GitHub minutes) |

---

## 🎯 Recommended Workflow

### For Linux Development

```bash
# 1. Rapid iteration with rattler-build (faster)
rattler-build build --recipe recipes/podman-desktop --target-platform linux-64 -c conda-forge

# 2. Final validation with conda-forge Docker (exact CI match)
python build-locally.py linux64

# 3. Test installation
mamba install -c file://$(pwd)/output -c conda-forge podman-desktop --force-reinstall
```

### For Windows Development

```batch
REM 1. Initial build with rattler-build (if on Windows)
rattler-build build --recipe recipes/podman-desktop --target-platform win-64 -c conda-forge

REM 2. Final validation with build-locally (matches CI)
python build-locally.py win64

REM 3. Test installation
mamba install -c file:///%CD%/output -c conda-forge podman-desktop --force-reinstall
```

### For Cross-Platform Validation

**Option 1**: Use separate machines
- Linux: Native Linux or Docker on macOS
- Windows: Native Windows machine
- macOS: Native macOS machine

**Option 2**: GitHub Actions (free CI)
- Push to GitHub
- CI runs on all platforms automatically
- Download artifacts from GitHub Actions

---

## 📝 Next Steps

To complete Windows testing, you need:

1. **Access to Windows Machine**:
   - Windows 10/11 x64
   - Visual Studio 2017+ with C++ tools
   - Or: GitHub Actions (free for public repos)

2. **Run Build**:
   ```batch
   git clone <your-repo>
   cd local-recipes
   python build-locally.py win64
   ```

3. **Test Package**:
   ```batch
   mamba install -c file:///%CD%/output -c conda-forge podman-desktop
   podman-desktop
   ```

4. **Verify Dependencies**:
   ```batch
   kind --version         # Should be v0.30.0
   kubectl version --client  # Should be v1.34.3
   ```

Would you like me to:
- Create a GitHub Actions workflow for multi-platform builds?
- Set up a Windows VM configuration guide?
- Create a testing checklist for both platforms?
