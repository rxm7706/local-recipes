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

# Debug — note: --debug flag was removed in v0.61 (Mar 2026); use the dedicated subcommand
rattler-build build -r recipe.yaml --render-only   # Render only
rattler-build build -r recipe.yaml --keep-build    # Keep build dir
rattler-build debug -r recipe.yaml                 # Drop into a debug shell

# Environment isolation modes (v0.62+, Apr 2026)
rattler-build build -r recipe.yaml --env-isolation strict       # default; remaps $HOME
rattler-build build -r recipe.yaml --env-isolation conda-build  # legacy compat
rattler-build build -r recipe.yaml --env-isolation none         # debug only — never ship

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

**Sdist (preferred):**
```
https://pypi.org/packages/source/{first_letter}/{name}/{name}-{version}.tar.gz
```

Example:
```
https://pypi.org/packages/source/r/requests/requests-2.31.0.tar.gz
```

**Wheel (only when no sdist exists):**
```
https://pypi.org/packages/{py_tag}/{first_letter}/{name}/{name}-{version}-{py_tag}-none-any.whl
```

Example:
```
https://pypi.org/packages/py3/r/runcell/runcell-0.1.15-py3-none-any.whl
```

**Never** use the hashed `https://files.pythonhosted.org/packages/<aa>/<bb>/<longhash>/...` URL — it bypasses standard JFrog Artifactory PyPI proxies in air-gapped corporate setups. See `docs/enterprise-deployment.md` §3.

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

## Project Pixi Tasks

Tasks defined in this repo's `pixi.toml` for the local-recipes monorepo. Each is also available as an MCP tool where noted.

> **Tip:** Pixi task names invoke the entrypoint wrapper layer at
> `.claude/scripts/conda-forge-expert/`, which delegates to the canonical
> implementation in `.claude/skills/conda-forge-expert/scripts/`. Run any task
> with `--help` to see its options. Pass extra args after `--`:
> `pixi run -e local-recipes validate -- recipes/<name>`.

### Environment & preflight

```bash
# Confirm the shell is inside the local-recipes pixi environment
pixi run -e local-recipes verify-env

# Combined env + BMAD-installation + active-project check before BMAD work
pixi run -e local-recipes bmad-preflight

# Full diagnostic on the dev environment (also: run_system_health_check MCP tool)
pixi run -e local-recipes health-check
```

### Recipe authoring

```bash
# Validate / lint a recipe
pixi run -e local-recipes validate recipes/<name>/recipe.yaml
pixi run -e local-recipes lint-optimize recipes/<name>/recipe.yaml
pixi run -e conda-smithy lint recipes/<name>

# Resolve a PyPI package name to its conda-forge equivalent
pixi run -e local-recipes resolve-name <pypi-name>

# Check that all recipe deps resolve on conda-forge
pixi run -e local-recipes check-deps recipes/<name>/recipe.yaml

# Validate SPDX license + license_file presence
pixi run -e local-recipes license-check recipes/<name>/recipe.yaml

# Scaffold a new recipe from PyPI / template / GitHub
pixi run -e local-recipes generate-recipe <pypi-name>

# Per-source recipe scaffolders
pixi run -e local-recipes generate-cran <r-package>          # CRAN
pixi run -e local-recipes generate-cpan <perl-module>        # CPAN
pixi run -e local-recipes generate-luarocks <lua-rock>       # LuaRocks
pixi run -e local-recipes generate-npm <npm-package>         # npm registry

# Grayskull-based scaffolding (alternative entrypoint, separate env)
pixi run -e grayskull pypi <pypi-name>                       # v1 recipe.yaml
pixi run -e grayskull cran <r-package>                       # v1 recipe.yaml
pixi run -e grayskull pypi-v0 <pypi-name>                    # legacy meta.yaml
pixi run -e grayskull cran-v0 <r-package>                    # legacy meta.yaml

# Migrate meta.yaml → recipe.yaml v1 (use --dry-run first)
pixi run -e local-recipes migrate recipes/<name>/meta.yaml

# Read-only latest-release lookup
pixi run -e local-recipes version-check --repo <owner>/<repo>
```

### Autotick (recipe updates)

```bash
# PyPI / GitHub / npm autotick — all support --dry-run
pixi run -e local-recipes autotick recipes/<name>/recipe.yaml
pixi run -e local-recipes autotick-github recipes/<name>/recipe.yaml
pixi run -e local-recipes autotick-npm recipes/<name>/recipe.yaml
```

### Local builds (Docker-less rattler-build)

```bash
# Diagnose available platforms / SDKs first
pixi run -e local-recipes build-local-check

# Native build (linux-64) with full tests
pixi run -e local-recipes build-local recipes/<name>

# All supported platforms (skips tests on cross-targets)
pixi run -e local-recipes build-local-all recipes/<name>

# Download MacOSX SDK to ./SDKs/ for osx-* cross-builds
pixi run -e local-recipes build-local-setup-sdk
```

### Per-platform build runners (Docker / native)

These wrap `build-locally.py` and live in dedicated feature envs (`linux`,
`osx`, `win`). Use them when you want the full per-platform variant matrix
rather than a single rattler-build invocation.

```bash
pixi run -e linux build-linux            # all linux-* configs (Docker on host)
pixi run -e osx build-osx                # all osx-* configs (native; macOS only)
pixi run -e win build-win                # all win-* configs (native; Windows only)

# Activation-script siblings — populate per-platform shell env (sourced auto by pixi)
pixi run -e osx build-osx.env
pixi run -e win build-win.env
```

### Cross-channel package intelligence (Atlas)

```bash
# Build / refresh the conda-forge atlas (~165 MB SQLite, ~10 min first time)
pixi run -e local-recipes build-cf-atlas

# Query the atlas for a single package
pixi run -e local-recipes query-cf-atlas <name>

# Atlas summary stats
pixi run -e local-recipes stats-cf-atlas

# Detail card with cross-channel + build matrix.
# Build matrix tries api.anaconda.org first; on failure (corporate egress
# blocks) it falls back to current_repodata.json from a conda channel
# mirror via _http.resolve_conda_forge_urls() — see "Air-gap fallback"
# below. Add --vdb in the vuln-db env for multi-source CVE lookup.
pixi run -e local-recipes detail-cf-atlas <name>
pixi run -e vuln-db detail-cf-atlas <name> --vdb

# Scope the vuln scan to a specific version (defaults to latest_conda_version
# from the atlas). Useful when you want CVEs affecting a release you're pinned to.
pixi run -e vuln-db detail-cf-atlas <name> --version 5.2.12 --vdb --vdb-all

# Same as above, but using the convenience wrapper task that presets --vdb --vdb-all.
pixi run -e vuln-db detail-cf-atlas-vdb <name> --version 5.2.12

# Air-gap fallback: when api.anaconda.org is blocked but a conda channel
# mirror is reachable, the build matrix is fetched from current_repodata.json.
# The resolver chain is: CONDA_FORGE_BASE_URL env → pixi `mirrors` →
# pixi `default-channels` → repo.prefix.dev/conda-forge →
# conda.anaconda.org/conda-forge. JFrog auth headers (X-JFrog-Art-Api or
# Basic) are injected automatically when the relevant env vars are set.
CONDA_FORGE_BASE_URL=https://artifactory.corp/artifactory/conda-forge \
JFROG_API_KEY=$MY_KEY \
  pixi run -e local-recipes detail-cf-atlas <name>
```

### Vulnerability scanning (vuln-db env)

```bash
# Build / refresh the AppThreat multi-source vulnerability DB (~5–10 min)
pixi run -e vuln-db vdb-refresh

# Refresh the lighter OSV CVE DB used by scan-vulnerabilities
pixi run -e local-recipes update-cve-db

# Scan a recipe's pinned deps using the local OSV DB
pixi run -e local-recipes scan-vulnerabilities recipes/<name>/recipe.yaml

# Scan a project tree (or --github URL) across pixi.lock, pixi.toml, Cargo.lock,
# requirements.txt, pyproject.toml, environment.yml, Containerfile.
# Add --os for OS-level CVEs, --brief for summary, --sbom {cyclonedx,spdx}.
pixi run -e vuln-db scan-project <path-or-dir>
pixi run -e vuln-db scan-project --github <owner>/<repo>

# Inventory a channel/mirror (conda repodata.json, PyPI Simple, npm, crates.io).
# JFrog auth via env vars; --diff for upstream comparison; --health for mirror signals.
pixi run -e vuln-db inventory-channel <url-or-file>
```

### Atlas intelligence (v7.0.0)

The cf_atlas data layer (~16 schema versions, 15 phases, 12 MCP tools).
All read-side CLIs are **offline-safe**; Phase G's *fresh* vuln data
needs the `vuln-db` env (cached counts work everywhere).

```bash
# Build / rebuild the atlas
pixi run -e local-recipes build-cf-atlas
PHASE_E_ENABLED=1 pixi run -e local-recipes build-cf-atlas    # incl. cf-graph
PHASE_N_ENABLED=1 PHASE_N_MAINTAINER=rxm7706 \
    pixi run -e local-recipes build-cf-atlas                    # + GitHub live data

# Phase F download source: auto | anaconda-api | s3-parquet (default auto;
# auto probes api.anaconda.org once and falls through to S3 on failure)
PHASE_F_SOURCE=s3-parquet pixi run -e local-recipes build-cf-atlas
PHASE_F_S3_MONTHS=24 PHASE_F_SOURCE=s3-parquet \
    pixi run -e local-recipes build-cf-atlas                    # trailing-24-months cap

# Per-package detail card (offline)
pixi run -e local-recipes detail-cf-atlas <pkg>
pixi run -e vuln-db detail-cf-atlas-vdb <pkg>                   # with live vdb scan

# Maintainer triage
pixi run -e local-recipes staleness-report --maintainer <handle>
pixi run -e local-recipes staleness-report --by-risk --has-vulns
pixi run -e local-recipes staleness-report --bot-stuck

# Feedstock health (Phase M cf-graph + Phase N GitHub live)
pixi run -e local-recipes feedstock-health --maintainer <handle> \
    --filter stuck   # or: bad / open-pr / ci-red / open-issues / open-prs-human / all

# Dependency graph queries (Phase J)
pixi run -e local-recipes whodepends <pkg>                     # forward
pixi run -e local-recipes whodepends <pkg> --reverse           # who depends on this

# Multi-source upstream-of-record comparison (Phase H/K/L)
pixi run -e local-recipes behind-upstream --maintainer <handle>

# CVE delta vs prior snapshot (Phase G snapshot history)
pixi run -e local-recipes cve-watcher --maintainer <handle> \
    --severity C --only-increases

# Per-version downloads + release cadence (Phase I)
pixi run -e local-recipes version-downloads <pkg>
pixi run -e local-recipes release-cadence --maintainer <handle>

# Lifecycle & alternatives
pixi run -e local-recipes adoption-stage --package <pkg>
pixi run -e local-recipes find-alternative <archived-pkg>

# Unified scanner (also has inventory-channel and scan-project below)
pixi run -e vuln-db scan-project <path>                          # local manifest discovery
pixi run -e vuln-db scan-project --image python:3.12             # container (syft/trivy)
pixi run -e vuln-db scan-project --sbom-in <file>                # CycloneDX/SPDX/syft/trivy
pixi run -e vuln-db scan-project --conda-env <env-path>          # live conda env
pixi run -e vuln-db scan-project --venv <venv-path>              # live Python venv
pixi run -e vuln-db scan-project --helm-chart <chart-path>       # helm template
pixi run -e vuln-db scan-project --kustomize <overlay-path>      # kustomize build
pixi run -e vuln-db scan-project --argo-app <cr.yaml>            # Argo CD Application
pixi run -e vuln-db scan-project --flux-cr <cr.yaml>             # Flux HelmRelease/Kustomization
pixi run -e vuln-db scan-project --kubectl-all                   # live K8s cluster scan
pixi run -e vuln-db scan-project --oci-manifest <ref>            # registry probe (no SBOM)
pixi run -e vuln-db scan-project <path> --license-check \
    --target-license Apache-2.0                                  # license compatibility
pixi run -e vuln-db scan-project <path> --sbom cyclonedx \
    --enrich-vulns-from-atlas                                    # SBOM with offline vuln annotations
```

### Maintenance & sync

```bash
# Refresh the PyPI ↔ conda name mapping cache (also: update_mapping_cache MCP tool)
pixi run -e local-recipes update-mapping-cache

# Sync with upstream conda-forge/staged-recipes (rebases local commits)
pixi run -e local-recipes sync-upstream-conda-forge

# Pull the latest from the public GitHub fork (rebase/merge local commits)
pixi run -e local-recipes sync-upstream-public-fork

# Submit a finished recipe to conda-forge (also: submit_pr MCP tool; use --dry-run first)
pixi run -e local-recipes submit-pr <recipe-name>

# Match a build error log against known failure patterns
pixi run -e local-recipes analyze-failure <path-to-error-log>
```

### Tests

```bash
# Offline / fast subset
pixi run -e local-recipes test

# Full suite incl. live-network tests
pixi run -e local-recipes test-all

# Coverage report
pixi run -e local-recipes test-coverage

# Run test-recipes.py (random / targeted recipe smoke validation)
pixi run -e local-recipes test-recipes
```

### Enterprise routing (JFrog Artifactory, internal mirrors)

Routing is **runtime-driven** via `_http.py`; nothing enterprise-specific lives in the committed `pixi.toml`. Set whichever env vars apply before `pixi run`:

```bash
# JFrog auth — first match wins (API key beats user/pass)
export JFROG_API_KEY=...                 # → X-JFrog-Art-Api header
# or:
export JFROG_USERNAME=... JFROG_PASSWORD=...   # → Basic auth

# GitHub API auth (only attached to *.github.com hosts; never leaks elsewhere)
export GITHUB_TOKEN=...                  # or GH_TOKEN

# Mirror redirection
export CONDA_FORGE_BASE_URL=https://artifactory.example.com/artifactory/conda-forge
export ANACONDA_API_BASE=https://artifactory.example.com/artifactory/anaconda
export GITHUB_API_BASE=https://github.example.com/api/v3
export S3_PARQUET_BASE_URL=https://artifactory.example.com/artifactory/anaconda-package-data  # Phase F S3 parquet mirror

# System trust roots (override only if your CA bundle isn't at the default)
export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

# Or use ~/.netrc for any host (Basic auth, picked up automatically)
# machine artifactory.example.com login alice password ...
```

See `docs/enterprise-deployment.md` for the full air-gapped setup.

### Pixi/uv install layer (separate from `_http.py`)

`pixi install -e vuln-db` resolves PyPI deps via uv **before** any conda-forge-expert script runs, so `_http.py`'s auth chain doesn't apply. If install fails on `files.pythonhosted.org` behind your firewall, point uv at JFrog's PyPI Simple index:

```bash
# Option A: project-local pixi config (gitignored)
cp docs/pixi-config-jfrog.example.toml .pixi/config.toml
$EDITOR .pixi/config.toml      # set JFrog URL + auth + tls-root-certs
pixi install -e vuln-db

# Option B: env vars (one-shot)
export UV_INDEX_URL="https://<jfrog-host>/artifactory/api/pypi/<repo>/simple"
export UV_NATIVE_TLS=true       # trust OS / corporate CA roots
export UV_KEYRING_PROVIDER=subprocess
pixi install -e vuln-db
```

Diagnose with `pixi install -e vuln-db -vvv`. See `docs/enterprise-deployment.md` § 4 for the full schema, auth methods, and JFrog admin alternative.
