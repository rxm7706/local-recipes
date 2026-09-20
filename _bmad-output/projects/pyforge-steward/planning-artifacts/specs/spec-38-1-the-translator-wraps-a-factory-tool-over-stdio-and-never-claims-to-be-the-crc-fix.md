---
title: '38.1: The translator wraps a factory tool over stdio and never claims to be the CRC fix'
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

**Problem:** a stdio process that speaks MCP 1.x-legal traffic to a FastMCP 3 / mcp 1.x child

**Approach:** a modern client (no handshake, `_meta` on every call) can call a factory tool without either SDK being loaded in the same interpreter.

## Boundaries & Constraints

**Always:**
- The contract is the story body in `epics.md` (Intent, Surface, Given/When/Then).
- Filename is exactly `spec-38-1-the-translator-wraps-a-factory-tool-over-stdio-and-never-claims-to-be-the-crc-fix.md` (CHAIN-STANDARD §5).

**Never:**
- Do not mint a new story or change `epics.md` numbering.
- Do not hand-edit `sprint-status-ledger.yaml`.
- Do not touch `recipes/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| a modern client with no handshake **When** it calls a wrapped child **Then** the child sees a fabricated `initialize` handshake and every `_meta` key is stripp… | it calls a wrapped child **Then** the child sees a fabricated `initialize` handshake and every `_meta` key is stripped… | the child sees a fabricated `initialize` handshake and every `_meta` key is stripped before the child sees the request | fail loud; never silent skip |
| And-clause from epics.md | when the story lands | a handshake-era client passes through without a double `initialize` | n/a |
| And-clause from epics.md | when the story lands | a plain-text or `text`-keyed child result wraps as `content:[{type:"text",text}]` | n/a |
| And-clause from epics.md | when the story lands | an unsupported protocol version is rejected before the child process starts | n/a |
| And-clause from epics.md | when the story lands | `--help` and the module docstring both state this does not change gunicorn `/stations/<name>/mcp` and does not lift `python-agent-platform` (CAP-2's non-CRC claim) | n/a |
| And-clause from epics.md | when the story lands | the process imports neither `mcp` 1.x nor 2.x | n/a |

</intent-contract>

## Binding

Parent Spec capability: `named on the story in epics.md`.
Surface: named on the story in epics.md
Ledger key: `38-1-the-translator-wraps-a-factory-tool-over-stdio-and-never-claims-to-be-the-crc-fix`.
Ledger status at mint (unchanged): `done`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-38-1-the-translator-wraps-a-factory-tool-over-stdio-and-never-claims-to-be-the-crc-fix.md`.

## Epic excerpt

As an MCP client operator,
I want a stdio process that speaks MCP 1.x-legal traffic to a FastMCP 3 / mcp 1.x child,
So that a modern client (no handshake, `_meta` on every call) can call a factory tool
without either SDK being loaded in the same interpreter.

**Type:** feature • **Effort:** S • **Deps:** none • **FR/AD:** spec-mcp-factory-stdio-translator CAP-1, CAP-2
**Given** a modern client with no handshake **When** it calls a wrapped child **Then** the
child sees a fabricated `initialize` handshake and every `_meta` key is stripped before
the child sees the request
**And** a handshake-era client passes through without a double `initialize`
**And** a plain-text or `text`-keyed child result wraps as `content:[{type:"text",text}]`
**And** an unsupported protocol version is rejected before the child process starts
**And** `--help` and the module docstring both state this does not change gunicorn
`/stations/<name>/mcp` and does not lift `python-agent-platform` (CAP-2's non-CRC claim)
**And** the process imports neither `mcp` 1.x nor 2.x
**Status:** done — shipped `ba4ae74f73` (2026-08-26), tests in
`tests/scripts/test_mcp_factory_stdio_translator.py` (6 passed)

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `38-1-the-translator-wraps-a-factory-tool-over-stdio-and-never-claims-to-be-the-crc-fix: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
