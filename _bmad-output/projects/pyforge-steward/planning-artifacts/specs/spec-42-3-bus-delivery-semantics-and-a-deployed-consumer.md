---
title: "Bus delivery semantics and a deployed consumer"
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
  - "src/shared/packages/django-pyforge/src/django_pyforge/events/fabric.py"
  - "src/shared/packages/django-pyforge/src/django_pyforge/events/constants.py"
  - "src/platform/deploy/charts/platform/templates/worker-deployment.yaml"
warnings: []
deferred:
  - "OpenLineage emission riding CAP-8 (stack.md leverage)."
---

<intent-contract>

## Intent

**Problem:** The fabric has a producer, one registered event type and no deployed consumer.
`_apply` retries a failing well-formed event immediately and forever (no ACK,
no attempt counter, no backoff); `harvest_poison` quarantines only unparseable
entries and its default `min_idle_time=0` steals live messages; the envelope
carries no `traceparent`. Red-team **A-1**, **A-2**, **A-4**, **A-5**,
directive **R-9**.

**Approach:** Track attempts via `XPENDING` delivery count; exponential backoff; DLQ a
well-formed event after N failures with the exception recorded; real
`min_idle_time` (≥ handler timeout); one consumer runner
(`manage.py consume_events --station <name>`) shipped as a chart Deployment per
subscribing station; register the Warden→Doctor→Mason vocabulary; add
`traceparent` as a CloudEvents extension and propagate it into Celery headers.

## Acceptance Criteria

- Given a well-formed event whose handler raises N times, when consumed, then it is moved to the DLQ with the last error and ACKed; the CAP-8 success clause test (poison lands in DLQ instead of retrying forever) exists and fails without the change.
- Given retries, when they occur, then delays follow the documented backoff and the consumer does not spin.
- Given `harvest_poison`, when run, then it claims only entries idle longer than the configured threshold.
- Given `helm template`, when rendered, then a `consume-events` Deployment exists for each station listed in `events.consumers`, on the platform image, with the same contexts as worker.
- Given `EVENT_TYPES`, when read, then it registers at least `recipe.audit.failed`, `remedy.requested`, `recipe.rebuild.requested`, `remedy.completed`, each with a `dataschema`.
- Given an event published from a request with a `traceparent`, when a consumer handles it and enqueues Celery work, then the same trace id appears in the task headers and structlog context.

## Boundaries & Constraints

**Always:** Write under `_bmad-output/projects/pyforge-steward/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` only — never `scripts/bmad-switch`.
Ledger key `42-3-bus-delivery-semantics-and-a-deployed-consumer`. Host never imports `pyforge.*`. Consumer group name = station token. One stream, one DLQ (AD-8). Loop-depth ceiling unchanged.

**Block If:** Implementation would add a second bus, trim the DLQ automatically, or make retries unbounded again.

**Never:** A consumer that ACKs before the handler returns. A DLQ write without the error recorded.

</intent-contract>

## Tasks

- [ ] Fabric retry/backoff/DLQ
- [ ] Consumer runner command + Deployment template
- [ ] Event vocabulary + schemas
- [ ] traceparent extension + Celery header propagation
- [ ] Tests incl. real redis-server
- [ ] Ledger `42-3-bus-delivery-semantics-and-a-deployed-consumer` → `review` then `done` via `sprint-ledger-sync`.

## Verification

`src/platform/tests/test_cloudevents_redis_broker.py` extended; chart invariants; `platform-dev` env.

## Source

Red-team review: `research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md` (directive and finding ids in the FR/AD line of
`epics.md` Story 42.3). Sprint change proposal:
`sprint-change-proposal-2026-09-02-red-team-high.md`.
