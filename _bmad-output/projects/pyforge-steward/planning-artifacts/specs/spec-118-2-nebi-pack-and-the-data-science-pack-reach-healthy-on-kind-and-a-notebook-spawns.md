---
title: "118.2: nebi-pack and the data-science pack reach Healthy on kind and a notebook spawns"
type: 'feature'
created: '2026-10-31'
status: 'done'
baseline_revision: '9cff05faea33a8ca70a85969607391f3d3f0b434'
review_loop_iteration: 1
followup_review_recommended: false
declared_low_risk: false
deferred:
  - summary: >-
      Attended kind AC2 (hub OAuth, notebook spawn, landing cards, Keycloak bootstrap job) not run in this session.
    evidence: |-
      Same deferral pattern as Story 118.1: the unattended floor is unit tests plus validate; the operator runs
      `deploy nic up` on rootless Docker/kind when ready.
    location: >-
      docs/how-to/host-nebari.md
    severity: medium
  - summary: >-
      Keycloak-on-kind (#613) decision not recorded on spec-pyforge-steward memlog yet.
    evidence: |-
      docs/how-to/host-nebari.md documents the open question; a `(decision)` memlog entry waits on the attended pack run.
    location: >-
      _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md
    severity: medium (unverified)
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
  - _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md
  - docs/dreams/pyforge-steward.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py
  - recipes/nebari-infrastructure-core/recipe.yaml
  - docs/how-to/host-nebari.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-118-1-steward-deploy-nic-brings-up-and-tears-down-an-nkp-cluster-on-local-kind.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/deploy_nic.py
  - src/platform/deploy/nic/my-nebari-local.yaml
---

<intent-contract>

## Intent

**Problem:** An NKP core (118.1) serves a landing page with "No services found". The data-science pack (chart `nebari-data-science-pack` 0.1.7: JupyterHub 5.4.3, jhub-apps, a `nebi` init container) and its prerequisite nebi-pack install as ArgoCD Applications committed to the GitOps source, and upstream's docs show no Application YAML; by hand that is two manifests, a namespace label and a wait, repeated per cluster.

**Approach:** The config gains a `packs:` block (nebi-pack first, in namespace `nebi`; then data-science-pack with `keycloak.hostname: keycloak.nebari.local`, `sharedStorage.nfsServer.enabled: true` on kind, `nebi.remote.enabled: true`). `deploy nic up` renders one ArgoCD `Application` per pack from the chart's OCI reference on `quay.io/nebari/charts`, writes it into the GitOps source (CAP-178: `repository.local` on kind), labels the pack namespaces `nebari.dev/managed=true`, waits for `Healthy`, and journals it. Behind `pyforge.steward.nkp_packs`. The attended run answers the Keycloak-on-kind question (NIC issue #613: the hub's direct OAuth may need the chart's `keycloak.backchannelURL`) on the memlog.

Ledger key: `118-2-nebi-pack-and-the-data-science-pack-reach-healthy-on-kind-and-a-notebook-spawns`.
Type / Effort / Deps: feature / L / S-118.1.

### Living CAP citations

- **`spec-pyforge-steward` CAP-177** — nebi-pack, then the data-science pack, install from the same config as ArgoCD Applications on the cluster CAP-176 brings up; this story is its kind run (Epic 118).
- **`spec-pyforge-steward` CAP-176** (the cluster) and **CAP-178** (the GitOps source the Applications are written to) — extended, not rewritten.
- **`spec-pyforge-warden`** — the digest policy on the charts and images ArgoCD pulls; kept as written.

## Acceptance Criteria

- **AC1 — The Applications.** `deploy nic up` on a config with `packs:` writes `nebi-pack` then `data-science-pack` as ArgoCD Applications into the GitOps source, labels `nebi` and `data-science` with `nebari.dev/managed=true`, and waits until both read `Healthy`; a config without `packs:` changes nothing.
- **AC2 — The hub.** `https://hub.nebari.local` signs in through Keycloak, a `small-instance` server spawns with `/shared` mounted, the landing page shows the JupyterHub and Nebi cards, and the pack's Keycloak bootstrap job completes (`kubectl -n keycloak get jobs -l app.kubernetes.io/instance=data-science-pack`).
- **AC3 — The answer.** The Keycloak-on-kind outcome (direct OAuth works, or needs `keycloak.backchannelURL`, or needs a real cluster) is one memlog `decision` entry on `spec-pyforge-steward` and a line in `docs/how-to/host-nebari.md`.
- **AC4 — Warden.** The pulled chart and image references (with digests) are listed in the journal for Warden's digest policy; nothing is pulled from a registry the config does not name.
- **AC5 — The flag.** `pyforge.steward.nkp_packs` joins `src/platform/config/flags.json` and the three shipped-flag tables; OFF leaves `up` at the NKP core; a test builds both states.

## Boundaries & Constraints

**Always:**
- Install nebi-pack before the data-science pack; keep `nebi.remote.enabled: true` (operator ruling 2 of 2026-10-31).
- Read `docs/how-to/host-nebari.md` § *What the attended run looked like* and Story 118.1's spec § *Attended run 2026-10-31 (AC2)* before touching the cluster: this host runs rootless Docker (the inotify limit is set; the gateway is a MetalLB address reached by `kubectl port-forward`; Keycloak needs `JAVA_OPTS_KC_HEAP`), the pixi env ships NIC 0.14.0 (`nic` has no `init`; `deploy nic down` passes `--auto-approve`), the data-science pack needs a RWX StorageClass (the chart's transitional NFS server on kind) and `keycloak.hostname: keycloak.nebari.local`, and an attended AC (AC2) may be deferred the way 118.1 deferred its cluster AC, with `validate` and the unit suite as the unattended floor.
- Render the Applications from the config; never hand-apply a manifest to the cluster.

**Never:**
- Never add a pack other than nebi-pack and the data-science pack in this story; never pin a chart by `latest`; never hand-edit `SPEC.md`.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-steward` CAP-177.

Parent: `spec-pyforge-steward` CAP-177

- Dream: `docs/dreams/pyforge-steward.md` § *2026-10-31 — Nebari hosted: NKP on kind, then Hetzner, with the data-science pack*.
- Epic: Epic 118, minted with this story.
- Ledger key: `118-2-nebi-pack-and-the-data-science-pack-reach-healthy-on-kind-and-a-notebook-spawns`.
- Deps: S-118.1.
- Surface: `marshal-policy.toml` `[epic_surfaces]."118"`.
- Minted 2026-10-31 in one chain commit with CAP-176..CAP-178, FR-50..FR-52 and Stories 118.1 and 118.3.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: exit 0 (the station suite; the gate's binding, MRS-GATE-010/011).

**Story checks (the session runs these; they are not the gate's binding):**
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_deploy_nic_packs.py -q` — expected: pass (both flag states, the two Applications, the label, the wait).
- `pixi run -e pyforge-steward pyforge steward deploy nic up -f src/platform/deploy/nic/my-nebari-local.yaml` — expected: exit 0 with both packs `Healthy`.
- `python scripts/flag_gate_check.py --spec _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-118-2-nebi-pack-and-the-data-science-pack-reach-healthy-on-kind-and-a-notebook-spawns.md` — expected: exit 0 once `status: 'done'`.

**Run before the push:**
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0.
- `pixi run -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check`, `spec-surface-check` — expected: exit 0 each.

## Auto Run Result

Status: done

Summary: After successful `deploy nic up`, `deploy_nic_packs` writes nebi-pack (0.1.0) and data-science-pack (0.1.7) OCI Applications into NIC GitOps `apps/`, commits them, waits for Argo CD `Healthy`, labels pack namespaces, and journals chart refs/digests behind `pyforge.steward.nkp_packs`.

Files changed:
- `src/shared/packages/pyforge-steward/src/pyforge/steward/deploy_nic_packs.py` — pack Application render, GitOps commit, kubectl wait/label, journal
- `src/shared/packages/pyforge-steward/src/pyforge/steward/deploy_nic.py` — hook pack install after `up`; inherit parent env for pack subprocesses
- `src/shared/packages/pyforge-steward/tests/unit/test_deploy_nic_packs.py` — flag states, ordering, mocked `up` path
- `src/platform/deploy/nic/my-nebari-local.yaml` — `packs:` block with pinned chart versions
- `src/platform/config/flags.json`, `flag-overlays.json`, shipped-flag tests — `pyforge.steward.nkp_packs`
- `docs/how-to/host-nebari.md` — pack switch and chart pins; Keycloak-on-kind still open
- `.gitignore` — `.steward/nkp-pack-deploy.jsonl`

Review: patches applied for pack subprocess env inheritance, Argo CD project `foundational`, sync-wave ordering (10/11), wait-before-label, and `helm pull` digests. AC2 and AC3 memlog decision deferred (attended run).

Verification: `pytest test_deploy_nic_packs.py` and full `pyforge-steward-test` exit 0; `python scripts/spec_surface_reconcile.py` exit 0 after memlog reconcile on spec-pyforge-steward, spec-pyforge-unifying-strategy, spec-pyforge-core, spec-pyforge-doctor.

Residual risks: live `up` needs `kubectl`, `helm`, and kubeconfig on PATH; nebi-pack OCI is 0.1.0 (not 0.1.7) per quay.io publish state.

### Attended run 2026-10-31 (AC2, AC3)

Host: rootless Docker 29.9.1, NIC 0.14.0 (SelfExplainML), kind node `kindest/node:v1.36.1`, kubectl 1.34.3 and helm 4.3.0 from `platform-dev` on `PATH`; cluster brought up by `deploy nic up` on the tracked config, 11:20–12:10 CDT, eleven `up` runs (each config change is one `up`: `nic deploy` reuses the kind cluster in under a second and the pack step re-commits and waits).

- The merged story could not install a pack; each defect surfaced on the real cluster and is Story 118.5: nebi-pack refused to render (`nebariapp.hostname is required when nebariapp.enabled is true`); `kubectl wait` failed at once (`Error from server (NotFound): applications.argoproj.io "nebi-pack" not found` — `nebari-root` polls `file://` every 3 min); Argo CD refused both Applications in project `foundational` (`namespace 'nebi' do not match any of the allowed destinations`, `repo oci://quay.io/nebari/charts/nebari-nebi-pack is not permitted`) — NIC's `nebari-apps` project (`*` destinations, `*` repos) is the one for packs; `up` exited 0 on a transient `Healthy` (106 s, data-science-pack still syncing) and, on a re-run, on the previous sync's `Succeeded` (7 s); the data-science NebariApp was refused by server-side apply (`.spec.landingPage.iconDark: field not declared in schema`, operator 0.1.0-alpha.20 vs chart 0.1.7) and the `null` overrides never reached Helm through `valuesObject` (the apiserver drops null entries) until the values travelled as a `helm.values` string.
- AC1 with the fixes: `up` exit 0 with `nebi-pack` and `data-science-pack` `Healthy` after their sync (62 s, 73 s, 72 s, 74 s on the last four config changes); `apps/nebi-pack.yaml` and `apps/data-science-pack.yaml` committed in `~/.nic/gitops/my-nebari-local` (`steward: add NKP pack Argo CD Applications`, one commit per change); namespaces `nebi` and `data-science` labelled `nebari.dev/managed=true`; `nebi-pack` stays `OutOfSync` while `Healthy` on its postgres StatefulSet (server-side-apply drift).
- AC3 — Keycloak-on-kind: direct OAuth does not work on kind. Pods cannot resolve `*.nebari.local` (NIC 0.14.0 adds no CoreDNS entry): nebi logged `failed to discover OIDC provider: ... lookup keycloak.nebari.local on 10.96.0.10:53: server misbehaving`, and the hub's `/hub/oauth_callback` returned 500 with `tornado.curl_httpclient.CurlError: HTTP 599: Could not resolve host: keycloak.nebari.local` at `get_token_info`. It works with split-horizon OIDC: `keycloak.backchannelURL` and `KC_REALM_API_URL` (hub), `auth.oidc.discoveryURL` (nebi), all `http://keycloak-keycloakx-http.keycloak.svc.cluster.local:8080`; NIC's operator already does the same for gateway-enforced apps (the nebi SecurityPolicy's `issuer`/`tokenEndpoint` are in-cluster, `authorizationEndpoint` public). No real cluster is needed for OAuth; the memlog carries the decision.
- AC2 with the split-horizon values: `https://hub.nebari.local/` → `/hub/oauth_login` → `https://keycloak.nebari.local/realms/nebari/protocol/openid-connect/auth` (`Sign in to Nebari`) → `POST` as `admin` → `/hub/oauth_callback` 302 with `jupyterhub-hub-login` set → `/hub/api/user` 200 `name=admin groups=['/argocd-admins']`; `POST /hub/spawn profile=small-instance` → server ready 20 s later (`/user/admin/`, pod `jupyter-admin` Running, `quay.io/nebari/nebari-data-science-pack-jupyterlab:sha-22afdc1`, limits cpu 1 / memory 2 GiB, the `install-nebi` init container ok); the landing page's `/api/v1/services` (SPA bearer) lists `JupyterHub` (`https://hub.nebari.local`, Data Science, `healthy`) and `Nebi` (`https://nebi.nebari.local`, Platform, `healthy`); `kubectl -n keycloak get jobs -l app.kubernetes.io/instance=data-science-pack` → `data-science-pack-nebari-data-science-pack-rbac-bootstrap Complete 1/1` (it skipped `view-groups`, absent in Keycloak 26.5, and assigned the shared-mount role to `/argocd-admins`, NIC's bootstrap admin group).
- AC2's `/shared` mount is the one part this host cannot prove: the first spawn died in z2jh's `block-cloud-metadata` init container (`iptables v1.8.9 (legacy): can't initialize iptables table 'filter': Table does not exist` — disabled for kind), the role-gated lookup needed `KC_REALM_API_URL` (its admin API URL derives from the public issuer; `backchannelURL` does not cover it), and once the role reached `/argocd-admins` the spawn mounted the share and hung on `MountVolume.SetUp failed ... mount.nfs: Resource temporarily unavailable`: the chart's transitional NFS server dies inside the node's user namespace (`rpc.nfsd: Unable to access /proc/fs/nfsd errno 2`) and the node's kernel NFS client answers `mount.nfs: Operation not permitted` for v4 (uid_map `0 1000 1`). `sharedStorage.enabled: false` on the rootless kind profile; `/shared/<group>` needs rootful Docker (`nfsvers=3` kept) or a cluster with an RWX class (118.3's Hetzner profile, longhorn).
- Argo CD: a sync waiting for the hub Deployment while the hub crash-looped stayed `Running` (no operation timeout) and blocked the next auto-sync; `status.operationState.phase=Terminating` ended it (twice). AC4: `.steward/nkp-pack-deploy.jsonl` carries both chart refs with digests (`sha256:d9320f18…` nebi-pack 0.1.0, `sha256:1bc02ece…` data-science-pack 0.1.7); nothing was pulled from a registry the config does not name.
- `deploy nic kubeconfig` and `outputs` exit 0; `deploy nic down` (`nic destroy --auto-approve`) removed the node at the end of the run. Journal: `.steward/nic-deploy.jsonl`.

## Spec Change Log

- 2026-10-31 (attended): AC2 and AC3 run on this host, recorded under `## Auto Run Result` § *Attended run 2026-10-31 (AC2, AC3)*; DW-steward-118-2 and DW-steward-118-2-2 closed; the defects it found are Story 118.5; `/shared` stays unproven on rootless Docker (see the record).
- 2026-10-31 (later): `context:` gains the how-to, Story 118.1's spec, `deploy_nic.py` and the tracked kind config; one Always bullet points the session at the attended-run record (rootless Docker, NIC 0.14.0, RWX storage, the deferrable attended AC).
- 2026-10-31 (later): `## Verification` → `**Commands:**` bound to the station's policy verify command so the dispatch gate (`check_spec_binding`, MRS-GATE-011) admits it; the story's own checks moved under their own label.
- 2026-10-31: minted from the station Dream's 2026-10-31 section (Nebari hosted: NKP on kind, then Hetzner, with the data-science pack) and the operator's four rulings of the same date.

## Review Triage Log

### 2026-10-31 — Review pass
- verdicts: 8 findings — high 2, medium 3, low 2, false 0, maybe-false 1
- findings:
  - `[high]` `[patch]` Pack subprocesses received empty env — fixed by merging `os.environ` in `_pack_runner`.
  - `[high]` `[patch]` Namespace labels before namespaces existed — fixed by waiting for `Healthy` before `kubectl label`.
  - `[medium]` `[patch]` Warden digest journal empty from `helm show chart` — fixed with `helm pull` digest parse.
  - `[medium]` `[patch]` Parallel sync-wave for both packs — nebi wave 10, data-science wave 11.
  - `[medium]` `[patch]` Argo CD project should be `foundational` on NIC clusters — Application spec updated.
  - `[medium]` `[defer]` Shallow unit assertions on kubectl argv — acceptable for unattended floor; attended run covers integration.
  - `[low]` `[reject]` Duplicate managedNamespaceMetadata vs manual label — manual label satisfies AC1; both kept.
  - `[low]` `[defer]` Partial `packs:` map allowed — operator config is the full kind profile with both packs.
