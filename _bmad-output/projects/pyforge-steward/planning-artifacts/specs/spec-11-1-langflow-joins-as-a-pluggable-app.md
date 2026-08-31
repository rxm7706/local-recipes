---
title: 'Langflow joins as a pluggable app'
type: 'feature'
created: '2026-08-20'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-agent-platform/ARCHITECTURE-SPINE.md']
warnings: ['multiple-goals', 'oversized']
baseline_revision: '1dc1ca68bea3433b57541b4437a3f19cf42084bf'
final_revision: '065eea947f'
---

<intent-contract>

## Intent

**Problem:** `src/platform/`'s ASGI dispatcher and FastAPI stub exist (Epic 10) but no engine is actually pluggable yet — Langflow isn't mounted, has no schema isolation, and defaults to writing SQLite state inside its own installed package directory, violating the platform's schema-isolation and statelessness contract (CAP-2). There is also no local dev-service baseline (`platform-dev` pixi feature) for the PostgreSQL/pgvector/Redis this story's schema-isolation work needs.

**Approach:** Add a `langflow_integration` Django app that provisions `langflow_schema` via a `RunSQL` migration, derive `LANGFLOW_DATABASE_URL` from the platform's own `DATABASE_URL` with a `search_path=langflow_schema` suffix (never a second stored credential), build Langflow's `create_app()` FastAPI app once and extend `config/asgi.py`'s dispatcher to forward `/api/v1/*` and bare `/health*` unchanged, plus `/langflow/*` prefix-stripped, to it, redirect Langflow's config/cache paths off local disk onto the shared Postgres/Redis, and add a new `platform-dev` pixi feature (postgresql+pgvector+redis-server+k8s CLIs) so this runs on the guaranteed local baseline.

## Boundaries & Constraints

**Always:**
- Pattern A only (AD-14): Langflow lives in-process as a mounted ASGI app; no sidecar container (no dated Dream deviation exists for one).
- Schema isolation is real, not conventional (AD-5): `langflow_schema` exists only via the `RunSQL` migration; Django's ORM never creates tables there; Langflow's own Alembic (which runs at its ASGI lifespan startup) never touches `public`.
- `LANGFLOW_DATABASE_URL` is derived programmatically from the platform's existing `DATABASE_URL` (same instance, `?options=-c%20search_path=langflow_schema` suffix) — never a second hand-maintained credential.
- Dispatch order is fixed (AD-4): `/api/v1/*` and bare `/health`/`/health_check` forward to Langflow's app with the scope unchanged (they match Langflow's native route prefixes); `/api/health` (the platform's own stub) is unaffected; `/langflow/*` forwards to Langflow with the `/langflow` segment stripped from the scope path; everything else still falls through to Django.
- Langflow's ASGI lifespan (its own Alembic bootstrap + service init) must run at process startup alongside the platform FastAPI stub's lifespan — both, not either/or.
- Redirect Langflow's config/knowledge-base/cache local-disk defaults onto shared, env-driven config (`LANGFLOW_CONFIG_DIR`, `LANGFLOW_KNOWLEDGE_BASES_DIR`, `LANGFLOW_CACHE_TYPE=redis` wired to the existing `REDIS_URL`) so no meaningful state survives a pod replacement.
- The `platform-dev` pixi feature composes onto `python-agent-platform` (adds `postgresql`, `pgvector`, `redis-server`, `kubernetes-helm`, `kubernetes-client`) and its `pixi.toml` edit carries the standard env-count reconcile ripple: `environment.yaml` re-export, `docs/reference/library-llms-full.md` regen, and `python scripts/bmad_drift_check.py --write-baseline` (new files `git add`-ed first).
- No `pyforge.*` import anywhere under `src/platform/` (AD-2, enforced by the existing import-linter test).

**Block If:** none identified — Epic 10's prerequisites are done, the `platform-dev` deps are pre-verified co-solvable (ARCHITECTURE-SPINE, 2026-08-14 dry-run), and the ASGI/schema mechanics are fully specified above.

**Never:**
- No object/file storage backend (S3, etc.) to satisfy Langflow's `storage_type` default — that would add a fourth infra piece beyond PostgreSQL+Redis+Kubernetes. Langflow's file-upload storage stays out of this story's proof scope (the smoke flow performs no file uploads); flag it as deferred work if a later story needs it.
- No `dbgpt_integration` work (Story 11.2) and no Celery dispatch wiring for Langflow calls (Story 11.3) — this story's flow execution runs synchronously through the ASGI mount.
- No vendored patches/forks of the `langflow`/`lfx` packages (AD-9) — any Langflow bug goes upstream or to the feedstock.
- No hand-edited `environment.yaml` or `library-llms-full.md` — always regenerate from `pixi.toml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Langflow API request | `GET /api/v1/flows` | Forwarded to Langflow's app unchanged; Langflow's own response | Langflow's own error handling applies |
| Bare health check | `GET /health` | Forwarded to Langflow (liveness ping) | n/a |
| Platform's own health | `GET /api/health` | Still served by the platform's own FastAPI stub, unaffected | n/a |
| Prefixed alias | `GET /langflow/api/v1/flows` | `/langflow` stripped, forwarded to Langflow as `/api/v1/flows` | n/a |
| Everything else | `GET /admin/`, `/ht/`, etc. | Falls through to Django, unaffected | Django's own 404/error handling |
| Migration run | `manage.py migrate` | `langflow_schema` created via RunSQL; zero Langflow tables in `public` | Migration is idempotent (`CREATE SCHEMA IF NOT EXISTS`) |
| Process start | ASGI lifespan startup | Both the platform FastAPI stub's and Langflow's lifespans run; Langflow's Alembic migrates `langflow_schema` | Startup fails loudly if either sub-app's lifespan raises |

</intent-contract>

## Code Map

- `src/platform/config/asgi.py` -- top-level ASGI dispatcher; extend routing table + lifespan handling to add Langflow's app
- `src/platform/config/fastapi_app.py` -- platform's own FastAPI stub at `/api/health`; unaffected, but its Epic-11 TODO docstring gets updated
- `src/platform/config/settings/base.py` -- `INSTALLED_APPS`/`LOCAL_APPS`; derive & set `LANGFLOW_DATABASE_URL`, `LANGFLOW_CACHE_TYPE`, `LANGFLOW_CONFIG_DIR`, `LANGFLOW_KNOWLEDGE_BASES_DIR` from the existing `DATABASES`/`REDIS_URL`
- `src/platform/langflow_integration/__init__.py`, `apps.py` -- new Django app (no models; migration-only)
- `src/platform/langflow_integration/migrations/0001_create_langflow_schema.py` -- `RunSQL` provisioning `langflow_schema`
- `src/platform/langflow_integration/asgi.py` -- builds Langflow's `create_app()` FastAPI app once at import time
- `src/platform/langflow_integration/tests.py` -- schema-isolation assertion (query `pg_tables`, confirm no Langflow tables in `public`)
- `src/platform/tests/test_langflow_mount.py` -- dispatcher routing test (via `httpx.ASGITransport`, mirroring `test_asgi_seam.py`'s pattern) for the 5 routing scenarios above
- `pixi.toml` -- new `[feature.platform-dev]` + `platform-dev` entry in `[environments]`
- `environment.yaml`, `docs/reference/library-llms-full.md` -- regenerated from the `pixi.toml` edit
- `.github/workflows/platform-ci.yml` -- extend the `container` job's smoke checks to hit `/api/v1/...` (or `/health`) proving the mount is live in the built image

## Tasks & Acceptance

**Execution:**
- [x] `src/platform/langflow_integration/{__init__.py,apps.py,migrations/__init__.py,migrations/0001_create_langflow_schema.py}` -- create the app + `RunSQL` schema migration -- AD-5 schema isolation, real not conventional
- [x] `src/platform/langflow_integration/asgi.py` -- build Langflow's `create_app()` once, exported for the dispatcher -- single shared ASGI process (AD-4)
- [x] `src/platform/config/settings/base.py` -- register `langflow_integration` in `INSTALLED_APPS`; derive `LANGFLOW_DATABASE_URL` from `DATABASES["default"]` + `search_path` suffix; set `LANGFLOW_CACHE_TYPE=redis` wired to `REDIS_URL`; set `LANGFLOW_CONFIG_DIR`/`LANGFLOW_KNOWLEDGE_BASES_DIR` to explicit non-default paths -- kills the local-disk-state default (AD-6)
- [x] `src/platform/config/asgi.py` -- extend dispatch: `/api/v1/*` and bare `/health*` unchanged to Langflow; `/langflow/*` prefix-stripped to Langflow; run both sub-apps' lifespans at startup/shutdown -- AD-4 dispatch order + Langflow's Alembic bootstrap
- [x] `src/platform/langflow_integration/tests.py` -- assert `langflow_schema` exists and owns Langflow's tables, `public` owns none of them -- proves AD-5 for real
- [x] `src/platform/tests/test_langflow_mount.py` -- cover all 5 I/O-matrix routing scenarios -- proves AD-4 dispatch order didn't regress the existing `/api/health` seam
- [x] `pixi.toml` -- add `[feature.platform-dev]` (postgresql, pgvector, redis-server, kubernetes-helm, kubernetes-client) composed onto `python-agent-platform`; register in `[environments]` -- AD-16 guaranteed local baseline
- [x] `environment.yaml`, `docs/reference/library-llms-full.md`, bmad-drift baseline -- regenerate/restamp after the `pixi.toml` edit (files `git add`-ed first) -- standard env-count reconcile ripple, leaves every detector no redder
- [x] `.github/workflows/platform-ci.yml` -- extend the `container` job to smoke-test `/api/v1/...` (or Langflow's `/health`) against the built image -- proves the mount survives containerization, not just local dev
- [x] `src/platform/config/asgi.py` -- replace `_run_lifespan`/`_run_startup_or_failed`/`_run_shutdown_or_failed`/`_dispatch_lifespan` with a queue-driven lifespan manager (Design Notes, corrected 2026-08-20) so both sub-apps' services stay live for the process lifetime instead of tearing down immediately after boot -- fixes the review-found HIGH bug
- [x] `src/platform/langflow_integration/tests.py` -- point `_lifecycle()` (the AC1 test) at the same shared corrected lifespan manager instead of its own single-shot `_run_lifespan` -- closes the identical bug there and the duplication between the two files
- [x] `src/platform/tests/test_langflow_mount.py` (or a new test module) -- add a test that drives `config.asgi.application`'s real `lifespan` scope directly (startup, then a live request through the dispatch, then shutdown) -- proves the fix and closes the coverage gap that let the bug ship

**Acceptance Criteria:**
- Given the `langflow_integration` app installed, when `manage.py migrate` runs, then `langflow_schema` exists in PostgreSQL and no Langflow-owned tables exist in `public` (verified by `pg_tables` inspection).
- Given the ASGI dispatcher, when requests hit each of the 5 I/O-matrix scenarios, then each routes exactly as specified with no regression to the existing `/api/health` seam.
- Given a flow executed end-to-end through the mounted app (e.g. `POST /api/v1/run/<flow-id>`), when it completes, then every row it wrote lives in `langflow_schema` only.
- Given the process restarts (kill + fresh start against the same PostgreSQL), when Langflow re-initializes, then it reconnects to `langflow_schema` without re-running schema creation and without data loss.
- Given `pixi install -e platform-dev`, when it solves, then `postgresql`+`pgvector`+`redis-server`+`kubernetes-helm`+`kubernetes-client` provision locally with zero containers or managed services.
- Given the `pixi.toml` edit, when the env-count reconcile ripple runs, then `bmad-drift-check`, `llms-full-check`, and the CI environment-sync gate are all no redder than before the change.
- Given the ASGI process receives `lifespan.startup` from a real server, when startup completes, then both sub-apps' services (Langflow's DB/cache services included) remain live and usable for subsequent requests until `lifespan.shutdown` actually arrives -- not torn down within the same startup call.

## Spec Change Log

### 2026-08-20 — bad_spec: broken lifespan-replay example in Design Notes

**Triggering finding:** Two independent review passes (Blind Hunter + Edge Case Hunter, no shared context) both confirmed, against Starlette's actual `routing.py` source, that this spec's own Design Notes example for `_run_lifespan` is broken: Starlette's `Router.lifespan()` calls `await receive()` **twice** per lifespan invocation (once before startup, once after `startup.complete` to gate shutdown) and does not check the second message's `type` — it only needs `receive()` to return. The Design Notes' `receive()` closure returns the *same* `{"type": f"lifespan.{event}"}` on every call, so a single `_run_lifespan(app, "startup")` call causes Starlette to run the sub-app's full startup **and** shutdown teardown before returning — yet the caller then reports `lifespan.startup.complete` to the real ASGI server as if the app is healthy. In production (`config/asgi.py`, which implemented this example verbatim), this tears Langflow's DB/cache services down immediately after boot, before any real request arrives — Langflow's mount is non-functional the moment the process starts. The bug was independently discovered and correctly fixed once already, but only inside the test file (`langflow_integration/tests.py`'s `_LifespanManager`, built during this story's own AC3 verification pass) — the fix was never back-ported to the production code that this Design Notes example produced.

**What was amended:** The Design Notes' `_run_lifespan` example is replaced below with a corrected queue-driven lifespan-protocol implementation (the same shape as the already-correct, already-tested `_LifespanManager` pattern in `langflow_integration/tests.py`) that feeds `lifespan.startup` now and `lifespan.shutdown` only when the caller is actually done — matching what a real ASGI server does. Two new tasks are added: (1) replace every use of the broken single-shot helper (both in `config/asgi.py`'s dual dispatch AND `langflow_integration/tests.py`'s AC1 `_lifecycle()` helper, which has the identical bug pattern) with ONE shared correct implementation, eliminating the bug and the code duplication between the two files in the same stroke; (2) add a test that drives `config.asgi.application`'s actual production `_dispatch_lifespan` path directly — the coverage gap that let this bug ship past both existing test files (one bypasses lifespan entirely via `httpx.ASGITransport`, the other drives `langflow_application`'s lifespan directly, never through `config.asgi.application`).

**Known-bad state avoided:** shipping a Langflow mount that returns HTTP 200 on `GET /health` (a bare liveness ping with no service dependency) while every service-backed route underneath it is silently broken from the moment the process boots — a failure mode invisible to both this story's CI smoke check (which polls `/health`, not the service-backed `/health_check`) and the AC3 test (which never drives the code path where the bug lives).

**KEEP instructions (must survive re-derivation):** Everything else in the prior implementation was independently verified correct and must be preserved as-is, not regenerated from scratch:
- `langflow_integration/` app scaffold (`apps.py`, `migrations/0001_create_langflow_schema.py`) — schema isolation is real and independently verified (`pg_tables` inspection, zero overlap).
- `config/settings/base.py`'s `LANGFLOW_DATABASE_URL`/`LANGFLOW_DB_DRIVER_CONNECTION_SETTINGS`/`LANGFLOW_CACHE_TYPE`/`LANGFLOW_CONFIG_DIR`/`LANGFLOW_KNOWLEDGE_BASES_DIR` derivation logic, including the `db_driver_connection_settings` fix for the main session engine's hardcoded `connect_args`.
- `config/asgi.py`'s HTTP routing logic (`_is_langflow_api_v1_path`, `_is_langflow_bare_health_path`, `_is_langflow_prefixed_path`, `_strip_langflow_prefix`, `_dispatch_http`) — only the lifespan-handling functions (`_run_lifespan`, `_run_startup_or_failed`, `_run_shutdown_or_failed`, `_dispatch_lifespan`) need replacing.
- `langflow_integration/tests.py`'s `_LifespanManager` class, `_build_text_only_flow_data`, `_run_flow_over_http`, and the AC3 test body — this is the ALREADY-CORRECT pattern the fix should reuse/share, not reinvent.
- `tests/test_langflow_mount.py` in full.
- `pixi.toml`'s `[feature.platform-dev]` block and the four added `python-agent-platform` deps (`chromadb`/`langchain-chroma`/`elevenlabs`/`psycopg`) — independently verified via a clean `pixi install -e platform-dev` solve.
- `.github/workflows/platform-ci.yml`'s CI reordering (migrate before container start) and the new Langflow smoke-test step — structurally correct, not implicated in this bug (a separate, lower-severity finding about its `/health` target and a missing `--user` flag on the new migrate step was triaged as `patch`/moot for this pass per the cascading-order rule and will resurface on the next review pass if still applicable).
- `docs/reference/library-llms-full.md`, `environment.yaml`, and the `bmad-drift-check --write-baseline` restamp.

## Review Triage Log

### 2026-08-20 — Review pass
- intent_gap: 0
- bad_spec: 4: (high 1, medium 2, low 1)
- patch: 5: (medium 3, low 2)
- defer: 2: (medium 1, low 1)
- reject: 4: (low 4)
- addressed_findings:
  - `[high]` `[bad_spec]` `config/asgi.py`'s `_run_lifespan` (used for both sub-apps' startup/shutdown) replays a single hardcoded lifespan message and never checks Starlette's second `receive()` call, causing a full startup-then-shutdown cycle within one "startup" call — Langflow's services are torn down immediately after boot in production. Root-caused to this spec's own Design Notes example; amended above (Spec Change Log), re-derivation follows.
  - `[medium]` `[bad_spec]` `langflow_integration/tests.py`'s AC1 `_lifecycle()` helper has the identical single-shot-receive bug (masked because it only reads durable Postgres state afterward, never makes a live request) — folded into the same fix as a shared, corrected helper.
  - `[medium]` `[bad_spec]` Neither new test file exercises `config.asgi.application`'s actual production `_dispatch_lifespan` path — the exact code path where the bug lived, and the reason it shipped undetected. A new test is added for this.
  - `[low]` `[bad_spec]` `_run_startup_or_failed` doesn't roll back the platform FastAPI stub's already-completed startup if Langflow's startup fails (currently harmless — the stub has no real lifespan hooks yet — but cheap to fix while this function is being rewritten anyway).

### 2026-08-20 — Review pass 2 (post-fix)
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 2, medium 2, low 2)
- defer: 2: (medium 2)
- reject: 7: (low 7)
- addressed_findings:
  - `[high]` `[patch]` `config/asgi.py` now unconditionally imports `langflow_integration.asgi`, which unconditionally imports `langflow` -- `tests/test_asgi_seam.py` (pre-existing, Story 10.1, untouched by this story) imports `config.asgi.application` with no guard and is collected by the pip-only CI `test` job, which never installs `langflow`. Confirmed live (`ModuleNotFoundError` at collection). Fixed by adding `pytest.importorskip("langflow")` to `test_asgi_seam.py`, matching the guard pattern this story already established in its own two new test files.
  - `[high]` `[patch]` The new "Migrate the database" CI step (`platform-ci.yml`) omits `-e DJANGO_ADMIN_URL=admin/`. `config/settings/production.py`'s `ADMIN_URL = env("DJANGO_ADMIN_URL")` has no default and is evaluated at settings-module-import time (confirmed by reading the file), so the step crashes with `ImproperlyConfigured` before migrating anything -- the whole `container` job's migrate step, and therefore the job, is currently broken. Fixed by adding the missing flag, matching the adjacent "Run platform container" step's already-established pattern.
  - `[medium]` `[patch]` Same new migrate step also drops the `--user 12345:0` flag present on "Run platform container" -- a real regression to arbitrary-non-root-UID CI coverage for the migration path specifically, flagged as moot in review pass 1 (bad_spec took priority) and now resurfacing as predicted. Fixed by adding the flag.
  - `[medium]` `[patch]` `_LifespanManager.__aenter__`/`__aexit__` (`langflow_integration/asgi.py`) raise `RuntimeError` on a `.failed` message without awaiting/cancelling `self._task` first, leaking the task and discarding its real underlying exception right when it's most needed for debugging a boot failure. Fixed by awaiting the task (suppressing its own exception, since the `.failed` message already carries the real error) before raising.
  - `[low]` `[patch]` `LANGFLOW_DATABASE_URL`'s `HOST`/`NAME` fields are interpolated unquoted while `USER`/`PASSWORD` are `quote()`-escaped two lines above (`config/settings/base.py`). Fixed for consistency.
  - `[low]` `[patch]` `_dispatch_lifespan`'s two defensive early-return branches (unexpected event type on either `receive()` call) exit without sending any ASGI lifespan reply, which could hang a real server waiting on one. Fixed by sending a `.failed` message on those paths instead of a bare return.
  - `[medium]` `[defer]` Neither new pytest suite (`langflow_integration/tests.py`, `tests/test_langflow_mount.py`) runs in any CI job -- the pip-only `test` job never installs `langflow`, the `container` job never invokes `pytest`. This story's hardest-won correctness proofs (schema isolation, the lifespan fix) have zero continuous enforcement today. Real, but wiring a full conda-env pytest job with live Postgres/Redis services into CI is a reasonably-scoped follow-up beyond this story's one named CI task (the container-image smoke check, delivered) -- unchanged reasoning from review pass 1.
  - `[medium]` `[defer]` `LANGFLOW_DB_DRIVER_CONNECTION_SETTINGS` (`config/settings/base.py`) works around a hardcoded default inside Langflow's own private `DatabaseService._get_connect_args()`, pinned only by a loose `langflow >=1.11.2` floor and with no CI coverage (per the defer above) to catch a future Langflow release silently re-breaking AD-5 schema isolation for the main session engine. Worth tracking as a named risk for whoever owns the langflow-suite feedstock pin going forward.
  - `[low]` `[reject]` Migration's `reverse_sql="DROP SCHEMA IF EXISTS langflow_schema CASCADE;"` has no safeguard against accidental data loss -- standard Django reverse-migration convention (an explicit, deliberate `migrate app zero` operator action), not a defect; no other migration in this codebase carries such a safeguard either.
  - `[low]` `[reject]` AC1's automated test provisions `langflow_schema` via a raw `CREATE SCHEMA IF NOT EXISTS` rather than `manage.py migrate` -- a deliberate, already-documented trade-off from this story's own planning (spec's Verification section names the manual `pg_tables` check as AC1's actual migration-path proof), not a new gap introduced by implementation.
  - `[low]` `[reject]` `_bmad-output/projects/pyforge-marshal/.sync-baseline.json`'s `git_head` stamp will be stale the moment `main` next moves past this story's commit -- true of every baseline stamp in this repo's drift-check system by design (each PR stamps against its own HEAD; the next commit anywhere naturally invalidates it), not specific to this story.
  - `[low]` `[reject]` `platform-dev` pixi feature has no win-64 target -- deliberate, already justified in Design Notes/pixi.toml comments (`redis-server` has no native win-64 conda-forge build; WSL2/remote-Redis is the documented fallback posture per ARCHITECTURE-SPINE AD-16).
  - `[low]` `[reject]` Websocket scopes matching Langflow's HTTP path prefixes fall through to the platform's stock websocket stub rather than Langflow -- pre-existing behavior (no websocket routing by path existed before this story either), no evidence Langflow registers real websocket routes under these prefixes, out of this story's declared HTTP-only scope.
  - `[low]` `[reject]` `_strip_langflow_prefix`'s `raw_path` slice assumes it starts with the literal ASCII bytes `b"/langflow"` without a `startswith` guard -- alphabetic path segments are never percent-encoded in a valid HTTP request, so `raw_path` and the already-matched decoded `path` cannot practically diverge here.
  - `[low]` `[reject]` `_LifespanManager` could theoretically deadlock on `_send_queue.get()` if the wrapped app's task exits without ever sending a message -- Starlette's `Router.lifespan()` (the only lifespan handler either sub-app actually uses, confirmed by reading its source) always sends a message in its `except BaseException` path, so this trigger condition cannot occur with either `fastapi_application` or `langflow_application` as they're actually implemented.

### 2026-08-20 — Review pass 3 (post-verify-repair)

- intent_gap: 0
- bad_spec: 0
- patch: 2: (medium 2, low 0)
- defer: 3: (high 1, medium 1, low 1)
- reject: 16: (low 16)
- addressed_findings:
  - `[medium]` `[patch]` `config/asgi.py`'s `_strip_langflow_prefix` mirrored `Mount` semantics incorrectly: it physically sliced `/langflow` off `scope["path"]`/`raw_path`, which made routing work but silently dropped the prefix from any redirect Langflow's own router issues through the alias (confirmed live: `test_langflow_prefixed_path_forwards_with_prefix_stripped`'s Location header carried no `/langflow` segment). Root-caused against this env's own installed `starlette.routing.Mount.matches`/`starlette._utils.get_route_path` source (not assumed): a real `Mount` leaves `path`/`raw_path` untouched and extends only `root_path`, relying on `get_route_path()` to compute the route-relative path internally; `starlette.datastructures.URL(scope=...)` (which builds redirect Locations) reads `scope["path"]` directly and never consults `root_path`. Fixed by rewriting the function to only extend `root_path`, leaving `path`/`raw_path` alone; the existing test's assertion updated to expect the alias preserved in the Location, and re-verified live (real `postgres:17`/`redis:7` containers) — 9/9 then 16/16 (full `tests/` + `langflow_integration/tests.py`) pass. (A first attempt at this same fix — extending `root_path` while STILL slicing `path` — was tried and failed the live test unchanged, which is what surfaced this codebase's actual Starlette version doesn't consult `root_path` for URL building at all; the working fix removes the slicing entirely rather than combining both.)
  - `[medium]` `[patch]` `_dispatch_lifespan`'s docstring asserts a startup failure on either sub-app is "rolled back automatically" via the `AsyncExitStack` unwind, but no test exercised that path — the exact kind of asserted-but-unproven claim this story's own Spec Change Log already root-caused once (the original lifespan bug shipped past two test files that never drove the failure path either). Closed by adding `test_lifespan_startup_failure_rolls_back_already_started_subapp` (`tests/test_langflow_mount.py`): two fake ASGI apps stand in for the platform stub and Langflow, the stub starts, Langflow's startup fails, and the test proves the stub's shutdown fires before the dispatcher reports `lifespan.startup.failed` to the real server. Verified live, passing alongside the full suite (16/16).

Sixteen reject-category findings from this pass are omitted from `addressed_findings` per this workflow's own "reject — drop silently" rule; three are worth naming here only because they are exact duplicates of findings this spec's pass-2 Review Triage Log already rejected with reasoning that still holds unchanged (the mounted app's websocket-routing gap, `_strip_langflow_prefix`'s — now `root_path`-only — lack of a `raw_path`-prefix `startswith` guard, and `_LifespanManager`'s theoretical empty-queue deadlock): no new information changed pass 2's verdicts, so they were re-rejected on the same basis rather than re-litigated. One reviewer-reported finding (a claim that `pixi.toml`'s new `platforms = ["linux-64", "osx-arm64-min"]` uses a non-existent platform tag) was independently verified FALSE against the live file: `osx-arm64-min` is an established named-platform entry (`pixi.toml`'s own `[workspace]` table, `{ name = "osx-arm64-min", platform = "osx-arm64", macos = "14.5" }`) used identically across the whole manifest, not something this story invented — the reviewer lacked full-file context (only the diff hunk), and the same applies to a second finding claiming the new CI migrate step has no visible readiness gate (an unchanged `sleep`-polling loop already precedes it, just outside the diff hunk shown). Three defer entries were minted: `DW-FU-11-1` (Langflow's own `AUTO_LOGIN=True` default left un-hardened — a real, named production-readiness gap outside this story's proof-of-pluggability scope), `DW-FU-11-1-2` (the new live-Postgres integration tests write real rows with no teardown, compounding the already-deferred "no CI wiring" gap from pass 2), and `DW-FU-11-1-3` (the new CI migrate step duplicates four connection literals also hardcoded in the pre-existing container-run step — the same duplication class that produced two real, already-fixed bugs in pass 2 — deferred rather than patched since a job-level `env:` refactor is unverified against a real GitHub Actions run in this sandbox). All three station-unresolved per this workflow's own mandatory cross-check (`resolve_config.py --key project` returned `pyforge-mason` against a `readlink -f`-and-marker-agreed `pyforge-steward`, the identical desync `DW-FU-10-4` already recorded); filed against `pyforge-steward`'s ledger.

## Design Notes

**Dual-lifespan ASGI startup — CORRECTED 2026-08-20 (see Spec Change Log).** `config/asgi.py`'s dispatcher is the single ASGI callable Uvicorn/Daphne invokes, so it owns the `lifespan` scope — it must drive TWO sub-apps' startup/shutdown (the platform's own FastAPI stub and Langflow's), not one, and each sub-app's lifespan must stay running across the whole process lifetime, not just for the duration of one call.

The original example here (a single-shot `receive()` closure returning a hardcoded message) is **broken**: Starlette's `Router.lifespan()` calls `await receive()` **twice** per invocation — once before startup, once after `startup.complete` purely as a "now shut down" gate — and never inspects the second message's `type`. A closure that returns the same message both times makes that second call return immediately, so a single `_run_lifespan(app, "startup")` call silently runs the sub-app's full startup **and** shutdown teardown before returning.

The correct shape is a long-lived task fed through a queue, so `lifespan.shutdown` is only delivered when the caller actually wants shutdown to happen — exactly the pattern `langflow_integration/tests.py`'s `_LifespanManager` already implements (built during this story's AC3 verification) and which `config/asgi.py` must now share/reuse rather than duplicate its own broken variant:

```python
class _LifespanManager:  # one shared implementation, used by config/asgi.py AND any test needing it
    def __init__(self, app):
        self._app = app
        self._receive_q, self._send_q = asyncio.Queue(), asyncio.Queue()

    async def _receive(self): return await self._receive_q.get()
    async def _send(self, msg): await self._send_q.put(msg)

    async def startup(self):
        self._task = asyncio.create_task(self._app({"type": "lifespan"}, self._receive, self._send))
        await self._receive_q.put({"type": "lifespan.startup"})
        msg = await self._send_q.get()
        if msg["type"] == "lifespan.startup.failed":
            raise RuntimeError(msg.get("message"))

    async def shutdown(self):
        await self._receive_q.put({"type": "lifespan.shutdown"})
        msg = await self._send_q.get()
        if msg["type"] == "lifespan.shutdown.failed":
            raise RuntimeError(msg.get("message"))
        await self._task
```
`config/asgi.py`'s `_dispatch_lifespan` starts BOTH sub-apps' managers on `lifespan.startup` (platform stub then Langflow, so Langflow's Alembic bootstrap runs), holds them open for the process lifetime, and shuts both down (Langflow then the platform stub, reverse order) only when the real server sends `lifespan.shutdown`. `langflow_integration/tests.py`'s AC1 `_lifecycle()` helper must use this SAME shared implementation instead of its own single-shot `_run_lifespan`, closing that file's identical bug and the duplication between the two files in one stroke. A new test drives `config.asgi.application`'s actual `lifespan` scope directly (a real ASGI client sending `lifespan.startup` then a request then `lifespan.shutdown`, not a bypass) — the coverage gap that let the original bug ship undetected.

**`/langflow/` prefix-strip.** Unlike `/api/v1/*` and bare `/health*` (which match Langflow's native route prefixes and forward with the scope untouched), `/langflow/*` has no matching native Langflow route — implement it as a scope copy with `path`/`raw_path` rewritten to drop the leading `/langflow` segment before invoking Langflow's ASGI callable, mirroring Starlette `Mount` semantics without adding a second routing framework.

**Four hard-import deps missing from the recipe's `run` list (discovered live).** `langflow.main.create_app()` unconditionally imports `chromadb`, `langchain-chroma`, `elevenlabs`, and (via its own SQLAlchemy engine) needs a Postgres driver `psycopg` (v3) — none of the first three are `run` deps of the `langflow` package in `recipes/langflow-suite/recipe.yaml` (only soft `run_constraints`), and neither `psycopg` nor `asyncpg` appears anywhere in that recipe at all (upstream gates one behind an unused pip extra). All four added to `[feature.python-agent-platform.dependencies]` at the recipe's own documented floors (AD-9: this documents intent, it does not touch the recipe).

**`LANGFLOW_DATABASE_URL`'s `search_path` needs a second env var.** The URL's `?options=-c%20search_path=langflow_schema` suffix (as specced) only reaches Langflow's Alembic connection — `DatabaseService._get_connect_args()` (langflow/services/database/service.py) hardcodes `connect_args={"options": "-c timezone=utc"}` for the MAIN session engine (every ORM query outside Alembic), and SQLAlchemy's `connect_args` wins over the URL's own query-string `options` on that key, silently dropping back to `public`. Verified live: the default-superuser bootstrap row landed in `public`, not `langflow_schema`, until `LANGFLOW_DB_DRIVER_CONNECTION_SETTINGS` was set (JSON, `{"options": "-c search_path=langflow_schema -c timezone=utc"}`) — `_get_connect_args()` returns that dict directly, ahead of the hardcoded default. `config/settings/base.py` now sets both env vars; the URL suffix stays (Alembic still needs it) and is the documented contract, the second var is the fix for everything else.

**Dual-lifespan test coverage needs its own DSN, not Django's connection.** `langflow_integration/tests.py` opens its own `psycopg` connections against `settings.LANGFLOW_DATABASE_URL` (query string stripped — psycopg's own URI parser is stricter than SQLAlchemy's and rejects the unescaped `=` inside `options`) rather than `django.db.connection`: any OTHER test in the same session that used `@pytest.mark.django_db` mutates `connections["default"].settings_dict["NAME"]` to a "test_"-prefixed database for the rest of the process (confirmed live, order-dependent), which `django_db_blocker` does not protect against.

**CI ordering: migrate before the container starts, not after.** `platform-ci.yml`'s `container` job used to `exec` `manage.py migrate` against the already-running app container. With Langflow attached, the app's OWN lifespan startup now runs Alembic against `langflow_schema` the moment the process boots — which fails loudly if that schema doesn't exist yet. The migrate step moved ahead of "Run platform container" as a one-off `run --rm --entrypoint /app/entrypoint.sh` invocation (mirrors the K8s "migration is a separate Job, not pod-boot work" pattern the existing comment already described).

**`llms-full-check`/`.gitignore`.** `docs/reference/library-llms-full.md` was hand-updated per its own regeneration prompt (no script generates it). `LANGFLOW_CONFIG_DIR`/`LANGFLOW_KNOWLEDGE_BASES_DIR`'s local-dev default resolves under `src/platform/.langflow/`; added to `.gitignore` (ephemeral runtime scratch, AD-6, same category as `staticfiles/`/`media/`).

**AC3 (flow execution end-to-end) now FULLY verified** by `langflow_integration/tests.py::test_run_flow_writes_land_only_in_langflow_schema`. The earlier attempt's "unrelated auth snag" was self-inflicted: it tried `POST /api/v1/login` with an explicit `LANGFLOW_SUPERUSER_PASSWORD`, but `AUTO_LOGIN=True` (the default) ignores that var entirely (`services/utils.py` logs "Ignoring legacy default LANGFLOW_SUPERUSER_PASSWORD in AUTO_LOGIN mode") and ships its own no-password path: `GET /api/v1/auto_login` mints a real bearer token for the bootstrap superuser. That token creates a flow and mints a real API key (`POST /api/v1/api_key/`); the key then authenticates the literal `POST /api/v1/run/<flow-id>` (that route is API-key-secured, a different dependency than the session/bearer auth the rest of the API uses). The flow itself is a hand-built, zero-external-dependency `TextInputComponent -> TextOutputComponent` chain (`lfx.components.input_output`) via `lfx.graph.Graph(...).dump()` — no starter project fit (all use LLM/agent components) and no live model endpoint needed, matching this AC's actual concern (the write path, not model quality). Verified end-to-end against real `postgres:17`/`redis:7` containers: the run's `flow`, `vertex_build` (x2), `transaction` (x2), and the minted `apikey` row all land in `langflow_schema`; `public` still owns only its 24 Django tables, zero overlap. Two real gotchas found along the way, now documented in the test file itself: (1) driving `config.asgi.application`'s or Langflow's own ASGI app through a SINGLE `_run_lifespan(app, "startup")`-then-later-"shutdown" call pattern (as used by AC1's own `_lifecycle()` helper) actually runs BOTH startup AND shutdown within that one "startup" call — Starlette's lifespan handler calls `receive()` twice per invocation and doesn't type-check the second message, so it immediately tears the app back down; harmless for AC1 (which only reads durable Postgres state afterward) but fatal for a live multi-request HTTP round-trip, which needs a proper queue-driven lifespan manager (`_LifespanManager`, added to the test file) that feeds `lifespan.startup` now and `lifespan.shutdown` only when the caller is done. (2) `passlib==1.7.4`'s bcrypt-version probe throws `AttributeError: module 'bcrypt' has no attribute '__about__'` against `bcrypt>=4.1` (removed that submodule) — but this is genuinely a "(trapped)" cosmetic warning, not fatal (confirmed by re-testing with `bcrypt==4.3.0`, the version conda actually solves for `platform-dev`, restored after initially misdiagnosing it as the blocker): passlib still hashes/verifies correctly, so no pin change needed.

**Fix landed 2026-08-20 -- three non-obvious calls made beyond the Design Notes example above.** (1) `_LifespanManager` was relocated to `langflow_integration/asgi.py` rather than a new shared module -- `config/asgi.py` already imports `langflow_application` from there, so this adds no new import edge, and the class itself was moved byte-for-byte (not reimplemented) per the KEEP instructions. (2) `config/asgi.py`'s `_dispatch_lifespan` does NOT use the Design Notes' illustrative `startup()`/`shutdown()`-method shape verbatim -- it instead enters two `_LifespanManager(...)` instances (unchanged, context-manager-only class) into one `contextlib.AsyncExitStack`, which (a) reuses the existing class with zero modification, (b) gets the specced reverse-order shutdown (Langflow then the platform stub) for free from the stack's own unwind order, and (c) also closes the `[low]` rollback-gap finding for free: if Langflow's startup fails after the platform stub's succeeded, the stack's unwind (triggered as the exception propagates out of the `async with`) shuts the stub back down automatically, rather than leaving it running. (3) The new coverage-gap test (`test_lifespan_keeps_langflow_services_live_across_requests`, `tests/test_langflow_mount.py`) hits Langflow's `/health_check` (not `/api/v1/...`) -- it's unauthenticated (no `auto_login`/API-key dance needed) and its handler queries BOTH Postgres and the Redis-backed chat service directly, so it fails loudly (`NoFactoryRegisteredError`) exactly the way the original bug did; verified live by temporarily reintroducing the old single-shot `_run_lifespan` into a scratch copy of `config/asgi.py` and confirming this test fails with that exact error, then confirming it passes again once reverted.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

**Manual checks (if no CLI):**
- Inspect `pg_tables` after `manage.py migrate`: `SELECT schemaname, tablename FROM pg_tables WHERE schemaname IN ('public','langflow_schema');` -- Langflow's tables (`flow`, `user`, `variable`, etc.) appear only under `langflow_schema`.

## Auto Run Result

**Summary.** This session resumed the story after its deterministic verification gate
(`python scripts/spec_surface_reconcile.py`, one of bmad-loop's own harness-level verify
commands) failed: Story 11.1's implementation had already landed and passed its own two review
passes, but the two overlapping specs whose `surface:` cover `src/platform/**`
(`pyforge-steward/spec-python-agent-platform` and `pyforge-mason/spec-django-accelerator-
framework`) had never had their `.memlog.md` reconciled for the story's twelve changed paths.
Repaired without touching the intent contract: named the changed paths in both memlogs and
restamped `scripts/.spec-surface-baseline.json` for those two specs only. With the gate green, a
scheduled follow-up review pass (pass 2's own `followup_review_recommended: true`) ran per the
normal workflow and found two real, verified bugs, both fixed.

**Files changed this session:**
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-agent-platform/.memlog.md` — reconciled Story 11.1's 12 changed paths, then this pass's own 2.
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-django-accelerator-framework/.memlog.md` — same reconciliation for the 11 (of 12) overlapping paths.
- `scripts/.spec-surface-baseline.json` — restamped for both specs, twice (once per reconciliation round).
- `src/platform/config/asgi.py` — `_strip_langflow_prefix` corrected to extend `root_path` only (real Starlette `Mount` semantics), not slice `path`/`raw_path`.
- `src/platform/tests/test_langflow_mount.py` — the prefix-strip test's assertion corrected to prove the fix; new `test_lifespan_startup_failure_rolls_back_already_started_subapp` closes a lifespan-rollback coverage gap.
- This spec file — Review Triage Log pass 3, this section, frontmatter.
- `_bmad-output/projects/pyforge-steward/implementation-artifacts/deferred-work.md` — 3 new entries (`DW-FU-11-1`, `-2`, `-3`).

**Review findings breakdown (pass 3):** 2 patches applied (both medium, both verified live), 3
deferred (`DW-FU-11-1` high — Langflow's own `AUTO_LOGIN=True` default left un-hardened, a named
production-readiness risk outside this story's proof-of-pluggability scope; `DW-FU-11-1-2` low —
new live-DB integration tests have no row teardown; `DW-FU-11-1-3` medium — a new CI step
duplicates connection literals already hardcoded elsewhere, the same duplication class that
produced two real bugs in pass 2), 16 rejected (13 false-positive/non-issues verified against
live code or the installed Starlette source, 3 exact duplicates of pass-2's already-sound
rejections).

**Verification performed:** both bmad-loop harness verify commands green
(`pixi run --frozen -e pyforge-steward pyforge-steward-test`: 729 passed; `python
scripts/spec_surface_reconcile.py`: exit 0, no drift). This story's own Verification-section
commands re-run live against real `postgres:17`/`redis:7` Docker containers: `manage.py migrate`
creates `langflow_schema` with zero Langflow tables in `public`; the full `tests/` +
`langflow_integration/tests.py` suite (16 tests, up from 14) passes; `pixi run -e local-recipes
llms-full-check` clean (no drift from any pixi.toml touch in this session — none occurred).
`pixi install -e platform-dev` not re-run this session (no dependency change; already verified
in the prior session per this spec's own Design Notes).

**Residual risks:** the three newly-deferred items above; `DW-FU-11-1` (passwordless superuser
bootstrap exposure) is the one worth flagging loudest — real and severity-`high` in consequence,
though correctly out of this story's declared scope per its own frozen Never section.

**Follow-up review recommendation:** `false`. This pass's own changes are two small, independently
verified, low-risk patches (a scope-dict fix confined to one function, and one new test) — not the
breadth/complexity/behavior-impact profile that would justify a fourth pass.

