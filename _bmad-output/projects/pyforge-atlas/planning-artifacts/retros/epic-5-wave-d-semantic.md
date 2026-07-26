---
doc_type: retrospective
project: pyforge-atlas
epic: 5
wave: D
title: Wave D — Semantic Layer & Dashboards
stories: 3
date: 2026-07-25
basis: reconstructed from tracked evidence (run log, epics.md, PRs #86/#87/#88)
---

# Epic 5 · Wave D — Semantic Layer & Dashboards

**Scope:** D1 Boring Semantic Layer models over the core metrics, FR-8 (`580e5ba`,
#86) · D2 BSL-driven Vizro dashboard + CLI-port pages, FR-9 (`7b6b3ca`, #87) ·
D3 Vizro-AI NL interface + `query_vizro_ai` MCP tool, FR-9 (`d58a4bd`, #88).

## What worked

- **One metric definition, three consumers.** D1 defined the metrics once in BSL;
  D2's dashboard and D3's NL interface both read *through* it. No dashboard SQL,
  no re-derived metrics — the layering held.
- **Pure Ibis→DuckDB throughout**, consistent with CAP-6 (one engine for compute,
  graph, and vector). The semantic layer did not become a reason to add an engine.
- **D3 shipped the interface with the LLM backend deferred** (`DW-D3-1`). The
  seam — tool contract, dry-run path — is real and testable; only the model call
  is absent.

## What did not

- **The dashboards have no rendering test.** D2 shipped pages; nothing asserts a
  page renders. The gate covers the semantic layer beneath them, so a broken page
  above a healthy metric would pass.
- **`query_vizro_ai` is a tool whose answer nobody can check** without the
  deferred backend. It counts toward the 11-tool surface while being the one tool
  that cannot be exercised end-to-end.
- **Three of the four `DW-D*` entries are among the 45 lost to truncation.**

## Carry-forward

1. **A UI surface needs at least a smoke assertion.** "The metric is correct" is
   not "the page renders."
2. **Flag tools that cannot be exercised end-to-end** in the surface count, so
   "11 tools" is not read as "11 working tools."
