# Enterprise Deployment & Air-Gapped Environments

Complete guide for deploying conda-forge packages in environments without internet access, and integrating with JFrog Artifactory. This document consolidates the architecture for air-gapped setups and the Artifactory proxying mechanism.

---

## 1. Air-Gapped Environment Setup

Air-gapped environments require:
1. **Package Mirror** - Local copy of required packages
2. **Build Tools** - Offline-capable build infrastructure
3. **Channel Configuration** - Point to local mirrors

### Architecture Options

1. **Full Mirror**: Mirror entire conda-forge channel locally. (Pros: Complete package availability. Cons: Large storage, slow sync).
2. **Selective Mirror**: Mirror only required packages and dependencies. (Pros: Smaller footprint. Cons: May miss transitive dependencies).
3. **Artifactory Proxy (Hybrid)**: Use Artifactory to cache packages on-demand. (Pros: Automatic caching. Cons: Requires initial internet access).

### Setup Steps

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

### Mirror Management (Using `scripts/mirror-channels.py`)

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

### Building Packages Offline (Using `scripts/offline-build.sh`)

1. **Prerequisites**: Pre-download build tools (`rattler-build`, `conda-build`, `python=3.12`) into an environment and transfer it.
2. **Build Process**:
```bash
export CONDA_OFFLINE=1
export CONDA_PKGS_DIRS=/opt/mirror/pkgs
./scripts/offline-build.sh recipes/my-package
```

---

## 2. JFrog Artifactory Integration

Artifactory can serve as a Remote Repository (proxy), a Local Repository (internal packages), and a Virtual Repository (combined).

### Repository Setup via REST API

**Remote Repository (Proxy)**
```bash
curl -X PUT \
  -H "Authorization: Bearer $ARTIFACTORY_TOKEN" \
  -H "Content-Type: application/json" \
  "https://artifactory.company.com/artifactory/api/repositories/conda-forge-remote" \
  -d '{
    "key": "conda-forge-remote",
    "rclass": "remote",
    "packageType": "conda",
    "url": "https://conda.anaconda.org/conda-forge",
    "repoLayoutRef": "simple-default"
  }'
```

**Local & Virtual Repositories**
Follow the same pattern for `conda-internal` (rclass: local) and `conda-all` (rclass: virtual, containing both).

### Client Configuration

**~/.condarc**
```yaml
channels:
  - https://artifactory.company.com/artifactory/api/conda/conda-all
channel_alias: https://artifactory.company.com/artifactory/api/conda
ssl_verify: /etc/pki/tls/certs/company-ca-bundle.crt
```

**pixi.toml**
```toml
[project]
channels = ["https://artifactory.company.com/artifactory/api/conda/conda-all"]
```

### Uploading Packages

**Via curl**
```bash
curl -H "Authorization: Bearer $ARTIFACTORY_TOKEN" \
  -T my-package.conda \
  "https://artifactory.company.com/artifactory/conda-internal/linux-64/my-package.conda"
```

*Note: You must trigger a reindex after uploading:*
```bash
curl -X POST \
  -H "Authorization: Bearer $ARTIFACTORY_TOKEN" \
  "https://artifactory.company.com/artifactory/api/conda/conda-internal/reindex"
```

### CI/CD Integration Example (GitHub Actions)

```yaml
name: Build and Publish
on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup conda
        uses: conda-incubator/setup-miniconda@v3
        with:
          channels: ${{ secrets.ARTIFACTORY_CONDA_URL }}
      - name: Build package
        run: |
          rattler-build build -r recipe.yaml -c ${{ secrets.ARTIFACTORY_CONDA_URL }}
      - name: Upload to Artifactory
        env:
          ARTIFACTORY_TOKEN: ${{ secrets.ARTIFACTORY_TOKEN }}
        run: |
          for pkg in output/*.conda; do
            curl -H "Authorization: Bearer $ARTIFACTORY_TOKEN" \
              -T "$pkg" \
              "${{ secrets.ARTIFACTORY_URL }}/artifactory/conda-internal/linux-64/$(basename $pkg)"
          done
```
