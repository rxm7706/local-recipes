---
title: '58.1: A station''s real MCP tool is reachable through a deployed cluster'
type: 'feature'
created: '2026-09-18'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** an agent calling `/stations/<name>/mcp` to reach that station's real tool implementation, not the identity stub

**Approach:** a correctly-signed host assertion can publish a run against a deployed cluster instead of being answered with `Unknown tool`.

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-58-1-a-stations-real-mcp-tool-is-reachable-through-a-deployed-cluster.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| `asgi_for_station(name)` registered exactly one tool, `station_face()`, returning the station's own name **When** this story lands **Then** the sidecar discove… | this story lands **Then** the sidecar discovers marshal's real held-loop tools through the same `iter_station_mcp_apps(… | the sidecar discovers marshal's real held-loop tools through the same `iter_station_mcp_apps()` seam the web pod uses in-process | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | `POST /stations/marshal/mcp` with `publish_loop_run` returns a run handle from `publish_held_loop_bounded`, never `Unknown tool: publish_loop_run` | n/a |
| And-clause from epics.md | when the story lands | the MCP SDK's `**payload: Any` → required-nested-`payload` schema bug the first fix uncovered is fixed in the same pass | n/a |

</intent-contract>

## Binding

Parent Spec capability: `named on the story in epics.md`.
Surface: `src/platform/mcp_host/app.py`; `src/platform/mcp_host/settings.py` (minimal
Ledger key: `58-1-a-stations-real-mcp-tool-is-reachable-through-a-deployed-cluster`.
Ledger status at mint (unchanged): `done`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-58-1-a-stations-real-mcp-tool-is-reachable-through-a-deployed-cluster.md`.

## Epic excerpt

As a platform operator,
I want an agent calling `/stations/<name>/mcp` to reach that station's real tool
implementation, not the identity stub,
So that a correctly-signed host assertion can publish a run against a deployed
cluster instead of being answered with `Unknown tool`.

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-mcp-host-real-station-tools CAP-1
**Surface:** `src/platform/mcp_host/app.py`; `src/platform/mcp_host/settings.py` (minimal
Django settings — `django_pyforge` + `django_marshal_portal` only, no Langflow, no Redis);
`src/shared/packages/django-marshal/src/django_marshal_portal/mcp_asgi.py`
**Given** `asgi_for_station(name)` registered exactly one tool, `station_face()`, returning
the station's own name **When** this story lands **Then** the sidecar discovers marshal's
real held-loop tools through the same `iter_station_mcp_apps()` seam the web pod uses
in-process
**And** `POST /stations/marshal/mcp` with `publish_loop_run` returns a run handle from
`publish_held_loop_bounded`, never `Unknown tool: publish_loop_run`
**And** the MCP SDK's `**payload: Any` → required-nested-`payload` schema bug the first fix
uncovered is fixed in the same pass
**Status:** done — shipped `20a85dcc79` (2026-09-12); proven live against the deployed CRC
cluster: a real `HostPublisher` published, heartbeat'd and completed a run

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `58-1-a-stations-real-mcp-tool-is-reachable-through-a-deployed-cluster: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
