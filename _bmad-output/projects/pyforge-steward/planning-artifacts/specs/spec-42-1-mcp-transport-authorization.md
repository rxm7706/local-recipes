---
title: "MCP transport authorization and a streaming proxy"
type: "fix"
created: "2026-09-02"
status: "done"
followup_review_recommended: true
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

## Source

Red-team review: `research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md` (directive and finding ids in the FR/AD line of
`epics.md` Story 42.1). Sprint change proposal:
`sprint-change-proposal-2026-09-02-red-team-high.md`.
