---
name: sprint-change-proposal-2026-08-24-canopy
type: sprint-change-proposal
status: approved
created: '2026-08-24'
scope: pyforge-unifying-strategy Phase 5 — pyforge-warden Canopy obligations (planning-only)
approach: Direct Adjustment
---

# Sprint Change Proposal — Canopy obligations (2026-08-24)

## 1. Issue Summary

**Trigger:** Phase 5 of `docs/dreams/pyforge-unifying-strategy.md` — per-station
`bmad-correct-course` to record Canopy obligations without expanding warden scope.

**Category:** Cross-station platform convergence (steward-owned execution).

**Problem statement:** Warden ships the estate's only mounted portal today (`compliance_face`
at `/compliance/`, Epic 8). Canopy FR-9a/9b (steward Story 19.1) relocates it to
`/stations/warden/` behind a **permanent** redirect and renames the reusable Django app to
distribution `django-warden`, module `django_warden_fabric`, label `warden_fabric`. Existing
models stay; the portal remains a projection — no second write path. Warden planning artifacts
that name `compliance_face` must still resolve after that rename (Story 19.1 AC).

**This pass:** record the obligation and add pointers. **Out of scope:** performing the rename
in warden package code, adding chrome, FastAPI ports, or a second dashboard stack.

**Evidence:** `config/urls.py` mounts the portal at `/compliance/`; steward Epic 19 Story 19.1
binds FR-9a/FR-9b; pyforge-unifying-strategy realization log 2026-08-24 (portal URL scheme +
reusable-app triple).

## 2. Impact Analysis

### Epic impact

- **Epics 1–8 (warden ledger, complete):** unchanged. Epic 8 (`spec-compliance-factory-web-face`)
  remains the shipped web-face contract; mount path and Django distribution name are Canopy
  concerns owned by steward, not a ninth warden epic.
- **No new warden epic.** Last warden epic is **8**.

### Five-tier symmetry (warden station)

| Tier | Surface | Status | Owner |
|------|---------|--------|-------|
| 1 — CLI | `pyforge-warden` / `warden` entry point | **Shipped** (Epics 1–7) | warden |
| 2 — Web Portal | `compliance_face` → `django_warden_fabric` at `/stations/warden/` | **Shipped, being moved** (Epic 8; execution = steward S-19.1) | steward |
| 3 — FastAPI/MCP Service | Station MCP face on host ASGI | **Not started** | steward Epic 21 |
| 4 — Domain Skill | Station SKF skill | **Not started** | steward Epic 29 |
| 5 — Agent Persona | Station autonomous persona | **Not started** | steward Epic 29 |

### Artifact conflicts

- **`epics.md`:** append `## Canopy obligations (2026-08-24)` — pointer to steward chain, no
  story renumbering.
- **`deferred-work-ledger.md`:** append `DW-CANOPY-2026-08-24` — tracks rename/relocation until
  S-19.1 lands.
- **Warden specs:** no `/compliance/` hard-codes found in `planning-artifacts/specs/`; no spec
  rewrites required. If future edits cite the old mount, they remain valid via the permanent
  redirect (FR-9a).

### Technical impact (deferred to steward S-19.1)

- URL mount: `/compliance/` → permanent redirect → `/stations/warden/`
- Package rename: `compliance_face` → `django-warden` / `django_warden_fabric` / `warden_fabric`
- App-label migration must preserve job rows, `django_migrations`, and content types
- Must complete before Epic 27 stories that revoke app-role DDL (FR-9b sequencing)

## 3. Recommended Approach

**Selected: Direct Adjustment.** Append planning obligations and pointers; do not reopen shipped
warden epics or add chrome/MCP/dashboard scope to warden.

| Option | Selected | Rationale |
|--------|----------|-----------|
| Direct Adjustment | **Yes** | Obligation recording only; execution lives in steward Epic 19. |
| Rollback | No | Epic 8 portal is shipped and correct; only mount naming moves. |
| MVP review | No | No warden MVP change; five-tier gaps 3–5 are explicitly steward-owned. |

**Effort:** trivial (this planning pass). **Risk:** low — no warden code changes in this pass.
**Timeline:** warden ledger frozen at Epic 8; S-19.1 is steward-scheduled.

## 4. Detailed Change Proposals

### 4.1 `epics.md` — append `## Canopy obligations (2026-08-24)`

Records five-tier status, steward ownership of FR-9a/9b execution, and pointer to this proposal.
No story additions under warden epics.

### 4.2 `deferred-work-ledger.md` — append `DW-CANOPY-2026-08-24`

Tracks portal rename/relocation until steward S-19.1 merges; cites Story 19.1 AC that warden
planning artifacts must still resolve.

### 4.3 Warden specs — no edits

Grep of `planning-artifacts/specs/` found no hard-coded `/compliance/` URLs. Specs name the
web face capability (`spec-compliance-factory-web-face`) without mount paths; they remain
authoritative. Post-rename resolution is satisfied by FR-9a permanent redirect for any
operational references outside this tree.

## 5. Implementation Handoff

**Scope classification:** Minor (planning-only).

**Routed to:** steward (`pyforge-steward`) — Story 19.1 for code/package/URL work; Epic 21/29
for tiers 3–5.

**Warden station success criteria (this pass):**

- [x] `sprint-change-proposal-2026-08-24-canopy.md` written and approved
- [x] `epics.md` carries Canopy obligations section
- [x] `deferred-work-ledger.md` carries `DW-CANOPY-2026-08-24`
- [x] No warden package rename performed
- [x] No new warden epic beyond 8

**Downstream (steward, not warden):** merge S-19.1; close `DW-CANOPY-2026-08-24` when
`compliance_face` identifiers are gone from `src/` and redirect is live.
