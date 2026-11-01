# Glossary — Steward

Companion to `SPEC.md` (added 2026-11-01, EGM fleet audit STW-M-C5). Pointer-only: one line per station term, each
naming where the term is defined. Fleet terms (station, `CAP-n`, `FR-n`, `AD-n` and its prefixes, A and B, Frame, CFE,
twin, the tiers, Path B, Lane 1) are defined in `docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md` § 0.
The station's other companions keep their own terms: `vocabulary-map.md` (the Intelligence Hub's words),
`cluster-bringup-facts.md` (the CRC / OpenShift Local bring-up), `adoption-register.md`, `install-matrix.md` and
`release-cadence.md` (the bmad-suite).

"The Dream's NKP section" below is `docs/dreams/pyforge-steward.md` § *2026-10-31 — Nebari hosted: NKP on kind, then
Hetzner, with the data-science pack*.

## Hosted Nebari (CAP-176..CAP-178)

- **NKP** — the Nebari Kubernetes Platform: the cluster `nic` brings up plus the components its ArgoCD installs; the Dream's NKP section, *The Dream* and *What is real*.
- **NIC, `nic`** — `nebari-dev/nebari-infrastructure-core` (the successor to nebari-classic) and its CLI; the Dream's NKP section, *What is real*; the package is `recipes/nebari-infrastructure-core/` and its channel row is in `docs/governance/pin-policy.yaml`.
- **ArgoCD** — the GitOps controller `nic` installs on the cluster; upstream's component there, not steward's reconciler (`SPEC.md` § Non-goals, the 2026-10-31 clarification).
- **Keycloak** — the identity provider ArgoCD installs (`keycloakx`, realm `nebari`); on kind it is reached by split-horizon OIDC, `docs/how-to/host-nebari.md` § *Commands* (the Keycloak-on-kind paragraph).
- **nebi-pack** — the Helm chart `nebari-nebi-pack` (the nebi server, PostgreSQL, Keycloak SSO), installed first in namespace `nebi`; version and values in `src/platform/deploy/nic/my-nebari-local.yaml`.
- **data-science pack** — the Helm chart `nebari-data-science-pack` (JupyterHub, jhub-apps, the `nebi` init container); the Dream's NKP section, *What is real*; version and values in the same config.
- **`NIC_TOFU_PATH`** — the variable through which `nic` takes conda-forge's `opentofu` for cloud providers (kind needs none); the Dream's NKP section, *Constraints*.
- **`<project_name>`** — the config's `project_name` field, also the config file's stem (`src/platform/deploy/nic/<project_name>.yaml`), NIC's local GitOps directory (`~/.nic/gitops/<project_name>`) and, on cloud, the branch and path `gitops/<project_name>`; the Dream's NKP section, operator ruling 4.
- **attended** — run by the operator on their own host, with the sign-ins and any outward step theirs, of the same class as Story 12.7 on CRC (CAP-65); the Dream's NKP section, operator ruling 1.
- **CAP-176 extends CAP-62 and CAP-65** — CAP-62 (cluster bring-up) and CAP-65 (attended verification) give the attended bring-up pattern CAP-176 follows; `.memlog.md`, the 2026-10-31 bmad-spec update decision.
- **`small-instance`** — the data-science pack's JupyterHub server profile the probes spawn (1 CPU / 2 GiB on the attended run); `docs/how-to/host-nebari.md` § *What the attended pack run looked like*.
- **Keycloak bootstrap job** — the data-science pack's Job in namespace `keycloak` that assigns the pack's Keycloak roles (the shared-mount role to the groups `rbac.bootstrap.sharedMountGroups` names); `docs/how-to/host-nebari.md` § *What the attended pack run looked like*; its check is in Story 118.2's spec, AC2.
- **hub and nebi hosts** — `hub.<domain>` (JupyterHub) and `nebi.<domain>` (nebi-pack's `nebariapp.hostname`), the packs' gateway hostnames; `hub.nebari.local` in `docs/how-to/host-nebari.md` § *What the attended pack run looked like*, `nebi.nebari.local` in `src/platform/deploy/nic/my-nebari-local.yaml` (`nebi-pack` `values.nebariapp.hostname`, under `domain: nebari.local`).
