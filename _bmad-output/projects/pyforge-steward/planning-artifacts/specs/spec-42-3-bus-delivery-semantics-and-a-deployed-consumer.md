---
title: "Bus delivery semantics and a deployed consumer"
type: "fix"
created: "2026-09-02"
status: "done"
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
      is a stuck consumer, not a stuck event. Review P3 narrowed the rollout
      exposure to exactly one handler: SIGTERM now stops the fabric before the
      next claim/read and interrupts the idle wait.
    location: >-
      src/shared/packages/django-pyforge/src/django_pyforge/management/commands/consume_events.py
    severity: low
  - summary: >-
      `consume_events` now binds through `connect_event_broker` (review P6), so
      a deployment whose `REDIS_CACHE_URL` equals `REDIS_BROKER_URL` -- the
      compose stack, which sets only `REDIS_URL` -- refuses to start the
      consumer with `EventBrokerConfigError`.
    evidence: |-
      `config/settings/base.py` defaults both `REDIS_BROKER_URL` and
      `REDIS_CACHE_URL` to `REDIS_URL`; the chart sets distinct Service URLs,
      compose does not. That refusal is AD-10 doing its job (one Redis serving
      both roles is the canopy anti-pattern), and it lands on the same compose
      gap already recorded above (no `consume-events` service). Running the
      consumer locally needs `REDIS_CACHE_URL` pointed at a second database or
      instance.
    location: >-
      src/platform/compose/compose.yml
    severity: low
  - summary: >-
      A SIGTERM that lands mid-batch leaves the entries XREADGROUP already
      delivered (but not yet attempted) pending under the departing consumer
      name.
    evidence: |-
      Review P3's stop check runs before each entry, so a batch of up to 100
      new entries read in one XREADGROUP may be partly unattempted when the
      loop returns. Those entries carry delivery count 1 and are retried after
      `backoff_ms(1)` by a consumer of the same name, or reclaimed by
      `harvest_poison` after the handler timeout by the replacement pod (whose
      hostname-derived name differs) -- a delay, never a loss. Covered by
      `test_run_passes_stops_after_pass_harvests_on_schedule_and_waits_only_when_idle`.
      Reading smaller batches once a stop is likely would shorten it.
    location: >-
      src/shared/packages/django-pyforge/src/django_pyforge/events/fabric.py
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
  - summary: >-
      The real-redis delivery test skips in CI: `platform-ci-test` has no
      `redis-server` binary, so CI proves retry/backoff/DLQ/harvest only
      against `MemoryRedis`.
    evidence: |-
      `test_real_redis_retry_backoff_dlq_and_harvest` skips when
      `shutil.which("redis-server")` is None; the binary is a `platform-dev`
      feature dependency only and CI's `redis:7` is a service container, not a
      PATH binary. Adding it to the CI env is a `pixi.toml` + `environment.yaml`
      change outside this story. The in-memory double now pins redis-py's
      XCLAIM contract (review P13b), which narrows but does not close the gap.
    location: >-
      pixi.toml (feature.platform-dev)
    severity: medium
  - summary: >-
      A process that dies mid-handler still leaves that group's event
      at-most-once (red-team A-3): the group-scoped applied key is set before
      the handler runs, so the redelivery is ACKed as a duplicate.
    evidence: |-
      Review pass reaffirmed the implementation pass's A-3 entry after the
      applied key became group-scoped (review P1): scoping fixed cross-group
      loss, not same-group crash loss. Out of this story's intent (A-1, A-2,
      A-4, A-5, R-9).
    location: >-
      src/shared/packages/django-pyforge/src/django_pyforge/events/fabric.py
    severity: medium
  - summary: >-
      The handler timeout remains a budget, not an enforced limit; a handler
      that blocks past it stalls the single-threaded consumer and the
      harvester re-runs the entry concurrently after the threshold.
    evidence: |-
      Nothing wraps `handler(event)` in a timeout. Reaffirmed by the review
      pass; the intent treats the handler timeout as a given, not a deliverable.
    location: >-
      src/shared/packages/django-pyforge/src/django_pyforge/events/fabric.py
    severity: low
  - summary: >-
      Consumer names default to `<station>-<hostname>` (the pod name), so
      every rollout mints a new consumer and dead consumers accumulate in the
      group; nothing runs XGROUP DELCONSUMER.
    evidence: |-
      `consume_events.py` derives the consumer from `socket.gethostname()`;
      abandoned entries return only via `harvest_poison` after the handler
      timeout, and `XINFO CONSUMERS` grows with each restart.
    location: >-
      src/shared/packages/django-pyforge/src/django_pyforge/management/commands/consume_events.py
    severity: low
  - summary: >-
      The consumer has no in-process reconnect for a broker outage; a redis
      ConnectionError ends the loop and the pod relies on Kubernetes restarts
      (CrashLoopBackOff) to recover.
    evidence: |-
      `run_passes` wraps neither `consume` nor `harvest_poison`; a
      redis-broker restart kills every consumer pod once.
    location: >-
      src/shared/packages/django-pyforge/src/django_pyforge/management/commands/consume_events.py
    severity: low
  - summary: >-
      The consume-events Deployment has no liveness probe, so a consumer whose
      Redis socket hangs or whose handler blocks forever is never replaced.
    evidence: |-
      The template states "No probes -- the consumer has no HTTP surface";
      an exec probe on a per-pass heartbeat file would let the Deployment
      self-heal. Parity with the worker Deployment, which the intent asked for,
      is preserved as shipped.
    location: >-
      src/platform/deploy/charts/platform/templates/consume-events-deployment.yaml
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
- [x] Review-pass findings P1–P17 applied (2026-09-03; see Verification § Review pass)
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

### Review pass (2026-09-03) — findings P1–P17 and the test that pins each

- **P1** applied key is per group (`applied:<group>:<event id>`; `applied_key(event_id, group)`) —
  `test_each_group_applies_independently`: doctor consumes a `remedy.requested` first and ACKs it
  untouched; mason's handler still runs.
- **P2** `test_task_receiver_rebinds_traceparent_after_structlog_rebuilds_context` (sends
  `bind_extra_task_metadata` after `clear_contextvars()` for both request shapes) and
  `test_traceparent_from_task_request_reads_both_shapes`; the eager AC-6 test now says what it does and
  does not prove.
- **P3** `EventFabric.consume(..., should_stop=)` checked before each claim/read; `StopFlag` is a
  `threading.Event` whose signal handler only sets it; `run_passes` waits on it (interruptible) —
  `test_run_passes_stops_after_pass_harvests_on_schedule_and_waits_only_when_idle` (stop mid-pass ends
  the loop after that pass; harvest on passes 2 and 4 of `harvest_every=2`; waits only after idle passes).
- **P4** `MemoryRedis` clock is purely logical (starts at 0, moves only by `advance_ms`); no test needs
  wall time on the double (key TTLs still use `time.time()` — they model SET EX).
- **P5** `list_event_dlq` prints `reason/attempts/group/stream_id/quarantined_at/error` before the event —
  extended `test_enumerate_dlq_returns_quarantined_and_empty`.
- **P6** `consume_events` binds via `connect_event_broker(REDIS_BROKER_URL, REDIS_CACHE_URL)` —
  `test_consume_events_binds_the_broker_through_the_ad10_guard`.
- **P7** `CommandError` for a station with no subscriptions (`test_consume_events_command_runs_one_pass_for_station`);
  ungated `test_values_event_consumers_match_subscriptions` ties `events.consumers` to `SUBSCRIPTIONS`.
- **P8** (a) trimmed-while-pending entry: ERROR log with stream_id/group/attempts/error before the ACK —
  `test_exhausted_entry_trimmed_from_stream_is_acked_with_an_error_log` (`MemoryRedis.xdel` added);
  (b) `_pending_rows` raises `TypeError("... must support XPENDING ...")` — `test_broker_without_xpending_is_refused`.
- **P9** `bound_trace` uses `structlog.contextvars.bound_contextvars` inside an `ExitStack`, all under the
  `try/finally` — `test_bound_trace_restores_outer_context_even_when_body_raises`.
- **P10** `backoff_ms` and `handler_timeout_ms` floored at 1 ms — `test_knob_floors_never_reach_zero`.
- **P11** wording: values.yaml/template ("equal to, not derived from"; env vars are process env, not chart
  values), constants.py (adapters check required keys; nothing resolves the URN), README (`quarantined_at`,
  `lasterror:<stream_id>` keys with the applied TTL); `DLQ_QUARANTINED_AT_FIELD` constant.
- **P12** `range $station := uniq …` in the Deployment template and the NetworkPolicy — the `{doctor,doctor}`
  render case in `test_consume_events_follows_values_and_refuses_non_station`.
- **P13** (a) `_free_port()` (kernel-assigned) for the real-redis and durability tests; (b) `MemoryRedis.xclaim`
  raises `DataError` for a bare id or empty list — `test_memory_xclaim_pins_redis_py_list_contract`.
- **P14** `test_entry_already_at_ceiling_is_quarantined_without_a_handler_call` and
  `test_max_attempts_one_quarantines_after_first_failure`.
- **P15** `redact_secrets` on every recorded/quarantined error — `test_recorded_error_redacts_url_userinfo`.
- **P16** `register_adapter` raises `UnregisteredEventTypeError`; `station_handler -> Handler` —
  `test_register_adapter_refuses_unregistered_type`.
- **P17** version `ff` rejected — `test_parse_traceparent_rejects_version_ff_and_zero_ids`.
- Re-run of the spec's Verification (fresh test DB, platform-dev helm + redis-server on PATH):
  `tests/test_cloudevents_redis_broker.py` + `tests/test_chart_invariants.py` — **112 passed / 1 failed**
  (the pre-existing unmarked `test_execute_supervised_run_leaves_no_celery_result_key`); `helm lint`
  0 failed.

## Source

Red-team review: `research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md` (directive and finding ids in the FR/AD line of
`epics.md` Story 42.3). Sprint change proposal:
`sprint-change-proposal-2026-09-02-red-team-high.md`.

## Review Triage Log

### 2026-09-03 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 17: (high 1, medium 4, low 12)
- defer: 6: (high 0, medium 2, low 4)
- reject: 21: (high 0, medium 0, low 21)
- addressed_findings:
  - `[high]` `[patch]` P1 — the applied (idempotency) key was per event id and set before the handler for every group, so with doctor and mason both consuming the one stream the second group ACKed each entry as a duplicate and never ran its handler; key is now scoped by group (`applied:<group>:<event id>`), regression test `test_each_group_applies_independently`.
  - `[medium]` `[patch]` P2 — AC-6's structlog assertion passed by contextvar inheritance under eager Celery, leaving the worker-side rebind receiver and the attribute-form request path unexecuted; added `test_task_receiver_rebinds_traceparent_after_structlog_rebuilds_context` and `test_traceparent_from_task_request_reads_both_shapes`.
  - `[medium]` `[patch]` P3 — SIGTERM was checked only between passes (a pass can run 200 handlers against a 310 s grace), the idle sleep was uninterruptible, and the signal handler logged; `consume(should_stop=)` now stops claiming/reading between entries, `StopFlag` wraps a `threading.Event` (set-only handler, interruptible wait), test `test_run_passes_stops_after_pass_harvests_on_schedule_and_waits_only_when_idle`.
  - `[medium]` `[patch]` P4 — `MemoryRedis` idle times rode `time.monotonic`, making the backoff/no-spin tests load-sensitive; the clock is now purely logical (moves only via `advance_ms`).
  - `[medium]` `[patch]` P5 — `list_event_dlq` printed only the `event` field, hiding `reason`/`error`/`attempts`/`group`/`stream_id`/`quarantined_at`; it now prints the metadata, test extended.
  - `[low]` `[patch]` P6 — `consume_events` built its Redis client directly, bypassing `connect_event_broker`'s AD-10 guard; now goes through it (`test_consume_events_binds_the_broker_through_the_ad10_guard`).
  - `[low]` `[patch]` P7 — a station with no `SUBSCRIPTIONS` entry consumed and ACKed the whole stream while looking healthy, and nothing tied `events.consumers` to `SUBSCRIPTIONS`; the command refuses a non-subscribing station and an ungated parity test was added.
  - `[low]` `[patch]` P8 — an exhausted entry trimmed from the stream was ACKed silently, and `_pending_rows` failed open on a broker without `xpending_range`; now an ERROR log before the ACK and a `TypeError`, both tested.
  - `[low]` `[patch]` P9 — `bound_trace` unbound outer structlog keys instead of restoring them and left the contextvar/OTel attach outside the `finally`; uses `bound_contextvars` under `try/finally`, tested.
  - `[low]` `[patch]` P10 — backoff and handler-timeout knobs accepted 0 (immediate re-claim / harvest stealing live messages); floored at 1 ms, tested.
  - `[low]` `[patch]` P11 — values.yaml/template/constants/README wording claimed chart-settable env knobs, a derived handler timeout, and schema validation that does not exist; reworded, `quarantined_at` documented and given a `DLQ_QUARANTINED_AT_FIELD` constant, `lasterror:` keys documented.
  - `[low]` `[patch]` P12 — a duplicated station in `events.consumers` rendered two Deployments with one name; `uniq` in the Deployment and NetworkPolicy templates, `{doctor,doctor}` render case added.
  - `[low]` `[patch]` P13 — the real-redis tests picked a wall-clock-derived port (parallel collisions) and `MemoryRedis.xclaim` accepted the bare id redis-py rejects; kernel-assigned `_free_port()` and a `DataError`-raising double, tested.
  - `[low]` `[patch]` P14 — the branch quarantining an entry whose XPENDING count is already at the ceiling was untested; added `test_entry_already_at_ceiling_is_quarantined_without_a_handler_call` and `test_max_attempts_one_quarantines_after_first_failure`.
  - `[low]` `[patch]` P15 — recorded handler errors could persist DSN credentials in the never-trimmed DLQ; `redact_secrets()` strips URL userinfo, tested.
  - `[low]` `[patch]` P16 — `register_adapter` raised `PayloadShapeError` for a registration error and `station_handler` was typed `Any`; now `UnregisteredEventTypeError` and `-> Handler`, tested.
  - `[low]` `[patch]` P17 — `parse_traceparent` accepted the W3C-forbidden version byte `ff`; rejected, tested.

## Auto Run Result

Status: done
Blocking condition: none

**Summary of implemented change.** The event fabric now has real delivery semantics: attempts are the XPENDING delivery counter, retries follow an exponential backoff (1 s/2 s/4 s/8 s, capped), a well-formed event is written to the one DLQ with its last error after `EVENT_MAX_ATTEMPTS` and only then ACKed, unparseable entries are quarantined on first sight, and `harvest_poison` defaults its `min_idle_time` to the handler timeout so it never steals a live message. One consumer runner (`manage.py consume_events --station <name>`, consumer group = station token, SIGTERM-graceful between entries) ships as a chart Deployment per station in `events.consumers`, mirroring the worker's image, env, security contexts and volumes. The Warden → Doctor → Mason vocabulary (`recipe.audit.failed`, `remedy.requested`, `recipe.rebuild.requested`, `remedy.completed`) is registered with a dataschema each, adapters route by station subscription, and `traceparent` rides the envelope as a CloudEvents extension, is re-activated around the handler, and is forwarded into Celery headers and structlog context. The review pass's high finding (a per-event idempotency key that silently starved the second consumer group) is fixed with a group-scoped key.

**Files changed.**
- `src/shared/packages/django-pyforge/src/django_pyforge/events/fabric.py` — XPENDING-counted attempts, backoff, DLQ-with-error, group-scoped applied key, `should_stop`, last-error keys, secret redaction, harvest threshold.
- `src/shared/packages/django-pyforge/src/django_pyforge/events/constants.py` — four-type vocabulary + dataschemas, `SUBSCRIPTIONS`, delivery knobs, DLQ field names, `EXT_TRACEPARENT`.
- `src/shared/packages/django-pyforge/src/django_pyforge/events/adapters.py` — per-type domain adapters, `register_adapter`/`adapter_for`, `station_handler`.
- `src/shared/packages/django-pyforge/src/django_pyforge/events/tracing.py` (new) — W3C traceparent parse/carry, `bound_trace`, Celery header helpers.
- `src/shared/packages/django-pyforge/src/django_pyforge/events/memory.py` — logical clock, consumer-filtered `xpending_range`, redis-py-shaped `xclaim`, `xdel`.
- `src/shared/packages/django-pyforge/src/django_pyforge/events/__init__.py` — exports.
- `src/shared/packages/django-pyforge/src/django_pyforge/management/commands/consume_events.py` (new) — the consumer runner.
- `src/shared/packages/django-pyforge/src/django_pyforge/management/commands/list_event_dlq.py` — prints DLQ metadata.
- `src/shared/packages/django-pyforge/src/django_pyforge/tasks.py` — traceparent Celery header + structlog rebind receiver.
- `src/platform/deploy/charts/platform/templates/consume-events-deployment.yaml` (new) — one Deployment per station in `events.consumers`.
- `src/platform/deploy/charts/platform/templates/redis-networkpolicy.yaml`, `templates/_helpers.tpl`, `values.yaml`, `src/platform/deploy/README.md` — consumer admission, fullname helper, `events:` values, docs.
- `src/platform/tests/test_cloudevents_redis_broker.py`, `src/platform/tests/test_chart_invariants.py` — 31 story tests (six ACs, never-clauses, real redis-server, chart invariants, review-pass regressions).
- `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml` (`42-3-… → review`), `specs/spec-pyforge-unifying-strategy/.memlog.md`, this spec.

**Review findings breakdown.** 17 patches applied (1 high, 4 medium, 12 low); 6 deferred (2 medium, 4 low) into the frontmatter `deferred` list; 21 rejected as noise or outside the intent (deterministic-error fast-fail, span-per-hop/tracestate, publish-time schema binding, compose service, station reactions, pass-based harvest cadence, Redis < 7 shapes, and similar). No intent_gap, no bad_spec, no loopback.

**Follow-up review recommendation:** `true` — patched counts high 1, medium 4, low 12; score 3 × 4 + 12 = 24 (≥ 5) and a high-severity patch was applied.

**Verification performed.**
- Spec Verification re-run after the patches (`platform-ci-test` python, `platform-dev` helm + redis-server on PATH, ephemeral postgres, lane1 shim): `tests/test_cloudevents_redis_broker.py` + `tests/test_chart_invariants.py` → **112 passed, 1 failed**; the failure is `test_execute_supervised_run_leaves_no_celery_result_key`, present and failing identically at baseline `1af2ca2b62` (unmarked `django_db`, Story 40.2), untouched by this diff. No skips, so the helm-gated and redis-server-gated tests ran.
- `helm lint src/platform/deploy/charts/platform` → 1 chart linted, 0 failed.
- Full platform suite (implementation agent, fresh DB): 13 failed / 642 passed / 6 skipped / 5 errors — the 18 FAILED/ERROR ids are exactly the pre-existing baseline set (baseline 611 passed + 31 story tests).
- The intent contract has no I/O & Edge-Case Matrix; matrix audit not applicable.

**Residual risks.** See the `deferred` list: CI proves the delivery semantics only against the in-memory double (no `redis-server` in `platform-ci-test`); same-group crash-mid-handler remains at-most-once (A-3, out of scope); the handler timeout is a budget, not an enforced limit; consumer names are pod names (dead consumers accumulate); no in-process broker reconnect and no liveness probe on the consumer Deployment; compose has no consumer service and, with one `REDIS_URL`, the AD-10 guard would refuse one there. The ledger key stays at `review`; `done` follows landing via the marshal's promotion.
