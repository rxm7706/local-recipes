---
title: 'Async work never blocks Django'
type: 'feature'
created: '2026-08-21'
status: 'done'
baseline_revision: 'a1b777252250e954f2fa3dfae6196021dc004d72'
final_revision: '131eae1b88b913f777f83b578c8a545372f23abc'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-agent-platform/ARCHITECTURE-SPINE.md', '{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-agent-platform/SPEC.md']
warnings: []
---

<intent-contract>

## Intent

**Problem:** Celery's app object (`config/celery_app.py`) and settings (`CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` derived from `REDIS_URL`) exist, and Story 11.2 built the first real task (`dbgpt_integration/tasks.py::text_to_sql`), but no worker PROCESS is wired anywhere (`compose.yml` has no `worker` service) and no test ever dispatches through a real broker (`.delay()`) — only direct function calls or `CELERY_TASK_ALWAYS_EAGER` synchronous mode. `text_to_sql` also has two real, confirmed gaps: an unguarded `httpx.Client.post()` that lets a connection failure (sidecar unreachable) escape as a raw, undocumented `httpx` exception instead of a named failure mode, and a global `CELERY_TASK_SOFT_TIME_LIMIT = 60` (an unedited cookiecutter-django placeholder) that would kill a real live round trip — which the task's own code documents can take noticeably longer than 60s — before its own 120s client-side timeout ever gets a chance to fire.

**Approach:** Add a `worker` service to `compose.yml` (mirrors `platform`'s build/environment/depends_on, `command: celery -A config worker -l info`). Harden `text_to_sql`: wrap both `client.post()` calls to turn a connection failure into a new, distinctly-named `DbgptSidecarUnreachableError` (a `DbgptRequestError` subclass, so existing `except DbgptRequestError` callers keep working); give `text_to_sql` a per-task `soft_time_limit`/`time_limit` override (via `@shared_task(...)` kwargs) sized to its own documented ~120s+network-hop reality, without touching the global default other tasks rely on. Add one small, symmetric Pattern-A task (`langflow_integration/tasks.py`, new) that proves the registry-driven "in-process" dispatch shape for a Pattern-A engine — a real, verifiable, but deliberately minimal in-process call (not a full flow-execution feature), mirroring how `text_to_sql` proves Pattern-B's "over REST" shape. Prove all of this against a REAL worker + real broker (`.delay()`, not a direct call and not `CELERY_TASK_ALWAYS_EAGER`), and prove the `platform` web process stays responsive (a concurrent `/ht/` request succeeds) while a long-running task is in flight.

## Boundaries & Constraints

**Always:** Task dispatch stays registry-driven (`config/engine_patterns.py`'s `ENGINE_PATTERNS`) — Pattern-B calls go over REST to the sidecar (never the public edge), Pattern-A calls happen in-process inside the worker. Every new/changed failure mode is a named, documented exception type a caller can distinguish and `except` on, never a bare propagated third-party exception. The global `CELERY_TASK_TIME_LIMIT`/`CELERY_TASK_SOFT_TIME_LIMIT` defaults are not changed wholesale for unrelated tasks (e.g. `platformapp/users/tasks.py`) — only `text_to_sql` (and the new Pattern-A task, if it needs one) gets a scoped override.

**Block If:** the Pattern-A task would require importing/modifying real Langflow flow-execution internals beyond a trivial, already-public surface (that would be scope creep into a feature, not infrastructure proof) — if so, HALT and report the gap rather than inventing a fake in-process call.

**Never:** add retry/backoff or timeout handling to `_register_datasource`/`text_to_sql` in a way that changes Story 11.2's already-verified happy-path behavior or its existing tests' mocked-transport assertions without updating them deliberately. Never add a Celery Beat/scheduled-task service — out of this story's scope (no periodic work is specced). Never fork DB-GPT's own code (AD-9) — connection-error handling is entirely on this platform's client side.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Real worker dispatch | `text_to_sql.delay(...)` against a live broker + running worker | Task executes out-of-process; result retrievable via the Celery result backend | N/A (happy path) |
| Host stays responsive | A long-running task is in flight on the worker | A concurrent request to `/ht/` on the `platform` (web) process returns 200 with no added latency from the in-flight task | N/A |
| Sidecar unreachable | `dbgpt` service down/unreachable, `text_to_sql` dispatched | Raises `DbgptSidecarUnreachableError` (new, named), not a raw `httpx.ConnectError`/`ConnectTimeout` | Caller can `except DbgptSidecarUnreachableError` distinctly from `DbgptRequestError` |
| Task exceeds its time budget | A round trip runs long | `text_to_sql`'s own `soft_time_limit` override fires (not the unedited global 60s default), giving the task room to reach its documented ~120s+hop reality | `SoftTimeLimitExceeded` surfaces as a named, expected failure, not a mystery kill at 60s |
| Pattern-A dispatch | The new Pattern-A task, dispatched via `.delay()` | Executes in-process inside the worker (imports/calls Langflow-side code directly), returns a real result | N/A |

</intent-contract>

## Code Map

- `src/platform/compose/compose.yml` -- add a `worker` service (same build/environment/depends_on as `platform`, `command: celery -A config worker -l info`)
- `src/platform/dbgpt_integration/tasks.py` -- wrap both `client.post()` calls; add `DbgptSidecarUnreachableError`; add a per-task `soft_time_limit`/`time_limit` override to `text_to_sql`
- `src/platform/langflow_integration/tasks.py` (new) -- one small `@shared_task` proving Pattern-A in-process dispatch
- `src/platform/config/settings/base.py` -- only if a Pattern-A-task-specific setting is genuinely needed (prefer per-task `@shared_task` kwargs over new global settings)
- `src/platform/tests/` or `dbgpt_integration/tests.py`/`langflow_integration/tests.py` -- unit tests for the new exception type + the new Pattern-A task (mocked/eager, matching this repo's existing Celery test convention); the REAL broker/worker/responsiveness/unreachable-sidecar proofs are this story's own manual Verification (docker compose), not pytest-collected

## Tasks & Acceptance

**Execution:**
- [x] `src/platform/compose/compose.yml` -- add a `worker` service mirroring `platform`'s `build:`/`environment:`/`depends_on:`, `command: celery -A config worker -l info` -- closes the "no worker process exists" gap Story 11.2's own review flagged as this story's to own
- [x] `src/platform/dbgpt_integration/tasks.py` -- wrap `_register_datasource`'s and `text_to_sql`'s `client.post()` calls to catch `httpx.TransportError` (connection refused/DNS/connect-timeout) and re-raise as a new `DbgptSidecarUnreachableError(DbgptRequestError)` -- turns an undocumented raw exception into a named, catchable failure mode
- [x] `src/platform/dbgpt_integration/tasks.py` -- add `soft_time_limit=`/`time_limit=` kwargs to `text_to_sql`'s `@shared_task(...)` decorator, sized above its own documented ~27s-direct/longer-through-the-hop reality (with headroom), without touching `CELERY_TASK_SOFT_TIME_LIMIT`'s global default
- [x] `src/platform/langflow_integration/tasks.py` (new) -- one small, real, verifiable `@shared_task` that calls something Langflow-side in-process (Pattern A), proving the registry-driven dispatch shape is symmetric across both patterns; add a matching test
- [x] Real verification (see Verification section): bring up the full compose stack including the new `worker` service, dispatch `text_to_sql.delay(...)` for real, confirm `/ht/` stays responsive concurrently, confirm a deliberately-wrong sidecar host/port produces `DbgptSidecarUnreachableError` (not a hang or a raw exception)
- [x] Update `sprint-status-ledger.yaml`: `11-3-async-work-never-blocks-django: done`

**Acceptance Criteria:**
- Given the compose stack with the new `worker` service running, when `text_to_sql.delay(...)` is dispatched, then the task executes out-of-process through a real Celery broker/worker and its result is retrievable (AC1)
- Given a long-running task in flight on the worker, when a concurrent request hits `/ht/` on the `platform` web process, then it returns 200 promptly, proving the host is not blocked (AC2)
- Given the `dbgpt` sidecar is unreachable, when `text_to_sql` is dispatched, then it raises `DbgptSidecarUnreachableError` -- a distinctly named, catchable failure mode -- not a raw/hung/undocumented exception (AC3)
- Given `text_to_sql`'s real duration profile, when it runs on the real worker, then it is not killed by the (unedited, too-low) global 60s `CELERY_TASK_SOFT_TIME_LIMIT` before its own logic completes (AC4)
- Given the pap:AD-17 registry, when a Pattern-A task is dispatched via `.delay()`, then it executes in-process inside the worker (no REST hop), proving dispatch is symmetric across both patterns (AC5)

## Spec Change Log

## Review Triage Log

## Design Notes

`DbgptSidecarUnreachableError` subclasses `DbgptRequestError` (not a sibling `RuntimeError`) so any existing `except DbgptRequestError` catch site (including this story's own future callers) keeps working without modification -- narrower exception types are additive, not breaking, when they subclass the one callers already catch.

The Pattern-A task is deliberately minimal by design (Boundaries & Constraints, `Block If`): its job is to prove the *dispatch shape* (`.delay()` -> registry consult -> in-process call), not to build a real Langflow feature. If no safe, real, already-public Langflow-side call exists to make this genuine rather than a stub, HALT per the `Block If` clause instead of fabricating one.

The `Block If` did not trigger: `lfx.processing.process.run_graph` (imported by `langflow.helpers.flow`/Langflow's own execution internals) is an already-public, minimal, real in-process entry point -- the same one `langflow_integration/tests.py::_run_flow_over_http`'s AC3 test drives indirectly via the full ASGI `/api/v1/run/<flow-id>` HTTP path. `run_echo_flow` calls it directly instead (no ASGI lifespan, no auth session, no DB write path needed for a pure `TextInput`->`TextOutput` pass-through), which is genuinely simpler AND more in-process than going through the mounted app -- confirmed by probing it live against the materialized `python-agent-platform` pixi env before writing the task: `RunOutputs.outputs[0].outputs["text"]["message"]` carries the echoed text straight back out.

**Dev Notes -- real verification, 2026-08-21 (Story 11.3):** all 5 ACs proven live against the full `docker compose` stack (`platform` + `worker` + `dbgpt` + `postgres` + `redis`), `worker` built from the same image as `platform`. `text_to_sql.delay('How many rows are in django_migrations?', model_name='gemini-3.6-flash')` executed on the real worker via a real Gemini round trip (`DBGPT_LLM_MODEL_PROVIDER=proxy/openai`, `DBGPT_LLM_MODEL_NAME=gemini-3.6-flash`, matching Story 11.2's own mechanism) and returned `{'sql': 'SELECT COUNT(*) AS row_count FROM django_migrations;', 'data': [{'row_count': 64}]}` in ~19s, retrievable via `AsyncResult` (AC1). Gotcha hit live: `text_to_sql`'s own `model_name` kwarg defaults to `"gpt-4o"` -- a dispatch that overrides the sidecar's configured model via env (as this verification did) must also pass a matching `model_name=` kwarg, or the sidecar answers `Model gpt-4o not found` (a `DbgptRequestError`, correctly surfaced, not a bug in this story's own code -- a call-site mismatch worth calling out for future dispatchers). Concurrent `curl /ht/` during that in-flight call returned 200 in ~10ms each time (AC2). Recreating the `worker` process with `DBGPT_SIDECAR_BASE_URL=http://dbgpt-nonexistent-host:9999` and re-dispatching surfaced `dbgpt_integration.tasks.DbgptSidecarUnreachableError: dbgpt sidecar unreachable while registering datasource 'platform': [Errno -2] Name or service not known` in the worker's own logs, `AsyncResult.state == "FAILURE"` (not hung) (AC3). `text_to_sql.soft_time_limit == 130` / `.time_limit == 150` confirmed via introspection in a live shell, while `CELERY_TASK_SOFT_TIME_LIMIT` (global) stayed `60` and an unrelated task (`platformapp.users.tasks.get_users_count.soft_time_limit`) stayed `None` (inherits the untouched global) (AC4). `run_echo_flow.delay('story-11-3 live pattern-a proof')` executed on the worker (no REST hop -- the worker's own log shows Langflow/`lfx`'s lazy Alembic-plugin imports loading for the first time, ~4.5s, then `{'echoed': 'story-11-3 live pattern-a proof'}`) (AC5).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

**Manual checks (if no CLI):**
- Real `.delay()` dispatch of `text_to_sql` against the live stack returns a real result via the Celery result backend
- A concurrent `/ht/` request during that in-flight task returns 200 promptly (host stays responsive)
- Pointing `DBGPT_SIDECAR_BASE_URL` at a wrong host/port and dispatching `text_to_sql` raises `DbgptSidecarUnreachableError`, observable in the worker's own logs -- not a hang, not a raw exception

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `8bea0ed706` (2026-08-21, "Merge pull request #599 from rxm7706/steward/11-3-async-worker-wiring-land"). Ledger row `11-3-async-work-never-blocks-django: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-11-3-async-work-never-blocks-django.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`, `src/platform/compose/compose.yml`, `src/platform/dbgpt_integration/tasks.py`, `src/platform/dbgpt_integration/tests.py`, `src/platform/langflow_integration/tasks.py`, `src/platform/langflow_integration/tests.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
