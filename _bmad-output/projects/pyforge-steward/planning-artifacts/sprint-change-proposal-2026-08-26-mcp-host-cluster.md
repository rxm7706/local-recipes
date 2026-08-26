---
title: Sprint Change Proposal — cluster requires mcp-host
date: 2026-08-26
project: pyforge-steward
chain: spec-mcp-era-isolation
status: approved
trigger: Operator — enforce the MCP bridge on the cluster now; do not mix into Epic 34
mode: batch
scope: minor
operator: Rxm7706
---

# Sprint Change Proposal — MCP host required on cluster (CAP-4)

## 1. Issue summary

Slice 1 shipped the mcp-host sidecar and host proxy. Host MCP on CRC can still
look optional if the chart templates a blank image or production boots without
`MCP_HOST_SIDECAR_BASE_URL`. The operator wants that path **fail-loud**.

This is **not** unifying CAP-19. This is **not** slice 3 (do not delete the
ImportError skip).

## 2. Impact analysis

| ID | Status | Finding |
|---|---|---|
| 1.1 | Done | Trigger is operator enforce-bridge ruling. Chart already always emits mcp-host; gap is omission fail-loud. |
| 2.1 | Done | Epics 18–34 unchanged. New **Epic 35** (one story). |
| 3.1 | Done | `spec-mcp-era-isolation` CAP-4 + `cluster-required.md`. Unifying SPEC only points at the sibling. |
| 4.1 | Viable | Direct Adjustment. Risk: low (Helm `required` + Django check). |

## 3. Recommended approach

**Direct Adjustment.** Story 35.1 ready-for-dev. Dispatch **after** 34.1
(serial sessions; no code dependency).

## 4. Applied

- SPEC CAP-4; companions `cluster-required.md`, `retire-skip.md`, diagrams.
- Dreams: `mcp-era-isolation` sequence item 4; unifying Grounding pointer.
- `epics.md` Epic 35 / 35.1.
- Story spec `spec-35-1-cluster-requires-mcp-host.md`.
- PRD What Comes Next: 35.1 after 34.1.
- Readiness addendum for Epic 35.
- Ledger keys `35-1-cluster-requires-mcp-host`, `epic-35`.
