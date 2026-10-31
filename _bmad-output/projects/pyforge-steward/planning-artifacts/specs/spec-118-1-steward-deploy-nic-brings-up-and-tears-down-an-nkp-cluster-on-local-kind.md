---
title: "118.1: steward deploy nic brings up and tears down an NKP cluster on local kind"
type: 'feature'
created: '2026-10-31'
baseline_revision: 'b9e221eb909e01b0a7511a27220f5d16992503a8'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
deferred:
  - summary: >-
      Attended kind bring-up through Healthy ArgoCD apps, Keycloak sign-in, and tear-down (AC2) was not executed in this unattended run.
    evidence: |-
      `deploy nic validate` on the tracked config exited 0; full `up`/`down` and kubectl health checks require operator Docker, sysctl/port setup, and secrets in untracked `.env`.
    location: >-
      src/platform/deploy/nic/my-nebari-local.yaml
    severity: high (unverified)
flag:
  key: pyforge.steward.nkp_deploy
  provider: openfeature-file
  default: {production: on, staging: on, dev: on}
  scope: global
  fallback: "deploy nic refuses with usage code 2; no cluster is created, changed or removed"
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

**Problem:** NIC 0.17.0 is packaged (`recipes/nebari-infrastructure-core`, PR #2343) but nothing in the estate runs it: bringing up a Nebari Kubernetes Platform is a hand-run `nic` session with secrets in the shell, no journal and no verb to repeat it. The operator ruled on 2026-10-31 that the first cluster is this host's kind.

**Approach:** The `deploy` duty gains a `nic` sub-verb — `steward deploy nic validate|up|kubeconfig|outputs|down -f <config>` — that wraps `nic validate|deploy|kubeconfig|outputs|destroy` by subprocess (AD-1) over a tracked config `src/platform/deploy/nic/my-nebari-local.yaml` (`provider: local`, `repository: {local: {}}`, `domain: nebari.local`), reads `GIT_TOKEN` and any provider credential through `keys` from an untracked `.env`, journals each run under `.steward/`, returns a `DutyResult` (AD-8) and sits behind `pyforge.steward.nkp_deploy`. `nic` is pinned into the steward pixi feature; the channel (the estate's own recipe published to SelfExplainML, or `prefix.dev/github-releases`) is the Spec's open question and this story records the answer on the memlog. kind needs no OpenTofu. The attended run on this host is the acceptance.

Ledger key: `118-1-steward-deploy-nic-brings-up-and-tears-down-an-nkp-cluster-on-local-kind`.
Type / Effort / Deps: feature / L / none.

### Living CAP citations

- **`spec-pyforge-steward` CAP-176** — an NKP cluster is brought up, torn down and reported from one tracked config through `steward deploy nic`; this story is its kind half (Epic 118). The four operator rulings of 2026-10-31 are on the Dream's 2026-10-31 section and the Spec's `.memlog.md`.
- **`spec-pyforge-steward` CAP-62** and **CAP-65** (the attended CRC bring-up and its Tier-3 verification, Stories 12.4 and 12.7) — the pattern this story repeats on kind.
- **`spec-pyforge-steward` CAP-1** (`keys`), **CAP-3** (`provision`), **CAP-56** (the `nic` recipe) and **CAP-178** (the GitOps source) — kept as written; 118.3 builds on CAP-178.

## Acceptance Criteria

- **AC1 — The verb.** `pixi run -e pyforge-steward pyforge steward deploy nic validate -f src/platform/deploy/nic/my-nebari-local.yaml` exits 0 on the tracked config and refuses (usage code 2, the reason named) a config missing an operator-owned input; `up`, `kubeconfig`, `outputs` and `down` each run exactly one `nic` subprocess and journal `{verb, config, seconds, exit}` under `.steward/`.
- **AC2 — The cluster.** On this host the attended `up` reaches every NKP ArgoCD Application `Healthy` (`kubectl get applications -n argocd`, read through the kubeconfig `kubeconfig` wrote); `outputs` prints `nebari.local` and the Keycloak issuer; `https://nebari.local` signs in as `admin`; `down` removes the cluster. The measured minutes land in § Auto Run Result.
- **AC3 — Secrets.** No credential is read from the environment directly: the verb resolves `GIT_TOKEN` and provider credentials through `keys`; `.env` is untracked and `git status` stays clean after a run.
- **AC4 — Provisioning.** `nic` resolves from the pixi environment (`which nic` inside `pixi run -e pyforge-steward`), never from `PATH` outside it; the channel decision is one memlog `decision` entry on `spec-pyforge-steward`; `environment.yaml` is regenerated in the same PR.
- **AC5 — The flag.** `pyforge.steward.nkp_deploy` joins `src/platform/config/flags.json` and the three shipped-flag tables; OFF makes every `deploy nic` action refuse with usage code 2; a test builds both states.

## Boundaries & Constraints

**Always:**
- Wrap `nic` by subprocess; never reimplement a provider, ArgoCD, Keycloak or the GitOps write.
- Read every verdict from an exit code; journal every run; keep `.env` untracked.
- Apply the unprivileged-port sysctl or the config's port override before `up` on rootless Docker, and say which in the journal.

**Never:**
- Never commit a secret, a kubeconfig or `.env`; never touch `main` or any `gitops/*` branch from this story; never hand-edit `SPEC.md`; never run `nic` against a cloud provider in this story.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-steward` CAP-176.

Parent: `spec-pyforge-steward` CAP-176

- Dream: `docs/dreams/pyforge-steward.md` § *2026-10-31 — Nebari hosted: NKP on kind, then Hetzner, with the data-science pack*.
- Epic: Epic 118, minted with this story.
- Ledger key: `118-1-steward-deploy-nic-brings-up-and-tears-down-an-nkp-cluster-on-local-kind`.
- Deps: none.
- Surface: `marshal-policy.toml` `[epic_surfaces]."118"`.
- Minted 2026-10-31 in one chain commit with CAP-176..CAP-178, FR-50..FR-52 and Stories 118.2 and 118.3.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: exit 0 (the station suite; the gate's binding, MRS-GATE-010/011).

**Story checks (the session runs these; they are not the gate's binding):**
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_deploy_nic.py -q` — expected: pass (both flag states, the refusal, the journal, one subprocess per action).
- `pixi run -e pyforge-steward pyforge steward deploy nic validate -f src/platform/deploy/nic/my-nebari-local.yaml` — expected: exit 0.
- `python scripts/flag_gate_check.py --spec _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-118-1-steward-deploy-nic-brings-up-and-tears-down-an-nkp-cluster-on-local-kind.md` — expected: exit 0 once `status: 'done'`.

**Run before the push:**
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0.
- `pixi run -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check`, `spec-surface-check` — expected: exit 0 each.

## Auto Run Result

Status: done

Summary: Added `steward deploy nic validate|up|kubeconfig|outputs|down` wrapping `nic` by subprocess with keys-backed `.env` secrets, `pyforge.steward.nkp_deploy` kill switch, tracked kind config, SelfExplainML `nic` pin (linux-64), tests, and `docs/how-to/host-nebari.md`.

Files changed:
- `src/shared/packages/pyforge-steward/src/pyforge/steward/deploy_nic.py` — NIC duty adapter, journaling, secrets through keys
- `src/shared/packages/pyforge-steward/src/pyforge/steward/{cli,deploy}.py` — CLI wiring and dispatch
- `src/shared/packages/pyforge-steward/tests/unit/test_deploy_nic.py` — unit coverage (flag, journal, subprocess mapping, refusal)
- `src/platform/deploy/nic/my-nebari-local.yaml` — tracked kind config
- `src/platform/config/{flags.json,flag-overlays.json}` + shipped-flag tests — `pyforge.steward.nkp_deploy`
- `pixi.toml` / `pixi.lock` / `environment.yaml` — `nebari-infrastructure-core` on SelfExplainML (linux-64)
- `docs/how-to/host-nebari.md` — operator runbook
- `.gitignore` — ignore `.steward/nic-deploy.jsonl`

Review: 3 findings — 2 patched (journal must stay gitignored; regenerate `environment.yaml`), 1 deferred (AC2 attended cluster). Rejected: none.

Verification:
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — exit 0 (1697 + 33 tests)
- `pytest src/shared/packages/pyforge-steward/tests/unit/test_deploy_nic.py -q` — 7 passed
- `pyforge steward deploy nic validate -f src/platform/deploy/nic/my-nebari-local.yaml` — exit 0
- `python scripts/spec_surface_reconcile.py` — OK

Residual risk: SelfExplainML still ships `nebari-infrastructure-core` 0.14.0; floor raises when 0.17.0 publishes beside `recipes/nebari-infrastructure-core`.

### Attended run 2026-10-31 (AC2)

Host: rootless Docker 29.9.1, cgroup v2, NIC 0.14.0 (SelfExplainML), kind node `kindest/node:v1.36.1`, kubectl 1.34.3 from `platform-dev`. Config: `src/platform/deploy/nic/my-nebari-local.yaml`, untouched.

- `deploy nic validate` — exit 0 (0.03 s). `deploy nic up` — exit 0 in 354 s to a Ready node; one nic WARN (`Could not retrieve load balancer endpoint` after 5m) because MetalLB was crash-looping.
- Host settings the run needed (both `sudo`, operator-run): `fs.inotify.max_user_instances=1024` — at 128 cloudnative-pg, envoy-gateway and metallb-controller crash-looped with `too many open files` (uid 1000 held all 128); `net.ipv4.ip_unprivileged_port_start=0` turned out unnecessary for 0.14.0 (kind publishes 6443 only; the gateway is a MetalLB address on the kind Docker network, reached from the host through `kubectl port-forward`).
- ArgoCD: the keycloak and metallb-config syncs had failed on the missing webhooks and auto-sync does not retry a failed revision; a manual sync (`operation.sync` patch) after the restarts moved them on. Keycloak 26.5.0 was then `OOMKilled` at 2Gi in its build phase: inside the pod JDK 21 logs `controller memory is not enabled` (host `/proc/cgroups` has no `memory` row) and sizes the heap from host RAM; `JAVA_OPTS_KC_HEAP=-Xms256m -Xmx1280m` committed in `~/.nic/gitops/my-nebari-local/values/keycloak/base.yaml` (ArgoCD's `file://` source) fixed it. Final state: 14/14 Applications `Healthy`, 12 `Synced`; `gateway-config` and `httproutes` `OutOfSync` on server-side-apply drift after a successful sync.
- `deploy nic kubeconfig` — exit 0; `kubectl get applications -n argocd` read through it. `deploy nic outputs` — exit 0: `Domain nebari.local`, `Keycloak issuer URL https://keycloak.nebari.local`, `Gateway address 192.168.1.100`, passwords redacted.
- Sign-in: through `kubectl port-forward` on 127.0.0.1:443, `https://nebari.local` served `Nebari | Launchpad` (HTTP 301 from port 80), and an authorization-code + PKCE flow against realm `nebari` (client `nebari-system-nebari-landing-spa`, the landing page's) signed in as `admin`: 302 back to `https://nebari.local/` with `code`, `KEYCLOAK_IDENTITY` set, token `preferred_username=admin`, realm roles include `admin`.
- `deploy nic down` — exit 1 in 0.03 s: `nic destroy` prompts `Type 'yes' to confirm`; `failed to read user input: EOF`. `nic destroy --auto-approve` removed the node in 5 s. Fix: Story 118.4.
- Wall clock: `up` 06:39–06:45 (CDT); first Healthy Keycloak 07:08; sign-in 07:12; tear-down 07:17 — 38 min attended, of which 30 min were the two host settings and the Keycloak heap. Journal: `.steward/nic-deploy.jsonl` (validate 0.033 s, up 353.6 s, kubeconfig 0.19 s, outputs 0.20 s, down exit 1).

## Spec Change Log

- 2026-10-31 (attended): AC2 run on this host recorded under `## Auto Run Result` § *Attended run 2026-10-31 (AC2)*; DW-steward-118-1 closed; the `down` defect it found is Story 118.4.
- 2026-10-31 (later): `## Verification` → `**Commands:**` bound to the station's policy verify command so the dispatch gate (`check_spec_binding`, MRS-GATE-011) admits it; the story's own checks moved under their own label.
- 2026-10-31: minted from the station Dream's 2026-10-31 section (Nebari hosted: NKP on kind, then Hetzner, with the data-science pack) and the operator's four rulings of the same date.

## Review Triage Log

### 2026-10-31 — Review pass
- verdicts: 3 findings — high 0, medium 1, low 0, false 0, maybe-false 2
- findings:
  - `[medium]` `[patch]` Local `.steward/nic-deploy.jsonl` from validate was tracked — added `.gitignore` entry and removed from git index.
  - `[maybe-false]` `[defer]` AC2 attended kind cluster Healthy/sign-in/tear-down not run in unattended session — deferred with `location: src/platform/deploy/nic/my-nebari-local.yaml`.
  - `[maybe-false]` `[patch]` `environment.yaml` not regenerated after `pixi.toml` change — exported with `pixi workspace export conda-environment -e build environment.yaml`.
