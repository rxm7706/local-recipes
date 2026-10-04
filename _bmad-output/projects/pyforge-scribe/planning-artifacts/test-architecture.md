---
title: "Test Architecture — pyforge-scribe"
type: test-architecture
generator: bmad_tea_playwright.py
generator_version: 2.1.0
status: generated
station: scribe
source_fingerprint: bbb01943a54c7451
story_count: 48
test_file_count: 23
coverage_target_unit: ">=80%"
coverage_target_integration: ">=70%"
---

# Test Architecture — PyForge Scribe

This document is **machine-generated** by `bmad_tea_playwright.py` (v2.1.0). Do not hand-edit; re-run the generator after epics or tests change.

## Executive Summary

- **Station:** `pyforge-scribe`
- **Stories parsed:** 48
- **Epics parsed:** 26
- **Test files inventoried:** 23 under `src/shared/packages/pyforge-scribe/tests/`
- **Frameworks:** pytest (unit/integration/meta) + Playwright where present
- **Coverage targets:** unit ≥80%, integration ≥70% (gated by Story 19.3)
- **Source fingerprint:** `bbb01943a54c7451`

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
- Epic 8: Scribe in effect — the compile runs on a schedule the estate owns
- Epic 9: Scoped retrieve can cite the poster’s numbers
- Epic 10: The story you are on compiles; the ones you finished do not
- Epic 11: Recall withholds what landed after last night's compile
- Epic 12: Every recall door uses the same default bag
- Epic 13: Planning novels stay files; the graph holds pointers
- Epic 15: Graphify walks the named code trees, not the warehouse
- Epic 16: Recall names the surface, not a kind bag
- Epic 17: One owner for “where is this symbol?”
- Epic 18: Planning retrieve names the planning surface
- Epic 19: The session contract reaches every harness
- Epic 20: The managed instruction block carries no aspiration (spec-pyforge-scribe CAP-30)
- Epic 21: The instruction surface names the estate first (spec-python-foundry-cutover fnd:CAP-15)
- Epic 22: The local Postgres cluster starts from any checkout (spec-pyforge-scribe CAP-31)
- Epic 23: The instruction surface loads once (spec-pyforge-scribe CAP-27)
- Epic 24: Every session reads one derived picture of the BMAD estate (spec-pyforge-scribe CAP-32)
- Epic 25: The estate catalog reads only in-tree skills (spec-pyforge-scribe CAP-32)
- Epic 26: Phase 4+5 of the deferral burn-down: scribe's open medium and low deferrals

### Low-risk epics

- Epic 7: Scribe keeps the docs with three utility skills
- Epic 14: Named docs extras, never the docs tree

## Test Inventory

| Relative path | Level | Linked stories |
|---------------|-------|----------------|
| `src/shared/packages/pyforge-scribe/tests/meta/test_first_portal_slice.py` | meta | none observed |
| `src/shared/packages/pyforge-scribe/tests/meta/test_guild_env_membership.py` | meta | none observed |
| `src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py` | meta | none observed |
| `src/shared/packages/pyforge-scribe/tests/meta/test_skf_skill_ownership.py` | meta | none observed |
| `src/shared/packages/pyforge-scribe/tests/meta/test_station_persona.py` | meta | none observed |
| `src/shared/packages/pyforge-scribe/tests/unit/test_capture.py` | unit | none observed |
| `src/shared/packages/pyforge-scribe/tests/unit/test_catalog_bmad_estate.py` | unit | none observed |
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
| `src/shared/packages/pyforge-scribe/tests/unit/test_navigation_owner.py` | unit | none observed |
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
| 8.1 | The nightly compile gets a trigger the estate owns, and a freshness signal th... | none observed |
| 8.2 | The nightly compile keeps the graphify code surface | none observed |
| 8.3 | Herald fact ledgers join the compile | none observed |
| 8.4 | The compile keeps knowledge layers honest | none observed |
| 8.5 | Default recall omits the code surface | none observed |
| 8.6 | Session path names scribe recall | none observed |
| 9.1 | Scoped recall admits the project's own fact ledger | none observed |
| 10.1 | In-flight story specs join the compile | none observed |
| 11.1 | Recall withholds sources committed after compile | none observed |
| 12.1 | Portal and Marshal inherit default recall | none observed |
| 13.1 | Planning pointers join the compile | none observed |
| 14.1 | Named docs join the compile | none observed |
| 15.1 | Graphify target list joins the compile | none observed |
| 16.1 | Recall modes join the CLI | none observed |
| 17.1 | Marshal codegraph owns symbol navigation | none observed |
| 18.1 | Retrieve and sessions pass mode planning | none observed |
| 19.1 | One AGENTS.md, reached natively or by a one-line pointer from every harness | none observed |
| 19.2 | scribe capture and recall run from the session default environment | none observed |
| 19.3 | The instruction surface is version-aware — Claude Code's built-in agents-md mod | none observed |
| 20.1 | The parity meta-test reds a TODO inside the managed block | none observed |
| 21.1 | `AGENTS.md` opens with what this repository is | none observed |
| 21.2 | `AGENTS.md` says what runs `governance-currency` | none observed |
| 22.1 | `scribe-pg-up` succeeds from a long-path worktree | none observed |
| 23.1 | The SKF managed block lives in `AGENTS.md` only | none observed |
| 24.1 | The BMAD estate catalog is generated, not written | none observed |
| 24.2 | The catalog cannot drift silently | none observed |
| 24.3 | Every harness is pointed at the catalog once | none observed |
| 25.1 | The estate catalog skips skill directories git ignores | none observed |
| 26.1 | Recall breaks ties by recency, and scribe's other open deferrals close | none observed |

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
