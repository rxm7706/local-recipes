---
title: "Resilience invariants — RFC-1..5 and BS-1..8"
chain: "pyforge-unifying-strategy"
created: "2026-08-24"
updated: "2026-08-24"
---

# Resilience invariants

Companion to `SPEC.md`. The Dream states thirteen directives — five RFCs and eight blind spots.
Four did not survive Phase-2 research against the live pins. This companion is the **authoritative
form of each**: what the Dream asked for, what research found, and what the SPEC actually binds.
Where a row says *revised*, the Dream's own text is superseded and the revision is recorded in its
Realization log dated 2026-08-24.

Each invariant names the capability that carries it. An invariant with no test that fails in its
absence is not implemented, however much code exists (CAP-10 success criterion).

## RFC directives

| # | Dream's remediation | Status | What the SPEC binds | CAP |
|---|---|---|---|---|
| **RFC-1** | Split each station's runtime into a low-latency REST pool (500ms ceiling, for HTMX portals) and a dedicated async pool for streaming agent connections. | **as written** | Unchanged. Note it *modifies an existing seam* — FastAPI already runs in-host at `src/platform/config/fastapi_app.py`; it is not being introduced. | CAP-11 |
| **RFC-2** | Two Redis services: `redis-broker` (`noeviction`, for Celery and Streams) and `redis-cache` (`allkeys-lru`, for sessions, HTMX partials, rate limiting). | **as written** | Unchanged, and cheap — the platform already runs Redis for both roles on one instance, so this is a split, not a new dependency. Success: filling the cache to eviction provably loses no queued task. | CAP-11 |
| **RFC-3** | Standardize `pyforge.core.client` on signed internal JWTs (HMAC-SHA256) carrying `idp_subject`, roles, and `delegated_by: "pyforge-host"`; Celery tasks capture `idp_subject` at invocation to mint scoped execution tokens. | **as written** | Unchanged. Confirmed genuinely unbuilt — `pyforge.core` ships `atomic_write`, `errors`, `landing_evidence`, `process`, `report`, `verdict`, and no `client`. | CAP-6 |
| **RFC-4** | DLQ at `pyforge:events:dlq` harvested by an `XAUTOCLAIM` consumer; loop-depth ceiling `X-PyForge-Loop-Depth <= 5` on inter-station payloads. | **as written** | Unchanged. Confirmed unbuilt — Redis is present for Celery and cache only; no `XADD`/`XAUTOCLAIM` anywhere in `src/`. | CAP-8 |
| **RFC-5** | **All** PostgreSQL DDL estate-wide via Liquibase changelogs; application frameworks "strictly prohibited from generating runtime DDL alterations." | **REVISED** | See below — the literal form is not implementable. | CAP-9 |

### RFC-5, revised

The directive's literal reading fails on one documented fact: `post_migrate` fires "at the end of
the `migrate` command (even if no migrations are run)" and is the **only** supported mechanism
populating `django_content_type`, `auth_permission` and `django_site`. Those handlers perform DML,
not DDL. A schema Liquibase built perfectly, with `migrate` never run, boots with empty permission
and content-type tables: the admin fails, every `has_perm` fails, allauth's `SITE_ID` lookup fails.
Separately, `create_test_db()` builds every test database by running `migrate`, so the test runner
has no documented path off Django migrations at all.

Research also found **zero prior art** — no blog post, talk, or maintained repository documents any
team running Liquibase or Flyway as schema authority for a Django application. The only bridge
package, `liquimigrate`, last released in 2016 and predates Django 2.0. And Django has no
`ddl-auto: validate` equivalent: `migrate --check` and `makemigrations --check` compare models to
*migration files*, never to the live schema, so ORM/schema drift is invisible until a runtime error.

**What the SPEC binds instead, in order:**

1. **DDL revoked at the database role.** The application role holds DML only; a separate migration
   role holds `CREATE`/`ALTER`/`DROP` and is used exclusively by the migration job. This is the
   only control an auditor can verify and the only one an agent cannot bypass by accident. It also
   makes every step below fail loudly rather than silently.
2. **Liquibase owns production DDL via a Helm `pre-upgrade` hook Job — never an init container.**
   An init container runs per pod, so N replicas produce N concurrent Liquibase runs contending on
   `DATABASECHANGELOGLOCK`, whose default wait is 5 minutes; a rollout where migration exceeds that
   leaves pods failing to start. A pod killed mid-migration leaves a stuck lock needing manual
   `liquibase release-locks` — that runbook needs an owner before first production use.
3. **Django migrations stay the authoring surface**, extracted with `sqlmigrate` and landed as
   changesets, with a CI gate failing the build when the extraction is stale. **This gate has no
   prior art; we build it.**
4. **`liquibase update`, then `migrate --fake`.** No Django DDL is emitted, `django_migrations`
   stays consistent so `check_consistent_history` passes on later deploys, and `post_migrate` still
   fires to populate content types, permissions and sites. One-time cutover uses `--fake-initial`,
   with its documented caveat that it matches table names only — so baseline the existing schema by
   generating changelogs from the live database, never by hand.
5. **Test databases are carved out of the directive entirely.** Ephemeral `test_*` databases are
   not part of the governed estate.

6. **Liquibase arrives as a conda-forge feedstock** — decided 2026-08-24, closing
   `liquibase-delivery-vehicle`. It is not on conda-forge today (the sole anaconda.org hit is a
   third-party `maize-genetics/liquibase` 4.21.0, zero downloads, two majors behind Community
   5.0.4), so this is a sixth new recipe in this chain. `openjdk` 25.0.2 clears the Java 17+ floor,
   `apache-tika` is the exact shape to copy, and the PostgreSQL JDBC driver must be **vendored into
   the recipe** because 5.0 Community stopped bundling it and LPM fetches over the network.
   Per repo Rule 1 that story's dev session invokes `conda-forge-expert`.

**The hook this needs is already shipped**, which is what made the feedstock the cheap option.
`src/platform/deploy/charts/platform/templates/migrate-job.yaml` is a
`helm.sh/hook: post-install,pre-upgrade` Job at weight `0` that runs the **platform image** and
passes its command as `args`. So step 2 adds a Job at weight `-1` on that same image, and step 4
changes this one's args from `migrate --noinput` to `migrate --fake`. No new image, no new supply
path, and Story 12.1's chart contract is untouched. Its header also rejects init containers for an
entirely different reason than step 2 does — `helm install --wait` deadlocks migration-gated
readiness — so two unrelated arguments land on the same design.

**If the estate's real goal is auditable, DBA-gated DDL rather than Liquibase specifically**, step 1
alone delivers most of it at a fraction of the cost, and `sqlmigrate` output is already a reviewable
SQL artifact. Worth putting back to whoever wrote the directive.

## Blind spots

| # | Dream's remediation | Status | What the SPEC binds | CAP |
|---|---|---|---|---|
| **BS-1** | Dual-driver Scribe: SQLite locally, PostgreSQL + `pgvector` on OpenShift. Premise: SQLite over `ReadWriteMany` corrupts B-trees under concurrent writes. | **REVISED — premise false** | Scribe is **not** SQLite. It ships `FlatFileGraphStore`, a single JSON file at `.claude/data/pyforge-scribe/graph.json`. There is no B-tree to corrupt. The invariant is rewritten as **flat-file → PostgreSQL/pgvector behind the existing `GraphStore` port**, keeping a local path. Note also that `recall.py` is deterministic token overlap, so "semantic search" is a new capability, not a backend swap. | CAP-14 |
| **BS-2** | FastAPI emits `:keepalive` every 15s; OpenShift routes declare `haproxy.router.openshift.io/timeout: 30m`. | **REVISED — transport superseded** | See below. | CAP-4 |
| **BS-3** | Celery tasks receive an immutable `delegation_context` (`idp_subject`) and mint scoped tokens via Keycloak client-credentials Token Exchange (RFC 8693). | **as written, with a caveat** | Unchanged. Caveat for CAP-4: the current MCP authorization spec requires RFC 8707 resource indicators, which exist in Keycloak only behind an experimental `RESOURCE_INDICATORS` flag; the documented interim is an audience protocol mapper. Pin the Keycloak version in acceptance criteria. | CAP-12, CAP-6 |
| **BS-4** | Django HTTPX clients use PyBreaker with 500ms fail-fast; HTMX views render degraded badges. | **REVISED — library cannot do it** | PyBreaker's async support is **Tornado-coroutine, not asyncio**. Passing an `httpx.AsyncClient` coroutine to `breaker.call()` returns the un-awaited coroutine, the breaker records an immediate success, and **the circuit never trips**. Native `acall` exists only in an unmerged PR from 2026-03-21. The SPEC binds: PyBreaker for sync paths (it is on conda-forge, dependency-free, and its Redis storage plugs into `django_redis`), plus **our own async wrapper** over PyBreaker's state storage. Rejected: `aiocircuitbreaker` (on conda-forge, dormant since January 2022) and `purgatory` (maintained, not packaged). Stale-while-revalidate HTMX fallbacks: unchanged. | CAP-10 |
| **BS-5** | Single dedicated ingestion worker writes `atlas.duckdb`; all FastAPI services and Vizro dashboards mount it `read_only=True`. | **as written** | Unchanged and genuinely unbuilt — production code calls bare `duckdb.connect()`; no `read_only=True` appears on any DuckDB file handle. Atlas's existing `filelock` admission covers Kedro *Parquet* outputs, a different surface. | CAP-10 |
| **BS-6** | Forward-compatible CloudEvents envelope carrying `schema_version: "2.x"`; validation in domain adapters, not at the stream boundary. | **as written** | Unchanged. No CloudEvents envelope exists today. | CAP-8 |
| **BS-7** | `PydanticFormErrorBridge` in `django-pyforge` unpacks HTTP 422 JSON error arrays into Django `ValidationError` dicts for inline HTMX highlighting. | **as written** | Unchanged — and note it lands in `django-pyforge`, which per CAP-1 is **ours to build**; `django-lasuite` supplies OIDC plumbing, not chrome or form bridging. | CAP-10, CAP-1 |
| **BS-8** | Idempotent startup reconciliation; Mason scans MinIO on boot to re-index database records, PostgreSQL as canonical anchor. | **as written, unscoped dependency** | Unchanged in principle, but note there is **no MinIO or `boto3` in `pyforge-mason` at all** — object storage is not part of Mason today. BS-8 therefore introduces a new backing store to a station that has none, which brushes the "exactly PostgreSQL + Redis + Kubernetes" constraint. Decompose the object-store decision before the reconciliation story. | CAP-10 |

### BS-2, revised

The directive is stale twice over, and the second point is the one that breaks it.

**The transport is deprecated.** HTTP+SSE — the two-endpoint `/sse` + POST shape the Dream
describes — has been Deprecated since MCP `2025-03-26`, and the current `2026-07-28` revision
classifies it Deprecated under the lifecycle policy: new implementations *should not* adopt it.

**The modern replacement removed what the design depends on.** `2026-07-28` removed the standalone
GET stream *and* protocol-level sessions from Streamable HTTP itself. A compliant server exposes a
single POST endpoint and answers GET or DELETE on it with `405`. `Mcp-Session-Id` is gone;
`Last-Event-ID` resumability is gone. SSE survives only as the wire format of a response to one
POST. And because stream closure now **means cancellation**, a held-open stream turns every
transient ingress hiccup into a silently cancelled build.

**The timeout annotation does not do what the Dream claims.** `haproxy.router.openshift.io/timeout:
30m` is valid syntax and does raise `timeout server` per route — but `timeout client` stays at
OpenShift's cluster-wide 30-second default with **no per-route annotation to change it**, and
HAProxy governs SSE by `timeout client`/`timeout server`, not `timeout tunnel`. A documented
OpenShift case shows a 30-second heartbeat failing with HTTP 504 and 15 seconds fixing it. So the
Dream's own 15s figure was right, but for a reason it did not state, and its 30m annotation buys
nothing for an idle stream.

**What the SPEC binds:** a single POST `/mcp` endpoint on the official `mcp` 2.0.0 SDK (on
conda-forge, and the only current-spec path — FastMCP reaches `2026-07-28` only at v4, still beta);
operations over ~30s return a **Tasks-extension handle** (SEP-2663) with `ttlMs` and
`pollIntervalMs`, or emit `notifications/progress` on the request's own stream; keep-alive comment
frames well under 30 seconds plus `X-Accel-Buffering: no`; the route annotation retained as
defence-in-depth for slow non-streaming responses, never as the mechanism.

**Open:** `mcp-tasks-runtime` — FastMCP's own PR notes that no SDK in any language shipped a
server-side Tasks runtime at time of writing. This is the largest gap between the recommended
pattern and shippable code, and CAP-4's success criterion depends on closing it.
