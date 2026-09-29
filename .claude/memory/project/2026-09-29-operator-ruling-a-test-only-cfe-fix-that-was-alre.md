---
name: "2026-09-29-operator-ruling-a-test-only-cfe-fix-that-was-alre"
description: "2026-09-29 operator ruling: a test-only CFE fix that was already implemented still took the full chain before merging,…"
metadata:
  type: project
---

2026-09-29 operator ruling: a test-only CFE fix that was already implemented still took the full chain before merging, rather than landing as a bare retro(cfe) commit the way PR #1091 (v8.90.1 merge guard, no story) did. PR #1669 (CFE v8.91.1: host-gate tests made hermetic against ambient *_BASE_URL vars such as a Claude Code shell's ANTHROPIC_BASE_URL, which had failed a local pr-preflight while CI stayed green) became spec-pyforge-mason CAP-34 / FR-56 / Epic 24 / Story 24.1, minted at done in the same PR, with SPEC.md rendered by an operator-approved script. AGENTS.md's Dream-first rule names small fixes as not exempt.
