# Air-Gapped Environment Setup

Complete guide for deploying conda-forge packages in environments without internet access.

## Overview

Air-gapped environments require:
1. **Package Mirror** - Local copy of required packages
2. **Build Tools** - Offline-capable build infrastructure
3. **Channel Configuration** - Point to local mirrors

## Architecture Options

### Option 1: Full Mirror

Mirror entire conda-forge channel locally.

**Pros:** Complete package availability
**Cons:** Large storage (5+ TB), slow sync

### Option 2: Selective Mirror

Mirror only required packages and dependencies.

**Pros:** Smaller footprint, faster sync
**Cons:** May miss transitive dependencies

### Option 3: Artifactory Proxy (Hybrid)

Use Artifactory to cache packages on-demand.

**Pros:** Automatic caching, minimal setup
**Cons:** Requires initial internet access

## Setup Steps

### Step 1: Inventory Required Packages

Create a package list:

```bash
# Export from existing environment
mamba env export -n myenv > environment.yml

# Or list specific packages
cat > packages.txt << EOF
python=3.12
numpy>=1.26
pandas>=2.0
scikit-learn>=1.4
matplotlib>=3.8
EOF
```

### Step 2: Resolve Dependencies

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

### Step 3: Download Packages

```bash
# Download all packages
mkdir -p mirror/conda-forge/{linux-64,osx-64,osx-arm64,win-64,noarch}

while read url; do
    subdir=$(echo $url | grep -oP '(linux-64|osx-64|osx-arm64|win-64|noarch)')
    filename=$(basename $url)
    curl -L -o "mirror/conda-forge/$subdir/$filename" "$url"
done < urls.txt
```

### Step 4: Generate Repodata

```bash
# Install conda-index
mamba install -c conda-forge conda-index

# Index each subdirectory
for subdir in linux-64 osx-64 osx-arm64 win-64 noarch; do
    conda-index mirror/conda-forge/$subdir
done
```

### Step 5: Transfer to Air-Gapped System

```bash
# Create archive
tar -czvf conda-mirror.tar.gz mirror/

# Transfer via approved method (USB, secure file transfer, etc.)
# On air-gapped system:
tar -xzvf conda-mirror.tar.gz -C /opt/
```

### Step 6: Configure Conda

On air-gapped systems, create `/etc/conda/condarc`:

```yaml
channels:
  - file:///opt/mirror/conda-forge
  - nodefaults

offline: true

ssl_verify: false  # If using self-signed certs

# Disable network features
allow_other_channels: false
notify_outdated_conda: false
```

### Step 7: Configure pip (for PyPI fallback)

```bash
# Create pip.conf
mkdir -p ~/.config/pip
cat > ~/.config/pip/pip.conf << EOF
[global]
index-url = https://internal-pypi.company.com/simple
trusted-host = internal-pypi.company.com
EOF
```

## Mirror Management

### Update Mirror

On internet-connected system:

```bash
# Sync new packages
python enterprise/mirror-channels.py \
  --source conda-forge \
  --dest /path/to/mirror \
  --packages-file packages.txt \
  --update
```

### Verify Mirror Integrity

```bash
# Check package hashes
python enterprise/mirror-channels.py \
  --verify /path/to/mirror
```

### Remove Old Packages

```bash
# Keep only latest versions
python enterprise/mirror-channels.py \
  --cleanup /path/to/mirror \
  --keep-versions 2
```

## Building Packages Offline

### Prerequisites

Pre-download build tools:

```bash
# Create build environment
mamba create -n build-env \
  rattler-build \
  conda-build \
  conda-smithy \
  python=3.12

# Export for offline use
mamba list -n build-env --export > build-env-packages.txt
```

### Offline Build Process

```bash
# Set environment
export CONDA_OFFLINE=1
export CONDA_PKGS_DIRS=/opt/mirror/pkgs

# Build recipe
./enterprise/offline-build.sh recipes/my-package
```

### Handle Missing Dependencies

If a dependency is missing:

1. Add to mirror on connected system
2. Re-transfer to air-gapped system
3. Update local repodata index

## Troubleshooting

### "Package not found"

```bash
# Check if package exists in mirror
ls /opt/mirror/conda-forge/linux-64/ | grep package-name

# Verify repodata includes it
zcat /opt/mirror/conda-forge/linux-64/repodata.json.gz | jq '.packages | keys | map(select(startswith("package-name")))'
```

### "Hash mismatch"

Package may be corrupted. Re-download and re-index:

```bash
# Re-download
curl -L -o /opt/mirror/conda-forge/linux-64/package.conda "original-url"

# Re-index
conda-index /opt/mirror/conda-forge/linux-64
```

### "SSL certificate verify failed"

```yaml
# In condarc
ssl_verify: /path/to/company-ca-bundle.crt
# OR
ssl_verify: false  # Not recommended for production
```

## Security Considerations

### Package Verification

Verify package signatures before importing:

```bash
# Check package integrity
for pkg in mirror/conda-forge/*/*.conda; do
    conda-package-handling verify $pkg
done
```

### Allowlist Packages

Create package allowlist:

```yaml
# allowed-packages.yml
packages:
  - python>=3.10
  - numpy
  - pandas
  # ... approved packages only
```

### Audit Trail

Log all package installations:

```bash
# Enable logging
conda config --set report_errors true
conda config --set json_log_level info
```

## Automation

### Scheduled Mirror Sync

```bash
# Cron job on connected system
0 2 * * * /path/to/enterprise/mirror-channels.py --sync >> /var/log/conda-mirror.log 2>&1
```

### CI/CD Integration

```yaml
# GitLab CI example
build-package:
  stage: build
  script:
    - export CONDA_CHANNEL_URL=file:///opt/mirror/conda-forge
    - ./enterprise/offline-build.sh recipes/$PACKAGE_NAME
  tags:
    - airgapped-runner
```

## Reference Configurations

### Minimal condarc

```yaml
channels:
  - file:///opt/conda-mirror/conda-forge
offline: true
auto_update_conda: false
notify_outdated_conda: false
```

### Full Enterprise condarc

```yaml
channels:
  - https://artifactory.company.com/api/conda/conda-forge-cache
  - file:///opt/conda-mirror/internal-packages

channel_priority: strict
offline: false  # Using Artifactory cache

ssl_verify: /etc/pki/tls/certs/company-ca-bundle.crt

proxy_servers:
  http: http://proxy.company.com:8080
  https: http://proxy.company.com:8080

envs_dirs:
  - /opt/conda/envs
  - ~/.conda/envs

pkgs_dirs:
  - /opt/conda/pkgs
  - ~/.conda/pkgs

auto_update_conda: false
report_errors: false
```
