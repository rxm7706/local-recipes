# JFrog Artifactory Integration

Complete guide for integrating conda-forge with JFrog Artifactory.

## Overview

Artifactory can serve as:
1. **Remote Repository** - Proxy/cache for conda-forge
2. **Local Repository** - Host internal packages
3. **Virtual Repository** - Combine remote + local

## Repository Setup

### Create Remote Repository (Proxy)

```bash
# Via REST API
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

### Create Local Repository (Internal)

```bash
curl -X PUT \
  -H "Authorization: Bearer $ARTIFACTORY_TOKEN" \
  -H "Content-Type: application/json" \
  "https://artifactory.company.com/artifactory/api/repositories/conda-internal" \
  -d '{
    "key": "conda-internal",
    "rclass": "local",
    "packageType": "conda",
    "repoLayoutRef": "simple-default"
  }'
```

### Create Virtual Repository (Combined)

```bash
curl -X PUT \
  -H "Authorization: Bearer $ARTIFACTORY_TOKEN" \
  -H "Content-Type: application/json" \
  "https://artifactory.company.com/artifactory/api/repositories/conda-all" \
  -d '{
    "key": "conda-all",
    "rclass": "virtual",
    "packageType": "conda",
    "repositories": ["conda-internal", "conda-forge-remote"],
    "defaultDeploymentRepo": "conda-internal"
  }'
```

## Client Configuration

### Configure conda

```yaml
# ~/.condarc
channels:
  - https://artifactory.company.com/artifactory/api/conda/conda-all

channel_alias: https://artifactory.company.com/artifactory/api/conda

ssl_verify: /etc/pki/tls/certs/company-ca-bundle.crt

# Optional: credentials
channel_settings:
  - channel: https://artifactory.company.com/artifactory/api/conda/conda-all
    auth: "${ARTIFACTORY_USER}:${ARTIFACTORY_TOKEN}"
```

### Configure pixi

```toml
# pixi.toml
[project]
channels = ["https://artifactory.company.com/artifactory/api/conda/conda-all"]

[system-requirements]
linux = "4.18"
```

### Environment Variables

```bash
# Set credentials
export CONDA_TOKEN="your-api-token"

# Or use netrc
cat >> ~/.netrc << EOF
machine artifactory.company.com
login your-username
password your-api-token
EOF
chmod 600 ~/.netrc
```

## Uploading Packages

### Upload with curl

```bash
# Upload .conda file
curl -H "Authorization: Bearer $ARTIFACTORY_TOKEN" \
  -T my-package-1.0.0-py312h123_0.conda \
  "https://artifactory.company.com/artifactory/conda-internal/linux-64/my-package-1.0.0-py312h123_0.conda"
```

### Upload with anaconda-client

```bash
# Configure
anaconda config --set url https://artifactory.company.com/artifactory/api/conda

# Login
anaconda login --username $ARTIFACTORY_USER --password $ARTIFACTORY_TOKEN

# Upload
anaconda upload -u conda-internal my-package-1.0.0-py312h123_0.conda
```

### Upload Script

```python
#!/usr/bin/env python3
"""Upload conda packages to Artifactory."""
import os
import sys
import requests
from pathlib import Path

ARTIFACTORY_URL = os.environ.get("ARTIFACTORY_URL", "https://artifactory.company.com")
ARTIFACTORY_TOKEN = os.environ["ARTIFACTORY_TOKEN"]
REPO = os.environ.get("ARTIFACTORY_REPO", "conda-internal")

def upload_package(package_path: Path, subdir: str = "linux-64"):
    """Upload a conda package to Artifactory."""
    url = f"{ARTIFACTORY_URL}/artifactory/{REPO}/{subdir}/{package_path.name}"

    headers = {
        "Authorization": f"Bearer {ARTIFACTORY_TOKEN}",
        "Content-Type": "application/octet-stream"
    }

    with open(package_path, "rb") as f:
        response = requests.put(url, headers=headers, data=f)

    response.raise_for_status()
    print(f"Uploaded: {package_path.name} -> {url}")

if __name__ == "__main__":
    for path in sys.argv[1:]:
        upload_package(Path(path))
```

## Reindexing

After uploading packages, reindex the repository:

```bash
# Trigger reindex via API
curl -X POST \
  -H "Authorization: Bearer $ARTIFACTORY_TOKEN" \
  "https://artifactory.company.com/artifactory/api/conda/conda-internal/reindex"
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Build and Publish
on:
  push:
    branches: [main]

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

### GitLab CI

```yaml
stages:
  - build
  - publish

build:
  stage: build
  script:
    - rattler-build build -r recipe.yaml -c ${ARTIFACTORY_CONDA_URL}
  artifacts:
    paths:
      - output/*.conda

publish:
  stage: publish
  script:
    - |
      for pkg in output/*.conda; do
        curl -H "Authorization: Bearer ${ARTIFACTORY_TOKEN}" \
          -T "$pkg" \
          "${ARTIFACTORY_URL}/artifactory/conda-internal/linux-64/$(basename $pkg)"
      done
  only:
    - main
```

### Azure Pipelines

```yaml
trigger:
  - main

pool:
  vmImage: ubuntu-latest

steps:
  - task: UsePythonVersion@0
    inputs:
      versionSpec: '3.12'

  - script: |
      curl -L -O https://github.com/prefix-dev/rattler-build/releases/latest/download/rattler-build-x86_64-unknown-linux-gnu.tar.gz
      tar -xzf rattler-build-*.tar.gz
      ./rattler-build build -r recipe.yaml -c $(ARTIFACTORY_CONDA_URL)
    displayName: Build Package

  - script: |
      for pkg in output/*.conda; do
        curl -H "Authorization: Bearer $(ARTIFACTORY_TOKEN)" \
          -T "$pkg" \
          "$(ARTIFACTORY_URL)/artifactory/conda-internal/linux-64/$(basename $pkg)"
      done
    displayName: Publish to Artifactory
```

## Access Control

### Repository Permissions

```json
{
  "name": "conda-developers",
  "repositories": {
    "include-patterns": ["conda-internal/**"],
    "exclude-patterns": [],
    "actions": ["read", "write", "delete"]
  },
  "principals": {
    "groups": ["developers"]
  }
}
```

### Read-Only Access

```json
{
  "name": "conda-users",
  "repositories": {
    "include-patterns": ["conda-all/**"],
    "actions": ["read"]
  },
  "principals": {
    "groups": ["all-users"]
  }
}
```

## Monitoring

### Check Cache Status

```bash
# Get remote cache statistics
curl -H "Authorization: Bearer $ARTIFACTORY_TOKEN" \
  "https://artifactory.company.com/artifactory/api/storageinfo" | jq '.repositoriesSummaryList[] | select(.repoKey == "conda-forge-remote-cache")'
```

### Package Download Stats

```bash
# Get download statistics
curl -H "Authorization: Bearer $ARTIFACTORY_TOKEN" \
  "https://artifactory.company.com/artifactory/api/storage/conda-forge-remote/linux-64/numpy-1.26.0-py312h123_0.conda?stats"
```

## Troubleshooting

### "Unable to retrieve repodata"

Check Artifactory can reach conda-forge:

```bash
# Test from Artifactory server
curl -I https://conda.anaconda.org/conda-forge/linux-64/repodata.json
```

### "Authentication failed"

Verify token:

```bash
# Test authentication
curl -H "Authorization: Bearer $ARTIFACTORY_TOKEN" \
  "https://artifactory.company.com/artifactory/api/system/ping"
```

### "Package not found in cache"

Force refresh from remote:

```bash
# Clear cache for specific package
curl -X DELETE \
  -H "Authorization: Bearer $ARTIFACTORY_TOKEN" \
  "https://artifactory.company.com/artifactory/conda-forge-remote-cache/linux-64/package-name-*.conda"
```

## Best Practices

1. **Use virtual repositories** - Combine internal + external
2. **Set retention policies** - Clean old cached packages
3. **Monitor storage** - Conda packages are large
4. **Secure tokens** - Use short-lived tokens in CI
5. **Configure SSL** - Use proper certificates
6. **Enable logging** - Track package usage
