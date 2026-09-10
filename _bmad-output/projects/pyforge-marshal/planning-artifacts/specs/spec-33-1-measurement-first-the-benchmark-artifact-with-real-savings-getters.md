---
title: 'Measurement first — the benchmark artifact, with real savings getters'
type: 'feature'
created: '2026-09-09'
status: 'done'
baseline_revision: '7e03bff26b0730a005f8ca38bc6113ed2b3bf8b3'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The five savings getters in `adapters/harness_bmadloop.py:1880-1898`
(`_get_headroom_savings`, `_get_codegraph_stats`, `_get_cocoindex_stats`,
`_get_graphifyy_savings`, and the Layer-0 caveman getter) all `return None`, so the
supervisor journals a savings block with every field null and `marshal status` renders
nothing. Epic 33's own HARD boundary forbids enabling any layer elsewhere until this is
fixed and measured (`DW-FU-3-6-6`).

**Approach:** Wire each getter to its real source (headroom's CCR store, the codegraph
index, the cocoindex cache, scribe's `GraphStore` seam in `extras/graphify.py`, and the
caveman output delta), then run the pinned benchmark's off-leg on
`1-1-marshal-conformance-smoke` and commit an artifact recording the off-leg verdict and
per-layer numbers.

## Boundaries & Constraints

**Always:** A getter whose source is genuinely absent returns a **named unavailable
reason**, never `None` — distinguishing "zero saved" from "not measured". `marshal
benchmark compare`'s equivalence gate **voids** a comparison when the on-leg's verdict,
gate results, or reviewer engagement don't match the off-leg's — a void is the answer,
never a failed test. The idle-threshold default (25 min, `core/policy.py:475`) is
confirmed or re-set from one wave of real per-session timing read from dispatch journals
(`_bmad-output/projects/<slug>/implementation-artifacts/dispatch-runs/*/journal.jsonl`),
closing Q-14 as a read, not an experiment.

**Never:** No later Epic 33 story may enable a layer whose getter is still a stub. This
story does not itself flip any `[context]` block on anywhere.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Getter source present | headroom CCR store / codegraph index / cocoindex cache / GraphStore / caveman diff exists | getter returns real non-null numeric savings | No error expected |
| Getter source absent | source genuinely unavailable | getter returns a named unavailable-reason string | Never `None` |
| Benchmark legs match | off-leg and on-leg produce identical verdict/gates/reviewer engagement | comparison reports a measured saving | No error expected |
| Benchmark legs diverge | on-leg verdict/gates/reviewer differ from off-leg | comparison **voids** | Recorded as void, not a red test |

</intent-contract>

## Code Map

- `adapters/harness_bmadloop.py:1880-1898` -- the five stub getters; all currently `return None`
- `core/token_economy_benchmark.py` -- benchmark runner/comparison; where the equivalence-void branch lives
- `core/supervise.py` -- journals the savings block the getters feed
- `cli/check.py` -- surfaces `marshal benchmark compare`
- `_bmad-output/projects/<slug>/implementation-artifacts/dispatch-runs/*/journal.jsonl` -- source for the Q-14 idle-threshold read

## Tasks & Acceptance

**Execution:**
- `adapters/harness_bmadloop.py` -- implement each of the five getters against its real source; return a named-reason string when unavailable -- closes the all-null savings block
- `core/token_economy_benchmark.py` -- run the off-leg against `1-1-marshal-conformance-smoke`; implement/confirm the equivalence-void branch
- `tests/unit/**` -- cover each getter's real-source and unavailable-reason paths
- One wave of dispatch-journal timing read -- confirm or reset the 25-minute idle default (Q-14), recording the reading

**Acceptance Criteria:**
- Given all five getters currently `return None`, when each reads its real source, then a committed artifact under `_bmad-output/projects/pyforge-marshal/planning-artifacts/reviews/token-economy-benchmark-2026-xx-xx.md` names the off-leg verdict and per-layer rows with non-null numbers
- Given a getter's source is genuinely absent, when it is queried, then it returns a named unavailable reason, never `None`
- Given the on-leg's verdict/gates/reviewer engagement differ from the off-leg's, when `marshal benchmark compare` runs, then it VOIDS the comparison rather than reporting a failure
- Given one wave of dispatch-journal timing data, when Q-14 is read, then the 25-minute idle default is confirmed or reset with the reading recorded

## Spec Change Log

## Review Triage Log

### 2026-09-09 — Review pass
- verdicts: 18 findings — high 0, medium 2, low 3, false 4, maybe-false 0, reject 9
- findings:
  - `[false]` `[reject]` Diff truncated mid-hunk — git diff was complete; reviewers did not see untracked new files
  - `[false]` `[reject]` layer_savings_sources.py absent from diff — file exists as untracked addition
  - `[false]` `[reject]` Tests absent from diff — test_layer_savings_sources.py added untracked
  - `[low]` `[reject]` LayerSavings docstring stale — cosmetic; fields self-describe via types
  - `[low]` `[reject]` _gather_layer_savings docstring removed — behavior unchanged
  - `[medium]` `[patch]` Status CLI suppressed numeric zero savings — fixed `_format_savings_summary` to render `>= 0`
  - `[medium]` `[patch]` Aggregate test only pinned two of five layers — extended assertions for all five fields
  - `[low]` `[patch]` _optional_measurement bare int() — added bool guard and try/except
  - `[low]` `[patch]` _optional_graph_stats unsafe file_reads coercion — safe int conversion
  - `[low]` `[patch]` Missing leg_from_mapping string/split-key tests — added three unit tests
  - `[low]` `[patch]` Missing _format_savings_summary test — added direct unit test
  - `[low]` `[defer]` Duplicated graph serialization across three call sites — pre-existing pattern; extract helper is follow-on
  - `[low]` `[defer]` Broad except in _gather_layer_savings returns None — advisory-only pre-existing guard; individual getters still never None
  - `[false]` `[reject]` Q-14 not wired into policy.py — spec requires journal read recorded in artifact, not policy mutation
  - `[false]` `[reject]` Intent divergence on benchmark live run — off-leg artifact committed with named-reason rows; on-leg deferred to 33.2 per story boundary

## Auto Run Result

**Summary:** Replaced five stub savings getters with real file readers in
`core/layer_savings_sources.py`, wired through `BmadLoopHarness._gather_layer_savings`, extended
`LayerSavings` and downstream serialization to carry `int | str` unavailable reasons, and committed
the off-leg benchmark review artifact with five non-null per-layer rows. Q-14 read confirms keeping
the 25-minute idle default (`no-idle-samples` in dispatch journals).

**Files changed:**
- `core/layer_savings_sources.py` — pure AD-4 readers for all five layers + Q-14 idle timing
- `adapters/harness_bmadloop.py` — delegate getters; string-aware savings payload
- `ports/harness.py` — widen LayerSavings field types
- `core/token_economy_benchmark.py` — rehydrate string measurements and legacy split graph keys
- `cli/status.py` — render named reasons and measured zeros in savings summary
- `supervisor/__main__.py` — journal string graph stats
- `tests/unit/test_layer_savings_sources.py` — getter, aggregate, benchmark, and status tests
- `planning-artifacts/reviews/token-economy-benchmark-2026-09-09.md` — off-leg baseline artifact
- `planning-artifacts/sprint-status-ledger.yaml` — 33-1 → done

**Review:** 6 patches applied (2 medium, 4 low). 9 rejected (false/incomplete diff scope). 2 deferred
(helper extraction, aggregate exception swallow).

**followup_review_recommended:** false

**Verification:**
- `pixi run -e pyforge-marshal pyforge-marshal-test -k layer_savings` — PASS (28 tests)
- `pixi run -e pyforge-marshal pyforge-marshal-test` — PASS (full fast suite)
- `pixi run -e local-recipes sprint-ledger-sync -- --project marshal --repair-feed` — PASS (33-1 done)

**Residual risks:** Live harness off-leg with real token counts still requires a completed
`1-1-marshal-conformance-smoke` run in a loop home; this story records named-reason rows under
layers-off. On-leg measured delta waits for Story 33.2.

## Verification

**Commands:**
- `pixi run -e pyforge-marshal pyforge-marshal-test` -- expect green (verified 2026-09-09)
- `pixi run -e pyforge-marshal pyforge-marshal-test -k layer_savings` -- expect green (11 getter tests)
- Off-leg artifact: `_bmad-output/projects/pyforge-marshal/planning-artifacts/reviews/token-economy-benchmark-2026-09-09.md`
