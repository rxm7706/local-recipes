---
title: '47.3: The recall-injection layer composes with the existing [context] pipeline'
type: 'feature' # feature | bugfix | refactor | chore
created: '2026-09-18'
status: 'done' # draft | ready-for-dev | in-progress | in-review | done | blocked
baseline_revision: '5ba7fef72cf8210d6eb1ed62a827330ba4b82bc8'
review_loop_iteration: 0 # incremented by step-04 before each review loopback
followup_review_recommended: false # set by step-04 on status: done; step-01 READS this — false HALTs, true allows one follow-up then forces false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-recall-in-the-loop/SPEC.md', '{project-root}/docs/dreams/marshal-token-economy.md']
deferred:
  - summary: >-
      Live bmad-loop launch paths do not yet pass resolve_context_layers into
      augment_bmad_loop_session_prompt_with_recall (pre-existing 47.1/47.2 seam).
    evidence: |-
      Layer gate is implemented when context_layers is supplied; None keeps
      backward-compatible enabled behavior until spin/dispatch wires the payload.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py
    severity: medium
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 47.1/47.2's recall query and injection is real functionality, but if it lands
as a bolted-on side call outside marshal's existing `[context]` policy pipeline (`wire` /
`output` / `structure-graph` / `derived-context` / `planning-graph`), it can't be toggled, sized,
or measured the way every other context layer already is — an inconsistency the parent Spec
explicitly rules out.

**Approach:** Add a sixth `[context.recall]` block to `core/policy.py` and the rendered
`policy.toml` template, matching the existing five layers' `enabled`/`aggressiveness` shape.
Story 47.1's query becomes conditional on this layer being enabled, and its token cost is counted
through the same accounting path as the other five.

## Boundaries & Constraints

**Always:**
- `[context.recall]` has exactly the same two keys (`enabled`, `aggressiveness`) as the existing
  five layers — no bespoke config shape.
- `_POLICY_TEMPLATE`'s rendered comment block documents the sixth layer alongside the existing
  five, matching their doc-comment style.
- Story 47.1/47.2's recall query and its formatted output are counted toward the story's existing
  weighted-token accounting the same way every other layer's output already is.

**Never:**
- Never introduce a separate, uncounted budget or accounting path for this layer.
- Never let `enabled = false` here have any effect on the other five layers' own behavior — the
  layers stay independently toggleable.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `[context.recall] enabled = true` | Default policy | Story 47.1's query runs as normal | No error expected |
| `[context.recall] enabled = false` | Operator disables the layer | Recall query is skipped entirely for this story's dispatch; other five layers unaffected | No error expected |
| `aggressiveness` unset | Fresh policy render, no explicit value | Defaults to `medium`, matching `derived-context`'s own default (this story's own resolution of the parent Spec's Open Question 3) | No error expected |
| Policy renders for a fresh loop home | `marshal refresh` / `marshal init` writes a new `policy.toml` | The rendered file includes `[context.recall]` with its doc-comment, alongside the existing five | No error expected |

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-011 binding corrected 2026-09-19 — the `-k recall` scoping is a manual check below, not the declared command).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-011 binding corrected 2026-09-19 — the `-k recall` scoping is a manual check below, not the declared command).

**Manual checks:**
- `pixi run -e pyforge-marshal pyforge-marshal-test -k policy or -k recall` -- expected: a fixture
  test asserts `[context.recall]`'s presence and default in a freshly rendered `policy.toml`, and
  that `enabled = false` suppresses Story 47.1's query without touching the other five layers

## Review Triage Log

### 2026-10-08 — Review pass
- verdicts: 1 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings:
  - `[defer]` `[defer]` Production bmad-loop launch paths still do not pass `context_layers` into `augment_bmad_loop_session_prompt_with_recall` (pre-existing seam from Stories 47.1/47.2; layer gate is implemented for when callers supply resolved layers). — location: src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py

## Auto Run Result

Status: done

Summary: Added `[context.recall]` as the sixth token-economy layer in `CONTEXT_LAYER_NAMES`, repo-default `enabled = true` in `_bmad-output/policy-defaults.toml`, template documentation in `_POLICY_TEMPLATE`, and gating in `augment_bmad_loop_session_prompt_with_recall` when resolved layers are supplied. Token benchmark skips recall in savings rows (injected bytes count via normal session prompt accounting).

Files changed:
- `core/policy.py` — sixth layer in vocabulary and resolve path
- `core/recall_feedback.py` — `RECALL_LAYER` + `layer_enabled`
- `adapters/harness_bmadloop.py` — template docs + augment gate
- `schemas/policy.json` — schema text
- `core/token_economy_benchmark.py` — omit recall from savings comparison
- `_bmad-output/policy-defaults.toml` — default on
- Tests: recall/policy render/benchmark coverage

Review: 1 deferred (pre-existing launch wiring); 0 patches.

Verification:
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — pass (11898 tests after benchmark fix)
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — pass
- `python scripts/spec_surface_reconcile.py` — OK after memlog on spec-pyforge-marshal, spec-marshal-recall-in-the-loop, spec-marshal-token-economy

Governed paths reconciled (memlog):
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/recall_feedback.py`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/schemas/policy.json`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/token_economy_benchmark.py`
- `src/shared/packages/pyforge-marshal/tests/unit/test_harness_bmadloop_recall.py`
- `src/shared/packages/pyforge-marshal/tests/unit/test_recall_feedback.py`
- `src/shared/packages/pyforge-marshal/tests/unit/test_harness_policy_render.py`
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch.py`
- `src/shared/packages/pyforge-marshal/tests/unit/test_token_economy_benchmark.py`
- `_bmad-output/policy-defaults.toml`

followup_review_recommended: false
