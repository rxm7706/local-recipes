---
title: 'Scribe exposes caller-declared derived-context refresh, closing the CAP-5/CAP-6 gap'
type: 'fix'
created: '2026-09-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/scribe_cli.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/derived_context.py
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Marshal's `derived-context` layer (Story 28.8) is fully built and already invoked by every dispatch/spin session (`marshal context refresh`), but degrades every single time: scribe's `index refresh` only ever fingerprinted its own two hardcoded artifacts (graphify-ingest, move-list) and had no `--declare <manifest>` option for a caller to register its own artifacts against the same incremental engine. Live-verified 2026-09-10: `marshal context refresh --project pyforge-marshal --epic 20` reported `MRS-CTX-002`, `scribe index refresh --declare ... exited 2`; `scribe index refresh --help` confirmed no `--declare` option existed at all.

**Approach:** Add `--declare <manifest>` to `scribe index refresh` (`cli.py::index_refresh` / new `_index_refresh_declared`): parse marshal's own manifest JSON (`{"artifacts": [{"name", "sources", "output"}, ...]}`), register each as a `DerivedArtifact` with a no-op `derive()` (scribe fingerprints; it never authors a caller's content — that stays the calling agent's own job), and run `refresh_incremental()` against a caller-namespaced index file (`declared-artifacts-index.json`, via the existing `_index_artifact_path` convention) so it never shares state with scribe's own graph/move-list index. An explicit `--declare` invocation bypasses `SCRIBE_COCOINDEX_EXTRA` entirely — the explicit call is its own opt-in, matching `cocoindex_extra_enabled()`'s own documented contract.

A second, packaging-level gap surfaced during live verification: fixing the CLI alone still degraded, this time with `CocoindexUnavailableError` — the `pyforge-scribe` pixi env (deliberately lean, Story 1.1) never carried the `cocoindex` conda package at all, even though `local-recipes` did for unrelated reasons. Since `ScribeCli.resolve_binary` prefers the `pyforge-scribe` env's own binary before ever falling back to `local-recipes`, the fallback env's cocoindex was unreachable in practice. Closed by adding `cocoindex = ">=1.0.20"` to `[feature.pyforge-scribe.dependencies]` in `pixi.toml`, matching the `[cocoindex]` extra's own declared floor in `pyforge-scribe`'s `pyproject.toml`.

## Boundaries & Constraints

**Always:** Keep `scope=None`/no-`--declare` byte-identical to prior behavior — additive only. A declared artifact's `derive()` stays a no-op; scribe answers "did the sources change", never regenerates content. Use a caller-namespaced index file, never `default_cocoindex_index_path`.

**Never:** Have scribe author or regenerate a caller's derived content. Let a malformed manifest crash uncaught — exit 2 with a clear message. Touch the wire/output/structure-graph/planning-graph layers in this story — Stories 28.27/28.29/28.30/28.31's own scope.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| FIRST_RUN | `--declare <manifest>`, no prior index | Every declared artifact reports `refreshed` | N/A |
| UNCHANGED_SOURCES | Second run, same manifest, unchanged sources | Every artifact reports `skipped (unchanged)` | N/A |
| ONE_SOURCE_CHANGED | One declared artifact's source file edited | Only that artifact reports `refreshed` | N/A |
| NAMESPACE_ISOLATION | `--declare` run alongside scribe's own `index refresh` | `declared-artifacts-index.json` and `cocoindex-index.json` never share state | N/A |
| MALFORMED_MANIFEST | Missing file, invalid JSON, no `artifacts` list, or a malformed entry | Exit 2 with a message naming the manifest path and the defect | Never an unhandled traceback |
| COCOINDEX_UNAVAILABLE | `cocoindex` not importable | Exit 2, `CocoindexUnavailableError` text | Same shape as the existing built-in path |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py` — `--declare` option on `index refresh`, `_index_refresh_declared`, `_declared_artifacts_index_path`
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/extras/cocoindex_flow.py` — reused unchanged (`DerivedArtifact`, `refresh_incremental`)
- `pixi.toml` — `cocoindex` added to `[feature.pyforge-scribe.dependencies]`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/scribe_cli.py` / `core/derived_context.py` / `cli/context.py` — unchanged; the consumer side already matched this contract (Story 28.8)

## Tasks & Acceptance

**Execution:**
- `cli.py` — `--declare` option + `_index_refresh_declared` — fix
- `pixi.toml` — `cocoindex` dependency for the `pyforge-scribe` feature — fix
- `tests/unit/test_cli.py` (scribe) — 9 new tests covering the full matrix above

**Acceptance Criteria:**
- Given a manifest JSON, when `scribe index refresh --declare <manifest-path>` runs, then it fingerprints each declared artifact's sources via `refresh_incremental()` and prints the same `refreshed: ...; skipped (unchanged): ...` report line `core/derived_context.py::parse_refresh_report` already parses
- Given a `derive()` no-op, when an artifact's sources are unchanged, then it always reports `skipped`, never `failed` from a derive-side exception
- Given an unparseable or missing manifest, when `--declare` runs, then it exits non-zero with a clear message
- Given `marshal context refresh --project pyforge-marshal --epic 20 --format json` (the exact live-verification command from this story's own Note), when run after both fixes, then it returns `"mode": "incremental"` with no `MRS-CTX-*` finding

## Spec Change Log

## Review Triage Log

## Auto Run Result

Status: done

**Summary:** Closed the CAP-5 gap end-to-end. `scribe index refresh --declare` now exists and works; a second, previously-hidden packaging gap (`cocoindex` absent from the lean `pyforge-scribe` pixi env) was found and fixed in the same pass — without it, the CLI fix alone still degraded with `CocoindexUnavailableError`. Live-verified against the exact command this story's own Note names: `mode: incremental`, zero findings, `verdict: clean`, and the second run correctly reports both artifacts `fresh`.

**Files changed:**
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py` — `--declare` option, `_index_refresh_declared`, `_declared_artifacts_index_path`
- `src/shared/packages/pyforge-scribe/tests/unit/test_cli.py` — 9 new tests
- `pixi.toml` — `cocoindex` added to `[feature.pyforge-scribe.dependencies]`
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml` — 28-28 → done

**Review:** Implementation verified directly against the spec's own I/O matrix plus a real live end-to-end `marshal context refresh` call; no separate review-loop pass for this fix.

**Verification:** `pyforge-scribe-test` → 331 passed, 4 skipped. `pyforge-marshal-test` → 7697 passed (unchanged — marshal's own consumer code was untouched). `pixi install -e pyforge-scribe` solved cleanly with the new dependency. Live: `marshal context refresh --project pyforge-marshal --epic 20 --format json` → `mode: incremental`, `findings: []`, `verdict: clean`; a second run reports both artifacts `fresh`.

**Residual risks:** The other 7 stations have `[context."derived-context"]` still declared off in their own `marshal-policy.toml` (Story 28.27 rolled out `planning-graph` fleet-wide but deliberately left `derived-context` alone — that fleet-wide rollout, now that this gap is closed, is a natural follow-on but out of this story's own scope). `pixi.lock` regenerated by `pixi install -e pyforge-scribe`; not independently re-verified on every platform (win-64/osx-arm64-min) beyond confirming the solve completed without error on this machine's linux-64 lock update.

## Verification

**Commands:**
- `pixi run -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/unit/test_cli.py -k declare -q` — expected: 9 passed
- `pixi run -e pyforge-scribe pyforge-scribe-test` — expected: all pass
- `pixi run -e pyforge-marshal marshal context refresh --project pyforge-marshal --epic 20 --format json` — expected: `mode: incremental`, `verdict: clean`
