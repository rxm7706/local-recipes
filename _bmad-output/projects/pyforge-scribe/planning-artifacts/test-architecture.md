---
title: "Test Architecture — pyforge-scribe"
type: test-architecture
date: 2026-08-02
version: 1.0.0
status: draft
scope: "Documentation generation, memory management, team context sharing"
target_coverage: "Unit ≥80%, Integration ≥70%, E2E critical paths"
---

# Test Architecture — PyForge Scribe

## Executive Summary

**Scribe** manages team memory and documentation — capturing decisions, project context, team feedback, and reference material in structured, reviewable prose for every contributor.

**Coverage Target**: Unit ≥80%, Integration ≥70%, E2E (memory write → verification → promotion).

---

## Test Strategy Overview

| Level | Approach | Target Stories | Status |
|-------|----------|----------------|--------|
| **Unit (UT)** | Memory schema, promotion rules, formatting | TBD | ⏳ READY |
| **Integration (IT)** | Memory workflows, git integration | TBD | ⏳ READY |
| **E2E** | End-to-end (capture → verify → promote to team) | TBD | ⏳ READY |

---

## Test Fixtures & Mocks

**Shared Fixtures** (`tests/conftest.py`):
- `memory_store`: Real memory filesystem at tmp_path
- `schema_validator`: Mock memory schema validator
- `promotion_engine`: Mock promotion workflow (user → team)
- `git_interface`: Mock git operations (commit, push)

**Mocks** (`tests/mocks/`):
- `mock_memory.py`: Generates test memory entries
- `mock_validator.py`: Stubs schema validation
- `mock_git.py`: Simulates git commit/push

---

## Meta-Tests

- **Determinism**: Same memory entry written twice = identical YAML output
- **Envelope**: Memory entries have all required frontmatter fields
- **Promotion**: Team memory passing all team-relevance checks

---

## Framework & Tooling

**Pytest**: Unit + integration testing
- `tests/unit/` ← memory schema, validation, promotion rules
- `tests/integration/` ← memory workflows, git operations
- `tests/meta/` ← invariants (determinism, envelope, validation)

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
