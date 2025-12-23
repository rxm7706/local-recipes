# WriteFreely conda-forge Recipe

This recipe builds [WriteFreely](https://writefreely.org), a clean, Markdown-based
publishing platform made for writers.

## Recipe Formats

This folder contains **two recipe formats** - you only need one:

| File | Format | Tool | When to Use |
|------|--------|------|-------------|
| `meta.yaml` + `build.sh` + `bld.bat` | v0 (traditional) | conda-build | Most staged-recipes PRs |
| `recipe.yaml` | v1 (new) | rattler-build | Simple Go/Rust packages |

**For staged-recipes submission**, use `meta.yaml` + `build.sh` + `bld.bat` (delete `recipe.yaml`).

## About WriteFreely

WriteFreely is a Go-based blogging platform with the following features:
- Distraction-free, auto-saving editor
- Full Markdown support
- ActivityPub federation (connect with Mastodon, Pleroma, etc.)
- SQLite or MySQL database support
- Multi-user/community hosting

## Supported Platforms

| Platform | Status | Notes |
|----------|--------|-------|
| Linux x86_64 | ✅ Tested | Primary platform |
| macOS x86_64/arm64 | ✅ Should work | Same as Linux, CGO supported |
| Windows x86_64 | ✅ Should work | Uses `bld.bat`, requires conda-forge CGO |

## Prerequisites for Local Testing

### Linux/macOS
```bash
# Install conda/mamba
curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj bin/micromamba
# or
curl -fsSL https://pixi.sh/install.sh | bash

# Install conda-build
micromamba create -n build-env conda-build -c conda-forge -y
micromamba activate build-env
```

### Windows
```powershell
# Install miniforge or mambaforge from:
# https://github.com/conda-forge/miniforge/releases

# Install conda-build
conda install conda-build -c conda-forge -y
```

## Local Build Testing

### Linux/macOS - Quick Manual Test

If you want to quickly verify the build works without full conda-build:

```bash
# Install Go 1.23+ and SQLite
# Ubuntu/Debian:
sudo apt install golang sqlite3 libsqlite3-dev
# macOS:
brew install go sqlite3

# Clone and build
git clone https://github.com/writefreely/writefreely.git
cd writefreely
git checkout v0.16.0
export CGO_ENABLED=1
cd cmd/writefreely
go build -v -tags='netgo sqlite' -ldflags="-s -w" -o writefreely .
./writefreely --version
```

### Linux/macOS - Full conda-build Test

```bash
# Clone staged-recipes
git clone https://github.com/conda-forge/staged-recipes.git
cd staged-recipes

# Copy recipe files
cp -r /path/to/writefreely-recipe recipes/writefreely

# Build
conda build recipes/writefreely
```

### Windows - Full conda-build Test

```powershell
# Clone staged-recipes
git clone https://github.com/conda-forge/staged-recipes.git
cd staged-recipes

# Copy recipe files
Copy-Item -Recurse C:\path\to\writefreely-recipe recipes\writefreely

# Build (requires Visual Studio build tools for C compiler)
conda build recipes\writefreely
```

### Docker Test (Recommended - matches CI)

```bash
# Linux build
docker run --rm -v $(pwd):/recipe quay.io/condaforge/linux-anvil-cos7-x86_64 \
    conda build /recipe

# macOS cross-compile (from Linux)
docker run --rm -v $(pwd):/recipe quay.io/condaforge/linux-anvil-cos7-x86_64 \
    conda build /recipe --target-platform osx-64
```

## Submitting to conda-forge

1. Fork https://github.com/conda-forge/staged-recipes
2. Create a new branch: `git checkout -b add-writefreely`
3. Copy recipe files to `recipes/writefreely/`:
   - `meta.yaml`
   - `build.sh`
   - `bld.bat`
   - (optionally) `conda_build_config.yaml`
4. Replace `YOUR_GITHUB_USERNAME` in meta.yaml with your actual GitHub username
5. Commit and push your changes
6. Open a Pull Request to `conda-forge/staged-recipes`

## Post-Installation Usage

After installation, you can run WriteFreely:

```bash
# Initialize a new WriteFreely instance
mkdir my-blog && cd my-blog

# Copy static assets from conda installation
# Linux/macOS:
cp -r $CONDA_PREFIX/share/writefreely/* .
# Windows:
xcopy /E %CONDA_PREFIX%\Library\share\writefreely\* .

# Generate configuration
writefreely config generate

# Initialize database
writefreely db init

# Create admin user
writefreely user create --admin <username>

# Start the server
writefreely serve
```

## Technical Notes

### CGO Requirement

WriteFreely uses SQLite via `github.com/mattn/go-sqlite3`, which requires CGO.
The recipe uses:
- `{{ compiler('cgo') }}` - Go compiler with CGO enabled
- `{{ compiler('c') }}` - C compiler for SQLite bindings
- `{{ stdlib('c') }}` - C standard library

### Build Tags

The build uses these Go tags:
- `sqlite` - Enables SQLite database support
- `netgo` - Uses pure Go network stack (more portable)

### License Collection

The recipe uses `go-licenses` to collect all dependency licenses as required
by conda-forge policy. Licenses are stored in `library_licenses/`.

## Troubleshooting

### Build fails with CGO errors
Ensure the C compiler is available and CGO is enabled:
```bash
export CGO_ENABLED=1
go build -v -tags='netgo sqlite' ...
```

### Windows build fails
- Ensure Visual Studio Build Tools are installed
- The conda-forge CGO compiler should handle most cases
- Check that `%LIBRARY_BIN%` is set correctly

### Tests fail
```bash
# Unix
./writefreely --version

# Windows
writefreely.exe --version
```

### Missing static assets at runtime
WriteFreely requires templates/static files in its working directory:
```bash
# Copy from conda installation
cp -r $CONDA_PREFIX/share/writefreely/* ./
```
