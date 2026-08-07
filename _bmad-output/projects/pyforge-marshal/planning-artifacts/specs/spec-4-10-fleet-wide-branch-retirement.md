---
title: 'Fleet-wide branch retirement'
type: 'feature'
created: '2026-08-06'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md']
warnings: []
baseline_revision: '98a32785e3877cd9bf23cf70737233be1ab8b5af'
---

<intent-contract>

## Intent

**Problem:** every branch this package's own commands create — bmad-loop's own per-story, worktree-isolated task branches most of all — accumulates with no owner ever proposing "this one is safe to delete now." `marshal land`/`land-story` (Stories 4.8/4.3) already retire the ONE station branch (`loop/<slug>`) their own wave landed through, but a project running bmad-loop's worktree-isolated mode mints a SEPARATE branch per story task (`ports/harness.py::TaskPhaseSnapshot.branch`, Story 3.8) — none of Marshal's own shipped commands ever proposes deleting those. FR-63/AD-47 close this gap: a fleet-wide sweep across every project's loop home that proposes exactly the branches it can PROVE are safe — never guesses, never defaults to delete on ambiguous evidence.

**Approach:** `cli/retire.py` (NEW top-level `marshal retire` command, no required project argument — sweeps every project the fleet currently has a loop home for, discovered the SAME way `marshal homes` already does). For each project: read the most recent bmad-loop run's `TaskPhaseSnapshot` tuple (the SAME `_latest_run_dir`/`_resolve_harness_run_id_for_resume`/`HarnessPort.run_status_snapshot` read primitives `cli/deploy.py::_gather_claimed_commits` already established for Story 4.5 — reused, not reimplemented, inheriting that same story's own accepted "most recent run only" scope decision), which carries `story_key`/`phase`/`commit_sha`/`branch` for every task the harness ran. `core/retire.py` holds the PURE evidence-classification logic (AD-4: no I/O) that turns three independently-gathered facts per candidate branch into a propose/refuse decision: (1) `VcsPort.is_branch_merged` (Story 1.8's own patch-id-based merged check, reused verbatim — the AC's own "reachable... by patch-id" wording is this method's own documented behavior almost word-for-word), (2) `VcsPort.worktree_path_for_branch(...) is None` ("no live worktree currently checked out on this branch" — the harness-neutral, git-only proxy for "its run concluded"), (3) `TaskPhaseSnapshot.phase == "done"` and `.commit_sha is not None` (the harness's OWN recorded terminus and merge sha for that story — no re-derivation from commit-subject matching needed, since Story 3.8 already added `commit_sha`/`branch` to this exact type for precisely this kind of downstream consumer). `loop/*` branches and `rescue/*` tags are excluded BEFORE evidence-gathering even runs against them — structural, never policy-configurable. Dry-run by default (report-only); an explicit `--execute` flag performs the actual `VcsPort.delete_branch` calls — never a `--force` override, since every proposal is, by construction, already provably safe (mirrors `marshal teardown`'s own NFR-6 "no destructive default" discipline, though via a different mechanism: teardown refuses an unsafe remove and needs `--force` to override it; retire never proposes an unsafe one to begin with, so there is nothing to override).

## Boundaries & Constraints

**Always:**
- **`cli/retire.py` is a NEW top-level subcommand** (`marshal retire`, wired in `cli/main.py` alongside `config`/`init`/`gate`/`deploy`/`factory`/`land`). No required positional argument — it sweeps the WHOLE fleet by default (a `--project <slug>` flag scopes it to one project, matching every other command's own precedent).
- **Fleet enumeration reuses `VcsPort.list_worktrees`** (Story 1.6, the SAME primitive `marshal homes` already uses): every entry whose `.branch` starts with `"loop/"` names one project's slug (`branch.removeprefix("loop/")`). A project with no currently-attached loop-home worktree is out of scope for this sweep (matches `marshal homes`'s own established fleet-membership definition — no new one invented).
- **Per-project evidence gathering reuses `_latest_run_dir`/`_resolve_harness_run_id_for_resume`/`HarnessPort.run_status_snapshot`** (Story 4.5's own established read sequence, imported from `cli/deploy.py` the SAME way `cli/land.py` already imports that module's private helpers) — never a second, independently-drifting read path. `RunStatusSnapshot.tasks` (`TaskPhaseSnapshot`, Story 3.8) is the per-task source: `story_key` (bmad-loop-native spelling, normalized via `core.identity.normalize` at the CLI boundary — a task whose key does not normalize is skipped, mirroring `_gather_claimed_commits`'s own established skip-invalid convention), `phase`, `commit_sha`, `branch` (`""` when the task never ran worktree-isolated — skipped, nothing to retire).
- **Three independently-gathered facts per candidate branch, each provable or the branch is refused:**
  1. `merged_by_patch_id: bool` — `VcsPort.is_branch_merged(repo_root, branch, into=base)` (`base` = `effective.landing_base_branch.value`, Story 4.7's policy key, reused).
  2. `run_concluded: bool` — `VcsPort.worktree_path_for_branch(repo_root, branch) is None`.
  3. `story_done_with_sha: str | None` — `snapshot.commit_sha` when `snapshot.phase == "done"` (the exact literal `supervisor/durability.py::_DONE_PHASE` already uses — reused, not re-spelled), else `None`.
  A branch is PROPOSED only when all three are true/non-`None`; the proposal names its evidence per branch (`merged_by_patch_id: true`, `worktree: null`, `recorded_merge_sha: <sha>`). Any branch where even one fact is false/unprovable (including a `VcsCommandError` from either `VcsPort` call) is REFUSED — omitted from the proposal list, named instead in a separate `insufficient_evidence` report entry stating which fact(s) could not be established. Never a silent drop.
- **`loop/*` branches and `rescue/*` tags are excluded structurally, before evidence-gathering, unconditionally** — no policy key governs this exclusion (unlike `landing_rules`'s own configurable shape); a hard `branch.startswith("loop/")` filter on the candidate set itself, applied identically for every project, every run, with no override.
- **A branch FR-59/AD-40 already retired at landing time is never re-proposed here.** Since `land`'s own `merge_pr(..., delete_branch=True)` (Story 4.8) already deletes the STATION branch as part of its own atomic merge call, and this sweep's candidate set is station-branch-EXCLUDED by the structural `loop/*` filter above, the two mechanisms never even evaluate the same branch — no explicit cross-check is needed; the exclusion itself is the proof they cannot disagree.
- **Dry-run by default; `--execute` performs the writes.** Without `--execute`, `marshal retire` reports every proposal (and every `insufficient_evidence` entry) and calls `VcsPort.delete_branch` on NOTHING. With `--execute`, it calls `delete_branch(repo_root, branch, force=False)` for every PROPOSED branch only (never `force=True` — a proposed branch is, by this command's own evidence bar, always content-safe per `is_branch_merged`'s own patch-id proof, so `delete_branch`'s ordinary `-d` semantics are sufficient and correct; `force=True` is reserved for `marshal teardown`'s own different, already-established use).
- **Every deletion is journaled** — an OBSERVATION entry (mirrors `_journal_manual_landing`'s established shape) naming which branches were deleted, under which project, with which evidence, fsync=True — written even in `--execute` mode's own single pass (no separate intent/outcome pair: `delete_branch` is not a two-phase write like `merge_pr`/`commit_paths`, and a failed delete on one branch does not roll back or block the others — each branch's own deletion attempt is independent and independently reported).
- **A `delete_branch` failure for one branch does not abort the sweep** — the remaining proposed branches still get their own attempt; the failure is a registered finding naming which branch and why.

**Never:**
- No `--force` flag on this command at all (mirrors `marshal land`'s own precedent, Story 4.8's Never bullet) — a red/unprovable branch is never deletable through this command by any override; the operator's only recourse for a branch this sweep refuses to propose is a direct `git branch -D` outside Marshal entirely.
- No re-implementation of `is_branch_merged`, `worktree_path_for_branch`, `list_worktrees`, or the `_latest_run_dir`/harness-read sequence — all reused verbatim.
- No policy key to configure the `loop/*`/`rescue/*` exclusion — structural, per the AC's own explicit wording.
- No deletion of the currently-active project's own STATION branch, ever (already impossible given the structural `loop/*` exclusion, stated here for clarity since it's this story's single most safety-critical invariant).
- Do not attempt to enumerate or delete `rescue/*` tags themselves (nothing in this codebase currently mints one) — the exclusion is a defensive filter against a future/external ref sharing that prefix, not a feature that manages tags.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| No loop homes at all | Empty fleet | Clean no-op, `data.proposals: []` | No finding |
| A project with no worktree-isolated tasks (`branch == ""` for every task) | Nothing to retire | That project contributes zero candidates | No finding |
| A branch fully provable (merged by patch-id, no live worktree, phase done with a sha) | Happy path | Proposed, evidence named | No finding |
| A branch merged by patch-id but STILL has a live worktree | Run still in progress | Refused (`insufficient_evidence`: `run_concluded: false`) | No finding, informational report entry |
| A branch with a live worktree removed but phase never reached `"done"` (task abandoned/deferred) | Incomplete story | Refused (`story_done_with_sha: null`) | No finding, informational report entry |
| A task key that does not normalize | Malformed `story_key` | Skipped entirely (mirrors `_gather_claimed_commits`'s own convention) | No finding (not a hard failure) |
| `VcsCommandError` from `is_branch_merged`/`worktree_path_for_branch` for one branch | Git read failure | That branch refused (`insufficient_evidence`), sweep continues for others | Registered WARN finding naming the branch |
| A branch named `loop/<slug>` appears among task snapshots (should never happen -- defense in depth) | Malformed harness data | Excluded structurally, never evaluated, never proposed | No finding |
| Dry-run (`--execute` absent) with real proposals | Default invocation | Report only, `data.executed: false`, zero `delete_branch` calls | No finding |
| `--execute` with real proposals | Explicit opt-in | Every proposed branch deleted (`force=False`), journaled | No finding for success; a per-branch WARN for any deletion failure |
| `--execute` where one of N proposed branches fails to delete | Partial failure | The other N-1 still attempted and deleted; the sweep does not abort | Registered WARN naming the failed branch |
| Two projects, one with proposals, one with none | Mixed fleet | Both reported; only the one with proposals contributes deletions under `--execute` | No finding |

</intent-contract>

## Code Map

- `src/pyforge/marshal/cli/retire.py` — NEW. `add_retire_subparser`, `run_retire(args, *, vcs=None, fs=None, harness=None) -> int`, `_render_text_retire`. Reuses `cli/deploy.py`'s `_latest_run_dir`/`_resolve_harness_run_id_for_resume` (imported from `cli/spin.py`, mirroring `_gather_claimed_commits`'s own established local-import convention) and `_home_path` (from `cli/init.py`).
- `src/pyforge/marshal/core/retire.py` — NEW. Pure evidence-classification: `RetirementCandidate` (frozen dataclass: `slug`, `branch`, `story_key`), `RetirementProposal`/`InsufficientEvidence` result shapes, `classify_retirement(candidate, *, merged_by_patch_id, run_concluded, recorded_merge_sha) -> RetirementProposal | InsufficientEvidence` (pure, AD-4), `is_structurally_excluded(branch: str) -> bool` (the `loop/*` prefix check).
- `src/pyforge/marshal/core/findings.py` / `core/verdict.py` — EDIT. Register + classify `MRS-RETIRE-001`..`MRS-RETIRE-00N` (malformed `--project` slug, a `VcsCommandError` during evidence gathering, a `delete_branch` failure under `--execute`).
- `src/pyforge/marshal/cli/main.py` — EDIT. Wire `retire_cli.add_retire_subparser(subparsers)`.
- `tests/unit/test_retire.py` — NEW. `core/retire.py`'s pure classification matrix (no I/O) + `cli/retire.py`'s full I/O matrix with fake `VcsPort`/`FsPort`/`HarnessPort` doubles (mirrors `test_land.py`'s established fake-port style).
- `tests/unit/test_cli.py` — EDIT. `retire` subcommand wiring smoke test.

## Design Notes

- **Why `core/retire.py`'s classification never reads `TaskPhaseSnapshot` directly:** keeping the pure core's input shape to three plain facts (`merged_by_patch_id: bool`, `run_concluded: bool`, `recorded_merge_sha: str | None`) rather than the whole harness-native snapshot type means the classification logic has zero coupling to bmad-loop's own field names/spellings — `cli/retire.py` is the one place that translates `TaskPhaseSnapshot.phase == "done"` into the `recorded_merge_sha` fact the pure core actually consumes, matching AD-33's "git is a repo-fact authority, journal/harness is a process-fact authority, and something at the CLI boundary translates between them" pattern every other Epic 4 story already established.
- **Why the "run concluded" fact is a WORKTREE check, not a harness-reported run-status field:** `RunStatusSnapshot` itself has run-level pause/deferred state (Story 3.7), but nothing that says "this SPECIFIC task's own branch's worktree has been torn down" more directly than asking git itself — `worktree_path_for_branch(...) is None` is the SAME git-truthful signal `marshal homes`'s own isolation checks already trust, and needs no interpretation of harness-native run-state vocabulary at all.
- **Why `ClaimedCommit` (Story 4.5) is NOT reused for this story's own gathering:** `ClaimedCommit` deliberately drops `TaskPhaseSnapshot.branch` (Story 4.5's own scope never needed it — `refresh-feed`'s domain reconciliation is keyed by `story_key` alone). This story needs the branch name itself, so it reads `TaskPhaseSnapshot` directly rather than through that narrower, already-shipped projection — reusing the READ PRIMITIVES underneath both, never a second harness-read mechanism.
- **Why no `--force` exists on this command at all (unlike `teardown`):** `teardown`'s `--force` exists because a home CAN legitimately need destroying despite carrying real, provably-uncaptured work (an operator's own informed override of a real safety refusal). `retire` has no equivalent scenario: every proposal it makes is, by construction, already three-ways provably safe -- there is no "I know better than the evidence" case to support, so adding an override flag would only ever be a way to defeat the very evidence bar this story exists to enforce.

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`
- `pixi run --frozen -e pyforge-ci pyforge-deps-test`
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`

## Spec Change Log

**1. `WorktreeEntry.path` (from `list_worktrees`) is used directly as each project's loop home, rather than recomputing it via `cli/init.py::_home_path` — a scope-narrowing adaptation, not the contract itself.** The Code Map named `_home_path` as a reuse target, but `marshal homes` itself already trusts `list_worktrees`'s own reported path as each home's real location; recomputing it a second way would add a redundant, potentially-diverging path (a home whose worktree was moved/relinked since `list_worktrees` last read it, however unlikely) for no behavioral benefit `marshal homes`'s own precedent doesn't already accept.

**2. `MRS-RETIRE-003` covers BOTH a `delete_branch` failure and a post-deletion journal-write failure — one code, not two.** The Code Map named three total codes without separately enumerating a journal-failure case; reused the same code, mirroring `cli/deploy.py::_journal_manual_landing`'s own established precedent of folding a journal-write failure into an existing landing-action code rather than minting a dedicated one.

## Review Triage Log

### 2026-08-06 — Review pass 1 (Blind Hunter + Edge Case Hunter, parallel)

- intent_gap: 0
- bad_spec: 0
- patch: 2 (high 1, medium 1)
- defer: 1
- reject: 0
- addressed_findings:
  - `[high]` `[patch]` **`vcs.delete_branch(..., force=False)` contradicts `VcsPort.delete_branch`'s own documented contract and `cli/init.py::run_teardown`'s identical, already-established precedent — `git branch -d`'s ancestry-based check would spuriously refuse exactly the squash-merged branches this command's own `is_branch_merged` (patch-id/content-based) proof already establishes as safe, making `--execute` a near-total no-op against this repo's real landing convention.** Independently found by BOTH reviewers as the single most severe finding against this story. Fixed: `force=True`, matching `is_branch_merged`'s own trusted content-based proof and `run_teardown`'s own precedent — a failure downgrades to a WARN, never blocks the rest of the sweep. Test updated: `test_execute_deletes_every_proposed_branch_and_journals` now asserts `force=True`.
  - `[medium]` `[patch]` **Two `TaskPhaseSnapshot` entries in the same run naming the SAME branch (a harness anomaly, or a retried story reusing a worktree-isolated branch) gathered evidence twice, double-reported the branch in `proposals`, and — under `--execute` — attempted `delete_branch` twice, the second call necessarily failing and producing a spurious WARN for a deletion that had actually already succeeded.** Found by the Edge Case Hunter. Fixed: a per-slug `seen_branches: set[str]` skips a branch already classified this run, before any evidence-gathering call. New test: `test_duplicate_task_branch_in_one_run_is_evaluated_and_deleted_only_once`.
- deferred (not fixed in this pass, appended to `deferred-work.md` as a NEW entry):
  - `[low]` D1: `data["proposals"]`'s report hard-codes `merged_by_patch_id`/`worktree` as literals rather than deriving them from `RetirementProposal` (which carries neither field) — correct today only because of `classify_retirement`'s own current gating, fragile against a future change to that gating with no test able to catch a desync.
- rejected: none this pass.

## Suggested Review Order

**The safety-critical fix — start here**

- `run_retire`'s `--execute` block: the `force=True` fix and its rationale comment.
  [`retire.py`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/retire.py) — search `vcs.delete_branch`

**Correctness fix**

- The per-slug `seen_branches` dedup guard.
  [`retire.py`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/retire.py) — search `seen_branches`

**The pure classification core (peripherals)**

- `core/retire.py::classify_retirement`/`is_structurally_excluded` — unchanged by this review pass, already sound per both reviewers.

**Tests**

- `test_retire.py`'s full I/O matrix, plus the two new/updated tests from this pass.
</intent-contract>
