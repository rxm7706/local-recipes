---
title: 'Story 2.2: Nothing happens unless something actually changed'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** Story 2.1's `--build` refreshes `docs/dashboard/` but never touches git — an operator still has to hand-run `git add`/`commit`/`push` (or skip it, wondering whether anything actually changed) after every build. Left un-reconciled, a habit of "always commit" produces empty/no-op commits on every run.

**Approach:** Add `dashboard_diff` (git-diff `docs/dashboard/` against the committed tree) and `commit_and_push_dashboard` (add + commit + push to the currently checked-out branch on `origin`) to `deploy.py`. Extend `_run_dashboard` so bare `steward deploy dashboard` (no `--build`) builds, diffs, and only commits+pushes when the diff is non-empty (FR-9) — direct push to whatever branch is checked out, no new Actions workflow, no daemon (AD-4).

## Boundaries & Constraints

**Always:**
- `dashboard_diff` runs `git diff -- docs/dashboard` and returns its stdout verbatim; empty/whitespace-only output means "no diff."
- `commit_and_push_dashboard` performs `git add -- docs/dashboard`, `git commit -m "dashboard: refresh status (steward deploy dashboard)"`, `git rev-parse HEAD`, `git symbolic-ref --short HEAD`, then `git push origin <branch>` — as four/five discrete `subprocess.run(check=True, ...)` calls, so a failure is attributable to a specific step via its own `exc.cmd` (not a single opaque scripted command).
- `_run_dashboard`'s bare-invocation branch order is: build → diff → (no diff: report and stop) → (diff: commit+push, report the new SHA).
- Every `git`/`pixi` subprocess call in this duty continues to propagate `subprocess.CalledProcessError` to `DeployDuty.run`'s single boundary catch (unchanged from Story 2.1) — no new per-primitive try/except.
- `commit_and_push_dashboard` pushes to whatever branch `git symbolic-ref --short HEAD` reports at call time — never a hardcoded `"main"` — because the branch GitHub Pages serves from IS `main` in real operation (`.github/workflows/dashboard.yml` triggers on push to `main`), but hardcoding that string would make this primitive untestable against a scratch repo on any other branch name and would silently push to the wrong ref on a future rename.

**Block If:** none.

**Never:**
- No `--dry-run` flag yet (Story 2.3) — bare `deploy dashboard` with a diff commits+pushes unconditionally in this story's slice; the operator cannot preview first until Story 2.3 lands.
- No new state file recording "last deploy" (Story 2.4's FR-11 constraint applies to the whole epic, not just Story 2.4 — this story doesn't introduce one either, since the reconciliation itself needs no memory beyond the current git diff).
- No squashing/amending of a prior deploy commit — every real diff produces exactly ONE new commit; this story never rewrites history.
- No partial-diff / selective-file commit — `git add -- docs/dashboard` stages the WHOLE directory's diff in one commit, matching FR-9's "commit contains exactly the changed dashboard files" (i.e. not more, not fewer, not split across multiple commits).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| No diff, run once | fresh build == committed tree | Zero commits; `ok=True`, "no diff" | No error |
| No diff, run twice | same repo state, `deploy dashboard` run twice in a row | Zero commits BOTH times — `git log` identical before/after both runs | No error |
| Real diff | `docs/dashboard/generate.py`'s output differs from the committed tree | Exactly ONE new commit, containing only the `docs/dashboard/` diff, pushed to the current branch | No error |
| `git diff` itself fails | `cwd` not a git worktree | Nothing committed | `subprocess.CalledProcessError` → `DutyResult(ok=False, ...)` |
| `git push` fails (e.g. no `origin`, rejected) | valid diff, commit succeeds, push fails | Commit exists locally; push failure surfaced, not swallowed | `subprocess.CalledProcessError` → `DutyResult(ok=False, ...)` — a known partial-completion state (commit made, push failed), documented in Design Notes, not silently retried |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/deploy.py` -- add `dashboard_diff`, `commit_and_push_dashboard`; extend `_run_dashboard`'s bare-invocation branch
- `src/shared/packages/pyforge-steward/tests/conformance/test_deploy_reconcile.py` -- NEW: real scratch git repos (not mocked) proving the zero-commit / exactly-one-commit properties

## Tasks & Acceptance

**Execution:**
- [x] `deploy.py` -- `dashboard_diff(*, cwd) -> str`
- [x] `deploy.py` -- `commit_and_push_dashboard(*, cwd) -> str` (returns new commit SHA)
- [x] `deploy.py` -- extend `_run_dashboard`: bare invocation now builds, diffs, and commits+pushes iff non-empty diff
- [x] `tests/conformance/test_deploy_reconcile.py` -- zero-commit-twice property, exactly-one-commit-on-real-diff property, both via a real scratch git repo (`git init`, a fake `origin` remote as a second bare repo)

**Acceptance Criteria:**
- Given a repo state where `docs/dashboard/`'s committed content already matches what a fresh build produces, when `steward deploy dashboard` is run twice in a row with no source changes between runs, then the second (and first) run results in zero commits.
- Given a change to `docs/dashboard/generate.py`'s output between runs, when `steward deploy dashboard` is run, then exactly one new commit is created, containing exactly the changed dashboard files, and the commit is pushed to the branch GitHub Pages already serves from (direct push, no new Actions workflow — AD-4).

## Spec Change Log

## Review Triage Log

### 2026-08-07 — Self-review (adversarial re-read before marking done)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 1
- reject: 0
- addressed_findings:
  - `[low]` `[defer]` `dashboard_diff` uses `git diff`, which only reports
    changes to already-tracked files — it would NOT see a brand-new
    untracked file `dashboard-gen` might someday create under
    `docs/dashboard/`. Considered fixing via `git add -N` (intent-to-add)
    before diffing, but that mutates the index as a side effect — which
    would break Story 2.3's own AC that `--dry-run` leaves `git status`
    byte-for-byte unchanged. Not fixed: `docs/dashboard/generate.py`'s own
    docstring states it only ever refreshes the existing tracked `data.js`
    in place (confirmed by reading the real script, not assumed) — this is
    a real, currently-inert limitation of `dashboard_diff` against a
    hypothetical future change to `generate.py`'s own file-writing
    behavior, not a gap in this story's actual scope. Recorded here so a
    future change to `generate.py` that starts writing new files is a flag
    to revisit this function, not a silent miss.
- Read-modify-write race class (the prompt's specific concern, by analogy
  with `keys-inventory.yaml`): considered and found NOT applicable the same
  way — see this story's spec, "Design Notes" ("why no lock ... git's own
  index lock already serializes concurrent add/commit"). A concurrent
  `steward deploy dashboard` hitting a locked `.git/index.lock` fails
  loudly via the existing `subprocess.CalledProcessError` boundary; it does
  not silently clobber another invocation's write the way two racing
  `save_inventory` calls could before Story 1.4's fix.
- Exception handling: `commit_and_push_dashboard`'s five sequential
  `subprocess.run(check=True, ...)` calls (vs. one scripted multi-command
  string) verified to make a `git push` failure attributable via
  `exc.cmd` distinctly from an `add`/`commit` failure —
  `test_commit_and_push_reports_a_specific_failing_step_when_push_target_is_missing`
  proves this AND proves the already-made local commit is not rolled back
  (the documented accepted partial-completion state).

## Design Notes

**Why five discrete `subprocess.run` calls instead of one shell script:** attributable failure. If `git push` fails after a successful local commit, `exc.cmd` names `git push` specifically — the operator (or a caller parsing `DutyResult.summary`) can tell "committed locally, not yet on the remote" apart from "nothing happened," rather than getting one opaque non-zero exit with no indication of how far reconciliation got.

**The push-fails-after-commit partial state is a KNOWN, accepted tradeoff, not a bug:** re-running `steward deploy dashboard` after a failed push will see NO new diff (the local commit already matches the just-built tree) and report "no diff — nothing to deploy," which would silently leave the unpushed commit stranded. This mirrors `keys.py`'s own accepted `age --output` non-atomicity precedent (Story 1.4's Design Notes) — not solved this story. An operator whose push failed sees the failure message and can `git push` by hand; a future story could add a "local commit ahead of origin" check to `deploy status` (Story 2.4) if this proves a recurring problem in practice. Not proposed as a fix here since Story 2.4's own scope (read the LAST commit) doesn't require it, and speculative recovery logic ahead of any real reported incident isn't warranted per this repo's Simplicity First principle.

**Why no lock/race-protection around the reconcile step (unlike `keys-inventory.yaml`'s `_locked_inventory`):** the state being reconciled here is `docs/dashboard/` itself plus git's own history — `git`'s own index lock (`.git/index.lock`) already serializes concurrent `add`/`commit` invocations at the filesystem level (a second concurrent `steward deploy dashboard` hitting a locked index fails loudly with a non-zero `git` exit, caught by the existing `subprocess.CalledProcessError` boundary — never a silent lost update). Unlike `keys-inventory.yaml` (a bespoke YAML file with no built-in concurrency primitive Steward would otherwise have to add its own lock around), git already owns this exact problem for its own on-disk state.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` -- expected: all tests pass

**Results (2026-08-07):** `pixi run --frozen -e pyforge-steward pyforge-steward-test` — 111 passed (105 pre-existing + 6 new in `test_deploy_reconcile.py`), including the zero-commit-run-twice and exactly-one-commit-on-real-diff properties against real scratch git repos with a real bare `origin` remote.

## Review Triage Log

### 2026-08-07 -- Epic 2 close-out adversarial review (Blind Hunter + Edge Case Hunter, parallel, no shared context, git-operation-focused given this module shells out to commit/push)
- intent_gap: 0
- bad_spec: 0
- patch: 4 (high 1, medium 2, low 1)
- defer: 0
- reject: 0
- addressed_findings:
  - `high` `patch` (Blind Hunter, live-confirmed via repro) **`git commit` with no pathspec commits the ENTIRE index, not just what `git add -- docs/dashboard` staged.** An unrelated file staged by the operator (or another process sharing the same working tree) at call time would silently ride along into the `dashboard: refresh status` commit and get pushed under a misleading message. Fixed: `git commit -- docs/dashboard` (pathspec-scoped, mirroring the preceding `git add`'s own scope). New test: `test_commit_and_push_never_sweeps_in_an_unrelated_staged_file` (stages an unrelated `secret.txt`, asserts it's absent from the resulting commit and still staged afterward).
  - `medium` `patch` (Blind Hunter) **Detached HEAD: the commit happened BEFORE the branch-resolution failure that revealed it.** `git symbolic-ref --short HEAD` ran last, after `git add`/`git commit` already succeeded -- a detached-HEAD checkout left a real, silently-orphaned commit with zero record it was ever made once garbage-collected. Fixed: branch resolution now runs FIRST, before any write; a detached HEAD now refuses cleanly with the working tree exactly as it was. New test: `test_commit_and_push_refuses_before_committing_on_a_detached_head`.
  - `medium` `patch` (Edge Case Hunter) **A failed push becomes permanently silent on the very next run.** This spec's own Design Notes above already named this exact gap ("push-fails-after-commit... not proposed as a fix here since speculative recovery logic ahead of any real reported incident isn't warranted") and deliberately deferred it. The review changed that calculus: Edge Case Hunter demonstrated the CONCRETE consequence, not a speculative one -- the next run's own diff against the already-committed working tree comes back empty, permanently reporting "nothing to deploy" with no path back to noticing, and `deploy status` (Story 2.4) independently misreports the unpushed commit as a completed deploy. That combination (silently-converts-to-success AND status actively lies about it) is a real, demonstrated failure mode, not the speculative one this spec's own Design Notes declined to solve for. Fixed: new `_push_pending_commit_if_ahead` -- before the diff check (never during `--dry-run`, which must never push), checks whether HEAD is ahead of its upstream and retries the push if so, reporting the pushed SHA rather than silently declaring "nothing to deploy". New test: `test_a_stuck_unpushed_commit_is_retried_and_pushed_on_the_next_run`. The companion `deploy status` fix (an explicit "ahead of origin" note) is recorded in Story 2.4's own spec, since that's the file it lives in.
  - `low` `patch` (Edge Case Hunter) **`cmd_name` in `DeployDuty.run`'s exception handler was always the literal string `"git"`**, since every subprocess call in this module starts with it -- contradicting the module's own docstring claim of "attributable to a specific step by its own `exc.cmd`." Fixed: the full command line is now used instead of just `exc.cmd[0]`.

**Follow-up review recommendation: false** -- all four findings are isolated to `commit_and_push_dashboard`'s own write sequence and the shared exception-formatting boundary, each covered by a dedicated new test proving the fix; no new design questions opened.

**Re-verification (2026-08-07, after all four patches):** `pixi run --frozen -e pyforge-steward pyforge-steward-test` -- **126 passed** (122 pre-review-pass baseline + 4 new tests; one of the four review tests -- the status "ahead of origin" note -- lives in and is counted under Story 2.4's own spec).
