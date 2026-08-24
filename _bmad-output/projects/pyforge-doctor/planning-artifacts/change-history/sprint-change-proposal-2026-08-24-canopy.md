---
name: sprint-change-proposal-2026-08-24-canopy
type: sprint-change-proposal
status: approved
created: '2026-08-24'
scope: spec-pyforge-unifying-strategy Canopy obligations (pyforge-doctor spoke)
---

# Sprint Change Proposal — 2026-08-24 (Canopy)

## Issue Summary

**Trigger:** Phase 5 of `spec-pyforge-unifying-strategy` (the Canopy). The Dream is approved;
steward owns the host build (Epics 18–30). Doctor is spoke #5 under the eight-station hub-and-spoke
model. Doctor's own chain (`spec-pyforge-doctor`, Epics 1–16) is largely shipped or in active
dispatch — CLI diagnostics, verdict sources, BMAD drift, deferred-work visibility.

**Category:** Strategic extension / five-tier symmetry reconciliation (spoke station).

**Problem statement:** Pre-audit Dream and architecture prose described doctor as a standalone
FastAPI microservice (`:8008`, `doctor_portal`, `services/` tier). The 2026-08-24 Grounding
audit is authoritative: the Canopy is the existing `src/platform/` host; MCP is an in-host ASGI
seam (`POST /stations/<name>/mcp`); portals mount under `/stations/<name>/` with the reusable-app
naming triple; no extra public ports; no `pyforge.*` imports under `src/platform/`. Without an
explicit course correction, reviewers could mint doctor Epics 17+ duplicating steward Epics 18–30,
or treat the pre-audit `:8008` / `services/` shape as still binding.

**Operator decision (bound):** proceed. Status **approved** 2026-08-24.

**What this proposal does:** records doctor's Canopy obligations, preserves Epics 1–16 as the
sole doctor implementation chain, and defers portal/MCP-dispatch/events/skill/persona tiers to
steward cross-station epics — without reopening shipped CLI semantics.

## Impact Analysis

### Epic impact — doctor (Epics 1–16)

- **Epics 1–16:** **Not reopened.** The station contract (`spec-pyforge-doctor` CAP-1..9,
  AD-1..AD-6, NFR-1..5) remains authoritative for CLI gather, prescribe, verdict sources, and
  ambient drift detection. Canopy tiers are **additive obligations fulfilled by steward**, not
  new doctor epics.
- **No Epics 17+ minted:** Last doctor epic is 16 (`spec-sibling-dreams-drift`). Steward
  Epics 18–30 are **not copied** into this project's backlog.

### Five-tier gap (doctor today)

| Tier | Shipped / in-flight | Canopy obligation | Steward epic |
|------|---------------------|-------------------|--------------|
| CLI | `doctor` console script (Epics 1–16) | Also reachable as `pyforge doctor …` (dispatch only) | 22 |
| Web portal | absent | `/stations/doctor/`; triple `django-doctor` / `django_doctor_<app>` / `doctor_<app>` | 19 |
| Service/MCP | in-process MCP **client** (AD-6) | `POST /stations/doctor/mcp` on host ASGI; official `mcp` SDK; dual-era | 21 |
| Domain skill | absent | SKF skill from `pyforge-doctor/`; `conda-forge-expert` is mason, not doctor | 29 |
| Agent persona | absent | BMAD persona consults doctor domain skill | 29 |

### Artifact conflicts

- **`docs/dreams/pyforge-unifying-strategy.md` (pre-audit prose):** `:8008`, `doctor_portal/`,
  `services/pyforge-doctor/` — **superseded** by Grounding §2026-08-24. Doctor does not grow a
  FastAPI `services/` process or bind a second public port.
- **`architecture/.../ARCHITECTURE-SPINE.md`:** AD-6 (MCP-first client for atlas Watch axes)
  remains valid for CLI/in-process paths. Host MCP **server** face is a steward mount concern
  (Epic 21), not a rewrite of AD-6's client semantics.
- **`epics.md`:** append `## Canopy obligations (2026-08-24)`; do not append Epics 17+.
- **`spec-pyforge-doctor/SPEC.md`:** unchanged — CAP-1..9 and non-goals (read-only, no new
  scanning engines) stand; Canopy web/agent tiers are out of v1 CLI scope by design.

### Out of scope (this station)

- Implementing portal, host MCP mount, unified CLI spine, events bus, SKF skill, or persona
  (steward Epics 18–30).
- Minting doctor stories that duplicate steward 19 / 21 / 22 / 24 / 29.
- Reopening Epics 1–16 CLI acceptance criteria.

## Recommended Approach

**Direct Adjustment (selected).** Record Canopy obligations in `epics.md` and
`deferred-work-ledger.md`. Keep Epics 1–16 as the doctor build surface. Bind missing tiers to
steward epics by reference. Supersede pre-audit standalone-service prose without code rollback.

**Effort: Minor** — planning-artifact updates only; no doctor epic/story additions.

**Rollback: not applicable.** No shipped doctor stories are invalidated.

**MVP review: not needed.** `spec-pyforge-doctor` scope is unchanged; Canopy tiers are steward-owned.

## Detailed Change Proposals

**`epics.md` — append Canopy obligations block (2026-08-24):**
```
NEW: ## Canopy obligations (2026-08-24) — doctor spoke obligations; Epics 1–16 unchanged;
     no Epics 17+; portal/MCP-dispatch/events/skill/persona deferred to steward Epics 18–30.
```

**`deferred-work-ledger.md` — append `DW-CANOPY-2026-08-24`:**
```
NEW: Ledger entry recording five-tier gaps, steward epic bindings, pre-audit prose superseded,
     Epics 1–16 not extended for Canopy tiers.
```

**Pre-audit service shape — superseded interpretation:**
```
OLD: doctor as standalone FastAPI on :8008 under services/pyforge-doctor/ with doctor_portal.

NEW: doctor domain logic stays in pyforge-doctor package; host exposes POST /stations/doctor/mcp
     (Epic 21); portal at /stations/doctor/ (Epic 19); no services/ tier; no extra public port;
     portal uses django-pyforge client only — no pyforge.* import under src/platform/.
```

**CLI naming — preserved with unified dispatch:**
```
OLD: console script `doctor` only.

NEW: `doctor` remains the station binary; `pyforge doctor …` dispatches without reimplementing
     station logic (Epic 22 / FR-13). pyforge-core copies no doctor gather/prescribe code.
```

**Events — conditional obligation:**
```
NEW: if doctor publishes cross-station notifications, they use pyforge.events on redis-broker
     (Epic 24, CloudEvents envelope). No ad-hoc pub/sub. Doctor's v1 CLI remains read-only;
     event publishing is forward work when a web/agent surface needs it.
```

**No changes proposed to:** Epic 1–16 story bodies, `spec-pyforge-doctor/SPEC.md` capabilities,
sprint-status for shipped doctor stories, or steward planning artifacts.

## Implementation Handoff

**Scope classification: Minor.**

**Routed to:** Steward implementation on Epics 18–30 for doctor's missing tiers; doctor
station continues Epics 13–16 (and any remaining backlog) under existing specs.

**Action items (approved 2026-08-24):**
1. ✅ This sprint-change-proposal (approved).
2. ✅ Append `## Canopy obligations (2026-08-24)` to `epics.md`.
3. ✅ Append `DW-CANOPY-2026-08-24` to `deferred-work-ledger.md`.
4. Continue doctor Epics 1–16 per existing decomposition — **no Epics 17+**.
5. When steward lands Epic 19/21/22/24/29, doctor package supplies domain MCP tools and HTTP
   contract; steward mounts portal and host MCP face.
6. Do not add `services/` FastAPI process, second chrome, or `pyforge.*` imports under
   `src/platform/` from doctor stories.

**Success criteria:** Doctor planning artifacts record Canopy obligations without duplicating
steward epics; Epics 1–16 remain the doctor contract; five-tier completeness for doctor is
trackable via steward Epic 29.3 once steward tiers land; pre-audit `:8008` / `services/` prose
is not cited as binding in doctor reviews.
