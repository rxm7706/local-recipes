---
title: "83.16: Dispatch finalize commits paths with spaces"
type: 'fix'
created: '2026-10-03'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/vcs_git.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** On 2026-10-03 herald Story 35.1's supervisor could not commit the session's work: `vcs.changed_files` reads `git status --porcelain` line by line, and porcelain v1 wraps a path that contains spaces in double quotes, so the finalize ran `git add -- "\"presentations/pyforge-atlas/project/PyForge Atlas - Infographic Deck.dc.html\""`, git refused the pathspec, and the run stopped with every change uncommitted (`stopped_externally`). The operator committed it by hand. Every path under `presentations/*/project/` has spaces.

**Approach:** Read status with `-z` (NUL-terminated, never quoted; a rename's two paths are separate fields) and parse that, so every consumer of `changed_files` gets the literal path.

Ledger key: `83-16-dispatch-finalize-commits-paths-with-spaces`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- the dispatch finalize (Story 28.24) and the scope check that reads `changed_files`. A defect of shipped behaviour, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given an untracked and a modified file whose paths contain spaces (and one with a non-ASCII character) When `changed_files` runs Then each comes back as its literal path, with no surrounding quotes
- Given such a file in a session's worktree When the supervisor finalizes Then it commits the file and the run does not stop
- Given a rename of a spaced path When `changed_files` runs Then only the new path is returned
- Given the `-z` parsing removed When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Use git's NUL-terminated output; test with a real git repository in `tmp_path`.

**Never:** Never unquote porcelain text by hand.

</intent-contract>

## Binding

Parent: Story 28.24 (the supervisor finalize).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-03 (night, latest) entry.
Ledger key: `83-16-dispatch-finalize-commits-paths-with-spaces`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 at the operator's request.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- No review has run yet.
