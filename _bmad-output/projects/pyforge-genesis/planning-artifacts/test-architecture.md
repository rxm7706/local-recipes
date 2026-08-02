---
title: "Test Architecture — pyforge-genesis"
type: test-architecture
date: 2026-08-02
version: 1.0.0
status: draft
scope: "Installer bootstrapping, environment provisioning, dependency resolution"
target_coverage: "Unit ≥80%, Integration ≥70%, E2E critical paths"
---

# Test Architecture — PyForge Genesis

## Executive Summary

**Genesis** bootstraps the PyForge factory installer — provisioning reproducible environments, resolving dependencies, and initializing the complete factory stack from scratch.

**Coverage Target**: Unit ≥80%, Integration ≥70%, E2E (bootstrap → verify → full factory ready).

---

## Test Strategy Overview

| Level | Approach | Target Stories | Status |
|-------|----------|----------------|--------|
| **Unit (UT)** | Environment config, dependency resolution logic | TBD | ⏳ READY |
| **Integration (IT)** | Install workflows, environment provisioning | TBD | ⏳ READY |
| **E2E** | End-to-end (bootstrap → verify tools → factory ready) | TBD | ⏳ READY |

---

## Test Fixtures & Mocks

**Shared Fixtures** (`tests/conftest.py`):
- `clean_env`: Clean environment for bootstrap testing
- `dependency_resolver`: Mock pixi/conda resolver
- `installer`: Mock factory installer
- `verification_suite`: Mock tool verification (all 30+ tools)

**Mocks** (`tests/mocks/`):
- `mock_installer.py`: Stubs installation process
- `mock_resolver.py`: Simulates dependency resolution
- `mock_verify.py`: Stubs tool verification suite

---

## Meta-Tests

- **Determinism**: Same bootstrap twice = identical environment
- **Envelope**: All factory tools installed and verified
- **Completeness**: All 30+ tools present, correct versions

---

## Framework & Tooling

**Pytest**: Unit + integration testing
- `tests/unit/` ← config, dependency resolution logic
- `tests/integration/` ← install workflows, provisioning
- `tests/meta/` ← invariants (determinism, envelope, completeness)

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
