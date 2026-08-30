---
title: 'Planning-graph retrieval behind the Scribe seam (Story 28.9, Epic 28)'
type: 'feature'
created: '2026-08-30'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
difficulty: heavy
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/integration-layers.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings:
  - The seam is Scribe's CAP-18 port set (unifying-strategy Grounding 2026-08-30):
    `graph_store` (persist; CAP-18 plugins shipped as scribe Story 4.1), `compile_surface`
    (ingest; the graphify extra is scribe Story 6.1), `recall_ranker`. "Behind GraphStore"
    means ingest writes GraphNodes *through* the persist port. If the graphify extra is not
    yet shipped when this story dispatches, implement the marshal-consumer side against the
    declared grammar with the fallback proven, and record the dependency in the story
    record — do not build a marshal-internal graph to route around it.
---

<intent-contract>

## Intent

**Problem:** An epic story's routing needs ~1.5k tokens of planning context but the
documents it lives in are 65k (`epics.md`) and 46k (`prd.md`) tokens; when the epic-context
cache misses, the whole document gets loaded.

**Approach:** When the `[context]` planning-graph layer is on and Scribe's ports are
available — planning corpus ingested via the `compile_surface` graphify extra (scribe
Story 6.1) writing GraphNodes through the `graph_store` persist port — step-01 routing
retrieves the scoped fields a story binds to by graph query; when the seam is absent or the
layer off, the epic-context file path (Story 28.8) is the proven fallback. Marshal consumes
the graph through Scribe's grammar — `pyforge scribe …` / the seam's declared API — never by
importing graph internals.

## Acceptance Criteria

- Given the seam available and the layer on, when step-01 routes an epic story, then the
  iteration completes within the epic-context token target with zero full-document loads
  (no `epics.md`/`prd.md` wholesale read).
- Given the seam disabled, when the same story routes, then the epic-context-file fallback
  demonstrably serves — same routing outcome.
- Given the retrieval path, when inspected, then marshal consumes via the Scribe grammar
  only: no graphifyy import inside `pyforge.marshal`, no second graph built.
- Given a graph answer, when it is used, then the story contract artifacts the agent binds
  to (spec, ACs) are still read verbatim — retrieval scopes the *context*, never the
  *contract*.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-marshal/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-marshal` only — never `scripts/bmad-switch`. Ledger
key `28-9-planning-graph-retrieval-behind-the-scribe-seam`.

**Block If:** A change would build or persist a marshal-owned knowledge graph, import
`pyforge.scribe` internals, or substitute a graph summary for the verbatim story contract.

**Never:** Replacing Story 28.8's fallback. Touching Scribe's own station code beyond the
consumer side of the seam.

</intent-contract>

## Code Map

- `.claude/skills/bmad-build-auto/step-01-clarify-and-route.md` (retrieval consumer)
- Scribe CAP-18 ports (consumer side only; grammar per pyforge-scribe SKILL.md): `graph_store` persist (Story 4.1, shipped) + `compile_surface` graphify extra (Story 6.1, producer)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py` (layer flag)

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated
(bounded retrieval, fallback proof, grammar-only consumption, contract-verbatim guarantee).
Land this spec in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 28.9 and spec-marshal-token-economy CAP-6. Read
`.claude/skills/pyforge-scribe/active/pyforge-scribe/SKILL.md` before writing any
scribe-touching code (grammar: `pyforge scribe …`; recall never invents an uncited answer).
Ordered last in the epic deliberately: 28.1–28.8 are self-contained; this one has the
cross-station seam. The same graphify extra also produces the foundry-cutover move-list
reports (unifying-strategy stack.md § Estate leverage) — one binding, two consumers; do not
duplicate its ingest for planning artifacts.

## Spec Change Log

- 2026-08-30: drafted from epics.md Epic 28 for fleet-drain preflight (Dream/Spec chain: docs/dreams/marshal-token-economy.md → spec-marshal-token-economy)
- 2026-08-30: seam named precisely as Scribe's CAP-18 ports (`graph_store` persist + `compile_surface` graphify extra, scribe Stories 4.1/6.1) per the unifying-strategy Grounding 2026-08-30; noted the shared-with-cutover binding
