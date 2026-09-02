---
title: Architecture Review Report — PyForge Unifying Strategy (Red Team)
type: research
kind: adversarial-architecture-review
subject: docs/dreams/pyforge-unifying-strategy.md
project: pyforge-steward
date: 2026-09-02
reviewer: Claude (Principal Enterprise Architect / Staff Security Engineer / Autonomous AI Systems lens)
status: delivered
verdict: CONDITIONAL — viable as a modular monolith; NOT production-viable until the CRITICAL and HIGH directives below land
---

# Architecture Review Report — PyForge Unifying Strategy

> **Disposition (2026-09-02).** Operator chose option 1. R-1 → steward Story **40.1**, R-2 → Story **40.2**
> (`sprint-change-proposal-2026-09-02-red-team-critical.md`, Epic 40, `ready-for-dev`). R-3 … R-25 await a
> second correct-course after Epic 40 lands.

**Scope.** Adversarial review of `docs/dreams/pyforge-unifying-strategy.md` (2,092 lines,
2026-09-01 revision) through six lenses: topology, deployment/state, security, agentic
fabric, monorepo/dependencies, blind spots. The Dream's own rule is that **Grounding wins
over the architecture prose**, so every finding is graded against the *living* topology
(one ASGI hub, eight station packages, Celery, PostgreSQL, two Redis roles, DuckDB query
plane) and cross-checked against the shipped code in `src/platform/`,
`src/shared/packages/django-pyforge/`, the Helm chart, and `pixi.toml`/`pixi.lock`.
Where the review prompt's premise (nine FastAPI `:800x` services, dual-headed `/mcp/sse`,
isolated Vizro containers, MinIO, Vault-in-app, 16–32 vCPU) is the **historical**
topology the document itself says not to build, that is stated and the living shape is
reviewed instead.

Every claim below cites a file so it can be verified or refuted. Severity: **CRITICAL**
(exploitable or data-losing today), **HIGH** (breaks the stated contract under normal
production load), **MEDIUM** (degrades or blocks scale-out), **LOW** (doc or hygiene).

---

## 1. Executive Summary

**Verdict: the strategy is viable — the document is not.**

The living architecture (a Django/Wagtail ASGI hub that mounts eight station packages,
pushes heavy work to Celery, keeps PostgreSQL + Redis as the only infra kinds, and treats
DuckDB as a library) is a sound, deliberately boring modular monolith. The 2026-08-24
Grounding and the SPEC's `resilience-invariants.md` already killed the worst ideas
(process-per-station, HMAC shared secrets, PyBreaker-async, Vault-in-app, `/mcp/sse`).
That correction work is of unusually high quality and is the strongest part of this
effort.

Three things stop it being production-viable today:

1. **The identity delegation chain is forgeable.** `POST /assertion/mint/` on the host is
   `csrf_exempt` and mints a host-signed RS256 station assertion from a bearer whose
   **signature, issuer, audience and expiry are never checked** — the payload is
   base64-decoded and its `sub`/`groups` are trusted verbatim
   (`django_pyforge/assertion/identity.py`, `views.py`). Anyone who can reach the host
   becomes any subject with any roles for any station. Everything downstream (supervisor
   `start`, role-sliced Lane 3 rows, MCP tool leasing) rests on this. **CRITICAL.**
2. **The "no-loss" broker is an `emptyDir` with no memory ceiling.** `redis-broker` runs
   `noeviction` with **no `maxmemory`** on ephemeral storage, no resource limits, and it
   also carries the Celery result backend, Channels layer, the event stream, the PEL, the
   DLQ, and the idempotency keys. A pod restart deletes every queued task, every event,
   and the dead-letter queue; unbounded growth OOM-kills it first. **CRITICAL.**
3. **The document actively misleads an implementer.** Roughly 60 % of the file is
   "historical, do not build" prose that still reads as instruction (nine `:800x`
   services, `pyforge.core.client` calling `/api/v1/compliance/check` — a path the shipped
   ASGI router hands to **Langflow**, not Warden). The authoritative content is a
   Grounding section that overrides the diagrams beneath it. An architecture that can
   only be read correctly by people who already know what is wrong with it is not a
   specification. **HIGH.**

Beneath those: the query plane's single-writer DuckDB **file** cannot be shared across
pods without RWX storage DuckDB does not support; the event fabric has a producer, one
registered event type, and **no deployed consumer**, so the Warden→Doctor scenario is not
wired; retries on the bus are infinite with no backoff and a well-formed-but-failing event
can never reach the DLQ; the platform image runs **Python 3.12** while Atlas/Doctor
declare `>=3.14`, so the "100 % parity" claim fails at the interpreter; and nothing on the
host rate-limits an agent, so a runaway MCP loop is a platform-wide denial of service.

None of these are hard problems. All of them must be closed **before** the Phase 0–6
cutover to `python-foundry` copies them into the lasting repo.

---

## 2. Systemic Risks & Bottlenecks

### Lens 1 — Topological feasibility and the "dual-headed" design

**Premise correction.** The dual-headed FastAPI (REST + `/mcp/sse`) pattern and Layer-5
compute services are historical. Living: one gunicorn/uvicorn process serving Django,
Wagtail, **Langflow's entire FastAPI app**, a FastAPI seam, station MCP faces (in-process
or proxied to an `mcp-host` sidecar), and a Channels WebSocket stub
(`src/platform/config/asgi.py::_dispatch_http`).

| # | Finding | Severity | Evidence |
|---|---|---|---|
| T-1 | **Langflow shares the host event loop and lifespan.** A blocking call, a slow lifespan, or an OOM inside Langflow takes down Guildhall, every portal and every MCP face. The Dream already records one such outage (boot-time `a2a_checkpoints` DDL crashed the web process). Blast radius of the hub is "everything". | HIGH | `asgi.py` mounts `langflow_application` and drives its lifespan in the same `AsyncExitStack` as the platform stub and MCP apps. |
| T-2 | **`/api/v1/*` belongs to Langflow, not to stations.** The router forwards any `/api/v1` path to Langflow before the FastAPI seam sees it. The Dream's client SDK example (`client.post("/api/v1/compliance/check")`) would hit Langflow's router. There is no versioned station API namespace at all. | HIGH | `asgi.py::_is_langflow_api_v1_path`; Dream § 5 "Shared Data Contracts". `pyforge.core.client` does not exist (`pyforge/core/` has no `client.py`; the Dream's own 2026-08-24 log confirms). |
| T-3 | **Lane 2 → compute is a self-request over loopback.** Portals are "zero-model HTMX clients" that call "the host" over `httpx`. The host *is* the same gunicorn pool. Under load a worker awaits a worker; with `ATOMIC_REQUESTS = True` every such view holds an open PostgreSQL transaction while it waits. This is the classic self-call deadlock/latency amplifier, not the "sub-millisecond inner loop" the LocalStack section promises. | HIGH | `config/settings/base.py:86` (`ATOMIC_REQUESTS`), Dream § Django Reusable Apps § 2. |
| T-4 | **MCP dispatch bypasses every Django middleware.** `dispatch_station_mcp` runs first in `_dispatch_http`, before sessions, CSRF, allauth, `TokenRolesMiddleware` and `AssertionMiddleware`. Authorization exists only *inside* tools that route through the supervisor (`verify_assertion` in `supervisor.py`). `initialize`, `tools/list`, and any tool not wired through the supervisor are anonymous. | HIGH | `asgi.py:130`; `django_pyforge/mcp_dual_era.py` contains no auth handling (0 matches for bearer/authorization). |
| T-5 | **The sidecar proxy is a 5-second, fully-buffered, header-forwarding hop.** `proxy_station_mcp` uses `httpx.AsyncClient(timeout=5.0)`, reads `response.content` (no streaming — Streamable HTTP SSE bodies are buffered to completion), and forwards **all** inbound headers including `Authorization` to `mcp-host` over cleartext HTTP. Any tool call over 5 s through the sidecar is a 502. | HIGH | `django_pyforge/mcp_http.py::proxy_station_mcp`. |
| T-6 | **Long work has a 300-second ceiling.** The living answer to "no MCP Tasks extension" is `start`/`get` + Celery. `CELERY_TASK_TIME_LIMIT = 300`, `SOFT = 60`. A rattler-build, a bulk Warden audit, or the BS-3 "2-hour Marshal sprint" cannot run on this worker. | HIGH | `base.py:418-421`; Helm `worker.terminationGracePeriodSeconds: 310` is derived from the same number. |
| T-7 | **Concurrency budget is undefined.** Chart defaults: web `replicaCount: 1`, `mcp-host` `replicas: 1` hard-coded, `resources: {}` on every pod (BestEffort QoS → first evicted under node pressure). No HPA exists. "Robust for concurrent human and agent traffic" is asserted, not sized. | MEDIUM | `deploy/charts/platform/values.yaml`, `mcp-host-deployment.yaml`. |
| T-8 | **Browser event streaming is a ping/pong stub.** The "HTMX SSE / WebSockets `/ws/events/` live badges" pillar has no implementation; `websocket.py` echoes `pong!`. | MEDIUM | `config/websocket.py`. |
| T-9 | **"Zero domain models on portals" is already bent.** `django-pyforge` ships three migrations (`RunState` supervisor tables). Acceptable, but the constraint should say "no *station-domain* models on `django-<station>`", or CI will fail the moment a portal needs a waiver table. | LOW | `django_pyforge/migrations/000{1,2,3}_*.py`. |

**Does Lane 2 / compute separation add latency or state issues?** Yes, but not for the
reason the prompt assumes. There is no network hop to a separate compute tier; the cost is
the self-call (T-3), the shared event loop (T-1), and transaction pinning. The state
synchronization problem is real in one place only: supervisor `RunState` in PostgreSQL vs
Celery task state on a volatile broker (see S-1) — a broker restart leaves `RUNNING` rows
that no worker will ever complete.

### Lens 2 — Deployment and state management (LocalStack vs OpenShift)

**Premise correction.** The living sizing table is 32–64 vCPU / 64–128 GB, sizes **zero**
station compute pods, and Vizro is "1–2 replicas". The 16–32 vCPU figure is the 2026-08-23
historical one.

| # | Finding | Severity | Evidence |
|---|---|---|---|
| S-1 | **`redis-broker` is `noeviction` without `maxmemory`, on `emptyDir`, unlimited.** `maxmemory` unset = unlimited, so `noeviction` never fires; the container grows until the kubelet OOM-kills it (no limits). Losses on restart: Celery queue, Celery **results** (`CELERY_RESULT_BACKEND = REDIS_BROKER_URL`), Channels layer, `pyforge.events`, the PEL, **`pyforge.events.dlq`**, and every `pyforge.events.applied:*` idempotency key. The Dream's "Redis AOF 20–50 GB RWO" storage row is not in the chart. A DLQ that dies with its broker is not a DLQ. | CRITICAL | `redis-deployment.yaml:3` ("emptyDir only -- Redis stays ephemeral"), `:52-58` (only cache gets `--maxmemory`), `values.yaml` `redis.broker`. |
| S-2 | **Celery is at-most-once by configuration.** No `task_acks_late`, no `task_reject_on_worker_lost`, no `task_routes`/queues, no `visibility_timeout`. A worker SIGKILL (grace 310 s, task limit 300 s — a 10 s window) silently drops the task; supervisor `RunState` stays `RUNNING` forever. All eight stations share one default queue: a Mason build flood starves Doctor remedies and supervisor completions. | HIGH | `config/settings/base.py` (no ACKS/ROUTES keys), `worker-deployment.yaml:42` (`celery -A config worker`, no `-Q`). |
| S-3 | **The query plane is a *file* and the topology is multi-pod.** `atlas.duckdb` has one writer guarded by `filelock`; readers are supposed to open `read_only=True` (the SPEC records this as "genuinely unbuilt — production code calls bare `duckdb.connect()`"). In Mode C the writer is a Celery pod and readers are web + Vizro pods, so the file must sit on RWX storage; DuckDB explicitly does not support concurrent access over network filesystems, and `filelock` on NFS is advisory at best. Parquet + `ATTACH` (34.x) is the correct direction; the `.duckdb` file must not be the shared artifact. | HIGH | Dream § The query plane; `resilience-invariants.md` BS-5 row; no PVC for DuckDB in the chart. |
| S-4 | **Scribe's PostgreSQL driver performs runtime DDL as the app role.** `graph_store_pg.py` executes `CREATE EXTENSION IF NOT EXISTS vector`, `CREATE SCHEMA`, `CREATE TABLE IF NOT EXISTS` at runtime. RFC-5 (revised) forbids runtime DDL and CAP-9 gives `platform_app` DML only, so in production this either fails with `permission denied` or, if someone "fixes" it by widening the role, silently defeats the auditor control. `CREATE EXTENSION` additionally requires superuser or a trusted-extension grant. | HIGH | `pyforge-scribe/src/pyforge/scribe/graph_store_pg.py:99-115`; `db/create_app_role.sql`; `db/sqlmigrate-map.yaml` has no scribe entry. |
| S-5 | **Parity is broken at the interpreter.** The platform image materializes `python-agent-platform` (`python = "3.12.*"`, forced by langflow/dbgpt). Atlas and Doctor declare `>=3.14`; the host's own `_log_import_skip` exists precisely because their MCP faces cannot import in that interpreter, hence the `mcp-host` sidecar. Laptop (3.14 station envs) and cluster (3.12 image) run different bytecode, different C-extension builds, different `asyncio`. "Identical Pydantic models … run seamlessly" is true only of pure-Python code. | HIGH | `pixi.toml:181`, `mcp_http.py::_log_import_skip`, Dream § Fleet conventions "Python floor" row. |
| S-6 | **Mode A is a different system, not a smaller one.** SQLite + in-memory broker cannot exercise Redis Streams, XAUTOCLAIM, the DLQ, Channels, pgvector, the DML/DDL role split, or Liquibase. Anything proven in Mode A is unproven for Mode C. Mode B pins `keycloak:24.0` in the Dream while CAP-6 research names `26.4.0`; `podman pod` ports are fixed at `pod create`, so adding a service later means recreating the pod. | MEDIUM | Dream § 4 Modes A/B; `compose.yml` has no Keycloak service. |
| S-7 | **Sizing memory is wrong for the web pod; CPU is dominated by workers.** The host process imports Langflow with `chromadb`, `langchain-chroma`, `elevenlabs` hard-imported at module load, plus Django/Wagtail. Langflow idles at 1.5–3 GB RSS; gunicorn without `--preload` multiplies that per worker. "2 GB / 4 GB" for 2–4 replicas will OOM at two workers. No rows exist for the DB-GPT sidecar, `mcp-host`, or the Liquibase Job (JVM). "LLM engines" (`transformers`, `diffusers`, `llama.cpp`) live in `local-recipes`, not in the platform env, so they are not in Mode C at all — the table should say so. 32–64 vCPU is plausible **only** because Celery (rattler-build) absorbs it; the web tier is memory-bound, not CPU-bound. | MEDIUM | `pixi.toml:198-200`, Dream § Cluster Compute. |
| S-8 | **Single PostgreSQL, 8 Gi, no standby, no backup.** The sizing table says "1 primary + 1 standby, 100–500 GB"; the chart ships `replicas: 1`, `size: 8Gi`. See B-2. | HIGH | `postgres-statefulset.yaml:19`, `values.yaml` `postgres.persistence.size`. |
| S-9 | **DB-GPT sidecar keeps its metadata on SQLite over an RWO PVC, 1 replica.** Documented as structurally unavoidable upstream. Fine as a constraint; wrong to omit from the DR/RPO story. | LOW | `values.yaml` `sidecar.metadataMountPath`. |
| S-10 | **Wagtail media on RWX `FileSystemStorage`.** RWX on OCP means NFS/CephFS/ODF; the "object store profile" row has no adapter. Backups of media are nobody's job. | LOW | `values.yaml` `media`. |

**On the "100 % parity" claim.** There are four topologies (A, B, C, plus the laptop pixi
envs). They differ in interpreter (S-5), broker semantics (S-1, S-6), storage (S-3, S-10),
and privilege model (S-4). The honest statement is "Mode B and Mode C share a Helm-shaped
contract; Mode A is a demo." The 15-factor baseline (`spec-python-agent-platform`
CAP-6 "air-gap parity is a failing check") is the right *mechanism*; the claim just
overreaches it.

### Lens 3 — Security, RBAC and air-gap constraints

| # | Finding | Severity | Evidence |
|---|---|---|---|
| X-1 | **Identity forgery via the mint endpoint.** `POST /assertion/mint/` (`csrf_exempt`, `require_POST`) calls `identity_from_idp_bearer`, which splits the token on `.`, base64-decodes segment 2, and returns `sub` and `groups`. **No signature, JWKS, issuer, audience, `exp`, or `nbf` check exists anywhere** in `django_pyforge` or `src/platform/config` (grep for `jwks`, `PyJWKClient`, `issuer`: no hits). The result is passed to `mint_assertion`, which signs an RS256 assertion for the requested station with the requested roles. Attack: `{"sub":"anyone","groups":["warden","steward","atlas"]}` → base64 → `x.<payload>.y` → one POST → a valid five-minute assertion, renewable forever. The module docstring says "Live token-exchange is deferred"; the deferral shipped as the live path. This defeats RFC-3/CAP-6/AD-7, supervisor `start` authorization, and Lane 3 row slicing. | CRITICAL | `django_pyforge/assertion/{identity,views,urls}.py`; `src/platform/config/urls.py:34`. |
| X-2 | **`rediss://` disables certificate verification.** `CELERY_BROKER_USE_SSL = {"ssl_cert_reqs": ssl.CERT_NONE}` whenever the broker URL is TLS. Under an enterprise TLS mandate this is worse than plaintext: it looks encrypted and is MITM-able. | HIGH | `config/settings/base.py:398-402`. |
| X-3 | **Role namespace = station namespace = tenant namespace.** Reachability is "IdP group name equals station slug" (`roles_from_request`, `access.py`). The Lane 3 isolation test uses groups `east`/`west` as tenants alongside `atlas` as a capability. Any IdP group that happens to be named `atlas`, `steward`, or `flags` grants access. The Dream's five-persona Keycloak matrix (`pyforge-admin`, `maintainer`, `compliance-auditor`, `viewer`, `agent-service-account`) does not exist in code. | HIGH | `django_pyforge/roles.py`, `access.py`, `tests/test_host_board_row_isolation.py`. |
| X-4 | **`idp_subject` does not reach Lane 3 over a signed channel.** The Dream's `X-Tenant-Signature` is unimplemented. The steward dashboard kit trusts `X-Forwarded-User` from a proxy hop it must be network-isolated to; the chart has NetworkPolicies **only for the two Redis pods** — none for web, worker, `mcp-host`, sidecar, or a Vizro pod. Any pod in the namespace can spoof the header. Meanwhile the host itself forbids importing Vizro/Dash (`_SECOND_STACK_TOP`), so the "isolated Vizro container" is real but unsecured at the network layer. | HIGH | `pyforge-steward/.../dashboard/middleware.py`, `declarations.py`; `redis-networkpolicy.yaml` is the only policy. |
| X-5 | **`mcp-host` is reachable without going through the host.** No auth in `mcp_host/app.py`, no NetworkPolicy, `Authorization` forwarded by the proxy over HTTP (T-5). The sidecar is effectively an unauthenticated MCP server on `:8090` for anything in the namespace. | HIGH | `src/platform/mcp_host/app.py`, chart. |
| X-6 | **`restricted-v2` is met; `readOnlyRootFilesystem` is not.** Pod/container contexts are correct and hard-coded (good). But `readOnlyRootFilesystem: true` appears in Dream § 4 "Hardened Container Contract" while Grounding admits the image needs writable `$HOME`/`.langflow`/media. Missing hardening: `automountServiceAccountToken: false`, PodDisruptionBudgets, default-deny NetworkPolicy, `imagePullPolicy` by digest. | MEDIUM | `_helpers.tpl` `platform.restricted*SecurityContext`. |
| X-7 | **go-sops + age is a developer vault, not an enterprise secret strategy.** Age keys have no expiry, no HSM binding, no audit log, no rotation protocol. The chart requires a *pre-created* Secret (`existingSecret: platform-secrets`) and never says who creates it; no ESO `SecretStore`/`ExternalSecret` manifests exist. Whoever decrypts the sops file at deploy time (CI) holds the master key. The RS256 assertion signing key is a settings PEM with no rotation story. | MEDIUM | `values.yaml` `existingSecret`; no `ExternalSecret` in chart or overlay. |
| X-8 | **Supply chain: a personal conda channel is load-bearing for the production env.** `channels = ["conda-forge", "SelfExplainML"]` with `channel-priority = "flexible"` on `python-agent-platform` (for `slowapi 0.1.10`, OpenFeature, `fastmcp-v4`). An air-gap mirror must include it; nothing signs it; bus factor is one maintainer. | MEDIUM | `pixi.toml:19,178,1683`. |
| X-9 | **Secrets in event payloads are unconstrained.** CloudEvents `data` is a free dict on a broker with no encryption at rest (`emptyDir`) and no redaction policy. | LOW | `events/fabric.py::publish`. |

**Does the architecture pass `idp_subject` through effectively?** The *design* (allauth
session → per-request token roles → short-lived RS256 audience-bound assertion → verified
at the supervisor) is correct and better than the HMAC original. The *implementation*
trusts an unverified bearer at the root (X-1), the transport to the sidecar is open (T-5,
X-5), and the last hop to Lane 3 is an unsigned header on an unpoliced network (X-4). The
chain is only as strong as its weakest link, and today that link is missing.

### Lens 4 — Agentic fabric and asynchronous orchestration

What exists is better than the Dream describes: CloudEvents 1.0 on `pyforge.events`,
per-station consumer groups, `XAUTOCLAIM` harvest to `pyforge.events.dlq`, loop-depth
extension with ceiling 8, idempotency via `SET NX` (`django_pyforge/events/fabric.py`).
The gaps are in what surrounds it.

| # | Finding | Severity | Evidence |
|---|---|---|---|
| A-1 | **No consumer is deployed.** The chart runs `celery worker` and gunicorn. Nothing runs `EventFabric.consume(group, consumer, handler)` — no Deployment, no Celery beat task, no management command loop. `EVENT_TYPES` contains exactly one type (`recipe.audit.failed`). "Warden fails → Doctor reacts" is a producer with no listener. | HIGH | `events/constants.py:22`, chart templates. |
| A-2 | **Infinite immediate retry, no backoff, no attempt counter.** `_apply` on handler exception deletes the applied key and returns **without ACK**; `consume` first drains the consumer's own pending (`start="0"`) so the same message is retried on every call, forever. `harvest_poison` DLQs only **unparseable** entries; a well-formed event whose handler always raises is re-`XCLAIM`ed to its previous owner and never quarantined. The Dream's "DLQ + retries" exists for malformed input only. | HIGH | `fabric.py::_apply`, `::harvest_poison`. |
| A-3 | **Idempotency is at-most-once and unbounded.** The `applied:` key is set *before* the handler runs; a process crash mid-handler leaves it set, so the event is never re-applied. Keys have no TTL on a `noeviction` broker → unbounded growth (S-1). | HIGH | `fabric.py::_apply`, `::_mark_applied`. |
| A-4 | **`XAUTOCLAIM` default `min_idle_time=0` steals live messages.** With the default, harvest claims every pending entry including ones a healthy consumer is processing right now, then hands them back. Churn and duplicate delivery under load. | MEDIUM | `fabric.py::harvest_poison` signature. |
| A-5 | **No distributed tracing across the bus.** `structlog` `request_id` crosses into Celery (`DjangoStructLogInitStep`); the CloudEvents body carries `specid`/`gitsha`/`sbompurl` but **no `traceparent`**. OTel is configured for HTTP only. A Warden→Doctor→Mason chain is un-traceable. | MEDIUM | `constants.py` extensions; `celery_app.py`. |
| A-6 | **Runaway-agent protection is unimplemented.** Loop-depth caps *event* recursion only. Nothing rate-limits `POST /stations/<name>/mcp` per subject/agent; Atlas's `RateLimitedScheduler` is outbound to GitHub. The Dream's "token bucket per `agent_id` + semantic breaker (>10 builds/min)" has no code. Supervisor `start` creates a `RunState` row and a Celery task per call → an agent loop fills PostgreSQL and the `noeviction` broker → broker OOM → Channels, Celery and the event bus all die. **A hallucinating agent is a platform-wide DoS with no backpressure.** Assertions expire in 5 min but are re-mintable (X-1). | HIGH | `supervisor.py::publish_run`, absence of any limiter in `mcp_dual_era.py`/`mcp_http.py`. |
| A-7 | **Doctor "auto-rollback within 10 s" has no metrics pipeline.** Requires OTel metrics tagged by flag, an anomaly evaluator, and a write path to flags; flags are a FILE resolver (`flags.json`) mounted from a ConfigMap — Doctor cannot flip them at runtime without a ConfigMap write + pod reload. | MEDIUM | `flags-configmap.yaml`, Dream § Automated Circuit Breakers. |
| A-8 | **Circuit breaker is per-process, in-memory.** `django_pyforge/circuits.py` is correct for asyncio (the PyBreaker trap was avoided) but state is per gunicorn worker: N workers trip N times, and the "stale-while-revalidate" fallback has no shared cache to serve stale from. | LOW | `circuits.py`. |

### Lens 5 — Monorepo and dependency complexity (pixi, Python 3.14)

Measured, not claimed: `pixi.toml` 2,333 lines; 13 top-level features, 29 environments;
`pixi.lock` 59,437 lines / 2.9 MB; `local-recipes` env resolves **3,392** conda records,
`python-agent-platform` **980**; **zero PyPI records** (conda-forge-only sourcing).

| # | Finding | Severity | Evidence |
|---|---|---|---|
| D-1 | **The multi-Python table is not what the repo does.** The Dream claims 3.12/3.13/3.14 "100 % SUCCESS … byte-for-byte". The repo pins `python-agent-platform` to `3.12.*` because langflow/dbgpt cannot move, and everything else to `3.14.*`; Atlas/Doctor declare `>=3.14`. "Byte-for-byte" across Python minors is impossible (different ABI builds). Two interpreters that cannot share a process is the real state and is what forced the `mcp-host` sidecar. | HIGH | `pixi.toml:36,181`; S-5. |
| D-2 | **One lockfile for 29 environments is a merge-conflict machine.** Any dep change to any feature re-solves and rewrites a 59 k-line file; the `environment.yaml` sync gate doubles the diff. The Dream runs eight stations in parallel, one story each — every one of those PRs touches the same two files. The `factory/` island and per-package `pixi.toml` (Phase 1–3) are the right fix and are unscheduled. | HIGH | `pixi.lock` size; CLAUDE.md PR gate 2. |
| D-3 | **Disjoint pins already forced a second image.** `dbgpt-app` pins `fastapi <0.113`; `langflow-base` needs `>=0.135`. No single env can hold both, hence the DB-GPT sidecar. Expect this to recur (langflow vs. wagtail vs. dagster vs. kedro upper bounds); the 1,000-package single-solve is one upstream cap away from splitting again. | MEDIUM | `compose.yml` header comment; `pixi.toml` `[feature.dbgpt-sidecar]`. |
| D-4 | **conda-forge-only means the estate owns feedstocks it did not want.** Four OpenFeature packages, a `cachebox 5.x` downgrade build, Liquibase (needs `openjdk ≥17`), `fastmcp-v4` on a personal channel, and a Django 5.2 line that lagged upstream security releases by two patches until the operator personally bumped it. Security-patch latency = one maintainer's availability. | MEDIUM | Dream 2026-08-24 rulings 4, 7; `pixi.toml:1683`. |
| D-5 | **"Free-threading" and "Windows 100 % native" are overstated.** Free-threaded 3.14 is a separate ABI (`python-freethreading`); duckdb/polars/pyarrow/psycopg C builds are not on it. `python-agent-platform` declares `platforms = ["linux-64", "osx-arm64-min"]` — no `win-64` — so the platform env is not Windows-native at all. | LOW | `pixi.toml:177`. |
| D-6 | **`channel-priority = "flexible"` on the production env.** Required for SelfExplainML fallthrough; also the setting that lets a name-collision on a lower channel win silently. | MEDIUM | `pixi.toml:178`; X-8. |

### Lens 6 — Blind spots and missing architecture

| # | Missing | Severity | Notes |
|---|---|---|---|
| B-1 | **Cross-station DB migration governance.** `db/sqlmigrate-map.yaml` is a single global sequence for one distribution (`python-agent-platform:N`). Eight independently-released `django-<station>` packages serialize every schema change through steward's changelog = release coupling. No rollback changesets policy, no `runInTransaction=false` exception process, no ownership rule per schema (Scribe creates its own — S-4). Langflow (Alembic) and DB-GPT (own SQLite) are outside Liquibase by admission. | HIGH | |
| B-2 | **Disaster recovery.** No backup, no PITR, no RPO/RTO, no restore drill, one Postgres replica, ephemeral Redis, RWX media, a DuckDB file, a SQLite PVC. BS-8 "startup reconciliation with PostgreSQL as the anchor" presupposes a PostgreSQL restore that nothing produces. | CRITICAL | |
| B-3 | **API versioning between Lane 2 and compute.** No station REST contract, no OpenAPI, no `pyforge.core.client`, `/api/v1` is Langflow's (T-2), no contract tests between `django-<station>` and the host. MCP handles protocol revisions (dual-era, good); CloudEvents require `dataschema` (good) but one type is registered. | HIGH | |
| B-4 | **CD and the Golden Path.** `platform-ci.yml` builds and tests; nothing pushes an image, records a digest, or releases Helm. Chart default is `tag: latest` + `pullPolicy: Always` — the opposite of "the artifact Warden passed is the artifact Steward deploys". No GitOps repo, no promotion environments, no Warden→deploy gate. Story 12.9 (OCP smoke) is "optional; Actions minutes" — Mode C is verified by hand on CRC. | HIGH | |
| B-5 | **Observability contract.** OTel + structlog configured; no SLOs, alerts, dashboards, log retention, or trace propagation across the bus (A-5). Doctor's auto-rollback and the Q5 scorecard both need this and neither names it as a prerequisite. | MEDIUM | |
| B-6 | **Tenancy model.** Row-slicing by IdP group (X-3) is the entire model. No tenant entity, no tenant on `RunState`, no tenant on CloudEvents, no per-tenant quotas. | MEDIUM | |
| B-7 | **Capacity, quotas and backpressure.** No resource requests, no HPA, no queue-depth limits, no per-subject rate limits (A-6), no retention/TTL on `RunState`, `applied:` keys, DLQ, Celery results. | HIGH | |
| B-8 | **Upgrade and rollback runbook.** Liquibase forward-only; `migrate --fake`; two Helm releases (core + OCP overlay) with no ordering guarantee; no blue/green for the schema-coupled web/worker pair. "Auto-rollback" refers to flags only. | MEDIUM | |
| B-9 | **Keycloak/IdP lifecycle.** Realm export, client registration, role mapping, and audience mapper (BS-3 caveat) are not versioned anywhere; Mode B has no Keycloak service in `compose.yml`. | LOW | |
| B-10 | **The document as an artifact.** 2,092 lines; the living contract is a Grounding block that overrides the diagrams below it; five "historical, do not build" sections still read as instructions; the Realization log contains research prose with mid-sentence truncation. A reviewer given this file will grade the wrong topology (this review's prompt did). | HIGH | |

---

## 3. Unaddressed Edge Cases (the "what ifs")

1. **Redis-broker pod is rescheduled during a Mason build.** Result backend, PEL, DLQ and
   `applied:` keys vanish. Supervisor rows stay `RUNNING`; the portal shows a spinner
   forever; `list_event_dlq` prints `(empty)` and the operator concludes nothing was lost.
2. **An agent loops `start` on `mason` 50×/min for an hour.** 3,000 `RunState` rows, 3,000
   Celery tasks on an unbounded broker, each build 300 s → worker backlog of ~5 hours,
   Doctor's remedies queued behind them, broker RSS climbs until OOM (see 1).
3. **A forged bearer hits `/assertion/mint/`.** Valid steward assertion; supervisor
   accepts `start`; Lane 3 rows for every tenant; MCP tools leased. No log line
   distinguishes it from a real user because the `sub` is whatever the attacker typed.
4. **Two web replicas and a sidecar timeout.** Tool call takes 6 s → 502 from replica A;
   client retries → replica B → duplicate work, no idempotency at the MCP layer.
5. **Langflow's lifespan hangs on a slow `langflow_schema` Alembic step during a rollout.**
   `startupProbe` fails, the new ReplicaSet never becomes Ready, `helm upgrade --wait`
   times out, Liquibase hook Job already ran → schema is ahead of the running code with no
   rollback changeset.
6. **The DuckDB file is on RWX and a reader opens it while the writer holds it.** DuckDB
   over NFS: undefined; best case `IO Error: Could not set lock`, worst case a corrupt
   cache that Kedro will not regenerate because the Parquet inputs are unchanged.
7. **A well-formed `recipe.audit.failed` whose Doctor handler raises `KeyError`.** Retried
   on every consume call forever (A-2); never quarantined; consumer CPU pegged; the
   `applied:` key flaps set/deleted on the broker.
8. **IdP admin creates a group named `atlas` for the analytics team.** Every member gains
   Atlas portal reachability and `atlas`-audience assertions (X-3).
9. **conda-forge lags a Django CVE by three weeks.** The only path is a personal feedstock
   PR; the platform image cannot take a pip hotfix (pip is "a residual seam", extras that
   uninstall conda packages are a build failure).
10. **Scribe boots against `platform_app` in production.** `CREATE EXTENSION vector` →
    `permission denied`; Scribe recall is down; the fix that gets merged at 2 a.m. is
    `GRANT CREATE ON DATABASE` to the app role.
11. **Postgres PVC is lost.** There is no backup. The estate's Guildhall, supervisor
    history, Wagtail content, Langflow flows, and Scribe graph are gone; DuckDB Parquet
    cache survives and now describes a database that does not exist.
12. **Cutover Phase 1 copies `src/shared/packages/` into `python-foundry`.** Every finding
    above ships to the lasting repo, and `local-recipes` is archived with the only
    history of why.

---

## 4. Actionable Remediation Directives

Ordered by blast radius. Each names the artifact that must exist **before** the next
Epic dispatches on this chain, and before cutover Phase 1.

### CRITICAL — block everything else

**R-1 Verify the IdP bearer before minting (closes X-1).**
`identity_from_idp_bearer` must validate signature via the IdP's JWKS (`PyJWKClient`, cached,
air-gap: JWKS mirrored or pinned), `iss`, `aud`, `exp`, `nbf`, and `azp`. Reject
`alg=none`. Add a negative test that a hand-rolled three-segment string is refused, and a
CI policy test that greps for `b64decode` outside the verifier. Until then, disable
`/assertion/mint/` behind a NetworkPolicy + `DJANGO_PYFORGE_MINT_ENABLED=false` default.
Write the deferred Keycloak Token Exchange (RFC 8693) story as the *replacement* for this
endpoint, not an enhancement to it.

**R-2 Make `redis-broker` durable and bounded (closes S-1, A-3, B-7 part).**
Chart: PVC + `appendonly yes` + `appendfsync everysec` for the broker; `--maxmemory` with
`noeviction` sized to the PVC; `resources.requests/limits` on both Redis roles; move
`CELERY_RESULT_BACKEND` to PostgreSQL (`django-celery-results`) or `redis-cache` with TTL;
TTL on `applied:*` keys (≥ max retry window); `XTRIM MAXLEN ~` policy on `pyforge.events`;
DLQ retention documented. Add a chaos test: kill the broker pod mid-task and assert the
task re-runs and the event is re-delivered.

**R-3 Write the DR contract (closes B-2, S-8).**
One page: RPO/RTO per store (PostgreSQL, Redis-broker, media RWX, DB-GPT SQLite, DuckDB
cache), backup mechanism (pgBackRest/CloudNativePG or `pg_basebackup` CronJob + WAL
archive to the profile object store), restore drill cadence, and the BS-8 reconciliation
order. Standby replica or operator is a *sizing* choice; a backup is not.

### HIGH — before the next station epic dispatches

**R-4 Split the document (closes B-10).**
Move everything the Grounding marks historical into
`docs/dreams/archive/pyforge-unifying-strategy-2026-08-23-topology.md` (or an appendix
file) and leave a ≤ 400-line living Dream whose diagrams are the ones to build. Add a
`dreams-hygiene` check that a Dream marked `specified` contains no section titled
"historical" longer than 20 lines.

**R-5 Define the station API contract (closes T-2, B-3).**
Reserve `/stations/<name>/api/v<N>/` on the FastAPI seam; move Langflow off bare
`/api/v1` (it already works under `/langflow/`); publish OpenAPI per station; build the
missing `pyforge.core.client` with a version header, contract tests in
`pyforge-testing-kit`, and the `PydanticFormErrorBridge` (BS-7). Delete the `/api/v1/compliance/check` example from the Dream until it is true.

**R-6 Stop the self-call; enforce the boundary in-process (closes T-3).**
Portals call station code through an in-process port (`django-pyforge` client → station
package via `pyforge.core.dispatch`) when co-located, and over HTTP only when
`STATION_REMOTE=1`. Add `ATOMIC_REQUESTS` exemptions for streaming/long views
(`@transaction.non_atomic_requests`). Keep the host import boundary by importing through
the hook registry, not `pyforge.*` directly.

**R-7 Put authorization on the MCP transport (closes T-4, T-5, X-5).**
Verify the RS256 assertion (audience `mcp:<station>`) in `dispatch_station_mcp` *before*
routing, for every JSON-RPC method; strip inbound `Authorization` and forward only the
verified assertion to the sidecar; make the proxy stream (`client.stream`, `aiter_bytes`,
`X-Accel-Buffering: no`, keep-alive comments) with a per-tool timeout ≥ the Celery hard
limit; add a NetworkPolicy so only `web` may reach `mcp-host:8090`; mTLS or at least a
shared-nothing service mesh policy for that hop.

**R-8 Rate-limit and bound agents (closes A-6, B-7).**
Token bucket per `sub` in `redis-cache` on `/stations/<name>/mcp` and on supervisor
`start`; per-station queue-depth ceiling that returns `429` with `Retry-After`; max
concurrent `RUNNING` per `sub`; TTL/archival on `RunState`. Tag every Celery task with
`sub` so a runaway subject can be revoked in one command.

**R-9 Fix delivery semantics on the bus (closes A-1, A-2, A-4).**
`consume` must track attempts (`XPENDING` `delivery_count`) and DLQ a well-formed event
after N failures with exponential backoff; `harvest_poison` must use a real
`min_idle_time` (≥ handler timeout); ship one consumer runner (`manage.py
consume_events --station doctor`) as a chart Deployment per subscribing station; register
the actual event vocabulary for Warden→Doctor→Mason. Add `traceparent` as a CloudEvents
extension and propagate it into Celery headers (closes A-5).

**R-10 Celery hardening (closes S-2, T-6).**
`task_acks_late = True`, `task_reject_on_worker_lost = True`, `worker_prefetch_multiplier
= 1`, per-station queues with `-Q`, a dedicated `builds` queue with its own time limit
(hours) and its own Deployment, and `terminationGracePeriodSeconds` derived from that
limit. Route Doctor remedies and supervisor completions to a high-priority queue.

**R-11 Query plane process boundary (closes S-3).**
Rule: the `.duckdb` file is **never** shared across pods. Writer pod owns it on RWO;
everything it publishes is Parquet on shared/object storage; readers `ATTACH` Parquet
and Postgres read-only. Enforce `read_only=True` on every non-writer `duckdb.connect`
with a policy test. Name the Vizro process's storage explicitly.

**R-12 Scribe DDL into the changelog (closes S-4, B-1 part).**
Move `CREATE EXTENSION vector`, `CREATE SCHEMA scribe_schema`, and the table into a
Liquibase changeset (owned by scribe, sequence reserved per station: `<station>:N`), and
make the runtime path assert-only. Extend `sqlmigrate-map.yaml` to a per-distribution
map so stations own their sequences; write the rollback policy (every changeset carries
`rollback:` or a documented `runInTransaction=false` exception).

**R-13 Namespace roles (closes X-3, B-6).**
Prefix capability roles (`pyforge:station:atlas`), tenant claims (`pyforge:tenant:east`),
and admin roles (`pyforge:admin`) under one configurable claim; refuse bare station names.
Add `tenant` to `RunState` and to the CloudEvents extensions.

**R-14 TLS honesty (closes X-2).**
`CELERY_BROKER_USE_SSL = {"ssl_cert_reqs": ssl.CERT_REQUIRED, "ssl_ca_certs": <truststore>}`.
`CERT_NONE` is permitted only under `COMPONENT_RUNTIME=local` and must fail the
production settings check.

**R-15 Golden Path CD (closes B-4).**
Image pushed by digest; Helm `image.tag` defaults to `required`; Warden verdict recorded
against the digest; a `deploy` workflow (or GitOps repo) that promotes exactly that
digest; Story 12.9 becomes a required check the moment Actions minutes exist.

**R-16 Right-size the interpreter story (closes S-5, D-1).**
Either raise langflow/dbgpt to 3.14 (feedstock work) or declare the platform image a
3.12 host and lower Atlas/Doctor floors, or formalize the two-interpreter topology
(host 3.12 + `mcp-host` 3.14) as the *design*, with the sidecar sized, policed and
replicated. Delete the multi-Python "100 % SUCCESS" table; replace with the measured
per-env solve matrix.

### MEDIUM — before cutover Phase 1

**R-17 Lock topology.** `factory/` island lock and per-package `pixi.toml` (Phase 1–3)
scheduled ahead of any further eight-wide station wave; `environment.yaml` regeneration
automated in CI, not by hand.

**R-18 Sizing rewrite.** Per-pod rows for web (memory-bound; `--preload`; Langflow RSS
measured), worker (CPU-bound; separate `builds` pool), `mcp-host`, DB-GPT sidecar,
Liquibase Job (JVM), Vizro. Requests/limits in `values.yaml`; HPA on web and worker;
PodDisruptionBudgets. State plainly that LLM inference is external (Ollama/Tachyon).

**R-19 Network baseline.** Default-deny NetworkPolicy in the namespace; explicit allows
for web→postgres/redis/mcp-host/sidecar, worker→postgres/redis, Vizro→(nothing but the
plane), `automountServiceAccountToken: false`.

**R-20 Secrets profile.** Document the age key custody (who holds it, where it rotates),
ship an `ExternalSecret` example for the Vault/ESO profile, and a rotation runbook for
`DJANGO_SECRET_KEY`, `REDIS_PASSWORD`, the DB roles, and the assertion PEM (dual-key
verify during rotation).

**R-21 Observability contract.** SLOs for `/ht/`, MCP p99, queue age, event lag; alert
rules; a metrics write path for Doctor's flag kill-switch (ConfigMap patch + reload, or
switch the FILE resolver to a Redis-backed provider).

**R-22 Live browser streaming.** Implement `/ws/events/` as a Channels consumer over
`redis-broker` Streams with per-`sub` filtering, or delete the pillar from the Dream.

### LOW

**R-23** Fix `readOnlyRootFilesystem` and Windows/free-threading claims in the Dream to
match the shipped Containerfile and `pixi.toml` platforms.
**R-24** Pin the Keycloak version once (`26.4.0`) across Dream, compose and research.
**R-25** Rewrite the "zero domain models" constraint as "no station-domain models on
`django-<station>`".

---

## 5. What the review did *not* find wrong

For balance, and because "merciless" should not mean "indiscriminate":

- The modular-monolith ruling over process-per-station is correct for this team size.
- RS256 audience-bound five-minute assertions are the right primitive; only the root
  (R-1) is broken.
- The `resilience-invariants.md` revisions (PyBreaker-async trap, HMAC rejection, MCP
  transport supersession, RFC-5 least-bad with role-level DDL revocation) are the kind of
  research-backed correction most programs never do.
- `restricted-v2` compliance is hard-coded in the chart, not a values knob. Good.
- The Liquibase Job refusing pooling-proxy hosts and the `preserveSchemaCase` `Never:`
  are exactly the sort of sharp edges that should be codified.
- conda-forge-only sourcing with zero PyPI records is a real supply-chain posture; the cost
  (D-4) is the price of it, not a mistake.
- The fleet-conventions table (exit codes, decision-tag namespaces, one status source)
  is the honest diagnosis of an eight-station estate, and Doctor-verdicts-Marshal is the
  right separation.

---

## Appendix — Evidence index

| Claim | Path |
|---|---|
| Unverified bearer → minted assertion | `src/shared/packages/django-pyforge/src/django_pyforge/assertion/{identity,views,urls}.py`; `src/platform/config/urls.py:34` |
| MCP dispatched before Django middleware | `src/platform/config/asgi.py:130` |
| Sidecar proxy 5 s / buffered / header pass-through | `src/shared/packages/django-pyforge/src/django_pyforge/mcp_http.py::proxy_station_mcp` |
| `/api/v1` owned by Langflow | `src/platform/config/asgi.py::_is_langflow_api_v1_path` |
| Broker emptyDir, no maxmemory | `src/platform/deploy/charts/platform/templates/redis-deployment.yaml:3,52-58` |
| Celery limits, result backend on broker, TLS CERT_NONE | `src/platform/config/settings/base.py:396-421` |
| No acks_late / routes | `src/platform/config/settings/` (absent) |
| Event fabric semantics | `src/shared/packages/django-pyforge/src/django_pyforge/events/{fabric,constants}.py` |
| No event consumer deployment | `src/platform/deploy/charts/platform/templates/` |
| Scribe runtime DDL | `src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_pg.py:99-115` |
| Two interpreters | `pixi.toml:36,181`; `mcp_http.py::_log_import_skip` |
| Lock composition | `pixi.lock` (29 envs; `local-recipes` 3,392 / `python-agent-platform` 980 conda records; 0 PyPI) |
| Only Redis NetworkPolicies | `src/platform/deploy/charts/platform/templates/redis-networkpolicy.yaml` |
| Postgres single replica, 8 Gi, no backup | `postgres-statefulset.yaml:19`; `values.yaml` |
| WebSocket stub | `src/platform/config/websocket.py` |
| SPEC status of RFC/BS rows | `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/resilience-invariants.md` |
