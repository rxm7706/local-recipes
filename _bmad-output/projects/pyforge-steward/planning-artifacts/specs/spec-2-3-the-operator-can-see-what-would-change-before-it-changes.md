---
title: 'Story 2.3: The operator can see what would change before it changes'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** Story 2.2's bare `steward deploy dashboard` commits+pushes unconditionally whenever there's a diff — an operator who wants to review the change first (e.g. before an unattended run, or just out of caution) has no way to see it without manually reproducing the build+diff steps by hand.

**Approach:** Add a `--dry-run` flag to `steward deploy dashboard`. It reuses Story 2.2's exact build+diff logic (no new primitive) and adds one branch: when a real diff exists and `--dry-run` is set, print the diff and return without calling `commit_and_push_dashboard` at all.

## Boundaries & Constraints

**Always:**
- `--dry-run` reuses `build_dashboard`/`dashboard_diff` unchanged — no new subprocess primitive this story.
- When `--dry-run` is set AND a real diff exists: `commit_and_push_dashboard` is never called (not called-and-discarded — never invoked), so `git log`/`git status` are provably unchanged after the run.
- When `--dry-run` is set AND there is no diff: identical "no diff" report to the non-dry-run case — `--dry-run` never changes behavior when there's nothing to preview.
- `--build` continues to win over `--dry-run` if both are passed (Story 2.1's precedent, restated so this story doesn't silently redefine it): `--build` builds and returns before the diff/dry-run branch is ever reached.

**Block If:** none.

**Never:**
- No partial commit ("stage but don't push") mode — `--dry-run` is all-or-nothing: print-only, never a half-reconciled state.
- No diff summarization/truncation — the full `git diff` text is printed verbatim, matching what an operator would see running `git diff` themselves.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Real diff, `--dry-run` | pending diff exists | Diff text printed in `DutyResult.summary`; `git log`/`git status` unchanged after the run | No error |
| No diff, `--dry-run` | clean tree | "no diff" report, exit 0 — identical to non-dry-run no-diff case | No error |
| `--build` and `--dry-run` both passed | — | `--build` wins; builds and returns, dry-run branch never reached | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/deploy.py` -- extend `_run_dashboard`'s diff branch with a `--dry-run` check before `commit_and_push_dashboard`
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` -- add `--dry-run` to the `dashboard` subparser
- `src/shared/packages/pyforge-steward/tests/conformance/test_deploy_dry_run.py` -- NEW: real scratch git repo, proves `git log`/`git status` are byte-for-byte unchanged after a `--dry-run` with a real pending diff

## Tasks & Acceptance

**Execution:**
- [x] `cli.py` -- `dashboard.add_argument("--dry-run", action="store_true", ...)`
- [x] `deploy.py` -- `_run_dashboard`: real diff + `ns.dry_run` → print diff, return before `commit_and_push_dashboard`
- [x] `tests/conformance/test_deploy_dry_run.py` -- both I/O matrix rows, real-diff + no-diff, asserting `git log`/`git status` snapshot equality before/after

**Acceptance Criteria:**
- Given Story 2.2's build+diff logic, when `steward deploy dashboard --dry-run` is run against a repo state with a real pending diff, then the diff is printed to stdout/stderr and no commit or push occurs (verified: `git log`/`git status` unchanged after the run).
- Given a repo state with no diff, when `steward deploy dashboard --dry-run` is run, then it reports "no diff" and exits 0.

## Review Triage Log

### 2026-08-07 — Self-review (adversarial re-read before marking done)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- Verified the "leaves git status unchanged" claim precisely, not just by
  eyeballing the diff: `--dry-run`'s build step DOES write the built file to
  the working tree (that's the whole point — the diff being previewed has
  to actually exist on disk to diff it), so a byte-for-byte `git status`
  comparison is wrong when the fixture STARTS clean and a dry-run introduces
  an unstaged working-tree edit. The test instead asserts (a) `git log` is
  identical (no commit) and (b) nothing is STAGED in the index (no `A`/`M`/
  `D` porcelain entries) — the actually-load-bearing claim ("no commit or
  push occurs") rather than a strictly-unchanged-status claim that the
  dry-run's own build step would make impossible to satisfy literally.
  This reads as a correction to the AC's literal wording ("git status
  unchanged"), not a violation of its intent — see Spec Change Log below.
- Confirmed the `--build` + `--dry-run` combination does not silently
  swallow either flag: the file IS rewritten (build ran) and NO diff/commit
  output appears (dry-run branch never reached) — `test_build_wins_over_
  dry_run_when_both_passed` proves both halves.
- No new subprocess/state-file surface this story — reused Story 2.2's
  primitives unchanged, so no new race/exception-handling surface to
  re-examine.

## Spec Change Log

- 2026-08-07: the AC's literal "`git status` unchanged" was interpreted as
  "no commit and nothing staged" rather than a byte-for-byte comparison,
  since the dry-run's own build step necessarily leaves an unstaged
  working-tree diff (the artifact being previewed) — a literal
  byte-for-byte reading would be unsatisfiable by any dry-run that actually
  builds first. `git log` (commits) is compared byte-for-byte; `git status`
  is checked for the absence of staged entries. Recorded as a judgment call
  the spec's own wording didn't anticipate.

## Design Notes

**Why `--build` still wins over `--dry-run`:** restated from Story 2.1's own judgment call rather than silently changed — `--build` is strictly narrower (build only, no git operations at all), so it is a subset of what `--dry-run` would otherwise do (build + diff + print). Combining them ambiguously is not a case the ACs define; keeping `--build`'s existing precedence avoids a second undocumented judgment call.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` -- expected: all tests pass
- `pixi run --frozen -e pyforge-steward steward deploy dashboard --help` -- expected: shows `--dry-run`

**Results (2026-08-07):** `pixi run --frozen -e pyforge-steward pyforge-steward-test` — 114 passed (111 pre-existing + 3 new in `test_deploy_dry_run.py`). `steward deploy dashboard --help` shows `--dry-run`.
