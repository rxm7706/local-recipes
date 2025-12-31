# Podman Desktop Conda Recipe

Conda package for [Podman Desktop](https://podman-desktop.io), a graphical tool for developing containerized applications using Podman and Kubernetes.

## Package Information

- **Version**: 1.24.2
- **Upstream**: https://github.com/podman-desktop/podman-desktop
- **License**: Apache-2.0
- **Technology**: Electron 40.0.0 + TypeScript + Svelte

## Current Status

**Multi-Platform Support**

Recipe supports:
- ✅ Linux x86_64 (tested and working)
- ✅ Windows x64 (recipe ready, requires Windows build environment)
- ✅ macOS x64 (Intel Macs - recipe ready, requires macOS build environment)
- ✅ macOS arm64 (Apple Silicon - recipe ready, requires macOS build environment)

Planned expansion:
- ⏳ Windows arm64
- ⏳ Linux arm64

**Important**: Electron applications **cannot be cross-compiled**. Each platform must be built on its native OS due to:
- Platform-specific Electron binaries
- Native Node.js module compilation
- OS-specific electron-builder requirements

## Build Information

### Build Method
Builds from source using:
- **pnpm 10.20.0** (via corepack)
- **Node.js 24.x** (LTS)
- **electron-builder 26.0.12**
- **C/C++ compilers** (for native node modules)

### Build Requirements
- **Time**: 15-30 minutes (depends on CPU/network)
- **Disk Space**: ~3 GB during build
- **Memory**: 6 GB RAM recommended (Vite renderer build)
- **Network**: ~500 MB download (node_modules + Electron binary)

### Build Outputs
- **Package Size**: ~300-350 MB (unpacked Electron app)
- **Install Location**: `$PREFIX/lib/podman-desktop/`
- **Launcher**: `$PREFIX/bin/podman-desktop`
- **Desktop File**: `$PREFIX/share/applications/podman-desktop.desktop` (Linux)
- **Icon**: `$PREFIX/share/icons/hicolor/512x512/apps/podman-desktop.png` (Linux)

## Local Build Instructions

### Linux Build

#### Using Rattler Build (recipe.yaml)
```bash
# Build for Linux x64
rattler-build build --recipe recipes/podman-desktop --target-platform linux-64 -c conda-forge

# Output: output/linux-64/podman-desktop-1.24.2-*.conda
```

#### Using conda-build (meta.yaml)
```bash
# Build for current platform
conda-build recipes/podman-desktop

# Output: $CONDA_BLD_PATH/linux-64/podman-desktop-1.24.2-*.tar.bz2
```

### Windows Build

**Requirements**:
- Windows 10/11 x64
- Visual Studio 2017 or newer (with C++ build tools)
- Python 3.12 (for node-gyp)
- Node.js 24.x
- rattler-build or conda-build

**Build on Windows**:
```batch
REM Using rattler-build
rattler-build build --recipe recipes/podman-desktop --target-platform win-64 -c conda-forge

REM Using conda-build
conda-build recipes/podman-desktop

REM Output: output\win-64\podman-desktop-1.24.2-*.conda
```

**Note**: Windows builds **must be performed on a Windows machine**. Cross-compilation from Linux/macOS is not supported for Electron applications.

### Testing the Build
```bash
# Install from local build
conda install -c local podman-desktop

# Test CLI
podman-desktop --version
podman-desktop --help

# Launch GUI (Linux)
podman-desktop
```

## Recipe Formats

This recipe provides **both** modern and legacy formats:

### recipe.yaml (Primary - Rattler Build)
- Modern format with `schema_version: 1`
- Uses `${{ }}` context substitution
- Platform selectors via `if/then/else`
- Schema validation via YAML language server

### meta.yaml (Fallback - conda-build)
- Legacy format for conda-build compatibility
- Uses `{{ }}` Jinja2 templating
- Platform selectors via `# [selector]` comments
- Required for conda-smithy linting

## Known Limitations

### Current MVP (Phase 1)
- **Linux x64 only**: Other platforms require additional testing
- **Build time**: 15-30 minutes due to TypeScript compilation and Electron packaging
- **Memory intensive**: Requires 6 GB RAM for Vite renderer build
- **Large package**: ~300 MB due to bundled Electron runtime and Chromium

### Platform-Specific Notes

**Linux**:
- Requires X11 or Wayland display server
- Dependencies: libgl, libxkbfile, libsecret (included in recipe)
- Desktop integration via .desktop file

**macOS** (Planned):
- Requires macOS 10.15+ (Catalina)
- Both x64 (Intel) and arm64 (Apple Silicon) support planned
- Universal binaries NOT planned (too large for conda)

**Windows** (Planned):
- Requires Windows 10+
- Visual Studio 2022 build tools needed for native modules
- x64 initially, arm64 later

## Build Process Details

### Steps
1. **Setup**: Enable pnpm via corepack (bundled with Node.js 24+)
2. **Install**: `pnpm install --frozen-lockfile` (~500 MB node_modules)
3. **Build**: `pnpm build` (compile TypeScript/Svelte)
4. **Package**: `pnpm compile:linux` (electron-builder creates distributable)
5. **Licenses**: Generate ThirdPartyNotices.txt for npm dependencies
6. **Install**: Copy app bundle to `$PREFIX/lib/podman-desktop/`
7. **Integrate**: Create launcher script and desktop file

### Key Environment Variables
- `NODE_OPTIONS=--max-old-space-size=6144` - Memory limit for Vite
- `CSC_IDENTITY_AUTO_DISCOVERY=false` - Disable code signing
- `PUBLISH_FOR_UPDATES=false` - Disable auto-update

### Code Signing
Code signing is **disabled** for conda builds:
- Not needed for conda distribution
- Avoids certificate requirements
- Simplifies build process

## Troubleshooting

### Build Fails: Out of Memory
**Problem**: Vite renderer build uses 6 GB RAM

**Solution**:
- Ensure system has 8+ GB RAM
- Set `NODE_OPTIONS=--max-old-space-size=6144` (already in build.sh)
- Close other applications during build

### Build Fails: pnpm not found
**Problem**: corepack not enabled

**Solution**:
```bash
corepack enable
corepack prepare pnpm@10.20.0 --activate
```

### Build Fails: Native Module Compilation
**Problem**: Missing C/C++ compilers or Python

**Solution**:
- Ensure GCC/Clang installed (Linux/macOS)
- Ensure Visual Studio Build Tools installed (Windows)
- Python 3.12 required for node-gyp

### GUI Doesn't Start: Display Error
**Problem**: No X11/Wayland display

**Solution** (Headless testing):
```bash
# Use Xvfb for headless testing
xvfb-run -a podman-desktop --version
```

### Long Build Times
**Problem**: 20+ minute builds in CI

**Solution**:
- Use CI caching for node_modules and pnpm store
- Consider pre-built binary approach (see Alternative Approach below)

## Alternative Approach: Pre-Built Binaries

If source builds prove too slow or complex, consider packaging pre-built binaries:

### Pros
- Fast builds (2-5 minutes)
- Matches upstream tested binaries
- Smaller recipe complexity

### Cons
- Not "building from source"
- May not pass conda-forge review for staged-recipes
- Dependent on upstream release cadence

### Example
```yaml
# Download official release tarball instead
source:
  url: https://github.com/podman-desktop/podman-desktop/releases/download/v1.24.2/podman-desktop-1.24.2-linux-x64.tar.gz
  sha256: <hash>
```

## Linting

Before submission to conda-forge:

```bash
# Run conda-smithy linter
conda-smithy recipe-lint recipes/podman-desktop

# Common checks:
# ✅ License case (Apache-2.0 not apache-2.0)
# ✅ License files exist
# ✅ Source is tarball with SHA256
# ✅ All dependencies exist in conda-forge
# ✅ No generic instruction comments
```

## Dependencies

All build and runtime dependencies exist in conda-forge:
- nodejs 24.x ✅
- gcc/gxx compilers ✅
- python 3.12 ✅
- libgl-devel, libxkbfile-devel, libsecret-devel (Linux) ✅

## Future Roadmap

### Phase 2: Platform Expansion
1. **macOS support** (x64 and arm64)
   - Update build.sh for macOS-specific steps
   - Handle .app bundle installation
   - Test on macOS runners

2. **Windows support** (x64 and arm64)
   - Complete bld.bat implementation
   - Handle .exe installation
   - Test on Windows runners

3. **Linux arm64** support
   - Electron provides arm64 binaries
   - Native modules compile via ARM GCC
   - Test on aarch64 runners

### Phase 3: Optimizations
- CI caching strategy for node_modules
- Build time optimization (<15 min target)
- Package size reduction if possible

## References

- **Upstream**: https://github.com/podman-desktop/podman-desktop
- **Documentation**: https://podman-desktop.io/docs
- **Conda-forge**: https://conda-forge.org/docs/
- **Rattler Build**: https://rattler.build/latest/
- **Electron**: https://www.electronjs.org/

## Maintainers

- @rxm7706

## License

This conda recipe is released under the same license as Podman Desktop: Apache-2.0
