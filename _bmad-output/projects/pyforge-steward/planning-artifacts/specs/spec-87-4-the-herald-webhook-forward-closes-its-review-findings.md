---
title: "87.4: The herald webhook forward closes its review findings"
type: 'fix'
created: '2026-10-10'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-87-3-the-host-forwards-herald-s-webhooks-to-the-mcp-host-sidecar.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-87-1-the-platform-host-boots-without-herald-and-says-why.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-19-2-one-real-ship-records-itself-against-a-persistent-store.md
  - src/shared/packages/django-pyforge/src/django_pyforge/sidecar_forward.py
  - src/shared/packages/django-pyforge/src/django_pyforge/mcp_dual_era.py
  - src/platform/config/asgi.py
  - src/platform/mcp_host/app.py
  - src/platform/config/flag-overlays.json
  - src/platform/tests/test_herald_webhook_sidecar.py
  - src/platform/tests/test_host_boots_without_herald.py
  - src/platform/tests/test_openfeature_file_flags.py
  - src/shared/packages/pyforge-core/tests/unit/test_flags.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/webhook.py
  - pixi.toml
  - docs/explanation/platform-deployment-architecture.md
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 87.3 landed on `main` (merge `85e70dedf5`, spec promoted to `done` by `a8eae09dce`) with its
independent review's findings unfixed. The review is recorded in 87.3's spec, `## Review Triage Log`, entry
"2026-10-10 — Independent review, iteration 1: FAIL (3 high, 3 medium)". Five of its `[patch]` items are code defects
this story closes. The sixth, the corrupted `environment.yaml`, was closed by the 2026-10-10 hygiene change that also
turned `pyforge.steward.herald_webhook_sidecar` OFF in every environment (merged as `c183207e67`). Line numbers below
are at `c183207e67`; every cited source file except the test file is unchanged since `a8eae09dce`.

- **[high] Dot segments reach the sidecar's MCP faces.** `is_herald_webhook_path`
  (`django_pyforge/sidecar_forward.py:38`-`:39`) checks only that the decoded path starts with
  `/stations/herald/api/v1/webhooks/`, and `_sidecar_url` (`:51`-`:57`) appends that path and the client's query
  string to the sidecar's base URL. httpx removes dot segments, so `/stations/herald/api/v1/webhooks/../../../../marshal/mcp`
  (or the same with `%2e%2e`) reached the sidecar's `POST /stations/marshal/mcp`, which the sidecar does not
  authenticate. That skips the host's MCP assertion and rate limit. `%3F` and `%23` inject a query or a fragment.
  `%0d%0a` turns into a 502 and a forged log line, because the failure log writes the URL (`:112`).
- **[high] `mcp-host-serve` cannot start.** The task (`pixi.toml:401`) sets `cwd = "src/platform"`, but its
  `PYTHONPATH` entries are written from the repo root. `pixi run -e mcp-host mcp-host-serve` exits 1 with
  `ModuleNotFoundError: django_pyforge`, and nothing binds `127.0.0.1:8090` (87.3's AC 10).
- **[medium] The host reads a webhook body with no cap.** `proxy_herald_webhook` (`:79`-`:118`) calls
  `mcp_dual_era.read_body` (`:89`), which buffers every chunk until the client stops. No secret is needed to send one.
  Herald in-process refuses past `MAX_BODY_BYTES = 1_000_000` bytes or `MAX_BODY_MESSAGES = 10_000` ASGI messages
  with a 413, before it verifies the signature (`pyforge/herald/webhook.py:217`, `:222`, `:1067`-`:1072`, `:1322`).
- **[medium] The tests do not prove 87.3's ACs 4, 6, 7 and 14.** The forward tests call
  `dispatch_herald_webhook_forward` directly with httpx patched. Nothing drives `config.asgi.application`, so
  deleting the forward branch in `config/asgi.py` (`:135`) leaves every test green. AC 3's herald-absent test patches
  `importlib.import_module` (`src/platform/tests/test_herald_webhook_sidecar.py:132`-`:144`), so the error it raises
  is not the one a missing package raises.
- **[low] The sidecar's 404 can blame the wrong module.** `_dispatch_herald_webhook` (`mcp_host/app.py:43`-`:63`)
  turns every `ModuleNotFoundError` into "pyforge.herald is not installed" (`:49`-`:55`). A missing dependency of
  herald, such as `pyforge.core.errors`, which `pyforge.herald.webhook` imports, is reported as herald being absent.

**What herald accepts.** Herald routes on two exact paths, `ON_SHIP_PATH = "/stations/herald/api/v1/webhooks/on-ship"`
and `ON_PR_CLOSE_PATH = "/stations/herald/api/v1/webhooks/on-pr-close"` (`webhook.py:183`-`:184`, matched with `==`
at `:1271`-`:1274`). Neither `webhook.py` nor `webhook_host.py` reads the query string.

**Approach:** forward only what herald serves, read no more than herald would, and prove it through the host's real
entry point.
- **An exact allowlist.** With the forward active (the flag ON and `MCP_HOST_SIDECAR_BASE_URL` set), the host
  forwards a request only when its decoded path equals one of herald's two webhook paths. Any other path under
  `/stations/herald/api/v1/webhooks/` is answered 404 by the host, with the host's usual `{"detail": "Not Found"}`
  body. Nothing is sent to the sidecar, and no log record carries the client's path.
  - `src/platform/` never imports `pyforge.*` (pap:AD-2), and the forwarder in `django_pyforge` runs in the image
    env, where `pyforge.herald` is not installed. So the forwarder spells the two paths as literals. A test reads
    herald's constants by module name (`importlib`) in `platform-ci-test`, where herald is installed, and fails if the
    literals drift.
  - The URL the host requests is the sidecar's base URL plus the matched literal. Nothing from the client's path or
    query string enters it. Herald's webhook reads no query string, so none is forwarded.
- **A capped read.** The forwarder reads the body itself, with herald's two caps (1,000,000 bytes, 10,000 messages)
  as literals checked against herald's constants by the same test. A body over either cap gets a 413 with a JSON body
  naming the cap, and the sidecar is never contacted. `mcp_dual_era.read_body`, which the MCP proxy uses, does not
  change.
- **A task that starts.** `mcp-host-serve`'s `PYTHONPATH` is anchored to `$PIXI_PROJECT_ROOT` or written relative to
  `src/platform` (the task's `cwd`), as other tasks in `pixi.toml` already do. Only `[feature.mcp-host.tasks]`
  changes; the bind stays `127.0.0.1:8090`.
- **Tests through the real entry point.** New tests drive `config.asgi.application` with `httpx.ASGITransport`
  against a fake sidecar, for 87.3's AC 4 (flag ON forwards), AC 6 (flag OFF or URL unset gives the in-process herald
  or Story 87.1's 404) and AC 7 (`openapi.json` and a non-webhook herald route are never forwarded). The flag is set
  through the FILE provider (a flagd tree), as the two-state test does, not by patching `evaluate_boolean`. AC 3's
  herald-absent case uses a meta-path finder that refuses `pyforge.herald` and its submodules, as Story 87.1's tests
  do.
- **An honest 404.** The sidecar answers 404 only when the `ModuleNotFoundError`'s `name` is `pyforge.herald` or
  starts with `pyforge.herald.`. Any other missing module is re-raised, so it surfaces as the sidecar's error and
  traceback, never as "herald is not installed".
- **The flag comes back ON in dev, last.** `pyforge.steward.herald_webhook_sidecar` is OFF in every environment since
  the 2026-10-10 hygiene change. This story turns dev back ON only after ACs (1) to (5) pass, in the same commit set:
  `src/platform/config/flag-overlays.json` (`dev` on), the two flag-default tables
  (`src/platform/tests/test_openfeature_file_flags.py` `_SHIPPED_BOOLEANS`, `src/shared/packages/pyforge-core/tests/unit/test_flags.py`),
  and 87.3's spec, whose `flag.default` and **Flag** bullet then read dev ON again (87.3 is `done`, so
  `flag-gate-check` compares its declared defaults with the tree). Staging and production stay OFF, for 87.3's
  reason: the chart and compose still hand the sidecar no herald store or secret (`DW-steward-87-3-2`).

Ledger key: `87-4-the-herald-webhook-forward-closes-its-review-findings`.
Type / Effort / Deps: fix / M / S-87.3.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-steward` CAP-68 (the isolated mcp-host env and its task) and CAP-69 (the host
  forwards to the sidecar; sidecar down is loud), both from `spec-mcp-era-isolation`. These are the CAPs Story 87.3
  bound. This story fixes the realization 87.3 shipped, so it mints no CAP and changes no `SPEC.md`.
- `spec-pyforge-unifying-strategy` CAP-10 stays met through Story 87.1: with the forward inactive, the host behaves
  exactly as before.
- pap:AD-2: `src/platform/` never imports `pyforge.*`. The allowlist and the caps are literals, checked against
  herald by a test that loads herald by module name.
- **No flag of its own.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag. It restores the behaviour
  87.3's flag was meant to gate, and it sets that flag's dev default back to ON.
- **Origin.** `docs/dreams/pyforge-steward.md` Realization log, 2026-10-10 (herald forward review findings). Operator
  ruling 2026-10-10, verbatim label: "Forward-fix (Recommended)".

## Acceptance Criteria

Every criterion runs in `platform-ci-test` (through `platform-ci-local -- --test`), where herald is installed beside
the host's packages, except AC (2)'s live run. A fake sidecar records every request it receives.

- **(1) Only herald's two webhook paths are forwarded.**
  - **Given** the flag ON and `MCP_HOST_SIDECAR_BASE_URL` pointing at the fake **When** `config.asgi.application`
    receives `POST` on each path below **Then** each answers 404 with `{"detail": "Not Found"}`, the fake records
    nothing, and no log record contains the path:
    - `/stations/herald/api/v1/webhooks/../../../../marshal/mcp`;
    - `/stations/herald/api/v1/webhooks/%2e%2e/%2e%2e/%2e%2e/%2e%2e/marshal/mcp`;
    - `/stations/herald/api/v1/webhooks/on-ship%3Fx=1`;
    - `/stations/herald/api/v1/webhooks/on-ship%23frag`;
    - `/stations/herald/api/v1/webhooks/on-ship%0d%0aInjected: 1`;
    - `/stations/herald/api/v1/webhooks/` and `/stations/herald/api/v1/webhooks/other`.
  - **Given** the same **When** a signed `POST /stations/herald/api/v1/webhooks/on-ship?x=1` arrives **Then** the fake
    records exactly one request, to `<base>/stations/herald/api/v1/webhooks/on-ship` with no query string, and
    `on-pr-close` is forwarded the same way.
  - A test loads `pyforge.herald.webhook` by module name and asserts the forwarder's two paths equal
    `ON_SHIP_PATH` and `ON_PR_CLOSE_PATH`.
- **(2) `mcp-host-serve` starts on loopback.**
  - A test reads the `mcp-host-serve` task from `pixi.toml`. It resolves each `PYTHONPATH` entry from the task's
    `cwd` (with `$PIXI_PROJECT_ROOT` read as the repo root) and asserts it is an existing directory, and that
    `mcp_host`, `django_pyforge` and `django_marshal_portal` are each found under one of them. It asserts the command
    binds `--host 127.0.0.1 --port 8090`.
  - Live (manual check): `pixi run --frozen -e mcp-host mcp-host-serve` stays up. `ss -ltnH` shows `127.0.0.1:8090`
    and no wildcard bind on 8090, and `GET http://127.0.0.1:8090/health` answers 200 with `{"status":"ok"}`.
- **(3) The host caps the body at herald's limits.**
  - **Given** the forward active **When** a `POST` to `on-ship` streams 1,000,001 bytes, and separately 10,001
    zero-length `http.request` messages **Then** the host answers 413 with a JSON body naming the cap, and the fake
    records nothing. A body of exactly 1,000,000 bytes is forwarded.
  - The test of AC (1) also asserts the forwarder's two caps equal herald's `MAX_BODY_BYTES` and
    `MAX_BODY_MESSAGES`.
- **(4) The tests go through the host's entry point.** Through `httpx.ASGITransport` on `config.asgi.application`:
  - 87.3's AC 4: with the flag ON, a signed `POST …/webhooks/on-ship` with body B and the headers `Content-Type`,
    `X-Hub-Signature-256`, `X-Hub-Timestamp`, `Authorization` and `Cookie` reaches the fake with body B byte for
    byte, the first three headers unchanged and no `authorization` or `cookie`, and the caller gets the fake's
    status and JSON body.
  - 87.3's AC 6: with the flag OFF, and separately with the URL unset, the same request reaches the in-process
    herald v1 app and the fake records nothing. With herald refused by a meta-path finder, it gets Story 87.1's 404
    with the absent reason.
  - 87.3's AC 7: with the flag ON, `GET /stations/herald/api/v1/openapi.json` and `GET …/health` answer exactly as
    with the flag OFF, and the fake records nothing.
  - 87.3's AC 3, herald absent: the sidecar test refuses `pyforge.herald` and its submodules with a meta-path finder,
    and the 404's JSON names `pyforge.herald`. No test patches `importlib.import_module`.
- **(5) The sidecar's 404 names only herald.** Through `starlette.testclient.TestClient(mcp_host.app.app)`:
  - a finder refusing `pyforge.herald` gives 404 with JSON naming it;
  - a finder refusing `pyforge.core.errors` (imported by `pyforge.herald.webhook`) gives no 404: the error
    propagates as the sidecar's own failure, and `/health` still answers 200 afterwards.
- **(6) The flag comes back ON in dev, and only in dev.**
  - `src/platform/config/flag-overlays.json` reads `dev` on, `staging` off, `production` off for
    `pyforge.steward.herald_webhook_sidecar`, and both flag-default tables expect the same.
  - 87.3's spec `flag.default` reads `{production: off, staging: off, dev: on}`. Its **Flag** bullet says dev was
    OFF from the hygiene change until this story closed the review's findings.
  - `test_herald_webhook_sidecar_flag_two_states` passes unchanged.
  - `pixi run --frozen -e pyforge-guild flag-gate-check` exits 0, and `flag-gate-check -- --spec` on 87.3's spec
    returns `pass`.
  - This change lands in the same commit set as ACs (1) to (5), never before them.
- **(7) Nothing else moves.**
  - `src/platform/tests/test_mcp_host_sidecar.py`, `test_mcp_transport_auth.py` and `test_host_boots_without_herald.py`
    pass unedited, and `POST /stations/atlas/mcp` without an assertion is still refused.
  - `pixi.toml` changes only in `[feature.mcp-host.tasks]`. `pixi.lock` does not change. `environment.yaml` parses as
    YAML and equals `pixi project export conda-environment -e build 2>/dev/null`.
  - `git diff origin/main -- src/platform` contains no `import pyforge` or `from pyforge`.
  - `docs/explanation/platform-deployment-architecture.md` names the two forwarded paths (not a `/*` family), the
    404 for anything else under the prefix, and the body caps. `docs-currency-check` exits 0.
- **(8) Mutations fail the tests.**
  - Matching the prefix again instead of the two paths fails AC (1).
  - Building the URL from the client's path or query fails AC (1).
  - Dropping either cap fails AC (3).
  - Deleting the forward branch in `config/asgi.py` fails AC (4).
  - Treating every `ModuleNotFoundError` as herald absent fails AC (5).

## Boundaries & Constraints

**Always:**
- Change only these paths:
  - `src/shared/packages/django-pyforge/src/django_pyforge/sidecar_forward.py`;
  - `src/platform/mcp_host/app.py`, and `src/platform/config/asgi.py` only if the forward branch must move;
  - `pixi.toml` (`[feature.mcp-host.tasks]` only), and `environment.yaml` only through its export command;
  - `src/platform/config/flag-overlays.json`, `src/platform/tests/` (new tests, `test_herald_webhook_sidecar.py`,
    `test_openfeature_file_flags.py`), and `src/shared/packages/pyforge-core/tests/unit/test_flags.py`, for the flag
    and the tests;
  - 87.3's spec (`flag.default` and its **Flag** bullet only);
  - `docs/explanation/platform-deployment-architecture.md`, and `docs/governance/flag-inventory/` through
    `flag-inventory` only.
- Turn the dev default ON in the same commit set as the fixes, after they pass.
- Reconcile every governed path the change touches on the memlogs of the Specs that govern it, then stamp those Specs
  scoped: `spec-pyforge-steward` and every co-governor `spec-surface-check` names (AGENTS.md pre-PR item 5).
- Run every pixi task from the repo root, and read every verdict from its exit code, never through a pipe.

**Never:**
- Never forward a path outside herald's two webhook paths, or any client query string.
- Never verify the webhook signature in the host, and never forward a header off 87.3's allowlist.
- Never write `import pyforge` or `from pyforge` under `src/platform/`, and never import `pyforge.herald` from
  `django_pyforge`.
- Never change the MCP proxy path, `mcp_dual_era.read_body`, herald's code, the chart, compose or the Containerfile.
- Never turn the flag ON in staging or production.
- Never edit 87.3's acceptance criteria, Review Triage Log or status.
- Never run `pixi add`, `pixi update` or an unfrozen install, and never hand-edit `SPEC.md`, a ledger or a derived
  file.

## I/O & Edge-Case Matrix

| Request (flag ON, URL set, unless stated) | Today (`c183207e67`) | After |
|---|---|---|
| `POST …/webhooks/on-ship` or `…/on-pr-close`, signed | forwarded, path and query kept | forwarded to the literal path, no query |
| a path under the prefix with `..` or `%2e%2e` | forwarded; httpx resolves it to the sidecar's MCP face | 404 at the host; nothing forwarded |
| `%3F`, `%23` or `%0d%0a` in the path | forwarded; a query or fragment is injected, or a 502 with a forged log line | 404 at the host; no log record with the path |
| any other path under the prefix | forwarded | 404 at the host |
| body over 1,000,000 bytes or 10,000 messages | buffered without limit, then forwarded | 413 at the host; nothing forwarded |
| flag OFF or URL unset | in-process herald, or 87.1's 404 | unchanged |
| `GET …/herald/api/v1/health` or `…/openapi.json` | not forwarded | unchanged |
| sidecar, `pyforge.herald` missing | 404 naming the module | unchanged |
| sidecar, a dependency of herald missing | 404 blaming herald | the error propagates; no 404 |
| `pixi run -e mcp-host mcp-host-serve` | exits 1, `ModuleNotFoundError: django_pyforge` | binds `127.0.0.1:8090`; `/health` 200 |

</intent-contract>

## Binding

- Parent Spec capabilities: `spec-pyforge-steward` CAP-68 and CAP-69 (both from `spec-mcp-era-isolation`), the CAPs
  Story 87.3 bound.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-10 (herald forward review findings) entry.
- Epic: Epic 87 (`in-progress`). No new epic: 87.3, whose findings this story closes, is in the same epic.
- Ledger key: `87-4-the-herald-webhook-forward-closes-its-review-findings`.
- Ledger status at mint: `backlog`.
- Deps: S-87.3 (`done` on `main`), whose code this story fixes.
- Review source: 87.3's spec, `## Review Triage Log`, "2026-10-10 — Independent review, iteration 1: FAIL (3 high, 3
  medium)". This story closes its five code items. Its `environment.yaml` item was closed by the 2026-10-10
  hygiene change.
- Cross-station: herald Story 19.2 (`19-2-one-real-ship-records-itself-against-a-persistent-store`, `blocked`) is
  gated on this story, not on 87.3. 87.3 is `done` on `main`, but its forward is dark and unsafe to turn on until
  this story lands. 19.2's spec still names 87.3 as its gate. That text and the flip of 19.2's key are herald's to
  write, after this story is `done` on `main`. This story flips no key.
- Spec: the `spec-pyforge-steward` memlog records the ruling and this mint. No `SPEC.md` changes.
- Surface: Epic 87's `[epic_surfaces]` entry already holds every path in the Always list.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: exit 0, including the new tests of ACs (1) to
  (5), `test_herald_webhook_sidecar_flag_two_states`, and the unedited files of AC (7).
- AC (2)'s live run: `pixi run --frozen -e mcp-host mcp-host-serve`, then `ss -ltnH 'sport = :8090'` and
  `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8090/health` — expected: one `127.0.0.1:8090` listener
  and `200`.
- `pixi run -e pyforge-guild pyforge-station-tests` — expected: exit 0 (`pixi.toml` changed).
- `pixi run --frozen -e pyforge-guild flag-gate-check` and `… flag-gate-check -- --spec` on 87.3's spec — expected:
  exit 0 and `pass`.
- `diff <(pixi project export conda-environment -e build 2>/dev/null) environment.yaml` — expected: no output.
- The five mutations of AC (8) — expected: each fails its named test.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconciles and scoped
  stamps.
- `git diff origin/main -- src/platform` searched for `import pyforge` and `from pyforge`, and
  `git diff origin/main -- src/shared/packages/django-pyforge` searched for `pyforge.herald` — expected: no match.

## Spec Change Log

- 2026-10-10: minted from the operator's ruling "Forward-fix (Recommended)": Story 87.3 stays `done` on `main`, its
  forward stays dark, and this story closes its independent review's findings and then turns dev back ON. A `fix`
  under the CAPs 87.3 bound, in Epic 87, with no flag of its own.
