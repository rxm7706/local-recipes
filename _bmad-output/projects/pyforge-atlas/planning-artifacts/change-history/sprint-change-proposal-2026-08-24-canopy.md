---
doc_type: sprint-change-proposal
project: pyforge-atlas
date: 2026-08-24
trigger: Phase 5 — pyforge-unifying-strategy Canopy mounts eight stations on `src/platform/`
scope_classification: Minor
status: approved
approved: 2026-08-24
approach: Direct Adjustment
---

# Sprint Change Proposal — Canopy obligations (atlas station)

## 1. Issue Summary

Phase 5 of `docs/dreams/pyforge-unifying-strategy.md` records how the Platform Canopy
(`src/platform/`) mounts the eight spoke stations. Atlas Epics 1–17 are **done**; steward
Epics 18–30 own Canopy implementation. Without a station-scoped course correction, atlas
planning artifacts could silently re-scope steward work (second MCP server, Lane 1 absorbing
DW-H3, Vizro behind `pyforge.steward.dashboard`, duplicate DuckDB-writer gates, or a second
chrome/public port).

**Trigger:** headless/express `bmad-correct-course` for station **pyforge-atlas**, Phase 5.
Written only under physical
`_bmad-output/projects/pyforge-atlas/planning-artifacts/` (no `bmad-switch`).

## 2. Impact Analysis

### Epic impact

- Epics 1–17: **unchanged** — no new atlas epic; **no Epic 18** that copies steward.
- Epic 16 (`spec-wagtail-corporate-brain`) and DW-H3: **contract preserved**; relationship to
  Canopy Lane 1 is **not decided here** (joint open question `lane1-serves-dw-h3` with steward).
- Five-tier completeness (CLI, portal, MCP, skill, persona): **tracked as obligations** on
  steward Epics 19 / 21 / 29 — atlas does not implement portal chrome or host MCP mount.

### Artifact conflicts resolved

| Artifact | Change |
|---|---|
| `epics.md` | Append `## Canopy obligations (2026-08-24)` — five binding non-goals/cooperations |
| `deferred-work-ledger.md` | Append `DW-CANOPY-2026-08-24`; `lane1-serves-dw-h3` **still open** |
| `spec-wagtail-corporate-brain/SPEC.md` | **No edit** — not re-minted under Canopy Lane 1 |

PRD, architecture spine, and story specs: **no semantic change** beyond cross-references above.

### Technical impact

**None in atlas code.** Documentation-only boundary between atlas-local contracts (Epic 16
`LaSuiteClient` frozen REST, BS-5 read paths, existing `build_server()`) and steward Canopy
delivery (host ASGI MCP mount, portal registration, five-tier gates).

## 3. Recommended Approach

**Direct Adjustment — selected and approved 2026-08-24.**

Record atlas Canopy obligations and the joint DW-H3 / Lane 1 open question; do **not** add
implementation stories. Effort **Minimal**, risk **Low**, timeline **unchanged**.

Alternatives rejected:

- **Rollback** — nothing to revert; atlas shipped work stands.
- **MVP replan** — Canopy is steward scope; atlas ledger ends at Epic 17.

## 4. Detailed Change Proposals

### 4.1 `epics.md` — append `## Canopy obligations (2026-08-24)`

Five points (see applied section in `epics.md`):

1. **`lane1-serves-dw-h3`** — joint open question with steward; Canopy Lane 1 must not absorb or
   re-mint `spec-wagtail-corporate-brain`. Epic 16 + `LaSuiteClient` REST (`POST /api/v1/documents/`
   etc.) are **not** Wagtail's own API surface.
2. **MCP** — atlas ships `build_server()` today; steward Story **21.2** mounts it on host ASGI
   with the official `mcp` SDK and dual-era handshake. Atlas does **not** build a second server.
3. **CAP-7 boards** — host-backed analytical boards consume `pyforge.steward.dashboard` only.
   Atlas adopting that pattern for its own Vizro CLI boards is a **non-goal**; Vizro stays outside
   the host.
4. **BS-5 DuckDB** — single writer + `read_only=True` is atlas-local discipline; steward Story
   **25.2** owns the absence-test gate. Record cooperation; **do not duplicate** the story.
5. **Five-tier symmetry** — atlas already has CLI; steward Epics **19** (`/stations/atlas/` portal),
   **21** (MCP face), **29** (SKF skill + persona) complete the tiers. Atlas must not grow a second
   chrome layer or an extra public port.

### 4.2 `deferred-work-ledger.md` — append `DW-CANOPY-2026-08-24`

Consolidates Phase 5 canopy obligations and explicitly leaves **`lane1-serves-dw-h3` open**
(joint with steward). Does **not** close DW-H3.

## 5. Implementation Handoff

**Scope: Minor** — documentation applied in this pass; no bmad-loop story.

**Success criteria**

1. `sprint-change-proposal-2026-08-24-canopy.md` exists with `status: approved`.
2. `epics.md` carries `## Canopy obligations (2026-08-24)` after Epic 17 with **no Epic 18**.
3. `deferred-work-ledger.md` ends with `DW-CANOPY-2026-08-24`; `lane1-serves-dw-h3` recorded
   **open**, not answered.
4. No artifact re-scopes `spec-wagtail-corporate-brain` into Canopy Lane 1.

**Routed to:** steward Epics 18–30 for Canopy build; atlas maintains local contracts only.

## 6. Addendum — `lane1-serves-dw-h3` answered (2026-08-25)

**Answer: no.** Host Wagtail is `/cms/`. Atlas `LaSuiteClient` is La Suite Docs REST
(`POST /api/v1/documents/` etc. in `src/shared/packages/pyforge-atlas/src/pyforge/atlas/factory/lasuite.py`). Lane 1 does not satisfy DW-H3.
DW-H3 remains open until the attended bring-up of a server that speaks that contract.
`spec-wagtail-corporate-brain` is not absorbed. Recorded on steward unifying SPEC, atlas
`epics.md` canopy obligations, and `DW-CANOPY-2026-08-24`.
