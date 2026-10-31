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
`nebari-data-science-pack` 0.1.7 on `quay.io/nebari/charts`. Keycloak-on-kind for direct OAuth
(hub and packs) is still an open question (NIC issue #613); record the attended outcome on
`spec-pyforge-steward` and update this section when resolved.

## What the attended run looked like (2026-10-31, NIC 0.14.0, kind v1.36.1)

- `up`: 354 s to a Ready node with ArgoCD 3.4.4, cert-manager, MetalLB, Envoy Gateway, CloudNativePG, Keycloak 26.5.0, the nebari-operator and the landing page as 14 ArgoCD Applications. Three controllers crash-looped until the inotify limit above was raised; their ArgoCD syncs had failed on the missing webhooks and needed a manual sync (`kubectl patch application -n argocd <app> --type merge -p '{"operation":{"sync":{}}}'`), since auto-sync does not retry a failed revision.
- Keycloak was `OOMKilled` at its 2Gi limit during the Quarkus build phase: inside a rootless kind pod JDK 21 logs `controller memory is not enabled` (the host's `/proc/cgroups` has no `memory` row) and sizes the heap from host RAM. Setting `JAVA_OPTS_KC_HEAP=-Xms256m -Xmx1280m` in `~/.nic/gitops/<project_name>/values/keycloak/base.yaml` (committed there, so ArgoCD applies it) fixed it. Upstream owns the durable fix (an explicit heap in NIC's Keycloak values); filing it is the operator's.
- `gateway-config` and `httproutes` stay `OutOfSync` while `Healthy` after a successful sync (server-side-apply drift on the Gateway and the HTTPRoutes); every Application reports `Healthy`.
- `https://nebari.local` served `Nebari | Launchpad`; the landing page's Keycloak client (`nebari-system-nebari-landing-spa`, realm `nebari`) signed in as `admin` with a PKCE code flow and the token's `preferred_username` was `admin`.
- `down` (after Story 118.4): `nic destroy --auto-approve` removed the kind node in 5 s.
