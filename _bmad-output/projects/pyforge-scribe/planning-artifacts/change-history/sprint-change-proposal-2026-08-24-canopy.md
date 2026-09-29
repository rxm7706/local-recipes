---
name: sprint-change-proposal-2026-08-24-canopy
type: sprint-change-proposal
status: approved
created: '2026-08-24'
scope: pyforge-unifying-strategy Phase 5 — pyforge-scribe Canopy obligations
approach: Direct Adjustment
---

# Sprint Change Proposal — 2026-08-24 (Canopy)

## 1. Issue Summary

**Trigger:** Canopy **CAP-14** / **steward Epic 28** (`Scribe's graph outlives a file`) —
Phase 5 `bmad-correct-course` for station **pyforge-scribe**, headless/express.

**Category:** Planning premise correction + Canopy obligation recording.

**Problem statement:** `docs/dreams/pyforge-unifying-strategy.md` (BS-1, §5 station
course-correction) assumed Scribe already had a **dual-driver** storage engine (SQLite local
vs PostgreSQL production). That premise is **false**. Shipped Scribe v1 implements a single
concrete adapter — **`FlatFileGraphStore`** (deterministic sorted-keys JSON at
`.claude/data/pyforge-scribe/graph.json`) — behind the existing **`GraphStore` port** (Story
2.1 / AD-5). There is no SQLite driver, no PostgreSQL driver, and no runtime driver selection
today.

**Evidence:** `spec-2-1-graphstore-port-flat-file-v1-adapter.md` (shipped); live
`graph_store.py::FlatFileGraphStore`; technical research
(`technical-scribe-capture-promotion-graph-2026-08-08.md`) documents flat-file as the resolved
v1 choice. Steward Epic 28 Stories 28.1–28.2 now own durable PG/pgvector + semantic recall on
that same port (FR-35, FR-36; parent AD-1, parent AD-5 for schema isolation).

**What this proposal does:** Records Scribe's Canopy obligations without minting a competing
**Epic 4** that would re-implement steward Epic 28. Scribe's local epics remain 1–3; graph
durability and semantic recall ride the Canopy vehicle.

## 2. Impact Analysis

### Epic impact

- **Epics 1–3 (scribe-local, canonical):** **No structural change.** Epic 1 (capture/promotion)
  and Epic 2 (compile/recall on `FlatFileGraphStore`) are shipped. Epic 3 (transcript mining)
  is in flight. None are superseded.
- **Epic 4 (would-be graph backend):** **Explicitly not created.** Steward Epic 28 is the sole
  vehicle for CAP-14 (PostgreSQL/pgvector durable driver + local-path retention + semantic
  recall). A scribe-local Epic 4 would duplicate FR-35/FR-36 and split ownership.
- **Steward Epics 19, 21, 29 (Canopy, cross-station):** Scribe's **five-tier** obligations —
  portal at `/stations/scribe/`, MCP service face, SKF domain skill, station persona — are
  owned there (FR-9, FR-11, FR-37–FR-39), not as new scribe epics.

### Story impact

- **No new scribe stories** for graph durability or semantic recall. Steward **S-28.1**
  (PostgreSQL driver behind existing port) and **S-28.2** (semantic recall) are the binding
  stories.
- Scribe cooperates by keeping **`compile.py` / `recall.py` caller-agnostic** (AD-5) and by
  not introducing alternate storage paths (no SQLite-over-RWX; no second graph backend epic).

### Artifact conflicts

- **`docs/dreams/pyforge-unifying-strategy.md` BS-1:** Reads as if SQLite local already
  exists. Corrected here and in `deferred-work-ledger.md` (`DW-CANOPY-2026-08-24`); Dream
  Realization log update is a separate Herald/steward pass, not this scribe-local proposal.
- **`ARCHITECTURE-SPINE.md` AD-5 Deferred note:** Still accurate — engine choice was deliberately
  open; flat-file won v1. CAP-14 adds a second adapter via steward Epic 28, not a scribe epic
  rewrite.
- **PRD / specs (Epics 1–3):** Unaffected. FR-12/FR-13 recall semantics hold; semantic recall
  is an additive capability (FR-36), not a regression on lexical recall.

### Technical impact

- **Dual-driver internals stay scribe-local** behind `GraphStore`; **schema isolation** is
  parent **AD-1** / parent **AD-5** (`scribe_schema` on the platform PostgreSQL cluster).
- **Rejected:** SQLite mounted over RWX/NFS/CephFS — BS-1's failure mode; CAP-14 mandates
  PostgreSQL/pgvector for multi-pod durability, not SQLite-over-shared-volume.
- **Five-tier symmetry:** CLI (`scribe` / future `pyforge scribe`) exists; portal, MCP, skill,
  persona tiers are steward-owned (Epics 19/21/29). **No second chrome, no extra port** beyond
  the estate's `:8005` service face.

## 3. Recommended Approach

**Option 1 — Direct Adjustment (SELECTED, APPROVED 2026-08-24).** Append Canopy obligations
to `epics.md`, record the premise correction in `deferred-work-ledger.md`, and **point** graph
backend work at steward Epic 28. Effort: **Low** (documentation + obligation binding only).
Risk: **Low** — avoids duplicate epic ownership.

**Option 2 — New scribe Epic 4:** **Rejected.** Would re-implement steward Epic 28 and violate
Phase-5 ruling (one Canopy vehicle per capability).

**Option 3 — MVP review:** **Not needed.** Scribe's shipped capture/compile/recall loop is
complete; CAP-14 extends durability and recall quality, it does not retract MVP scope.

## 4. Detailed Change Proposals

### `epics.md` — append `## Canopy obligations (2026-08-24)`

Thin cooperation note: scribe-local epics stop at 3; CAP-14 / FR-35–FR-36 / five-tier gaps
delegate to steward Epics 28, 19, 21, 29. No story list.

### `deferred-work-ledger.md` — append `DW-CANOPY-2026-08-24`

Records the false dual-driver premise, current `FlatFileGraphStore` ground truth, SQLite-over-RWX
rejection, and steward Epic 28 as the implementation vehicle.

### Artifacts explicitly NOT modified in this pass

- No new Epic 4 or stories in `epics.md`.
- No PRD or architecture spine rewrites (steward Epic 28 carries FR-35/FR-36 binding).
- No code changes — implementation handoff is steward Epic 28.

## 5. Implementation Handoff

**Scope classification:** Minor (planning/obligation recording only).

**Routed to:** **pyforge-steward** Epic 28 (primary implementer for CAP-14 graph backend +
semantic recall). **pyforge-scribe** maintains AD-5 port discipline and cooperates in review
when steward stories touch `GraphStore` callers.

**Success criteria:**

- Steward Epic 28 S-28.1 passes the graph suite against **both** durable PG/pgvector and the
  existing local flat-file path; callers do not branch on driver.
- Steward Epic 28 S-28.2 delivers semantic recall that finds targets lexical overlap misses.
- Scribe planning artifacts contain **no Epic 4** and **no duplicate CAP-14 story list**.
- Five-tier completeness for Scribe is verifiable via steward Epic 29 S-29.3 when executed.
