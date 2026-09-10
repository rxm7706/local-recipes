---
title: 'The layers are enabled on factory dispatch'
type: 'feature'
created: '2026-09-09'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
difficulty: medium
baseline_revision: '78fc2be72b980c64725efdb6764e1f74e57d7e32'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/integration-layers.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/reviews/token-economy-benchmark-2026-09-09.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-33-1-measurement-first-the-benchmark-artifact-with-real-savings-getters.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Epic 28 built the token-economy layer plumbing (CAP-1 composition site,
CAP-2 wire wrap, Genesis kit seeding), and Story 33.1 wired real savings getters plus an
off-leg benchmark — but no `[context]` block exists anywhere, so every layer stays off on
`factory dispatch` and the on-leg comparison against 33.1's artifact cannot run.

**Approach:** Declare all five layers enabled in `marshal-policy.toml`, prove
`resolve_context_layers` and `factory dispatch` resolve them from that single composition
site, extend the committed benchmark artifact with the on-leg (layers-on) record against
33.1's off-leg baseline, and add regression tests on the real tracked policy file.

## Boundaries & Constraints

**Always:** The on-leg is recorded against 33.1's artifact — not asserted without reference.
Any layer that degrades reports a named reason via `resolve_wire_wrap`'s existing degrade
path, never silent skip. Savings getters return 33.1's real shapes (measured int or named
unavailable reason, never `None`). Write under `_bmad-output/projects/pyforge-marshal/`
literally; `BMAD_ACTIVE_PROJECT=pyforge-marshal` only.

**Never:** Do not enable layers on `factory spin` (Story 33.3). Do not fold
`read_repo_policy_defaults()` into spin (33.3). Do not run a live fan-out wave (33.8). Do
not change verdict/gate/reviewer behavior — layers-on must be equivalence-safe with the
off-leg contract.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| All layers declared on | `[context]` block with five layers `enabled = true` in marshal-policy.toml | `resolve_context_layers` returns all five enabled; dispatch journals the same payload | No error expected |
| Wire store uncreatable | wire layer on but store dir not writable | `resolve_wire_wrap` returns `applied=False` with named reason; dispatch still launches unwrapped | Degrade path, never silent skip |
| Kit items for enabled layers | structure-graph and output layers on | `marshal seed kit` gates caveman-skill and codegraph-index items on those layers | Missing kit surfaces as seed check finding, not crash |
| Benchmark on-leg | layers-on dispatch context matches off-leg equivalence preconditions | benchmark artifact gains an on-leg section referencing 33.1 off-leg rows | void if equivalence fails |

</intent-contract>

## Code Map

- `_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml` — add `[context]` tables for all five layers (before `model_tier_map`; TOML table-scoping rule)
- `core/policy.py:1845-1877` — `resolve_context_layers` single composition site both engines call
- `cli/dispatch.py:310-332` — `_compose_policy` reads marshal-policy.toml; `:1416` resolves context payload
- `adapters/harness_bmadbuild.py:235` — `_resolve_wire_wrap` consumes wire layer from same payload
- `cli/seed.py:224-253` — `resolve_context_layers` at seed boundary; kit verb uses it
- `seed/verbs/kit.py` — provisions caveman-skill (output) and codegraph-index (structure-graph) when layers on
- `core/token_economy_benchmark.py` — on-leg artifact shaping; equivalence gate vs off-leg
- `planning-artifacts/reviews/token-economy-benchmark-2026-09-09.md` — 33.1 off-leg baseline to extend with on-leg
- `tests/unit/test_dispatch.py` — existing CAP-1/CAP-2 dispatch context tests; add real-policy regression
- `tests/unit/test_policy.py` — compose/render regression on tracked marshal-policy.toml

## Tasks & Acceptance

**Execution:**
- `planning-artifacts/marshal-policy.toml` — declare `[context."wire"|"output"|"structure-graph"|"derived-context"|"planning-graph"]` each with `enabled = true`; place before `model_tier_map` with Story 33.2 comment
- `tests/unit/test_policy.py` — regression: real marshal-policy.toml composes cleanly and `resolve_context_layers` enables all five layers
- `tests/unit/test_dispatch.py` — regression: `_compose_policy("pyforge-marshal")` on real repo resolves all five layers enabled in dispatch context payload
- `planning-artifacts/reviews/token-economy-benchmark-2026-09-09.md` — append on-leg section (layers on, references off-leg per-layer rows from 33.1)
- `planning-artifacts/sprint-status-ledger.yaml` — flip `33-2-the-layers-are-enabled-on-factory-dispatch` to `done` via sprint-ledger-sync

**Acceptance Criteria:**
- Given no `[context]` block existed and CAP-1's absent-block contract held, when the block is declared in marshal-policy.toml and a story dispatches, then all five layers resolve enabled on the factory dispatch path via `resolve_context_layers`
- Given Story 33.1's off-leg artifact, when the on-leg is recorded, then the benchmark review names layers mode `on`, references the off-leg rows, and documents per-layer on-leg state
- Given output and structure-graph layers are on, when `resolve_context_layers` is read at the seed boundary, then kit gating sees those layers enabled (caveman-skill and codegraph-index eligible)
- Given wire layer is on but its store is uncreatable, when dispatch launches, then `resolve_wire_wrap` degrades with a named reason rather than silently skipping

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test -k "context_layers or marshal_policy_declares"` — expected: pass (new regression tests)
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: full suite green
- `pixi run -e local-recipes sprint-ledger-sync -- --project pyforge-marshal --repair-feed` — expected: 33-2 status synced

**Manual checks:**
- `planning-artifacts/reviews/token-economy-benchmark-2026-09-09.md` contains both off-leg (33.1) and on-leg (33.2) sections

## Spec Change Log

## Review Triage Log

### 2026-09-09 — Review pass
- verdicts: 1 finding — high 0, medium 0, low 1, false 0, maybe-false 0
- findings:
  - `[low]` `[patch]` `test_run_dispatch_surfaces_the_context_payload` read tracked marshal-policy.toml after Story 33.2 enablement — monkeypatched layers-off composition to preserve Story 28.1 absent-block regression

## Auto Run Result

**Summary:** Enabled all five token-economy `[context]` layers in tracked
`marshal-policy.toml` for factory dispatch (Story 33.2 / CAP-1). Added regression tests on
the real policy file and dispatch composition site; extended the token-economy benchmark
artifact with the on-leg (layers-on) section referencing 33.1's off-leg baseline; fixed
Story 28.1 dispatch context test to pin layers-off explicitly.

**Files changed:**
- `planning-artifacts/marshal-policy.toml` — `[context]` tables for wire, output, structure-graph, derived-context, planning-graph
- `planning-artifacts/reviews/token-economy-benchmark-2026-09-09.md` — on-leg section vs 33.1 off-leg
- `planning-artifacts/specs/spec-33-2-the-layers-are-enabled-on-factory-dispatch.md` — story spec (this file)
- `planning-artifacts/sprint-status-ledger.yaml` — 33-2 → done
- `tests/unit/test_policy.py` — real-policy all-layers-enabled regression
- `tests/unit/test_dispatch.py` — real `_compose_policy` regression + Story 28.1 test fix

**Review:** 1 patch applied (low). 0 deferred.

**followup_review_recommended:** false

**Verification:**
- `pixi run -e pyforge-marshal pyforge-marshal-test` — PASS (7563 tests)
- `pixi run -e local-recipes sprint-ledger-sync -- --project marshal` — skipped (no Tier-3 feed in dispatch worktree); ledger updated directly

**Residual risks:** Measured token delta still requires `marshal seed kit` deployment plus a completed `1-1-marshal-conformance-smoke` harness run; per-layer rows remain named unavailable reasons until kit artifacts exist in a loop home.
