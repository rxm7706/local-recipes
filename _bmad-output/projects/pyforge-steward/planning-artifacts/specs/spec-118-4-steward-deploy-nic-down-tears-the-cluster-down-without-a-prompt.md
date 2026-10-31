---
title: "118.4: steward deploy nic down tears the cluster down without a prompt"
type: 'fix'
created: '2026-10-31'
baseline_revision: 'a03e997948'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: true
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
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-118-1-steward-deploy-nic-brings-up-and-tears-down-an-nkp-cluster-on-local-kind.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/deploy_nic.py
  - docs/how-to/host-nebari.md
---

<intent-contract>

## Intent

**Problem:** Story 118.1's attended run (2026-10-31, this host) took the kind cluster to every NKP ArgoCD Application `Healthy` and signed in as `admin`, but its last verb failed: `deploy nic down` exited 1 with `failed to read user input: EOF`. `nic destroy` asks `Type 'yes' to confirm` on a terminal, and the adapter runs it by subprocess with no terminal to answer from, so the one tear-down verb the story promised cannot remove a cluster.

**Approach:** `down` passes `--auto-approve` to `nic destroy` and nothing else changes: the kill switch (`pyforge.steward.nkp_deploy`) and the explicit `down` action are the consent, the other four verbs keep their argv, and the argv test pins both facts. The same PR records what the attended run found (the rootless-Docker host settings, the Keycloak heap, the two drifting Applications) in the how-to and closes DW-steward-118-1.

Ledger key: `118-4-steward-deploy-nic-down-tears-the-cluster-down-without-a-prompt`.
Type / Effort / Deps: fix / S / S-118.1.

### Living CAP citations

- **`spec-pyforge-steward` CAP-176** — the tear-down half of "brought up, torn down and reported from one tracked config"; this story makes `down` true. AD-1 (wrap `nic`, never reimplement) and AD-8 (`DutyResult` only) unchanged.

## Acceptance Criteria

- **AC1 — The argv.** `run_nic(action="down")` runs `nic destroy -f <config> --auto-approve`; `validate`, `up`, `kubeconfig` and `outputs` run without it; `test_each_action_runs_one_nic_subprocess_and_journals` pins both.
- **AC2 — The tear-down.** On this host `nic destroy --auto-approve -f src/platform/deploy/nic/my-nebari-local.yaml` removed the kind node (`docker ps -a` lists no `my-nebari-local-*`) in 5 s on 2026-10-31; the steward verb now issues that argv.
- **AC3 — The record.** `docs/how-to/host-nebari.md` names the inotify limit, the port-forward route to the MetalLB address and the Keycloak heap the rootless host needed; DW-steward-118-1 is `closed` with the run's evidence; Story 118.1's spec carries the attended-run result under `## Auto Run Result`.

## Boundaries & Constraints

**Always:**
- Keep `--auto-approve` on `destroy` only; keep every refusal path of Story 118.1 (flag OFF, missing config, missing `nic`, unmapped secret).

**Never:**
- Never add a `--yes`-style flag to the steward grammar for this (the action is already explicit); never feed the prompt through stdin; never touch the GitOps repository from this story.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-steward` CAP-176.

Parent: `spec-pyforge-steward` CAP-176

- Dream: `docs/dreams/pyforge-steward.md` § *2026-10-31 — Nebari hosted: NKP on kind, then Hetzner, with the data-science pack*.
- Epic: Epic 118.
- Ledger key: `118-4-steward-deploy-nic-down-tears-the-cluster-down-without-a-prompt`.
- Deps: S-118.1.
- Surface: `marshal-policy.toml` `[epic_surfaces]."118"`.
- Minted 2026-10-31 from Story 118.1's attended run; hand-landed in the same PR as its record.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: exit 0 (the station suite; the gate's binding, MRS-GATE-010/011).

**Story checks (the session runs these; they are not the gate's binding):**
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_deploy_nic.py -q` — expected: pass (`--auto-approve` on `destroy` alone).
- `python scripts/flag_gate_check.py --spec _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-118-4-steward-deploy-nic-down-tears-the-cluster-down-without-a-prompt.md` — expected: exit 0.

**Run before the push:**
- `pixi run -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check`, `spec-surface-check`, `deferred-work-check` — expected: exit 0 each.

## Auto Run Result

Status: done

Summary: `deploy nic down` now runs `nic destroy --auto-approve`; the argv test pins the flag on `destroy` and its absence elsewhere; the how-to carries the rootless-Docker prerequisites and the attended run's findings; DW-steward-118-1 closed; Story 118.1's spec records the attended run.

Files changed:
- `src/shared/packages/pyforge-steward/src/pyforge/steward/deploy_nic.py` — `_NIC_EXTRA_ARGS`, `--auto-approve` on `destroy`
- `src/shared/packages/pyforge-steward/tests/unit/test_deploy_nic.py` — argv pin per action
- `docs/how-to/host-nebari.md` — prerequisites, `down` consent, the attended run
- `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md` — DW-steward-118-1 closed
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-118-1-steward-deploy-nic-brings-up-and-tears-down-an-nkp-cluster-on-local-kind.md` — attended-run result
- `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md`, `sprint-status-ledger.yaml`, `test-architecture.md` — Story 118.4

Review: hand-landed; the adversarial read is the attended run itself (the defect surfaced on the real `nic destroy`). Rejected: none.

Verification:
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — see the landing PR's checks
- `pytest src/shared/packages/pyforge-steward/tests/unit/test_deploy_nic.py -q` — 18 passed

Residual risk: NIC 0.17.0 (the recipe's version) keeps `--auto-approve` on `destroy` (its `destroy --help` lists it); re-check when the SelfExplainML build moves past 0.14.0.

## Spec Change Log

- 2026-10-31: minted from Story 118.1's attended run (DW-steward-118-1) and hand-landed with its record.
