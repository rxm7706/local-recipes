---
title: "Dream — PyForge Atlas Intelligence Platform"
date: 2026-08-02
status: dreamt
owner: atlas
scope: "Intelligence layer, cf_atlas data pipeline, phase orchestration, schema evolution"
---

# PyForge Atlas — Intelligence Platform

## Vision

**Atlas** is the intelligence backbone of the PyForge factory — a Kedro/Dagster/DuckDB data pipeline that orchestrates discovery, analysis, and decision-support across the conda-forge ecosystem. It transforms raw package metadata into actionable intelligence: trending candidates, adoption signals, version velocity, security posture, and dependency completeness.

**The ask**: Build a deterministic, horizontally-scalable, air-gap-capable intelligence layer that makes every decision in the factory data-driven, observable, and auditable.

## Problem

- **Raw metadata is useless without context.** PyPI releases 500+ packages/day; conda-forge ingests them. Without structured discovery and ranking, operators drown in noise.
- **Decisions are scattered across tools.** Adoption heuristics live in one CLI, schema decisions in another, phase logic in a third. No single source of truth for "what we know about this ecosystem."
- **Phase logic is fragile.** 15 phases (B → N) orchestrate the pipeline. Each has rate limits, dependencies, and state management. One failure cascades; one wrong decision blocks the whole run.
- **Air-gap deployments are an afterthought.** Real enterprises can't phone home. Atlas must work offline: bundled schemas, cached feeds, deterministic reproducibility.

## Realization

**Atlas** delivers:

1. **Discovery Engine** — Trending-candidate classifier with 8 signals (GitHub trends, PyPI velocity, conda adoption, maintenance age, community size, license stance, platform coverage, ecosystem maturity). One query → ranked recommendations.

2. **Schema Evolution Layer** — 16 versions of the cf_atlas schema, each with backward-compatible views. Phase outputs declare their schema; validation happens on ingest. No silent schema mismatches.

3. **Phase Orchestrator** — Kedro/Dagster combo: Kedro for task graphs (deterministic, cached, reproducible), Dagster for scheduling and observability. Every phase produces a catalog entry; every output is versioned and validated.

4. **DuckDB Analytics** — Parquet-backed cold storage for billions of rows; DuckDB for OLAP queries in tests and dashboards. No PostgreSQL required; works offline.

5. **Determinism Contract** — Same inputs → byte-identical output, always. No timestamps in the logic path, no random walks, no "good enough" approximations. Operators trust the data.

## Success Criteria

- ✅ **Completeness**: Every phase in the original cf_atlas pipeline ported to Kedro nodes
- ✅ **Velocity**: Phase runs complete in <5 min (single-box) or <30 min (multi-worker)
- ✅ **Reliability**: 99.9% uptime for the discovery engine; 0 silent schema mismatches
- ✅ **Observability**: Every decision logged, every phase run recorded, every finding attributed
- ✅ **Air-gap**: Deployable to air-gapped environments with bundled schemas and no external API calls
- ✅ **Testability**: 15+ pipeline stages each with UT + IT + E2E coverage; determinism verified in CI

## Acceptance

Atlas is done when:
1. All 15 phases ported and passing locally
2. Schema v29 → v30 migration tested end-to-end
3. Discovery engine deployed to staging and ranking real packages
4. Dashboards consuming cf_atlas data live and accurate
5. Air-gap deployment tested in isolated network (no internet access)
