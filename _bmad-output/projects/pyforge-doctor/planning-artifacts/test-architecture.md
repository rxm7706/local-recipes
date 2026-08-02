---
title: "Test Architecture — pyforge-doctor"
type: test-architecture
date: 2026-08-02
version: 1.0.0
status: draft
scope: "Dependency health diagnostics, version tracking, obsolescence detection"
target_coverage: "Unit ≥80%, Integration ≥70%, E2E critical paths"
---

# Test Architecture — PyForge Doctor

## Executive Summary

**Doctor** diagnoses Python/Conda dependency health — tracking versions, detecting obsolescence, monitoring adoption signals, and providing actionable remediation.

**Coverage Target**: Unit ≥80%, Integration ≥70%, E2E (scan → diagnostics → remediation).

---

## Test Strategy Overview

| Level | Approach | Target Stories | Status |
|-------|----------|----------------|--------|
| **Unit (UT)** | Health scoring, version logic, adoption signals | TBD | ⏳ READY |
| **Integration (IT)** | Dependency resolution, diagnostics workflows | TBD | ⏳ READY |
| **E2E** | End-to-end (scan → diagnostics → remediation) | TBD | ⏳ READY |

---

## Test Fixtures & Mocks

**Shared Fixtures** (`tests/conftest.py`):
- `health_report`: Real dependency health report
- `version_tracker`: Mock version history tracking
- `adoption_signals`: Mock adoption metrics (downloads, age, community)
- `remediation_engine`: Mock fix recommendation logic

**Mocks** (`tests/mocks/`):
- `mock_version_tracker.py`: Stubs PyPI/conda version history
- `mock_adoption.py`: Mocks adoption signal calculation
- `mock_remediation.py`: Simulates remediation recommendations

---

## Meta-Tests

- **Determinism**: Same dependency scanned twice = identical health score
- **Envelope**: HealthReport has all required fields
- **Scoring**: Health score correctly weights all signals

---

## Framework & Tooling

**Pytest**: Unit + integration testing
- `tests/unit/` ← health scoring, version logic, signals
- `tests/integration/` ← dependency resolution, diagnostics
- `tests/meta/` ← invariants (determinism, envelope, scoring)

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
