---
sources:
  - scripts/mirror-channels.py
  - scripts/offline-build.sh
  - docs/explanation/enterprise-deployment.md
  - docs/reference/pixi-config-jfrog.example.toml
  - .scripts/build_steps.sh
verified: 2026-11-24
---

# Air-gapped mirror setup

Procedural steps for mirroring conda-forge packages and building offline. For architecture rationale and JFrog integration design, see [`docs/explanation/enterprise-deployment.md`](../explanation/enterprise-deployment.md).

To adopt the operating model and fill a clone's shared substrate on the same site, see [How to use Marshal's seed and substrate bootstrap in an air-gapped site](use-marshal-in-an-air-gapped-site.md).

Air-gapped environments require:

1. **Package Mirror** — Local copy of required packages
2. **Build Tools** — Offline-capable build infrastructure
3. **Channel Configuration** — Point to local mirrors

## Architecture options

1. **Full Mirror**: Mirror entire conda-forge channel locally. (Pros: Complete package availability. Cons: Large storage, slow sync).
2. **Selective Mirror**: Mirror only required packages and dependencies. (Pros: Smaller footprint. Cons: May miss transitive dependencies).
3. **Artifactory Proxy (Hybrid)**: Use Artifactory to cache packages on-demand. (Pros: Automatic caching. Cons: Requires initial internet access).

## Setup steps

**Step 1: Inventory Required Packages**

```bash
# Export from existing environment
mamba env export -n myenv > environment.yml

# Or list specific packages
cat > packages.txt << EOF
python=3.12
numpy>=1.26
pandas>=2.0
EOF
```

**Step 2: Resolve Dependencies**

```bash
# Get full dependency tree
mamba create -n temp --dry-run \
  -c conda-forge \
  --file packages.txt \
  --json > resolved.json

# Extract package URLs
python -c "
import json
data = json.load(open('resolved.json'))
for pkg in data.get('actions', {}).get('FETCH', []):
    print(pkg['url'])
" > urls.txt
```

**Step 3: Download Packages**

```bash
mkdir -p mirror/conda-forge/{linux-64,osx-64,osx-arm64,win-64,noarch}

while read url; do
    subdir=$(echo $url | grep -oP '(linux-64|osx-64|osx-arm64|win-64|noarch)')
    filename=$(basename $url)
    curl -L -o "mirror/conda-forge/$subdir/$filename" "$url"
done < urls.txt
```

**Step 4: Generate Repodata**

```bash
mamba install -c conda-forge conda-index

# conda-index takes the channel root and indexes every subdir under it
python -m conda_index mirror/conda-forge
```

**Step 5: Transfer to Air-Gapped System**

```bash
tar -czvf conda-mirror.tar.gz mirror/
# On air-gapped system:
tar -xzvf conda-mirror.tar.gz -C /opt/
```

**Step 6: Configure Conda & pip**

On air-gapped systems, create `/etc/conda/condarc`:

```yaml
channels:
  - file:///opt/mirror/conda-forge
  - nodefaults
offline: true
ssl_verify: false
allow_other_channels: false
notify_outdated_conda: false
```

Configure `~/.config/pip/pip.conf`:

```ini
[global]
index-url = https://internal-pypi.company.com/simple
trusted-host = internal-pypi.company.com
```

## Mirror management (`scripts/mirror-channels.py`)

The script has four subcommands: `mirror`, `verify`, `cleanup` and `index`. It needs the
`requests` package.

**Create or update a mirror**

```bash
python scripts/mirror-channels.py mirror \
  --source conda-forge \
  --dest /path/to/mirror \
  --packages-file packages.txt
```

`mirror` resolves dependencies unless you pass `--no-deps`, and takes `--packages <name ...>`,
`--subdirs <subdir ...>` and `--workers <n>` (default 4). Re-run it to pick up new versions.

**Verify, clean up, reindex**

```bash
python scripts/mirror-channels.py verify /path/to/mirror
python scripts/mirror-channels.py cleanup /path/to/mirror --keep-versions 2
python scripts/mirror-channels.py index /path/to/mirror
```

## Building packages offline (`scripts/offline-build.sh`)

1. **Prerequisites**: Pre-download build tools (`rattler-build`, `conda-build`, `python=3.12`) into an environment and transfer it.
2. **Build Process**:

```bash
./scripts/offline-build.sh recipes/my-package --mirror /opt/mirror
```

The script sets `CONDA_OFFLINE=1` and `CONDA_PKGS_DIRS=<mirror>/pkgs` itself and builds against
`file://<mirror>/conda-forge`. The mirror path defaults to `/opt/conda-mirror`
(`CONDA_MIRROR_PATH`), so pass `--mirror` when you extracted to `/opt/mirror` as in Step 5.
Other options: `--target-platform <platform>`, `--output <dir>` (default `./output`) and
`--conda-build` for `meta.yaml` recipes; rattler-build is the default.

## JFrog-proxied deployment checklist

The steps above cover raw filesystem mirroring. If you're behind JFrog Artifactory instead (see
[`docs/explanation/enterprise-deployment.md`](../explanation/enterprise-deployment.md) § 2 for the
proxy architecture), use this checklist instead of Steps 1-6.

### Setup (one-time)

- [ ] Confirm JFrog has remote repositories for: conda-forge, pypi.org, files.pythonhosted.org (recommended), api.anaconda.org (optional)
- [ ] Set up corporate CA in OS trust store, or set `REQUESTS_CA_BUNDLE` env var, or pixi's `tls-root-certs = "system"`
- [ ] Author `~/.pixi/config.toml` from the template at `docs/reference/pixi-config-jfrog.example.toml` (never overwrite the tracked project file `.pixi/config.toml`)
- [ ] Set up `*_BASE_URL` env vars in `~/.bashrc` / `.envrc` / pixi env activation (see [`docs/explanation/enterprise-deployment.md`](../explanation/enterprise-deployment.md) § 6 for the full table)
- [ ] Bootstrap the CVE database from the internal mirror: `pixi run -e local-recipes update-cve-db`
- [ ] Bootstrap the atlas: `pixi run -e local-recipes bootstrap-data -- --fresh` (30-45 min cold; uses your `*_BASE_URL` overrides)
- [ ] Validate: `pixi run -e local-recipes health-check` (expects no public-host errors)
- [ ] Confirm the `build` env resolves — `environment.yaml` is exported from it, and the Docker build lane (`.scripts/build_steps.sh`) installs that file
- [ ] Decide which `pyforge-*` envs you need; they are `no-default-feature`, so each pulls only its own run-deps (`pyforge-guild` is the session default, `local-recipes` is the recipe factory)
- [ ] Run `pixi run -e pyforge-guild bmad-preflight` (it calls `pyforge steward session check`) to confirm the environment, the BMAD installation and the active project

### Per-session

- [ ] Confirm `JFROG_API_KEY` is set ONLY in JFrog-only shells (or use subshell scoping — see § *Cross-host credential leak* in the explanation doc)
- [ ] If running cron jobs, wrap each cron command in a subshell that unsets `JFROG_API_KEY` if it hits external hosts
