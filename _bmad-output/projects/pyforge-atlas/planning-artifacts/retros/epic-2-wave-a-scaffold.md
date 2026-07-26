---
doc_type: retrospective
project: pyforge-atlas
epic: 2
wave: A
title: Wave A — nebi Scaffold & Catalog
stories: 3
date: 2026-07-25
basis: reconstructed from tracked evidence (run log, epics.md, PRs #71/#72)
---

# Epic 2 · Wave A — `nebi` Scaffold & Catalog

**Scope:** A1 member scaffold (`1d8c5ab`→`188c6ef`) · A2 data catalog, 73 entries
(`8b04f3b`→`0d6c801`) · A3 `IncrementalParquetDataset` + TTL hook
(`2b53d3e`→`b2565ad`).

## What worked

- **Copying the warden pattern rather than inventing one.** A1 scaffolded as a
  pixi workspace member on the shape warden had already proven. The `kedro-test`
  gate was green on first landing — no bespoke build story to debug.
- **The catalog as a gated artifact.** 73 entries behind `kedro-catalog-check`
  made "all IO is catalog-declared" (CAP-2) enforceable instead of aspirational.
- **A late reviewer round made the gate provably bite.** On A2 the gate was
  written, then a subsequent round demonstrated it actually failed on a bad
  catalog. Writing a gate and proving a gate are different acts.

## What did not

- **Both A2 and A3 needed external review to reach correctness** — Gemini PR-71
  (4 medium, gate hardening) and PR-72 (3 medium, perf + cross-platform). Seven
  medium findings across two stories in the *foundation* wave. The in-loop pair
  passed them; an outside reader did not.
- **Cross-platform defects appeared this early** and kept recurring (Wave G's
  backslash/`as_posix` sweep, the post-merge Gemini pass). A path-handling
  convention fixed in A3 would have pre-empted several later findings.

## Carry-forward

1. **A gate is not done when it is written — it is done when it has been shown to
   fail correctly.** Adopt "prove the gate bites" as an acceptance step.
2. Settle **cross-platform path handling once, in the scaffold wave**. It was
   re-litigated at least three times downstream.
3. The 7 medium findings in the foundation wave are the strongest argument in
   this effort for the independent-review pass that Wave B formalized.
