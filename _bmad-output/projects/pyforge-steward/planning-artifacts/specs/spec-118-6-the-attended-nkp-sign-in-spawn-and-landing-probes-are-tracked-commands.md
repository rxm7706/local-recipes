---
title: "118.6: The attended NKP sign-in, spawn and landing probes are tracked commands"
type: 'fix'
created: '2026-11-01'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: true
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/research/egm-audit-2026-11-01.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-118-2-nebi-pack-and-the-data-science-pack-reach-healthy-on-kind-and-a-notebook-spawns.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-118-5-deploy-nic-up-installs-the-packs-under-nebari-apps-and-waits-for-the-sync-it-rendered.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
  - docs/how-to/host-nebari.md
  - pixi.toml
---

<intent-contract>

## Intent

**Problem:** CAP-177's success names observables a person checks by hand: `https://hub.<domain>` signs in through Keycloak, a `small-instance` server spawns, and the landing page shows the JupyterHub and Nebi cards. The attended kind runs of 2026-10-31 proved them with `kc_signin.py`, `hub_signin.py` and `landing_cards.py`, and the deferred-work ledger closed DW-steward-118-1, DW-steward-118-2 and DW-steward-118-2-2 on those runs. None of the three scripts is tracked. So the success line cannot be repeated, and Story 118.3 AC3 has to prove sign-in again on Hetzner with nothing to run (EGM audit 2026-11-01, finding STW-D-R4, cluster STW-CL-10; contested, settled for the refute skeptic on the bootstrap job, which already has a tracked `kubectl` check in Story 118.2's spec AC2).

**Approach:** Add `src/shared/packages/pyforge-steward/tests/integration/` with three attended probes and one pixi task to run them. Each probe reads the domain and the bootstrap admin credential from `nic outputs --show-secrets` at run time and stores neither. Each probe skips with the reason named when no kubeconfig is reachable, so the task is safe on any host. `pyforge-steward-test` and `pyforge-steward-live-test` keep collecting only `tests/unit` and `tests/meta`. The how-to names the command, and the three closed DW rows gain a dated note citing it. The Keycloak bootstrap job is out of scope.

Ledger key: `118-6-the-attended-nkp-sign-in-spawn-and-landing-probes-are-tracked-commands`.
Type / Effort / Deps: fix / M / S-118.5.

### Living CAP citations

- **`spec-pyforge-steward` CAP-177** — the sign-in, spawn and landing-card observables of its success line; this story makes them repeatable commands. A fix: no new CAP, no FR, no AD moves (AD-1: the probes call the cluster's endpoints and `nic outputs`, never reimplement them).

## Acceptance Criteria

- **AC1 — The probes.** `src/shared/packages/pyforge-steward/tests/integration/` holds attended probes for: the landing SPA's Keycloak auth-code + PKCE sign-in as the bootstrap admin (Story 118.1 AC2); the hub's OAuth sign-in through Keycloak followed by a `small-instance` spawn that reaches ready; and the landing page's JupyterHub and Nebi cards, both reported healthy.
- **AC2 — No stored secret.** Each probe reads the domain and the admin credential from `nic outputs --show-secrets -f <config>` at run time. No credential is written to disk, to a log, to the journal or to pytest output; a unit-level check over the probe module's output proves the password never appears.
- **AC3 — Safe anywhere.** With no reachable kubeconfig every probe skips with its reason named, and the task exits 0. The config path is a parameter, and the domain comes from the config, so Story 118.3 AC3 reuses the probes on the Hetzner config unchanged.
- **AC4 — One command.** A task under `[feature.pyforge-steward.tasks]` in `pixi.toml` runs `tests/integration` alone; `pyforge-steward-test` and `pyforge-steward-live-test` still collect only `tests/unit` and `tests/meta`.
- **AC5 — The record.** `docs/how-to/host-nebari.md` names the task. DW-steward-118-1, DW-steward-118-2 and DW-steward-118-2-2 in `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md` each gain a dated note citing it; their `RESOLVED` verdicts are not rewritten.
- **AC6 — Green.** `pyforge-steward-test` and `lint-types` exit 0, and the spec-surface stamp is scoped to `pyforge-steward/spec-pyforge-steward` after its memlog reconcile.

## Boundaries & Constraints

**Always:**
- Read every credential at run time from `nic outputs --show-secrets`; skip, never fail, when the cluster is absent.
- Keep the probes out of the default station suite and out of CI; they are attended.

**Never:**
- Never commit a credential, a kubeconfig or a captured token; never add the Keycloak bootstrap-job check here (Story 118.2's spec owns it); never touch `deploy_nic.py` or `deploy_nic_packs.py`.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-steward` CAP-177.

Parent: `spec-pyforge-steward` CAP-177

- Dream: `docs/dreams/pyforge-steward.md` § *2026-10-31 — Nebari hosted: NKP on kind, then Hetzner, with the data-science pack*, and its Realization log's 2026-11-01 (the EGM fleet audit) entry.
- Epic: Epic 118.
- Ledger key: `118-6-the-attended-nkp-sign-in-spawn-and-landing-probes-are-tracked-commands`.
- Deps: S-118.5.
- Surface: `marshal-policy.toml` `[epic_surfaces]."118"`; the story's files are `src/shared/packages/pyforge-steward/tests/integration/` (new), `pixi.toml`, `docs/how-to/host-nebari.md` and `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md`.
- Audit: EGM audit 2026-11-01 finding STW-D-R4 (cluster STW-CL-10); residue `_bmad-output/projects/pyforge-steward/planning-artifacts/research/egm-audit-2026-11-01.md`.
- Minted 2026-11-01 by the EGM fleet audit landing (marshal Story 113.7); lands in that PR.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: exit 0 (the station suite; the gate's binding, MRS-GATE-010/011).

**Story checks (the session runs these; they are not the gate's binding):**
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/integration -q -rs` — expected: exit 0; with no kubeconfig every probe is skipped with its reason.
- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit src/shared/packages/pyforge-steward/tests/meta --collect-only -q` — expected: no path under `src/shared/packages/pyforge-steward/tests/integration` collected.
- `grep -n 'tests/integration' docs/how-to/host-nebari.md` — expected: exit 0.
- `pixi run -e pyforge-guild lint-types` — expected: exit 0.

**Attended (the operator runs this on a live cluster):**
- the new task on `src/platform/deploy/nic/my-nebari-local.yaml` — expected: exit 0 with the three probes passed.

**Run before the push:**
- `pixi run -e pyforge-guild chain-completeness-check`, `story-status-check`, `deferred-work-check`, `spec-surface-check` — expected: exit 0 each.

## Auto Run Result

Status: backlog

Summary: not started.

## Spec Change Log

- 2026-11-01: minted from the EGM fleet audit (marshal Story 113.7), finding STW-D-R4, cluster STW-CL-10; in the audit landing PR.

## Review Triage Log

- (none yet)
