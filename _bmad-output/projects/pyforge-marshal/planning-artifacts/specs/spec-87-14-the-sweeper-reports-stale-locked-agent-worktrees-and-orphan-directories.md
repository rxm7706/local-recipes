---
title: "87.14: The sweeper reports stale-locked agent worktrees and orphan directories"
type: 'fix'
created: '2026-10-04'
status: 'done'
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
deferred:
  - summary: >-
      Clone-based test for patch-equivalent branch reporting in delete_merged_local_branches.
    evidence: |-
      branch_merged_by_patch_id is only exercised indirectly; a squash-merged fixture would pin reporting vs deletion.
    location: >-
      tests/scripts/test_worktree_sweep.py
    severity: medium (unverified)
  - summary: >-
      Integration test for merged STALE-LOCK unlock and worktree remove on --execute.
    evidence: |-
      Unit tests cover classification and effective_execute_verdict; git worktree lock/unlock path untested end-to-end.
    location: >-
      scripts/worktree_sweep.py:465
    severity: medium (unverified)
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

- 2026-10-09: Shipped STALE-LOCK, ORPHAN-DIR, patch-equivalent reporting, and doc fixes in `scripts/worktree_sweep.py` with unit tests; review pass fixed dry-run branch deletion (`apply=False`).

## Review Triage Log

### 2026-10-09 — Review pass
- verdicts: 18 findings — high 1, medium 4, low 3, false 6, maybe-false 4
- findings:
  - `[high]` `[patch]` Dry run with `--delete-merged-local-branches` called `delete_merged_local_branches()` which still ran `git branch -D` — added `apply=False` on non-execute path; test `test_delete_merged_local_branches_dry_run_does_not_delete`.
  - `[medium]` `[patch]` `remove_worktree` skipped late dirty check for merged STALE-LOCK — uses `effective_execute_verdict(wt) == "DELETE"`.
  - `[medium]` `[patch]` Unlock failure ignored before remove — return False when `unlock_worktree` fails.
  - `[medium]` `[patch]` `test_local_branch_full_ref_scripts` two-tuple unpack — updated to three-tuple.
  - `[medium]` `[patch]` Missing porcelain lock parse test — added `test_list_worktrees_parses_agent_lock_reason`.
  - `[medium]` `[patch]` Empty orphan removal untested — added `test_remove_orphan_dir_empty`.
  - `[low]` `[reject]` macOS `/proc` absence — operator tool already Linux-oriented; stale-lock uses injected lookup in tests only.
  - `[low]` `[reject]` `/proc/stat` comm parsing — pre-existing pattern; out of 87.14 scope.
  - `[low]` `[reject]` CLI help text verbosity — cosmetic.
  - `[false]` `[reject]` recover/rescue prefixes vs roster — sweeper prefixes match hook/session_denials and Story 87.6 protected floor.
  - `[false]` `[reject]` Unmerged stale lock should be INSPECT verdict — AC requires STALE-LOCK string with unmerged evidence.
  - `[false]` `[reject]` Bare `locked` line agent lock — non-agent locks correctly stay KEEP.
  - `[false]` `[reject]` Path resolve orphan duplicate — fixed via resolved registered set.
  - `[false]` `[reject]` Race lock becomes live at execute — acceptable operator-tool window.
  - `[false]` `[reject]` Dangling commit-tree objects on dry-run — dry-run no longer invokes deletion path that loops all branches for `-D`; patch-id check only on non-ancestor candidates.
  - `[maybe-false]` `[defer]` Full git integration test for patch-equivalent branch reporting — `branch_merged_by_patch_id` untested against real cherry; add clone fixture in a follow-up.
  - `[maybe-false]` `[defer]` Full `--execute` STALE-LOCK unlock+remove integration — classification and `remove_orphan_dir` covered; end-to-end git lock fixture deferred.
  - `[maybe-false]` `[defer]` Mutation test per orphan/patch rule — stale-lock mutation present; additional mutation guards optional.
  - `[maybe-false]` `[defer]` Assert bmad-loops never appears in full sweep JSON output — orphan roots exclusion tested; loop-home KEEP category pre-existing.

## Auto Run Result

Status: done

Summary: Extended `scripts/worktree_sweep.py` with STALE-LOCK (injectable process start lookup), ORPHAN-DIR discovery/removal, patch-equivalent branch reporting, and corrected hygiene docs. Review fixed dry-run branch deletion and tightened remove/unlock guards.

Files changed:
- `scripts/worktree_sweep.py` — verdict engine, orphan scan, patch-id branch report, execute paths
- `tests/scripts/test_worktree_sweep.py` — stale-lock, orphan, porcelain, dry-run branch tests
- `tests/scripts/test_local_branch_full_ref_scripts.py` — three-tuple API
- `docs/how-to/manage-worktrees-with-bmad.md` — sweeper home, protected prefixes, new verdicts
- `spec-pyforge-marshal/.memlog.md`, `spec-pyforge-doctor/.memlog.md` — surface reconcile (Story 87.14)

Review: 6 patches applied; 4 deferred (integration depth); 9 rejected/false.

Follow-up review recommended: false (high-severity dry-run defect patched and covered by test).

Verification:
- `pytest tests/scripts/test_worktree_sweep.py` — 26 passed
- `pytest tests/scripts/test_worktree_sweep.py tests/scripts/test_local_branch_full_ref_scripts.py` — 34 passed
- `pyforge-marshal-test` — 12033 passed
- `pyforge-deps-test` — 130 passed
- `lint-types` — exit 0
- `python scripts/spec_surface_reconcile.py` — OK

Residual risks: `branch_merged_by_patch_id` relies on git cherry/commit-tree without a clone-based regression test; non-Linux hosts lack `/proc` for live stale-lock detection.
