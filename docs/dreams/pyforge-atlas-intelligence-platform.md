---
title: "Dream — PyForge Atlas Intelligence Platform"
date: 2026-08-02
status: archived
archived-reason: duplicate
owner: atlas
scope: "Intelligence layer, cf_atlas data pipeline, phase orchestration, schema evolution"
---

> **Superseded.** This Dream restates scope already fully realized by
> [`docs/dreams/pyforge-atlas.md`](pyforge-atlas.md) (status: realized) and its shipped
> 38-story, 11-wave chain (Waves 0, A–H, I). Its "Realization" list maps directly onto
> already-shipped waves: Discovery Engine → Wave B/H (pipeline porting, factory personas);
> Schema Evolution → the schema v29→v30 work Wave I's post-audit truth-up already covers;
> Phase Orchestrator (Kedro/Dagster) → Wave C ("Integrate kedro-dagster for scheduling +
> execution"); DuckDB Analytics → Wave F, story F1, verbatim ("DuckDB consolidation + prove
> the cold-start claim"); air-gap capability → already implemented repo-wide via the
> `<HOST>_BASE_URL` redirect pattern documented in `project-context.md`. Its own
> "Acceptance" criteria ("all 15 phases ported," "schema v29→v30 migration tested,"
> "dashboards consuming cf_atlas data live") describe work that is already done — Atlas is
> 100% code-complete (38/38 stories, 930 real tests, retro delivered). Created 2026-08-02
> in the same bulk commit already found this session to contain fabricated content (a false
> migration note, boilerplate test-architecture docs, and two other duplicate dreams —
> Marshal's loop-orchestrator, Mason's recipe-validator — retired the same way). Retired
> same day rather than spec'd as new work. See `spec-pyforge-atlas-intelligence-platform`
> for the retirement record.

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
