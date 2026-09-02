---
title: "Agent rate limits and run bounds"
type: "feature"
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
  - "src/shared/packages/django-pyforge/src/django_pyforge/supervisor.py"
  - "src/shared/packages/django-pyforge/src/django_pyforge/mcp_http.py"
  - "src/shared/packages/django-pyforge/src/django_pyforge/models.py"
warnings: []
deferred:
  - "Semantic circuit breaker (>N builds/min per subject) — after telemetry exists (R-21)."
---

<intent-contract>

## Intent

**Problem:** Nothing rate-limits `POST /stations/<name>/mcp` per subject. Each supervisor
`start` creates a `RunState` row and a Celery task; an agent loop fills
PostgreSQL and the broker until the broker OOMs and Channels, Celery and the bus
die together. Loop-depth caps only bus recursion. Red-team **A-6**, directive
**R-8**.

**Approach:** Token bucket per `sub` in `redis-cache` on the MCP route and on `start`;
per-station queue-depth ceiling returning 429 with `Retry-After`; a maximum of
concurrent `RUNNING` runs per `sub`; TTL/archival on `RunState`; every Celery
task tagged with `sub` so one command revokes a runaway subject.

## Acceptance Criteria

- Given one `sub` issuing more than the configured rate, when it calls the MCP route, then 429 with `Retry-After` and a structured log; other subjects are unaffected.
- Given the per-station ceiling reached, when `start` is called, then 429 and no `RunState` row is written.
- Given `MAX_RUNNING_PER_SUB` reached, when `start` is called, then 409 with the live run ids.
- Given `pyforge steward revoke --sub <id>`, when run, then queued tasks for that subject are revoked and its RUNNING rows are marked CANCELLED.
- Given `RunState` older than the retention window, when the archival task runs, then rows are pruned or archived and the count is bounded.

## Boundaries & Constraints

**Always:** Write under `_bmad-output/projects/pyforge-steward/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` only — never `scripts/bmad-switch`.
Ledger key `42-2-agent-rate-limits-and-run-bounds`. Host never imports `pyforge.*`. Limits live in `redis-cache` (evictable, AD-10). Numbers are settings with documented defaults.

**Block If:** Implementation would put limiter state on the broker, or gate humans and agents by client name instead of `sub`.

**Never:** An unbounded `start`. A limiter that fails open silently when the cache is down (fail closed with a loud log).

</intent-contract>

## Tasks

- [ ] Limiter in chrome
- [ ] Supervisor ceilings + 429/409
- [ ] Revoke duty + Celery `sub` header
- [ ] Retention task
- [ ] Tests
- [ ] Ledger `42-2-agent-rate-limits-and-run-bounds` → `review` then `done` via `sprint-ledger-sync`.

## Verification

`src/platform/tests/test_warden_portal_audit_start_get.py` extended; new limiter tests; steward duty test.

## Source

Red-team review: `research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md` (directive and finding ids in the FR/AD line of
`epics.md` Story 42.2). Sprint change proposal:
`sprint-change-proposal-2026-09-02-red-team-high.md`.
