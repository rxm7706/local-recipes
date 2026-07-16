---
stepsCompleted: [1]
inputDocuments: []
workflowType: 'research'
lastStep: 1
research_type: 'domain'
research_topic: 'cf_atlas domain triad: conda/PyPI packaging ecosystem, data-pipeline orchestration, software supply-chain security'
research_goals: 'Broad scan of all three domains, then targeted deep dives. Ground the cfe-atlas-datapipeline Kedro migration spec (v5.1) in current ecosystem evidence; systematically discover uncaptured external signals/feeds (e.g. are-we-recipe-v1-yet, migration trackers, advisory APIs) the atlas should ingest; validate or challenge the committed tool bets (Kedro + Dagster + DuckDB + Ibis/BSL + Vizro); map the vulnerability-feed and SBOM-standards landscape around FR-13/16/17/18/19.'
user_name: 'Rxm7706'
date: '2026-07-16'
web_research_enabled: true
source_verification: true
---

# Research Report: domain

**Date:** 2026-07-16
**Author:** Rxm7706
**Research Type:** domain

---

## Research Overview

[Research overview and methodology will be appended here]

---

<!-- Content will be appended sequentially through research workflow steps -->

## Domain Research Scope Confirmation

**Research Topic:** cf_atlas domain triad — conda/PyPI packaging ecosystem, data-pipeline orchestration, software supply-chain security
**Research Goals:** Broad scan of all three domains, then targeted deep dives. Ground the cfe-atlas-datapipeline Kedro migration spec (v5.1) in current ecosystem evidence; systematically discover uncaptured external signals/feeds (e.g. are-we-recipe-v1-yet, migration trackers, advisory APIs) the atlas should ingest; validate or challenge the committed tool bets (Kedro + Dagster + DuckDB + Ibis/BSL + Vizro); map the vulnerability-feed and SBOM-standards landscape around FR-13/16/17/18/19.

**Domain Research Scope:**

- Industry Analysis — structure and key players of each domain: packaging (conda-forge, prefix.dev, Anaconda, PyPA), orchestration (Kedro, Dagster, Airflow, Prefect, DuckDB-centric stacks), supply-chain security (OSV/Google, Aqua, Anchore, OWASP, Basilisk)
- Regulatory Environment — EU CRA, US EO 14028 / SSDF, SBOM mandates; PEP 740 / SLSA / CEPs as de-facto standards
- Technology Trends — recipe v1 adoption (are-we-recipe-v1-yet), rattler-build/pixi momentum, the DuckDB "small data" movement, semantic layers, agent-facing data surfaces (MCP)
- Economic Factors — ecosystem sizes, growth signals, sustainability of feeds the atlas would depend on
- Supply Chain / Ecosystem Analysis — the upstream release → advisory → packaging → consumption value chain; the **signal census** (every tracker/API/feed each domain publishes, mapped against current atlas ingestion)

**Research Methodology:**

- All claims verified against current public sources
- Multi-source validation for critical domain claims
- Confidence level framework for uncertain information
- Findings structured for direct incorporation into the migration spec's § 13 integration-surface matrix and § 12.1 candidate-signals table

**Scope Confirmed:** 2026-07-16
