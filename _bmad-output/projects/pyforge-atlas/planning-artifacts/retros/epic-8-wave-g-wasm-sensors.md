---
doc_type: retrospective
project: pyforge-atlas
epic: 8
wave: G
title: Wave G — WebAssembly Portability & Event-Driven Sensors
stories: 3
date: 2026-07-25
basis: reconstructed from tracked evidence (run log, epics.md, PRs #96/#97/#98)
---

# Epic 8 · Wave G — WebAssembly Portability & Event-Driven Sensors

**Scope:** G1 DuckDB-WASM in-browser read surface + `wasm-smoke` gate, FR-14
(`203be0c`, #96) · G2 host-agnostic static-host Parquet emitter + HTTP-Range gate,
FR-14 (`6146f83`, `33b3fd8`, #97) · G3 Dagster sensors for near-real-time upstream
ingestion, FR-6 (`40b9eae`, #98).

## What worked

- **The read surface runs with no backend at all (CAP-16), and it is gated.**
  `wasm-smoke` plus the HTTP-Range gate make "works from a static host" a checked
  property rather than a claim.
- **G3 was the first story to complete its own full review loop** — the process
  reached steady state by the eighth epic, which is itself a finding.
- **G2's path-traversal MUST-FIX was caught by the independent reviewer**, then
  hardened twice: `_require_safe_name`, then rejecting over-long names up front.
  The second pass came from thinking about the *class* of input, not the instance.

## What did not

- **A path-traversal defect reached review in a file-emitting story.** For a
  component whose entire job is writing user-influenced filenames to a static
  host, traversal is the first thing to design against, not the first thing to
  find in review.
- **G3 re-deferred the live daemon** (`DW-G3`) — the third wave to defer the same
  bring-up (after C1, before H4) with no owning item.
- **`wasm-smoke` proves it loads, not that it is correct.** No assertion compares
  a WASM-side query result against the native path.

## Carry-forward

1. **Any component that writes a path from external input starts with a
   name-safety helper**, not a review finding. Make it a checklist item.
2. **Hardening should generalize from the instance to the class** — G2's
   over-long-name follow-up is the model.
3. **A smoke gate is a floor.** Where two engines answer the same question (WASM
   vs native), assert they agree.
