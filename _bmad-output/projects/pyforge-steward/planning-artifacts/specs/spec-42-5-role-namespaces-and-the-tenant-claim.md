---
title: "Role namespaces and the tenant claim"
type: "fix"
created: "2026-09-02"
status: "done"
updated: "2026-09-03"
baseline_commit: "b1e8e188d504add83c7e074f1bf01759270ca742"
baseline_revision: "b1e8e188d504add83c7e074f1bf01759270ca742"
severity: "HIGH"
followup_review_recommended: false
review_loop_iteration: 0
context:
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/resilience-invariants.md"
  - "src/shared/packages/django-pyforge/src/django_pyforge/roles.py"
  - "src/shared/packages/django-pyforge/src/django_pyforge/access.py"
  - "src/platform/tests/test_host_board_row_isolation.py"
warnings: []
deferred:
  - summary: >-
      Per-tenant quotas (after R-8 limiter).
  - summary: >-
      Legacy bare tenant ids (east/west without pyforge:tenant:) are not accepted even under DJANGO_PYFORGE_LEGACY_BARE_ROLES — only bare station slugs get the migration switch.
    evidence: |-
      Spec AC targets bare station names; tenant prefix is required from day one per R-13.
    severity: low
---

<intent-contract>

## Intent

**Problem:** Reachability is "IdP group name equals station slug". Tenants are also bare
group names (`east`, `west`). Any IdP group that happens to be called `atlas`
or `flags` grants access; the Dream's five-persona matrix does not exist in
code. Red-team **X-3**, **B-6**, directive **R-13**.

**Approach:** One configurable claim carrying prefixed values: `pyforge:station:<name>`,
`pyforge:tenant:<id>`, `pyforge:admin`. `roles.py` parses and refuses bare
station names (with a documented migration switch for one release). `tenant`
is added to `RunState` and as a CloudEvents extension; Lane 3 row slicing
reads the tenant prefix, not a bare group.

## Acceptance Criteria

- Given a group `atlas` (bare), when reachability is computed, then it is refused unless `DJANGO_PYFORGE_LEGACY_BARE_ROLES=1`, which logs a deprecation.
- Given `pyforge:station:atlas` and `pyforge:tenant:east`, when the board is requested, then rows are sliced by tenant and the station is reachable; the existing row-isolation test passes under the new names.
- Given `start`, when a run is published, then `RunState.tenant` is set from the assertion and the CloudEvent carries `pyforgetenant`.
- Given the Dream RBAC matrix, when updated, then it lists the implemented prefixes and nothing else.

## Boundaries & Constraints

**Always:** Write under `_bmad-output/projects/pyforge-steward/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` only — never `scripts/bmad-switch`.
Ledger key `42-5-role-namespaces-and-the-tenant-claim`. Host never imports `pyforge.*`. Roles are re-read from the token per request (AD-15). Mint (40.1) reads the same parser.

**Block If:** Implementation would store roles in Django groups as the authority, or leave bare names accepted silently.

**Never:** A capability role and a tenant id in the same namespace.

</intent-contract>

## Tasks

- [x] Parser + prefixes
- [x] Migration switch + deprecation log
- [x] `RunState.tenant` migration via changelog
- [x] CloudEvents extension
- [x] Tests + Dream matrix
- [x] Ledger `42-5-role-namespaces-and-the-tenant-claim` → `review` then `done` via `sprint-ledger-sync`.

## Verification

`src/platform/tests/test_host_board_row_isolation.py`, `test_django_pyforge_chrome.py`, assertion tests.

## Review Triage Log

### 2026-09-03 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 1: (low 1)
- reject: 2
- addressed_findings:
  - none

## Auto Run Result

Status: done

Implemented prefixed role namespaces in `django_pyforge.roles` (`pyforge:station:*`, `pyforge:tenant:*`, `pyforge:admin`) with bare-station refusal and `DJANGO_PYFORGE_LEGACY_BARE_ROLES` deprecation logging. Lane 3 board slicing reads tenant prefix; mint uses `station_granted`; `RunState.tenant` + Liquibase changeset 21; `pyforgetenant` CloudEvents extension and `run.started` publish on supervisor start; Dream RBAC matrix updated.

**Files changed:**
- `django_pyforge/roles.py` — parser, reachability + tenant helpers
- `django_atlas_portal/board.py` — tenant-based row role
- `django_pyforge/models.py` + migration/changelog — `RunState.tenant`
- `django_pyforge/events/*` — `pyforgetenant`, `run.started`
- `django_pyforge/supervisor.py` — tenant persistence + event emit
- `django_pyforge/assertion/views.py` — prefixed station gate
- `docs/dreams/pyforge-unifying-strategy.md` — RBAC matrix
- Platform tests — prefixed roles + `test_role_namespaces.py`

**Review:** 0 patches; 1 defer (legacy bare tenants); 2 reject (noise).

**Follow-up review:** false (0 patch findings).

**Verification:** 55 passed non-db (`test_django_pyforge_chrome`, assertion suite, `test_role_namespaces`) under `platform-ci-test`; django_db suites require PostgreSQL (not available locally).

**Residual risks:** IdP mappers must emit prefixed groups before legacy switch is removed; `run.started` publish is best-effort when broker URLs differ.

## Source

Red-team review: `research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md` (directive and finding ids in the FR/AD line of
`epics.md` Story 42.5). Sprint change proposal:
`sprint-change-proposal-2026-09-02-red-team-high.md`.
