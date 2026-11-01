---
title: "16.10: The fleet export carries each repo's head_sha"
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
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-16-1-warden-inventories-a-ghe-organisation-s-repos.md
  - src/shared/packages/django-warden/src/django_warden_fabric/fleet_inventory.py
  - src/shared/packages/pyforge-warden/src/pyforge/warden/fleet_github_rest.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/orchestration/fleet_inventory_sensor.py
deferred: []
---

<intent-contract>

## Intent

**Problem:** warden's fleet inventory export is the data Atlas reads (`spec-pyforge-atlas:CAP-61`), and atlas's sensor
rejects it: `parse_fleet_inventory`
(`src/shared/packages/pyforge-atlas/src/pyforge/atlas/orchestration/fleet_inventory_sensor.py` about :62-65) returns
`None` for any row without a non-empty `head_sha`, and `export_document` (`src/shared/packages/django-warden/src/django_warden_fabric/fleet_inventory.py` about :271-279 at
`03a7aff5d9`) writes `full_name`, `default_branch`, `clone_url` and `archived` only. The question has been open since
2026-10-10 (Story 16.1's spec, *Named, not fixed here*; the 2026-10-11 memlog decision, item 9). CAP-26 success also
leaves the export's fields unpinned (WAR-M-Z3; its keys-not-blobs part is refuted: that rule governs the Celery
message).

**Operator ruling 2026-11-01** (the `spec-pyforge-warden` memlog's decision of that date): add `head_sha`.

EGM audit 2026-11-01, cluster WAR-CL-4; finding WAR-M-Z3, accepted by the operator on 2026-11-01; residue `_bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md`.

**Approach:**
- The `GET`-only client (`src/shared/packages/pyforge-warden/src/pyforge/warden/fleet_github_rest.py`) reads each repo's default-branch tip (one `GET` per repo), and
  `export_document` writes it as `head_sha` on each `repos[]` row.
- A repo whose tip cannot be read (an empty repo has none) goes to the export's `skipped` list with its reason, never
  to `repos[]` without `head_sha`.
- A test proves the export meets the acceptance rule of atlas's `parse_fleet_inventory`, reading the export as data.
- CAP-26 success pins the export fields (`full_name`, `default_branch`, `clone_url`, `archived`, `head_sha`) through
  the `spec-pyforge-warden` `bmad-spec` re-derive (with WAR-CL-3's), with the rest of WAR-CL-4's scoping (the proposal
  lifecycle is never a verdict; `platform-ci-local -- --test` is the platform suite).

Ledger key: `16-10-the-fleet-export-carries-each-repo-s-head-sha`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-warden` CAP-26 (FR-43) — the inventory is published as data other stations read. A `fix`, so no new
  CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag (`pyforge.warden.fleet_inventory` keeps gating the
  inventory).

## Acceptance Criteria

- **AC1 — Each row carries `head_sha`.** Given the fictional fixture organisation `example-org` of three repos and a
  fixture client with no real network, When the inventory runs, Then the export's `repos[]` holds three rows, each with
  `full_name`, `default_branch`, `clone_url`, `archived` and a non-empty `head_sha` equal to the fixture's tip.
- **AC2 — Reads stay `GET`.** Given the AC1 run, Then every request the client issued is a `GET`, and the token is
  never in the export, a log, the Celery message or error text.
- **AC3 — An unreadable tip is skipped.** Given a fixture repo with no commits, When the inventory runs, Then it is
  listed under `skipped` with its reason and absent from `repos[]`.
- **AC4 — Atlas accepts the export.** Given the AC1 export read as data, Then it meets the acceptance rule of atlas's
  `parse_fleet_inventory` (every row has a non-empty `full_name` and `head_sha`); no station imports
  `django_warden_fabric` or `pyforge.warden` for it.
- **AC5 — The target stays private.** The leak-guard tests stay green; fixtures name `example-org` only.
- **AC6 — The contract follows.** CAP-26 success pins the five export fields through a `bmad-spec` re-derive; no
  `SPEC.md` hand edit.
- **AC7 — Green.** `pixi run --frozen -e pyforge-warden pyforge-warden-test` and
  `pixi run -e pyforge-guild platform-ci-local -- --test` pass.

## Boundaries & Constraints

**Always:** the inventory is read-only (`GET` for REST); the export path stays gitignored; no tracked file names the
designated organisation, its repositories or its projects.

**Never:** change atlas's sensor (the ruling chose warden's export over relaxing it); write a partial export on a typed
error; hand-edit `SPEC.md`.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-warden` CAP-26 (FR-43) — the fleet inventory, published as data
  (`spec-pyforge-atlas:CAP-61` reads it); a fix, no new CAP.

Parent: CAP-26

- EGM audit finding carried: WAR-M-Z3 (cluster WAR-CL-4; accepted 2026-11-01; one memlog event on
  `spec-pyforge-warden/.memlog.md`); operator ruling 2026-11-01 (the memlog decision of that date); residue `_bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md`.
- Epic: Epic 16 — a fix story joins its done epic (operator rule 2026-10-04; doctor Story 41.5 lets the epic key roll up
  to `in-progress`).
- Ledger key: `16-10-the-fleet-export-carries-each-repo-s-head-sha`.
- Ledger status at mint: `backlog`.
- Deps: —.
- Surface: `src/shared/packages/django-warden/src/django_warden_fabric/fleet_inventory.py`, `src/shared/packages/pyforge-warden/src/pyforge/warden/fleet_github_rest.py`, `src/platform/tests/test_warden_fleet_inventory.py`,
  `src/shared/packages/pyforge-warden/tests/unit/test_fleet_github_rest.py`.
- Dream: `docs/dreams/pyforge-warden.md` § *Realization log*, the 2026-11-01 (the EGM fleet audit) entry.
- Minted 2026-11-01 by the EGM audit landing (marshal Story 113.7, spec-pyforge-marshal:CAP-302); mode in-PR: built in the audit's landing PR.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/unit/test_fleet_github_rest.py -q` — expected: pass.
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: pass (the `django-warden` tests under
  `src/platform/tests/`, including `src/platform/tests/test_warden_fleet_inventory.py` and its leak-guard tests).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Auto Run Result

Status: backlog

Summary: not yet dispatched.

## Spec Change Log

- 2026-11-01: minted `backlog` from the EGM fleet audit (marshal Story 113.7): cluster WAR-CL-4, finding WAR-M-Z3,
  accepted by the operator; operator ruling 2026-11-01 (add `head_sha`); mode in-PR.

## Review Triage Log

- (none yet)
