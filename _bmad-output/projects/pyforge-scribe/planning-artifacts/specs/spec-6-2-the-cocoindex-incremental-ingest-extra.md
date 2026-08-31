---
title: 'The cocoindex incremental ingest extra (Story 6.2, Epic 6)'
type: 'feature'
created: '2026-08-30'
status: 'done'
baseline_revision: 'd32c20cc64f99e291de10f0099f78e2eeb061351'
review_loop_iteration: 0
followup_review_recommended: true
difficulty: heavy
context:
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-6-1-the-graphify-ingest-extra-and-its-move-list-verbs.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/stack.md
warnings:
  - Marshal Story 28.8 consumes this extra for epic-context/continuity freshness (by scribe
    grammar only) and the foundry cutover consumes it for move-list refresh when Mason 12.x
    or Atlas 20.x land. Declare the refresh grammar in the scribe SKILL.md.
---

<intent-contract>

## Intent

**Problem:** Story 6.1's derived artifacts (graph, move list) and marshal's derived
planning context go stale as `main` moves; recomputing them wholesale per change is exactly
the waste the token-economy spec measures. `cocoindex` (≥1.0.20, Apache-2.0, active in
pixi) is the estate's incremental-derivation engine and is scheduled "bind now" — with no
story building the binding.

**Approach:** Bind cocoindex as an **optional `compile_surface` extra** that maintains
declared derived artifacts incrementally: delta re-index on each commit / source change,
rewriting only the derived rows whose sources changed. Outputs write through the persist
port or land as derived gitignored artifacts. cocoindex is the freshness *engine* — never a
GraphStore engine, never a store of record (Grounding 2026-08-30). Extras off by default
(air-gap).

## Acceptance Criteria

- Given the extra off (default), when a compile runs, then behavior is unchanged — proven
  by an off-mode test.
- Given the extra on, when two consecutive runs see unchanged sources, then zero recompute
  occurs; when exactly one source changed, then exactly one refresh occurs touching only
  the affected derived rows.
- Given the outputs, when inspected, then they write through the persist port or land as
  derived gitignored artifacts — no cocoindex-owned store of record.
- Given the implementation, when inspected, then no `cocoindex.serve` MCP product exists,
  no `@coco.fn` lineage surface is introduced (OpenLineage rides CAP-8), and cocoindex is
  imported only inside the extra adapter.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-scribe/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-scribe` only — never `scripts/bmad-switch`. Ledger
key `6-2-the-cocoindex-incremental-ingest-extra`. AD-1/AD-2/AD-6 bind (extras off by
default; write boundary; append-only mutation path).

**Block If:** A change would mint a second store-of-record, a long-running daemon scribe
doesn't own, or alter the `GraphStore` protocol.

**Never:** `cocoindex.serve` as an MCP product. `@coco.fn` as the lineage religion. A
mem0 binding (out of this epic). Publishing freshness as a PR-gate verdict.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py` (compile_surface fan-in — extra hook point)
- cocoindex extra adapter (new, e.g. `pyforge/scribe/extras/cocoindex_flow.py`; optional dependency, active in pixi)
- Story 6.1's graphify extra artifacts (first incremental consumers: graph + move list)
- `.claude/skills/pyforge-scribe/active/pyforge-scribe/SKILL.md` (declare the refresh grammar)

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated
(off-mode unchanged, zero-recompute on unchanged sources, exactly-one-refresh on one edit,
no-store-of-record, adapter-only import). Land this spec in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 6.2. Use cocoindex's flow/dataflow model for change detection rather
than hand-rolled hash checks — that is the point of binding the engine. The declared derived
artifacts start with Story 6.1's (graph, move list); marshal Story 28.8 registers its
epic-context/continuity distills against the same grammar later — this story must not
special-case marshal, only expose the generic "declare sources → derived artifact" surface.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: pass, including this story's own new/updated test coverage.

## Spec Change Log

- 2026-08-30: drafted as Epic 6 preflight (unifying-strategy stack.md "bind now" rows; pairs with marshal Epic 28's token-economy consumers)

## Review Triage Log

### 2026-08-30 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 7 (high 1, medium 2, low 4)
- defer: 0
- reject: 11
- addressed_findings:
  - `[high]` `[patch]` `_source_signature()`'s directory walk (`cocoindex_flow.py`) had no noise-directory exclusion, unlike `move_list.py`/`compile.py`'s established `_rglob_excluding`/`_EXCLUDED_DIR_NAMES` convention — since the graphify-ingest artifact's default source is `src/shared/packages` (the exact tree this repo's own pytest runs populate with fresh `__pycache__/*.pyc` churn), this silently defeated AC2's "zero recompute on unchanged sources" promise in ordinary dev use. Fixed by excluding the same noise directories.
  - `[medium]` `[patch]` `scribe index refresh`'s cocoindex-on branch (`cli.py`) never caught `CocoindexUnavailableError` (only `GraphifyUnavailableError`), so a truthy `SCRIBE_COCOINDEX_EXTRA` with `cocoindex` not installed raised an unhandled traceback instead of the documented clean `exit 2`. Fixed by catching both; added a CLI-level regression test.
  - `[medium]` `[patch]` `_source_signature()`'s per-file `.stat()` call (`cocoindex_flow.py`) had no `OSError` guard, so a file deleted/made unreadable between the `rglob` listing and the `.stat()` call (a real race in this repo's shared-worktree workflows) crashed the whole refresh instead of degrading to a warning like the existing "path does not exist at scan-start" branch. Fixed by catching `OSError` around the stat and warning instead.
  - `[low]` `[patch]` `cocoindex_flow.py`'s `default_cocoindex_index_path` docstring cited `.gitignore:718` for the `.claude/data/` ignore line; the actual line is 721. Corrected.
  - `[low]` `[patch]` `_load_index` (`cocoindex_flow.py`) already guards against the `fingerprints` key being a non-dict, but not against the top-level JSON document itself being a non-dict (e.g. a corrupted/hand-edited index holding a bare list), which would raise `AttributeError` on `.get`. Fixed symmetrically with the existing check.
  - `[low]` `[patch]` `scribe index refresh`'s cocoindex-on mode reported only artifact names (`refreshed: move-list, graphify-ingest`), dropping the per-artifact counts the off-mode branch reports (`graphify-ingest (1 node(s))`). Fixed via CLI-local closures capturing each `derive()` call's count for the summary line — the generic `DerivedArtifact.derive: Callable[[], None]` / `RefreshResult` engine contract was deliberately left untouched (Design Notes: "must not special-case marshal, only expose the generic surface"; adding a return value there would fit only this story's two concrete consumers).
  - `[low]` `[patch]` SKILL.md's "Usage" section listed "marshal Story 28.8's freshness check" flatly among existing consumers of the `scribe index refresh` grammar, while the module docstring and another SKILL.md bullet correctly call it a future consumer (28.8 does not exist yet). Reworded for consistency.
  - `[reject]` (11 findings, not itemized — see review-layer output for detail): unbounded `cocoindex` pin (matches the existing unbounded `graphifyy` pin convention from Story 6.1, not a deviation this story introduced); redundant repo-wide `move_list_sources()` walk on the rarer actual-refresh path (bounded, stat-only cost, avoiding it needs extra plumbing for negligible benefit); partial-failure side effects not echoed to the user beyond the propagated exception + exit 2 (matches the documented "persist progress via `finally`, propagate the exception" contract and its own passing test); duplicated `_FakeFingerprint`/`_FakeCocoindexModule` test doubles across `test_cli.py`/`test_extras_cocoindex_flow.py` (mirrors the pre-existing `_FakeGraphifyModule` duplication pattern from Story 6.1); no CLI flag to override the fingerprint-index path (no AC requires it; the library-level `index_path` override already exists for programmatic callers); no duplicate-`DerivedArtifact`-name validation in the generic engine (unreachable today — this story's own two registrations use fixed, distinct names; Design Notes explicitly forbid special-casing a not-yet-built future consumer); intent-alignment auditor's "hook-point" divergence — the Code Map's boilerplate "compile.py — extra hook point" line (copy-pasted verbatim from sibling spec 6.1) is superseded by this spec's own Grounding text and by `stack.md`'s authoritative bind description ("`scribe index`: AST graph + incremental index"), which names the exact CLI surface (`scribe index`) the diff extended — hooking into `compile_graph()`'s reset-then-rebuild fan-in instead would have violated AD-1 (skip-if-unchanged inside a reset cycle silently deletes nodes), per `compile.py`'s own new docstring; intent-alignment auditor's "row vs. artifact granularity" divergence — the Approach's "derived rows" and Design Notes' "flow/dataflow model, not hand-rolled hash checks" are looser prose than AC2's own concrete Given/When/Then, which is satisfied exactly at the only granularity the spec's declared derived artifacts (graph, move list) actually have, using the real `cocoindex.memo_fingerprint` primitive (not a hand-rolled hash) over a necessarily bespoke source-signature tuple; intent-alignment auditor's "each commit" auto-trigger divergence — Design Notes scope this story to exposing the generic refresh surface only, not building a triggering mechanism, matching Story 6.1's own manually-invoked `index build`/`index move-list` precedent; AD-2 citation gap in new docstrings (substantively satisfied — writes stay under `.claude/data/pyforge-scribe/` or through the persist port — just not name-checked in prose alongside AD-1/AD-6); spec `status`/`review_loop_iteration` bump reflecting normal in-review workflow state, not a defect.

## Auto Run Result

**Summary:** Implemented Story 6.2 — the cocoindex `compile_surface` incremental-ingest extra. A new generic "declare sources → derived artifact" engine (`DerivedArtifact` + `refresh_incremental()`) fingerprints declared source files/dirs via `cocoindex.memo_fingerprint` and calls each artifact's `derive()` only on a fingerprint mismatch, persisting a `{name: fingerprint_hex}` JSON index under `.claude/data/pyforge-scribe/cocoindex-index.json` (derived, gitignored, never a store of record). Wired via a new `scribe index refresh` CLI verb registering Story 6.1's two derived artifacts (graphify-ingest, move-list); off by default (`SCRIBE_COCOINDEX_EXTRA` unset) it behaves exactly like `index build` + `index move-list`. Deliberately NOT hooked into `compile_graph()`'s automatic fan-in (documented in `compile.py`'s docstring): that function's reset-then-rebuild contract (AD-1) is structurally incompatible with a skip-if-unchanged step, and `stack.md`'s own Grounding text names `scribe index` — not `compile_graph()` — as the bind surface.

**Files changed:**
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/extras/cocoindex_flow.py` (new) — the `DerivedArtifact`/`RefreshResult`/`refresh_incremental()` generic incremental-derivation engine.
- `src/shared/packages/pyforge-scribe/tests/unit/test_extras_cocoindex_flow.py` (new) — unit coverage for the engine (env gating, unavailable-package path, skip/refresh isolation, missing/vanishing-source handling, corrupted-index handling, AC3/AC4 checks).
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py` — new `scribe index refresh` verb; `index_build`/`index_move_list` bodies factored into shared `_write_graph_index`/`_write_move_list` helpers.
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py` — docstring explaining why the cocoindex extra is not hooked into the automatic fan-in.
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/extras/move_list.py` — `move_list_sources()` extracted so the engine and the real scan share one file list.
- `src/shared/packages/pyforge-scribe/pyproject.toml` — new `cocoindex` optional extra (`cocoindex>=1.0.20`).
- `src/shared/packages/pyforge-scribe/tests/unit/test_cli.py`, `test_compile.py` — new/updated coverage for the CLI verb and for `compile_graph()`'s non-integration.
- `.claude/skills/pyforge-scribe/0.1.0/pyforge-scribe/SKILL.md` — declares the `scribe index refresh` grammar for future consumers (marshal Story 28.8) per the spec's warning.

**Review findings breakdown:** 7 patched (1 high, 2 medium, 4 low — see Review Triage Log above for detail and fixes applied), 0 deferred, 11 rejected (documented above with reasoning, including two intent-alignment-auditor-raised interpretation questions resolved in favor of the diff's reading via `stack.md`'s Grounding text).

**Follow-up review recommendation:** `true` (one patched finding was high severity — the `__pycache__` noise-directory exclusion gap — which independently triggers the recommendation regardless of the medium/low score).

**Verification performed:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — 296 passed (pre-patch), then 300 passed (post-patch, after the 7 fixes' new/updated tests).
- Matrix Test Audit: not applicable — the spec's intent-contract uses Given/When/Then ACs, not a formal I/O & Edge-Case Matrix.
- Manual/independent re-verification: confirmed each of the 7 patch fixes present in the actual source (grep-verified `_rglob_excluding` reuse, `OSError` guards, `isinstance(document, dict)` check) rather than trusting the subagent's report alone.

**Residual risks:**
- A pre-existing Story 6.1 defect was found (out of scope for this story): `extras/graphify.py`'s `graphify.extract(...)` call raises `TypeError: 'module' object is not callable` against the real installed `graphifyy` package (a namespace collision), reproducible via plain `ingest_repo()`. Never surfaces in this story's own verification since `graphifyy` is intentionally absent from the `pyforge-scribe` pixi test env. Worth a follow-up against Story 6.1's adapter.
- The sprint-status-ledger.yaml is a generated file (regenerate via `sprint-ledger-sync`); this run did not hand-edit it, matching Story 6.1's own spec file convention.
- This PR touches only non-`recipes/` paths — needs the `maintenance` label per repo convention. No `pixi.toml` change, so no `environment.yaml` regeneration is required.
