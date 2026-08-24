---
story: 25-3-every-spec-folder-accepts-a-6-11-bmad-spec-update
epic: 25
status: done
completion_path: not-loop-native
date: 2026-08-22
---
# Story 25.3 — every spec folder accepts a 6.11 bmad-spec update

Hand-driven (bmad-build path, operator-verified). Contract: spec-bmad-611-era-alignment CAP-3.

Migration: 8 legacy memlogs gained 6.11 frontmatter (topic marks the migration;
original body byte-intact below it), 14 memlog-less folders gained a
genesis-baseline .memlog.md (S-13.7 pattern: structural bootstrap, no content
claimed reconciled). Verification exceeded the contract: `memlog.py append`
proven against ALL 86 spec folders fleet-wide (0 failures), each verification
append itself the dated migration record. spec-surface reconcile: 0 findings
with no re-stamps (memlog-only movement is not drift by design).
