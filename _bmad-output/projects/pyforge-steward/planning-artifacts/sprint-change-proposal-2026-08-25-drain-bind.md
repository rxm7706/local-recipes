---
title: Sprint Change Proposal — bind the Canopy SPEC to the fleet drain
date: 2026-08-25
project: pyforge-steward
chain: pyforge-unifying-strategy
status: approved
trigger: docs/dreams/pyforge-unifying-strategy.md Grounding (drain + CRC) vs SPEC status ready / companions 2026-08-24
mode: batch
scope: minor
operator: Rxm7706 directed implementation (SPEC contract match the drain, not only the Dream)
---

# Sprint Change Proposal — Drain bind into the Canopy SPEC

## 1. Issue summary

The Unifying Strategy SPEC (`status: ready`, companions dated 2026-08-24) still describes a
**build program**: one portal, no `django-pyforge`, MCP as a future `services/` tier, 12-7
permanently skipped. The **canopy drain** (steward stories 18.1–32.2 ledger `done`, eight peer
CAP-18 hook stories `done`) and Dream Grounding dated 2026-08-25 already treat that residual as
**historical**. The contract was lying about what to build next.

Type: **misunderstanding of remaining scope** after implementation — not a new product, not a
rollback.

Evidence: steward `sprint-status-ledger.yaml` 18–32 `done`; peer ledgers (warden 9.1–9.3, mason
10-1, marshal 26-1, atlas 18-1, doctor 17-1, herald 16-1, scribe 4-1); Dream Grounding drain +
CRC blocks; `spec-12-1-…-verification-2026-08-25.md`; architecture spine paradigm `modular
monolith`.

## 2. Impact analysis

### Checklist (batch)

| ID | Status | Finding |
|---|---|---|
| 1.1 | Done | Trigger is drain completion vs stale SPEC, not a single red story. 12-7 remains live residual. |
| 1.2 | Done | Type: implementation overtook the ready-plan residual. |
| 1.3 | Done | Ledgers + Dream Grounding + CRC verification record. |
| 2.1 | Done | Epics 18–32 **stories** are done; epic *rollup* keys still `backlog` (pre-existing ledger shape). No new epic. |
| 2.2 | Done | **No story rewrite.** Banner + SPEC/companion bind. |
| 2.3 | Done | Do not re-open 18–32. Residual is 12-7 live `/ht/` + RFC-5 CRC holes (contrib, `liquibase` schema, engine boot DDL). |
| 2.4 | Done | No obsolete epic. Do **not** mint a `services/` epic. |
| 2.5 | Done | Do not resequence. Packaging 26.3/27.1 are ledger-done; CRC did not close CAP-9 live. |
| 3.1–3.4 | Done | SPEC kernel + companions + PRD vision + epics banner. No UX artifact. |
| 4.1 | Viable | Direct Adjustment. Effort: S. Risk: Low (docs only). |
| 4.2–4.3 | Not viable | Do not roll back drain; do not shrink CAPs. |
| 4.4 | Done | **Option 1 — Direct Adjustment.** Operator already directed apply. |

### Epic / story impact

None of Epics 18–32 gain or lose stories. Peer stations stay on **one CAP-18 obligation** each.
Steward **12-7** stays the live-cluster story on `spec-python-agent-platform` / 12.1 orbit — this
chain’s CAP-9 **success** is not claimed until `/ht/` 200 after governed DDL.

### Artifact conflicts

- SPEC.md + companions (convergence, architecture-diagrams, resilience RFC-5, stack sequencing, memlog)
- PRD vision / status
- epics.md Canopy list banner
- Dream already updated (not this SCP’s write)

### Technical impact

None in this pass (docs). CRC follow-through (changeset 15, schema create, image overlay) stays
12-7 execution, not a new FR.

## 3. Recommended approach

**Direct Adjustment.** Classify **Minor**. Apply in this session.

## 4. Detailed change proposals (applied)

See git diff on the files listed in §5. Kernel moves:

- SPEC `status: in-progress`; `updated: 2026-08-25`; `services/**` dropped from `surface`.
- Why / CAP-4 / CAP-9 / Always lines match drain + CRC holes.
- Convergence residual 1–20 marked **landed 2026-08-25** with live leftovers named.
- Architecture diagram residual subgraph → shipped; leftover = live CAP-9 / 12-7.
- RFC-5 companion: contrib changelog, create `liquibase` schema, no engine boot DDL.
- Stack: packaging stories ledger-done; not a second “open with packaging” schedule.
- PRD: vision no longer “one of eight portals.”
- Epics: Canopy list notes stories `done`; rollup keys unchanged.

## 5. Implementation handoff

**Scope:** Minor — Developer (this session).

**Success:** SPEC companions and PRD no longer instruct a greenfield `services/` farm or an
unbuilt chrome package; 12-7 / CAP-9 live holes remain explicit; CAP-18 remains hooks not
scorecard.

**Routed to:** applied below.
