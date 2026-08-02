---
title: "Test Architecture — pyforge-atlas"
type: test-architecture
date: 2026-08-02
version: 1.0.0
status: draft
scope: "Atlas intelligence layer, data pipeline, phase orchestration, schema evolution"
target_coverage: "Unit ≥80%, Integration ≥70%, E2E critical paths"
---

# Test Architecture — PyForge Atlas

## Executive Summary

**Atlas** powers the cf_atlas intelligence layer — a Kedro/Dagster/DuckDB data pipeline orchestrating 15 phases (B → N) across 16 schema versions, discovery engine, and feedstock intelligence.

**Coverage Target**: Unit ≥80%, Integration ≥70%, E2E critical paths (discovery → schema → phase execution).

---

## Test Strategy Overview

| Level | Approach | Target Stories | Status |
|-------|----------|----------------|--------|
| **Unit (UT)** | Core logic (phase runners, schema validation, discovery logic) | TBD | ⏳ READY |
| **Integration (IT)** | Pipeline stages (phase execution, data flow, transformations) | TBD | ⏳ READY |
| **E2E** | End-to-end (discovery → schema → full pipeline run) | TBD | ⏳ READY |

---

## Test Fixtures & Mocks

**Shared Fixtures** (`tests/conftest.py`):
- `atlas_db_fixture`: Real DuckDB instance at tmp_path
- `phase_runner`: Mock Kedro/Dagster phase executor
- `discovery_engine`: Mock cf_atlas discovery (trending candidates, category, adoption)
- `schema_registry`: Atlas schema versions (16 versions, v29→v30 tracking)

**Mocks** (`tests/mocks/`):
- `mock_phase_runner.py`: Simulates phase execution with deterministic timing
- `mock_discovery.py`: Stubs discovery engine (trending, classification, adoption)
- `mock_schema.py`: Mocks schema versions and evolution

---

## Meta-Tests

- **Determinism**: Multiple runs with identical input produce byte-identical output
- **Envelope**: Pipeline outputs have all required fields per schema
- **Schema Validation**: All phase outputs conform to declared schema version

---

## Framework & Tooling

**Pytest**: Unit + integration testing
- `tests/unit/` ← phase logic, discovery, schema validation
- `tests/integration/` ← pipeline stage workflows
- `tests/meta/` ← invariants (determinism, envelope, schema)

**DuckDB**: Real in-memory database for integration tests

---

## Readiness Checklist

- [ ] Stories defined in epics.md
- [ ] Stories mapped to FRs + ADs
- [ ] UT + IT strategy defined
- [ ] E2E critical paths identified
- [ ] Pytest config generated (`pytest.ini`)
- [ ] Playwright config generated (`playwright.config.ts`)
- [ ] Test fixtures implemented
- [ ] CI gates configured
- [ ] Coverage baselines established

---

**Status**: DRAFT — ready for epic/story generation from Dream

**Last updated**: 2026-08-02
