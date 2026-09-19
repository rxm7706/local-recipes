---
title: '51.1: Verification sees the merge result'
type: 'fix'
created: '2026-09-19'
status: 'done'
baseline_revision: 'bf6795312e9da368f31b07aba474c838ba8e590e'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: [oversized]
deferred:
  - summary: >-
      The pre-existing "already landed" check in execute_dispatch_land reasons from
      local main while the new Story 51.1 merge-tree-preview check fetches and diffs
      against origin/main, leaving two different freshness assumptions about "main"
      side by side in the same function.
    evidence: >-
      vcs.commit_subjects(git_repo_root, _MERGE_BASE) (_MERGE_BASE = "main", the local
      branch) is unchanged by this story and never fetches; the new
      _refuse_via_merge_tree_preview check explicitly fetches origin/main first. If the
      local main ref is stale, the already-landed check could give a wrong answer. This
      predates Story 51.1 and is outside its intent (fixing merge-result verification,
      not the already-landed check), so it was not fixed here.
    location: 'src/pyforge/marshal/dispatch_land.py (the commit_subjects/_MERGE_BASE check)'
    severity: medium
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** On 2026-09-18 marshal Story 50.4's review pass rewired doctor's `sources/marshal.py`/`sources/ledger.py` 42 minutes after doctor Story 27.5 had rewired the same files past 50.4's baseline. 50.4's branch suite was green, `dispatch land` refused on a real conflict, and the operator hand-composed the merge commit `1a5895317f` — the part git would have auto-merged called `bare_merge.py` with 2 args against the new 3-arg signature, a runtime `TypeError` no verification pass ever saw because verification only ever ran against the branch's own tree, never the tree `origin/main` would actually contain after landing.

**Approach:** before `dispatch land` calls `forge.merge_pr`, when the branch's baseline is behind `origin/main` at all, materialize the tree git would actually produce (`git merge-tree --write-tree origin/main <head>`) into a throwaway, unreferenced worktree and re-run the station's own `verify_commands` against it; refuse with a new named finding (`MRS-DISP-044`) when that run is red, quoting the real failure. A branch whose baseline already equals `origin/main` verifies exactly once, byte-identical to today. A real (git-detected) merge conflict is untouched — it already has an owner (`MRS-DISP-038`/heal); this check only ever fires on a merge git itself considers clean.

## Boundaries & Constraints

**Always:**
- Re-run the station's `verify_commands` (not the full independent-verification gate — see Design Notes) against a `git merge-tree --write-tree origin/main <head>` preview whenever `commits_behind(head, origin/main) > 0`.
- A branch already even with `origin/main` (`commits_behind == 0`) verifies exactly once, with no new git calls beyond the existing `fetch`/`commits_behind` check — byte-identical outcome to pre-51.1 behavior.
- A red merge-tree run refuses landing with a new `MRS-DISP-044` finding naming the failing command and the tail of its captured output (so the fixture's runtime `TypeError` is legible directly from the finding, not just from a data blob).
- The 50.4/27.5 fixture (branch green, merge-tree red with the `bare_merge.py` `TypeError`) must refuse via `MRS-DISP-044`; a fixture whose merge-tree is clean and green must land with no operator action; removing the merge-tree run must make the 50.4/27.5 fixture land green again (the mutation test).
- The throwaway worktree/commit this check creates is never referenced by any branch or ref, and is always removed (best-effort) before `execute_dispatch_land` returns or raises.
- A REFUSED result from this check carries `pr_number`/`subject`/`marshal_native=True` (Story 51.2's own convention — this refusal fires after the PR is already open and the subject is already known-marshal-native).

**Never:**
- Do not trust a session's self-report, perform the real land merge (only materialize/inspect a preview of it — git's own `merge-tree` computes the merge, marshal never runs `git merge`/`git merge --no-ff` here), add a second gate or verdict owner (this reuses `Finding`/`Envelope`/`MRS-DISP-*`/`MRS-GATE-*` machinery unchanged, and reuses the exact same per-command classification `evaluate_dispatch_verification` already uses), move a primary checkout that is not a clean `main`, or re-attribute landed history.
- Do not re-run the scope/spec-binding/cross-surface checks against the merge-tree worktree (see Design Notes: `changed_files`'s `base...HEAD` triple-dot diff is merge-base-aware, so pointing it at a merge-tree HEAD would fold `origin/main`'s own independent commits into the "changed files" set and spuriously widen scope — this is why only `verify_commands` are re-run, not the whole gate).
- Do not gate this check on file-level overlap between the branch's own changes and `origin/main`'s new commits (a `commits_behind > 0` proxy is used instead — see Design Notes for why).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| baseline even with origin/main | `commits_behind(worktree, origin/main) == 0` | lands via the existing single-verification path, no new git calls | n/a |
| baseline behind, clean merge, green | `commits_behind > 0`; `merge_tree_write` returns a tree oid; verify_commands pass in the preview worktree | lands with no operator action | n/a |
| baseline behind, clean merge, red (50.4/27.5 fixture) | as above but a verify_command exits non-zero (the `bare_merge.py` `TypeError`) | `REFUSED` with `MRS-DISP-044` naming the command and the TypeError text; PR stays open | PR facts (`pr_number`/`subject`/`marshal_native`) preserved on the result |
| baseline behind, real conflict | `merge_tree_write` returns `None` (git itself reports `CONFLICT`) | unchanged: falls through to the existing `forge.merge_pr` attempt and its `MRS-DISP-038`/heal path | owned entirely by existing code, not touched by this story |
| cannot determine behind-ness | `vcs.fetch`/`vcs.commits_behind` raises `VcsCommandError` | `REFUSED` with `MRS-DISP-044` naming the failure (unevaluable is treated as failure, never silently passed) | same PR-facts preservation as above |

</intent-contract>

## Code Map

- `src/pyforge/marshal/dispatch_land.py:355` — insertion point: immediately before the existing `try: forge.merge_pr(...)` block (already past the marshal-native-subject check at :331-353). New logic goes here, inside `execute_dispatch_land`.
  - `_MERGE_BASE = "main"` (module constant, :41) is the LOCAL landing base used elsewhere in this file — the new check must use `"origin/main"` explicitly (a new module constant), never `_MERGE_BASE`, or it reproduces the exact blind spot this story fixes.
  - `head_sha` (bound :250-266) and `head_branch` (bound :173) are already in scope at the insertion point and are exactly what `merge_tree_write`/`add_worktree_for_tree` need.
  - Existing `MRS-DISP-038` refusal (:381-399, inside the `except ForgeCommandError` around `forge.merge_pr`) is the existing conflict owner — untouched.
  - `DispatchLandingResult` (:45-58) already supports `pr_number`/`subject`/`marshal_native` on `REFUSED` (Story 51.2) — the new refusal reuses this, not a new field.
- `src/pyforge/marshal/dispatch_verify.py`
  - `_run_verify_command` (:31-69) — the exact per-command classification (`gate.classify_outcome`) to reuse. Private; add a new small PUBLIC sibling function (e.g. `run_verify_commands_only`) that loops `effective.verify_commands.value` through it and returns `(command_reports, findings)` — deliberately NOT calling `evaluate_dispatch_verification` itself (see Design Notes on why the scope check can't be reused as-is).
  - `_SCOPE_BASE = "origin/main"` (:27) — confirms `origin/main` is already this module's own convention for "the real remote main."
- `src/pyforge/marshal/ports/vcs.py:437-450` — `merge_tree_conflict_paths`/`file_text_at_ref` Protocol stubs are the exact style to mirror for two new methods:
  - `merge_tree_write(repo_root, base, branch) -> str | None` — the `--write-tree` sibling the Spec's Binding names; returns a tree oid on a clean merge-tree preview, `None` when git itself reports a conflict (never raises for an ordinary conflict — only for a genuine git failure).
  - `add_worktree_for_tree(repo_root, home, tree_oid, *, parent) -> None` — wraps `tree_oid` in a throwaway, unreferenced commit (pinned identity, mirrors `is_branch_merged`'s `commit-tree` discipline at `adapters/vcs_git.py:445-467`) with `parent` as its sole parent, then `git worktree add --detach home <synthetic-sha>` (mirrors `add_worktree`, `adapters/vcs_git.py:295-351`).
  - `commits_behind`/`fetch` (already-existing Protocol methods, :407-436) are reused unchanged for the `commits_behind(worktree, "origin/main") > 0` gate condition — `fetch` must run first so the local `origin/main` ref is current.
  - `remove_worktree` (already existing, `adapters/vcs_git.py:511-528`) is reused unchanged for best-effort cleanup in a `finally`; it RAISES on failure, so the caller (`dispatch_land.py`) wraps it in `try/except VcsCommandError: pass`, matching how `dispatch_land.py` already treats `forge.add_labels` failures as swallowed best-effort (:325-327).
- `src/pyforge/marshal/adapters/vcs_git.py`
  - `merge_tree_conflict_paths` (:1116-1143) — exact style to mirror for `merge_tree_write`: same `_run(... "merge-tree" ...)` shape, same `"CONFLICT" in result.stdout` disambiguation between a real conflict and a genuine failure, but with `--write-tree` and returning the stdout tree-oid line instead of parsing conflict paths.
  - `is_branch_merged` (:445-467) — exact pinned-identity `commit-tree` invocation to mirror for `add_worktree_for_tree` (`-c user.name=... -c user.email=... -c commit.gpgsign=false commit-tree <tree> -p <parent> -m <msg>`).
  - `add_worktree` (:295-351) — exact `git worktree add --detach` invocation/timeout/error-message style to mirror.
  - `merge_branch` (:885-1036) — the closest full precedent (throwaway `tempfile.mkdtemp` + `worktree add --detach` + work inside it + guaranteed cleanup) — NOT reused directly (it performs a real merge+ref update, which this story's boundaries forbid), but its try/finally shape is the model for `dispatch_land.py`'s own new orchestration block.
- `src/pyforge/marshal/core/dispatch_landing.py` — NOT modified: `may_attempt_dispatch_landing` stays as-is; this story's new precondition is a `dispatch_land.py`-local check, not a widening of this pure eligibility function (no existing caller needs the new information).
- Tests: `tests/unit/test_dispatch_landing.py` — `FakeVcs`/`FakeForge`/`FakeProcess`/`BrokenForge` (:71-160) are the fixtures every existing `execute_dispatch_land` test builds on; the new tests add `merge_tree_write`/`add_worktree_for_tree`/`commits_behind`/`fetch` stubs to a `FakeVcs` subclass (mirroring `HealCapableVcs`'s pattern at :251-279) rather than widening the shared `FakeVcs` itself, to keep every pre-existing test's `FakeVcs()` construction unchanged.

## Tasks & Acceptance

**Execution:**
- `src/pyforge/marshal/ports/vcs.py` -- add `merge_tree_write` and `add_worktree_for_tree` Protocol methods (docstrings mirroring `merge_tree_conflict_paths`/`file_text_at_ref`) -- gives `dispatch_land.py` a typed contract for the two new git primitives.
- `src/pyforge/marshal/adapters/vcs_git.py` -- implement both on `GitVcs`, mirroring `merge_tree_conflict_paths` (the `--write-tree` call + conflict disambiguation) and `is_branch_merged`'s pinned `commit-tree` + `add_worktree`'s `worktree add --detach` (wrapping the tree and checking it out) -- the actual git mechanics.
- `src/pyforge/marshal/dispatch_verify.py` -- add a small public `run_verify_commands_only(effective, *, process, worktree) -> tuple[tuple[dict, ...], tuple[Finding, ...]]` that loops `effective.verify_commands.value` through the existing `_run_verify_command` -- reuses the exact per-command classification without the scope/spec-binding/cross-surface layers that don't transfer to a merge-tree diff.
- `src/pyforge/marshal/dispatch_land.py` -- in `execute_dispatch_land`, immediately before the existing `forge.merge_pr` call (:355): fetch `origin/main`, check `commits_behind`; if `> 0`, call `merge_tree_write`; if it returns a tree oid, materialize a throwaway worktree via `add_worktree_for_tree`, run `run_verify_commands_only` against it, and refuse with `MRS-DISP-044` (carrying `pr_number`/`subject`/`marshal_native=True`) on any finding, always removing the worktree in a `finally`; if `merge_tree_write` returns `None` (real conflict) or `commits_behind == 0`, fall through unchanged -- the actual fix.
- `tests/unit/test_dispatch_landing.py` -- add: (1) the 50.4/27.5 fixture (a `FakeVcs` subclass whose `merge_tree_write` returns a tree oid and whose injected `FakeProcess` fails one command only when `cwd` is the merge-tree worktree, passing on the plain branch worktree) asserting `REFUSED`/`MRS-DISP-044` naming the failure; (2) a clean-merge-and-green fixture asserting `LANDED` with no new findings; (3) a `commits_behind == 0` fixture asserting byte-identical behavior (no `merge_tree_write`/`add_worktree_for_tree` calls made at all); (4) the mutation test: with the new check's call removed/stubbed to a no-op, the 50.4/27.5 fixture lands green -- proving the check is load-bearing.
- `tests/unit/test_dispatch_verification.py` (or a new `tests/unit/test_dispatch_verify_merge_tree.py`) -- unit-test `run_verify_commands_only` directly against `FakeProcess` (one passing command, one failing command, an empty `verify_commands` tuple) -- the I/O matrix's edge cases at the smaller-grained level.

**Acceptance Criteria:**
- Given the 50.4/27.5 fixture (branch verification green, merge-tree preview red with the `bare_merge.py` `TypeError`), when `execute_dispatch_land` runs, then it returns `REFUSED` with an `MRS-DISP-044` finding naming the command and the `TypeError` text, and `pr_number`/`subject`/`marshal_native=True` are populated on the result.
- Given a fixture whose branch baseline is behind `origin/main` but the merge-tree preview is clean and green, when `execute_dispatch_land` runs, then it returns `LANDED` with no new findings and no operator action.
- Given a fixture whose branch baseline already equals `origin/main` (`commits_behind == 0`), when `execute_dispatch_land` runs, then no `merge_tree_write`/`add_worktree_for_tree` call is made and the outcome is byte-identical to the pre-51.1 code path.
- Given a fixture where `merge_tree_write` returns `None` (a real git conflict), when `execute_dispatch_land` runs, then behavior is unchanged from today (falls through to `forge.merge_pr` and the existing `MRS-DISP-038`/heal path).
- Given the 50.4/27.5 fixture with the new merge-tree-verify call stubbed out (mutation test), when `execute_dispatch_land` runs, then it returns `LANDED` -- proving the new check, not some other mechanism, is what refuses it.
- Given the throwaway worktree created for a merge-tree preview, when `execute_dispatch_land` returns or raises for any reason, then the worktree has been removed (best-effort) and no leftover `git worktree list` entry remains.

## Spec Change Log

## Review Triage Log

### 2026-09-19 — Review pass
- verdicts: 18 findings — high 0, medium 10, low 4, false 3, maybe-false 1
- findings:
  - `[medium]` `[patch]` (intent-alignment) `merge_tree_write`/`add_worktree_for_tree` have zero new tests — verified: grep of `tests/unit/test_vcs_git.py` for both names returns no hits; this package's own real-git test convention (`add_worktree`, `is_branch_merged`) is not followed for the two new methods. Grouped with the real-git-test-gap entries below; fix applied there.
  - `[medium]` `[patch]` (intent-alignment) the 50.4/27.5 acceptance fixture is only simulated (a hand-rolled fake `VcsPort`/`Process`), never proven against real git `merge-tree`/`commit-tree`/`worktree add` plumbing — same root cause as above. Fix applied there.
  - `[medium]` `[patch]` (intent-alignment) `commits_behind`/`merge_tree_write`/`add_worktree_for_tree` raising `VcsCommandError` are untested at the orchestration layer — verified: `MergeTreePreviewVcs` has no raise path for any of the three. The `commits_behind` portion is redundant with the already-tested `fetch`-raises path (identical `except` block, identical outcome), but `merge_tree_write`-raises and `add_worktree_for_tree`-raises are genuinely uncovered — grouped with the cleanup-bug entry below (adding the missing test for `add_worktree_for_tree`-raises is what surfaced that bug).
  - `[low]` `[patch]` (blind-hunter) `_describe_verify_failures` rebuilds failure text from raw `reports` fields instead of reusing `gate.classify_outcome`'s own `Finding.message`, losing the "was terminated by signal N" phrasing for a killed command and the real reason for an unresolvable command (collapsed to a generic "could not be run") — verified directly against `core/gate.py`'s `classify_outcome`. Fix: build the `MRS-DISP-044` message from `verify_findings`'s own message text instead of re-deriving it from `reports`.
  - `[false]` `[reject]` (blind-hunter) base `FakeVcs` lacks typed defaults for `merge_tree_write`/`add_worktree_for_tree`/`remove_worktree`, risking a future `AttributeError` — refuted: every current test's `commits_behind` defaults to `0`, which short-circuits `_refuse_via_merge_tree_preview` before any of the three methods are ever called; the claimed `AttributeError` requires a test that does not exist today. Speculative, not a defect in this diff.
  - `[medium]` `[patch]` (blind-hunter) no real-git integration test for `merge_tree_write`/`add_worktree_for_tree` — grouped with the intent-alignment/verification-gap findings above; fix: added real-git tests to `test_vcs_git.py` covering a clean merge, a real conflict, and that the checked-out worktree actually contains the merged content.
  - `[low]` `[patch]` (blind-hunter) `_ORIGIN_MAIN = "origin/main"` in `dispatch_land.py` duplicates the literal already defined as `_SCOPE_BASE = "origin/main"` in `dispatch_verify.py` — verified, real duplication. Fix: reuse one constant instead of two.
  - `[low]` `[patch]` (blind-hunter) `vcs.fetch(git_repo_root, _ORIGIN_REMOTE, "main")` hardcodes the literal `"main"` instead of reusing the `_MERGE_BASE` constant defined a few lines above it in the same file — verified. Fix: reuse `_MERGE_BASE`.
  - `[false]` `[reject]` (blind-hunter) the merge-tree-preview check runs after `forge.create_pr`/`update_pr`/`add_labels`, causing PR churn on every refused retry — refuted: the spec's own `<intent-contract>` "Always" bullet explicitly requires this refusal to carry `pr_number`/`subject`/`marshal_native=True` because "this refusal fires after the PR is already open and the subject is already known-marshal-native" (Story 51.2's convention) — the ordering is an explicit, read-only intent requirement, not an implementation oversight.
  - `[medium]` `[patch]` (blind-hunter) cleanup of the throwaway worktree swallows a failed `vcs.remove_worktree(...)` with a bare `except VcsCommandError: pass` and no fallback — verified against the `merge_branch` precedent this code is explicitly modeled on (`adapters/vcs_git.py:885-1036`), which falls back to `shutil.rmtree(ignore_errors=True)` + `git worktree prune` when the primary removal fails; the new code has only the first stage. Fix: added the same fallback stage.
  - `[medium]` `[defer]` (blind-hunter) the pre-existing "already landed" check (`vcs.commit_subjects(git_repo_root, _MERGE_BASE)`) still reasons from local `main` while the new check fetches and diffs against `origin/main`, so the function now holds two different freshness assumptions about "main" — verified real, but the already-landed check's own staleness predates this story and is outside its intent (fixing merge-result verification, not the already-landed check). Recorded to `deferred` frontmatter.
  - `[false]` `[reject]` (blind-hunter) `sprint-status-ledger.yaml` still says "backlog" and the Tier-2 spec frontmatter still says "ready" — refuted: promoting the ledger/Tier-2-spec status is the dispatch-land/finalize pipeline's job once this code actually merges via a real PR, not something a code-implementation diff performs.
  - `[medium]` `[patch]` (verification-gap) `merge_tree_write`/`add_worktree_for_tree` are exercised only through a hand-rolled fake (`MergeTreePreviewVcs`), never against real git — filed pre-verified per the verification-gap protocol; disposition weighed as filed (its `test_vcs_git.py::merge_tree_conflict_paths` citation was independently checked and found inaccurate — zero hits for that name in the file — but the underlying claim was re-grounded on `add_worktree`'s and `is_branch_merged`'s genuine real-git coverage, the actual established convention `add_worktree_for_tree` claims to mirror). Grouped with the real-git-test-gap entries above; same fix.
  - `[medium]` `[patch]` (edge-case-hunter) `vcs.add_worktree_for_tree` raising `VcsCommandError` leaves `preview_home` uncleaned — verified: the `except` block for that call returns immediately, before the `try/finally` that wraps `run_verify_commands_only` and calls `remove_worktree`, so a partially-created worktree is never cleaned up, violating the spec's own "removed (best-effort) before `execute_dispatch_land` returns or raises" acceptance criterion. Fix: extended the `try/finally` to cover `add_worktree_for_tree` too, plus a test asserting cleanup is attempted on this path.
  - `[medium]` `[patch]` (edge-case-hunter) `vcs.remove_worktree` raising during cleanup leaves an orphaned worktree with zero visibility — grouped with the blind-hunter finding above (missing `merge_branch`'s fallback stage); fix: added the `shutil.rmtree`+`git worktree prune` fallback.
  - `[low]` `[patch]` (edge-case-hunter) a signal-terminated verify command surfaces as `"exited -9"` instead of `"was terminated by signal 9"` — grouped with the blind-hunter `_describe_verify_failures` finding above; same fix.
  - `[maybe-false]` `[reject]` (edge-case-hunter) `origin/main` could advance again between the merge-tree preview passing and the actual `forge.merge_pr` call (a TOCTOU race) — could not verify whether this ever produces an uncaught bad outcome: GitHub's merge endpoint re-validates mergeability at merge time independent of any preview, and the window is a single function invocation wide; what would settle it is a demonstrated case where a real merge landed content the preview never saw and no downstream check caught it. If true this would only be a rare, narrow-window `low` (existing merge-time re-validation and the `MRS-DISP-038`/heal path already bound it), so rejected per the maybe-false/only-low rule rather than deferred.
  - `[medium]` `[patch]` (edge-case-hunter) `add_worktree_for_tree` failure is caught by its own `except` block, returning before the `finally`-guarded `remove_worktree` is ever reached, so no removal is ever attempted — same defect as the edge-case-hunter finding above (grouped); same fix.

## Design Notes

- **Why `commits_behind` gates instead of a file-intersection check:** the epics.md When-clause says "behind `origin/main` on any file the branch touches," but the Spec's own Binding section names exactly ONE new git primitive (the `--write-tree` sibling of `merge_tree_conflict_paths`) — not a second one for computing `origin/main`'s own touched-file set since the fork point. `commits_behind(worktree, "origin/main") > 0` is a safe superset of "behind on a touched file" (it never misses a real case, and only costs an extra merge-tree preview + verify run on the rare land that overlaps zero files with `origin/main`'s recent history) and needs no new primitive beyond what's already named. This is the reading consistent with the Binding section's explicit scope.
- **Why `verify_commands` only, not the full `evaluate_dispatch_verification`:** `changed_files`'s own diff is `git diff -M --name-status {base}...HEAD` (`adapters/vcs_git.py:654`) — the TRIPLE-DOT form, which diffs `HEAD` against `merge-base(base, HEAD)`, not against `base` itself. Pointing `worktree` at the merge-tree preview commit (parent = the branch's own tip) leaves `merge-base(origin/main, preview)` at the branch's OLD fork point, so the diff would include every file `origin/main` itself changed since that fork point — folding `origin/main`'s own independent commits into the "changed files" set and spuriously widening the scope check. Re-running only `verify_commands` sidesteps this entirely and matches the epics.md When-clause literally: "runs the station's own `verify_commands` against that tree."
- **Why the new commit is never referenced by any ref:** mirrors `is_branch_merged`'s existing `commit-tree`-for-comparison-only discipline exactly — the object exists solely so `git worktree add` has a commit-ish to check out; nothing ever points to it, and it is garbage-collected normally once the worktree referencing it is removed.

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-249`.
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py` (the hook before `forge.merge_pr`; the MRS-DISP-038 branch), `.../dispatch_verify.py::evaluate_dispatch_verification` (a merged-tree checkout is another `worktree` path), `.../ports/vcs.py` + `.../adapters/vcs_git.py` (a `--write-tree` sibling of `merge_tree_conflict_paths` that materialises the tree), `.../core/dispatch_landing.py` (pure eligibility), `.../dispatch_supervisor/__main__.py` (`_run_and_journal_landing`, only if a new journal kind is needed), tests.
Ledger key: `51-1-verification-sees-the-merge-result`.
Minted 2026-09-19 from `epics.md` so `marshal factory dispatch` (51.x) or a hand-driven `bmad-build-auto` (52.x) can resolve `spec-51-1-verification-sees-the-merge-result.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expected: pass.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- expected: pass.

## Auto Run Result

**Summary of implemented change:** before `execute_dispatch_land` calls `forge.merge_pr`, when the branch's baseline is behind `origin/main` (`commits_behind(worktree, "origin/main") > 0`), the code now fetches `origin/main`, materializes the tree `git merge-tree --write-tree origin/main <head>` would actually produce into a throwaway, unreferenced worktree (`add_worktree_for_tree`, wrapping the merge-tree oid in a pinned-identity synthetic commit so `git worktree add --detach` has a commit-ish to check out), and re-runs the station's own `verify_commands` against that materialized tree via a new public `run_verify_commands_only`. A red result refuses landing with a new `MRS-DISP-044` finding (`Verdict.ERROR`) naming the failing command and the tail of its captured output, carrying `pr_number`/`subject`/`marshal_native=True`. A branch already even with `origin/main`, or one where `merge_tree_write` reports a real conflict (`None`), falls through unchanged -- byte-identical to pre-51.1 behavior. The throwaway worktree is always removed via a two-stage best-effort cleanup (`remove_worktree`, falling back to `shutil.rmtree` + a new `prune_worktrees` primitive on failure, mirroring `merge_branch`'s own precedent) inside a single `try/finally` that also covers `add_worktree_for_tree` itself raising.

**Files changed:**
- `src/pyforge/marshal/ports/vcs.py` -- added `merge_tree_write`, `add_worktree_for_tree`, and `prune_worktrees` Protocol methods (docstrings mirroring `merge_tree_conflict_paths`/`file_text_at_ref`).
- `src/pyforge/marshal/adapters/vcs_git.py` -- implemented the three new methods on `GitVcs`: `merge_tree_write` (the `--write-tree` sibling of `merge_tree_conflict_paths`), `add_worktree_for_tree` (pinned-identity `commit-tree` + `worktree add --detach`), `prune_worktrees` (`git worktree prune`, the two-stage cleanup's fallback primitive).
- `src/pyforge/marshal/dispatch_verify.py` -- added public `run_verify_commands_only(effective, *, process, worktree)`, looping `verify_commands` through the existing `_run_verify_command` classification without the scope/spec-binding/cross-surface layers.
- `src/pyforge/marshal/dispatch_land.py` -- new `_refuse_via_merge_tree_preview` orchestration inserted immediately before `forge.merge_pr`; imports `_SCOPE_BASE as _ORIGIN_MAIN` from `dispatch_verify` instead of duplicating the literal; reuses `_MERGE_BASE` instead of a hardcoded `"main"` in the `fetch` call; `_describe_verify_failures` rewritten to build its message from each failing command's own `Finding.message` (correct for both the "never ran" and "ran and failed, including signal-terminated" cases) plus the captured-output tail when available; both new git calls and the verify run share one `try/finally` with two-stage cleanup.
- `src/pyforge/marshal/core/findings.py` -- registered `MRS-DISP-044`.
- `src/pyforge/marshal/core/verdict.py` -- classified `MRS-DISP-044` as `Verdict.ERROR` (same tier as `MRS-DISP-038`).
- `tests/unit/test_dispatch_landing.py` -- extended `MergeTreePreviewVcs` with `add_worktree_raises`/`remove_worktree_raises`/`prune_worktrees` tracking; added the 50.4/27.5 fixture, the clean-merge-and-green fixture, the `commits_behind == 0` byte-identical fixture, the mutation test, and three regression tests for the cleanup-bug fixes (`merge_tree_write` raising, `add_worktree_for_tree` raising, `remove_worktree` raising falls back to `prune_worktrees`).
- `tests/unit/test_dispatch_verify_merge_tree.py` (new) -- unit tests for `run_verify_commands_only` against `FakeProcess` (passing command, failing command, empty `verify_commands`).
- `tests/unit/test_findings.py` -- registration test for `MRS-DISP-044`.
- `tests/unit/test_vcs_git.py` -- four new real-git tests: `merge_tree_write` on a clean merge and on a real conflict, `add_worktree_for_tree` checking out the merged content (verifying both files' content, the worktree's presence in `git worktree list`, and that the synthetic wrapper commit is unreferenced by any ref), and `add_worktree_for_tree` raising `VcsCommandError` on an unresolvable parent.

**Review findings breakdown** (18 findings from intent-alignment, blind-hunter, verification-gap, edge-case-hunter -- full per-finding log in `## Review Triage Log` above):
- *Patched* (6 grouped entries, all fixed and covered by new/extended tests):
  - real-git-test-gap (medium) -- zero real-git coverage for `merge_tree_write`/`add_worktree_for_tree`, and the 50.4/27.5 fixture only ever simulated via a hand-rolled fake -- fixed with four new real-git tests in `test_vcs_git.py`.
  - add_worktree_for_tree-cleanup (medium) -- `add_worktree_for_tree` raising skipped the `try/finally` entirely, leaving a partially-created worktree uncleaned, and this path was untested -- fixed by nesting both git calls in one shared `try/finally`, plus a regression test.
  - remove_worktree-fallback (medium) -- cleanup swallowed a failed `remove_worktree` with a bare `pass` and no fallback, unlike the `merge_branch` precedent it's modeled on -- fixed with a new `prune_worktrees` primitive and a `shutil.rmtree` + prune fallback, plus a regression test.
  - message-fidelity (low) -- `_describe_verify_failures` lost "terminated by signal N" phrasing and the real "could not be run" reason -- fixed by building the message from each `Finding.message` instead of re-deriving it from raw report fields.
  - DRY nit: `_ORIGIN_MAIN` duplicated `_SCOPE_BASE` (low) -- fixed by importing the existing constant.
  - DRY nit: hardcoded `"main"` literal duplicated `_MERGE_BASE` (low) -- fixed by reusing the constant.
- *Deferred* (1): the pre-existing "already landed" check (`vcs.commit_subjects(git_repo_root, _MERGE_BASE)`) reasons from local `main` while this story's new check fetches/diffs against `origin/main` -- real inconsistency, but pre-existing and outside this story's intent; recorded in frontmatter `deferred`.
- *Rejected* (4, no code change):
  - `false` -- base `FakeVcs` lacking typed defaults for the three new methods: refuted, `commits_behind` already defaults to `0` and short-circuits every existing test before those methods are ever reached.
  - `false` -- merge-tree-preview check running after `forge.create_pr`/`update_pr`/`add_labels`: refuted, the spec's own `<intent-contract>` explicitly mandates this exact ordering (the refusal must carry `pr_number`/`subject`/`marshal_native=True` since the PR is already open).
  - `false` -- `sprint-status-ledger.yaml`/Tier-2 spec status not updated: refuted, that promotion is the landing/finalize pipeline's job once this code merges via a real PR, not a code-implementation diff's job.
  - `maybe-false` -- a TOCTOU race between the merge-tree preview passing and the actual `forge.merge_pr` call: could not be verified either way; its if-true severity is bounded to `low` by GitHub's own merge-time re-validation and the existing `MRS-DISP-038`/heal path, so rejected per the maybe-false/only-low rule rather than deferred.

**Follow-up review recommendation: `true`.** This is a first pass; three grouped patched entries were rated `medium` (real-git-test-gap, add_worktree_for_tree-cleanup, remove_worktree-fallback), meeting the "two or more medium entries patched" trigger (patched-by-verdict: medium 3, low 3). Named unverified risk: the two-stage cleanup fallback (`remove_worktree` failing, then `shutil.rmtree` + `prune_worktrees`) is only exercised against a `VcsCommandError` raised by a fake/stub in this pass's tests -- it has not been exercised against a genuine OS-level worktree-removal failure (e.g. a file actually locked or busy on disk), so a follow-up pass should add or confirm coverage for that real-filesystem case before treating the fallback as fully proven.

**Verification performed:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- **PASS** (8258 passed, 1 skipped, 12 deselected), re-run after all patches were applied.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- **PASS** (130 passed, 3 skipped), re-run after all patches were applied.

**Residual risks:**
- The deferred already-landed/local-vs-`origin/main` freshness inconsistency (see frontmatter `deferred`).
- The named unverified risk above (real-filesystem cleanup-fallback coverage), driving the `true` follow-up recommendation.
- The rejected TOCTOU race (`maybe-false`, bounded `low` if true) remains theoretically possible but unverified and unactioned, per the maybe-false/only-low rejection rule.
