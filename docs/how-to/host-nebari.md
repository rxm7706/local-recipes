# Host Nebari (NKP on kind)

Bring up a local Nebari Kubernetes Platform cluster with the steward `deploy nic` verb (CAP-176, Story 118.1).

## Prerequisites

- Docker (rootless is supported; bind ports below 1024 only after `net.ipv4.ip_unprivileged_port_start=0` or use `cluster.local.http_port` / `https_port` overrides in the NIC config).
- The `pyforge-steward` pixi environment (`nic` is pinned there).
- An age identity (`SOPS_AGE_KEY_FILE` or an issued row in `.steward/keys-inventory.yaml`) when the config declares provider credentials.

## Tracked config

The kind profile lives at `src/platform/deploy/nic/my-nebari-local.yaml` (`repository.local`, domain `nebari.local`).

## Secrets

Map each NIC environment variable to an age-encrypted file in an untracked `.env` at the repo root:

```bash
GIT_TOKEN=.steward/nkp-secrets/git-token.age
```

Steward decrypts through `keys` before starting `nic`; nothing sensitive is read from the parent shell environment.

## Commands

```bash
pixi run -e pyforge-steward pyforge steward deploy nic validate -f src/platform/deploy/nic/my-nebari-local.yaml
pixi run -e pyforge-steward pyforge steward deploy nic up -f src/platform/deploy/nic/my-nebari-local.yaml
pixi run -e pyforge-steward pyforge steward deploy nic kubeconfig -f src/platform/deploy/nic/my-nebari-local.yaml
pixi run -e pyforge-steward pyforge steward deploy nic outputs -f src/platform/deploy/nic/my-nebari-local.yaml
pixi run -e pyforge-steward pyforge steward deploy nic down -f src/platform/deploy/nic/my-nebari-local.yaml
```

Each run appends `{verb, config, seconds, exit}` to `.steward/nic-deploy.jsonl`.

The kill switch is `pyforge.steward.nkp_deploy` (ON in dev, staging, and production by default).
