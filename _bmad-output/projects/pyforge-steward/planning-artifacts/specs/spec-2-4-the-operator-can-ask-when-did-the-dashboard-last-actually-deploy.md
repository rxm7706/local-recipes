---
title: 'Story 2.4: The operator can ask "when did the dashboard last actually deploy?"'
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

**Problem:** After Stories 2.1-2.3, an operator running `steward deploy dashboard` has no built-in way to confirm when the dashboard last actually deployed without hand-running `git log -- docs/dashboard/`.

**Approach:** Add `last_deploy_commit` to `deploy.py` — reads the last commit that touched `docs/dashboard/` straight from `git log` (SHA + strict-ISO committer timestamp). No separate state file anywhere (FR-11's explicit constraint: git history IS the record). Wire `steward deploy status`.

## Boundaries & Constraints

**Always:**
- `last_deploy_commit` runs exactly `git log -1 --format=<sha><US><iso-date> -- docs/dashboard` and parses its stdout — no separate `.steward/`-owned state file, no cache, no memory of a prior run.
- Matches the last commit touching `docs/dashboard/` from ANY source (a `steward deploy dashboard`-created commit, a manual `git commit` after a local `dashboard-gen` run per the README's own documented workflow, or any other commit that happened to touch the path) — "last successful dashboard deploy" is a true fact about git history, not a Steward-provenance-tagged fact; nothing in this repo's history distinguishes Steward-authored commits by any marker the AC requires reading.
- No prior commit touching the path → a clear, explicit "no dashboard deploy commit found" report (`ok=True` — the absence itself is not a failure), never a crash and never a misleadingly-empty result (the AC's own wording).

**Block If:** none.

**Never:**
- No new git commit message convention or trailer added retroactively to distinguish Steward-created commits from manual ones — out of scope; the AC only asks "when did it last deploy," and every commit touching the path IS a real deploy regardless of who ran it.
- No writing of any kind — `deploy status` is a pure read.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Prior deploy commit exists | at least one commit touched `docs/dashboard/` | SHA + committer timestamp printed | No error |
| No prior deploy commit | `docs/dashboard/` untouched in this repo's history | Clear "no dashboard deploy commit found" report, `ok=True` | No error — not a crash, not a misleading empty result |
| `git log` itself fails | `cwd` not a git worktree | Nothing printed | `subprocess.CalledProcessError` → `DutyResult(ok=False, ...)` |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/deploy.py` -- add `DeployRecord`, `last_deploy_commit`; add the `status` verb to `_DEPLOY_VERBS`/`DeployDuty.run`
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` -- add `deploy status` subparser
- `src/shared/packages/pyforge-steward/tests/conformance/test_deploy_status.py` -- NEW: real scratch git repo, both matrix rows

## Tasks & Acceptance

**Execution:**
- [x] `deploy.py` -- `DeployRecord` (frozen dataclass: `sha`, `timestamp`)
- [x] `deploy.py` -- `last_deploy_commit(*, cwd) -> DeployRecord | None`
- [x] `deploy.py` -- `_run_status`; `_DEPLOY_VERBS` gains `"status"`; `DeployDuty.run` dispatches to it
- [x] `cli.py` -- `deploy status` subparser (no flags)
- [x] `tests/conformance/test_deploy_status.py` -- both matrix rows, primitive + CLI level

**Acceptance Criteria:**
- Given at least one prior deploy commit created by Story 2.2, when `steward deploy status` is run, then it prints that commit's SHA and timestamp, read from Git history (no separate state file — FR-11's "no separate state store" constraint).
- Given a repo with no prior Steward-created deploy commit, when `steward deploy status` is run, then it reports that clearly rather than crashing or printing a misleading empty result.

## Spec Change Log

- 2026-08-07: the AC's phrase "no prior Steward-created deploy commit" was read as "no prior commit touching `docs/dashboard/` at all," not "no commit whose provenance is specifically Steward" — see Design Notes for why: FR-11 gives `last_deploy_commit` no state file to record provenance in, and the README's own documented manual workflow (`generate.py` + `git commit` + `git push`) produces an equally real deploy this command should also see.

## Review Triage Log

### 2026-08-07 — Self-review (adversarial re-read before marking done)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- Confirmed `_run_status` matches its own docstring exactly: it does one
  read (`last_deploy_commit`) and one branch (`None` vs. a record) — no
  hidden write path anywhere in the `status` verb, verified by inspection
  (no `subprocess.run` call anywhere in `_run_status`/`last_deploy_commit`
  other than the single `git log`, which is read-only).
- Considered whether `last_deploy_commit`'s "any commit touching the path"
  semantics (rather than filtering to Steward-authored commits specifically)
  satisfies the AC's literal wording ("no prior Steward-created deploy
  commit") — recorded as a deliberate interpretation in this spec's own
  Spec Change Log rather than silently picked; FR-11 gives this function no
  state to record provenance in, and filtering on the exact commit message
  `commit_and_push_dashboard` writes would be a second undeclared state
  store smuggled into commit messages (this story's own Design Notes).
- `test_only_the_most_recent_dashboard_touching_commit_is_reported` proves
  `git log -1`'s ordering claim by construction (two dashboard-touching
  commits, then an unrelated one) rather than trusting the `-1` flag's
  documented behavior on faith.
- No read-modify-write race class applies here at all — `deploy status` is
  a single read-only `git log` invocation with no write anywhere in the
  path, structurally incapable of racing another concurrent invocation the
  way `keys-inventory.yaml`'s read-then-write cycle could.

### 2026-08-07 — Adversarial review pass (Blind Hunter + Edge Case Hunter, Epic 2 batch)

- intent_gap: 0
- bad_spec: 0
- patch: 1
- defer: 0
- reject: 0
- **Finding (Edge Case Hunter)**: `_run_status` reported a local commit's
  SHA/timestamp as-is even when that commit had never actually reached
  `origin` (e.g. the prior run's push failed after `deploy.py::commit_and_push_dashboard`
  had already committed — see [[spec-2-2-...]]'s own "stuck commit" fix for
  the write-side half of the same failure mode). Reporting only the local
  commit misrepresented an in-flight, not-yet-pushed change as a completed
  deploy.
- **Fix**: `_run_status` now also runs the same `git rev-list --count
  @{u}..HEAD` ahead-check `_push_pending_commit_if_ahead` uses, but
  read-only — it never pushes from `status`. When HEAD is ahead of
  `origin`, the printed summary appends `" -- HEAD is ahead of origin; the
  most recent commit(s) may not be pushed yet"` so the operator sees the
  distinction instead of a misleadingly-clean report.
- **Test**: `tests/conformance/test_deploy_status.py::test_deploy_status_notes_when_head_is_ahead_of_origin`
  — real scratch repo + real bare origin, commits to `docs/dashboard/`
  without pushing, asserts `"ahead of origin"` appears in the CLI output.
- **Re-verification (2026-08-07, after the patch):** `pixi run --frozen -e
  pyforge-steward pyforge-steward-test` -- **126 passed** (122 baseline + 4
  new tests across the Epic 2 review batch; this story's own share is the
  one `test_deploy_status_notes_when_head_is_ahead_of_origin` test noted
  above). See [[spec-2-2-nothing-happens-unless-something-actually-changed]]
  for the write-side companion fix (`_push_pending_commit_if_ahead`,
  wired into `deploy dashboard` itself) and the other three findings from
  this same review pass.

## Design Notes

**Why no Steward-provenance filter (e.g. matching the exact commit message `commit_and_push_dashboard` writes):** FR-11 explicitly rules out a separate state store, and grepping commit *messages* for a magic string would be exactly that — a second, parallel, un-declared "state store" smuggled into git history instead of a YAML file, fragile to a rebase/squash/amend changing the subject line (the same failure class `dashboard-drift-check`'s own description already documents for a DIFFERENT part of this repo — squash-merging PR #132 made Epic 10's merge subjects unreachable). Reading "the last commit that touched the path," full stop, is both simpler and matches what an operator's own `git log -- docs/dashboard/` already shows them.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` -- expected: all tests pass
- `pixi run --frozen -e pyforge-steward steward deploy status` -- expected: prints this repo's real last dashboard-touching commit

**Results (2026-08-07):** `pixi run --frozen -e pyforge-steward pyforge-steward-test` — 122 passed (114 pre-existing + 8 new in `test_deploy_status.py`).
