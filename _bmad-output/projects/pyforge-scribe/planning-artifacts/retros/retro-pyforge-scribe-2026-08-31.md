---
title: "pyforge-scribe — Epic 6 retrospective"
created: "2026-08-31"
updated: "2026-08-31"
covers: "Epic 6 (compile_surface extras — graphify, cocoindex, graph-node staleness), 2026-08-26 through 2026-08-30"
evidence: "git log --oneline --since=2026-08-26 -- src/shared/packages/pyforge-scribe _bmad-output/projects/pyforge-scribe; pixi run -e pyforge-scribe pyforge-scribe-test"
---

# pyforge-scribe — Epic 6 Retrospective, 2026-08-31

**Trigger:** `chain-currency-sweep` flagged the `code→retro` checkpoint stale (code landed `2026-08-30`, prior retro `2026-08-26`). Companion to `retro-pyforge-scribe-2026-08-26.md` (Epics 3–5) — this covers only Epic 6, which that retro predates. Full evidence-sourced analysis lives at `implementation-artifacts/epic-6-retro-2026-08-31.md` (Phase 1–5 retrospective-skill output, headless, sprint-mode); this document is the tracked planning-artifact summary the currency sweep's `retro` stage actually resolves against (`{pa}/retros/*{slug}*.md`).

## Delivery snapshot

| Date | Commit | What |
|---|---|---|
| 2026-08-27ish | `b594b9e2cd` (Merge 6-1) | Story 6.1 — the graphify ingest extra (`extras/graphify.py`) and its move-list verbs (`extras/move_list.py`); off by default, no foundry-root `graphify-out/` product dir (per epic constraint) |
| 2026-08-29ish | `e828362534` (Merge 6-2) | Story 6.2 — the cocoindex incremental-refresh `compile_surface` extra (`extras/cocoindex_flow.py`); AC4 confirmed no `cocoindex.serve` call, no `@coco.fn`/`@cocoindex.fn` |
| 2026-08-30 | `bc6bfc996a` (Merge 6-3) | Story 6.3 — the graph-node staleness flag (CAP-13); `compile.py` +108 lines, both `GraphStore` drivers (`graph_store_pg.py`, `graph_store_plane.py`) updated to consume it |

Between these, three separate `marshal: widen scribe epic_surfaces for 6 ...` commits (2nd- and 3rd-attempt scope misses) — the same `MRS-GATE-007`-class friction this session independently root-caused and is fixing at the source tonight (`docs/dreams/marshal-dependency-aware-dispatch.md`, marshal Stories 28.14/28.15).

## What shipped, in product terms

Epic 6 binds the two "bind now" estate pins from `spec-pyforge-unifying-strategy` as optional `compile_surface` ingest extras on Story 4.1's CAP-18 plugin contract — both off by default (air-gap posture). The epic's own explicit "Never, epic-wide" list (no second graph/vector store, no `cocoindex.serve` MCP product, no `@coco.fn` lineage religion, no foundry-root product dir, no `mem0.add` in place of `scribe capture`) was verified held: grepped the shipped source for each pattern — the only hits are the extras' own docstrings *documenting* the constraint, not violations.

Story 6.3's staleness flag is the cross-station load-bearing piece: marshal Story 28.9 (planning-graph retrieval, this session's own work) declares `Deps: S-28.8, scribe S-6.3` and was verified blocked on 6.3's landing this session, unblocking the moment it shipped — real, verified integration, not a paper dependency.

## Behavior verification

`pixi run -e pyforge-scribe pyforge-scribe-test`: **313 passed, 1 skipped, 0 failed** (2026-08-31, post-Tier-3-feed-repair, current `main`). Exercises all three new extras test files (`test_extras_graphify.py`, `test_extras_move_list.py`, `test_extras_cocoindex_flow.py`).

## Verdict

**Accepted.** Declared criteria (epic's own constraint list + three stories' ACs), all `done` in the tracked ledger, constraint grep clean, test suite clean, cross-station dependency verified satisfied. No fix-now action items — the recurring `epic_surfaces` friction already has an owned fix in flight (marshal 28.14/28.15), not duplicated here.
