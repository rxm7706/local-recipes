---
spec: enterprise-data-models-and-apis
status: extension-point   # UNCHANGED 2026-09-09 (batch § 2.2 row atlas-B4). The park is deliberate
                          # and its trigger stands; only the owner Dream moved (`specified ->
                          # dreamt`), because `extension-point` is neither `ready` nor beyond.
updated: "2026-09-09"
owner-dream: docs/dreams/enterprise-data-models-and-apis.md
trigger: "a PyForge-native subject needs multi-source normalization + REST/JSON:API with audit history (cf_atlas already solves its case with DuckDB/Kedro; atlas-query-dashboards is the nearer need)"
companions: []
sources:
  - ../../../../../../docs/dreams/enterprise-data-models-and-apis.md
open_questions:
  - "Cross-station (readiness E-6): the Extension contract below states that warden Story 8.1's consult line points here. 8.1 is `done` and its code moved to `src/shared/packages/django-warden/` in the `2394d850db` relocation — re-verify the consult line moved with the code before this pointer is trusted."
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

## Dream status reconcile — 2026-09-09

**Owner Dream `docs/dreams/enterprise-data-models-and-apis.md` moves `specified → dreamt`**
(operator, fleet-readiness decision batch § 2.2 row atlas-B4). This Spec **keeps
`status: extension-point`**: `docs/dreams/README.md` is explicit that `specified` requires a Spec
at `ready` or beyond, and `extension-point` is neither. The Dream's own Constraint says it "should
not advance past `dreamt` without a concrete PyForge-native domain", and its § What is real reads
"Nothing". It reverts to `specified` the moment a subject is named and this Spec reaches `ready`.

The 2026-08-22 extension-point reframe is unchanged and sound — but the socket it names is
steward's shipped AD-17 pluggable-app registry (`config/engine_patterns.py`), not a surface this
Dream owns, so under the realization gate this Dream has nothing of its own to exercise.

**Cross-station obligation (steward):** `docs/dreams/README.md` should NAME `extension-point` as a
recognised parked-Spec state that does NOT satisfy `specified`, and carry this Dream's corrected
row/status.
