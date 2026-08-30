---
title: 'The pinned wrapped-vs-unwrapped benchmark (Story 28.5, Epic 28)'
type: 'feature'
created: '2026-08-30'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
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

- new station-owned benchmark harness surface (tests/ or a `marshal`-adjacent tool under the station package)
- consumes Story 28.2's wrapper seam + Story 28.4's telemetry fields
- comparison artifact lands under `implementation-artifacts/` (Tier-3) with the summary promoted into the story record

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

## Spec Change Log

- 2026-08-30: drafted from epics.md Epic 28 for fleet-drain preflight (Dream/Spec chain: docs/dreams/marshal-token-economy.md → spec-marshal-token-economy)
