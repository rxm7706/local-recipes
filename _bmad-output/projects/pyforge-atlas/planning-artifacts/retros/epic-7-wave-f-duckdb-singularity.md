---
doc_type: retrospective
project: pyforge-atlas
epic: 7
wave: F
title: Wave F — The DuckDB Singularity
stories: 4
date: 2026-07-25
basis: reconstructed from tracked evidence (run log, epics.md, PRs #92–#95)
---

# Epic 7 · Wave F — The DuckDB Singularity

**Scope:** F1 DuckDB-singularity AST gate (`13a5ce3`, #92) · F2 data-validation
hook + inline Pandera contracts, FR-10 (`1e122c8`, #93) · F3 DuckDB `vss` vector
similarity RAG, FR-5 (`df58bfc`, `2acfeaa`, #94) · F4 dependency-hygiene node +
unified CI policy gate, FR-16/18/10 (`fd8e1c9`, #95).

## What worked

- **F1 enforced an architectural decision in the AST, not in review.** "One
  engine" (CAP-6) became a gate that fails on a competing engine import. This is
  the strongest pattern in the whole effort: *a decision nobody can quietly
  violate*. Contrast Wave B's `AD-13`, which was a decision re-implemented per
  site and violated twice.
- **F3 delivered vector search without a vector database.** DuckDB `vss` kept the
  one-engine constraint intact where the obvious move was to add a dependency.
- **F2's contracts are inline with the data**, so validation travels with the
  dataset instead of living in a separate suite that can drift.
- **F4 unified the policy gate** rather than adding a fifth bespoke check.

## What did not

- **The singularity is unbenchmarked.** F1's attended benchmark was deferred
  (`DW-F1-1`), so the *performance* premise of one-engine — the reason to accept
  the constraint — is asserted, not measured. The gate proves conformance, not
  that conformance was worth it.
- **F3 shipped with the production retriever deferred** (later `DC-6`), so the
  RAG path is proven structurally and unproven at production settings.
- **The F3 review finding was `LOW` and defensive** (`$`→`\Z` in an identifier
  regex). Correct, but it suggests the reviewer found little to grip on — a
  4-story wave with one low finding is either very clean or under-probed.

## Carry-forward

1. **AST-level enforcement is the best tool in this effort for a decision that
   must not erode.** Use it wherever a constraint is architectural.
2. **A constraint accepted for a performance reason owes a benchmark.** Otherwise
   the constraint outlives its justification unexamined.
3. When an adversarial pass returns only defensive LOW findings, **check whether
   the reviewer had enough context to bite.**
