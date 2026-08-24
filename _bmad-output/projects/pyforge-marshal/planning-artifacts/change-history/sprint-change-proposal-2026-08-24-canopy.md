---
doc_type: sprint-change-proposal
project_name: pyforge-marshal
date: 2026-08-24
via: bmad-correct-course
scope: moderate
status: approved
trigger: pyforge-unifying-strategy Phase 5 (operator-approved)
artifacts_modified:
  - planning-artifacts/specs/spec-factory-console/SPEC.md
  - planning-artifacts/index.md
  - planning-artifacts/epics.md
  - planning-artifacts/deferred-work-ledger.md
  - docs/dreams/factory-console.md
---

# Sprint Change Proposal — Canopy retires the static Guildhall console

## 1. Issue Summary

Lane 1 Wagtail (steward `spec-pyforge-unifying-strategy` **CAP-2**) supersedes the
statically-built Guildhall console governed by marshal `spec-factory-console`. Phase 5 of
`docs/dreams/pyforge-unifying-strategy.md` is operator-approved; planning retirement happens
now. Code under `docs/dashboard/` (generator, pixi tasks, `data.js`) **remains** until steward
Story **30.2** achieves parity — this pass does not delete implementation surfaces.
`docs/dashboard/kedro-viz/**` is atlas-owned publish output and is explicitly **out of scope**
for supersession.

## 2. Impact Analysis

| Artifact | Impact |
|---|---|
| `specs/spec-factory-console/SPEC.md` | `status: shipped` → `superseded`; `superseded_by` → steward CAP-2; dated retirement note in body |
| `index.md` | Spec table row marks factory-console superseded |
| `epics.md` | Appends `## Canopy obligations (2026-08-24)` — marshal station boundaries under Canopy; **no new epics** (last marshal epic stays 25) |
| `deferred-work-ledger.md` | Appends `DW-CANOPY-2026-08-24` at end |
| `docs/dreams/factory-console.md` | One Realization log line; corrects the binding-chain sentence that would otherwise lie |
| Steward epics 18–30 | **Not copied** into marshal — steward owns CAP-2, Epics 19/20/21/29/30 |
| `docs/dashboard/**` code | **Untouched** this pass (Story 30.2 deletion gate) |

## 3. Recommended Approach — Direct Adjustment (chosen)

Planning-only retirement of `spec-factory-console` with explicit handoff to steward's Canopy
chain. Marshal epics that touch the dashboard generator (Epic 16 path plumbing, Epic 23 velocity)
remain valid **generator** work until steward 30.2 removes the build path; they are **not** the
Lane 1 CMS front door.

## 4. Detailed Change Proposals (applied)

### `specs/spec-factory-console/SPEC.md`

**Old → new (frontmatter):**

```yaml
status: shipped
```

→

```yaml
status: superseded
superseded_by: _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md#cap-2--lane-1-is-cms-managed-and-it-is-the-only-front-door
```

**Old → new (body):** prepend dated supersession note (Pages front door; generator until 30.2;
Kedro-Viz excluded).

### `index.md`

**Old:** `spec-factory-console/` row — "the Guildhall console (+ companions…)"

**New:** same row, suffix **(superseded 2026-08-24 → steward CAP-2; generator until S-30.2)**

### `epics.md`

**Old:** file ended after Epic 25 / appendices.

**New:** append `## Canopy obligations (2026-08-24)` — five-tier marshal obligations, uniform
`/stations/marshal/` URL, no second chrome, no extra FastAPI port, supervisor ingest deferred to
steward Epic 21, Epic 16 explicitly not Lane 1 CMS.

### `deferred-work-ledger.md`

**Old:** ended at last `DW-FU-23-2-2` entry.

**New:** append `### DW-CANOPY-2026-08-24` ledger entry recording planning retirement + code
deletion gate.

### `docs/dreams/factory-console.md`

**Old:** blockquote claims `spec-factory-console` remains binding.

**New:** blockquote states planning superseded; generator/Kedro-Viz carve-outs. Realization log
gains **2026-08-24** one-liner.

## 5. Implementation Handoff

| Owner | Work |
|---|---|
| **Steward** | CAP-2, Epics 20 (Wagtail front door), 30 (console removal after parity), 19/29 (portals + five-tier) |
| **Steward** | Epic 21 (supervisor run state in PostgreSQL) — marshal bmad-loop ingest hooks **after** 21 lands |
| **Marshal** | Existing Epics 16/23 generator stories until 30.2; Canopy obligations section defines station URL/chrome/MCP boundaries — **no marshal Epic 26+** |
| **Atlas** | `docs/dashboard/kedro-viz/**` publish path unchanged |

**Success criteria:** `spec-factory-console` reads `superseded` with a valid `superseded_by`;
index and epics reflect retirement; ledger entry exists; no files deleted under `docs/dashboard/`
in this pass.
