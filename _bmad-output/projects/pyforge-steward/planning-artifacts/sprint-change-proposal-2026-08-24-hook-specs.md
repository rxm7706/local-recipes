---
title: Sprint Change Proposal — CAP-18 hook-spec + plugin registration
date: 2026-08-24
project: pyforge-steward
chain: pyforge-unifying-strategy
status: approved
trigger: operator bind — missing story not in Epics 18–30
mode: batch
---

# Sprint Change Proposal — One plugin API, then Warden, then station processes

## 1. Issue summary

AD-21 was recorded as an invariant. Canopy Epics **18–30** do not implement it. The
operator named the missing work:

1. **Shared contract** — one hook-spec + plugin-registration shape (`pyforge-core`) so
   eight stations do not invent eight APIs.
2. **PR-gate** — Warden owns gate hook specs; scanners become optional plugins; default
   Warden stays green with no Checkmarx. **New Warden epic** (retract “record only”).
3. **Station processes** — each `pyforge-*` package extracts one replaceable layer;
   today's backend is the default plugin.

Earlier OM SCP said **no CAP-18** meaning **no scorecard capability**. This proposal
mints **CAP-18 for hook specs**, which is not a scorecard.

## 2. Impact

| Artifact | Change |
|---|---|
| SPEC | CAP-18 |
| PRD | FR-43, FR-44, FR-45; SM-9; §2/§10/§14 stale-tail fixes |
| Spine | AD-21 binds CAP-18 |
| Steward epics | **Epic 32** (S-32.1 shared contract, S-32.2 deploy-profile plugins) |
| Warden | **Epic 9** (S-9.1–9.3) |
| Peers | atlas 18.1, mason 10.1, marshal 26.1, doctor 17.1, herald 16.1, scribe 4.1 |
| `DW-OM-2026-08-24` | `close_when` is implementation, not markdown-only |

Epics 18–30 unchanged in scope. They must not violate CAP-18.

## 3. Approach

Direct Adjustment. Order: **S-32.1 → Warden 9.x → station process stories**. First
Canopy chrome dispatch remains **S-18.1** (can run in parallel with 32.1).

## 4. Approval

Approved with the operator's three-layer plan (2026-08-24).
