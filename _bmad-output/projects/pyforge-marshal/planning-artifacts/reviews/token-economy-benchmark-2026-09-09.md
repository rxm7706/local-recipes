# Token Economy Benchmark — Off-Leg Baseline (Story 33.1, 2026-09-09)

**Contract:** `spec-33-1-measurement-first-the-benchmark-artifact-with-real-savings-getters`;
Epic 33 measurement-first gate (`DW-FU-3-6-6`). Records the **layers-off** leg against the
pinned smoke story `1-1-marshal-conformance-smoke` after wiring CAP-7 savings getters to real
file sources. No `[context]` layer is enabled in this story — unavailable-reason strings are
expected and satisfy the acceptance criteria (distinguishing "zero saved" from "not measured").

## Off-leg verdict

| Field | Value |
|---|---|
| Pinned story | `1-1-marshal-conformance-smoke` |
| Layers mode | `off` (all five context layers disabled) |
| Task phase | `done` (synthetic harness read — no live smoke run in this worktree) |
| Reviewer engaged | yes (equivalence gate precondition) |
| Weighted tokens | not recorded (no completed harness run in this worktree) |

## Per-layer savings rows (off-leg)

Each getter now reads its real source under the loop home via
`core/layer_savings_sources.py` and returns either a measured integer (or `(hits, reads)` pair)
or a **named unavailable reason** — never `None`.

| Layer | CAP-7 field | Off-leg value | Source checked |
|---|---|---|---|
| output (caveman) | `output_compression_saved` | `caveman-skill-not-deployed` | `<home>/.claude/skills/caveman/SKILL.md` + `.marshal/wire/output_savings.json` |
| wire (headroom) | `wire_compression_saved` | `ccr-store-directory-missing` | `<home>/.marshal/wire/ccr_store.db` |
| structure-graph | `graph_hits_vs_file_reads` | `codegraph-index-missing` | sidecar `.claude/data/pyforge-marshal/layer-savings/codegraph.json` or `.codegraph/codegraph.db` |
| derived-context | `derived_context_cache_hits` | `cocoindex-index-missing` | `.claude/data/pyforge-scribe/cocoindex-index.json` |
| planning-graph | `planning_graph_tokens_saved` | `planning-graph-store-missing` | `.claude/data/pyforge-marshal/planning-graph/last-retrieval.json` or scribe `graph.json` |

All five rows are **non-null** (named reasons, not silent `None` stubs).

## Equivalence gate (on-leg deferred)

Story 33.1 does **not** enable layers. The on-leg comparison and measured token delta belong to
Story 33.2+. The equivalence-void branch in `core/token_economy_benchmark.py` is confirmed by
unit tests (`test_equivalence_gate_fails_on_verdict_mismatch`, `test_build_artifact_voids_comparison_when_equivalence_fails`).

## Q-14 idle threshold read

One wave of dispatch-journal timing was read from
`_bmad-output/projects/pyforge-marshal/implementation-artifacts/dispatch-runs/*/journal.jsonl`
(primary checkout, 263 run directories present):

| Reading | Value |
|---|---|
| Status | `no-idle-samples` (journals present; no `idle_seconds` payload entries yet) |
| Sessions with idle data | 0 |
| **Decision** | **Keep** `idle_threshold_minutes = 25` (`core/policy.py:475`) — no evidence to reset |

When dispatch journals begin recording `idle_seconds`, re-read before changing the default.

## Verification commands (this story)

```text
pixi run -e pyforge-marshal pyforge-marshal-test -k layer_savings   # PASS (25 tests)
pixi run -e pyforge-marshal pyforge-marshal-test                      # PASS (full fast suite)
```
