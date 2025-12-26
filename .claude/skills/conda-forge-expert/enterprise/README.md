# Enterprise Module

Tools and guides for using conda-forge in enterprise and air-gapped environments.

## Contents

| File | Description |
|------|-------------|
| `airgapped-setup.md` | Complete guide for air-gapped deployments |
| `artifactory-integration.md` | JFrog Artifactory configuration |
| `mirror-channels.py` | Script to mirror conda channels |
| `offline-build.sh` | Build packages without internet |

## Quick Start

### 1. Configure Enterprise Settings

Copy and customize the enterprise config:

```bash
cp config/enterprise-config.yaml.template config/enterprise-config.yaml
# Edit with your organization's settings
```

### 2. Mirror Required Channels

```bash
python enterprise/mirror-channels.py \
  --source conda-forge \
  --dest https://artifactory.company.com/conda-forge-mirror \
  --packages numpy pandas scikit-learn
```

### 3. Build Offline

```bash
./enterprise/offline-build.sh recipes/my-package
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `CONDA_CHANNEL_URL` | Primary channel URL |
| `CONDA_MIRROR_URL` | Mirror/proxy URL |
| `ARTIFACTORY_URL` | Artifactory base URL |
| `ARTIFACTORY_TOKEN` | API token for uploads |
| `OFFLINE_MODE` | Set to `1` for offline builds |

## Network Requirements

### Fully Air-Gapped

- Pre-download all packages to local mirror
- Use `offline-build.sh` with local channels
- No external network access needed

### Proxy/Firewall

Configure in `~/.condarc`:

```yaml
proxy_servers:
  http: http://proxy.company.com:8080
  https: http://proxy.company.com:8080

ssl_verify: /path/to/company-ca.crt
```

### Artifactory Proxy

Artifactory can proxy conda-forge, caching packages:

```yaml
channels:
  - https://artifactory.company.com/api/conda/conda-forge
```
