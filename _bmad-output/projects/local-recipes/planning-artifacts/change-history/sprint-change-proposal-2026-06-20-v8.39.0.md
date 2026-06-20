---
doc_type: sprint-change-proposal
project_name: local-recipes
date: 2026-06-20
trigger: 'drift-check + 2026-06-20 artifact audit'
from_pin: 'conda-forge-expert v8.11.1'
to_pin: 'conda-forge-expert v8.39.0'
scope: major
status: approved
mode: batch
artifacts_changed: ['planning-artifacts/PRD.md', 'planning-artifacts/epics.md']
gates_to_regenerate: ['planning-artifacts/validation-report-PRD.md', 'planning-artifacts/implementation-readiness-report.md']
---

# Sprint Change Proposal — PRD/epics structural re-sync v8.11.1 → v8.39.0

## Section 1 — Issue Summary

The 2026-06-20 artifact audit and the new `scripts/bmad_drift_check.py` detector found the
`local-recipes` BMAD planning set pinned to **conda-forge-expert v8.11.1** while the live factory is
**v8.39.0** — ~28 releases of drift. The living architecture/overview/index docs were reconciled
mechanically in the same session (commit `7410f8c4fc`), but **PRD.md and epics.md carry a
structural gap**: whole capability clusters that shipped after the pin have **no FRs, epics, or
stories**, so they cannot be reconciled by a number-swap.

Evidence (detector output): `pin-behind` on PRD.md + epics.md (v8.11.1 < v8.39.0);
`phase-list-stale` on PRD.md (atlas-phase list stops at N, omits O–S); plus internal count drift in
epics.md (frontmatter **195** vs Wave Summary **173** vs epic-body sum **201**) and the readiness
report's "12 XL vs 0 XL remaining" contradiction.

## Section 2 — Impact Analysis

- **PRD impact** — FR set is missing the cf_atlas PyPI-intelligence layer, the security-signals
  cluster, 7 MCP tools, the 9th pixi env, and the full gotcha range; several FRs cite stale counts
  (schema v25, 17 phases, 37 tools, 8 envs, G1-G6).
- **Epic impact** — no epic covers phases O/P/Q/R/S, the schema v20→v28 migration chain + new
  tables, the security-signals fetchers/overlays. Epic 10 says "35 Tools" (now 42). Wave 3/5 story
  counts are stale; three doc-level totals disagree.
- **Architecture impact** — none new: the architecture set was already reconciled to v8.39.0 this
  session.
- **Gate impact** — `validation-report-PRD.md` and `implementation-readiness-report.md` validated the
  v7.8/v8.11-era PRD; they must be **regenerated** (not patched) after this change.
- **Technical impact** — documentation only; no code change (the code already shipped — this catches
  the docs up to it).

## Section 3 — Recommended Approach

**Direct Adjustment + scoped replan.** Add **one new epic (Epic 14: cf_atlas PyPI-Intelligence +
Security-Signals Layer)** in Wave 3 and retrofit stories into existing epics, rather than rewriting
the plan. Rationale: the rebuild plan's shape is sound; the gap is additive (post-pin capabilities),
so it maps cleanly onto a new epic + targeted story inserts. A pure number-swap was rejected — it
would leave the new capabilities unrepresented in the work-breakdown.

- **Effort:** ~+1 epic, ~+25–35 stories (Epic 14 + retrofits). Doc-only.
- **Risk:** low — additive; existing epics unchanged in intent.
- **Timeline:** this is a planning-doc catch-up, not new implementation (the features already ship).

## Section 4 — Detailed Change Proposals

**PRD.md** (applied this session):
- Update FRs to current reality — F2.1 schema v28 (21 tables + 4 views), F2.2 22 phases (B→N +
  O/P/Q/R/S), F3.2 42 MCP tools, F1.7 G1–G45, FX.2 9 pixi envs; extend any phase-ID list through S.
- Add net-new FRs for: the PyPI-intelligence layer (phases O–S, `pypi_universe`/`pypi_intelligence`,
  `conda_forge_readiness` score + `recommended_template`); the security-signals overlays (CISA KEV,
  EPSS, CWE + `fetch-epss`/`fetch-cwe-catalog`); the 7 net-new MCP tools.
- Re-pin source_pin → v8.39.0; version bump to v1.6.0; dated changelog entry.
- Leave the §7 architectural-gaps "G1-G6" numbering untouched (distinct from Recipe-Authoring
  Gotchas); preserve the already-fixed §9 DW17 row.

**epics.md** (applied this session):
- Add **Epic 14** (Wave 3) covering schema v20→v28 + new tables, phases O/P/Q/R/S, and the
  security-signals cluster, authored at the granularity of E7/E8/E9.
- Retrofit: Epic 1 +gcloud env story; Epic 6 +G7–G45 gotcha-authoring + new reference/guide docs;
  Epic 10 +7 MCP-tool stories (and header 35→42 Tools); Epic 9 +new-CLI stories.
- Reconcile the three totals: `total_epics` 13→14, `total_stories` to the true epic-body sum, and
  the Wave Summary rows (Wave 3 40→actual incl. Epic 14; Wave 5 16→actual) so all three agree.
- Re-pin source_pin → v8.39.0; date 2026-06-20; version 1.0.0 → 1.1.0; sync-lineage note.

## Section 5 — Implementation Handoff

- **Scope classification: MAJOR** (new epic + work-breakdown change).
- **Routed to:** `bmad-create-epics-and-stories` / `bmad-create-story` to deepen Epic 14 + retrofit
  story acceptance-criteria to full per-story detail as they are picked up (this proposal authors
  them at epic/story-title granularity matching the rest of the doc).
- **Gates:** regenerate `validation-report-PRD.md` via `bmad-validate-prd` and
  `implementation-readiness-report.md` via `bmad-check-implementation-readiness` against the synced
  PRD/epics (resolves the "12 XL vs 0 XL" contradiction at the same time).
- **Index:** run `bmad-index-docs` if the doc inventory shifts.
- **Baseline:** after the docs settle, `pixi run -e local-recipes bmad-drift-check -- --write-baseline`
  to re-anchor; `bmad-drift-check` should then show PRD/epics no longer `pin-behind`.

## Success criteria

`pixi run -e local-recipes bmad-drift-check` reports **no** `pin-behind`/`phase-list-stale` on
PRD.md or epics.md, the three epics totals agree, and the new capabilities have FRs + an epic.
