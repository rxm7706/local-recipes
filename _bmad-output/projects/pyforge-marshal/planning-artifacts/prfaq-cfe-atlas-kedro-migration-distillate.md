---
title: "PRFAQ Distillate: cfe-atlas-kedro-migration"
type: llm-distillate
source: "prfaq-cfe-atlas-kedro-migration.md"
created: "2026-07-16"
purpose: "Token-efficient context for downstream PRD creation"
---

# PRFAQ Distillate — cf_atlas Kedro Migration (premise kill-test, 2026-07-16)

## Verdict
- CONDITIONAL PASS. Premise survives on ONE leg: **agent-maintainability** (small contract-guarded nodes are what graduated-autonomy/loop execution can safely extend; the 10k-LOC procedural monolith is not). PRD must lead with this.
- Disposition: PROCEED to Tier-2 intake with three carried notes (below).

## Rejected framings (do NOT let the PRD use these)
- "The migration delivers the new signals (FR-19/20/21)" — REJECTED: signals are riders, ~3–4 stories on the legacy path too (Phases U/V/W; fetcher precedent exists; Q7 documents the interim). Never the justification.
- "Fixes the 1800 s defect / opaque execution" — REJECTED as justification: acute defects are ~0.5-story bolt-ons on legacy. Migration justification is chronic, not acute.
- "DuckDB drastically reduces the 3–4 h cold start" (§ 4.8/AC-7) — OVERCLAIM: cold start is network-bound (Phase R ~15 min first pull; F/K/N API-bound). Real perf story: incremental re-materialization + query-time analytics + Phase-F parquet reads.
- "§ 3.2 maintainability bottleneck" as urgency — DOWNGRADED: chronic tax (per-phase checkpoint/TTL/backoff re-implementation; Phase-I invisibility class), not a fire; legacy shipped 23 phases + ~10 releases/2 months.

## Null alternative (fairly priced, for the record)
- Keep legacy + Phases U/V/W (signals) + per-sub-step timeouts + logging ≈ **5 stories, zero parity risk, zero new deps**. Right choice IFF intelligence ambitions freeze at 23 phases / 28 questions. § 12.1 + § 13.1 candidate backlogs say they don't.

## Carried intake notes (spec touches for the PRD/next refinement)
1. Re-scope AC-7 / § 4.8 performance claim (incremental re-materialization, not engine-swap cold-start magic).
2. Record the **severability ramp**: the migration bundles two products — orchestration replacement (risk: kedro-dagster bus-factor-1, Prefect acquisition, parity) and the agent read surface (value: BSL+Vizro+Vizro-AI). Ibis-over-SQLite makes D/G-wave value survivable if the orchestration track stalls. Fallback, not plan.
3. Reframe § 3.2 first bullet acute→chronic (compounding-cost avoidance + agent-maintainability).

## Kill scenarios + tripwires (feed PRD risk section)
- Dagster-under-Prefect deterioration breaks kedro-dagster (`<2.0` pin) → tripwire: Q2 Wave-C re-verify; ramp: Dagster Components / Prefect deployer.
- B4 parity economically unreachable → tripwire: attended parity gate; ramp: keep legacy, salvage D-wave via severability.
- Verify-first sequencing slips (gates never built) → tripwire: Wave-A exit = six verify tasks are story deliverables.

## Scope signals
- IN: everything in spec v5.4 (22 FRs, 32 stories, Wave H per FR-22).
- Opportunity cost named: ~32 stories displacing feedstock-refresh throughput; acceptable via unattended execution (§ 2.5) + severable waves + B4 abort ramp. PRD should state this in one sentence.
- Customers: operator (rxm7706), CFE authoring agents, BMAD agents. Non-commercial; "adoption" = agent + operator usage, sustainability = § 13 matrix reviews.

## Timing intelligence
- Favorable: ECMA-424/427 formalized (Dec 2025); duckdb-wasm at parity; CRA Sep-2026 makes exploited-vuln signal classes regulatory-relevant.
- Unfavorable-but-unwaitable: orchestrator-market churn (Prefect+Dagster 2026-07-13). Waiting defers value without reducing uncertainty; exit ramps are the mitigation.
