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
  fallback: "deploy nic refuses every action (validate, up, kubeconfig, outputs, down) on a repository.existing config with usage code 2; kind's repository.local is unaffected"
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

**Approach (amended 2026-11-01 by Story 118.8):** `nic` alone writes `gitops/<project_name>`, under its own deploy key (`GITOPS_DEPLOY_KEY`, an SSH key the config names through `repository.existing.auth.ssh.env`; it replaces the `GIT_TOKEN` PAT, which acted as the operator). `refs/heads/gitops/` joins `docs/governance/guild-roster.json` `protected_refs` as an `operational-branch` (CAP-165), so the session hook denies its deletion; force-push and every other write are refused by the `gitops/**` server ruleset (`creation`, `update`, `deletion`, `non_fast_forward`; the deploy key its only bypass), which the live-ruleset proof covers. `run_nic` refuses, before `nic` starts and for every action (`up` included), a `repository.existing` config whose branch is `main` or outside `gitops/`. A non-local `up` runs only under the operator's `--yes` (the session hook already denies an agent's `deploy nic up --yes`, `session_denials` `steward-deploy-nic-up-yes`, Story 118.8). The pack step, on a `repository.existing` config, applies the pack Application objects to the cluster with `kubectl apply -n argocd` after `nic deploy` and never commits to or pushes any branch: nic 0.17.0's cloud clone is a temporary directory that exists only inside `nic deploy` (the source read and operator ruling of 2026-11-01 on the `spec-pyforge-steward` memlog), so `gitops_root_for` stops aliasing `repository.existing` to the local `~/.nic/gitops/<project_name>` directory. The Hetzner config (`cluster.hetzner`: one master and two `cpx31` workers, `longhorn` for `/shared`, Let's Encrypt, `repository.existing` on `rxm7706/local-recipes`, `branch: gitops/<project_name>`, `path: gitops/<project_name>`) runs `up --yes` with `opentofu` resolved through `NIC_TOFU_PATH` and the deploy key through `keys`. Behind `pyforge.steward.nkp_gitops_branch`. The operator-owned inputs — the deploy key and its `.steward/keys-inventory.yaml` row, `HETZNER_TOKEN`, the domain and DNS, the live `gitops/**` ruleset — exist outside git before `up`; without them the story stays `backlog`, and only the operator flips it `blocked`.

Ledger key: `118-3-the-gitops-branch-of-the-monorepo-is-the-gitops-source-and-a-hetzner-cluster-runs-on-it`.
Type / Effort / Deps: feature / L / S-118.1, S-118.2, S-118.8 (amended 2026-11-01 in place: S-118.8 added, EGM audit STW-M-D1, STW-D-R1).

### Living CAP citations

- **`spec-pyforge-steward` CAP-178** — the GitOps source is NIC's local directory on kind, or the monorepo on a branch only `nic`'s deploy key writes (amended 2026-11-01); this story is its cloud half (Epic 118).
- **`spec-pyforge-steward` CAP-176** — the Hetzner provider path of the deploy verb (`opentofu` through `NIC_TOFU_PATH`); extended, not rewritten.
- **`spec-pyforge-steward` CAP-177** — the data-science pack's `/shared`, spawn and landing-card proof on the cloud cluster (added 2026-11-05, EGM audit STW-D-F6).
- **`spec-pyforge-steward` CAP-165** (the protected refs declared once, proven live) and **CAP-1** (`keys`) — extended by one roster entry and one credential; kept as written otherwise.

## Acceptance Criteria

- **AC1 — The roster and the ruleset (amended 2026-11-01).** `guild-roster.json` `protected_refs` lists `refs/heads/gitops/` with kind `operational-branch`; the hook tests deny `git push origin --delete gitops/x`; the force-push denial's real source is the server ruleset, not the hook (the hook has no force-push matcher for the branch): `docs/governance/rulesets/protected-refs.json` and CAP-165's live-ruleset proof list `refs/heads/gitops/**` with `creation`, `update`, `deletion` and `non_fast_forward` rules whose only bypass actor is the repository's deploy keys, with `GITOPS_DEPLOY_KEY` its only write-enabled deploy key (GitHub's `DeployKey` bypass admits every deploy key of the repository). `scripts/_protected_refs_ruleset_lib.py` hard-codes `bypass_actors: []` and its parity check reds any live bypass actor, so both change to declare and verify a `DeployKey` bypass actor for `gitops/**` only; every other ruleset keeps the empty-bypass rule (amended 2026-11-05, EGM audit STW-M-F2).
- **AC2 — The refusal (amended 2026-11-01).** `run_nic` refuses, for every action (`validate`, `up`, `kubeconfig`, `outputs`, `down`) and before `nic` starts, `repository.existing.branch: main` and `feature/x` with usage code 2 and the reason named, and accepts `gitops/my-nebari-hetzner`; a unit test pins `up` refused on branch `main` with usage code 2 and no subprocess; kind's `repository.local` is unaffected.
- **AC3 — The cluster.** The attended Hetzner `up` reaches every NKP Application and both packs `Healthy`, `https://hub.<domain>` signs in through Keycloak with a Let's Encrypt certificate, `/shared` is `longhorn`-backed, and `down` removes the cluster and its load balancer (the Hetzner console shows no leftover server, volume or load balancer). Before `down`, `pixi run -e pyforge-steward pyforge-steward-nkp-probes` with the Hetzner config through `--nkp-config` exits 0 with no probe skipped (amended 2026-11-05, EGM audit STW-D-F6).
- **AC4 — The branch (amended 2026-11-01).** After `up`, `gitops/<project_name>` holds the generated Applications under `gitops/<project_name>/`, and `git log origin/main..origin/gitops/<project_name> --format='%an <%ae>%x09%cn <%ce>'` lists only `Nebari Infrastructure Core <nic[bot]@users.noreply.github.com>` (the identity nic 0.17.0 commits as; the branch starts from `main`'s tip, so the range excludes `main`'s own authors); the pack Applications reach the cluster through `kubectl apply`, and no commit on that branch is steward's; the config on `main` is `src/platform/deploy/nic/<project_name>.yaml` alone.
- **AC5 — The flag.** `pyforge.steward.nkp_gitops_branch` joins `src/platform/config/flags.json` and the three shipped-flag tables; OFF refuses every action on a `repository.existing` config with usage code 2; a test builds both states.
- **AC6 — No secret in the tracked config or the rendered tree (added 2026-11-01, Story 118.8, STW-M-D5).** A scan runs over `src/platform/deploy/nic/` in the pre-commit configuration and before any commit `deploy nic` makes (kind's local GitOps commit), and after a cloud `up` over `origin/main..origin/gitops/<project_name>` (nic commits the cloud tree inside its own clone, so no pre-commit hook of ours sees it); each refuses a planted secret-shaped value (a test plants one); the verb's `DutyResult` summary names `nic`'s exit code and never echoes `nic`'s output unredacted (a test feeds a secret-shaped last line and asserts it is absent from the summary).
- **AC7 — The deploy key's inventory row (added 2026-11-01, Story 118.8).** `GITOPS_DEPLOY_KEY` gains a `.steward/keys-inventory.yaml` row on CAP-164's pattern, its expiry and scope operator-owned; `keys` refuses to resolve it without the row; no `GIT_TOKEN` remains in the Hetzner config or the how-to.
- **AC8 — The consent gate (added 2026-11-01, Story 118.8, STW-M-D2).** `deploy nic up` on a config whose provider is not local kind refuses with usage code 2 without `--yes` and runs with it; `--yes` is accepted by the parser for `up` only; `tests/scripts/test_pre_shell_hook.py`'s `steward-deploy-nic-up-yes` cases stay green.

## Boundaries & Constraints

**Always:**
- Resolve `opentofu` from conda-forge through `NIC_TOFU_PATH` (the 2026-09-09 air-gap ruling); read every credential through `keys`.
- Name the operator-owned inputs in this spec and the how-to; wait for them.

**Never:**
- Never create a repository, a ruleset, a token, a deploy key or a Hetzner resource from an agent session (outward work); never point `repository.existing` at `main`; never commit a kubeconfig, `.env` or any generated manifest to `main`; never hand-edit `SPEC.md`.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-steward` CAP-178.

Parent: `spec-pyforge-steward` CAP-178

- Dream: `docs/dreams/pyforge-steward.md` § *2026-10-31 — Nebari hosted: NKP on kind, then Hetzner, with the data-science pack*.
- Epic: Epic 118, minted with this story.
- Ledger key: `118-3-the-gitops-branch-of-the-monorepo-is-the-gitops-source-and-a-hetzner-cluster-runs-on-it`.
- Deps: S-118.1, S-118.2, S-118.8 (amended 2026-11-01 in place: Story 118.8 names the gitops writer and amends this spec before dispatch, EGM audit STW-M-D1, STW-D-R1).
- Surface: `marshal-policy.toml` `[epic_surfaces]."118"`; the files include `scripts/_protected_refs_ruleset_lib.py` and its parity check (the `gitops/**` bypass actor), `src/shared/packages/pyforge-steward/src/pyforge/steward/deploy_nic.py` (the branch refusal on every action, the `--yes` gate, the unechoed summary), `src/shared/packages/pyforge-steward/src/pyforge/steward/deploy_nic_packs.py` (`gitops_root_for` stops aliasing `repository.existing` to the local directory; the `kubectl apply` path for cloud), `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` (`--yes` on `up`), `.pre-commit-config.yaml` (the secret scan over `src/platform/deploy/nic/`), `.steward/keys-inventory.yaml` handling (the `GITOPS_DEPLOY_KEY` row is operator-written) and `docs/how-to/host-nebari.md`.
- Minted 2026-10-31 in one chain commit with CAP-176..CAP-178, FR-50..FR-52 and Stories 118.1 and 118.2.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: exit 0 (the station suite; the gate's binding, MRS-GATE-010/011).

**Story checks (the session runs these; they are not the gate's binding):**
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_deploy_nic.py src/shared/packages/pyforge-steward/tests/unit/test_deploy_nic_packs.py src/shared/packages/pyforge-steward/tests/unit/test_protected_refs.py -q` — expected: pass (both flag states, the branch refusal on every action with `up` on `main` refused with usage code 2, the `kubectl apply` cloud pack path with no commit or push, the `--yes` gate, the unechoed summary, the roster entry).
- `pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_pre_shell_hook.py -q` — expected: pass (the `steward-deploy-nic-up-yes` denial and the `gitops/` deletion denial).
- The pre-commit secret scan run over a fixture with a planted secret-shaped value under `src/platform/deploy/nic/` — expected: refused.
- `pixi run -e pyforge-steward pyforge steward deploy nic validate -f src/platform/deploy/nic/<project_name>.yaml` — expected: exit 0 on `gitops/<project_name>`, usage code 2 on `main`.
- `python scripts/flag_gate_check.py --spec _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-118-3-the-gitops-branch-of-the-monorepo-is-the-gitops-source-and-a-hetzner-cluster-runs-on-it.md` — expected: exit 0 once `status: 'done'`.

**Run before the push:**
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0.
- `pixi run -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check`, `spec-surface-check` — expected: exit 0 each.

## Auto Run Result

Status: backlog

Summary: not started.

## Spec Change Log

- 2026-11-01: amended before dispatch by Story 118.8 (STW-M-D1, STW-M-Z2, STW-M-C4, STW-D-R1, STW-D-C5, STW-M-D5, STW-M-D2), after the nic 0.17.0 source read and the operator's rulings of 2026-11-01 and 2026-11-01: the deploy key `GITOPS_DEPLOY_KEY` replaces `GIT_TOKEN`; AC1's force-push denial is the server ruleset's; AC2's refusal runs in `run_nic` for every action; the flag fallback covers every action; AC4 uses the identity probe; the Approach applies cloud pack Applications with `kubectl` instead of writing them into nic's clone (the clone is a temporary directory inside `nic deploy`; this departs from Story 118.8's own AC7 wording, on the operator's 2026-11-01 ruling); the Surface names `gitops_root_for`; AC6–AC8 added (secret scan, inventory row, `--yes`). Status unchanged (`backlog`).
- 2026-11-05: text amended, status unchanged (EGM audit STW-D-F6, STW-M-F2, marshal Story 113.18): AC3 requires the probe task, CAP-177 joins the citations, and AC1 and the Surface name the ruleset lib and its parity check.
- 2026-11-01: Deps gains S-118.8 (EGM fleet audit, marshal Story 113.7; operator ruling 2026-11-01). Story 118.8 names the `gitops/<project_name>` writer and amends this spec's AC1, AC2, AC4, Approach, flag fallback and Surface, and adds the no-secret, `GIT_TOKEN` inventory and consent ACs, before this story is dispatched. No AC body changed here; status unchanged. Findings STW-M-D1, STW-D-R1; residue `_bmad-output/projects/pyforge-steward/planning-artifacts/research/egm-audit-2026-11-01.md`.
- 2026-10-31 (later): `## Verification` → `**Commands:**` bound to the station's policy verify command so the dispatch gate (`check_spec_binding`, MRS-GATE-011) admits it; the story's own checks moved under their own label.
- 2026-10-31: minted from the station Dream's 2026-10-31 section (Nebari hosted: NKP on kind, then Hetzner, with the data-science pack) and the operator's four rulings of the same date.

## Review Triage Log

- (none yet)
