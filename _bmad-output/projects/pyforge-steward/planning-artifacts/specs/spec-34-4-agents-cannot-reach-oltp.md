---
title: Agents cannot reach OLTP
type: feature
created: '2026-08-26'
status: done
updated: '2026-08-26'
baseline_commit: 9d3ad9105b
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** DB-GPT Text-to-SQL still registers Django PostgreSQL as the estate datasource. Hallucinated SQL can hit OLTP.

**Approach:** Estate read DSN is the query plane (`duckdb:` / `parquet:` / `atlas.duckdb`). A gate fails OLTP / `langflow_schema` writer URLs. Langflow estate RAG env matches. Host never imports `pyforge.*`.

## Acceptance Criteria

- Given platform Langflow / DB-GPT config, when the gate runs, then the estate read DSN is the plane.
- Given an OLTP DSN for Text-to-SQL, when the gate runs, then it fails.

## Boundaries & Constraints

**Always:** Ledger `34-4-agents-cannot-reach-oltp`. `LANGFLOW_DATABASE_URL` stays Langflow's own metadata schema.

**Never:** `pyforge.*` under `src/platform/`. Slice 3. Mosaic required.

</intent-contract>

## Tasks

- [x] `config/estate_dsn.py` gate + `QUERY_PLANE_ESTATE_DSN`.
- [x] DB-GPT register payload uses the plane.
- [x] Tests: plane DSN ok; postgres OLTP fails.
- [x] Ledger → `done` via `sprint-ledger-sync`.

## Verification

`pixi run -e python-agent-platform -- pytest src/platform/tests/test_estate_dsn_is_plane.py src/platform/dbgpt_integration/tests.py -q`
