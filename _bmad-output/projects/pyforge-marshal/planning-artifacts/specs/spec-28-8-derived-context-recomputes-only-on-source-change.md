---
title: 'Derived context recomputes only on source change (Story 28.8, Epic 28)'
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
  - This story's surface includes the bmad-build-auto skill's epic-context compile flow
    (`.claude/skills/bmad-build-auto/`), which is repo-level, not station-package-level —
    keep the skill's semantics identical and change only the freshness mechanism.
---

<intent-contract>

## Intent

**Problem:** The epic-context distill (800–1500-token target) is recompiled on a
cache-validity hunch inside bmad-build-auto: a stale cache silently misleads, an
over-eager recompile re-reads the 65k-token `epics.md` / 46k-token `prd.md` for nothing.

**Approach:** Make epic-context and continuity distills incrementally-maintained derived
artifacts: recompute exactly when their declared planning sources change, never otherwise.
The incremental engine is **Scribe's `compile_surface` cocoindex extra** (scribe Story 6.2;
unifying-strategy Grounding 2026-08-30: cocoindex is a `compile_surface` extra that writes
*through* `GraphStore`, not a GraphStore engine) — marshal consumes it via the scribe
grammar, never a marshal-private cocoindex flow. Marshal renders the layer flag
(Story 28.1); the extra owns freshness.

## Acceptance Criteria

- Given two consecutive iterations with unchanged planning sources, when the second routes
  its story, then zero recompute occurs (observable: no re-derivation, no full-document
  read).
- Given a planning-source edit, when the next iteration routes, then exactly one refresh
  occurs and the derived artifact reflects the edit.
- Given the layer declared off, when an iteration routes, then today's compile-on-hunch
  behavior is unchanged.
- Given the derived artifacts, when inspected, then BMAD skill semantics (what the distill
  contains, its token target, where it lives) are untouched — only the freshness mechanism
  changed.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-marshal/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-marshal` only — never `scripts/bmad-switch`. Ledger
key `28-8-derived-context-recomputes-only-on-source-change`.

**Block If:** A change would alter the epic-context content contract, compress the story
spec, or import cocoindex anywhere in `pyforge.marshal` (the engine lives behind Scribe's
`compile_surface` extra; marshal consumes by grammar only).

**Never:** A background daemon the supervisor doesn't own. Rewriting bmad-build-auto's
routing semantics. A marshal-private cocoindex flow — if scribe Story 6.2's extra is not
yet shipped when this dispatches, implement the consumer side against its declared grammar
with the layer-off fallback proven, and record the dependency in the story record.

</intent-contract>

## Code Map

- `.claude/skills/bmad-build-auto/compile-epic-context.md` + `step-01-clarify-and-route.md` (freshness consumers)
- Scribe `compile_surface` cocoindex extra (producer — scribe Story 6.2; consumer side only here, grammar per pyforge-scribe SKILL.md)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py` (layer flag from Story 28.1)

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated
(zero-recompute, exactly-one-refresh, off-means-unchanged). Land this spec in
`planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 28.8 and spec-marshal-token-economy CAP-5. cocoindex is the
incremental-derivation engine (keeps derived indexes fresh with minimal recomputation) —
use its flow model rather than hand-rolled hash checks, but only through the scribe extra:
the same extra also serves the foundry-cutover move-list refresh (unifying-strategy
stack.md § Estate leverage), so one binding serves both consumers. Read the pyforge-atlas
SKILL.md gotchas before touching anything Kedro-adjacent; this story does not enter atlas's
pipeline surface.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, including this story's own new/updated test coverage.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (no undeclared dependency surface).

## Spec Change Log

- 2026-08-30: drafted from epics.md Epic 28 for fleet-drain preflight (Dream/Spec chain: docs/dreams/marshal-token-economy.md → spec-marshal-token-economy)
- 2026-08-30: bound the incremental engine to Scribe's `compile_surface` cocoindex extra (scribe Story 6.2) per the unifying-strategy Grounding 2026-08-30 ruling — no marshal-private cocoindex flow; one binding shared with the cutover move-list consumer
