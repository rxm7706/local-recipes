# Getting Started with conda-forge

A step-by-step guide to creating and submitting your first conda-forge recipe.

## Prerequisites

### Required Tools

Install these tools before starting:

```bash
# Using pixi (recommended)
pixi global install rattler-build
pixi global install conda-smithy
pixi global install grayskull

# OR using conda/mamba
mamba install -c conda-forge rattler-build conda-smithy grayskull
```

### Accounts Needed

1. **GitHub account** - Required for submitting recipes
2. **conda-forge membership** - Automatic after first merged PR

## Quick Start Workflow

```
1. Generate recipe → 2. Customize → 3. Lint → 4. Build locally → 5. Submit PR
```

## Step 1: Generate a Recipe

### For Python Packages (PyPI)

```bash
# Using grayskull (generates meta.yaml)
grayskull pypi my-package
grayskull pypi my-package==1.2.3  # Specific version

# Using rattler-build (generates recipe.yaml)
rattler-build generate-recipe pypi my-package
```

### For R Packages (CRAN)

```bash
grayskull cran my-package
rattler-build generate-recipe cran my-package
```

### From Templates

Copy a template from `templates/` and customize:

```bash
cp templates/python/noarch-recipe.yaml recipes/my-package/recipe.yaml
```

## Step 2: Customize the Recipe

### Essential Fields to Update

```yaml
# recipe.yaml (v1 format)
context:
  name: my-package           # Package name
  version: "1.2.3"           # Version
  python_min: "3.10"         # Minimum Python (for noarch)

source:
  sha256: ACTUAL_HASH        # Get from PyPI or curl

about:
  license: MIT               # SPDX identifier
  license_file: LICENSE      # Must exist in source

extra:
  recipe-maintainers:
    - your-github-username   # Your GitHub username
```

### Get the SHA256 Hash

```bash
# From PyPI
curl -sL "https://pypi.org/packages/source/m/my-package/my-package-1.2.3.tar.gz" | sha256sum

# From URL
curl -sL "https://github.com/org/repo/archive/v1.2.3.tar.gz" | sha256sum
```

### Check Dependencies Exist

All dependencies must already exist in conda-forge:

```bash
# Search for a package
mamba search -c conda-forge numpy

# Check if package exists
curl -s "https://conda.anaconda.org/conda-forge/noarch/repodata.json" | jq '.packages | keys | map(select(startswith("my-dep")))' | head
```

## Step 3: Lint the Recipe

**Always lint before building or submitting:**

```bash
conda-smithy recipe-lint recipes/my-package
```

### Common Lint Errors

| Error | Fix |
|-------|-----|
| `missing license_file` | Add `license_file: LICENSE` to about section |
| `missing recipe-maintainers` | Add your GitHub username to extra section |
| `should be noarch: python` | Add `noarch: python` for pure Python packages |
| `invalid license` | Use SPDX format (e.g., `MIT`, `Apache-2.0`) |

## Step 4: Build Locally

### Using rattler-build (Modern)

```bash
# Basic build
rattler-build build -r recipes/my-package/recipe.yaml -c conda-forge

# For specific platform
rattler-build build -r recipes/my-package/recipe.yaml \
  --target-platform linux-64 -c conda-forge
```

### Using conda-build (Legacy)

```bash
conda-build recipes/my-package -c conda-forge
```

### Using build-locally.py

```bash
# Interactive
python build-locally.py

# Specific platform
python build-locally.py linux64
python build-locally.py win64
python build-locally.py osx64
```

## Step 5: Submit to conda-forge

### Fork and Clone staged-recipes

```bash
# Fork https://github.com/conda-forge/staged-recipes on GitHub first
git clone https://github.com/YOUR-USERNAME/staged-recipes.git
cd staged-recipes
git remote add upstream https://github.com/conda-forge/staged-recipes.git
```

### Create a Branch

```bash
git checkout -b add-my-package
```

### Add Your Recipe

```bash
# Copy your recipe
cp -r /path/to/recipes/my-package recipes/

# Or create directly
mkdir -p recipes/my-package
# ... create recipe.yaml or meta.yaml
```

### Commit and Push

```bash
git add recipes/my-package
git commit -m "Add my-package recipe"
git push origin add-my-package
```

### Create Pull Request

1. Go to https://github.com/conda-forge/staged-recipes
2. Click "New pull request"
3. Select your branch
4. Fill in the template
5. Submit

### PR Checklist

Include this in your PR description:

```markdown
**Checklist:**
- [x] Title is "Add [package-name]"
- [x] License file is included
- [x] Source is from official source (PyPI, GitHub release)
- [x] Build number is 0
- [x] All dependencies exist on conda-forge
- [x] Recipe lints successfully
- [x] I am willing to maintain this package
```

## Recipe Format Choice

### Use recipe.yaml (v1) When:
- Starting new packages
- Want cleaner YAML syntax
- Need complex conditionals
- Using rattler-build

### Use meta.yaml (legacy) When:
- Contributing to existing feedstock
- Need conda-build specific features
- More examples available online

## Complete Example: Python Package

### recipe.yaml (Modern)

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/prefix-dev/recipe-format/main/schema.json
schema_version: 1

context:
  name: example-package
  version: "1.0.0"
  python_min: "3.10"

package:
  name: ${{ name | lower }}
  version: ${{ version }}

source:
  url: https://pypi.org/packages/source/${{ name[0] }}/${{ name }}/${{ name }}-${{ version }}.tar.gz
  sha256: abc123def456...

build:
  number: 0
  noarch: python
  script: ${{ PYTHON }} -m pip install . -vv --no-deps --no-build-isolation

requirements:
  host:
    - python ${{ python_min }}.*
    - pip
    - hatchling
  run:
    - python >=${{ python_min }}
    - click >=8.0
    - requests

tests:
  - python:
      imports:
        - example_package
      pip_check: true
  - script:
      - example-cli --version

about:
  homepage: https://github.com/org/example-package
  license: MIT
  license_file: LICENSE
  summary: An example Python package

extra:
  recipe-maintainers:
    - your-github-username
```

### meta.yaml (Legacy)

```yaml
{% set name = "example-package" %}
{% set version = "1.0.0" %}

package:
  name: {{ name|lower }}
  version: {{ version }}

source:
  url: https://pypi.org/packages/source/{{ name[0] }}/{{ name }}/{{ name }}-{{ version }}.tar.gz
  sha256: abc123def456...

build:
  number: 0
  noarch: python
  script: {{ PYTHON }} -m pip install . -vv --no-deps --no-build-isolation

requirements:
  host:
    - python {{ python_min }}
    - pip
    - hatchling
  run:
    - python >={{ python_min }}
    - click >=8.0
    - requests

test:
  imports:
    - example_package
  commands:
    - pip check
    - example-cli --version
  requires:
    - pip

about:
  home: https://github.com/org/example-package
  license: MIT
  license_file: LICENSE
  summary: An example Python package

extra:
  recipe-maintainers:
    - your-github-username
```

## After Your PR is Merged

1. **Feedstock Created**: A new repo `my-package-feedstock` is created
2. **Team Added**: You're added to the maintainer team
3. **Package Available**: Within ~30 minutes on conda-forge
4. **Auto-Updates**: Bot will create PRs for new versions

### Install Your Package

```bash
mamba install -c conda-forge my-package
```

## Common Issues

### "Dependency not found"

All dependencies must exist on conda-forge. Submit dependencies first.

### "Hash mismatch"

Re-download and recalculate:
```bash
curl -sL "URL" | sha256sum
```

### "Build fails on Windows"

- Check path separators (`/` vs `\`)
- Use `ninja` instead of `make`
- Add Windows-specific dependencies

### "noarch: python not suitable"

Remove `noarch: python` if package has:
- Compiled extensions
- Platform-specific code
- Entry points with shebangs

## Next Steps

- Read [Migration Guide](migration.md) to convert between formats
- Read [CI Troubleshooting](ci-troubleshooting.md) for build failures
- Read [Feedstock Maintenance](feedstock-maintenance.md) for updates

## Resources

- [conda-forge Documentation](https://conda-forge.org/docs/)
- [staged-recipes Repository](https://github.com/conda-forge/staged-recipes)
- [rattler-build Documentation](https://rattler.build/latest/)
- [Example Feedstocks](https://github.com/conda-forge?q=feedstock&type=all)
