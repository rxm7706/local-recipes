---
name: sprint-change-proposal-2026-08-24-canopy
type: sprint-change-proposal
project: pyforge-herald
status: approved
created: '2026-08-24'
via: bmad-correct-course
mode: headless-express
approach: Direct Adjustment
scope: minor
trigger: Phase 5 — pyforge-unifying-strategy Canopy obligations (station 6/8)
artifacts_modified:
  - epics.md
  - deferred-work-ledger.md
---

# Sprint Change Proposal — Canopy obligations (2026-08-24)

## 1. Issue Summary

**Trigger:** Phase 5 of `docs/dreams/pyforge-unifying-strategy.md` — one `bmad-correct-course`
run per spoke station so every station planning artifact records its **Canopy obligations**
under steward-owned Epics 18–30, without duplicating that implementation chain locally.

**Category:** Architectural alignment — planning-only; no herald code changes in this pass.

**Problem statement:** Herald Epics 1–15 are **complete** (47 foundation/Moments stories + live
backend + deck QA + PPTX pipeline). The unifying strategy binds **five-tier symmetry** (CLI,
Web Portal, FastAPI/MCP Service, Domain Skill, Agent Persona) across all eight stations, but
Herald's planning artifacts predate the Canopy contract and do not record which tiers Herald
owns vs which tiers steward delivers through the platform host.

**Evidence:**

- `sprint-status-ledger.yaml`: Epics 1–15 all `done`.
- `spec-pyforge-herald/SPEC.md:137`: Herald explicitly **does not** own the Guildhall console.
- `spec-herald-moments-2-4-live-backend/SPEC.md`: Herald adopts `spec-secure-live-dashboards`
  (framework-neutral static dashboard) — second named adopter after atlas; operational hosting
  is steward-owned.
- Unifying-strategy realization log (2026-08-24): Phase-5 scope is all eight stations; steward
  owns the Canopy; peer stations record obligations only.

## 2. Impact Analysis

### Epic impact

- **Epics 1–15:** **No change.** All stories remain `done`; no acceptance criteria reopened.
- **Epic 16+:** **Must not be created** to copy steward Epics 18–30 (portal host, MCP faces,
  unified CLI spine, SKF skills, personas, Wagtail front door, Liquibase, packaging chain).
  Herald's last epic stays **15**.

### Story impact

- **None.** No story text, ledger keys, or sprint-status entries change.

### Artifact conflicts

| Artifact | Action |
|---|---|
| `epics.md` | Append `## Canopy obligations (2026-08-24)` |
| `deferred-work-ledger.md` | Append `DW-CANOPY-2026-08-24` |
| `spec-pyforge-herald/SPEC.md` | **Unchanged** — non-goals already align (no console, no Lane 1 CMS) |
| `ARCHITECTURE-SPINE.md` | **Unchanged** — deck-bridge ADs stand; Canopy integration is steward-side mount |
| PRD / UX | **Unchanged** — Moments static web surface remains in scope; portal projection is steward |

### Technical impact

- **Portal:** `/stations/herald/` via steward Epic 19 (`django-herald` / `django_herald_<app>` /
  `herald_<app>` naming triple).
- **Service face:** `POST /stations/herald/mcp` on host ASGI (steward Epic 21.4) — replaces any
  standalone `:8006` or `services/` FastAPI pattern; existing transport bridge migrates, not
  duplicates.
- **CLI:** `herald` entry point remains; `pyforge herald …` dispatch is steward Epic 22.
- **Skill + persona:** SKF compiles from `pyforge-herald`; Agent-Herald consults it (steward
  Epic 29).
- **Dashboard:** Moments UI stays static/framework-neutral; CAP-7 isolation via
  `pyforge.steward.dashboard`; **no Vizro adoption**.

## 3. Recommended Approach

**Option 1 — Direct Adjustment (SELECTED, APPROVED 2026-08-24).** Record Canopy obligations
in planning artifacts only. No new herald epics, no story rewrites, no rollback of shipped work.

**Option 2 — Rollback:** Not applicable — nothing to revert.

**Option 3 — MVP review:** Not applicable — herald product scope is unchanged; only tier
ownership is clarified.

**Effort:** Minor (documentation). **Risk:** Low — explicit boundary prevents duplicate
implementation. **Timeline:** No dispatch impact on herald; steward Epics 18–30 carry build work.

## 4. Detailed Change Proposals

### epics.md — append section

```markdown
## Canopy obligations (2026-08-24)
```

(Full text applied in repo — see `epics.md` tail.)

**Rationale:** Makes steward-owned tiers visible at the canonical epic source without inventing
herald Epics 16+.

### deferred-work-ledger.md — append entry

```markdown
## DW-CANOPY-2026-08-24
```

(Full text applied in repo — see ledger tail.)

**Rationale:** Durable cross-station pointer so integration debt is not re-discovered as herald
backlog items.

## 5. Implementation Handoff

**Scope classification:** Minor — planning documentation only.

**Routed to:** Steward (`pyforge-steward` Epics 19, 21, 22, 29) for Canopy build; Herald
consumes at integration hooks when those epics land.

**Herald agent responsibilities (future, post-steward):**

1. Register portal views that project Moments data through `django-pyforge` client — no raw HTTP
   to station internals.
2. Mount existing MCP/transport surface at `/stations/herald/mcp` — retire standalone service
   assumptions in docs/runbooks.
3. Verify `pyforge herald …` dispatches to existing `herald` CLI without grammar fork.
4. Consume compiled `pyforge-herald` SKF skill; wire Agent-Herald persona per FR-38.

**Success criteria:**

- `epics.md` carries `## Canopy obligations (2026-08-24)`.
- `deferred-work-ledger.md` ends with `DW-CANOPY-2026-08-24`.
- No herald Epic 16+ appears in planning artifacts.
- Herald PRs that add second chrome, extra public ports, or `services/` FastAPI are review-blocked
  against this proposal.

---

**Approval:** Direct Adjustment — **approved** 2026-08-24 (headless-express; no interactive
elicitation).
