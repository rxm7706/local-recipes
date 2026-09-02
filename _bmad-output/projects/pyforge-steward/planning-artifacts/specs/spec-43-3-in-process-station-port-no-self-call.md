---
title: "In-process station port, no self-call"
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
  - "src/platform/config/settings/base.py"
  - "src/shared/packages/django-pyforge/src/django_pyforge/portals.py"
  - "src/shared/packages/pyforge-core/src/pyforge/core/dispatch.py"
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Portals call "the host" over `httpx`; the host is the same gunicorn pool, so a
worker awaits a worker and `ATOMIC_REQUESTS = True` pins a PostgreSQL
transaction for the wait. Under load this is a self-call deadlock and latency
amplifier. Red-team **T-3**, directive **R-6**.

**Approach:** Portals call station code through an in-process port (`django-pyforge` client
→ `pyforge.core.dispatch` via the hook registry) when co-located, and over
HTTP only when `STATION_REMOTE=1`; streaming/long views are marked
`non_atomic_requests`; the import boundary is kept by importing through the
registry, never `pyforge.<station>` directly.

## Acceptance Criteria

- Given a portal view in the default profile, when it needs station data, then no HTTP request to the host's own address is made (test asserts zero loopback calls).
- Given `STATION_REMOTE=1`, when the same view runs, then it uses `pyforge.core.client` over HTTP with the assertion.
- Given the SSE / long-poll views, when inspected, then they are `non_atomic_requests` and a policy test lists them.
- Given the host import-linter, when run, then it still passes (no `pyforge.*` import under `src/platform/`).

## Boundaries & Constraints

**Always:** Write under `_bmad-output/projects/pyforge-steward/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` only — never `scripts/bmad-switch`.
Ledger key `43-3-in-process-station-port-no-self-call`. Host never imports `pyforge.*`. One assertion format on both paths (AD-7). Import boundary test stays green.

**Block If:** Implementation would import station packages into `src/platform/` directly, or drop `ATOMIC_REQUESTS` globally.

**Never:** A portal view that awaits its own gunicorn pool.

</intent-contract>

## Tasks

- [ ] In-process port in chrome
- [ ] Profile switch
- [ ] Non-atomic sweep + policy test
- [ ] Loopback-call test
- [ ] Ledger `43-3-in-process-station-port-no-self-call` → `review` then `done` via `sprint-ledger-sync`.

## Verification

`src/platform/tests` import boundary + new loopback test; chrome tests.

## Source

Red-team review: `research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md` (directive and finding ids in the FR/AD line of
`epics.md` Story 43.3). Sprint change proposal:
`sprint-change-proposal-2026-09-02-red-team-high.md`.
