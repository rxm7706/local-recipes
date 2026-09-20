---
title: "Story 1-4: Pointer-stub write-back + idempotent re-invocation"
type: "feature"
created: "2026-08-07"
status: "done"
recovery_tier: 3
recovery_source: "epics.md"
recovery_date: "2026-08-08"
---

<!-- RECOVERED 2026-08-08 Tier 3 (epics.md-derived Intent + ACs). No session transcript or
     bmad-loop worktree snapshot survived for this story — regenerated from epics.md per
     CLAUDE.md's recovery priority order. -->

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

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: pass (this station's own verify suite; backfilled generically, no per-story claim).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `75696cc29b` (2026-08-07, "Merge pull request #296 from rxm7706/scribe/1-4-and-1-5-epic-1-close-out"). Ledger row `1-4-pointer-stub-write-back-idempotent-re-invocation: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `.claude/memory/MEMORY.md`, `.claude/memory/README.md`, `.claude/memory/feedback/bmad-runs-cfe-retro.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/sprint-status-ledger.yaml`, `src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py`, `src/shared/packages/pyforge-scribe/src/pyforge/scribe/promote.py`, `src/shared/packages/pyforge-scribe/tests/unit/test_cli.py`, `src/shared/packages/pyforge-scribe/tests/unit/test_promote.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
