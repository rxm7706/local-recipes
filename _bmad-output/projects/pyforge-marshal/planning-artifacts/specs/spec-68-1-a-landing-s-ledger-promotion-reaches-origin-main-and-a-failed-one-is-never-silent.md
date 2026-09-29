---
title: '68.1: A landing''s ledger promotion reaches origin/main, and a failed one is never silent'
type: 'fix'
created: '2026-09-28'
status: 'in-review'
baseline_revision: '0c8c07e6fc667f8442ab7c142a6a62bde074b228'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - scripts/pre_push_preflight.sh
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Marshal 64.1 landed on 2026-09-28 (PR #1647, merge `b4d55afeea`), but its tracked ledger still read `64-1 … backlog` on `origin/main`, and every report said `landed`. Four things combined:
- **The push dies.** The promotion publish, `VcsPort.commit_paths_onto_remote_tip`, pushes `<sha>:refs/heads/main` with a 120 s git timeout. That push runs the repository's `pre-push` hook (`scripts/pre_push_preflight.sh`, `spec-pyforge-steward:CAP-154`), which skips only branch deletes, `dispatch/*` refs and the journaled `PYFORGE_PREFLIGHT_SKIP=1` opt-out. For anything else it runs the full `pr-preflight`, in the primary checkout, never on the pushed commit, and git is killed at 120 s. 64.1's finalize ran three times with the same result.
- **The promotion hides it.** `_promote_sprint_ledger` reports a failed publish as `MRS-LAND-011` WARN by design and leaves its INTENT without an OUTCOME.
- **Finalize hides it.** Finalize exits 1 only for an ERROR finding, and its `dispatch-land-finalize-resync` observation carries no findings.
- **`dispatch land` hides it.** It runs finalize with `process.run` and never reads the exit code; `PosixProcess.run` does not raise on a non-zero exit.

Measured over this checkout's journals: since the hook landed on 2026-09-20, 0 of 9 promotion intents reached `origin/main`; before it, 74 of 74 did.

**Approach:**
- **The opt-out, proof-carrying.** `commit_paths_onto_remote_tip` gains a keyword-only `preflight_skip_reason: str | None = None`. When a caller passes one, the adapter checks the commit it built before pushing: `git diff --name-only <tip> <new>` must name no path outside the written set, and every written path must lie under `_bmad-output/projects/<slug>/planning-artifacts/`. Anything else is a `VcsCommandError` before any push. When the check passes, it sets `PYFORGE_PREFLIGHT_SKIP=1` and a `PYFORGE_PREFLIGHT_SKIP_REASON` naming the new sha, the paths and the caller's reason, for that one `git push`, through the POSIX `env` utility, exactly as `GitVcs.push` does for Story 57.1. Where `env` is absent, the push runs the preflight. With no reason, the push is unchanged.
- **Every caller names its story.** `_promote_sprint_ledger` passes the promoted keys, finalize's intake publish passes the story key, and the supervisor's `_promote_blocked_twin` passes its story key.
- **Never silent.**
  - `_promote_sprint_ledger` writes its OUTCOME `ok: false` with the error when the publish fails (AD-6).
  - Finalize carries every finding it collected, all severities, in its resync observation.
  - After the promotion step, finalize reads `origin/main`'s tracked `sprint-status-ledger.yaml` (the ref the promotion writes). When the landed key is absent, reads another status, or cannot be read, it adds `MRS-DISP-051` (ERROR, "the landed story's ledger key does not read done on origin/main"), which makes it exit 1 through its existing rule.
  - `dispatch land` keeps finalize's `ProcessResult`. A non-zero exit becomes `MRS-DISP-020` (ERROR, naming the exit code and finalize's stderr) and `DispatchLandingVerdict.REFUSED` with the PR facts, the branch a finalize launch failure already takes. Story 56.1 already renders that in `marshal status` and in `fleet-picture`'s ATTENTION as "is on main but its ledger key is not done: finish the promote + ledger".
  - A failed blocked-twin publish is journaled by the supervisor as a WARN instead of returned silently.

Ledger key: `68-1-a-landing-s-ledger-promotion-reaches-origin-main-and-a-failed-one-is-never-silent`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-277 (FR-223).
- Kinship: `spec-pyforge-marshal` CAP-267 (Story 57.1, the opt-out precedent); `spec-pyforge-steward:CAP-154` / `spec-pyforge-steward:CAP-156` (the hook and its skip journal, unchanged); `spec-pyforge-steward:CAP-159` (a faster preflight, which would still judge the primary checkout, not the pushed commit).

## Acceptance Criteria

- Given a real repository with a bare remote and a `pre-push` hook that sleeps past the push timeout unless `PYFORGE_PREFLIGHT_SKIP=1` (and then appends `PYFORGE_PREFLIGHT_SKIP_REASON` to a log) When `GitVcs.commit_paths_onto_remote_tip` publishes a ledger-only write with `preflight_skip_reason` set Then the push completes, the remote's `main` holds the commit, and the logged reason names the new sha, the ledger path and the caller's story
- Given the same fixture When the built commit also names a path outside the written set, or a written path outside `_bmad-output/projects/<slug>/planning-artifacts/` Then `VcsCommandError` is raised and the remote's `main` is unchanged (no push attempted)
- Given a publish with no `preflight_skip_reason` When it pushes Then the hook runs as today (no opt-out variables reach it)
- Given `commit_paths_onto_remote_tip` raising `VcsCommandError("git command timed out after 120.0s: …")` When `_promote_sprint_ledger` runs Then it journals the INTENT and an OUTCOME `ok: false` naming the error, appends `MRS-LAND-011`, and returns `()`
- Given that failure inside finalize for story 64.1, with `origin/main`'s ledger reading `64-1 … backlog` When `finalize_dispatch_land` runs Then its resync observation carries `MRS-LAND-011` and `MRS-DISP-051`, and it returns 1
- Given `origin/main`'s ledger unreadable after the promotion When finalize runs Then `MRS-DISP-051` names the read failure and finalize returns 1
- Given finalize exiting 1 When `execute_dispatch_land` runs Then it returns `DispatchLandingVerdict.REFUSED` with `pr_number` and `marshal_native`, and the envelope carries `MRS-DISP-020` naming the exit code and finalize's stderr
- Given that refused landing journaled for a story on `main` whose tracked ledger reads `backlog` When `fleet-picture` renders the row Then ATTENTION names the story's owed promote + ledger
- Given a promotion that reaches `origin/main` When finalize and `dispatch land` run Then finalize returns 0 and the landing is `landed` and clean, as before
- Given the exit-code read removed from `execute_dispatch_land` When the 64.1 replay runs Then it lands `landed` and the test fails (mutation)
- Given a blocked-twin publish that raises `VcsCommandError` When the supervisor promotes the twin Then a WARN naming the story and the error is journaled
- Given `MRS-DISP-051` When `test_findings.py` runs Then it is registered at the ERROR tier

## Boundaries & Constraints

**Always:** Implement only the Surface named in `epics.md` Story 68.1. Check the built commit's paths in the adapter before setting the opt-out, every time. Name the story in every reason. Read "reached `done`" from `origin/main`'s ledger, never from `_promote_sprint_ledger`'s return value alone.

**Never:**
- Do not change `scripts/pre_push_preflight.sh`, `.pre-commit-config.yaml` or `pr-preflight`; the hook is steward's.
- Do not set the opt-out for any push but these publishes, and never process-wide (no `os.environ` write).
- Do not raise the push timeout to outlast the preflight.
- Do not rewrite, revert or re-merge a landed PR because its bookkeeping failed.
- Do not change `pyforge-core`'s process primitive here. A git process killed on timeout leaving its hook's children running is `DW-marshal-git-timeout-orphans-hook-children-2026-09-28` (spec-pyforge-core).
- Do not hand-edit `sprint-status-ledger.yaml` or `SPEC.md`; do not run `scripts/bmad-switch`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| ledger promotion, hook present | reason set; ledger-only commit | push completes; hook logs the reason | none |
| extra path in the commit | diff names a path not written | refused before push | `VcsCommandError` → `MRS-LAND-011` |
| path outside planning-artifacts | a write to `src/…` with a reason | refused before push | `VcsCommandError` |
| no reason | any caller that passes none | pushes as today, preflight runs | as today |
| no `env` utility | reason set, `env` absent | pushes through the preflight | as today |
| push times out | 64.1's shape | OUTCOME `ok: false`; `MRS-LAND-011` + `MRS-DISP-051`; finalize 1; land REFUSED `MRS-DISP-020` | ATTENTION: finish the promote + ledger |
| key already done on `origin/main` | converged ledger | no promotion; finalize 0 | none |
| `origin/main` unreadable | fetch or read fails | `MRS-DISP-051` naming the failure; finalize 1 | never a clean `landed` |
| blocked-twin publish fails | `VcsCommandError` | WARN journaled | never silent |

</intent-contract>

## Code Map

All paths under `src/shared/packages/pyforge-marshal/` (`src/pyforge/marshal/` for code, `tests/` for tests).

- `src/pyforge/marshal/ports/vcs.py` (`commit_paths_onto_remote_tip`, ~L526) -- port signature and docstring gain keyword-only `preflight_skip_reason`.
- `src/pyforge/marshal/adapters/vcs_git.py` (`GitVcs.commit_paths_onto_remote_tip`, ~L1309; precedent `GitVcs.push` ~L625-647, Story 57.1) -- the check-then-`env` opt-out. Reuse `shutil.which("env")`, `_GIT_FETCH_TIMEOUT_S` (unchanged), `VcsCommandError`. `commit_paths` (~L804) commits only the named paths.
- `src/pyforge/marshal/cli/land.py` (`_promote_sprint_ledger`, ~L1320-1539) -- INTENT at ~L1485, publish at ~L1497, `except VcsCommandError` at ~L1504 returns `()` with no OUTCOME today. `_parse_sprint_ledger_statuses` (~L1247) and `_LEDGER_DONE_STATUS` are reused by finalize. Two more callers (`run_land`, ~L613 and ~L1025) inherit the fix.
- `src/pyforge/marshal/dispatch_land_finalize/__main__.py` (`_run_deferred_work_intake` ~L50-150, `finalize_dispatch_land` ~L155-266) -- intake publish names the story; new ledger read after `_promote_sprint_ledger`; the observation payload (~L251) carries every finding; exit rule (~L261) is ERROR-only and stays.
- `src/pyforge/marshal/dispatch_land.py` (`execute_dispatch_land`, finalize `process.run` ~L1045-1079) -- keep the `ProcessResult`; non-zero -> `MRS-DISP-020` + REFUSED, the same return shape the `ProcessError` branch already has.
- `src/pyforge/marshal/dispatch_supervisor/__main__.py` (`_promote_blocked_twin` ~L742-795, one call site ~L1747; journal idiom `_journal_dispatch_blocked` ~L575 and `_append_entry`) -- name the story; journal a WARN OBSERVATION on `VcsCommandError` and return the advanced counter.
- `src/pyforge/marshal/core/findings.py` (MRS-DISP registry ~L1802-1811) and `core/verdict.py` (~L1170-1177) -- register `MRS-DISP-051` ERROR.
- `scripts/pre_push_preflight.sh` -- READ ONLY. Its `journal_skip` writes `$PYFORGE_PREFLIGHT_SKIP_REASON` as the last tab-separated field, so a reason carries no tab or newline.
- Tests: `tests/unit/test_vcs_git.py` (real git; `vcs`, `repo`, `remote` fixtures, ~L1931), `tests/unit/test_land.py` (fake at ~L148), `tests/unit/test_dispatch_land_finalize.py` (`_StubVcs` ~L21, `_FakeIntakeVcs` ~L338), `tests/unit/test_dispatch_landing.py` (`FakeProcess` ~L173, `BrokenProcess`), `tests/unit/test_dispatch_supervisor_blocked_halt.py` (`FakeVcs` ~L74, `_promote_blocked_twin` tests ~L443-600), `tests/unit/test_dispatch_supervisor_main_loop.py` (fake ~L257), `tests/unit/test_findings.py` (~L351), `tests/meta/test_fleet_picture_landing_findings.py`, `tests/meta/test_local_branch_refs_are_full_refnames.py` (`_NOT_A_REF` must classify the new `str` parameter).

## Tasks & Acceptance

**Execution:**
- `src/pyforge/marshal/ports/vcs.py` -- add keyword-only `preflight_skip_reason: str | None = None`; document the proof and the no-`env` fallback -- the port is the contract.
- `src/pyforge/marshal/adapters/vcs_git.py` -- with a reason set: refuse before any write or fetch when a written path is not `_bmad-output/projects/<slug>/planning-artifacts/...` in normalized form; after the commit, refuse when `git diff --name-only -z <tip> <new>` names a path outside the written set; then push through `env PYFORGE_PREFLIGHT_SKIP=1 PYFORGE_PREFLIGHT_SKIP_REASON=<new sha, paths, reason>` when `env` exists. No reason: byte-identical push -- the opt-out is proof-carrying, never blanket.
- `src/pyforge/marshal/cli/land.py` -- pass the promoted keys (wave keys on a feed-only sync) as the reason; on `VcsCommandError` write OUTCOME `ok: false` + `error` before the `MRS-LAND-011` WARN and `return ()` -- AD-6, no INTENT without an OUTCOME.
- `src/pyforge/marshal/dispatch_land_finalize/__main__.py` -- intake publish passes the story; after the promotion, fetch and read `origin/main`'s ledger and add `MRS-DISP-051` (ERROR) when the key is absent, not `done`, or unreadable; the observation carries every finding.
- `src/pyforge/marshal/dispatch_land.py` -- read the finalize exit code; non-zero -> `MRS-DISP-020` (exit code + stderr) and REFUSED with the PR facts.
- `src/pyforge/marshal/dispatch_supervisor/__main__.py` -- `_promote_blocked_twin` passes the story and journals a WARN naming story and error on a failed publish.
- `src/pyforge/marshal/core/findings.py`, `core/verdict.py` -- register `MRS-DISP-051` at ERROR.
- Tests (files under Code Map) -- one test per I/O-matrix row and per Acceptance Criterion above; update each fake `VcsPort` and `_StubVcs` for the new keyword and the two reads finalize now makes.

**Acceptance Criteria:**
- Given the Acceptance Criteria in the intent contract, when `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` runs, then every one has a passing test and the suite is green.

## Spec Change Log

## Review Triage Log

## Design Notes

- The reason is a plain string with the full new sha, the sorted written paths and the caller's reason, with no tab or newline (the hook's log is tab-separated).
- The written-path check runs before any file is written: a `../` path would otherwise be written outside the throwaway worktree before the check saw it.
- `MRS-DISP-051` reads `origin/main` with a fresh `vcs.fetch` and the full refname (`ORIGIN_MAIN`), never the short name (Stories 57.1 / 60.1).
- The supervisor's twin WARN reuses `MRS-LAND-011` (a promotion publish that could not land); no code beyond `MRS-DISP-051` is minted.

## Source

Contract authored from the operator's 2026-09-28 direction after marshal 64.1 landed with its ledger unpromoted, and `spec-pyforge-marshal` CAP-277 with its 2026-09-28 (later) direction entry in the Spec's `.memlog.md` (the journals, the file:line evidence and the measured loss), decomposed the same session as Epic 68's mint.

## Binding

Parent Spec capability: `spec-pyforge-marshal` CAP-277 (FR-223).
Ledger key: `68-1-a-landing-s-ledger-promotion-reaches-origin-main-and-a-failed-one-is-never-silent`.
Ledger status at mint: `backlog`.
Deferred-work row filed with this story, closed elsewhere: `DW-marshal-git-timeout-orphans-hook-children-2026-09-28` (spec-pyforge-core).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Local run form (this dispatch worktree has no `.pixi/envs`; never delete `.pixi/`, its `config.toml` is tracked):** from the worktree root, run the primary checkout's marshal env against the worktree's sources:
`PYTHONPATH="$PWD/src/shared/packages/pyforge-marshal/src:$PWD/src/shared/packages/pyforge-core/src" /home/rxm7706/UserLocal/Projects/Github/rxm7706/local-recipes/.pixi/envs/pyforge-marshal/bin/python -m pytest src/shared/packages/pyforge-marshal/tests -q -m "not slow" -p no:cacheprovider` -- expected: pass. Read the verdict from the exit code, never through a pipe. Do not `git commit` or push; the run commits.

**Manual checks:**
- After the first landing through this story's code, `origin/main`'s `sprint-status-ledger.yaml` reads that story `done` in a `marshal: promote sprint-status ledger` commit, and `.steward/preflight-skips.log` names that commit's sha and the story.
