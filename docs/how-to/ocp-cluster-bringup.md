# OpenShift Local cluster bring-up (Story 12.4 / CAP-1)

Reproducible bring-up for the local OCP hybrid environment. Ground truth:
`cluster-bringup-facts.md` in the steward spec companions folder
(`_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-local-ocp-hybrid-environment/`).

**Baseline:** CRC **2.63.0** bundling OpenShift **4.22.7** (verified 2026-08-22).

**OpenShift preset resources:** 4 physical cores, **10.5 GB** free RAM, **35 GB** disk.

**Supported host OS (CRC upstream):** Windows 11, macOS 15+, RHEL/CentOS/Fedora
(latest two). **Ubuntu and Debian are explicitly unsupported** by CRC — use a
supported host or a VM that matches the list.

Every command below is copy-pasteable. Do not improvise steps outside this doc
and the linked deploy READMEs.

---

## 1. Choose a bring-up path

| Path | When to use |
|------|-------------|
| **A — Podman Desktop extension** | You want the GUI lifecycle (init/start/stop/delete) and already run Podman Desktop. |
| **B — Linux `crc` on PATH** | Headless/automation-friendly Linux; extension optional. |

On **Linux**, path A still requires the **`crc` binary on PATH** before the
extension can drive the cluster — the extension does not bundle `crc`. Install
from the [CRC release](https://github.com/crc-org/crc/releases/tag/v2.63.0) or
use this repo's client recipes (`recipes/openshift-client/`,
`recipes/podman-desktop/`) as packaging references.

---

## 2. Path A — Podman Desktop + OpenShift Local extension

1. Install **Podman Desktop** (see `recipes/podman-desktop/` in this repo for
   the conda-forge packaging story).
2. On Linux, install **`crc` 2.63.0** and ensure `crc version` reports
   **2.63.0** / OpenShift **4.22.7**.
3. In Podman Desktop, open **Extensions** → install **Red Hat OpenShift Local**
   (`crc-org/crc-extension`) from the catalog, or from OCI
   `ghcr.io/crc-org/crc-extension`.
4. Start the cluster from the extension UI. On **first start**, paste the
   **pull secret** when prompted (see §4).
5. Wait until the cluster status is **Running**.

The extension wraps the same `crc` lifecycle as path B; the CLI remains usable
alongside (`crc setup`, `crc start`, `crc stop`, `crc delete`).

---

## 3. Path B — Linux with `crc` on PATH

From a shell on a supported Linux host with the resource headroom above:

```sh
crc version          # expect 2.63.0 / OpenShift 4.22.7
crc setup            # once per machine
crc start -p ~/.config/openshift/pull-secret.json   # see §4 for the secret file
eval $(crc oc-env)   # every new shell that needs oc
crc status           # expect Running
```

If `crc start` prompts interactively for the pull secret instead of `-p`, paste
the same JSON file path or contents when asked.

**Login helpers:**

```sh
crc console --credentials
# prints: oc login -u kubeadmin -p <password> https://api.crc.testing:6443
# also documents developer/developer for the developer account
```

Alternatively, use the web console **Copy login command** flow (session token).

---

## 4. Pull secret (required once per cluster)

1. Download from [Red Hat OpenShift Local](https://console.redhat.com/openshift/create/local)
   → **Obtain pull-secret** (Red Hat account required).
2. Save to a **local, untracked path**, e.g.
   `~/.config/openshift/pull-secret.json`. **Never commit this file.**
3. Record metadata in `.steward/keys-inventory.yaml` per §5 (`crc-pull-secret`).

Steward records **provenance only** — it cannot revoke upstream pull secrets.

---

## 5. Keys discipline (inventory, never secrets in git)

Credential **values** live outside git (env vars, `~/.config/…`, password
manager). The repo tracks **metadata** in `.steward/keys-inventory.yaml`
(FR-5): name, scope, provenance, status, `last_rotated` — never the secret
itself.

After bring-up, confirm these three **first inventory rows** exist (hand-seeded
by this story; update `last_rotated` when you rotate):

| Inventory `name` | What the operator holds locally | Notes |
|------------------|----------------------------------|-------|
| `crc-pull-secret` | `~/.config/openshift/pull-secret.json` (or your path) | `provenance: observed` |
| `crc-kubeadmin` | Password from `crc console --credentials` | Rotate via CRC; Steward records only |
| `github-pat-read-project` | Classic PAT with `read:project` | For Story 12.8 dlt ingest; fine-grained PATs cannot reach user-owned projects |

Verify without exposing values:

```sh
pixi run -e local-recipes steward keys list
```

Optional JSON for automation:

```sh
pixi run -e local-recipes steward keys list --json
```

When a credential rotates, update `last_rotated` in the inventory (ISO-8601) and
replace the local secret file or env var — do not add secret values to the YAML.

---

## 6. Authenticate `oc`

After the cluster is Running:

```sh
eval $(crc oc-env)    # if not already done
oc login -u kubeadmin -p '<password-from-crc-console-credentials>' \
  https://api.crc.testing:6443
oc whoami             # kubeadmin
oc project default    # or create/switch to your deploy namespace
```

---

## 7. Build the platform image (host)

From the **repository root** (build context must include `pixi.toml` /
`pixi.lock` — see `src/platform/Containerfile` header):

```sh
podman build -f src/platform/Containerfile -t platform:local .
# docker build -f src/platform/Containerfile -t platform:local .   # equivalent
```

This is the same image Story 10.3 / Platform CI build; no separate OCP image.

---

## 8. Push via the internal registry (canonical image path)

CRC's CRI-O cannot see the host's local container storage directly — the
**internal OpenShift registry** is the supported path (`cluster-bringup-facts.md`).

Replace `<project>` with your target namespace (e.g. `default` or a dedicated
`platform` project):

```sh
oc login -u kubeadmin -p '<password>' https://api.crc.testing:6443

podman login -u kubeadmin -p "$(oc whoami -t)" \
  default-route-openshift-image-registry.apps-crc.testing --tls-verify=false

podman tag localhost/platform:local \
  default-route-openshift-image-registry.apps-crc.testing/<project>/platform:local

podman push \
  default-route-openshift-image-registry.apps-crc.testing/<project>/platform:local \
  --tls-verify=false
```

This creates an **ImageStream** `<project>/platform:local` the chart can pull.

**Helm image seams** (core chart `values.yaml`):

```sh
pixi run -e platform-dev helm install platform src/platform/deploy/charts/platform \
  -f src/platform/deploy/overlays/ocp/core-overrides.yaml \
  --set image.registry=default-route-openshift-image-registry.apps-crc.testing \
  --set image.repository=<project>/platform \
  --set image.tag=local
```

Then install the Route overlay per `README.md` in this directory.

**Known gotcha (not native Linux):** pushing from inside a Podman *machine* VM
can fail DNS for the registry route (`crc#3897`). On native Linux, use the
commands above from the host shell. Alternatives (binary build, extension
"Push image…") are documented in `cluster-bringup-facts.md` for completeness but
are **not** the IaC path for this fleet.

---

## 9. Deploy the chart (after registry push)

Full Secret contract, two-release OCP shape, and limitations:
`docs/explanation/platform-deployment-architecture.md` and `overlays/ocp/README.md`.

Minimal sequence (namespace + Secret + both releases):

```sh
kubectl create namespace platform --dry-run=client -o yaml | kubectl apply -f -
oc project platform

kubectl create secret generic platform-secrets \
  --from-literal=DJANGO_SECRET_KEY='…' \
  --from-literal=DATABASE_URL='postgres://platform_app:…@platform-postgres:5432/platform' \
  --from-literal=MIGRATION_DATABASE_URL='postgres://platform:…@platform-postgres:5432/platform' \
  --from-literal=POSTGRES_PASSWORD='…'

pixi run -e platform-dev helm install platform src/platform/deploy/charts/platform \
  -f src/platform/deploy/overlays/ocp/core-overrides.yaml \
  --namespace platform \
  --set image.registry=default-route-openshift-image-registry.apps-crc.testing \
  --set image.repository=platform/platform \
  --set image.tag=local

pixi run -e platform-dev helm install platform-ocp src/platform/deploy/overlays/ocp/chart \
  --namespace platform \
  --set route.service.name=platform
```

Compose `DATABASE_URL` from `helm install` NOTES output — the chart never
renders passwords into manifests (AD-12).

---

## 10. Verification checklist

Run in order after deploy:

```sh
crc status | grep -i running
oc whoami
oc get imagestream -n platform platform   # or your project/image name
oc get pods -n platform
oc get deploy -n platform -l app.kubernetes.io/component=mcp-host
oc get route -n platform
```

**Success signal (CAP-1):** cluster Running, `oc` authenticated, platform
ImageStream present, web pods pull the internal-registry image without
`ImagePullBackOff`.

**mcp-host (spec-mcp-era-isolation CAP-4):** a `mcp-host` Deployment and
ClusterIP must be Ready. Web/worker must have `MCP_HOST_SIDECAR_BASE_URL`
pointing at that Service. Helm refuses an empty `mcpHost.image.repository`.
Sidecar not Ready is HTTP 502 on `/stations/<name>/mcp`, not a web CrashLoop.

Attended proof of Route admission, SCC enforcement, PVC binding, and
postgres/redis under arbitrary UID is **Story 12.7** — not claimed here.

---

## 11. What this doc deliberately excludes

- DB-GPT sidecar chart work → Story 12.5
- mcp-host is **required** on this overlay (Epic 35 / CAP-4), not optional
  chart work — do not omit the Deployment or blank the image repository
- Redis AUTH + NetworkPolicy → Story 12.6; broker AOF PVC + bounded
  maxmemory → Story 40.2 (`redis.broker.persistence`, `/data` mount)
- Live Tier-3 verification record → Story 12.7
- GKE/kind CI profiles → Stories 12.2 / 12.3 (unchanged)
- `--docker-image` / host-socket deploy shortcuts → struck in
  `reconciliation-and-corrections.md`

---

## 12. GitHub Projects V2 → `github_metrics` (Story 12.8)

After the platform Postgres pod is reachable (port-forward or in-cluster), load
board data with the dlt pipeline documented in
[`src/platform/ingest/github_projects/README.md`](../../../ingest/github_projects/README.md).

Quick path:

1. Create/link the board: `gh project create` + `gh project link … --repo rxm7706/local-recipes`
2. Export a **classic** PAT with `read:project` as `GITHUB_TOKEN`
3. Port-forward Postgres: `oc port-forward -n platform svc/platform-postgresql 5432:5432`
4. Set `GITHUB_METRICS_DATABASE_URL=postgresql://…`
5. Run: `pixi run -e python-agent-platform github-metrics-dlt -- PVT_yourProjectId`

Dry-run first: add `--dry-run --max-pages 1` (no Postgres required).
