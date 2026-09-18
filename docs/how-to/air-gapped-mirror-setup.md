# Air-gapped mirror setup

Procedural steps for mirroring conda-forge packages and building offline. For architecture rationale and JFrog integration design, see [`docs/explanation/enterprise-deployment.md`](../explanation/enterprise-deployment.md).

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

for subdir in linux-64 osx-64 osx-arm64 win-64 noarch; do
    conda-index mirror/conda-forge/$subdir
done
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

**Update Mirror**

```bash
python scripts/mirror-channels.py \
  --source conda-forge \
  --dest /path/to/mirror \
  --packages-file packages.txt \
  --update
```

**Verify & Cleanup**

```bash
python scripts/mirror-channels.py --verify /path/to/mirror
python scripts/mirror-channels.py --cleanup /path/to/mirror --keep-versions 2
```

## Building packages offline (`scripts/offline-build.sh`)

1. **Prerequisites**: Pre-download build tools (`rattler-build`, `conda-build`, `python=3.12`) into an environment and transfer it.
2. **Build Process**:

```bash
export CONDA_OFFLINE=1
export CONDA_PKGS_DIRS=/opt/mirror/pkgs
./scripts/offline-build.sh recipes/my-package
```

## JFrog-proxied deployment checklist

The steps above cover raw filesystem mirroring. If you're behind JFrog Artifactory instead (see
[`docs/explanation/enterprise-deployment.md`](../explanation/enterprise-deployment.md) § 2 for the
proxy architecture), use this checklist instead of Steps 1-6.

### Setup (one-time)

- [ ] Confirm JFrog has remote repositories for: conda-forge, pypi.org, files.pythonhosted.org (recommended), api.anaconda.org (optional)
- [ ] Set up corporate CA in OS trust store, or set `REQUESTS_CA_BUNDLE` env var, or pixi's `tls-root-certs = "native"`
- [ ] Author `.pixi/config.toml` from the template at `docs/reference/pixi-config-jfrog.example.toml`
- [ ] Set up `*_BASE_URL` env vars in `~/.bashrc` / `.envrc` / pixi env activation (see [`docs/explanation/enterprise-deployment.md`](../explanation/enterprise-deployment.md) § 6 for the full table)
- [ ] Bootstrap the CVE database from the internal mirror: `pixi run -e vuln-db update-cve-db`
- [ ] Bootstrap the atlas: `pixi run bootstrap-data -- --fresh` (30-45 min cold; uses your `*_BASE_URL` overrides)
- [ ] Validate: `pixi run health-check` (expects no public-host errors)
- [ ] Confirm the `build` env resolves — the CI linter exports `environment.yaml` from it
- [ ] Decide which product envs you need; they are `no-default-feature` and cheap, but each still pulls its own run-deps
- [ ] **Do NOT** budget for `pixi run bmad-preflight` — that task is broken (see [`docs/how-to/pixi-tasks.md`](pixi-tasks.md))

### Per-session

- [ ] Confirm `JFROG_API_KEY` is set ONLY in JFrog-only shells (or use subshell scoping — see § *Cross-host credential leak* in the explanation doc)
- [ ] If running cron jobs, wrap each cron command in a subshell that unsets `JFROG_API_KEY` if it hits external hosts
