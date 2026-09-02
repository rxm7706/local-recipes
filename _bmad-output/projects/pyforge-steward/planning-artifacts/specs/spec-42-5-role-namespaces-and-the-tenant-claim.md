---
title: "Role namespaces and the tenant claim"
type: "fix"
created: "2026-09-02"
status: "ready-for-dev"
updated: "2026-09-02"
baseline_commit: "58ee07a0"
severity: "HIGH"
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
  - "Per-tenant quotas (after R-8 limiter)."
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

- [ ] Parser + prefixes
- [ ] Migration switch + deprecation log
- [ ] `RunState.tenant` migration via changelog
- [ ] CloudEvents extension
- [ ] Tests + Dream matrix
- [ ] Ledger `42-5-role-namespaces-and-the-tenant-claim` → `review` then `done` via `sprint-ledger-sync`.

## Verification

`src/platform/tests/test_host_board_row_isolation.py`, `test_django_pyforge_chrome.py`, assertion tests.

## Source

Red-team review: `research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md` (directive and finding ids in the FR/AD line of
`epics.md` Story 42.5). Sprint change proposal:
`sprint-change-proposal-2026-09-02-red-team-high.md`.
