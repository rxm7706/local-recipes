---
title: "87.1: The platform host boots without Herald and says why"
type: 'fix'
created: '2026-10-10'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-43-2-station-api-contract-and-the-api-v1-collision.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-19-1-the-webhook-routes-move-onto-the-station-api-seam.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/deferred-work-ledger.md
  - src/platform/config/station_api.py
  - src/platform/config/asgi.py
  - src/platform/tests/test_station_api_host_dispatch.py
  - src/platform/tests/test_station_api_seam.py
  - src/platform/tests/meta/test_no_pyforge_import.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/station_api.py
  - docs/dreams/pyforge-steward.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the platform host cannot start in any env that does not carry `pyforge-herald`. Herald is an optional
station on the host, but a missing herald stops `import config.asgi`.

- **The ruling.** On 2026-10-10 the operator chose, verbatim "Yes, lazy import story": "Mint a fix story:
  _register_herald_v1 imports herald lazily (or the herald mount is skipped with a logged reason when the package is
  absent), plus a test that config.asgi imports without pyforge-herald installed."
- **What the code does on `2d90c634f3`:**
  - `src/platform/config/station_api.py:166`-`:168` seeds warden v1 and herald v1 at import time.
  - `register_station_api` (`:142`) builds the sub-app through `_build_station_app` (`:126`), which calls
    `_register_herald_v1` (`:113`) for herald v1 (`:137`-`:138`).
  - `_register_herald_v1` defines a host-side `herald_health` route (`:116`-`:118`), then loads herald's mount helper
    by name, `importlib.import_module("pyforge.herald.station_api")` (`:122`), with no guard. The comment at
    `:120`-`:121` explains why the name is a string: `src/platform/` never imports `pyforge.*` (pap:AD-2).
  - Herald's `attach_webhook_asgi` (`src/shared/packages/pyforge-herald/src/pyforge/herald/station_api.py:30`-`:37`)
    wires the deck-export and deck-twin routes from `django_herald_portal` and mounts the lazy webhook app at `/`.
  - `config/asgi.py:55`-`:56` imports `config.station_api`, so the seed runs whenever the host is imported. Its
    station-API branch (`:134`-`:145`) answers a `KeyError` from `station_application` with 404
    `{"detail": "Not Found"}`.
- **Where herald is installed.** Only `platform-ci-test` carries `pyforge-herald` (`pixi.toml:410`, added by Story 19.1
  "for importlib mount"). The image env does not (`src/platform/Containerfile:90`,
  `pixi install --frozen -e python-agent-platform`), and neither does `platform-dev`. Their `pixi.lock` blocks hold no
  `pyforge-herald`.
- **The failure, reproduced 2026-10-10.** In `platform-dev`, `import config.asgi` stops with `ModuleNotFoundError: No
  module named 'pyforge.herald'`: `config/asgi.py:55` → `station_api.py:168` → `:146` → `:138` → `:122`. The image was
  not built, because container builds are paused (`PAUSE_PLATFORM_CONTAINER_BUILDS`).
- **Why nothing caught it.** Story 19.1's review rejected the finding "importlib crash when pyforge-herald absent" as
  `[false]`, because `platform-ci-test` now carries herald
  (`_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-19-1-the-webhook-routes-move-onto-the-station-api-seam.md:93`).
  No herald deferred-work row recorded it until this mint added `DW-herald-19-1`.
- **Why herald does not simply join the image.** Adding `pyforge-herald` to `[feature.python-agent-platform]` does not
  solve (2026-10-10): herald declares `mcp >=2.2.0`, and every langflow-base 1.12.x pins `mcp >=1.28.0,<2.0.0`. So the
  image and `platform-dev` stay without herald, and this story is what keeps them importable.

**Approach:** skip herald's mount with a logged reason. Do not import it lazily.

- **Why not a lazy import.** A lazy import moves the failure to the first request. The host-side `herald_health` route
  would answer 200 while every webhook and deck route failed with a 500, and the reason would surface per request or not
  at all. Skipping at registration fails once, at boot, and every herald path then answers the same honest 404.
- **One helper, `src/platform/config/optional_components.py` (new).** It is stdlib only at module level, and Story 87.2
  reuses it for Langflow.
  - `import_optional(module: str, *, component: str, provided_by: str, remedy: str) -> ModuleType | None` imports
    `module` with `importlib.import_module`.
  - It treats the component as absent only when the import raises `ModuleNotFoundError` and `exc.name` is
    `provided_by`, a parent package of it, or a submodule of it. For herald: `module="pyforge.herald.station_api"`,
    `provided_by="pyforge.herald"`, so `pyforge`, `pyforge.herald` and `pyforge.herald.station_api` count as absent.
  - When absent, it records the component's reason, emits one WARNING record on the `config.optional_components`
    logger, and returns `None`. The reason reads `<component> is not installed on this host: No module named
    '<exc.name>'`, and the log record adds the remedy.
  - Any other exception propagates unchanged. That includes a `ModuleNotFoundError` naming an unrelated module, such as
    `django_herald_portal` or a dependency of herald's.
  - `absent_reason(component: str) -> str | None` returns the recorded reason, and the module keeps nothing else.
- **`station_api.py`.**
  - Herald's module is loaded through `import_optional` before any herald route is defined.
  - When it returns `None`, herald v1 is not added to `_station_apps`: no sub-app, no host-side health route, no
    OpenAPI document.
  - When it returns the module, registration is exactly today's.
  - The `:120`-`:121` comment is kept, and the module name stays a string literal.
- **`asgi.py`.** The `KeyError` branch answers 404 with `{"detail": absent_reason(station)}` when the station has a
  recorded reason. Otherwise it keeps today's exact `{"detail": "Not Found"}`.
- **Tests, in `src/platform/tests/test_host_boots_without_herald.py` (new).**
  - The host-level cases run `config.asgi` in a fresh interpreter, a `subprocess` started with the parent's
    `sys.path`, `DJANGO_SETTINGS_MODULE=config.settings.test` and `COMPONENT_RUNTIME=local`. The interpreter installs a
    meta-path finder that raises `ModuleNotFoundError(name=fullname)` for `pyforge.herald` and every
    `pyforge.herald.*`. It installs the same `langflow` / `langflow.main` stub the in-process host tests install, until
    Story 87.2 lands.
  - A fresh interpreter is required because `config.asgi` is imported once per pytest process, by modules that need
    herald present. An in-process test would depend on collection order.
  - The helper's own cases run in-process against throwaway packages under `tmp_path`.

Ledger key: `87-1-the-platform-host-boots-without-herald-and-says-why`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- **Shipped behaviour:** `spec-pyforge-unifying-strategy` CAP-10, "Failure is contained": a failing dependency degrades
  its caller instead of cascading. An optional station whose package is absent takes the whole host down today. The
  seam is CAP-6's versioned station API (Story 43.2). This story mints no CAP and changes no `SPEC.md` text.
- **pap:AD-2** (the host never imports `pyforge.*`): the helper takes module names as strings. The import-linter
  contract (`src/platform/pyproject.toml` `[tool.importlinter]`) reads import statements, so a string is outside its
  scope, as Story 19.1's load already is.
- **Precedent in the same file:** `config/asgi.py:214`-`:237` already loads steward's events WebSocket app by name and
  closes the socket with 4403 on `ImportError`. This story gives the HTTP side the same posture, with a narrower catch.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag.
- **Epic.** Epics 43 (the seam) and 11 (the host) are `done`, so this fix opens Epic 87.

## Acceptance Criteria

- **(1) The host imports without herald.** Given a fresh interpreter whose meta-path finder refuses `pyforge.herald` and
  its submodules When it runs `import config.asgi` Then it exits 0. `[s for s, _v, _a in
  config.station_api.iter_station_apps()]` contains `warden` and not `herald`.
- **(2) One reason is logged.** In that same run, the interpreter's combined stdout and stderr carry the reason exactly
  once. It names `herald` and `pyforge.herald`.
- **(3) Herald's paths answer 404 with the reason.** In that same interpreter, through `httpx.ASGITransport` on
  `config.asgi.application`:
  - `GET /stations/herald/api/v1/health`, `GET /stations/herald/api/v1/openapi.json` and `POST
    /stations/herald/api/v1/webhooks/on-ship` each return 404 with JSON `{"detail": <the reason>}`.
  - `GET /stations/unknown/api/v1/health` returns 404 with exactly `{"detail": "Not Found"}`.
  - `GET /stations/warden/api/v1/health` returns 200 with `{"status": "ok", "station": "warden"}`.
- **(4) Only a missing herald is skipped.** Given a throwaway package under `tmp_path` whose `__init__` imports a module
  that does not exist When `import_optional` loads it Then the `ModuleNotFoundError` naming that module propagates.
  Given a module name that does not exist at all, or whose parent package does not, it returns `None` and
  `absent_reason` returns the reason. The same reason is not logged twice in one process.
- **(5) With herald present, nothing changes.** In `platform-ci-test`, these pass without edits:
  `tests/test_station_api_host_dispatch.py` (herald openapi, health, legacy 404, unsigned webhook 401),
  `tests/test_station_api_seam.py`, `tests/test_herald_deck_exports.py` and `tests/test_herald_portal_deck_viewer.py`.
  No WARNING record from `config.optional_components` is emitted.
- **(6) The import boundary holds.** `src/platform/tests/meta/test_no_pyforge_import.py` (`lint-imports`) passes.
  Steward's `tests/meta/test_object_store_seam_boundaries.py` passes with its allowlist unchanged. Scribe's and warden's
  `test_src_platform_has_no_pyforge_import` pass. `git diff origin/main -- src/platform` contains neither `import
  pyforge` nor `from pyforge`, comments and docstrings included.
- **(7) The deferral closes.** Herald's `DW-herald-19-1` row carries the closed status that ledger uses. A dated
  `verified:` line cites the guard (path:line) and the test names for (1)-(3).
  `pixi run -e pyforge-guild deferred-work-check` exits 0.
- **(8) Mutations fail the tests.** Restoring the unguarded `importlib.import_module` fails (1). Widening the catch to
  any `ImportError`, or to any `ModuleNotFoundError`, fails (4). Answering an absent station with `{"detail": "Not
  Found"}` fails (3).

## Boundaries & Constraints

**Always:**
- Change only these paths:
  - `src/platform/config/station_api.py`;
  - `src/platform/config/asgi.py`, the station-API 404 branch only;
  - `src/platform/config/optional_components.py` (new);
  - `src/platform/tests/test_host_boots_without_herald.py` (new);
  - herald's `deferred-work-ledger.md`, the `DW-herald-19-1` row only.
- Keep every module name a string literal passed to `importlib`.
- Log one record per absent component per process.
- Co-governors: `src/platform/**` is governed by `spec-pyforge-unifying-strategy`. Add a memlog entry on every Spec
  `spec-surface-check` names, then `git add`. Run one scoped stamp per named Spec from a clean tree, re-run the check and
  read its exit code.

**Never:**
- Never write `import pyforge` or `from pyforge` anywhere under `src/platform/`, comments included. Scribe's
  meta-test reads the diff text.
- Never edit herald's package, tests, specs, epics or ledger rows other than `DW-herald-19-1`. Herald's Story 19.2 is
  herald's chain.
- Never add `pyforge-herald` to `[feature.python-agent-platform]` or `[feature.platform-dev]`. It does not solve, and
  the env layer is Story 87.2's.
- Never answer 200 from a herald route when herald is absent.
- Never change the unknown-station 404 body.
- Never catch a bare `ImportError` or `Exception` around the load.
- Never hand-edit `SPEC.md` or `sprint-status-ledger.yaml`.

## I/O & Edge-Case Matrix

| Env / request | Verdict |
|---|---|
| herald present (`platform-ci-test`), any herald path | as today; no WARNING |
| herald absent, `import config.asgi` | exit 0; one WARNING naming herald and `pyforge.herald` |
| herald absent, `GET /stations/herald/api/v1/health` | 404, `{"detail": "herald is not installed on this host: No module named 'pyforge.herald'"}` (the name is whatever `exc.name` reported) |
| herald absent, `GET …/openapi.json` or `POST …/webhooks/on-ship` | 404, same detail |
| herald absent, `GET /stations/warden/api/v1/health` | 200, as today |
| any env, `GET /stations/unknown/api/v1/health` | 404, `{"detail": "Not Found"}`, as today |
| herald present, `django_herald_portal` missing | import fails, naming `django_herald_portal` (not skipped) |
| no `pyforge` package at all | treated as herald absent (`exc.name == "pyforge"`) |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-unifying-strategy` CAP-10, over Story 43.2's station API seam (CAP-6). Heals
  herald Story 19.1, recorded as herald's `DW-herald-19-1`.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-10 (herald absent) entry.
- Epic: Epic 87 (new; Epics 11 and 43 are `done`).
- Ledger key: `87-1-the-platform-host-boots-without-herald-and-says-why`; `epic-87` and `epic-87-retrospective` minted
  with it.
- Ledger status at mint: `backlog`.
- Deps: —. Independent of herald's Story 19.2 and of Story 87.2. Story 87.2 reuses this story's helper, so it depends
  on this one.
- Interaction: herald's 2026-10-10 attempt to put `pyforge-herald` into the image feature did not solve (the `mcp`
  conflict above). Had it landed, the image and `platform-dev` would carry herald and this story's skip would not fire
  there. It still guards every env or image that lacks herald.
- Spec: the `spec-pyforge-unifying-strategy` and `spec-pyforge-steward` memlogs record the ruling, the evidence and the
  mint. `SPEC.md` is untouched and no CAP is minted.
- Surface: Epic 87's `[epic_surfaces]` entry holds `src/platform/config/**`, `src/platform/tests/**` and herald's
  `deferred-work-ledger.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks (not a dispatch gate):**
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: exit 0, including the new test file and the
  four herald host test files of AC (5).
- The three mutations of AC (8) — expected: each fails its named test.
- `pixi run -e pyforge-guild deferred-work-check` — expected: exit 0 with `DW-herald-19-1` closed.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlogs and scoped stamps.
- `git diff origin/main -- src/platform` searched for `import pyforge` and `from pyforge` — expected: no match.

## Spec Change Log

- 2026-10-10: minted from the operator's ruling "Yes, lazy import story". The skip-with-reason branch of the ruling is
  chosen over the lazy import, for the reason in the Approach.

## Review Triage Log

- No review has run yet.
