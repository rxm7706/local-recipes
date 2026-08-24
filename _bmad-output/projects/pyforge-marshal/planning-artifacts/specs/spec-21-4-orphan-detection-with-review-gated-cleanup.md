---
title: Orphan detection with review-gated cleanup
type: feature
created: '2026-08-23'
status: done
updated: '2026-08-24'
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

## Auto Run Result

Status: done

Summary: Implemented CAP-4 orphan detection with review-gated cleanup for `marshal planning chain-regenerate`. Orphan manifest (`orphans.json` + `orphans.md`) is always written. Default leaves orphans on disk and all changes unstaged. `--apply-orphans` deletes orphaned `kind=spec` units only (never `epics.md`). `--stage` indexes regenerated planning paths and orphan deletions via `adapters.vcs_git.stage_index_paths` without committing. Never auto-commits/pushes. Story 21.5 param polish not implemented beyond these flags.

Files changed:
- `core/chain_regen.py` — real `apply_orphans_hook` / `stage_hook` + injectable stager (AD-4)
- `adapters/vcs_git.py` — `stage_index_paths` (git add / add -u, no commit)
- `cli/planning.py` — CAP-4 flag help + stager wiring
- `tests/unit/test_chain_regen.py` — default/apply/stage/no-commit coverage

Verification: `pixi run -e pyforge-marshal pyforge-marshal-test` green; `test_chain_regen.py` → 29 passed.

Admin merge: PR https://github.com/rxm7706/local-recipes/pull/709 merge SHA `584818efcb8881b51e71ac2b67128ca9a770db89` via `gh pr merge --merge --admin` (GitHub Actions billing blocks CI; local tests green).
