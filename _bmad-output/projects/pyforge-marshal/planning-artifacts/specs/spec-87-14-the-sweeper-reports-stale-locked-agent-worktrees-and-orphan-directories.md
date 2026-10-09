---
title: "87.14: The sweeper reports stale-locked agent worktrees and orphan directories"
type: 'fix'
created: '2026-10-04'
status: 'in-progress'
baseline_revision: 'a0d4662b82abab4e75cb79e199bd87f7eef1e0e7'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/preserved-work-refs-2026-10-04.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/preserved-work-refs-2026-10-04-review.md
  - scripts/worktree_sweep.py
  - tests/scripts/test_worktree_sweep.py
  - docs/how-to/manage-worktrees-with-bmad.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The sweeper never retires agent working copies.
- **Stale locks.** It keeps every locked worktree (`scripts/worktree_sweep.py:191`). Claude Code locks a subagent worktree to the parent process as `claude agent agent-<id> (pid N start T)`, and the lock outlives the process, so a finished agent's worktree is KEEP forever.
- **Orphan directories.** It reads only registered worktrees. Six empty, unregistered Cursor directories (`~/.cursor/worktrees/*`, `.cursor/worktrees/steward-29-2-personas`) and an empty `.claude/worktrees/.retired-worktrees-20260822` are invisible to it.
- **Patch-equivalent branches.** `--delete-merged-local-branches` treats a patch-id-equivalent branch that is not an ancestor as unmerged, with no report.
- **Stale docs.** The docstring still names `marshal retire` as the logic's home, which the 2026-10-03 ruling reversed. It and the how-to understate the protected list (research § 9).

**Approach:**
- **`STALE-LOCK`.** A worktree whose lock names a pid that is dead, or whose `/proc/<pid>/stat` start time differs from the recorded one (pid reuse), gets the verdict `STALE-LOCK` with the usual merged / unmerged evidence. A merged one becomes eligible for the existing merged-worktree removal; an unmerged one is INSPECT until Story 87.8's preserve exists. A live lock stays KEEP.
- **`ORPHAN-DIR`.** An unregistered directory under `.claude/worktrees/`, `.cursor/worktrees/` or `~/.cursor/worktrees/` is `ORPHAN-DIR`: DELETE when empty, INSPECT otherwise. `~/.bmad-loops/` is never listed.
- **Patch-equivalent branches** are reported, not deleted.
- **Docs.** The docstring and the how-to are corrected.

Unflagged (operator ruling 2026-10-04, review minor 5 and Q16).

Ledger key: `87-14-the-sweeper-reports-stale-locked-agent-worktrees-and-orphan-directories`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- The worktree and branch hygiene tool `scripts/worktree_sweep.py`, made the permanent home by the Phase 3 ruling on DW-HYGIENE-2026-09-05-1 (2026-10-03), and AD-81's rule that agent worktrees are working copies under the sweeper's rules. A defect of shipped tooling, so it is a `fix` with no flag.

## Acceptance Criteria

- Given a worktree locked as `claude agent <id> (pid N start T)` whose pid is dead When the sweep runs Then the verdict is `STALE-LOCK` with merged / unmerged evidence; the same with a live pid whose start time differs from T; with the live process and matching start time, it stays KEEP.
- Given an empty unregistered directory under `.claude/worktrees/`, `.cursor/worktrees/` or `~/.cursor/worktrees/` When `--execute` runs Then it is removed; a non-empty one is INSPECT and kept.
- Given any path under `~/.bmad-loops/` When the sweep runs in any mode Then it is never listed.
- Given `--delete-merged-local-branches` and a merged branch that is patch-id-equivalent to `main` but not an ancestor When it runs Then it is reported and not deleted.
- Given the script's docstring and `docs/how-to/manage-worktrees-with-bmad.md` When they are read Then neither names `marshal retire` as the sweeper's home, and both state the declared protected list.
- Given each rule removed When the tests run Then a test fails (mutation); the process table is injected, never the live one.

## Boundaries & Constraints

**Always:** Dry run by default. Injected process facts in tests.

**Never:** Never remove a non-empty directory or an unmerged worktree here. Never touch `~/.bmad-loops/`. Never kill a process.

</intent-contract>

## Binding

Parent: DW-HYGIENE-2026-09-05-1 (closed 2026-10-03); `spec-pyforge-marshal` CAP-287 / AD-81.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-04 (preserved-work refs) entry.
Research: drafts' Story 87.8, split by the review (minor 5); research § 4 item 8 and § 9.
Ledger key: `87-14-the-sweeper-reports-stale-locked-agent-worktrees-and-orphan-directories`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-04 under the operator's ruling of the same day.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_worktree_sweep.py -q` — expected: pass.
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — expected: pass (the CI `scripts-suite` twin).

## Spec Change Log

- No change yet.

## Review Triage Log

- No review has run yet.
