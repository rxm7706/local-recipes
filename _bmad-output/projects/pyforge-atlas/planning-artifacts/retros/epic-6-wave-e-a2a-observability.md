---
doc_type: retrospective
project: pyforge-atlas
epic: 6
wave: E
title: Wave E — A2A Integration, Lineage & Observability
stories: 2
date: 2026-07-25
basis: reconstructed from tracked evidence (run log, epics.md, PRs #90/#91)
---

# Epic 6 · Wave E — A2A Integration, Lineage & Observability

**Scope:** E1 A2A structured-payload surface, FR-11 (`210b3a3`, `01f8f82`, #90) ·
E2 OpenLineage + OpenTelemetry via the hook layer, FR-12 (`153a5ad`, #91).

## What worked

- **Review hardened the contract, not just the code.** On E1 the pass enforced
  `schema_version`, hardened the `AD-20` guard, and **closed a `model_construct`
  bypass** — a validation escape hatch that would have let unvalidated payloads
  into the inter-agent channel. That is precisely the class of defect worth an
  adversarial reviewer.
- **Observability through the hook layer (E2), not through node bodies.** Lineage
  and telemetry attach without touching pipeline logic — consistent with CAP-3
  (state is a dataset concern, not a node concern).
- **`schema_version` on the payload from day one**, so the channel can evolve.

## What did not

- **`model_construct` was reachable at all.** Pydantic's documented validation
  bypass sitting on the boundary of a structured channel is a foreseeable hazard;
  it should have been closed when the model was written, not when it was reviewed.
- **Lineage is emitted but never asserted.** Nothing tests that a run produces a
  well-formed OpenLineage event. Post-merge Gemini had to add a *fail-safe* emit
  path — the emitter could take down the thing it was observing.
- **Observability is unmeasured.** No test says "this run is traceable to the API
  call" (CAP-12), so the capability is asserted rather than demonstrated.

## Carry-forward

1. **Ban validation-bypass constructors at trust boundaries** as a standing rule,
   not a per-review catch.
2. **An observability emitter must be fail-safe by construction** — it may never
   break the run it observes. Assert it.
3. **Assert one lineage event end-to-end.** Emitting is not observing.
