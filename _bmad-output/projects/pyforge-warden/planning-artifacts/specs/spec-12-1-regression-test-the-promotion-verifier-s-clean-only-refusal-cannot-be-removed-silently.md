---
title: 'Story 12.1: Regression test — the promotion verifier''s clean-only refusal cannot be removed silently'
type: 'test'
created: '2026-09-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
baseline_revision: 'e866da4ed6f94facde6ceb37975113d6eed142fa'
---

<intent-contract>

## Intent

**Problem:** `scripts/platform-deploy-verify-promotion.py` is the estate's only
fail-closed deploy gate (`warden_status != "clean"` refusal, shipped in
`1016f4e763`), but no test exercises it — a silent removal of those three lines
would restore the Dream's third structural gap with zero CI signal.

**Approach:** Add a behavioral regression test beside the platform CI test lane
that invokes the real verifier script with synthetic promotion JSON fixtures,
proving non-`clean` verdicts are refused (naming the driver finding id) and
`clean` is accepted — without asserting on source text.

## Boundaries & Constraints

**Always:** Exercise `scripts/platform-deploy-verify-promotion.py` itself via
subprocess with temp promotion artifacts and the same env vars
(`PROMOTION_JSON`, `PLATFORM_DIGEST`, `SIDECAR_DIGEST`, `MCP_HOST_DIGEST`) the
deploy workflow uses. Host the test in `src/platform/tests/` so it runs in the
existing `platform-ci.yml` `test` job — that workflow already path-filters
`scripts/platform-deploy-verify-promotion.py`, so edits to the gate re-run the
guard. The test asserts the existing gate only; it must not compute a second
promotion verdict.

**Never:** Do not assert on the script's source text (no `grep`/`read_text`
checks for `!= "clean"`). Do not add a third CI lane. Do not relax the verifier
or introduce a deploy-side waiver override. Do not move the script into
pyforge-warden.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Clean verdict | Promotion JSON with matching digests and `warden_status: clean` | Exit 0, success message on stdout | No error expected |
| Non-clean top-level status | `warden_status` is `indeterminate`, `warn`, or `fail` with matching digests | Exit non-zero; stderr names status and driver finding id | `::error::` line on stderr |
| Non-clean nested status | No top-level `warden_status`; `warden.status.value` is non-`clean` | Exit non-zero; stderr names status and driver finding id | Same as above |
| Missing verdict object | Promotion JSON lacks a `warden` object | Exit non-zero before digest checks | `::error::` on stderr |

</intent-contract>

## Code Map

- `scripts/platform-deploy-verify-promotion.py:17-56` — the verifier under test (`status != "clean"` gate at lines 31-36; driver finding id in refusal message) — read-only.
- `.github/workflows/platform-ci.yml:96,116,252` — path filter includes the script; `test` job runs `python -m pytest -v` from `src/platform` — the PR gate lane.
- `.github/workflows/platform-deploy.yml:53` — deploy job invokes the same script — read-only context.
- `scripts/platform-ci-local.sh:209-214` — local replay invokes the verifier the same way — read-only.
- `src/platform/tests/test_deploy_verify_promotion_clean_only.py` (NEW) — Story 12.1 regression suite; subprocess pattern matches `test_chart_invariants.py` / `test_openfeature_file_flags.py`.
- `_bmad-output/projects/pyforge-warden/planning-artifacts/sprint-status-ledger.yaml` — flip `12-1-regression-test-the-promotion-verifier-s-clean-only-refusal-cannot-be-removed-silently` from `backlog` to `done` after implementation.

## Tasks & Acceptance

**Execution:**
- `src/platform/tests/test_deploy_verify_promotion_clean_only.py` — add subprocess tests covering clean acceptance, each non-`clean` rung (`indeterminate`, `warn`, `fail`), nested-status fallback, and missing `warden` object — satisfies the CAP-5 regression guard without source-text assertions.
- `_bmad-output/projects/pyforge-warden/planning-artifacts/sprint-status-ledger.yaml` — promote story 12.1 to `done` via Tier-3 feed + `sprint-ledger-sync`.

**Acceptance Criteria:**
- Given the verifier as it stands on `main`, when the test suite runs, then a promotion record whose `warden_status` is `indeterminate`, `warn`, `fail`, or absent (with non-clean nested status) is refused with a non-zero exit and stderr naming the driver finding id.
- Given a promotion record whose status is `clean` with matching digests, when the verifier runs, then it exits 0.
- Given the regression tests, when a maintainer deletes or weakens the `!= "clean"` gate (accepting `warn`, turning refusal into a log-only warning, or dropping the check), then at least one test fails — proven by exercising the script, not by reading its source.
- Given `platform-ci.yml`, when a PR touches `scripts/platform-deploy-verify-promotion.py` or `src/platform/tests/test_deploy_verify_promotion_clean_only.py`, then the `test` job schedules these tests.
- Given the full change, when no second promotion verdict is introduced anywhere, then the tests only assert the existing gate's behavior.

## Spec Change Log

## Review Triage Log

### 2026-09-10 — Review pass
- verdicts: 12 findings — high 0, medium 0, low 4, false 5, maybe-false 0
- findings:
  - `[low]` `[patch]` Parametrize used fictional `"fail"` status instead of warden lattice tokens — replaced with `error` and `policy-violation`.
  - `[low]` `[patch]` Refusal tests did not assert the `::error::` GitHub Actions prefix required by the I/O matrix — added `_assert_refused` helper and prefix checks on all refusal paths.
  - `[low]` `[patch]` Nested-status refusal test omitted the `"does not promote"` suffix assertion present on the top-level test — unified via `_assert_refused`.
  - `[low]` `[patch]` No case for conflicting top-level vs nested status or for a present `warden` object with no resolvable status — added `test_top_level_status_wins_over_conflicting_nested_clean` and `test_missing_resolved_status_is_refused`.
  - `[false]` `[reject]` Ledger flip missing from diff — refuted: `sprint-status-ledger.yaml` was updated in the same run before finalize.
  - `[false]` `[reject]` `"fail"` refusal untested leaves real rungs unexercised — partially refuted by patch; remaining lattice tokens now covered; epic wording used colloquial "fail" but verifier is string-compare only.
  - `[false]` `[reject]` Subprocess calls need a timeout — rejected: no hung-verifier incident; other platform tests are inconsistent on this; adding timeout is speculative complexity.
  - `[false]` `[reject]` Edge strings like `""` or whitespace-padded `"clean"` must be fixture-tested — rejected: story requires behavioral proof of the `!= "clean"` gate, not exhaustive string normalization; empty string is still non-clean and covered indirectly.
  - `[false]` `[reject]` `_VERIFY_SCRIPT.is_file()` precondition guard required — rejected: script is repo-tracked and path-filtered; failure mode is immediate subprocess error, acceptable for this guard.
  - `[false]` `[reject]` Intent requires editing `platform-ci.yml` to prove PR gating — rejected: spec Design Notes document inherited path filters; no workflow change needed for the lane contract.

## Design Notes

**Suite choice:** `src/platform/tests/` over
`pyforge-warden/tests/integration/` because `pyforge-station-tests.yml` does not
path-filter `scripts/` — a warden-hosted test would not re-run when the three
gate lines change. Platform CI already watches the script and runs this pytest
tree on every matching PR.

## Verification

**Commands:**
- `cd src/platform && python -m pytest tests/test_deploy_verify_promotion_clean_only.py -v` — expected: all tests pass.
- `pixi run -e pyforge-warden pyforge-warden-test` — expected: unchanged green (no warden package edits).

## Auto Run Result

**Summary:** Added a platform CI regression suite that subprocess-invokes
`scripts/platform-deploy-verify-promotion.py` with synthetic promotion JSON,
locking the deploy gate's clean-only refusal, driver-id naming, top-level status
precedence, and `::error::` stderr shape — without source-text assertions or a
second verdict.

**Files changed:**
- `src/platform/tests/test_deploy_verify_promotion_clean_only.py` (new) — 12 behavioral tests covering clean acceptance, four real non-clean lattice tokens at top-level and nested-only paths, conflicting status precedence, missing resolved status, and missing `warden` object.
- `_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-12-1-regression-test-the-promotion-verifier-s-clean-only-refusal-cannot-be-removed-silently.md` (new) — story contract spec.
- `_bmad-output/projects/pyforge-warden/planning-artifacts/sprint-status-ledger.yaml` — flipped story 12.1 from `backlog` to `done`.

**Review findings breakdown:** 4 low patches applied (real status tokens, `::error::` + message symmetry, conflicting-status and null-status cases). 5 false/rejected (ledger already updated, timeout/edge-string/precondition guards, workflow edit not required). 0 deferred.

**Follow-up review recommendation:** `false` — only low-severity patches; no medium/high findings.

**Verification performed:**
- `pixi run -e platform-ci-test python -m pytest tests/test_deploy_verify_promotion_clean_only.py -v` from `src/platform` — 12 passed.
- I/O matrix rows mapped to passing tests (clean, non-clean top-level, nested-only, missing warden, refusal stderr shape).

**Residual risks:** None identified for the regression-guard scope. Tier-3 `sprint-status.yaml` feed is absent in this worktree; ledger was updated directly (same pattern as Story 11.1 when no feed exists).
