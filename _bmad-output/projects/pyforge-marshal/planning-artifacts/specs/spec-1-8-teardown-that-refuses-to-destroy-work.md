---
title: 'Story 1.8: Teardown that refuses to destroy work'
type: 'feature'
created: '2026-07-31'
status: 'done'
baseline_revision: '7f0bb6b23f65374a52ac5fdbda9862ffbbe8bc38'
final_revision: 'e5b4c38c546381773e8b402ea6220f429f883bab'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `marshal init` (1.4) provisions a loop home but nothing ever removes one -- an operator cleaning up by hand (`rm -rf` + manual branch delete) has no safeguard against deleting a worktree that still holds uncommitted or never-landed work, exactly the kind of loss NFR-6/AD-29 exist to prevent.

**Approach:** A new `marshal teardown <slug> [--force]` command removes the `loop/<slug>` worktree and branch via `VcsPort`, refusing with a registered finding when the home is dirty or the branch's content is not yet captured elsewhere, unless `--force` is given; it also carries a documented, currently-no-op call site for the AD-29 promotion-reachability predicate Epic 4 will wire in.

## Boundaries & Constraints

**Always:**
- `marshal teardown <slug> [--force] [--format text|json]` in `cli/init.py`, mirroring `run_init`/`run_preflight`'s DI seam (`vcs: VcsPort | None`, `fs: FsPort | None`) and pre-I/O slug-shape gate (reuse `policy._is_valid_project_slug` plus the same git-ref-shape guard `run_init`/`run_preflight` already apply) -- `MRS-TEARDOWN-001`.
- **"Unmerged work" is patch-CONTENT equivalence against `main`, never commit-SHA ancestry.** Live-verified during planning: this repo's own bmad-loop landing convention produces single-parent "squash" commits (`7f0bb6b23f`, message "Merge ... into loop/pyforge-marshal", exactly one parent) -- `git merge-base --is-ancestor <branch> main` and `git branch --merged main` both report every successfully-landed story branch as UNMERGED, which would force every ordinary teardown to pass `--force` and train the refusal away (the exact failure AD-29's own F-14 amendment warns about). The correct check: build a detached virtual commit from the branch's current tree, parented on `merge-base(main, branch)`, and compare it against `main` via `git cherry` (patch-id content, not SHA) -- confirmed live to correctly read a squash-merged branch as merged even after `main` has since advanced further. Try the cheap ancestry check first (covers plain-merge/fast-forward workflows for free); fall back to the virtual-commit comparison only when ancestry says no.
- Refusal (`MRS-TEARDOWN-003`, blocking) fires when: the home's working tree has uncommitted changes (`git status --porcelain`, which already covers untracked files -- no separate check needed), OR the branch fails the merged check above, OR the promotion-reachability extension point (below) names anything unreachable -- and `--force` was not supplied. The finding names every condition that triggered it.
- `--force` is one plain boolean overriding all three refusal conditions together, matching NFR-6's "an explicit flag" and the AC's single "unless explicitly forced."
- Once removal is authorized, branch deletion uses `git branch -D` whenever MARSHAL's own merged-check already confirmed safety -- git's own `-d` uses ancestry and would otherwise refuse the identical squash-merged branches this story exists to unblock; worktree removal passes `--force` only on the path where the operator's own `--force` was needed to authorize it (a clean, merged home removes with plain `git worktree remove`, no flag).
- Extend `VcsPort`/`GitVcs` with four methods -- `has_uncommitted_changes(worktree_path)`, `is_branch_merged(repo_root, branch, *, into)`, `remove_worktree(repo_root, home, *, force=False)`, `delete_branch(repo_root, branch, *, force=False)` -- following the module's existing `_run`/`VcsCommandError` conventions exactly (timeout-guarded, no raw subprocess error escapes). The internal `commit-tree` call for the merged-check pins its own author/committer identity and disables GPG signing (`-c user.name=... -c commit.gpgsign=false` etc.) so it never depends on or blocks on the operator's global git config in an unattended context.
- The promotion-reachability extension point is one small, clearly-documented module-level function in `cli/init.py` -- not a new Protocol/port; a repo-wide grep found zero promotion/reachability machinery anywhere yet, and the story's own declared surface is `cli/init.py` + `adapters/vcs_git.py` only. It is called before the refusal decision and hardcoded to return "nothing unreachable" today; Epic 4 replaces only its body, never its call site or contract.
- `MRS-TEARDOWN-001` (malformed slug, pre-I/O) classifies `Verdict.UNEVALUABLE`; `MRS-TEARDOWN-002` (a git operation failed) and `MRS-TEARDOWN-003` (refused: work would be lost) classify `Verdict.ERROR`.
- Teardown calls no `FsPort` write method and never references the canonical Tier-3 store path -- proven by a new AD-11 write-boundary meta-test mirroring `marshal homes`'s own zero-FsPort-writes test, extended to assert the one `VcsPort` mutation (`remove_worktree`'s target) resolves under the home.
- After a successful removal, `git worktree list` carries no entry for `branch` (the AC's literal wording).

**Block If:** none -- every decision here (patch-equivalence over ancestry, one boolean `--force`, the bare-function extension point, "nothing provisioned" as a clean no-op) resolves from git's own documented behavior, this repo's own live-observed merge convention, or AD-29's own already-adjudicated text.

**Never:**
- Never push, force-push, or fetch from any remote (NFR-6) -- entirely local git state.
- Never touch the canonical Tier-3 store (`_bmad-output/projects/<slug>/implementation-artifacts` in the main checkout) -- structurally outside the home, and never referenced by any `FsPort` call this command makes.
- Never implement AD-29's real promotion-reachability predicate (pushed / merged / durable-local-ref routes) -- genuinely Epic 4's scope.
- Never require naming story keys via `--force` (AD-29's "a forced teardown over an unreachable promotion requires the operator to name the story keys being abandoned") -- unreachable while the predicate is a no-op; Epic 4 extends the flag's shape only when it makes the predicate real.
- Never treat "nothing provisioned for this slug" as a failure -- a clean, zero-finding no-op (teardown is a cleanup command, not a precondition-verifying one like `preflight`).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Clean, fully-merged home | No uncommitted changes; branch's content already captured on `main` (plain ancestry OR squash-content match) | Worktree + branch removed, `git worktree list` clean, exit 0, `data.removed=true` | n/a |
| Uncommitted changes, no `--force` | `git status --porcelain` non-empty in the home | Exit non-zero, `MRS-TEARDOWN-003` naming the dirty state; nothing removed | n/a |
| Genuinely unmerged branch, no `--force` | Branch has commits with no equivalent content anywhere on `main` | Exit non-zero, `MRS-TEARDOWN-003` naming the unmerged commits; nothing removed | n/a |
| Either of the above, with `--force` | Same states plus the flag | Worktree removed (`--force`), branch deleted (`-D`), exit 0, `data.forced=true` | n/a |
| Branch squash-merged into `main` (this repo's own convention) | Ancestry check says "no"; virtual-commit `git cherry` check says "yes" | Removed cleanly, NO `--force` required, `data.removed=true` | n/a |
| Nothing provisioned for the slug | No registered worktree for `loop/<slug>`, branch absent | Exit 0, `data.already_removed=true`, zero findings | n/a |
| Malformed slug | e.g. `../escaped`, `/etc` | Exit non-zero, `MRS-TEARDOWN-001`, no I/O attempted | n/a |
| A git operation fails after checks pass | `remove_worktree`/`delete_branch` raises `VcsCommandError` | Exit non-zero, `MRS-TEARDOWN-002` naming the failure | n/a |

</intent-contract>

## Code Map

- `src/pyforge/marshal/ports/vcs.py` -- EDIT: add `has_uncommitted_changes`, `is_branch_merged`, `remove_worktree`, `delete_branch` to `VcsPort`
- `src/pyforge/marshal/adapters/vcs_git.py` -- EDIT: implement the four methods on `GitVcs`; `is_branch_merged` tries cheap ancestry first, falls back to the virtual-commit `git cherry` comparison
- `src/pyforge/marshal/core/findings.py` -- EDIT: register `MRS-TEARDOWN-001..003`, extend module docstring
- `src/pyforge/marshal/core/verdict.py` -- EDIT: classify the three codes, extend module docstring
- `src/pyforge/marshal/cli/init.py` -- EDIT: `add_teardown_subparser`/`run_teardown`/`_render_text_teardown`/`_emit_teardown`; the `_unreachable_promotions(repo_root, branch) -> tuple[str, ...]` AD-29 stub; extend module docstring's registry paragraph
- `src/pyforge/marshal/cli/main.py` -- EDIT: wire `init_cli.add_teardown_subparser(subparsers)`
- `tests/unit/test_vcs_git.py` -- EXTEND: real-git tests for the four new methods, including a squash-merge fixture reproducing this repo's own convention
- `tests/unit/test_init.py` -- EXTEND: `FakeVcs` gains the four methods + `fail_*` hooks; CLI-layer tests for `run_teardown` covering the I/O matrix
- `tests/meta/test_ad11_write_boundary.py` -- EXTEND: a new teardown test proving zero `FsPort` writes and the one `VcsPort` removal target resolves under the home

## Tasks & Acceptance

**Execution:**
- [x] `ports/vcs.py` -- extend `VcsPort` with the four new methods
- [x] `adapters/vcs_git.py` -- implement them on `GitVcs`, including the ancestry-then-content-equivalence fallback for `is_branch_merged`
- [x] `core/findings.py`, `core/verdict.py` -- register + classify `MRS-TEARDOWN-001..003`
- [x] `cli/init.py` -- `add_teardown_subparser`/`run_teardown`, the AD-29 stub, refusal + forced-removal logic
- [x] `cli/main.py` -- wire the new subparser
- [x] `tests/unit/test_vcs_git.py` -- cover the four new `GitVcs` methods, incl. the squash-merge scenario
- [x] `tests/unit/test_init.py` -- cover the full I/O matrix at the CLI/envelope layer
- [x] `tests/meta/test_ad11_write_boundary.py` -- add the teardown write-boundary test

**Acceptance Criteria:**
- Given a provisioned, clean loop home, when `marshal teardown <slug>` runs, then the worktree and branch are removed and `git worktree list` is clean afterward
- Given a home with uncommitted changes or a genuinely unmerged branch, when `marshal teardown <slug>` runs without `--force`, then it exits non-zero with `MRS-TEARDOWN-003` and removes nothing
- Given the same state, when `marshal teardown <slug> --force` runs, then the worktree and branch are removed
- Given a branch landed via this repo's own squash-merge convention (single-parent merge commit, tip not an ancestor of `main`), when `marshal teardown <slug>` runs, then it is NOT treated as unmerged and removes without requiring `--force`
- Given no loop home is provisioned for the slug, when `marshal teardown <slug>` runs, then it exits 0 reporting `already_removed` with zero findings
- Given any teardown invocation, when it completes, then no `FsPort` write occurred and the canonical Tier-3 store was never referenced

## Spec Change Log

## Review Triage Log

### 2026-07-31 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 12: (high 3, medium 4, low 5)
- defer: 3: (medium 1, low 2)
- reject: 4: (low 4)
- addressed_findings:
  - `[high]` `[patch]` `has_uncommitted_changes` ran plain `git status --porcelain` with no explicit config pin, so an operator's `status.showUntrackedFiles=no` (local or global) would hide untracked files from the dirty check, silently defeating the refusal NFR-6 exists to drive. Added `-c status.showUntrackedFiles=normal` to the call, mirroring `is_branch_merged`'s own explicit-config-pin discipline. Test: `test_has_uncommitted_changes_true_for_untracked_file_despite_local_config_hiding_it`.
  - `[high]` `[patch]` `run_teardown` passed the merely COMPUTED `home` to `vcs.remove_worktree`, not git's own registered `worktree_path` (the dirty-check just above it correctly used `worktree_path`) -- on a genuine mismatch (e.g. `BMAD_LOOP_HOME_ROOT` changed since provisioning), removal would target the wrong path. Fixed to pass `worktree_path`, mirroring `run_init`'s own precedent of trusting git's truth over a computed path. Test: `test_teardown_remove_worktree_uses_the_git_registered_path_not_the_computed_home`.
  - `[high]` `[patch]` The "nothing provisioned" no-op path trusted git's registry alone and never checked whether `home` still existed on disk -- a worktree deregistered by a prior partial/failed removal (this repo's own documented failure class) with real, possibly-uncommitted files left behind was silently reported as fully cleaned up (`already_removed: true`). Added a read-only `fs.is_dir(home)` check; a leftover directory now reports `MRS-TEARDOWN-002` naming it instead. Test: `test_teardown_leftover_directory_with_nothing_registered_is_not_already_removed`.
  - `[medium]` `[patch]` `is_branch_merged`'s content-equivalence fallback used `all(line.startswith("-") ...)` over `git cherry`'s output, which is vacuously `True` for zero lines -- a safety gate defaulting to "safe to delete" on an unproven, never-observed shape. Changed to raise `VcsCommandError` when `git cherry` produces no lines instead of silently reporting "merged". Test: `test_is_branch_merged_raises_on_empty_cherry_output`.
  - `[medium]` `[patch]` When `delete_branch` failed AFTER `remove_worktree` had already succeeded, the emitted `MRS-TEARDOWN-002` was raw git stderr with no mention the worktree was already gone, leaving the operator to infer recovery state. The message now says so explicitly. Test: extended `test_teardown_delete_branch_failure_reports_mrs_teardown_002`.
  - `[medium]` `[patch]` `remove_worktree` used the default 30s query timeout rather than `_GIT_CHECKOUT_TIMEOUT_S` (600s) -- removal deletes the SAME full tree `add_worktree` populates, and this module's own existing comment reasons about large-repo cold-cache checkouts exceeding 30s for that symmetric case. Applied the same extended timeout.
  - `[medium]` `[patch]` `has_uncommitted_changes` was called unconditionally on a registered worktree; a directory deleted by hand (git still registers it) made the call raise, short-circuiting to `MRS-TEARDOWN-002` BEFORE the refusal/`--force` branch was ever reached -- `--force` could not help. Added an `fs.is_dir(worktree_path)` guard (mirrors `run_init`'s/`run_homes`'s own stale-worktree-directory pattern) that skips the dirty check when the directory is missing; git's own `worktree remove` cleans up the stale registration without needing `--force` (confirmed live). Test: `test_teardown_worktree_directory_missing_skips_dirty_check_and_removes`.
  - `[low]` `[patch]` The AD-29 promotion-reachability refusal branch (`if unreachable: reasons.append(...)`) had zero test coverage since `_unreachable_promotions` is a hardcoded no-op -- the message-formatting path would fire in production for the first time only once Epic 4 makes the predicate real. Added a monkeypatch-based test proving the wiring (refusal AND `--force` override) works today. Test: `test_teardown_ad29_unreachable_promotion_blocks_without_force`.
  - `[low]` `[patch]` An inline comment in `run_teardown` and a docstring paragraph in `core/findings.py` both claimed `run_preflight` already applies the same `.`/`..`/`.lock` git-ref-shape guard `run_init` and `run_teardown` do -- it doesn't (verified by inspection: `run_preflight`'s slug gate calls only `policy._is_valid_project_slug`). Corrected both to state the guard is shared with `run_init` only, and logged `run_preflight`'s own gap as deferred work (see below) rather than fixed here (out of this story's surface).
  - `[low]` `[patch]` `--force`'s help text named only two of the three conditions it overrides (uncommitted changes, unmerged branch), omitting the AD-29 promotion-reachability stub -- harmless today but already stale the day Epic 4 activates it. Updated the help text to name all three.
  - `[low]` `[patch]` The module docstring's and an inline comment's "it performs no write of its own at all" / "writes nothing at all" claims overclaimed: `is_branch_merged`'s fallback DOES create one internal git object via `commit-tree` (detached, unreferenced, GC-eligible) -- a write in the general sense, outside AD-11's FsPort/tracked-artifact meaning of the term but not accurately described as "no write". Reworded both to scope the claim correctly.
  - `[low]` `[patch]` The module docstring said "Story 1.8 adds a FOURTH command in this same module" -- config/init/homes/preflight are already four, making teardown the FIFTH (self-caught during verification, not reviewer-reported). Corrected the count.
- deferred: 3 -- `run_preflight` (Story 1.7) genuinely lacks the git-ref-shape guard the comment-fix above stopped overclaiming (pre-existing gap, this story's surface does not include `run_preflight`); `run_teardown`'s unconditional `delete_branch(..., force=True)` re-verifies nothing between `is_branch_merged`'s read and the delete, a narrow TOCTOU window under an out-of-scope concurrent-writer scenario; `is_branch_merged`'s `into="main"` is hardcoded with no policy override, inheriting (not introducing) Story 1.4's own `add_worktree(..., base="main")` precedent -- all three logged to `deferred-work.md` with full evidence.
- rejected as scope creep, already covered, or unreachable in practice: extracting a shared helper for the (now two, not three) copies of the git-ref-shape guard -- a design preference, not a defect, now that the false "three copies" premise is corrected; a preview of what `--force` would destroy before committing -- not in the story's AC, meaningful scope creep beyond Effort:S; "no documented resume story for an interrupted two-step removal" -- the branch-only reconciliation path already exists and is already tested (`test_teardown_branch_only_no_worktree_deletes_just_the_branch`), this was a prose-only nit; a repo-bootstrap/unborn-`main` edge case -- unreachable in practice since `marshal init` itself already requires `main` to carry the target project's committed planning-artifacts before a loop home can exist.

### 2026-07-31 — Follow-up review pass
- intent_gap: 0
- bad_spec: 0
- patch: 8: (high 0, medium 3, low 5)
- defer: 3: (high 2, medium 1)
- reject: 3: (low 3)
- addressed_findings:
  - `[medium]` `[patch]` A `VcsCommandError` from the dirty or merged probe returned `MRS-TEARDOWN-002` BEFORE the `--force` branch was ever consulted -- `--force` could not carry past a damaged-but-present worktree (corrupt `.git` gitdir pointer, unresolvable `refs/heads/main`), the exact states teardown is most needed for, and the same dead-end class the first pass's missing-directory fix removed for one variant. Under `--force` the probe's answer cannot change the outcome, so its failure is now absorbed as one more named forced-past reason; without `--force` it still blocks as 002. Tests: `test_teardown_dirty_probe_error_with_force_is_absorbed_and_removal_proceeds`, `test_teardown_merged_probe_error_with_force_is_absorbed_and_removal_proceeds`.
  - `[medium]` `[patch]` `is_branch_merged`'s `git cherry` call ran under the default 30s query timeout although it computes a patch-id (full diff) for every commit on `main` since the merge base -- history-proportional work on a large repo where loop homes routinely fork long before teardown; a SIGKILL mid-scan would surface as a spurious, non-force-overridable `MRS-TEARDOWN-002`. Applied `_GIT_CHECKOUT_TIMEOUT_S`, the same large-repo reasoning `remove_worktree`'s own extended timeout already documents.
  - `[medium]` `[patch]` The leftover-on-disk guard ran only in the NOTHING-registered arm -- in the branch-only state (a prior partial removal deregistered the worktree but left real files AND the branch behind, this repo's own documented failure class) teardown deleted the branch and reported `removed: true` while the unverified leftover sat there. The guard now covers every worktree-deregistered state. Test: `test_teardown_branch_only_with_leftover_on_disk_refuses_instead_of_deleting_the_branch`.
  - `[low]` `[patch]` A net-zero branch (a change plus its revert: tree identical to the merge base's) was spuriously refused as "not yet safely captured on main" -- the virtual commit's diff is empty and `git cherry` reports an empty-diff commit as `+` (live-verified during this pass), forcing `--force` for a branch with nothing to lose. `is_branch_merged` now answers by tree equality before building the virtual commit. Test: `test_is_branch_merged_true_for_a_net_zero_branch`.
  - `[low]` `[patch]` The leftover guard probed `fs.is_dir`, so a leftover regular FILE at the home path slipped through as `already_removed: true` -- the same silently-claimed-cleanup defect the guard exists to prevent, one file-type away. Switched to the port's existing `fs.exists` (Story 1.6 surface). Test: `test_teardown_leftover_plain_file_with_nothing_registered_is_not_already_removed`.
  - `[low]` `[patch]` The `MRS-TEARDOWN-003` headline named the merely COMPUTED `home` even in the moved-home case where the dirty check and the removal both operate on git's REGISTERED path -- the finding directed the operator to inspect a directory that is not the one being checked or removed. The message now names the registered path when one exists. Test: `test_teardown_refusal_message_names_the_git_registered_path`.
  - `[low]` `[patch]` The AD-11 teardown meta-test's docstrings claimed the one `VcsPort` write "resolves under the provisioned home" universally, while the same diff's own moved-home unit test proves the code deliberately removes git's registered path outside any home root -- a guard asserting a containment property the code does not have. Scoped both docstrings to the provisioned-in-place case the guard constructs, cross-referencing the moved-home test; assertions unchanged.
  - `[low]` `[patch]` `core/findings.py`'s docstring described `MRS-TEARDOWN-002` as strictly "a git operation failed", but the leftover-on-disk guard emits it when NO git operation failed (an on-disk state git no longer accounts for). Extended the docstring to cover that case.
- deferred: 3 -- `marshal teardown` cannot see gitignored content (`git status --porcelain` omits it; unforced `git worktree remove` deletes it -- run state, unpromoted Tier-3 story specs; live-verified against both a scratch repo and the real fleet home), not naively patchable since every home carries gitignored content and a blanket refusal would train the gate away -- the designed home for the fix is Epic 4's AD-29 `_unreachable_promotions` wiring; nested REGISTERED run worktrees inside a home are silently destroyed (uncommitted nested work lost, prunable orphan registrations left; six of eight fleet homes carry them), needs a designed per-nested-worktree policy; no liveness guard for an actively-executing run (footprint entirely gitignored, both probes pass mid-run), needs a liveness mechanism design. All three logged to `deferred-work.md` with full evidence.
- rejected as noise, safe-by-design, or spec-adjudicated: "patch-CONTENT equivalence is really patch-TEXT equivalence" (conflict-resolved squashes refuse) -- the mechanism and its terminology are the spec's own adjudicated text, and the failure direction is safe (refuse, `--force` available); `loop/<slug>` checked out in the MAIN working tree -- git itself refuses the removal with an accurate message, no loss; a locked worktree needs `git worktree remove --force --force` -- a worktree lock is deliberate extra protection someone explicitly added, and auto-double-forcing through it on a single marshal `--force` would be a safety regression (git's error names the lock; `git worktree unlock` is the documented path).

## Design Notes

**Why content-equivalence, not ancestry, for "unmerged."** Verified live during planning against a throwaway repo reproducing this repo's own squash-merge pattern (parent count of `7f0bb6b23f` == 1): `git merge-base --is-ancestor` and `git branch --merged` both say "not merged" for a branch whose full content is already safely on `main`. Using either as the refusal predicate would make `--force` mandatory on every normal teardown -- exactly the "trained-away safety gate" AD-29's own F-14 amendment describes for the promotion case. The fix (a detached virtual commit -- the branch's tree, parented on the merge-base -- compared via `git cherry`'s patch-id matching) was confirmed live to correctly read the squash-merged branch as merged, even after further unrelated commits landed on `main`.

**Why `branch -D` even on the non-forced path.** Once Marshal's own content-equivalence check says a branch is safe, using plain `git branch -d` would still be refused by git's own ancestry-only heuristic for the identical squash-merged case -- surfacing a spurious operation failure for something already proven safe. Marshal's own more-accurate check is what authorizes the `-D`, not the operator's `--force` (which exists solely to override a *real* refusal).

**Why the extension point is a bare function, not a new port.** The story's declared surface is `cli/init.py` + `adapters/vcs_git.py` only, and a repo-wide grep for `promotion`/`reachability` turned up zero existing machinery. A documented no-op function co-located with its one call site is the minimum that satisfies "a documented extension point exists" without speculatively designing Epic 4's real interface today.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expected: all unit + meta tests pass
- `pixi run -e pyforge-marshal marshal teardown <slug>` against a real provisioned loop home -- expected: worktree + branch removed, `git worktree list` clean
- `pixi run -e pyforge-marshal marshal teardown <slug>` a second time -- expected: exit 0, `already_removed: true`, no error

## Auto Run Result

**Status:** done (follow-up review pass, 2026-07-31).

**Summary:** Independent follow-up review of the already-implemented `marshal teardown` (baseline `7f0bb6b23f` → `38d817d681`), run because the first pass set `followup_review_recommended: true`. Blind Hunter + Edge Case Hunter fan-out produced 14 deduplicated findings: 8 patched, 3 deferred to the ledger, 3 rejected. No intent gaps, no spec deviations -- the code faithfully implements the contract; every patched item hardens the implementation within it.

**Files changed (this pass, commit `e5b4c38c`):**
- `adapters/vcs_git.py` -- net-zero tree-equality shortcut in `is_branch_merged` (empty-diff virtual commits read as `+` by `git cherry`, live-verified); `git cherry` moved to the extended timeout
- `cli/init.py` -- `--force` absorbs dirty/merged probe failures as named forced-past reasons; leftover-on-disk guard hoisted to cover the branch-only state and probes `fs.exists`; `MRS-TEARDOWN-003` names git's registered path; docstring updates
- `core/findings.py` -- `MRS-TEARDOWN-002` docstring covers its leftover-state emission
- `tests/meta/test_ad11_write_boundary.py` -- containment claim scoped to the provisioned-in-place case (assertions unchanged)
- `tests/unit/test_init.py` -- 5 new CLI-layer tests covering every patched behavior
- `tests/unit/test_vcs_git.py` -- real-git net-zero-branch regression test

**Review findings breakdown:** 8 patched (3 medium, 5 low -- see triage log); 3 deferred with full evidence to `deferred-work.md` as NEW entries (gitignored-content blindness, nested registered run worktrees, no liveness guard -- all high/medium, all pointing at Epic 4's AD-29 `_unreachable_promotions` wiring or a designed policy beyond this Effort:S contract); 3 rejected (spec-adjudicated mechanism wording, main-worktree checkout, locked-worktree double-force).

**Follow-up review recommendation:** false. This pass's patches are narrower than the first pass's (no high-severity, each a few lines, all live-verified and regression-tested); the remaining high-consequence items are deferred design work a further review pass would only re-find, not fix.

**Verification:** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- 761 passed; slow/integration subset (`-m slow`, real-git end-to-end incl. the squash-merge headline scenario) -- 8 passed. Net-zero `git cherry` behavior re-verified against a live scratch repo before patching.

**Residual risks:** the three deferred items are real, evidence-backed gaps in what teardown's refusal model can SEE (gitignored content, nested run worktrees, run liveness) -- until Epic 4 wires the AD-29 predicate, `marshal teardown` on a fleet home with unpromoted gitignored work removes it without refusal exactly as raw `git worktree remove` would; operators should prefer `marshal homes` + manual inspection before tearing down a home that hosted recent runs. The delete-branch TOCTOU and hardcoded `into="main"` entries from the first pass remain open in the ledger.

