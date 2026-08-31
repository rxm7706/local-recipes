---
title: 'Derived context recomputes only on source change (Story 28.8, Epic 28)'
type: 'feature'
created: '2026-08-30'
status: 'in-review'
baseline_revision: '1e1eb736c70e4909d23f49454d0d947c04ea3f5f'
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
deferred:
  - summary: >-
      Scribe's `index refresh` grammar has no caller-declaration surface, so marshal's
      consumer binding degrades on every real invocation until scribe ships one.
    evidence: |-
      Scribe Story 6.2 shipped the GENERIC "declare sources -> derived artifact" engine
      (`extras/cocoindex_flow.py::DerivedArtifact` / `refresh_incremental`, with an
      `index_path` override "for programmatic callers"), and its own Design Notes say
      "marshal Story 28.8 registers its epic-context/continuity distills against the
      same grammar later". What it wired into the CLI is only its OWN two registrations:
      `scribe index refresh [--target PATH]` takes no caller manifest. This story is the
      CONSUMER side by its own Code Map ("consumer side only here"), and its Never bullet
      forbids a marshal-private cocoindex flow, so marshal cannot add the missing option
      itself. `adapters/scribe_cli.py` therefore renders the declared grammar plus a
      `--declare <manifest>` argument and reports a scribe that rejects it as an ordinary
      layer degradation (`MRS-CTX-002`, WARN) — the layer-off fallback is proven and
      today's compile-on-hunch behavior is byte-identical, so nothing is broken, but the
      incremental path cannot engage live until scribe exposes the option. The moment it
      does, marshal lights up with zero further change. The scribe-side work is a small
      addition to `cli.py::index_refresh` (read a manifest, build `DerivedArtifact`s with
      a no-op derive for freshness-only callers) and belongs to Scribe Epic 6.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/scribe_cli.py
    severity: high
  - summary: >-
      An enabled `derived-context` layer invokes the scribe CLI once per routing, with no
      journalled record of what it cost or whether it engaged.
    evidence: |-
      `marshal context refresh` is invoked by the bmad-build-auto skill during step-01
      routing, and its degradation reason is printed into that session's transcript only.
      CAP-7 (Story 28.4, savings telemetry) is the seam that puts per-layer engagement and
      savings into the run journal and `marshal status`; until it lands, an operator whose
      `derived-context` layer has been silently degrading for a week has no fleet-level
      signal — only per-session output nobody re-reads. CAP-10 (Story 28.7, index
      freshness as an advisory `marshal check` finding) is the other half.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/context.py
    severity: medium
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
- 2026-08-31: implemented. Recorded two `deferred:` entries — the load-bearing one is that scribe's shipped `index refresh` grammar has no caller-declaration surface, so the consumer binding is built against the declared grammar with the layer-off fallback proven (the Never bullet's own instruction), and lights up unchanged when scribe exposes it.

## Auto Run Result

**Summary:** Implemented the consumer side of CAP-5. `core/derived_context.py` (pure)
declares an epic's two derived artifacts and their planning sources — the source set is
`step-01-clarify-and-route.md`'s own path-B document vocabulary verbatim (`*prd*`,
`*architecture*`, `*ux*`, `*epic*`, `*brief*`), so a story spec landing no longer
invalidates an epic's distill, and a change to a document the distill actually reads does.
`adapters/scribe_cli.py` is the sole seam permitted to invoke the `scribe` CLI and turns
every failure shape into a named degradation rather than an exception. `cli/context.py`
adds `marshal context refresh --project <slug> --epic <N>`: layer off → `compile-on-hunch`,
nothing invoked and nothing written; layer on → one `fresh`/`stale` row per artifact;
layer on but degraded → `compile-on-hunch` plus a WARN `MRS-CTX-002`, never a blocked
iteration. `.claude/skills/bmad-build-auto/step-01-clarify-and-route.md` items 1.A.2 and
1.A.5 now consult that verdict and fall back to the previous mtime rule verbatim; the
epic-context distill's headings, 800–1500 token target, provenance comment, and location
are untouched, pinned by a meta test.

**Contract-level notes:**
- No `import cocoindex` and no `import pyforge.scribe` anywhere in `pyforge.marshal` —
  enforced package-wide by an AST meta test with synthetic-offender vacuity checks.
- The continuity distill's cache file (`epic-<N>-continuity.md`) is written ONLY while the
  layer is enabled; with the layer off the skill writes nothing at all, so AC 3's
  "today's behavior unchanged" holds byte-for-byte.
- `MRS-CTX-001` (UNEVALUABLE) / `MRS-CTX-002` (WARN) registered; 002 shares the
  never-blocking tier and reasoning of Story 28.2's `MRS-DISP-033` and Story 28.3's
  `MRS-PREFLIGHT-015`.
