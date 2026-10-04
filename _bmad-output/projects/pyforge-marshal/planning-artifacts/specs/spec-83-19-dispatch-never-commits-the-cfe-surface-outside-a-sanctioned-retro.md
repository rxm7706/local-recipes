---
title: "83.19: Dispatch never commits the CFE surface outside a sanctioned retro"
type: 'fix'
created: '2026-10-03'
status: 'in-review'
baseline_revision: '325ca80bfb'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/worktree_checkpoint.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_ruff_format.py
  - src/shared/packages/pyforge-testing-kit/src/pyforge/testing_kit/branch_diff_guard.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Doctor Story 41.1's session edited `.claude/skills/conda-forge-expert/tests/meta/test_spec_surface_check.py`, and the supervisor's auto-checkpoints committed it as `wip: 41.1 (auto-checkpoint)` (59bb1effb3, 121e11b963). Every station's "CFE not replaced" meta-test runs `branch_diff_guard.unsanctioned_commits`, which refuses any branch commit that touches the conda-forge-expert surface unless its subject starts `retro:` / `retro(<scope>):` and the CFE `CHANGELOG.md` moves in the same commit. A `wip:` checkpoint can never satisfy that, so any dispatched story that touches the CFE surface can only land after a history rewrite. The supervisor's own finalize and ruff-format commits have the same problem, and a session's own commit can carry CFE paths too.

**Approach:** Dispatch's own commits (auto-checkpoint, ruff format, finalize, spec-surface reconcile) leave the CFE surface out, using the guards' own pathspec and CHANGELOG path (one owner, shared with `branch_diff_guard`). At finalize, CFE-surface changes are committed once, in a commit whose subject starts `retro(cfe):`, and only when the CFE `CHANGELOG.md` is among them; otherwise verification refuses, naming the Rule 2 requirement. Verification also runs `unsanctioned_commits` over `origin/main..HEAD` and refuses, naming each offending commit, before anything is pushed.

Ledger key: `83-19-dispatch-never-commits-the-cfe-surface-outside-a-sanctioned-retro`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- the dispatch commit path (Stories 34.2, 28.24, 83.9). A defect of shipped behaviour, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a session that edits a file under the CFE surface When the supervisor auto-checkpoints, ruff-formats or finalizes Then none of those commits contains a CFE-surface path
- Given the CFE edit plus a CFE `CHANGELOG.md` entry When the supervisor finalizes Then the CFE paths land in exactly one commit whose subject starts `retro(cfe):`, and `unsanctioned_commits` over the branch is empty
- Given a CFE edit with no CFE `CHANGELOG.md` change When dispatch verifies Then it refuses, naming the Rule 2 requirement, and nothing is pushed
- Given a branch that already carries a commit touching the CFE surface outside a sanctioned retro When dispatch verifies Then it refuses naming that commit
- Given a story that touches no CFE path When dispatch runs Then its commits are unchanged
- Given the exclusion or the verification check removed When its new tests run Then they fail (mutation)

## Boundaries & Constraints

**Always:** Read the CFE pathspec and CHANGELOG path from one owner shared with `branch_diff_guard`; test with a real git repository.

**Never:** Never rewrite a branch's history. Never weaken `unsanctioned_commits` or the station guards. Never touch the CFE surface in this story.

</intent-contract>

## Binding

Parent: Story 34.2 (worktree auto-checkpoints) and Story 28.24 (the supervisor finalize).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-03 (night, last) entry.
Ledger key: `83-19-dispatch-never-commits-the-cfe-surface-outside-a-sanctioned-retro`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 at the operator's request ("yes chain both fixes").

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- 2026-10-04: Implementation review against AC — checkpoint/finalize/ruff paths exclude CFE; verify runs `commit_pending_cfe_retro` then `unsanctioned_commits` (`MRS-GATE-020`). Unit fixtures in `test_dispatch_cfe_commit.py`. Verification: `pyforge-marshal-test`, `pyforge-deps-test`, `lint-types`, `spec_surface_reconcile.py` green.

## Auto Run Result

Status: in-review
Blocking condition: —
