---
title: "24.1: CFE's host-gate tests pass in any developer shell"
type: 'fix'
created: '2026-09-29'
status: 'done'
baseline_revision: '3e047430cf'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - docs/dreams/pyforge-mason.md
  - .claude/skills/conda-forge-expert/SKILL.md
  - .claude/skills/conda-forge-expert/tests/conftest.py
  - .claude/skills/conda-forge-expert/scripts/_http.py
  - .claude/skills/conda-forge-expert/scripts/inventory_channel.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the credential host gate decides which hosts may receive a JFrog credential from an allowlist derived at
call time: every `*_BASE_URL` env var that is set, plus npm's own registry vars, minus the public default hosts.
`_http._configured_enterprise_hosts()`, `inventory_channel._fallback_configured_enterprise_hosts()` and
`dependency-checker.py`'s `_auth_headers` all build it that way. So any such var the test runner's shell exports joins
the set a test asserts. A Claude Code shell exports `ANTHROPIC_BASE_URL`. On 2026-09-29 a local
`pixi run -e pyforge-guild pr-preflight` failed 1 of 9152 tests on
`test_inventory_channel_auth_host_gate.py::TestInventoryChannelFallbackAuthHostGate::test_malformed_base_url_does_not_crash_the_allowlist_scan`,
which asserts `_fallback_configured_enterprise_hosts() == {"good.example.com"}` and got `api.anthropic.com` as well.
CI exports no such var, so it stayed green, and the pre-push hook blocked the push. Of the six modules that exercise the
gate, one cleared every such var, two cleared none, and three cleared a subset.

**Approach:** one shared, opt-in fixture, `clean_mirror_env`, in the CFE `tests/conftest.py`. It removes every
`*_BASE_URL` and each name in `_http._EXTRA_MIRROR_ENV_VARS`, reading that tuple from `_http` under a private module
name, so the list cannot drift from the gate and no test module's own `_http` copy is replaced. The fixture is opt-in,
not suite-wide autouse, because `network`-marked CFE tests should keep an operator's real mirror routing. Each host-gate
module opts in: two module-level with `pytestmark`, two whose autouse fixtures now build on it, and the gate classes of
the two resolver modules. A new `test_clean_mirror_env.py` plants stray vars before the fixture runs, so CI, which
exports none, still exercises the regression. `_http.py` and `inventory_channel.py` do not change.

Ledger key: `24-1-cfe-s-host-gate-tests-pass-in-any-developer-shell`.
Ledger status (do not edit the ledger): `done`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-mason` CAP-34 (FR-56); AD-1 (CFE tests only, and Mason reaches none of it); AD-15 (the CFE surface moves
  only in the `retro(cfe):` commit).
- `spec-packaging-factory` and `spec-conda-forge-expert-rebuild` govern the CFE surface; both were reconciled.
- `spec-feature-flag-governance` CAP-1, Q1: a fix, no flag.

## Acceptance Criteria

- Given a shell that exports `ANTHROPIC_BASE_URL` When the seven affected CFE test modules run Then they pass
- Given the same modules When they run under `env -u ANTHROPIC_BASE_URL` Then they pass
- Given a stray `*_BASE_URL` and both npm registry vars set before the fixture runs When `clean_mirror_env` runs Then no `*_BASE_URL` and neither npm var remains, and `_fallback_configured_enterprise_hosts()` returns an empty set
- Given the fixture body disabled When the regression test and the originally failing test run Then all three of those tests fail (mutation)
- Given `network`-marked tests When they run Then they do not use the fixture
- Given `_http.py` and `inventory_channel.py` When the change lands Then neither file has moved
- Given a shell that exports `ANTHROPIC_BASE_URL` When `pixi run --frozen -e pyforge-guild pr-preflight` runs Then it exits 0
- Given the story closes When the Rule-2 retro runs Then its `retro(cfe):` commit carries the fixture, the tests, a CFE `CHANGELOG.md` semver entry and the version carriers

## Tasks

1. Invoke `conda-forge-expert` (Rule 1). Reproduce the failure with `ANTHROPIC_BASE_URL` set.
2. Add `clean_mirror_env` to `tests/conftest.py`, reading `_EXTRA_MIRROR_ENV_VARS` from `_http`.
3. Opt in `test_inventory_channel_auth_host_gate.py`, `test_http_skip_auth.py`, `test_http_jfrog_host_gate.py`,
   `test_dependency_checker_auth_host_gate.py`, and the gate classes of `test_http_resolvers.py` and
   `test_s3_resolver.py`. Drop the per-test `delenv` loops the fixture makes redundant.
4. Add `tests/unit/test_clean_mirror_env.py`, and run the fixture-disabled mutation check.
5. Add the testing rule to SKILL.md's host-gate constraint; bump the CFE version carriers to 8.91.1.
6. Reconcile every Spec `spec-surface` names: memlog first, `git add`, then a scoped `--write-baseline --spec` each.
7. Land everything in one commit, subject starting `retro(cfe):`, never `Story 24.1:`.

## Boundaries & Constraints

**Always:**
- Go through `conda-forge-expert`.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not change `_http.py` or `inventory_channel.py`.
- Do not make the fixture suite-wide autouse.
- Do not touch `src/shared/packages/pyforge-mason/`, `pixi.toml`, `pixi.lock` or `recipes/**`.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| agent shell | `ANTHROPIC_BASE_URL` exported | host-gate tests pass | — |
| clean shell | no stray var | host-gate tests pass | — |
| npm-routed shell | `npm_config_registry` exported | cleared before each host-gate test | — |
| fixture broken | body disabled | regression test and original test fail | CI reds |
| network tests | `-m network` | fixture not applied; real routing kept | — |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-34 (FR-56).
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-09-29 (later) — Proposed: the CFE host-gate tests give
the same verdict in any developer shell*.
Ledger key: `24-1-cfe-s-host-gate-tests-pass-in-any-developer-shell`.
Ledger status at mint: `done` (the code landed in the same PR as this chain, #1669).
Deps: —.
Flag: none (a fix; `spec-feature-flag-governance` CAP-1, Q1).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`; this story
  changes no Mason code).

**Manual checks:**
- `pytest` over the seven affected host-gate modules, with `ANTHROPIC_BASE_URL` set and under
  `env -u ANTHROPIC_BASE_URL` — expected: pass both ways.
- `pixi run --frozen -e pyforge-guild pr-preflight` from a shell that exports `ANTHROPIC_BASE_URL` — expected: exit 0.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Review Triage Log

- No independent review has run (implementation and review stay separate; behavioural guideline 8). The operator ruled
  that this already-implemented fix take the chain before merging, and the diff was verified by the checks below, not
  by a second reviewer. `followup_review_recommended: true` records that gap.

## Auto Run Result

Status: done (hand-landed; no harness run)

**Summary:** Added the opt-in `clean_mirror_env` fixture to the CFE `tests/conftest.py` and opted in every CFE test
module that exercises the credential host gate, so the gate's exact-set assertions no longer depend on the mirror and
tool env vars the runner's shell exports. Tests only; CFE v8.91.1.

**Files changed:**
- `.claude/skills/conda-forge-expert/tests/conftest.py` — `clean_mirror_env` fixture
- `.claude/skills/conda-forge-expert/tests/unit/test_clean_mirror_env.py` — new regression test
- `tests/unit/test_inventory_channel_auth_host_gate.py`, `test_http_skip_auth.py` — module-level opt-in
- `tests/unit/test_http_jfrog_host_gate.py`, `test_dependency_checker_auth_host_gate.py` — autouse fixtures build on it
- `tests/unit/test_http_resolvers.py`, `test_s3_resolver.py` — gate classes opt in
- CFE `SKILL.md` (host-gate testing paragraph), `CHANGELOG.md`, `MANIFEST.yaml`, `config/skill-config.yaml` — v8.91.1

**Verification (measured on the PR branch):**
- Before: 1 failed / 160 passed across the five host-gate files with `ANTHROPIC_BASE_URL` set.
- After: 182 passed across the seven affected files with the var set, and 182 passed under `env -u ANTHROPIC_BASE_URL`.
- Mutation: with the fixture body disabled, 3 failed (both new tests and the original); restored, all pass.
- `pixi run --frozen -e pyforge-guild pr-preflight` with `ANTHROPIC_BASE_URL` set: exit 0; the `test-ci` leg 9177
  passed, 0 failed; the pre-push hook's re-run also passed.
- PR #1669 CI: `detectors`, `scripts-suite` and `cfe-regression-net` passed.

**Residual risks:** the gate's other allowlist source, pixi config, is stubbed only in `test_http_jfrog_host_gate.py`. The
other modules assert no full allowlist, so an operator's pixi mirrors cannot red them today, but a future exact-set
assertion there would need the same stub.
