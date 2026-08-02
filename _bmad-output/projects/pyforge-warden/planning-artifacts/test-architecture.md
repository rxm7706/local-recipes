---
title: "Test Architecture — pyforge-warden"
type: test-architecture
date: 2026-08-02
version: 1.0.0
status: draft
scope: "Compliance gates, dependency scanning, policy enforcement, findings aggregation"
target_coverage: "Unit ≥80%, Integration ≥70%, E2E critical paths"
---

# Test Architecture — PyForge Warden

## Executive Summary

**Warden** is a pluggable multi-axis Python dependency compliance gate — axes: hygiene (deptry), security (osv-scanner + CISA-KEV + EPSS), license, currency, with flag-activated gates, baseline & grandfathering, and opt-in fix-PR actuator.

**Coverage Target**: Unit ≥80%, Integration ≥70%, E2E (scan → verdict → enforcement).

---

## Test Strategy Overview

| Level | Approach | Target Stories | Status |
|-------|----------|----------------|--------|
| **Unit (UT)** | Gate logic, verdict aggregation, policy | TBD | ⏳ READY |
| **Integration (IT)** | Scanning workflows, manifest parsing, findings | TBD | ⏳ READY |
| **E2E** | End-to-end (scan → verdict → gate enforcement) | TBD | ⏳ READY |

---

## Test Fixtures & Mocks

**Shared Fixtures** (`tests/conftest.py`):
- `compliance_report`: Real ComplianceReport with all axes
- `gate_policy`: Policy composition (gates, thresholds, baselines)
- `manifest_parser`: Mock manifest parser (pyproject.toml, poetry.lock, pixi.lock)
- `scanner_runner`: Mock osv-scanner + deptry runners

**Mocks** (`tests/mocks/`):
- `mock_scanner.py`: Stubs osv-scanner, deptry, license checker
- `mock_manifest.py`: Mocks Python/Conda/Pixi manifest formats
- `mock_gate.py`: Simulates gate evaluation + verdict

---

## Meta-Tests

- **Determinism**: Same manifest scanned twice = identical verdict
- **Envelope**: All ComplianceReport fields populated per schema
- **Gate Logic**: Gate never false-greens (fails if any axis fails)

---

## Framework & Tooling

**Pytest**: Unit + integration testing
- `tests/unit/` ← gate logic, verdict aggregation, policy
- `tests/integration/` ← scanning, manifest parsing
- `tests/meta/` ← invariants (determinism, envelope, correctness)

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
