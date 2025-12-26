# Conda-Forge Commands Cheatsheet

Quick reference for common conda-forge packaging commands.

## Package Managers

### pixi (Recommended)

```bash
# Install pixi
curl -fsSL https://pixi.sh/install.sh | sh              # macOS/Linux
powershell -c "irm https://pixi.sh/install.ps1 | iex"   # Windows

# Global installs
pixi global install rattler-build
pixi global install conda-smithy
pixi global install grayskull

# Project management
pixi init                          # Initialize project
pixi add numpy pandas              # Add dependencies
pixi add --pypi requests           # Add PyPI dependency
pixi run test                      # Run task
pixi shell                         # Enter environment
pixi lock                          # Lock dependencies
```

### conda/mamba

```bash
# Install from conda-forge
mamba install -c conda-forge <package>
conda install -c conda-forge <package>

# Create environment
mamba create -n myenv python=3.12 numpy
conda activate myenv

# Export environment
mamba env export > environment.yml
```

## Recipe Generation

### grayskull (Python/R packages)

```bash
# From PyPI
grayskull pypi <package-name>
grayskull pypi <package-name>==1.2.3        # Specific version
grayskull pypi https://github.com/user/repo # From GitHub

# From CRAN
grayskull cran <package-name>

# Options
grayskull pypi <pkg> --strict-conda-forge   # Strict mode
grayskull pypi <pkg> --output recipes/      # Output directory
```

### rattler-build generate-recipe

```bash
# From PyPI
rattler-build generate-recipe pypi numpy
rattler-build generate-recipe pypi numpy==1.26.0

# From CRAN
rattler-build generate-recipe cran ggplot2

# Convert meta.yaml to recipe.yaml
rattler-build generate-recipe convert meta.yaml
```

## Building

### rattler-build (Modern)

```bash
# Basic build
rattler-build build -r recipe.yaml
rattler-build build -r recipe.yaml -c conda-forge

# With variant config
rattler-build build -r recipe.yaml --variant-config .ci_support/win64.yaml

# Target platform
rattler-build build -r recipe.yaml --target-platform linux-64
rattler-build build -r recipe.yaml --target-platform osx-arm64

# Debug
rattler-build build -r recipe.yaml --render-only   # Render only
rattler-build build -r recipe.yaml --keep-build    # Keep build dir

# Test
rattler-build test --package-file output/*.conda
```

### conda-build (Legacy)

```bash
# Basic build
conda-build recipes/my-package
conda-build recipes/my-package -c conda-forge

# Test artifact
conda-build --test path/to/package.conda
conda-build --test path/to/package.tar.bz2

# Debug
conda-build recipes/my-package --debug
conda-build recipes/my-package --keep-old-work
```

### build-locally.py

```bash
# Interactive
python build-locally.py

# Specific platform
python build-locally.py win64
python build-locally.py linux64
python build-locally.py osx64
python build-locally.py osxarm64

# Filter
python build-locally.py --filter "win*"
```

## Linting

```bash
# Lint single recipe (MANDATORY before submission)
conda-smithy recipe-lint recipes/my-package

# Lint all recipes
conda-smithy recipe-lint --conda-forge recipes/*

# Lint with specific checks
conda-smithy recipe-lint recipes/my-package --pedantic
```

## Migration Tools

```bash
# feedrattler (meta.yaml to recipe.yaml feedstock)
pixi exec feedrattler my-package-feedstock gh_username

# conda-recipe-manager
pip install conda-recipe-manager
conda-recipe-manager convert meta.yaml > recipe.yaml

# Rerender feedstock
conda-smithy rerender
```

## Source Checksums

```bash
# Get SHA256 from URL
curl -sL https://url/to/source.tar.gz | sha256sum

# Get SHA256 from local file
sha256sum source.tar.gz

# PyPI source
curl -sL "https://pypi.org/packages/source/p/package/package-1.0.0.tar.gz" | sha256sum
```

## Git Operations

```bash
# Clone staged-recipes
git clone https://github.com/conda-forge/staged-recipes.git
cd staged-recipes

# Create branch for new recipe
git checkout -b add-my-package

# Submit PR
gh pr create --title "Add my-package" --body "Description..."
```

## GitHub CLI

```bash
# Trigger workflow
gh workflow run test-all.yml -f recipes="my-package"
gh workflow run test-linux.yml -f recipes="my-package"
gh workflow run test-windows.yml -f recipes="my-package"
gh workflow run test-macos.yml -f recipes="my-package"

# Watch run
gh run watch

# View logs
gh run view --log
```

## Testing Recipes

```bash
# test-recipes.py (local)
python test-recipes.py --recipe my-package
python test-recipes.py --recipe my-package --all          # All platforms
python test-recipes.py --recipe my-package --dry-run      # Preview
python test-recipes.py --random 5                         # Random recipes
python test-recipes.py --check                            # Check tools
```

## Environment Variables

```bash
# Windows
set CONFIG=win64
set CONDA_BLD_PATH=C:\bld

# Linux/macOS
export CONFIG=linux64
export CONDA_BLD_PATH=/tmp/bld

# Cross-compilation
export build_platform=linux-64
export target_platform=osx-arm64
```

## Debugging

```bash
# Check solver
mamba repoquery depends my-package
mamba repoquery whoneeds my-package

# Check artifact contents
tar -tvf package.conda
unzip -l package.conda

# Check repodata
curl -s https://conda.anaconda.org/conda-forge/linux-64/repodata.json | jq '.packages["pkg"]'

# Render recipe
rattler-build build -r recipe.yaml --render-only
conda-render recipes/my-package
```

## Common Patterns

### Get PyPI source URL
```
https://pypi.org/packages/source/{first_letter}/{name}/{name}-{version}.tar.gz
```

Example:
```
https://pypi.org/packages/source/r/requests/requests-2.31.0.tar.gz
```

### Check package exists on conda-forge
```bash
mamba search -c conda-forge my-package
curl -s "https://conda.anaconda.org/conda-forge/noarch/repodata.json" | jq '.packages | keys | map(select(startswith("my-package")))'
```

### Pin subpackage
```yaml
# recipe.yaml
- ${{ pin_subpackage("libfoo", upper_bound="x.x.x") }}
- ${{ pin_subpackage("libfoo", exact=true) }}

# meta.yaml
- {{ pin_subpackage('libfoo', max_pin='x.x.x') }}
- {{ pin_subpackage('libfoo', exact=True) }}
```
