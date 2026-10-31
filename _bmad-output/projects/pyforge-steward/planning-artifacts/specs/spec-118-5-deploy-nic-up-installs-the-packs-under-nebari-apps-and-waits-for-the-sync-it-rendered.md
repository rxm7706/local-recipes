---
title: "118.5: deploy nic up installs the packs under nebari-apps and waits for the sync it rendered"
type: 'fix'
created: '2026-10-31'
baseline_revision: '662c03e8ca'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag:
  key: pyforge.steward.nkp_packs
  provider: openfeature-file
  default: {production: on, staging: on, dev: on}
  scope: global
  fallback: "deploy nic up stops at the NKP core: no pack Application is written, labelled or awaited"
  cleanup: "90 days after ON in every environment (Q4); the owning station files the removal story"
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-118-2-nebi-pack-and-the-data-science-pack-reach-healthy-on-kind-and-a-notebook-spawns.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/deploy_nic_packs.py
  - src/platform/deploy/nic/my-nebari-local.yaml
  - docs/how-to/host-nebari.md
---

<intent-contract>

## Intent

**Problem:** Story 118.2's attended run (2026-10-31, this host) found that `deploy nic up` as merged cannot install a pack on an NKP kind cluster: the Applications it renders name Argo CD project `foundational`, which NIC restricts to its own namespaces and chart repositories (`application destination ... namespace 'nebi' do not match any of the allowed destinations in project 'foundational'`; `application repo oci://quay.io/nebari/charts/nebari-nebi-pack is not permitted`); its `kubectl wait` fails at once with `applications.argoproj.io "nebi-pack" not found` because the root Application only polls the `file://` source every three minutes; when the Application does exist, a freshly created one reads `Healthy` before its first comparison and a re-run reads the previous sync's `Succeeded`, so `up` exited 0 twice while data-science-pack was still syncing; and a `null` meant to delete a chart default never reaches Helm through `valuesObject` (the apiserver drops null entries), which left two fields the NIC 0.14.0 operator's NebariApp CRD does not declare (`landingPage.iconLight`/`iconDark`) on the data-science NebariApp (`.spec.landingPage.iconDark: field not declared in schema`). The kind config also lacked the values the packs need on this host: nebi-pack's required `nebariapp.hostname`, split-horizon OIDC (pods cannot resolve `*.nebari.local`), the z2jh `block-cloud-metadata` init container that `iptables` cannot run on rootless kind, and the transitional NFS server that cannot start inside the node's user namespace.

**Approach:** The Applications go through NIC's `nebari-apps` AppProject; after the GitOps commit `up` annotates `nebari-root` for a refresh, polls until each Application exists, then polls `kubectl get application -o json` until the last operation is `Succeeded`, its `syncResult.source` equals the source this run rendered, and health is `Healthy` (`InvalidSpecError`/`ComparisonError` fail at once; `SyncError` is left to Argo CD's retry); values travel as a `helm.values` YAML string. The kind profile gains the values the attended run proved (the hostname, the icon nulls, `keycloak.backchannelURL`, `auth.oidc.discoveryURL`, `KC_REALM_API_URL`, `sharedMountGroups`, `blockWithIptables: false`, `sharedStorage.enabled: false` with the rootless reason). The same PR records the run on Story 118.2's spec, closes DW-steward-118-2 and DW-steward-118-2-2, and writes the Keycloak-on-kind decision (118.2 AC3).

Ledger key: `118-5-deploy-nic-up-installs-the-packs-under-nebari-apps-and-waits-for-the-sync-it-rendered`.
Type / Effort / Deps: fix / M / S-118.2.

### Living CAP citations

- **`spec-pyforge-steward` CAP-177** — "nebi-pack, then the data-science pack, install from the same config as ArgoCD Applications on the cluster CAP-176 brings up"; this story makes the install true on a real cluster. AD-1 (wrap `nic`, `kubectl`, `helm`, never reimplement) and AD-8 (`DutyResult` only) unchanged.
- **`spec-pyforge-steward` CAP-178** — the GitOps source the Applications are written to; the root refresh reads it sooner, nothing else moves.

## Acceptance Criteria

- **AC1 — The project.** `render_application` sets `spec.project: nebari-apps`; `test_render_application_uses_oci_and_namespace` pins it.
- **AC2 — The wait.** After `git_commit_applications`, `apply_nkp_packs` refreshes `nebari-root`, waits for each Application to exist (poll, not `kubectl wait`), then for a `Succeeded` operation whose `syncResult.source` equals the rendered source to read `Healthy`; the transient `Healthy`, the stale `Succeeded`, the `SyncError` and the `InvalidSpecError` cases each have a unit test; no `kubectl wait` is issued.
- **AC3 — The values.** `spec.source.helm.values` is a YAML string; a `None` value renders as `key: null` and reaches Helm (test); `valuesObject` is gone.
- **AC4 — The kind profile.** `src/platform/deploy/nic/my-nebari-local.yaml` carries, with the reason beside each: nebi-pack `nebariapp.hostname: nebi.nebari.local` and `auth.oidc.discoveryURL`; data-science-pack `keycloak.backchannelURL`, `nebariapp.landingPage.iconLight/iconDark: null`, `rbac.bootstrap.sharedMountGroups: ["/argocd-admins"]`, `jupyterhub.hub.extraEnv.KC_REALM_API_URL`, `jupyterhub.singleuser.cloudMetadata.blockWithIptables: false`, `sharedStorage.enabled: false` (rootless Docker) with `nfsServer.mountOptions: ["nfsvers=3"]` kept for rootful hosts.
- **AC5 — The record.** Story 118.2's spec carries the attended run under `## Auto Run Result`; DW-steward-118-2 and DW-steward-118-2-2 are `closed` with command-cited evidence; `docs/how-to/host-nebari.md` § *What the attended pack run looked like* replaces the open question; `spec-pyforge-steward`'s memlog carries the `(decision)` entry for Keycloak-on-kind (118.2 AC3).

## Boundaries & Constraints

**Always:**
- Keep every refusal path of Story 118.2 (unknown pack key, `latest`, missing chart/version/namespace, the kill switch OFF); keep nebi-pack before data-science-pack (sync waves 10/11).
- Render the Applications from the config; the attended run's only hand touches on the cluster were two `status.operationState.phase=Terminating` patches on a sync stuck waiting for the hub Deployment, and a diagnostic NFS mount from the kind node.

**Never:**
- Never read `.status.sync.status == Synced` as the pack being up (nebi-pack's postgres StatefulSet stays `OutOfSync` on server-side-apply drift while `Healthy`); never hand-edit `SPEC.md`; never add a pack beyond the two.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-steward` CAP-177.

Parent: `spec-pyforge-steward` CAP-177

- Dream: `docs/dreams/pyforge-steward.md` § *2026-10-31 — Nebari hosted: NKP on kind, then Hetzner, with the data-science pack*.
- Epic: Epic 118.
- Ledger key: `118-5-deploy-nic-up-installs-the-packs-under-nebari-apps-and-waits-for-the-sync-it-rendered`.
- Deps: S-118.2.
- Surface: `marshal-policy.toml` `[epic_surfaces]."118"`.
- Minted 2026-10-31 from Story 118.2's attended run; hand-landed in the same PR as its record.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: exit 0 (the station suite; the gate's binding, MRS-GATE-010/011).

**Story checks (the session runs these; they are not the gate's binding):**
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_deploy_nic_packs.py -q` — expected: pass (the project, the refresh, the existence poll, the four wait cases, the values string).
- `pixi run -e pyforge-steward pyforge steward deploy nic up -f src/platform/deploy/nic/my-nebari-local.yaml` — expected: exit 0 with both packs `Healthy` after the sync of the rendered source (62–106 s per config change on a running cluster, 2026-10-31).
- `python scripts/flag_gate_check.py --spec _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-118-5-deploy-nic-up-installs-the-packs-under-nebari-apps-and-waits-for-the-sync-it-rendered.md` — expected: exit 0.

**Run before the push:**
- `pixi run -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check`, `spec-surface-check`, `deferred-work-check` — expected: exit 0 each.

## Auto Run Result

Status: done

Summary: pack Applications render under `nebari-apps` with a `helm.values` string; `up` refreshes `nebari-root`, waits for the Applications to exist and for the sync of the rendered source to be `Succeeded` + `Healthy`; the kind profile carries the eight values the attended run proved; Story 118.2's AC2 and AC3 are recorded.

Files changed:
- `src/shared/packages/pyforge-steward/src/pyforge/steward/deploy_nic_packs.py` — `PACK_PROJECT`, `refresh_root_application`, `wait_applications_exist`, the poll-based `wait_applications_healthy` with `_source_fingerprint`, `helm.values`
- `src/shared/packages/pyforge-steward/tests/unit/test_deploy_nic_packs.py` — the project, the refresh, the existence poll, the four wait cases, the values string, the verb order
- `src/platform/deploy/nic/my-nebari-local.yaml` — the kind-profile values, each with its reason
- `docs/how-to/host-nebari.md` — § *What the attended pack run looked like*; the Keycloak-on-kind answer
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-118-2-nebi-pack-and-the-data-science-pack-reach-healthy-on-kind-and-a-notebook-spawns.md` — attended-run result
- `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md` — DW-steward-118-2, DW-steward-118-2-2 closed
- `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md`, `sprint-status-ledger.yaml`, `test-architecture.md` — Story 118.5

Review: hand-landed; the adversarial read is the attended run itself (every defect surfaced on the real cluster, and each fix was re-run through `deploy nic up` before the next). Rejected: none.

Verification:
- `pytest src/shared/packages/pyforge-steward/tests/unit/test_deploy_nic_packs.py src/shared/packages/pyforge-steward/tests/unit/test_deploy_nic.py -q` — 51 passed, 2 skipped (the worktree's `src` on `PYTHONPATH`)
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — see the landing PR's checks
- `deploy nic up` on this host — exit 0 with both packs Healthy on each of the last five config changes (62–106 s each); exit 1 with the Argo CD refusal quoted when the project was wrong

Residual risks: the wait reads `Healthy` the moment the Deployment's status catches up with its new spec, so a hub restart triggered by the same sync can still be rolling for a few seconds after `up` returns (`kubectl rollout status -n data-science deploy/hub` closes that gap); NIC 0.17.0's `nebari-apps` project and operator CRD may differ from 0.14.0's — re-check both when the SelfExplainML build moves.

## Spec Change Log

- 2026-10-31: minted from Story 118.2's attended run (DW-steward-118-2, DW-steward-118-2-2) and hand-landed with its record.
