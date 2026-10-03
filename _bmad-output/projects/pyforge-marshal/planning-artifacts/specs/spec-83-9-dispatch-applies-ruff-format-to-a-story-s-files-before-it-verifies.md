---
title: "83.9: Dispatch applies ruff format to a story's files before it verifies"
type: 'fix'
created: '2026-10-03'
status: 'done'
baseline_revision: 'aed01eccf995261125cccccdbbe65f3c6a8d2b8c'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
  - scripts/lint_types.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** On 2026-10-02 and 2026-10-03 every Cursor dispatch session of marshal Epics 83 and 66 and Story 84.1 (83.2, 83.3, 83.6, 66.2, 84.1, among others) finished its work and was refused at verification on `pixi run --frozen -e pyforge-guild lint-types`, most often on `ruff format` alone, which a machine can apply. Each was fixed by hand and re-dispatched for land-only. The sessions reported the check green; a session's report cannot be the guard.

**Approach:** After the session ends and before verification runs, dispatch runs `ruff format` (the same per-package invocation `scripts/lint_types.py ruff-format --fix` uses) in the story worktree, keeps the reformatting only for files the story itself changed, commits it to the story branch as a separate commit, and journals the files it reformatted. Everything else in verification is unchanged: a mypy or `ruff check` failure still refuses the landing.

Ledger key: `83-9-dispatch-applies-ruff-format-to-a-story-s-files-before-it-verifies`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- Story 28.20 / Story 79.2 (dispatch verification and the derived `lint-types` command). A defect of the dispatch flow, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a finished session whose changed `.py` files are not `ruff format`-clean When dispatch verifies Then it first reformats those files, commits them to the story branch, journals the file list, and `lint-types` no longer refuses on formatting
- Given a session whose files are already formatted When dispatch verifies Then no commit is made and nothing is journaled
- Given `ruff format` would also rewrite a file the story did not change When dispatch reformats Then that file is left exactly as it was (not staged, not committed)
- Given a mypy or `ruff check` error When dispatch verifies Then verification still refuses on `lint-types` as today
- Given the pre-verification format step removed When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Fix the defect where dispatch verification runs, and pin it with a test that fails without the fix. Use each package's own `ruff` configuration (the per-package invocation in `scripts/lint_types.py`).

**Never:** Never reformat or commit a file the story did not change. Never relax or skip any verification command. Never apply `ruff check --fix` or any non-formatting rewrite. Never format in the primary checkout.

</intent-contract>

## Binding

Parent: Story 28.20 / Story 79.2 (dispatch verification and the derived `lint-types` command).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-03 (later) entry.
Ledger key: `83-9-dispatch-applies-ruff-format-to-a-story-s-files-before-it-verifies`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 at the operator's request (the tenth defect: every Cursor session refused on formatting).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

### 2026-10-03 — Review pass
- verdicts: 1 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings:
  - `[reject]` `[reject]` CAP-4 land-only path formats without journaling — supervisor path journals; CAP-4 has no run journal; intent satisfied on primary verify path.

## Auto Run Result

Status: done

Summary: Before independent verification, dispatch runs per-package `ruff format` on story-scoped `.py` files (vs `origin/main`), commits reformats on the story branch, and the supervisor journals `dispatch-ruff-format` when paths change.

Files changed:
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_ruff_format.py` — core format+commit logic
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py` — verify entrypoint
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py` — journal before verify
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` — CAP-4 verify hook
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch.py` — journal kind constant
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_ruff_format.py` — unit + mutation tests

Review: 0 patches applied; 0 deferred; 1 rejected (CAP-4 journaling scope).

Follow-up review recommended: false

Verification:
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — 10865 passed
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — 130 passed
- `pixi run --frozen -e pyforge-guild lint-types` — exit 0
- `python scripts/spec_surface_reconcile.py` — OK

Residual risk: non-supervisor verify entrypoints format and commit but do not journal (land-only CAP-4).
