---
title: "16.6: Fleet approve re-solves and delivers the fix it queued"
type: 'fix'
created: '2026-11-01'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/.memlog.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-16-3-each-fleet-fix-waits-in-a-proposal-queue-for-operator-approval.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-14-3-the-actuator-opens-the-fix-as-a-draft-pr-on-an-estate-repo.md
  - src/shared/packages/django-warden/src/django_warden_fabric/tasks.py
  - src/shared/packages/django-warden/src/django_warden_fabric/proposals.py
  - src/platform/tests/test_warden_fleet_proposals.py
deferred: []
---

<intent-contract>

## Intent

**Problem:** the one Blocker that survived the EGM audit's triage (WAR-D-C1). Story 16.3's approve path never delivers
the fix it queued (line numbers at `03a7aff5d9`):
- `_run_fix_actuator` (`src/shared/packages/django-warden/src/django_warden_fabric/tasks.py` about :350-366) calls `run_actuator` without `fixed_version_candidates` or
  `manifest_locations`. With `pyforge.warden.fix_target_resolution` on, every `vuln:` proposal fails on "no fixed-version
  candidates"; with it off, the draft PR carries an empty tree.
- Queue time runs the actuator in dry-run, which prepares no edit (Stories 14.1 and 14.2 forbid the solver under
  dry-run), so `planned_paths_json` is always empty and the approve has no inputs (WAR-D-R3).
- `FixProposal.target` stores the outcome's `subject`, the package name, not the resolved version (`src/shared/packages/django-warden/src/django_warden_fabric/proposals.py`
  about :64-74).
- `src/platform/tests/test_warden_fleet_proposals.py` patches `_run_fix_actuator` (about :236-241), so no test runs the
  real actuator on the approve path.

EGM audit 2026-11-01, cluster WAR-CL-1; findings WAR-D-C1 and WAR-D-R3, accepted by the operator on 2026-11-01;
residue `_bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md`.

**Approach:**
- Factor the `manifest_locations` builder out of `src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py` (about :1296-1307) into a public `pyforge.warden` helper
  that takes an inventory and returns the canonical-subject-keyed locations; `cli.py` calls it, unchanged in behaviour.
- At queue time, `proposals.py` stores the dry-run `fix_resolution` target in `FixProposal.target` and keeps the
  candidates in the scan's stored `report_json`; it never stores a diff.
- At approve time, `_run_fix_actuator` builds `manifest_locations` on the fresh clone through the helper and passes
  `fixed_version_candidates` from the stored `report_json` actuation `fix_resolution`; the actuator re-resolves on the
  clone (approve-time re-resolution, WAR-M-C3's sub-point).
- An approve that would yield no `manifest_fix` records a `failed` actuation on the proposal and opens no PR.
- The platform test drives the real `run_actuator` with a fake forge client passed through its `client` parameter and a
  stubbed solver seam, and asserts the commit and the refuse path.
- A memlog decision on `spec-pyforge-warden` records the handoff (the queue records the dry-run target and candidates,
  never a diff; the approve re-solves on the fresh clone), which supersedes Story 16.3's "planned diff summary"
  through this story. Story 16.3 is done and is not edited.

Ledger key: `16-6-fleet-approve-re-solves-and-delivers-the-fix-it-queued`.
Type / Effort / Deps: fix / M / S-14.4 (the approve re-solve runs the default solver that Story 14.4 fixes).

### Living CAP citations

- `spec-pyforge-warden` CAP-26 (FR-43) — the fleet's approve-then-open path; CAP-24 (FR-41) — the actuator path it
  opens through. A `fix`, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag
  (`pyforge.warden.fleet_fix_proposals` keeps gating the queue and the approve).

## Acceptance Criteria

- **AC1 — The queue stores the target.** Given a fleet run whose dry-run actuation planned a `vuln:` fix with
  `fix_resolution` target `1.3.0`, When the run finalizes, Then the `FixProposal.target` is `1.3.0`, not the package
  name, and the proposal stores no diff.
- **AC2 — The approve delivers.** Given that proposal and a fixture clone whose manifest declares the package, When the
  operator approves it and `open_fix_proposal` runs, Then the real `run_actuator` (not patched) receives the stored
  candidates and the clone's `manifest_locations`, and the fake forge client records one draft PR on a `warden/fix/`
  branch whose one commit carries the manifest edit to the target floor.
- **AC3 — No fix, no PR.** Given an approve whose re-solve yields no `manifest_fix` (no candidate accepted, or no
  declaring manifest), When it runs, Then the proposal records a `failed` actuation with the reason and the fake forge
  client records zero writes.
- **AC4 — One helper.** Given the new public helper, When `warden scan` builds its actuator inputs, Then it calls the
  helper and its output is unchanged (the existing CLI tests stay green).
- **AC5 — The contract follows.** A memlog decision on `spec-pyforge-warden` records the queue-then-re-solve handoff; no
  `SPEC.md` hand edit.
- **AC6 — Green.** `pixi run --frozen -e pyforge-warden pyforge-warden-test` and
  `pixi run -e pyforge-guild platform-ci-local -- --test` pass.

## Boundaries & Constraints

**Always:** nothing auto-opens on a fleet repo: zero forge writes until an approve, one per approval; the fleet
repository is admitted only through `authorized_fleet_repo`; the scanned clone is never written outside its throwaway
copy; failures are `failed` actuation outcomes, never a rung or an exit code.

**Never:** run a live approve against the designated organisation: the credential for a live fleet write is not ruled (`spec-pyforge-warden/.memlog.md`, the 2026-10-11 decision, item 9), so the code path is tested against a fake
forge client only; store a diff at queue time; edit Story 16.3's text or ledger row; hand-edit `SPEC.md`.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-warden` CAP-26 (FR-43) — Warden scans the fleet; each fix waits for the operator's
  approval.
- Parent capability: `spec-pyforge-warden` CAP-24 (FR-41) — the actuator path an approved proposal opens through.

Parent: CAP-26

- EGM audit findings carried: WAR-D-C1 (the one Blocker that survived triage) and WAR-D-R3 (cluster WAR-CL-1; accepted
  2026-11-01; one memlog event each on `spec-pyforge-warden/.memlog.md`); residue `_bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md`.
- Epic: Epic 16 — a fix story joins its done epic (operator rule 2026-10-04; doctor Story 41.5 lets the epic key roll up
  to `in-progress`).
- Ledger key: `16-6-fleet-approve-re-solves-and-delivers-the-fix-it-queued`.
- Ledger status at mint: `backlog`.
- Deps: S-14.4.
- Surface: `src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py`, `src/shared/packages/pyforge-warden/src/pyforge/warden/actuator.py`, `src/shared/packages/django-warden/src/django_warden_fabric/tasks.py`, `src/shared/packages/django-warden/src/django_warden_fabric/proposals.py`,
  `src/platform/tests/test_warden_fleet_proposals.py`.
- Dream: `docs/dreams/pyforge-warden.md` § *Realization log*, the 2026-11-01 (the EGM fleet audit) entry.
- Minted 2026-11-01 by the EGM audit landing (marshal Story 113.7, spec-pyforge-marshal:CAP-302); mode in-PR: built in the audit's landing PR.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (the station's `verify_commands`).
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: pass (the `django-warden` tests under
  `src/platform/tests/`, including `src/platform/tests/test_warden_fleet_proposals.py` and
  `src/platform/tests/test_warden_fleet_run.py`).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks:**
- `grep -n "_run_fix_actuator" src/platform/tests/test_warden_fleet_proposals.py` — expected: no `patch(` of it.

## Auto Run Result

Status: backlog

Summary: not yet dispatched.

## Spec Change Log

- 2026-11-01: minted `backlog` from the EGM fleet audit (marshal Story 113.7): cluster WAR-CL-1, findings WAR-D-C1
  (Blocker) and WAR-D-R3, accepted by the operator; the live-approve credential stays the operator's; mode in-PR.

## Review Triage Log

- (none yet)
