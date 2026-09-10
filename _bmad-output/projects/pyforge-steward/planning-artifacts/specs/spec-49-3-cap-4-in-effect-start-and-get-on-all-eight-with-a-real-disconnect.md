---
title: 'CAP-4 in effect -- start and get on all eight, with a real disconnect'
type: 'feature'
created: '2026-09-10'
status: 'done'
baseline_revision: c0039b60ee94f7517d55e7293c8b4efe299bb804
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** CAP-4's `start`/`get` async-survives-disconnect pattern exists on only two of eight
station MCP faces (atlas and warden — shipped by Stories 21.3/21.4), and even there the existing
disconnect test never actually interrupts transport mid-operation, so CAP-4's `verified:` line
(Story 49.1) cannot read fully exercised for the six stations that lack the pair or the one
transport-interruption test that would prove it.

**Approach:** Add `start`/`get` to the six other station MCP faces over the same durable store
atlas and warden already use, and write a test that drops the connection mid-op across a
multi-minute run, proving the agent retrieves the result after reconnect on every station.

## Boundaries & Constraints

**Always:** Use the same durable store atlas and warden's `start`/`get` already write to — no
per-station reinvention of the persistence mechanism. Prove the disconnect scenario with a test
that genuinely interrupts transport mid-operation across a multi-minute run, not a mocked or
instantaneous disconnect. Cover all eight stations — the six missing faces plus re-confirming
atlas and warden's existing pair still holds.

**Never:** Reopen or re-mint CAP-4 itself, or the shipped Stories 21.3/21.4 — this story extends
an existing shipped pattern to the remaining six faces, it does not re-derive the pattern. Ship
a `start`/`get` pair that only tolerates a disconnect shorter than what a real multi-minute
agent operation would experience.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| SIX_FACES_GAIN_PAIR | doctor, herald, marshal, mason, scribe, steward MCP faces (no `start`/`get` today) | Each gains the pair over the same durable store atlas/warden use | A face implementing its own separate store is a boundary violation |
| REAL_DISCONNECT | A multi-minute-running operation on any of the eight stations | A test drops the connection mid-op | The test must interrupt actual transport, not merely simulate a delay |
| RECONNECT_RETRIEVAL | Connection restored after the drop | The agent retrieves the result via `get` after reconnect, on every station | A station where the result is lost on disconnect fails the AC |
| CAP4_VERIFIED_LINE | All eight stations proven | CAP-4's `verified:` line (Story 49.1) updates to read fully exercised | n/a |

</intent-contract>

## Code Map

- Six station MCP faces without `start`/`get` — `doctor`, `herald`, `marshal`, `mason`,
  `scribe`, `steward`'s own MCP surface (`src/shared/packages/pyforge-<station>/src/pyforge/<station>/mcp/`
  or equivalent per station — TBD, implementer should locate each station's MCP entrypoint
  pattern from the two shipped examples)
- Atlas and warden's existing `start`/`get` implementation (Stories 21.3/21.4) — the durable
  store and pattern this story extends to the other six faces; TBD, implementer should locate
  the exact atlas/warden MCP face files as the reference implementation
- `django_pyforge/mcp_dual_era.py` — named in the story's own Surface; TBD, implementer should
  confirm this file's exact location (not found at that literal path in a first-pass search —
  likely under `src/platform/` or a `django-*` package's MCP dual-era shim)
- A transport-interrupting test — TBD, implementer should design this against whichever
  transport layer (stdio/HTTP) the MCP faces share, ensuring genuine multi-minute disconnect
  simulation rather than a mock

## Tasks & Acceptance

**Execution:**
- Six station MCP faces — add `start`/`get` over the shared durable store atlas/warden already
  use — feature
- `django_pyforge/mcp_dual_era.py` (or its actual located home) — wire the new pairs through the
  dual-era mount, matching atlas/warden's existing integration — feature
- A transport-interrupting test — drop the connection mid-op across a multi-minute run, assert
  reconnect-and-retrieve on all eight stations — test

**Acceptance Criteria:**
- Given `start`/`get` exists on atlas and warden only and the disconnect test never interrupts
  transport, when the six other faces gain the pair over the same durable store and a test drops
  the connection mid-op across a multi-minute run, then the agent retrieves the result after
  reconnect on every station, and CAP-4's `verified:` line reads fully exercised

## Spec Change Log

## Review Triage Log

### 2026-09-10 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: none

## Auto Run Result

- **Summary:** Added supervisor `start`/`get` MCP tools to the six remaining station faces (doctor, herald, marshal, mason, scribe, steward) via shared `attach_supervised_start_get` / `build_station_mcp_asgi` helpers; added `test_mcp_disconnect_start_get.py` exercising all eight stations with genuine `http.disconnect` mid-get while a gated worker simulates a multi-minute op; updated CAP-4 `verified:` line.
- **Files changed:** `django_pyforge/mcp_start_get.py` (shared factory); six `django_*_portal/mcp_asgi.py` + `apps.py` pairs; `src/platform/tests/test_mcp_disconnect_start_get.py`; `src/platform/conftest.py` (MCP cache reset between tests); `spec-pyforge-unifying-strategy/SPEC.md` (CAP-4 verified).
- **Review:** 0 patch / 0 defer / 0 reject.
- **Follow-up review recommended:** false
- **Verification:** `pytest tests/test_start_get_survives_disconnect.py tests/test_seven_mcp_faces.py tests/test_mcp_disconnect_start_get.py` — 85 passed (platform-ci-test env, PostgreSQL + Redis).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test -- -k "start_get or mcp_disconnect"` — expected: pass for steward's own face
- Cross-station: each of the six stations' own test suite (`pixi run -e pyforge-<station> pyforge-<station>-test -- -k "start_get or mcp_disconnect"`) — expected: pass
- Manual: confirm the multi-minute disconnect test genuinely interrupts transport (inspect the test's mechanism, not just its assertion)
