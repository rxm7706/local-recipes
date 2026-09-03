---
title: "Celery hardening and the builds pool"
type: "fix"
created: "2026-09-02"
status: "done"
updated: "2026-09-03"
baseline_commit: "58ee07a0"
baseline_revision: "1d9b50fbdd218dde1c16646d7b023aa790ebbec9"
followup_review_recommended: false
review_loop_iteration: 0
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
  - summary: >-
      Compose stack still runs a single undifferentiated Celery worker with no
      beat or builds pool — local dev does not mirror the Kubernetes split-pool
      topology introduced here.
    evidence: |-
      src/platform/compose/compose.yml worker service unchanged; deploy/README
      documents K8s only.
    location: >-
      src/platform/compose/compose.yml
    severity: low
  - summary: >-
      Story 42.4 Helm render tests are gated on `@requires_helm` and skip in
      platform-ci-test when helm is absent — the same pre-existing CI pattern
      as other chart stories.
    evidence: |-
      test_chart_invariants.py `@requires_helm`; platform-ci-test env has no
      kubernetes-helm dependency.
    location: >-
      src/platform/tests/test_chart_invariants.py
    severity: medium
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

- [x] Settings
- [x] Routing table + queue names in chrome
- [x] Chart: second worker Deployment + values
- [x] Supervisor sweep task
- [x] Tests
- [x] Ledger `42-4-celery-hardening-and-the-builds-pool` → `review` then `done` via `sprint-ledger-sync`.

## Verification

`src/platform` policy suite; chart invariants; supervisor tests.

## Source

Red-team review: `research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md` (directive and finding ids in the FR/AD line of
`epics.md` Story 42.4). Sprint change proposal:
`sprint-change-proposal-2026-09-02-red-team-high.md`.

## Review Triage Log

### 2026-09-03 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 1: (medium 1)
- defer: 2: (medium 1, low 1)
- reject: 14
- addressed_findings:
  - `[medium]` `[patch]` Added AST literal guard for `CELERY_WORKER_PREFETCH_MULTIPLIER` beside the existing `acks_late` / `reject_on_worker_lost` guards in `test_delivery_is_at_least_once_by_configuration` so an env-overridable prefetch cannot silently reopen S-2.

## Auto Run Result

Status: done

**Summary:** Celery delivery hardened (`acks_late`, `reject_on_worker_lost`, prefetch 1); canonical queue topology in `django_pyforge.queues` with Mason builds → `builds`, Doctor remedy → `priority`, per-station queues on the general pool; hours-scale `builds` pool with separate Helm Deployment and derived grace period; beat Deployment for prune + worker-lost sweep; `sweep_lost_runs` supervisor backstop with `worker_lost` terminalization.

**Files changed (since baseline `1d9b50fbdd`):**
- `src/platform/config/settings/base.py` — Celery hardening knobs, queue declaration, builds limit, beat schedule
- `src/shared/packages/django-pyforge/src/django_pyforge/queues.py` — single routing/topology table
- `src/shared/packages/django-pyforge/src/django_pyforge/supervisor.py` — `begin_attempt`, `sweep_lost_runs`, `live_task_ids`
- `src/shared/packages/django-pyforge/src/django_pyforge/tasks.py` — redelivery-aware supervised run + sweep task
- `src/shared/packages/django-pyforge/src/django_pyforge/management/commands/sweep_lost_runs.py` — operator command
- `src/platform/deploy/charts/platform/*` — worker-builds + beat Deployments, values, helpers, NetworkPolicy
- `src/platform/tests/test_celery_hardening_and_builds_pool.py` — AC coverage (settings, router, supervisor, sweep)
- `src/platform/tests/test_chart_invariants.py` — Helm render invariants for split pools
- `src/platform/deploy/README.md` — topology documentation

**Review findings:** 1 medium patch applied; 2 deferred (compose local-dev parity, helm-skipped CI pattern); 14 rejected as out-of-scope docs/skill noise or already-handled behavior.

**Follow-up review recommendation:** false — patched counts: medium 1, low 0; score = 3 (< 5).

**Verification performed:**
- `pixi run -e platform-ci-test pytest src/platform/tests/test_celery_hardening_and_builds_pool.py src/platform/tests/test_chart_invariants.py` — 60 passed, 37 skipped (`@requires_helm`), 10 DB-dependent supervisor integration tests errored locally (postgres unreachable from host; chart + non-DB tests green)
- `pytest …::test_delivery_is_at_least_once_by_configuration` — pass after prefetch AST patch

**Residual risks:** AC1/AC4 proven at settings/supervisor unit seams with simulated redelivery, not live SIGKILL integration; compose laptop stack still single-worker; helm render tests skip when helm absent in CI (pre-existing pattern).
