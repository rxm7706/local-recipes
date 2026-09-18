---
title: '47.3: The recall-injection layer composes with the existing [context] pipeline'
type: 'feature' # feature | bugfix | refactor | chore
created: '2026-09-18'
status: 'ready-for-dev' # draft | ready-for-dev | in-progress | in-review | done | blocked
baseline_revision: ''
review_loop_iteration: 0 # incremented by step-04 before each review loopback
followup_review_recommended: false # set by step-04 on status: done; step-01 READS this — false HALTs, true allows one follow-up then forces false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-recall-in-the-loop/SPEC.md', '{project-root}/docs/dreams/marshal-token-economy.md']
deferred: [] # append-only machine-readable deferred review findings; each item carries summary/evidence and optional location/severity
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
- `pixi run -e pyforge-marshal pyforge-marshal-test -k policy or -k recall` -- expected: a fixture
  test asserts `[context.recall]`'s presence and default in a freshly rendered `policy.toml`, and
  that `enabled = false` suppresses Story 47.1's query without touching the other five layers

## Auto Run Result
