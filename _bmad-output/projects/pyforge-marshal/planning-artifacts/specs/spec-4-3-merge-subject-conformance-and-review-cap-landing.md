---
title: 'Merge-subject conformance and review-cap landing'
type: 'feature'
created: '2026-08-06'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md']
warnings: []
baseline_revision: '4d5218a9c73431b99903af8d6e09a0c6c48a77c4'
---

<intent-contract>

## Intent

**Problem:** two real pyforge-warden stories were landed by hand (FR-27's own motivating evidence) with no governed path — no re-run of the full gate immediately before the merge, no guaranteed use of the conventional merge-subject form, no journal record of the manual decision or its justification. `marshal land` (the fully automated last mile) is Story 4.8, several stories away; operators need a governed manual-landing path now, for the case FR-27 names explicitly: a story that is sound but did not converge in review.

**Approach:** `marshal deploy land-story <slug> <key>` re-runs the full gate (verify commands + `--scope-check`, reusing `cli/gate.py::run_evaluate` rather than a parallel implementation), and on green: renders the merge subject from policy's `merge_subject_template` via the already-shipped `core.identity.render_merge_subject` (never hand-typed), performs the merge via a new `VcsPort.merge_branch` primitive, and journals the landing with the operator's required `--justification`. The same command also audits merge-subject conformance for every commit between a `--since` ref and the post-merge `main` HEAD, using `core.identity.parse_merge_subject` — the SAME parser that rendered the subject, never a second regex (AD-24) — reporting (not blocking on) any non-conforming merge in that window.

## Boundaries & Constraints

**Always:**
- `land-story` re-runs the **full** gate before merging: both halves (verify commands AND `--scope-check`) must be green. Reuse `cli/gate.py::run_evaluate`'s own logic as a function call, not a shelled-out subprocess re-invocation of the `marshal` CLI itself — this command is already inside the `marshal` process. If `run_evaluate`'s current shape doesn't support in-process reuse cleanly, refactor the minimum needed to call it as a function (check its signature before assuming a shelled-out call is required).
- The merge subject is rendered via `core.identity.render_merge_subject(key, template)` where `template = effective.merge_subject_template.value` — the operator supplies only the story key and an optional `--justification` (required, non-empty), never the subject text itself. No f-string/format literal renders a merge subject anywhere in this story's new code.
- `VcsPort.merge_branch(repo_root: Path, branch: str, *, into: str, subject: str) -> str` (new; returns the new merge commit sha) — a real `git merge --no-ff -m <subject> <branch>` against `into` (checked out or resolved via `git -C`, whichever matches this file's existing invocation pattern for write operations), read-only against `branch` itself, the only write is the merge commit on `into`. Raises `VcsCommandError` on any conflict or failure — `land-story` treats a merge failure as a hard stop, never a partial/silent state (the gate already passed; a merge conflict at this point is reported plainly, not retried or auto-resolved).
- **The manual landing is journaled** (one `observation` entry, `fsync=True` matching Story 4.2's own precedent for an operator-authorizing entry): `story_key`, `justification` (the operator's required text, redacted at capture per AD-34 since free text from an operator can carry anything pane-derived text can), `merge_sha`, `gate_verdict` (the full-gate result that authorized the merge).
- **Conformance audit, same command, folded into one report — not a separate action.** After a successful merge, `land-story` gathers `VcsPort.commit_subjects(repo_root, "main")` and, for every subject between `--since` (a required-or-defaulted ref — default: the merge-base of `branch` and `main` before this landing, i.e. "everything that landed on main since this branch diverged") and the new merge commit, attempts `core.identity.parse_merge_subject(subject, template)`. Every subject that does NOT conform is named in the report (`data.non_conforming_merges`) — this is a **reported finding, not a blocking one**: FR-27's own text says "deploy reports", not "deploy refuses". A wave containing an old-style GitHub PR merge (this repo's own real history, per Story 4.1's own finding) is expected to report non-conformance, not fail the landing.
- `--since` accepts an explicit ref; when omitted, computed as `git merge-base <branch> main` (a read the new `merge_branch` call's own precondition check already needs, so no second git round-trip).

**Never:**
- No hand-typed merge subject anywhere in this story's code — always through `render_merge_subject`.
- No second regex for conformance checking — always `core.identity.parse_merge_subject`, the same function `render_merge_subject`'s own template governs.
- The conformance audit never blocks the landing — it is purely a report.
- Do not touch `cli/land.py`/`core/landing.py` (Story 4.8's own surface) or attempt PR/label/check automation (Story 4.4/4.8) — this is a manual, single-story, operator-driven path, not the automated last mile.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Full gate green | Verify commands pass, scope check clean | Merge proceeds, subject rendered from policy, journaled | No error |
| Full gate red (either half) | Verify command fails OR scope violation | Landing refused before any merge attempt; no journal entry, no merge | Registered finding naming which half failed |
| No `--justification` supplied | Missing/empty | Refused before the gate even runs — cheap precondition first | Registered finding |
| Merge conflict | `git merge` fails | Hard stop; reported plainly; no partial journal entry (journal only on confirmed success) | `VcsCommandError` surfaced as a finding |
| Conformance audit, all subjects conform | Every commit in the window renders/parses cleanly | `data.non_conforming_merges: []` | No error |
| Conformance audit, some subjects don't conform | e.g. a GitHub-PR-merge subject in the window | Named in `data.non_conforming_merges`, landing still succeeds | Reported, never blocking |
| `--since` omitted | No explicit ref | Defaults to `merge-base(branch, main)` | No error |
| Story key resolves to no real branch | Typo, or branch never existed | Refused before the gate runs | Registered finding |

</intent-contract>

## Code Map

- `src/pyforge/marshal/ports/vcs.py` — EDIT. `VcsPort.merge_branch(repo_root: Path, branch: str, *, into: str, subject: str) -> str`.
- `src/pyforge/marshal/adapters/vcs_git.py` — EDIT. Implement `merge_branch` (`git merge --no-ff -m <subject> <branch>`, resolves `into` via whatever this file's existing write-method convention for a target ref is).
- `src/pyforge/marshal/cli/deploy.py` — EDIT. New `land-story` action: `--justification` precondition, in-process full-gate re-run (reusing `cli/gate.py::run_evaluate`), subject rendering, merge, journaling, conformance audit.
- `src/pyforge/marshal/core/findings.py` / `core/verdict.py` — EDIT. New codes: missing-justification, gate-not-green (or reuse existing gate finding codes directly — check before inventing new ones), merge-failed.
- `tests/unit/test_vcs_git.py` — EDIT. `merge_branch` against a real temp git repo (clean merge, conflict case).
- `tests/unit/test_deploy.py` — EDIT. `land-story` end-to-end via fake `VcsPort`/gate result, including the conformance-audit report.

## Tasks & Acceptance

**Execution:**
- [x] `ports/vcs.py` + `adapters/vcs_git.py` — `merge_branch`.
- [x] `cli/deploy.py` — `land-story` action: justification precondition, full-gate re-run, subject rendering, merge, journaling.
- [x] `cli/deploy.py` — conformance audit folded into the same command's report.
- [x] `core/findings.py` / `core/verdict.py` — register new codes as needed.
- [x] Unit tests for every new/edited module, including the full I/O matrix above.
- [x] `deferred-work.md` — log any scope narrowed during implementation. *(None narrowed — see Spec Change Log for the adaptations made instead.)*

**Acceptance Criteria:**
*(Story 4.3's ACs from `epics.md`, preserved as the contract of record.)*
- [x] Given a named story branch that is sound but did not converge in review, when the review-cap landing command runs, then it re-runs the full gate — verify commands plus scope check — and lands only on a green result (FR-27)
- [x] And the merge uses the conventional subject rendered from policy; the operator never hand-types it
- [x] And the manual landing and its justification are journaled
- [x] And deploy reports any merge in the wave whose subject does not conform, using the same parser that renders it — not a second regex (AD-24)
- [x] And the subject template lives in policy, not as a literal in code

## Design Notes

**Why the conformance audit is folded into `land-story` rather than a separate command.** FR-27's own text places both concerns in one requirement ("deploy reports any merge in the wave whose subject does not conform" appears as a consequence of the SAME landing path, not a distinct FR). A landing is the natural moment to also surface what else landed non-conformantly in the same window — the operator is already looking at this wave's history to justify the manual merge.

**Why `--since` defaults to the merge-base, not some fixed lookback window.** "The wave" has no persisted definition yet (that's arguably Story 4.6/4.9's concern — regenerable derived state, idempotent re-runs). The merge-base of the branch being landed against `main` is the one boundary this story can compute without inventing new state: everything reachable from `main` but not from the branch's own fork point is, by construction, what landed on `main` while this branch was in flight.

## Spec Change Log

**1. "A named story branch" resolves to the loop-home's own STATION branch (`f"loop/{slug}"`), not a per-story branch — adapted, not the contract itself.** No code anywhere in this package derives a per-story branch NAME from a bare story key: the one place a per-story branch is named at all is `ports/harness.py`'s `TaskPhaseSnapshot.branch`/`StoryTask.branch`, minted by bmad-loop itself when a story runs worktree-isolated, with no naming convention Marshal can reconstruct offline. Every real write this package already makes against a story's own development branch (`cli/init.py`'s `add_worktree`, `run_teardown`; `supervisor/__main__.py`'s durability watcher) targets the loop-home's station branch, `f"loop/{slug}"` — this repo's own established convention for "where a project's stories actually land while in flight." `land-story <slug> <key>` therefore merges that station branch; `<key>` renders the merge subject and drives the full-gate re-run's `--story` binding, but names no branch of its own. This also gives the Design Notes' own "wave" a concrete referent: the station branch's own commit history since its merge-base with `main`.

**2. `merge_base` added as a standalone `VcsPort` primitive rather than folded silently inside `merge_branch` — adapted, not the contract itself.** The Always bullet describes the `--since` merge-base read as "a read the new `merge_branch` call's own precondition check already needs" — but a real `git merge --no-ff` needs no separate merge-base read of its own (git resolves that internally); the value is needed by `land-story` itself, before the merge, for the `--since` default (the Design Notes' own "computed before the merge"). Exposed as `VcsPort.merge_base(repo_root, a, b) -> str` (mirroring `is_branch_merged`'s existing internal `git merge-base` call, but returning the value rather than a derived boolean) rather than reimplementing the read a second way inside `cli/deploy.py`.

**3. The conformance audit calls `VcsPort.commit_subjects` with a git revision RANGE (`f"{since}..{merge_sha}"`) rather than the full `"main"` history sliced by subject-string position — adapted, not the contract itself.** The literal Code Map wording names `commit_subjects(repo_root, "main")` plus positional slicing between `--since` and the merge commit. Slicing a subject LIST by string position is fragile the moment two commits anywhere in the repo's history share an identical subject line (not a rare shape — this repo's own bare `"initial"`/`"wip"` commits collide) — a git revision range is git's own unambiguous answer to "every commit reachable from the merge commit but not from `--since`", needs no second read, and cannot misalign on a duplicate subject. `VcsPort.commit_subjects`'s existing signature (a bare `ref: str`, passed straight to `git log <ref> --format=%s`) already accepts a range expression with no interface change.

**4. `cli/gate.py::run_evaluate` was split into `evaluate_gate` (pure envelope core) + a thin `run_evaluate` wrapper — the minimal refactor the Always bullet itself anticipates.** `run_evaluate`'s original body gathered every impure input, ran every check, built the envelope, AND printed/exited in one function — not cleanly callable in-process without also triggering a second stdout write and losing the envelope needed to decide "is the gate green" and to journal `gate_verdict`. `evaluate_gate(args, *, process, vcs, fs) -> Envelope` is the pre-print body verbatim; `run_evaluate` now calls it, renders, prints, and returns the exit code — identical behavior/output for every existing caller and test. `cli/deploy.py::run_land_story` calls `evaluate_gate` directly with a synthetic `argparse.Namespace(project=slug, run_id=None, scope_check=True, story=str(key))`.

**5. `cli/deploy.py::run_land_story` imports `evaluate_gate`/`_home_path` via LOCAL (function-scoped) imports, not module-level ones — a necessary adaptation the Always bullet's "reuse `run_evaluate`'s own logic as a function call" did not anticipate needing.** `cli/init.py` imports this module (`from . import deploy`) and `cli/gate.py` imports `cli/init.py` (`from .init import _home_path`); a module-level `from .gate import evaluate_gate` / `from .init import _home_path` inside `cli/deploy.py` would create a load-order-fragile `cli.deploy <-> cli.init` / `cli.deploy -> cli.gate -> cli.init -> cli.deploy` cycle (`main.py` imports `deploy_cli` before `gate_cli`/`init_cli`, so the cycle would bite on the very first `marshal` invocation). Both imports are deferred inside `run_land_story`'s own body instead — a cheap `sys.modules` lookup by the time any CLI handler actually runs, since `main.py` already imports every subcommand module before dispatch.

**6. Four new `MRS-DEPLOY-*` codes (006–009), not fewer.** The Code Map allowed reusing existing gate codes for "gate not green" (done — `evaluate_gate`'s own findings, e.g. `MRS-GATE-001`/`007`/`008`, are folded straight into `land-story`'s own report, no new code) but named "missing justification" and "merge-failed" as the only two NEW codes explicitly. A third (`MRS-DEPLOY-007`, branch/merge-base resolution failure — "story key resolves to no real branch") and a fourth (`MRS-DEPLOY-009`, the conformance audit's own read failure — WARN, deliberately non-blocking per the story's own Never bullet) were needed once the branch-resolution and audit-failure rows of the I/O matrix were implemented; see `core/findings.py`/`core/verdict.py` for the full classification rationale.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: all green, new tests included, zero regressions.
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache` — expected: all import-linter contracts hold.

**Manual checks (if no CLI):**
- Against a real throwaway branch with a trivial diff: run `marshal deploy land-story <slug> <key> --justification "test"` and confirm the merge commit's subject matches `render_merge_subject`'s own output exactly.

## Review Triage Log

### 2026-08-06 — Review pass 1 (Blind Hunter + Edge Case Hunter, parallel)

- intent_gap: 0
- bad_spec: 0
- patch: 7 (critical 1, high 4, medium 2)
- defer: 2
- reject: 0
- addressed_findings:
  - `[critical]` `[patch]` **`GitVcs.merge_branch` ran `git checkout <into>` directly against `repo_root` — this project's ONE shared, currently-active working directory, not an isolated worktree — with no dirty-tree precondition and no restoration of whatever was checked out before.** `land-story`'s entire purpose is a governed, safe manual `git merge`; the original implementation could silently switch the operator's own currently-checked-out branch, lose uncommitted context, or race with concurrent work in that same checkout — exactly the scenario active during this very session (this repo's own primary working directory is its main checkout). Independently flagged as the single most dangerous finding by both reviewers. Fixed: `merge_branch` now NEVER checks out or otherwise mutates `repo_root`'s own active working tree. It resolves `into`'s current tip sha, performs the merge inside a throwaway DETACHED worktree (`git worktree add --detach <tmp> <old_sha>`), advances the real `into` ref via a three-arg `git update-ref refs/heads/<into> <new_sha> <old_sha>` compare-and-swap (atomically verifying `into` has not moved concurrently — this also closes the P4 TOCTOU gap below), and removes the temp worktree in a `finally` block that is itself guarded end-to-end so a cosmetic cleanup failure can never mask an already-durable merge (P5). New tests: `test_merge_branch_never_touches_repo_roots_own_active_checkout`, `test_merge_branch_leaves_no_temp_worktree_behind_on_success`, `test_merge_branch_raises_vcs_command_error_on_conflict` (extended to assert cleanup), `test_merge_branch_refuses_when_into_moves_concurrently`, `test_merge_branch_still_returns_the_sha_if_temp_worktree_cleanup_fails`, `test_merge_branch_still_returns_the_sha_if_cleanup_raises_outright`.
  - `[high]` `[patch]` **The gate-green check accepted `Verdict.WARN`, not just `Verdict.CLEAN`, as sufficient to land.** `status_for` treats `{clean, warn}` as "ok", but a WARN-tier gate result (real findings exist, just non-blocking ones) is not "green" in the strict sense FR-27 requires for a manual, deliberate landing decision. Fixed: `run_land_story` now requires `gate_envelope.verdict is Verdict.CLEAN` exactly; anything else — including warn — refuses with a new `MRS-DEPLOY-010` finding (`Verdict.GATE_FAILED`), same as a real gate failure. New test: `test_land_story_refuses_a_warn_tier_gate_not_exactly_clean`.
  - `[high]` `[patch]` **A `PolicyIOError` resolving the merge-subject template was recorded as a finding but execution fell through and merged anyway using a silently-defaulted template** — the one place AD-24's own core promise ("policy governs the subject, never a code literal") could be silently defeated by a policy read failure. Independently found by both reviewers. Fixed: a `PolicyIOError` here is now a hard stop, exactly like every other precondition failure in this function — no merge attempt, no journal entry. New test: `test_land_story_policy_read_failure_is_a_hard_stop_no_merge_attempted`.
  - `[high]` `[patch]` **Nothing pinned the branch's own tip before the (potentially slow) gate run completed, so a commit landing on the branch during gate evaluation would be merged as if the now-stale gate result still applied to it.** Closed structurally by the P1 redesign's compare-and-swap protecting `into`, but the branch's own tip also needed pinning. Fixed: a new `VcsPort.resolve_ref` primitive captures `branch`'s tip immediately after the gate runs, re-verifies immediately before merging that it has not moved, and `merge_branch` is handed the CAPTURED sha (not the bare branch name) — a mismatch refuses with a new `MRS-DEPLOY-011` finding (`Verdict.ERROR`) naming "branch moved during gate evaluation" rather than silently merging whatever the branch now points to. New test: `test_land_story_refuses_when_branch_moves_during_the_gate_window`.
  - `[high]` `[patch]` **A failure of the trailing `git rev-parse HEAD` readback after a successful checkout+merge was raised as the exact same `VcsCommandError` as a genuine merge failure, so a successfully-landed merge could be treated identically to "nothing happened" and skip journaling.** The P1 redesign structurally closes this: the temp-worktree cleanup step (the only step after the CAS) is wrapped end-to-end so it can never raise, even when `_run` itself raises (not merely returns non-zero) — a successfully-landed merge is now always returned to the caller and journaled. New tests: `test_merge_branch_still_returns_the_sha_if_temp_worktree_cleanup_fails`, `test_merge_branch_still_returns_the_sha_if_cleanup_raises_outright`.
  - `[medium]` `[patch]` **No "already merged" guard existed before running the full gate and attempting a merge, so re-running `land-story` on an already-durably-merged key produced a spurious empty merge commit and a duplicate journal entry.** Fixed: reuses Story 4.1's own durability-detection machinery (`VcsPort.commit_subjects` + `core.promotion.merged_story_keys`), never a reimplementation — checked before the gate runs; a match short-circuits to a clean no-op report (`data.already_merged: True`), no gate run, no merge attempt. New test: `test_land_story_already_merged_is_a_clean_noop`.
  - `[medium]` `[patch]` **A `--justification` redaction failure silently wrote `null` into the permanent journal record with no warning that the operator's stated justification was lost.** Independently found by both reviewers. Fixed: `_journal_manual_landing` now appends a registered WARN finding (`MRS-DEPLOY-012`) naming the gap when redaction fails; the landing itself still proceeds (not a safety-critical precondition, unlike P1–P4). New test: `test_land_story_redaction_failure_warns_but_still_lands`.
- deferred (not fixed in this pass, appended to `deferred-work.md` as NEW entries):
  - `[low]` D1: the conformance-audit `--since` default (merge-base computed before the gate run) can include commits that land on `main` DURING the potentially slow gate evaluation, misattributing them to "this landing's own wave" in the non-blocking report. Low practical impact since the audit is reporting-only, never blocking.
  - `[low]` D2: `land-story` resolves "the named story branch" to the whole loop-home station branch (`loop/<slug>`), not a per-story branch — an already-documented, accepted limitation (see this spec's own Spec Change Log entry 1: no per-story branch name is derivable anywhere in this codebase today). Logged in `deferred-work.md` for a reader of that ledger alone, since it was not previously present there.
- rejected: none this pass.

</intent-contract>

## Suggested Review Order

**The safety-critical fix (P1) — start here**

- `merge_branch`'s detached-worktree + compare-and-swap redesign: never touches the shared checkout, cleanup on every exit path.
  [`vcs_git.py:798`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/vcs_git.py#L798)

- `resolve_ref`, the new primitive the CAS and branch-tip pinning (P4) both depend on.
  [`vcs_git.py:779`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/vcs_git.py#L779)

**Landing orchestration**

- `run_land_story`: justification precondition, already-merged short-circuit (P6), strict-CLEAN gate check (P2), policy-failure hard-stop (P3), branch-tip re-verification (P4), journaling with the P7 redaction-failure warning.
  [`deploy.py:1151`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py#L1151)

**Tests (peripherals)**

- `merge_branch`/`resolve_ref` against real temp git repos, including the shared-checkout-untouched proof and the simulated concurrent-move CAS-refusal test.
  [`test_vcs_git.py:1`](../../../../src/shared/packages/pyforge-marshal/tests/unit/test_vcs_git.py#L1)

- `land-story` end-to-end, full I/O matrix plus every P1-P7 regression.
  [`test_deploy.py:1`](../../../../src/shared/packages/pyforge-marshal/tests/unit/test_deploy.py#L1)
