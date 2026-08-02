---
title: "Test Architecture — pyforge-mason"
type: test-architecture
date: 2026-08-02
version: 1.0.0
status: draft
scope: "Recipe validation, conda-forge linting, schema enforcement"
target_coverage: "Unit ≥80%, Integration ≥70%, E2E critical paths"
---

# Test Architecture — PyForge Mason

## Executive Summary

**Mason** validates conda-forge recipes against linting rules, schema, and best practices — enforcing recipe.yaml/meta.yaml conformance, selector syntax, pinning policy, and cross-platform compatibility.

**Coverage Target**: Unit ≥80%, Integration ≥70%, E2E (recipe parse → validate → findings).

---

## Test Strategy Overview

| Level | Approach | Target Stories | Status |
|-------|----------|----------------|--------|
| **Unit (UT)** | Linting rules, schema validation, policy checks | TBD | ⏳ READY |
| **Integration (IT)** | Recipe parsing, full validation workflows | TBD | ⏳ READY |
| **E2E** | End-to-end (recipe → linting → findings report) | TBD | ⏳ READY |

---

## Test Fixtures & Mocks

**Shared Fixtures** (`tests/conftest.py`):
- `recipe_parser`: Real YAML recipe parser
- `linting_engine`: Mock linting rule executor
- `schema_validator`: Mock recipe schema validator
- `findings_report`: Real findings report with all rule codes

**Mocks** (`tests/mocks/`):
- `mock_recipe.py`: Generates test recipes (valid, invalid, edge cases)
- `mock_linter.py`: Stubs linting engine
- `mock_schema.py`: Mocks recipe.yaml/meta.yaml schemas

---

## Meta-Tests

- **Determinism**: Same recipe linted twice = identical findings
- **Envelope**: Findings have all required fields (code, severity, message)
- **Coverage**: All linting rules tested with at least one pass + one fail case

---

## Framework & Tooling

**Pytest**: Unit + integration testing
- `tests/unit/` ← linting rules, schema, policy
- `tests/integration/` ← recipe parsing, full validation
- `tests/meta/` ← invariants (determinism, envelope, coverage)

---

## Readiness Checklist

- [ ] Stories defined in epics.md
- [ ] Stories mapped to FRs + ADs
- [ ] UT + IT strategy defined
- [ ] E2E critical paths identified
- [ ] Pytest config generated (`pytest.ini`)
- [ ] Test fixtures implemented
- [ ] CI gates configured
- [ ] Coverage baselines established

---

**Status**: DRAFT — ready for epic/story generation from Dream

**Last updated**: 2026-08-02
