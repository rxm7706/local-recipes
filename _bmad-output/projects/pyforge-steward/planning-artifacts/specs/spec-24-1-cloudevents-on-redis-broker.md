---
title: 'CloudEvents on redis-broker'
type: feature
created: '2026-08-25'
status: done
baseline_commit: 152a0f3cc1c0907b7ae1600c38b70b50af68a13d
baseline_revision: 152a0f3cc1c0907b7ae1600c38b70b50af68a13d
review_loop_iteration: 0
followup_review_recommended: true
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-20-2-media-renditions-and-a-cache-that-cannot-eat-the-queue.md
warnings:
  - oversized
deferred:
  - summary: >-
      Applied-id keys on redis-broker have no TTL, so
      pyforge.events.applied:* grows on a noeviction instance.
    evidence: |-
      EventFabric._mark_applied uses SET NX with no EXPIRE. canopy:AD-10
      binds redis-broker as noeviction. Story 24.1 ACs do not require a
      retention policy for idempotency keys.
    location: >-
      src/shared/packages/django-pyforge/src/django_pyforge/events/fabric.py
    severity: medium
---

<intent-contract>

## Intent

**Problem:** Stations have no durable event backbone. A down consumer drops work, a poison payload can stall a group, and ad-hoc JSON has no identity envelope (canopy:FR-17, canopy:FR-18, canopy:AD-8).

**Approach:** Publish CloudEvents 1.0 onto the existing redis-broker Streams split from Story 20.2. One estate stream and DLQ, consumer groups named by station token, poison harvested with XAUTOCLAIM, envelope identity required except Jira.

## Boundaries & Constraints

**Always:** `XADD` CloudEvents `specversion=1.0` to `pyforge.events` on redis-broker only. DLQ is `pyforge.events.dlq`. Group name is a station token. `dataschema` is required. Envelope carries `specid`, `gitsha`, `sbompurl`; `workitemid` is optional. Missing Jira is not a fail. Idempotency key is CloudEvents `id`. Cite canopy:AD-8 / canopy:AD-10. Specs under `_bmad-output/projects/pyforge-steward/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-steward`. Physical writes only under that slug.

**Block If:** Implementation would re-split Redis, add MinIO, start Liquibase 27-1, or require a live cluster Redis that tests cannot replace with an in-process stream backend.

**Never:** Start 24.2 (loop-depth ceiling, type registry, adapter payload validation). Epic 30. `import pyforge` under `src/platform/`. MinIO. Colon stream keys. Writing events to redis-cache. `scripts/bmad-switch`. `bmad-loop`. Other stations' ledgers.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Consumer down | Group exists; consumer stopped; `XADD` to `pyforge.events` | On return, `XREADGROUP` delivers once; handler runs once | No error |
| No double-apply | Same `id` redelivered pending after apply before ACK | Handler not run again; message ACKed | Idempotent skip |
| Poison harvest | Malformed body (not CloudEvents JSON) pending on the group | `XAUTOCLAIM` on `pyforge.events` then `XADD` to `pyforge.events.dlq`; group reads next | Original ACKed after DLQ |
| Enumerate DLQ | One or more quarantined messages | Operator list returns those stream entries | Empty list if none |
| Broker only | Distinct broker vs cache clients | Producer `XADD` only on broker; cache `XADD` count stays 0 | Same URL → refuse connect |
| dataschema required | Publish without `dataschema` | Producer raises; stream unchanged | Fail the producer, not the group |
| Jira optional | Publish with `specid`/`gitsha`/`sbompurl`, no Jira, no `workitemid` | Event is on the stream | Must not drop or raise |

</intent-contract>

## Code Map

- `src/shared/packages/django-pyforge/src/django_pyforge/events/__init__.py` -- public: constants, `EventFabric`, `connect_event_broker`, `list_quarantined`
- `src/shared/packages/django-pyforge/src/django_pyforge/events/constants.py` -- `STREAM=pyforge.events`, `DLQ=pyforge.events.dlq`, station tokens, CE extension names (`specid`, `gitsha`, `sbompurl`, `workitemid`)
- `src/shared/packages/django-pyforge/src/django_pyforge/events/memory.py` -- in-process Streams (`xadd`/`xgroup_create`/`xreadgroup`/`xack`/`xautoclaim`/`xrange`) for tests; no live Redis
- `src/shared/packages/django-pyforge/src/django_pyforge/events/fabric.py` -- produce structured CloudEvents JSON in field `event`; consume with applied-id SET on the same broker; harvest poison via `XAUTOCLAIM` then DLQ
- `src/shared/packages/django-pyforge/src/django_pyforge/management/commands/list_event_dlq.py` -- operator enumerate (injectable client)
- `src/platform/tests/test_cloudevents_redis_broker.py` -- NEW: full I/O matrix; cache-spy; no `import pyforge`
- `src/platform/tests/test_chart_invariants.py` -- read-only: redis-cache vs redis-broker already split (do not re-split)
- `src/platform/platformapp/front_door/lane1_runtime.py` -- read-only URL helpers; do not retarget Celery onto cache
- `src/platform/config/settings/base.py` -- read-only `REDIS_BROKER_URL` / `REDIS_CACHE_URL`
- Never: `src/platform/**` importing `pyforge.*`; type registry / `pyforgeloopdepth` ceiling (24.2)

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/django-pyforge/src/django_pyforge/events/` -- CloudEvents producer, group consumer, DLQ harvest, memory backend
- `src/shared/packages/django-pyforge/src/django_pyforge/management/commands/list_event_dlq.py` -- operator list
- `src/platform/tests/test_cloudevents_redis_broker.py` -- matrix + broker-only spy

**Acceptance Criteria:**
- Given a consumer that is down, when an event is `XADD`ed to `pyforge.events`, then it is delivered on return without double-apply.
- Given a malformed event, when harvested, then it lands in `pyforge.events.dlq` via `XAUTOCLAIM` and does not block the group.
- Given quarantined messages, when an operator enumerates, then those messages are listed.
- Given producers, when they publish, then they never write to redis-cache and `dataschema` is required.
- Given the envelope, when published, then it carries `spec_id`, git sha, and SBOM purl, plus an optional work-item id; a missing Jira key is not a fail.

## Spec Change Log

## Review Triage Log

### 2026-08-25 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 0, medium 4, low 1)
- defer: 1: (high 0, medium 1, low 0)
- reject: 18
- addressed_findings:
  - `[medium]` `[patch]` harvest test spies `xautoclaim` on `pyforge.events` and asserts the PEL is empty after DLQ
  - `[medium]` `[patch]` publish with `workitemid` lands that extension on the stream
  - `[medium]` `[patch]` applied-id `SET NX` before the handler; handler failure deletes the key
  - `[medium]` `[patch]` well-formed claims are `XCLAIM`ed back to the original consumer
  - `[low]` `[patch]` `connect_event_broker` constructs only the broker client

## Design Notes

Wire names are CloudEvents extensions (lowercase letters/digits only): product `spec_id` → `specid`, git sha → `gitsha`, SBOM purl → `sbompurl`, work-item → `workitemid`. Do not emit a `jira` attribute. Stream field is one JSON object (`specversion`, `id`, `source`, `type`, `dataschema`, extensions). Applied keys: `pyforge.events.applied:<id>` on the broker. Harvest: `XAUTOCLAIM` on `pyforge.events` (not the DLQ key); destination of the claim is `pyforge.events.dlq`. Event `type` in tests may be any dotted string — registry is 24.2.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

Summary: CloudEvents 1.0 fabric on redis-broker Streams (`pyforge.events` / `pyforge.events.dlq`) in `django_pyforge.events`, with consumer-group delivery, applied-id idempotency, XAUTOCLAIM poison harvest, and operator DLQ list.

Files changed:
- `django_pyforge/events/*` -- produce/consume/harvest + in-process Streams
- `django_pyforge/management/commands/list_event_dlq.py` -- enumerate DLQ
- `src/platform/tests/test_cloudevents_redis_broker.py` -- I/O matrix
- this spec

Review: 5 patches applied, 1 deferred (applied-key TTL), 18 rejected (24.2, live Redis, AD-8 harvest-on-DLQ-key vs story AC, retry-budget numeric, URL aliases). Follow-up recommended: true (medium 4, low 1; score 13).

Verification: `pixi run -e platform-ci-test pytest src/platform/tests/test_cloudevents_redis_broker.py src/platform/tests/meta/test_no_pyforge_import.py -q` → 8 passed.

Residual: MemoryRedis is a test subset; `list_event_dlq` live `from_url` path untested; no station adapters yet (24.2).
