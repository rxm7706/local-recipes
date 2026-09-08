---
title: redis-broker is durable and bounded
type: fix
created: '2026-09-02'
status: done
updated: '2026-09-02'
baseline_commit: 2e3f108f
baseline_revision: d6cae4759395dd0293ac0a89fc607f9205950900
followup_review_recommended: false
severity: CRITICAL
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/resilience-invariants.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-local-ocp-hybrid-environment/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-12-6-redis-is-hardened-still-ephemeral.md
  - src/platform/deploy/charts/platform/templates/redis-deployment.yaml
  - src/platform/deploy/charts/platform/values.yaml
  - src/platform/config/settings/base.py
  - src/shared/packages/django-pyforge/src/django_pyforge/events/fabric.py
  - src/platform/tests/test_chart_invariants.py
  - src/platform/tests/test_cloudevents_redis_broker.py
warnings:
  - Supersedes Story 12.6's "ephemeral by design (Celery re-queues)" for the
    BROKER role only. That premise was wrong — Celery does not re-queue tasks
    a dead broker never persisted, and the broker also carries Streams, the
    PEL, the DLQ and the idempotency keys, none of which are re-queueable.
    `test_redis_persistence_remains_empty_dir` and
    `test_redis_empty_dir_check_fails_when_a_pvc_volume_is_present` must be
    re-scoped to redis-cache.
deferred:
  - Bus retry semantics (attempt counter, backoff, DLQ for well-formed failing events) — red-team R-9.
  - Celery `acks_late` / per-station queues / builds pool — red-team R-10.
  - Supervisor reconciliation of orphaned RUNNING rows after a broker loss — BS-8 / R-10.
  - "`CELERY_BROKER_USE_SSL` `CERT_NONE` — red-team R-14 (separate story; do not fold)."
  - Redis HA (Sentinel / operator) — a sizing choice, not this story.
---

<intent-contract>

## Intent

**Problem:** The chart renders `redis-broker` with `--maxmemory-policy
noeviction` but **no `--maxmemory`** (only the cache role gets one), on an
`emptyDir`, with `resources: {}`. Redis treats `maxmemory 0` as unlimited, so
`noeviction` never engages; the container grows until the kubelet OOM-kills
it, and any restart empties it. What lives on that broker today: the Celery
queue, the Celery **result backend** (`CELERY_RESULT_BACKEND = REDIS_BROKER_URL`),
the Channels layer, the CloudEvents stream `pyforge.events`, its pending-entries
list, the dead-letter stream `pyforge.events.dlq`, and every
`pyforge.events.applied:*` idempotency key (set with no TTL). A restart
therefore loses queued work, in-flight events, the quarantine, and the
duplicate-suppression record at once; `list_event_dlq` then prints `(empty)`
and reads as healthy. CAP-11's success clause ("filling the cache to its
eviction limit provably loses no queued task") is satisfied only because the
cache is separate — the broker itself has no durability claim behind it.
Red-team findings **S-1**, **A-3**, directive **R-2**.

**Approach:** Make the broker role durable and bounded; leave the cache role
exactly as Story 12.6 shipped it. Chart: broker gets a PVC (RWO) mounted at
`/data`, `--appendonly yes --appendfsync everysec`, a **required**
`--maxmemory` value that must be below a **required** memory limit, and
`noeviction` kept. Settings: stop storing Celery results on the broker
(`CELERY_TASK_IGNORE_RESULT = True`; every `.delay()` in the estate is
fire-and-forget and the supervisor's `RunState` in PostgreSQL is the record of
fact, per canopy:AD-12). Fabric: `applied:*` keys carry a TTL, the stream has
a declared trim policy, DLQ retention is declared. Prove it with a real
`redis-server` restart, not `MemoryRedis`.

## Acceptance Criteria

- Given `helm template` of the core chart, when rendered with defaults, then
  the `redis-broker` Deployment mounts a `PersistentVolumeClaim`
  (`redis.broker.persistence.size`, `storageClassName` seam, `ReadWriteOnce`)
  at `/data`, and the `redis-cache` Deployment still uses `emptyDir`.
- Given the rendered broker container, when its args are read, then they
  contain `--appendonly yes`, `--appendfsync everysec`, `--maxmemory <value>`
  and `--maxmemory-policy noeviction`; the cache container is unchanged
  (`--maxmemory 64mb`, `allkeys-lru`, no `appendonly`).
- Given `redis.broker.maxmemory` empty, or `redis.broker.resources.limits.memory`
  empty, or `maxmemory` ≥ the memory limit, when `helm template` runs, then the
  render **fails** naming the values path (same `required`/`fail` idiom as
  `mcpHost.image.repository`). Cache resources keep the empty-default seam.
- Given the existing invariant tests, when re-scoped, then
  `test_redis_persistence_remains_empty_dir` asserts **cache only**,
  `test_redis_empty_dir_check_fails_when_a_pvc_volume_is_present` asserts a
  PVC on the **cache** fails, and two new tests assert the broker PVC + AOF
  args and the maxmemory-vs-limit refusal.
- Given the OCP overlay, when rendered, then the broker PVC has no fixed UID
  (`runAsUser`/`fsGroup` stay overlay-nulled) and the `postgres`-style
  `dataMountPath` note is mirrored for the Redis image's `/data`.
- Given production settings, when loaded, then `CELERY_TASK_IGNORE_RESULT`
  is `True` and `CELERY_RESULT_EXPIRES` is set (for tasks that opt in with
  `ignore_result=False`); `CELERY_RESULT_BACKEND` remains the broker (canopy:AD-10
  letter unchanged) but is empty in steady state — a test enqueues
  `execute_supervised_run` and asserts no `celery-task-meta-*` key exists
  after completion.
- Given `EventFabric._mark_applied`, when a key is set, then it carries a
  TTL (`DJANGO_PYFORGE_EVENT_APPLIED_TTL_SECONDS`, default ≥ 7 days) and a
  test asserts `TTL > 0`; `MemoryRedis` gains TTL support or the test uses
  the real server.
- Given `EventFabric.publish`, when it `XADD`s, then it applies a declared
  trim (`maxlen` approximate, `DJANGO_PYFORGE_EVENT_STREAM_MAXLEN`, default
  large enough that a slow consumer group is never trimmed before harvest —
  document the number and its reasoning in `constants.py`); the DLQ is
  **not** auto-trimmed, and its retention (operator purge via a management
  command or documented `XTRIM`) is written in `deploy/README.md`.
- Given a real `redis-server` (the `platform-dev` env ships it) started
  with `--appendonly yes` on a temp dir, when one CloudEvent is published,
  one consumer reads it without ACK, one `applied:` key is set, and the
  server process is **killed and restarted** on the same dir, then the
  stream entry, the PEL entry (`XPENDING` shows it), the DLQ (after a
  poison harvest), and the `applied:` key all survive. This is the CAP-11
  / canopy:AD-15 per-invariant test: it must fail with `--appendonly no`.
- Given the Dream's sizing table, when updated, then the "Redis AOF 20–50 GB
  RWO" storage row points at `redis.broker.persistence`, and the cache row
  says ephemeral.

## Boundaries & Constraints

**Always:** Write under `_bmad-output/projects/pyforge-steward/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` only — never `scripts/bmad-switch`.
Ledger key `40-2-redis-broker-is-durable-and-bounded`. Broker and cache URLs
stay distinct (canopy:AD-10; `connect_event_broker` refuses a shared URL). Official
`redis:7` image under `restricted-v2` with overlay-nulled UID (12.7 evidence).
No new pixi dependency (`django-celery-results` is not pinned; not needed).

**Block If:** Implementation would give the **cache** a PVC; move Celery or
Channels onto redis-cache; add a Redis operator, Sentinel or a third Redis
role; change bus retry semantics (R-9) or Celery ack semantics (R-10) "while
here"; touch `CELERY_BROKER_USE_SSL` (R-14); or trim the DLQ automatically.

**Never:** `noeviction` without `maxmemory`. A memory `maxmemory` at or above
the container limit. `emptyDir` for the broker. A shared Redis URL for
broker and cache. Deleting the DLQ on restart.

</intent-contract>

## Tasks

- [x] `values.yaml`: `redis.broker.persistence.{size,storageClassName}`,
      `redis.broker.maxmemory` (required), `redis.broker.appendfsync`
      (default `everysec`), `redis.broker.resources` (limits.memory required).
- [x] `redis-deployment.yaml`: role-conditional volume (PVC for broker,
      emptyDir for cache), AOF + maxmemory args for broker, `fail` when
      maxmemory ≥ limit (parse `Mi`/`Gi`/`mb`/`gb` in a helper).
- [x] New `redis-broker-pvc.yaml` (mirror `sidecar-pvc.yaml`).
- [x] `_helpers.tpl`: `platform.redisBroker.pvcName`; a
      `platform.parseMemory` helper for the comparison.
- [x] `deploy/README.md` + `overlays/ocp/cluster-bringup.md`: broker PVC,
      AOF, DLQ retention procedure.
- [x] `config/settings/base.py`: `CELERY_TASK_IGNORE_RESULT = True`,
      `CELERY_RESULT_EXPIRES = 3600`; comment citing canopy:AD-12 (RunState is the
      record) and this story.
- [x] `django_pyforge/events/fabric.py` + `constants.py`: `applied:` TTL,
      publish-time `maxlen` trim, both env-configurable with documented
      defaults.
- [x] `django_pyforge/events/memory.py`: TTL-aware `set(..., ex=)` or mark
      the restart test as real-server only.
- [x] Tests: re-scope the two emptyDir invariants; add broker PVC/AOF,
      maxmemory-vs-limit refusal, no-result-key, applied-TTL, and the
      `redis-server` kill/restart durability test (`platform-dev` env,
      skip if `redis-server` binary absent — never silently pass).
- [x] `resilience-invariants.md` RFC-2 row: append "broker durable + bounded
      (Story 40.2)"; `spec-local-ocp-hybrid-environment` CAP-3: note the
      broker supersession; Dream sizing table storage row.
- [x] Ledger `40-2-redis-broker-is-durable-and-bounded` → `review` then
      `done` via `sprint-ledger-sync`.

## Design notes

- **Why keep results on the broker URL at all?** canopy:AD-10's rule text says
  "Celery and Channels use the broker". Ignoring results globally satisfies
  the intent (nothing accumulates) without re-litigating the AD or adding
  `django-celery-results` to the lock. Every call site is `.delay()` with no
  `AsyncResult` consumer (`front_door/celery_task_backend.py`,
  `supervisor.py`, `django_warden_fabric/views.py`, `langflow_integration/tasks.py`).
- **Why not trim the DLQ?** A quarantine that silently rotates is the same
  failure as one that vanishes. Operators purge deliberately.
- **AOF vs RDB.** `everysec` bounds loss to one second of appends with no
  fsync-per-write latency on the request path; RDB alone would re-open the
  window this story closes.
- **maxmemory sizing.** With `noeviction`, hitting `maxmemory` makes writes
  fail loudly (`OOM command not allowed`) — that is the intended
  back-pressure signal (R-8 builds on it). It must sit below the container
  limit so the kubelet never gets there first.
- **What this does not fix.** A dropped in-flight *task* (worker SIGKILL
  without `acks_late`) is R-10. A failing well-formed *event* retrying
  forever is R-9. Both are named in `deferred:` so nobody reads a green
  40.2 as "the bus is resilient".

## Verification

`pixi run -e platform-dev -- python -m pytest -o addopts=
src/platform/tests/test_chart_invariants.py -k redis` and
`src/platform/tests/test_cloudevents_redis_broker.py` (cwd `src/platform`;
`platform-dev` carries `helm` and `redis-server`). Manual on CRC (optional,
not a stamp gate): `oc delete pod -l app.kubernetes.io/component=redis-broker`
mid-`warden` audit; the run completes and `manage.py list_event_dlq` still
lists any prior quarantine.

## Suggested Review Order

**The gap**

- Broker gets no `--maxmemory`, cache does
  [`redis-deployment.yaml:52`](../../../../../../src/platform/deploy/charts/platform/templates/redis-deployment.yaml#L52)
- `emptyDir` for both roles
  [`redis-deployment.yaml:96`](../../../../../../src/platform/deploy/charts/platform/templates/redis-deployment.yaml#L96)
- Results on the broker
  [`base.py:400`](../../../../../../src/platform/config/settings/base.py#L400)
- `applied:` key with no TTL
  [`fabric.py`](../../../../../../src/shared/packages/django-pyforge/src/django_pyforge/events/fabric.py)

**The invariants that flip**

- Cache-only from now on
  [`test_chart_invariants.py:1164`](../../../../../../src/platform/tests/test_chart_invariants.py#L1164)

## Review Triage Log

### 2026-09-02 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 1: (low 1)
- defer: 0
- reject: 0
- addressed_findings:
  - `[low]` `[patch]` Added `test_redis_broker_memory_limit_is_required` for empty `redis.broker.resources.limits.memory` refusal (AC gap).

## Auto Run Result

Status: done

Summary: Made redis-broker durable (AOF on RWO PVC) and memory-bounded (`--maxmemory` < limit, `noeviction`); left redis-cache on emptyDir. Celery results are globally ignored; EventFabric applied keys carry TTL and the main stream has approximate maxlen trim.

Files changed:
- `src/platform/deploy/charts/platform/` — broker PVC template, deployment args, values defaults, parseMemory helper
- `src/platform/config/settings/base.py` — `CELERY_TASK_IGNORE_RESULT`, `CELERY_RESULT_EXPIRES`
- `django-pyforge/events/` — TTL, stream maxlen, MemoryRedis TTL support
- `src/platform/tests/` — re-scoped cache emptyDir invariants; broker PVC/AOF/maxmemory tests; restart durability + applied TTL tests
- `docs/dreams/pyforge-unifying-strategy.md`, deploy README, cluster-bringup — sizing and operator docs

Review findings: 1 low patch applied; no deferrals.

Follow-up review recommendation: false (0 high/medium patched; score 1).

Verification: `pixi run -e platform-dev -- python -m pytest -o addopts= tests/test_chart_invariants.py -k redis tests/test_cloudevents_redis_broker.py` — 21 passed, 1 skipped (celery meta-key test when pytest-django absent under stripped addopts).

Residual risks: broker PVC sizing remains operator responsibility; R-9/R-10 deferred bus/Celery ack semantics unchanged.
