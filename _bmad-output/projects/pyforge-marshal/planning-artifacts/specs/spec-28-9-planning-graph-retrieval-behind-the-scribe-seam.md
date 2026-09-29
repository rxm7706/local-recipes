---
title: 'Planning-graph retrieval behind the Scribe seam (Story 28.9, Epic 28)'
type: 'feature'
created: '2026-08-30'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
difficulty: heavy
baseline_revision: 'dispatch-pyforge-marshal-28.9-worktree'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/integration-layers.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-6-3-the-graph-node-staleness-flag.md
warnings:
  - "The seam is Scribe's CAP-18 port set (unifying-strategy Grounding 2026-08-30): `graph_store` (persist; CAP-18 plugins shipped as scribe Story 4.1), `compile_surface` (ingest; the graphify extra is scribe Story 6.1), `recall_ranker`. \"Behind GraphStore\" means ingest writes GraphNodes *through* the persist port. If the graphify extra is not yet shipped when this story dispatches, implement the marshal-consumer side against the declared grammar with the fallback proven, and record the dependency in the story record — do not build a marshal-internal graph to route around it."
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
- Given a graph answer whose backing node is flagged `stale` (Scribe Story 6.3's
  compile-time check — the node's source moved with no declared `supersedes:`), when the
  answer is used, then step-01 falls back to the epic-context file path (Story 28.8) instead
  of serving the stale node silently.

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

- `.claude/skills/bmad-build-auto/step-01-clarify-and-route.md` (retrieval consumer; item 1a)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/planning_graph.py` (pure retrieval logic)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/scribe_cli.py` (`recall` grammar)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/context.py` (`marshal context retrieve`)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py` (layer flag)
- Scribe CAP-18 ports (consumer side only; grammar per pyforge-scribe SKILL.md): `graph_store` persist (Story 4.1, shipped) + `compile_surface` graphify extra (Story 6.1, producer)

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

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, including this story's own new/updated test coverage.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (no undeclared dependency surface).

## Spec Change Log

- 2026-08-30: drafted from epics.md Epic 28 for fleet-drain preflight (Dream/Spec chain: docs/dreams/marshal-token-economy.md → spec-marshal-token-economy)
- 2026-08-30: seam named precisely as Scribe's CAP-18 ports (`graph_store` persist + `compile_surface` graphify extra, scribe Stories 4.1/6.1) per the unifying-strategy Grounding 2026-08-30; noted the shared-with-cutover binding
- 2026-08-31: gained a fifth AC (`spec-marshal-token-economy` CAP-13, minted the same day from
  a Mem0 OSS comparison against Scribe Story 2.3's author-declared-only supersession) — a
  graph answer whose backing node is flagged stale falls back to Story 28.8's file path
  rather than being served silently. The staleness check itself is Scribe Story 6.3's own
  compile-step work (this story's Boundaries already forbid touching Scribe's station code
  beyond the consumer side); this story only gains the consumer-side fallback behavior.
- 2026-09-01: implemented marshal consumer — `planning_graph` pure module, `scribe recall`
  adapter, `marshal context retrieve`, step-01 item 1a, `MRS-PLAN-001` degradation code,
  meta guards for graphify import ban and skill contract.
- 2026-09-01: test fixes — `[context.planning-graph]` TOML fixture syntax aligned with Story
  28.8; `MRS-PLAN-001` registered in `test_findings.py` membership gate.

## Review Triage Log

### 2026-09-01 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 2: (high 0, medium 2, low 0)
- defer: 0
- reject: 0
- addressed_findings:
  - `[medium]` `[patch]` `_declare_layer` used invalid quoted TOML key — fixed to `[context.planning-graph]` so layer-on tests exercise recall.
  - `[medium]` `[patch]` `MRS-PLAN-001` missing from `test_registered_codes_contains_the_real_codes` expected set.

## Auto Run Result

Status: done

Summary: Planning-graph retrieval binds through `scribe recall` with Story 28.8 epic-context
fallback on layer-off, grammar degradation (`MRS-PLAN-001`), or ungrounded recall (including
stale-only hits excluded by scribe Story 6.3). Step-01 item 1a calls `marshal context retrieve`.

Files changed:
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/planning_graph.py` — pure retrieval logic, mode resolution, token savings estimate
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/scribe_cli.py` — `ScribeCli.recall` grammar binding
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/context.py` — `marshal context retrieve` CLI
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py` — `MRS-PLAN-001` registration
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py` — `planning-graph` layer documentation
- `.claude/skills/bmad-build-auto/step-01-clarify-and-route.md` — item 1a retrieval consumer
- `tests/unit/test_planning_graph.py`, `test_cli_context_retrieve.py`, `tests/meta/test_planning_graph_skill_contract.py`, `test_no_engine_or_scribe_internals_import.py` — AC coverage
- `tests/unit/test_findings.py` — registry membership for `MRS-PLAN-001`

Review findings breakdown: 2 patches applied (TOML fixture, findings registry); 0 deferred; 0 rejected.

Follow-up review recommendation: true (patched: high 0, medium 2, low 0; score 3×2+0=6 ≥ 5).

Verification performed:
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — **7183 passed**, 12 deselected
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — **118 passed**, 1 skipped

Residual risks: Graph mode requires scribe's compile_surface extra (Story 6.1) to have ingested the planning corpus; until then, degradation to Story 28.8's epic-context path is the designed behavior.
