---
title: "MCP transport authorization and a streaming proxy"
type: "fix"
created: "2026-09-02"
status: "done"
followup_review_recommended: false
updated: "2026-09-02"
baseline_commit: "58ee07a0"
baseline_revision: "f098b49823b297fc62d12f52e8bcc9901a667613"
severity: "HIGH"
context:
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/resilience-invariants.md"
  - "src/platform/config/asgi.py"
  - "src/shared/packages/django-pyforge/src/django_pyforge/mcp_http.py"
  - "src/shared/packages/django-pyforge/src/django_pyforge/mcp_dual_era.py"
  - "src/platform/mcp_host/app.py"
  - "src/platform/deploy/charts/platform/templates/redis-networkpolicy.yaml"
warnings: []
deferred:
  - "mTLS or mesh policy for the web→mcp-host hop (steward deploy-profile)."
  - summary: >-
      Nothing outside the pytest settings supplies PYFORGE_ASSERTION_PUBLIC_KEY, so a
      deployed or laptop run now answers 503 on every station MCP route.
    evidence: |-
      `config/settings/base.py:610-611` defaults both assertion keys to `""`; only
      `config/settings/test.py:66-67` assigns them, and `grep -rn ASSERTION
      src/platform/deploy/` returns nothing — `platform.djangoEnv` carries no such
      env and no secretKeyRef. `resolve_public_pem()` therefore yields `""` and the
      gate takes its fail-closed 503 branch. The underlying gap is pre-existing —
      `supervisor.start_run`/`get`, `assertion/client.py`, `AssertionMiddleware` and
      the mason/doctor portals already call `crypto.verify_assertion`, whose
      `_setting_pem` raises on an empty key — but this story widens the blast radius
      from "the supervisor tools and portals" to "every JSON-RPC method on every
      station". Wiring the keypair Secret is AD-19 / Story 40.1 territory; the
      matching chart invariant and a `REQUIRED_SETTINGS` entry belong with it.
    location: >-
      src/platform/deploy/charts/platform/templates/_helpers.tpl (platform.djangoEnv)
    severity: high
  - summary: >-
      The new NetworkPolicy admits only `component: web`, while mcp-host's three
      probes are httpGet on the same port and originate from the node.
    evidence: |-
      `mcp-host-deployment.yaml:40-55` uses httpGet startup/liveness/readiness probes
      on `:8090`; the policy has no ipBlock or node allowance. The chart's only prior
      NetworkPolicy guards Redis, whose probes are `exec`, so there is no in-repo
      precedent for an HTTP-probed pod behind a podSelector-only ingress rule. On a
      CNI that subjects node→pod probe traffic to NetworkPolicy the pod never passes
      its startupProbe. Not fixable inside this story: AC 4 requires ingress "only
      from web pods", and the invariant enforces exactly one ingress rule, so a probe
      exception would fail the story's own test. Needs a deploy-profile decision
      alongside the mTLS/mesh item above.
    location: >-
      src/platform/deploy/charts/platform/templates/mcp-host-networkpolicy.yaml
    severity: medium
  - summary: >-
      The sidecar hop never watches `receive` for `http.disconnect`, and its budget
      rose from 5s to at least 300s.
    evidence: |-
      `_stream_upstream_body` relays until upstream ends; with `Queue(maxsize=1)`
      backpressure an abandoned request pins both the pump task and the upstream
      sidecar connection for the full read budget. Harmless at the old 5s cap, a real
      resource-holding window at the Celery hard limit. Out of scope on intent
      authority — the intent asks only that the budget be raised.
    location: >-
      src/shared/packages/django-pyforge/src/django_pyforge/mcp_http.py
    severity: medium
  - summary: >-
      Agent-facing docs and station skills still document a bare
      `POST /stations/<name>/mcp`, which now returns 401.
    evidence: |-
      `CLAUDE.md`, `AGENTS.md`, the eight `.claude/skills/pyforge-*/SKILL.md` blocks
      and the `bmad-agent-*` persona skills all describe the route with no
      `Authorization: Bearer <assertion>` requirement and no pointer to how a caller
      obtains one. No in-repo caller breaks (portals call in-process by design, per
      `assertion/client.py`), so the whole behavioural change lands on out-of-repo
      callers whose contract lives in files this story does not touch.
    severity: medium
  - summary: >-
      AC 4's only chart-render proof is `@requires_helm`, and the CI test env has no
      helm, so it silently skips there.
    evidence: |-
      `requires_helm` is a `skipif`, not a failure. The Platform CI `test` job runs
      the `platform-ci-test` pixi env, whose deps declare no helm; `kubernetes-helm`
      is only in `feature.platform-dev`. The story's three (now eight) guard-removed
      companions are not helm-gated but feed hand-built dicts to the helper, so they
      prove the helper, not the chart — the template could be deleted with a green
      CI run. Pre-existing for every chart test in this suite, not introduced here.
    location: >-
      src/platform/tests/test_chart_invariants.py
    severity: medium
  - summary: >-
      401/403 refusals carry no `WWW-Authenticate` challenge and the body is not
      JSON-RPC-shaped.
    evidence: |-
      `TransportRefusal.body()` emits `{"error": "..."}` on an endpoint that otherwise
      speaks JSON-RPC 2.0, and no challenge header points a client at the mint view or
      at protected-resource metadata, so an MCP client has no discoverable path from
      the refusal to a working call. The intent specifies the status codes only.
    location: >-
      src/shared/packages/django-pyforge/src/django_pyforge/mcp_auth.py
    severity: low
  - summary: >-
      Every station app is built `json_response=True`, so the keep-alive frame never
      fires against the real sidecar and the raised budget stays capped by the ~30s
      ingress idle timeout.
    evidence: |-
      `mcp_dual_era.py:55-56` builds every station MCP app with `json_response=True,
      stateless_http=True`, so the sidecar's body is always `application/json` and
      never `text/event-stream`. `_keepalive_frame()` returns `None` for anything but
      an event stream — correctly, since a comment frame injected into JSON corrupts
      it — which means the keep-alive path is unreachable in production and a JSON
      tool call still emits no bytes until it completes. T-5 is therefore only
      partially closed: the 5s cap and the full-response buffering are gone, but a
      long JSON call still dies at whatever idle timeout sits in front of the pod.
      Not fixable inside this story: the intent prescribes comment frames, and there
      is no legal way to keep a JSON body alive. Closing it needs either SSE-shaped
      sidecar responses or an ingress idle-timeout decision.
    location: >-
      src/shared/packages/django-pyforge/src/django_pyforge/mcp_http.py
    severity: medium
  - summary: >-
      The chart wires `MCP_HOST_SIDECAR_BASE_URL` into worker and migrate-job pods
      that the new NetworkPolicy then denies.
    evidence: |-
      `_helpers.tpl` (`platform.djangoEnv`) injects the sidecar URL into
      `worker-deployment.yaml` and `migrate-job.yaml`, and
      `test_platform_pods_wire_mcp_host_sidecar_base_url_to_internal_service`
      (`test_chart_invariants.py:1349`) asserts web AND worker carry it — while the
      new policy admits only `component: web` and the X-5 guard pins the rule to
      exactly one peer. Nothing breaks today: the only reader is `sidecar_base_url()`,
      reached solely from `config/asgi.py`'s dispatch, which runs in web. But the two
      invariants now encode opposite intents, and the first worker-side MCP call will
      fail at the network layer rather than at the config layer.
    location: >-
      src/platform/deploy/charts/platform/templates/mcp-host-networkpolicy.yaml
    severity: medium
  - summary: >-
      No test drives the real ASGI entrypoint; every test builds its own app around
      `dispatch_station_mcp`.
    evidence: |-
      The single production caller is `_dispatch_http` in `src/platform/config/asgi.py`.
      `test_mcp_transport_auth.py` calls `dispatch_station_mcp` directly with
      hand-built scope dicts, and the five updated files each wrap it in their own
      `application`. So the ACs' "Given `POST /stations/atlas/mcp`" is proved against
      an assembled callable, not the app gunicorn serves — a reordering inside
      `_dispatch_http` that let a station path bypass the gate would not fail any
      test. Pre-existing convention across this suite, not introduced here.
    location: >-
      src/platform/config/asgi.py
    severity: medium
  - summary: >-
      `MCP_PROXY_TIMEOUT_SECONDS` is documented only in a source comment.
    evidence: |-
      The new env var appears in no `values.yaml`, no chart template, and not in
      `src/platform/deploy/overlays/ocp/cluster-bringup.md`, which already carries an
      mcp-host readiness checklist. An operator raising the sidecar budget has to read
      `mcp_http.py` to learn the name exists.
    location: >-
      src/platform/deploy/overlays/ocp/cluster-bringup.md
    severity: low
---

<intent-contract>

## Intent

**Problem:** `dispatch_station_mcp` runs before every Django middleware, so `initialize`,
`tools/list` and any tool not routed through the supervisor are anonymous.
`proxy_station_mcp` buffers the whole response (`response.content`), has a 5 s
timeout, and forwards every inbound header including `Authorization` to
`mcp-host` over cleartext HTTP; `mcp-host` has no auth and no NetworkPolicy, so
any pod in the namespace can call it directly. Red-team **T-4**, **T-5**,
**X-5**, directive **R-7**.

**Approach:** Verify the RS256 assertion (audience `mcp:<station>`) in
`dispatch_station_mcp` before routing, for every JSON-RPC method; strip the
inbound `Authorization` and forward only the verified assertion; make the proxy
stream (`client.stream`, `aiter_bytes`, `X-Accel-Buffering: no`, keep-alive
comment frames under 30 s) with a per-tool timeout at least the Celery hard
limit; add a NetworkPolicy so only `web` may reach `mcp-host:8090`.

## Acceptance Criteria

- Given `POST /stations/atlas/mcp` with no assertion, when any JSON-RPC method is sent, then 401; with a valid assertion for `mcp:warden`, then 403 on the atlas route.
- Given the proxy, when the sidecar streams a 20 s response, then the client receives the first bytes within 1 s and the whole stream completes (no 502, no buffering); a test asserts chunked delivery.
- Given the proxy, when it forwards, then the inbound `Authorization` header is replaced by the verified assertion and no other credential header passes through.
- Given `helm template`, when rendered, then a NetworkPolicy allows ingress to `mcp-host` only from `web` pods; the existing Redis policies are unchanged.
- Given the in-process path (laptop), when the same request is made, then the same verifier runs (one code path, transport-agnostic).

## Boundaries & Constraints

**Always:** Write under `_bmad-output/projects/pyforge-steward/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` only — never `scripts/bmad-switch`.
Ledger key `42-1-mcp-transport-authorization`. Host never imports `pyforge.*`. Official `mcp` SDK dual-era stays. `start`/`get` in the supervisor keeps its own check (defence in depth).

**Block If:** Implementation would branch on client name, add `mcpHost.enabled`, or reintroduce `/mcp/sse`.

**Never:** Forwarding an IdP bearer to the sidecar. A tool reachable without an assertion.

</intent-contract>

## Tasks

- [x] Verifier at dispatch (chrome, Django-free)
- [x] Streaming proxy + timeouts
- [x] NetworkPolicy template + invariant
- [x] Tests on both paths
- [ ] Ledger `42-1-mcp-transport-authorization` → `review` then `done` via `sprint-ledger-sync`.

## Verification

`src/platform/tests/test_start_get_survives_disconnect.py` extended; new `test_mcp_transport_auth.py`; chart invariants.

## Dev Notes

**2026-09-02 — implementation.**

- Verifier: the RS256 claim rules moved out of `assertion/crypto.py` into a
  Django-free `assertion/verify.py`; `crypto.verify_assertion` (supervisor,
  portals, `AssertionMiddleware`) now delegates to it, so the transport gate
  and the defence-in-depth checks cannot drift apart. The gate itself is
  `django_pyforge/mcp_auth.py` (`authorize_station_scope`), called from
  `dispatch_station_mcp` before either route is taken: 401 with no/!valid
  assertion, 403 on the wrong audience, 503 when no public key resolves
  (fail closed), and a 405 for any non-POST *before* the gate, since a method
  that cannot carry a JSON-RPC call needs no assertion and must not reach the
  sidecar. The credential travels as `Authorization: Bearer <assertion>`.
- Proxy: `client.stream` + `aiter_bytes`, `X-Accel-Buffering: no`, a 15s
  keep-alive comment frame for `text/event-stream` bodies only (never injected
  into JSON), and a read budget floored at the Celery hard limit (300s;
  `MCP_PROXY_TIMEOUT_SECONDS` may raise it, nothing may lower it). Forwarded
  request headers are an ALLOWLIST, so no unnamed credential can ride along.
- **Ledger not advanced.** `sprint-ledger-sync` promotes the Tier-3 feed to the
  tracked twin, and neither worktree can produce the row: this dispatch
  worktree has no `implementation-artifacts/`, and the main worktree's feed
  predates Epic 42 (no `42-1` key) and is ~30 `done` keys behind the twin, so a
  sync there would be refused by the monotonic guard. Advancing it needs the
  landing/marshal step (feed repair + scoped promote), not a hand-edit of a
  GENERATED file.
- Deferred as specced: mTLS / mesh policy for the web→mcp-host hop.

**2026-09-02 — review hardening.** The notes above predate the review pass; the
five `patch` findings it applied are recorded under *Review Triage Log* and
*Auto Run Result* below.

## Review Triage Log

### 2026-09-02 — Review pass

- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 1, medium 2, low 2)
- defer: 6: (high 1, medium 4, low 1)
- reject: 7: (high 0, medium 2, low 5)
- addressed_findings:
  - `[high]` `[patch]` `_drain_upstream` caught only `(httpx.HTTPError, OSError)`, so a
    pump dying of anything else — `httpx.StreamError` is a `RuntimeError` — queued
    nothing, leaving the consumer spinning on `asyncio.wait_for` forever and the ASGI
    body never closed. Now reports any `BaseException` (re-raising `CancelledError`),
    breaks when `pump.done() and queue.empty()`, and retrieves the dead task's
    exception. Covered by `test_a_pump_failure_of_any_type_terminates_the_relay`
    (parametrized) and `test_a_pump_that_dies_without_reporting_still_closes_the_body`,
    both under a 10s deadline so a hang fails instead of blocking the suite.
  - `[medium]` `[patch]` `proxy_timeout_seconds()` accepted `nan`/`inf`: `max(nan, 300.0)`
    returns `nan`, and `inf` removed the read budget the floor exists to guarantee. Now
    rejects non-finite and non-positive values back to the floor; the budget test sweeps
    `5 / 0 / -1 / nan / NaN / inf / -inf / not-a-number`.
  - `[medium]` `[patch]` The X-5 chart guard read the ingress peer's `podSelector` without
    asserting it was the peer's ONLY key, so a policy carrying a `namespaceSelector` or
    `ipBlock` beside it — admitting web-labelled pods in ANY namespace — passed; and it
    checked only `app.kubernetes.io/component`, so dropping the `platform.selectorLabels`
    include from either selector passed while widening the rule release-wide. Both now
    asserted, with the expected scoping labels derived from the rendered Deployment
    rather than re-declared, plus five more guard-removed companions.
  - `[low]` `[patch]` The AC-5 Django-free AST scan covered only `mcp_auth.py` and
    `verify.py`, not the modules they import at module scope; a Django import added to
    `assertion/schema.py` would have broken the guarantee with the test green. The scan
    now walks the module-scope import closure and asserts it actually reached
    `schema.py` and `exceptions.py`.
  - `[low]` `[patch]` The proxy tests asserted only what the header allowlist excludes, so
    removing `b"content-type"` (which 415s the sidecar's Streamable HTTP transport) would
    have passed; `_StubUpstream.status_code` was never varied, so a hardcoded 200 would
    have passed; and nothing asserted the request body reached upstream, so dropping
    `content=body` would have passed. All three now covered.

### 2026-09-02 — Review pass (follow-up, the single allowed one)

- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 0, medium 1, low 2)
- defer: 4: (high 0, medium 3, low 1)
- reject: 16: (high 0, medium 6, low 10)
- addressed_findings:
  - `[medium]` `[patch]` `proxy_station_mcp` caught only `httpx.RequestError`, but httpx's
    failure surface is not one tree: `StreamError` subclasses `RuntimeError` and
    `InvalidURL` subclasses `Exception`, so neither is a `RequestError`. A stream
    teardown failing that way escaped AFTER the head was sent — bypassing the very
    `started and not closed` branch written to close the body — and a malformed
    `MCP_HOST_SIDECAR_BASE_URL` became an unhandled ASGI exception instead of the 502
    every other unreachable-hop case answers. This is the same class error the prior
    pass fixed one layer down in `_drain_upstream`, left standing one layer up. Now
    caught as `hop_failures = (RequestError, StreamError, InvalidURL)`, covered by
    `test_a_teardown_failure_outside_request_error_still_closes_the_body`
    (parametrized over both branches) and
    `test_a_sidecar_url_httpx_rejects_answers_502_rather_than_crashing`.
  - `[low]` `[patch]` The `proxy_station_mcp` docstring claimed "Streamed both ways",
    which is false — `read_body(receive)` still buffers the whole request before the
    hop opens, and only the response streams. Reworded to say which direction streams
    and why the request cannot.
  - `[low]` `[patch]` `_module_scope_imports` iterated only `tree.body`, so an import
    nested in a module-scope `try:`/`if:` — which runs on import exactly like an
    outermost one — was invisible to the Django-free guarantee: `try: import django`
    in any closure module would have passed. It now walks module-scope compound
    statements while still excluding function and lambda bodies, because
    `mcp_auth._settings_public_pem` imports Django inside a function BY DESIGN.
    Covered by `test_the_django_free_scan_sees_imports_nested_at_module_scope`.

Both code patches were mutation-checked: narrowing the catch back to
`httpx.RequestError` fails exactly the two new tests (the `request-error`
parametrization stays green, so they are not trivially passing), and restoring the
`tree.body`-only scan fails the new companion.

Findings this pass re-raised that were already recorded and stay so: the
`PYFORGE_ASSERTION_PUBLIC_KEY` 503 (all four layers found it independently — it is the
dominant residual risk), kubelet probes vs. the NetworkPolicy, the missing
`http.disconnect` watch, the agent-facing docs that still show a bare POST, the
helm-gated chart proof, and the missing `WWW-Authenticate` challenge.

Rejected, with the premises re-verified rather than inherited from the prior pass:
`Mcp-Session-Id`/`Last-Event-Id` are absent from the allowlist and non-POST is 405'd
before the gate — both correct, because `mcp_dual_era.py:55-56` builds every station
app `json_response=True, stateless_http=True`, so no session id is ever issued and
there is no GET SSE stream or DELETE teardown to reach (the in-process path is already
`DualEraPostOnlyASGI`); `contextlib.suppress(CancelledError, Exception)` around
`await pump` is the canonical `cancel()`-then-await idiom, not a swallowed
cancellation; `_settings_public_pem` does catch a bad `DJANGO_SETTINGS_MODULE`, since
`ModuleNotFoundError` subclasses `ImportError`; the duplicate-header dict collapse and
the latin-1 header round-trip are both pre-existing shapes the baseline had verbatim;
`proxy_timeout_seconds()` needs no ceiling because the intent specifies a floor;
double verification at the supervisor is mandated by the intent ("defence in depth");
roles-at-transport and an egress rule are outside an intent that names the audience
check and ingress-from-web only; and the four unaccompanied chart assertions are
already covered for every X-5 exposure by the eight existing guard-removal companions.

## Auto Run Result

Status: done
Blocking condition: none

**Implemented change.** The RS256 assertion is verified in `dispatch_station_mcp`
before either transport is chosen, so every JSON-RPC method — `initialize` and
`tools/list` included — is authorized (T-4); the sidecar hop streams both the head
and each chunk, forwards a header allowlist whose only credential is the verified
assertion, and budgets at least the Celery hard limit instead of five seconds
(T-5); and a NetworkPolicy admits only `web` to `mcp-host:8090` (X-5).

**Files changed**

- `src/shared/packages/django-pyforge/src/django_pyforge/mcp_auth.py` — new: the
  transport gate. `authorize_station_scope` returns `AuthorizedCall | TransportRefusal`,
  never `None`. 401 missing/invalid/expired/tampered, 403 wrong audience, 503 when no
  public key resolves (fail closed). Django-free at module scope.
- `src/shared/packages/django-pyforge/src/django_pyforge/assertion/verify.py` — new: the
  RS256 claim rules, moved verbatim out of `crypto.py` so the gate and the
  defence-in-depth checks cannot drift into two rule sets.
- `src/shared/packages/django-pyforge/src/django_pyforge/assertion/crypto.py` —
  `verify_assertion` is now the settings-resolved-PEM wrapper delegating to `verify`.
- `src/shared/packages/django-pyforge/src/django_pyforge/mcp_http.py` — gate before
  routing; 405 for non-POST ahead of the gate; `proxy_station_mcp` rewritten to
  `client.stream`/`aiter_bytes` with `X-Accel-Buffering: no`, 15s keep-alive comment
  frames for `text/event-stream` only, a request-header allowlist, response framing
  re-framed, and the body closed exactly once.
- `src/platform/deploy/charts/platform/templates/mcp-host-networkpolicy.yaml` — new:
  ingress to mcp-host from `web` pods on TCP/8090 only.
- `src/platform/tests/test_mcp_transport_auth.py` — new: 27 tests over the gate, the
  streaming proxy, the header discipline and the one-verifier claim.
- `src/platform/tests/test_chart_invariants.py` — the NetworkPolicy proof plus eight
  guard-removed companions.
- `src/platform/tests/test_start_get_survives_disconnect.py` — an anonymous `tools/call`
  creates no run row.
- `test_atlas_mcp_host.py`, `test_mcp_host_sidecar.py`, `test_seven_mcp_faces.py`,
  `test_openfeature_file_flags.py`, `test_warden_portal_audit_start_get.py` — fixtures
  now carry the assertion the gate verifies.

**Review findings breakdown.** 5 patches applied (1 high, 2 medium, 2 low); 6 items
deferred (see frontmatter `deferred`); 7 rejected — dropped MCP session/resume headers
(the SDK is built `stateless_http=True`, `json_response=True`, so no session id is ever
issued), the 405/401 answer for an unregistered station name, an unreachable empty-PEM
branch in `verify.py`, `leeway=0` clock skew (pre-existing, moved verbatim), a global
`register_station_mcp_app` left un-torn-down with no observable leak, the "replaced"
framing in three docstrings being degenerate when the inbound credential is the
assertion itself, and roles-not-enforced-at-transport (the intent names the audience
check only).

**Follow-up review recommended: true.** Patched by severity: high 1, medium 2, low 2.
Score `3 × 2 + 1 × 2 = 8` (≥ 5), and a high-severity finding was patched — either
condition alone sets the flag.

**Verification.** Run from `src/platform` under the `platform-ci-test` pixi env
(CI parity: pytest 9.1.1, pytest-django, celery 5.6.3, mcp 2.1.1) with `platform-dev`
on `PATH` for helm and an ephemeral PostgreSQL 17 for the DB-marked tests.

- Targeted: `test_mcp_transport_auth` 27, `test_chart_invariants` 71,
  `test_mcp_host_sidecar` 10, `test_atlas_mcp_host` 14 — **122 passed, no skips**
  (the helm-gated chart tests ran).
- Whole platform suite, branch vs. `f098b498` baseline under identical conditions:
  **603 passed / 13 failed / 5 errors** against baseline **566 passed / 13 failed /
  5 errors** — the same 13 failures and 5 errors, none of them in this story's surface
  (redis-broker, host-board row isolation, openfeature channel policy, liquibase DDL
  governance, and transactional-DB teardown). Net **+37 passing tests, no regressions**.
- Each patch was mutation-checked: reverting the pump fix, the `nan`/`inf` guard, the
  namespaceSelector/scoping assertions, the `schema.py` Django import, and each of
  `content=body` / hardcoded 200 / the `content-type` allowlist entry all fail.

**Residual risks.** The high-severity deferral dominates: as shipped, nothing outside
`config/settings/test.py` supplies `PYFORGE_ASSERTION_PUBLIC_KEY`, so a real deployment
or a laptop `runserver` answers 503 on every station MCP route until the AD-19 keypair
Secret lands. The gate is correct and fails closed; it simply has no key to verify
against outside pytest. Secondary: the NetworkPolicy may block kubelet httpGet probes on
strict CNIs, and out-of-repo MCP clients now need a header no documentation mentions.
Two verification surfaces stay weaker than their ACs — AC 4's chart render is
`@requires_helm` (skips in CI), and AC 2's streaming is proved against a stubbed
`httpx.AsyncClient` rather than a live 20s hop.

### Follow-up review pass — 2026-09-02

**Implemented change.** No behavioural change to the story's contract. Three patches
hardened what shipped: the sidecar hop now catches every branch of httpx's failure
surface instead of only `RequestError`, so a stream teardown or a malformed sidecar
URL closes the body / answers 502 rather than escaping as an unhandled ASGI exception;
the `proxy_station_mcp` docstring no longer claims the request body streams; and the
AC-5 Django-free scan sees module-scope imports nested in `try:`/`if:`.

**Files changed**

- `src/shared/packages/django-pyforge/src/django_pyforge/mcp_http.py` — `hop_failures`
  tuple replaces the bare `except httpx.RequestError`; docstring corrected to describe
  a streamed response over a buffered request.
- `src/platform/tests/test_mcp_transport_auth.py` — `_StubUpstream` gains
  `close_failure` / `open_failure` knobs; three new tests (two parametrized teardown
  branches, the 502-on-InvalidURL case, the AST-scan companion); `_module_scope_imports`
  walks module-scope compound statements while still excluding function bodies.

**Review findings breakdown.** 3 patches applied (0 high, 1 medium, 2 low); 4 new items
deferred; 16 rejected. Six earlier findings were re-raised and left recorded as already
deferred.

**Follow-up review recommended: false (forced).** Patched by severity: high 0, medium 1,
low 2. Score `3 × 1 + 1 × 2 = 5` (≥ 5), which would set `true` — but this pass WAS the
single allowed follow-up entered from a `done` spec, so the flag is forced `false` and
the story does not re-enter review.

**Verification.** Run from `src/platform` under `platform-ci-test`, helm from
`platform-dev` on `PATH`.

- `test_mcp_transport_auth` + `test_mcp_host_sidecar` + `test_atlas_mcp_host`:
  **55 passed** (was 51; the four new tests are the delta).
- `test_chart_invariants` with helm present: **72 passed, no skips** — the helm-gated
  NetworkPolicy render ran.
- `test_start_get_survives_disconnect` against an ephemeral PostgreSQL 17: **8 passed,
  1 error**. The error is the known pre-existing `seed_lane1_homepage` collision during
  `django_db_setup` (its `post_migrate` receiver adds a second child with slug `home`
  beside the one wagtailcore's initial-data migration creates); the traceback never
  reaches test code, and it is an artifact of the local DB bootstrap, not of this story.
- Both code patches mutation-checked, as recorded in the triage log.

**Residual risks.** Unchanged and still dominated by the `PYFORGE_ASSERTION_PUBLIC_KEY`
deferral: outside pytest nothing supplies the key, so every station MCP route
fail-closes to 503 until the AD-19 keypair Secret lands. Newly recorded this pass: the
keep-alive frame cannot fire against a `json_response=True` sidecar, so a long JSON
tool call is still bounded by the ingress idle timeout rather than the 300s budget.

## Source

Red-team review: `research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md` (directive and finding ids in the FR/AD line of
`epics.md` Story 42.1). Sprint change proposal:
`sprint-change-proposal-2026-09-02-red-team-high.md`.
