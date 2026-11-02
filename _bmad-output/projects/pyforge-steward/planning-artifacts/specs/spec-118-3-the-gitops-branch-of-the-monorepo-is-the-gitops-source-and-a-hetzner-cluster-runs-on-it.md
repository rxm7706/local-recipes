---
title: "118.3: The gitops branch of the monorepo is the GitOps source and a Hetzner cluster runs on it"
type: 'feature'
created: '2026-10-31'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag:
  key: pyforge.steward.nkp_gitops_branch
  provider: openfeature-file
  default: {production: on, staging: on, dev: on}
  scope: global
  fallback: "deploy nic validate refuses every repository.existing config; kind's repository.local is unaffected"
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

**Problem:** A cloud cluster needs a GitOps repository that ArgoCD can reach, and `nic deploy` commits generated manifests on every run. The operator ruled on 2026-10-31 that the source is the monorepo on a branch of its own, never `main`: a `nic` commit on `main` would bypass PRs, `detectors-ci` and the commit-msg hook, and no server rule protects such a branch today (`protected-refs.json` covers `attempt-preserve/**`, `loop/**`, `preserve/**`, `archive/**` and three tag families).

**Approach:** `refs/heads/gitops/` joins `docs/governance/guild-roster.json` `protected_refs` as an `operational-branch` (CAP-165), so the session hook denies its deletion and force-push and the live-ruleset proof covers it; `deploy nic validate` refuses a `repository.existing` config whose branch is `main` or outside `gitops/`; the Hetzner config (`cluster.hetzner`: one master and two `cpx31` workers, `longhorn` for `/shared`, Let's Encrypt, `repository.existing` on `rxm7706/local-recipes`, `branch: gitops/<project_name>`, `path: gitops/<project_name>`) runs `up` with `opentofu` resolved through `NIC_TOFU_PATH` and `GIT_TOKEN` (a fine-grained PAT, Contents read and write) through `keys`. Behind `pyforge.steward.nkp_gitops_branch`. The operator-owned inputs — the PAT, `HETZNER_TOKEN`, the domain and DNS, the live ruleset — exist outside git before `up`; without them the story stays `backlog`, and only the operator flips it `blocked`.

Ledger key: `118-3-the-gitops-branch-of-the-monorepo-is-the-gitops-source-and-a-hetzner-cluster-runs-on-it`.
Type / Effort / Deps: feature / L / S-118.1, S-118.2, S-118.8 (amended 2026-11-01 in place: S-118.8 added, EGM audit STW-M-D1, STW-D-R1).

### Living CAP citations

- **`spec-pyforge-steward` CAP-178** — the GitOps source is NIC's local directory on kind, or the monorepo on a branch that only `nic` writes; this story is its cloud half (Epic 118).
- **`spec-pyforge-steward` CAP-176** — the Hetzner provider path of the deploy verb (`opentofu` through `NIC_TOFU_PATH`); extended, not rewritten.
- **`spec-pyforge-steward` CAP-165** (the protected refs declared once, proven live) and **CAP-1** (`keys`) — extended by one roster entry and one credential; kept as written otherwise.

## Acceptance Criteria

- **AC1 — The roster.** `guild-roster.json` `protected_refs` lists `refs/heads/gitops/` with kind `operational-branch`; the hook tests deny `git push origin --delete gitops/x` and `git push --force origin gitops/x`; CAP-165's live-ruleset proof lists `refs/heads/gitops/**` with `deletion` and `non_fast_forward` rules.
- **AC2 — The refusal.** `deploy nic validate` refuses `repository.existing.branch: main` and `feature/x` with the reason named, and accepts `gitops/my-nebari-hetzner`; kind's `repository.local` is unaffected.
- **AC3 — The cluster.** The attended Hetzner `up` reaches every NKP Application and both packs `Healthy`, `https://hub.<domain>` signs in through Keycloak with a Let's Encrypt certificate, `/shared` is `longhorn`-backed, and `down` removes the cluster and its load balancer (the Hetzner console shows no leftover server, volume or load balancer).
- **AC4 — The branch.** After `up`, `gitops/<project_name>` holds the generated Applications under `gitops/<project_name>/`, and `git log origin/main` carries no commit authored by `nic`; the config on `main` is `src/platform/deploy/nic/<project_name>.yaml` alone.
- **AC5 — The flag.** `pyforge.steward.nkp_gitops_branch` joins `src/platform/config/flags.json` and the three shipped-flag tables; OFF refuses every `repository.existing` config; a test builds both states.

## Boundaries & Constraints

**Always:**
- Resolve `opentofu` from conda-forge through `NIC_TOFU_PATH` (the 2026-09-09 air-gap ruling); read every credential through `keys`.
- Name the operator-owned inputs in this spec and the how-to; wait for them.

**Never:**
- Never create a repository, a ruleset, a token or a Hetzner resource from an agent session (outward work); never point `repository.existing` at `main`; never commit a kubeconfig, `.env` or any generated manifest to `main`; never hand-edit `SPEC.md`.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-steward` CAP-178.

Parent: `spec-pyforge-steward` CAP-178

- Dream: `docs/dreams/pyforge-steward.md` § *2026-10-31 — Nebari hosted: NKP on kind, then Hetzner, with the data-science pack*.
- Epic: Epic 118, minted with this story.
- Ledger key: `118-3-the-gitops-branch-of-the-monorepo-is-the-gitops-source-and-a-hetzner-cluster-runs-on-it`.
- Deps: S-118.1, S-118.2, S-118.8 (amended 2026-11-01 in place: Story 118.8 names the gitops writer and amends this spec before dispatch, EGM audit STW-M-D1, STW-D-R1).
- Surface: `marshal-policy.toml` `[epic_surfaces]."118"`.
- Minted 2026-10-31 in one chain commit with CAP-176..CAP-178, FR-50..FR-52 and Stories 118.1 and 118.2.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: exit 0 (the station suite; the gate's binding, MRS-GATE-010/011).

**Story checks (the session runs these; they are not the gate's binding):**
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_deploy_nic_gitops.py src/shared/packages/pyforge-steward/tests/unit/test_protected_refs.py -q` — expected: pass (both flag states, the branch refusal, the roster entry).
- `pixi run -e pyforge-steward pyforge steward deploy nic validate -f src/platform/deploy/nic/<project_name>.yaml` — expected: exit 0 on `gitops/<project_name>`, usage code 2 on `main`.
- `python scripts/flag_gate_check.py --spec _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-118-3-the-gitops-branch-of-the-monorepo-is-the-gitops-source-and-a-hetzner-cluster-runs-on-it.md` — expected: exit 0 once `status: 'done'`.

**Run before the push:**
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0.
- `pixi run -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check`, `spec-surface-check` — expected: exit 0 each.

## Auto Run Result

Status: backlog

Summary: not started.

## Spec Change Log

- 2026-11-01: Deps gains S-118.8 (EGM fleet audit, marshal Story 113.7; operator ruling 2026-11-01). Story 118.8 names the `gitops/<project_name>` writer and amends this spec's AC1, AC2, AC4, Approach, flag fallback and Surface, and adds the no-secret, `GIT_TOKEN` inventory and consent ACs, before this story is dispatched. No AC body changed here; status unchanged. Findings STW-M-D1, STW-D-R1; residue `_bmad-output/projects/pyforge-steward/planning-artifacts/research/egm-audit-2026-11-01.md`.
- 2026-10-31 (later): `## Verification` → `**Commands:**` bound to the station's policy verify command so the dispatch gate (`check_spec_binding`, MRS-GATE-011) admits it; the story's own checks moved under their own label.
- 2026-10-31: minted from the station Dream's 2026-10-31 section (Nebari hosted: NKP on kind, then Hetzner, with the data-science pack) and the operator's four rulings of the same date.

## Review Triage Log

- (none yet)
