# GitHub Actions Testing Guide for podman-desktop

Your repository already has **excellent workflow-dispatch workflows** set up for on-demand testing! Here's how to use them for podman-desktop.

## 🎯 Available Workflows

### 1. **Test All Platforms** (Recommended for podman-desktop)
**File**: `.github/workflows/test-all.yml`
**Trigger**: Manual (workflow_dispatch)

Runs Linux, Windows, and macOS builds in parallel.

### 2. **Test Linux Builds**
**File**: `.github/workflows/test-linux.yml`
**Trigger**: Manual or called by test-all.yml

### 3. **Test Windows Builds**
**File**: `.github/workflows/test-windows.yml`
**Trigger**: Manual or called by test-all.yml

### 4. **Test macOS Builds**
**File**: `.github/workflows/test-macos.yml`
**Trigger**: Manual or called by test-all.yml

---

## 🚀 How to Test podman-desktop

### Method 1: Test All Platforms (Best for podman-desktop)

1. **Go to GitHub Actions**:
   ```
   https://github.com/<your-username>/local-recipes/actions
   ```

2. **Click "Test All Platforms"** in the left sidebar

3. **Click "Run workflow"** button (right side)

4. **Configure options**:
   ```
   Recipes to build: podman-desktop
   Platforms: linux,windows  (skip macOS initially)
   Linux base image: alma9
   Python version: 3.12
   CUDA version: (leave empty)
   ```

5. **Click "Run workflow"** (green button)

6. **Wait ~25-30 minutes** for builds to complete

7. **Download artifacts**:
   - Linux: `linux-64-conda-packages.zip`
   - Windows: `win-64-conda-packages.zip`

---

### Method 2: Test Linux Only (Faster)

1. **Go to Actions** → **Test Linux Builds**

2. **Run workflow** with:
   ```
   Recipes: podman-desktop
   Linux version: alma9
   Architecture: linux-64
   Python version: 3.12
   ```

3. **Download**: `linux-64-conda-packages.zip`

---

### Method 3: Test Windows Only

1. **Go to Actions** → **Test Windows Builds**

2. **Run workflow** with:
   ```
   Recipes: podman-desktop
   Python version: 3.12
   Use rattler-build: true
   ```

3. **Download**: `win-64-conda-packages.zip`

---

## 📦 What Gets Built

Each workflow:
1. ✅ **Detects** the recipe (podman-desktop)
2. ✅ **Sets up** conda-forge environment
3. ✅ **Builds** using rattler-build or conda-build
4. ✅ **Tests** the package
5. ✅ **Uploads** artifacts for download

### Linux Build
- **Docker Image**: `quay.io/condaforge/linux-anvil-alma-9-x86_64` (default)
- **Environment**: Matches conda-forge exactly
- **Output**: `podman-desktop-1.24.2-hb0f4dca_0.conda` (~122 MB)
- **Includes**: kubernetes-kind, kubernetes-client

### Windows Build
- **Runner**: `windows-latest` (Windows Server 2022)
- **Miniforge**: Auto-provisioned to `D:\Miniforge`
- **Compiler**: MSVC from GitHub Actions runner
- **Output**: `podman-desktop-1.24.2-h9490d1a_0.conda` (~150 MB)
- **Includes**: kubernetes-kind, kubernetes-client

---

## 🎛️ Advanced Options

### Build Specific Recipe Only

```yaml
Recipes: podman-desktop
```

### Build Multiple Recipes

```yaml
Recipes: podman-desktop,another-recipe
```

### Build All Recipes

```yaml
Recipes: all
```

### Skip CI (Commit Message)

Add to commit message:
```
[skip ci]       - Skip all platforms
[skip linux]    - Skip Linux only
[skip windows]  - Skip Windows only
```

---

## 📊 Workflow Features (Already Implemented!)

### ✅ Efficient Resource Usage

```yaml
# From test-all.yml
on:
  workflow_dispatch:  # Manual trigger only!
```

**Why this is smart**:
- ❌ No automatic runs on every commit (saves GitHub Actions minutes)
- ✅ Run only when needed
- ✅ Choose specific platforms
- ✅ Preserves free tier quota

### ✅ Recipe Detection

The workflow automatically:
- Detects which recipes changed
- Builds only affected recipes
- Can override with manual recipe selection

### ✅ Platform Selection

```yaml
platforms:
  - 'all'
  - 'linux'
  - 'windows'
  - 'macos'
  - 'linux,windows'  # Recommended for podman-desktop
```

### ✅ Artifact Upload

Each build uploads:
- `<platform>-conda-packages.zip`
- Contains all built `.conda` files
- Available for 90 days
- Downloadable without needing to rebuild

### ✅ Build Summary

Automatic summary showing:
- Platform status (success/failure/skipped)
- Configuration used
- Recipes built

---

## 🧪 Testing Workflow

### Step 1: Trigger Build

**For podman-desktop** (Linux + Windows):
1. Go to Actions → Test All Platforms
2. Run workflow:
   ```
   Recipes: podman-desktop
   Platforms: linux,windows
   Python: 3.12
   ```

### Step 2: Monitor Build

**Linux** (~25-30 min):
- Sets up Docker container
- Installs dependencies (2773 npm packages)
- Builds with pnpm + electron-builder
- Creates conda package
- Runs tests

**Windows** (~20-25 min):
- Provisions Miniforge
- Installs dependencies
- Builds with pnpm + electron-builder
- Creates conda package
- Runs tests

### Step 3: Download Artifacts

When complete:
1. Click on the successful workflow run
2. Scroll to "Artifacts" section at bottom
3. Download:
   - `linux-64-conda-packages.zip`
   - `win-64-conda-packages.zip`

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
REM Unzip win-64-conda-packages.zip
mamba install -c file:///%CD%/win-64 -c conda-forge podman-desktop
podman-desktop
kind --version
kubectl version --client
```

---

## 🔍 Troubleshooting Workflows

### Build Fails - View Logs

1. Click on failed workflow run
2. Click on failed job (Linux/Windows/macOS)
3. Expand failed step
4. Review error logs

### Common Issues

**Linux: Docker timeout**
- Solution: Docker pull can be slow, retry workflow

**Windows: MSVC not found**
- Solution: Should not happen (GitHub runners have MSVC)
- If occurs, check workflow uses `windows-latest`

**Recipe not detected**
- Solution: Specify manually in "Recipes" input: `podman-desktop`

**Build timeout (>360 min)**
- Solution: This shouldn't happen for podman-desktop (~30 min)
- If occurs, check for infinite loops in build.sh/build.bat

---

## 📈 Workflow Status

Current setup already has:

✅ **Manual triggers** (efficient, no wasted minutes)
✅ **Multi-platform support** (Linux, Windows, macOS)
✅ **Recipe detection** (automatic or manual)
✅ **Artifact uploads** (90-day retention)
✅ **Skip keywords** (commit message control)
✅ **Platform selection** (build only what you need)
✅ **Build summaries** (clear status reporting)
✅ **rattler-build support** (modern recipe format)
✅ **conda-build fallback** (legacy recipes)

---

## 🎯 Recommended Testing Flow for podman-desktop

### Initial Testing

```
1. Local Linux build (fastest iteration)
   → rattler-build build --recipe recipes/podman-desktop --target-platform linux-64

2. GitHub Actions Linux (CI validation)
   → Actions → Test Linux Builds → podman-desktop

3. GitHub Actions Windows (if Linux succeeds)
   → Actions → Test Windows Builds → podman-desktop

4. GitHub Actions All Platforms (final validation)
   → Actions → Test All Platforms → podman-desktop → linux,windows
```

### After Changes

```
1. Test locally first (rapid iteration)
2. Push to GitHub
3. Run workflow manually
4. Download and verify artifacts
```

---

## 💰 Cost Efficiency

### Your Current Setup is Optimal!

| Trigger | Cost | When Used |
|---------|------|-----------|
| `on: push` | ❌ High (runs on every commit) | ❌ Not used (smart!) |
| `on: pull_request` | ⚠️ Medium (runs on PR) | ⚠️ Not used (good!) |
| `on: workflow_dispatch` | ✅ Zero waste (manual only) | ✅ **Your setup!** |

**Why this is efficient**:
- 🎯 Run only when needed
- 🎯 Choose specific platforms
- 🎯 Skip unchanged recipes
- 🎯 No automatic burns

**GitHub Free Tier**:
- 2,000 minutes/month
- Linux: 1x multiplier
- Windows: 2x multiplier
- macOS: 10x multiplier

**podman-desktop build costs**:
- Linux: ~30 min = 30 minutes
- Windows: ~25 min = 50 minutes (2x multiplier)
- **Total**: ~80 minutes per full test

---

## 🚀 Quick Start for podman-desktop

### Right Now (5 minutes to start)

1. **Go to**: https://github.com/rxm7706/local-recipes/actions
2. **Click**: "Test All Platforms"
3. **Click**: "Run workflow"
4. **Enter**: `podman-desktop` in "Recipes to build"
5. **Select**: `linux,windows` in "Platforms"
6. **Click**: "Run workflow" (green button)
7. **Wait**: ~30 minutes
8. **Download**: Both artifacts
9. **Test**: On respective platforms

### Expected Results

**Linux artifact**:
- File: `podman-desktop-1.24.2-hb0f4dca_0.conda`
- Size: ~122 MB
- Dependencies: kubernetes-kind, kubernetes-client included

**Windows artifact**:
- File: `podman-desktop-1.24.2-h9490d1a_0.conda`
- Size: ~150 MB
- Dependencies: kubernetes-kind, kubernetes-client included

---

## 📝 Next Steps

1. **Trigger workflow** for podman-desktop on Linux + Windows
2. **Monitor build** progress in Actions tab
3. **Download artifacts** when complete
4. **Test on both platforms**
5. **Document results** (build times, package sizes, test results)
6. **Commit and submit** to conda-forge if successful

---

## ✨ Summary

You already have **everything you need**! The GitHub Actions setup is:
- ✅ Well-designed (manual triggers, efficient)
- ✅ Multi-platform (Linux, Windows, macOS)
- ✅ Feature-complete (artifacts, summaries, skip keywords)
- ✅ Cost-effective (no waste, on-demand only)

**Just trigger the workflow** and you'll get tested packages for both platforms without needing local Windows setup!
