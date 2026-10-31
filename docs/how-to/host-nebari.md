# Host Nebari (NKP on kind)

Bring up a local Nebari Kubernetes Platform cluster with the steward `deploy nic` verb (CAP-176, Stories 118.1 and 118.4).

## Prerequisites

- Docker. Rootless Docker works, with two host settings the attended run of 2026-10-31 needed (both `sudo`, both persist under `/etc/sysctl.d/`):
  - `fs.inotify.max_user_instances=1024` — rootless Docker charges every container's inotify instances to your uid; at the default 128 the cloudnative-pg, envoy-gateway and metallb controllers crash-loop with `too many open files`.
  - `net.ipv4.ip_unprivileged_port_start=0` only when the NIC config publishes ports 80/443 on the host. NIC 0.14.0's local provider publishes 6443 alone and hands the gateway a MetalLB address on the kind Docker network (`192.168.1.100`), which rootless Docker does not route to the host — reach it with `kubectl port-forward -n envoy-gateway-system svc/<envoy-gateway-service> 443:443 80:80` and `curl --resolve nebari.local:443:127.0.0.1`, or `/etc/hosts` entries for `nebari.local` and `keycloak.nebari.local` pointing at `127.0.0.1`.
- The `pyforge-steward` pixi environment (`nic` is pinned there; `kubectl` lives in `platform-dev`).
- An age identity (`SOPS_AGE_KEY_FILE` or an issued row in `.steward/keys-inventory.yaml`) when the config declares provider credentials.

## Tracked config

The kind profile lives at `src/platform/deploy/nic/my-nebari-local.yaml` (`repository.local`, domain `nebari.local`). NIC keeps the generated GitOps repository at `~/.nic/gitops/<project_name>` (ArgoCD reads it as `file://`); it survives `down`.

## Secrets

Map each NIC environment variable to an age-encrypted file in an untracked `.env` at the repo root:

```bash
GIT_TOKEN=.steward/nkp-secrets/git-token.age
```

Steward decrypts through `keys` before starting `nic`; nothing sensitive is read from the parent shell environment. A `repository.local` config declares no credential, so `.env` is not read for it.

## Commands

```bash
pixi run -e pyforge-steward pyforge steward deploy nic validate -f src/platform/deploy/nic/my-nebari-local.yaml
pixi run -e pyforge-steward pyforge steward deploy nic up -f src/platform/deploy/nic/my-nebari-local.yaml
pixi run -e pyforge-steward pyforge steward deploy nic kubeconfig -f src/platform/deploy/nic/my-nebari-local.yaml
pixi run -e pyforge-steward pyforge steward deploy nic outputs -f src/platform/deploy/nic/my-nebari-local.yaml
pixi run -e pyforge-steward pyforge steward deploy nic down -f src/platform/deploy/nic/my-nebari-local.yaml
```

`down` runs `nic destroy --auto-approve`: the explicit action behind the kill switch is the consent, and `nic destroy` cannot read its `Type 'yes' to confirm` prompt from a subprocess (Story 118.4). `outputs` redacts the bootstrap admin passwords; `nic outputs --show-secrets` prints them when you need them.

Each run appends `{verb, config, seconds, exit}` to `.steward/nic-deploy.jsonl`.

The kill switch is `pyforge.steward.nkp_deploy` (ON in dev, staging, and production by default).

Pack Applications (`nebi-pack`, then `data-science-pack`) install after a successful `up` when the
config declares `packs:` and `pyforge.steward.nkp_packs` is ON (also ON by default). With the pack
switch OFF, `up` stops at the NKP core. The kind profile pins `nebari-nebi-pack` 0.1.0 and
`nebari-data-science-pack` 0.1.7 on `quay.io/nebari/charts`. Each pack is one Argo CD Application
under NIC's `nebari-apps` project (its `foundational` project admits only NIC's own namespaces and
chart repositories), committed to the GitOps source; `up` refreshes `nebari-root`, waits for the
Applications to exist, then for the sync of the source it rendered to be `Succeeded` and `Healthy`
(Story 118.5). `up` on a running cluster is how a pack value changes: `nic deploy` reuses the kind
cluster, and the pack step commits the new Applications and waits again (62–106 s on 2026-10-31).

Keycloak-on-kind (NIC issue #613), answered on the attended run of 2026-10-31: direct OAuth does not
work on kind because pods cannot resolve `*.nebari.local` (NIC 0.14.0 adds no CoreDNS entry for the
domain); it works with split-horizon OIDC, which the kind profile carries — the data-science pack's
`keycloak.backchannelURL` (the hub's token and userinfo legs) and `KC_REALM_API_URL` (its role-gated
`/shared` lookups), nebi-pack's `auth.oidc.discoveryURL` (its token verifier), all pointing at
`http://keycloak-keycloakx-http.keycloak.svc.cluster.local:8080`. NIC's operator already does the
same for gateway-enforced apps (the landing page, Nebi): their SecurityPolicy's `issuer` and
`tokenEndpoint` are the in-cluster URL while `authorizationEndpoint` stays public. A real cluster
whose CoreDNS resolves the domain can drop the three values.

## What the attended pack run looked like (2026-10-31, chart 0.1.7 / nebi-pack 0.1.0, operator 0.1.0-alpha.20)

- Every pack value the kind profile carries was found on this run, each with its error beside it in the config: nebi-pack refuses to render without `nebariapp.hostname`; chart 0.1.7 renders `landingPage.iconLight`/`iconDark`, which the operator's NebariApp CRD does not declare and server-side apply refuses (`field not declared in schema`), so both are `null` — and a `null` only reaches Helm through `helm.values` (the apiserver drops null entries from `valuesObject`); the z2jh `block-cloud-metadata` init container fails on rootless kind (`iptables ... can't initialize iptables table 'filter'`), so `blockWithIptables: false`; the chart's transitional NFS server cannot start inside the node's user namespace (`rpc.nfsd: Unable to access /proc/fs/nfsd`) and the node's kernel NFS client answers `mount.nfs: Operation not permitted`, so `sharedStorage.enabled: false` on rootless Docker — `/shared/<group>` needs rootful Docker (keep `nfsvers=3` for kind's overlayfs) or a cluster with an RWX StorageClass.
- Proven with those values: `up` exit 0 with both Applications `Healthy`; `https://hub.nebari.local` → Keycloak → `/hub/oauth_callback` 302 → `/hub/api/user` as `admin` (groups `/argocd-admins`); a `small-instance` server ready about 20 s after `POST /hub/spawn` (1 CPU / 2 GiB, the `nebi` init container copied the binary); the landing page's `/api/v1/services` lists JupyterHub and Nebi, both `healthy`; the pack's Keycloak bootstrap job `Complete` (it skips `view-groups`, absent in Keycloak 26.5, and assigned the shared-mount role to `/argocd-admins`, NIC's bootstrap admin group); `nebi` reports `OIDC authentication enabled`.
- Argo CD on this cluster: a pack sync that waits for the hub Deployment while the hub crash-loops stays `Running` (no operation timeout) and blocks the next auto-sync; `kubectl patch application -n argocd data-science-pack --type merge -p '{"status":{"operationState":{"phase":"Terminating"}}}'` ends it. `nebi-pack` stays `OutOfSync` while `Healthy` on its postgres StatefulSet (server-side-apply drift), which is why `up` never waits for `Synced`.
- Wall clock: 11:20–12:10 CDT attended, eleven `up` runs (the first core bring-up 6 min; each later config change 62–106 s); `down` after the run. Journals: `.steward/nic-deploy.jsonl`, `.steward/nkp-pack-deploy.jsonl` (chart digests for Warden).

## What the attended run looked like (2026-10-31, NIC 0.14.0, kind v1.36.1)

- `up`: 354 s to a Ready node with ArgoCD 3.4.4, cert-manager, MetalLB, Envoy Gateway, CloudNativePG, Keycloak 26.5.0, the nebari-operator and the landing page as 14 ArgoCD Applications. Three controllers crash-looped until the inotify limit above was raised; their ArgoCD syncs had failed on the missing webhooks and needed a manual sync (`kubectl patch application -n argocd <app> --type merge -p '{"operation":{"sync":{}}}'`), since auto-sync does not retry a failed revision.
- Keycloak was `OOMKilled` at its 2Gi limit during the Quarkus build phase: inside a rootless kind pod JDK 21 logs `controller memory is not enabled` (the host's `/proc/cgroups` has no `memory` row) and sizes the heap from host RAM. Setting `JAVA_OPTS_KC_HEAP=-Xms256m -Xmx1280m` in `~/.nic/gitops/<project_name>/values/keycloak/base.yaml` (committed there, so ArgoCD applies it) fixed it. Upstream owns the durable fix (an explicit heap in NIC's Keycloak values); filing it is the operator's.
- `gateway-config` and `httproutes` stay `OutOfSync` while `Healthy` after a successful sync (server-side-apply drift on the Gateway and the HTTPRoutes); every Application reports `Healthy`.
- `https://nebari.local` served `Nebari | Launchpad`; the landing page's Keycloak client (`nebari-system-nebari-landing-spa`, realm `nebari`) signed in as `admin` with a PKCE code flow and the token's `preferred_username` was `admin`.
- `down` (after Story 118.4): `nic destroy --auto-approve` removed the kind node in 5 s.
