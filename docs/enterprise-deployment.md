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

---

## 3. PyPI Source URLs in Recipes

Recipes that pull source from PyPI must use a URL pattern that flows through a standard JFrog Artifactory PyPI Remote Repository (or any other `pypi.org` proxy). Only `pypi.org/packages/...` paths are proxied by the typical Remote Repository setup. Hashed `files.pythonhosted.org/packages/<aa>/<bb>/<longhash>/...` URLs bypass that proxy and require the org to configure a *second* Remote Repository pointing at `files.pythonhosted.org` — uncommon and easy to forget.

### Required URL patterns

**Sdists (`*.tar.gz`)**
```yaml
source:
  url: https://pypi.org/packages/source/{{ name[0] }}/{{ name }}/{{ name }}-{{ version }}.tar.gz
```
For projects whose sdist filename uses underscores instead of hyphens (e.g. `litellm_proxy_extras-0.4.69.tar.gz` for project `litellm-proxy-extras`), hard-code the underscore form in the filename:
```yaml
  url: https://pypi.org/packages/source/{{ name[0] }}/{{ name }}/litellm_proxy_extras-{{ version }}.tar.gz
```

**Wheels (`*.whl`)** — use only when upstream publishes no sdist
```yaml
source:
  url: https://pypi.org/packages/{{ py_tag }}/{{ name[0] }}/{{ name }}/{{ name }}-{{ version }}-{{ py_tag }}-none-any.whl
```
where `{{ py_tag }}` is the Python wheel tag (`py3`, `py2.py3`, `cp310`, etc.). The `<py-tag>` segment is **upstream-specific** — when the upstream package changes its supported Python range, the tag in the URL changes and the recipe must be updated. Add a comment to that effect in the recipe.

### Anti-pattern

**Do not use** the hashed `files.pythonhosted.org` URL that PyPI's web UI shows in the "Download files" tab:
```yaml
# WRONG — bypasses Artifactory PyPI proxy
url: https://files.pythonhosted.org/packages/86/8c/3d6c606c.../ayx_plugin_cli-1.1.0-py3-none-any.whl
```

This URL was generated by `grayskull` and many older recipes carry it; rewrite to the `pypi.org` form on touch.

### Why pypi.org over files.pythonhosted.org?

Both serve the same bytes (Warehouse 301-redirects `pypi.org/packages/<py-tag>/...` to `files.pythonhosted.org/packages/<py-tag>/...`), but:

- `pypi.org/packages/...` requests flow through Artifactory's PyPI Remote Repository unchanged — the proxy passes the full path under `<artifactory>/api/pypi/<repo>/...`.
- `files.pythonhosted.org/packages/<hash>/...` requests do **not** map to a `pypi.org` proxy — they require a separate `files.pythonhosted.org` proxy or an HTTP-level transparent proxy.

In an air-gapped network with only the standard `pypi.org` proxy configured, a `files.pythonhosted.org` URL in a recipe causes `rattler-build` (or `conda-build`) to fail at the source-fetch step with a connection error.

### Verification

Before merging a recipe with a PyPI source URL, run:

```bash
curl -sILo /dev/null -w "%{http_code}\n" "<your URL>"
```

A `200` (or `301` if not following redirects) confirms PyPI serves the file. Then verify content integrity:

```bash
curl -sSL "<your URL>" | sha256sum
```

against the `sha256:` field in the recipe. The `conda-forge-expert` skill's recipe-generator emits these patterns automatically; manual edits should follow the same shape.

---

## 4. The `vuln-db` pixi env behind a corporate firewall

The `vuln-db` feature pulls `appthreat-vulnerability-db` from PyPI. On corporate networks where direct access to `files.pythonhosted.org` is blocked, `pixi install -e vuln-db` fails — even though `pypi.org` itself is reachable through JFrog. This is the **same root cause** as the recipe-source issue in §3, hitting at a different layer (the pixi/uv resolver instead of `rattler-build`'s source fetch).

### Why `_http.py` does not help

The skill's runtime HTTP helper (`.claude/skills/conda-forge-expert/scripts/_http.py`) injects truststore + JFrog/GitHub/.netrc auth into every request **made by the conda-forge-expert scripts**. But `pixi install` runs **before** any script is launched — it goes through pixi → uv → `pypi.org/simple` → `files.pythonhosted.org`. None of that flow touches `_http.py`. Routing the resolver requires a separate fix at the pixi/uv layer.

### Why `files.pythonhosted.org` shows up here

Same mechanism as recipe sources (§3): PyPI's Simple index returns wheel/sdist URLs at `files.pythonhosted.org/packages/<a>/<b>/<hash>/...`, and a standard JFrog "PyPI Remote Repository" proxies `pypi.org` but not `files.pythonhosted.org`. The fix is to make uv resolve **against JFrog's PyPI Simple endpoint instead of `pypi.org/simple`** — JFrog's index then rewrites those URLs to flow through itself, and `files.pythonhosted.org` is never contacted.

### Fix: pixi config (recommended, no committed edit)

Pixi 0.67+ supports a `[pypi-config]` table in its config files. Settings here apply to the resolver before any pixi env is created — no changes to the committed `pixi.toml` needed.

A ready-to-edit template lives at **`docs/pixi-config-jfrog.example.toml`**. Copy it into your project-local pixi config:

```bash
cp docs/pixi-config-jfrog.example.toml .pixi/config.toml
$EDITOR .pixi/config.toml      # set your JFrog URL + auth
pixi install -e vuln-db        # should now succeed
```

`.pixi/` is gitignored, so the populated config never lands in version control. Alternative locations:

- `~/.pixi/config.toml` — per-user, applies to every pixi project on this machine.
- `/etc/pixi/config.toml` — system-wide (needs root).

Pixi reads the **first** config it finds in `project → user → system` order; settings do **not** merge across layers, so a project file shadows the user file completely for the keys it sets.

### Verified pixi 0.67.2 config schema

Probed against the running pixi binary; values that are accepted:

| Key | Type | Notes |
|---|---|---|
| `pypi-config.index-url` | URL string | Primary PyPI index. Set to `https://<jfrog-host>/artifactory/api/pypi/<repo>/simple`. |
| `pypi-config.extra-index-urls` | list of URL | Fallback indexes; uv tries each in order. |
| `pypi-config.keyring-provider` | enum | Only `"disabled"` or `"subprocess"` accepted in 0.67.2. |
| `pypi-config.allow-insecure-host` | list of host | Skip TLS verification for specific hosts (foot-gun — prefer `tls-root-certs`). |
| `tls-root-certs` | enum | `"webpki"` (Mozilla bundle), `"native"` (OS trust store), `"all"` (both). Most enterprise users want `"native"` or `"all"` to pick up corporate CA roots. |
| `tls-no-verify` | bool | Global TLS bypass — never set this in prod. |
| `run-post-link-scripts` | enum | Only `"insecure"` is accepted in pixi 0.67.2 (or omit the line). Set to `"insecure"` when packages fail because post-link / activation scripts didn't run — common with Intel MKL, CUDA, and internal tooling wheels. Pixi disables them by default for safety; opting in is reasonable on a curated internal JFrog feed. |
| `proxy-config.{http,https,non-proxy-hosts}` | strings / list | Only if you're behind an HTTP CONNECT forward proxy. |
| `default-channels` | list of URL/spec | Channels pixi resolves against by default. Set to your JFrog Conda Virtual Repository (e.g., `https://<jfrog-host>/artifactory/api/conda/conda-forge-external-virtual`) so the resolver hits the internal mirror first. |
| `repodata-config.disable-sharded` | bool | Set to `true` so pixi requests classic `repodata.json` instead of sharded repodata. Most JFrog Conda Remote Repository deployments don't proxy the sharded protocol correctly (404s during solve). |
| `repodata-config.disable-{zstd,bzip2,jlap}` | bool | Companion toggles for compressed/incremental repodata formats; flip to `true` if your JFrog returns 404s on `.json.zst`, `.json.bz2`, or JLAP requests. |
| `mirrors` | table | Conda channel mirrors: `{ "https://conda.anaconda.org/conda-forge" = ["https://<jfrog>/artifactory/api/conda/conda-forge-external-virtual"] }`. Catches anything that bypasses `default-channels` (e.g., recipe-pinned channel URLs). Separate from PyPI. |
| `authentication-override-file` | path | JSON file mapping hosts to tokens. |

### Env-var alternative (one-shot)

If you can't (or don't want to) drop a config file:

```bash
export UV_INDEX_URL="https://artifactory.example.com/artifactory/api/pypi/pypi/simple"
export UV_NATIVE_TLS=true            # use OS trust store (corporate CA)
export UV_KEYRING_PROVIDER=subprocess # or embed creds in the URL — see below
pixi install -e vuln-db
```

Auth: pick **one**.

- **Keyring (recommended).** `pip install keyring`, then `keyring set artifactory.example.com <username>` and paste your API key as the password. Set `UV_KEYRING_PROVIDER=subprocess`.
- **`~/.netrc`.** Add: `machine artifactory.example.com login alice password <api-key>`. uv reads it automatically.
- **URL-embedded.** `export UV_INDEX_URL="https://USER:TOKEN@artifactory.example.com/.../simple"`. Quick, but the token leaks into shell history and process listings.

### Diagnostic: trace a failing install

```bash
pixi install -e vuln-db -vvv 2>&1 | grep -E "files.pythonhosted|artifactory|TLS|cert|401|403|404"
```

Common signatures:

- **`files.pythonhosted.org` connection timeout/refused** → uv is still hitting public PyPI; your `pypi-config.index-url` (or `UV_INDEX_URL`) didn't take effect. Verify with `pixi config list pypi-config`.
- **TLS / `unable to get local issuer certificate`** → corporate CA root not trusted. Set `tls-root-certs = "native"` in pixi config (or `UV_NATIVE_TLS=true`), or point to your bundle: `REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt`.
- **HTTP 401/403** → JFrog needs auth. Use one of the auth methods above.
- **HTTP 404 on `appthreat-vulnerability-db`** → JFrog's PyPI Remote Repository is configured with a curated allow-list that doesn't include the package. Ask your JFrog admin to verify the upstream URL is `https://pypi.org/simple/` and remove the allow-list (or add the package).

### Org-level alternative (if you have JFrog admin)

Add a **second** Remote Repository targeting `https://files.pythonhosted.org/`. With both `pypi.org` and `files.pythonhosted.org` proxied, every Python tool — pip, uv, poetry, pixi, conda-build sources — works without per-developer config. This is the same fix referenced in §3 for recipe source URLs.

## 5. `detail-cf-atlas` build-matrix fallback (v6.1.0+)

The `detail-cf-atlas` script now has a two-stage chain for the build-matrix section. This matters for air-gapped users because **the two stages hit completely different APIs and your IT may have proxied one but not the other**.

### Stage 1: anaconda.org files API (preferred)

`detail_cf_atlas.py:fetch_anaconda_files` hits `https://api.anaconda.org/package/conda-forge/<name>/files`. Override the base via:

```bash
export ANACONDA_API_BASE=https://artifactory.corp/artifactory/anaconda-org-remote
```

This works only if your JFrog admin has set up a Generic Remote Repository proxying `api.anaconda.org`. Many shops haven't, because anaconda.org's metadata API is rarely on the standard "things to mirror" checklist.

### Stage 2: conda channel `current_repodata.json` (fallback)

When Stage 1 returns any error, `fetch_repodata_build_matrix` walks `_http.resolve_conda_forge_urls()`:

| Priority | Source | Notes |
|---------:|--------|-------|
| 1 | `CONDA_FORGE_BASE_URL` env var | Set this to your JFrog conda-forge mirror |
| 2 | Pixi `mirrors["https://conda.anaconda.org/conda-forge"][*]` | From `.pixi/config.toml` / `~/.pixi/config.toml` / `/etc/pixi/config.toml` |
| 3 | Pixi `default-channels` containing `"conda-forge"` | Same priority order as pixi itself |
| 4 | `https://repo.prefix.dev/conda-forge` | Public CDN mirror |
| 5 | `https://conda.anaconda.org/conda-forge` | Last-resort default |

For each subdir (atlas-derived, or the standard 7), fetches `<base>/<sd>/current_repodata.json` and selects the latest matching package by `timestamp`. JFrog auth (`X-JFrog-Art-Api` for tokens, Basic for username+password) is injected automatically by `_http.make_request`:

```bash
export CONDA_FORGE_BASE_URL=https://artifactory.corp/artifactory/conda-forge-remote
export JFROG_API_KEY=$MY_TOKEN
# OR:
export JFROG_USERNAME=alice
export JFROG_PASSWORD=$MY_PASSWORD
```

The build-matrix header label is dynamic so you can see which source actually produced the data:

```
Build matrix (6 subdirs, latest per subdir from https://repo.prefix.dev/conda-forge)
```

vs. the happy path:

```
Build matrix (7 subdirs, latest per subdir from anaconda.org)
```

### What you lose on the fallback

- **`upload_time`** — `current_repodata.json` carries `timestamp` (build time, in millis), not upload time. The renderer prints the date column as empty when this happens. The data is still there; it's just a slightly different timestamp.
- **Stale-only builds** — `current_repodata.json` is a subset of `repodata.json`: only the latest version per Python tag per subdir. If a package had a build that's been superseded for the same Python version, it won't appear. In practice this is what you want anyway.
- **Deprecated subdirs** — `win-32` (deprecated 2018) is excluded from the standard subdir set. If the atlas record happens to track a historical win-32 build, it won't show on the fallback path. You'll see `linux-64`, `linux-aarch64`, `linux-ppc64le`, `noarch`, `osx-64`, `osx-arm64`, `win-64`.

### Verifying the fallback

```bash
# Force the files API to fail and confirm the channel mirror picks up the slack:
ANACONDA_API_BASE=https://nope.invalid pixi run -e local-recipes detail-cf-atlas django

# Check the source-summary footer — you should see anaconda failing AND
# conda-forge channel (repodata) succeeding, with the resolved base URL.
```

### Verifying with a JFrog mirror

```bash
# Point at your JFrog channel mirror and confirm the build-matrix header
# shows the JFrog URL (not anaconda.org or prefix.dev).
ANACONDA_API_BASE=https://nope.invalid \
CONDA_FORGE_BASE_URL=https://artifactory.corp/artifactory/conda-forge-remote \
JFROG_API_KEY=$MY_TOKEN \
  pixi run -e local-recipes detail-cf-atlas django
```
