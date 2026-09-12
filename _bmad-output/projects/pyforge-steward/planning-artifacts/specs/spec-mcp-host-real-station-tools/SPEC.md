---
spec: mcp-host-real-station-tools
# Flipped draft -> shipped 2026-09-12, same day as the Dream/Spec: both open
# questions were resolved by implementing CAP-1..3 directly rather than
# researching them separately -- see the Design Notes below and the
# memlog's own decision entries for the resolution detail.
status: shipped
created: "2026-09-12"
updated: "2026-09-12"
owner-dream: docs/dreams/mcp-host-real-station-tools.md
surface:
  - docs/dreams/mcp-host-real-station-tools.md
  - src/platform/mcp_host/app.py
  - src/platform/mcp_host/settings.py
  - src/platform/compose/mcp-host/Containerfile
  - src/platform/deploy/charts/platform/templates/_helpers.tpl
  - src/platform/deploy/charts/platform/templates/mcp-host-deployment.yaml
  - src/platform/deploy/charts/platform/templates/networkpolicy-egress.yaml
  - src/platform/deploy/charts/platform/templates/networkpolicy-postgres-ingress.yaml
  - src/shared/packages/django-marshal/src/django_marshal_portal/mcp_asgi.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/publisher_host.py
  - pixi.toml
  - "[feature.mcp-host]"
companions: []
sources:
  - ../../../../../../docs/dreams/mcp-host-real-station-tools.md
open_questions: []
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for
> what to build, test, and validate. `owner-dream` carries the narrative rationale this
> contract intentionally omits.

# SPEC — The sidecar that only says its own name

## Why

**A pain to solve.** `spec-mcp-era-isolation` (shipped, slice 1) built the mcp-host
sidecar to work around `python-agent-platform`'s `mcp 1.x` pin: the web image cannot
import `mcp.server.mcpserver`, so a second process (mcp 2.x, no Langflow) proxies
`/stations/<name>/mcp` instead. That sidecar is the *only* place any station's real MCP
tools could run — but `mcp_host/app.py` built each station's app with
`asgi_for_station(name)`, a function whose entire body is one tool, `station_face()`,
returning the station's own name string. No station's real tool surface (marshal's
held-loop `publish_loop_run`/`heartbeat_loop_run`/`complete_loop_run` included) was
reachable through a deployed platform's HTTP surface. Found 2026-09-12 chasing CAP-3's
own live-run proof (`spec-run-state-one-publisher`): a real, correctly-signed host
assertion could not publish a run because the real tool it needed was never registered
on the server that answered the call.

## Capabilities

- **CAP-1**
  - **intent:** An agent that calls a station's real MCP tool (e.g. marshal's
    `publish_loop_run`) through a deployed platform's `/stations/<name>/mcp` reaches
    that tool's real implementation, the same code path a laptop or `platform-ci-local`
    run reaches in-process.
  - **success:** `POST /stations/marshal/mcp` with `publish_loop_run` on a real deployed
    cluster returns a run handle from `publish_held_loop_bounded`, not
    `Unknown tool: publish_loop_run`.
  - **shipped:** proven live 2026-09-12 — a real `HostPublisher` process against the
    deployed CRC cluster published, heartbeat'd, and completed a run; a second,
    previously-unreachable bug (the client's flat-kwargs call shape vs the real tool's
    required nested `payload` field) was found and fixed in the same pass.
- **CAP-2**
  - **intent:** A station with no real in-process MCP app keeps working exactly as
    slice 1 shipped it — the generic identity stub remains its answer.
  - **success:** `spec-mcp-era-isolation`'s own CAP-1..3 acceptance criteria (dual-era
    handshake, protocol-version negotiation, 405 on non-POST) still hold, unchanged,
    for any station without a real app, after this Spec's change lands.
  - **shipped:** proven 2026-09-12 — the sidecar's boot logs show all 9 stations'
    session managers starting cleanly; a local smoke test confirmed `_apps` covers all
    9 default stations while `_real_apps` covers only `{"marshal"}`. `django.setup()`
    failing for any reason falls back to the stub for every station (a mocked-failure
    unit test covers this isolation seam directly).
- **CAP-3**
  - **intent:** CAP-3's own attended-CRC exercise can complete its one unproven item.
  - **success:** `spec-run-state-one-publisher`'s verification record is re-run and its
    "Live run appears on `/runs/`, timing survives teardown" row flips from
    `NOT PROVEN` to `PASS`.
  - **shipped:** proven 2026-09-12 — `verification-2026-09-12.md` records the row as
    `PASS`, with the live run's evidence.

## Constraints

- `spec-mcp-era-isolation`'s shipped slices 1–3 stay exactly as they are: the dual-era
  wire, the proxy dispatch in `dispatch_station_mcp`, `MCP_HOST_SIDECAR_BASE_URL`
  wiring, CAP-4's cluster-required fail-loud, the stdio translator (slice 2), and the
  `ImportError`-skip retirement gate (slice 3, `retire-skip.md`). This Spec is additive:
  what the sidecar hosts, never how it is reached. Held exactly — no changes to those
  files.
- A station's own portal package (`django_<name>_portal`) stays that station's surface.
  This Spec owns only how the sidecar discovers and mounts what already exists there —
  it does not redesign any station's tool implementation. Held — `django_marshal_portal`
  itself only gained a signature fix (CAP-1's own schema bug), not new behavior.

## Non-goals

- Retiring the mcp 1.x/2.x `ImportError` skip in the web image (slice 3 — gated on an
  upstream FastMCP 4 release or an unpinned Langflow; tracked in
  `spec-mcp-era-isolation/retire-skip.md`).
- The factory stdio wire-format translator (`spec-mcp-factory-stdio-translator`, slice
  2) — a different, already-specced problem (modern MCP clients vs FastMCP 3 stdio
  tools), not this HTTP dispatch path.
- Generalizing real-tool hosting to every station with a `django_<name>_portal` package.
  This Spec scoped CAP-1 to marshal alone (see Design Notes) — a future effort should
  decide whether/when the remaining seven stations need the same treatment.

## Success signal

A real bmad-loop-style run, driven from a workstation against a real deployed
cluster, publishes through `/stations/marshal/mcp` to marshal's real held-loop tools,
appears on `/runs/`, and its timing is queryable after the workstation that ran it is
gone — closing the one item `spec-run-state-one-publisher/verification-2026-09-12.md`
left `NOT PROVEN`. **Met 2026-09-12.**

## Design Notes (resolved open questions)

- **ORM access shape.** A minimal Django settings module
  (`src/platform/mcp_host/settings.py`) registers only `django_pyforge` +
  `django_marshal_portal` in `INSTALLED_APPS`, with real `DATABASE_URL`/
  `DJANGO_SECRET_KEY` and no `CACHES` config — the four functions this sidecar calls
  (`publish_held_loop_bounded`/`heartbeat_held_run`/`complete_held_run`/
  `list_published_story_tasks`) never touch `django.core.cache`, and
  `REDIS_BROKER_URL`/`REDIS_CACHE_URL` are deliberately left unset so the best-effort
  `run.started` event publish silently no-ops rather than needing a Redis client
  dependency at all. `mcp_host/app.py` wraps `django.setup()` in a try/except: any
  failure falls back to the identity stub for every station (CAP-2's guarantee).
- **Station scope.** CAP-1 scoped to marshal alone. `MarshalPortalConfig.ready()` is
  lean (registers a runner callback only, no `pyforge.marshal` import at all) —
  unlike, e.g., `django_mason_portal`'s eager `pyforge.mason.boot` import
  (`config/settings/base.py`'s own comment names this exact conflict with the web
  image's `langflow-base` pin) — making marshal the safe, self-contained first
  candidate. Generalizing to the other seven stations is deferred, not blocked.
