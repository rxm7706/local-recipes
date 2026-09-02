---
title: "MCP transport authorization and a streaming proxy"
type: "fix"
created: "2026-09-02"
status: "ready-for-dev"
updated: "2026-09-02"
baseline_commit: "58ee07a0"
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

- [ ] Verifier at dispatch (chrome, Django-free)
- [ ] Streaming proxy + timeouts
- [ ] NetworkPolicy template + invariant
- [ ] Tests on both paths
- [ ] Ledger `42-1-mcp-transport-authorization` → `review` then `done` via `sprint-ledger-sync`.

## Verification

`src/platform/tests/test_start_get_survives_disconnect.py` extended; new `test_mcp_transport_auth.py`; chart invariants.

## Source

Red-team review: `research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md` (directive and finding ids in the FR/AD line of
`epics.md` Story 42.1). Sprint change proposal:
`sprint-change-proposal-2026-09-02-red-team-high.md`.
