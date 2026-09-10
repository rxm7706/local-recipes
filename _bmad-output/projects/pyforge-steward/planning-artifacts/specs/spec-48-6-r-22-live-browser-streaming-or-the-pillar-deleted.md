---
title: "Story 48.6: R-22 live browser streaming, or the pillar deleted"
type: story
created: 2026-09-10
baseline_revision: c83aafd3fcda9ebf3a8e03366646f49c3cb4c859
status: in-progress
review_loop_iteration: 0
followup_review_recommended: false
context:
  - src/platform/config/asgi.py
  - src/platform/config/websocket.py
  - src/platform/config/settings/production.py
  - src/platform/platformapp/front_door/lane1_runtime.py
  - src/shared/packages/django-pyforge/src/django_pyforge/events/
  - src/shared/packages/django-pyforge/src/django_pyforge/assertion/
  - src/shared/packages/pyforge-steward/pyproject.toml
  - docs/dreams/archive/pyforge-unifying-strategy-2026-08-23-topology.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md
warnings: []
deferred: []
declared_low_risk: false
---

# Story 48.6: R-22 live browser streaming, or the pillar deleted

<intent-contract>

## Intent

**Problem:** Red-team T-8 found the Dream's `/ws/events/` live-badge pillar is unimplemented — `config/websocket.py` is a ping/pong stub that accepts every websocket path with no Redis Stream relay and no per-subject filtering.

**Approach:** **Operator ruling 2026-09-10: implement the pillar, do not delete it.** Ship a Channels `AsyncWebsocketConsumer` at `/ws/events/` behind the `pyforge-steward[dashboard]` extra that tail-reads `pyforge.events` on redis-broker (non-group fan-out), verifies an RS256 assertion at connect, and forwards only CloudEvents whose `data.subject` matches the verified `sub` claim. Wire the platform ASGI router to delegate `/ws/events/` to this consumer when the extra is importable; leave other websocket paths on the existing stub.

## Boundaries & Constraints

**Always:** Tail-read the main stream only — never join station XREADGROUP consumer groups or ACK entries on behalf of browsers. Per-sub filter compares verified JWT `sub` to `event["data"]["subject"]`; events without `data.subject` are dropped silently. Assertion verification reuses `django_pyforge.assertion.verify.verify_assertion_claims` with audience `mcp:events` (new constant beside existing `mcp:` audiences). Consumer code lives under `pyforge.steward.dashboard` (the `[dashboard]` extra). Platform `asgi.py` lazy-imports the consumer and closes with code 4403 when the extra is absent. Update `docs/dreams/pyforge-unifying-strategy.md` § Capability checklist to record the ruling and the live `/ws/events/` surface.

**Never:** Do not delete the archive topology pillar text (historical). Do not add HTMX badge UI in this story — transport only. Do not change NetworkPolicy (48.3), observability contract (48.5), or event publish/consume semantics (42.x). Do not hand-edit `sprint-status-ledger.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| AUTH_OK | Valid assertion token in query `?token=` at connect | WebSocket accepted; relay task starts | Invalid/expired token → close 4401 before accept |
| SUB_MATCH | Stream entry with `data.subject == sub` | JSON CloudEvent text frame sent to client | N/A |
| SUB_MISMATCH | Stream entry with different or missing `data.subject` | Frame not sent | Silent drop |
| NO_EXTRA | `[dashboard]` extra not installed | `/ws/events/` close 4403 | Other paths still hit ping/pong stub |
| OTHER_PATH | WebSocket to `/ws/other/` | ping/pong stub unchanged | N/A |
| DISCONNECT | Client disconnects mid-relay | Background tail task cancelled cleanly | No leaked tasks |

</intent-contract>

## Code Map

- `src/platform/config/asgi.py:209-215` — websocket branch; add `/ws/events/` delegation before stub
- `src/platform/config/websocket.py` — keep as fallback for non-events paths
- `src/platform/config/settings/production.py:38` — existing `CHANNEL_LAYERS` on redis-broker
- `src/platform/platformapp/front_door/lane1_runtime.py:28-35` — `channel_layers_for_broker` helper
- `src/shared/packages/django-pyforge/src/django_pyforge/events/fabric.py` — `parse_cloudevent`, `STREAM` constant
- `src/shared/packages/django-pyforge/src/django_pyforge/events/constants.py` — `STREAM = "pyforge.events"`
- `src/shared/packages/django-pyforge/src/django_pyforge/events/memory.py` — `MemoryRedis` test double
- `src/shared/packages/django-pyforge/src/django_pyforge/supervisor.py:418` — `data.subject` on `run.started`
- `src/shared/packages/django-pyforge/src/django_pyforge/assertion/verify.py` — `verify_assertion_claims`
- `src/shared/packages/django-pyforge/src/django_pyforge/assertion/schema.py` — add `EVENTS_AUDIENCE = "mcp:events"`
- `src/shared/packages/pyforge-steward/pyproject.toml:44-50` — `[dashboard]` extra deps (channels stack)
- `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/` — new consumer + relay modules

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/django-pyforge/src/django_pyforge/assertion/schema.py` — add `EVENTS_AUDIENCE = "mcp:events"` constant
- `src/shared/packages/django-pyforge/src/django_pyforge/events/browser_relay.py` — `matches_subject(event, sub)`, async `tail_events(broker_url, *, last_id, stop)` generator
- `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/consumers.py` — `EventsStreamConsumer` (auth at connect, relay loop)
- `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/routing.py` — `websocket_urlpatterns` for `ws/events/`
- `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/asgi.py` — thin `URLRouter` ASGI app export
- `src/platform/config/asgi.py` — route `/ws/events/` to dashboard ASGI when importable
- `docs/dreams/pyforge-unifying-strategy.md` — record 2026-09-10 ruling + `/ws/events/` transport shipped
- `src/shared/packages/pyforge-steward/tests/unit/test_events_stream_consumer.py` — MemoryRedis + sub filter unit tests
- `src/platform/tests/test_ws_events.py` — ASGI path routing + auth rejection tests

**Acceptance Criteria:**
- Given a valid assertion with `sub=alice` and a published `run.started` with `data.subject=alice`, when a websocket client connects to `/ws/events/?token=…`, then the client receives the CloudEvent JSON frame
- Given the same token but an event with `data.subject=bob`, when relay runs, then no frame is sent for that event
- Given `/ws/events/` with the dashboard extra absent (ImportError path), when a websocket connects, then the connection closes with code 4403
- Given `/ws/ping` websocket with text `ping`, when connected, then response is still `pong!`
- Given `pytest` for the new test modules, when run under `pyforge-steward` and `platform-dev` envs, then all tests pass

## Verification

**Commands:**
- `pixi run -e pyforge-steward pyforge-steward-test -- -q -k events_stream` — expected: pass
- `pixi run -e platform-dev pytest -c /dev/null src/platform/tests/test_ws_events.py -q` — expected: pass

## Spec Change Log

## Review Triage Log

## Design Notes

Browser relay uses `$` blocking XREAD (not XREADGROUP) so it never competes with station consumer groups or ACK semantics. The connect-time assertion uses query param `token` so HTMX `hx-ext="ws"` can pass it without a custom subprotocol. Public key comes from `PYFORGE_ASSERTION_PUBLIC_KEY` env (same as MCP/supervisor). Only `run.started` currently publishes `data.subject`; other event types are dropped until publishers add the field — acceptable for R-22's first slice.

## Auto Run Result
