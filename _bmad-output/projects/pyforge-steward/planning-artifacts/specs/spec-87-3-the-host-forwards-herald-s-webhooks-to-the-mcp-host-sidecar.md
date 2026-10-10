---
title: "87.3: The host forwards Herald's webhooks to the mcp-host sidecar"
type: 'feature'
created: '2026-10-10'
status: 'in-review'
baseline_revision: '5f141b983ec9ed60127f0706c5d5e3a82e5198a3'
review_loop_iteration: 0
followup_review_recommended: false
flag:
  key: pyforge.steward.herald_webhook_sidecar
  provider: openfeature-file
  default: {production: off, staging: off, dev: on}
  scope: global
  fallback: "Story 87.1's behaviour: the host serves herald's webhook in-process when pyforge-herald is installed and answers 404 with the absent reason when it is not; nothing is forwarded"
  cleanup: 90 days after ON in every environment (Q4)
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-mcp-era-isolation/retire-skip.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-mcp-era-isolation/cluster-required.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-87-1-the-platform-host-boots-without-herald-and-says-why.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-87-2-the-platform-host-boots-without-langflow-and-the-full-stack-env-runs-it.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-19-2-one-real-ship-records-itself-against-a-persistent-store.md
  - src/platform/config/asgi.py
  - src/platform/config/station_api.py
  - src/platform/config/optional_components.py
  - src/platform/mcp_host/app.py
  - src/platform/compose/mcp-host/Containerfile
  - src/platform/compose/compose.yml
  - src/platform/deploy/charts/platform/templates/_helpers.tpl
  - src/shared/packages/django-pyforge/src/django_pyforge/mcp_http.py
  - src/shared/packages/django-pyforge/src/django_pyforge/flags.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/webhook.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/webhook_host.py
  - src/shared/packages/pyforge-herald/pixi.toml
  - src/platform/tests/test_mcp_host_sidecar.py
  - src/platform/tests/test_host_boots_without_herald.py
  - pixi.toml
  - docs/explanation/platform-deployment-architecture.md
  - docs/reference/story-spec-flag-block.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** herald's webhook cannot run in the platform's image env, and the host has nowhere else to reach it.

- **The image env cannot hold herald.** `pyforge-herald` declares `mcp >=2.2.0`
  (`src/shared/packages/pyforge-herald/pixi.toml:34`). In `pixi.lock`, `langflow-base 1.12.3` requires
  `mcp >=1.28.0,<2.0.0` and `lfx 1.12.3` requires `mcp >=1.17.0,<2.0.0`. Adding herald to
  `[feature.python-agent-platform]` does not solve for `platform-dev` (`pixi lock`, 2026-10-10): "pyforge-herald 0.1.0
  would require mcp >=2.2.0", while "langflow-base 1.12.4 would require mcp >=1.28.0,<2.0.0" and 1.12.3 the same. The
  image env and `platform-dev` lock `mcp 1.28.1`.
- **Story 87.1 keeps the host up, without the webhook.** With herald absent, `/stations/herald/api/v1/…` answers 404
  with the absent reason (`src/platform/config/asgi.py:134`-`:145`, `config/optional_components.absent_reason`). So
  the image host serves no webhook at all.
- **The estate already runs an mcp 2.x process beside the host.** The mcp-host sidecar (`spec-mcp-era-isolation`,
  steward CAP-68 and CAP-69) is `src/platform/mcp_host/app.py`, built from the `mcp-host` env (`pixi.toml:372`-`:395`,
  `mcp 2.2.0` in the lock). The host forwards `POST /stations/<name>/mcp` to it when `MCP_HOST_SIDECAR_BASE_URL` is set
  (`django_pyforge/mcp_http.py`, `dispatch_station_mcp` and `proxy_station_mcp`).

**The ruling.** On 2026-10-10 the operator chose, verbatim label "Via the sidecar (Recommended)": "Mint a steward story:
mcp-host env gains pyforge-herald; the sidecar mounts herald's webhook ASGI; the host forwards
/stations/herald/api/v1/webhooks/* to MCP_HOST_SIDECAR_BASE_URL like MCP. 19.2's proof runs host + sidecar locally
(loopback). 87.1 stays (host never imports herald); 87.2's full-stack composition can be dropped." Story 87.2 is retired
by the same ruling (its spec's banner).

**Approach:**

- **Env.** `[feature.mcp-host.dependencies]` gains `pyforge-herald = { path = "src/shared/packages/pyforge-herald" }`.
  Solve with `pixi lock`; the session hook denies a live `pixi add` or `pixi update`. Only the `mcp-host` environment
  composes the feature (`pixi.toml:1140`), so only its lock block may move. Herald's run-deps (`pyforge-core`,
  `playwright`, `boto3`, `python-pptx`, `fastapi`, `asgiref`) join the env; the memlog records the env's size before
  and after.
- **Sidecar.** `mcp_host/app.py` serves every path under `/stations/herald/api/v1/webhooks/` with herald's webhook
  ASGI app, the path unchanged (herald routes on the full path: `webhook.ON_SHIP_PATH` and `ON_PR_CLOSE_PATH`,
  `webhook.py:183`-`:184`).
  - It loads `pyforge.herald.webhook_host` by module name (`importlib`) on the first webhook request and takes its
    `application`, which herald builds lazily from `HERALD_REPO_ROOT` and `HERALD_WEBHOOK_SECRET`
    (`webhook_host.py:230`-`:241`). `src/platform/` still contains no `import pyforge` or `from pyforge` text.
  - HMAC verification stays herald's (`webhook.verify_signature`). The sidecar adds no check of its own.
  - Herald absent from the sidecar's interpreter: 404 with JSON `{"detail": …}` naming the missing module.
  - Herald's env missing (`HeraldError` from `_resolve_repo_root` or `resolve_webhook_secret`): 503 with JSON naming
    the variable. The sidecar stays up; `/health` and the MCP faces are untouched.
  - Every other sidecar path behaves as today.
- **Host.** When `MCP_HOST_SIDECAR_BASE_URL` is set and the flag is ON, `_dispatch_http` (`config/asgi.py`) forwards
  any request whose path starts with `/stations/herald/api/v1/webhooks/` to `<base><path>` (query string kept), ahead
  of the station-API branch. It mirrors `proxy_station_mcp`:
  - the method and the body pass byte-identical (herald signs the raw body);
  - only an allowlist of request headers crosses: `content-type`, `x-hub-signature-256`, `x-hub-timestamp`,
    `traceparent`, `tracestate`. No `authorization`, no `cookie`;
  - no MCP assertion and no MCP rate limit: the webhook authenticates by herald's HMAC, in the sidecar;
  - the sidecar's status and body come back, without the hop-by-hop headers `DROPPED_RESPONSE_HEADERS` names;
  - an unreachable sidecar is a 502 and one ERROR log naming the URL (CAP-69: sidecar down is loud);
  - the timeout is `proxy_timeout_seconds()`, connect `CONNECT_TIMEOUT_SECONDS`.

  The forwarder lives in `django_pyforge` beside the MCP proxy (a new `django_pyforge/sidecar_forward.py`, or a
  function in `mcp_http.py`) and reuses `sidecar_base_url()`, `proxy_timeout_seconds()` and
  `proxied_response_headers()`. The flag is read with `django_pyforge.flags.evaluate_boolean(key, default=False)`.
  - Flag OFF, or the URL unset: exactly today's behaviour. Herald is served in-process when installed
    (`platform-ci-test`), and Story 87.1's 404 with the reason answers when it is not. Nothing is forwarded.
  - Herald's other v1 paths (`/health`, `/openapi.json`, the deck export and twin routes) are never forwarded.
- **Local run.** `[feature.mcp-host.tasks]` gains `mcp-host-serve`: `uvicorn mcp_host.app:app --host 127.0.0.1 --port
  8090`, run from `src/platform` with the `PYTHONPATH` the Containerfile sets (`mcp_host`, `django_pyforge`,
  `django_marshal_portal`), pointed at their sources. It binds loopback only. Herald Story 19.2's proof starts the
  sidecar with it.
- **Flag.** `pyforge.steward.herald_webhook_sidecar`, registered in the four places `docs/reference/story-spec-flag-block.md`
  § *Registering a flag* names. Dev is ON (the local runtime's default environment). Staging and production stay OFF:
  the chart and compose do not yet hand herald's store and secret to the sidecar (next bullet), so a cluster that set
  the flag would forward to a sidecar that answers 503.
- **Recorded, not wired.** The chart's `platform.mcpHostEnv` (`_helpers.tpl:526`) and compose's `mcp-host` service
  (`compose.yml:399`) pass no `HERALD_REPO_ROOT` or `HERALD_WEBHOOK_SECRET`, and a cluster store needs a persistent
  volume, which is a deployment decision. The Containerfile needs no change: `pixi install --frozen -e mcp-host`
  installs herald into the env the runtime stage copies. Its image build is paused (`PAUSE_PLATFORM_CONTAINER_BUILDS`).
  This story opens one steward deferred-work row for the chart and compose wiring, triggered by the first non-dev
  environment that turns the flag ON.

### Living CAP citations

- **`spec-pyforge-steward` CAP-68** (isolated mcp-host env ← `spec-mcp-era-isolation` CAP-2): the env gains herald.
  Its "no Langflow, no FastMCP 3" constraint holds.
- **`spec-pyforge-steward` CAP-69** (host proxies; sidecar down is loud ← `spec-mcp-era-isolation` CAP-3): one more
  forwarded path family, under the same down-is-loud contract.
- CAP-70 (the cluster overlay requires mcp-host) is unchanged. With the flag OFF in production and staging, nothing a
  cluster serves changes.
- `spec-pyforge-unifying-strategy` CAP-10 (failure is contained): Story 87.1's skip stays. This story adds a route
  around it, never a hard dependency.
- pap:AD-2: `src/platform/` never imports `pyforge.*`.
- The estate's PostgreSQL 17 (fnd:CAP-12, AGENTS.md § Policy): no `postgresql`, `libpq`, `psycopg` or `pgvector` pin
  moves.
- **No CAP is minted.** The story widens CAP-68's env and CAP-69's forward by one route. The steward memlog records
  the widening for the next `bmad-spec` pass. `SPEC.md` is untouched.
- **A flag.** A new forwarded route through a second process is new runtime behaviour, so the story is `type:
  feature` under `spec-feature-flag-governance` Q1. None of the five `flag-exempt` values fits.
- **Deferred row `DW-steward-87-3-1`** (operator ruling 2, 2026-10-10): the trigger that ends the split, and its
  follow-ups. This story does not act on it.

## Acceptance Criteria

- **(1) The `mcp-host` env carries herald, and only its lock moves.**
  - `[feature.mcp-host.dependencies]` holds `pyforge-herald = { path = "src/shared/packages/pyforge-herald" }`, and
    `pixi lock` exits 0.
  - Comparing `pixi.lock`'s `environments:` blocks at the base and at the head, only `mcp-host` differs.
    `python-agent-platform`, `platform-dev` and `platform-ci-test` are byte-identical.
  - In the new `mcp-host` block, `mcp` is 2.x, `psycopg` is 3.2.10, and no `postgresql` or `libpq` is 18 or later.
  - `pixi.toml` changes only in `[feature.mcp-host.dependencies]` and `[feature.mcp-host.tasks]`.
  - `pixi install --frozen -e mcp-host` exits 0, and so does
    `pixi run --frozen -e mcp-host python -c "import importlib; importlib.import_module('pyforge.herald.webhook_host')"`.
- **(2) The sidecar serves herald's webhook.** In the `mcp-host` env, a stdlib-only drive of `mcp_host.app:app` over
  ASGI (the env has no pytest), with `HERALD_REPO_ROOT` a temporary directory and `HERALD_WEBHOOK_SECRET` set:
  - a signed `POST /stations/herald/api/v1/webhooks/on-ship` with a body `webhook.handle_on_ship` accepts returns 201;
  - the same body with a wrong signature returns 401, and a `GET` returns 405;
  - `GET /health` returns 200, and an unknown path keeps today's 404.
- **(3) The sidecar's edges.** In `platform-ci-test` (mcp 2.x and herald, like the sidecar's env), through
  `starlette.testclient.TestClient(mcp_host.app.app)`:
  - with a meta-path finder refusing `pyforge.herald` and its submodules, a webhook path returns 404 with JSON naming
    the missing module;
  - with `HERALD_WEBHOOK_SECRET` unset, it returns 503 with JSON naming `HERALD_WEBHOOK_SECRET`; with
    `HERALD_REPO_ROOT` unset, the JSON names `HERALD_REPO_ROOT`;
  - in each case `/health` stays 200 and the atlas MCP face still answers `initialize`.
- **(4) The host forwards, intact.** With `MCP_HOST_SIDECAR_BASE_URL` pointing at a fake sidecar and the flag ON,
  through `httpx.ASGITransport` on `config.asgi.application`, a `POST
  /stations/herald/api/v1/webhooks/on-ship?x=1` carrying body B and the headers `Content-Type`,
  `X-Hub-Signature-256`, `X-Hub-Timestamp`, `Authorization` and `Cookie`:
  - reaches the fake at the same path and query, with the same method and body B byte for byte;
  - carries `content-type`, `x-hub-signature-256` and `x-hub-timestamp` unchanged, and no `authorization` or `cookie`;
  - returns the fake's status and JSON body to the caller;
  - needs no MCP assertion.
- **(5) Sidecar down is loud.** With the URL pointing at a closed port and the flag ON, the same request returns 502,
  and exactly one ERROR record names the sidecar URL.
- **(6) Flag OFF or URL unset changes nothing.**
  - In `platform-ci-test` (herald installed), the request reaches the in-process herald v1 app, and the fake sidecar
    records no request. Every existing herald host test passes unedited (`test_station_api_host_dispatch.py`,
    `test_station_api_seam.py`, `test_herald_deck_exports.py`, `test_herald_portal_deck_viewer.py`).
  - With herald refused by Story 87.1's meta-path finder, the request returns 87.1's 404 with the absent reason, and
    the fake records nothing. `test_host_boots_without_herald.py` passes unedited.
- **(7) Only webhooks are forwarded.** With the URL set and the flag ON, `GET /stations/herald/api/v1/health` and
  `GET …/openapi.json` behave exactly as with the flag OFF (200 in-process, or 87.1's 404), and the fake records no
  request. `GET /stations/warden/api/v1/health` returns 200.
- **(8) MCP forwarding is unchanged.** `src/platform/tests/test_mcp_host_sidecar.py` and
  `src/platform/tests/test_mcp_transport_auth.py` pass unedited. `POST /stations/atlas/mcp` without an assertion is
  still refused.
- **(9) The flag is registered.** `pyforge.steward.herald_webhook_sidecar` is in `src/platform/config/flags.json`, in
  `src/platform/config/flag-overlays.json` (`dev` on, `staging` off, `production` off), in
  `src/shared/packages/pyforge-core/tests/unit/test_flags.py` and in `src/platform/tests/test_openfeature_file_flags.py`
  (`_SHIPPED_BOOLEANS`). `flag-gate-check` exits 0, and `flag-gate-check --spec <this spec>` returns `pass`.
- **(10) The sidecar runs locally on loopback.** `pixi run --frozen -e mcp-host mcp-host-serve` starts it; `ss -ltnH`
  shows `127.0.0.1:8090` and no wildcard bind for that port, and `GET http://127.0.0.1:8090/health` returns
  `{"status":"ok"}`.
- **(11) The docs name the route.** `docs/explanation/platform-deployment-architecture.md`, where it describes the
  mcp-host sidecar, names `/stations/herald/api/v1/webhooks/*`, the flag, the header allowlist, where the signature is
  verified, and `mcp-host-serve`. `docs-currency-check` and `docs-map-hygiene-check` exit 0.
- **(12) Derived files come from their tools.** `environment.yaml` is regenerated with `pixi project export
  conda-environment -e build > environment.yaml`. `docs/reference/environments.md` comes from `docs-environments`,
  `docs/foundry/sbom-gaps.md` from `sbom-gaps-check -- --write-doc` if that check reds, and
  `docs/reference/library-llms-full.md` from the catalog's reconciler if `llms-full-check` reds. `sbom-gaps-check`
  and `llms-full-check` exit 0.
- **(13) The follow-up is a row.** Steward's `deferred-work-ledger.md` gains one row for the chart's
  `platform.mcpHostEnv` and compose's `mcp-host` service: herald's two variables, the store's persistent volume, and
  an image build once `PAUSE_PLATFORM_CONTAINER_BUILDS` lifts. Its trigger is the first non-dev environment that
  turns the flag ON.
- **(14) Mutations fail the tests.** Removing the forward branch fails (4). Forwarding without the flag check fails
  (6). Adding `authorization` to the allowlist fails (4). Dropping the path dependency fails (1)'s import.
- **(15) Gates.** These are green:
  - `pixi run --frozen -e pyforge-steward pyforge-steward-test`;
  - `pixi run -e pyforge-guild pyforge-station-tests` (`pixi.toml` changed);
  - `pixi run -e pyforge-guild platform-ci-local -- --test`;
  - `pixi run --frozen -e pyforge-guild lint-types`.

  Every Spec `spec-surface-check` names gets a memlog entry and one scoped stamp.

## Boundaries & Constraints

**Always:**
- Change only these paths:
  - `pixi.toml` (`[feature.mcp-host.dependencies]`, `[feature.mcp-host.tasks]`), `pixi.lock`, `environment.yaml`;
  - `src/platform/mcp_host/app.py`;
  - `src/platform/config/asgi.py`, and `src/platform/config/flags.json` and `flag-overlays.json` for the flag;
  - `src/shared/packages/django-pyforge/src/django_pyforge/mcp_http.py` or a new
    `src/shared/packages/django-pyforge/src/django_pyforge/sidecar_forward.py`;
  - `src/platform/tests/` (new tests; `test_openfeature_file_flags.py` for the flag);
  - `src/shared/packages/pyforge-core/tests/unit/test_flags.py`, for the flag only;
  - `docs/explanation/platform-deployment-architecture.md`;
  - `docs/reference/environments.md`, `docs/foundry/sbom-gaps.md` and `docs/reference/library-llms-full.md`, through
    their generators only;
  - `docs/governance/flag-inventory/`, through `flag-inventory` only;
  - steward's `deferred-work-ledger.md`, for AC (13)'s row.
- Run `pixi lock` and every pixi task from the repo root. Read every verdict from the exit code, never through a pipe.

**Never:**
- Never add `pyforge-herald` to `[feature.python-agent-platform]` or `[feature.platform-dev]`, and never compose the
  `mcp-host` feature into another environment.
- Never move an `mcp`, `psycopg`, `libpq`, `postgresql` or `pgvector` pin to clear the solve.
- Never run `pixi add`, `pixi update`, or `pixi install` without `--frozen` against a changed manifest.
- Never verify the webhook signature in the host, and never forward `authorization`, `cookie` or any header off the
  allowlist.
- Never forward a herald path outside `/stations/herald/api/v1/webhooks/`.
- Never write `import pyforge` or `from pyforge` under `src/platform/`.
- Never change herald's code, the chart, compose or the Containerfile. The chart and compose are AC (13)'s row.
- Never hand-edit `SPEC.md`, `sprint-status-ledger.yaml`, or a derived file.
- Never flip herald's `19-2-…` ledger key. It is herald's to write.

## I/O & Edge-Case Matrix

| State / request | Verdict |
|---|---|
| URL set, flag ON, `POST …/webhooks/on-ship` | forwarded; sidecar's status and body returned |
| URL set, flag ON, sidecar down | 502, one ERROR log naming the URL |
| URL set, flag OFF | today's: in-process herald, or 87.1's 404 with the reason |
| URL unset, flag ON | today's |
| URL set, flag ON, `GET …/herald/api/v1/health` | not forwarded; today's |
| inbound `Authorization` / `Cookie` | dropped at the host |
| sidecar, herald absent | 404, JSON naming the module |
| sidecar, `HERALD_WEBHOOK_SECRET` or `HERALD_REPO_ROOT` unset | 503, JSON naming the variable; `/health` 200 |
| sidecar, bad signature | herald's 401 |
| `POST /stations/<name>/mcp` | today's MCP path (assertion, rate limit, proxy) |

</intent-contract>

## Binding

- Parent Spec capabilities: `spec-pyforge-steward` CAP-68 (the env) and CAP-69 (the forward), both from
  `spec-mcp-era-isolation`. CAP-10 of `spec-pyforge-unifying-strategy` stays met through Story 87.1.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-10 (herald via the sidecar) entry.
- Epic: Epic 87.
- Ledger key: `87-3-the-host-forwards-herald-s-webhooks-to-the-mcp-host-sidecar`.
- Ledger status at mint: `backlog`.
- Deps: S-87.1 (`done`), for the absent-herald 404 this story keeps as its fallback.
- Cross-station: herald's Story 19.2 live proof runs the platform host from `platform-dev` and this sidecar, both on
  loopback, so it waits on this story. Marshal's `Deps:` parser is station-local, so herald's chain holds the gate as
  its own row, `blocked`. That flip is herald's write; this story never touches herald's ledger.
- Deferred: `DW-steward-87-3-1` (the trigger that ends the split) is recorded with this mint and stays open.
- Spec: the `spec-pyforge-steward`, `spec-pyforge-unifying-strategy`, `spec-python-foundry-cutover` and
  `spec-mcp-era-isolation` memlogs record the ruling, the retirement of 87.2 and this mint. No `SPEC.md` changes.
- Surface: Epic 87's `[epic_surfaces]` entry holds every path in the Always list.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks (not a dispatch gate):**
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: exit 0, including the new forward and sidecar
  tests and the unedited files of ACs (6) and (8).
- `pixi lock` and AC (1)'s per-environment comparison — expected: only `mcp-host` differs.
- AC (2)'s stdlib drive in the `mcp-host` env — expected: exit 0.
- AC (10)'s local run — expected: loopback bind and `/health` 200.
- `pixi run -e pyforge-guild sbom-gaps-check` and `pixi run -e pyforge-guild llms-full-check` — expected: exit 0 each.
- `pixi run -e pyforge-guild flag-gate-check` and `… flag-gate-check -- --spec <this spec>` — expected: exit 0 and
  `pass`.
- `pixi run -e pyforge-guild pyforge-station-tests` and `pixi run --frozen -e pyforge-guild lint-types` — expected:
  exit 0 each.
- The four mutations of AC (14) — expected: each fails its named test.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlogs and scoped stamps.
- `git diff origin/main -- src/platform` searched for `import pyforge` and `from pyforge` — expected: no match.

## Named, not fixed here

- **The split itself.** Herald and Langflow cannot share an env while langflow-base and lfx pin `mcp <2`.
  `DW-steward-87-3-1` holds the trigger and the follow-ups: retire the bridge's ImportError skip, reconsider the
  sidecar split, and let herald join the image again.
- **Herald's non-webhook routes in the image.** `/stations/herald/api/v1/health`, `openapi.json` and the deck export
  and twin routes stay 87.1's 404 there. The ruling forwards webhooks only.
- **The cluster.** AC (13)'s row: the chart, compose, the store's volume and the paused image build.

## Spec Change Log

- 2026-10-10: minted from the operator's ruling "Via the sidecar (Recommended)", which also retires Story 87.2. The
  story is `type: feature` with a flag: it adds a forwarded route through a second process, which no shipped
  behaviour covered. Flag defaults: dev ON for herald 19.2's local proof; staging and production OFF until the chart
  wires herald's store and secret.

## Review Triage Log

- No review has run yet.

## Auto Run Result

Status: in-review

Implementation on branch `dispatch/pyforge-steward/87.3`: mcp-host env carries `pyforge-herald`; sidecar serves webhook ASGI; host forwards under `pyforge.steward.herald_webhook_sidecar` + `MCP_HOST_SIDECAR_BASE_URL`; flag registered; deferred row `DW-steward-87-3-2` added.

Verification: `python scripts/spec_surface_reconcile.py` OK; `pixi run --frozen -e pyforge-steward pyforge-steward-test` 2292 passed; `platform-ci-test` herald webhook tests 13 passed; `flag-gate-check --spec` pass; `pixi install --frozen -e mcp-host` + herald import OK. `platform-ci-local --test` mypy leg still fails on pre-existing `pyforge-herald` webhook.py syntax check (unchanged herald source).
