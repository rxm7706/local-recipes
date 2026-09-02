---
title: "Celery hardening and the builds pool"
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
  - "src/platform/deploy/charts/platform/templates/worker-deployment.yaml"
  - "src/platform/deploy/charts/platform/values.yaml"
warnings: []
deferred:
  - "Sandboxed build containers for Mason (mason chain)."
---

<intent-contract>

## Intent

**Problem:** No `task_acks_late`, no `task_reject_on_worker_lost`, one default queue for
all stations, `CELERY_TASK_TIME_LIMIT = 300` and a 310 s grace period. A worker
SIGKILL silently drops the task and the supervisor row stays `RUNNING` forever;
a Mason build flood starves Doctor remedies; nothing longer than five minutes
can run at all. Red-team **S-2**, **T-6**, directive **R-10**.

**Approach:** `task_acks_late=True`, `task_reject_on_worker_lost=True`,
`worker_prefetch_multiplier=1`; per-station queues with routing; a dedicated
`builds` queue with an hours-scale time limit and its own Deployment whose
grace period derives from that limit; a `priority` queue for Doctor remedies
and supervisor completions; a supervisor sweep that marks RUNNING rows whose
task is gone as FAILED (BS-8 partial).

## Acceptance Criteria

- Given a worker killed mid-task, when a replacement starts, then the task re-runs exactly once (acks_late + reject_on_worker_lost) and the supervisor row reaches a terminal state.
- Given `helm template`, when rendered, then `worker` consumes the default + per-station queues and a separate `worker-builds` Deployment consumes `builds` with `terminationGracePeriodSeconds` = builds limit + slack.
- Given a Mason build enqueued, when routed, then it lands on `builds`; a Doctor remedy lands on `priority`; a test asserts the routing table.
- Given a RunState RUNNING with no live task for longer than the limit, when the sweep runs, then it is marked FAILED with reason `worker_lost`.

## Boundaries & Constraints

**Always:** Write under `_bmad-output/projects/pyforge-steward/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` only — never `scripts/bmad-switch`.
Ledger key `42-4-celery-hardening-and-the-builds-pool`. Host never imports `pyforge.*`. Celery + redis-broker (AD-10). One image, entrypoint args differ.

**Block If:** Implementation would move to RQ or django-tasks, or raise the default queue limit to hours.

**Never:** A task idempotency assumption without `acks_late`. A builds pod with the 300 s limit.

</intent-contract>

## Tasks

- [ ] Settings
- [ ] Routing table + queue names in chrome
- [ ] Chart: second worker Deployment + values
- [ ] Supervisor sweep task
- [ ] Tests
- [ ] Ledger `42-4-celery-hardening-and-the-builds-pool` → `review` then `done` via `sprint-ledger-sync`.

## Verification

`src/platform` policy suite; chart invariants; supervisor tests.

## Source

Red-team review: `research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md` (directive and finding ids in the FR/AD line of
`epics.md` Story 42.4). Sprint change proposal:
`sprint-change-proposal-2026-09-02-red-team-high.md`.
