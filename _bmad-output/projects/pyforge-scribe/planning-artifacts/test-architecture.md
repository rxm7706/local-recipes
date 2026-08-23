---
title: "Test Architecture — pyforge-scribe"
type: test-architecture
generator: bmad_tea_playwright.py
generator_version: 2.0.0
status: generated
station: scribe
source_fingerprint: af525a8bf9c4d000
story_count: 11
test_file_count: 8
coverage_target_unit: ">=80%"
coverage_target_integration: ">=70%"
---

# Test Architecture — PyForge Scribe

This document is **machine-generated** by `bmad_tea_playwright.py` (v2.0.0). Do not hand-edit; re-run the generator after epics or tests change.

## Executive Summary

- **Station:** `pyforge-scribe`
- **Stories parsed:** 11
- **Epics parsed:** 5
- **Test files inventoried:** 8 under `src/shared/packages/pyforge-scribe/tests/`
- **Frameworks:** pytest (unit/integration/meta) + Playwright where present
- **Coverage targets:** unit ≥80%, integration ≥70% (gated by Story 19.3)
- **Source fingerprint:** `af525a8bf9c4d000`

## Risk Assessment

### High-risk epics

- none observed

### Medium-risk epics

- Epic 1: Team Memory — Capture & Promotion
- Epic 2: Knowledge Graph — Compile & Recall
- Epic 3: Scribe reaches the raw transcripts
- Epic 1: Team Memory — Capture & Promotion
- Epic 2: Knowledge Graph — Compile & Recall

### Low-risk epics

- none observed

## Test Inventory

| Relative path | Level | Linked stories |
|---------------|-------|----------------|
| `src/shared/packages/pyforge-scribe/tests/unit/test_capture.py` | unit | none observed |
| `src/shared/packages/pyforge-scribe/tests/unit/test_cli.py` | unit | none observed |
| `src/shared/packages/pyforge-scribe/tests/unit/test_compile.py` | unit | none observed |
| `src/shared/packages/pyforge-scribe/tests/unit/test_graph_store.py` | unit | none observed |
| `src/shared/packages/pyforge-scribe/tests/unit/test_promote.py` | unit | none observed |
| `src/shared/packages/pyforge-scribe/tests/unit/test_recall.py` | unit | none observed |
| `src/shared/packages/pyforge-scribe/tests/unit/test_supersession.py` | unit | none observed |
| `src/shared/packages/pyforge-scribe/tests/unit/test_transcripts.py` | unit | none observed |

## Story Coverage Matrix

| Story | Title | Linked test files |
|-------|-------|-------------------|
| 1.1 | Package scaffold + direct capture into team memory | none observed |
| 1.2 | `CLAUDE.md` wiring — team memory loads automatically | none observed |
| 1.3 | Promotion workflow — proposal-then-confirm, team-voice rewrite | none observed |
| 1.4 | Pointer-stub write-back + idempotent re-invocation | none observed |
| 1.5 | Seed promotion — the end-to-end proof | none observed |
| 2.1 | `GraphStore` port + flat-file v1 adapter | none observed |
| 2.2 | Nightly compile from named tool surfaces | none observed |
| 2.3 | Fact supersession in the compiled graph | none observed |
| 2.4 | `scribe recall` — grounded, cited answers | none observed |
| 3.1 | The scanner surfaces what sessions said but memory missed | none observed |
| 3.2 | Transcripts join the compile sources | none observed |

## Quality Gates

| Gate | Target | Enforcement |
|------|--------|-------------|
| Unit coverage | ≥80% | Story 19.3 CI gate |
| Integration coverage | ≥70% | Story 19.3 CI gate |
| Forbidden placeholder token | zero occurrences | this generator (hard fail) |
| Idempotent regen | byte-identical on unchanged tree | FR-132 |

## Regeneration

```bash
python _bmad/scripts/bmad_tea_playwright.py --project pyforge-scribe
python _bmad/scripts/bmad_tea_playwright.py --all
```
