---
title: "118.7: deploy nic finds kubectl and helm in the pyforge-steward environment"
type: 'fix'
created: '2026-11-01'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/research/egm-audit-2026-11-01.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-118-5-deploy-nic-up-installs-the-packs-under-nebari-apps-and-waits-for-the-sync-it-rendered.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/deploy_nic_packs.py
  - docs/how-to/host-nebari.md
  - pixi.toml
---

<intent-contract>

## Intent

**Problem:** `deploy nic up`'s pack step shells `kubectl` and `helm` (`deploy_nic_packs.py`, `_default_runner`, a bare `subprocess.run` that never catches `FileNotFoundError`). pap:AD-16 says those CLIs are pixi-provisioned, but `kubernetes-client` and `kubernetes-helm` sit only in `[feature.platform-dev.dependencies]` of `pixi.toml`, and `docs/how-to/host-nebari.md` tells the operator `kubectl` lives in `platform-dev`. Run from the `pyforge-steward` environment alone, the pack step crashes instead of refusing (EGM audit 2026-11-01, finding STW-M-C6, cluster STW-CL-9; the nic pin, the chart pins, the ledger mode, AD-4 and the self-citation parts of the finding are refuted by recorded decisions).

**Approach:** Add `kubernetes-client >=1.37.1` and `kubernetes-helm >=4.3.0` (the floors `platform-dev` already declares) to `[feature.pyforge-steward.dependencies]`, lock, and regenerate `environment.yaml` through `pixi run -e pyforge-steward pyforge steward estate reconcile`. In `deploy_nic_packs.py`, before the first `kubectl` or `helm` call, check `shutil.which` for both and return a refusing `DutyResult` (AD-8) that names the missing CLI. Update the how-to's prerequisites line. A `pixi.toml` change lands alone through the estate-refresh lane (operator note 2026-11-01), so this story is parked at `backlog`.

Ledger key: `118-7-deploy-nic-finds-kubectl-and-helm-in-the-pyforge-steward-environment`.
Type / Effort / Deps: fix / S / S-118.5.

### Living CAP citations

- **`spec-pyforge-steward` CAP-176** — `nic` and its CLIs come from the pixi environment; this story makes that true for the CLIs the pack step needs.
- **`spec-pyforge-steward` CAP-177** — the pack step that shells `kubectl` and `helm`. A fix: no new CAP, no FR; pap:AD-16 and AD-8 as written.

## Acceptance Criteria

- **AC1 — Provisioned.** `pixi.toml` `[feature.pyforge-steward.dependencies]` lists `kubernetes-client >=1.37.1` and `kubernetes-helm >=4.3.0`; `pixi.lock` and `environment.yaml` are regenerated in the same change; `pixi run -e pyforge-steward kubectl version --client` and `pixi run -e pyforge-steward helm version` exit 0.
- **AC2 — Refused by name.** With `kubectl` or `helm` absent from `PATH`, the pack step returns `DutyResult(ok=False)` whose summary names the missing CLI and runs no subprocess; a unit test in `src/shared/packages/pyforge-steward/tests/unit/test_deploy_nic_packs.py` pins both absences and the present case.
- **AC3 — The how-to.** `docs/how-to/host-nebari.md`'s prerequisites line names the `pyforge-steward` environment for `nic`, `kubectl` and `helm`, and no longer sends the operator to `platform-dev`.
- **AC4 — Green.** `pixi run -e pyforge-guild pyforge-station-tests` (a `pixi.toml` change fires every suite), `pixi run -e pyforge-guild llms-full-check` and `pixi run -e pyforge-guild lint-types` exit 0.
- **AC5 — Reconciled.** Surface-reconcile memlog entries name `pixi.toml` and `pixi.lock` in full on `spec-pyforge-steward` and on the co-governor of `src/` the detector names; each Spec is stamped scoped, one `--spec` each.

## Boundaries & Constraints

**Always:**
- Use the floors `platform-dev` already declares; regenerate `environment.yaml` through `pyforge steward estate reconcile`, never by hand.
- Land alone through the estate-refresh lane.

**Never:**
- Never `pixi add` or `pixi update` live from an agent session; never cap or pin either package without a `docs/governance/pin-policy.yaml` row; never catch `FileNotFoundError` as the fix in place of the `shutil.which` check.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-steward` CAP-176, CAP-177.

Parent: `spec-pyforge-steward` CAP-176

- Dream: `docs/dreams/pyforge-steward.md` § *2026-10-31 — Nebari hosted: NKP on kind, then Hetzner, with the data-science pack*, and its Realization log's 2026-11-01 (the EGM fleet audit) entry.
- Epic: Epic 118.
- Ledger key: `118-7-deploy-nic-finds-kubectl-and-helm-in-the-pyforge-steward-environment`.
- Deps: S-118.5.
- Surface: `marshal-policy.toml` `[epic_surfaces]."118"`; the story's files are `pixi.toml`, `pixi.lock`, `environment.yaml`, `src/shared/packages/pyforge-steward/src/pyforge/steward/deploy_nic_packs.py`, `src/shared/packages/pyforge-steward/src/pyforge/steward/deploy_nic.py` (the refusal before `nic` starts, added 2026-11-01 after review), `src/shared/packages/pyforge-steward/tests/unit/test_deploy_nic_packs.py` and `docs/how-to/host-nebari.md`.
- Audit: EGM audit 2026-11-01 finding STW-M-C6 (cluster STW-CL-9); residue `_bmad-output/projects/pyforge-steward/planning-artifacts/research/egm-audit-2026-11-01.md`.
- Minted 2026-11-01 by the EGM fleet audit landing (marshal Story 113.7); parked at `backlog` because a `pixi.toml` change lands alone through the estate-refresh lane.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: exit 0 (the station suite; the gate's binding, MRS-GATE-010/011).

**Story checks (the session runs these; they are not the gate's binding):**
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_deploy_nic_packs.py -q` — expected: pass, the missing-CLI refusals included.
- `pixi run -e pyforge-steward kubectl version --client` and `pixi run -e pyforge-steward helm version` — expected: exit 0 each.
- `pixi run -e pyforge-guild pyforge-station-tests` — expected: exit 0.
- `pixi run -e pyforge-guild llms-full-check` — expected: exit 0.
- `pixi run -e pyforge-guild lint-types` — expected: exit 0.

**Run before the push:**
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0.
- `pixi run -e pyforge-guild chain-completeness-check`, `story-status-check`, `spec-surface-check` — expected: exit 0 each.

## Auto Run Result

Status: done

Summary (2026-11-01, hand-driven in the five-story EGM landing PR):
- AC1: `pixi.toml` `[feature.pyforge-steward.dependencies]` gains `kubernetes-client >=1.37.1` and `kubernetes-helm >=4.3.0` (the `platform-dev` floors); `pixi lock` exit 0 added kubernetes-client 1.37.2 and kubernetes-helm 4.3.1 to `pyforge-steward`, `pyforge-container` and `pyforge-foundry-full` on every platform (`pyforge-foundry-full-stack` already had both through `platform-dev`), and changed nothing else; `pixi project export conda-environment -e build` is byte-identical to the tracked `environment.yaml` (the `build` environment does not compose the `pyforge-steward` feature), so `environment.yaml` does not move; `pixi run -e pyforge-steward kubectl version --client` and `helm version` exit 0.
- AC2: `deploy_nic_packs.py` gains `missing_pack_clis` / `require_pack_clis` (a `shutil.which` lookup, injectable through `PackDeps.which`); `apply_nkp_packs` refuses with `DutyResult(ok=False)` naming the missing CLI, before it writes an Application or runs a subprocess. `tests/unit/test_deploy_nic_packs.py` pins each absence, both, the present case and the default lookup. After the independent review the refusal also runs in `run_nic` before `nic` starts (`preflight_pack_clis`, only when the pack step would run), carries usage code 2 and the `refused —` form like the verb's other refusals (`test_run_nic_up_refuses_a_missing_pack_cli_before_nic_starts`, `test_run_nic_validate_with_packs_needs_no_pack_cli`); the pack and deploy-nic files give 62 passed, 2 skipped. Mutation: dropping the refusal fails `test_apply_nkp_packs_default_lookup_is_shutil_which` ("no subprocess may run when a pack CLI is missing").
- AC3: `docs/how-to/host-nebari.md`'s prerequisites line names the `pyforge-steward` environment for `nic`, `kubectl` and `helm`.
- AC4/AC5: verified in the landing PR's full preflight and scoped stamps.

## Spec Change Log

- 2026-11-01: lands in one PR with marshal 113.14, mason 25.17/25.18 and steward 118.8 (operator 2026-11-01: the five parked EGM stories as a single PR), not alone through the estate-refresh lane; the `pixi.toml` change is the two pins only. `environment.yaml` is regenerated and unchanged (its `build` environment does not compose `pyforge-steward`). The refusal is injectable through `PackDeps.which`, so the existing pack tests stay hermetic.
- 2026-11-01: minted from the EGM fleet audit (marshal Story 113.7), finding STW-M-C6, cluster STW-CL-9; parked at `backlog` for the estate-refresh lane.

## Review Triage Log

- 2026-11-01 — independent review 1 (separate agent, read-only): AC1–AC3 met; the refusal exited 1 without the verb's `refused —` form and fired only after `nic deploy` had built the cluster → fixed: usage code 2, the `refused —` form, and `preflight_pack_clis` in `run_nic` before `nic` starts (a malformed `packs:` block refuses there too); nits (the `helm pull` comment, the test counts, the lock's environment list) fixed; AC5 (the scoped reconcile) runs last in the landing.
- 2026-11-01 — re-review 2: every fix verified; tests hermetic with and without the CLIs on `PATH`; no new defect.
