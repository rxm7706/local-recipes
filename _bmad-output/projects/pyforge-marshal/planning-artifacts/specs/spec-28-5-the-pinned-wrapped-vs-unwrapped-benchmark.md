---
title: 'The pinned wrapped-vs-unwrapped benchmark (Story 28.5, Epic 28)'
type: 'feature'
created: '2026-08-30'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
baseline_revision: 'pending-vcs'
difficulty: medium
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/integration-layers.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** Upstream savings claims (caveman ~65%, headroom 40–95%) are their benchmarks on
their workloads. Marshal's ceilings (50M/500M weighted) were sized for an uncompressed
world; recalibrating them on marketing numbers would be guessing twice.

**Approach:** A pinned, re-runnable benchmark: the same story run twice — token-economy
layers off, then on — emitting a per-layer before/after weighted-token comparison artifact.
The on-leg must land the same story (same verdict, same gate results, reviewer never
skipped), or the comparison is void.

## Acceptance Criteria

- Given the pinned benchmark story, when the harness runs both legs, then it emits a
  comparison artifact reporting before/after weighted tokens per layer.
- Given the on-leg, when it completes, then its verdict and gate results match the off-leg
  and the independent reviewer ran (equivalence gate, not just a savings number).
- Given a re-run, when inputs are unchanged, then the artifact is reproducibly derivable
  (pinned story, pinned policy, recorded environment) — not a one-off session log.
- Given the artifact, when ceilings are recalibrated, then the recalibration note cites it.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-marshal/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-marshal` only — never `scripts/bmad-switch`. Ledger
key `28-5-the-pinned-wrapped-vs-unwrapped-benchmark`.

**Block If:** A change would let a savings number ship without the equivalence gate, or
would auto-tighten ceilings from a single benchmark run.

**Never:** Trusting upstream benchmark numbers as the baseline. A second PR-gate verdict.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/token_economy_benchmark.py` — pure CAP-9 artifact shaping: `BenchmarkLegRecord`, `check_equivalence`, `build_layer_comparison`, `build_artifact`, `leg_from_mapping`, `digest_context_layers`; constants `PINNED_BENCHMARK_STORY_KEY`, `LEDGER_KEY`, `ARTIFACT_SCHEMA`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/benchmark.py` — `marshal benchmark compare`: materializes the artifact from two JSON leg records or harness run ids via `collect_leg_from_harness`; default output under `implementation-artifacts/token-economy-benchmark-<timestamp>.json`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/main.py` — wires `add_benchmark_subparser`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py` + `core/verdict.py` — `MRS-BENCH-001`..`004` registration
- `src/shared/packages/pyforge-marshal/tests/unit/test_token_economy_benchmark.py` — pure-module AC tests (artifact shape, equivalence gate, reproducibility)
- `src/shared/packages/pyforge-marshal/tests/unit/test_cli_benchmark.py` — CLI compare + harness leg collection
- consumes Story 28.2's wrapper seam indirectly (layers on/off via resolved `[context]`) + Story 28.4's `LayerSavings` / `UsageSnapshot` fields

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated
(artifact shape, equivalence gate, reproducibility). Land this spec in
`planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 28.5 and spec-marshal-token-economy CAP-9. The model to copy is
caveman's own counterfactual benchmark discipline (pinned benchmark, exact-answer checks) —
measure on OUR workload. Weighted-token accounting reuses the existing tally
(`cache_read_weight = 0.1`), never a second accounting scheme.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test -- tests/unit/test_token_economy_benchmark.py tests/unit/test_cli_benchmark.py` — expected: pass, including this story's own new/updated test coverage.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (no undeclared dependency surface).

**Operator workflow:**
- Run the pinned story twice (all `[context]` layers off, then on) through the normal harness.
- `pixi run -e pyforge-marshal marshal benchmark compare --project pyforge-marshal --off <off-run-or.json> --on <on-run-or.json>`
- Ceiling recalibration notes cite the emitted artifact path; void artifacts (equivalence gate failed) must not drive ceiling tightening.

## Spec Change Log

- 2026-08-30: drafted from epics.md Epic 28 for fleet-drain preflight (Dream/Spec chain: docs/dreams/marshal-token-economy.md → spec-marshal-token-economy)
- 2026-09-01: implemented CAP-9 benchmark harness (`core/token_economy_benchmark.py`, `marshal benchmark compare`, unit tests)

## Review Triage Log

### 2026-09-01 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- addressed_findings:
  - none

## Auto Run Result

Status: done

Summary: Added the station-owned pinned wrapped-vs-unwrapped benchmark surface (CAP-9): pure comparison/artifact module, `marshal benchmark compare` CLI, registered `MRS-BENCH-*` findings, and unit tests covering artifact shape, equivalence gate voiding, and JSON round-trip reproducibility.

Files changed:
- `core/token_economy_benchmark.py` — new pure benchmark artifact builder
- `cli/benchmark.py` — new `marshal benchmark compare` command
- `cli/main.py` — subparser wiring
- `core/findings.py`, `core/verdict.py` — MRS-BENCH registration
- `tests/unit/test_token_economy_benchmark.py`, `tests/unit/test_cli_benchmark.py` — new tests
- `tests/unit/test_findings.py` — registry parity

Review findings breakdown: 0 patch, 0 defer, 0 reject.

Follow-up review recommendation: false (0 patched findings).

Verification: `pyforge-marshal-test` / `pyforge-deps-test` not executed in this session (shell unavailable); run locally before merge.

Residual risks: Live two-leg orchestration (spinning both runs automatically) remains operator-driven — `compare` accepts recorded JSON legs or completed run ids. Per-layer weighted-token breakdown beyond total story weighted tokens still maps through Story 28.4 savings fields until layers expose finer-grained token attribution.
