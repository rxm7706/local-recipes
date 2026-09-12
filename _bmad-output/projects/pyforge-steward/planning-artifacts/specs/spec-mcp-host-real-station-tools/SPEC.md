---
spec: mcp-host-real-station-tools
status: draft
created: "2026-09-12"
updated: "2026-09-12"
owner-dream: docs/dreams/mcp-host-real-station-tools.md
surface:
  - docs/dreams/mcp-host-real-station-tools.md
  - src/platform/mcp_host/app.py
  - src/platform/compose/mcp-host/Containerfile
  - src/shared/packages/django-pyforge/src/django_pyforge/mcp_dual_era.py
  - src/shared/packages/django-pyforge/src/django_pyforge/mcp_http.py
companions: []
sources:
  - ../../../../../../docs/dreams/mcp-host-real-station-tools.md
open_questions:
  - "How does the sidecar get Django ORM access for a station whose real app needs it (e.g. django_marshal_portal.mcp_asgi calling into django_pyforge.supervisor)? The sidecar image today runs no Django at all by design. Candidate shapes: (a) a minimal settings module registering only the portal AppConfigs + DB connectivity, no Langflow; (b) a station's real app builder takes an ORM-free path instead; (c) another shape entirely."
  - "Does CAP-1 need every station with a django_<name>_portal package, or should it scope to marshal's held-loop tools alone first (the only one a live production path currently needs) and generalize later?"
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
tools could run — but `mcp_host/app.py` builds each station's app with
`asgi_for_station(name)`, a function whose entire body is one tool, `station_face()`,
returning the station's own name string. No station's real tool surface (marshal's
held-loop `publish_loop_run`/`heartbeat_loop_run`/`complete_loop_run` included) is
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
- **CAP-2**
  - **intent:** A station with no real in-process MCP app keeps working exactly as
    slice 1 shipped it — the generic identity stub remains its answer.
  - **success:** `spec-mcp-era-isolation`'s own CAP-1..3 acceptance criteria (dual-era
    handshake, protocol-version negotiation, 405 on non-POST) still hold, unchanged,
    for any station without a real app, after this Spec's change lands.
- **CAP-3**
  - **intent:** CAP-3's own attended-CRC exercise can complete its one unproven item.
  - **success:** `spec-run-state-one-publisher`'s verification record is re-run and its
    "Live run appears on `/runs/`, timing survives teardown" row flips from
    `NOT PROVEN` to `PASS`.

## Constraints

- `spec-mcp-era-isolation`'s shipped slices 1–3 stay exactly as they are: the dual-era
  wire, the proxy dispatch in `dispatch_station_mcp`, `MCP_HOST_SIDECAR_BASE_URL`
  wiring, CAP-4's cluster-required fail-loud, the stdio translator (slice 2), and the
  `ImportError`-skip retirement gate (slice 3, `retire-skip.md`). This Spec is additive:
  what the sidecar hosts, never how it is reached.
- A station's own portal package (`django_<name>_portal`) stays that station's surface.
  This Spec owns only how the sidecar discovers and mounts what already exists there —
  it does not redesign any station's tool implementation.

## Non-goals

- Retiring the mcp 1.x/2.x `ImportError` skip in the web image (slice 3 — gated on an
  upstream FastMCP 4 release or an unpinned Langflow; tracked in
  `spec-mcp-era-isolation/retire-skip.md`).
- The factory stdio wire-format translator (`spec-mcp-factory-stdio-translator`, slice
  2) — a different, already-specced problem (modern MCP clients vs FastMCP 3 stdio
  tools), not this HTTP dispatch path.

## Success signal

A real bmad-loop-style run, driven from a workstation against a real deployed
cluster, publishes through `/stations/marshal/mcp` to marshal's real held-loop tools,
appears on `/runs/`, and its timing is queryable after the workstation that ran it is
gone — closing the one item `spec-run-state-one-publisher/verification-2026-09-12.md`
left `NOT PROVEN`.

## Open Questions

- How does the sidecar get Django ORM access for a station whose real app needs it
  (e.g. `django_marshal_portal.mcp_asgi` calling into `django_pyforge.supervisor`)? The
  sidecar image today runs no Django at all by design ("No Langflow. No FastMCP.").
  Candidate shapes: (a) a minimal settings module registering only the portal
  AppConfigs plus DB connectivity, no Langflow; (b) a station's real app builder takes
  an ORM-free path instead; (c) another shape entirely.
- Does CAP-1 need every station with a `django_<name>_portal` package, or should it
  scope to marshal's held-loop tools alone first (the only one a live production path
  currently needs) and generalize later?
