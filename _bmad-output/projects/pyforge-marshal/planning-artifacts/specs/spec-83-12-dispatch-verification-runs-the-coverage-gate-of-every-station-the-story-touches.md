---
title: "83.12: Dispatch verification runs the coverage gate of every station the story touches"
type: 'fix'
created: '2026-10-03'
status: 'in-progress'
baseline_revision: '2f131c2bae4fd9a7a0951ab5be1986b3ce4a9931'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py
  - scripts/coverage_gates_ci.py
  - .github/workflows/coverage-gates.yml
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** CI's `named-module-gates (<station>)` job runs `scripts/coverage_gates_ci.py` in each touched station's own environment and fails the PR when a source module the branch touched sits under the station's 80% unit floor. Dispatch verification never runs it. The station `verify_commands` run the suite without coverage, and `dispatch/*` branches skip the `pr-preflight` pre-push hook that mirrors the gate locally. So a session reports done, verification passes, the PR goes red in CI, and the fix costs a CI round trip plus a hand fix or a send-back. On 2026-10-03 PR #1773 (Story 83.10) went red this way: `pyforge.marshal.core.dispatch_retry` measured 78.1% against the 80% floor while all 10,889 tests passed.

**Approach:** Dispatch verification derives one more command per station whose `src/` the story's changes touch: that station's own coverage-gate task, `pixi run --frozen -e pyforge-<station> pyforge-<station>-coverage-gate` (each station's task already runs `scripts/coverage_gates_ci.py --base origin/main --head HEAD --suites unit` in its own env, scoped by `COVERAGE_GATES_STATIONS`). The commands are folded in where Stories 79.2 and 83.2 fold in `lint-types`, the pyforge-core suite and `deferred-work-check`, so a red result is an ordinary MRS-GATE-001 naming the command, and it is never reclassified as pre-existing (the gate measures only modules the branch touched).

Ledger key: `83-12-dispatch-verification-runs-the-coverage-gate-of-every-station-the-story-touches`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- Story 79.2 and Story 83.2 (the derived verification commands), and spec-coverage-gate-independence (the named-module gate). A defect of shipped behaviour, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a story whose changes touch `src/shared/packages/pyforge-<station>/src/` When dispatch verifies it Then it runs `pixi run --frozen -e pyforge-<station> pyforge-<station>-coverage-gate`, once, in that station's own environment
- Given a touched module under the station's unit floor When that command runs Then verification refuses with MRS-GATE-001 naming the command, and the refusal is not reclassified as pre-existing
- Given a story that touches two stations' `src/` When dispatch verifies it Then it runs each station's coverage-gate command once
- Given a story that touches no station `src/` (planning artifacts only, or only `pyforge-core`) When dispatch verifies it Then no coverage-gate command is added
- Given the derivation removed When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Derive the commands where `_verify_commands_with_surface_guard` folds in the other derived commands, from the story's changed paths. Run each station's gate in that station's own environment, through its existing `pyforge-<station>-coverage-gate` task. Read every verdict from the exit code. Pin the change with a test that fails without it.

**Never:** Never run one station's gate in another station's environment. Never lower or bypass a floor. Never add the gate for a station the story did not touch. Never change what the CI lane measures.

</intent-contract>

## Design notes (non-binding)

- scribe's coverage gate needs its Postgres (CI starts a service; locally `pixi run -e pyforge-scribe scribe-pg-up`). If the cluster is not running, the scribe command fails and the refusal names it; the operator starts the cluster and re-dispatches for land-only. Do not skip scribe's gate silently.
- Before pushing, also run `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` by hand (exit 0): it is not yet a derived command, so the spec binding cannot list it under Verification.
- The gate takes about 2-2.5 minutes for marshal (its unit suite under coverage). That is the price of catching a red gate before the push, against a CI round trip plus a session.
- `run_verify_commands_only` (the merge-tree preview, Story 51.1) shares the same derivation; the gate there diffs the preview tree against `origin/main`, which is the merge result CI will see.

## Binding

Parent: Story 79.2 and Story 83.2 (the derived verification commands).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-03 (late night) entry.
Ledger key: `83-12-dispatch-verification-runs-the-coverage-gate-of-every-station-the-story-touches`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 at the operator's request (PR #1773 went red on the coverage gate after verification passed).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- No review has run yet.
