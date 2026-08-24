---
name: sprint-change-proposal-2026-08-24-canopy
type: sprint-change-proposal
status: approved
created: '2026-08-24'
scope: pyforge-unifying-strategy Phase 5 — Canopy obligations (pyforge-mason)
approach: Direct Adjustment
---

# Sprint Change Proposal — 2026-08-24 (Canopy / pyforge-mason)

## 1. Issue Summary

**Trigger:** Phase 5 of `docs/dreams/pyforge-unifying-strategy.md` — the Platform Canopy
(`src/platform/`) mounts **mason** as one of eight spoke stations. Mason's existing epic chain
(Epics 1–9, CLI packaging factory) predates the Canopy binding and must record its obligations
without duplicating steward's implementation epics (18–30).

**Category:** Architecture binding — record cross-station contracts, no mason scope expansion.

**Problem statement:** The unifying-strategy Dream's BS-8 example ("Mason scans MinIO on boot")
and the five-tier symmetry matrix imply portal, MCP, SKF skill, and persona surfaces mason does
not own. Without an explicit correct-course pass, implementers could (a) mint mason Epics 10+
copying steward 18–30, (b) introduce MinIO/boto3 boot reconciliation, or (c) treat SKF-compiled
`pyforge-mason` as a replacement for the hand-authored `conda-forge-expert` operating skill.

**Evidence:** Steward `epics.md` already binds FR-9/11/17/37–39 to Epics 19/21/24/29; Story 25.4
names mason operators and forbids MinIO reconcile; canopy AD-17 preserves hand-authored CFE.
Mason's last epic is **9** (`External integration seams`); Epics 1–8 cover the CLI factory.

## 2. Impact Analysis

### Epic impact

- **Epics 1–9 (mason):** **Unchanged.** No story text edits; no new mason epics.
- **Steward Epics 18–30:** **Owner of Canopy implementation.** Mason consumes; does not copy.
- **No epics become obsolete.** No rollback.

### Story impact

- **No mason stories added or re-scoped.** Portal (`/stations/mason/`), MCP
  (`POST /stations/mason/mcp`), SKF domain skill (`pyforge-mason`), persona (`Agent-Mason`),
  event produce/consume, and PostgreSQL boot reconcile land under steward stories — principally
  S-19.2, S-21.4, S-24.1/24.2, S-25.4, S-29.1–29.3.
- **Mason may gain event producers later** (when build/run surfaces emit CloudEvents); types
  register in `django-pyforge`, backbone is steward Epic 24.

### Artifact conflicts

- **`epics.md`:** append `## Canopy obligations (2026-08-24)` — authoritative mason-side record.
- **`deferred-work-ledger.md`:** append `DW-CANOPY-2026-08-24` — tracks steward-owned work.
- **PRD / architecture spine:** no edits required; mason ADs remain CLI-factory scoped.
- **Liquibase / OpenFeature / cachebox packaging:** explicitly **out of mason chain**
  (operator-owned; steward S-26.3 gate).

### Technical impact

- **Forbidden:** MinIO or S3 object-store scan on mason service boot; boto3/MinIO as mason
  runtime backing store.
- **Required pattern (steward S-25.4):** idempotent startup reconcile against **PostgreSQL**
  (canonical anchor) plus **RWX-mounted files** when present.
- **Preserved:** `conda-forge-expert` hand-authored; SKF compiles station domain skill only.
- **Topology:** one host ASGI process — no second chrome, no extra public port (canopy AD-1,
  AD-5, AD-10).

## 3. Recommended Approach

**Option 1 — Direct Adjustment (SELECTED, APPROVED 2026-08-24).** Append canopy obligation
sections to mason planning artifacts; defer all implementation to steward chain. Effort: **Minor**
(documentation only). Risk: **Low** — explicit non-goals prevent scope creep.

**Option 2 — Rollback:** not applicable. No mason Canopy code shipped.

**Option 3 — MVP review:** not needed. Mason Epics 1–9 remain the mason MVP; Canopy tiers 2–5
are steward-delivered extensions.

## 4. Detailed Change Proposals

### `epics.md` — append `## Canopy obligations (2026-08-24)`

Records: five-tier table (CLI exists; portal/MCP/skill/persona steward-owned); MinIO forbidden;
CFE hand-authored; event backbone participation rules; explicit non-goals (no Epic 10+, no
steward 18–30 copy, no operator packaging in mason chain).

### `deferred-work-ledger.md` — append `DW-CANOPY-2026-08-24`

Single umbrella entry pointing at steward Epics 19/21/24/29 and S-25.4 for mason-specific
reconcile; status `open` until steward chain delivers the five missing tiers.

**No changes proposed to:** mason PRD, architecture spine, story specs, Epics 1–9 text,
`conda-forge-expert` skill files.

## 5. Implementation Handoff

**Scope classification: Minor** — documentation binding only; zero mason code changes from this
proposal.

**Routed to:** Steward station (`pyforge-steward` Epics 19/21/24/29) for Canopy surfaces;
mason station continues Epics 1–9 CLI factory work unchanged.

**Success criteria:**

1. Mason `epics.md` carries `## Canopy obligations (2026-08-24)`.
2. `DW-CANOPY-2026-08-24` is the durable deferred-work pointer.
3. No mason epic numbered ≥10 appears in mason planning artifacts.
4. Any future mason boot-reconcile design cites PostgreSQL (+ RWX files), never MinIO.
5. SKF `pyforge-mason` and hand-authored `conda-forge-expert` coexist per canopy AD-17.

**Approval:** Direct Adjustment — **approved 2026-08-24** (headless-express / batch Phase 5).
