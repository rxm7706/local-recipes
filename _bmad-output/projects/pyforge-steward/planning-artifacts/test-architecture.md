---
title: "Test Architecture — pyforge-steward"
type: test-architecture
date: 2026-08-02
version: 1.0.0
status: draft
scope: "Feedstock maintenance, conda-forge integration, automated updates"
target_coverage: "Unit ≥80%, Integration ≥70%, E2E critical paths"
---

# Test Architecture — PyForge Steward

## Executive Summary

**Steward** automates feedstock maintenance — version tracking, autotick updates, bot command routing, and conda-forge integration for hands-off recipe lifecycle management.

**Coverage Target**: Unit ≥80%, Integration ≥70%, E2E (update detect → PR create → merge).

---

## Test Strategy Overview

| Level | Approach | Target Stories | Status |
|-------|----------|----------------|--------|
| **Unit (UT)** | Version detection, update logic, bot commands | TBD | ⏳ READY |
| **Integration (IT)** | Autotick workflows, PR creation, conda-forge ops | TBD | ⏳ READY |
| **E2E** | End-to-end (version detect → PR → merge) | TBD | ⏳ READY |

---

## Test Fixtures & Mocks

**Shared Fixtures** (`tests/conftest.py`):
- `feedstock_repo`: Real feedstock git repo at tmp_path
- `version_detector`: Mock upstream version tracking
- `pr_creator`: Mock GitHub PR workflow
- `cf_interface`: Mock conda-forge API (commands, PRs, merges)

**Mocks** (`tests/mocks/`):
- `mock_upstream.py`: Stubs upstream version detection
- `mock_github.py`: Simulates PR creation, merging
- `mock_cf_bot.py`: Stubs conda-forge bot commands

---

## Meta-Tests

- **Determinism**: Same feedstock updated twice = identical PR subjects
- **Envelope**: PR metadata (title, body, labels) complete
- **CF Integration**: Bot commands follow conda-forge conventions

---

## Framework & Tooling

**Pytest**: Unit + integration testing
- `tests/unit/` ← version detection, logic, bot commands
- `tests/integration/` ← autotick workflows, PR creation
- `tests/meta/` ← invariants (determinism, envelope, CF conventions)

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
