---
title: 'CAP-4 land heals mechanical and DIRTY PRs (Story 28.20, Epic 28)'
type: 'feature'
created: '2026-09-01'
status: 'done'
updated: '2026-09-02'
review_loop_iteration: 0
followup_review_recommended: false
difficulty: medium
baseline_revision: 20e88e8b0fd1ccd2cc38101691ac72aeb8df71cc
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-drain-self-resolution/SPEC.md
  - docs/dreams/marshal-dependency-aware-dispatch.md
warnings: []
deferred:
  - summary: >-
      Optional spec frontmatter `status:` ready→done union on mechanical land
      conflicts (parent CAP-3 wording) — not in story ACs; defer to a follow-on.
    evidence: |-
      Intent approach mentions optional spec status union; implementation unions
      sprint-status-ledger.yaml only. No AC requires spec status healing.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_heal.py
    severity: medium
---

<intent-contract>

## Intent

**Problem:** PR #985 died on a ledger-only conflict, then `gh pr merge` stayed
`DIRTY` while `merge-tree` was clean. CAP-4 waited for a chat.

**Approach:** Union `sprint-status-ledger.yaml` keys (`done` beats `backlog`);
optionally spec `status:` ready→done. If git is clean and GitHub `mergeable` is
false, advance `main`, retire the PR, resync ledger. Unknown conflicts escalate
with paths named.

## Acceptance Criteria

- Given a PR whose only conflict is the sprint ledger, when land runs, then
  both sides' `done` keys survive, the branch is pushed, merge is retried.
- Given clean `merge-tree` and GitHub `DIRTY`, when land runs, then `main`
  contains the story commits and the PR is not left OPEN+DIRTY.
- Given a conflict in an unknown path, when land runs, then it escalates
  naming that path and does not merge.

## Boundaries & Constraints

**Never:** Merge unknown conflicts. Skip story-caused red CI. `scripts/bmad-switch`.

Ledger key: `28-20-cap-4-land-heals-mechanical-and-dirty-prs`.

</intent-contract>

## Code Map

- `core/dispatch_landing.py` — pure ledger union / mechanical-path classification
- `dispatch_land_heal.py` — heal orchestration (ledger union + local main advance)
- `dispatch_land.py` — wires heal into `execute_dispatch_land` on merge failure
- `ports/vcs.py`, `adapters/vcs_git.py` — `merge_tree_conflict_paths`, `file_text_at_ref`
- `ports/forge.py`, `adapters/forge_gh.py` — `pr_merge_state`, `close_pr`
- `core/findings.py`, `core/verdict.py` — `MRS-DISP-038` unknown-conflict refusal
- Tests: `tests/unit/test_dispatch_land_heal.py`, `tests/unit/test_dispatch_landing.py`

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`

## Review Triage Log

### 2026-09-02 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 0, medium 0, low 1)
- defer: 1: (high 0, medium 1, low 0)
- reject: 0
- addressed_findings:
  - `low` `patch` Remove dead `core/dispatch_land_heal.py` stub (implementation lives in `dispatch_land_heal.py`); left in tree if deletion blocked — no imports reference it.

## Auto Run Result

Status: done

**Summary:** CAP-4 dispatch land now heals mechanical sprint-ledger conflicts via
key union (`done` beats `backlog`) and retries `gh pr merge`. When
`git merge-tree` is clean but GitHub reports `DIRTY`/`CONFLICTING`, land
advances `main` locally, closes the PR, and retires the branch. Unknown conflict
paths emit `MRS-DISP-038` and refuse merge.

**Files changed:**
- `dispatch_land_heal.py` — heal orchestration (ledger union + local main advance)
- `core/dispatch_landing.py` — pure ledger union / mechanical path classification
- `dispatch_land.py` — wire heal after merge failure
- `adapters/vcs_git.py`, `adapters/forge_gh.py` — `merge-tree`, `pr_merge_state`, `close_pr`
- `ports/vcs.py`, `ports/forge.py` — port contracts
- `core/findings.py`, `core/verdict.py` — `MRS-DISP-038`
- `tests/unit/test_dispatch_land_heal.py`, `tests/unit/test_dispatch_landing.py` — AC fixtures
- `tests/meta/test_ad3_ad4_import_linter.py`, `pyproject.toml` — AD-3 seam for heal module
- `spec-28-20-cap-4-land-heals-mechanical-and-dirty-prs.md` — spec closed

**Review findings:** 1 low patch (stub cleanup); 1 medium defer (optional spec
`status:` ready→done union from parent CAP-3 wording — not in story ACs, not
shipped in v1).

**Follow-up review:** false (0 high patches, score 0).

**Verification:** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — 7431 passed, 12 deselected.

**Residual risks:** Local main advance bypasses GitHub merge API when stale
`DIRTY`; gated to clean `merge-tree` and excludes `BLOCKED`/`BEHIND`. Live
GitHub paths not exercised in unit tests. Dead `core/dispatch_land_heal.py`
stub remains if filesystem deletion is blocked — no imports reference it.
