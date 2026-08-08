<!-- RECOVERED 2026-08-08 Tier 3 (epics.md-derived Intent + ACs). No session transcript or
     bmad-loop worktree snapshot survived for this story — regenerated from epics.md per
     CLAUDE.md's recovery priority order. -->
---
title: "Story 1-4: Pointer-stub write-back + idempotent re-invocation"
type: "feature"
created: "2026-08-07"
status: "done"
recovery_tier: 3
recovery_source: "epics.md"
recovery_date: "2026-08-08"
---

## Intent
A promoted user-local memory entry is replaced with a pointer stub, and re-running the promotion
command skips already-promoted entries — so promotion is traceable and safe to re-invoke without
duplicating work.

## Acceptance Criteria

- **Given** a promotion proposal from Story 1.3 has been confirmed, **When** the confirmed writes
  execute, **Then** each promoted user-local entry is rewritten to the pointer-stub format
  (`promoted: true` frontmatter + a redirect body naming the promoted file's path and an ISO
  `YYYY-MM-DD` date) — the original body content is not preserved in user-local memory after
  promotion (FR-5).
- **Given** `scribe capture --promote` is re-invoked after a successful promotion, **When** it
  re-scans user-local memory, **Then** entries carrying `promoted: true` are classified
  `already-promoted` and skipped — no re-proposal, no re-write (FR-6).
- **And** nothing outside `.claude/memory/` and the specific promoted user-local entry's
  pointer-stub rewrite is touched by this command (FR-7).

## Delivery Record
Merged via PR #296 (`scribe: Epic 1 close-out — Stories 1.4-1.5 (pointer-stub write-back, real
seed promotion)`), merge commit `75696cc29b`, 2026-08-07T16:25:58Z.
https://github.com/rxm7706/local-recipes/pull/296
