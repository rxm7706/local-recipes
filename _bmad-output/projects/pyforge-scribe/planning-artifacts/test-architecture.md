---
title: "Test Architecture — pyforge-scribe"
type: test-architecture
generator: bmad_tea_playwright.py
generator_version: 2.1.0
status: generated
station: scribe
source_fingerprint: 00b63c144e11556b
story_count: 19
test_file_count: 19
coverage_target_unit: ">=80%"
coverage_target_integration: ">=70%"
---

# Test Architecture — PyForge Scribe

This document is **machine-generated** by `bmad_tea_playwright.py` (v2.1.0). Do not hand-edit; re-run the generator after epics or tests change.

## Executive Summary

- **Station:** `pyforge-scribe`
- **Stories parsed:** 19
- **Epics parsed:** 7
- **Test files inventoried:** 19 under `src/shared/packages/pyforge-scribe/tests/`
- **Frameworks:** pytest (unit/integration/meta) + Playwright where present
- **Coverage targets:** unit ≥80%, integration ≥70% (gated by Story 19.3)
- **Source fingerprint:** `00b63c144e11556b`

## Risk Assessment

### High-risk epics

- none observed

### Medium-risk epics

- Epic 1: Team Memory — Capture & Promotion
- Epic 2: Knowledge Graph — Compile & Recall
- Epic 3: Scribe reaches the raw transcripts
- Epic 4: GraphStore on the shared plugin contract
- Epic 5: Scribe owns remaining skill/persona and one portal job
- Epic 6: The compile_surface extras — graphify and cocoindex behind the ports

### Low-risk epics

- Epic 7: Scribe keeps the docs with three utility skills

## Test Inventory

| Relative path | Level | Linked stories |
|---------------|-------|----------------|
| `src/shared/packages/pyforge-scribe/tests/meta/test_first_portal_slice.py` | meta | none observed |
| `src/shared/packages/pyforge-scribe/tests/meta/test_skf_skill_ownership.py` | meta | none observed |
| `src/shared/packages/pyforge-scribe/tests/meta/test_station_persona.py` | meta | none observed |
| `src/shared/packages/pyforge-scribe/tests/unit/test_capture.py` | unit | none observed |
| `src/shared/packages/pyforge-scribe/tests/unit/test_cli.py` | unit | none observed |
| `src/shared/packages/pyforge-scribe/tests/unit/test_compile.py` | unit | none observed |
| `src/shared/packages/pyforge-scribe/tests/unit/test_extras_cocoindex_flow.py` | unit | none observed |
| `src/shared/packages/pyforge-scribe/tests/unit/test_extras_graphify.py` | unit | none observed |
| `src/shared/packages/pyforge-scribe/tests/unit/test_extras_move_list.py` | unit | none observed |
| `src/shared/packages/pyforge-scribe/tests/unit/test_graph_store.py` | unit | none observed |
| `src/shared/packages/pyforge-scribe/tests/unit/test_graph_store_operations.py` | unit | none observed |
| `src/shared/packages/pyforge-scribe/tests/unit/test_graph_store_pg.py` | unit | none observed |
| `src/shared/packages/pyforge-scribe/tests/unit/test_graph_store_plane.py` | unit | none observed |
| `src/shared/packages/pyforge-scribe/tests/unit/test_graph_store_plugins.py` | unit | none observed |
| `src/shared/packages/pyforge-scribe/tests/unit/test_promote.py` | unit | none observed |
| `src/shared/packages/pyforge-scribe/tests/unit/test_recall.py` | unit | none observed |
| `src/shared/packages/pyforge-scribe/tests/unit/test_recall_semantic.py` | unit | none observed |
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
| 3.3 | The nightly compile gets a schedule and a cost ceiling | none observed |
| 4.1 | Register GraphStore as CAP-18 plugins | none observed |
| 5.1 | SKF skill ownership and BMAD persona for scribe | none observed |
| 5.2 | First portal slice — one recall query | none observed |
| 6.1 | The graphify ingest extra and its move-list verbs | none observed |
| 6.2 | The cocoindex incremental ingest extra | none observed |
| 6.3 | The graph-node staleness flag | none observed |
| 7.1 | Three docs skills are scribe-wielded | none observed |

## Quality Gates

| Gate | Target | Enforcement |
|------|--------|-------------|
| Unit coverage | ≥80% | Story 19.3 CI gate |
| Integration coverage | ≥70% | Story 19.3 CI gate |
| Forbidden placeholder token | zero occurrences | this generator (hard fail) |
| Idempotent regen | byte-identical on unchanged tree | FR-132 |
| Story-id coverage drift | every epic story id in matrix | `--check` (CAP-5 / Story 19.4) |

## Regeneration

```bash
python _bmad/scripts/bmad_tea_playwright.py --project pyforge-scribe
python _bmad/scripts/bmad_tea_playwright.py --all
python _bmad/scripts/bmad_tea_playwright.py --project pyforge-scribe --check
python _bmad/scripts/bmad_tea_playwright.py --all --check
```
