---
title: 'Planning-graph is proven live for dispatch — extend the win fleet-wide'
type: 'feature'
created: '2026-09-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/recall.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/planning_graph.py
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `[context].planning-graph` was only ever enabled for `pyforge-marshal` (Story 33.2, a canary) even though the underlying mechanism — skill-file wiring, the `marshal context retrieve` CLI, scribe's `recall` grammar — is fully built and, when tested live, genuinely works: grounded retrieval with a real citation. The other 7 stations get no benefit from a proven-working, zero-further-engineering layer.

**Approach:** Turn on `[context.planning-graph]` for the other 7 stations. Live verification during implementation surfaced a second, deeper bug: `scribe recall` has no notion of "project" in its scoring — a query naming a project slug tokenizes to generic words plus the slug (itself splitting into sub-tokens on `-`), so a wrong-project document with denser matching vocabulary can outscore the correct-project one. Fixed at the source (scribe's own `recall.py`) with a `scope` parameter that filters candidates to one project's citation tree before scoring, for both lexical and semantic modes.

## Boundaries & Constraints

**Always:** Verify each station's retrieval is genuinely grounded under its OWN citation tree, not just `grounded: true` (which the pre-fix bug also reported, incorrectly). Keep `scope=None` byte-identical to prior behavior — this is additive, not a breaking API change to `recall()`.

**Never:** Touch wire/output/structure-graph/derived-context policy for any station in this story — those are Stories 28.28-28.31's own scope. Guess project attribution for a `commit:`/code/transcript citation under a scope filter — exclude rather than guess.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| CROSS_PROJECT_LEAK (the live bug) | Query names project A, graph has a denser-vocabulary node for project B | Pre-fix: B's node returned as if grounded for A. Post-fix: only A's own nodes are candidates | N/A |
| GENUINE_MISS | Scoped query has no matching node in that project's own tree | `grounded: false`, epic-context-fallback | Clean fallback, not an error |
| UNSCOPED_CALL | `scope=None` (any caller not naming a project) | Identical to pre-fix behavior — global candidate pool | No behavior change |
| NON_PROJECT_CITATION | A `commit:`/code/transcript node would win lexically under a scope | Excluded — no reliable per-project attribution in the citation string | Falls through to the next candidate or a clean miss |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/recall.py` — `_citation_in_scope`/`_scope_prefix` helpers, `scope` parameter on `answer()` and `_answer_semantic()`
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py` — `recall_cmd`'s new `--scope` option
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/planning_graph.py` — `render_scribe_recall_argv`'s new `scope` parameter
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/scribe_cli.py` — `ScribeCli.recall`'s new `scope` parameter, threaded to argv
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/context.py` — `run_context_retrieve` passes `scope=slug`
- 7 station `marshal-policy.toml` files — `[context."planning-graph"] enabled = true`

## Tasks & Acceptance

**Execution:**
- `recall.py` — scope-filter candidates before scoring, both modes — fix
- `cli.py`/`planning_graph.py`/`scribe_cli.py`/`context.py` — thread `scope` end-to-end — fix
- 7 `marshal-policy.toml` files — enable the layer — feature
- `tests/unit/test_recall.py` (scribe) — 4 new tests reproducing the live incident and proving the fix, both modes
- `tests/unit/test_planning_graph.py` (marshal) — 3 new tests for `render_scribe_recall_argv`'s scope argv

**Acceptance Criteria:**
- Given a query naming project A with a denser-vocabulary project-B node in the graph, when `answer(..., scope="A")` runs, then only project A's own citations are candidates
- Given `scope=None`, when `answer()` runs, then behavior is unchanged from before this story
- Given all 8 stations post-rollout, when `marshal context retrieve --project <slug> --epic 1` runs, then every grounded result's citation is genuinely under that project's own `_bmad-output/projects/<slug>/` tree

## Spec Change Log

## Review Triage Log

## Auto Run Result

Status: done

**Summary:** Enabled `planning-graph` for all 7 non-marshal stations. Found and fixed a real cross-project content-leak bug in `scribe recall`'s scoring (no project-scoping existed at all) as part of verifying the rollout — the bug would have made every station's "grounded" retrieval potentially wrong, not just marshal's canary correct. Also captured the finding into this repo's own scribe-backed team memory (`.claude/memory/reference/`) and researched + recorded BMAD's own skill-customization mechanics (`.claude/docs/bmad-skill-customization-mechanics.md`) as a byproduct of confirming how Story 28.30's future skill-file wiring should be governed.

**Files changed:**
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/recall.py` — scope filtering
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py` — `--scope` CLI option
- `src/shared/packages/pyforge-scribe/tests/unit/test_recall.py` — 4 new tests
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/planning_graph.py` — `scope` param
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/scribe_cli.py` — `scope` param
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/context.py` — passes `scope=slug`
- `src/shared/packages/pyforge-marshal/tests/unit/test_planning_graph.py` — 3 new tests
- 7 station `marshal-policy.toml` files — layer enabled
- `spec-28-27-…md` — story contract
- `sprint-status-ledger.yaml` — 28-27 → done

**Review:** Implementation verified directly against the spec's own I/O matrix and live per-station retrieval checks; no separate review-loop pass for this fix-plus-rollout.

**Verification:** `pyforge-scribe-test` → 322 passed, 4 skipped. `pyforge-marshal-test` → 7697 passed. Live: all 7 rolled-out stations return `grounded: true` with a citation verified to start with their own `_bmad-output/projects/<slug>/` prefix.

**Residual risks:** None identified for the scope fix itself. A separate, unscoped lexical-ranking observation (a large, text-dense document like a CHANGELOG can outscore a shorter, more topical one in an UNSCOPED query) was noticed but is out of this story's scope — scoped callers (marshal's own use) are unaffected since `scope` narrows the candidate pool before that dynamic matters.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/unit/test_recall.py -q` — expected: all pass
- `pixi run --frozen -e pyforge-marshal python -m pytest src/shared/packages/pyforge-marshal/tests/unit/test_planning_graph.py -q` — expected: all pass
- `for p in pyforge-steward pyforge-warden pyforge-atlas pyforge-doctor pyforge-herald pyforge-mason pyforge-scribe; do pixi run -e pyforge-marshal marshal context retrieve --project "$p" --epic 1 --format json; done` — expected: every result `grounded: true` with a citation under that project's own tree
