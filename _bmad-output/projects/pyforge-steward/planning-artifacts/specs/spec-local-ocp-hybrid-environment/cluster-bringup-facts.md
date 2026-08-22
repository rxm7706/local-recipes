# Cluster bring-up facts (verified 2026-08-22)

The externally-verified ground truth Story 12.4 documents against. Sources:
crc-org releases/docs, podman-desktop.io docs, crc-extension README, Red Hat
registry docs, live Docker Hub / GitHub API.

## Versions & requirements

- OpenShift Local = **CRC 2.63.0** (2026-08-18) bundling **OpenShift 4.22.7**
  (also OKD 4.22.0-okd-scos.6, MicroShift 4.22.0).
- OpenShift preset: **4 physical cores, 10.5 GB free RAM, 35 GB disk**
  (MicroShift: 2/4/35). OS support: Windows 11, macOS 15+, RHEL/CentOS/
  Fedora latest-two; **Ubuntu/Debian explicitly unsupported**.
- Extension: "Red Hat OpenShift Local" (`crc-org/crc-extension`), via the
  Podman Desktop catalog or OCI `ghcr.io/crc-org/crc-extension`. **On Linux
  the `crc` binary must be installed on PATH manually** (the repo packages
  it: `recipes/openshift-client/`, `recipes/podman-desktop/` exist for the
  clients). Extension drives init/start/stop/delete; `crc` CLI usable
  alongside (`crc setup`, `crc oc-env`).
- Pull secret: prompted at first start; from console.redhat.com/openshift/
  create/local ("Obtain pull-secret" button). Record per keys discipline
  (provenance `observed` — steward can record/retire, not revoke upstream).

## Login

Canonical: `crc console --credentials` prints
`oc login -u kubeadmin -p <password> https://api.crc.testing:6443` (+
developer/developer). The web-console "Copy login command" token flow also
works (session token, not "temporary kubeadmin token").

## Internal-registry image path (operator-locked canonical)

```
oc login …
podman login -u kubeadmin -p $(oc whoami -t) \
  default-route-openshift-image-registry.apps-crc.testing --tls-verify=false
podman tag localhost/<image> \
  default-route-openshift-image-registry.apps-crc.testing/<project>/<image>:<tag>
podman push … --tls-verify=false          # creates the ImageStream
oc new-app --image-stream=<project>/<image>   # or the chart's image.registry seam
```

Known gotcha (not our case on native Linux): pushing from inside a podman
machine VM fails DNS — the default-route resolves to 127.0.0.1 in the
machine (crc#3897). Alternatives documented for completeness: binary build
(`oc new-build --binary --strategy=docker` + `oc start-build --from-dir=.`)
and the extension's "Push image to OpenShift Local cluster" (has recorded
silent-failure UX history, podman-desktop#3538 — not the IaC path).

## Data-service images under restricted-v2 (Story 12.7's contingency)

Docker-library `postgres`/`redis` commonly fail under an SCC-assigned
arbitrary UID (initdb permissions). Fallbacks, in order: the chart's
`postgres.dataMountPath`/UID seams (nulled on OCP by the overlay so the SCC
assigns), `registry.redhat.io/rhel9/postgresql-*`-style images, bitnami.
Record whichever the live run needed as part of the Tier-3 verification.

## dlt / Projects V2 budget facts (Story 12.8)

GraphQL-only objects (`ProjectV2`, `ProjectV2Item`, field types); classic
PAT `read:project` (queries) — **fine-grained PATs cannot reach user-owned
projects** (org-level permission exists; user-level gap per GitHub community
#36441/#156512). Primary rate limit 5,000 points/hr; `first/last` ≤ 100;
`gh project link <n> --owner X --repo Y` links the board
(`linkProjectV2ToRepository` mutation, introspection-verified). dlt side:
scheme `postgresql://` via port-forward; `dataset_name="github_metrics"`
creates the schema — never hand-psql.
