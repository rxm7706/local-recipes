---
title: Orphan detection with review-gated cleanup
type: feature
created: '2026-08-23'
status: ready
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: 528da5567b
---

<intent-contract>

## Intent

**Problem:** After chain regeneration (21.2), artifacts the new chain no longer references (old spec folders, replaced epics, dream-deleted refs) need naming and review-gated cleanup — never silent delete (FR-192 CAP-4; Q3 resolved 2026-08-23).

**Approach:** After regen, write orphan manifest (`orphans.json` + `orphans.md` under `.chain-regen/<run-id>/`) listing candidates with paths + reasons. Default: unstaged working-tree only (no `git add`, no disk delete). Optional `--stage` stages regenerated paths and orphan deletions without commit. `--apply-orphans` performs disk deletes only on explicit operator action. Never auto-commit/push. Deps: 21.2 done; Q3 resolved. Do not implement CAP-5 param polish (21.5) beyond these flags.

## Acceptance Criteria

- Consolidation/regen run produces named orphan candidate list + human-readable report.
- Default leaves orphans on disk and all changes unstaged.
- `--stage` stages regenerated paths and orphan rm paths without commit.
- `--apply-orphans` deletes orphan files only when explicitly passed; still no commit.
- Nothing deleted, committed, or pushed without explicit operator action.
- Does not implement Story 21.5 beyond these flags.

## Boundaries & Constraints

**Never:** Auto-delete without `--apply-orphans`. Never auto-commit/push. Finalize marshal ledger only.

</intent-contract>

## Code Map

- Parent: `spec-fleet-chain-completeness/SPEC.md` (CAP-4; Q3 resolved)
- Extends: `core/chain_regen.py` phase-8 orphan report → stage/apply gates
- Tests: manifest contents; default no-delete; `--stage` index-only; `--apply-orphans` disk delete; no-commit

## Verification

- `pixi run -e pyforge-marshal pyforge-marshal-test` green
- Fixture: orphaned spec folder detected, survives default run, removed only with `--apply-orphans`
