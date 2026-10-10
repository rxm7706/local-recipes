---
title: "87.2: The platform host boots without Langflow, and the full-stack env runs it"
type: 'fix'
created: '2026-10-10'
status: 'blocked'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-87-1-the-platform-host-boots-without-herald-and-says-why.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-11-1-langflow-joins-as-a-pluggable-app.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-19-2-one-real-ship-records-itself-against-a-persistent-store.md
  - src/platform/config/asgi.py
  - src/platform/langflow_integration/asgi.py
  - src/platform/langflow_integration/tests.py
  - src/platform/config/__init__.py
  - src/platform/config/celery_app.py
  - src/platform/config/settings/base.py
  - pixi.toml
  - docs/foundry/sbom-gaps.md
  - scripts/sbom_gap_derive.py
  - docs/reference/environments.md
  - docs/dreams/pyforge-steward.md
deferred: []
declared_low_risk: false
---

> **Retired 2026-10-10 — never dispatch.** The operator's ruling of the same day, verbatim label "Via the sidecar
> (Recommended)", routes herald's webhook through the mcp-host sidecar instead and says "87.2's full-stack composition
> can be dropped". Steward Story 87.3 (`87-3-the-host-forwards-herald-s-webhooks-to-the-mcp-host-sidecar`) replaces
> this story. It was never dispatched and changed no file outside planning. The ledger key moved `backlog` →
> `blocked` so no drain picks it up; an operator flip does not revive it. The pre-authorised flip of herald's 19.2
> key named in § Binding is void: 19.2 now waits on 87.3. The text below is kept as history (memlogs:
> `spec-pyforge-steward`, `spec-pyforge-unifying-strategy`, `spec-python-foundry-cutover`, 2026-10-10).

<intent-contract>

## Intent

**Problem:** herald Story 19.2's live proof needs one locked env that runs `config.asgi:application` with
`pyforge-herald` installed. No env can do that today.

- **The ruling.** On 2026-10-10 the operator chose, verbatim "Host without langflow": "Make config.asgi boot without
  langflow and give pyforge-foundry-full-stack celery, django-environ and wagtail (cross-station: steward's SBOM env).
  Matches 19.2's original 'full-stack' wording."
- **Why the image env cannot hold herald.** Adding `pyforge-herald` to `[feature.python-agent-platform]` fails to solve
  for `platform-dev` (2026-10-10, `pixi lock`). `pyforge-herald 0.1.0` requires `mcp >=2.2.0`, and langflow 1.12.3 and
  1.12.4 require `langflow-base ==1.12.x`, which requires `mcp >=1.28.0,<2.0.0`. Herald's only `mcp` import is
  function-level in `transport/mcp_transport.py` (Story 1.2), but the package still declares the dependency.
- **Why the laptop stack env cannot run the host.** `pyforge-foundry-full-stack` (`pixi.toml:1126`) composes every
  station feature plus `platform-dev` and `platform-object-storage`. It has daphne, PostgreSQL 17, `psycopg` 3.2.10 and
  `pyforge-herald`, but none of the host's Django packages.
  - `import config` stops at `src/platform/config/__init__.py:3` → `config/celery_app.py:4` with `ModuleNotFoundError:
    No module named 'celery'` (reproduced 2026-10-10).
  - Measured on the lock at `2d90c634f3`, the env lacks 42 of the 56 non-path packages
    `[feature.python-agent-platform.dependencies]` declares. Leave out the engines (`langflow`, `dbgpt`, `dbgpt-serve`,
    `chromadb`, `langchain-chroma`, `elevenlabs`), `dlt`, `psycopg2`, the Liquibase CLI (`liquibase`,
    `liquibase-postgresql`, `pgjdbc`) and `uvicorn-worker`. That still leaves 30 Django-host packages:
    `django-environ`, `wagtail`, `django-allauth`, `django-crispy-forms`, `crispy-bootstrap5`, `django-celery-beat`
    (which brings `celery`), `django-health-check`, `django-structlog`, `django-compressor`, `whitenoise`,
    `django-redis`, `django-model-utils`, `django-anymail`, the OpenTelemetry Django, WSGI and Celery instrumentation,
    the flagd provider set, `cachebox`, `hiredis`, `fido2`, `qrcode`, and seven smaller ones.
  - The settings name most of them in `INSTALLED_APPS` (`config/settings/base.py:127`-`:203`) and `MIDDLEWARE`
    (`:275`-`:299`), which `django.setup()` and the ASGI handler import. Which of the rest the import chain needs, the
    proof (AC 6) decides.
- **The ruling names three packages; the host needs the set.** Celery, django-environ and wagtail are the first three
  imports that fail. They are not the whole gap. The ruling's stated goal, "make config.asgi boot", is this story's
  proof (AC 6). So the env must take the host's full set, and the three named packages are part of it.
- **The set already exists as one feature.** `[feature.platform-ci-test]` (`pixi.toml:397`-`:507`, Story 16.1, "SOLE
  authority for Platform CI test job Python deps") is the env Platform CI imports `config.asgi` in, with Langflow stubbed.
  It declares 26 of the 30 directly. The other four (`django-timezone-field`, `cron-descriptor`, `django-appconf`,
  `rjsmin`) arrive transitively, as do `celery` and `django-tasks`, all present in its lock. It pins the estate's
  PostgreSQL 17 posture (`psycopg >=3.2.10,<3.2.11`, `libpq >=17.11,<18`). It is linux-64 only, which matches the
  full-stack env's own platform.
- **Langflow at import.** `config/asgi.py:65`-`:66` imports `langflow_integration.asgi`, whose `:42`-`:44` runs `from
  langflow.main import create_app` and `langflow_application = create_app()` at import. The same module defines
  `_LifespanManager` (`:47`), which the host also uses for the FastAPI and MCP lifespans (`config/asgi.py:188`-`:191`).
  Langflow's routes are the bare health paths (`:91`, `:146`-`:147`) and `/langflow/…` (`:148`-`:149`). The platform
  tests stub `langflow.main` in `sys.modules` to import the host at all (`tests/test_station_api_host_dispatch.py:15`-`:20`,
  and two more files).

**Approach:**

- **Host half.**
  - Reuse Story 87.1's `config/optional_components.import_optional` with `module="langflow_integration.asgi"`,
    `component="langflow"`, `provided_by="langflow"`. A `ModuleNotFoundError` naming `langflow` or a `langflow.*`
    module counts as absent. Anything else, including a failure inside `create_app()`, propagates.
  - Move `_LifespanManager` into a Langflow-free host module (`config/lifespan.py`). `langflow_integration/asgi.py`
    re-exports it, so `langflow_integration/tests.py` keeps importing it from there.
  - When Langflow is absent, `_dispatch_http` answers the bare health paths and `/langflow/…` with 404
    `{"detail": absent_reason("langflow")}`, and `_dispatch_lifespan` does not enter a Langflow manager.
  - With Langflow present, every branch is today's.
- **Env half.**
  - `pyforge-foundry-full-stack` gains `"platform-ci-test"` in its `features` list. Nothing else in `pixi.toml` moves.
    It adds no new pin site: the three packages the ruling names arrive at Platform CI's own pins (`celery >=5.6.3`,
    `django-environ >=0.14.0`, `wagtail >=7.4.3,<8.0`), with the rest of the host set beside them.
  - It also carries Platform CI's test tooling (pytest, pytest-django, ruff, mypy, import-linter). fnd:CAP-12 asks the
    laptop install to run "tests, lint and the local CI mirrors", so that tooling belongs there.
  - Solve with `pixi lock`. The session hook denies a live `pixi add` or `pixi update`.
  - **Fallback**, only if that solve fails on a test or lint tool pin: a new `[feature.platform-host]`. It holds
    `platform-ci-test`'s runtime entries, every package except the test, lint and docs tools and `kubernetes-helm`, at
    pins byte-identical to `platform-ci-test`'s, and is composed into `pyforge-foundry-full-stack` only. The memlog
    records the solver's message.
  - If the fallback does not solve either, the story stops and records the conflict. No pin is relaxed.
- **Regenerated, never hand-edited:** `environment.yaml` (`pixi project export conda-environment -e build >
  environment.yaml`), `docs/reference/environments.md` (`pixi run -e pyforge-guild docs-environments`) and
  `docs/foundry/sbom-gaps.md` (`pixi run -e pyforge-guild sbom-gaps-check -- --write-doc`).
  - Composing `platform-ci-test` into the layer env removes the derived `feature:platform-ci-test` row, and the fat-only
    `pin:` rows whose package that feature declares: at mint, `opentelemetry-api`, `opentelemetry-sdk`, `structlog` and
    `wagtail`.
- **A steward meta-test** (`src/shared/packages/pyforge-steward/tests/meta/test_full_stack_runs_the_platform_host.py`,
  new) reads `pixi.toml` and pins two things:
  - `pyforge-foundry-full-stack` composes `platform-ci-test` (or `platform-host` with each pin equal to
    `platform-ci-test`'s);
  - it never composes `python-agent-platform`.

Ledger key: `87-2-the-platform-host-boots-without-langflow-and-the-full-stack-env-runs-it`.
Type / Effort / Deps: fix / M / S-87.1.

### Living CAP citations

- **Shipped behaviour, host half:** `spec-pyforge-unifying-strategy` CAP-10, "Failure is contained". An absent engine
  takes the whole host down today. The mount itself is Story 11.1's (Langflow as a pluggable app, pap:CAP-2).
- **Shipped behaviour, env half:** `spec-python-foundry-cutover` fnd:CAP-12, "The laptop SBOM": through a layer
  environment, the SBOM runs "the platform local stack". The layer env carries the stack's services but cannot import
  its host. fnd:CAP-13's gap list is re-derived, not hand-edited.
- **canopy:AD-16** (local-first, pixi-provisioned): the env change stays in `pixi.toml`.
- **The estate's PostgreSQL 17** (fnd:CAP-12, AGENTS.md § Policy): no `postgresql` or `libpq` pin to 18, and no
  psycopg, psycopg2 or pgvector cap lifted.
- This story mints no CAP and changes no `SPEC.md` text. fnd:CAP-12's success sentence names `platform-dev` and
  `platform-object-storage` as the layer. The cutover memlog records that `platform-ci-test` joins them, for the next
  `bmad-spec` pass.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag.

## Acceptance Criteria

- **(1) The host imports without Langflow.** Given a fresh interpreter (as in Story 87.1) whose meta-path finder refuses
  `langflow` and every `langflow.*`, with no `langflow` stub When it runs `import config.asgi` Then it exits 0. Its
  combined stdout and stderr carry exactly one reason naming `langflow` and the missing module.
- **(2) Langflow's paths answer 404 with the reason.** In that interpreter, through `httpx.ASGITransport` on
  `config.asgi.application`:
  - `GET /langflow/`, `GET /langflow/api/v1/auto_login`, `GET /health` and `GET /health_check` return 404 with JSON
    `{"detail": <the reason>}`.
  - `GET /api/v1/flows` returns the FastAPI seam's 404 `{"detail": "Not Found"}`, as today.
  - `GET /stations/warden/api/v1/health` returns 200.
- **(3) The lifespan completes without Langflow.** In that interpreter, driving `application` with a `lifespan` scope
  (`lifespan.startup`, then `lifespan.shutdown`) yields `lifespan.startup.complete` and then
  `lifespan.shutdown.complete`. The FastAPI app's and every loaded station MCP app's lifespans are still entered.
- **(4) With Langflow present, nothing changes.** In `platform-ci-test`, the in-process host tests that stub Langflow
  pass without edits (`tests/test_station_api_host_dispatch.py`, `tests/test_ws_events.py`,
  `tests/test_station_port_no_loopback.py`). `from langflow_integration.asgi import _LifespanManager` still works
  (`langflow_integration/tests.py:77`, `:165`).
- **(5) The full-stack env composes the host set.** `pixi.toml`'s `pyforge-foundry-full-stack` composes
  `platform-ci-test`, or the fallback `platform-host` whose every pin equals `platform-ci-test`'s, and still composes no
  `python-agent-platform`. The steward meta-test pins both.
- **(6) The proof.** From the repo root, this exits 0:

  ```bash
  pixi run --frozen -e pyforge-foundry-full-stack bash -c 'cd src/platform && python - <<"PY"
  import asyncio, httpx, config.asgi as h
  async def main():
      t = httpx.ASGITransport(app=h.application)
      async with httpx.AsyncClient(transport=t, base_url="http://testserver") as c:
          for p in ("/stations/herald/api/v1/health", "/stations/herald/api/v1/openapi.json"):
              r = await c.get(p)
              assert r.status_code == 200, (p, r.status_code, r.text)
  asyncio.run(main())
  PY'
  ```
- **(7) The lock moves only where it should.**
  - `pixi lock` exits 0.
  - Comparing `pixi.lock`'s `environments:` blocks at the base and at the head, only `pyforge-foundry-full-stack`
    differs.
  - In its new block, no `postgresql` or `libpq` is 18 or later, `psycopg` is 3.2.10, and `pgvector` (if present) is
    0.8.1.
  - `pixi.toml` changed only in the `pyforge-foundry-full-stack` line, or by the fallback feature plus that line.
- **(8) Every derived file is regenerated by its own tool.** `environment.yaml`, `docs/reference/environments.md` and
  `docs/foundry/sbom-gaps.md` match their generators. `sbom-gaps-check` exits 0, and so do `llms-full-check` and
  `upstream-todos-check`. The `feature:platform-ci-test` row and the four `pin:` rows named in the Approach leave
  `sbom-gaps.md`.
- **(9) Only a missing Langflow is skipped.** With `langflow` importable but `langflow.main`'s `create_app` raising, the
  import of `config.asgi` fails with that error. Story 87.1's helper tests cover the `ModuleNotFoundError`-naming-another
  case.
- **(10) Mutations fail the tests.** Restoring the unconditional Langflow import fails (1). Entering a Langflow lifespan
  when it is absent fails (3). Dropping `platform-ci-test` from the full-stack env fails the steward meta-test (5).
- **(11) Gates.** These are green:
  - `pixi run --frozen -e pyforge-steward pyforge-steward-test`;
  - `pixi run -e pyforge-guild pyforge-station-tests` (`pixi.toml` changed);
  - `pixi run -e pyforge-guild platform-ci-local -- --test`;
  - `pixi run --frozen -e pyforge-guild lint-types`.

  Every Spec `spec-surface-check` names gets a memlog entry and one scoped stamp. `pixi.toml` alone has several
  governors; reconcile each one the detector names.

## Boundaries & Constraints

**Always:**
- Change only these paths:
  - `src/platform/config/asgi.py`;
  - `src/platform/config/lifespan.py` (new);
  - `src/platform/config/optional_components.py`, only if a Langflow case needs a helper change, which keeps Story
    87.1's tests green;
  - `src/platform/langflow_integration/asgi.py`, the move and re-export only;
  - `src/platform/tests/test_host_boots_without_langflow.py` (new);
  - `pixi.toml`, `pixi.lock` and `environment.yaml`;
  - `docs/reference/environments.md` and `docs/foundry/sbom-gaps.md`, through their generators;
  - `docs/reference/library-llms-full.md`, only if `llms-full-check` reds, through the catalog's reconciler;
  - `src/shared/packages/pyforge-steward/tests/meta/test_full_stack_runs_the_platform_host.py` (new).
- Run `pixi lock` and every pixi task from the repo root.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Never run `pixi add`, `pixi update`, or `pixi install` without `--frozen` against a changed manifest to "see what
  happens".
- Never compose `python-agent-platform` (Langflow) into the full-stack env.
- Never add `pyforge-herald` to the image feature.
- Never change `[feature.platform-ci-test]`'s entries, `[feature.python-agent-platform]` or `[feature.platform-dev]`.
  The image, `platform-dev` and Platform CI envs stay byte-identical in `pixi.lock`.
- Never raise a `postgresql` or `libpq` pin to 18, or lift a psycopg, psycopg2 or pgvector cap, to clear the solve.
- Never hand-edit `sbom-gaps.md`, `environments.md`, `environment.yaml`, `SPEC.md` or `sprint-status-ledger.yaml`.
- Never write `import pyforge` or `from pyforge` under `src/platform/`.
- Never change the deployed stage-1 refusal for `LANGFLOW_SUPERUSER_PASSWORD` (`config/startup/stage_one.py:103`). A
  deployed image always carries Langflow, and the local runtime skips stage 1.
- Never flip herald's `19-2-…` ledger key. It is herald's to write.

## I/O & Edge-Case Matrix

| Env / request | Verdict |
|---|---|
| Langflow present (stub or real), any path | as today; no WARNING |
| Langflow absent, `import config.asgi` | exit 0; one WARNING naming langflow |
| Langflow absent, `/langflow/…`, `/health`, `/health_check` | 404, `{"detail": "langflow is not installed on this host: No module named 'langflow'"}` (the name is `exc.name`) |
| Langflow absent, `/api/…` | FastAPI seam, as today |
| Langflow absent, lifespan | startup and shutdown complete; FastAPI and MCP lifespans entered |
| `langflow` importable, `create_app()` raises | import fails with that error |
| `pyforge-foundry-full-stack`, `import config.asgi` | exit 0 |
| `pyforge-foundry-full-stack`, herald health / openapi | 200 / 200 |
| solve with `platform-ci-test` fails | fallback `platform-host`; if that fails too, stop and record |

</intent-contract>

## Binding

- Parent Spec capabilities: `spec-pyforge-unifying-strategy` CAP-10 (the host half; Story 11.1's mount), and
  `spec-python-foundry-cutover` fnd:CAP-12 (the layer env) with fnd:CAP-13 (the re-derived gap list).
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-10 (host without Langflow) entry.
- Epic: Epic 87.
- Ledger key: `87-2-the-platform-host-boots-without-langflow-and-the-full-stack-env-runs-it`.
- Ledger status at mint: `backlog`.
- Deps: S-87.1, for its `optional_components` helper. Marshal's `Deps:` parser orders the two inside this station.
- Cross-station: herald's Story 19.2 live proof runs `config.asgi:application` from `pyforge-foundry-full-stack`, so it
  waits on this story. Marshal's `Deps:` parser is station-local, so herald's chain holds that gate as its own row. The
  operator's 2026-10-10 ruling pre-authorises flipping herald's
  `19-2-one-real-ship-records-itself-against-a-persistent-store` key to `backlog` once this story is `done` on `main`.
  That flip is herald's write; this story never touches herald's ledger.
- Spec: the `spec-pyforge-unifying-strategy`, `spec-python-foundry-cutover` and `spec-pyforge-steward` memlogs record
  the ruling, the evidence and the mint. `SPEC.md` files are untouched and no CAP is minted.
- Surface: Epic 87's `[epic_surfaces]` entry holds every path in the Always list.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks (not a dispatch gate):**
- AC (6)'s proof command — expected: exit 0.
- AC (7)'s per-environment lock comparison — expected: only `pyforge-foundry-full-stack` differs.
- `pixi run -e pyforge-guild sbom-gaps-check`, `pixi run -e pyforge-guild llms-full-check` and
  `pixi run -e pyforge-guild upstream-todos-check` — expected: exit 0 each.
- `pixi run -e pyforge-guild pyforge-station-tests`, `pixi run -e pyforge-guild platform-ci-local -- --test` and
  `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0 each.
- The three mutations of AC (10) — expected: each fails its named test.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlogs and scoped stamps.

## Named, not fixed here

- Herald's `mcp >=2.2.0` against Langflow's `mcp <2.0.0` keeps the two out of one env. Narrowing herald's dependency,
  for example by moving `mcp` to an extra since its only import is function-level, is herald's chain and is not asked
  for here.
- The deployed image keeps Langflow and has no herald. Story 87.1 keeps it importable.

## Spec Change Log

- 2026-10-10: minted from the operator's ruling "Host without langflow". The ruling names celery, django-environ and
  wagtail. The mint measured the gap at 30 host packages and meets the ruling's goal by composing Platform CI's host set.
  The three named packages are in that set at Platform CI's pins.

- 2026-10-10 (later): **retired before dispatch.** The operator ruled "Via the sidecar (Recommended)": "Mint a steward
  story: mcp-host env gains pyforge-herald; the sidecar mounts herald's webhook ASGI; the host forwards
  /stations/herald/api/v1/webhooks/* to MCP_HOST_SIDECAR_BASE_URL like MCP. 19.2's proof runs host + sidecar locally
  (loopback). 87.1 stays (host never imports herald); 87.2's full-stack composition can be dropped." Story 87.3
  replaces this one. Status `ready-for-dev` → `blocked`, ledger `backlog` → `blocked`; nothing else in this file
  changed.

## Review Triage Log

- No review has run yet.
