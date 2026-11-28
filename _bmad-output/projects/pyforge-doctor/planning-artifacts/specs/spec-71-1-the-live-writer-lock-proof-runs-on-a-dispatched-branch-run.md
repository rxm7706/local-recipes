---
title: '71.1: The live writer-lock proof runs on a dispatched branch run'
type: 'fix'
created: '2026-11-27'
status: 'done'
story: 71-1-the-live-writer-lock-proof-runs-on-a-dispatched-branch-run
spec: spec-pyforge-doctor
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - '.github/workflows/pyforge-station-tests.yml'
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/writer_lock.py
  - src/shared/packages/pyforge-doctor/tests/unit/test_live_cutover_ledger.py
  - docs/dreams/pyforge-doctor.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `test_writer_lock_reports_this_checkout_is_the_writer` (doctor's live half) reads `git merge-base refs/remotes/origin/main HEAD` through `writer_lock.gather` (CAP-100). Story 57.3's step "Name the base tip as origin/main" names the merge commit's first parent as `origin/main` on a pull request, and a push to `main` already has the ref. A run dispatched on a branch (`workflow_dispatch`, how the push-only jobs such as `guild-container` are run before a merge) has neither: its two-commit checkout holds only the branch, so the test fails with "no merge base of origin/main and HEAD -- origin/main cannot be resolved here -- the writer lock cannot be evaluated" (runs 46072884555 and 46096009355).

**Approach:** run the step on `workflow_dispatch` too. When `refs/remotes/origin/main` is missing on a dispatched run, fetch `main` at depth 1, then deepen `main` and the dispatched commit by 25, 100 and 400 commits until `git merge-base` resolves; the step fails on the last `git merge-base` when the two never meet. A dispatch on `main` already has the ref and exits at the first check. The pull request path is unchanged.

Ledger key: `71-1-the-live-writer-lock-proof-runs-on-a-dispatched-branch-run`.

### Living CAP citations

- spec-pyforge-doctor CAP-100 (a chain write off the writer is named; its live proof; realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- The pull request and push paths of the step stay as they were.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never change the test, `writer_lock.py`, or what either asserts.
- Never add a flag, a capability or an architecture decision.

## Acceptance Criteria

**Given** a run dispatched on a branch has no `refs/remotes/origin/main`, so the live writer-lock test finds no merge base
**When** the step runs on `workflow_dispatch`, fetches `main` and deepens both sides until they meet
**Then** the merge base resolves for a branch at `main`'s tip and for a branch forked behind it, and a dispatch on `main` keeps its own ref
**And** `doctor-live-test` passes on a dispatched branch run

- **AC1 — A dispatched branch run's `doctor-live-test` passes.** Expected: both `doctor-live-test` shards conclude `success`.

  ```bash
  gh workflow run pyforge-station-tests.yml --repo rxm7706/local-recipes --ref <branch>
  ```

- **AC2 — The workflow still parses, and its pull request and push path lists still match.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/meta/test_workflow_path_filters_match.py -q
  ```

</intent-contract>

## Result (2026-11-27)

- Simulated with an alternates-backed bare remote and `git fetch --depth=2` checkouts like `actions/checkout`'s:
  - a branch one commit past `main`'s tip resolves `cf535eb132`, with no deepening;
  - a branch forked 11 commits behind `main` resolves its fork point `f5c4f2ab71` after one deepening;
  - a checkout of `main` has the ref and exits at the first check.
- On the simulated dispatched clone, `writer_lock.gather` reads OK ("is the writer") with the step. Without the step it reads the CI failure's message.
