---
title: "99.2: Dispatch-verification tests run on a fixture root and name their findings when they fail"
type: 'fix'
created: '2026-10-12'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-99-1-seed-check-probes-its-tools-at-once-and-its-budget-tests-hold-under-load.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verification.py
  - .claude/memory/feedback/the-local-pr-preflight-marshal-lane-pyforge-marshal-test-can.md
---

<intent-contract>

## Intent

**Problem:** `tests/unit/test_dispatch_verification.py::test_evaluate_dispatch_verification_pre_existing_packaging_gate_warns`
(`:1712`-`:1744`) went red in the full local `pr-preflight` marshal lane on two branches on 2026-10-12. The first was
`chain-ci-pause-control-plane-2026-10-12` (twice, per team memory). The second was `hygiene-memory-index-prune`, a
diff that touched no marshal file. Each time it read `refused` where it expects `verified`. It passes alone, and CI's
marshal-test is green on the same trees. Line numbers below are at `c447946b3f`.

**What is known, and what is not:**
- The failure prints only the verdict: `assert <DispatchVeri...ED: 'refused'> == <DispatchVeri...D: 'verified'>`.
  It never names the finding that made the verdict `refused`. So two red runs left no evidence of their cause.
- The test passes the live checkout as `repo_root` (`_REPO_ROOT`, `:47`-`:49`, found by walking up from the test
  file). It is one of 30 calls in the module that do so.
- Inside `evaluate_dispatch_verification` (`dispatch_verify.py:753`-`:1053`), `repo_root` reaches two places. One is
  the injected `vcs` port, which this test fakes. The other is `_load_commit_msg_hook_module` (`:75`-`:103`), which
  executes the live `scripts/commit_msg_hook.py`. It caches the loaded module in the module-level
  `_COMMIT_MSG_HOOK_CACHE` (`:72`), keyed on `(worktree, repo_root)`, and nothing in the test suite clears that cache.
- Reproduction failed three ways on 2026-10-12, so the cause is not proven:
  - the test file alone, serially and under `-n auto`;
  - the full `pyforge-marshal-test` lane with twelve busy-loop processes beside it;
  - the full lane twice, beside the steward, doctor and detectors lanes.

  In every case the test carried a debug assertion that prints its findings.
- Team memory's hypothesis is the hook cache. That is plausible but not shown: each test's `worktree` is its own
  `tmp_path`, so the cache key differs between tests.

**Approach:** remove the live checkout from the test's inputs, so whatever the live tree holds at that moment cannot
reach a verdict. Isolate the cache. Make every verdict assertion in the module name its findings when it fails, so the
next red explains itself instead of costing another investigation.

### Living CAP citations

- **Shipped behaviour.** These are tests of the dispatch-verification gates that Story 28.22 (the pre-existing
  packaging gate this test pins) and Stories 83.17 and 83.24 (the commit-attribution check that loads the hook) shipped
  under `spec-pyforge-marshal`'s dispatch capabilities. No product behaviour changes. No CAP is minted, and no
  `SPEC.md` text changes.
- **No flag.** This is a test-only `fix` (`spec-feature-flag-governance` Q1).
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, 2026-10-12 (the marshal suite under load), and the
  operator's ask the same day: "start the flaky marshal tests fix".

## Acceptance Criteria

- **AC1 — A failed verdict names its findings.** Every assertion in `test_dispatch_verification.py` that compares
  `judge_dispatch_verification(...)` with an expected verdict goes through one helper. When the helper fails, its
  message lists every finding's code, severity and message. A unit test feeds the helper an envelope whose verdict
  differs from the expected one, catches the `AssertionError`, and asserts that each finding's code appears in the
  message.
- **AC2 — No test in the module reads the live checkout.** A fixture builds a repo root under `tmp_path` that holds a
  copy of `scripts/commit_msg_hook.py`, the one file the evaluated path reads from `repo_root`. The module's tests
  that call `evaluate_dispatch_verification`, `check_branch_commit_attribution` or `_load_commit_msg_hook_module` take
  that root. `_REPO_ROOT` remains only as the source the fixture copies from. A meta assertion in the module fails if a
  call passes `repo_root=_REPO_ROOT`.
- **AC3 — The hook cache is per test.** An autouse fixture clears `dispatch_verify._COMMIT_MSG_HOOK_CACHE` before and
  after each test in the module. A test loads the hook twice for the same `(worktree, repo_root)` with the fixture
  root's hook file changed in between, and asserts that the second load reads the changed file.
- **AC4 — The flaky test pins its findings, not only its verdict.** `test_evaluate_dispatch_verification_pre_existing_packaging_gate_warns`
  asserts the exact set of finding codes the envelope carries, besides `MRS-GATE-001` being absent and
  `PRE_EXISTING_GATE_CODE` being present. An unexpected `ERROR` finding then fails with its own code.
- **AC5 — Mutation.** Each change below makes a named test fail:
  - Pass `repo_root=_REPO_ROOT` again in any call: AC2's meta assertion.
  - Remove the cache clearing: AC3's reload test.
  - Drop the finding list from the helper's message: AC1's test.

## Boundaries & Constraints

**Always:**
- Keep each test's intent. The module's assertions about codes, verdicts and data keys stay, and only their inputs
  move to the fixture root.
- Put the shared fixture where the module can use it. That is `tests/unit/conftest.py` if it fits that file's
  conventions, or else the module itself.
- Read every verdict from the exit code, never through a pipe.
- Reconcile every governed path on the memlogs of the Specs that govern it (spec-pyforge-marshal, and
  spec-pyforge-core, which co-governs station `src/`), then stamp scoped (AGENTS.md pre-PR item 5).

**Never:**
- Never change `dispatch_verify.py`'s behaviour in this story. A product fix found while doing it is recorded in the
  Spec Change Log and on the memlog, and it is chained as its own story.
- Never `skip`, `xfail` or `flaky`-rerun a test, and never mark one `slow` to take it out of the default lane.
- Never weaken an assertion to make it pass.

**Residual risk:**
- If the flake's cause lies outside `repo_root`, it can still recur. AC1 and AC4 make it name its cause when it does.
  Record that, if it happens, as a new memlog entry and a new story.

## I/O & Edge-Case Matrix

| Input | Before | After |
|---|---|---|
| `repo_root` in the module's tests | the live checkout | a `tmp_path` fixture root holding a copy of the hook |
| `_COMMIT_MSG_HOOK_CACHE` between tests | never cleared | cleared before and after each test |
| A verdict mismatch | prints only the two verdicts | prints every finding's code, severity and message |

</intent-contract>

## Binding

- Parent Spec capabilities: `spec-pyforge-marshal`'s dispatch-verification capabilities, as shipped by Stories 28.22,
  83.17 and 83.24. This story changes no behaviour. No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-12 (the marshal suite under load) entry.
- Epic: Epic 99 (new), minted with Story 99.1.
- Ledger key: `99-2-dispatch-verification-tests-run-on-a-fixture-root-and-name-their-findings-when-they-fail`.
- Ledger status at mint: `backlog`.
- Deps: none. Story 99.1 touches different files.
- Surface: `marshal-policy.toml` `[epic_surfaces]."99"`, added with this mint.
- Spec: the `spec-pyforge-marshal` memlog records the evidence, the failed reproductions and this mint.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, with AC1-AC4's tests (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-marshal python -m pytest -q -n auto src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verification.py` five times — expected: 5 of 5 exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlogs and scoped stamps.
- The three mutations of AC5 — expected: each fails its named test. Restore each.

## Named, not fixed here

- **Six more modules read the live checkout.** `test_dispatch_cfe_commit.py`, `test_dispatch_environment_yaml.py`,
  `test_dispatch_spec_frontmatter.py`, `test_dispatch_verify_fix.py`, `test_dispatch_ruff_format_trees.py` and
  `test_dispatch_landing.py` also use a `_REPO_ROOT` found by walking up from the test file. None of them has been
  seen to flake. They can adopt AC2's fixture once it exists.
- **Doctor's 5 s budget test.** `pyforge-doctor`'s `tests/unit/test_check_speed_budget.py` failed in both 2026-10-12
  preflight runs (median 5.76 s under load) and passes alone. It is doctor's test, so it belongs on doctor's chain.

## Spec Change Log

- 2026-10-12: minted with Story 99.1 at the operator's ask "start the flaky marshal tests fix". It is evidence-first
  because three reproduction attempts failed (listed above).

## Review Triage Log

- No review has run yet.
