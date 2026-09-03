---
title: "Bus delivery semantics and a deployed consumer"
type: "fix"
created: "2026-09-02"
status: "in-review"
updated: "2026-09-03"
baseline_commit: "58ee07a0"
baseline_revision: "1af2ca2b629b3f9a83da8ebe9d651d56a89de9b3"
followup_review_recommended: true
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
  - summary: >-
      The shipped adapters validate shape and log; Doctor's and Mason's actual
      reactions (choosing a remedy, running a rebuild, reporting completion)
      are not implemented here.
    evidence: |-
      `DomainAdapter.apply` is a no-op for all four types in
      `django_pyforge/events/adapters.py`. The story's Approach binds the
      vocabulary, the consumer runner and its Deployment — which now exist and
      are proven end to end (publish -> consume -> Celery header) — but the
      station-side behaviour behind each type is station work (Doctor owns the
      `remedy.requested` consumer per the change proposal's ownership table).
      `register_adapter()` is the seam: a station subclasses the adapter for
      its type and re-registers it at AppConfig ready time.
    location: >-
      src/shared/packages/django-pyforge/src/django_pyforge/events/adapters.py
    severity: medium
  - summary: >-
      A process that dies mid-handler leaves the event at-most-once: the
      applied key is set before the handler runs (red-team A-3, not in this
      story's scope).
    evidence: |-
      `_apply` does `SET NX` before calling the handler and only deletes the
      key on a raised exception. After a crash the retry pass re-claims the
      entry, `_mark_applied` fails because the key is still set, and the entry
      is ACKed as a duplicate without re-running. The TTL from Story 40.2
      bounds this to seven days. Fixing it means moving the applied mark after
      the handler (at-least-once) or a per-consumer in-flight marker; both
      change the idempotency contract and belong to a story that names A-3.
    location: >-
      src/shared/packages/django-pyforge/src/django_pyforge/events/fabric.py
    severity: medium
  - summary: >-
      The handler timeout is a budget, not an enforced limit: nothing
      interrupts a handler that runs past `DJANGO_PYFORGE_EVENT_HANDLER_TIMEOUT_MS`.
    evidence: |-
      The consumer runs handlers inline. The timeout is what `harvest_poison`
      uses as its `min_idle_time` (so a live handler is never stolen from) and
      what the chart's `terminationGracePeriodSeconds` is sized against; a
      handler that hangs holds its entry until the pod is replaced, after which
      the harvest reclaims it. A real limit needs a thread or `SIGALRM` guard;
      handlers today enqueue Celery work rather than doing it, so the exposure
      is a stuck consumer, not a stuck event.
    location: >-
      src/shared/packages/django-pyforge/src/django_pyforge/management/commands/consume_events.py
    severity: low
  - summary: >-
      A harvest claim counts as a delivery, so an abandoned delivery spends an
      attempt; with `EVENT_MAX_ATTEMPTS=1` a reclaimed entry is quarantined
      without a retry.
    evidence: |-
      XAUTOCLAIM increments the delivery counter (JUSTID would not, but then
      the fields needed for the unparseable check are not returned). The rule
      is stated in `harvest_poison` and covered by
      `test_harvest_quarantines_exhausted_entry_with_recorded_error`; with the
      default of five attempts it costs one retry per crash, which is the
      honest reading of "delivered and never acknowledged".
    location: >-
      src/shared/packages/django-pyforge/src/django_pyforge/events/fabric.py
    severity: low
  - summary: >-
      compose.yml has no `consume-events` service; only the chart deploys the
      consumer.
    evidence: |-
      AC 4 names `helm template`. The local compose stack still runs a producer
      with no listener; `python manage.py consume_events --station doctor` from
      a shell against the compose Redis is the workaround until a compose
      service is added alongside `worker`.
    location: >-
      src/platform/compose/compose.yml
    severity: low
  - summary: >-
      `events.replicaCount` and `events.resources` are one knob for every
      consumer station.
    evidence: |-
      The values block is a list of station names plus shared settings.
      Per-station replicas would need a map-shaped value; deliberately not
      done until a station needs more than one consumer.
    location: >-
      src/platform/deploy/charts/platform/values.yaml
    severity: low
  - summary: >-
      `test_execute_supervised_run_leaves_no_celery_result_key` (pre-existing,
      Story 40.2) fails locally for lack of a `django_db` mark; unchanged here.
    evidence: |-
      It calls `migrate` and creates a `RunState` row without the mark, so
      pytest-django refuses the connection. Identical at the `1af2ca2b62`
      baseline (verified by running the HEAD copy in isolation); it is one of
      the thirteen pre-existing local failures the platform-suite memory note
      lists. Not touched because it is not this story's test and a mark change
      deserves its own eyes.
    location: >-
      src/platform/tests/test_cloudevents_redis_broker.py
    severity: low
  - summary: >-
      Ruff and mypy findings on the touched files are pre-existing categories,
      not new ones.
    evidence: |-
      `ruff check` (platform config) over the touched django-pyforge files:
      18 findings, all `PLR0913`/`PLR0917`/`FBT001`/`FBT002` on signatures that
      predate this story plus five `E501` in code this story did not write.
      `mypy tests/test_cloudevents_redis_broker.py tests/test_chart_invariants.py`
      (CI's scope): five errors, all in pre-existing code (`CountingRedis.xadd`
      override, the `lookup_runner` monkeypatch, the liquibase Job helper's
      `Any | None` key). Platform CI's `ruff check .` does not lint
      `src/shared/packages/`.
    location: >-
      src/platform/pyproject.toml
    severity: low
  - summary: >-
      Scoped spec-surface stamp for `spec-pyforge-unifying-strategy` is not run
      by this story.
    evidence: |-
      The memlog entry for this story is appended (downgrading the drift to
      `drift-presumed: warn`); `--write-baseline --spec
      pyforge-steward/spec-pyforge-unifying-strategy` must run from a CLEAN
      worktree after landing, never from the dispatch worktree — the same
      residual Story 42.2 recorded, whose ~60-path lag this story does not
      reconcile either.
    location: >-
      scripts/.spec-surface-baseline.json
    severity: low
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

- [x] Fabric retry/backoff/DLQ
- [x] Consumer runner command + Deployment template
- [x] Event vocabulary + schemas
- [x] traceparent extension + Celery header propagation
- [x] Tests incl. real redis-server
- [x] Ledger `42-3-bus-delivery-semantics-and-a-deployed-consumer` → `review` (done 2026-09-03 via `sprint-ledger-sync --project steward`); `done` follows landing.

## Verification

`src/platform/tests/test_cloudevents_redis_broker.py` extended; chart invariants; `platform-dev` env.

### Record (2026-09-03, dispatch worktree, `platform-ci-test` python + `platform-dev` helm/redis-server/postgres)

- AC 1 — `test_well_formed_poison_lands_in_dlq_after_max_attempts_with_last_error`: handler raises
  `KeyError` five times; DLQ row carries `reason=exhausted`, `error="KeyError: 'reason'"`,
  `attempts=5`; original ACKed; never re-attempted. Fails against the `1af2ca2b62` fabric (the old
  `_apply` re-ran the handler on every call and the DLQ stayed empty).
- AC 2 — `test_retry_delays_follow_documented_backoff_and_consumer_does_not_spin`: 25 polls without
  time passing make no second attempt; attempts fire at 1s/2s/4s/8s exactly, not before.
- AC 3 — `test_harvest_claims_only_entries_idle_past_threshold`: `xautoclaim` is called with
  `min_idle_time=300000`; nothing is claimed until idle exceeds it; then the unparseable entry is
  quarantined and the well-formed ones are retried after their backoff.
- AC 4 — `test_consume_events_deployment_per_configured_station` (+ `_follows_values_and_refuses_non_station`,
  + ungated guard companion): one Deployment per `events.consumers` entry, args
  `python manage.py consume_events --station <name>`, image/env/securityContexts/volumes/serviceAccount
  equal to worker's; `--set events.consumers={nope}` fails the render; the redis NetworkPolicy admits the
  consumer components. `helm lint` green.
- AC 5 — `test_event_vocabulary_registered_with_dataschemas`: four types, each with a
  `urn:pyforge:schema:events:<type>:v1` dataschema and an adapter; all publish.
- AC 6 — `test_trace_id_from_request_reaches_celery_headers_and_structlog`: Django test client request with
  `traceparent: 00-0af76519…-01` publishes; the envelope carries the same trace id; the consumer's handler
  enqueues an eager Celery task whose `request.headers["traceparent"]` and structlog contextvars
  `trace_id` equal it. `test_enqueue_supervised_run_carries_traceparent_header` covers the supervisor path.
- Real broker — `test_real_redis_retry_backoff_dlq_and_harvest` against `redis-server` (platform-dev):
  three attempts at ≥100 ms / ≥200 ms spacing, DLQ row with the error, `XPENDING` drained, harvest honours
  the threshold, reclaimed entry retried after its backoff.
- Never-clauses — `test_ack_only_after_handler_returns` (entry still pending inside the handler);
  `test_harvest_quarantines_exhausted_entry_with_recorded_error` (DLQ from harvest carries the error the
  dead consumer recorded).
- Full platform suite on a fresh test database: **13 failed / 626 passed / 6 skipped / 5 errors**;
  detached worktree at `1af2ca2b62`: 13 failed / 611 passed / 5 errors — the FAILED/ERROR lists are
  identical in both directions (the 15 extra passes are this story's tests). The 13 + 5 are the
  pre-existing local-environment set (host-board row isolation, openfeature channel policy, liquibase DDL
  governance, transactional-DB teardown, the unmarked redis-broker test, the `pyforge.core`-less station
  portal shells).

## Source

Red-team review: `research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md` (directive and finding ids in the FR/AD line of
`epics.md` Story 42.3). Sprint change proposal:
`sprint-change-proposal-2026-09-02-red-team-high.md`.
