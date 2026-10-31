---
title: "118.1: steward deploy nic brings up and tears down an NKP cluster on local kind"
type: 'feature'
created: '2026-10-31'
baseline_revision: 'b9e221eb909e01b0a7511a27220f5d16992503a8'
status: 'in-progress'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
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

Status: backlog

Summary: not started.

## Spec Change Log

- 2026-10-31 (later): `## Verification` → `**Commands:**` bound to the station's policy verify command so the dispatch gate (`check_spec_binding`, MRS-GATE-011) admits it; the story's own checks moved under their own label.
- 2026-10-31: minted from the station Dream's 2026-10-31 section (Nebari hosted: NKP on kind, then Hetzner, with the data-science pack) and the operator's four rulings of the same date.

## Review Triage Log

- (none yet)
