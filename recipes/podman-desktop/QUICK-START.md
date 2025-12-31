# Quick Start Guide - Podman Desktop CI Testing

This guide shows how to trigger GitHub Actions CI builds and test the artifacts using the automation scripts.

## Prerequisites

1. **GitHub CLI (gh)** - Required for trigger-ci-build.sh
   ```bash
   # Check if installed
   gh --version

   # Install if needed:
   # Ubuntu/Debian: sudo apt install gh
   # macOS: brew install gh
   # Windows: winget install --id GitHub.cli
   ```

2. **Authenticate with GitHub** (one-time setup)
   ```bash
   gh auth login
   # Follow prompts to authenticate
   ```

3. **conda/mamba** - Required for test-ci-artifacts.sh
   ```bash
   # Should already be installed if you're using this repo
   mamba --version
   ```

## Option 1: Automated Workflow (Recommended)

Use the provided scripts to automate the entire process:

### Step 1: Trigger CI Build and Download Artifacts

```bash
cd /home/rxm7706/UserLocal/Projects/Github/rxm7706/local-recipes
./recipes/podman-desktop/trigger-ci-build.sh
```

**What this does**:
- ✅ Triggers GitHub Actions workflow for podman-desktop (Linux + Windows + macOS)
- ✅ Monitors build progress in real-time (~30 minutes)
- ✅ Automatically downloads artifacts when complete
- ✅ Organizes packages into platform-specific directories

**Output**:
```
ci-artifacts/
├── linux-64/
│   └── podman-desktop-1.24.2-hb0f4dca_0.conda (~122 MB)
├── win-64/
│   └── podman-desktop-1.24.2-h9490d1a_0.conda (~150 MB)
├── osx-64/
│   └── podman-desktop-1.24.2-*.conda (~140 MB)
└── osx-arm64/
    └── podman-desktop-1.24.2-*.conda (~140 MB)
```

### Step 2: Test the Downloaded Artifacts

```bash
./recipes/podman-desktop/test-ci-artifacts.sh
```

**What this does**:
- ✅ Inspects package metadata
- ✅ Verifies dependencies (kubernetes-kind, kubernetes-client)
- ✅ Optionally installs and tests the package
- ✅ Verifies binaries (podman-desktop, kind, kubectl)
- ✅ Optionally launches GUI for manual testing

**Interactive prompts**:
- "Install and test podman-desktop? [y/N]" - Type `y` to test installation
- "Launch podman-desktop GUI? [y/N]" - Type `y` to test GUI (Linux only)

## Option 2: Manual Workflow

If you prefer manual control or want to customize settings:

### Step 1: Trigger Workflow Manually

1. Go to: https://github.com/rxm7706/local-recipes/actions/workflows/test-all.yml
2. Click: **"Run workflow"** button (right side)
3. Configure:
   - **Recipes to build**: `podman-desktop`
   - **Platforms**: `linux,windows` (or `linux,windows,macos` for all)
   - **Linux base image**: `alma9` (default)
   - **Python version**: `3.12` (default)
4. Click: **"Run workflow"** (green button)

### Step 2: Monitor Progress

1. Click on the running workflow
2. Watch progress for each platform:
   - **Linux**: ~25-30 minutes
   - **Windows**: ~20-25 minutes
   - **macOS**: ~30-35 minutes (if included)

### Step 3: Download Artifacts

When complete:
1. Scroll to **"Artifacts"** section at bottom
2. Download:
   - `linux-64-conda-packages.zip`
   - `win-64-conda-packages.zip`
   - `osx-64-conda-packages.zip` (if built)

### Step 4: Extract and Test

**Linux**:
```bash
unzip linux-64-conda-packages.zip
mamba install -c file://$(pwd)/linux-64 -c conda-forge podman-desktop
podman-desktop
kind --version
kubectl version --client
```

**Windows**:
```batch
REM Extract win-64-conda-packages.zip
mamba install -c file:///%CD%/win-64 -c conda-forge podman-desktop
podman-desktop
kind --version
kubectl version --client
```

**macOS**:
```bash
# Extract osx-64-conda-packages.zip (Intel) or osx-arm64-conda-packages.zip (Apple Silicon)
mamba install -c file://$(pwd)/osx-64 -c conda-forge podman-desktop  # Intel
# OR
mamba install -c file://$(pwd)/osx-arm64 -c conda-forge podman-desktop  # Apple Silicon

# Launch application
open -a "Podman Desktop"
# Or from terminal
podman-desktop

# Verify Kubernetes tools
kind --version
kubectl version --client
```

## Option 3: Local Build (No CI)

For rapid iteration during development:

### Linux Local Build

```bash
# Using rattler-build (fastest)
rattler-build build --recipe recipes/podman-desktop --target-platform linux-64 -c conda-forge

# Install and test
mamba install -c file://$(pwd)/output -c conda-forge podman-desktop --force-reinstall
podman-desktop
```

### Windows Local Build

**Requirements**: Native Windows machine with Visual Studio 2017+

```batch
REM Using rattler-build
rattler-build build --recipe recipes/podman-desktop --target-platform win-64 -c conda-forge

REM Install and test
mamba install -c file:///%CD%/output -c conda-forge podman-desktop --force-reinstall
podman-desktop
```

### macOS Local Build

**Requirements**: macOS machine (Intel or Apple Silicon)

```bash
# Using rattler-build
# For Intel Macs (x86_64)
rattler-build build --recipe recipes/podman-desktop --target-platform osx-64 -c conda-forge

# For Apple Silicon (arm64)
rattler-build build --recipe recipes/podman-desktop --target-platform osx-arm64 -c conda-forge

# Install and test
mamba install -c file://$(pwd)/output -c conda-forge podman-desktop --force-reinstall
open -a "Podman Desktop"
# Or from terminal
podman-desktop
```

## Troubleshooting

### Script Permission Denied

```bash
chmod +x recipes/podman-desktop/trigger-ci-build.sh
chmod +x recipes/podman-desktop/test-ci-artifacts.sh
```

### GitHub CLI Not Authenticated

```bash
gh auth status
# If not authenticated:
gh auth login
```

### Workflow Trigger Failed

Check authentication and retry:
```bash
gh auth refresh
./recipes/podman-desktop/trigger-ci-build.sh
```

### Artifact Not Found

Wait for workflow to complete (check GitHub Actions web UI):
```
https://github.com/rxm7706/local-recipes/actions
```

### Installation Failed: Hash Mismatch

Clear package cache:
```bash
rm -f ~/UserLocal/Apps/LocalConda/pkgs/podman-desktop-*.conda
conda clean --all
```

### GUI Won't Launch (Headless)

Test without GUI:
```bash
# Check binaries only
which podman-desktop kind kubectl
kind --version
kubectl version --client

# Skip GUI launch in test-ci-artifacts.sh
# (answer 'n' when prompted)
```

## Expected Test Results

### Successful Linux Build
- **Package**: `podman-desktop-1.24.2-hb0f4dca_0.conda`
- **Size**: ~122 MB
- **Dependencies**: kubernetes-kind, kubernetes-client included
- **Binary**: `/home/rxm7706/UserLocal/Apps/LocalConda/bin/podman-desktop`
- **Extensions**: 9 extensions loaded
- **Kubernetes**: kind v0.30.0, kubectl v1.34.3

### Successful Windows Build
- **Package**: `podman-desktop-1.24.2-h9490d1a_0.conda`
- **Size**: ~150 MB
- **Dependencies**: kubernetes-kind, kubernetes-client included
- **Binary**: `%CONDA_PREFIX%\Scripts\podman-desktop.bat`
- **Extensions**: 9 extensions loaded
- **Kubernetes**: kind v0.30.0, kubectl v1.34.3

### Successful macOS Build (x64)
- **Package**: `podman-desktop-1.24.2-*.conda`
- **Size**: ~140 MB
- **Dependencies**: kubernetes-kind, kubernetes-client included
- **Binary**: `$CONDA_PREFIX/bin/podman-desktop`
- **App Bundle**: `$CONDA_PREFIX/lib/Podman Desktop.app`
- **Extensions**: 9 extensions loaded
- **Kubernetes**: kind v0.30.0, kubectl v1.34.3

### Successful macOS Build (arm64)
- **Package**: `podman-desktop-1.24.2-*.conda`
- **Size**: ~140 MB
- **Dependencies**: kubernetes-kind, kubernetes-client included
- **Binary**: `$CONDA_PREFIX/bin/podman-desktop`
- **App Bundle**: `$CONDA_PREFIX/lib/Podman Desktop.app`
- **Extensions**: 9 extensions loaded
- **Kubernetes**: kind v0.30.0, kubectl v1.34.3

## Next Steps

After successful testing:

1. **Document Results**: Note build times, package sizes, any issues
2. **Update README.md**: Add test results to the recipe documentation
3. **Commit Changes**:
   ```bash
   git add recipes/podman-desktop/
   git commit -m "Add podman-desktop recipe with multi-platform support (Linux/Windows/macOS)"
   git push
   ```
4. **Submit to conda-forge** (when ready):
   - Fork: https://github.com/conda-forge/staged-recipes
   - Create PR with your recipe
   - Reference: https://conda-forge.org/docs/maintainer/adding_pkgs.html

## Comparison: CI vs Local Builds

| Aspect | CI (GitHub Actions) | Local Build |
|--------|---------------------|-------------|
| **Environment** | Exact conda-forge (Docker/Miniforge) | Your local setup |
| **Platforms** | Linux + Windows + macOS in parallel | Single platform only |
| **Build Time** | ~30 min (parallel) | ~25 min (single) |
| **Artifacts** | Pre-built packages ready to test | Must build each time |
| **Debugging** | Limited (CI logs only) | Full interactive access |
| **Cost** | GitHub Actions minutes | Local resources |
| **Use Case** | Final validation before submission | Rapid development iteration |

## Quick Reference

```bash
# One-line CI test
./recipes/podman-desktop/trigger-ci-build.sh && ./recipes/podman-desktop/test-ci-artifacts.sh

# One-line local build and test (Linux)
rattler-build build --recipe recipes/podman-desktop --target-platform linux-64 -c conda-forge && \
mamba install -c file://$(pwd)/output -c conda-forge podman-desktop --force-reinstall && \
podman-desktop

# Check workflow status
gh run list --workflow=test-all.yml --limit 5

# View latest run logs
gh run view --log

# Download specific run artifacts
gh run download <RUN_ID>
```

## Support

- **Workflow Issues**: Check `.github/workflows/` for workflow configuration
- **Build Issues**: See `recipes/podman-desktop/README.md` and `CI-BUILD-GUIDE.md`
- **GitHub Actions**: See `recipes/podman-desktop/GITHUB-ACTIONS-GUIDE.md`
- **Conda-forge**: https://conda-forge.org/docs/
- **Podman Desktop**: https://github.com/podman-desktop/podman-desktop
