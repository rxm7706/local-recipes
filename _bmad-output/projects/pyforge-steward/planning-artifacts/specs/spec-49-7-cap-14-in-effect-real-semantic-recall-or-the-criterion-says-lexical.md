---
title: 'CAP-14 in effect — real semantic recall, or the criterion says lexical'
type: 'feature'
created: '2026-09-11'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** CAP-14's "semantic recall" clause is, today, a 32-dim SHA-256 bag-of-concepts over a
hardcoded 7-entry synonym map, off by default (`recall.py:94` `mode="lexical"`; `cli.py:316-320` is
the opt-in `--semantic` flag) — not real embedding-based recall. CAP-14's *other* clause ("the same
graph operations pass against both drivers") is already satisfied and exercised in CI
(`conftest.py:119-138` parametrized over both drivers; `pyforge-station-tests.yml:215-238` runs a
pgvector service), and single-plugin selection is the documented design
(`graph_store_plugins.py:36-39`, AD-1) — not a shortfall. Only the semantic-recall half is in
question.

**Approach:** Either back "semantic" recall with a real embedding model over the plane's `vss`
index, with a test that fails under pure lexical overlap, or rewrite CAP-14's criterion honestly to
state that `lexical` is the graded default and `semantic` is documented as the SHA-256
bag-of-concepts approximation it actually is. Whichever branch is chosen, the story states which
mode (`lexical` or `semantic`) the criterion is graded against, and records that the Spec's
"dual-write" wording mis-described a correct dual-driver design rather than naming a gap.

## Boundaries & Constraints

**Always:**
- State explicitly, in the landed spec, which mode (`lexical` or `semantic`) CAP-14's criterion is
  graded against.
- Correct the Spec's "dual-write" wording — the dual-driver CI parametrization
  (`conftest.py:119-138`) is a correct design already exercised, not a gap.
- Leave the existing dual-driver CI parity coverage unchanged.

**Never:**
- Do not claim "semantic" recall is embedding-based if the bag-of-concepts approximation is kept —
  name it honestly either way.
- Do not silently widen the 7-entry synonym map as a substitute for the branch decision — that is
  neither branch.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| REAL_SEMANTIC branch | A real embedding model over the plane `vss` index | A test fails under pure lexical overlap, passes under real semantic similarity | N/A |
| CRITERION_REWRITE branch | Bag-of-concepts approximation kept | CAP-14's criterion names `lexical` as the graded default and describes the approximation honestly | N/A |
| Dual-driver parity (unaffected) | `conftest.py:119-138` parametrized CI | Continues passing against both graph-store drivers, unchanged | N/A |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/embeddings.py`
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_plugins.py:36-39` (AD-1
  single-plugin-selection design — not in scope to change)
- the plane `vss` index
- `recall.py:94` (`mode="lexical"` default), `cli.py:316-320` (`--semantic` opt-in flag)

## Tasks & Acceptance

**Execution:**
- `decision` — choose REAL_SEMANTIC (back recall with a real embedding model + failing-lexical
  test) or CRITERION_REWRITE (name `lexical` as the graded default, document the bag-of-concepts
  approximation honestly).
- `docs` — correct the Spec's "dual-write" wording for the already-correct dual-driver design.

**Acceptance Criteria:**
- Given "semantic" recall is a 32-dim SHA-256 bag-of-concepts over a hardcoded 7-entry synonym map,
  off by default, while CAP-14's dual-driver clause is already satisfied and exercised in CI, when
  this story runs, then either recall is backed by a real embedding model over the plane's `vss`
  index with a test that fails under lexical overlap, or the criterion is rewritten honestly.
- And in either branch, the story states which mode (`lexical` or `semantic`) the criterion is
  graded against, and records that the Spec's "dual-write" wording mis-described a correct design.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: full suite green (no
  steward-package code changes expected; this command proves nothing else regressed)

**Manual checks (if no CLI):**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: full scribe suite green,
  including whichever branch's new/updated test (the actual code change lives here, not in
  pyforge-steward)

## Spec Change Log

## Review Triage Log
