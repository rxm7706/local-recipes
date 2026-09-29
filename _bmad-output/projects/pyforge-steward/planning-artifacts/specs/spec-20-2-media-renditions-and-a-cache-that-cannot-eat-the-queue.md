---
title: Media, renditions, and a cache that cannot eat the queue
type: feature
created: '2026-08-24'
status: done
updated: '2026-08-25'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-20-1-wagtail-publishes-without-a-deploy.md
warnings:
  - oversized
baseline_revision: 4d816a6dbcfd543cc509c5fca21c19adae0dffd9
review_loop_iteration: 0
followup_review_recommended: false
deferred: []
---

<intent-contract>

## Intent

**Problem:** Lane 1 (Wagtail at `/`) stores media on pod-local `MEDIA_ROOT` and shares one Redis for cache and Celery. Scaling replicas loses uploads; filling the cache can evict queued work (canopy:FR-8, canopy:FR-30, canopy:AD-13, canopy:AD-10, NFR-C7).

**Approach:** Mount a ReadWriteMany PVC for Django filesystem media. Split Redis into `redis-cache` (evicts) and `redis-broker` (does not). Renditions use the `renditions` cache alias. Wagtail `django_tasks` runs on an in-tree Celery `BaseTaskBackend`. Independent work scale remains the existing Celery worker Deployment.

## Acceptance Criteria

- Given a ReadWriteMany PVC for Wagtail media and two Redis Deployments, when replica A stores an upload, then replica B retrieves it.
- Given a rendition generated on A, when B serves it, then it comes from redis-cache without regeneration.
- Given redis-cache filled to eviction, when a task is queued on redis-broker, then that queued task is not lost.
- Given host settings, when inspected, then Celery and Channels use the broker; Django cache and Wagtail renditions use the cache.
- Given the chart, when scaled, then independent work is a Celery worker Deployment — not a second public ASGI process.
- Given Lane 1 state, when pods restart, then no media/rendition/page payload lives only on ephemeral pod disk; MinIO/S3 in the chart is a review-blocking finding.
- Given search and background work, when configured, then search is PostgreSQL FTS and Wagtail tasks use the in-tree Celery `BaseTaskBackend` (not django-tasks DB/RQ, not `django-tasks-celery`).

## Boundaries & Constraints

**Always:** Lane 1 stays at `/`. Physical writes under `_bmad-output/projects/pyforge-steward/`. `BMAD_ACTIVE_PROJECT=pyforge-steward`. Media is Django `FileSystemStorage` on RWX PVC. Two Redis Deployments, same image class. `CELERY_*` and `CHANNEL_LAYERS` → broker; `CACHES['default']` and `CACHES['renditions']` → cache. Worker Deployment already in-tree is the scale unit. Cite canopy:AD-13 / canopy:AD-10 vs parent AD-1 (still Redis-the-kind).

**Block If:** Shared storage cannot be a PVC (cluster has no RWX) and the only proposed substitute is MinIO/S3; or platform-ci-test cannot import `django_tasks` / Wagtail images.

**Never:** MinIO/S3; Elasticsearch; Epic 30 console deletion; absorb `spec-wagtail-corporate-brain`; `import pyforge.*` under `src/platform/`; start Story 21.1; a second public ASGI process; PyPI `django-tasks-celery`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Shared upload | Replica A saves a file under MEDIA_ROOT on RWX | Replica B reads the same bytes from that path | Missing file fails the test |
| Rendition cache | Rendition created on A; DB row deleted | B `get_rendition` is cache-hit (`_from_cache`); generate not required | Cache miss would regenerate — fail |
| Cache eviction | Helm redis-cache `allkeys-lru`; broker `noeviction`; distinct URLs | Filling cache policy cannot apply to broker keys | Shared URL fails the test |
| Role split | Settings / djangoEnv | Celery+Channels broker URLs; CACHES+renditions cache URLs | Cross-wire fails |
| Worker scale | Chart | Worker args are `celery … worker`; no worker Service/Ingress/port 8000 | Extra ASGI fails |
| Forbidden infra | Chart + settings | No minio/s3/elasticsearch; TASKS backend is in-tree Celery class | Review-blocking |
| FTS + tasks | Settings | `wagtail.search.backends.database`; TASKS not DB/RQ/`django-tasks-celery` | Wrong backend fails |

</intent-contract>

## Code Map

- `src/platform/config/settings/base.py` — `REDIS_BROKER_URL` / `REDIS_CACHE_URL`; `CELERY_BROKER_URL` + result backend on broker; locmem `CACHES` with `renditions`; `TASKS` → in-tree backend; `MEDIA_ROOT` from env; keep PostgreSQL FTS
- `src/platform/config/settings/production.py` — RedisCache aliases on cache URL; `CHANNEL_LAYERS` on broker URL
- `src/platform/config/settings/local.py` — locmem `renditions` alias (do not drop it)
- `src/platform/config/settings/test.py` — `CELERY_TASK_ALWAYS_EAGER` so the Celery backend runs in-process
- `src/platform/config/urls.py` — mount `wagtail.images` / `wagtail.documents` serve URLconfs (20.1 deferred this)
- `src/platform/platformapp/front_door/lane1_runtime.py` — **new** URL/cache/channel helpers (testable without production secrets)
- `src/platform/platformapp/front_door/celery_task_backend.py` — **new** `CeleryTaskBackend(BaseTaskBackend)`
- `src/platform/platformapp/front_door/tasks.py` — **new** Celery `run_django_task` used by the backend
- `src/platform/deploy/charts/platform/templates/` — split redis Deployments/Services/NetworkPolicies; media RWX PVC; mount on web+worker; djangoEnv URLs
- `src/platform/deploy/charts/platform/templates/_helpers.tpl` — `redisCache`/`redisBroker`/`media` names; djangoEnv `REDIS_*` + `MEDIA_ROOT`
- `src/platform/deploy/charts/platform/values.yaml` — `media` + redis cache/broker policy knobs
- `src/platform/tests/test_chart_invariants.py` — two Redis components; two PVCs; worker not public ASGI; no minio/s3
- `src/platform/tests/test_media_renditions_cache.py` — **new** matrix tests
- Helm `redis-deployment.yaml` — currently one Deployment, emptyDir, no maxmemory-policy
- `CACHES` today in production.py uses single `REDIS_URL` (same as Celery) — the bug this story splits

## Tasks & Acceptance

**Execution:**
- `src/platform/platformapp/front_door/lane1_runtime.py` — broker vs cache helpers
- `src/platform/platformapp/front_door/celery_task_backend.py` + `tasks.py` — in-tree Celery `BaseTaskBackend`
- `src/platform/config/settings/{base,local,production,test}.py` — split URLs, caches, TASKS, eager Celery in tests
- `src/platform/config/urls.py` — image/document serving
- `src/platform/deploy/charts/platform/` — RWX media PVC; redis-cache vs redis-broker; env wiring
- `src/platform/tests/test_chart_invariants.py` — update 12.6 redis uniqueness; add 20.2 proofs
- `src/platform/tests/test_media_renditions_cache.py` — I/O matrix

**Acceptance Criteria:**
- Given RWX + two Redis, when A writes media, then B reads it.
- Given a cached rendition, when B fetches it, then no regeneration.
- Given cache eviction policy, when broker has a queued task, then it survives.
- Given settings, when loaded, then Celery/Channels = broker and Django/Wagtail renditions = cache.
- Given the chart, when inspected, then work scales via the Celery worker Deployment only.
- Given templates/settings, when scanned, then no MinIO/S3/Elasticsearch and no django-tasks DB/RQ/`django-tasks-celery`.

## Spec Change Log

## Review Triage Log

### 2026-08-24 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 1, medium 1, low 1)
- defer: 5: (high 1, medium 3, low 1)
- reject: 4
- addressed_findings:
  - `[high]` `[patch]` Langflow `LANGFLOW_REDIS_URL` defaults to `REDIS_CACHE_URL`, not the broker alias
  - `[medium]` `[patch]` Redis DNS names truncate the release prefix so `-cache`/`-broker` cannot collide
  - `[low]` `[patch]` gitignore `platformapp/media/` so test uploads cannot be committed
- deferred:
  - locmem rendition test cannot delete the ORM row and still unpickle a Rendition; helm `allkeys-lru` vs `noeviction` is the eviction proof
  - RWX StorageClass and restricted-v2 writable PVC (no fsGroup) are cluster overlays
  - compose still a single Redis for local-dev; chart is the deployed contract
  - `transaction.on_commit` around Celery enqueue
  - live two-process redis-cache round-trip

## Design Notes

Wagtail 7.4 `AbstractRendition.cache_backend` uses `caches["renditions"]` when that alias exists. Do not set `WAGTAILIMAGES_RENDITION_STORAGE` to S3.

Broker `maxmemory-policy noeviction`; cache `allkeys-lru` plus `--maxmemory`. Same Redis image. Parent AD-1: still Redis, two Deployments.

`django_tasks` default is `ImmediateBackend`. Replace with in-tree Celery backend; workers execute `run_django_task` which `import_string`s the original callable (if the name resolves to a `Task`, call `.call()`).

Do not absorb corporate-brain REST. Do not add supervisor tables (21.1).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `4dc8d8abda` (2026-08-24, "Merge pull request #760 from rxm7706/steward/20-2-ledger-finalize"); also `5c6764d9f5` (2026-08-24, "Merge pull request #759 from rxm7706/steward/20-2-media-renditions-and-a-cache-that-cannot"). Ledger row `20-2-media-renditions-and-a-cache-that-cannot-eat-the-queue: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `.cursor/pyforge-fleet-drain/queues.yaml`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
