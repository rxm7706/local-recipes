---
title: "118.2: nebi-pack and the data-science pack reach Healthy on kind and a notebook spawns"
type: 'feature'
created: '2026-10-31'
status: 'backlog'
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
  - _bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md
  - docs/dreams/pyforge-steward.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py
  - recipes/nebari-infrastructure-core/recipe.yaml
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
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_deploy_nic_packs.py -q` — expected: pass (both flag states, the two Applications, the label, the wait).
- `pixi run -e pyforge-steward pyforge steward deploy nic up -f src/platform/deploy/nic/my-nebari-local.yaml` — expected: exit 0 with both packs `Healthy`.
- `python scripts/flag_gate_check.py --spec _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-118-2-nebi-pack-and-the-data-science-pack-reach-healthy-on-kind-and-a-notebook-spawns.md` — expected: exit 0 once `status: 'done'`.

**Run before the push:**
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0.
- `pixi run -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check`, `spec-surface-check` — expected: exit 0 each.

## Auto Run Result

Status: backlog

Summary: not started.

## Spec Change Log

- 2026-10-31: minted from the station Dream's 2026-10-31 section (Nebari hosted: NKP on kind, then Hetzner, with the data-science pack) and the operator's four rulings of the same date.

## Review Triage Log

- (none yet)
