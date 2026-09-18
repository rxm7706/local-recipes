---
title: '23.2: Every presentation has a local twin; design systems are mirrored as libraries'
type: 'feature'
created: '2026-09-16'
status: 'ready'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** agentic-sdlc has no registry section; two presentation projects have no twin; three design systems exist only in Design.

**Approach:** Each presentation gets a twin with prototype pulled byte-exact and a machine-owned registry section. Each design system is pulled byte-exact to presentations/_design-systems/<name>/. No deck glob matches the design-system home.

## Boundaries & Constraints

**Always:**
- Fourteen decks plus agentic-sdlc, six-quarter-roadmap, llm-knowledge-bases resolve through registry.read.

**Never:**
- Do not let currency/trio/Pages globs pick up _design-systems/.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| second pull | already-twinned design system | writes nothing | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-design-sync-loop CAP-2`.
Surface: presentations/agentic-sdlc/README.md; six-quarter-roadmap/**; llm-knowledge-bases/**; _design-systems/{modernist,broadsheet,nocturne}/**..
Ledger key: `23-2-every-presentation-has-a-local-twin-design-systems-are-mirrored-as-libraries`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-23-2-every-presentation-has-a-local-twin-design-systems-are-mirrored-as-libraries.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's policy `verify_commands` entry; MRS-GATE-010 binds the dispatch gate to this Success signal, and it is read from the primary tree's tracked spec, so it must be declared here before dispatch, not by the session).

**Manual checks:**
- `registry.read` resolves the fourteen decks plus `agentic-sdlc`, `six-quarter-roadmap` and `llm-knowledge-bases`; the three `presentations/_design-systems/<name>/` mirrors match Design byte-for-byte and a second pull writes nothing; no deck glob matches `_design-systems/`.
