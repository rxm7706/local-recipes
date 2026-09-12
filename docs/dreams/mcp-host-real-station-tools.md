---
title: The sidecar that only says its own name
type: dream
owner: steward
status: dreamt
---

# The sidecar that only says its own name

## The Dream

An agent that reaches a deployed platform's `/stations/<name>/mcp` should get that
station's real tools — the ones the same code exposes in-process on a laptop or in
`platform-ci-local`. Today it gets one tool, for every station, no matter which
station's URL it called: `station_face()`, which returns the station's own name
string and nothing else. The mcp-host sidecar that `spec-mcp-era-isolation` shipped
to work around the web image's `mcp 1.x` pin is real infrastructure — a second
process, a second image, a live proxy hop — built to eventually carry real traffic.
It has never carried any.

> A bridge that only echoes the name of the far bank has not yet been walked across.

## Why now — found chasing a different proof

The 2026-09-12 CAP-3 attended CRC exercise set out to drive one real bmad-loop-style
run through a deployed platform and watch it appear on `/runs/`. Every layer beneath
that goal turned out sound once four small, genuine bugs were fixed (Containerfile
missing a `COPY`, two independent DNS-egress NetworkPolicy defects, a JWKS scheme
check, and — found in this same pass — an unwired assertion-signing keypair). A real
Authorization Code + PKCE login worked. A real IdP bearer verified. A real host
assertion minted. Then the actual publish call — `POST /stations/marshal/mcp`,
`publish_loop_run` — came back `Unknown tool: publish_loop_run`, from the real `mcp`
library's own tool manager, meaning a real `MCPServer` answered the call and simply
never had that tool registered.

Tracing it down: `platform.djangoEnv` (the chart's shared env helper, used by every
platform-image pod unconditionally) always sets `MCP_HOST_SIDECAR_BASE_URL`, and
`dispatch_station_mcp` in `django_pyforge/mcp_http.py` proxies **every** station's
MCP call to that URL whenever it is set — no per-station carve-out. The sidecar
(`src/platform/mcp_host/app.py`) builds its per-station apps with
`asgi_for_station(name)`, from `django_pyforge/mcp_dual_era.py` — a function whose
entire body is a `server.tool()` decorator around a closure that returns `name`. It
was written to prove the **dual-era handshake wire** works across the mcp 1.x/2.x
pin boundary (`spec-mcp-era-isolation` CAP-1..3, shipped and still true today —
re-verified live this same exercise), not to carry any station's real tool surface.

Checked directly against the web pod's own interpreter: `from mcp.server.mcpserver
import MCPServer` still raises `ModuleNotFoundError` there (the pin `mcp-era-isolation`
exists to work around is still live), so there is no way to reach `django_marshal_portal`,
`django_herald_portal`, or any other station's real MCP tools **in-process** either.
The sidecar is the only place any of them could run. None of them do.

`spec-mcp-era-isolation`'s own three-slice sequence (`docs/dreams/mcp-era-isolation.md`)
never names this as future work: slice 2 is a stdio wire-format translator for a
different problem (modern MCP clients vs FastMCP 3 stdio, unrelated to this HTTP
dispatch path — confirmed by reading `spec-mcp-factory-stdio-translator`), and slice 3
is retiring the in-process `ImportError` skip once FastMCP 4 or an unpinned Langflow
ships upstream. Nothing currently specced closes the gap between "the sidecar exists
and proxies correctly" and "the sidecar actually hosts a station's tools."

## What it looks like when real

- `POST /stations/marshal/mcp` with `publish_loop_run` reaches the SAME
  `publish_held_loop_bounded` code path a laptop or `platform-ci-local` run reaches
  — through the sidecar, not despite it.
- Every station wired with a real in-process MCP app today (`django_marshal_portal`,
  and whichever siblings define one) is reachable the same way once the sidecar is
  the only process that can load `mcp.server.mcpserver`.
- The generic `station_face()` stub stops being the answer for a station that has a
  real implementation; it may remain the fallback for one that does not.
- CAP-3's own live-run proof — a real bmad-loop run appearing on `/runs/`, its timing
  queryable after the workstation that ran it is gone — becomes achievable on a real
  deployed cluster, closing the one item its own verification record
  (`spec-run-state-one-publisher/verification-2026-09-12.md`) left "NOT PROVEN."

## Constraints / Non-goals

- **Not a rewrite of slice 1.** The dual-era handshake, the proxy dispatch, the
  `MCP_HOST_SIDECAR_BASE_URL` wiring, the CAP-4 cluster-required fail-loud — all stay
  exactly as shipped. This Dream is additive: what the sidecar hosts, not how it is
  reached.
- **Not the stdio translator.** `spec-mcp-factory-stdio-translator` (slice 2) solves a
  different, already-specced problem (modern-client wire format against FastMCP 3
  stdio tools). This Dream does not touch it.
- **Not retiring the ImportError skip.** Slice 3 stays gated on an upstream FastMCP
  4 / Langflow pin change, tracked in `retire-skip.md`. This Dream does not change
  when that skip goes away.
- **Django-in-the-sidecar is a real design question, not a given.** The real
  per-station apps (e.g. `django_marshal_portal.mcp_asgi`) call into
  `django_pyforge.supervisor`, which needs Django's ORM. The sidecar image
  deliberately runs no Django today ("No Langflow. No FastMCP. Imports
  `django_pyforge.mcp_dual_era` only."). Whether the derived Spec adds a minimal
  Django settings module + ORM connectivity to the sidecar, or finds another shape
  entirely, is an open question for that Spec to answer — not pre-decided here.
- **Cross-station by construction.** A station's own portal package
  (`django_<name>_portal`) stays that station's surface; this Dream's Spec only
  owns how the sidecar discovers and mounts what already exists.

## Kinships

[[mcp-era-isolation]] (the ancestor — slice 1 shipped the proxy and the handshake;
this Dream is the un-specced gap between "proxies correctly" and "hosts anything
real") · [[run-state-one-publisher]] (CAP-3's own live-run criterion is blocked on
this, discovered running its attended CRC exercise 2026-09-12) · [[pyforge-unifying-strategy]]
(CAP-17 — the criterion this ultimately unblocks) · [[pyforge-steward]] (the station;
`mcp_http.py`, `mcp_dual_era.py`, `mcp_host/app.py`, the chart's sidecar wiring are
all its surface) · [[pyforge-marshal]] (the first station whose real tools this
would actually carry, and the one that found the gap).

## Realization log

- **2026-09-12** — Seeded (operator ruling: gap-closure enters through the Dream-to-Code
  chain like any other effort). Found running the CAP-3 attended CRC exercise
  (`spec-run-state-one-publisher/verification-2026-09-12.md`) while chasing why a
  real, correctly-signed host assertion still could not publish a run: the mint
  path worked end-to-end once its own bug (unwired signing keypair, landed
  separately) was fixed, but the publish call hit the mcp-host sidecar's
  identity-only stub instead of marshal's real held-loop tools. Confirmed by
  reading `mcp_host/app.py`, `mcp_dual_era.py::asgi_for_station`, and
  `django_pyforge/mcp_http.py::dispatch_station_mcp`, and by re-checking live on
  the CRC cluster that the web pod's own interpreter still cannot import
  `mcp.server.mcpserver` — the sidecar remains the only place a real per-station
  MCP app could run, and none run there today. Cross-checked against
  `spec-mcp-era-isolation`'s own three-slice sequence and `spec-mcp-factory-stdio-translator`:
  neither names this gap. Next act: `bmad-spec` derives the Spec under `pyforge-steward`.
