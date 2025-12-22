# WriteFreely conda-forge Recipe

This recipe builds [WriteFreely](https://writefreely.org), a clean, Markdown-based
publishing platform made for writers.

## Recipe Formats

This folder contains **two recipe formats** - you only need one:

| File | Format | Tool | When to Use |
|------|--------|------|-------------|
| `meta.yaml` + `build.sh` | v0 (traditional) | conda-build | Most staged-recipes PRs |
| `recipe.yaml` | v1 (new) | rattler-build | Simple Go/Rust packages |

**For staged-recipes submission**, use `meta.yaml` + `build.sh` (delete `recipe.yaml`).

## About WriteFreely

WriteFreely is a Go-based blogging platform with the following features:
- Distraction-free, auto-saving editor
- Full Markdown support
- ActivityPub federation (connect with Mastodon, Pleroma, etc.)
- SQLite or MySQL database support
- Multi-user/community hosting

## Prerequisites for Local Testing

You'll need:
- `conda` or `mamba` (or `pixi`)
- `conda-build` package

```bash
# Using conda
conda install conda-build

# Or using pixi (your preferred tool)
pixi global install conda-build
```

## Local Build Testing

### Option 1: Using conda-build directly

```bash
# Clone staged-recipes if you haven't already
git clone https://github.com/conda-forge/staged-recipes.git
cd staged-recipes

# Copy this recipe to the recipes folder
cp -r /path/to/writefreely-recipe recipes/writefreely

# Build the recipe
conda build recipes/writefreely
```

### Option 2: Using the conda-forge docker image (recommended)

This ensures your build environment matches the CI:

```bash
# Pull the conda-forge build image
docker pull quay.io/condaforge/linux-anvil-cos7-x86_64

# Run the build in the container
docker run --rm -v $(pwd):/recipe quay.io/condaforge/linux-anvil-cos7-x86_64 \
    conda build /recipe
```

### Option 3: Using pixi with rattler-build

If you prefer the newer v1 recipe format with rattler-build:

```bash
pixi global install rattler-build
rattler-build build --recipe .
```

## Submitting to conda-forge

1. Fork https://github.com/conda-forge/staged-recipes
2. Create a new branch for your recipe
3. Copy the recipe files to `recipes/writefreely/`
4. Update `YOUR_GITHUB_USERNAME` in meta.yaml with your actual GitHub username
5. Commit and push your changes
6. Open a Pull Request to `conda-forge/staged-recipes`

## Post-Installation Usage

After installation, you can run WriteFreely:

```bash
# Initialize a new WriteFreely instance
mkdir my-blog && cd my-blog
writefreely config start

# Or generate a config file
writefreely config generate

# Start the server
writefreely
```

WriteFreely needs its static assets (templates, CSS, etc.) in the working directory.
The package includes these in `$CONDA_PREFIX/share/writefreely/` for reference.

You can copy them to your working directory:
```bash
cp -r $CONDA_PREFIX/share/writefreely/* .
```

## Notes

- **Windows Support**: Currently skipped due to CGO cross-compilation complexity.
  Windows users can use WSL2 or the official pre-built binaries.

- **SQLite vs MySQL**: This build includes SQLite support by default.
  For MySQL, WriteFreely will connect to an external MySQL server.

- **License Collection**: The recipe uses `go-licenses` to collect all
  dependency licenses as required by conda-forge policy.

## Troubleshooting

### Build fails with CGO errors
Make sure you have the C compiler available. The recipe uses `{{ compiler('c') }}`
along with `{{ compiler('cgo') }}`.

### Tests fail
Ensure the binary was built correctly:
```bash
./writefreely --version
```

### Missing static assets
WriteFreely expects certain files in its working directory. See the
post-installation usage section above.
