---
title: Sprint Change Proposal — station skill/persona + first portal job
date: 2026-08-25
project: pyforge-steward
chain: pyforge-unifying-strategy
status: approved
trigger: operator — next build wave after Canopy drain; do not remint 18–30
mode: batch
---

# Sprint Change Proposal — Steward-owned skill, persona, first portal job

## 1. Issue summary

Canopy Epics 18–32 and peer CAP-18 hooks are landed. Steward 29 proved SKF+persona *shape*
(Scribe) and a reporter. Epic 19 shipped empty HTMX shells. Remaining 03 work is
**station-owned**, not a second unifying-strategy architecture.

## 2. Impact

| Artifact | Change |
|---|---|
| Steward `epics.md` | **Epic 33** (S-33.1 skill+persona, S-33.2 provision-list portal). Not added to Canopy 18–30 list. |
| Peer stations | Own epics (atlas 19, warden 10, doctor 18, herald 17, marshal 27, mason 11, scribe 5) |
| Canopy SPEC / spine | Unchanged. No second architecture. |
| CRC / Liquibase | Ops: CRC Stopped this session; `:17`/`:18` not applied |

## 3. Approach

Direct Adjustment. First dispatch per station: skill/persona story, then portal slice.
Mason: persona consults `conda-forge-expert` only (no replacing SKF).

## 4. Approval

Operator directed 2026-08-25: complete planning queue item 2.
