---
spec: enterprise-data-models-and-apis
status: extension-point
owner-dream: docs/dreams/enterprise-data-models-and-apis.md
trigger: "a PyForge-native subject needs multi-source normalization + REST/JSON:API with audit history (cf_atlas already solves its case with DuckDB/Kedro; atlas-query-dashboards is the nearer need)"
companions: []
sources:
  - ../../../../../../docs/dreams/enterprise-data-models-and-apis.md
---

# SPEC — A normalized data model and REST API pattern (PARKED)

Parked by the Dream's own constraint — it is a parity capture whose premise
is not yet real here. The Dream itself calls this the most purely speculative of its batch. Zero stories minted; when the trigger fires, this
spec gets a real pass and decomposition. Parking recorded 2026-08-22 so
INV-1 holds without speculative work.

**Trigger:** a PyForge-native subject needs multi-source normalization + REST/JSON:API with audit history (cf_atlas already solves its case with DuckDB/Kedro; atlas-query-dashboards is the nearer need)

## Extension contract (added 2026-08-22)

The seam already exists: the platform's AD-17 pluggable-app registry
(`config/engine_patterns.py` — Pattern A in-process / Pattern B sidecar) is
the integration point. The three-tier raw/conformed/curated model +
DRF-JSON:API-with-audit-history pattern recorded here lands as a
separately-developed pluggable app — including an air-gapped extension —
whenever a subject appears; warden 8.1's consult line points here. No core
story exists or is needed: this spec IS the contract's pattern notes.
